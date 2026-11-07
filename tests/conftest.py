import re

import pytest
from werkzeug.security import generate_password_hash

from pic import create_app
from pic.extensions import db
from pic.security import reset_rate_limits

ADMIN_PASSWORD = 'correct-horse-battery'


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret',
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',  # in-memory
        'SESSION_COOKIE_SECURE': False,
        'SERVER_NAME': 'localhost',
        'MAIL_USERNAME': 'owner@example.com',
        'MAIL_DEFAULT_SENDER': 'owner@example.com',
        'GEMINI_API_KEY': 'fake',
        'ADMIN_USERNAME': 'admin',
        'ADMIN_PASSWORD_HASH': generate_password_hash(ADMIN_PASSWORD),
        'AUTO_REPLY': True,
        'WHATSAPP_NUMBER': None,
        'BOOKING_URL': None,
        'TURNSTILE_SITE_KEY': None,
        'TURNSTILE_SECRET_KEY': None,
        'DISPLAY_TIMEZONE': 'UTC',
    })
    with app.app_context():
        db.create_all()
        reset_rate_limits()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def csrf(client, path='/contact'):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)


@pytest.fixture
def token(client):
    return csrf(client)


@pytest.fixture
def admin(client):
    """A client that is logged in to the admin area."""
    tok = csrf(client, '/admin/login')
    resp = client.post('/admin/login', data={'csrf_token': tok, 'username': 'admin', 'password': ADMIN_PASSWORD})
    assert resp.status_code == 302, resp.get_data(as_text=True)
    client.csrf = tok
    return client


VALID_CONTACT = {
    'name': 'Jane Banda',
    'email': 'jane@example.com',
    'phone': '+265 991 234 567',
    'service': 'supply',
    'preferred_contact': 'whatsapp',
    'message': 'We need cement and roofing sheets every month.',
    'consent': 'yes',
}
