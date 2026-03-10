from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_ALL_ROOT = ROOT.parent / "ALL"                    # H:\ALL (non-core modules)
if str(_ALL_ROOT) not in sys.path:
    sys.path.insert(0, str(_ALL_ROOT))

import all as seoul_all

DEFAULT_BLOCKED_HOSTS = sorted({str(x).strip().lower() for x in getattr(seoul_all, "BLOCKED_OUTBOUND_HOSTS", set()) if str(x).strip()})
URL_RE = re.compile(r"https?://[^\s<>'\"\)]+", flags=re.I)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def ensure_parent(path: str) -> None:
    target = Path(path)
    if target.parent:
        target.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: str, payload: dict) -> None:
    ensure_parent(path)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_hosts(raw: str) -> list[str]:
    items = []
    if raw:
        for token in re.split(r"[,\s]+", str(raw).strip()):
            host = seoul_all._host_of(token)
            if host:
                items.append(host)
    if not items:
        items = list(DEFAULT_BLOCKED_HOSTS)
    seen = set()
    ordered = []
    for host in items:
        if host in seen:
            continue
        seen.add(host)
        ordered.append(host)
    return ordered


def is_blocked_host(host: str, blocked_hosts: Iterable[str]) -> bool:
    normalized = seoul_all._host_of(host)
    if not normalized:
        return False
    for blocked in blocked_hosts:
        blocked_host = seoul_all._host_of(blocked)
        if not blocked_host:
            continue
        if normalized == blocked_host or normalized.endswith("." + blocked_host):
            return True
    return False


def extract_blocked_urls(text: str, blocked_hosts: Iterable[str]) -> list[dict]:
    src = str(text or "")
    if not src:
        return []
    found = []
    seen = set()
    for match in URL_RE.finditer(src):
        candidate = str(match.group(0) or "").strip().rstrip(".,;:!?")
        host = seoul_all._host_of(candidate)
        if not host or (not is_blocked_host(host, blocked_hosts)):
            continue
        key = (candidate, host)
        if key in seen:
            continue
        seen.add(key)
        found.append({"url": candidate, "host": host})
    return found


def sanitize_html(html: str, blocked_hosts: Iterable[str]) -> tuple[str, list[dict]]:
    original = str(html or "")
    if not original:
        return original, []

    soup = BeautifulSoup(original, "html.parser")
    removed = []
    tag_specs = [
        ("a", "href", "unwrap"),
        ("link", "href", "decompose"),
        ("iframe", "src", "decompose"),
        ("script", "src", "decompose"),
        ("img", "src", "decompose"),
        ("source", "src", "decompose"),
        ("embed", "src", "decompose"),
    ]
    for tag_name, attr_name, action in tag_specs:
        for tag in list(soup.find_all(tag_name)):
            value = str(tag.get(attr_name, "") or "").strip()
            if not value:
                continue
            host = seoul_all._host_of(value)
            if not host or (not is_blocked_host(host, blocked_hosts)):
                continue
            removed.append({"url": value, "host": host, "source": f"{tag_name}[{attr_name}]"})
            if action == "unwrap" and tag.name == "a":
                tag.unwrap()
            else:
                tag.decompose()

    rendered = str(soup)

    def _replace_plain(match: re.Match) -> str:
        candidate = str(match.group(0) or "").strip().rstrip(".,;:!?")
        host = seoul_all._host_of(candidate)
        if not host or (not is_blocked_host(host, blocked_hosts)):
            return match.group(0)
        removed.append({"url": candidate, "host": host, "source": "plain_text"})
        return ""

    rendered = URL_RE.sub(_replace_plain, rendered)
    return rendered, removed


