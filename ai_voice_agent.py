import os
import json
from openai import OpenAI
from orders_db import lookup_order, format_order_status, extract_order_number_from_speech

def get_openai_client():
    """Initialize OpenAI client with Replit AI Integrations"""
    return OpenAI(
        base_url=os.environ.get('AI_INTEGRATIONS_OPENAI_BASE_URL'),
        api_key=os.environ.get('AI_INTEGRATIONS_OPENAI_API_KEY')
    )

SYSTEM_PROMPT = """You are a friendly call center AI. Be brief (1-2 sentences max). Help with orders, hours, and general questions. Escalate refunds, returns, billing issues, or complaints to humans."""

CACHED_RESPONSES = {
    'store_hours': "Our store is open Monday through Friday, 9 AM to 5 PM. Is there anything else I can help you with?",
    'greeting': "Hello! How can I help you today?",
    'ask_order_number': "I'd be happy to help you track your order! What's your order number?",
    'order_not_found': "I couldn't find that order in our system. Let me connect you with a team member who can help.",
    'goodbye': "Thank you for calling! Have a great day. Goodbye!",
    'escalate': "Of course, let me connect you with a team member who can help you right away.",
    'anything_else': "Is there anything else I can help you with?",
    'didnt_catch': "I didn't catch that. Could you please repeat your order number?"
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


class AIVoiceAgent:
    def __init__(self, company_config):
        """Initialize AI agent with company-specific configuration"""
        self.company_config = company_config
        self.conversation_history = []
        self.conversation_state = 'initial'  # initial, waiting_for_order_number, order_resolved, offering_more_help, goodbye
        self.current_intent = None
        self.order_data = None
        
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
        # Add user message to conversation history
        self.conversation_history.append({
            'role': 'user',
            'content': user_speech
        })
        
        # Handle different conversation states
        if self.conversation_state == 'offering_more_help':
            # User responded to "Is there anything else I can help you with?"
            return self._handle_followup_response(user_speech)
        
        if self.conversation_state == 'waiting_for_order_number':
            # User should be providing their order number
            return self._handle_order_number_response(user_speech)
        
        # Check for immediate escalation triggers
        escalation_check = self._check_escalation(user_speech)
        if escalation_check['should_escalate']:
            return escalation_check
        
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
            order_data = lookup_order(order_num)
            if order_data:
                status_response = format_order_status(order_data)
                self.conversation_state = 'offering_more_help'
                self.order_data = order_data
                
                response_text = f"{status_response} Is there anything else I can help you with?"
                
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response_text
                })
                
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
        
        response_text = CACHED_RESPONSES['ask_order_number']
        
        self.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })
        
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
        order_num = extract_order_number_from_speech(user_speech)
        
        if not order_num:
            # Couldn't extract order number, ask again
            response_text = CACHED_RESPONSES['didnt_catch']
            
            self.conversation_history.append({
                'role': 'assistant',
                'content': response_text
            })
            
            return {
                'response': response_text,
                'should_escalate': False,
                'should_end_call': False,
                'intent': 'order_status',
                'confidence': 0.7,
                'escalation_reason': None
            }
        
        # Look up order
        order_data = lookup_order(order_num)
        
        if not order_data:
            return self._handle_order_not_found(order_num)
        
        # Success! Provide order status
        status_response = format_order_status(order_data)
        self.conversation_state = 'offering_more_help'
        self.order_data = order_data
        
        response_text = f"{status_response} Is there anything else I can help you with?"
        
        self.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })
        
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
        response_text = f"I couldn't find order {order_num}. " + CACHED_RESPONSES['order_not_found'].split('. ')[1]
        
        self.conversation_history.append({
            'role': 'assistant',
            'content': response_text
        })
        
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
                response_text = CACHED_RESPONSES['goodbye']
                
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
                response_text = CACHED_RESPONSES['goodbye']
                
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
            response_text = CACHED_RESPONSES['goodbye']
            
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
            response_text = f"Our business hours are {hours}. {CACHED_RESPONSES['anything_else']}"
            self.conversation_state = 'offering_more_help'
            self.conversation_history.append({'role': 'assistant', 'content': response_text})
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
            
            ai_response = response.choices[0].message.content
            
            # Check if we should offer more help after this response
            should_offer_help = self._should_offer_more_help(intent_analysis['intent'])
            
            if should_offer_help:
                self.conversation_state = 'offering_more_help'
                ai_response += " Is there anything else I can help you with?"
            
            # Add AI response to history
            self.conversation_history.append({
                'role': 'assistant',
                'content': ai_response
            })
            
            # Re-analyze for escalation after GPT response
            final_analysis = self._check_for_escalation_in_response(ai_response, intent_analysis)
            
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
                    'response': CACHED_RESPONSES['escalate'],
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
