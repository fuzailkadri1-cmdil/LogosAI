"""
providers.py — Telephony Provider Abstraction Layer

Defines a common interface (TelephonyProvider) for building TwiML responses
so the rest of the codebase doesn't depend directly on Twilio. Alternative
providers (Cisco, SIP) can be swapped in without touching call logic.

Current default: TwilioProvider using Amazon Polly Neural TTS voice
(Polly.Joanna-Neural) for natural-sounding speech.

All text is passed through strip_ssml() before reaching Twilio's <Say>
verb to ensure no stray XML tags are ever spoken aloud.
"""

from abc import ABC, abstractmethod
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Record, Dial
import os
from typing import Any
from ssml_helper import conversational_response, get_cached_ssml, strip_ssml, SSML_ENABLED


class TelephonyProvider(ABC):
    """
    Abstract base class defining the interface every telephony provider must implement.

    Any provider (Twilio, Cisco, SIP) must implement all five methods below.
    This allows the call-handling code in app.py to remain provider-agnostic.
    """

    @abstractmethod
    def create_call_response(self, message, next_action=None) -> Any:
        """
        Build a response that speaks a message and either redirects or hangs up.

        Args:
            message (str):          Text to speak to the caller.
            next_action (str|None): URL to redirect to after speaking, or None to hang up.

        Returns:
            Any: Provider-specific response (TwiML string, JSON dict, etc.).
        """
        pass

    @abstractmethod
    def create_gather_response(self, message, action_url, input_type='dtmf',
                               timeout=5, speech_timeout=None, speech_model=None) -> Any:
        """
        Build a response that speaks a message and collects caller input.

        Args:
            message (str):              Text to speak before waiting for input.
            action_url (str):           URL to POST the caller's input to.
            input_type (str):           "dtmf", "speech", or "both".
            timeout (int):              Seconds to wait for input before giving up.
            speech_timeout (str|None):  How long to wait after speech stops ("auto" or seconds).
            speech_model (str|None):    Twilio STT model name (e.g. "experimental_conversations").

        Returns:
            Any: Provider-specific response.
        """
        pass

    @abstractmethod
    def create_record_response(self, message, action_url, max_length=60) -> Any:
        """
        Build a response that speaks a message and then records the caller's voice.

        Args:
            message (str):      Prompt to play before recording starts.
            action_url (str):   URL to POST the recording details to when done.
            max_length (int):   Maximum recording length in seconds.

        Returns:
            Any: Provider-specific response.
        """
        pass

    @abstractmethod
    def transfer_call(self, phone_number) -> Any:
        """
        Build a response that transfers the call to a phone number.

        Args:
            phone_number (str): The E.164 phone number to transfer to.

        Returns:
            Any: Provider-specific response.
        """
        pass

    @abstractmethod
    def send_sms(self, to_number, from_number, message) -> Any:
        """
        Send an SMS message.

        Args:
            to_number (str):   Recipient's E.164 phone number.
            from_number (str): Sender's E.164 phone number (must be a Twilio number).
            message (str):     Message body text.

        Returns:
            Any: Message SID or equivalent identifier, or None on failure.
        """
        pass


