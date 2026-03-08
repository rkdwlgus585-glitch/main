# CRM Sheet Contract

## Primary Tabs
- Consult tab: `TAB_CONSULT`
- Listing tab: `TAB_ITEM`
- Recommendation tab: `TAB_RECOMMEND`
- Quote tab: `TAB_QUOTE`

## Pipeline Entry Points
1. Intake: `lead_intake.py`
2. Matching: `match.py`
3. Recommendation: `listing_matcher.py`
4. Quote: `quote_engine.py`
5. Wrapper: `sales_pipeline.py`

## Safe Validation Commands
- Intake dry-run: `python lead_intake.py --csv lead_intake_sample.csv --dry-run`
- Recommendation dry-run: `python listing_matcher.py --lead-id <id> --dry-run`
- Quote dry-run: `python quote_engine.py --lead-id <id> --dry-run`
- Pipeline dry-run: `python sales_pipeline.py --lead-id <id> --dry-run --no-sheet --no-files`

## Scheduler Checks
- Status: `python consult_match_scheduler.py --status`
- Single run: `python consult_match_scheduler.py --once`
- Daemon loop: `python consult_match_scheduler.py --scheduler`

