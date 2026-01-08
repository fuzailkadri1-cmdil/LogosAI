from abc import ABC, abstractmethod
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Record, Dial
import os
from typing import Any
from ssml_helper import conversational_response, get_cached_ssml, SSML_ENABLED

class TelephonyProvider(ABC):
    
    @abstractmethod
    def create_call_response(self, message, next_action=None) -> Any:
        pass
    
    @abstractmethod
    def create_gather_response(self, message, action_url, input_type='dtmf', timeout=5, speech_timeout=None, speech_model=None) -> Any:
        pass
    
    @abstractmethod
    def create_record_response(self, message, action_url, max_length=60) -> Any:
        pass
    
    @abstractmethod
    def transfer_call(self, phone_number) -> Any:
        pass
    
    @abstractmethod
    def send_sms(self, to_number, from_number, message) -> Any:
        pass


class TwilioProvider(TelephonyProvider):
    
    def __init__(self, account_sid=None, auth_token=None):
        self.account_sid = account_sid or os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = auth_token or os.environ.get('TWILIO_AUTH_TOKEN')
        self.client = None
        
        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
            except Exception as e:
                print(f"Error initializing Twilio client: {e}")
    
    def create_call_response(self, message, next_action=None, use_ssml=True):
        response = VoiceResponse()
        
        # Apply SSML if enabled and requested
        if use_ssml and SSML_ENABLED and not message.startswith('<speak>'):
            message = conversational_response(message)
        
        # Use SSML-aware say method
        if message.startswith('<speak>'):
            response.say(message, voice='Polly.Joanna', language='en-US')
        else:
            response.say(message, voice='Polly.Joanna', language='en-US')
        
        if next_action:
            response.redirect(next_action)
        else:
            response.hangup()
        
        return str(response)
    
    def create_gather_response(self, message, action_url, input_type='dtmf', timeout=5, speech_timeout=None, speech_model=None, use_ssml=True):
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
        
        # Apply SSML if enabled and requested
        if use_ssml and SSML_ENABLED and not message.startswith('<speak>'):
            message = conversational_response(message)
        
        # Use Polly.Joanna for more natural voice
        gather.say(message, voice='Polly.Joanna', language='en-US')
        response.append(gather)
        
        # Use cached SSML for no-input message
        no_input_msg = get_cached_ssml('no_input')
        response.say(no_input_msg, voice='Polly.Joanna', language='en-US')
        response.redirect(action_url)
        
        return str(response)
    
    def create_record_response(self, message, action_url, max_length=60, use_ssml=True):
        response = VoiceResponse()
        
        # Apply SSML if enabled
        if use_ssml and SSML_ENABLED and not message.startswith('<speak>'):
            message = conversational_response(message)
        
        response.say(message, voice='Polly.Joanna', language='en-US')
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
        response = VoiceResponse()
        # Use cached SSML for transfer message
        transfer_msg = get_cached_ssml('transfer_hold')
        response.say(transfer_msg, voice='Polly.Joanna', language='en-US')
        dial = Dial()
        dial.number(phone_number)
        response.append(dial)
        return str(response)
    
    def send_sms(self, to_number, from_number, message):
        if not self.client:
            print(f"SMS would be sent to {to_number}: {message}")
            return None
        
        try:
            message = self.client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            return message.sid
        except Exception as e:
            print(f"Error sending SMS: {e}")
            return None


class CiscoProvider(TelephonyProvider):
    
    def __init__(self, config=None):
        self.config = config or {}
    
    def create_call_response(self, message, next_action=None):
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="woman">{message}</Say>
    {f'<Redirect>{next_action}</Redirect>' if next_action else '<Hangup/>'}
</Response>'''
        return xml
    
    def create_gather_response(self, message, action_url, input_type='dtmf', timeout=5, speech_timeout=None, speech_model=None):
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
    
    def __init__(self, config=None):
        self.config = config or {}
    
    def create_call_response(self, message, next_action=None):
        return {
            "type": "say",
            "message": message,
            "next_action": next_action,
            "hangup": next_action is None
        }
    
    def create_gather_response(self, message, action_url, input_type='dtmf', timeout=5, speech_timeout=None, speech_model=None):
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
