from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import permit_diagnosis_calculator


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _random_current(rng: random.Random, required: float, scenario: str, ratio_floor: float, ratio_ceil: float) -> float:
    if scenario == "below":
        return max(0.0, round(required * rng.uniform(0.0, max(0.01, ratio_floor)), 2))
    if scenario == "exact":
        return round(required, 2)
    if scenario == "above":
        return round(required * rng.uniform(max(1.01, ratio_floor), max(1.1, ratio_ceil)), 2)
    return round(required * rng.uniform(0.0, max(1.2, ratio_ceil)), 2)


def run_fuzz(iterations: int, seed: int) -> Dict[str, Any]:
    rng = random.Random(seed)

    payload = permit_diagnosis_calculator._prepare_ui_payload(
        catalog=permit_diagnosis_calculator._load_catalog(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH),
        rule_catalog=permit_diagnosis_calculator._load_rule_catalog(permit_diagnosis_calculator.DEFAULT_RULES_PATH),
    )
    lookup = dict(payload.get("rules_lookup") or {})
    rule_rows = [
        {"service_code": code, "rule": rule}
        for code, rule in lookup.items()
        if isinstance(rule, dict) and isinstance(rule.get("requirements"), dict)
    ]
    if not rule_rows:
        return {
            "generated_at": now_iso(),
            "ok": False,
            "error": "no_rules_loaded",
            "iterations": 0,
            "samples": [],
            "anomaly_counter": {},
        }

    ok_count = 0
    anomaly_counter: Dict[str, int] = {}
    samples: List[Dict[str, Any]] = []
    scenario_counter: Dict[str, int] = {}
    scenarios = ["below", "exact", "above", "mixed"]

    for idx in range(max(10, int(iterations))):
        picked = rng.choice(rule_rows)
        rule = picked["rule"]
        req = dict(rule.get("requirements") or {})
        scenario = rng.choice(scenarios)
        scenario_counter[scenario] = int(scenario_counter.get(scenario, 0)) + 1

        required_capital = float(req.get("capital_eok") or 0.0)
        required_tech = int(req.get("technicians") or 0)
        required_equipment = int(req.get("equipment_count") or 0)

        current_capital = _random_current(rng, required_capital, scenario, 0.8, 2.3)
        current_tech = max(
            0,
            int(
                round(
                    _random_current(
                        rng,
                        float(required_tech),
                        scenario if scenario != "mixed" else rng.choice(["below", "above"]),
                        0.8,
                        2.2,
                    )
                )
            ),
        )
        current_equipment = max(
            0,
            int(
                round(
                    _random_current(
                        rng,
                        float(required_equipment),
                        scenario if scenario != "mixed" else rng.choice(["below", "above"]),
                        0.8,
                        2.2,
                    )
                )
            ),
        )

        raw_capital_input = f"{current_capital}"
        if scenario == "mixed" and rng.random() < 0.35:
            raw_capital_input = str(int(current_capital * 100))

        out = permit_diagnosis_calculator.evaluate_registration_diagnosis(
            rule=rule,
            current_capital_eok=current_capital,
            current_technicians=current_tech,
            current_equipment_count=current_equipment,
            raw_capital_input=raw_capital_input,
        )

        anomalies: List[str] = []
        cap = dict(out.get("capital") or {})
        tech = dict(out.get("technicians") or {})
        equip = dict(out.get("equipment") or {})
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
        if bool(out.get("overall_ok")) != (bool(cap.get("ok")) and bool(tech.get("ok")) and bool(equip.get("ok"))):
            anomalies.append("overall_ok_mismatch")

        if anomalies:
            for key in anomalies:
                anomaly_counter[key] = int(anomaly_counter.get(key, 0)) + 1
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
                    },
                    "requirements": req,
                    "result": out,
                    "anomalies": anomalies,
                }
            )

    total = max(1, int(iterations))
    return {
        "generated_at": now_iso(),
        "ok": len(anomaly_counter) == 0,
        "iterations": int(iterations),
        "ok_count": ok_count,
        "ok_rate_pct": round((ok_count / total) * 100.0, 3),
        "anomaly_total": int(sum(anomaly_counter.values())),
        "anomaly_counter": anomaly_counter,
        "scenario_counter": scenario_counter,
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal variable fuzz for permit diagnosis calculator.")
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20260305)
    parser.add_argument("--report", default="logs/permit_diagnosis_input_fuzz_latest.json")
    args = parser.parse_args()

    report = run_fuzz(iterations=max(10, int(args.iterations)), seed=int(args.seed))
    out_path = (ROOT / str(args.report)).resolve()
    save_json(out_path, report)
    print(f"[saved] {out_path}")
    print(f"[ok] {bool(report.get('ok'))}")
    print(f"[ok_rate_pct] {report.get('ok_rate_pct')}")
    print(f"[anomaly_total] {report.get('anomaly_total')}")
    return 0 if bool(report.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
