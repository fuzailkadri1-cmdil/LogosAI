"""
models.py — SQLAlchemy Database Models

Defines every table in the Logos AI PostgreSQL database.
All models use Flask-SQLAlchemy with the declarative base pattern.

Table overview:
  Company        — A business using Logos AI (one per account)
  User           — An authenticated user, linked to a Company
  OAuth          — Stores OAuth tokens for Replit Auth sessions
  Integration    — Third-party integrations (Twilio, etc.) per company
  CallLog        — Record of every inbound call, including AI transcript
  Voicemail      — Recorded voicemail messages left by callers
  PilotCustomer  — A retail store enrolled in the pilot programme
  PilotOrder     — An order record uploaded via CSV for a pilot store
  Lead           — A captured sales lead from a purchase inquiry call
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import json
from flask_login import UserMixin


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class Company(db.Model):
    """
    Represents a business account on Logos AI.

    Each company has its own Twilio phone number, greeting, business hours,
    and escalation number. All other records (users, calls, leads) are
    linked back to a company via foreign keys.
    """

    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Voice AI configuration
    greeting_message = db.Column(db.Text, default="Hi, thanks for calling! How can I help you today?")
    menu_options = db.Column(db.Text, default='{"1": "Order Status", "2": "Store Hours", "3": "Speak to Agent"}')
    business_hours = db.Column(db.Text, default='{"monday-friday": "9am-9pm", "saturday-sunday": "10am-6pm"}')
    escalation_number = db.Column(db.String(20), nullable=True)

    # Relationships — cascade deletes so removing a company cleans up all related records
    users = db.relationship('User', backref='company', lazy=True)
    integrations = db.relationship('Integration', backref='company', lazy=True, cascade='all, delete-orphan')
    call_logs = db.relationship('CallLog', backref='company', lazy=True, cascade='all, delete-orphan')
    voicemails = db.relationship('Voicemail', backref='company', lazy=True, cascade='all, delete-orphan')
    pilot_customers = db.relationship('PilotCustomer', backref='company', lazy=True, cascade='all, delete-orphan')

    def get_menu_options(self):
        """
        Parse the JSON menu_options column into a Python dict.

        Returns:
            dict: Mapping of keypad digit → option label.
                  Falls back to defaults if the stored JSON is malformed.
        """
        try:
            return json.loads(self.menu_options)
        except Exception:
            return {"1": "Order Status", "2": "Store Hours", "3": "Speak to Agent"}

    def get_business_hours(self):
        """
        Parse the JSON business_hours column into a Python dict.

        Returns:
            dict: Mapping of day range → hours string, e.g. {"monday-friday": "9am-5pm"}.
                  Falls back to defaults if the stored JSON is malformed.
        """
        try:
            return json.loads(self.business_hours)
        except Exception:
            return {"monday-friday": "9am-9pm", "saturday-sunday": "10am-6pm"}

    def __repr__(self):
        return f'<Company {self.name}>'


class User(UserMixin, db.Model):
    """
    An authenticated user, linked to a Company.

    Users log in via Replit Auth (OAuth). The id field is the Replit user ID
    (a string), not an auto-incrementing integer.
    """

    __tablename__ = 'users'

    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    profile_image_url = db.Column(db.String(500), nullable=True)

    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default='user')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    @property
    def full_name(self):
        """
        Return the user's display name, falling back gracefully.

        Returns:
            str: "First Last", "First", email prefix, or "User" — in that order.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.email:
            return self.email.split('@')[0]
        return "User"

    def __repr__(self):
        return f'<User {self.email}>'


class OAuth(db.Model):
    """
    Stores OAuth session tokens for Replit Auth.

    Each row ties a user + browser session + provider together.
    The unique constraint prevents duplicate tokens per session.
    """

    __tablename__ = 'oauth'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'))
    browser_session_key = db.Column(db.String, nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    token = db.Column(db.JSON, nullable=True)

    user = db.relationship('User')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'browser_session_key', 'provider',
                            name='uq_user_browser_session_provider'),
    )


class Integration(db.Model):
    """
    A third-party integration configured for a company (e.g. Twilio).

    The config column stores provider-specific credentials as JSON
    (API keys, account SIDs, etc.).
    """

    __tablename__ = 'integrations'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    provider_type = db.Column(db.String(50), nullable=False)
    provider_name = db.Column(db.String(100), nullable=False)
    config = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_tested = db.Column(db.DateTime, nullable=True)
    test_status = db.Column(db.String(20), default='pending')

    def get_config(self):
        """
        Parse the JSON config column into a dict.

        Returns:
            dict: Provider credentials/settings. Empty dict if malformed.
        """
        try:
            return json.loads(self.config)
        except Exception:
            return {}

    def set_config(self, config_dict):
        """
        Serialize a config dict and store it in the config column.

        Args:
            config_dict (dict): Provider credentials/settings to store.
        """
        self.config = json.dumps(config_dict)

    def __repr__(self):
        return f'<Integration {self.provider_name} for Company {self.company_id}>'


