from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yangdo_blackbox_api


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        txt = str(value).replace(",", "").strip()
        if not txt:
            return None
        num = float(txt)
        if num != num:
            return None
        return num
    except Exception:
        return None


def _round4(value: Any) -> Optional[float]:
    num = _to_float(value)
    if num is None:
        return None
    return round(float(num), 4)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _dump_json(path: Path, payload: Dict[str, Any]) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    _ensure_parent(path)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


@dataclass
class RunContext:
    estimator: yangdo_blackbox_api.YangdoBlackboxEstimator
    train_records: List[Dict[str, Any]]
    by_seoul_no: Dict[int, Dict[str, Any]]
    meta: Dict[str, Any]


def _build_context(estimator: yangdo_blackbox_api.YangdoBlackboxEstimator) -> RunContext:
    meta = estimator.refresh()
    train_records, _token_index, _meta = estimator._snapshot()
    by_seoul_no: Dict[int, Dict[str, Any]] = {}
    for rec in train_records:
        no_raw = rec.get("number")
        try:
            no = int(no_raw)
        except Exception:
            continue
        by_seoul_no[no] = rec
    return RunContext(
        estimator=estimator,
        train_records=train_records,
        by_seoul_no=by_seoul_no,
        meta=meta,
    )


def _sample_license_text(base_text: str, rng: random.Random) -> str:
    raw = str(base_text or "").strip()
    if not raw:
        return raw
    picks = [
        raw,
        raw.replace("공사업", ""),
        raw.replace("건설업", ""),
        raw.replace("공사", ""),
        raw + " 공사업",
        raw + " 건설업",
        raw.replace("/", " / "),
    ]
    # Alias stress: estimator should still pin to same core.
    alias_swap = {
        "실내건축": "실내",
        "철근콘크리트": "철콘",
        "상하수도설비": "상하",
        "토목건축": "토건",
        "소방시설": "소방",
        "정보통신": "통신",
    }
    for src, dst in alias_swap.items():
        if src in raw:
            picks.append(raw.replace(src, dst))
        if dst in raw:
            picks.append(raw.replace(dst, src))
    return str(rng.choice([p for p in picks if str(p).strip()]) or raw).strip()


def _jitter(base: Optional[float], rng: random.Random, lo: float, hi: float, floor: float = 0.0) -> Optional[float]:
    if base is None:
        return None
    out = float(base) * rng.uniform(lo, hi)
    if floor > 0:
        out = max(floor, out)
    return round(out, 4)


