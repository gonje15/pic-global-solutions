"""Admin dashboard: login, overview, enquiry inbox, CSV export and AI-widget insights."""
import csv
import io
import logging
from collections import Counter
from datetime import datetime, time, timedelta, timezone

from flask import (Blueprint, Response, current_app, flash, redirect, render_template, request,
                   session, url_for)
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func, or_, select

from .auth import admin_configured, authenticate
from .extensions import db
from .models import (SERVICE_CHOICES, SERVICE_LABELS, STATUS_LABELS, STATUSES, Activity,
                     ContactSubmission, ServiceFitQuery, utcnow)
from .security import rate_limited

log = logging.getLogger(__name__)
bp = Blueprint('admin', __name__, url_prefix='/admin')

PER_PAGE = 25


@bp.before_request
def require_login():
    if request.endpoint == 'admin.login' or current_user.is_authenticated:
        return None
    nxt = request.full_path if request.method == 'GET' and request.query_string else request.path
    return redirect(url_for('admin.login', next=nxt))


@bp.context_processor
def inject_admin_globals():
    if not current_user.is_authenticated:
        return {}
    new_count = db.session.scalar(select(func.count()).where(ContactSubmission.status == 'new'))
    return {'new_count': new_count, 'status_labels': STATUS_LABELS}


# --- Auth ---
def _safe_next(target):
    return target if target and target.startswith('/admin') and not target.startswith('//') else None


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    status = 200
    if request.method == 'POST':
        if rate_limited(('admin-login', request.remote_addr), limit=5, window_seconds=900):
            flash('Too many login attempts. Please wait 15 minutes and try again.', 'error')
            return render_template('admin/login.html', configured=admin_configured()), 429
        user = authenticate(request.form.get('username', ''), request.form.get('password', ''))
        if user:
            session.permanent = True
            login_user(user)
            log.info('Admin login from %s', request.remote_addr)
            return redirect(_safe_next(request.args.get('next')) or url_for('admin.dashboard'))
        log.warning('Failed admin login from %s', request.remote_addr)
        flash('Incorrect username or password.', 'error')
        status = 401
    return render_template('admin/login.html', configured=admin_configured()), status


@bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin.login'))


# --- Overview ---
def _tz():
    return current_app.extensions['display_tz']


def _to_utc(local_dt):
    return local_dt.astimezone(timezone.utc).replace(tzinfo=None)


def _local_week_start(weeks_ago=0):
    """Monday 00:00 (display timezone) of the current week, minus `weeks_ago` weeks, as naive UTC."""
    today = datetime.now(_tz()).date()
    monday = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks_ago)
    return _to_utc(datetime.combine(monday, time.min, tzinfo=_tz()))


def _count(*conditions):
    return db.session.scalar(select(func.count(ContactSubmission.id)).where(*conditions)) or 0


@bp.route('/')
def dashboard():
    this_week = _local_week_start(0)
    last_week = _local_week_start(1)

    by_status = dict(db.session.execute(
        select(ContactSubmission.status, func.count()).group_by(ContactSubmission.status)).all())
    by_service_raw = dict(db.session.execute(
        select(ContactSubmission.service, func.count()).group_by(ContactSubmission.service)).all())
    by_service = [(label, by_service_raw.get(key, 0)) for key, label in SERVICE_CHOICES]
    if by_service_raw.get(None):
        by_service.append(('Not specified', by_service_raw[None]))

    # Average time to first response over the last 90 days.
    responded = db.session.execute(
        select(ContactSubmission.submitted_at, ContactSubmission.contacted_at).where(
            ContactSubmission.contacted_at.is_not(None),
            ContactSubmission.submitted_at >= utcnow() - timedelta(days=90),
        )).all()
    durations = [(c - s).total_seconds() / 3600 for s, c in responded if s and c and c >= s]
    avg_response_hours = sum(durations) / len(durations) if durations else None

    won, lost = by_status.get('won', 0), by_status.get('lost', 0)
    win_rate = round(100 * won / (won + lost)) if won + lost else None

    # Enquiries per week for the last 12 weeks (weeks start on Monday, display timezone).
    starts = [_local_week_start(i) for i in range(11, -1, -1)]
    stamps = db.session.scalars(
        select(ContactSubmission.submitted_at).where(ContactSubmission.submitted_at >= starts[0])).all()
    weekly = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else None
        n = sum(1 for t in stamps if t and t >= start and (end is None or t < end))
        label = start.replace(tzinfo=timezone.utc).astimezone(_tz()).strftime('%d %b')
        weekly.append((label, n))

    month_ago = utcnow() - timedelta(days=30)
    ai_queries = db.session.scalars(
        select(ServiceFitQuery.suggested).where(ServiceFitQuery.created_at >= month_ago)).all()
    ai_counts = Counter(k for s in ai_queries for k in (s or '').split(',') if k)

    recent = db.session.scalars(
        select(ContactSubmission).order_by(ContactSubmission.submitted_at.desc()).limit(5)).all()

    return render_template(
        'admin/dashboard.html',
        total=sum(by_status.values()),
        by_status=[(label, by_status.get(key, 0), key) for key, label in STATUSES],
        new=by_status.get('new', 0),
        this_week=_count(ContactSubmission.submitted_at >= this_week),
        last_week=_count(ContactSubmission.submitted_at >= last_week, ContactSubmission.submitted_at < this_week),
        avg_response_hours=avg_response_hours,
        win_rate=win_rate,
        weekly=weekly,
        by_service=by_service,
        ai_total=len(ai_queries),
        ai_by_service=[(SERVICE_LABELS[k], ai_counts.get(k, 0)) for k, _ in SERVICE_CHOICES if k != 'not_sure'],
        recent=recent,
    )


