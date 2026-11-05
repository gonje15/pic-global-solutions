# PythonAnywhere WSGI config for P.I.C Global Solutions.
#
# Copy the contents of this file into the WSGI configuration file that
# PythonAnywhere creates for you (Web tab -> "WSGI configuration file" link,
# e.g. /var/www/<username>_pythonanywhere_com_wsgi.py), replacing everything
# in it. Change YOUR_USERNAME below to your PythonAnywhere username.

import sys

project_home = '/home/YOUR_USERNAME/pic-global-solutions'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# app.py loads .env from its own folder, so secrets in
# /home/YOUR_USERNAME/pic-global-solutions/.env are picked up automatically.
from app import app as application  # noqa: E402
