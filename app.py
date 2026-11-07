"""Entry point. PythonAnywhere's WSGI file does `from app import app`; locally run `flask --app app run --debug`."""
import os

from pic import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
