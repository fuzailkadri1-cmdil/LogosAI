"""
call_engine.py — Legacy Call Flow Engine

Handles the original DTMF (keypad) and keyword-based call routing that
predates the AI voice agent. Used for non-AI call flows and as a utility
layer for logging calls.

Note: The primary call handling path now goes through AIVoiceAgent in
ai_voice_agent.py. CallFlowEngine is still used for call logging and as
a fallback for DTMF-based menus.
"""

import re
from datetime import datetime
from models import db, CallLog


class CallFlowEngine:
    """
    Handles intent detection and call routing based on DTMF keypresses
    or keyword matching. Also provides call logging utilities.
    """

    # Canonical intent name constants
    INTENTS = {
        'ORDER_STATUS': 'OrderStatus',
        'STORE_HOURS': 'StoreHours',
        'CONNECT_AGENT': 'ConnectAgent',
        'VOICEMAIL': 'Voicemail',
        'UNKNOWN': 'Unknown'
    }

    # Fallback order database used when no pilot CSV has been uploaded
    ORDER_DATABASE = {
        '12345': 'Your order is out for delivery and will arrive tomorrow',
        '67890': 'Your order has been shipped and is in transit',
        '11111': 'Your order is being prepared and will ship within 24 hours',
        '22222': 'Your order has been delivered',
        '99999': 'Your order is pending payment confirmation'
    }

    def __init__(self, company):
        """
        Args:
            company (Company): The Company model instance for this call.
                               Used to read menu options, business hours, etc.
        """
        self.company = company

    def determine_intent(self, user_input, dtmf_choice=None):
        """
        Determine caller intent from either a DTMF keypress or speech input.

        DTMF keypresses are checked first because they are unambiguous.
        Speech input falls back to keyword matching.

        Args:
            user_input (str or None): The caller's spoken words (Twilio SpeechResult).
            dtmf_choice (str or None): The keypad digit pressed, if any.

        Returns:
            str: One of the INTENTS values (e.g. "OrderStatus", "StoreHours").
        """
        # DTMF takes priority — map keypress to the menu label, then to an intent
        if dtmf_choice:
            menu_options = self.company.get_menu_options()
            option_text = menu_options.get(str(dtmf_choice), '').lower()

            if 'order' in option_text:
                return self.INTENTS['ORDER_STATUS']
            elif 'hour' in option_text or 'time' in option_text:
                return self.INTENTS['STORE_HOURS']
            elif 'agent' in option_text or 'speak' in option_text:
                return self.INTENTS['CONNECT_AGENT']
            elif 'voicemail' in option_text or 'message' in option_text:
                return self.INTENTS['VOICEMAIL']

        if not user_input:
            return self.INTENTS['UNKNOWN']

        user_input_lower = user_input.lower()

        # Keyword lists for each intent — checked in priority order
        order_keywords = ['order', 'package', 'delivery', 'tracking', 'shipment', 'shipped']
        hours_keywords = ['hours', 'open', 'close', 'time', 'when', 'schedule']
        agent_keywords = ['agent', 'person', 'human', 'representative', 'help', 'speak', 'talk']
        voicemail_keywords = ['voicemail', 'message', 'leave a message', 'callback']

        if any(keyword in user_input_lower for keyword in order_keywords):
            return self.INTENTS['ORDER_STATUS']
        elif any(keyword in user_input_lower for keyword in hours_keywords):
            return self.INTENTS['STORE_HOURS']
        elif any(keyword in user_input_lower for keyword in voicemail_keywords):
            return self.INTENTS['VOICEMAIL']
        elif any(keyword in user_input_lower for keyword in agent_keywords):
            return self.INTENTS['CONNECT_AGENT']

        return self.INTENTS['UNKNOWN']

    def handle_order_status(self, order_number=None):
        """
        Look up an order and return a spoken status response.

        Checks the in-memory ORDER_DATABASE fallback. In a real deployment
        this would query PilotOrder via the database.

        Args:
            order_number (str or None): The order number provided by the caller.

        Returns:
            str: A spoken response describing the order status, or a prompt
                 asking the caller to provide their order number.
        """
        if not order_number:
            return "Please tell me your order number, or enter it using your keypad."

        # Strip non-digit characters (handles "order #12345", "12,345", etc.)
        order_number = re.sub(r'\D', '', order_number)

        if order_number in self.ORDER_DATABASE:
            return self.ORDER_DATABASE[order_number]
        else:
            return (
                f"I'm sorry, I couldn't find order number {order_number} in our system. "
                "Please verify your order number and try again, or press 3 to speak with an agent."
            )

    def handle_store_hours(self):
        """
        Build a spoken response describing the company's business hours.

        Returns:
            str: A response like "Our business hours are: Monday through Friday, 9am-5pm."
        """
        hours = self.company.get_business_hours()

        response = "Our business hours are as follows: "
        for period, times in hours.items():
            period_formatted = period.replace('-', ' through ').replace('_', ' ')
            response += f"{period_formatted}, {times}. "

        return response + "Is there anything else I can help you with?"

    def handle_connect_agent(self):
        """
        Generate a hold/transfer response, or a voicemail offer if no
        escalation number is configured.

        Returns:
            str: A spoken response for the caller.
        """
        if self.company.escalation_number:
            return "Please hold while I transfer you to an available agent."
        else:
            return (
                "I'm sorry, all agents are currently busy. "
                "Would you like to leave a voicemail? Press 1 for yes, or 2 to hear the menu again."
            )

    def handle_voicemail(self):
        """
        Return instructions for leaving a voicemail.

        Returns:
            str: Spoken instructions for the caller.
        """
        return "Please leave your message after the beep. When you're finished, press the pound key or simply hang up."

    def handle_unknown(self):
        """
        Handle an unrecognised intent by replaying the menu.

        Returns:
            str: An apology + the full greeting and menu options.
        """
        return "I'm sorry, I didn't understand your request. Let me repeat the menu options. " + self.get_greeting_with_menu()

    def get_greeting_with_menu(self):
        """
        Build the full greeting + keypad menu string for the company.

        Returns:
            str: Greeting message followed by "Press 1 for X, Press 2 for Y…"
        """
        greeting = self.company.greeting_message
        menu_options = self.company.get_menu_options()

        menu_text = " Please choose from the following options: "
        for key, value in sorted(menu_options.items()):
            menu_text += f"Press {key} for {value}. "

        return greeting + menu_text

    def extract_order_number(self, text):
        """
        Extract the first plausible order number from a text string.

        Looks for numeric sequences of 4–10 digits, which covers most
        real-world order number formats.

        Args:
            text (str): The caller's raw speech input.

        Returns:
            str or None: The first matching digit sequence, or None.
        """
        numbers = re.findall(r'\d+', text)

        for num in numbers:
            if 4 <= len(num) <= 10:
                return num

        return None

    def log_call(self, caller_phone, call_sid, intent, outcome,
                 transcript='', handled_by_ai=True, duration=0):
        """
        Create a new CallLog record in the database.

        Called at the start of every inbound call to establish the record,
        then updated as the call progresses.

        Args:
            caller_phone (str): The caller's phone number (E.164 format).
            call_sid (str):     The Twilio Call SID for this call.
            intent (str):       The detected intent (or None if not yet known).
            outcome (str):      Initial outcome — typically "in_progress".
            transcript (str):   Optional plain-text transcript summary.
            handled_by_ai (bool): True if the AI is handling the call.
            duration (int):     Call duration in seconds (0 at call start).

        Returns:
            CallLog: The newly created and committed CallLog instance.
        """
        call_log = CallLog(
            company_id=self.company.id,
            caller_phone=caller_phone,
            call_sid=call_sid,
            intent=intent,
            outcome=outcome,
            transcript=transcript,
            handled_by_ai=handled_by_ai,
            duration_seconds=duration,
            completed_at=datetime.utcnow() if outcome != 'in_progress' else None
        )

        db.session.add(call_log)
        db.session.commit()

        return call_log

    def update_call_log(self, call_log, **kwargs):
        """
        Update any fields on an existing CallLog and commit.

        Automatically sets completed_at if outcome changes away from
        "in_progress".

        Args:
            call_log (CallLog): The CallLog instance to update.
            **kwargs:           Column name → new value pairs.

        Returns:
            CallLog: The updated CallLog instance.
        """
        for key, value in kwargs.items():
            if hasattr(call_log, key):
                setattr(call_log, key, value)

        if kwargs.get('outcome') and call_log.outcome != 'in_progress':
            call_log.completed_at = datetime.utcnow()

        db.session.commit()
        return call_log


class IntentRouter:
    """
    Dispatches a resolved intent to the appropriate handler method.

    A stateless utility class — all methods are static.
    """

    @staticmethod
    def route_intent(engine, intent, context=None):
        """
        Call the correct handler on a CallFlowEngine based on detected intent.

        Args:
            engine (CallFlowEngine): The engine instance for this call.
            intent (str):            One of the CallFlowEngine.INTENTS values.
            context (dict, optional): Extra data needed by the handler.
                                      e.g. {"order_number": "12345"}

        Returns:
            str: The spoken response to send back to the caller.
        """
        context = context or {}

        if intent == CallFlowEngine.INTENTS['ORDER_STATUS']:
            order_number = context.get('order_number')
            return engine.handle_order_status(order_number)

        elif intent == CallFlowEngine.INTENTS['STORE_HOURS']:
            return engine.handle_store_hours()

        elif intent == CallFlowEngine.INTENTS['CONNECT_AGENT']:
            return engine.handle_connect_agent()

        elif intent == CallFlowEngine.INTENTS['VOICEMAIL']:
            return engine.handle_voicemail()

        else:
            return engine.handle_unknown()
