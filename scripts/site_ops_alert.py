import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import requests


ROOT = Path(__file__).resolve().parents[1]


def _read_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    text = ""
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            text = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        text = path.read_text(encoding="utf-8", errors="replace")
    for raw in text.splitlines():
        s = str(raw or "").strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _load_env(env_file: str) -> Dict[str, str]:
    merged = dict(_read_env_file((ROOT / env_file).resolve()))
    for key in ("DISCORD_WEBHOOK_URL", "SLACK_WEBHOOK_URL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        if os.getenv(key):
            merged[key] = str(os.getenv(key) or "").strip()
    return merged


def _append_jsonl(path: Path, row: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _send_discord(webhook: str, text: str) -> Tuple[bool, str]:
    if not webhook:
        return False, "missing-webhook"
    try:
        res = requests.post(webhook, json={"content": text[:1800]}, timeout=15)
        ok = 200 <= int(res.status_code) < 300
        return ok, f"status={res.status_code}"
    except Exception as exc:
        return False, str(exc)


def _send_slack(webhook: str, text: str) -> Tuple[bool, str]:
    if not webhook:
        return False, "missing-webhook"
    try:
        res = requests.post(webhook, json={"text": text[:3000]}, timeout=15)
        ok = 200 <= int(res.status_code) < 300
        return ok, f"status={res.status_code}"
    except Exception as exc:
        return False, str(exc)


def _send_telegram(bot_token: str, chat_id: str, text: str) -> Tuple[bool, str]:
    if not bot_token or not chat_id:
        return False, "missing-token-or-chat-id"
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text[:3500]}
        res = requests.post(url, json=payload, timeout=15)
        ok = 200 <= int(res.status_code) < 300
        return ok, f"status={res.status_code}"
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send SeoulMNA site operation alerts.")
    parser.add_argument("--event", required=True)
    parser.add_argument("--severity", default="warn")
    parser.add_argument("--message", required=True)
    parser.add_argument("--detail-file", default="")
    parser.add_argument("--extra-json", default="")
    parser.add_argument("--log-jsonl", default="logs/site_ops_alerts.jsonl")
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args()

    env = _load_env(str(args.env_file))
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sev = str(args.severity or "warn").strip().lower()
    event = str(args.event or "site_ops").strip()
    message = str(args.message or "").strip()

    extra_payload: Dict = {}
    if str(args.extra_json).strip():
        try:
            loaded = json.loads(str(args.extra_json))
            if isinstance(loaded, dict):
                extra_payload = loaded
        except Exception:
            extra_payload = {"raw_extra_json": str(args.extra_json)}

    detail_file = str(args.detail_file or "").strip()
    text_lines: List[str] = [
        f"[{sev.upper()}] {event}",
        message,
        f"time={ts}",
    ]
    if detail_file:
        text_lines.append(f"detail={detail_file}")
    if extra_payload:
        text_lines.append("extra=" + json.dumps(extra_payload, ensure_ascii=False))
    text = "\n".join(text_lines)

    channels = []
    discord_ok, discord_msg = _send_discord(str(env.get("DISCORD_WEBHOOK_URL", "")).strip(), text)
    if str(env.get("DISCORD_WEBHOOK_URL", "")).strip():
        channels.append({"name": "discord", "ok": discord_ok, "result": discord_msg})

    slack_ok, slack_msg = _send_slack(str(env.get("SLACK_WEBHOOK_URL", "")).strip(), text)
    if str(env.get("SLACK_WEBHOOK_URL", "")).strip():
        channels.append({"name": "slack", "ok": slack_ok, "result": slack_msg})

    tg_ok, tg_msg = _send_telegram(
        str(env.get("TELEGRAM_BOT_TOKEN", "")).strip(),
        str(env.get("TELEGRAM_CHAT_ID", "")).strip(),
        text,
    )
    if str(env.get("TELEGRAM_BOT_TOKEN", "")).strip() and str(env.get("TELEGRAM_CHAT_ID", "")).strip():
        channels.append({"name": "telegram", "ok": tg_ok, "result": tg_msg})

    if not channels:
        channels.append({"name": "stdout_only", "ok": True, "result": "no channel configured"})

    row = {
        "generated_at": ts,
        "event": event,
        "severity": sev,
        "message": message,
        "detail_file": detail_file,
        "extra": extra_payload,
        "channels": channels,
    }
    _append_jsonl((ROOT / str(args.log_jsonl)).resolve(), row)
    print("[alert] " + text.replace("\n", " | "))
    print("[channels] " + json.dumps(channels, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
