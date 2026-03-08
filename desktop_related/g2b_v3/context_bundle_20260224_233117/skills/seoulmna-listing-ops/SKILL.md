---
name: seoulmna-listing-ops
description: Operate the SeoulMNA listing ingestion and publishing pipeline in all.py. Use when tasks involve nowmna listing collection, Google Sheet sync, seoulmna.co.kr MNA board upload, reconcile or rollback execution, low-confidence price exports, admin memo fixes, or claim price restoration from Kakao exports.
---

# SeoulMNA Listing Ops

Use this skill to run `all.py` safely for collection, sync, publish, and recovery work.

## Preflight
1. Confirm the workspace root is active (`c:/Users/rkdwl/Desktop/auto`).
2. Confirm `.env` contains `JSON_FILE`, `SHEET_NAME`, `SITE_URL`, `MNA_BOARD_SLUG`.
3. Confirm `service_account.json` exists before sheet operations.
4. For site write operations, confirm `ADMIN_ID` and `ADMIN_PW` are set.
5. Start from safe mode first when possible (`--reconcile-dry-run`, `--reconcile-sheet-only`, `--backfill-dry-run`).

## Operation Selector
- Default collect plus upload:
```bash
python all.py
```
- Single UID collect:
```bash
python all.py --uid 7734
```
- Reconcile preview only:
```bash
python all.py --reconcile-published --reconcile-dry-run
```
- Reconcile apply (sheet only, no seoul login):
```bash
python all.py --reconcile-published --reconcile-sheet-only
```
- Reconcile apply (sheet plus seoul):
```bash
python all.py --reconcile-published
```
- Rollback latest snapshot preview:
```bash
python all.py --reconcile-rollback latest --rollback-dry-run
```
- Low confidence export and review sheet sync:
```bash
python all.py --export-low-confidence --sync-low-confidence-sheet --low-skip-reviewed
```
- Restore claim price from Kakao export text:
```bash
python all.py --restore-claim-from-kakao --restore-claim-file path/to/chat.txt --restore-claim-dry-run
```

## Guardrails
1. Run `--reconcile-dry-run` before any reconcile apply run.
2. Prefer `--reconcile-sheet-only` when auth state is unknown.
3. Never run rollback apply without a dry-run preview first.
4. Keep operation notes by tagging high-risk runs with `--reconcile-audit-tag`.
5. If runtime behavior is unclear, check launcher mapping first via:
```bash
python scripts/show_entrypoints.py
```

## References
- Read `references/flags.md` for detailed mode and flag bundles.

