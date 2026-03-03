Quality contracts define minimum quality checks per automation.

Each `*.contract.json` file follows `contract.schema.json` and is consumed by:

`scripts/quality_gate_runner.py`

Supported check types:
- `file_exists`
- `python_compile`
- `python_import`
- `unittest_discover`
- `command`
- `json_report`

Notes:
- Use `"{python}"` in `command` checks to run with the current interpreter.
- Set `"required": false` for warning-only checks.
- String `command` checks run with shell by default (for example: `"echo ok"`).
- Daily runner supports report retention via `--keep-days` (default: 30).
- `batch_entrypoints.contract.json` validates root `.bat` shims + `launchers/*.bat` via `scripts/batch_smoke_check.py`, and `scripts/*.cmd` via `scripts/cmd_smoke_check.py`.
- `scripts/show_entrypoints.py` can print role mapping (`ROOT_SHIM` / `REAL_LAUNCHER` / `OPS_RUNNER`) for operator review.
- `scripts/show_entrypoints.py --strict` fails when unclassified `.bat/.cmd` entrypoints are found.
- Daily schedule also writes trend snapshots via `scripts/quality_trend_report.py`.
