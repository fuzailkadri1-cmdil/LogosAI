import re
from datetime import datetime
from models import db, CallLog

class CallFlowEngine:
    
    INTENTS = {
        'ORDER_STATUS': 'OrderStatus',
        'STORE_HOURS': 'StoreHours',
        'CONNECT_AGENT': 'ConnectAgent',
        'VOICEMAIL': 'Voicemail',
        'UNKNOWN': 'Unknown'
    }
    
    ORDER_DATABASE = {
        '12345': 'Your order is out for delivery and will arrive tomorrow',
        '67890': 'Your order has been shipped and is in transit',
        '11111': 'Your order is being prepared and will ship within 24 hours',
        '22222': 'Your order has been delivered',
        '99999': 'Your order is pending payment confirmation'
    }
    
    def __init__(self, company):
        self.company = company
    
    def determine_intent(self, user_input, dtmf_choice=None):
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
        if not order_number:
            return "Please tell me your order number, or enter it using your keypad."
        
        order_number = re.sub(r'\D', '', order_number)
        
        if order_number in self.ORDER_DATABASE:
            return self.ORDER_DATABASE[order_number]
        else:
            return f"I'm sorry, I couldn't find order number {order_number} in our system. Please verify your order number and try again, or press 3 to speak with an agent."
    
    def handle_store_hours(self):
        hours = self.company.get_business_hours()
        
        response = "Our business hours are as follows: "
        for period, times in hours.items():
            period_formatted = period.replace('-', ' through ').replace('_', ' ')
            response += f"{period_formatted}, {times}. "
        
        return response + "Is there anything else I can help you with?"
    
    def handle_connect_agent(self):
        if self.company.escalation_number:
            return f"Please hold while I transfer you to an available agent."
        else:
            return "I'm sorry, all agents are currently busy. Would you like to leave a voicemail? Press 1 for yes, or 2 to hear the menu again."
    
    def handle_voicemail(self):
        return "Please leave your message after the beep. When you're finished, press the pound key or simply hang up."
    
    def handle_unknown(self):
        return "I'm sorry, I didn't understand your request. Let me repeat the menu options. " + self.get_greeting_with_menu()
    
    def get_greeting_with_menu(self):
        greeting = self.company.greeting_message
        menu_options = self.company.get_menu_options()
        
        menu_text = " Please choose from the following options: "
        for key, value in sorted(menu_options.items()):
            menu_text += f"Press {key} for {value}. "
        
        return greeting + menu_text
    
    def extract_order_number(self, text):
        numbers = re.findall(r'\d+', text)
        
        for num in numbers:
            if len(num) >= 4 and len(num) <= 10:
                return num
        
        return None
    
    def log_call(self, caller_phone, call_sid, intent, outcome, transcript='', handled_by_ai=True, duration=0):
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
        for key, value in kwargs.items():
            if hasattr(call_log, key):
                setattr(call_log, key, value)
        
        if kwargs.get('outcome') and call_log.outcome != 'in_progress':
            call_log.completed_at = datetime.utcnow()
        
        db.session.commit()
        return call_log


class IntentRouter:
    
    @staticmethod
    def route_intent(engine, intent, context=None):
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
