from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    greeting_message = db.Column(db.Text, default="Welcome to our call center.")
    menu_options = db.Column(db.Text, default='{"1": "Order Status", "2": "Store Hours", "3": "Speak to Agent"}')
    business_hours = db.Column(db.Text, default='{"monday-friday": "9am-9pm", "saturday-sunday": "10am-6pm"}')
    escalation_number = db.Column(db.String(20), nullable=True)
    
    users = db.relationship('User', backref='company', lazy=True, cascade='all, delete-orphan')
    integrations = db.relationship('Integration', backref='company', lazy=True, cascade='all, delete-orphan')
    call_logs = db.relationship('CallLog', backref='company', lazy=True, cascade='all, delete-orphan')
    voicemails = db.relationship('Voicemail', backref='company', lazy=True, cascade='all, delete-orphan')
    
    def get_menu_options(self):
        try:
            return json.loads(self.menu_options)
        except:
            return {"1": "Order Status", "2": "Store Hours", "3": "Speak to Agent"}
    
    def get_business_hours(self):
        try:
            return json.loads(self.business_hours)
        except:
            return {"monday-friday": "9am-9pm", "saturday-sunday": "10am-6pm"}
    
    def __repr__(self):
        return f'<Company {self.name}>'


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='admin')
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Integration(db.Model):
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
        try:
            return json.loads(self.config)
        except:
            return {}
    
    def set_config(self, config_dict):
        self.config = json.dumps(config_dict)
    
    def __repr__(self):
        return f'<Integration {self.provider_name} for Company {self.company_id}>'


class CallLog(db.Model):
    __tablename__ = 'call_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    caller_phone = db.Column(db.String(20), nullable=False)
    call_sid = db.Column(db.String(100), unique=True, nullable=True)
    intent = db.Column(db.String(50), nullable=True)
    outcome = db.Column(db.String(50), default='in_progress')
    duration_seconds = db.Column(db.Integer, default=0)
    transcript = db.Column(db.Text, nullable=True)
    provider_type = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    handled_by_ai = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<CallLog {self.id} - {self.intent}>'


class Voicemail(db.Model):
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
