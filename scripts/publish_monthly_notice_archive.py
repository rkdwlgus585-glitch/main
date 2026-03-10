#!/usr/bin/env python3
"""
Publish monthly notice archive bundles to seoulmna.co.kr notice board.

Behavior:
- One post per month key (e.g. 2026-02, 2026-03).
- The scheduled job only syncs the current month unless --month-key is given.
- If current month has no wr_id in state, keep trying to create it until success.
- After creation, current month updates are allowed once per Monday/ISO week.
- Skip unchanged months by content hash (ignoring the volatile "YYYY.MM.DD 기준" banner date).
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
_ALL_ROOT = ROOT.parent / "ALL"                    # H:\ALL (non-core modules)
if str(_ALL_ROOT) not in sys.path:
    sys.path.insert(0, str(_ALL_ROOT))
load_dotenv(ROOT / ".env")

import all as listing_ops  # noqa: E402
from scripts import monthly_notice_rotation as notice_rotation  # noqa: E402


DEFAULT_MANIFEST = ROOT / "output" / "notice_archive" / "notice_archive_manifest.json"
DEFAULT_STATE = ROOT / "logs" / "notice_publish_state.json"
VOLATILE_NOTICE_DATE_RE = re.compile(r"\b\d{4}\.\d{2}\.\d{2}\s*기준\b")


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


def _hash_payload(subject: str, body: str) -> str:
    payload = f"{subject}\n\n{body}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_body_for_hash(body: str) -> str:
    return VOLATILE_NOTICE_DATE_RE.sub("__NOTICE_DATE__ 기준", str(body or ""))


def _content_hash(subject: str, body: str) -> str:
    return _hash_payload(subject, _normalize_body_for_hash(body))


def _legacy_content_hash(subject: str, body: str) -> str:
    return _hash_payload(subject, body)


def _legacy_compatible_hashes(subject: str, body: str, prev: dict) -> set[str]:
    hashes = {_legacy_content_hash(subject, body)}
    prev_synced = _parse_iso_datetime(prev.get("last_synced_at", ""))
    if prev_synced is None:
        return hashes
    compatible_body = VOLATILE_NOTICE_DATE_RE.sub(f"{prev_synced:%Y.%m.%d} 기준", str(body or ""))
    hashes.add(_hash_payload(subject, compatible_body))
    return hashes


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


def _month_key_from_datetime(now: datetime) -> str:
    return f"{now.year:04d}-{now.month:02d}"


def _iso_week_key(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _parse_iso_datetime(raw: str) -> datetime | None:
    txt = str(raw or "").strip()
    if not txt:
        return None
    try:
        return datetime.fromisoformat(txt)
    except Exception:
        return None


def _state_week_key(prev: dict) -> str:
    explicit = str(prev.get("last_schedule_week", "")).strip()
    if explicit:
        return explicit
    fallback = _parse_iso_datetime(prev.get("last_synced_at", ""))
    if fallback is None:
        return ""
    return _iso_week_key(fallback)


def _plan_sync_action(
    month_key: str,
    digest: str,
    legacy_hashes: set[str],
    prev: dict,
    *,
    now: datetime,
    only_month: str,
    min_update_days: float,
) -> dict:
    current_month_key = _month_key_from_datetime(now)
    wr_id = int(prev.get("wr_id", 0) or 0)
    prev_hash = str(prev.get("content_hash", "")).strip()
    prev_matches = prev_hash == digest or prev_hash in set(legacy_hashes or set())

    if only_month:
        if month_key != only_month:
            return {"action": "skip", "reason": "filtered-month"}
    elif month_key != current_month_key:
        return {"action": "skip", "reason": "not-current-month"}

    if wr_id <= 0:
        schedule_kind = "monthly_create" if now.day == 1 else "catchup_create"
        return {"action": "create", "reason": "missing-post", "schedule_kind": schedule_kind}

    if prev_matches:
        return {"action": "skip", "reason": "unchanged"}

    if only_month:
        if min_update_days > 0:
            prev_synced = _parse_iso_datetime(prev.get("last_synced_at", ""))
            if prev_synced is not None:
                age_days = (now - prev_synced).total_seconds() / 86400.0
                if age_days < min_update_days:
                    return {"action": "skip", "reason": "min-update-days"}
        return {
            "action": "update",
            "reason": "targeted-month",
            "schedule_kind": "targeted_month_update",
        }

    if now.weekday() != 0:
        return {"action": "skip", "reason": "wait-until-monday"}

    current_week_key = _iso_week_key(now)
    if _state_week_key(prev) == current_week_key:
        return {"action": "skip", "reason": "already-synced-this-week"}

    return {
        "action": "update",
        "reason": "weekly-monday-update",
        "schedule_kind": "weekly_monday_update",
    }


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
    now = datetime.now()
    current_month_key = _month_key_from_datetime(now)

    candidates = []
    deferred: list[tuple[str, str]] = []
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
        legacy_hashes = _legacy_compatible_hashes(subject, body, prev)
        plan = _plan_sync_action(
            month_key=month_key,
            digest=digest,
            legacy_hashes=legacy_hashes,
            prev=prev,
            now=now,
            only_month=only_month,
            min_update_days=min_update_days,
        )
        if plan.get("action") == "skip":
            reason = str(plan.get("reason", "")).strip()
            if month_key == current_month_key and reason not in {"unchanged", "not-current-month"}:
                deferred.append((month_key, reason))
            continue
        candidates.append(
            {
                "month_key": month_key,
                "subject": subject,
                "body": body,
                "subject_path": str(subject_path),
                "body_path": str(body_path),
                "digest": digest,
                "wr_id": int(prev.get("wr_id", 0) or 0),
                "schedule_kind": str(plan.get("schedule_kind", "")).strip(),
                "planned_action": str(plan.get("action", "")).strip() or "update",
            }
        )

    candidates.sort(key=lambda x: _month_sort_key(x["month_key"]), reverse=True)
    if not candidates:
        for month_key, reason in deferred[:3]:
            print(f"[hold] {month_key}: {reason}")
        print("[ok] no notice changes to sync")
        return 0

    print(f"[plan] changed months: {len(candidates)}")
    for c in candidates:
        mode = str(c.get("planned_action", "")).strip() or ("update" if int(c.get("wr_id", 0) or 0) > 0 else "create")
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
    reserve_for_rotation = 0
    rotation_prev_month_key = ""
    if any(str(c.get("month_key", "")).strip() == current_month_key for c in candidates):
        rotation_prev_month_key = notice_rotation.pick_previous_notice_month(month_state, current_month_key)
        if rotation_prev_month_key:
            reserve_for_rotation = 1
    total_write_need = len(candidates) + reserve_for_rotation
    allowed = total_write_need
    if max_writes > 0:
        allowed = min(allowed, max_writes)
    if write_cap > 0:
        allowed = min(allowed, safe_remaining)
    allowed = max(0, allowed - reserve_for_rotation)

    if allowed <= 0:
        print(
            "[skip] write budget exhausted "
            f"(used={write_used}, cap={write_cap}, buffer={write_buffer}, pending={len(candidates)})"
        )
        if rotation_prev_month_key:
            print(f"[hold] notice rotation deferred: prev={rotation_prev_month_key} current={current_month_key}")
        return 0

    applied = 0
    failed = 0
    rotation_done = False
    for idx, row in enumerate(candidates):
        if applied >= allowed:
            break
        month_key = row["month_key"]
        subject = row["subject"]
        body = row["body"]
        wr_id = int(row.get("wr_id", 0) or 0)
        schedule_kind = str(row.get("schedule_kind", "")).strip()
        if wr_id <= 0:
            discovered = _find_existing_month_post(
                publisher=publisher,
                board_slug=board_slug,
                month_key=month_key,
                max_pages=discover_pages,
            )
            if discovered:
                wr_id = int(discovered)
                if schedule_kind in {"monthly_create", "catchup_create"}:
                    schedule_kind = "state_recovery_update"
        mode = "update" if wr_id > 0 else "create"
        should_notice = month_key == current_month_key
        try:
            if wr_id > 0:
                action_url, payload = _get_notice_write_form(
                    publisher=publisher,
                    board_slug=board_slug,
                    wr_id=wr_id,
                )
                if should_notice:
                    payload = notice_rotation.set_notice_flag(payload, enabled=True)
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
                if should_notice:
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
                    retry_wait = min(2.0, max(0.5, delay_sec or 0.0))
                    for attempt in range(3):
                        if attempt > 0 and retry_wait > 0:
                            time.sleep(retry_wait)
                        discovered = _find_existing_month_post(
                            publisher=publisher,
                            board_slug=board_slug,
                            month_key=month_key,
                            max_pages=max(discover_pages, 5),
                        )
                        if discovered:
                            out_wr_id = int(discovered)
                            final_url = final_url or f"{site_url}/{board_slug}/{out_wr_id}"
                            break
                    if not out_wr_id:
                        raise RuntimeError(f"wr_id parse failed from url: {final_url}")

            previous_entry = dict(month_state.get(month_key, {}) or {})
            created_at = str(previous_entry.get("created_at", "")).strip()
            if not created_at:
                created_at = previous_entry.get("last_synced_at", "") if mode == "update" else ""
            if mode == "create" or not created_at:
                created_at = datetime.now().isoformat(timespec="seconds")
            month_state[month_key] = {
                "wr_id": int(out_wr_id),
                "url": final_url,
                "content_hash": row["digest"],
                "subject_path": row["subject_path"],
                "body_path": row["body_path"],
                "created_at": created_at,
                "last_mode": mode,
                "last_schedule_kind": schedule_kind or mode,
                "last_schedule_week": _iso_week_key(datetime.now()),
                "last_synced_at": datetime.now().isoformat(timespec="seconds"),
                "notice_enabled": bool(should_notice),
            }
            applied += 1
            print(f"[ok] {month_key} {mode} wr_id={int(out_wr_id)}")
            if should_notice and rotation_prev_month_key and (not rotation_done) and rotation_prev_month_key != month_key:
                prev_entry = dict(month_state.get(rotation_prev_month_key, {}) or {})
                prev_wr_id = int(prev_entry.get("wr_id", 0) or 0)
                if prev_wr_id > 0:
                    prev_action_url, prev_payload = _get_notice_write_form(
                        publisher=publisher,
                        board_slug=board_slug,
                        wr_id=prev_wr_id,
                    )
                    prev_payload = notice_rotation.set_notice_flag(prev_payload, enabled=False)
                    publisher.submit_edit_updates(prev_action_url, prev_payload, {})
                    prev_entry["notice_enabled"] = False
                    prev_entry["last_notice_rotated_at"] = datetime.now().isoformat(timespec="seconds")
                    month_state[rotation_prev_month_key] = prev_entry
                    rotation_done = True
                    print(f"[ok] {rotation_prev_month_key} unpinned notice wr_id={prev_wr_id}")
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
