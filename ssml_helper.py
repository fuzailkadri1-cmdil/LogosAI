"""
ssml_helper.py — TTS Voice Formatting Utilities

Provides helpers for making the AI voice sound more natural via SSML
(Speech Synthesis Markup Language) and for cleaning text before it
is passed to Twilio's <Say> verb.

IMPORTANT — SSML IS CURRENTLY DISABLED (SSML_ENABLED = False):
  Twilio's Python SDK HTML-escapes content inside <Say>, so SSML tags
  like <break time="200ms"/> get spoken aloud as literal text rather
  than being processed as pauses. Until a proper SSML injection path is
  implemented, all text is passed as plain strings.

  The strip_ssml() function acts as a safety net — it removes any stray
  XML tags before text reaches Twilio, ensuring nothing is ever read aloud
  as markup.

Voice:
  All TTS uses Amazon Polly's Neural voice (Polly.Joanna-Neural), which
  handles natural intonation and pacing without requiring explicit SSML.
"""

import re
import os

# Set to True to re-enable SSML once a compatible injection method is found.
# WARNING: Neural voices do NOT support <emphasis> tags — only <break> and <prosody>.
SSML_ENABLED = False


def build_ssml(text, rate="medium", pitch="medium"):
    """
    Wrap plain text in SSML prosody tags with natural pauses.

    Note: Twilio's <Say> verb acts as the outer SSML container — do NOT
    add a <speak> wrapper here. The tags are embedded directly in the text
    and Twilio forwards them to Amazon Polly.

    Args:
        text (str):  Plain text to convert.
        rate (str):  Speech rate — "slow", "medium", "fast", or a percentage
                     like "90%".
        pitch (str): Voice pitch — "low", "medium", "high", or semitones
                     like "+2st".

    Returns:
        str: SSML-formatted string (without <speak> wrapper) if SSML is
             enabled, or the original plain text if disabled.
    """
    if not SSML_ENABLED:
        return text

    ssml_text = add_natural_pauses(text)
    ssml_text = add_emphasis(ssml_text)

    return f'<prosody rate="{rate}" pitch="{pitch}">{ssml_text}</prosody>'


def add_natural_pauses(text):
    """
    Insert SSML <break> tags at natural pause points in the text.

    Pause durations:
      - After sentence-ending punctuation (. ! ?): 400ms
      - After commas: 200ms
      - After colons and semicolons: 300ms
      - After common greeting words (Hi, Thanks, Perfect, etc.): 150ms

    Args:
        text (str): Plain or partially-formatted text.

    Returns:
        str: Text with <break> tags inserted.
    """
    # Sentence boundaries
    text = re.sub(r'([.!?])\s+', r'\1<break time="400ms"/> ', text)

    # Commas
    text = re.sub(r',\s+', r',<break time="200ms"/> ', text)

    # Colons and semicolons
    text = re.sub(r'[:;]\s+', r'<break time="300ms"/> ', text)

    # Greeting words — brief pause before the next word
    greetings = ['Hi', 'Hello', 'Hey', 'Thanks', 'Sure', 'Absolutely', 'Great', 'Perfect', 'Okay', 'Alright']
    for greeting in greetings:
        text = re.sub(rf'\b{greeting}\b([!,.]?)\s+', rf'{greeting}\1<break time="150ms"/> ', text)

    return text


def add_emphasis(text):
    """
    Placeholder for SSML emphasis tags.

    NOTE: Amazon Polly Neural voices do NOT support <emphasis> tags.
    This function intentionally returns the text unchanged to prevent
    TTS errors on neural voices.

    Args:
        text (str): Input text.

    Returns:
        str: Unchanged input text.
    """
    return text


def conversational_response(text):
    """
    Apply conversational SSML enhancements (pauses + slight rate reduction).

    Tuned for warm, customer-service tone. Uses 95% speech rate to sound
    slightly more relaxed and human.

    Args:
        text (str): Plain text to enhance.

    Returns:
        str: SSML-wrapped text if enabled, or original text if disabled.
    """
    if not SSML_ENABLED:
        return text

    ssml_text = add_natural_pauses(text)
    ssml_text = add_emphasis(ssml_text)

    return f'<prosody rate="95%">{ssml_text}</prosody>'


