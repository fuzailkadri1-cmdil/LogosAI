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

SYSTEM_PROMPT = """You're a warm, helpful customer service assistant. Speak naturally like a real person - use contractions (I'm, you're, we'll), vary your sentence length, and sound genuinely friendly. Keep responses brief (1-2 sentences). You can help with orders, store hours, and general questions. For refunds, returns, billing, or complaints, warmly offer to connect the caller with a team member."""

def get_response(key):
    """Get cached response with SSML if enabled."""
    return get_cached_ssml(key)

CACHED_RESPONSES = {
    'store_hours': "We're open Monday through Friday, 9 to 5! Anything else I can help with?",
    'greeting': "Hi there! What can I help you with today?",
    'ask_order_number': "Sure thing! What's your order number?",
    'order_not_found': "Hmm, I'm not finding that one. Let me get you to someone who can dig a bit deeper.",
    'goodbye': "Thanks so much for calling! Take care!",
    'escalate': "Absolutely, let me get you to someone who can help with that right away.",
    'anything_else': "Anything else I can help with?",
    'didnt_catch': "Sorry, I didn't quite catch that. What was your order number again?"
}

ESCALATION_KEYWORDS = [
    'speak to someone', 'human', 'agent', 'representative', 'manager',
    'refund', 'return', 'cancel', 'dispute', 'complaint', 'angry',
    'supervisor', 'person', 'real person'
]

GOODBYE_PHRASES = [
    # Exact phrases (for whole phrase matching)
    "that's all", "that's it", "i'm good", "i'm done",
    "nothing else", "no thanks", "no thank you", "that'll be all",
    "all set", "i'm all set", "that helps", "that's everything",
    "that would be all", "i'm finished", "that does it"
]

GOODBYE_WORDS = [
    # Single words requiring word boundary matching
    'nope', 'goodbye', 'bye'
]

SENSITIVE_INTENTS = ['refund', 'return', 'cancel_order', 'billing_issue', 'complaint']

