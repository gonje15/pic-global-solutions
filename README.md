# P.I.C Global Solutions

Marketing site for P.I.C Global Solutions, built with Flask, Jinja templates and Tailwind CSS.
It includes a contact form (saved to SQLite and emailed through Gmail), a Gemini-powered
"which service fits me?" widget, and a password-protected admin dashboard at `/admin`
for tracking enquiries.

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # then fill in the values
flask --app app db upgrade        # create/update the database
flask --app app hash-password     # sets the admin password in .env
flask --app app run --debug
```

Run the tests with `python -m pytest`.

## Project layout

| Path | What's there |
|---|---|
| `app.py` | Entry point (`app = create_app()`), used by PythonAnywhere's WSGI file |
| `pic/__init__.py` | App factory and configuration (all settings come from `.env`) |
| `pic/public.py` | Public pages and the contact form |
| `pic/api.py` | `/api/service-fit` (Gemini widget) |
| `pic/admin.py` | Admin dashboard, inbox, CSV export, AI insights |
| `pic/models.py` | Database tables |
| `pic/content.py` | Text for the three service pages |
| `pic/cli.py` | `hash-password` and `backup-db` commands |
| `migrations/` | Database migrations (Flask-Migrate / Alembic) |
| `tests/` | pytest suite |

### Changing the database

Edit `pic/models.py`, then:

```bash
flask --app app db migrate -m "describe the change"   # review the generated file in migrations/versions/
flask --app app db upgrade
```

CSS is prebuilt in `static/css/output.css`. If you change Tailwind classes, rebuild it:

```bash
npm install
npm run build:css
```

Deployment steps are in [DEPLOY.md](DEPLOY.md).

## Routes

| Route | Description |
|---|---|
| `/` | Homepage |
| `/about` | About the company |
| `/contact` | Contact form + details |
| `/why_us` | Why choose us (linked from About, not in main nav) |
| `/services` | Services overview |
| `/services/<slug>` | Service detail page (`supply`, `consultancy`, `marketing`). Content lives in `pic/content.py` |
| `/privacy` | Privacy notice (linked from the contact form) |
| `/admin` | Admin dashboard (login required) |
| `/api/service-fit` | POST: Gemini service recommendation (rate-limited) |

## Known TODOs Before Launch

- [ ] Replace placeholder phone number, address and testimonial with real details
- [ ] Add real team member names/photos to the About page
- [ ] Replace the map placeholder on the Contact page
- [ ] Add real LinkedIn/Facebook links (currently `#`)
- [ ] Register the domain used in `info@picglobalsolutions.com`, or change the address
- [ ] Have the privacy notice (`templates/privacy.html`) checked against local data-protection law

## Contributing

This is a student/personal project. If you're collaborating:

1. Create a new branch for your changes:
```bash
   git checkout -b your-feature-name
```
2. Commit your changes and push:
```bash
   git push origin your-feature-name
```
3. Open a pull request on GitHub for review before merging into `main`.

## License

Not yet specified.
