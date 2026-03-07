from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import permit_diagnosis_calculator


BOOLEAN_INPUT_KEYS = (
    "office_secured",
    "facility_secured",
    "qualification_secured",
    "insurance_secured",
    "safety_secured",
    "document_ready",
)


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


def normalize_profile(raw: Any) -> str:
    key = str(raw or "").strip().lower().replace("_", "-")
    if key in {"normal", "market", "market-normal", "normal-market"}:
        return "normal-market"
    return "full-spectrum"


def load_rule_rows() -> List[Dict[str, Any]]:
    payload = permit_diagnosis_calculator._prepare_ui_payload(
        catalog=permit_diagnosis_calculator._load_catalog(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH),
        rule_catalog=permit_diagnosis_calculator._load_rule_catalog(permit_diagnosis_calculator.DEFAULT_RULES_PATH),
    )
    lookup = dict(payload.get("rules_lookup") or {})
    return [
        {"service_code": code, "rule": rule}
        for code, rule in lookup.items()
        if isinstance(rule, dict) and isinstance(rule.get("requirements"), dict)
    ]


def scenario_population(profile: str) -> Tuple[List[str], List[float]]:
    if normalize_profile(profile) == "normal-market":
        return (["below", "exact", "above", "mixed"], [0.22, 0.36, 0.28, 0.14])
    return (["below", "exact", "above", "mixed"], [0.25, 0.25, 0.25, 0.25])


def ratio_window(profile: str, scenario: str, metric: str) -> Tuple[float, float, float]:
    metric_key = str(metric or "").strip().lower()
    profile_key = normalize_profile(profile)
    if profile_key == "normal-market":
        if scenario == "below":
            if metric_key == "capital":
                return (0.72, 0.98, 0.90)
            return (0.74, 0.99, 0.92)
        if scenario == "exact":
            return (1.0, 1.0, 1.0)
        if scenario == "above":
            if metric_key == "capital":
                return (1.02, 1.36, 1.12)
            return (1.02, 1.32, 1.10)
        if metric_key == "capital":
            return (0.82, 1.28, 1.02)
        return (0.84, 1.24, 1.00)
    if scenario == "below":
        return (0.0, 0.80, 0.55)
    if scenario == "exact":
        return (1.0, 1.0, 1.0)
    if scenario == "above":
        return (1.01, 2.30, 1.15)
    return (0.0, 2.20, 0.95)


def sample_amount(rng: random.Random, required: float, scenario: str, profile: str, *, metric: str) -> float:
    if scenario == "exact":
        return round(required, 2)
    lo, hi, mode = ratio_window(profile, scenario, metric)
    return max(0.0, round(required * rng.triangular(lo, hi, mode), 2))


def sample_count(rng: random.Random, required: int, scenario: str, profile: str, *, metric: str) -> int:
    if required <= 0:
        if normalize_profile(profile) == "normal-market":
            return 0 if rng.random() < 0.92 else 1
        return 0 if rng.random() < 0.78 else rng.randint(0, 2)
    if scenario == "exact":
        return int(required)
    lo, hi, mode = ratio_window(profile, scenario, metric)
    return max(0, int(round(float(required) * rng.triangular(lo, hi, mode))))


def build_extra_inputs(rng: random.Random, scenario: str, profile: str) -> Dict[str, bool]:
    profile_key = normalize_profile(profile)
    if profile_key == "normal-market":
        base_prob = {
            "below": 0.62,
            "exact": 0.82,
            "above": 0.90,
            "mixed": 0.74,
        }.get(scenario, 0.78)
    else:
        base_prob = {
            "below": 0.45,
            "exact": 0.68,
            "above": 0.80,
            "mixed": 0.58,
        }.get(scenario, 0.62)
    bias = {
        "office_secured": 0.06,
        "facility_secured": 0.02,
        "qualification_secured": 0.04,
        "insurance_secured": -0.02,
        "safety_secured": -0.01,
        "document_ready": -0.05,
    }
    out: Dict[str, bool] = {}
    for key in BOOLEAN_INPUT_KEYS:
        prob = max(0.05, min(0.98, base_prob + bias.get(key, 0.0) + rng.uniform(-0.08, 0.08)))
        out[key] = rng.random() < prob
    return out


