from unittest import mock

import pytest

from pic import gemini
from pic.extensions import db, mail
from pic.models import ContactSubmission, ServiceFitQuery

from .conftest import VALID_CONTACT


@pytest.mark.parametrize('path', [
    '/', '/about', '/contact', '/why_us', '/services', '/privacy',
    '/services/supply', '/services/consultancy', '/services/marketing',
])
def test_pages_render(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert resp.headers['X-Content-Type-Options'] == 'nosniff'


def test_unknown_service_is_404(client):
    assert client.get('/services/nope').status_code == 404


def test_robots_hides_admin(client):
    assert 'Disallow: /admin' in client.get('/robots.txt').get_data(as_text=True)


def test_contact_prefills_service_from_query(client):
    html = client.get('/contact?service=marketing').get_data(as_text=True)
    assert '<option value="marketing" selected>' in html


def test_contact_saves_and_emails_owner_and_visitor(client, token):
    with mail.record_messages() as outbox:
        resp = client.post('/contact', data={**VALID_CONTACT, 'csrf_token': token})
    assert resp.status_code == 302
    sub = db.session.scalar(db.select(ContactSubmission))
    assert sub.name == 'Jane Banda' and sub.service == 'supply' and sub.preferred_contact == 'whatsapp'
    assert sub.status == 'new' and sub.consent is True
    assert [m.recipients for m in outbox] == [['owner@example.com'], ['jane@example.com']]
    assert '/admin/messages/' in outbox[0].body
    assert 'on WhatsApp' in outbox[1].body


def test_auto_reply_can_be_turned_off(app, client, token):
    app.config['AUTO_REPLY'] = False
    with mail.record_messages() as outbox:
        client.post('/contact', data={**VALID_CONTACT, 'csrf_token': token})
    assert len(outbox) == 1


def test_mail_failure_still_thanks_visitor(client, token):
    with mock.patch.object(mail, 'send', side_effect=OSError('smtp down')):
        resp = client.post('/contact', data={**VALID_CONTACT, 'csrf_token': token}, follow_redirects=True)
    assert "Thanks for reaching out" in resp.get_data(as_text=True)
    assert db.session.scalar(db.select(db.func.count(ContactSubmission.id))) == 1


@pytest.mark.parametrize('override, error', [
    ({'consent': ''}, 'agree to us storing'),
    ({'email': 'not-an-email'}, 'valid email'),
    ({'service': ''}, 'choose the service'),
    ({'phone': '', 'preferred_contact': 'whatsapp'}, 'add a phone number'),
    ({'message': ''}, 'enter a message'),
])
def test_contact_validation(client, token, override, error):
    resp = client.post('/contact', data={**VALID_CONTACT, **override, 'csrf_token': token})
    assert resp.status_code == 400
    html = resp.get_data(as_text=True)
    assert error in html
    assert 'Jane Banda' in html  # keeps what the visitor typed
    assert db.session.scalar(db.select(db.func.count(ContactSubmission.id))) == 0


def test_contact_requires_csrf(client):
    resp = client.post('/contact', data=VALID_CONTACT)
    assert resp.status_code == 302
    assert db.session.scalar(db.select(db.func.count(ContactSubmission.id))) == 0


def test_honeypot_is_silently_dropped(client, token):
    client.post('/contact', data={**VALID_CONTACT, 'website': 'http://spam', 'csrf_token': token})
    assert db.session.scalar(db.select(db.func.count(ContactSubmission.id))) == 0


def test_contact_rate_limit(client, token):
    for _ in range(5):
        client.post('/contact', data={**VALID_CONTACT, 'csrf_token': token})
    resp = client.post('/contact', data={**VALID_CONTACT, 'csrf_token': token}, follow_redirects=True)
    assert 'Too many messages' in resp.get_data(as_text=True)
    assert db.session.scalar(db.select(db.func.count(ContactSubmission.id))) == 5


def test_booking_and_whatsapp_links_when_configured(app, client):
    app.config['BOOKING_URL'] = 'https://cal.example.com/pic'
    app.config['WHATSAPP_NUMBER'] = '+265 991 234 567'
    html = client.get('/').get_data(as_text=True)
    assert 'href="https://cal.example.com/pic"' in html
    assert 'https://wa.me/265991234567' in html


def test_service_fit_records_query(client, token):
    answer = 'I recommend our Supply of Goods service for reliable sourcing.'
    with mock.patch.object(gemini, 'ask_gemini', return_value=answer):
        resp = client.post('/api/service-fit', json={'description': 'Hardware shop needs cement'},
                           headers={'X-CSRF-Token': token})
    assert resp.status_code == 200 and resp.json['recommendation'] == answer
    q = db.session.scalar(db.select(ServiceFitQuery))
    assert q.suggested == 'supply' and q.ok


def test_service_fit_failure_is_logged_and_503(client, token):
    with mock.patch.object(gemini, 'ask_gemini', return_value=None):
        resp = client.post('/api/service-fit', json={'description': 'x'}, headers={'X-CSRF-Token': token})
    assert resp.status_code == 503
    assert db.session.scalar(db.select(ServiceFitQuery)).ok is False


@pytest.mark.parametrize('body', ['null', '[1]', '"text"'])
def test_service_fit_rejects_bad_json(client, token, body):
    resp = client.post('/api/service-fit', data=body, content_type='application/json',
                       headers={'X-CSRF-Token': token})
    assert resp.status_code == 400


def test_service_fit_requires_csrf(client):
    assert client.post('/api/service-fit', json={'description': 'x'}).status_code == 400


def test_detect_services():
    assert gemini.detect_services('Our Business Consultancy & Advisory and Marketing teams') == ['consultancy', 'marketing']
    assert gemini.detect_services(None) == []
