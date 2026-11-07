"""Emails sent when someone submits the contact form. Failures are logged, never shown to visitors."""
import logging

from flask import current_app, url_for
from flask_mail import Message

from .extensions import mail

log = logging.getLogger(__name__)


def _send(msg, what, submission_id):
    try:
        mail.send(msg)
        return True
    except Exception:
        log.exception('Failed to send %s for submission %s', what, submission_id)
        return False


def notify_owner(sub):
    owner = current_app.config.get('MAIL_USERNAME')
    if not owner:
        log.warning('MAIL_USERNAME is not set; skipping notification for submission %s', sub.id)
        return False
    link = url_for('admin.message_detail', submission_id=sub.id, _external=True)
    body = (
        f'New enquiry from {sub.name}\n\n'
        f'Service: {sub.service_label}\n'
        f'Preferred contact: {sub.contact_label}\n'
        f'Email: {sub.email}\n'
        f'Phone: {sub.phone or "-"}\n\n'
        f'{sub.message}\n\n'
        f'Open it in the admin dashboard: {link}\n'
    )
    msg = Message(
        subject=f'New enquiry: {sub.service_label} — {sub.name}',
        recipients=[owner],
        reply_to=sub.email,
        body=body,
    )
    return _send(msg, 'owner notification', sub.id)


def send_auto_reply(sub):
    if not current_app.config.get('MAIL_USERNAME'):
        return False
    first_name = sub.name.split()[0] if sub.name.split() else sub.name
    how = {
        'phone': ' by phone',
        'whatsapp': ' on WhatsApp',
    }.get(sub.preferred_contact, '')
    body = (
        f'Hi {first_name},\n\n'
        'Thank you for contacting P.I.C Global Solutions. '
        f"We've received your message and will get back to you{how} shortly.\n\n"
        "For your reference, here's what you sent:\n\n"
        f'{sub.message}\n\n'
        'Kind regards,\n'
        'P.I.C Global Solutions\n'
    )
    msg = Message(
        subject="We've received your message — P.I.C Global Solutions",
        recipients=[sub.email],
        body=body,
    )
    return _send(msg, 'auto-reply', sub.id)
