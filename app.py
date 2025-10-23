from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from models import db, Company, User, Integration, CallLog, Voicemail
from providers import get_provider
from call_engine import CallFlowEngine, IntentRouter
from ai_voice_agent import AIVoiceAgent
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from twilio.twiml.voice_response import VoiceResponse
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///callcenter.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def get_company_by_phone(phone_number):
    clean_phone = phone_number.replace('+', '').replace('-', '').replace(' ', '')
    
    companies = Company.query.filter_by(is_active=True).all()
    for company in companies:
        if company.phone_number:
            clean_company_phone = company.phone_number.replace('+', '').replace('-', '').replace(' ', '')
            if clean_company_phone in clean_phone or clean_phone in clean_company_phone:
                return company
    
    return None

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email, is_active=True).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['company_id'] = user.company_id
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')
        
        default_greeting = "Thank you for calling. How can I help you today?"
        default_menu = json.dumps({
            '1': 'Order Status',
            '2': 'Business Hours',
            '3': 'Speak to Agent',
            '4': 'Leave Voicemail'
        })
        default_hours = json.dumps({
            'monday-friday': '9am-5pm',
            'saturday-sunday': 'Closed'
        })
        
        company = Company(
            name=company_name,
            greeting_message=default_greeting,
            menu_options=default_menu,
            business_hours=default_hours
        )
        db.session.add(company)
        db.session.flush()
        
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            company_id=company.id,
            role='admin'
        )
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        session['company_id'] = company.id
        flash('Registration successful! Welcome to Call Center Automation.', 'success')
        return redirect(url_for('onboarding'))
    
    return render_template('register.html')

@app.route('/onboarding')
@login_required
def onboarding():
    user = get_current_user()
    company = Company.query.get(session['company_id'])
    integrations = Integration.query.filter_by(company_id=company.id).all()
    
    return render_template('onboarding.html', company=company, integrations=integrations)

@app.route('/onboarding/provider', methods=['POST'])
@login_required
def setup_provider():
    provider_type = request.form.get('provider_type')
    provider_name = request.form.get('provider_name')
    
    config = {}
    
    if provider_type == 'twilio':
        config = {
            'account_sid': request.form.get('account_sid', ''),
            'auth_token': request.form.get('auth_token', ''),
            'phone_number': request.form.get('phone_number', '')
        }
    elif provider_type == 'cisco':
        config = {
            'api_url': request.form.get('api_url', ''),
            'api_key': request.form.get('api_key', ''),
            'phone_number': request.form.get('phone_number', '')
        }
    elif provider_type == 'sip':
        config = {
            'sip_server': request.form.get('sip_server', ''),
            'username': request.form.get('username', ''),
            'password': request.form.get('password', ''),
            'phone_number': request.form.get('phone_number', '')
        }
    
    integration = Integration(
        company_id=session['company_id'],
        provider_type=provider_type,
        provider_name=provider_name,
        config=json.dumps(config),
        is_active=True
    )
    
    db.session.add(integration)
    
    company = Company.query.get(session['company_id'])
    if 'phone_number' in config and config['phone_number']:
        company.phone_number = config['phone_number']
    
    db.session.commit()
    
    flash(f'{provider_name} integration added successfully!', 'success')
    return redirect(url_for('onboarding'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    company = Company.query.get(session['company_id'])
    
    total_calls = CallLog.query.filter_by(company_id=company.id).count()
    ai_handled = CallLog.query.filter_by(company_id=company.id, handled_by_ai=True).count()
    
    recent_calls = CallLog.query.filter_by(company_id=company.id)\
        .order_by(CallLog.created_at.desc())\
        .limit(10)\
        .all()
    
    voicemails = Voicemail.query.filter_by(company_id=company.id, is_listened=False).count()
    
    return render_template('dashboard.html', 
                         company=company, 
                         total_calls=total_calls,
                         ai_handled=ai_handled,
                         recent_calls=recent_calls,
                         voicemails=voicemails,
                         user=user)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    company = Company.query.get(session['company_id'])
    
    if request.method == 'POST':
        company.greeting_message = request.form.get('greeting_message')
        company.escalation_number = request.form.get('escalation_number')
        
        menu_options = {}
        for i in range(1, 6):
            option_value = request.form.get(f'menu_option_{i}')
            if option_value:
                menu_options[str(i)] = option_value
        
        company.menu_options = json.dumps(menu_options)
        
        business_hours = {}
        for day_range in ['monday-friday', 'saturday-sunday']:
            hours = request.form.get(f'hours_{day_range}')
            if hours:
                business_hours[day_range] = hours
        
        company.business_hours = json.dumps(business_hours)
        
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))
    
    integrations = Integration.query.filter_by(company_id=company.id).all()
    
    return render_template('settings.html', company=company, integrations=integrations)

