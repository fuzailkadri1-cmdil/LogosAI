from abc import ABC, abstractmethod
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Record, Dial
import os
from typing import Any

class TelephonyProvider(ABC):
    
    @abstractmethod
    def create_call_response(self, message, next_action=None) -> Any:
        pass
    
    @abstractmethod
    def create_gather_response(self, message, action_url, input_type='dtmf', timeout=5) -> Any:
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
    
    def create_call_response(self, message, next_action=None):
        response = VoiceResponse()
        response.say(message, voice='alice', language='en-US')
        
        if next_action:
            response.redirect(next_action)
        else:
            response.hangup()
        
        return str(response)
    
    def create_gather_response(self, message, action_url, input_type='dtmf', timeout=5):
        response = VoiceResponse()
        
        if input_type == 'speech' or input_type == 'both':
            gather = Gather(
                input='dtmf speech',
                action=action_url,
                method='POST',
                timeout=timeout,
                speech_timeout='auto'
            )
        else:
            gather = Gather(
                input='dtmf',
                action=action_url,
                method='POST',
                timeout=timeout,
                num_digits=1
            )
        
        gather.say(message, voice='alice', language='en-US')
        response.append(gather)
        
        response.say("We didn't receive any input. Please try again.", voice='alice')
        response.redirect(action_url)
        
        return str(response)
    
    def create_record_response(self, message, action_url, max_length=60):
        response = VoiceResponse()
        response.say(message, voice='alice', language='en-US')
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
        response.say("Please hold while we transfer your call.", voice='alice')
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
    
    def create_gather_response(self, message, action_url, input_type='dtmf', timeout=5):
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
    
    def create_gather_response(self, message, action_url, input_type='dtmf', timeout=5):
        return {
            "type": "gather",
            "message": message,
            "action_url": action_url,
            "input_type": input_type,
            "timeout": timeout
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
