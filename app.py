from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from models import db, Company, User, Integration, CallLog, Voicemail
from providers import get_provider
from call_engine import CallFlowEngine, IntentRouter
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
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
        
        company = Company(name=company_name)
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
        'intents': intent_data,
        'daily_calls': {
            'labels': last_7_days,
            'data': daily_calls
        }
    })

@app.route('/voice/webhook', methods=['POST'])
def voice_webhook():
    from_number = request.values.get('From', request.values.get('from', 'Unknown'))
    to_number = request.values.get('To', request.values.get('to', ''))
    call_sid = request.values.get('CallSid', f'SIM_{datetime.utcnow().timestamp()}')
    
    company = get_company_by_phone(to_number)
    
    if not company:
        company = Company.query.filter_by(is_active=True).first()
    
    if not company:
        return "No active company found", 404
    
    integration = Integration.query.filter_by(company_id=company.id, is_active=True).first()
    provider_type = integration.provider_type if integration else 'twilio'
    provider_config = integration.get_config() if integration else None
    
    provider = get_provider(provider_type, provider_config)
    engine = CallFlowEngine(company)
    
    session_key = f'call_state_{call_sid}'
    if session_key not in session:
        engine.log_call(from_number, call_sid, None, 'in_progress', provider_type=provider_type)
        session[session_key] = {'step': 'greeting'}
    
    greeting_with_menu = engine.get_greeting_with_menu()
    response = provider.create_gather_response(
        greeting_with_menu,
        url_for('voice_handle_input', _external=True),
        input_type='both'
    )
    
    return response, 200, {'Content-Type': 'text/xml' if provider_type != 'sip' else 'application/json'}

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