# --- Inbox ---
def _filters():
    return {
        'status': request.args.get('status', ''),
        'service': request.args.get('service', ''),
        'q': request.args.get('q', '').strip(),
    }


def _filtered_query(f):
    stmt = select(ContactSubmission)
    if f['status'] in STATUS_LABELS:
        stmt = stmt.where(ContactSubmission.status == f['status'])
    if f['service'] in SERVICE_LABELS:
        stmt = stmt.where(ContactSubmission.service == f['service'])
    elif f['service'] == 'none':
        stmt = stmt.where(ContactSubmission.service.is_(None))
    if f['q']:
        like = f"%{f['q']}%"
        stmt = stmt.where(or_(
            ContactSubmission.name.ilike(like), ContactSubmission.email.ilike(like),
            ContactSubmission.phone.ilike(like), ContactSubmission.message.ilike(like),
        ))
    return stmt.order_by(ContactSubmission.submitted_at.desc(), ContactSubmission.id.desc())


@bp.route('/messages')
def messages():
    f = _filters()
    page = db.paginate(_filtered_query(f), page=request.args.get('page', 1, type=int),
                       per_page=PER_PAGE, error_out=False)
    return render_template('admin/messages.html', page=page, filters=f,
                           statuses=STATUSES, services=SERVICE_CHOICES)


def _csv_safe(value):
    """Stop spreadsheet apps from treating user text as a formula (CSV injection)."""
    text = '' if value is None else str(value)
    return "'" + text if text[:1] in ('=', '+', '-', '@', '\t', '\r') else text


@bp.route('/messages/export.csv')
def export_csv():
    rows = db.session.scalars(_filtered_query(_filters())).all()
    fmt = current_app.jinja_env.filters['localtime']
    out = io.StringIO()
    out.write('﻿')  # BOM so Excel opens UTF-8 correctly
    writer = csv.writer(out)
    writer.writerow(['ID', 'Submitted', 'Name', 'Email', 'Phone', 'Service', 'Preferred contact',
                     'Status', 'First contacted', 'Message'])
    for s in rows:
        writer.writerow([_csv_safe(v) for v in (
            s.id, fmt(s.submitted_at), s.name, s.email, s.phone, s.service_label, s.contact_label,
            s.status_label, fmt(s.contacted_at) if s.contacted_at else '', s.message)])
    filename = f'enquiries-{utcnow():%Y%m%d}.csv'
    return Response(out.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})


@bp.route('/messages/<int:submission_id>')
def message_detail(submission_id):
    sub = db.get_or_404(ContactSubmission, submission_id)
    return render_template('admin/message_detail.html', sub=sub, statuses=STATUSES)


@bp.route('/messages/<int:submission_id>/status', methods=['POST'])
def update_status(submission_id):
    sub = db.get_or_404(ContactSubmission, submission_id)
    new = request.form.get('status')
    if new not in STATUS_LABELS:
        flash('Unknown status.', 'error')
    elif new != sub.status:
        db.session.add(Activity(submission=sub, kind='status', from_status=sub.status, to_status=new,
                                author=current_user.id))
        if sub.contacted_at is None and new != 'new':
            sub.contacted_at = utcnow()
        sub.status = new
        db.session.commit()
        flash(f'Status changed to {STATUS_LABELS[new]}.', 'success')
    return redirect(url_for('admin.message_detail', submission_id=sub.id))


@bp.route('/messages/<int:submission_id>/notes', methods=['POST'])
def add_note(submission_id):
    sub = db.get_or_404(ContactSubmission, submission_id)
    body = (request.form.get('body') or '').strip()
    if not body or len(body) > 5000:
        flash('Notes must be between 1 and 5000 characters.', 'error')
    else:
        db.session.add(Activity(submission=sub, kind='note', body=body, author=current_user.id))
        db.session.commit()
        flash('Note added.', 'success')
    return redirect(url_for('admin.message_detail', submission_id=sub.id))


@bp.route('/messages/<int:submission_id>/delete', methods=['POST'])
def delete_message(submission_id):
    sub = db.get_or_404(ContactSubmission, submission_id)
    db.session.delete(sub)
    db.session.commit()
    log.info('Admin %s deleted submission %s', current_user.id, submission_id)
    flash('Enquiry deleted.', 'success')
    return redirect(url_for('admin.messages'))


# --- AI widget insights ---
@bp.route('/insights')
def insights():
    page = db.paginate(select(ServiceFitQuery).order_by(ServiceFitQuery.created_at.desc()),
                       page=request.args.get('page', 1, type=int), per_page=PER_PAGE, error_out=False)
    all_suggested = db.session.scalars(select(ServiceFitQuery.suggested)).all()
    counts = Counter(k for s in all_suggested for k in (s or '').split(',') if k)
    by_service = [(SERVICE_LABELS[k], counts.get(k, 0)) for k, _ in SERVICE_CHOICES if k != 'not_sure']
    return render_template('admin/insights.html', page=page, by_service=by_service,
                           total=len(all_suggested))
