import os
import json
from openai import OpenAI

def get_openai_client():
    """Initialize OpenAI client with Replit AI Integrations"""
    return OpenAI(
        base_url=os.environ.get('AI_INTEGRATIONS_OPENAI_BASE_URL'),
        api_key=os.environ.get('AI_INTEGRATIONS_OPENAI_API_KEY')
    )

SYSTEM_PROMPT = """You are a helpful AI voice assistant for a call center. Your role is to:
1. Understand customer queries and determine their intent
2. Provide helpful responses to common questions
3. Be conversational and friendly
4. Recognize when you should escalate to a human agent

You can help with:
- Order status inquiries (ask for order number)
- Store hours and location information
- General product questions
- Appointment scheduling

You should escalate to a human when:
- Customer explicitly asks to speak with someone
- Refund or return requests
- Billing disputes or account changes
- Complaints or sensitive issues
- You're uncertain how to help (low confidence)

Always be brief and natural in your responses. This is a phone conversation, so keep responses under 2-3 sentences."""

ESCALATION_KEYWORDS = [
    'speak to someone', 'human', 'agent', 'representative', 'manager',
    'refund', 'return', 'cancel', 'dispute', 'complaint', 'angry',
    'supervisor', 'person', 'real person'
]

SENSITIVE_INTENTS = ['refund', 'return', 'cancel_order', 'billing_issue', 'complaint']


class AIVoiceAgent:
    def __init__(self, company_config):
        """Initialize AI agent with company-specific configuration"""
        self.company_config = company_config
        self.conversation_history = []
        
    def process_speech(self, user_speech, context=None):
        """
        Process user speech and generate AI response
        Returns: {
            'response': str,
            'should_escalate': bool,
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
        
        # Check for immediate escalation triggers
        escalation_check = self._check_escalation(user_speech)
        if escalation_check['should_escalate']:
            return escalation_check
        
        # Build system prompt with company info
        system_msg = self._build_system_prompt()
        
        # Call OpenAI for response
        try:
            client = get_openai_client()
            response = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {'role': 'system', 'content': system_msg},
                    *self.conversation_history
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            ai_response = response.choices[0].message.content
            
            # Add AI response to history
            self.conversation_history.append({
                'role': 'assistant',
                'content': ai_response
            })
            
            # Analyze intent and confidence
            intent_analysis = self._analyze_intent(user_speech, ai_response)
            
            return {
                'response': ai_response,
                'should_escalate': intent_analysis['should_escalate'],
                'intent': intent_analysis['intent'],
                'confidence': intent_analysis['confidence'],
                'escalation_reason': intent_analysis.get('escalation_reason')
            }
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            # Fallback to safe escalation
            return {
                'response': "I'm having trouble processing your request. Let me connect you with someone who can help.",
                'should_escalate': True,
                'intent': 'error',
                'confidence': 0.0,
                'escalation_reason': 'api_error'
            }
    
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
                    'response': "Of course, let me connect you with a team member who can help you right away.",
                    'should_escalate': True,
                    'intent': 'escalate_requested',
                    'confidence': 1.0,
                    'escalation_reason': f'keyword: {keyword}'
                }
        
        return {'should_escalate': False}
    
    def _analyze_intent(self, user_speech, ai_response):
        """Analyze intent and determine if escalation is needed"""
        user_lower = user_speech.lower()
        
        # Detect common intents
        if any(word in user_lower for word in ['order', 'tracking', 'shipment', 'delivery']):
            intent = 'order_status'
            confidence = 0.9
        elif any(word in user_lower for word in ['hours', 'open', 'close', 'location']):
            intent = 'store_hours'
            confidence = 0.9
        elif any(word in user_lower for word in ['appointment', 'schedule', 'book']):
            intent = 'appointment'
            confidence = 0.8
        elif any(word in user_lower for word in ['refund', 'return', 'send back']):
            intent = 'refund'
            confidence = 0.9
            # Sensitive intent - escalate
            return {
                'intent': intent,
                'confidence': confidence,
                'should_escalate': True,
                'escalation_reason': 'sensitive_intent: refund/return'
            }
        elif any(word in user_lower for word in ['billing', 'charge', 'payment', 'invoice']):
            intent = 'billing'
            confidence = 0.8
            # Sensitive intent - escalate
            return {
                'intent': intent,
                'confidence': confidence,
                'should_escalate': True,
                'escalation_reason': 'sensitive_intent: billing'
            }
        else:
            intent = 'general_inquiry'
            confidence = 0.6
        
        # Check if AI expressed uncertainty in response
        uncertainty_phrases = [
            "i'm not sure", "i don't know", "i can't help", 
            "let me connect you", "speak with someone"
        ]
        if any(phrase in ai_response.lower() for phrase in uncertainty_phrases):
            return {
                'intent': intent,
                'confidence': 0.3,
                'should_escalate': True,
                'escalation_reason': 'ai_uncertainty'
            }
        
        # Low confidence threshold - escalate if below 0.5
        if confidence < 0.5:
            return {
                'intent': intent,
                'confidence': confidence,
                'should_escalate': True,
                'escalation_reason': 'low_confidence'
            }
        
        return {
            'intent': intent,
            'confidence': confidence,
            'should_escalate': False
        }
    
    def get_conversation_summary(self):
        """Get summary of conversation for logging"""
        return {
            'turns': len(self.conversation_history) // 2,
            'messages': self.conversation_history
        }
