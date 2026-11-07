import re
from datetime import datetime, timezone

import sqlalchemy as sa

from .extensions import db

SERVICE_CHOICES = [
    ('supply', 'Supply of Goods'),
    ('consultancy', 'Business Consultancy & Advisory'),
    ('marketing', 'Marketing & Business Development'),
    ('not_sure', 'Not sure yet'),
]
CONTACT_METHODS = [
    ('email', 'Email'),
    ('phone', 'Phone call'),
    ('whatsapp', 'WhatsApp'),
]
STATUSES = [
    ('new', 'New'),
    ('contacted', 'Contacted'),
    ('won', 'Won'),
    ('lost', 'Lost'),
]
SERVICE_LABELS = dict(SERVICE_CHOICES)
CONTACT_LABELS = dict(CONTACT_METHODS)
STATUS_LABELS = dict(STATUSES)


def utcnow():
    """Naive UTC timestamp. SQLite has no timezone support, so everything is stored as UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ContactSubmission(db.Model):
    __tablename__ = 'contact_submission'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=utcnow, index=True)

    service = db.Column(db.String(30))
    preferred_contact = db.Column(db.String(20))
    consent = db.Column(db.Boolean, nullable=False, default=False, server_default=sa.false())
    status = db.Column(db.String(20), nullable=False, default='new', server_default='new', index=True)
    contacted_at = db.Column(db.DateTime)  # first time it left "new"; used for response-time stats
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    activities = db.relationship(
        'Activity', backref='submission', cascade='all, delete-orphan',
        order_by='Activity.created_at.desc()',
    )

    @property
    def service_label(self):
        return SERVICE_LABELS.get(self.service, 'Not specified')

    @property
    def contact_label(self):
        return CONTACT_LABELS.get(self.preferred_contact, 'Email')

    @property
    def status_label(self):
        return STATUS_LABELS.get(self.status, self.status)

    @property
    def whatsapp_link(self):
        digits = re.sub(r'\D', '', self.phone or '')
        return f'https://wa.me/{digits}' if len(digits) >= 8 else None


class Activity(db.Model):
    """Timeline entry on an enquiry: a status change or an internal note."""
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(
        db.Integer, db.ForeignKey('contact_submission.id', ondelete='CASCADE'), nullable=False, index=True,
    )
    kind = db.Column(db.String(20), nullable=False)  # 'status' or 'note'
    from_status = db.Column(db.String(20))
    to_status = db.Column(db.String(20))
    body = db.Column(db.Text)
    author = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class ServiceFitQuery(db.Model):
    """One use of the 'which service fits me?' widget."""
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    recommendation = db.Column(db.Text)
    suggested = db.Column(db.String(60))  # comma-separated service keys found in the answer
    ok = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    @property
    def suggested_labels(self):
        return [SERVICE_LABELS.get(k, k) for k in (self.suggested or '').split(',') if k]
