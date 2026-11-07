# P.I.C Global Solutions

Marketing site for P.I.C Global Solutions, built with Flask, Jinja templates and Tailwind CSS.
It includes a contact form (saved to SQLite and emailed through Gmail) and a Gemini-powered
"which service fits me?" widget.

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in the values
FLASK_DEBUG=1 python app.py
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
| `/services/<slug>` | Service detail page (`supply`, `consultancy`, `marketing`). Content lives in `services_data.py` |
| `/api/service-fit` | POST: Gemini service recommendation (rate-limited) |

## Known TODOs Before Launch

- [ ] Replace placeholder phone number, address and testimonial with real details
- [ ] Add real team member names/photos to the About page
- [ ] Replace the map placeholder on the Contact page
- [ ] Add real LinkedIn/Facebook links (currently `#`)
- [ ] Register the domain used in `info@picglobalsolutions.com`, or change the address

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
