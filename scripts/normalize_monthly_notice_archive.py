#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "output" / "notice_archive" / "notice_archive_manifest.json"
LEGAL_NOTICE_HTML = (
    '<div data-notice-legal="1" style="margin-top: 14px; padding: 14px 16px; border-radius: 10px; '
    'background: #fff7ed; border: 1px solid #fed7aa; color: #7c2d12; font-size: 15px; line-height: 1.7;">'
    '<strong style="font-weight: 800;">안내</strong> 본 공지는 검색·비교 편의를 위한 월간 요약 자료입니다. '
    "최종 거래 조건과 양도가, 법무·세무 판단은 계약 및 실사 이후 확정됩니다."
    "</div>"
)


def _read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(_read_text(path))
    except Exception:
        return default


def _has_legal_notice(text: str) -> bool:
    src = re.sub(r"\s+", " ", str(text or ""))
    required = ["최종 거래 조건", "법무", "세무", "계약", "실사", "확정"]
    return all(token in src for token in required)


def _normalize_listing_title(title: str) -> str:
    raw = re.sub(r"\s+", " ", str(title or "")).strip()
    if not raw.startswith("[") or "|" not in raw:
        return raw
    inner = raw[1:-1] if raw.endswith("]") else raw[1:]
    parts = [part.strip() for part in inner.split("|")]
    if len(parts) < 2:
        return raw
    if not any(re.search(r"양도\b", part) for part in parts[1:]):
        parts.insert(1, "건설업 양도")
    return "[" + " | ".join(parts) + "]"


def _ensure_body_compliance(body_path: Path) -> dict[str, int]:
    body = _read_text(body_path)
    soup = BeautifulSoup(body, "html.parser")
    changed = 0
    listing_titles_fixed = 0
    image_alt_fixed = 0
    legal_inserted = 0

    plain_text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    if not _has_legal_notice(plain_text):
        target = soup.find("h2")
        legal_fragment = BeautifulSoup(LEGAL_NOTICE_HTML, "html.parser")
        legal_node = legal_fragment.find(attrs={"data-notice-legal": "1"}) or legal_fragment.find("div")
        if legal_node is not None:
            if target is not None:
                target.insert_before(legal_node)
            elif soup.div is not None:
                soup.div.append(legal_node)
            else:
                soup.append(legal_node)
            legal_inserted = 1
            changed = 1

    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href", "")).strip()
        if "/mna/" not in href:
            continue
        before = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))
        after = _normalize_listing_title(before)
        if before != after:
            anchor.string = after
            listing_titles_fixed += 1
            changed = 1

    for img in soup.select("img"):
        alt = str(img.get("alt", "")).strip()
        if alt:
            continue
        img["alt"] = "서울건설정보 건설업 양도양수 안내 이미지"
        image_alt_fixed += 1
        changed = 1

    if changed:
        body_path.write_text(str(soup), encoding="utf-8")

    return {
        "changed": changed,
        "legal_inserted": legal_inserted,
        "listing_titles_fixed": listing_titles_fixed,
        "image_alt_fixed": image_alt_fixed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize monthly notice archive bundles before review/publish.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--month-key", default="", help="Only normalize one month key (YYYY-MM).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = _load_json(Path(args.manifest), {})
    months = list(manifest.get("months", []) or [])
    only_month = str(args.month_key or "").strip()
    if only_month:
        months = [row for row in months if str(row.get("month_key", "")).strip() == only_month]
    if not months:
        print("[skip] manifest months empty")
        return 0

    total_changed = 0
    for row in months:
        month_key = str(row.get("month_key", "")).strip()
        body_path = Path(str(row.get("body", "")).strip())
        if not month_key or not body_path.exists():
            continue
        result = _ensure_body_compliance(body_path)
        total_changed += int(result.get("changed", 0) or 0)
        print(
            f"[normalize] {month_key} changed={result['changed']} legal_inserted={result['legal_inserted']} "
            f"listing_titles_fixed={result['listing_titles_fixed']} image_alt_fixed={result['image_alt_fixed']}"
        )
    print(f"[done] normalized={total_changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
