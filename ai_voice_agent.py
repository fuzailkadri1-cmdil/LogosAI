import os
import json
from openai import OpenAI
from orders_db import lookup_order, format_order_status, extract_order_number_from_speech, normalize_spoken_numbers
from ssml_helper import get_cached_ssml, conversational_response, SSML_ENABLED
from latency_logger import get_tracker, reset_tracker, start_new_turn
from business_hours import is_store_open

def get_openai_client():
    """Initialize OpenAI client with Replit AI Integrations"""
    return OpenAI(
        base_url=os.environ.get('AI_INTEGRATIONS_OPENAI_BASE_URL'),
        api_key=os.environ.get('AI_INTEGRATIONS_OPENAI_API_KEY')
    )

SYSTEM_PROMPT = """You're a warm, helpful customer service assistant. Speak naturally like a real person - use contractions (I'm, you're, we'll), vary your sentence length, and sound genuinely friendly. Keep responses brief (1-2 sentences). You can help with orders, store hours, pickup status, and general questions."""

def get_response(key):
    """Get cached response with SSML if enabled."""
    return get_cached_ssml(key)

CACHED_RESPONSES = {
    'store_hours': "We're open Monday through Friday, 9 to 5! Anything else I can help with?",
    'greeting': "Hi there! What can I help you with today?",
    'ask_order_number': "Sure thing! What's your order number?",
    'order_not_found': "Hmm, I'm not finding that one. Could you double-check that order number for me?",
    'goodbye': "Thanks so much for calling! Take care!",
    'escalate': "Absolutely, let me get you to someone who can help with that right away.",
    'anything_else': "Anything else I can help with?",
    'didnt_catch': "Sorry, I didn't quite catch that. What was your order number again?",
    'after_hours_human_needed': "Our team is with other customers right now, but I want to make sure you get help. Can I get your name so someone can call you back?",
    'pickup_ready': "Great news! Your order is ready for pickup.",
    'pickup_not_ready': "Your order is still being prepared. We'll let you know as soon as it's ready!"
}

GOODBYE_PHRASES = [
    "that's all", "that's it", "i'm good", "i'm done",
    "nothing else", "no thanks", "no thank you", "that'll be all",
    "all set", "i'm all set", "that helps", "that's everything",
    "that would be all", "i'm finished", "that does it"
]

GOODBYE_WORDS = [
    'nope', 'goodbye', 'bye'
]

# Intent Categories - determines escalation behavior
INTENT_CATEGORIES = {
    # AI handles these 24/7, no escalation needed
    'AI_RESOLVABLE': ['order_status', 'store_hours', 'pickup_readiness', 'general_inquiry', 'greeting', 'goodbye'],
    # Sales inquiries - capture lead, escalate only during hours
    'SALES_LEAD': ['purchase_inquiry'],
    # Requires human - escalate during hours, offer callback after hours
    'HUMAN_REQUIRED': ['refund', 'return', 'cancel_order', 'billing_issue', 'complaint', 'speak_to_human']
}

# Keywords that explicitly request human assistance
EXPLICIT_HUMAN_REQUEST = [
    'speak to someone', 'human', 'agent', 'representative', 'manager',
    'supervisor', 'person', 'real person', 'talk to someone', 'speak to a person'
]

# Keywords for human-required intents (issues needing human judgment)
HUMAN_REQUIRED_KEYWORDS = {
    'refund': ['refund', 'money back', 'get my money'],
    'return': ['return', 'send back', 'exchange'],
    'cancel_order': ['cancel my order', 'cancel order', 'cancel the order'],
    'billing_issue': ['billing', 'charged wrong', 'overcharged', 'double charged', 'payment issue'],
    'complaint': ['complaint', 'angry', 'upset', 'frustrated', 'disappointed', 'terrible', 'horrible', 'worst']
}

# =============================================================================
# CONTEXT-AWARE INTENT DETECTION SYSTEM
# =============================================================================
#
# PROBLEM SOLVED: Phrases like "I'm looking for" or "do you have" could mean:
#   - ORDER inquiry: "I'm looking for my order status" (AI handles 24/7)
#   - SALES inquiry: "I'm looking for a red jacket" (capture lead)
#
# SOLUTION: Check for ORDER CONTEXT first, then check for PURCHASE INTENT
# The AI analyzes the FULL sentence, not just the opening words.
# =============================================================================

# ORDER CONTEXT WORDS - indicate caller is asking about an EXISTING order
# These use possessive patterns (my, the) or reference existing transactions
ORDER_CONTEXT_WORDS = [
    # Possessive + order-related nouns
    'my order', 'my package', 'my delivery', 'my shipment', 'my tracking',
    'my purchase', 'my item', 'my stuff',

    # Definite article + order context (referring to specific existing order)
    'the order', 'the package', 'the delivery', 'the shipment',

    # Status/tracking specific phrases
    'order status', 'order number', 'order info', 'order information',
    'tracking number', 'tracking info', 'tracking status',
    'delivery status', 'delivery date', 'delivery time',
    'shipment status', 'shipment info',

    # Question patterns about existing orders
    'where is my', 'when will my', 'has my', 'did my', 'is my order',
    'check on my', 'update on my', 'status of my', 'info on my',
    'where\'s my', 'when\'s my',

    # Past tense - indicates they already placed an order
    'placed an order', 'made an order', 'placed order', 'made order',
    'ordered something', 'ordered from', 'i ordered',

    # Confirmation/receipt references
    'confirmation number', 'receipt', 'order confirmation',
    'reference number', 'order id'
]

# PURCHASE INTENT PHRASES - indicate caller wants to BUY something new
# These are checked ONLY if no order context is found
PURCHASE_INTENT_PHRASES = [
    # "Do you have" patterns (product availability)
    'do you have', 'do you carry', 'do you sell', 'do you stock',
    'got any', 'have any',

    # "Looking for" patterns (product search) - NOT "looking for my order"
    'looking for a', 'looking for an', 'looking for some',
    "i'm looking for a", "i'm looking for an", "i'm looking for some",
    'i am looking for a', 'i am looking for an',

    # "Looking to" patterns (intent to purchase)
    'looking to order', 'looking to buy', 'looking to get', 'looking to purchase',
    "i'm looking to order", "i'm looking to buy",

    # "Want to" patterns (purchase intent)
    'i want to buy', 'i want to order', 'i want to get', 'i want to purchase',
    'want to buy', 'want to order', 'want to get',
    'i wanna buy', 'i wanna order', 'wanna buy', 'wanna order',

    # "Would like to" patterns
    'i would like to order', 'i would like to buy',
    "i'd like to order", "i'd like to buy",
    'like to order', 'like to buy',

    # "Can I" patterns
    'can i order', 'can i buy', 'can i get', 'can i purchase',

    # "Need" patterns (product need, not order support need)
    'i need a', 'i need an', 'i need some', 'i need to buy', 'i need to order',

    # Stock/availability questions
    'is this in stock', 'in stock', 'available', 'availability',
    'do you still have',

    # Price inquiries (indicates purchase interest)
    'price of', 'how much is', 'how much does', 'how much for',
    'what does it cost', 'cost of',

    # General purchase language
    'purchase', 'interested in', 'interested in buying',
    'want to get', 'can you get',

    # Place order patterns (future action, not existing order)
    'place an order', 'make an order', 'put in an order',
    'to order a', 'to buy a', 'to get a'
]

# Phrases for pickup readiness inquiries
PICKUP_READINESS_PHRASES = [
    'is my order ready', 'order ready for pickup', 'ready for pickup',
    'can i pick up', 'pickup ready', 'is it ready', 'ready to pick up',
    'when can i pick up', 'pickup status', 'ready yet',
    'come pick up', 'come get my order'
]

# Order status inquiry phrases (legacy - now merged with ORDER_CONTEXT_WORDS)
ORDER_STATUS_PHRASES = [
    'order status', 'where is my order', 'track my order', 'tracking',
    'shipment', 'delivery', 'package', 'when will', 'order number',
    'my order', 'an order', 'the order'
]

# Store hours inquiry phrases
STORE_HOURS_PHRASES = [
    'hours', 'open', 'close', 'closing', 'opening', 'when do you',
    'what time', 'are you open', 'business hours', 'store hours',
    'when are you', 'what are your hours'
]


