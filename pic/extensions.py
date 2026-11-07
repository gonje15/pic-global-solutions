"""Flask extensions, created unbound and attached to the app in create_app()."""
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
mail = Mail()
# render_as_batch lets Alembic alter SQLite tables (SQLite has limited ALTER TABLE).
migrate = Migrate(render_as_batch=True, compare_type=True)
login_manager = LoginManager()
