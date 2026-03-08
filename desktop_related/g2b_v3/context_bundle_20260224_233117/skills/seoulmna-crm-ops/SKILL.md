---
name: seoulmna-crm-ops
description: Operate the SeoulMNA consult to sales pipeline using lead_intake.py, match.py, listing_matcher.py, quote_engine.py, sales_pipeline.py, and consult_match_scheduler.py. Use when tasks involve intake ingestion, lead matching, recommendation drafting, quote generation, scheduler status checks, or sheet contract troubleshooting.
---

# SeoulMNA CRM Ops

Use this skill to run the consult intake and sales pipeline safely from raw inquiry to quote output.

## Preflight
1. Confirm `.env` has `JSON_FILE`, `SHEET_NAME`, `TAB_CONSULT`, `TAB_ITEM`, `TAB_RECOMMEND`, `TAB_QUOTE`.
2. Confirm `service_account.json` is present and valid.
3. Start with dry-run paths when row targeting is uncertain.

## Pipeline Modes
- Intake sample and dry-run validation:
```bash
python lead_intake.py --sample-csv
python lead_intake.py --csv lead_intake_sample.csv --dry-run
```
- Intake real batch and run matching:
```bash
python lead_intake.py --csv lead_intake_sample.csv --run-match
```
- Run matching only:
```bash
python match.py
```
- Recommendation draft only:
```bash
python listing_matcher.py --lead-id LD20260224123456789 --dry-run
```
- Quote draft only:
```bash
python quote_engine.py --lead-id LD20260224123456789 --dry-run
```
- Full sales pipeline wrapper:
```bash
python sales_pipeline.py --lead-id LD20260224123456789 --run-match
```

## Scheduler Operations
- Show scheduler status:
```bash
python consult_match_scheduler.py --status
```
- Run one sync now:
```bash
python consult_match_scheduler.py --once
```
- Run daily loop:
```bash
python consult_match_scheduler.py --scheduler
```

## Guardrails
1. Use `--consult-row` when lead id is missing or duplicated.
2. Use `--no-sheet` and `--no-files` during smoke checks.
3. If output looks inconsistent, rerun `match.py` before recommendation and quote steps.

## References
- Read `references/sheet-contract.md` for expected tab and column contracts.

