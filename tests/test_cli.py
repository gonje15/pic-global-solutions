import os
import sqlite3

from werkzeug.security import check_password_hash

from pic import create_app


def test_hash_password_prints_usable_hash(app):
    result = app.test_cli_runner().invoke(args=['hash-password'], input='a-long-password\na-long-password\n')
    assert result.exit_code == 0, result.output
    line = next(l for l in result.output.splitlines() if l.startswith('ADMIN_PASSWORD_HASH='))
    assert check_password_hash(line.split('=', 1)[1].strip("'"), 'a-long-password')


def test_hash_password_rejects_short(app):
    result = app.test_cli_runner().invoke(args=['hash-password'], input='short\nshort\n')
    assert result.exit_code != 0


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
