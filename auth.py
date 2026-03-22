"""
auth.py — Email/Password Authentication

Replaces replit_auth.py. Provides the same public interface:
  init_auth(app)   — configure Flask-Login and seed the demo account
  require_login    — decorator that redirects unauthenticated users to /login
  require_admin    — decorator that additionally checks is_admin flag

Uses Flask-Login for session management and Werkzeug for password hashing.
No external OAuth providers or environment-specific credentials required.
"""

import uuid
import logging
from functools import wraps

from flask import redirect, url_for, flash, request, session
from flask_login import LoginManager, current_user
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from models import db, User, Company

log = logging.getLogger(__name__)
login_manager = LoginManager()


def init_auth(app):
    """
    Configure Flask-Login and attach it to the Flask app.

    Also runs a lightweight DB migration to add the password_hash column
    if it doesn't already exist, then seeds a demo account so the app is
    usable immediately without a separate setup step.

    Args:
        app (Flask): The Flask application instance.
    """
    login_manager.init_app(app)

    # Flask-Login will redirect unauthenticated requests to the 'login' view
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        """Load a user from the DB by their string UUID primary key."""
        return db.session.get(User, user_id)

    with app.app_context():
        _add_password_hash_column()
        _ensure_demo_user()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _add_password_hash_column():
    """
    Add the password_hash column to the users table if it doesn't exist.

    Uses a raw SQL ALTER TABLE so this is safe to run on every startup —
    it silently does nothing if the column is already present.
    """
    try:
        db.session.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(256)"
        ))
        db.session.commit()
        log.info("password_hash column ensured on users table")
    except Exception as e:
        db.session.rollback()
        log.warning(f"Could not add password_hash column (may already exist): {e}")


def _ensure_demo_user():
    """
    Create a demo account and company if they don't already exist.

    Credentials:  demo@example.com / demo123
    The demo user is created as an admin so every dashboard feature is accessible.
    """
    try:
        demo = User.query.filter_by(email='demo@example.com').first()
        if demo:
            return  # Already exists — nothing to do

        # Create (or reuse) the demo company
        company = Company.query.filter_by(name='Demo Store').first()
        if not company:
            company = Company(
                name='Demo Store',
                is_active=True,
                greeting_message="Hi, thanks for calling Demo Store! How can I help you today?",
            )
            db.session.add(company)
            db.session.flush()  # get company.id before committing

        demo = User(
            id=str(uuid.uuid4()),
            email='demo@example.com',
            first_name='Demo',
            last_name='User',
            password_hash=generate_password_hash('demo123'),
            company_id=company.id,
            is_admin=True,
            role='admin',
            is_active=True,
        )
        db.session.add(demo)
        db.session.commit()
        log.info("Demo account created: demo@example.com / demo123")

    except Exception as e:
        db.session.rollback()
        log.warning(f"Could not create demo user: {e}")


# ---------------------------------------------------------------------------
# Access-control decorators — same interface as old replit_auth.py
# ---------------------------------------------------------------------------

def require_login(f):
    """
    Decorator: redirect to /login if the user is not authenticated.

    Saves the originally requested URL in the session so the user is sent
    back there after a successful login.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            session['next_url'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """
    Decorator: require both authentication and the is_admin flag.

    Redirects unauthenticated users to /login and non-admin users to the
    dashboard with a flash message.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            session['next_url'] = request.url
            return redirect(url_for('login'))
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated
