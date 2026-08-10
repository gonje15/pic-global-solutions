git config user.email "176077316+gonje15@users.noreply.github.com"
git commit --amend --reset-author --no-edit
git push -u origin main

## Routes

| Route | Description |
|---|---|
| `/` | Homepage |
| `/about` | About the company |
| `/contact` | Contact form + details |
| `/why_us` | Why choose us (linked from About, not in main nav) |
| `/services` | Services overview |
| `/services/consultancy` | Business Consultancy & Advisory |
| `/services/marketing` | Marketing & Business Development |
| `/services/supply` | Supply of Goods |

## Known TODOs Before Launch

- [ ] Replace placeholder hero/team images
- [ ] Replace placeholder phone number, address, and testimonial with real details
- [ ] Wire the contact form to actually send email or store submissions (currently just reloads the page)
- [ ] Decide whether "Services" nav link should point to `/services` instead of the homepage anchor
- [ ] Add real team member names/photos to the About page

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