def _build_payload_from_record(rec: Dict[str, Any], rng: random.Random) -> Tuple[Dict[str, Any], str]:
    scenario = rng.choices(
        population=["near", "sparse", "extreme", "unit_typo", "year_shift"],
        weights=[0.52, 0.15, 0.17, 0.08, 0.08],
        k=1,
    )[0]

    lic = _sample_license_text(str(rec.get("license_text") or ""), rng)
    specialty = _to_float(rec.get("specialty"))
    y23 = _to_float(rec.get("years", {}).get("y23"))
    y24 = _to_float(rec.get("years", {}).get("y24"))
    y25 = _to_float(rec.get("years", {}).get("y25"))
    sales3 = _to_float(rec.get("sales3_eok"))
    sales5 = _to_float(rec.get("sales5_eok"))
    balance = _to_float(rec.get("balance_eok"))
    capital = _to_float(rec.get("capital_eok"))
    surplus = _to_float(rec.get("surplus_eok"))
    license_year = int(_to_float(rec.get("license_year")) or rng.randint(1995, 2025))

    payload: Dict[str, Any] = {
        "license_text": lic,
        "specialty": _jitter(specialty, rng, 0.55, 1.65, floor=0.2),
        "y23": _jitter(y23, rng, 0.50, 1.85, floor=0.0),
        "y24": _jitter(y24, rng, 0.50, 1.85, floor=0.0),
        "y25": _jitter(y25, rng, 0.50, 1.85, floor=0.0),
        "sales3_eok": _jitter(sales3, rng, 0.45, 1.95, floor=0.1),
        "sales5_eok": _jitter(sales5 if sales5 is not None else sales3, rng, 0.60, 1.95, floor=0.1),
        "balance_eok": _jitter(balance, rng, 0.50, 1.90, floor=0.0),
        "capital_eok": _jitter(capital, rng, 0.50, 1.80, floor=0.05),
        "surplus_eok": _jitter(surplus, rng, 0.25, 2.10, floor=0.0),
        "license_year": int(license_year + rng.randint(-4, 4)),
        "company_type": rng.choice(["주식회사", "유한회사", "개인"]),
        "credit_level": rng.choice(["우수", "보통", "주의"]),
        "admin_history": rng.choice(["없음", "있음"]),
        "top_k": rng.choice([10, 12, 14, 16]),
    }

    if scenario == "sparse":
        # Sparse signal to verify graceful fallback.
        for k in ("y23", "y24", "y25", "sales5_eok", "capital_eok", "surplus_eok"):
            if rng.random() < 0.75:
                payload[k] = None
    elif scenario == "extreme":
        payload["specialty"] = _jitter(specialty, rng, 0.10, 3.20, floor=0.1)
        payload["sales3_eok"] = _jitter(sales3, rng, 0.08, 3.60, floor=0.1)
        payload["sales5_eok"] = _jitter(sales5 if sales5 is not None else sales3, rng, 0.08, 3.60, floor=0.1)
        payload["balance_eok"] = _jitter(balance, rng, 0.03, 12.0, floor=0.0)
        payload["capital_eok"] = _jitter(capital, rng, 0.08, 3.20, floor=0.05)
    elif scenario == "unit_typo":
        # Intentional unit typo stress.
        b = _to_float(payload.get("balance_eok"))
        if b is not None and b > 0:
            payload["balance_eok"] = round(b * rng.choice([10, 100, 1000]), 4)
        s = _to_float(payload.get("sales3_eok"))
        if s is not None and s > 0 and rng.random() < 0.35:
            payload["sales3_eok"] = round(s * rng.choice([0.1, 10]), 4)
    elif scenario == "year_shift":
        payload["license_year"] = int(payload["license_year"]) - rng.randint(5, 15)

    return payload, scenario


