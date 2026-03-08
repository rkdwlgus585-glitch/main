#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.widget_health_contract import load_widget_health_contract


def _request(
    method: str,
    url: str,
    *,
    payload: Dict[str, object] | None = None,
    api_key: str = "",
    origin: str = "",
    host: str = "",
    request_id: str = "",
    timeout: int = 15,
) -> Tuple[int, Dict[str, str], str]:
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-Request-Id": request_id or uuid.uuid4().hex,
    }
    if api_key:
        headers["X-API-Key"] = api_key
    if origin:
        headers["Origin"] = origin
    if host:
        headers["Host"] = host
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), dict(resp.headers.items()), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return int(exc.code), dict(exc.headers.items()), exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        body = {"ok": False, "error": "request_failed", "details": str(exc.reason or exc)}
        return 0, {}, json.dumps(body, ensure_ascii=False)
    except Exception as exc:
        body = {"ok": False, "error": "request_failed", "details": str(exc)}
        return 0, {}, json.dumps(body, ensure_ascii=False)


def _json_loads(text: str) -> Dict[str, object]:
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _build_payload(service: str, channel_id: str) -> Dict[str, object]:
    request_block = {
        "channel_id": channel_id,
        "requested_at": "2026-03-06T12:00:00+09:00",
        "source": "partner_smoke",
        "request_id": f"smoke_{uuid.uuid4().hex[:12]}",
    }
    if service == "permit":
        return {
            "request": request_block,
            "selector": {"service_code": "09_27_03_P"},
            "inputs": {
                "capital_eok": 0.3,
                "technicians_count": 1,
                "office_secured": True,
            },
        }
    return {
        "request": request_block,
        "inputs": {
            "license_text": "건축공사업",
            "sales3_eok": 32.0,
            "capital_eok": 3.5,
            "specialty": 18.0,
            "ok_capital": True,
            "ok_engineer": True,
            "ok_office": True,
        },
    }


def _check(name: str, ok: bool, details: str = "") -> Dict[str, object]:
    row = {"name": str(name), "ok": bool(ok)}
    if details:
        row["details"] = str(details)
    return row


def _health_checks(status: int, headers: Dict[str, str], body: Dict[str, object]) -> List[Dict[str, object]]:
    expected_contract = load_widget_health_contract()
    health_contract = body.get("health_contract") if isinstance(body.get("health_contract"), dict) else {}
    expected_text = str(expected_contract.get("text") or "").strip()
    actual_text = str(health_contract.get("text") or "").strip()
    components = health_contract.get("components") if isinstance(health_contract, dict) else {}
    return [
        _check("http_status_ok", 200 <= int(status) < 500, f"status={status}"),
        _check("json_body", bool(body)),
        _check("body_ok", bool(body.get("ok"))),
        _check("header_api_version", bool(headers.get("X-Api-Version"))),
        _check("header_request_id", bool(headers.get("X-Request-Id"))),
        _check("health_contract_present", bool(health_contract)),
        _check("health_contract_text", bool(actual_text)),
        _check("health_contract_components", isinstance(components, dict) and bool(components)),
        _check("health_contract_match_local", bool(expected_text) and actual_text == expected_text),
    ]


def _service_checks(
    *,
    status: int,
    headers: Dict[str, str],
    body: Dict[str, object],
    request_id: str,
    channel_id: str,
) -> List[Dict[str, object]]:
    response_meta = body.get("response_meta") if isinstance(body.get("response_meta"), dict) else {}
    data_block = body.get("data") if isinstance(body.get("data"), dict) else {}
    header_request_id = str(headers.get("X-Request-Id") or "").strip()
    header_channel_id = str(headers.get("X-Channel-Id") or "").strip()
    meta_request_id = str(response_meta.get("request_id") or "").strip()
    meta_channel_id = str(response_meta.get("channel_id") or "").strip()
    body_request_id = str(body.get("request_id") or "").strip()
    body_channel_id = str(body.get("channel_id") or "").strip()
    return [
        _check("http_status_ok", 200 <= int(status) < 300, f"status={status}"),
        _check("json_body", bool(body)),
        _check("body_ok", bool(body.get("ok"))),
        _check("response_meta_present", bool(response_meta)),
        _check("data_present", bool(data_block)),
        _check("request_id_match", request_id in {header_request_id, meta_request_id, body_request_id}),
        _check("channel_id_match", (not channel_id) or channel_id in {header_channel_id, meta_channel_id, body_channel_id}),
        _check("header_api_version", bool(headers.get("X-Api-Version"))),
        _check("header_service_name", bool(headers.get("X-Service-Name"))),
        _check("header_response_tier", bool(headers.get("X-Response-Tier"))),
    ]


