#!/usr/bin/env python3
"""Zero-touch revenue runner: refresh pipeline, dispatch outreach batch, and evaluate goal floor."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).parent.resolve()
RESULT_DIR = BASE_DIR / "result"
CONFIG_FILE = BASE_DIR / "config.txt"
SALES_ACTIVITY_CSV = RESULT_DIR / "sales_activity_latest.csv"
SALES_QUEUE_CSV = RESULT_DIR / "sales_queue_latest.csv"
SALES_SIM_JSON = RESULT_DIR / "sales_simulation_latest.json"

H_NUMBER = "\ubc88\ud638"
H_BIZ = "\uc0ac\uc5c5\uba85"
H_ORG = "\ubc1c\uc8fc\uae30\uad00"
H_CONTACT_NAME = "\ub2f4\ub2f9\uc790"
H_CONTACT_TEL = "\uc5f0\ub77d\ucc98"
H_LEAD_SCORE = "\ub9ac\ub4dc\uc810\uc218"
H_OFFER = "\ucd94\ucc9c\uc0c1\ud488"
H_OFFER_PRICE = "\uc81c\uc548\ub2e8\uac00(\uc6d0)"
H_EXPECTED_REV = "\uae30\ub300\ub9e4\ucd9c(\uc6d0)"
H_STATUS = "\uc0c1\ud0dc"
H_NEXT_ACTION_DATE = "\ub2e4\uc74c\uc561\uc158\uc77c"
H_OWNER = "\ub2f4\ub2f9\uc790\ubc30\uc815"
H_MEMO = "\uba54\ubaa8"
H_UPDATED_AT = "\ucd5c\uc885\uc218\uc815"

PACKAGE_PRICES = {
    "Quick Win": 1_200_000,
    "Standard": 1_800_000,
    "Premium": 2_500_000,
    "Retainer Lite": 390_000,
    "Retainer Pro": 990_000,
}


def parse_args():
    p = argparse.ArgumentParser(description="Run zero-touch revenue ops.")
    p.add_argument("--monthly-goal", type=int, default=200_000, help="Monthly revenue floor goal in KRW")
    p.add_argument("--max-outreach", type=int, default=20, help="Max new leads to dispatch per run")
    p.add_argument("--owner-default", default="outsourced_sdr", help="Default owner for auto-assigned outreach")
    p.add_argument("--webhook-url", default="", help="Optional webhook URL to dispatch outreach payload")
    p.add_argument("--skip-webhook", action="store_true", help="Skip webhook dispatch even if URL exists")
    p.add_argument("--skip-autopilot", action="store_true", help="Skip autopilot refresh step")
    p.add_argument("--full-refresh", action="store_true", help="Run full autopilot refresh (default is fast mode)")
    p.add_argument("--continue-on-error", action="store_true", help="Continue even if autopilot step fails")
    p.add_argument("--no-auto-mark-contacted", action="store_true", help="Do not auto-update status to contacted")
    return p.parse_args()


def parse_int(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default


def parse_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    cfg: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip()
    return cfg


def read_csv(path: Path) -> tuple[list[dict], list[str]]:
    if not path.exists():
        return [], []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = [r for r in reader if any((v or "").strip() for v in r.values())]
            fields = reader.fieldnames or []
        return rows, list(fields)
    except Exception:
        return [], []


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def normalize_status(raw: str) -> str:
    t = (raw or "").strip().lower()
    if t in ("new", "\uc2e0\uaddc"):
        return "new"
    if t in ("contacted", "\uc811\ucd09", "\uc5f0\ub77d\uc644\ub8cc"):
        return "contacted"
    if t in ("meeting", "\ubbf8\ud305", "\uc0c1\ub2f4"):
        return "meeting"
    if t in ("proposal", "\uc81c\uc548", "\uacac\uc801"):
        return "proposal"
    if t in ("closed", "\uc218\uc8fc", "\uacc4\uc57d", "\uc131\uc0ac"):
        return "closed"
    if t in ("lost", "\uc2e4\ud328", "\ubcf4\ub958"):
        return "lost"
    return "new"


def run_step(name: str, cmd: list[str]) -> tuple[int, float]:
    print(f"[STEP] {name}: {' '.join(cmd)}")
    start = datetime.now()
    rc = subprocess.run(cmd, cwd=str(BASE_DIR)).returncode
    elapsed = (datetime.now() - start).total_seconds()
    print(f"[STEP] {name}: rc={rc}, elapsed={elapsed:.1f}s")
    return rc, elapsed


def select_horizon_key(horizons: dict) -> str:
    if not horizons:
        return ""
    if "8w" in horizons:
        return "8w"
    parsed = []
    for k in horizons.keys():
        s = str(k)
        if s.endswith("w"):
            try:
                parsed.append((abs(int(s[:-1]) - 8), s))
            except Exception:
                continue
    if parsed:
        parsed.sort(key=lambda x: x[0])
        return parsed[0][1]
    return next(iter(horizons.keys()))


def render_call_script(contact_name: str, org: str, biz: str, offer: str, price: int) -> str:
    who = (contact_name or "담당자").strip()
    biz_short = (biz or "").strip()
    if len(biz_short) > 36:
        biz_short = biz_short[:33] + "..."
    return (
        f"{who}님, {org} {biz_short} 관련 지원 제안드립니다. "
        f"{offer} 패키지 기준 {price:,}원이며 15분 브리핑 일정 제안드립니다."
    )


def build_outreach_batch(
    activity_rows: list[dict],
    queue_index: dict[str, dict],
    max_outreach: int,
    owner_default: str,
    auto_mark_contacted: bool,
) -> tuple[list[dict], list[dict], int]:
    candidates = []
    for row in activity_rows:
        status = normalize_status(str(row.get(H_STATUS, "new")))
        tel = str(row.get(H_CONTACT_TEL, "")).strip()
        if status != "new" or not tel:
            continue
        score = parse_int(row.get(H_LEAD_SCORE, 0), 0)
        expected = parse_int(row.get(H_EXPECTED_REV, 0), 0)
        candidates.append((score, expected, row))
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    picked = [r for _, _, r in candidates[: max(0, max_outreach)]]
    picked_ids = {str(r.get(H_NUMBER, "")).strip() for r in picked}

    now = datetime.now()
    next_action = (now + timedelta(days=2)).date().isoformat()
    updated_rows = []
    for row in activity_rows:
        rid = str(row.get(H_NUMBER, "")).strip()
        if rid in picked_ids and auto_mark_contacted and normalize_status(str(row.get(H_STATUS, ""))) == "new":
            row[H_STATUS] = "contacted"
            if not str(row.get(H_OWNER, "")).strip():
                row[H_OWNER] = owner_default
            if not str(row.get(H_NEXT_ACTION_DATE, "")).strip():
                row[H_NEXT_ACTION_DATE] = next_action
            row[H_MEMO] = str(row.get(H_MEMO, "")).strip()
            row[H_UPDATED_AT] = now.isoformat(timespec="seconds")
            updated_rows.append(row)

    batch_rows = []
    for row in picked:
        rid = str(row.get(H_NUMBER, "")).strip()
        q = queue_index.get(rid, {})
        org = str(row.get(H_ORG, q.get(H_ORG, ""))).strip()
        biz = str(row.get(H_BIZ, q.get(H_BIZ, ""))).strip()
        contact_name = str(row.get(H_CONTACT_NAME, "")).strip()
        tel = str(row.get(H_CONTACT_TEL, "")).strip()
        offer = str(q.get(H_OFFER, row.get(H_OFFER, "Quick Win"))).strip() or "Quick Win"
        price = parse_int(q.get(H_OFFER_PRICE, row.get(H_OFFER_PRICE, PACKAGE_PRICES["Quick Win"])), PACKAGE_PRICES["Quick Win"])
        expected = parse_int(q.get(H_EXPECTED_REV, row.get(H_EXPECTED_REV, 0)), 0)
        score = parse_int(row.get(H_LEAD_SCORE, q.get(H_LEAD_SCORE, 0)), 0)
        batch_rows.append(
            {
                H_NUMBER: rid,
                H_BIZ: biz,
                H_ORG: org,
                H_CONTACT_NAME: contact_name,
                H_CONTACT_TEL: tel,
                H_LEAD_SCORE: score,
                H_OFFER: offer,
                H_OFFER_PRICE: price,
                H_EXPECTED_REV: expected,
                "status_before": "new",
                "status_after": "contacted" if auto_mark_contacted else "new",
                "owner_after": owner_default if auto_mark_contacted else "",
                "next_action_after": next_action if auto_mark_contacted else "",
                "call_script": render_call_script(contact_name, org, biz, offer, price),
            }
        )
    return batch_rows, activity_rows, len(updated_rows)


def post_webhook(url: str, payload: dict) -> tuple[bool, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=15) as resp:
            code = getattr(resp, "status", 200)
            return 200 <= int(code) < 300, f"HTTP {code}"
    except HTTPError as e:
        return False, f"HTTP {e.code}"
    except URLError as e:
        return False, f"URLError: {e.reason}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def build_goal_floor(monthly_goal: int, queue_rows: list[dict], sim: dict) -> dict:
    avg_offer = 0
    if queue_rows:
        avg_offer = int(round(sum(parse_int(r.get(H_OFFER_PRICE, 0), 0) for r in queue_rows) / len(queue_rows)))
    if avg_offer <= 0:
        avg_offer = PACKAGE_PRICES["Quick Win"]

    scenarios = sim.get("scenarios") or {}
    base = scenarios.get("base") or {}
    horizons = base.get("horizons") or {}
    hk = select_horizon_key(horizons)
    base_h = horizons.get(hk, {}) if hk else {}
    base_r = base_h.get("revenue") or {}
    p10 = parse_int(base_r.get("p10_krw", 0), 0)
    p50 = parse_int(base_r.get("p50_krw", 0), 0)
    p90 = parse_int(base_r.get("p90_krw", 0), 0)
    monthly_p10 = int(round(p10 / 2)) if p10 else 0
    monthly_p50 = int(round(p50 / 2)) if p50 else 0
    monthly_p90 = int(round(p90 / 2)) if p90 else 0

    closes_by_package = {}
    for name, price in PACKAGE_PRICES.items():
        closes_by_package[name] = int(math.ceil(monthly_goal / price)) if price > 0 else 0

    closes_by_avg = int(math.ceil(monthly_goal / avg_offer)) if avg_offer > 0 else 0
    sim_ok_p10 = monthly_p10 >= monthly_goal if monthly_p10 > 0 else False
    sim_ok_p50 = monthly_p50 >= monthly_goal if monthly_p50 > 0 else False

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "monthly_goal_krw": monthly_goal,
        "queue_avg_offer_price_krw": avg_offer,
        "required_monthly_closes_by_avg_offer": closes_by_avg,
        "required_monthly_closes_by_package": closes_by_package,
        "simulation_base_horizon": hk or "-",
        "simulation_monthly_runrate_estimate": {
            "p10_krw": monthly_p10,
            "p50_krw": monthly_p50,
            "p90_krw": monthly_p90,
        },
        "goal_feasibility": {
            "pass_on_p10": sim_ok_p10,
            "pass_on_p50": sim_ok_p50,
        },
    }


def write_goal_floor_outputs(floor_data: dict) -> tuple[Path, Path]:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_latest = RESULT_DIR / "revenue_floor_latest.json"
    json_archived = RESULT_DIR / f"Revenue_Floor_{ts}.json"
    md_latest = RESULT_DIR / "revenue_floor_latest.md"
    md_archived = RESULT_DIR / f"Revenue_Floor_{ts}.md"

    j = json.dumps(floor_data, ensure_ascii=False, indent=2)
    json_latest.write_text(j, encoding="utf-8")
    json_archived.write_text(j, encoding="utf-8")

    by_pkg = floor_data.get("required_monthly_closes_by_package") or {}
    sim = floor_data.get("simulation_monthly_runrate_estimate") or {}
    lines = [
        "# Revenue Floor",
        "",
        f"- generated_at: {floor_data.get('generated_at', '-')}",
        f"- monthly_goal: {int(floor_data.get('monthly_goal_krw', 0)):,} KRW",
        f"- avg_offer_price: {int(floor_data.get('queue_avg_offer_price_krw', 0)):,} KRW",
        f"- required_closes_by_avg_offer: {int(floor_data.get('required_monthly_closes_by_avg_offer', 0))}",
        f"- simulation_horizon: {floor_data.get('simulation_base_horizon', '-')}",
        f"- simulation_monthly_p10_p50_p90: {int(sim.get('p10_krw', 0)):,} / {int(sim.get('p50_krw', 0)):,} / {int(sim.get('p90_krw', 0)):,} KRW",
        "",
        "## Required Closes By Package",
    ]
    for name, closes in by_pkg.items():
        lines.append(f"- {name}: {int(closes)} closes/month")
    lines += [
        "",
        "## Feasibility",
        f"- pass_on_p10: {str((floor_data.get('goal_feasibility') or {}).get('pass_on_p10', False)).lower()}",
        f"- pass_on_p50: {str((floor_data.get('goal_feasibility') or {}).get('pass_on_p50', False)).lower()}",
    ]
    body = "\n".join(lines)
    md_latest.write_text(body, encoding="utf-8")
    md_archived.write_text(body, encoding="utf-8")
    return json_latest, md_latest


def write_ops_report(
    autopilot_rc: int | None,
    batch_rows: list[dict],
    updated_count: int,
    webhook_used: bool,
    webhook_status: str,
    floor_data: dict,
) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = RESULT_DIR / "zero_touch_ops_latest.md"
    archived = RESULT_DIR / f"Zero_Touch_Ops_{ts}.md"
    sim = floor_data.get("simulation_monthly_runrate_estimate") or {}
    lines = [
        "# Zero Touch Ops Report",
        "",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- autopilot_rc: {autopilot_rc if autopilot_rc is not None else 'skipped'}",
        f"- outreach_batch_count: {len(batch_rows)}",
        f"- activity_updated_to_contacted: {updated_count}",
        f"- webhook_used: {'yes' if webhook_used else 'no'}",
        f"- webhook_status: {webhook_status}",
        f"- monthly_goal: {int(floor_data.get('monthly_goal_krw', 0)):,} KRW",
        f"- simulation_monthly_p50: {int(sim.get('p50_krw', 0)):,} KRW",
        "",
        "## Next",
        "1. Keep zero-touch scheduler running daily.",
        "2. Review weekly report and only intervene on red alerts.",
        "3. If p50 drifts below goal for 2 weeks, tighten target list and offer mix.",
        "",
    ]
    body = "\n".join(lines)
    latest.write_text(body, encoding="utf-8")
    archived.write_text(body, encoding="utf-8")
    return latest


def main() -> int:
    args = parse_args()
    RESULT_DIR.mkdir(exist_ok=True)

    py_exec = sys.executable
    autopilot_rc: int | None = None
    if not args.skip_autopilot:
        cmd = [py_exec, "autopilot.py", "--continue-on-error"]
        if not args.full_refresh:
            cmd += ["--skip-test-api", "--skip-collect", "--skip-regression"]
        autopilot_rc, _ = run_step("autopilot-refresh", cmd)
        if autopilot_rc != 0 and not args.continue_on_error:
            print("[ERR] autopilot refresh failed")
            return 1

    activity_rows, activity_fields = read_csv(SALES_ACTIVITY_CSV)
    if not activity_rows:
        print("[ERR] sales_activity_latest.csv is missing or empty")
        return 1
    if not activity_fields:
        activity_fields = [
            H_NUMBER,
            H_BIZ,
            H_ORG,
            H_CONTACT_NAME,
            H_CONTACT_TEL,
            H_LEAD_SCORE,
            H_OFFER,
            H_OFFER_PRICE,
            H_EXPECTED_REV,
            H_STATUS,
            H_NEXT_ACTION_DATE,
            H_OWNER,
            H_MEMO,
            H_UPDATED_AT,
        ]

    queue_rows, _ = read_csv(SALES_QUEUE_CSV)
    queue_index = {str(r.get(H_NUMBER, "")).strip(): r for r in queue_rows}

    batch_rows, updated_activity, updated_count = build_outreach_batch(
        activity_rows=activity_rows,
        queue_index=queue_index,
        max_outreach=max(0, int(args.max_outreach)),
        owner_default=str(args.owner_default).strip() or "outsourced_sdr",
        auto_mark_contacted=not args.no_auto_mark_contacted,
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_latest = RESULT_DIR / "outreach_batch_latest.csv"
    batch_archived = RESULT_DIR / f"Outreach_Batch_{ts}.csv"
    batch_fields = [
        H_NUMBER,
        H_BIZ,
        H_ORG,
        H_CONTACT_NAME,
        H_CONTACT_TEL,
        H_LEAD_SCORE,
        H_OFFER,
        H_OFFER_PRICE,
        H_EXPECTED_REV,
        "status_before",
        "status_after",
        "owner_after",
        "next_action_after",
        "call_script",
    ]
    write_csv(batch_latest, batch_rows, batch_fields)
    write_csv(batch_archived, batch_rows, batch_fields)

    write_csv(SALES_ACTIVITY_CSV, updated_activity, activity_fields)
    activity_archived = RESULT_DIR / f"Sales_Activity_ZeroTouch_{ts}.csv"
    write_csv(activity_archived, updated_activity, activity_fields)

    cfg = load_config(CONFIG_FILE)
    webhook_url = str(args.webhook_url).strip() or os.environ.get("OUTREACH_WEBHOOK_URL", "").strip() or cfg.get("WEBHOOK_URL", "").strip()
    webhook_used = False
    webhook_status = "skipped"
    payload_latest = RESULT_DIR / "outreach_payload_latest.json"
    payload_archived = RESULT_DIR / f"Outreach_Payload_{ts}.json"
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "batch_count": len(batch_rows),
        "monthly_goal_krw": int(args.monthly_goal),
        "items": batch_rows,
    }
    payload_txt = json.dumps(payload, ensure_ascii=False, indent=2)
    payload_latest.write_text(payload_txt, encoding="utf-8")
    payload_archived.write_text(payload_txt, encoding="utf-8")

    if not args.skip_webhook and webhook_url and batch_rows:
        webhook_used = True
        ok, msg = post_webhook(webhook_url, payload)
        webhook_status = msg
        if not ok:
            print(f"[WARN] webhook dispatch failed: {msg}")
    elif args.skip_webhook:
        webhook_status = "skip-webhook"
    elif not webhook_url:
        webhook_status = "no-webhook-url"
    elif not batch_rows:
        webhook_status = "no-batch"

    sim = load_json(SALES_SIM_JSON, {})
    floor_data = build_goal_floor(int(args.monthly_goal), queue_rows, sim)
    floor_json, floor_md = write_goal_floor_outputs(floor_data)

    report_latest = write_ops_report(
        autopilot_rc=autopilot_rc,
        batch_rows=batch_rows,
        updated_count=updated_count,
        webhook_used=webhook_used,
        webhook_status=webhook_status,
        floor_data=floor_data,
    )

    print(f"[OK] outreach_batch: {batch_latest} ({len(batch_rows)} rows)")
    print(f"[OK] outreach_payload: {payload_latest}")
    print(f"[OK] activity_updated: {SALES_ACTIVITY_CSV} ({updated_count} rows changed)")
    print(f"[OK] revenue_floor_json: {floor_json}")
    print(f"[OK] revenue_floor_report: {floor_md}")
    print(f"[OK] zero_touch_report: {report_latest}")
    print(f"[ARCHIVE] {batch_archived}")
    print(f"[ARCHIVE] {payload_archived}")
    print(f"[ARCHIVE] {activity_archived}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