def collect_wr_ids(session: seoul_all.MnaBoardPublisher, max_pages: int, state_path: str, signature: str, reset_state: bool) -> tuple[list[int], int, set[int], int]:
    processed = set()
    resume_wr_id = 0
    if state_path:
        if reset_state:
            seoul_all._save_admin_memo_fix_state(state_path, signature, set(), last_success_wr_id=0)
        state = seoul_all._load_admin_memo_fix_state(state_path, signature)
        processed = set(state.get("processed_wr_ids", set()) or set())
        resume_wr_id = int(state.get("last_success_wr_id", 0) or 0)
    wr_ids, scanned_pages = seoul_all._collect_seoul_wr_ids(
        session,
        max_pages=max(0, int(max_pages or 0)),
        delay_sec=0.0,
        resume_wr_id=resume_wr_id if state_path else 0,
    )
    wr_ids = sorted(set(wr_ids), reverse=True)
    if state_path and resume_wr_id > 0:
        wr_ids = [wid for wid in wr_ids if int(wid) <= int(resume_wr_id)]
    return wr_ids, scanned_pages, processed, resume_wr_id


def mark_state(state_path: str, signature: str, processed: set[int], wr_id: int, last_success_wr_id: int) -> int:
    if not state_path:
        return last_success_wr_id
    wid = int(wr_id or 0)
    if wid > 0:
        processed.add(wid)
        if last_success_wr_id <= 0 or wid < last_success_wr_id:
            last_success_wr_id = wid
    seoul_all._save_admin_memo_fix_state(
        state_path,
        signature,
        processed,
        last_success_wr_id=last_success_wr_id,
    )
    return last_success_wr_id


def headroom_ok(session: seoul_all.MnaBoardPublisher, request_buffer: int, write_buffer: int, dry_run: bool) -> tuple[bool, str, dict]:
    live = session.daily_limit_summary()
    req_cap = int(live.get("request_cap", 0) or 0)
    req_used = int(live.get("requests", 0) or 0)
    if req_cap > 0 and req_used >= (req_cap - max(1, int(request_buffer or 0))):
        return False, "request_headroom", live
    if not dry_run:
        write_cap = int(live.get("write_cap", 0) or 0)
        write_used = int(live.get("writes", 0) or 0)
        if write_cap > 0 and write_used >= (write_cap - max(0, int(write_buffer or 0))):
            return False, "write_headroom", live
    return True, "", live


def fetch_view_hits(session: seoul_all.MnaBoardPublisher, wr_id: int, blocked_hosts: Iterable[str]) -> tuple[dict, list[dict]]:
    url = f"{seoul_all.SITE_URL}/mna/{int(wr_id)}"
    res = session.get(url, timeout=20)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    subject = ""
    for selector in (".bo_v_title", ".bo_v_tit", "h1", "title"):
        node = soup.select_one(selector)
        if node:
            subject = " ".join(node.get_text(" ", strip=True).split())
            if subject:
                break
    hits = extract_blocked_urls(res.text, blocked_hosts)
    return {"wr_id": int(wr_id), "url": url, "subject": subject}, hits


def run_scan(args: argparse.Namespace) -> int:
    blocked_hosts = parse_hosts(args.domains)
    session = seoul_all.MnaBoardPublisher(seoul_all.SITE_URL, seoul_all.MNA_BOARD_SLUG, "", "")
    signature = "banned-link-scan-v1|" + "|".join(blocked_hosts)
    results = []
    stats = {"scanned": 0, "flagged": 0, "failed": 0}
    try:
        ok, reason, live = headroom_ok(session, args.request_buffer, args.write_buffer, True)
        if not ok:
            print(f"[scan] stop before start: {reason} requests={live.get('requests')}/{live.get('request_cap')}")
            payload = {
                "mode": "scan",
                "site_url": seoul_all.SITE_URL,
                "blocked_hosts": blocked_hosts,
                "scanned_pages": 0,
                "stats": stats,
                "results": results,
                "updated_at": now_iso(),
                "note": reason,
            }
            write_json(args.report_file, payload)
            return 3

        wr_ids, scanned_pages, _, _ = collect_wr_ids(session, args.pages, "", signature, False)
        if args.limit and int(args.limit) > 0:
            wr_ids = wr_ids[: int(args.limit)]
        for idx, wr_id in enumerate(wr_ids, start=1):
            ok, reason, live = headroom_ok(session, args.request_buffer, args.write_buffer, True)
            if not ok:
                print(f"[scan] stop: {reason} requests={live.get('requests')}/{live.get('request_cap')}")
                break
            stats["scanned"] += 1
            try:
                info, hits = fetch_view_hits(session, wr_id, blocked_hosts)
                if hits:
                    stats["flagged"] += 1
                    results.append({**info, "matches": hits})
                    print(f"[scan] hit wr_id={wr_id} hosts={', '.join(sorted({x['host'] for x in hits}))}")
            except Exception as exc:
                stats["failed"] += 1
                print(f"[scan] fail wr_id={wr_id}: {exc}")
            if args.delay_sec > 0:
                time.sleep(args.delay_sec)
        payload = {
            "mode": "scan",
            "site_url": seoul_all.SITE_URL,
            "blocked_hosts": blocked_hosts,
            "scanned_pages": int(scanned_pages or 0),
            "stats": stats,
            "results": results,
            "updated_at": now_iso(),
        }
        write_json(args.report_file, payload)
        print(f"[scan] report={args.report_file} flagged={stats['flagged']} scanned={stats['scanned']}")
        return 0
    finally:
        session.close()


