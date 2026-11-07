"""Public website pages and the contact form."""
import logging
import re

from flask import Blueprint, Response, abort, current_app, flash, redirect, render_template, request, url_for

from . import notifications, turnstile
from .content import SERVICES
from .extensions import db
from .models import CONTACT_LABELS, CONTACT_METHODS, SERVICE_CHOICES, SERVICE_LABELS, ContactSubmission
from .security import rate_limited

log = logging.getLogger(__name__)
bp = Blueprint('public', __name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
THANKS = "Thanks for reaching out! We'll be in touch soon."


@bp.route('/')
def home():
    return render_template('index.html')


@bp.route('/about')
def about():
    return render_template('about.html')


@bp.route('/why_us')
def why_us():
    return render_template('why_us.html')


@bp.route('/services')
def services():
    return render_template('services/index.html')


@bp.route('/services/<slug>')
def service_detail(slug):
    service = SERVICES.get(slug)
    if service is None:
        abort(404)
    return render_template('services/detail.html', service=service, slug=slug)


@bp.route('/privacy')
def privacy():
    return render_template('privacy.html')


@bp.route('/robots.txt')
def robots():
    return Response('User-agent: *\nDisallow: /admin\nDisallow: /api\n', mimetype='text/plain')


def _render_contact(form, status=200):
    return render_template(
        'contact.html', form=form, services=SERVICE_CHOICES, methods=CONTACT_METHODS,
    ), status


def _validate(data):
    problems = []
    if not data['name'] or len(data['name']) > 100:
        problems.append('Please enter your name (up to 100 characters).')
    if not EMAIL_RE.match(data['email']) or len(data['email']) > 120:
        problems.append('Please enter a valid email address.')
    if len(data['phone']) > 30:
        problems.append('Phone number is too long.')
    if data['service'] not in SERVICE_LABELS:
        problems.append('Please choose the service you are interested in.')
    if data['preferred_contact'] not in CONTACT_LABELS:
        problems.append('Please choose how you would like us to contact you.')
    elif data['preferred_contact'] in ('phone', 'whatsapp') and not data['phone']:
        problems.append(f'Please add a phone number so we can reach you by {CONTACT_LABELS[data["preferred_contact"]].lower()}.')
    if not data['message'] or len(data['message']) > 5000:
        problems.append('Please enter a message (up to 5000 characters).')
    if not data['consent']:
        problems.append('Please agree to us storing your details so we can reply.')
    return problems


@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'GET':
        service = request.args.get('service', '')
        return _render_contact({
            'service': service if service in SERVICE_LABELS else '',
            'preferred_contact': 'email',
        })

    ip = request.remote_addr
    # Honeypot: real visitors never see or fill the "website" field.
    if request.form.get('website'):
        log.info('Honeypot triggered from %s', ip)
        flash(THANKS, 'success')
        return redirect(url_for('public.contact'))

    if rate_limited(('contact', ip), limit=5, window_seconds=3600):
        flash('Too many messages from your connection. Please try again later.', 'error')
        return redirect(url_for('public.contact'))

    data = {k: (request.form.get(k) or '').strip()
            for k in ('name', 'email', 'phone', 'message', 'service', 'preferred_contact')}
    data['name'] = ' '.join(data['name'].split())  # no newlines (it goes into an email subject)
    data['consent'] = request.form.get('consent') == 'yes'

    if not turnstile.verify(request.form.get('cf-turnstile-response'), ip):
        flash('Please complete the spam check and try again.', 'error')
        return _render_contact(data, 400)

    problems = _validate(data)
    if problems:
        for p in problems:
            flash(p, 'error')
        return _render_contact(data, 400)

    sub = ContactSubmission(
        name=data['name'], email=data['email'], phone=data['phone'] or None, message=data['message'],
        service=data['service'], preferred_contact=data['preferred_contact'], consent=True,
    )
    db.session.add(sub)
    db.session.commit()

    notifications.notify_owner(sub)
    if current_app.config['AUTO_REPLY']:
        notifications.send_auto_reply(sub)

    flash(THANKS, 'success')
    return redirect(url_for('public.contact'))
