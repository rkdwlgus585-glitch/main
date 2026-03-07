from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gabji
from utils import load_config

CONFIG = load_config(
    {
        "TISTORY_DAILY_START_REG": "7540",
        "TISTORY_DAILY_STATE_FILE": "logs/tistory_daily_state.json",
        "TISTORY_CHROME_DEBUGGER": "",
        "TISTORY_CHROME_USER_DATA_DIR": "",
        "TISTORY_DAILY_TIMEZONE_OFFSET": "+09:00",
        "TISTORY_DAILY_SKIP_IF_POSTED_TODAY": "1",
        "TISTORY_DAILY_INTERACTIVE_LOGIN": "1",
    }
)


def _default_chrome_profile_dir() -> str:
    import os

    localapp = os.environ.get("LOCALAPPDATA", str(Path.home()))
    base = Path(localapp) / "Google" / "Chrome" / "User Data CodexTistory"
    return str(base)


def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _to_bool(value: Any, default: bool = False) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return bool(default)
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _tz_from_config() -> timezone:
    raw = str(CONFIG.get("TISTORY_DAILY_TIMEZONE_OFFSET", "+09:00")).strip()
    # Python stdlib timezone parser implemented manually to avoid extra deps.
    sign = 1
    src = raw
    if src.startswith("-"):
        sign = -1
        src = src[1:]
    elif src.startswith("+"):
        src = src[1:]
    parts = src.split(":", 1)
    try:
        hh = int(parts[0])
        mm = int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        hh, mm = 9, 0
    from datetime import timedelta

    return timezone(sign * timedelta(hours=hh, minutes=mm))


def _today_str() -> str:
    return datetime.now(_tz_from_config()).strftime("%Y-%m-%d")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _collect_sheet_regs(start_registration: str) -> list[str]:
    lookup = gabji.ListingSheetLookup()
    rows = lookup._load_rows()  # noqa: SLF001 - existing internal helper
    out: list[str] = []
    seen = set()
    for row in rows[1:]:
        seq = lookup._row_value(row, lookup.COL_SEQ)  # noqa: SLF001
        reg = _digits(seq)
        if len(reg) < 4:
            continue
        if reg in seen:
            continue
        seen.add(reg)
        out.append(reg)

    if not out:
        return []
    start = _digits(start_registration)
    if not start:
        return out
    if start in out:
        return out[out.index(start) :]

    try:
        start_n = int(start)
    except Exception:
        return out
    for idx, reg in enumerate(out):
        try:
            if int(reg) >= start_n:
                return out[idx:]
        except Exception:
            continue
    return []


def _pick_next_registration(candidates: list[str], state: dict[str, Any], allow_repeat: bool) -> str:
    if not candidates:
        return ""
    published_order = state.get("published_order")
    if not isinstance(published_order, list):
        published_order = []
    published_set = {str(x) for x in published_order}

    preferred = str(state.get("next_registration") or "").strip()
    start_idx = 0
    if preferred in candidates:
        start_idx = candidates.index(preferred)
    else:
        last_reg = str(state.get("last_registration") or "").strip()
        if last_reg in candidates:
            start_idx = min(candidates.index(last_reg) + 1, len(candidates) - 1)

    ordered = candidates[start_idx:] + candidates[:start_idx]
    if allow_repeat:
        return ordered[0]
    for reg in ordered:
        if reg not in published_set:
            return reg
    return ""


def _next_after(candidates: list[str], current: str) -> str:
    if not candidates:
        return ""
    if current not in candidates:
        return candidates[0]
    idx = candidates.index(current)
    if idx + 1 < len(candidates):
        return candidates[idx + 1]
    return ""


