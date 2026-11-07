# Deploying to PythonAnywhere

Replace `YOUR_USERNAME` with your PythonAnywhere username everywhere below.

## 1. Push your latest code to GitHub

```bash
git push origin main
```

## 2. Clone the repo on PythonAnywhere

Open a **Bash console** (Dashboard → Consoles → Bash) and run:

```bash
git clone https://github.com/gonje15/pic-global-solutions.git
cd pic-global-solutions
```

## 3. Create a virtualenv and install dependencies

```bash
mkvirtualenv --python=python3.12 pic-venv
pip install -r requirements.txt
```

(If 3.12 isn't available, use the newest Python that the Web tab offers. Pick the **same version** in step 5.)

## 4. Add your secrets

`.env` is in `.gitignore`, so it isn't on GitHub. Create it on the server:

```bash
nano ~/pic-global-solutions/.env
```

```
SECRET_KEY=some-long-random-string
MAIL_USERNAME=you@gmail.com
MAIL_PASSWORD=your-gmail-app-password
GEMINI_API_KEY=your-gemini-key
ADMIN_USERNAME=admin
DISPLAY_TIMEZONE=UTC
```

[`.env.example`](.env.example) lists the optional settings too (WhatsApp number, booking link,
Cloudflare Turnstile spam check, auto-reply).

To generate a SECRET_KEY, run `python -c "import secrets; print(secrets.token_hex(32))"`.

## 5. Create the web app

1. Go to the **Web** tab → **Add a new web app**.
2. Choose **Manual configuration** (not "Flask"), then pick the same Python version as your virtualenv.
3. Under **Virtualenv**, enter: `/home/YOUR_USERNAME/.virtualenvs/pic-venv`
4. Under **Code**, set the source code directory to `/home/YOUR_USERNAME/pic-global-solutions`
5. Click the **WSGI configuration file** link, delete everything in it, and paste in the contents of
   [`pythonanywhere_wsgi.py`](pythonanywhere_wsgi.py). Change `YOUR_USERNAME` and save.
6. Under **Static files**, add:

   | URL        | Directory                                      |
   |------------|------------------------------------------------|
   | `/static/` | `/home/YOUR_USERNAME/pic-global-solutions/static` |

7. Turn on **Force HTTPS**.
8. Click **Reload**, then visit `https://YOUR_USERNAME.pythonanywhere.com`.

Then, in the Bash console, create the database and the admin password:

```bash
cd ~/pic-global-solutions && workon pic-venv
flask --app app db upgrade
flask --app app hash-password      # paste the printed ADMIN_PASSWORD_HASH='...' line into .env
```

Click **Reload** again and log in at `https://YOUR_USERNAME.pythonanywhere.com/admin`.

## Daily database backups

Scheduled tasks need a paid PythonAnywhere account. On the free plan, run the command below by hand
in a Bash console now and then (for example weekly, and always before a deploy). Once you upgrade,
add it on the **Tasks** tab as a daily scheduled task:

```
cd /home/YOUR_USERNAME/pic-global-solutions && /home/YOUR_USERNAME/.virtualenvs/pic-venv/bin/flask --app app backup-db
```

It keeps the newest 14 copies in `instance/backups/`. Download one now and then from the **Files** tab
so a copy also exists off the server.

## Updating the site later

```bash
cd ~/pic-global-solutions
git pull
workon pic-venv && pip install -r requirements.txt   # only if requirements changed
flask --app app db upgrade                            # applies any new database migrations (safe to always run)
```

Then click **Reload** on the Web tab.

If you change Tailwind classes, run `npm run build:css`
locally and commit `output.css` first. The server doesn't need Node.

## Troubleshooting

- **Errors or a blank page**: check the **error log** link on the Web tab.
- **Free accounts** can only reach allowlisted sites. `smtp.gmail.com` (contact form email) and Google's
  Gemini API should work. If the contact form or the service-fit widget fails with a connection error,
  check the error log and the PythonAnywhere allowlist (https://www.pythonanywhere.com/whitelist/).
- **Gmail login fails**: `MAIL_PASSWORD` has to be a Gmail **App Password** (with 2-Step Verification on),
  not your normal password.