class CallLog(db.Model):
    """
    A record of a single inbound phone call.

    Created when the call arrives and updated as the conversation progresses.
    Stores the full AI conversation transcript as JSON in ai_conversation.
    """

    __tablename__ = 'call_logs'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    caller_phone = db.Column(db.String(20), nullable=False)
    call_sid = db.Column(db.String(100), unique=True, nullable=True)   # Twilio call identifier
    intent = db.Column(db.String(50), nullable=True)                   # Detected caller intent
    outcome = db.Column(db.String(50), default='in_progress')          # resolved / escalated / voicemail / in_progress
    duration_seconds = db.Column(db.Integer, default=0)
    transcript = db.Column(db.Text, nullable=True)                     # Plain-text summary
    provider_type = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    handled_by_ai = db.Column(db.Boolean, default=True)

    # AI conversation details
    ai_conversation = db.Column(db.Text, nullable=True)                # JSON array of {role, content} turns
    ai_confidence = db.Column(db.Float, nullable=True)
    conversation_turns = db.Column(db.Integer, default=0)
    escalation_reason = db.Column(db.String(100), nullable=True)
    pilot_id = db.Column(db.Integer, db.ForeignKey('pilot_customers.id'), nullable=True)

    def get_conversation(self):
        """
        Parse the JSON ai_conversation column into a list of message dicts.

        Returns:
            list: List of {"role": str, "content": str} dicts.
                  Empty list if no conversation stored or JSON is malformed.
        """
        try:
            return json.loads(self.ai_conversation) if self.ai_conversation else []
        except Exception:
            return []

    def set_conversation(self, messages):
        """
        Serialize a list of message dicts and store in ai_conversation.

        Args:
            messages (list): List of {"role": str, "content": str} dicts.
        """
        self.ai_conversation = json.dumps(messages)

    def __repr__(self):
        return f'<CallLog {self.id} - {self.intent}>'


class Voicemail(db.Model):
    """
    A voicemail recording left by a caller.

    recording_url points to the Twilio-hosted audio file.
    transcription is the auto-generated text from Twilio's transcription service.
    """

    __tablename__ = 'voicemails'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    call_log_id = db.Column(db.Integer, db.ForeignKey('call_logs.id'), nullable=True)
    caller_phone = db.Column(db.String(20), nullable=False)
    recording_url = db.Column(db.String(500), nullable=True)
    transcription = db.Column(db.Text, nullable=True)
    duration_seconds = db.Column(db.Integer, default=0)
    is_listened = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Voicemail {self.id} from {self.caller_phone}>'


class PilotCustomer(db.Model):
    """
    A retail store enrolled in the Logos AI pilot programme.

    Each pilot store gets its own Twilio number and can upload a CSV of
    orders so callers can check their order status by phone.
    """

    __tablename__ = 'pilot_customers'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    industry = db.Column(db.String(100), nullable=True)
    contact_email = db.Column(db.String(200), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)
    twilio_number = db.Column(db.String(20), nullable=True)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')    # active / paused / ended
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('PilotOrder', backref='pilot', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<PilotCustomer {self.name}>'


class PilotOrder(db.Model):
    """
    An order record for a pilot store, uploaded via CSV.

    When a caller asks for their order status, the AI looks up the order number
    in this table for the matching pilot store.
    """

    __tablename__ = 'pilot_orders'

    id = db.Column(db.Integer, primary_key=True)
    pilot_id = db.Column(db.Integer, db.ForeignKey('pilot_customers.id'), nullable=False)
    order_id = db.Column(db.String(100), nullable=False)
    customer_name = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(50), default='processing')       # processing / shipped / delivered / etc.
    tracking_number = db.Column(db.String(100), nullable=True)
    estimated_delivery = db.Column(db.String(100), nullable=True)
    delivery_address = db.Column(db.Text, nullable=True)
    order_total = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PilotOrder {self.order_id} for Pilot {self.pilot_id}>'


class Lead(db.Model):
    """
    A sales lead captured from a purchase inquiry call.

    Created whenever a caller expresses interest in buying something.
    During business hours the lead is captured and the call is escalated
    to staff. After hours the lead is captured with a callback number
    for next-day follow-up.
    """

    __tablename__ = 'leads'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    pilot_id = db.Column(db.Integer, db.ForeignKey('pilot_customers.id'), nullable=True)
    caller_name = db.Column(db.String(200), nullable=True)
    caller_phone = db.Column(db.String(20), nullable=False)
    inquiry = db.Column(db.Text, nullable=True)                    # What the caller is looking for
    call_type = db.Column(db.String(20), default='during_hours')   # during_hours / after_hours
    status = db.Column(db.String(20), default='new')               # new / contacted / closed
    call_log_id = db.Column(db.Integer, db.ForeignKey('call_logs.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    company = db.relationship('Company', backref=db.backref('leads', lazy=True))
    pilot = db.relationship('PilotCustomer', backref=db.backref('leads', lazy=True))

    def __repr__(self):
        return f'<Lead {self.id} - {self.caller_name or self.caller_phone}>'