def _ordered_candidates_from_state(candidates: list[str], state: dict[str, Any], allow_repeat: bool) -> list[str]:
    if not candidates:
        return []
    target = _pick_next_registration(candidates, state, allow_repeat=allow_repeat)
    if not target:
        return []
    start_idx = candidates.index(target) if target in candidates else 0
    ordered = candidates[start_idx:] + candidates[:start_idx]
    if allow_repeat:
        return ordered
    published_order = state.get("published_order")
    if not isinstance(published_order, list):
        published_order = []
    published_set = {str(x).strip() for x in published_order if str(x).strip()}
    return [reg for reg in ordered if reg not in published_set]


def _parse_publish_outcome(stdout: str) -> tuple[str, str]:
    text = str(stdout or "")
    lower = text.lower()
    if '"published": true' in lower:
        return "published", ""
    if '"published": false' in lower:
        match = re.search(r'"skipped"\s*:\s*"([^"]+)"', text, flags=re.IGNORECASE)
        return "skipped", (match.group(1) if match else "skipped")
    if "publish blocked by state policy" in lower:
        return "skipped", "skip_duplicate"
    return "unknown", ""


def _is_transient_publish_failure(stdout: str, stderr: str) -> bool:
    text = f"{stdout or ''}\n{stderr or ''}".lower()
    transient_tokens = (
        "timeoutexception",
        "timeout during tistory editor automation",
        "timed out receiving message from renderer",
        "chrome debugger not reachable",
        "failed to start chrome for debugger",
        "session not created",
        "disconnected: not connected to devtools",
        "cannot determine loading status",
        "net::err",
        "connection reset",
        "connection refused",
    )
    return any(token in text for token in transient_tokens)


def _build_publish_command(args: argparse.Namespace, registration: str) -> list[str]:
    draft_policy = getattr(args, "draft_policy", "discard")
    audit_tag = getattr(args, "audit_tag", "daily_once")
    debugger_arg = getattr(args, "debugger", "")
    chrome_user_data_dir_arg = getattr(args, "chrome_user_data_dir", "")
    auto_login = bool(getattr(args, "auto_login", True))
    interactive_login = bool(getattr(args, "interactive_login", True))
    login_wait_sec = getattr(args, "login_wait_sec", 120)
    timeout_sec = getattr(args, "timeout_sec", 240)
    publish_delay_sec = getattr(args, "publish_delay_sec", 2)
    seo_min_score = getattr(args, "seo_min_score", 90)
    seo_gate = bool(getattr(args, "seo_gate", True))
    auto_images = bool(getattr(args, "auto_images", True))
    image_count = getattr(args, "image_count", 2)
    dry_run = bool(getattr(args, "dry_run", False))
    cmd = [
        sys.executable,
        str(ROOT / "tistory_ops" / "publish_browser.py"),
        "--registration",
        str(registration),
        "--open-browser",
        "--draft-policy",
        str(draft_policy),
        "--audit-tag",
        str(audit_tag or "daily_once"),
    ]
    debugger = str(debugger_arg or CONFIG.get("TISTORY_CHROME_DEBUGGER", "")).strip()
    if debugger:
        cmd.extend(["--debugger", debugger])
    user_data_dir = str(chrome_user_data_dir_arg or CONFIG.get("TISTORY_CHROME_USER_DATA_DIR", "")).strip()
    if user_data_dir:
        cmd.extend(["--user-data-dir", user_data_dir])

    if auto_login:
        cmd.append("--auto-login")
    else:
        cmd.append("--no-auto-login")
    if interactive_login:
        cmd.append("--interactive-login")
    cmd.extend(["--login-wait-sec", str(login_wait_sec)])
    cmd.extend(["--timeout-sec", str(timeout_sec)])
    cmd.extend(["--publish-delay-sec", str(publish_delay_sec)])
    cmd.extend(["--seo-min-score", str(seo_min_score)])
    if seo_gate:
        cmd.append("--seo-gate")
    else:
        cmd.append("--no-seo-gate")
    if auto_images:
        cmd.append("--auto-images")
    else:
        cmd.append("--no-auto-images")
    cmd.extend(["--image-count", str(image_count)])

    if dry_run:
        cmd.append("--dry-run")
    return cmd


