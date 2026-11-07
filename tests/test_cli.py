import os
import sqlite3

from dotenv import dotenv_values
from werkzeug.security import check_password_hash

from pic import create_app


PW = 'a-long-password\na-long-password\n'


def _set_password(app, env_file, pw_input=PW, *extra):
    return app.test_cli_runner().invoke(args=['hash-password', '--env-file', str(env_file), *extra], input=pw_input)


def _saved_hash(env_file):
    return dotenv_values(env_file).get('ADMIN_PASSWORD_HASH')


def test_hash_password_print_only(app, tmp_path):
    env = tmp_path / '.env'
    result = _set_password(app, env, PW, '--print-only')
    assert result.exit_code == 0, result.output
    line = next(l for l in result.output.splitlines() if l.startswith('ADMIN_PASSWORD_HASH='))
    assert check_password_hash(line.split('=', 1)[1].strip("'"), 'a-long-password')
    assert not env.exists()


def test_hash_password_appends_on_its_own_line_without_trailing_newline(app, tmp_path):
    # The real-world failure: the last line had no line break, so a naive append glued the hash onto it.
    env = tmp_path / '.env'
    env.write_text('SECRET_KEY=abc\nGEMINI_API_KEY=xyz')
    result = _set_password(app, env)
    assert result.exit_code == 0, result.output
    values = dotenv_values(env)
    assert values['GEMINI_API_KEY'] == 'xyz' and values['SECRET_KEY'] == 'abc'
    assert check_password_hash(values['ADMIN_PASSWORD_HASH'], 'a-long-password')
    assert values['ADMIN_PASSWORD_HASH'] not in result.output  # the hash isn't printed


def test_hash_password_replaces_existing_and_duplicates(app, tmp_path):
    env = tmp_path / '.env'
    env.write_text("A=1\nADMIN_PASSWORD_HASH='old'\nB=2\nADMIN_PASSWORD_HASH='older'\n")
    assert _set_password(app, env).exit_code == 0
    lines = env.read_text().splitlines()
    assert lines[0] == 'A=1' and lines[2] == 'B=2' and len(lines) == 3
    assert check_password_hash(_saved_hash(env), 'a-long-password')


def test_hash_password_refuses_glued_line(app, tmp_path):
    env = tmp_path / '.env'
    original = "GEMINI_API_KEY=xyzADMIN_PASSWORD_HASH='old'\n"
    env.write_text(original)
    result = _set_password(app, env)
    assert result.exit_code != 0 and 'own line' in result.output
    assert 'New admin password' not in result.output  # fails before asking for the password
    assert env.read_text() == original


def test_hash_password_creates_missing_file(app, tmp_path):
    env = tmp_path / '.env'
    assert _set_password(app, env).exit_code == 0
    assert check_password_hash(_saved_hash(env), 'a-long-password')
    assert oct(env.stat().st_mode & 0o777) == '0o600'


def test_hash_password_keeps_file_permissions(app, tmp_path):
    env = tmp_path / '.env'
    env.write_text('A=1\n')
    env.chmod(0o640)
    _set_password(app, env)
    assert oct(env.stat().st_mode & 0o777) == '0o640'


def test_hash_password_rejects_short(app, tmp_path):
    env = tmp_path / '.env'
    result = _set_password(app, env, 'short\nshort\n')
    assert result.exit_code != 0 and not env.exists()


def test_backup_db_keeps_newest(tmp_path):
    db_file = tmp_path / 'contacts.db'
    sqlite3.connect(db_file).execute('create table t (x)').connection.close()
    app = create_app({'TESTING': True, 'SECRET_KEY': 'x', 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_file}'})
    app.instance_path = str(tmp_path)
    backups = tmp_path / 'backups'
    backups.mkdir()
    for i in range(3):
        (backups / f'contacts-2020010{i}-000000.db').write_bytes(b'')
    result = app.test_cli_runner().invoke(args=['backup-db', '--keep', '2'])
    assert result.exit_code == 0, result.output
    names = sorted(os.listdir(backups))
    # The two oldest fake backups are pruned; the newest fake one and today's real one remain.
    assert names[0] == 'contacts-20200102-000000.db' and len(names) == 2
    assert sqlite3.connect(backups / names[1]).execute('select name from sqlite_master').fetchone() == ('t',)
