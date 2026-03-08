# Listing Ops Flags

## Core Modes
- Default collect and upload: `python all.py`
- Single uid collect: `python all.py --uid <uid>`
- Reconcile dry-run: `python all.py --reconcile-published --reconcile-dry-run`
- Reconcile apply (sheet only): `python all.py --reconcile-published --reconcile-sheet-only`
- Reconcile apply (sheet plus site): `python all.py --reconcile-published`

## Recovery Modes
- Rollback preview: `python all.py --reconcile-rollback latest --rollback-dry-run`
- Rollback apply: `python all.py --reconcile-rollback latest`
- Claim restore preview: `python all.py --restore-claim-from-kakao --restore-claim-file <txt> --restore-claim-dry-run`
- Claim restore apply with site reflection: `python all.py --restore-claim-from-kakao --restore-claim-file <txt> --restore-claim-apply-site`

## Quality and Audit
- Low confidence export: `python all.py --export-low-confidence`
- Sync low confidence to review sheet: `python all.py --sync-low-confidence-sheet`
- Daily dashboard generation: `python all.py --daily-dashboard --dashboard-days 7`
- Tag reconcile runs: `python all.py --reconcile-published --reconcile-audit-tag <tag>`