class TwilioProvider(TelephonyProvider):
    """
    Twilio implementation of TelephonyProvider.

    Builds TwiML (XML) responses that Twilio executes on the phone call.
    Uses Amazon Polly Neural TTS for natural-sounding voice output.

    All text is stripped of XML tags via strip_ssml() before being passed
    to Twilio's <Say> verb to prevent tags from being read aloud.
    """

    def __init__(self, account_sid=None, auth_token=None):
        """
        Initialise the Twilio REST client.

        Credentials are read from environment variables if not passed directly.
        The REST client is only needed for outbound actions (SMS, call initiation);
        inbound TwiML responses work without it.

        Args:
            account_sid (str|None): Twilio Account SID. Falls back to TWILIO_ACCOUNT_SID env var.
            auth_token (str|None):  Twilio Auth Token. Falls back to TWILIO_AUTH_TOKEN env var.
        """
        self.account_sid = account_sid or os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = auth_token or os.environ.get('TWILIO_AUTH_TOKEN')
        self.client = None

        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
            except Exception as e:
                print(f"Error initializing Twilio client: {e}")

    def create_call_response(self, message, next_action=None, use_ssml=True):
        """
        Speak a message and either redirect or hang up.

        Args:
            message (str):          Text to speak. Any XML tags are stripped first.
            next_action (str|None): URL to redirect to, or None to hang up.
            use_ssml (bool):        Whether to apply SSML enhancements (no-op while disabled).

        Returns:
            str: TwiML XML string.
        """
        response = VoiceResponse()

        if use_ssml and SSML_ENABLED and not message.startswith('<speak>'):
            message = conversational_response(message)

        # strip_ssml() is the safety net — ensures no XML tags reach Twilio's TTS
        response.say(strip_ssml(message), voice='Polly.Joanna-Neural', language='en-US')

        if next_action:
            response.redirect(next_action)
        else:
            response.hangup()

        return str(response)

    def create_gather_response(self, message, action_url, input_type='dtmf',
                               timeout=5, speech_timeout=None, speech_model=None, use_ssml=True):
        """
        Speak a message and collect caller input (keypress or speech).

        The Gather verb waits for the caller to speak or press a key, then
        POSTs the result to action_url. If no input is received within the
        timeout, a "no input" message is spoken and the call redirects back.

        Args:
            message (str):              Prompt to speak before waiting.
            action_url (str):           Webhook URL to POST input to.
            input_type (str):           "dtmf", "speech", or "both".
            timeout (int):              Seconds before timeout.
            speech_timeout (str|None):  "auto" or seconds after speech ends.
            speech_model (str|None):    e.g. "experimental_conversations".
            use_ssml (bool):            Whether to apply SSML (no-op while disabled).

        Returns:
            str: TwiML XML string.
        """
        response = VoiceResponse()

        if input_type == 'speech' or input_type == 'both':
            gather_params = {
                'input': 'dtmf speech',
                'action': action_url,
                'method': 'POST',
                'timeout': timeout,
                'speech_timeout': speech_timeout or 'auto'
            }
            if speech_model:
                gather_params['speech_model'] = speech_model

            gather = Gather(**gather_params)
        else:
            gather = Gather(
                input='dtmf',
                action=action_url,
                method='POST',
                timeout=timeout,
                num_digits=1
            )

        if use_ssml and SSML_ENABLED and not message.startswith('<speak>'):
            message = conversational_response(message)

        gather.say(strip_ssml(message), voice='Polly.Joanna-Neural', language='en-US')
        response.append(gather)

        # No-input fallback: re-prompt and loop back to the same URL
        no_input_msg = strip_ssml(get_cached_ssml('no_input'))
        response.say(no_input_msg, voice='Polly.Joanna-Neural', language='en-US')
        response.redirect(action_url)

        return str(response)

    def create_record_response(self, message, action_url, max_length=60, use_ssml=True):
        """
        Speak a prompt and record the caller's voice message.

        The recording is transcribed automatically by Twilio and posted to
        action_url + '/transcription'.

        Args:
            message (str):     Prompt to speak before recording.
            action_url (str):  URL to POST recording metadata to.
            max_length (int):  Maximum recording length in seconds (default 60).
            use_ssml (bool):   Whether to apply SSML (no-op while disabled).

        Returns:
            str: TwiML XML string.
        """
        response = VoiceResponse()

        if use_ssml and SSML_ENABLED and not message.startswith('<speak>'):
            message = conversational_response(message)

        response.say(strip_ssml(message), voice='Polly.Joanna-Neural', language='en-US')
        response.record(
            action=action_url,
            method='POST',
            max_length=max_length,
            play_beep=True,
            transcribe=True,
            transcribe_callback=action_url + '/transcription'
        )
        return str(response)

    def transfer_call(self, phone_number):
        """
        Place the caller on a brief hold message and dial out to a phone number.

        Args:
            phone_number (str): E.164 number to transfer to (e.g. "+15145550123").

        Returns:
            str: TwiML XML string.
        """
        response = VoiceResponse()
        transfer_msg = strip_ssml(get_cached_ssml('transfer_hold'))
        response.say(transfer_msg, voice='Polly.Joanna-Neural', language='en-US')
        dial = Dial()
        dial.number(phone_number)
        response.append(dial)
        return str(response)

    def send_sms(self, to_number, from_number, message):
        """
        Send an SMS via the Twilio REST API.

        Falls back to a print statement if credentials are not configured
        (useful during development/testing without live Twilio credentials).

        Args:
            to_number (str):   Recipient's E.164 number.
            from_number (str): Twilio number to send from.
            message (str):     SMS body text.

        Returns:
            str or None: The Twilio message SID, or None on failure.
        """
        if not self.client:
            print(f"SMS would be sent to {to_number}: {message}")
            return None

        try:
            msg = self.client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            return msg.sid
        except Exception as e:
            print(f"Error sending SMS: {e}")
            return None


