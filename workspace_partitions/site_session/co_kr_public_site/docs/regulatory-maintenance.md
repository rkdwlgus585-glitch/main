# Regulatory Maintenance

Date: 2026-03-11
Project: `co_kr_public_site`

## Goal

Legal and procedural copy on the public site should not remain static after laws, association notices, or filing years change.

## What Is Checked

- `regulatoryReviewedAt` age
- year-sensitive copy in the homepage and practice guidance
- warnings for year-sensitive first-party files outside the monitored set
- official source link availability

## Command

```bash
npm run verify:regulatory
```

## Operational Rule

- Run the check before every production deploy.
- Run it again when the calendar year changes, when associations publish a new schedule, or when a law/article link changes.
- Treat failures as content-maintenance issues, not cosmetic warnings.
- Imported legacy archive content is preserved as historical material and is not part of this regulatory freshness gate.