def run_cleanup(args: argparse.Namespace) -> int:
    blocked_hosts = parse_hosts(args.domains)
    confirm_token = str(args.confirm_apply or "").strip().upper()
    if (not args.dry_run) and confirm_token != "YES":
        print("[cleanup] bulk modification warning: add --confirm-apply YES")
        return 2

    admin_id = str(seoul_all.CONFIG.get("ADMIN_ID", "") or "").strip()
    admin_pw = str(seoul_all.CONFIG.get("ADMIN_PW", "") or "").strip()
    if not admin_id or not admin_pw:
        print("[cleanup] missing ADMIN_ID/ADMIN_PW")
        return 2

    signature = "banned-link-cleanup-v1|" + "|".join(blocked_hosts)
    session = seoul_all.MnaBoardPublisher(seoul_all.SITE_URL, seoul_all.MNA_BOARD_SLUG, admin_id, admin_pw)
    results = []
    stats = {
        "scanned": 0,
        "flagged": 0,
        "planned": 0,
        "updated": 0,
        "unchanged": 0,
        "template_only": 0,
        "failed": 0,
        "stop_headroom": 0,
    }
    try:
        ok, reason, live = headroom_ok(session, args.request_buffer, args.write_buffer, args.dry_run)
        if not ok:
            print(f"[cleanup] stop before login: {reason} requests={live.get('requests')}/{live.get('request_cap')} writes={live.get('writes')}/{live.get('write_cap')}")
            payload = {
                "mode": "cleanup-dry-run" if args.dry_run else "cleanup-apply",
                "site_url": seoul_all.SITE_URL,
                "blocked_hosts": blocked_hosts,
                "scanned_pages": 0,
                "state_file": str(args.state_file or "").strip(),
                "stats": stats,
                "remaining_after_run": 0,
                "results": results,
                "updated_at": now_iso(),
                "note": reason,
            }
            write_json(args.report_file, payload)
            return 3

        session.login()
        ok, reason, live = headroom_ok(session, args.request_buffer, args.write_buffer, args.dry_run)
        if not ok:
            print(f"[cleanup] stop before start: {reason} requests={live.get('requests')}/{live.get('request_cap')} writes={live.get('writes')}/{live.get('write_cap')}")
            return 3

        wr_ids, scanned_pages, processed, resume_wr_id = collect_wr_ids(session, args.pages, args.state_file, signature, args.reset_state)
        remaining = [wid for wid in wr_ids if wid not in processed]
        if args.limit and int(args.limit) > 0:
            remaining = remaining[: int(args.limit)]
        last_success_wr_id = int(resume_wr_id or 0)

        for idx, wr_id in enumerate(remaining, start=1):
            ok, reason, live = headroom_ok(session, args.request_buffer, args.write_buffer, args.dry_run)
            if not ok:
                stats["stop_headroom"] += 1
                print(f"[cleanup] stop: {reason} requests={live.get('requests')}/{live.get('request_cap')} writes={live.get('writes')}/{live.get('write_cap')}")
                break

            stats["scanned"] += 1
            try:
                info, view_hits = fetch_view_hits(session, wr_id, blocked_hosts)
                if not view_hits:
                    last_success_wr_id = mark_state(args.state_file, signature, processed, wr_id, last_success_wr_id)
                    continue

                stats["flagged"] += 1
                action_url, payload, _form, _html = session.get_edit_payload(wr_id)
                original_html = str(payload.get("wr_content", "") or "")
                cleaned_html, removed = sanitize_html(original_html, blocked_hosts)
                result_row = {
                    **info,
                    "view_matches": view_hits,
                    "removed": removed,
                    "action": "",
                }

                if cleaned_html == original_html:
                    stats["template_only"] += 1
                    result_row["action"] = "template_only"
                    results.append(result_row)
                    print(f"[cleanup] template_only wr_id={wr_id}")
                    last_success_wr_id = mark_state(args.state_file, signature, processed, wr_id, last_success_wr_id)
                    continue

                if args.dry_run:
                    stats["planned"] += 1
                    result_row["action"] = "planned"
                    results.append(result_row)
                    print(f"[cleanup] planned wr_id={wr_id} remove={len(removed)}")
                else:
                    session.submit_edit_updates(action_url, payload, {"wr_content": cleaned_html})
                    stats["updated"] += 1
                    result_row["action"] = "updated"
                    results.append(result_row)
                    print(f"[cleanup] updated wr_id={wr_id} remove={len(removed)}")

                last_success_wr_id = mark_state(args.state_file, signature, processed, wr_id, last_success_wr_id)
                if args.delay_sec > 0:
                    time.sleep(args.delay_sec)
            except Exception as exc:
                stats["failed"] += 1
                print(f"[cleanup] fail wr_id={wr_id}: {exc}")

        payload = {
            "mode": "cleanup-dry-run" if args.dry_run else "cleanup-apply",
            "site_url": seoul_all.SITE_URL,
            "blocked_hosts": blocked_hosts,
            "scanned_pages": int(scanned_pages or 0),
            "state_file": str(args.state_file or "").strip(),
            "stats": stats,
            "remaining_after_run": len([wid for wid in wr_ids if wid not in processed]),
            "results": results,
            "updated_at": now_iso(),
        }
        write_json(args.report_file, payload)
        print(f"[cleanup] report={args.report_file} updated={stats['updated']} planned={stats['planned']} template_only={stats['template_only']}")
        return 0
    finally:
        session.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan and remove blocked outbound links from seoulmna.co.kr board posts")
    parser.add_argument("--scan", action="store_true", help="scan public post pages and report blocked outbound links")
    parser.add_argument("--cleanup", action="store_true", help="remove blocked outbound links from editable post content")
    parser.add_argument("--dry-run", action="store_true", help="report cleanup plan only")
    parser.add_argument("--pages", type=int, default=0, help="board list pages to scan (0=all)")
    parser.add_argument("--limit", type=int, default=0, help="max posts to process (0=all candidates)")
    parser.add_argument("--delay-sec", type=float, default=0.0, help="delay between post operations")
    parser.add_argument("--domains", type=str, default="", help="comma or space separated blocked domains override")
    parser.add_argument("--report-file", type=str, default="logs/banned_link_guard_latest.json", help="json report path")
    parser.add_argument("--state-file", type=str, default="logs/banned_link_cleanup_state.json", help="resume state path for cleanup")
    parser.add_argument("--reset-state", action="store_true", help="reset cleanup state before run")
    parser.add_argument("--request-buffer", type=int, default=40, help="daily request headroom buffer")
    parser.add_argument("--write-buffer", type=int, default=6, help="daily write headroom buffer")
    parser.add_argument("--confirm-apply", type=str, default="", help="set YES to allow live cleanup")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if bool(args.scan) == bool(args.cleanup):
        print("choose exactly one of --scan or --cleanup")
        return 2
    if args.scan:
        return run_scan(args)
    return run_cleanup(args)


if __name__ == "__main__":
    raise SystemExit(main())


