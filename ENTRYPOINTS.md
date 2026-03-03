# Entrypoint Roles

This file defines launcher roles so operators can distinguish user launchers from maintenance runners.

## Quick Use Rule

- Click only root localized `*.bat` files.
- Do not click `launchers/*.bat` and `scripts/*.cmd` unless you are running maintenance/admin workflows.
- Verify current mapping and unknown entrypoints with:
  - `py -3 scripts/show_entrypoints.py`
  - `py -3 scripts/show_entrypoints.py --strict`

## Role Layers

1. `ROOT_SHIM` (root `*.bat`)
- Compatibility wrapper only.
- Keeps old desktop shortcuts and scheduler targets working.
- Forwards immediately to `launchers/launch_*.bat`.

2. `REAL_LAUNCHER` (`launchers/launch_*.bat`)
- Actual user launcher logic.
- Moves to repo root and runs the real Python entrypoint.

3. `OPS_RUNNER` (`scripts/*.cmd`)
- Operational/maintenance jobs.
- Intended for scheduler or admin execution, not regular user clicks.

## Canonical Real Launchers

- `launchers/launch_gabji.bat` -> `gabji.py`
- `launchers/launch_quote_engine.bat` -> `quote_engine.py`
- `launchers/launch_listing_pipeline.bat` -> `all.py` (default) / `all.py --reconcile-published` (`reconcile`) / `all.py --reconcile-published --reconcile-sheet-only` (`reconcile-sheet`) / `reconcile-menu`
- `launchers/launch_blog.bat` -> `mnakr.py` (`gui`, `--cli`, `--scheduler`, `--schedule-check`)
- `launchers/launch_tistory_publish.bat` -> `tistory_ops/run.py publish-listing ...` (browser automation)
- `launchers/launch_consult_match_scheduler.bat` -> `consult_match_scheduler.py --scheduler`
- `launchers/launch_sales_pipeline.bat` -> `sales_pipeline.py`
- `launchers/launch_listing_matcher.bat` -> `listing_matcher.py`
- `launchers/launch_premium_auto.bat` -> `premium_auto.py`
- `launchers/launch_calculator_autodrive.bat` -> start/status/stop autodrive scripts

## Root Wrapper Behavior

Most root localized `*.bat` files are wrappers that call one canonical launcher above.
Listing pipeline wrappers:
- `매물수집기.bat` -> `launchers/launch_listing_pipeline.bat %*`

`launchers/launch_listing_pipeline.bat reconcile-menu` provides reconcile menu modes:
- mode 1: reconcile (sheet + seoul)
- mode 2: reconcile (sheet only, no seoul login)
- mode 3/4: dry-run variants

## Purpose Groups

Root wrappers include `:: [GROUP] ...` tags so same-purpose entries are easy to identify:

- `DOCUMENT_AUTOMATION`
  - `갑지생성기.bat`
  - `견적생성기.bat`
- `BLOG_CONTENT`
  - `블로그생성기.bat`
  - `블로그자동발행.bat` (startup-once hidden mode; once/day)
  - `티스토리자동발행.bat`
  - `프리미엄글생성.bat`
- `LISTING_PIPELINE`
  - `매물수집기.bat`
  - `추천발송기.bat`
  - `상담매칭자동갱신.bat`
  - `영업파이프라인.bat`

Additional calculator autodrive root wrappers:
- `계산기자율주행_시작.bat`
- `계산기자율주행_상태.bat`
- `계산기자율주행_중지.bat`

## Ops Runner Targets

- `scripts/run_low_conf_sync.cmd` -> low-confidence sync flow
- `scripts/run_parallel_debug.cmd` -> parallel debug report flow
- `scripts/run_quality_daily.cmd` -> quality gate + 7-day trend report flow
- `scripts/run_startup_tistory_daily.cmd` -> tistory daily-once startup flow

## Runtime Inspection

Print current resolved role mapping:

```powershell
py -3 scripts/show_entrypoints.py
```

JSON output:

```powershell
py -3 scripts/show_entrypoints.py --json
```

Check current blog publish schedule and run conditions:

```powershell
py -3 mnakr.py --schedule-check
```

## Gate Verification

Validate all Windows entrypoints under quality contract:

```powershell
py -3 scripts/quality_gate_runner.py --contracts batch_entrypoints --fail-on-warn --quiet
```

## Calculator Ops Context

- Calculator 자율주행 작업 기준(스킬/컨텍스트/가드레일):
  - [skills_context_booster.md](/c:/Users/rkdwl/Desktop/auto/docs/skills_context_booster.md)
  - [calculator_autopilot_context.json](/c:/Users/rkdwl/Desktop/auto/docs/calculator_autopilot_context.json)

## Paid Ops Separation

- New-business/paid workflows are isolated under `paid_ops/`.
- Legacy runner (`run.py`) intentionally does not include paid commands.
- Paid commands must be run only via:
  - `py -3 paid_ops/run.py gb2-audit`
  - `py -3 paid_ops/run.py gabji-report ...`
  - `py -3 paid_ops/run.py verify-split`

## Tistory Ops Separation

- Tistory automation is isolated under `tistory_ops/`.
- Legacy launchers and `run.py` do not call `tistory_ops`.
- Tistory commands:
  - `py -3 tistory_ops/run.py publish-listing ...`
  - `py -3 tistory_ops/run.py daily-once --start-registration 7540`
  - `py -3 tistory_ops/run.py categories-api`
  - `py -3 tistory_ops/run.py verify-split`
