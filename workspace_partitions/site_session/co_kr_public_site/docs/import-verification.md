# Import Verification

Date: 2026-03-11
Project: `co_kr_public_site`

## Purpose

This project preserves the published public content imported from `seoulmna.co.kr`.
That preservation should be enforced mechanically, not by spot checks alone.

## What Is Verified

- Required imported JSON files exist under `data/imported/`
- `manifest.json` count values match the actual imported record counts
- `manifest.json` file metadata matches the real file path, size, SHA-256 hash, and record count
- Listing summaries and listing details have matching ordering and IDs
- Board post IDs and page slugs remain unique

## Commands

Verify the imported baseline:

```bash
npm run verify:legacy
```

If the imported files are already correct and the manifest only needs to be refreshed from disk:

```bash
npm run verify:legacy:sync
```

## Operational Rule

Run `npm run verify:legacy` after every legacy import refresh and before production deploys.
If this verification fails, treat it as a content-integrity issue, not a cosmetic warning.
