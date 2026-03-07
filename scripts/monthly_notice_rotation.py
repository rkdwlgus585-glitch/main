from __future__ import annotations

import re


def month_sort_key(month_key: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{4})-(\d{2})", str(month_key or "").strip())
    if not match:
        return (0, 0)
    return (int(match.group(1)), int(match.group(2)))


def pick_previous_notice_month(month_state: dict, current_month_key: str) -> str:
    current_key = month_sort_key(current_month_key)
    candidates: list[tuple[tuple[int, int], str]] = []
    for month_key, row in (month_state or {}).items():
        key = month_sort_key(month_key)
        if key >= current_key:
            continue
        if int((row or {}).get("wr_id", 0) or 0) <= 0:
            continue
        if (row or {}).get("notice_enabled") is False:
            continue
        candidates.append((key, str(month_key)))
    if not candidates:
        return ""
    candidates.sort(reverse=True)
    return candidates[0][1]


def set_notice_flag(payload: dict, enabled: bool, *, field_name: str = "notice", field_value: str = "1") -> dict:
    out = dict(payload or {})
    if enabled:
        out[field_name] = str(field_value)
    else:
        out.pop(field_name, None)
    return out
