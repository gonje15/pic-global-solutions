"""Command-line helpers: `flask --app app hash-password` and `flask --app app backup-db`."""
import glob
import os
import sqlite3

import click
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import utcnow


def init_app(app):
    @app.cli.command('hash-password')
    def hash_password():
        """Create ADMIN_PASSWORD_HASH for .env from a password you type."""
        password = click.prompt('New admin password', hide_input=True, confirmation_prompt=True)
        if len(password) < 10:
            raise click.ClickException('Use at least 10 characters.')
        click.echo('\nAdd this line to .env (keep the single quotes), then reload the web app:\n')
        click.echo(f"ADMIN_PASSWORD_HASH='{generate_password_hash(password)}'")

    @app.cli.command('backup-db')
    @click.option('--keep', default=14, show_default=True, type=click.IntRange(min=1),
                  help='How many backups to keep.')
    def backup_db(keep):
        """Copy the SQLite database to instance/backups/, keeping the newest N copies."""
        src = db.engine.url.database
        if not src or not os.path.exists(src):
            raise click.ClickException(f'Database not found: {src}')
        backup_dir = os.path.join(app.instance_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        dest = os.path.join(backup_dir, f'contacts-{utcnow():%Y%m%d-%H%M%S}.db')

        # sqlite3's backup API gives a consistent copy even if the site is writing at the same time.
        source, target = sqlite3.connect(src), sqlite3.connect(dest)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

        old = sorted(glob.glob(os.path.join(backup_dir, 'contacts-*.db')))[:-keep]
        for path in old:
            os.remove(path)
        click.echo(f'Backed up to {dest} ({len(old)} old backup(s) removed)')
