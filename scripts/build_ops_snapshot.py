#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
TXT_OUT = LOGS / "ops_snapshot_latest.txt"
JSON_OUT = LOGS / "ops_snapshot_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _latest_patent_bundle() -> Tuple[str, str]:
    base = ROOT / "snapshots" / "patent_handoff"
    if not base.exists() or not base.is_dir():
        return "", ""

    candidates: List[Path] = []
    for item in base.iterdir():
        if item.is_dir() and item.name.startswith("patent_handoff_"):
            candidates.append(item)
    if not candidates:
        return "", ""

    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    zip_path = latest.with_suffix(".zip")
    return str(latest), str(zip_path if zip_path.exists() else "")


def build_snapshot() -> Dict[str, Any]:
    security = _load_json(LOGS / "security_do_all_latest.json")
    monthly = _load_json(LOGS / "monthly_security_rehearsal_latest.json")
    policy = _load_json(LOGS / "tenant_policy_actions_latest.json")
    usage = _load_json(LOGS / "tenant_usage_billing_latest.json")

    sec_steps = security.get("steps") if isinstance(security.get("steps"), list) else []
    sec_fail = [s for s in sec_steps if isinstance(s, dict) and not bool(s.get("ok"))]

    monthly_steps = monthly.get("steps") if isinstance(monthly.get("steps"), list) else []
    monthly_fail = [s for s in monthly_steps if isinstance(s, dict) and not bool(s.get("ok"))]

    policy_summary = policy.get("summary") if isinstance(policy.get("summary"), dict) else {}
    usage_summary = usage.get("summary") if isinstance(usage.get("summary"), dict) else {}
    monthly_publish = monthly.get("publish") if isinstance(monthly.get("publish"), dict) else {}

    bundle_dir, bundle_zip = _latest_patent_bundle()

    payload: Dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "security_do_all": {
            "ok": bool(security.get("ok", False)),
            "generated_at": str(security.get("generated_at") or ""),
            "step_count": len(sec_steps),
            "fail_count": len(sec_fail),
            "failed_steps": [str(s.get("name") or "") for s in sec_fail][:10],
        },
        "monthly_rehearsal": {
            "ok": bool(monthly.get("ok", False)),
            "generated_at": str(monthly.get("generated_at") or ""),
            "step_count": len(monthly_steps),
            "fail_count": len(monthly_fail),
            "failed_steps": [str(s.get("name") or "") for s in monthly_fail][:10],
            "publish_should_send": bool(monthly_publish.get("should_send", False)),
            "publish_sent": bool(monthly_publish.get("sent", False)),
            "publish_reason": str(monthly_publish.get("reason") or ""),
            "ticket_md": str(monthly_publish.get("ticket_md") or ""),
        },
        "tenant_policy": {
            "action_count": int(policy_summary.get("action_count") or 0),
            "unresolved_action_count": int(policy_summary.get("unresolved_action_count") or 0),
            "high_severity_count": int(policy_summary.get("high_severity_count") or 0),
        },
        "usage": {
            "usage_row_count": int(usage_summary.get("usage_row_count") or 0),
            "total_estimated_tokens": int(usage_summary.get("total_estimated_tokens") or 0),
            "action_required_count": int(usage_summary.get("action_required_count") or 0),
        },
        "patent_bundle": {
            "latest_dir": bundle_dir,
            "latest_zip": bundle_zip,
        },
    }
    return payload


def to_text(payload: Dict[str, Any]) -> str:
    s = payload.get("security_do_all", {})
    m = payload.get("monthly_rehearsal", {})
    p = payload.get("tenant_policy", {})
    u = payload.get("usage", {})
    b = payload.get("patent_bundle", {})

    lines = [
        "SeoulMNA 운영 핵심 요약",
        f"생성시각: {payload.get('generated_at', '')}",
        "",
        "[1] 전체 보안 실행(security_do_all)",
        f"- 상태: {'정상' if bool(s.get('ok')) else '주의'}",
        f"- 실행시각: {s.get('generated_at', '')}",
        f"- 단계수: {s.get('step_count', 0)}",
        f"- 실패단계수: {s.get('fail_count', 0)}",
        f"- 실패단계: {', '.join(s.get('failed_steps', [])) if s.get('failed_steps') else '없음'}",
        "",
        "[2] 월간 리허설",
        f"- 상태: {'정상' if bool(m.get('ok')) else '주의'}",
        f"- 실행시각: {m.get('generated_at', '')}",
        f"- 단계수: {m.get('step_count', 0)}",
        f"- 실패단계수: {m.get('fail_count', 0)}",
        f"- 알림전송조건: {'예' if bool(m.get('publish_should_send')) else '아니오'}",
        f"- 알림전송결과: {'성공' if bool(m.get('publish_sent')) else '미전송/실패'}",
        f"- 알림사유: {m.get('publish_reason', '')}",
        f"- 티켓요약파일: {m.get('ticket_md', '')}",
        "",
        "[3] 테넌트 정책",
        f"- action_count: {p.get('action_count', 0)}",
        f"- unresolved_action_count: {p.get('unresolved_action_count', 0)}",
        f"- high_severity_count: {p.get('high_severity_count', 0)}",
        "",
        "[4] 사용량",
        f"- usage_row_count: {u.get('usage_row_count', 0)}",
        f"- total_estimated_tokens: {u.get('total_estimated_tokens', 0)}",
        f"- action_required_count: {u.get('action_required_count', 0)}",
        "",
        "[5] 특허 번들",
        f"- 최신폴더: {b.get('latest_dir', '') or '없음'}",
        f"- 최신ZIP: {b.get('latest_zip', '') or '없음'}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = build_snapshot()

    LOGS.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8-sig")
    text = to_text(payload)
    TXT_OUT.write_text(text, encoding="utf-8-sig")

    print(json.dumps({"ok": True, "text": str(TXT_OUT), "json": str(JSON_OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