def _split_host_port(debugger: str) -> tuple[str, int]:
    src = str(debugger or "").strip()
    if ":" not in src:
        return src or "127.0.0.1", 9222
    host, port = src.rsplit(":", 1)
    try:
        return host.strip() or "127.0.0.1", int(port.strip())
    except Exception:
        return host.strip() or "127.0.0.1", 9222


def _debugger_reachable(debugger: str) -> bool:
    host, port = _split_host_port(debugger)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        sock.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _ensure_chrome_debugger(debugger: str, chrome_user_data_dir: str = "", wait_sec: int = 5) -> None:
    if _debugger_reachable(debugger):
        return
    host, port = _split_host_port(debugger)
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError(f"debugger is not reachable: {debugger}")

    args = [f"--remote-debugging-port={port}"]
    profile = str(chrome_user_data_dir or "").strip() or _default_chrome_profile_dir()
    if profile:
        Path(profile).mkdir(parents=True, exist_ok=True)
        args.append(f"--user-data-dir={profile}")
    args.extend(["--new-window", "https://www.tistory.com"])
    try:
        subprocess.Popen(["chrome.exe", *args], cwd=str(ROOT))
    except Exception as exc:
        raise RuntimeError(f"failed to start chrome for debugger {debugger}: {exc}") from exc
    end_ts = time.time() + max(2, int(wait_sec))
    while time.time() < end_ts:
        if _debugger_reachable(debugger):
            return
        time.sleep(0.5)
    raise RuntimeError(f"chrome debugger not reachable after startup attempt: {debugger}")


