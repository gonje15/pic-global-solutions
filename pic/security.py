"""CSRF protection, a small in-memory rate limiter, and security headers."""
import secrets
import threading
import time
from collections import defaultdict, deque

from flask import flash, jsonify, redirect, request, session

_hits = defaultdict(deque)
_hits_lock = threading.Lock()


def rate_limited(key, limit, window_seconds):
    """Return True if `key` has already made `limit` calls in the last window.

    In-memory, so it's per process: fine for PythonAnywhere's single worker.
    """
    now = time.monotonic()
    with _hits_lock:
        q = _hits[key]
        while q and now - q[0] > window_seconds:
            q.popleft()
        if len(q) >= limit:
            return True
        q.append(now)
        return False


def reset_rate_limits():
    with _hits_lock:
        _hits.clear()


def csrf_token():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_urlsafe(32)
    return session['_csrf']


def init_app(app):
    @app.before_request
    def check_csrf():
        if request.method != 'POST':
            return None
        sent = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        expected = session.get('_csrf')
        if not sent or not expected or not secrets.compare_digest(sent, expected):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Your session expired. Please refresh the page and try again.'}), 400
            flash('Your session expired. Please try again.', 'error')
            return redirect(request.path)
        return None

    @app.after_request
    def security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        if request.path.startswith('/admin'):
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        return response
