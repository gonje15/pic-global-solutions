"""Command-line helpers: `flask --app app hash-password` and `flask --app app backup-db`."""
import glob
import os
import re
import shutil
import sqlite3

import click
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import utcnow


def _key_pattern(key):
    return re.compile(rf'^\s*(export\s+)?{re.escape(key)}\s*=')


def check_env_file(path, key):
    """Refuse to touch a .env where `key` appears glued to another line (e.g. a missing line break)."""
    if not os.path.exists(path):
        return
    with open(path, encoding='utf-8') as f:
        for number, text in enumerate(f.read().splitlines(), start=1):
            if f'{key}=' in text and not _key_pattern(key).match(text):
                raise click.ClickException(
                    f'{path} line {number} has {key} in the middle of another setting. '
                    f'Put {key} on its own line (or delete it) and run this again.')


def set_env_line(path, key, line):
    """Put `line` into the .env file, replacing any existing `key=` line, always on its own line.

    Other lines are kept as they are. The file is written to a temporary file and then swapped
    in, so a crash can't leave a half-written .env.
    """
    check_env_file(path, key)
    lines = []
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            lines = f.read().splitlines()
    pattern = _key_pattern(key)
    out, replaced = [], False
    for text in lines:
        if pattern.match(text):
            if not replaced:  # keep the position of the first one, drop any duplicates
                out.append(line)
                replaced = True
        else:
            out.append(text)
    if not replaced:
        out.append(line)

    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    if os.path.exists(path):
        shutil.copymode(path, tmp)
    else:
        os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def init_app(app):
    default_env = os.path.join(os.path.dirname(app.root_path), '.env')

    @app.cli.command('hash-password')
    @click.option('--env-file', default=default_env, show_default=True, type=click.Path(dir_okay=False),
                  help='The .env file to update.')
    @click.option('--print-only', is_flag=True, help="Print the line instead of saving it to .env.")
    def hash_password(env_file, print_only):
        """Set the admin password: saves ADMIN_PASSWORD_HASH to .env."""
        if not print_only:
            # Check before asking for the password, so nothing is typed for nothing.
            check_env_file(env_file, 'ADMIN_PASSWORD_HASH')
        password = click.prompt('New admin password', hide_input=True, confirmation_prompt=True)
        if len(password) < 10:
            raise click.ClickException('Use at least 10 characters.')
        line = f"ADMIN_PASSWORD_HASH='{generate_password_hash(password)}'"
        if print_only:
            click.echo('\nAdd this line to .env (keep the single quotes), then reload the web app:\n')
            click.echo(line)
            return
        set_env_line(env_file, 'ADMIN_PASSWORD_HASH', line)
        click.echo(f'Saved the new admin password to {env_file}. Reload the web app to use it.')

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
