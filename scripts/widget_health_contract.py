#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DASHBOARD_PATH = ROOT / "logs" / "ai_admin_dashboard_latest.json"


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def load_widget_health_contract(dashboard_path: Path | None = None) -> Dict[str, Any]:
    path = Path(dashboard_path or DEFAULT_DASHBOARD_PATH).resolve()
    dashboard = _read_json(path)
    one_line = dict(dashboard.get("one_line_summary") or {})
    components = dict(one_line.get("components") or {})
    payload = {
        "ok": bool(one_line.get("ok")),
        "text": str(one_line.get("text") or "").strip(),
        "components": {str(k): bool(v) for k, v in components.items()},
        "generated_at": str(dashboard.get("generated_at") or ""),
        "source": str(path),
    }
    if not payload["text"]:
        payload["ok"] = False
        payload["text"] = "CHECK | widgetHealth=missing-dashboard"
    return payload

