import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils import Notifier, load_config, setup_logger

CONFIG = load_config(
    {
        "SECURITY_WATCHDOG_LOOKBACK_MIN": "15",
        "SECURITY_WATCHDOG_AUTH_FAIL_THRESHOLD": "20",
        "SECURITY_WATCHDOG_RATE_LIMIT_THRESHOLD": "50",
        "SECURITY_WATCHDOG_FAIL_THRESHOLD": "5",
        "YANGDO_CONSULT_SECURITY_LOG_FILE": "logs/security_consult_events.jsonl",
        "YANGDO_BLACKBOX_SECURITY_LOG_FILE": "logs/security_blackbox_events.jsonl",
        "SECURITY_WATCHDOG_REPORT_FILE": "logs/security_watchdog_latest.json",
    }
)

logger = setup_logger(name="security_watchdog")


def _cfg_int(key: str, default: int) -> int:
    try:
        return int(str(CONFIG.get(key, default)).strip())
    except Exception:
        return int(default)


def _load_events(path: Path, min_ts: int) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = str(raw or "").strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        ts = int(row.get("ts", 0) or 0)
        if ts >= min_ts:
            rows.append(row)
    return rows


def _top_ips(rows: List[Dict[str, object]], key: str, limit: int = 5) -> List[Dict[str, object]]:
    c = Counter()
    for row in rows:
        if str(row.get("event", "")) == key:
            ip = str(row.get("ip", "unknown") or "unknown")
            c[ip] += 1
    out = []
    for ip, cnt in c.most_common(limit):
        out.append({"ip": ip, "count": int(cnt)})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Security event watchdog for SeoulMNA APIs")
    parser.add_argument("--lookback-min", type=int, default=_cfg_int("SECURITY_WATCHDOG_LOOKBACK_MIN", 15))
    parser.add_argument(
        "--consult-log",
        default=str(CONFIG.get("YANGDO_CONSULT_SECURITY_LOG_FILE", "logs/security_consult_events.jsonl")).strip(),
    )
    parser.add_argument(
        "--blackbox-log",
        default=str(CONFIG.get("YANGDO_BLACKBOX_SECURITY_LOG_FILE", "logs/security_blackbox_events.jsonl")).strip(),
    )
    parser.add_argument(
        "--report",
        default=str(CONFIG.get("SECURITY_WATCHDOG_REPORT_FILE", "logs/security_watchdog_latest.json")).strip(),
    )
    parser.add_argument("--auth-threshold", type=int, default=_cfg_int("SECURITY_WATCHDOG_AUTH_FAIL_THRESHOLD", 20))
    parser.add_argument("--rate-threshold", type=int, default=_cfg_int("SECURITY_WATCHDOG_RATE_LIMIT_THRESHOLD", 50))
    parser.add_argument("--fail-threshold", type=int, default=_cfg_int("SECURITY_WATCHDOG_FAIL_THRESHOLD", 5))
    args = parser.parse_args()

    now_ts = int(time.time())
    min_ts = now_ts - max(60, int(args.lookback_min) * 60)

    consult_rows = _load_events(Path(args.consult_log), min_ts=min_ts)
    blackbox_rows = _load_events(Path(args.blackbox_log), min_ts=min_ts)
    rows = consult_rows + blackbox_rows

    event_counter = Counter(str(r.get("event", "")) for r in rows)
    auth_fail = int(event_counter.get("auth_failed", 0) + event_counter.get("admin_auth_failed", 0))
    rate_limited = int(event_counter.get("rate_limited", 0))
    service_fail = int(
        event_counter.get("reload_failed", 0)
        + event_counter.get("estimate_failed", 0)
        + event_counter.get("usage_db_insert_failed", 0)
        + event_counter.get("db_insert_failed", 0)
    )

    alarms: List[str] = []
    if auth_fail >= max(1, int(args.auth_threshold)):
        alarms.append(f"auth_failed_spike:{auth_fail}")
    if rate_limited >= max(1, int(args.rate_threshold)):
        alarms.append(f"rate_limited_spike:{rate_limited}")
    if service_fail >= max(1, int(args.fail_threshold)):
        alarms.append(f"service_failure_spike:{service_fail}")

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": len(alarms) == 0,
        "lookback_min": int(args.lookback_min),
        "total_events": int(len(rows)),
        "event_counts": {k: int(v) for k, v in sorted(event_counter.items())},
        "top_auth_failed_ips": _top_ips(rows, "auth_failed"),
        "top_rate_limited_ips": _top_ips(rows, "rate_limited"),
        "alarms": alarms,
    }

    report_path = Path(args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if alarms:
        msg = (
            "[보안경보]\n"
            f"- lookback: {int(args.lookback_min)}분\n"
            f"- total_events: {len(rows)}\n"
            f"- alarms: {', '.join(alarms)}\n"
            f"- report: {report_path}"
        )
        Notifier(discord_url=CONFIG.get("DISCORD_WEBHOOK_URL", ""), slack_url=CONFIG.get("SLACK_WEBHOOK_URL", "")).send(
            msg, title="SeoulMNA API Security Watchdog"
        )
        logger.warning(msg)
    else:
        logger.info("watchdog ok: events=%s lookback=%smin", len(rows), int(args.lookback_min))

    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
