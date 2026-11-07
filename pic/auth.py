"""Single admin account, configured with ADMIN_USERNAME and ADMIN_PASSWORD_HASH in .env."""
import secrets

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash

from .extensions import login_manager


class AdminUser(UserMixin):
    def __init__(self, username):
        self.id = username


def admin_configured():
    return bool(current_app.config.get('ADMIN_PASSWORD_HASH'))


@login_manager.user_loader
def load_user(user_id):
    if admin_configured() and user_id == current_app.config['ADMIN_USERNAME']:
        return AdminUser(user_id)
    return None


def authenticate(username, password):
    if not admin_configured():
        return None
    expected = current_app.config['ADMIN_USERNAME']
    user_ok = secrets.compare_digest(username.encode(), expected.encode())
    try:
        # Always check the password, even for a wrong username, so timing doesn't reveal which was wrong.
        password_ok = check_password_hash(current_app.config['ADMIN_PASSWORD_HASH'], password)
    except ValueError:
        current_app.logger.error('ADMIN_PASSWORD_HASH is malformed; regenerate it with `flask --app app hash-password`.')
        return None
    return AdminUser(expected) if user_ok and password_ok else None
