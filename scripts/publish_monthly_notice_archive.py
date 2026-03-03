#!/usr/bin/env python3
"""
Publish monthly notice archive bundles to seoulmna.co.kr notice board.

Behavior:
- One post per month key (e.g. 2026-02, 2026-03).
- If month already has wr_id in state, update that post.
- If month has no wr_id, create a new post.
- Skip unchanged months by content hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import all as listing_ops  # noqa: E402


DEFAULT_MANIFEST = ROOT / "output" / "notice_archive" / "notice_archive_manifest.json"
DEFAULT_STATE = ROOT / "logs" / "notice_publish_state.json"


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
    payload = f"{subject}\n\n{body}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _extract_wr_id(url: str, board_slug: str) -> int | None:
    u = str(url or "").strip()
    if not u:
        return None

    try:
        parsed = urlparse(u)
        qs = parse_qs(parsed.query)
        wr = (qs.get("wr_id") or [""])[0]
        if str(wr).isdigit():
            return int(wr)

        m = re.search(rf"/{re.escape(board_slug)}/(\d+)(?:$|[/?#])", parsed.path or "")
        if m:
            return int(m.group(1))

        tail = re.search(r"/(\d+)(?:$|[/?#])", parsed.path or "")
        if tail:
            return int(tail.group(1))
    except Exception:
        return None
    return None


def _month_sort_key(month_key: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d{4})-(\d{2})", str(month_key or "").strip())
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2)))


def _get_notice_write_form(publisher, board_slug: str, wr_id: int | None = None):
    if wr_id and int(wr_id) > 0:
        url = f"{publisher.site_url}/bbs/write.php?bo_table={board_slug}&w=u&wr_id={int(wr_id)}"
    else:
        url = f"{publisher.site_url}/bbs/write.php?bo_table={board_slug}"

    res = publisher.get(url, timeout=20)
    res.raise_for_status()
    if "글을 쓸 권한이 없습니다" in str(res.text):
        raise RuntimeError("글쓰기 권한이 없습니다")

    soup = BeautifulSoup(res.text, "html.parser")
    form = publisher._find_form(soup)  # noqa: SLF001
    if not form:
        raise RuntimeError("notice 글쓰기 폼을 찾지 못했습니다")

    action = form.get("action") or "/bbs/write_update.php"
    action_url = urljoin(res.url, action)
    payload = publisher._collect_form_defaults(form)  # noqa: SLF001
    return action_url, payload


def _month_subject_tokens(month_key: str) -> list[str]:
    y, m = _month_sort_key(month_key)
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
    h = str(href or "").strip()
    if not h:
        return None
    m = re.search(r"[?&]wr_id=(\d+)", h)
    if m:
        return int(m.group(1))
    m = re.search(rf"/{re.escape(board_slug)}/(\d+)(?:$|[/?#])", h)
    if m:
        return int(m.group(1))
    return None


def _find_existing_month_post(publisher, board_slug: str, month_key: str, max_pages: int = 3) -> int | None:
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
            for a in soup.select("a[href]"):
                href = str(a.get("href", "")).strip()
                title = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
                if not href or not title:
                    continue
                wr_id = _extract_wr_id_from_href(href, board_slug)
                if not wr_id:
                    continue
                if any(tok in title for tok in tokens) and ("매물" in title or "양도" in title):
                    return wr_id
        except Exception:
            continue
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish notice archive bundles to seoul notice board.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--state-file", default=str(DEFAULT_STATE))
    parser.add_argument("--board-slug", default=os.getenv("NOTICE_BOARD_SLUG", "notice"))
    parser.add_argument("--site-url", default=os.getenv("SITE_URL", "https://seoulmna.co.kr"))
    parser.add_argument("--max-writes", type=int, default=2, help="Max writes per run (0=unlimited).")
    parser.add_argument("--write-buffer", type=int, default=12, help="Keep this many write slots as safety buffer.")
    parser.add_argument("--delay-sec", type=float, default=1.5, help="Delay between write requests.")
    parser.add_argument(
        "--min-update-days",
        type=float,
        default=float(os.getenv("NOTICE_SYNC_MIN_UPDATE_DAYS", "7") or 7),
        help="Minimum days between updates for an already published month post.",
    )
    parser.add_argument("--discover-pages", type=int, default=3, help="Pages to scan when discovering existing month post.")
    parser.add_argument("--month-key", default="", help="Only sync a specific month key (YYYY-MM).")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    state_path = Path(args.state_file)
    board_slug = str(args.board_slug or "").strip() or "notice"
    site_url = str(args.site_url or "").rstrip("/")
    max_writes = max(0, int(args.max_writes or 0))
    write_buffer = max(0, int(args.write_buffer or 0))
    delay_sec = max(0.0, float(args.delay_sec or 0.0))
    min_update_days = max(0.0, float(args.min_update_days or 0.0))
    discover_pages = max(1, int(args.discover_pages or 3))
    only_month = str(args.month_key or "").strip()

    manifest = _load_json(manifest_path, {})
    months = list(manifest.get("months", []) or [])
    if not months:
        print(f"[skip] manifest months empty: {manifest_path}")
        return 0

    state = _load_json(state_path, {"months": {}, "updated_at": ""})
    if not isinstance(state, dict):
        state = {"months": {}, "updated_at": ""}
    month_state = state.get("months", {})
    if not isinstance(month_state, dict):
        month_state = {}

    candidates = []
    for m in months:
        month_key = str(m.get("month_key", "")).strip()
        if only_month and month_key != only_month:
            continue
        subject_path = Path(str(m.get("subject", "")).strip())
        body_path = Path(str(m.get("body", "")).strip())
        if not month_key or not subject_path.exists() or not body_path.exists():
            continue
        subject = _read_text(subject_path).strip()
        body = _read_text(body_path)
        digest = _content_hash(subject, body)
        prev = dict(month_state.get(month_key, {}) or {})
        prev_hash = str(prev.get("content_hash", "")).strip()
        wr_id = int(prev.get("wr_id", 0) or 0)
        if wr_id > 0 and prev_hash == digest:
            continue
        if wr_id > 0 and min_update_days > 0:
            prev_synced_raw = str(prev.get("last_synced_at", "")).strip()
            if prev_synced_raw:
                try:
                    prev_synced = datetime.fromisoformat(prev_synced_raw)
                    age_days = (datetime.now() - prev_synced).total_seconds() / 86400.0
                    if age_days < min_update_days:
                        continue
                except Exception:
                    pass
        candidates.append(
            {
                "month_key": month_key,
                "subject": subject,
                "body": body,
                "subject_path": str(subject_path),
                "body_path": str(body_path),
                "digest": digest,
                "wr_id": wr_id,
            }
        )

    candidates.sort(key=lambda x: _month_sort_key(x["month_key"]), reverse=True)
    if not candidates:
        print("[ok] no notice changes to sync")
        return 0

    print(f"[plan] changed months: {len(candidates)}")
    for c in candidates:
        mode = "update" if int(c.get("wr_id", 0) or 0) > 0 else "create"
        print(f" - {c['month_key']}: {mode}")

    if args.dry_run:
        print("[dry-run] no writes executed")
        return 0

    admin_id = os.getenv("ADMIN_ID", "")
    admin_pw = os.getenv("ADMIN_PW", "")
    if not admin_id or not admin_pw:
        print("[error] ADMIN_ID/ADMIN_PW missing")
        return 1

    publisher = listing_ops.MnaBoardPublisher(site_url, board_slug, admin_id, admin_pw)
    try:
        publisher.login()
    except Exception as e:
        msg = str(e)
        if ("일일 요청 상한 초과" in msg) or ("일일 데이터 전송량 초과" in msg):
            print(f"[skip] login blocked by traffic/request cap: {msg}")
            return 0
        print(f"[error] login failed: {msg}")
        return 1
    limit = publisher.daily_limit_summary()
    write_cap = int(limit.get("write_cap", 0) or 0)
    write_used = int(limit.get("writes", 0) or 0)
    write_remaining = max(0, write_cap - write_used) if write_cap > 0 else len(candidates)
    safe_remaining = max(0, write_remaining - write_buffer) if write_cap > 0 else len(candidates)

    allowed = len(candidates)
    if max_writes > 0:
        allowed = min(allowed, max_writes)
    if write_cap > 0:
        allowed = min(allowed, safe_remaining)

    if allowed <= 0:
        print(
            "[skip] write budget exhausted "
            f"(used={write_used}, cap={write_cap}, buffer={write_buffer}, pending={len(candidates)})"
        )
        return 0

    applied = 0
    failed = 0
    for idx, row in enumerate(candidates):
        if applied >= allowed:
            break
        month_key = row["month_key"]
        subject = row["subject"]
        body = row["body"]
        wr_id = int(row.get("wr_id", 0) or 0)
        if wr_id <= 0:
            discovered = _find_existing_month_post(
                publisher=publisher,
                board_slug=board_slug,
                month_key=month_key,
                max_pages=discover_pages,
            )
            if discovered:
                wr_id = int(discovered)
        mode = "update" if wr_id > 0 else "create"
        try:
            if wr_id > 0:
                action_url, payload = _get_notice_write_form(
                    publisher=publisher,
                    board_slug=board_slug,
                    wr_id=wr_id,
                )
                out = publisher.submit_edit_updates(
                    action_url,
                    payload,
                    {"wr_subject": subject, "wr_content": body},
                )
                final_url = str(out.get("url", "")).strip() or f"{site_url}/{board_slug}/{wr_id}"
                out_wr_id = _extract_wr_id(final_url, board_slug) or wr_id
            else:
                action_url, payload = _get_notice_write_form(
                    publisher=publisher,
                    board_slug=board_slug,
                    wr_id=None,
                )
                payload["bo_table"] = board_slug
                payload["wr_subject"] = subject
                payload["wr_content"] = body
                if "wr_name" in payload and not str(payload.get("wr_name", "")).strip():
                    payload["wr_name"] = listing_ops.MY_COMPANY_NAME
                out = publisher._submit_write(action_url, payload)  # noqa: SLF001
                final_url = str(out.get("url", "")).strip()
                out_wr_id = _extract_wr_id(final_url, board_slug)
                if not out_wr_id:
                    raise RuntimeError(f"wr_id parse failed from url: {final_url}")

            month_state[month_key] = {
                "wr_id": int(out_wr_id),
                "url": final_url,
                "content_hash": row["digest"],
                "subject_path": row["subject_path"],
                "body_path": row["body_path"],
                "last_mode": mode,
                "last_synced_at": datetime.now().isoformat(timespec="seconds"),
            }
            applied += 1
            print(f"[ok] {month_key} {mode} wr_id={int(out_wr_id)}")
            if idx < len(candidates) - 1 and delay_sec > 0:
                time.sleep(delay_sec)
        except Exception as e:
            failed += 1
            print(f"[fail] {month_key} {mode}: {e}")

    state["months"] = month_state
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _save_json(state_path, state)

    print(f"[done] applied={applied} failed={failed} state={state_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