def run(args: argparse.Namespace) -> int:
    state_file = Path(str(args.state_file or CONFIG.get("TISTORY_DAILY_STATE_FILE", "logs/tistory_daily_state.json")).strip())
    if not state_file.is_absolute():
        state_file = ROOT / state_file
    state = _load_state(state_file)

    today = _today_str()
    skip_today = _to_bool(CONFIG.get("TISTORY_DAILY_SKIP_IF_POSTED_TODAY", "1"), True)
    if skip_today and not args.force:
        if str(state.get("last_publish_date") or "").strip() == today:
            print(json.dumps({"ok": True, "skipped": "already_posted_today", "date": today}, ensure_ascii=False, indent=2))
            return 0

    start_reg = str(args.start_registration or CONFIG.get("TISTORY_DAILY_START_REG", "7540")).strip()
    candidates = _collect_sheet_regs(start_reg)
    if not candidates:
        raise RuntimeError("no candidate registrations found in Google Sheet")

    targets = _ordered_candidates_from_state(candidates, state, allow_repeat=bool(args.allow_repeat))
    if not targets:
        print(json.dumps({"ok": True, "skipped": "all_candidates_published"}, ensure_ascii=False, indent=2))
        return 0

    max_retries = max(0, int(getattr(args, "publish_retries", CONFIG.get("TISTORY_DAILY_PUBLISH_RETRIES", "2"))))
    retry_backoff_sec = max(
        1,
        int(getattr(args, "publish_retry_backoff_sec", CONFIG.get("TISTORY_DAILY_PUBLISH_RETRY_BACKOFF_SEC", "20"))),
    )

    debugger = str(args.debugger or CONFIG.get("TISTORY_CHROME_DEBUGGER", "")).strip()
    if bool(args.ensure_chrome) and debugger:
        _ensure_chrome_debugger(
            debugger,
            chrome_user_data_dir=str(args.chrome_user_data_dir or CONFIG.get("TISTORY_CHROME_USER_DATA_DIR", "")).strip(),
            wait_sec=int(args.chrome_wait_sec),
        )

    last_skipped = ""
    attempted = []
    for target in targets:
        attempted.append(target)
        cmd = _build_publish_command(args, target)
        if args.print_command:
            print("[cmd]", " ".join(cmd))
        proc = None
        for attempt_idx in range(max_retries + 1):
            proc = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if proc.stdout:
                print(proc.stdout.rstrip())
            if proc.stderr:
                print(proc.stderr.rstrip(), file=sys.stderr)

            if proc.returncode == 0:
                break

            is_transient = _is_transient_publish_failure(proc.stdout or "", proc.stderr or "")
            if is_transient and attempt_idx < max_retries:
                wait_sec = retry_backoff_sec * (attempt_idx + 1)
                print(
                    f"[warn] transient publish failure(reg={target}, rc={proc.returncode}) "
                    f"-> retry {attempt_idx + 1}/{max_retries} after {wait_sec}s"
                )
                time.sleep(wait_sec)
                continue

            state["last_error_at"] = _utc_now_iso()
            state["last_error_registration"] = target
            state["last_error_rc"] = proc.returncode
            state["last_error_transient"] = bool(is_transient)
            state["last_error_attempts"] = int(attempt_idx + 1)
            state["last_error_detail"] = (str(proc.stderr or proc.stdout or "").strip())[:1000]
            state["updated_at"] = _utc_now_iso()
            _save_state(state_file, state)
            return proc.returncode if proc.returncode is not None else 1

        if not proc:
            state["last_error_at"] = _utc_now_iso()
            state["last_error_registration"] = target
            state["last_error_rc"] = 1
            state["last_error_transient"] = False
            state["last_error_attempts"] = 0
            state["last_error_detail"] = "subprocess_not_started"
            state["updated_at"] = _utc_now_iso()
            _save_state(state_file, state)
            return 1

        if bool(args.dry_run):
            print(
                json.dumps(
                    {
                        "ok": True,
                        "dry_run": True,
                        "target_registration": target,
                        "next_registration_preview": _next_after(candidates, target),
                        "state_file": str(state_file),
                        "state_updated": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        outcome, detail = _parse_publish_outcome(proc.stdout or "")
        if outcome == "published":
            published_order = state.get("published_order")
            if not isinstance(published_order, list):
                published_order = []
            if target not in published_order:
                published_order.append(target)
            state["published_order"] = published_order[-10000:]
            state["start_registration"] = _digits(start_reg) or str(start_reg)
            state["last_publish_date"] = today
            state["last_registration"] = target
            state["next_registration"] = _next_after(candidates, target)
            state["last_error_at"] = ""
            state["last_error_registration"] = ""
            state["last_error_rc"] = 0
            state["last_error_transient"] = False
            state["last_error_attempts"] = 0
            state["last_error_detail"] = ""
            state["updated_at"] = _utc_now_iso()
            _save_state(state_file, state)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "published_registration": target,
                        "next_registration": state.get("next_registration", ""),
                        "date": today,
                        "state_file": str(state_file),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        if outcome == "skipped":
            last_skipped = detail or "skipped"
            continue

        # Backward compatibility: if publisher returns rc=0 without explicit json outcome, treat as published.
        published_order = state.get("published_order")
        if not isinstance(published_order, list):
            published_order = []
        if target not in published_order:
            published_order.append(target)
        state["published_order"] = published_order[-10000:]
        state["start_registration"] = _digits(start_reg) or str(start_reg)
        state["last_publish_date"] = today
        state["last_registration"] = target
        state["next_registration"] = _next_after(candidates, target)
        state["last_error_at"] = ""
        state["last_error_registration"] = ""
        state["last_error_rc"] = 0
        state["last_error_transient"] = False
        state["last_error_attempts"] = 0
        state["last_error_detail"] = ""
        state["updated_at"] = _utc_now_iso()
        _save_state(state_file, state)
        print(
            json.dumps(
                {
                    "ok": True,
                    "published_registration": target,
                    "next_registration": state.get("next_registration", ""),
                    "date": today,
                    "state_file": str(state_file),
                    "note": "publisher_rc0_without_explicit_result",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    # All candidates were skipped by publisher policy (e.g., duplicate). Do not consume daily slot.
    if attempted:
        state["next_registration"] = _next_after(candidates, attempted[-1])
    state["updated_at"] = _utc_now_iso()
    _save_state(state_file, state)
    print(
        json.dumps(
            {
                "ok": True,
                "skipped": (last_skipped or "all_candidates_skipped"),
                "attempted": attempted,
                "next_registration": state.get("next_registration", ""),
                "date": today,
                "state_file": str(state_file),
                "state_updated": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish one listing per day from Google Sheet (sequential)")
    parser.add_argument("--start-registration", default="", help="starting registration number (default: env TISTORY_DAILY_START_REG=7540)")
    parser.add_argument("--state-file", default="", help="daily state json path")
    parser.add_argument("--debugger", default="", help="chrome debugger address")
    parser.add_argument("--ensure-chrome", action="store_true", default=True, help="start chrome debugger automatically when unavailable")
    parser.add_argument("--no-ensure-chrome", dest="ensure_chrome", action="store_false", help="do not auto-start chrome debugger")
    parser.add_argument("--chrome-user-data-dir", default="", help="chrome user data dir for debugger startup")
    parser.add_argument("--chrome-wait-sec", default="5", help="seconds to wait for debugger startup")
    parser.add_argument("--login-wait-sec", default="300", help="manual login wait timeout seconds")
    parser.add_argument("--timeout-sec", default=str(CONFIG.get("TISTORY_PAGE_TIMEOUT_SEC", "45")), help="browser page timeout seconds")
    parser.add_argument("--publish-delay-sec", default=str(CONFIG.get("TISTORY_PUBLISH_DELAY_SEC", "0.6")), help="delay between publish clicks")
    parser.add_argument("--publish-retries", default=str(CONFIG.get("TISTORY_DAILY_PUBLISH_RETRIES", "2")), help="max retries for transient publish failures")
    parser.add_argument("--publish-retry-backoff-sec", default=str(CONFIG.get("TISTORY_DAILY_PUBLISH_RETRY_BACKOFF_SEC", "20")), help="base backoff seconds between retries")
    parser.add_argument(
        "--interactive-login",
        action="store_true",
        default=_to_bool(CONFIG.get("TISTORY_DAILY_INTERACTIVE_LOGIN", "1"), True),
        help="allow manual login wait when auto-login fails",
    )
    parser.add_argument(
        "--no-interactive-login",
        dest="interactive_login",
        action="store_false",
        help="disable manual login wait fallback",
    )
    parser.add_argument("--draft-policy", choices=["discard", "resume"], default="discard", help="draft popup policy")
    parser.add_argument("--auto-login", action="store_true", default=True, help="enable auto-login first")
    parser.add_argument("--no-auto-login", dest="auto_login", action="store_false", help="disable auto-login")
    parser.add_argument("--seo-min-score", default=str(CONFIG.get("TISTORY_SEO_MIN_SCORE", "90")), help="SEO minimum score")
    parser.add_argument("--seo-gate", action="store_true", default=True, help="enforce SEO gate")
    parser.add_argument("--no-seo-gate", dest="seo_gate", action="store_false", help="disable SEO gate")
    parser.add_argument("--auto-images", action="store_true", default=True, help="auto-generate images")
    parser.add_argument("--no-auto-images", dest="auto_images", action="store_false", help="disable auto image generation")
    parser.add_argument("--image-count", default=str(CONFIG.get("TISTORY_IMAGE_COUNT", "2")), help="auto image count")
    parser.add_argument("--allow-repeat", action="store_true", help="allow reusing already published registrations")
    parser.add_argument("--audit-tag", default="daily_once", help="audit tag")
    parser.add_argument("--print-command", action="store_true", help="print delegated publish command")
    parser.add_argument("--dry-run", action="store_true", help="prepare/fill only, no publish click")
    parser.add_argument("--force", action="store_true", help="ignore once-per-day skip")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
