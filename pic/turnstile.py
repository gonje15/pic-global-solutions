"""Optional Cloudflare Turnstile spam check. Off unless TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY are set."""
import logging

import requests
from flask import current_app

log = logging.getLogger(__name__)

VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'


def enabled():
    return bool(current_app.config.get('TURNSTILE_SITE_KEY') and current_app.config.get('TURNSTILE_SECRET_KEY'))


def verify(token, remote_ip):
    if not enabled():
        return True
    if not token:
        return False
    try:
        resp = requests.post(VERIFY_URL, data={
            'secret': current_app.config['TURNSTILE_SECRET_KEY'],
            'response': token,
            'remoteip': remote_ip,
        }, timeout=5)
        return bool(resp.json().get('success'))
    except (requests.RequestException, ValueError):
        # If Cloudflare can't be reached (e.g. a host's outbound allowlist), don't block real customers;
        # the honeypot and rate limit still apply.
        log.warning('Turnstile verification unavailable; allowing submission', exc_info=True)
        return True
