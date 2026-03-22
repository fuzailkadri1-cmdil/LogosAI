"""
SSML Helper for Natural-Sounding TTS
Adds pauses, emphasis, and prosody to make AI voice less robotic.
"""
import re
import os

# Global config flag for easy rollback
SSML_ENABLED = False

def build_ssml(text, rate="medium", pitch="medium"):
    """
    Convert plain text to SSML with natural pauses and prosody.
    
    Note: Twilio's <Say> verb acts as the SSML container - do NOT wrap with <speak> tags.
    The SSML tags are embedded directly and Twilio interprets them with Polly voices.
    
    Args:
        text: Plain text to convert
        rate: Speech rate - "slow", "medium", "fast" or percentage like "90%"
        pitch: Voice pitch - "low", "medium", "high" or semitones like "+2st"
    
    Returns:
        SSML-formatted string (without <speak> wrapper) or plain text if SSML disabled
    """
    if not SSML_ENABLED:
        return text
    
    # Apply natural pauses and emphasis
    ssml_text = add_natural_pauses(text)
    ssml_text = add_emphasis(ssml_text)
    
    # Wrap in prosody only (Twilio's Say provides the outer container)
    return f'<prosody rate="{rate}" pitch="{pitch}">{ssml_text}</prosody>'

def add_natural_pauses(text):
    """
    Add natural pauses at punctuation marks.
    
    - Period/exclamation/question: 400ms pause
    - Comma: 200ms pause  
    - Colon/semicolon: 300ms pause
    - After greeting words: 150ms pause
    """
    # Add pause after sentences (. ! ?)
    text = re.sub(r'([.!?])\s+', r'\1<break time="400ms"/> ', text)
    
    # Add pause after commas
    text = re.sub(r',\s+', r',<break time="200ms"/> ', text)
    
    # Add pause after colons and semicolons
    text = re.sub(r'[:;]\s+', r'<break time="300ms"/> ', text)
    
    # Add pause after greeting words
    greetings = ['Hi', 'Hello', 'Hey', 'Thanks', 'Sure', 'Absolutely', 'Great', 'Perfect', 'Okay', 'Alright']
    for greeting in greetings:
        text = re.sub(rf'\b{greeting}\b([!,.]?)\s+', rf'{greeting}\1<break time="150ms"/> ', text)
    
    return text

def add_emphasis(text):
    """
    Emphasis tags are NOT supported by Amazon Polly Neural voices.
    Returns text unchanged to avoid TTS errors.
    """
    return text

def conversational_response(text):
    """
    Make a response more conversational with SSML enhancements.
    Specifically tuned for customer service AI.
    
    Note: Returns SSML without <speak> wrapper - Twilio's <Say> is the container.
    """
    if not SSML_ENABLED:
        return text
    
    ssml_text = add_natural_pauses(text)
    ssml_text = add_emphasis(ssml_text)
    
    # Use slightly slower rate for warmth (Twilio's Say is the outer container)
    return f'<prosody rate="95%">{ssml_text}</prosody>'

def quick_response(text):
    """
    For shorter responses that should feel snappy and friendly.
    """
    if not SSML_ENABLED:
        return text
    
    ssml_text = add_natural_pauses(text)
    
    # Normal rate (no wrapper needed, Twilio's Say is the container)
    return ssml_text

def empathetic_response(text):
    """
    For responses that need to convey empathy (apologies, escalations).
    """
    if not SSML_ENABLED:
        return text
    
    ssml_text = add_natural_pauses(text)
    
    # Slower rate for sincerity
    return f'<prosody rate="90%">{ssml_text}</prosody>'

# Pre-built SSML responses for cached messages (fastest path)
# Note: No <speak> wrapper - Twilio's <Say> is the container
SSML_CACHED_RESPONSES = {
    'store_hours': '<prosody rate="95%">We\'re open Monday through Friday,<break time="150ms"/> 9 to 5!<break time="300ms"/> Anything else I can help with?</prosody>',
    
    'greeting': 'Hi there!<break time="200ms"/> What can I help you with today?',
    
    'ask_order_number': 'Sure thing!<break time="150ms"/> What\'s your order number?',
    
    'order_not_found': '<prosody rate="90%">Hmm,<break time="200ms"/> I\'m not finding that one.<break time="300ms"/> Let me get you to someone who can help with that.</prosody>',
    
    'goodbye': 'Thanks so much for calling!<break time="200ms"/> Take care!',
    
    'escalate': '<prosody rate="90%">Absolutely,<break time="150ms"/> let me get you to someone who can help with that right away.</prosody>',
    
    'anything_else': 'Anything else I can help with?',
    
    'didnt_catch': '<prosody rate="90%">Sorry,<break time="150ms"/> I didn\'t quite catch that.<break time="200ms"/> Could you repeat that for me?</prosody>',
    
    'transfer_hold': '<prosody rate="90%">Sure thing,<break time="200ms"/> just one moment while I connect you.</prosody>',
    
    'no_input': 'We didn\'t receive any input.<break time="200ms"/> Please try again.'
}

def strip_ssml(text):
    """
    Remove all SSML/XML tags from text so nothing is ever spoken literally.
    Used as a safety net before passing any text to Twilio's Say verb.
    """
    return re.sub(r'<[^>]+>', '', text).strip()


def get_cached_ssml(key):
    """
    Get pre-built SSML response for cached messages.
    Falls back to plain text if SSML disabled.
    """
    if not SSML_ENABLED:
        # Return plain text fallbacks
        plain_responses = {
            'store_hours': "We're open Monday through Friday, 9 to 5! Anything else I can help with?",
            'greeting': "Hi there! What can I help you with today?",
            'ask_order_number': "Sure thing! What's your order number?",
            'order_not_found': "Hmm, I'm not finding that one. Let me get you to someone who can dig a bit deeper.",
            'goodbye': "Thanks so much for calling! Take care!",
            'escalate': "Absolutely, let me get you to someone who can help with that right away.",
            'anything_else': "Anything else I can help with?",
            'didnt_catch': "Sorry, I didn't quite catch that. What was your order number again?",
            'transfer_hold': "Please hold while we transfer your call.",
            'no_input': "We didn't receive any input. Please try again."
        }
        return plain_responses.get(key, "")
    
    return SSML_CACHED_RESPONSES.get(key, "")