def _validate_result(ctx: RunContext, payload: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
    est = ctx.estimator
    anomalies: List[str] = []
    if not bool(result.get("ok")):
        err = str(result.get("error") or "unknown_error")
        anomalies.append(f"not_ok:{err}")
        return anomalies

    center = _to_float(result.get("estimate_center_eok"))
    low = _to_float(result.get("estimate_low_eok"))
    high = _to_float(result.get("estimate_high_eok"))
    if center is None or low is None or high is None:
        anomalies.append("missing_core_numbers")
        return anomalies
    if not (low <= center <= high):
        anomalies.append("range_invariant_violation")

    target = est._target_from_payload(payload)
    target_tokens = est._canonical_tokens(target.get("license_tokens") or set())
    target_core = est._core_tokens(target_tokens)
    strict_single = bool(est._single_token_target_core(target_tokens))
    enforce_single_core_guard = strict_single and bool(target_core)
    neighbors = list(result.get("neighbors") or [])
    if not neighbors:
        anomalies.append("no_neighbors")
        return anomalies

    if enforce_single_core_guard:
        for n in neighbors:
            no = _to_float(n.get("seoul_no"))
            rec = ctx.by_seoul_no.get(int(no)) if no is not None else None
            cand_text = str((rec or {}).get("license_text") or n.get("license_text") or "")
            cand_tokens = est._canonical_tokens((rec or {}).get("license_tokens") or set())
            if not cand_tokens and cand_text:
                cand_tokens = est._canonical_tokens(
                    (est._target_from_payload({"license_text": cand_text}) or {}).get("license_tokens") or set()
                )
            if est._is_single_token_cross_combo(target_tokens, cand_tokens, cand_text):
                anomalies.append("single_core_cross_combo")
                break

        if ("전기" in target_core) and any(int(_to_float(n.get("seoul_no")) or 0) == 7238 for n in neighbors):
            anomalies.append("jeongi_contains_7238")

    return anomalies


def _run_cycle(
    ctx: RunContext,
    rng: random.Random,
    iterations: int,
    sample_limit: int,
) -> Dict[str, Any]:
    est = ctx.estimator
    train = ctx.train_records
    anomaly_counter: Counter[str] = Counter()
    scenario_counter: Counter[str] = Counter()
    ok_count = 0
    recovered_count = 0
    samples: List[Dict[str, Any]] = []

    for _ in range(max(1, int(iterations))):
        rec = rng.choice(train)
        payload, scenario = _build_payload_from_record(rec, rng)
        scenario_counter[scenario] += 1
        try:
            result = est.estimate(payload)
        except Exception as exc:
            anomaly_counter["runtime_exception"] += 1
            # Self-heal: refresh model and retry once.
            try:
                ctx.meta = est.refresh()
                ctx.train_records, _idx, _meta = est._snapshot()
                ctx.by_seoul_no = {
                    int(r.get("number")): r
                    for r in ctx.train_records
                    if str(r.get("number") or "").isdigit()
                }
                result = est.estimate(payload)
                recovered_count += 1
            except Exception:
                if len(samples) < sample_limit:
                    samples.append(
                        {
                            "type": "runtime_exception",
                            "scenario": scenario,
                            "error": str(exc),
                            "payload": payload,
                        }
                    )
                continue

        if not bool(result.get("ok")):
            err_txt = str(result.get("error") or "")
            if "유사" in err_txt and "매물" in err_txt:
                retry_payload = dict(payload)
                retry_payload["top_k"] = 12
                # Sparse/exreme fallback rescue
                if _to_float(retry_payload.get("sales3_eok")) is None and _to_float(retry_payload.get("sales5_eok")) is not None:
                    retry_payload["sales3_eok"] = _to_float(retry_payload.get("sales5_eok"))
                if _to_float(retry_payload.get("sales5_eok")) is None and _to_float(retry_payload.get("sales3_eok")) is not None:
                    retry_payload["sales5_eok"] = _to_float(retry_payload.get("sales3_eok")) * 1.55
                lic = str(retry_payload.get("license_text") or "")
                if ("/" in lic) and (len(lic) > 2):
                    retry_payload["license_text"] = str(lic.split("/", 1)[0]).strip() or lic
                retried = est.estimate(retry_payload)
                if bool(retried.get("ok")):
                    recovered_count += 1
                    result = retried
                    payload = retry_payload

        anomalies = _validate_result(ctx, payload, result)
        if anomalies:
            for a in anomalies:
                anomaly_counter[a] += 1
            if len(samples) < sample_limit:
                samples.append(
                    {
                        "type": "anomaly",
                        "scenario": scenario,
                        "anomalies": anomalies,
                        "payload": payload,
                        "result": {
                            "ok": bool(result.get("ok")),
                            "error": result.get("error"),
                            "estimate_center_eok": _round4(result.get("estimate_center_eok")),
                            "estimate_low_eok": _round4(result.get("estimate_low_eok")),
                            "estimate_high_eok": _round4(result.get("estimate_high_eok")),
                            "neighbor_count": int(_to_float(result.get("neighbor_count")) or 0),
                            "neighbors": list(result.get("neighbors") or [])[:8],
                        },
                    }
                )
            continue

        # Balance exclusion invariant check (전기/통신/소방 계열): balance should not alter center materially.
        target = est._target_from_payload(payload)
        if est._is_balance_separate_paid_group(target) and rng.random() < 0.22:
            p_lo = dict(payload)
            p_hi = dict(payload)
            p_lo["balance_eok"] = 0.12
            p_hi["balance_eok"] = 3750.0
            r_lo = est.estimate(p_lo)
            r_hi = est.estimate(p_hi)
            if bool(r_lo.get("ok")) and bool(r_hi.get("ok")):
                c_lo = _to_float(r_lo.get("estimate_center_eok"))
                c_hi = _to_float(r_hi.get("estimate_center_eok"))
                if c_lo is not None and c_hi is not None:
                    if abs(c_lo - c_hi) > 0.015:
                        anomaly_counter["balance_exclusion_violation"] += 1
                        if len(samples) < sample_limit:
                            samples.append(
                                {
                                    "type": "balance_exclusion_violation",
                                    "payload": payload,
                                    "center_low_balance": _round4(c_lo),
                                    "center_high_balance": _round4(c_hi),
                                }
                            )
                        continue

        ok_count += 1

    total = max(1, int(iterations))
    anomaly_total = sum(int(v) for v in anomaly_counter.values())
    return {
        "generated_at": now_str(),
        "iterations": total,
        "ok_count": int(ok_count),
        "ok_rate_pct": round((ok_count / total) * 100.0, 3),
        "recovered_count": int(recovered_count),
        "anomaly_total": int(anomaly_total),
        "anomaly_rate_pct": round((anomaly_total / total) * 100.0, 3),
        "scenario_counter": dict(scenario_counter),
        "anomaly_counter": dict(anomaly_counter),
        "samples": samples,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="KR publish 없이 양도양수 내부 엔진만 대상으로 무작위 조합 퍼징/자가복구 반복."
    )
    parser.add_argument("--iterations-per-cycle", type=int, default=12000)
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--forever", action="store_true")
    parser.add_argument("--reload-every-cycles", type=int, default=3)
    parser.add_argument("--seed", type=int, default=int(time.time()))
    parser.add_argument("--sample-limit", type=int, default=18)
    parser.add_argument("--sleep-sec", type=float, default=0.0)
    parser.add_argument("--report", default="logs/yangdo_internal_fuzz_latest.json")
    parser.add_argument("--jsonl", default="logs/yangdo_internal_fuzz_cycles.jsonl")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rng = random.Random(int(args.seed))
    report_path = (ROOT / str(args.report)).resolve()
    jsonl_path = (ROOT / str(args.jsonl)).resolve()

    estimator = yangdo_blackbox_api.YangdoBlackboxEstimator()
    ctx = _build_context(estimator)
    started = time.time()

    all_cycle_reports: List[Dict[str, Any]] = []
    aggregate_anomaly: Counter[str] = Counter()
    aggregate_scenario: Counter[str] = Counter()
    total_iterations = 0
    total_ok = 0
    total_recovered = 0

    cycle_no = 0
    forever = bool(args.forever)
    max_cycles = max(1, int(args.cycles))
    reload_every = max(1, int(args.reload_every_cycles))

    while True:
        cycle_no += 1
        if cycle_no > 1 and (cycle_no % reload_every == 1):
            ctx = _build_context(estimator)

        cycle_report = _run_cycle(
            ctx=ctx,
            rng=rng,
            iterations=max(1, int(args.iterations_per_cycle)),
            sample_limit=max(1, int(args.sample_limit)),
        )
        cycle_report["cycle"] = cycle_no
        all_cycle_reports.append(cycle_report)
        _append_jsonl(jsonl_path, cycle_report)

        total_iterations += int(cycle_report.get("iterations", 0))
        total_ok += int(cycle_report.get("ok_count", 0))
        total_recovered += int(cycle_report.get("recovered_count", 0))
        aggregate_anomaly.update(cycle_report.get("anomaly_counter") or {})
        aggregate_scenario.update(cycle_report.get("scenario_counter") or {})

        latest = {
            "generated_at": now_str(),
            "elapsed_sec": round(time.time() - started, 3),
            "mode": "forever" if forever else "bounded",
            "seed": int(args.seed),
            "cycles_done": cycle_no,
            "iterations_per_cycle": int(args.iterations_per_cycle),
            "totals": {
                "iterations": int(total_iterations),
                "ok_count": int(total_ok),
                "ok_rate_pct": round((total_ok / max(1, total_iterations)) * 100.0, 3),
                "recovered_count": int(total_recovered),
                "anomaly_total": int(sum(int(v) for v in aggregate_anomaly.values())),
                "anomaly_rate_pct": round(
                    (sum(int(v) for v in aggregate_anomaly.values()) / max(1, total_iterations)) * 100.0,
                    3,
                ),
            },
            "aggregate_scenario_counter": dict(aggregate_scenario),
            "aggregate_anomaly_counter": dict(aggregate_anomaly),
            "meta": ctx.meta,
            "latest_cycle": cycle_report,
        }
        _dump_json(report_path, latest)
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
