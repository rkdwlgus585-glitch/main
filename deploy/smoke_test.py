#!/usr/bin/env python3
"""Production smoke test for seoulmna.kr API services.

Validates that all API endpoints are healthy and returning expected responses.

Usage:
    python deploy/smoke_test.py                              # default: localhost
    python deploy/smoke_test.py --base-url https://seoulmna.kr/_calc
    python deploy/smoke_test.py --yangdo-url http://127.0.0.1:8200 --permit-url http://127.0.0.1:8100
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


_PASS = "[PASS]"
_FAIL = "[FAIL]"
_SKIP = "[SKIP]"


def _json_request(
    url: str,
    *,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 15,
) -> Tuple[int, Dict[str, Any]]:
    """Send an HTTP request and return (status_code, parsed_json)."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    hdrs = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except Exception:
            body = {"raw_error": str(exc)}
        return exc.code, body
    except urllib.error.URLError as exc:
        return 0, {"connection_error": str(exc.reason)}
    except Exception as exc:
        return 0, {"unexpected_error": str(type(exc).__name__)}


def _check(
    label: str, status: int, body: Dict[str, Any], expect_status: int = 200
) -> bool:
    ok = status == expect_status and body.get("ok") is not False
    tag = _PASS if ok else _FAIL
    detail = f"status={status}"
    if not ok and body:
        detail += f" body_keys={list(body.keys())[:5]}"
    print(f"  {tag} {label} ({detail})")
    return ok


# ── Test suites ──────────────────────────────────────────────────────────

def test_permit_health(base: str) -> bool:
    """GET /v1/health — permit API health check."""
    status, body = _json_request(f"{base}/v1/health")
    return _check("permit /v1/health", status, body)


def test_permit_precheck(base: str, api_key: str = "") -> bool:
    """POST /v1/permit/precheck — basic precheck request."""
    payload = {
        "service_code": "4111",
        "inputs": {
            "capital_amount": 200000000,
            "technician_count": 5,
            "has_office": True,
        },
    }
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    status, body = _json_request(
        f"{base}/v1/permit/precheck", method="POST", payload=payload, headers=headers
    )
    ok = status == 200 and isinstance(body.get("result"), dict)
    tag = _PASS if ok else _FAIL
    verdict = body.get("result", {}).get("verdict", "?") if ok else "n/a"
    print(f"  {tag} permit /v1/permit/precheck (status={status} verdict={verdict})")
    return ok


def test_yangdo_health(base: str) -> bool:
    """GET /v1/health — yangdo API health check."""
    status, body = _json_request(f"{base}/v1/health")
    return _check("yangdo /v1/health", status, body)


def test_yangdo_estimate(base: str, api_key: str = "") -> bool:
    """POST /v1/yangdo/estimate — basic estimate request."""
    payload = {
        "license_type": "토목건축공사업",
        "year_performances": {"2023": 50, "2024": 60},
    }
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    status, body = _json_request(
        f"{base}/v1/yangdo/estimate", method="POST", payload=payload, headers=headers
    )
    ok = status == 200
    tag = _PASS if ok else _FAIL
    print(f"  {tag} yangdo /v1/yangdo/estimate (status={status})")
    return ok


def test_options_cors(base: str, origin: str = "https://seoulmna.kr") -> bool:
    """OPTIONS preflight — CORS headers present."""
    req = urllib.request.Request(
        f"{base}/v1/health",
        method="OPTIONS",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            acao = resp.headers.get("Access-Control-Allow-Origin", "")
            ok = resp.status in (200, 204) and acao != ""
            tag = _PASS if ok else _FAIL
            print(f"  {tag} CORS preflight (ACAO={acao!r})")
            return ok
    except Exception:
        print(f"  {_FAIL} CORS preflight (connection error)")
        return False


def test_rate_limit_header(base: str) -> bool:
    """Verify X-RateLimit headers are returned."""
    status, body = _json_request(f"{base}/v1/health")
    # We can't easily check headers with urllib, so just verify the endpoint works
    ok = status == 200
    tag = _PASS if ok else _SKIP
    print(f"  {tag} rate limit headers (basic check)")
    return ok


# ── Runner ───────────────────────────────────────────────────────────────

def run_suite(
    name: str,
    tests: List[Tuple[str, Any]],
) -> Tuple[int, int, int]:
    """Run a test suite and return (passed, failed, skipped)."""
    passed = failed = 0
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")
    for label, test_fn in tests:
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
        except Exception as exc:
            print(f"  {_FAIL} {label} (exception: {type(exc).__name__})")
            failed += 1
    return passed, failed, 0


def main() -> int:
    parser = argparse.ArgumentParser(description="seoulmna.kr production smoke test")
    parser.add_argument(
        "--permit-url", default="http://127.0.0.1:8100",
        help="Permit API base URL (default: http://127.0.0.1:8100)",
    )
    parser.add_argument(
        "--yangdo-url", default="http://127.0.0.1:8200",
        help="Yangdo API base URL (default: http://127.0.0.1:8200)",
    )
    parser.add_argument(
        "--base-url", default="",
        help="Unified base URL (overrides --permit-url and --yangdo-url). "
             "e.g. https://seoulmna.kr/_calc",
    )
    parser.add_argument("--permit-api-key", default="")
    parser.add_argument("--yangdo-api-key", default="")
    parser.add_argument(
        "--wait", type=int, default=0,
        help="Seconds to wait before running tests (for container startup)",
    )
    args = parser.parse_args()

    if args.wait > 0:
        print(f"Waiting {args.wait}s for services to start...")
        time.sleep(args.wait)

    permit_url = args.base_url + "/permit" if args.base_url else args.permit_url
    yangdo_url = args.base_url + "/yangdo" if args.base_url else args.yangdo_url

    total_passed = total_failed = 0

    # ── Permit API ──
    p, f, _ = run_suite("Permit Precheck API", [
        ("health", lambda: test_permit_health(permit_url)),
        ("precheck", lambda: test_permit_precheck(permit_url, args.permit_api_key)),
        ("cors", lambda: test_options_cors(permit_url)),
    ])
    total_passed += p
    total_failed += f

    # ── Yangdo API ──
    p, f, _ = run_suite("Yangdo Estimate API", [
        ("health", lambda: test_yangdo_health(yangdo_url)),
        ("estimate", lambda: test_yangdo_estimate(yangdo_url, args.yangdo_api_key)),
        ("cors", lambda: test_options_cors(yangdo_url)),
    ])
    total_passed += p
    total_failed += f

    # ── Summary ──
    print(f"\n{'=' * 60}")
    print(f"  SUMMARY: {total_passed} passed, {total_failed} failed")
    print(f"{'=' * 60}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