class CiscoProvider(TelephonyProvider):
    """
    Cisco CUCM implementation (stub).

    Returns raw XML responses compatible with Cisco's IVR system.
    Not actively used in production — included for future enterprise integrations.
    """

    def __init__(self, config=None):
        self.config = config or {}

    def create_call_response(self, message, next_action=None):
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="woman">{message}</Say>
    {f'<Redirect>{next_action}</Redirect>' if next_action else '<Hangup/>'}
</Response>'''
        return xml

    def create_gather_response(self, message, action_url, input_type='dtmf',
                               timeout=5, speech_timeout=None, speech_model=None):
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather action="{action_url}" method="POST" timeout="{timeout}" numDigits="1">
        <Say voice="woman">{message}</Say>
    </Gather>
    <Say voice="woman">We didn't receive any input. Please try again.</Say>
    <Redirect>{action_url}</Redirect>
</Response>'''
        return xml

    def create_record_response(self, message, action_url, max_length=60):
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="woman">{message}</Say>
    <Record action="{action_url}" method="POST" maxLength="{max_length}" playBeep="true" transcribe="true"/>
</Response>'''
        return xml

    def transfer_call(self, phone_number):
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="woman">Please hold while we transfer your call.</Say>
    <Dial>{phone_number}</Dial>
</Response>'''
        return xml

    def send_sms(self, to_number, from_number, message):
        print(f"[CISCO] SMS would be sent to {to_number}: {message}")
        return "cisco_sms_" + str(hash(message))


class SIPProvider(TelephonyProvider):
    """
    Generic SIP implementation (stub).

    Returns JSON dicts instead of XML, for use with SIP-based telephony
    platforms that consume JSON instructions.
    """

    def __init__(self, config=None):
        self.config = config or {}

    def create_call_response(self, message, next_action=None):
        return {
            "type": "say",
            "message": message,
            "next_action": next_action,
            "hangup": next_action is None
        }

    def create_gather_response(self, message, action_url, input_type='dtmf',
                               timeout=5, speech_timeout=None, speech_model=None):
        return {
            "type": "gather",
            "message": message,
            "action_url": action_url,
            "input_type": input_type,
            "timeout": timeout,
            "speech_timeout": speech_timeout,
            "speech_model": speech_model
        }

    def create_record_response(self, message, action_url, max_length=60):
        return {
            "type": "record",
            "message": message,
            "action_url": action_url,
            "max_length": max_length
        }

    def transfer_call(self, phone_number):
        return {
            "type": "transfer",
            "message": "Please hold while we transfer your call.",
            "phone_number": phone_number
        }

    def send_sms(self, to_number, from_number, message):
        print(f"[SIP] SMS would be sent to {to_number}: {message}")
        return "sip_sms_" + str(hash(message))


def get_provider(provider_type, config=None):
    """
    Factory function — return the correct provider instance for a given type.

    Args:
        provider_type (str): "twilio", "cisco", or "sip" (case-insensitive).
        config (dict|None):  Optional credentials/config dict for the provider.
                             For Twilio: {"account_sid": "...", "auth_token": "..."}.

    Returns:
        TelephonyProvider: An initialised provider instance. Defaults to
                           TwilioProvider if the type is unrecognised.
    """
    if provider_type.lower() == 'twilio':
        if config:
            return TwilioProvider(
                account_sid=config.get('account_sid'),
                auth_token=config.get('auth_token')
            )
        return TwilioProvider()
    elif provider_type.lower() == 'cisco':
        return CiscoProvider(config)
    elif provider_type.lower() == 'sip':
        return SIPProvider(config)
    else:
        return TwilioProvider()
