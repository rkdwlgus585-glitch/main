# auto Threat Model (2026-03-05)

## Scope
In-scope runtime components in this repository:
- `yangdo_blackbox_api.py` (`/estimate`, `/reload`, `/meta`, `/health`)
- `yangdo_consult_api.py` (`/consult`, `/usage`, `/health`)
- `permit_diagnosis_calculator.py` (법령 기반 인허가 사전검토 룰/데이터 사용)
- `acquisition_calculator.py` (양도양수 계산기 HTML/JS 생성)

Out-of-scope for this document:
- WordPress 운영 자동화 파이프라인 전체
- 외부 인프라 내부 설정(Cloudflare, LB, WAF 실제 계정값)

## Assets
- A1. 상담/문의 개인정보(이름, 전화, 이메일, 상담요약)
- A2. 양도가 산정 알고리즘/결과 신뢰도
- A3. 인허가 등록기준 법령 데이터 무결성
- A4. API 인증키, 서비스 계정 파일, 운영 로그
- A5. 가용성(고객용 계산/상담 API 지속 제공)

## Trust Boundaries
1. Public Browser/Client -> API server (`yangdo_blackbox_api.py`, `yangdo_consult_api.py`)
- Threats: credential stuffing, abusive requests, malformed JSON payloads, origin abuse

2. API server -> local SQLite storage (`logs/*.sqlite3`)
- Threats: PII leakage, storage growth abuse

3. API server -> CRM bridge / Google Sheet API
- Threats: unauthorized write, abuse traffic amplification, external API key leakage

4. Static calculator rendering -> client-side execution
- Threats: endpoint/script injection via unsafe serialization

## Attacker model
- T1. Internet anonymous attacker (no credential)
- T2. Scraper/botnet focused on DDoS/resource exhaustion
- T3. Competitor/adversary attempting model abuse or operational disruption
- T4. Insider or leaked token holder

## Findings (Prioritized)

### TM-01 Unauthorized write and admin action on API endpoints (High)
- Affected assets: A1, A2, A5
- Abuse path: attacker posts directly to `/consult`, `/usage`, `/estimate`, `/reload` without trusted caller proof.
- Likelihood: High
- Impact: High
- Current controls added in code:
  - API key enforcement hooks: `yangdo_consult_api.py:530`, `yangdo_consult_api.py:673`
  - API/admin key enforcement hooks: `yangdo_blackbox_api.py:1849`, `yangdo_blackbox_api.py:1855`, `yangdo_blackbox_api.py:1919`, `yangdo_blackbox_api.py:1929`

### TM-02 DDoS and resource exhaustion (High)
- Affected assets: A5
- Abuse path: high-rate request flood, oversized payload, many source IP churn.
- Likelihood: High
- Impact: High
- Current controls added in code:
  - Sliding window rate limit: `yangdo_consult_api.py:711`, `yangdo_blackbox_api.py:1960`
  - `429` with `Retry-After`: `yangdo_consult_api.py:537`, `yangdo_blackbox_api.py:1863`
  - Body-size limit + JSON content-type check: `yangdo_consult_api.py:575`, `yangdo_consult_api.py:580`, `yangdo_blackbox_api.py:1876`, `yangdo_blackbox_api.py:1881`

### TM-03 CORS abuse / browser-origin confusion (Medium)
- Affected assets: A1, A2
- Abuse path: permissive cross-origin policies enable untrusted origins to invoke APIs from browsers.
- Likelihood: Medium
- Impact: Medium
- Current controls added in code:
  - Origin allowlist resolution: `security_http.py:18`, `security_http.py:30`
  - Consult API CORS tightened to configured allowlist: `yangdo_consult_api.py:523`
  - Blackbox API CORS no longer hardcoded `*`: `yangdo_blackbox_api.py:1817`, `yangdo_blackbox_api.py:1834`

### TM-04 Internal error leakage (Medium)
- Affected assets: A2, A4
- Abuse path: exception text in API response reveals internals/path/schema.
- Likelihood: Medium
- Impact: Medium
- Current controls added in code:
  - Error masking in consult/blackbox handlers: `yangdo_consult_api.py:619`, `yangdo_consult_api.py:649`, `yangdo_blackbox_api.py:1924`, `yangdo_blackbox_api.py:1934`

### TM-05 Data integrity poisoning of permit criteria source (Medium)
- Affected assets: A3
- Abuse path: rule source URL spoofing or non-official source inclusion.
- Likelihood: Medium
- Impact: High
- Existing controls observed:
  - Objective source host filter: `permit_diagnosis_calculator.py:14`, `permit_diagnosis_calculator.py:87`, `permit_diagnosis_calculator.py:129`

## Existing Controls (Observed)
- Endpoint URL sanitization for generated calculator links: `acquisition_calculator.py:13`
- Safe JSON embedding helper usage: `acquisition_calculator.py:8`, `permit_diagnosis_calculator.py:21`
- New API hardening helper module:
  - security headers baseline: `security_http.py:9`
  - auth token comparison (`hmac.compare_digest`): `security_http.py:51`
  - forwarded/client IP normalization: `security_http.py:60`
  - in-memory DDoS throttling primitive: `security_http.py:82`

## Mitigation Roadmap

### Phase 0 (Immediately applied in this repo)
- App-layer auth gate (`X-API-Key` or `Authorization: Bearer`)
- Per-IP sliding window rate limiting
- Request body cap and content-type validation
- CORS allowlist mode
- Security response headers
- Internal exception masking

### Phase 1 (Infra, required for true DDoS hardening)
- Place both APIs behind Cloudflare or equivalent reverse proxy with:
  - managed WAF rules
  - bot management
  - IP reputation block
  - country/ASN based rate policies
- Keep origin server private (allow only proxy egress IPs)
- Enforce TLS1.2+ and certificate rotation

### Phase 2 (Key theft and account abuse hardening)
- Rotate API keys every 30 days (overlap window)
- Split keys by tenant/site and by privilege (`public`, `admin`, `batch`)
- Move secrets from `.env` files to secret manager
- Add audit log for auth failures and key usage per tenant

### Phase 3 (Data protection and resilience)
- Encrypt SQLite at rest or move to managed encrypted DB
- Encrypt backups and apply retention policy
- Add WORM-like append-only audit trail for admin actions (`/reload`, rule update)
- Add anomaly detection on request spikes and failure ratios

## Residual Risk
- Application-level rate limiting alone does not stop volumetric L3/L4 DDoS.
- If API keys are embedded in public front-end code, theft risk remains.
- Local plaintext secret files remain a compromise risk until secret manager migration.

## Assumptions
- APIs are internet-exposed or reverse-proxied for public widget usage.
- Multi-tenant partner expansion will reuse the same core APIs.
- No existing external WAF policy is enforced yet (must be verified).
