# Long-Term Sustainability Plan (SeoulMNA)

## 1) Deployment Safety Policy
- Any live/high-traffic action must require explicit approval token (`--confirm-live YES`).
- Build/test/collection logic runs on the Glitch GitHub workspace first.
- Production reflection happens only after report verification.

## 2) Continuous Sustainability Guard
- Script: `scripts/sustainability_guard.py`
- Contract: `quality_contracts/sustainability_guard.contract.json`
- Default report: `logs/sustainability_guard_latest.json`
- Watchdog integration: `scripts/seoulmna_ops_watchdog.ps1` (`sustainability_guard` job)
- Permit collection integration: `scripts/seoulmna_ops_watchdog.ps1` (`permit_collect` job, daily)

### Guard Scope
- GitHub repo exposure risk (public/private, default branch protection)
- Tracked sensitive file checks (`.env`, `service_account.json`)
- Critical operational artifact freshness checks
- Log directory growth and stale-log accumulation
- `confirm-live` enforcement checks on high-impact scripts

## 3) Weekly Governance Checklist
- Review `logs/sustainability_guard_latest.json` and close high-severity issues.
- If repository is public, switch to private before adding new proprietary logic.
- Ensure default branch protection is enabled.
- Archive and prune old logs to keep disk growth bounded.
- Re-run permit industry collection and confirm data freshness.

## 4) Incident Rule
- If `high` issues appear in the sustainability report:
- Freeze live deploy tasks.
- Run fixes in GitHub branch first.
- Reflect to production only after explicit approval.
