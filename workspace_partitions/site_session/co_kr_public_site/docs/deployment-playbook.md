# Deployment Playbook

This project is the replacement candidate for `seoulmna.co.kr`.

## Content Rules

- `notice` and `premium` are preserved from the current public site.
- The listing board under `/mna` is driven by the Google Sheet snapshot.
- Other public guide pages are allowed to be upgraded as long as the original content intent is preserved.

## Current Migration Status

- Legacy content import verified on 2026-03-11.
- Legacy board counts: `mna` 1701, `notice` 349, `premium` 35, `news` 1, `pages` 26, `tl_faq` 1.
- Google Sheet listing snapshot exported on 2026-03-11 with 1701 records.
- Live `/mna` routes use the Google Sheet-backed dataset, not the legacy-only tail.
- Local lint, build, and HTTP smoke checks have passed.
- Preview deploy is currently blocked only by missing local Vercel auth.

## Local Release Flow

From `workspace_partitions/site_session/co_kr_public_site`:

```bash
npm.cmd run qa:local:release
```

This single command runs:

- Google Sheet export refresh
- legacy content verification
- market data verification
- regulatory freshness verification
- lint
- production build in a dedicated `.next-stage` directory
- local production server boot
- smoke test against the local production server

## Deploy Readiness

Run:

```bash
npm.cmd run validate:deploy
```

This validation checks:

- required imported JSON files
- Google Sheet listing snapshot presence
- imported asset directory presence
- Next.js build artifacts in `.next` or any `.next-*` build directory
- Vercel CLI availability and auth status
- recommended `.env.local` keys
- whether `NEXT_PUBLIC_SITE_HOST` is still using a preview-safe noindex host

## Preview Deploy

Authenticate once on this machine:

```bash
npx.cmd --yes vercel login
```

Then deploy a preview:

```bash
npm.cmd run deploy:preview
```

`deploy:preview` now runs this preflight chain automatically before it calls Vercel:

- `npm.cmd run sync:env`
- `npm.cmd run qa:local:release`

If the project is not linked yet, Vercel CLI may ask to link or create the project once.

## Current Blocker

Run this once on the machine before the first preview deploy:

```bash
npx.cmd --yes vercel login
```

After login, rerun:

```bash
npm.cmd run validate:deploy
npm.cmd run deploy:preview
```

## Current Known Constraint

The anonymous fallback uploader is not suitable for this site because the content package is too large.
Use authenticated Vercel CLI deploys for preview and production.

## Production Host Switch

`npm.cmd run sync:env` writes a preview-safe `NEXT_PUBLIC_SITE_HOST` by default so local and preview builds stay `noindex`.
Before the final production deploy, switch the host to the real public domain in Vercel env or regenerate with:

```bash
python scripts/sync_env_local.py --mode production --site-host https://seoulmna.co.kr
```
