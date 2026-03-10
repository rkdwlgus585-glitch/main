#!/usr/bin/env python3
"""
Publish a monthly market report draft to the notice board.

Behavior:
- Create or update the target month report.
- Set the target month post as notice.
- Unset the previous month report notice when found.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_ALL_ROOT = ROOT.parent / "ALL"                    # H:\ALL (non-core modules)
if str(_ALL_ROOT) not in sys.path:
    sys.path.insert(0, str(_ALL_ROOT))
load_dotenv(ROOT / ".env")

import all as listing_ops  # noqa: E402
from scripts import monthly_notice_rotation as notice_rotation  # noqa: E402
from scripts import review_monthly_market_report as market_review  # noqa: E402


DEFAULT_STATE = ROOT / "logs" / "monthly_market_report_publish_state.json"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "monthly_market_report"
DEFAULT_REVIEW_JSON = ROOT / "logs" / "monthly_market_report_review_latest.json"
DEFAULT_REVIEW_MD = ROOT / "logs" / "monthly_market_report_review_latest.md"


def _read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(_read_text(path))
    except Exception:
        return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _content_hash(subject: str, body: str) -> str:
    return hashlib.sha256(f"{subject}\n\n{body}".encode("utf-8")).hexdigest()


def _month_key(year: int, month: int) -> str:
    return f"{int(year):04d}-{int(month):02d}"


def _previous_month_key(month_key: str) -> str:
    y, m = notice_rotation.month_sort_key(month_key)
    if y <= 0 or m <= 0:
        return ""
    if m == 1:
        return f"{y - 1:04d}-12"
    return f"{y:04d}-{m - 1:02d}"


def _extract_wr_id(url: str, board_slug: str) -> int | None:
    src = str(url or "").strip()
    if not src:
        return None
    parsed = urlparse(src)
    qs = parse_qs(parsed.query)
    wr = (qs.get("wr_id") or [""])[0]
    if str(wr).isdigit():
        return int(wr)
    match = re.search(rf"/{re.escape(board_slug)}/(\d+)(?:$|[/?#])", parsed.path or "")
    if match:
        return int(match.group(1))
    return None


def _month_subject_tokens(month_key: str) -> list[str]:
    y, m = notice_rotation.month_sort_key(month_key)
    if y <= 0 or m <= 0:
        return []
    yy = y % 100
    return [
        f"{yy}년 {m}월",
        f"{yy}년 {m:02d}월",
        f"{y}년 {m}월",
        f"{y}년 {m:02d}월",
        f"{y}-{m:02d}",
    ]


def _extract_wr_id_from_href(href: str, board_slug: str) -> int | None:
    match = re.search(r"[?&]wr_id=(\d+)", str(href or ""))
    if match:
        return int(match.group(1))
    match = re.search(rf"/{re.escape(board_slug)}/(\d+)(?:$|[/?#])", str(href or ""))
    if match:
        return int(match.group(1))
    return None


def _find_existing_market_report(publisher, board_slug: str, month_key: str, max_pages: int = 5) -> int | None:
    tokens = _month_subject_tokens(month_key)
    if not tokens:
        return None
    for page in range(1, max_pages + 1):
        url = f"{publisher.site_url}/bbs/board.php?bo_table={board_slug}"
        if page > 1:
            url += f"&page={page}"
        try:
            res = publisher.get(url, timeout=20)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, "html.parser")
            for anchor in soup.select("a[href]"):
                title = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))
                href = str(anchor.get("href", "")).strip()
                wr_id = _extract_wr_id_from_href(href, board_slug)
                if not wr_id or not title:
                    continue
                if any(token in title for token in tokens) and any(key in title for key in ("리포트", "전망", "시장")):
                    return wr_id
        except Exception:
            continue
    return None


def _get_notice_write_form(publisher, board_slug: str, wr_id: int | None = None):
    if wr_id and int(wr_id) > 0:
        url = f"{publisher.site_url}/bbs/write.php?bo_table={board_slug}&w=u&wr_id={int(wr_id)}"
    else:
        url = f"{publisher.site_url}/bbs/write.php?bo_table={board_slug}"
    res = publisher.get(url, timeout=20)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    form = publisher._find_form(soup)  # noqa: SLF001
    if not form:
        raise RuntimeError("notice 글쓰기 폼을 찾지 못했습니다")
    action = form.get("action") or "/bbs/write_update.php"
    action_url = urljoin(res.url, action)
    payload = publisher._collect_form_defaults(form)  # noqa: SLF001
    return action_url, payload


def parse_args() -> argparse.Namespace:
    now = datetime.now()
    parser = argparse.ArgumentParser(description="Publish monthly market report HTML to notice board.")
    parser.add_argument("--year", type=int, default=now.year)
    parser.add_argument("--month", type=int, default=now.month)
    parser.add_argument("--state-file", default=str(DEFAULT_STATE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--board-slug", default=os.getenv("NOTICE_BOARD_SLUG", "notice"))
    parser.add_argument("--site-url", default=os.getenv("SITE_URL", "https://seoulmna.co.kr"))
    parser.add_argument("--discover-pages", type=int, default=5)
    parser.add_argument("--write-buffer", type=int, default=12)
    parser.add_argument("--review-report-json", default=str(DEFAULT_REVIEW_JSON))
    parser.add_argument("--review-report-md", default=str(DEFAULT_REVIEW_MD))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    month_key = _month_key(args.year, args.month)
    month_dir = Path(args.output_dir) / f"{args.year:04d}_{args.month:02d}"
    subject_path = month_dir / f"market_report_{args.year:04d}_{args.month:02d}_subject.txt"
    body_path = month_dir / f"market_report_{args.year:04d}_{args.month:02d}_body.html"
    source_snapshot_path = month_dir / f"market_report_{args.year:04d}_{args.month:02d}_source_snapshot.json"
    if not subject_path.exists() or not body_path.exists():
        print(f"[error] draft missing: {month_dir}")
        return 1

    subject = _read_text(subject_path).strip()
    body = _read_text(body_path)
    digest = _content_hash(subject, body)
    review_result = market_review.review_bundle(
        subject_path,
        body_path,
        month_key,
        source_snapshot_path=source_snapshot_path,
    )
    review_report = market_review.build_review_report(review_result)
    market_review.write_review_report(
        Path(args.review_report_json),
        Path(args.review_report_md),
        review_report,
    )
    if review_result.get("status") != "pass":
        print(
            "[error] review failed: "
            + ", ".join(review_result.get("blocking_issues", []) or ["unknown_review_error"])
        )
        return 1

    state_path = Path(args.state_file)
    state = _load_json(state_path, {"months": {}, "updated_at": ""})
    month_state = state.get("months", {}) if isinstance(state.get("months", {}), dict) else {}
    entry = dict(month_state.get(month_key, {}) or {})
    board_slug = str(args.board_slug or "").strip() or "notice"
    site_url = str(args.site_url or "").rstrip("/")

    current_wr_id = int(entry.get("wr_id", 0) or 0)
    if current_wr_id <= 0 and str(entry.get("url", "")).strip():
        current_wr_id = _extract_wr_id(str(entry.get("url", "")).strip(), board_slug) or 0

    if args.dry_run:
        print(
            f"[plan] month={month_key} current_wr_id={current_wr_id} "
            f"review_ok={review_report.get('ok')} subject={subject}"
        )
        prev_key = notice_rotation.pick_previous_notice_month(month_state, month_key) or _previous_month_key(month_key)
        print(f"[plan] previous_month={prev_key or '-'}")
        return 0

    if (
        current_wr_id > 0
        and str(entry.get("content_hash", "")).strip() == digest
        and bool(entry.get("notice_enabled"))
    ):
        print(f"[skip] unchanged month={month_key} wr_id={current_wr_id}")
        return 0

    admin_id = os.getenv("ADMIN_ID", "")
    admin_pw = os.getenv("ADMIN_PW", "")
    if not admin_id or not admin_pw:
        print("[error] ADMIN_ID/ADMIN_PW missing")
        return 1

    publisher = listing_ops.MnaBoardPublisher(site_url, board_slug, admin_id, admin_pw)
    publisher.login()
    limit = publisher.daily_limit_summary()
    write_cap = int(limit.get("write_cap", 0) or 0)
    write_used = int(limit.get("writes", 0) or 0)
    write_remaining = max(0, write_cap - write_used) if write_cap > 0 else 10
    safe_remaining = max(0, write_remaining - max(0, int(args.write_buffer or 0))) if write_cap > 0 else 10
    if safe_remaining <= 0:
        print("[skip] write budget exhausted")
        return 0

    if current_wr_id <= 0:
        current_wr_id = _find_existing_market_report(
            publisher,
            board_slug,
            month_key,
            max_pages=max(1, int(args.discover_pages)),
        ) or 0

    mode = "update" if current_wr_id > 0 else "create"
    if current_wr_id > 0:
        action_url, payload = _get_notice_write_form(publisher, board_slug, wr_id=current_wr_id)
        payload = notice_rotation.set_notice_flag(payload, enabled=True)
        out = publisher.submit_edit_updates(action_url, payload, {"wr_subject": subject, "wr_content": body})
        final_url = str(out.get("url", "")).strip() or f"{site_url}/{board_slug}/{current_wr_id}"
        out_wr_id = _extract_wr_id(final_url, board_slug) or current_wr_id
        if "/bbs/write.php" in final_url:
            final_url = f"{site_url}/{board_slug}/{int(out_wr_id)}"
    else:
        action_url, payload = _get_notice_write_form(publisher, board_slug, wr_id=None)
        payload = notice_rotation.set_notice_flag(payload, enabled=True)
        payload["bo_table"] = board_slug
        payload["wr_subject"] = subject
        payload["wr_content"] = body
        if "wr_name" in payload and not str(payload.get("wr_name", "")).strip():
            payload["wr_name"] = listing_ops.MY_COMPANY_NAME
        out = publisher._submit_write(action_url, payload)  # noqa: SLF001
        final_url = str(out.get("url", "")).strip()
        out_wr_id = _extract_wr_id(final_url, board_slug)
        if not out_wr_id:
            discovered = _find_existing_market_report(publisher, board_slug, month_key, max_pages=max(5, int(args.discover_pages)))
            if not discovered:
                raise RuntimeError(f"wr_id parse failed from url: {final_url}")
            out_wr_id = int(discovered)
        if (not final_url) or ("/bbs/write.php" in final_url):
            final_url = f"{site_url}/{board_slug}/{int(out_wr_id)}"

    prev_key = notice_rotation.pick_previous_notice_month(month_state, month_key)
    prev_wr_id = 0
    if prev_key:
        prev_wr_id = int((month_state.get(prev_key, {}) or {}).get("wr_id", 0) or 0)
    if prev_wr_id <= 0:
        prev_key = _previous_month_key(month_key)
        if prev_key:
            prev_wr_id = _find_existing_market_report(publisher, board_slug, prev_key, max_pages=max(1, int(args.discover_pages))) or 0

    if prev_wr_id > 0 and prev_wr_id != int(out_wr_id):
        prev_action_url, prev_payload = _get_notice_write_form(publisher, board_slug, wr_id=prev_wr_id)
        prev_payload = notice_rotation.set_notice_flag(prev_payload, enabled=False)
        publisher.submit_edit_updates(prev_action_url, prev_payload, {})
        prev_entry = dict(month_state.get(prev_key, {}) or {})
        prev_entry["wr_id"] = int(prev_wr_id)
        prev_entry["notice_enabled"] = False
        prev_entry["last_notice_rotated_at"] = datetime.now().isoformat(timespec="seconds")
        month_state[prev_key] = prev_entry
        print(f"[ok] previous month unpinned: {prev_key} wr_id={prev_wr_id}")

    month_state[month_key] = {
        "wr_id": int(out_wr_id),
        "url": final_url or f"{site_url}/{board_slug}/{int(out_wr_id)}",
        "subject_path": str(subject_path),
        "body_path": str(body_path),
        "content_hash": digest,
        "notice_enabled": True,
        "last_mode": mode,
        "last_synced_at": datetime.now().isoformat(timespec="seconds"),
    }
    state["months"] = month_state
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _save_json(state_path, state)
    print(f"[ok] {month_key} {mode} wr_id={int(out_wr_id)}")
    print(f"[saved] {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
