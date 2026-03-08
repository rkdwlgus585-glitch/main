---
name: seoulmna-blog-ops
description: Operate the SeoulMNA blog automation pipeline in mnakr.py. Use when tasks involve one-shot or scheduled publishing, WordPress auth checks, schedule diagnostics, SERP audit or repair runs, lifecycle maintenance, query rewrite operations, or blog related env troubleshooting.
---

# SeoulMNA Blog Ops

Use this skill to operate `mnakr.py` safely in CLI, scheduler, and maintenance modes.

## Preflight
1. Confirm `.env` has `GEMINI_API_KEY` and `WP_URL` for publish flows.
2. Confirm WordPress auth is configured with one of:
- `WP_JWT_TOKEN`
- `WP_USER` + `WP_APP_PASSWORD` (preferred)
- `WP_USER` + `WP_PASSWORD`
3. Confirm scheduler lock/state files are writable.
4. For data-driven SEO loops, confirm search context inputs are ready:
- `SEARCH_DATA_ENABLED`
- `GSC_PROPERTY_URL` and `GSC_SERVICE_ACCOUNT_FILE` or CSV fallback files
5. Bootstrap and validate search context quickly:
```bash
python scripts/bootstrap_search_context.py --check-gsc
```
5. Treat OpenAI reranking features as optional unless both enabled and keyed (`OPENAI_SCAN_ENABLED=true`, `OPENAI_API_KEY`).

## Operation Selector
- Show scheduler plan and maintenance times:
```bash
python mnakr.py --schedule-check
```
- Verify WordPress authentication:
```bash
python mnakr.py --wp-check
```
- Run one scheduled publish cycle now:
```bash
python mnakr.py --cli
```
- Run continuous scheduler:
```bash
python mnakr.py --scheduler
```
- Run SERP snippet audit:
```bash
python mnakr.py --serp-audit
```
- Run SERP snippet repair:
```bash
python mnakr.py --serp-repair
```

## Guardrails
1. Use `--wp-check` before scheduler starts after credential changes.
2. Do not start scheduler when machine sleep policy can interrupt runs.
3. Keep `--schedule-check` output as the source of truth for effective slots.
4. When SEO data sources are missing, keep maintenance enabled but avoid interpreting rewrite output as performance-validated decisions.

## References
- Read `references/context.md` for env matrix and SEO data prerequisites.

