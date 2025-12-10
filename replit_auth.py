import jwt
import os
import uuid
from functools import wraps
from urllib.parse import urlencode

from flask import g, session, redirect, request, url_for, flash
from flask_dance.consumer import (
    OAuth2ConsumerBlueprint,
    oauth_authorized,
    oauth_error,
)
from flask_dance.consumer.storage import BaseStorage
from flask_login import LoginManager, login_user, logout_user, current_user
from sqlalchemy.exc import NoResultFound

from models import db, OAuth, User, Company

login_manager = None
replit_blueprint = None

def init_auth(app):
    global login_manager, replit_blueprint
    
    login_manager = LoginManager(app)
    login_manager.login_view = 'replit_auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, user_id)
    
    replit_blueprint = make_replit_blueprint()
    app.register_blueprint(replit_blueprint, url_prefix="/auth")
    
    return replit_blueprint


class UserSessionStorage(BaseStorage):
    def get(self, blueprint):
        try:
            token = db.session.query(OAuth).filter_by(
                user_id=current_user.get_id(),
                browser_session_key=g.browser_session_key,
                provider=blueprint.name,
            ).one().token
        except NoResultFound:
            token = None
        return token

    def set(self, blueprint, token):
        db.session.query(OAuth).filter_by(
            user_id=current_user.get_id(),
            browser_session_key=g.browser_session_key,
            provider=blueprint.name,
        ).delete()
        new_model = OAuth()
        new_model.user_id = current_user.get_id()
        new_model.browser_session_key = g.browser_session_key
        new_model.provider = blueprint.name
        new_model.token = token
        db.session.add(new_model)
        db.session.commit()

    def delete(self, blueprint):
        db.session.query(OAuth).filter_by(
            user_id=current_user.get_id(),
            browser_session_key=g.browser_session_key,
            provider=blueprint.name
        ).delete()
        db.session.commit()


def make_replit_blueprint():
    try:
        repl_id = os.environ['REPL_ID']
    except KeyError:
        raise SystemExit("the REPL_ID environment variable must be set")

    issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")

    replit_bp = OAuth2ConsumerBlueprint(
        "replit_auth",
        __name__,
        client_id=repl_id,
        client_secret=None,
        base_url=issuer_url,
        authorization_url_params={
            "prompt": "login consent",
        },
        token_url=issuer_url + "/token",
        token_url_params={
            "auth": (),
            "include_client_id": True,
        },
        auto_refresh_url=issuer_url + "/token",
        auto_refresh_kwargs={
            "client_id": repl_id,
        },
        authorization_url=issuer_url + "/auth",
        use_pkce=True,
        code_challenge_method="S256",
        scope=["openid", "profile", "email", "offline_access"],
        storage=UserSessionStorage(),
    )

    @replit_bp.before_app_request
    def set_applocal_session():
        if '_browser_session_key' not in session:
            session['_browser_session_key'] = uuid.uuid4().hex
        session.modified = True
        g.browser_session_key = session['_browser_session_key']
        g.flask_dance_replit = replit_bp.session

    @replit_bp.route("/logout")
    def logout():
        try:
            del replit_bp.token
        except:
            pass
        logout_user()
        session.clear()

        end_session_endpoint = issuer_url + "/session/end"
        encoded_params = urlencode({
            "client_id": repl_id,
            "post_logout_redirect_uri": request.url_root,
        })
        logout_url = f"{end_session_endpoint}?{encoded_params}"

        return redirect(logout_url)

    return replit_bp


def save_user(user_claims):
    user = db.session.get(User, user_claims['sub'])
    
    if user is None:
        user = User()
        user.id = user_claims['sub']
        
        existing_users = User.query.count()
        user.is_admin = (existing_users == 0)
        
        default_company = Company(
            name=f"{user_claims.get('first_name', 'My')} Company",
            greeting_message="Hi there! How can I help you today?",
            menu_options='{"1": "Order Status", "2": "Store Hours", "3": "Speak to Agent"}',
            business_hours='{"monday-friday": "9am-5pm", "saturday-sunday": "Closed"}'
        )
        db.session.add(default_company)
        db.session.flush()
        user.company_id = default_company.id
    
    user.email = user_claims.get('email')
    user.first_name = user_claims.get('first_name')
    user.last_name = user_claims.get('last_name')
    user.profile_image_url = user_claims.get('profile_image_url')
    
    db.session.add(user)
    db.session.commit()
    return user


@oauth_authorized.connect
def logged_in(blueprint, token):
    user_claims = jwt.decode(token['id_token'], options={"verify_signature": False})
    user = save_user(user_claims)
    login_user(user)
    blueprint.token = token
    
    session['company_id'] = user.company_id
    
    flash(f'Welcome, {user.full_name}!', 'success')
    
    next_url = session.pop("next_url", None)
    if next_url is not None:
        return redirect(next_url)
    return redirect(url_for('dashboard'))


@oauth_error.connect
def handle_error(blueprint, error, error_description=None, error_uri=None):
    flash('Authentication failed. Please try again.', 'danger')
    return redirect(url_for('index'))


def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = get_next_navigation_url(request)
            return redirect(url_for('replit_auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = get_next_navigation_url(request)
            return redirect(url_for('replit_auth.login'))
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def get_next_navigation_url(request):
    is_navigation_url = request.headers.get('Sec-Fetch-Mode') == 'navigate' and \
                        request.headers.get('Sec-Fetch-Dest') == 'document'
    if is_navigation_url:
        return request.url
    return request.referrer or request.url