def quick_response(text):
    """
    Apply minimal SSML for short, snappy responses (no rate change).

    Args:
        text (str): Plain text to enhance.

    Returns:
        str: Text with pause tags if SSML is enabled, or plain text.
    """
    if not SSML_ENABLED:
        return text

    return add_natural_pauses(text)


def empathetic_response(text):
    """
    Apply SSML for responses that need warmth or sincerity (apologies,
    escalations). Uses a 90% speech rate to sound more deliberate.

    Args:
        text (str): Plain text to enhance.

    Returns:
        str: SSML-wrapped text if enabled, or original text if disabled.
    """
    if not SSML_ENABLED:
        return text

    ssml_text = add_natural_pauses(text)
    return f'<prosody rate="90%">{ssml_text}</prosody>'


def strip_ssml(text):
    """
    Remove all XML/SSML tags from a string.

    Used as a safety net immediately before passing any text to Twilio's
    <Say> verb. Ensures stale SSML tags from cached responses or old code
    paths are never spoken as literal text.

    Args:
        text (str): Text that may contain XML tags.

    Returns:
        str: Clean plain text with all tags removed and surrounding
             whitespace stripped.

    Example:
        strip_ssml('<prosody rate="95%">Hello<break time="200ms"/>!')
        → "Hello!"
    """
    return re.sub(r'<[^>]+>', '', text).strip()


# Pre-built responses for common messages.
# These contain SSML markup — only used when SSML_ENABLED = True.
# When disabled, get_cached_ssml() returns plain-text equivalents below.
SSML_CACHED_RESPONSES = {
    'store_hours':    '<prosody rate="95%">We\'re open Monday through Friday,<break time="150ms"/> 9 to 5!<break time="300ms"/> Anything else I can help with?</prosody>',
    'greeting':       'Hi there!<break time="200ms"/> What can I help you with today?',
    'ask_order_number': 'Sure thing!<break time="150ms"/> What\'s your order number?',
    'order_not_found': '<prosody rate="90%">Hmm,<break time="200ms"/> I\'m not finding that one.<break time="300ms"/> Let me get you to someone who can help with that.</prosody>',
    'goodbye':        'Thanks so much for calling!<break time="200ms"/> Take care!',
    'escalate':       '<prosody rate="90%">Absolutely,<break time="150ms"/> let me get you to someone who can help with that right away.</prosody>',
    'anything_else':  'Anything else I can help with?',
    'didnt_catch':    '<prosody rate="90%">Sorry,<break time="150ms"/> I didn\'t quite catch that.<break time="200ms"/> Could you repeat that for me?</prosody>',
    'transfer_hold':  '<prosody rate="90%">Sure thing,<break time="200ms"/> just one moment while I connect you.</prosody>',
    'no_input':       'We didn\'t receive any input.<break time="200ms"/> Please try again.'
}


def get_cached_ssml(key):
    """
    Return a pre-built response for a common message type.

    When SSML is enabled, returns the SSML-tagged version from
    SSML_CACHED_RESPONSES. When disabled, returns clean plain text.

    Args:
        key (str): Response identifier. Valid keys: store_hours, greeting,
                   ask_order_number, order_not_found, goodbye, escalate,
                   anything_else, didnt_catch, transfer_hold, no_input.

    Returns:
        str: The response text (plain or SSML depending on SSML_ENABLED).
             Empty string if the key is not found.
    """
    if not SSML_ENABLED:
        plain_responses = {
            'store_hours':      "We're open Monday through Friday, 9 to 5! Anything else I can help with?",
            'greeting':         "Hi there! What can I help you with today?",
            'ask_order_number': "Sure thing! What's your order number?",
            'order_not_found':  "Hmm, I'm not finding that one. Let me get you to someone who can dig a bit deeper.",
            'goodbye':          "Thanks so much for calling! Take care!",
            'escalate':         "Absolutely, let me get you to someone who can help with that right away.",
            'anything_else':    "Anything else I can help with?",
            'didnt_catch':      "Sorry, I didn't quite catch that. What was your order number again?",
            'transfer_hold':    "Please hold while we transfer your call.",
            'no_input':         "We didn't receive any input. Please try again."
        }
        return plain_responses.get(key, "")

    return SSML_CACHED_RESPONSES.get(key, "")
