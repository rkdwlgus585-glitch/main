# Security Best Practices Report

## Executive Summary
- Overall posture improved with non-disruptive hardening.
- High-risk XSS-style link injection risk in generated HTML was mitigated.
- Operational resilience against missed schedule windows (shutdown/sleep) was added.
- Secret leakage risk was reduced by adding repository ignore rules for sensitive files.

## Findings

### [S-001] Untrusted outbound URLs could be rendered directly in HTML (High)
- Impact: Generated content could embed unsafe links (for example, non-HTTP schemes) in published posts.
- Evidence: `mnakr.py:2896`, `mnakr.py:2904`
- Fix applied:
  - Added URL sanitizer for allowed schemes (`http`, `https`) with fallback.
  - Escaped link text and URL in rendered anchors.
  - Added `noopener noreferrer` to `target="_blank"` links.
- Related code: `mnakr.py:151`, `mnakr.py:2896`, `mnakr.py:2904`

### [S-002] Scheduler missed-run recovery was not persisted across restarts (Medium)
- Impact: If the PC was powered off during planned run windows, jobs could be skipped for the day.
- Evidence: schedule loop depended on runtime-only `run_pending`.
- Fix applied:
  - Added persisted scheduler state file and per-job run markers.
  - Added startup catch-up execution for due-but-not-run jobs.
  - Wrapped scheduled jobs with tracking wrapper.
- Related code: `mnakr.py:87`, `mnakr.py:3778`, `mnakr.py:3835`, `mnakr.py:3842`, `mnakr.py:3998`, `mnakr.py:4023`

### [S-003] Sensitive local artifacts could be accidentally committed (Medium)
- Impact: Credentials/keys and operational state files may leak if committed to VCS.
- Evidence: `.env`, `service_account.json`, runtime state files in project root.
- Fix applied:
  - Added `.gitignore` entries for secrets and runtime caches/state.
- Related file: `.gitignore`

## Residual Risks
- Local plaintext secret storage (`.env`, service account file) remains necessary for runtime.
- Windows startup script still depends on local user session/logon for launch.
- WordPress credentials should continue using Application Password or JWT only.

## Recommended Next Steps
1. Move secrets to OS secret store (Windows Credential Manager) and load at runtime.
2. Restrict file ACLs for `.env` and `service_account.json` to the current user only.
3. Keep `OPENAI_SCAN_ENABLED=false` and `SEMANTIC_GUARD_ENABLED=false` unless API billing is intentionally enabled.