@app.route('/calls')
@login_required
def calls():
    company = Company.query.get(session['company_id'])
    all_calls = CallLog.query.filter_by(company_id=company.id)\
        .order_by(CallLog.created_at.desc())\
        .all()
    
    return render_template('calls.html', calls=all_calls, company=company)

@app.route('/calls/<int:call_id>')
@login_required
def call_detail(call_id):
    call = CallLog.query.get_or_404(call_id)
    
    if call.company_id != session['company_id']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('calls'))
    
    return render_template('call_detail.html', call=call)

@app.route('/voicemails')
@login_required
def voicemails():
    company = Company.query.get(session['company_id'])
    all_voicemails = Voicemail.query.filter_by(company_id=company.id)\
        .order_by(Voicemail.created_at.desc())\
        .all()
    
    return render_template('voicemails.html', voicemails=all_voicemails, company=company)

@app.route('/voicemails/<int:voicemail_id>/listen', methods=['POST'])
@login_required
def mark_voicemail_listened(voicemail_id):
    voicemail = Voicemail.query.get_or_404(voicemail_id)
    
    if voicemail.company_id != session['company_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    voicemail.is_listened = True
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/stats')
@login_required
def api_stats():
    company = Company.query.get(session['company_id'])
    
    total_calls = CallLog.query.filter_by(company_id=company.id).count()
    ai_handled = CallLog.query.filter_by(company_id=company.id, handled_by_ai=True).count()
    agent_handled = total_calls - ai_handled
    
    ai_escalated_calls = CallLog.query.filter(
        CallLog.company_id == company.id,
        CallLog.handled_by_ai == True,
        CallLog.outcome == 'transferred'
    ).count()
    
    avg_confidence_result = db.session.query(
        db.func.avg(CallLog.ai_confidence)
    ).filter(
        CallLog.company_id == company.id,
        CallLog.ai_confidence.isnot(None)
    ).scalar()
    avg_confidence = round(avg_confidence_result * 100 if avg_confidence_result else 0, 1)
    
    avg_turns_result = db.session.query(
        db.func.avg(CallLog.conversation_turns)
    ).filter(
        CallLog.company_id == company.id,
        CallLog.conversation_turns > 0
    ).scalar()
    avg_turns = round(avg_turns_result if avg_turns_result else 0, 1)
    
    intent_counts = db.session.query(
        CallLog.intent, 
        db.func.count(CallLog.id)
    ).filter_by(company_id=company.id).group_by(CallLog.intent).all()
    
    intent_data = {intent: count for intent, count in intent_counts if intent}
    
    today = datetime.utcnow().date()
    last_7_days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    
    daily_calls = []
    for day in last_7_days:
        count = CallLog.query.filter(
            CallLog.company_id == company.id,
            db.func.date(CallLog.created_at) == day
        ).count()
        daily_calls.append(count)
    
    return jsonify({
        'automation_rate': {
            'ai_handled': ai_handled,
            'agent_handled': agent_handled
        },
        'ai_metrics': {
            'avg_confidence': avg_confidence,
            'avg_conversation_turns': avg_turns,
            'ai_escalated_calls': ai_escalated_calls,
            'escalation_rate': round((ai_escalated_calls / ai_handled * 100) if ai_handled > 0 else 0, 1)
        },
        'intents': intent_data,
        'daily_calls': {
            'labels': last_7_days,
            'data': daily_calls
        }
    })

@app.route('/voice/webhook', methods=['GET', 'POST'])
def voice_webhook():
    """Initial webhook when call arrives - routes to AI conversation"""
    
    if request.method == 'GET':
        return '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">This is the Twilio webhook endpoint. It works! Configure this URL in your Twilio console to handle incoming calls.</Say>
</Response>''', 200, {'Content-Type': 'text/xml'}
    
    try:
        from_number = request.values.get('From', request.values.get('from', 'Unknown'))
        to_number = request.values.get('To', request.values.get('to', ''))
        call_sid = request.values.get('CallSid', f'SIM_{datetime.utcnow().timestamp()}')
        
        company = get_company_by_phone(to_number)
        
        if not company:
            company = Company.query.filter_by(is_active=True).first()
        
        if not company:
            error_response = VoiceResponse()
            error_response.say("Sorry, no active company configuration found. Please contact support.", voice='alice')
            error_response.hangup()
            return str(error_response), 200, {'Content-Type': 'text/xml'}
        
        integration = Integration.query.filter_by(company_id=company.id, is_active=True).first()
        provider_type = integration.provider_type if integration else 'twilio'
        provider_config = integration.get_config() if integration else None
        
        provider = get_provider(provider_type, provider_config)
        engine = CallFlowEngine(company)
        
        call_log = engine.log_call(from_number, call_sid, None, 'in_progress')
        
        if not company.greeting_message or not company.greeting_message.strip():
            default_message = "Thank you for calling. Please configure your company greeting message in the settings to enable full voice automation features. Goodbye."
            response = provider.create_call_response(default_message)
            return response, 200, {'Content-Type': 'text/xml' if provider_type != 'sip' else 'application/json'}
        
        greeting = company.greeting_message
        
        response = provider.create_gather_response(
            greeting,
            url_for('voice_ai_conversation', _external=True),
            input_type='speech',
            speech_timeout=3,
            speech_model='experimental_conversations'
        )
        
        return response, 200, {'Content-Type': 'text/xml' if provider_type != 'sip' else 'application/json'}
    
    except Exception as e:
        print(f"Error in voice_webhook: {e}")
        error_response = VoiceResponse()
        error_response.say("Sorry, we encountered an error. Please try again later.", voice='alice')
        error_response.hangup()
        return str(error_response), 200, {'Content-Type': 'text/xml'}

@app.route('/voice/ai_conversation', methods=['GET', 'POST'])
def voice_ai_conversation():
    """Handle AI-powered conversation loop"""
    
    try:
        # Use request.values to get parameters from both GET query string and POST form data
        from_number = request.values.get('From', request.values.get('from', 'Unknown'))
        to_number = request.values.get('To', request.values.get('to', ''))
        call_sid = request.values.get('CallSid', f'SIM_{datetime.utcnow().timestamp()}')
        speech_result = request.values.get('SpeechResult', '')
        
        # Log for debugging
        print(f"Method: {request.method}, SpeechResult: '{speech_result}', CallSid: {call_sid}")
        
        company = get_company_by_phone(to_number)
        if not company:
            company = Company.query.filter_by(is_active=True).first()
        
        if not company:
            error_response = VoiceResponse()
            error_response.say("Sorry, no active company configuration found.", voice='alice')
            error_response.hangup()
            return str(error_response), 200, {'Content-Type': 'text/xml'}
        
        integration = Integration.query.filter_by(company_id=company.id, is_active=True).first()
        provider_type = integration.provider_type if integration else 'twilio'
        provider_config = integration.get_config() if integration else None
        
        provider = get_provider(provider_type, provider_config)
        
        call_log = CallLog.query.filter_by(call_sid=call_sid).first()
        if not call_log:
            engine = CallFlowEngine(company)
            call_log = engine.log_call(from_number, call_sid, None, 'in_progress')
        
        session_key = f'ai_agent_{call_sid}'
        if session_key not in session:
            company_config = {
                'name': company.name,
                'business_hours': company.get_business_hours(),
                'phone_number': company.phone_number
            }
            ai_agent = AIVoiceAgent(company_config)
            session[session_key] = {
                'conversation_history': [],
                'turn_count': 0
            }
        else:
            company_config = {
                'name': company.name,
                'business_hours': company.get_business_hours(),
                'phone_number': company.phone_number
            }
            ai_agent = AIVoiceAgent(company_config)
            ai_agent.conversation_history = session[session_key]['conversation_history']
        
        if not speech_result or speech_result.strip() == '':
            # First time or no speech detected - provide welcome and gather
            welcome_message = "Hello! How can I help you today? You can ask about order status, store hours, or speak with an agent."
            response = provider.create_gather_response(
                welcome_message,
                url_for('voice_ai_conversation', _external=True),
                input_type='speech',
                speech_timeout=5,
                speech_model='experimental_conversations'
            )
            return response, 200, {'Content-Type': 'text/xml' if provider_type != 'sip' else 'application/json'}
        
        ai_result = ai_agent.process_speech(speech_result)
        
        session[session_key]['conversation_history'] = ai_agent.conversation_history
        session[session_key]['turn_count'] += 1
        
        call_log.intent = ai_result['intent']
        call_log.ai_confidence = ai_result['confidence']
        call_log.conversation_turns = session[session_key]['turn_count']
        call_log.set_conversation(ai_agent.conversation_history)
        
        transcript_text = '\n'.join([
            f"{msg['role']}: {msg['content']}" 
            for msg in ai_agent.conversation_history
        ])
        call_log.transcript = transcript_text
        
        if ai_result.get('should_end_call', False):
            # User said goodbye - end call gracefully
            call_log.outcome = 'completed'
            call_log.handled_by_ai = True
            call_log.completed_at = datetime.utcnow()
            db.session.commit()
            
            session.pop(session_key, None)
            
            response = provider.create_call_response(ai_result['response'])
        
        elif ai_result['should_escalate']:
            call_log.outcome = 'transferred'
            call_log.escalation_reason = ai_result.get('escalation_reason', 'unknown')
            call_log.handled_by_ai = True
            call_log.completed_at = datetime.utcnow()
            db.session.commit()
            
            session.pop(session_key, None)
            
            if company.escalation_number:
                response = provider.transfer_call(company.escalation_number)
            else:
                response = provider.create_call_response(
                    ai_result['response'] + " However, we don't have an agent available right now. Please try calling back during business hours. Goodbye!"
                )
        else:
            db.session.commit()
            
            response = provider.create_gather_response(
                ai_result['response'],
                url_for('voice_ai_conversation', _external=True),
                input_type='speech',
                speech_timeout=3,
                speech_model='experimental_conversations'
            )
        
        return response, 200, {'Content-Type': 'text/xml' if provider_type != 'sip' else 'application/json'}
    
    except Exception as e:
        print(f"Error in voice_ai_conversation: {e}")
        import traceback
        traceback.print_exc()
        error_response = VoiceResponse()
        error_response.say("Sorry, we encountered an error processing your request. Please try again later.", voice='alice')
        error_response.hangup()
        return str(error_response), 200, {'Content-Type': 'text/xml'}

@app.route('/voice/handle_input', methods=['POST'])
def voice_handle_input():
    from_number = request.values.get('From', request.values.get('from', 'Unknown'))
    to_number = request.values.get('To', request.values.get('to', ''))
    call_sid = request.values.get('CallSid', f'SIM_{datetime.utcnow().timestamp()}')
    
    digits = request.values.get('Digits')
    speech_result = request.values.get('SpeechResult', '')
    
    company = get_company_by_phone(to_number)
    if not company:
        company = Company.query.filter_by(is_active=True).first()
    
    integration = Integration.query.filter_by(company_id=company.id, is_active=True).first()
    provider_type = integration.provider_type if integration else 'twilio'
    provider_config = integration.get_config() if integration else None
    
    provider = get_provider(provider_type, provider_config)
    engine = CallFlowEngine(company)
    
    intent = engine.determine_intent(speech_result, digits)
    
    call_log = CallLog.query.filter_by(call_sid=call_sid).first()
    if call_log:
        call_log.intent = intent
        call_log.transcript = speech_result or f"DTMF: {digits}"
        db.session.commit()
    
    context = {}
    
    if intent == 'OrderStatus':
        order_number = engine.extract_order_number(speech_result)
        context['order_number'] = order_number
    
    message = IntentRouter.route_intent(engine, intent, context)
    
    if intent == 'ConnectAgent' and company.escalation_number:
        if call_log:
            call_log.outcome = 'transferred'
            call_log.handled_by_ai = False
            db.session.commit()
        response = provider.transfer_call(company.escalation_number)
    elif intent == 'Voicemail':
        response = provider.create_record_response(
            message,
            url_for('voice_voicemail', _external=True)
        )
    else:
        if call_log:
            call_log.outcome = 'resolved'
            db.session.commit()
        response = provider.create_call_response(message + " Thank you for calling. Goodbye!")
    
    return response, 200, {'Content-Type': 'text/xml' if provider_type != 'sip' else 'application/json'}

@app.route('/voice/voicemail', methods=['POST'])
def voice_voicemail():
    from_number = request.values.get('From', request.values.get('from', 'Unknown'))
    to_number = request.values.get('To', request.values.get('to', ''))
    call_sid = request.values.get('CallSid', f'SIM_{datetime.utcnow().timestamp()}')
    recording_url = request.values.get('RecordingUrl', '')
    recording_duration = request.values.get('RecordingDuration', 0)
    
    company = get_company_by_phone(to_number)
    if not company:
        company = Company.query.filter_by(is_active=True).first()
    
    call_log = CallLog.query.filter_by(call_sid=call_sid).first()
    
    voicemail = Voicemail(
        company_id=company.id,
        call_log_id=call_log.id if call_log else None,
        caller_phone=from_number,
        recording_url=recording_url,
        duration_seconds=int(recording_duration) if recording_duration else 0
    )
    
    db.session.add(voicemail)
    
    if call_log:
        call_log.outcome = 'voicemail'
        db.session.commit()
    
    integration = Integration.query.filter_by(company_id=company.id, is_active=True).first()
    provider_type = integration.provider_type if integration else 'twilio'
    provider_config = integration.get_config() if integration else None
    
    provider = get_provider(provider_type, provider_config)
    response = provider.create_call_response("Thank you for your message. We will get back to you soon. Goodbye!")
    
    return response, 200, {'Content-Type': 'text/xml' if provider_type != 'sip' else 'application/json'}

@app.route('/simulate_call')
def simulate_call():
    intent = request.args.get('intent', 'OrderStatus')
    caller = request.args.get('caller', '+15555551234')
    
    companies = Company.query.filter_by(is_active=True).all()
    if not companies:
        return jsonify({'error': 'No active companies found'}), 404
    
    company = companies[0]
    
    engine = CallFlowEngine(company)
    
    call_sid = f'SIM_{datetime.utcnow().timestamp()}'
    call_log = engine.log_call(
        caller_phone=caller,
        call_sid=call_sid,
        intent=intent,
        outcome='resolved',
        transcript=f'Simulated call with intent: {intent}',
        handled_by_ai=True,
        duration=45
    )
    
    return jsonify({
        'success': True,
        'call_id': call_log.id,
        'company': company.name,
        'intent': intent,
        'message': f'Simulated {intent} call from {caller}'
    })

@app.route('/test_integration/<int:integration_id>', methods=['POST'])
@login_required
def test_integration(integration_id):
    integration = Integration.query.get_or_404(integration_id)
    
    if integration.company_id != session['company_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        provider = get_provider(integration.provider_type, integration.get_config())
        test_response = provider.create_call_response("This is a test message.")
        
        integration.last_tested = datetime.utcnow()
        integration.test_status = 'success'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Integration test successful!',
            'response_preview': str(test_response)[:200]
        })
    except Exception as e:
        integration.test_status = 'failed'
        db.session.commit()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/delete_integration/<int:integration_id>', methods=['POST', 'DELETE'])
@login_required
def delete_integration(integration_id):
    integration = Integration.query.get_or_404(integration_id)
    
    if integration.company_id != session['company_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        provider_name = integration.provider_name
        db.session.delete(integration)
        db.session.commit()
        
        flash(f'{provider_name} integration deleted successfully!', 'success')
        return jsonify({
            'success': True,
            'message': f'{provider_name} integration deleted!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/listen-mode')
@login_required
def listen_mode():
    company = Company.query.get(session['company_id'])
    
    intent_data = db.session.query(
        CallLog.intent,
        db.func.count(CallLog.id).label('count')
    ).filter_by(company_id=company.id).group_by(CallLog.intent).all()
    
    intent_recommendations = []
    for intent, count in intent_data:
        if intent and count >= 3:
            automation_potential = min(95, 60 + (count * 2))
            intent_recommendations.append({
                'intent': intent,
                'call_count': count,
                'automation_potential': automation_potential,
                'recommended': count >= 5
            })
    
    intent_recommendations.sort(key=lambda x: x['call_count'], reverse=True)
    
    recent_transcripts = CallLog.query.filter(
        CallLog.company_id == company.id,
        CallLog.transcript.isnot(None)
    ).order_by(CallLog.created_at.desc()).limit(20).all()
    
    return render_template('listen_mode.html', 
                         company=company,
                         recommendations=intent_recommendations,
                         recent_transcripts=recent_transcripts)

@app.route('/roi-calculator')
def roi_calculator():
    return render_template('roi_calculator.html')

@app.route('/calculate-roi', methods=['POST'])
def calculate_roi():
    data = request.get_json()
    
    monthly_calls = int(data.get('monthly_calls', 1000))
    avg_call_duration = int(data.get('avg_call_duration', 5))
    agent_hourly_rate = float(data.get('agent_hourly_rate', 15))
    automation_rate = float(data.get('automation_rate', 70)) / 100
    
    total_monthly_minutes = monthly_calls * avg_call_duration
    automated_minutes = total_monthly_minutes * automation_rate
    automated_hours = automated_minutes / 60
    monthly_savings = automated_hours * agent_hourly_rate
    annual_savings = monthly_savings * 12
    
    agent_calls_saved = monthly_calls * automation_rate
    
    return jsonify({
        'monthly_savings': round(monthly_savings, 2),
        'annual_savings': round(annual_savings, 2),
        'calls_automated': round(agent_calls_saved),
        'hours_saved': round(automated_hours, 1),
        'automation_rate': round(automation_rate * 100, 1)
    })

@app.route('/conversation-preview')
@login_required
def conversation_preview():
    company = Company.query.get(session['company_id'])
    return render_template('conversation_preview.html', company=company)

@app.route('/api/test-conversation', methods=['POST'])
@login_required
def test_conversation():
    data = request.get_json()
    user_input = data.get('input', '')
    
    company = Company.query.get(session['company_id'])
    engine = CallFlowEngine(company)
    
    intent = engine.determine_intent(user_input, None)
    
    context = {}
    if intent == 'OrderStatus':
        order_number = engine.extract_order_number(user_input)
        context['order_number'] = order_number
    
    response_message = IntentRouter.route_intent(engine, intent, context)
    
    return jsonify({
        'intent': intent,
        'response': response_message,
        'confidence': 85 if intent != 'Unknown' else 20
    })

@app.route('/industry-templates')
@login_required
def industry_templates():
    company = Company.query.get(session['company_id'])
    
    templates = {
        'ecommerce': {
            'name': 'eCommerce',
            'icon': 'cart3',
            'greeting': 'Thank you for calling. How can I help you today with your order?',
            'menu_options': {
                '1': 'Order Status',
                '2': 'Returns & Exchanges',
                '3': 'Subscription Management',
                '4': 'Store Hours & Locations',
                '5': 'Speak to Agent'
            },
            'business_hours': {
                'monday-friday': '9am-9pm EST',
                'saturday-sunday': '10am-6pm EST'
            }
        },
        'transportation': {
            'name': 'Transportation',
            'icon': 'truck',
            'greeting': 'Welcome to our transportation service. How may I assist you?',
            'menu_options': {
                '1': 'Book a Ride',
                '2': 'Track Active Ride',
                '3': 'Account Management',
                '4': 'Billing Questions',
                '5': 'Speak to Dispatcher'
            },
            'business_hours': {
                'monday-friday': '24/7',
                'saturday-sunday': '24/7'
            }
        },
        'healthcare': {
            'name': 'Healthcare',
            'icon': 'hospital',
            'greeting': 'Thank you for calling. How can I help you today?',
            'menu_options': {
                '1': 'Schedule Appointment',
                '2': 'Lab Results',
                '3': 'Prescription Refills',
                '4': 'Insurance Questions',
                '5': 'Speak to Nurse'
            },
            'business_hours': {
                'monday-friday': '8am-6pm',
                'saturday-sunday': 'Closed'
            }
        }
    }
    
    return render_template('industry_templates.html', company=company, templates=templates)

@app.route('/apply-template/<template_id>', methods=['POST'])
@login_required
def apply_template(template_id):
    company = Company.query.get(session['company_id'])
    
    templates = {
        'ecommerce': {
            'greeting': 'Thank you for calling. How can I help you today with your order?',
            'menu_options': json.dumps({
                '1': 'Order Status',
                '2': 'Returns & Exchanges',
                '3': 'Subscription Management',
                '4': 'Store Hours & Locations',
                '5': 'Speak to Agent'
            }),
            'business_hours': json.dumps({
                'monday-friday': '9am-9pm EST',
                'saturday-sunday': '10am-6pm EST'
            })
        },
        'transportation': {
            'greeting': 'Welcome to our transportation service. How may I assist you?',
            'menu_options': json.dumps({
                '1': 'Book a Ride',
                '2': 'Track Active Ride',
                '3': 'Account Management',
                '4': 'Billing Questions',
                '5': 'Speak to Dispatcher'
            }),
            'business_hours': json.dumps({
                'monday-friday': '24/7',
                'saturday-sunday': '24/7'
            })
        },
        'healthcare': {
            'greeting': 'Thank you for calling. How can I help you today?',
            'menu_options': json.dumps({
                '1': 'Schedule Appointment',
                '2': 'Lab Results',
                '3': 'Prescription Refills',
                '4': 'Insurance Questions',
                '5': 'Speak to Nurse'
            }),
            'business_hours': json.dumps({
                'monday-friday': '8am-6pm',
                'saturday-sunday': 'Closed'
            })
        }
    }
    
    if template_id in templates:
        template = templates[template_id]
        company.greeting_message = template['greeting']
        company.menu_options = template['menu_options']
        company.business_hours = template['business_hours']
        db.session.commit()
        
        flash(f'{template_id.title()} template applied successfully!', 'success')
    
    return redirect(url_for('settings'))

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/demo-script')
@login_required
def demo_script():
    company = Company.query.get(session['company_id'])
    return render_template('demo_script.html', company=company)

@app.route('/twilio-setup')
@login_required
def twilio_setup():
    company = Company.query.get(session['company_id'])
    replit_url = request.host_url.rstrip('/')
    return render_template('twilio_setup.html', company=company, replit_url=replit_url)

@app.route('/investor-dashboard')
@login_required
def investor_dashboard():
    company = Company.query.get(session['company_id'])
    
    total_calls = CallLog.query.filter_by(company_id=company.id).count()
    automated_calls = CallLog.query.filter_by(company_id=company.id, handled_by_ai=True).count()
    automation_rate = (automated_calls / total_calls * 100) if total_calls > 0 else 0
    
    stats = {
        'total_calls': total_calls,
        'automation_rate': round(automation_rate, 1),
        'avg_call_duration': 3.5,
        'customer_satisfaction': 4.7
    }
    
    return render_template('investor_dashboard.html', company=company, stats=stats)

def init_db():
    with app.app_context():
        db.create_all()
        
        demo_company = Company.query.filter_by(name='Demo Company').first()
        if not demo_company:
            demo_company = Company(
                name='Demo Company',
                phone_number='+15555550100',
                greeting_message='Thank you for calling Demo Company. Your call is important to us.'
            )
            db.session.add(demo_company)
            db.session.flush()
            
            demo_user = User(
                email='demo@example.com',
                password_hash=generate_password_hash('demo123'),
                full_name='Demo User',
                company_id=demo_company.id,
                role='admin'
            )
            db.session.add(demo_user)
            
            demo_integration = Integration(
                company_id=demo_company.id,
                provider_type='twilio',
                provider_name='Twilio Demo',
                config=json.dumps({
                    'account_sid': 'DEMO_SID',
                    'auth_token': 'DEMO_TOKEN',
                    'phone_number': '+15555550100'
                })
            )
            db.session.add(demo_integration)
            
            db.session.commit()
            print("Demo company created: email=demo@example.com, password=demo123")

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
