"""P.I.C Global Solutions web app (application factory)."""
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from flask import Flask, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from . import auth  # noqa: F401  (registers the Flask-Login user loader)
from . import cli, security, turnstile
from .extensions import db, login_manager, mail, migrate

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WHATSAPP_GREETING = "Hello P.I.C Global Solutions, I'd like to ask about your services."


def _env_flag(name, default):
    value = os.environ.get(name)
    return default if value is None else value.strip().lower() in ('1', 'true', 'yes', 'on')


def _load_config(app, test_config):
    env = os.environ.get
    app.config.update(
        SECRET_KEY=env('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI='sqlite:///contacts.db',  # lives in instance/
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=_env_flag('SESSION_COOKIE_SECURE', env('FLASK_DEBUG') != '1'),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),  # admin sessions expire after 8 hours

        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=env('MAIL_USERNAME'),
        MAIL_PASSWORD=env('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=env('MAIL_USERNAME'),
        AUTO_REPLY=_env_flag('AUTO_REPLY', True),

        GEMINI_API_KEY=env('GEMINI_API_KEY'),

        ADMIN_USERNAME=env('ADMIN_USERNAME') or 'admin',
        ADMIN_PASSWORD_HASH=env('ADMIN_PASSWORD_HASH'),
        DISPLAY_TIMEZONE=env('DISPLAY_TIMEZONE') or 'UTC',

        WHATSAPP_NUMBER=env('WHATSAPP_NUMBER'),
        BOOKING_URL=env('BOOKING_URL'),
        TURNSTILE_SITE_KEY=env('TURNSTILE_SITE_KEY'),
        TURNSTILE_SECRET_KEY=env('TURNSTILE_SECRET_KEY'),
    )
    if test_config:
        app.config.update(test_config)
    if not app.config['SECRET_KEY']:
        raise RuntimeError('SECRET_KEY is not set. Add it to .env (see DEPLOY.md).')


def _display_tz(app):
    try:
        return ZoneInfo(app.config['DISPLAY_TIMEZONE'])
    except (ZoneInfoNotFoundError, ValueError):
        app.logger.warning('Unknown DISPLAY_TIMEZONE %r; using UTC', app.config['DISPLAY_TIMEZONE'])
        return ZoneInfo('UTC')


def _register_template_helpers(app):
    tz = _display_tz(app)
    app.extensions['display_tz'] = tz

    @app.template_filter('localtime')
    def localtime(value, fmt='%d %b %Y, %H:%M'):
        if value is None:
            return '—'
        return value.replace(tzinfo=timezone.utc).astimezone(tz).strftime(fmt)

    @app.context_processor
    def inject_globals():
        number = re.sub(r'\D', '', app.config.get('WHATSAPP_NUMBER') or '')
        return {
            'current_year': datetime.now().year,
            'csrf_token': security.csrf_token,
            'booking_url': app.config.get('BOOKING_URL') or url_for('public.contact'),
            'whatsapp_url': f'https://wa.me/{number}?text={quote(WHATSAPP_GREETING)}' if number else None,
            'turnstile_site_key': app.config.get('TURNSTILE_SITE_KEY') if turnstile.enabled() else None,
        }


def create_app(test_config=None):
    load_dotenv(os.path.join(PROJECT_DIR, '.env'))  # absolute path so it works under WSGI too
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    app = Flask(
        __name__,
        instance_path=os.path.join(PROJECT_DIR, 'instance'),
        template_folder=os.path.join(PROJECT_DIR, 'templates'),
        static_folder=os.path.join(PROJECT_DIR, 'static'),
    )
    _load_config(app, test_config)
    os.makedirs(app.instance_path, exist_ok=True)

    # Hosts like PythonAnywhere sit behind one proxy; trust its X-Forwarded-For/-Proto
    # so rate limits see the visitor's IP and external links use https.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db, directory=os.path.join(PROJECT_DIR, 'migrations'))
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'
    login_manager.login_message = 'Please log in to continue.'
    login_manager.login_message_category = 'error'

    security.init_app(app)
    cli.init_app(app)
    _register_template_helpers(app)

    from . import admin, api, public
    app.register_blueprint(public.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(admin.bp)
    return app