class AIVoiceAgent:
    def __init__(self, company_config, pilot_id=None, call_sid=None, caller_phone=None):
        """Initialize AI agent with company-specific configuration"""
        self.company_config = company_config
        self.pilot_id = pilot_id
        self.call_sid = call_sid
        self.caller_phone = caller_phone
        self.conversation_history = []
        self.conversation_state = 'initial'
        self.current_intent = None
        self.order_data = None
        self.use_ssml = SSML_ENABLED

        self.lead_data = {
            'caller_name': None,
            'caller_phone': caller_phone,
            'inquiry': None,
            'call_type': None,
            'captured': False
        }

        self.latency_tracker = None

    def _has_order_context(self, user_lower):
        """
        Check if the sentence contains ORDER CONTEXT - indicating an existing order inquiry.
        This is checked FIRST, before purchase intent.

        Examples that return True:
          - "I'm looking for my order status" (contains "my order")
          - "Do you have info on my delivery" (contains "my delivery")
          - "I placed an order last week" (contains "placed an order")

        Examples that return False:
          - "I'm looking for a red jacket" (no order context)
          - "Do you have Nike shoes" (no order context)
        """
        for phrase in ORDER_CONTEXT_WORDS:
            if phrase in user_lower:
                return True
        return False

    def _is_purchase_intent(self, user_lower):
        """
        Check if this is a PURCHASE inquiry - but ONLY if no order context exists.
        This prevents "I'm looking for my order" from being classified as sales.

        Examples that return True:
          - "I'm looking for a red jacket" (no order context + purchase phrase)
          - "Do you have Nike shoes in stock" (no order context + purchase phrase)
          - "I'm looking to order a birthday gift" (no order context + purchase phrase)

        Examples that return False:
          - "I'm looking for my order status" (has order context)
          - "Do you have my tracking info" (has order context)
        """
        # SAFETY CHECK: If ANY order context exists, this is NOT a purchase inquiry
        if self._has_order_context(user_lower):
            return False

        # Now check for purchase intent phrases
        for phrase in PURCHASE_INTENT_PHRASES:
            if phrase in user_lower:
                return True

        return False

    def _extract_inquiry_details(self, user_speech):
        """Extract what the caller is looking for from their speech"""
        return user_speech.strip()

    def _is_store_open(self):
        """Check if store is currently open based on business hours"""
        import logging as _log
        from datetime import datetime
        business_hours = self.company_config.get('business_hours', {})
        result = is_store_open(business_hours)
        _log.info(f"HOURS CHECK: utc={datetime.utcnow().strftime('%a %H:%M')} biz_hours={business_hours} → is_open={result['is_open']}")
        return result['is_open']

    def _lookup_pilot_order(self, order_num):
        """Look up order from pilot's order database"""
        if not self.pilot_id:
            return None
        try:
            from models import PilotOrder
            order = PilotOrder.query.filter_by(pilot_id=self.pilot_id, order_id=order_num).first()
            if order:
                status_map = {
                    'processing': 'being prepared for shipment',
                    'shipped': 'shipped and on the way',
                    'out_for_delivery': 'out for delivery',
                    'delivered': 'delivered',
                    'cancelled': 'cancelled'
                }
                total = 0
                if order.order_total:
                    try:
                        clean_total = order.order_total.replace('$', '').replace(',', '').strip()
                        total = float(clean_total) if clean_total else 0
                    except (ValueError, AttributeError):
                        total = 0
                return {
                    'order_number': order.order_id,
                    'status': order.status.lower() if order.status else 'processing',
                    'status_text': status_map.get(order.status.lower() if order.status else 'processing', order.status or 'being processed'),
                    'delivery_date': order.estimated_delivery or 'soon',
                    'delivery_time': '',
                    'delivery_address': order.delivery_address or '',
                    'tracking_number': order.tracking_number,
                    'items': [],
                    'total': total,
                    'customer_name': order.customer_name
                }
        except Exception as e:
            print(f"Error looking up pilot order: {e}")
        return None

    def _smart_lookup_order(self, order_num):
        """Look up order from pilot database first, then fall back to demo database"""
        pilot_order = self._lookup_pilot_order(order_num)
        if pilot_order:
            return pilot_order
        return lookup_order(order_num)

    def process_speech(self, user_speech, context=None):
        """
        Process user speech and generate AI response
        Returns: {
            'response': str,
            'should_escalate': bool,
            'should_end_call': bool,
            'intent': str,
            'confidence': float,
            'escalation_reason': str or None
        }
        """
        # Start fresh latency tracking for this turn
        self.latency_tracker = start_new_turn(self.call_sid)
        self.latency_tracker.checkpoint('stt_complete')

        # Add user message to conversation history
        self.conversation_history.append({
            'role': 'user',
            'content': user_speech
        })

        # Handle different conversation states
        if self.conversation_state == 'offering_more_help':
            return self._handle_followup_response(user_speech)

        if self.conversation_state == 'waiting_for_order_number':
            return self._handle_order_number_response(user_speech)

        if self.conversation_state == 'capturing_lead_name':
            return self._handle_lead_name_response(user_speech)

        if self.conversation_state == 'capturing_lead_details':
            return self._handle_lead_details_response(user_speech)

        if self.conversation_state == 'confirming_callback':
            return self._handle_callback_confirmation(user_speech)

        # Analyze intent first to determine proper routing
        intent_analysis = self._analyze_intent(user_speech)
        category = intent_analysis.get('category', 'AI_RESOLVABLE')

        # Handle HUMAN_REQUIRED intents (respects business hours)
        if category == 'HUMAN_REQUIRED':
            escalation_check = self._check_escalation(user_speech)
            if escalation_check.get('should_escalate') or escalation_check.get('response'):
                return escalation_check

        # Handle SALES_LEAD intents - trigger lead capture flow
        if category == 'SALES_LEAD':
            return self._handle_purchase_intent(user_speech)

        # Handle AI_RESOLVABLE intents - AI handles 24/7
        if intent_analysis['intent'] == 'order_status':
            return self._handle_order_status_inquiry(user_speech)

        if intent_analysis['intent'] == 'pickup_readiness':
            return self._handle_pickup_readiness_inquiry(user_speech)

        if intent_analysis['intent'] == 'store_hours':
            return self._handle_store_hours_inquiry(user_speech)

        # For general inquiries, use GPT to generate response
        return self._generate_ai_response(user_speech, intent_analysis)

    def _handle_order_status_inquiry(self, user_speech):
        """Handle order status inquiry - ask for order number"""
        # Try to extract order number from initial query
        order_num = extract_order_number_from_speech(user_speech)

        if order_num:
            # User provided order number in initial query
            order_data = self._smart_lookup_order(order_num)
            if order_data:
                status_response = format_order_status(order_data)
                self.conversation_state = 'offering_more_help'
                self.order_data = order_data

                # Use SSML-enhanced response
                response_text = f"{status_response} {get_response('anything_else')}"

                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response_text
                })

                # Log response ready
                if self.latency_tracker:
                    self.latency_tracker.checkpoint('response_ready')
                    self.latency_tracker.log_summary()

                return {
                    'response': response_text,
                    'should_escalate': False,
                    'should_end_call': False,
                    'intent': 'order_status',
                    'confidence': 0.95,
                    'escalation_reason': None
                }
            else:
                # Order not found
                return self._handle_order_not_found(order_num)

        # Ask for order number
        self.conversation_state = 'waiting_for_order_number'
        self.current_intent = 'order_status'

        # Use SSML-enhanced response
        response_text = get_response('ask_order_number')

        self.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })

        # Log response ready
        if self.latency_tracker:
            self.latency_tracker.checkpoint('response_ready')
            self.latency_tracker.log_summary()

        return {
            'response': response_text,
            'should_escalate': False,
            'should_end_call': False,
            'intent': 'order_status',
            'confidence': 0.9,
            'escalation_reason': None
        }

    def _handle_order_number_response(self, user_speech):
        """Handle user providing their order number - routes based on current_intent"""
        import re

        # First try standard extraction
        order_num = extract_order_number_from_speech(user_speech)

        # If that fails, accept bare digits since we're already waiting for an order number
        if not order_num:
            normalized = normalize_spoken_numbers(user_speech)
            bare_match = re.match(r'^\s*(\d+)\s*$', normalized)
            if bare_match:
                order_num = bare_match.group(1)

        if not order_num:
            response_text = get_response('didnt_catch')

            self.conversation_history.append({
                'role': 'assistant',
                'content': response_text
            })

            if self.latency_tracker:
                self.latency_tracker.checkpoint('response_ready')
                self.latency_tracker.log_summary()

            return {
                'response': response_text,
                'should_escalate': False,
                'should_end_call': False,
                'intent': self.current_intent or 'order_status',
                'confidence': 0.7,
                'escalation_reason': None
            }

        # Look up order
        order_data = self._smart_lookup_order(order_num)

        if not order_data:
            return self._handle_order_not_found(order_num)

        # Route based on current_intent (pickup_readiness vs order_status)
        if self.current_intent == 'pickup_readiness':
            status = order_data.get('status', '').lower()
            if status in ['ready', 'ready_for_pickup', 'available']:
                response_text = f"Great news! Order {order_num} is ready for pickup. You can come get it during our business hours."
            elif status == 'delivered':
                response_text = f"It looks like order {order_num} has already been picked up or delivered."
            else:
                response_text = f"Order {order_num} is still being prepared. We'll let you know as soon as it's ready for pickup!"

            if self.use_ssml:
                response_text = conversational_response(response_text)
            intent = 'pickup_readiness'
        else:
            # Default: order status
            status_response = format_order_status(order_data)
            response_text = status_response
            intent = 'order_status'

        self.conversation_state = 'offering_more_help'
        self.order_data = order_data
        response_text += " " + get_response('anything_else')

        self.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })

        if self.latency_tracker:
            self.latency_tracker.checkpoint('response_ready')
            self.latency_tracker.log_summary()

        return {
            'response': response_text,
            'should_escalate': False,
            'should_end_call': False,
            'intent': intent,
            'confidence': 0.95,
            'escalation_reason': None
        }

    def _handle_order_not_found(self, order_num):
        """Handle when order number is not found in database - ask to retry, no escalation"""
        response_text = "Hmm, I'm not finding that order. Could you double-check the number and try again? It's usually on your order confirmation email."

        if self.use_ssml:
            response_text = conversational_response(response_text)

        self.conversation_state = 'waiting_for_order_number'

        self.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })

        if self.latency_tracker:
            self.latency_tracker.checkpoint('response_ready')
            self.latency_tracker.log_summary()

        return {
            'response': response_text,
            'should_escalate': False,
            'should_end_call': False,
            'intent': 'order_status',
            'confidence': 0.9,
            'escalation_reason': None
        }

    def _handle_pickup_readiness_inquiry(self, user_speech):
        """Handle pickup readiness inquiry - ask for order number and check status"""
        order_num = extract_order_number_from_speech(user_speech)

        if order_num:
            order_data = self._smart_lookup_order(order_num)
            if order_data:
                status = order_data.get('status', '').lower()
                if status in ['ready', 'ready_for_pickup', 'available']:
                    response_text = f"Great news! Order {order_num} is ready for pickup. You can come get it during our business hours."
                elif status == 'delivered':
                    response_text = f"It looks like order {order_num} has already been picked up or delivered."
                else:
                    response_text = f"Order {order_num} is still being prepared. We'll let you know as soon as it's ready for pickup!"

                if self.use_ssml:
                    response_text = conversational_response(response_text)

                response_text += " " + get_response('anything_else')
                self.conversation_state = 'offering_more_help'

                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response_text
                })

                if self.latency_tracker:
                    self.latency_tracker.checkpoint('response_ready')
                    self.latency_tracker.log_summary()

                return {
                    'response': response_text,
                    'should_escalate': False,
                    'should_end_call': False,
                    'intent': 'pickup_readiness',
                    'confidence': 0.95,
                    'escalation_reason': None
                }
            else:
                response_text = "I couldn't find that order. What's your order number? It should be on your confirmation email."
                self.conversation_state = 'waiting_for_order_number'
                self.current_intent = 'pickup_readiness'

                if self.use_ssml:
                    response_text = conversational_response(response_text)

                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response_text
                })

                return {
                    'response': response_text,
                    'should_escalate': False,
                    'should_end_call': False,
                    'intent': 'pickup_readiness',
                    'confidence': 0.8,
                    'escalation_reason': None
                }

        response_text = "Sure, I can check if your order is ready! What's your order number?"
        self.conversation_state = 'waiting_for_order_number'
        self.current_intent = 'pickup_readiness'

        if self.use_ssml:
            response_text = conversational_response(response_text)

        self.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })

        if self.latency_tracker:
            self.latency_tracker.checkpoint('response_ready')
            self.latency_tracker.log_summary()

        return {
            'response': response_text,
            'should_escalate': False,
            'should_end_call': False,
            'intent': 'pickup_readiness',
            'confidence': 0.9,
            'escalation_reason': None
        }

    def _handle_store_hours_inquiry(self, user_speech):
        """Handle store hours inquiry - AI resolves 24/7"""
        hours = self.company_config.get('business_hours', 'Monday through Friday, 9 AM to 5 PM')

        if self.use_ssml:
            response_text = conversational_response(f"Our business hours are {hours}.")
        else:
            response_text = f"Our business hours are {hours}."

        response_text += " " + get_response('anything_else')
        self.conversation_state = 'offering_more_help'

        self.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })

        if self.latency_tracker:
            self.latency_tracker.checkpoint('llm_complete')
            self.latency_tracker.checkpoint('response_ready')
            self.latency_tracker.log_summary()

        return {
            'response': response_text,
            'should_escalate': False,
            'should_end_call': False,
            'intent': 'store_hours',
            'confidence': 0.95,
            'escalation_reason': None
        }

    def _handle_followup_response(self, user_speech):
        """Handle response to 'Is there anything else I can help you with?'"""
        import re

        user_lower = user_speech.lower().strip()

        # Check for exact phrase matches
        for phrase in GOODBYE_PHRASES:
            if phrase in user_lower:
                self.conversation_state = 'goodbye'
                response_text = get_response('goodbye')

                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response_text
                })

                return {
                    'response': response_text,
                    'should_escalate': False,
                    'should_end_call': True,
                    'intent': 'goodbye',
                    'confidence': 1.0,
                    'escalation_reason': None
                }

        # Check for single-word matches with word boundaries
        for word in GOODBYE_WORDS:
            if re.search(r'\b' + re.escape(word) + r'\b', user_lower):
                self.conversation_state = 'goodbye'
                response_text = get_response('goodbye')

                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response_text
                })

                return {
                    'response': response_text,
                    'should_escalate': False,
                    'should_end_call': True,
                    'intent': 'goodbye',
                    'confidence': 1.0,
                    'escalation_reason': None
                }

        # Special case: bare "no" ONLY when it's the complete response
        if user_lower in ['no', 'no.', 'no!']:
            self.conversation_state = 'goodbye'
            response_text = get_response('goodbye')

            self.conversation_history.append({
                'role': 'assistant',
                'content': response_text
            })

            return {
                'response': response_text,
                'should_escalate': False,
                'should_end_call': True,
                'intent': 'goodbye',
                'confidence': 1.0,
                'escalation_reason': None
            }

        # User has another question - reset state and process it
        self.conversation_state = 'initial'
        self.current_intent = None
        self.order_data = None

        # Remove the just-added user message to prevent duplication when we re-process
        if self.conversation_history and self.conversation_history[-1]['role'] == 'user':
            self.conversation_history.pop()

        # Now process the new question normally
        return self.process_speech(user_speech)

    def _generate_ai_response(self, user_speech, intent_analysis):
        """Generate AI response using GPT for general queries - AI handles without escalation"""
        system_msg = self._build_system_prompt()

        try:
            client = get_openai_client()
            response = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {'role': 'system', 'content': system_msg},
                    *self.conversation_history[-4:]
                ],
                temperature=0.5,
                max_tokens=80
            )

            # Log LLM complete
            if self.latency_tracker:
                self.latency_tracker.checkpoint('llm_complete')

            ai_response = response.choices[0].message.content

            # Apply SSML to AI response if enabled
            if self.use_ssml:
                ai_response = conversational_response(ai_response)

            # Check if we should offer more help after this response
            should_offer_help = self._should_offer_more_help(intent_analysis['intent'])

            if should_offer_help:
                self.conversation_state = 'offering_more_help'
                ai_response += " " + get_response('anything_else')

            # Add AI response to history
            self.conversation_history.append({
                'role': 'assistant',
                'content': ai_response
            })

            # Re-analyze for escalation after GPT response
            final_analysis = self._check_for_escalation_in_response(ai_response, intent_analysis)

            # Log response ready
            if self.latency_tracker:
                self.latency_tracker.checkpoint('response_ready')
                self.latency_tracker.log_summary()

            return {
                'response': ai_response,
                'should_escalate': final_analysis['should_escalate'],
                'should_end_call': False,
                'intent': intent_analysis['intent'],
                'confidence': intent_analysis['confidence'],
                'escalation_reason': final_analysis.get('escalation_reason')
            }

        except Exception as e:
            print(f"OpenAI API error: {e}")
            # Fallback - escalate during hours, apologize after hours
            store_open = self._is_store_open()
            if store_open:
                return {
                    'response': "I'm having trouble processing your request. Let me connect you with someone who can help.",
                    'should_escalate': True,
                    'should_end_call': False,
                    'intent': 'error',
                    'confidence': 0.0,
                    'escalation_reason': 'api_error'
                }
            else:
                return {
                    'response': "I'm sorry, I'm having some trouble right now. Please try calling back during our business hours.",
                    'should_escalate': False,
                    'should_end_call': True,
                    'intent': 'error',
                    'confidence': 0.0,
                    'escalation_reason': None
                }

    def _should_offer_more_help(self, intent):
        """Determine if we should offer continued assistance after this response"""
        # Offer help after successfully resolving these intents
        helpful_intents = ['store_hours', 'general_inquiry', 'appointment']
        return intent in helpful_intents

    def _build_system_prompt(self):
        """Build system prompt with company-specific info"""
        company_info = f"""
Company: {self.company_config.get('name', 'Our Company')}
Business Hours: {self.company_config.get('business_hours', 'Monday-Friday 9am-5pm')}
Phone: {self.company_config.get('phone_number', '')}
"""
        return SYSTEM_PROMPT + "\n\n" + company_info

    def _check_escalation(self, user_speech):
        """Check if user speech contains escalation triggers - respects business hours"""
        user_lower = user_speech.lower()
        store_open = self._is_store_open()

        # Check for explicit human request
        for phrase in EXPLICIT_HUMAN_REQUEST:
            if phrase in user_lower:
                if store_open:
                    return {
                        'response': get_response('escalate'),
                        'should_escalate': True,
                        'should_end_call': False,
                        'intent': 'speak_to_human',
                        'confidence': 1.0,
                        'escalation_reason': f'explicit_request: {phrase}'
                    }
                else:
                    # After hours - start callback capture flow
                    return self._handle_after_hours_human_request(user_speech)

        # Check for human-required intents
        for intent, keywords in HUMAN_REQUIRED_KEYWORDS.items():
            for keyword in keywords:
                if keyword in user_lower:
                    if store_open:
                        return {
                            'response': get_response('escalate'),
                            'should_escalate': True,
                            'should_end_call': False,
                            'intent': intent,
                            'confidence': 0.9,
                            'escalation_reason': f'human_required: {intent}'
                        }
                    else:
                        # After hours - start callback capture flow
                        return self._handle_after_hours_human_request(user_speech)

        return {'should_escalate': False}

    def _handle_after_hours_human_request(self, user_speech):
        """Handle requests that need humans when store is closed - offer callback"""
        self.lead_data['inquiry'] = user_speech.strip()
        self.lead_data['call_type'] = 'after_hours'

        store_name = self.company_config.get('name', 'our store')
        response_text = f"Our team at {store_name} is unavailable right now, but I want to make sure you get the help you need. Can I get your name so someone can call you back?"

        self.conversation_state = 'capturing_lead_name'
        self.current_intent = 'callback_request'

        if self.use_ssml:
            response_text = conversational_response(response_text)

        self.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })

        if self.latency_tracker:
            self.latency_tracker.checkpoint('response_ready')
            self.latency_tracker.log_summary()

        return {
            'response': response_text,
            'should_escalate': False,
            'should_end_call': False,
            'intent': 'callback_request',
            'confidence': 0.9,
            'escalation_reason': None
        }

    def _analyze_intent(self, user_speech):
        """
        Analyze intent from user speech using CONTEXT-AWARE detection.

        KEY LOGIC: Check for ORDER CONTEXT first, THEN check for PURCHASE INTENT.
        This ensures "I'm looking for my order" routes to order_status, not sales.

        Priority Order:
        1. Explicit human request (speak to agent, etc.)
        2. Human-required intents (refund, return, complaint)
        3. ORDER CONTEXT (my order, tracking, delivery) -> order_status
        4. Pickup readiness phrases
        5. Store hours phrases
        6. PURCHASE INTENT (only if no order context)
        7. General inquiry (default)
        """
        user_lower = user_speech.lower()

        # 1. Check for explicit human request first (highest priority)
        for phrase in EXPLICIT_HUMAN_REQUEST:
            if phrase in user_lower:
                return {'intent': 'speak_to_human', 'confidence': 1.0, 'category': 'HUMAN_REQUIRED'}

        # 2. Check for human-required intents (refund, return, billing, complaint)
        for intent, keywords in HUMAN_REQUIRED_KEYWORDS.items():
            for keyword in keywords:
                if keyword in user_lower:
                    return {'intent': intent, 'confidence': 0.9, 'category': 'HUMAN_REQUIRED'}

        # 3. CHECK FOR ORDER CONTEXT FIRST - catches "I'm looking for my order status"
        #    This MUST come before purchase intent check!
        if self._has_order_context(user_lower):
            return {'intent': 'order_status', 'confidence': 0.95, 'category': 'AI_RESOLVABLE'}

        # 4. Check for pickup readiness
        for phrase in PICKUP_READINESS_PHRASES:
            if phrase in user_lower:
                return {'intent': 'pickup_readiness', 'confidence': 0.9, 'category': 'AI_RESOLVABLE'}

        # 5. Check for store hours
        for phrase in STORE_HOURS_PHRASES:
            if phrase in user_lower:
                return {'intent': 'store_hours', 'confidence': 0.9, 'category': 'AI_RESOLVABLE'}

        # 6. NOW check for purchase/sales intent - ONLY reaches here if NO order context
        #    This catches "I'm looking for a red jacket", "Do you have Nike shoes"
        if self._is_purchase_intent(user_lower):
            return {'intent': 'purchase_inquiry', 'confidence': 0.9, 'category': 'SALES_LEAD'}

        # 7. Default to general inquiry (AI can handle)
        return {'intent': 'general_inquiry', 'confidence': 0.7, 'category': 'AI_RESOLVABLE'}

    def _get_intent_category(self, intent):
        """Get the category for a given intent"""
        for category, intents in INTENT_CATEGORIES.items():
            if intent in intents:
                return category
        return 'AI_RESOLVABLE'

    def _check_for_escalation_in_response(self, ai_response, intent_analysis):
        """Check if AI response requires escalation based on intent category and business hours"""
        category = intent_analysis.get('category', self._get_intent_category(intent_analysis['intent']))
        store_open = self._is_store_open()

        # AI_RESOLVABLE intents never escalate - AI handles 24/7
        if category == 'AI_RESOLVABLE':
            return {'should_escalate': False}

        # SALES_LEAD intents only escalate during business hours
        if category == 'SALES_LEAD':
            # This is handled by lead capture flow, not here
            return {'should_escalate': False}

        # HUMAN_REQUIRED intents escalate during hours, offer callback after hours
        if category == 'HUMAN_REQUIRED':
            if store_open:
                return {
                    'should_escalate': True,
                    'escalation_reason': f"human_required: {intent_analysis['intent']}"
                }
            else:
                # After hours - don't escalate, handled separately
                return {'should_escalate': False}

        return {'should_escalate': False}

    def get_conversation_summary(self):
        """Get summary of conversation for logging"""
        return {
            'turns': len(self.conversation_history) // 2,
            'messages': self.conversation_history,
            'state': self.conversation_state,
            'intent': self.current_intent
        }

    def _handle_purchase_intent(self, user_speech):
        """Handle purchase intent - start lead capture flow"""
        store_open = self._is_store_open()
        self.lead_data['inquiry'] = self._extract_inquiry_details(user_speech)
        self.lead_data['call_type'] = 'during_hours' if store_open else 'after_hours'

        if store_open:
            response_text = "Let me connect you with our team. Before I transfer, can I get your name in case we get disconnected?"
        else:
            store_name = self.company_config.get('name', 'our store')
            response_text = "Thanks so much for calling! We're closed right now but we really appreciate you reaching out. Can I get your name so someone can follow up with you tomorrow?"

        self.conversation_state = 'capturing_lead_name'
        self.current_intent = 'purchase_inquiry'

        if self.use_ssml:
            response_text = conversational_response(response_text)

        self.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })

        if self.latency_tracker:
            self.latency_tracker.checkpoint('response_ready')
            self.latency_tracker.log_summary()

        return {
            'response': response_text,
            'should_escalate': False,
            'should_end_call': False,
            'intent': 'purchase_inquiry',
            'confidence': 0.9,
            'escalation_reason': None
        }

    def _extract_name(self, user_speech):
        """Strip intro phrases and return just the caller's name"""
        import re
        text = user_speech.strip()

        # Strip any leading filler words/phrases — applied repeatedly until stable
        # Each pattern matches common ways people introduce their name
        intro_patterns = [
            r"^(oh\s*[,.]?\s*)?(yes\s*[,.]?\s*)?(sure\s*[,.]?\s*)?my name is\s+",
            r"^(oh\s*[,.]?\s*)?(yes\s*[,.]?\s*)?this is\s+",
            r"^(oh\s*[,.]?\s*)?(yes\s*[,.]?\s*)?the name'?s?\s+",
            r"^(oh\s*[,.]?\s*)?(yes\s*[,.]?\s*)?name'?s?\s+",
            r"^(oh\s*[,.]?\s*)?(yes\s*[,.]?\s*)?i'?m\s+",
            r"^(oh\s*[,.]?\s*)?(yes\s*[,.]?\s*)?it'?s?\s+",
            r"^(oh\s*[,.]?\s*)?(yes\s*[,.]?\s*)?hi[,.]?\s+",
            r"^(oh\s*[,.]?\s*)?(yes\s*[,.]?\s*)?hey[,.]?\s+",
            r"^yes\s*[,.]?\s+",
            r"^sure\s*[,.]?\s+",
            r"^oh\s*[,.]?\s+",
        ]

        changed = True
        while changed:
            changed = False
            for pattern in intro_patterns:
                cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
                if cleaned and cleaned.lower() != text.lower():
                    text = cleaned
                    changed = True
                    break

        # Stop at the first sentence boundary — "David. And what time..." → "David"
        # Also stop at conjunctions that signal a new thought
        fragments = re.split(r'(?<=[a-zA-Z])[.!?]|\s+and\s+|\s*,\s+and\s+', text, maxsplit=1, flags=re.IGNORECASE)
        text = fragments[0].strip() if fragments else text

        # Strip any remaining trailing punctuation
        text = re.sub(r'[.,!?]+$', '', text).strip()

        # Keep first 1-2 words only (first + last name at most)
        words = text.split()
        if len(words) > 2:
            text = ' '.join(words[:2])

        return text.title() if text else user_speech.strip()

    def _handle_lead_name_response(self, user_speech):
        """Handle caller providing their name - supports both sales and callback requests"""
        self.lead_data['caller_name'] = self._extract_name(user_speech)
        store_open = self.lead_data['call_type'] == 'during_hours'

        inquiry = self.lead_data.get('inquiry', '')

        # Check if this is a callback request (human-required intent after hours) vs sales lead
        is_callback_request = self.current_intent == 'callback_request'

        caller_name = self.lead_data['caller_name']

        if is_callback_request:
            caller_phone = self.lead_data.get('caller_phone', '')
            display_phone = caller_phone[-4:] if caller_phone else 'your number'
            response_text = f"Nice to meet you, {caller_name}! We'll make sure someone reaches out as soon as possible. Is the number ending in {display_phone} still the best way to reach you?"
            self.conversation_state = 'confirming_callback'
        elif store_open:
            response_text = f"Nice to meet you, {caller_name}! You mentioned {inquiry} — any details on style, size, or color so our team can be ready for you?"
            self.conversation_state = 'capturing_lead_details'
        else:
            response_text = f"Nice to meet you, {caller_name}! What are you looking for — feel free to share any details like style, size, or color and we'll make sure our team is ready."
            self.conversation_state = 'capturing_lead_details'

        if self.use_ssml:
            response_text = conversational_response(response_text)

        self.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })

        if self.latency_tracker:
            self.latency_tracker.checkpoint('response_ready')
            self.latency_tracker.log_summary()

        return {
            'response': response_text,
            'should_escalate': False,
            'should_end_call': False,
            'intent': 'purchase_inquiry',
            'confidence': 0.9,
            'escalation_reason': None
        }

    def _handle_lead_details_response(self, user_speech):
        """Handle caller providing inquiry details"""
        if self.lead_data.get('inquiry'):
            self.lead_data['inquiry'] += f" - {user_speech.strip()}"
        else:
            self.lead_data['inquiry'] = user_speech.strip()

        store_open = self.lead_data['call_type'] == 'during_hours'
        caller_name = self.lead_data.get('caller_name', 'there')

        if store_open:
            self.lead_data['captured'] = True
            response_text = f"Got it, {caller_name}. Transferring you now."

            if self.use_ssml:
                response_text = conversational_response(response_text)

            self.conversation_history.append({
                'role': 'assistant',
                'content': response_text
            })

            if self.latency_tracker:
                self.latency_tracker.checkpoint('response_ready')
                self.latency_tracker.log_summary()

            return {
                'response': response_text,
                'should_escalate': True,
                'should_end_call': False,
                'intent': 'purchase_inquiry',
                'confidence': 0.95,
                'escalation_reason': 'lead_transfer',
                'lead_data': self.lead_data
            }
        else:
            caller_phone = self.lead_data.get('caller_phone', '')
            display_phone = caller_phone[-4:] if caller_phone else 'your number'
            inquiry = self.lead_data.get('inquiry', '')
            inquiry_note = f" — we'll let them know you're looking for {inquiry}" if inquiry else ""
            response_text = f"Got it{inquiry_note}. Our team will give you a call back first thing. Is the number ending in {display_phone} the best one to reach you on?"
            self.conversation_state = 'confirming_callback'

            if self.use_ssml:
                response_text = conversational_response(response_text)

            self.conversation_history.append({
                'role': 'assistant',
                'content': response_text
            })

            if self.latency_tracker:
                self.latency_tracker.checkpoint('response_ready')
                self.latency_tracker.log_summary()

            return {
                'response': response_text,
                'should_escalate': False,
                'should_end_call': False,
                'intent': 'purchase_inquiry',
                'confidence': 0.9,
                'escalation_reason': None
            }

    def _handle_callback_confirmation(self, user_speech):
        """Handle caller confirming callback number"""
        user_lower = user_speech.lower().strip()

        if any(word in user_lower for word in ['yes', 'yeah', 'yep', 'correct', 'that\'s right', 'sure']):
            pass
        else:
            self.lead_data['caller_phone'] = user_speech.strip()

        self.lead_data['captured'] = True
        store_name = self.company_config.get('name', 'our store')
        caller_name = self.lead_data.get('caller_name', '')
        name_part = f", {caller_name}" if caller_name else ""
        response_text = f"You're all set{name_part}! Someone from {store_name} will be in touch soon. Thanks so much for calling — have a great evening!"

        if self.use_ssml:
            response_text = conversational_response(response_text)

        self.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })

        if self.latency_tracker:
            self.latency_tracker.checkpoint('response_ready')
            self.latency_tracker.log_summary()

        return {
            'response': response_text,
            'should_escalate': False,
            'should_end_call': True,
            'intent': 'purchase_inquiry',
            'confidence': 0.95,
            'escalation_reason': None,
            'lead_data': self.lead_data
        }

    def get_lead_data(self):
        """Get captured lead data"""
        return self.lead_data if self.lead_data.get('captured') else None