PURCHASE_INTENT_PHRASES = [
    'do you have', 'looking for', 'i want to buy', 'i want to order',
    'is this in stock', 'in stock', 'available', 'do you carry',
    'can i order', 'can i buy', 'i need', "i'm looking for", 'i am looking for',
    'do you sell', 'price of', 'how much is', 'how much does',
    'purchase', 'interested in', 'want to get', 'can you get'
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
    
    def _detect_purchase_intent(self, user_speech):
        """Detect if user has purchase/product inquiry intent"""
        user_lower = user_speech.lower()
        for phrase in PURCHASE_INTENT_PHRASES:
            if phrase in user_lower:
                return True
        return False
    
    def _extract_inquiry_details(self, user_speech):
        """Extract what the caller is looking for from their speech"""
        return user_speech.strip()
    
    def _is_store_open(self):
        """Check if store is currently open based on business hours"""
        business_hours = self.company_config.get('business_hours', {})
        result = is_store_open(business_hours)
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
        
        # Check for immediate escalation triggers
        escalation_check = self._check_escalation(user_speech)
        if escalation_check['should_escalate']:
            return escalation_check
        
        # Check for purchase intent - trigger lead capture flow
        if self._detect_purchase_intent(user_speech):
            return self._handle_purchase_intent(user_speech)
        
        # Determine intent and handle accordingly
        intent_analysis = self._analyze_intent(user_speech)
        
        if intent_analysis['intent'] == 'order_status':
            return self._handle_order_status_inquiry(user_speech)
        
        # For other intents, use GPT to generate response
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
        """Handle user providing their order number"""
        import re
        
        # First try standard extraction
        order_num = extract_order_number_from_speech(user_speech)
        
        # If that fails, accept bare digits since we're already waiting for an order number
        if not order_num:
            # Normalize spoken numbers first
            normalized = normalize_spoken_numbers(user_speech)
            # Accept standalone digits (1-9) or multi-digit numbers
            bare_match = re.match(r'^\s*(\d+)\s*$', normalized)
            if bare_match:
                order_num = bare_match.group(1)
        
        if not order_num:
            # Couldn't extract order number, ask again with SSML
            response_text = get_response('didnt_catch')
            
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
                'confidence': 0.7,
                'escalation_reason': None
            }
        
        # Look up order
        order_data = self._smart_lookup_order(order_num)
        
        if not order_data:
            return self._handle_order_not_found(order_num)
        
        # Success! Provide order status with SSML
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
    
    def _handle_order_not_found(self, order_num):
        """Handle when order number is not found in database"""
        # Use SSML-enhanced response
        response_text = get_response('order_not_found')
        
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
            'should_escalate': True,
            'should_end_call': False,
            'intent': 'order_status',
            'confidence': 0.9,
            'escalation_reason': 'order_not_found'
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
        """Generate AI response using GPT for general queries"""
        if intent_analysis['intent'] == 'store_hours':
            hours = self.company_config.get('business_hours', 'Monday through Friday, 9 AM to 5 PM')
            anything_else = get_response('anything_else')
            
            # Build response with SSML if enabled
            if self.use_ssml:
                response_text = conversational_response(f"Our business hours are {hours}.") + " " + anything_else
            else:
                response_text = f"Our business hours are {hours}. {CACHED_RESPONSES['anything_else']}"
            
            self.conversation_state = 'offering_more_help'
            self.conversation_history.append({'role': 'assistant', 'content': response_text})
            
            # Log LLM complete (cached response, so instant)
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
            # Fallback to safe escalation
            return {
                'response': "I'm having trouble processing your request. Let me connect you with someone who can help.",
                'should_escalate': True,
                'should_end_call': False,
                'intent': 'error',
                'confidence': 0.0,
                'escalation_reason': 'api_error'
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
        """Check if user speech contains escalation triggers"""
        user_lower = user_speech.lower()
        
        # Check for explicit escalation keywords
        for keyword in ESCALATION_KEYWORDS:
            if keyword in user_lower:
                return {
                    'response': get_response('escalate'),
                    'should_escalate': True,
                    'should_end_call': False,
                    'intent': 'escalate_requested',
                    'confidence': 1.0,
                    'escalation_reason': f'keyword: {keyword}'
                }
        
        return {'should_escalate': False}
    
    def _analyze_intent(self, user_speech):
        """Analyze intent from user speech"""
        user_lower = user_speech.lower()
        
        # Detect common intents
        if any(word in user_lower for word in ['order', 'tracking', 'shipment', 'delivery', 'package']):
            return {'intent': 'order_status', 'confidence': 0.9}
        elif any(word in user_lower for word in ['hours', 'open', 'close', 'location', 'when']):
            return {'intent': 'store_hours', 'confidence': 0.9}
        elif any(word in user_lower for word in ['appointment', 'schedule', 'book']):
            return {'intent': 'appointment', 'confidence': 0.8}
        elif any(word in user_lower for word in ['refund', 'return', 'send back']):
            return {'intent': 'refund', 'confidence': 0.9}
        elif any(word in user_lower for word in ['billing', 'charge', 'payment', 'invoice']):
            return {'intent': 'billing', 'confidence': 0.8}
        else:
            return {'intent': 'general_inquiry', 'confidence': 0.6}
    
    def _check_for_escalation_in_response(self, ai_response, intent_analysis):
        """Check if AI response or intent requires escalation"""
        # Sensitive intents always escalate
        if intent_analysis['intent'] in SENSITIVE_INTENTS:
            return {
                'should_escalate': True,
                'escalation_reason': f"sensitive_intent: {intent_analysis['intent']}"
            }
        
        # Check if AI expressed uncertainty in response
        uncertainty_phrases = [
            "i'm not sure", "i don't know", "i can't help", 
            "let me connect you", "speak with someone"
        ]
        if any(phrase in ai_response.lower() for phrase in uncertainty_phrases):
            return {
                'should_escalate': True,
                'escalation_reason': 'ai_uncertainty'
            }
        
        # Low confidence threshold - escalate if below 0.5
        if intent_analysis['confidence'] < 0.5:
            return {
                'should_escalate': True,
                'escalation_reason': 'low_confidence'
            }
        
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
            response_text = f"Thanks for calling {store_name}! We're currently closed, but I'd love to make sure someone helps you first thing. Can I get your name?"
        
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
    
    def _handle_lead_name_response(self, user_speech):
        """Handle caller providing their name"""
        self.lead_data['caller_name'] = user_speech.strip()
        store_open = self.lead_data['call_type'] == 'during_hours'
        
        inquiry = self.lead_data.get('inquiry', '')
        
        if store_open:
            response_text = f"And you're looking for {inquiry} - any specific size, color, or other details?"
            self.conversation_state = 'capturing_lead_details'
        else:
            response_text = "And what are you looking for today?"
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
            response_text = f"Perfect, {caller_name}. Someone from our team will call you back when we open. Is {display_phone} the best number to reach you?"
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
        
        response_text = f"Great, expect a call from us soon! Thanks for calling {store_name}. Talk to you soon!"
        
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
