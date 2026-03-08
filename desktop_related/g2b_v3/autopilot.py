#!/usr/bin/env python3
"""Run the full ops loop and generate follow-up actions automatically."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).parent.resolve()
RESULT_DIR = BASE_DIR / "result"
LOG_DIR = BASE_DIR / "logs"
CLIENTS_CSV = BASE_DIR / "clients.csv"
LATEST_SUMMARY = RESULT_DIR / "latest_summary.json"
LATEST_ALL = RESULT_DIR / "latest_all.json"
DB_PATH = RESULT_DIR / "g2b_history.db"
SALES_QUEUE_CSV = RESULT_DIR / "sales_queue_latest.csv"
REVENUE_PLAN_JSON = RESULT_DIR / "revenue_plan_latest.json"
SALES_KPI_JSON = RESULT_DIR / "sales_kpi_latest.json"
SALES_DAILY_PLAN_MD = RESULT_DIR / "sales_daily_plan_latest.md"
SALES_SIM_JSON = RESULT_DIR / "sales_simulation_latest.json"

H_CONTACT_NAME = "\ub2f4\ub2f9\uc790"
H_CONTACT_TEL = "\uc5f0\ub77d\ucc98"
H_EXPECTED_REV = "\uae30\ub300\ub9e4\ucd9c(\uc6d0)"


def run_step(name: str, cmd: list[str], *, required: bool = True) -> tuple[int, float]:
    print(f"\n[STEP] {name}")
    print(f"  cmd: {' '.join(cmd)}")
    started = time.time()
    rc = subprocess.run(cmd, cwd=str(BASE_DIR)).returncode
    elapsed = time.time() - started
    status = "OK" if rc == 0 else "FAIL"
    print(f"  -> {status} (rc={rc}, {elapsed:.1f}s)")
    if required and rc != 0:
        print("  -> required step failed")
    return rc, elapsed


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_int(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default


def first_existing_key(row: dict, candidates: list[str], fallback_index: int | None = None) -> str:
    keys = list(row.keys())
    for k in candidates:
        if k in row:
            return k
    if fallback_index is not None and 0 <= fallback_index < len(keys):
        return keys[fallback_index]
    return ""


def clients_count() -> int:
    if not CLIENTS_CSV.exists():
        return 0
    try:
        with CLIENTS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
            rows = [r for r in csv.DictReader(f) if any((v or "").strip() for v in r.values())]
        return len(rows)
    except Exception:
        return 0


def contact_missing_ratio(all_data: list[dict]) -> float:
    if not all_data:
        return 0.0
    sample = all_data[0]
    person_key = first_existing_key(sample, [H_CONTACT_NAME, "contact_name"], fallback_index=12)
    tel_key = first_existing_key(sample, [H_CONTACT_TEL, "contact_tel"], fallback_index=13)
    missing = 0
    for row in all_data:
        person = str(row.get(person_key, "")).strip() if person_key else ""
        tel = str(row.get(tel_key, "")).strip() if tel_key else ""
        if not person and not tel:
            missing += 1
    return missing / len(all_data)


def previous_run_summary(current_run_id: str):
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT run_id, run_ts, total_count, disc_count, quality_level
            FROM run_history
            WHERE run_id <> ?
            ORDER BY run_ts DESC
            LIMIT 1
            """,
            (current_run_id,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return {
        "run_id": row[0],
        "run_ts": row[1],
        "total_count": row[2],
        "disc_count": row[3],
        "quality_level": row[4],
    }


def load_queue_rows():
    if not SALES_QUEUE_CSV.exists():
        return []
    try:
        with SALES_QUEUE_CSV.open("r", encoding="utf-8-sig", newline="") as f:
            return [r for r in csv.DictReader(f) if any((v or "").strip() for v in r.values())]
    except Exception:
        return []


def build_actions(summary: dict, all_data: list[dict]) -> list[str]:
    actions: list[str] = []
    c_count = clients_count()
    revenue_plan = load_json(REVENUE_PLAN_JSON, {})
    sales_kpi = load_json(SALES_KPI_JSON, {})
    sales_sim = load_json(SALES_SIM_JSON, {})
    queue_rows = load_queue_rows()

    if not summary:
        return [
            "Run collect.py once to build baseline outputs.",
            "After first run, execute regression_check.py and review result/latest_summary.json.",
        ]

    quality = (summary.get("quality") or {}).get("level", "UNKNOWN")
    counts = summary.get("counts") or {}
    all_count = int(counts.get("all") or 0)
    disc_count = int(counts.get("disc") or 0)
    matched_count = int(counts.get("matched") or 0)
    run_id = summary.get("run_id", "")

    if quality != "FULL":
        actions.append("Investigate API fallback profile/endpoint selection and rerun with --refresh-profile.")

    if c_count == 0:
        actions.append("Fill clients.csv so matching and finance enrichment can produce actionable leads.")
    elif matched_count == 0:
        actions.append("Matched count is zero with clients present: tune category mapping rules in match_clients().")

    if all_count > 0:
        disc_ratio = disc_count / all_count
        if disc_ratio < 0.2:
            actions.append("Discretionary contract ratio is low; verify DISC_LIMIT/SMALL_LIMIT against current policy.")
        elif disc_ratio > 0.8:
            actions.append("Discretionary contract ratio is high; add an extra sanity check for amount thresholds.")

    miss_ratio = contact_missing_ratio(all_data)
    if miss_ratio >= 0.3:
        actions.append(f"Contact coverage is low ({miss_ratio:.0%} missing); prioritize contact enrichment.")

    prev = previous_run_summary(run_id)
    if prev and prev.get("total_count"):
        delta = all_count - int(prev["total_count"])
        drop_ratio = delta / int(prev["total_count"])
        if drop_ratio <= -0.2:
            actions.append(
                f"Total count dropped {drop_ratio:.0%} vs previous run ({prev['run_id']}); inspect API response changes."
            )

    if queue_rows:
        expected_key = first_existing_key(queue_rows[0], [H_EXPECTED_REV, "expected_revenue_krw", "expected_revenue"])
        total_expected = 0
        for row in queue_rows[:20]:
            total_expected += parse_int(row.get(expected_key, 0), 0) if expected_key else 0
        actions.append(
            f"Start outreach to top 20 leads in sales_queue_latest.csv (top20 expected revenue: {total_expected:,} KRW)."
        )
        actions.append("Track outreach status in sales_activity_latest.csv (new -> contacted -> meeting -> proposal -> closed).")
        if SALES_DAILY_PLAN_MD.exists():
            actions.append("Execute the checklist in sales_daily_plan_latest.md every workday.")

    rates = sales_kpi.get("rates") or {}
    status_counts = sales_kpi.get("status_counts") or {}
    sample_sizes = sales_kpi.get("sample_sizes") or {}
    if rates:
        if float(rates.get("contacted_rate", 0) or 0) < 0.4:
            actions.append("Contacted rate is low: complete at least 50 first contacts this week.")
        if int(sample_sizes.get("meeting_plus", 0) or 0) >= 3 and float(rates.get("proposal_rate", 0) or 0) < 0.45:
            actions.append("Proposal rate is low: shorten quote/proposal turnaround time.")
        if int(sample_sizes.get("proposal_plus", 0) or 0) >= 3 and float(rates.get("close_rate", 0) or 0) < 0.2:
            actions.append("Close rate is low: add D+2 and D+5 proposal follow-up cadence.")
        if int(status_counts.get("closed", 0) or 0) == 0:
            actions.append("No closed deals yet: run a 2-week first-close sprint on A-tier leads.")

    base_revenue = ((revenue_plan.get("scenarios") or {}).get("base") or {}).get("expected_revenue_krw")
    if base_revenue:
        actions.append(f"Base monthly scenario from revenue_plan_latest.json: {int(base_revenue):,} KRW.")

    sim_base = ((sales_sim.get("scenarios") or {}).get("base") or {}).get("horizons") or {}
    horizon_key = "8w" if "8w" in sim_base else ""
    if not horizon_key and sim_base:
        try:
            parsed = []
            for k in sim_base.keys():
                ks = str(k)
                if ks.endswith("w"):
                    parsed.append((abs(int(ks.rstrip("w")) - 8), ks))
            if parsed:
                parsed.sort(key=lambda t: t[0])
                horizon_key = parsed[0][1]
        except Exception:
            horizon_key = ""
    if not horizon_key and sim_base:
        horizon_key = next(iter(sim_base.keys()))
    if horizon_key:
        sim_h = sim_base.get(horizon_key) or {}
        sim_r = sim_h.get("revenue") or {}
        p10 = parse_int(sim_r.get("p10_krw", 0), 0)
        p50 = parse_int(sim_r.get("p50_krw", 0), 0)
        p90 = parse_int(sim_r.get("p90_krw", 0), 0)
        if p50 > 0:
            actions.append(
                f"Pipeline simulation ({horizon_key}, base): P50 {p50:,} KRW, range {p10:,}~{p90:,} KRW."
            )
            downside_ratio = (p50 - p10) / p50 if p50 else 0.0
            if downside_ratio >= 0.35:
                actions.append(
                    "Simulation downside risk is high (p10 gap >=35%): prioritize meeting-to-proposal conversion this week."
                )
            if p10 == 0:
                actions.append(
                    "Simulation p10 is zero: add a loss-prevention review for all active proposals and overdue follow-ups."
                )
        if p90 > 0 and p50 > 0 and (p90 / p50) >= 1.6:
            actions.append(
                "Simulation upside dispersion is large: split execution into baseline-safe deals and high-upside deals."
            )

    if not actions:
        actions.append("No immediate blockers detected. Continue weekly runs and monitor delta sheet trends.")

    return actions


def write_action_report(summary: dict, actions: list[str], step_results: list[dict]) -> Path:
    RESULT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_latest = RESULT_DIR / "next_actions_latest.md"
    out_archived = RESULT_DIR / f"Next_Actions_{ts}.md"

    quality = (summary.get("quality") or {}).get("level", "UNKNOWN")
    counts = summary.get("counts") or {}
    lines = [
        "# Next Actions",
        "",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- run_id: {summary.get('run_id', '-')}",
        f"- quality: {quality}",
        f"- counts: all={counts.get('all', 0)}, disc={counts.get('disc', 0)}, matched={counts.get('matched', 0)}",
        "",
        "## Step Results",
    ]
    for row in step_results:
        lines.append(
            f"- {row['name']}: rc={row['rc']}, elapsed={row['elapsed']:.1f}s, required={'yes' if row['required'] else 'no'}"
        )
    lines.append("")
    lines.append("## Auto Brainstorm")
    for i, action in enumerate(actions, start=1):
        lines.append(f"{i}. {action}")
    lines.append("")

    body = "\n".join(lines)
    out_latest.write_text(body, encoding="utf-8")
    out_archived.write_text(body, encoding="utf-8")
    return out_latest


def parse_args():
    p = argparse.ArgumentParser(description="Run full G2B ops loop + generate follow-up actions.")
    p.add_argument("--year", type=int, default=None, help="Override target year for diagnostics and collection")
    p.add_argument("--max-pages", type=int, default=30, help="collect.py --max-pages")
    p.add_argument("--rows", type=int, default=999, help="collect.py --rows")
    p.add_argument("--sim-runs", type=int, default=2000, help="business_ops.py --sim-runs")
    p.add_argument("--sim-seed", type=int, default=42, help="business_ops.py --sim-seed")
    p.add_argument("--sim-horizons", default="4,8,12", help="business_ops.py --sim-horizons")
    p.add_argument("--skip-test-api", action="store_true", help="Skip test_api diagnostics step")
    p.add_argument("--skip-collect", action="store_true", help="Skip main collection run")
    p.add_argument("--skip-regression", action="store_true", help="Skip regression_check step")
    p.add_argument("--skip-business-ops", action="store_true", help="Skip business_ops step")
    p.add_argument("--continue-on-error", action="store_true", help="Run all optional steps even when one fails")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    LOG_DIR.mkdir(exist_ok=True)
    RESULT_DIR.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    diag_path = LOG_DIR / f"api_diag_{ts}.json"
    py_exec = sys.executable

    steps: list[dict] = []
    has_failure = False

    cmd_check = [py_exec, "collect.py", "--check-config", "--non-interactive"]
    if args.year:
        cmd_check += ["--year", str(args.year)]
    rc, elapsed = run_step("config-check", cmd_check, required=True)
    steps.append({"name": "config-check", "rc": rc, "elapsed": elapsed, "required": True})
    if rc != 0:
        has_failure = True
        if not args.continue_on_error:
            summary = load_json(LATEST_SUMMARY, {})
            all_data = load_json(LATEST_ALL, [])
            actions = build_actions(summary, all_data)
            report = write_action_report(summary, actions, steps)
            print(f"\n[REPORT] {report}")
            return 1

    if not args.skip_test_api:
        cmd_diag = [py_exec, "test_api.py", "--json", str(diag_path)]
        if args.year:
            cmd_diag += ["--year", str(args.year)]
        rc, elapsed = run_step("api-diagnostics", cmd_diag, required=False)
        steps.append({"name": "api-diagnostics", "rc": rc, "elapsed": elapsed, "required": False})
        if rc != 0:
            has_failure = True

    if not args.skip_collect:
        cmd_collect = [
            py_exec,
            "collect.py",
            "--non-interactive",
            "--max-pages",
            str(args.max_pages),
            "--rows",
            str(args.rows),
        ]
        if args.year:
            cmd_collect += ["--year", str(args.year)]
        rc, elapsed = run_step("collect", cmd_collect, required=True)
        steps.append({"name": "collect", "rc": rc, "elapsed": elapsed, "required": True})
        if rc != 0:
            has_failure = True
            if not args.continue_on_error:
                summary = load_json(LATEST_SUMMARY, {})
                all_data = load_json(LATEST_ALL, [])
                actions = build_actions(summary, all_data)
                report = write_action_report(summary, actions, steps)
                print(f"\n[REPORT] {report}")
                return 1

    if not args.skip_regression:
        cmd_reg = [py_exec, "regression_check.py"]
        rc, elapsed = run_step("regression-check", cmd_reg, required=False)
        steps.append({"name": "regression-check", "rc": rc, "elapsed": elapsed, "required": False})
        if rc != 0:
            has_failure = True

    if not args.skip_business_ops:
        cmd_business = [
            py_exec,
            "business_ops.py",
            "--sim-runs",
            str(max(100, int(args.sim_runs))),
            "--sim-seed",
            str(int(args.sim_seed)),
            "--sim-horizons",
            str(args.sim_horizons),
        ]
        rc, elapsed = run_step("business-ops", cmd_business, required=False)
        steps.append({"name": "business-ops", "rc": rc, "elapsed": elapsed, "required": False})
        if rc != 0:
            has_failure = True

    summary = load_json(LATEST_SUMMARY, {})
    all_data = load_json(LATEST_ALL, [])
    actions = build_actions(summary, all_data)
    report = write_action_report(summary, actions, steps)
    print(f"\n[REPORT] {report}")
    print(f"[DIAG] {diag_path if not args.skip_test_api else '(skipped)'}")

    return 1 if has_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
