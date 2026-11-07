import csv
import io
from datetime import timedelta

from pic.extensions import db
from pic.models import Activity, ContactSubmission, ServiceFitQuery, utcnow

from .conftest import csrf


def make_sub(**kw):
    data = dict(name='Jane Banda', email='jane@example.com', message='Need cement', service='supply',
                preferred_contact='email', consent=True)
    data.update(kw)
    sub = ContactSubmission(**data)
    db.session.add(sub)
    db.session.commit()
    return sub


def test_admin_requires_login(client):
    for path in ['/admin/', '/admin/messages', '/admin/insights', '/admin/messages/export.csv']:
        resp = client.get(path)
        assert resp.status_code == 302 and '/admin/login' in resp.headers['Location']


def test_login_redirects_back_to_requested_page(client):
    tok = csrf(client, '/admin/login')
    resp = client.post('/admin/login?next=/admin/insights',
                       data={'csrf_token': tok, 'username': 'admin', 'password': 'correct-horse-battery'})
    assert resp.headers['Location'].endswith('/admin/insights')


def test_login_ignores_offsite_next(client):
    tok = csrf(client, '/admin/login')
    resp = client.post('/admin/login?next=https://evil.example',
                       data={'csrf_token': tok, 'username': 'admin', 'password': 'correct-horse-battery'})
    assert resp.headers['Location'].endswith('/admin/')


def test_wrong_password_rejected(client):
    tok = csrf(client, '/admin/login')
    resp = client.post('/admin/login', data={'csrf_token': tok, 'username': 'admin', 'password': 'nope'})
    assert resp.status_code == 401
    assert client.get('/admin/').status_code == 302


def test_login_rate_limited(client):
    tok = csrf(client, '/admin/login')
    for _ in range(5):
        client.post('/admin/login', data={'csrf_token': tok, 'username': 'admin', 'password': 'nope'})
    resp = client.post('/admin/login', data={'csrf_token': tok, 'username': 'admin', 'password': 'correct-horse-battery'})
    assert resp.status_code == 429


def test_login_page_explains_setup_when_no_password(app, client):
    app.config['ADMIN_PASSWORD_HASH'] = None
    assert 'hash-password' in client.get('/admin/login').get_data(as_text=True)


def test_admin_pages_are_not_cached(admin):
    resp = admin.get('/admin/')
    assert resp.headers['Cache-Control'] == 'no-store'
    assert 'noindex' in resp.headers['X-Robots-Tag']


def test_dashboard_stats(admin):
    make_sub()
    s2 = make_sub(name='Peter', service='marketing', status='won', contacted_at=utcnow())
    s2.submitted_at = utcnow() - timedelta(hours=5)
    make_sub(name='Old', status='lost', contacted_at=utcnow())
    db.session.add(ServiceFitQuery(description='x', recommendation='Supply of Goods', suggested='supply'))
    db.session.commit()
    html = admin.get('/admin/').get_data(as_text=True)
    assert 'Awaiting reply' in html
    assert '50<span' in html  # win rate: 1 won / (1 won + 1 lost)
    assert 'Enquiries per week' in html and 'Peter' in html


def test_dashboard_empty_state(admin):
    html = admin.get('/admin/').get_data(as_text=True)
    assert 'No enquiries in the last 12 weeks' in html


def test_inbox_filters_and_search(admin):
    make_sub(name='Alice Supply')
    make_sub(name='Bob Marketing', service='marketing', status='contacted')
    html = admin.get('/admin/messages?service=marketing').get_data(as_text=True)
    assert 'Bob Marketing' in html and 'Alice Supply' not in html
    html = admin.get('/admin/messages?q=alice').get_data(as_text=True)
    assert 'Alice Supply' in html and 'Bob Marketing' not in html
    html = admin.get('/admin/messages?status=contacted').get_data(as_text=True)
    assert 'Bob Marketing' in html and 'Alice Supply' not in html


def test_status_change_records_history_and_first_contact(admin):
    sub = make_sub()
    resp = admin.post(f'/admin/messages/{sub.id}/status', data={'csrf_token': admin.csrf, 'status': 'contacted'})
    assert resp.status_code == 302
    db.session.refresh(sub)
    assert sub.status == 'contacted' and sub.contacted_at is not None
    first_contact = sub.contacted_at
    admin.post(f'/admin/messages/{sub.id}/status', data={'csrf_token': admin.csrf, 'status': 'won'})
    db.session.refresh(sub)
    assert sub.contacted_at == first_contact  # stays the first response time
    kinds = [(a.from_status, a.to_status) for a in db.session.scalars(db.select(Activity).order_by(Activity.id))]
    assert kinds == [('new', 'contacted'), ('contacted', 'won')]


def test_invalid_status_rejected(admin):
    sub = make_sub()
    admin.post(f'/admin/messages/{sub.id}/status', data={'csrf_token': admin.csrf, 'status': 'hacked'})
    db.session.refresh(sub)
    assert sub.status == 'new'


def test_notes(admin):
    sub = make_sub()
    admin.post(f'/admin/messages/{sub.id}/notes', data={'csrf_token': admin.csrf, 'body': 'Called, quote on Friday'})
    html = admin.get(f'/admin/messages/{sub.id}').get_data(as_text=True)
    assert 'Called, quote on Friday' in html


def test_admin_post_requires_csrf(admin):
    sub = make_sub()
    admin.post(f'/admin/messages/{sub.id}/status', data={'status': 'won'})
    db.session.refresh(sub)
    assert sub.status == 'new'


def test_delete_removes_enquiry_and_notes(admin):
    sub = make_sub()
    admin.post(f'/admin/messages/{sub.id}/notes', data={'csrf_token': admin.csrf, 'body': 'note'})
    admin.post(f'/admin/messages/{sub.id}/delete', data={'csrf_token': admin.csrf})
    assert db.session.scalar(db.select(db.func.count(ContactSubmission.id))) == 0
    assert db.session.scalar(db.select(db.func.count(Activity.id))) == 0
    assert admin.get(f'/admin/messages/{sub.id}').status_code == 404


def test_csv_export_escapes_formulas(admin):
    make_sub(name='=HYPERLINK("http://evil")')
    resp = admin.get('/admin/messages/export.csv')
    assert resp.mimetype == 'text/csv'
    rows = list(csv.reader(io.StringIO(resp.get_data(as_text=True).lstrip('﻿'))))
    assert rows[0][0] == 'ID'
    assert rows[1][2].startswith("'=")


def test_insights_page(admin):
    db.session.add(ServiceFitQuery(description='Need suppliers for cement', recommendation='Supply of Goods',
                                   suggested='supply'))
    db.session.add(ServiceFitQuery(description='Broken', ok=False))
    db.session.commit()
    html = admin.get('/admin/insights').get_data(as_text=True)
    assert 'Need suppliers for cement' in html and 'failed to answer' in html


def test_logout(admin):
    admin.post('/admin/logout', data={'csrf_token': admin.csrf})
    assert admin.get('/admin/').status_code == 302
