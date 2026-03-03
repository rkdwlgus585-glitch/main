# Launcher Folder

`launchers/` contains Windows launcher targets.

Root `*.bat` files are only `ROOT_SHIM` wrappers for compatibility with existing shortcuts and scheduler entries.

Use rule:
- Operators should click root localized `*.bat` files only.
- `launchers/*.bat` are internal launcher targets and can be called by wrappers/automation.

## Blog launcher

Use `launchers/launch_blog.bat`:
- `gui`: open GUI (`python mnakr.py`)
- `auto`: one-shot auto publish (`python mnakr.py --cli`)
- `scheduler`: continuous scheduler loop (`python mnakr.py --scheduler`)
- `status`: schedule plan check (`python mnakr.py --schedule-check`)
- `startup-once`: hidden startup runner (executes `mnakr.py --startup-once`, once/day)
- no args: menu prompt

`블로그자동발행.bat` now forwards to `startup-once` mode by default.

Scheduler behavior:
- Target slot is read from `AUTO_SCHEDULE_ENABLED` + `SCHEDULE_TIME`/AI slots.
- Actual publish slot can be shifted to previous day fixed time by:
  - `PUBLISH_PREV_DAY_ENABLED=true`
  - `PUBLISH_PREV_DAY_TIME=21:00`

## Root group tags

Root wrappers include `:: [GROUP] ...` tags for same-purpose visibility:
- `DOCUMENT_AUTOMATION`
- `BLOG_CONTENT`
- `LISTING_PIPELINE`

## Reference

See `ENTRYPOINTS.md` for the complete role map:
- root shim -> real launcher
- real launcher -> python target
- ops runner (`scripts/*.cmd`) roles

Canonical launchers in this folder:
- `launch_gabji.bat`
- `launch_quote_engine.bat`
- `launch_listing_pipeline.bat` (canonical listing/reconcile launcher)
- `launch_blog.bat`
- `launch_tistory_publish.bat` (tistory browser publish launcher)
- `launch_consult_match_scheduler.bat`
- `launch_sales_pipeline.bat`
- `launch_listing_matcher.bat`
- `launch_premium_auto.bat`
- `launch_calculator_autodrive.bat` (start/status/stop autodrive)

`launch_tistory_publish.bat` modes:
- argument `7540` like numeric registration: publish that registration.
- argument `daily` or no argument: run daily-once sequential publish (1/day, start from configured registration).
- argument `startup-once`: run hidden startup runner (`scripts/run_startup_tistory_daily.cmd`).

## Calculator autodrive launcher

Use `launchers/launch_calculator_autodrive.bat`:
- `start`: hidden autodrive loop until next 09:00 (`scripts/start_calculator_autodrive_until_9am.ps1`)
- `status`: print state/latest reports (`scripts/show_calculator_autodrive_status.ps1`)
- `stop`: terminate autodrive worker (`scripts/stop_calculator_autodrive.ps1`)

Root wrappers:
- `계산기자율주행_시작.bat`
- `계산기자율주행_상태.bat`
- `계산기자율주행_중지.bat`

## Listing launcher modes

Use root `매물수집기.bat`:
- no args: default collector (`launchers/launch_listing_pipeline.bat` -> `python all.py %*`)
- `menu`: interactive mode select
- `reconcile`: reconcile (sheet + seoul)
- `reconcile-sheet`: reconcile sheet-only (no seoul login)
- `reconcile-menu`: reconcile menu (apply/dry-run variants)
