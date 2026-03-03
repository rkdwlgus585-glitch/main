# Paid Ops Boundary

This folder contains only paid/new-business automation.

## Scope
- `run.py`: paid-only command router
- `build_gabji_analysis_report.py`: paid diagnostic report builder
- `audit_gb2_v3_integration.py`: backend compatibility audit (`gb2_v3` vs `gabji`)
- `verify_paid_legacy_split.py`: separation contract verifier

## Non-Scope
- Legacy production automations (`all.py`, `mnakr.py`, launchers, root bat files)
- Existing scheduler and entrypoint chains

## Runbook
1. Backend audit
```bash
py -3 paid_ops/run.py gb2-audit --out logs/gb2_v3_integration_audit_latest.json
```

2. Paid report generation
```bash
py -3 paid_ops/run.py gabji-report --registration 7737 --output output/7737_report.pdf
```

3. Separation verification
```bash
py -3 paid_ops/run.py verify-split --out logs/paid_legacy_split_verify_latest.json
```

## Guardrail
- If `verify-split` returns `ok=false`, do not deploy paid updates.