def run_smoke(
    *,
    base_url: str,
    service: str = "both",
    api_key: str = "",
    origin: str = "",
    host: str = "",
    channel_id: str = "seoul_web",
    timeout: int = 15,
) -> Dict[str, object]:
    base_url = str(base_url or "").rstrip("/")
    services = ["yangdo", "permit"] if service == "both" else [str(service)]
    results = []
    failed = False

    health_status, health_headers, health_body = _request(
        "GET",
        f"{base_url}/v1/health",
        api_key=str(api_key or ""),
        origin=str(origin or ""),
        host=str(host or ""),
        timeout=int(timeout),
    )
    health_json = _json_loads(health_body)
    health_checks = _health_checks(health_status, health_headers, health_json)
    health_ok = all(bool(item.get("ok")) for item in health_checks)
    results.append(
        {
            "kind": "health",
            "status": health_status,
            "ok": health_ok,
            "service": health_json.get("service"),
            "request_id": health_json.get("request_id"),
            "health_contract": health_json.get("health_contract"),
            "response_meta": health_json.get("response_meta"),
            "checks": health_checks,
            "headers": {
                "X-Api-Version": health_headers.get("X-Api-Version"),
                "X-Request-Id": health_headers.get("X-Request-Id"),
            },
        }
    )
    if not health_ok:
        failed = True

    for current_service in services:
        endpoint = "/v1/yangdo/estimate" if current_service == "yangdo" else "/v1/permit/precheck"
        payload = _build_payload(current_service, str(channel_id or ""))
        request_data = payload.get("request") if isinstance(payload.get("request"), dict) else {}
        request_id = str(request_data.get("request_id") or "")
        status, headers, body = _request(
            "POST",
            f"{base_url}{endpoint}",
            payload=payload,
            api_key=str(api_key or ""),
            origin=str(origin or ""),
            host=str(host or ""),
            request_id=request_id,
            timeout=int(timeout),
        )
        data = _json_loads(body)
        response_meta = data.get("response_meta") if isinstance(data.get("response_meta"), dict) else {}
        checks = _service_checks(
            status=status,
            headers=headers,
            body=data,
            request_id=request_id,
            channel_id=str(channel_id or ""),
        )
        service_ok = all(bool(item.get("ok")) for item in checks)
        results.append(
            {
                "kind": current_service,
                "status": status,
                "ok": service_ok,
                "error": data.get("error"),
                "service": data.get("service"),
                "channel_id": data.get("channel_id"),
                "response_meta": response_meta,
                "checks": checks,
                "headers": {
                    "X-Api-Version": headers.get("X-Api-Version"),
                    "X-Service-Name": headers.get("X-Service-Name"),
                    "X-Request-Id": headers.get("X-Request-Id"),
                    "X-Channel-Id": headers.get("X-Channel-Id"),
                    "X-Tenant-Plan": headers.get("X-Tenant-Plan"),
                    "X-Response-Tier": headers.get("X-Response-Tier"),
                },
            }
        )
        if not service_ok:
            failed = True

    return {"ok": not failed, "base_url": base_url, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run smoke checks against yangdo/permit partner API endpoints")
    parser.add_argument("--base-url", required=True, help="API base URL, e.g. https://calc.seoulmna.co.kr")
    parser.add_argument("--service", choices=["yangdo", "permit", "both"], default="both")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--origin", default="")
    parser.add_argument("--host", default="")
    parser.add_argument("--channel-id", default="seoul_web")
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()

    result = run_smoke(
        base_url=str(args.base_url or ""),
        service=str(args.service or "both"),
        api_key=str(args.api_key or ""),
        origin=str(args.origin or ""),
        host=str(args.host or ""),
        channel_id=str(args.channel_id or "seoul_web"),
        timeout=int(args.timeout),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if not bool(result.get("ok")) else 0


if __name__ == "__main__":
    raise SystemExit(main())