def run_cycle(rule_rows: List[Dict[str, Any]], iterations: int, rng: random.Random, profile: str) -> Dict[str, Any]:
    ok_count = 0
    anomaly_counter: Counter[str] = Counter()
    scenario_counter: Counter[str] = Counter()
    typed_status_counter: Counter[str] = Counter()
    coverage_status_counter: Counter[str] = Counter()
    extra_input_true_counter: Counter[str] = Counter()
    samples: List[Dict[str, Any]] = []

    scenarios, weights = scenario_population(profile)
    for idx in range(max(10, int(iterations))):
        picked = rng.choice(rule_rows)
        rule = picked["rule"]
        req = dict(rule.get("requirements") or {})
        scenario = rng.choices(scenarios, weights=weights, k=1)[0]
        scenario_counter[scenario] += 1

        required_capital = float(req.get("capital_eok") or 0.0)
        required_tech = int(req.get("technicians") or 0)
        required_equipment = int(req.get("equipment_count") or 0)

        current_capital = sample_amount(rng, required_capital, scenario, profile, metric="capital")
        current_tech = sample_count(rng, required_tech, scenario if scenario != "mixed" else rng.choice(["below", "above"]), profile, metric="technicians")
        current_equipment = sample_count(
            rng,
            required_equipment,
            scenario if scenario != "mixed" else rng.choice(["below", "above"]),
            profile,
            metric="equipment",
        )

        raw_capital_input = f"{current_capital}"
        if normalize_profile(profile) != "normal-market" and scenario == "mixed" and rng.random() < 0.35:
            raw_capital_input = str(int(current_capital * 100))

        extra_inputs = build_extra_inputs(rng, scenario, profile)
        for key, enabled in extra_inputs.items():
            if enabled:
                extra_input_true_counter[key] += 1

        out = permit_diagnosis_calculator.evaluate_registration_diagnosis(
            rule=rule,
            current_capital_eok=current_capital,
            current_technicians=current_tech,
            current_equipment_count=current_equipment,
            raw_capital_input=raw_capital_input,
            extra_inputs=extra_inputs,
        )

        anomalies: List[str] = []
        cap = dict(out.get("capital") or {})
        tech = dict(out.get("technicians") or {})
        equip = dict(out.get("equipment") or {})
        typed_status = str(out.get("typed_overall_status") or "").strip().lower() or "pass"
        coverage_status = str(out.get("coverage_status") or "").strip().lower() or "unknown"
        typed_status_counter[typed_status] += 1
        coverage_status_counter[coverage_status] += 1

        if float(cap.get("gap") or 0) < 0:
            anomalies.append("negative_capital_gap")
        if int(tech.get("gap") or 0) < 0:
            anomalies.append("negative_technician_gap")
        if int(equip.get("gap") or 0) < 0:
            anomalies.append("negative_equipment_gap")
        if bool(cap.get("ok")) != (float(cap.get("gap") or 0) <= 0):
            anomalies.append("capital_ok_mismatch")
        if bool(tech.get("ok")) != (int(tech.get("gap") or 0) <= 0):
            anomalies.append("technician_ok_mismatch")
        if bool(equip.get("ok")) != (int(equip.get("gap") or 0) <= 0):
            anomalies.append("equipment_ok_mismatch")

        typed_ok = typed_status in {"", "pass"}
        expected_overall_ok = bool(cap.get("ok")) and bool(tech.get("ok")) and bool(equip.get("ok")) and typed_ok
        if bool(out.get("overall_ok")) != expected_overall_ok:
            anomalies.append("overall_ok_mismatch")

        if normalize_profile(profile) == "normal-market" and scenario != "mixed":
            if bool(out.get("capital_input_suspicious")):
                anomalies.append("unexpected_capital_suspicious_flag")

        if anomalies:
            anomaly_counter.update(anomalies)
        else:
            ok_count += 1

        if idx < 32:
            samples.append(
                {
                    "iter": idx + 1,
                    "scenario": scenario,
                    "service_code": picked["service_code"],
                    "industry_name": str(rule.get("industry_name", "") or ""),
                    "inputs": {
                        "capital_eok": current_capital,
                        "technicians": current_tech,
                        "equipment_count": current_equipment,
                        "raw_capital_input": raw_capital_input,
                        **extra_inputs,
                    },
                    "requirements": req,
                    "result": out,
                    "anomalies": anomalies,
                }
            )

    total = max(1, int(iterations))
    return {
        "generated_at": now_iso(),
        "iterations": int(iterations),
        "ok_count": int(ok_count),
        "ok_rate_pct": round((ok_count / total) * 100.0, 3),
        "anomaly_total": int(sum(int(v) for v in anomaly_counter.values())),
        "anomaly_rate_pct": round((sum(int(v) for v in anomaly_counter.values()) / total) * 100.0, 3),
        "anomaly_counter": dict(anomaly_counter),
        "scenario_counter": dict(scenario_counter),
        "typed_status_counter": dict(typed_status_counter),
        "coverage_status_counter": dict(coverage_status_counter),
        "extra_input_true_counter": dict(extra_input_true_counter),
        "samples": samples,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Internal variable fuzz for permit diagnosis calculator.")
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--forever", action="store_true")
    parser.add_argument("--sleep-sec", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=int(time.time()))
    parser.add_argument("--profile", default="full-spectrum")
    parser.add_argument("--report", default="logs/permit_diagnosis_input_fuzz_latest.json")
    parser.add_argument("--jsonl", default="logs/permit_diagnosis_input_fuzz_cycles.jsonl")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile = normalize_profile(args.profile)
    rule_rows = load_rule_rows()
    if not rule_rows:
        report = {
            "generated_at": now_iso(),
            "ok": False,
            "error": "no_rules_loaded",
            "iterations": 0,
            "samples": [],
            "anomaly_counter": {},
        }
        out_path = (ROOT / str(args.report)).resolve()
        save_json(out_path, report)
        print(f"[saved] {out_path}")
        print("[ok] False")
        print("[ok_rate_pct] 0")
        print("[anomaly_total] 0")
        return 1

    rng = random.Random(int(args.seed))
    report_path = (ROOT / str(args.report)).resolve()
    jsonl_path = (ROOT / str(args.jsonl)).resolve()
    started = time.time()

    total_iterations = 0
    total_ok = 0
    aggregate_anomaly: Counter[str] = Counter()
    aggregate_scenario: Counter[str] = Counter()
    aggregate_typed_status: Counter[str] = Counter()
    aggregate_coverage_status: Counter[str] = Counter()
    aggregate_extra_input_true: Counter[str] = Counter()

    cycle_no = 0
    forever = bool(args.forever)
    max_cycles = max(1, int(args.cycles))

    while True:
        cycle_no += 1
        cycle_report = run_cycle(
            rule_rows=rule_rows,
            iterations=max(10, int(args.iterations)),
            rng=rng,
            profile=profile,
        )
        cycle_report["cycle"] = cycle_no
        append_jsonl(jsonl_path, cycle_report)

        total_iterations += int(cycle_report.get("iterations", 0))
        total_ok += int(cycle_report.get("ok_count", 0))
        aggregate_anomaly.update(cycle_report.get("anomaly_counter") or {})
        aggregate_scenario.update(cycle_report.get("scenario_counter") or {})
        aggregate_typed_status.update(cycle_report.get("typed_status_counter") or {})
        aggregate_coverage_status.update(cycle_report.get("coverage_status_counter") or {})
        aggregate_extra_input_true.update(cycle_report.get("extra_input_true_counter") or {})

        latest = {
            "generated_at": now_iso(),
            "elapsed_sec": round(time.time() - started, 3),
            "mode": "forever" if forever else "bounded",
            "seed": int(args.seed),
            "profile": profile,
            "cycles_done": cycle_no,
            "iterations_per_cycle": max(10, int(args.iterations)),
            "totals": {
                "iterations": int(total_iterations),
                "ok_count": int(total_ok),
                "ok_rate_pct": round((total_ok / max(1, total_iterations)) * 100.0, 3),
                "anomaly_total": int(sum(int(v) for v in aggregate_anomaly.values())),
                "anomaly_rate_pct": round(
                    (sum(int(v) for v in aggregate_anomaly.values()) / max(1, total_iterations)) * 100.0,
                    3,
                ),
            },
            "aggregate_anomaly_counter": dict(aggregate_anomaly),
            "aggregate_scenario_counter": dict(aggregate_scenario),
            "aggregate_typed_status_counter": dict(aggregate_typed_status),
            "aggregate_coverage_status_counter": dict(aggregate_coverage_status),
            "aggregate_extra_input_true_counter": dict(aggregate_extra_input_true),
            "latest_cycle": cycle_report,
        }
        latest["ok"] = len(aggregate_anomaly) == 0
        save_json(report_path, latest)
        print(
            json.dumps(
                {
                    "cycle": cycle_no,
                    "iterations": cycle_report.get("iterations"),
                    "ok_rate_pct": cycle_report.get("ok_rate_pct"),
                    "anomaly_rate_pct": cycle_report.get("anomaly_rate_pct"),
                    "top_anomalies": dict(Counter(cycle_report.get("anomaly_counter") or {}).most_common(6)),
                },
                ensure_ascii=False,
            )
        )

        if not forever and cycle_no >= max_cycles:
            break
        if float(args.sleep_sec) > 0:
            time.sleep(float(args.sleep_sec))

    print(f"[saved] {report_path}")
    print(f"[ok] {bool(latest.get('ok'))}")
    print(f"[ok_rate_pct] {latest.get('totals', {}).get('ok_rate_pct')}")
    print(f"[anomaly_total] {latest.get('totals', {}).get('anomaly_total')}")
    return 0 if bool(latest.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
