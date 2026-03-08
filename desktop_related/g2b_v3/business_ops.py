#!/usr/bin/env python3
"""Generate business-ready sales outputs from latest G2B data."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).parent.resolve()
RESULT_DIR = BASE_DIR / "result"
LATEST_ALL = RESULT_DIR / "latest_all.json"
LATEST_SUMMARY = RESULT_DIR / "latest_summary.json"
CLIENTS_CSV = BASE_DIR / "clients.csv"

# Korean headers (unicode escapes to keep source ASCII-stable).
H_NUMBER = "\ubc88\ud638"
H_BIZ = "\uc0ac\uc5c5\uba85"
H_ORG = "\ubc1c\uc8fc\uae30\uad00"
H_DEMAND = "\uc218\uc694\uae30\uad00"
H_BUDGET = "\uc608\uc0b0\uc561"
H_BUDGET_EOK = "\uc608\uc0b0(\uc5b5)"
H_DATE = "\ubc1c\uc8fc\uc2dc\uae30"
H_METHOD = "\uacc4\uc57d\ubc29\ubc95"
H_CATEGORY = "\uc5c5\uc885"
H_CONTRACT_TYPE = "\uc7ac\ub7c9\uc5ec\ubd80"
H_REGION = "\uc9c0\uc5ed"
H_CONTACT_NAME = "\ub2f4\ub2f9\uc790"
H_CONTACT_TEL = "\uc5f0\ub77d\ucc98"

H_LEAD_SCORE = "\ub9ac\ub4dc\uc810\uc218"
H_TIER = "\ud2f0\uc5b4"
H_OFFER = "\ucd94\ucc9c\uc0c1\ud488"
H_OFFER_PRICE = "\uc81c\uc548\ub2e8\uac00(\uc6d0)"
H_CLOSE_PROB = "\uc131\uc0ac\ud655\ub960"
H_EXPECTED_REV = "\uae30\ub300\ub9e4\ucd9c(\uc6d0)"
H_REASON = "\uadfc\uac70"

H_STATUS = "\uc0c1\ud0dc"
H_NEXT_ACTION_DATE = "\ub2e4\uc74c\uc561\uc158\uc77c"
H_OWNER = "\ub2f4\ub2f9\uc790(\uc601\uc5c5)"
H_ACTUAL_REV = "\uc2e4\uc81c\ub9e4\ucd9c(\uc6d0)"
H_MEMO = "\uba54\ubaa8"
H_UPDATED_AT = "\ucd5c\uc885\uc218\uc815"

H_COUNT = "\uac74\uc218"
H_AVG_SCORE = "\ud3c9\uade0\ub9ac\ub4dc\uc810\uc218"
H_EXPECTED_SUM = "\uae30\ub300\ub9e4\ucd9c\ud569(\uc6d0)"
H_TOP_CATEGORY = "\uc8fc\ub825\uc5c5\uc885"
H_TOP_REGION = "\uc8fc\ub825\uc9c0\uc5ed"
H_TARGET_ORG = "\uc7a0\uc7ac\uace0\uac1d\uae30\uad00"
H_TARGET_STATUS = "\uc0c1\ud0dc"
H_TARGET_MEMO = "\uba54\ubaa8"
H_TARGET_UPDATED = "\ucd5c\uc885\uc218\uc815"


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


def parse_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def pick_key(keys: list[str], candidates: list[str], fallback_idx: int) -> str:
    for c in candidates:
        if c in keys:
            return c
    if 0 <= fallback_idx < len(keys):
        return keys[fallback_idx]
    return keys[0] if keys else ""


def resolve_input_columns(sample: dict):
    keys = list(sample.keys())
    return {
        "number": pick_key(keys, [H_NUMBER, "number"], 0),
        "biz_name": pick_key(keys, [H_BIZ, "biz_name"], 1),
        "order_org": pick_key(keys, [H_ORG, "order_org"], 2),
        "demand_org": pick_key(keys, [H_DEMAND, "demand_org"], 3),
        "budget": pick_key(keys, [H_BUDGET, "budget_amt"], 4),
        "order_date": pick_key(keys, [H_DATE, "order_date"], 7),
        "contract_method": pick_key(keys, [H_METHOD, "contract_method"], 8),
        "category": pick_key(keys, [H_CATEGORY, "category"], 9),
        "contract_type": pick_key(keys, [H_CONTRACT_TYPE, "contract_type"], 10),
        "region": pick_key(keys, [H_REGION, "region"], 11),
        "contact_name": pick_key(keys, [H_CONTACT_NAME, "contact_name"], 12),
        "contact_tel": pick_key(keys, [H_CONTACT_TEL, "contact_tel"], 13),
    }


def parse_clients_count() -> int:
    if not CLIENTS_CSV.exists():
        return 0
    try:
        with CLIENTS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
            rows = [r for r in csv.DictReader(f) if any((v or "").strip() for v in r.values())]
        return len(rows)
    except Exception:
        return 0


def days_since(date_text: str) -> int:
    text = (date_text or "").strip()
    if not text:
        return 9999
    fmts = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d", "%Y%m%d%H%M%S"]
    for fmt in fmts:
        try:
            dt = datetime.strptime(text, fmt)
            return (datetime.now() - dt).days
        except Exception:
            continue
    return 9999


def normalize_contract_type(raw: str) -> str:
    t = (raw or "").strip()
    if t == "\uc7ac\ub7c9\uacc4\uc57d":
        return "discretionary"
    if t == "\uc18c\uc561\uc218\uc758":
        return "small_private"
    if t == "\uc77c\ubc18\uacbd\uc7c1":
        return "open_competition"
    return "other"


def classify_offer(contract_type_raw: str, budget_won: int):
    t = normalize_contract_type(contract_type_raw)
    budget_eok = budget_won / 100_000_000 if budget_won > 0 else 0.0
    if t in ("discretionary", "small_private"):
        if budget_eok <= 2:
            return "Quick Win", 1_200_000
        if budget_eok <= 5:
            return "Standard", 1_800_000
        return "Premium", 2_500_000
    if budget_eok <= 5:
        return "Bid Monitor", 900_000
    if budget_eok <= 20:
        return "Enterprise", 1_500_000
    return "Premium", 2_500_000


def lead_score(row: dict, col: dict):
    budget = parse_int(row.get(col["budget"]), 0)
    category = str(row.get(col["category"], "")).strip()
    contract_type_raw = str(row.get(col["contract_type"], "")).strip()
    contract_method = str(row.get(col["contract_method"], "")).strip()
    region = str(row.get(col["region"], "")).strip()
    contact_name = str(row.get(col["contact_name"], "")).strip()
    contact_tel = str(row.get(col["contact_tel"], "")).strip()
    days = days_since(str(row.get(col["order_date"], "")))

    score = 15
    reasons = []
    contract_type = normalize_contract_type(contract_type_raw)
    if contract_type == "discretionary":
        score += 25
        reasons.append("\uc7ac\ub7c9\uacc4\uc57d")
    elif contract_type == "small_private":
        score += 22
        reasons.append("\uc18c\uc561\uc218\uc758")
    elif contract_type == "open_competition":
        score += 10
    else:
        score += 6

    budget_eok = budget / 100_000_000 if budget > 0 else 0.0
    if 0 < budget_eok <= 2:
        score += 14
    elif budget_eok <= 5:
        score += 18
        reasons.append("\ud575\uc2ec \uc608\uc0b0\ubc34\ub4dc")
    elif budget_eok <= 10:
        score += 15
    elif budget_eok <= 30:
        score += 11
    else:
        score += 8

    if contact_name and contact_tel:
        score += 12
        reasons.append("\ub2f4\ub2f9\uc790+\uc5f0\ub77d\ucc98")
    elif contact_name or contact_tel:
        score += 6
    else:
        score -= 8
        reasons.append("\uc5f0\ub77d\ucc98 \ubd80\uc871")

    if region:
        score += 3
    else:
        score -= 2

    if category and category != "\uae30\ud0c0":
        score += 5
        reasons.append(f"\uc138\ubd80\uc5c5\uc885:{category}")

    if days <= 7:
        score += 6
        reasons.append("\ucd5c\uadfc\uacf5\uace0")
    elif days <= 30:
        score += 3

    if "\uc81c\ud55c\uacbd\uc7c1" in contract_method:
        score += 2

    score = max(0, min(100, score))
    tier = "A" if score >= 82 else ("B" if score >= 68 else "C")

    offer_name, offer_price = classify_offer(contract_type_raw, budget)
    close_prob = {"A": 0.22, "B": 0.14, "C": 0.08}[tier]
    if contract_type in ("discretionary", "small_private"):
        close_prob += 0.02
    if not contact_name and not contact_tel:
        close_prob = max(0.03, close_prob - 0.05)

    close_prob = min(0.45, close_prob)
    expected_revenue = round(offer_price * close_prob)
    return {
        "score": score,
        "tier": tier,
        "reasons": ", ".join(reasons),
        "offer_name": offer_name,
        "offer_price_krw": offer_price,
        "close_probability": round(close_prob, 3),
        "expected_revenue_krw": expected_revenue,
        "budget_eok": round(budget_eok, 2),
    }


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def build_sales_queue(all_rows: list[dict], top_n: int):
    if not all_rows:
        return [], []
    col = resolve_input_columns(all_rows[0])
    queue = []
    for row in all_rows:
        scored = lead_score(row, col)
        queue.append(
            {
                H_NUMBER: row.get(col["number"], ""),
                H_BIZ: row.get(col["biz_name"], ""),
                H_ORG: row.get(col["order_org"], ""),
                H_CATEGORY: row.get(col["category"], ""),
                H_CONTRACT_TYPE: row.get(col["contract_type"], ""),
                H_REGION: row.get(col["region"], ""),
                H_CONTACT_NAME: row.get(col["contact_name"], ""),
                H_CONTACT_TEL: row.get(col["contact_tel"], ""),
                H_BUDGET_EOK: scored["budget_eok"],
                H_LEAD_SCORE: scored["score"],
                H_TIER: scored["tier"],
                H_OFFER: scored["offer_name"],
                H_OFFER_PRICE: scored["offer_price_krw"],
                H_CLOSE_PROB: scored["close_probability"],
                H_EXPECTED_REV: scored["expected_revenue_krw"],
                H_REASON: scored["reasons"],
            }
        )

    queue.sort(key=lambda r: (parse_int(r[H_LEAD_SCORE]), parse_float(r[H_BUDGET_EOK])), reverse=True)

    selected = []
    org_cap = Counter()
    for row in queue:
        org = str(row.get(H_ORG, ""))
        if org_cap[org] >= 5:
            continue
        selected.append(row)
        org_cap[org] += 1
        if len(selected) >= top_n:
            break

    non_quick = [r for r in selected if r.get(H_OFFER) != "Quick Win"]
    target_non_quick = min(max(10, top_n // 5), top_n)
    if len(non_quick) < target_non_quick:
        selected_ids = {str(r.get(H_NUMBER, "")) for r in selected}
        needed = target_non_quick - len(non_quick)
        extras = []
        for row in queue:
            if row.get(H_OFFER) == "Quick Win":
                continue
            rid = str(row.get(H_NUMBER, ""))
            if rid in selected_ids:
                continue
            extras.append(row)
            selected_ids.add(rid)
            if len(extras) >= needed:
                break
        if extras:
            quick_idxs = [i for i, r in enumerate(selected) if r.get(H_OFFER) == "Quick Win"]
            quick_idxs = sorted(
                quick_idxs,
                key=lambda i: (parse_int(selected[i][H_LEAD_SCORE]), parse_float(selected[i][H_BUDGET_EOK])),
            )
            remove_set = set(quick_idxs[: len(extras)])
            selected = [r for i, r in enumerate(selected) if i not in remove_set]
            selected.extend(extras)
            selected.sort(key=lambda r: (parse_int(r[H_LEAD_SCORE]), parse_float(r[H_BUDGET_EOK])), reverse=True)
            selected = selected[:top_n]

    queue = selected

    acc = defaultdict(lambda: {"count": 0, "expected_revenue": 0, "scores": [], "category": Counter(), "region": Counter()})
    for row in queue:
        org = str(row[H_ORG])
        item = acc[org]
        item["count"] += 1
        item["expected_revenue"] += parse_int(row[H_EXPECTED_REV])
        item["scores"].append(parse_int(row[H_LEAD_SCORE]))
        item["category"][str(row[H_CATEGORY])] += 1
        item["region"][str(row[H_REGION])] += 1

    accounts = []
    for org, item in acc.items():
        top_cat = item["category"].most_common(1)[0][0] if item["category"] else ""
        top_region = item["region"].most_common(1)[0][0] if item["region"] else ""
        avg_score = round(sum(item["scores"]) / len(item["scores"]), 1) if item["scores"] else 0.0
        accounts.append(
            {
                H_ORG: org,
                H_COUNT: item["count"],
                H_AVG_SCORE: avg_score,
                H_EXPECTED_SUM: item["expected_revenue"],
                H_TOP_CATEGORY: top_cat,
                H_TOP_REGION: top_region,
            }
        )
    accounts.sort(key=lambda r: (parse_int(r[H_COUNT]), parse_int(r[H_EXPECTED_SUM])), reverse=True)
    return queue, accounts


def build_client_targets(accounts: list[dict], existing: dict[str, dict], limit: int = 40):
    targets = []
    now_text = datetime.now().isoformat(timespec="seconds")
    for row in accounts[:limit]:
        org = str(row.get(H_ORG, "")).strip()
        prev = existing.get(org, {})
        targets.append(
            {
                H_TARGET_ORG: org,
                H_COUNT: row.get(H_COUNT, 0),
                H_EXPECTED_SUM: row.get(H_EXPECTED_SUM, 0),
                H_TOP_CATEGORY: row.get(H_TOP_CATEGORY, ""),
                H_TOP_REGION: row.get(H_TOP_REGION, ""),
                H_TARGET_STATUS: prev.get("status", "new"),
                H_TARGET_MEMO: prev.get("memo", ""),
                H_TARGET_UPDATED: prev.get("updated_at", "") or now_text,
            }
        )
    return targets


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


def load_existing_targets(path: Path):
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = list(csv.DictReader(f))
    except Exception:
        return {}
    existing = {}
    for row in reader:
        org = str(row.get(H_TARGET_ORG, "")).strip()
        if not org:
            continue
        existing[org] = {
            "status": normalize_status(str(row.get(H_TARGET_STATUS, "new"))),
            "memo": str(row.get(H_TARGET_MEMO, "")).strip(),
            "updated_at": str(row.get(H_TARGET_UPDATED, "")).strip(),
        }
    return existing


def load_existing_activity(path: Path):
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = list(csv.DictReader(f))
    except Exception:
        return {}
    existing = {}
    for row in reader:
        rid = str(row.get(H_NUMBER, "")).strip()
        if not rid:
            continue
        existing[rid] = {
            "status": normalize_status(str(row.get(H_STATUS, "new"))),
            "next_action_date": str(row.get(H_NEXT_ACTION_DATE, "")).strip(),
            "owner": str(row.get(H_OWNER, "")).strip(),
            "actual_revenue": parse_int(row.get(H_ACTUAL_REV, 0), 0),
            "memo": str(row.get(H_MEMO, "")).strip(),
            "updated_at": str(row.get(H_UPDATED_AT, "")).strip(),
        }
    return existing


def build_activity_rows(queue: list[dict], existing: dict[str, dict], top_n: int = 50):
    rows = []
    now_text = datetime.now().isoformat(timespec="seconds")
    for item in queue[:top_n]:
        rid = str(item.get(H_NUMBER, "")).strip()
        prev = existing.get(rid, {})
        status = prev.get("status", "new")
        rows.append(
            {
                H_NUMBER: rid,
                H_BIZ: item.get(H_BIZ, ""),
                H_ORG: item.get(H_ORG, ""),
                H_CONTACT_NAME: item.get(H_CONTACT_NAME, ""),
                H_CONTACT_TEL: item.get(H_CONTACT_TEL, ""),
                H_LEAD_SCORE: item.get(H_LEAD_SCORE, ""),
                H_OFFER: item.get(H_OFFER, ""),
                H_OFFER_PRICE: item.get(H_OFFER_PRICE, ""),
                H_EXPECTED_REV: item.get(H_EXPECTED_REV, ""),
                H_STATUS: status,
                H_NEXT_ACTION_DATE: prev.get("next_action_date", ""),
                H_OWNER: prev.get("owner", ""),
                H_ACTUAL_REV: prev.get("actual_revenue", 0),
                H_MEMO: prev.get("memo", ""),
                H_UPDATED_AT: prev.get("updated_at", "") or now_text,
            }
        )
    return rows


def build_sales_kpi(activity_rows: list[dict]):
    status_counts = Counter(normalize_status(str(r.get(H_STATUS, "new"))) for r in activity_rows)
    total = len(activity_rows)
    contacted_plus = status_counts["contacted"] + status_counts["meeting"] + status_counts["proposal"] + status_counts["closed"]
    meeting_plus = status_counts["meeting"] + status_counts["proposal"] + status_counts["closed"]
    proposal_plus = status_counts["proposal"] + status_counts["closed"]

    contacted_rate = round(contacted_plus / total, 3) if total else 0.0
    meeting_rate = round(meeting_plus / contacted_plus, 3) if contacted_plus >= 3 else 0.0
    proposal_rate = round(proposal_plus / meeting_plus, 3) if meeting_plus >= 3 else 0.0
    close_rate = round(status_counts["closed"] / proposal_plus, 3) if proposal_plus >= 3 else 0.0

    weight = {"new": 0.05, "contacted": 0.1, "meeting": 0.25, "proposal": 0.5, "closed": 1.0, "lost": 0.0}
    weighted_pipeline = 0
    expected_sum = 0
    actual_closed = 0
    owner_counter = defaultdict(lambda: {"count": 0, "proposal": 0, "closed": 0})

    for row in activity_rows:
        status = normalize_status(str(row.get(H_STATUS, "new")))
        price = parse_int(row.get(H_OFFER_PRICE, 0), 0)
        expected = parse_int(row.get(H_EXPECTED_REV, 0), 0)
        expected_sum += expected
        weighted_pipeline += round(price * weight[status])
        if status == "closed":
            actual = parse_int(row.get(H_ACTUAL_REV, 0), 0) or price
            actual_closed += actual
        owner = str(row.get(H_OWNER, "")).strip()
        if owner:
            owner_counter[owner]["count"] += 1
            if status == "proposal":
                owner_counter[owner]["proposal"] += 1
            if status == "closed":
                owner_counter[owner]["closed"] += 1

    owners = []
    for owner, item in owner_counter.items():
        owners.append({"owner": owner, **item})
    owners.sort(key=lambda r: (r["closed"], r["proposal"], r["count"]), reverse=True)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_leads": total,
        "status_counts": dict(status_counts),
        "rates": {
            "contacted_rate": contacted_rate,
            "meeting_rate": meeting_rate,
            "proposal_rate": proposal_rate,
            "close_rate": close_rate,
        },
        "sample_sizes": {
            "contacted_plus": contacted_plus,
            "meeting_plus": meeting_plus,
            "proposal_plus": proposal_plus,
        },
        "pipeline": {
            "expected_revenue_sum_krw": expected_sum,
            "weighted_pipeline_krw": weighted_pipeline,
            "actual_closed_revenue_krw": actual_closed,
        },
        "owners": owners[:20],
    }


def build_revenue_plan(summary: dict, queue: list[dict], clients_count: int):
    counts = summary.get("counts") or {}
    all_count = parse_int(counts.get("all"), 0)
    disc_count = parse_int(counts.get("disc"), 0)
    run_id = summary.get("run_id", "-")

    top_pipeline = queue[:50]
    avg_offer_price = round(sum(parse_int(r[H_OFFER_PRICE]) for r in top_pipeline) / len(top_pipeline)) if top_pipeline else 0
    total_expected = sum(parse_int(r[H_EXPECTED_REV]) for r in top_pipeline)
    scenarios = {
        "conservative": {"contact_rate": 0.35, "meeting_rate": 0.45, "close_rate": 0.22},
        "base": {"contact_rate": 0.45, "meeting_rate": 0.50, "close_rate": 0.28},
        "aggressive": {"contact_rate": 0.55, "meeting_rate": 0.55, "close_rate": 0.33},
    }
    lead_count = len(top_pipeline)
    for s in scenarios.values():
        deals = round(lead_count * s["contact_rate"] * s["meeting_rate"] * s["close_rate"], 1)
        s["expected_deals"] = deals
        s["expected_revenue_krw"] = round(deals * avg_offer_price)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_id": run_id,
        "inputs": {
            "all_count": all_count,
            "disc_count": disc_count,
            "clients_count": clients_count,
            "top_pipeline_size": lead_count,
            "avg_offer_price_krw": avg_offer_price,
            "top50_expected_revenue_krw_sum": total_expected,
        },
        "scenarios": scenarios,
        "next_targets": {
            "new_clients_csv_records": max(20 - clients_count, 0),
            "weekly_outreach_target": 50,
            "weekly_meeting_target": 10,
            "weekly_close_target": 2,
        },
    }


def percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    xs = sorted(values)
    if len(xs) == 1:
        return int(xs[0])
    rank = (len(xs) - 1) * p
    low = int(rank)
    high = min(low + 1, len(xs) - 1)
    frac = rank - low
    return int(round(xs[low] + (xs[high] - xs[low]) * frac))


def simulate_pipeline(activity_rows: list[dict], scenarios: dict, horizons_weeks: list[int], runs: int, seed: int):
    baseline_closed_revenue = 0
    baseline_closed_deals = 0
    leads = []
    for row in activity_rows:
        status = normalize_status(str(row.get(H_STATUS, "new")))
        price = parse_int(row.get(H_OFFER_PRICE, 0), 0)
        actual = parse_int(row.get(H_ACTUAL_REV, 0), 0)
        if status == "closed":
            baseline_closed_revenue += actual or price
            baseline_closed_deals += 1
        else:
            leads.append({"status": status, "price": price})

    simulation = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "runs": runs,
        "seed": seed,
        "horizons_weeks": horizons_weeks,
        "baseline": {
            "closed_deals": baseline_closed_deals,
            "closed_revenue_krw": baseline_closed_revenue,
            "active_leads": len(leads),
        },
        "scenarios": {},
    }

    for scen_index, (name, s) in enumerate((scenarios or {}).items()):
        contact = float(s.get("contact_rate", 0.4))
        meeting = float(s.get("meeting_rate", 0.45))
        close = float(s.get("close_rate", 0.25))
        proposal = min(0.9, max(0.25, 0.45 + (meeting - 0.45) * 0.5))
        scenario_out = {"params": {"contact_rate": contact, "meeting_rate": meeting, "proposal_rate": proposal, "close_rate": close}, "horizons": {}}

        for w in horizons_weeks:
            rev_samples = []
            deal_samples = []
            for run_idx in range(runs):
                rng = random.Random(seed + scen_index * 100_000 + w * 10_000 + run_idx)
                revenue = baseline_closed_revenue
                deals = baseline_closed_deals

                for lead in leads:
                    status = lead["status"]
                    price = lead["price"]
                    for _ in range(w):
                        if status in ("closed", "lost"):
                            break
                        if status == "new":
                            if rng.random() < contact:
                                status = "contacted"
                            elif rng.random() < 0.02:
                                status = "lost"
                        elif status == "contacted":
                            if rng.random() < meeting:
                                status = "meeting"
                            elif rng.random() < 0.04:
                                status = "lost"
                        elif status == "meeting":
                            if rng.random() < proposal:
                                status = "proposal"
                            elif rng.random() < 0.04:
                                status = "lost"
                        elif status == "proposal":
                            if rng.random() < close:
                                status = "closed"
                                deals += 1
                                revenue += price
                            elif rng.random() < 0.06:
                                status = "lost"

                rev_samples.append(revenue)
                deal_samples.append(deals)

            key = f"{w}w"
            scenario_out["horizons"][key] = {
                "revenue": {
                    "mean_krw": int(round(sum(rev_samples) / len(rev_samples))) if rev_samples else 0,
                    "p10_krw": percentile(rev_samples, 0.10),
                    "p50_krw": percentile(rev_samples, 0.50),
                    "p90_krw": percentile(rev_samples, 0.90),
                },
                "deals": {
                    "mean": round(sum(deal_samples) / len(deal_samples), 2) if deal_samples else 0.0,
                    "p10": percentile(deal_samples, 0.10),
                    "p50": percentile(deal_samples, 0.50),
                    "p90": percentile(deal_samples, 0.90),
                },
            }

        simulation["scenarios"][name] = scenario_out
    return simulation


def write_simulation_report(simulation: dict):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_latest = RESULT_DIR / "sales_simulation_latest.json"
    json_archived = RESULT_DIR / f"Sales_Simulation_{ts}.json"
    md_latest = RESULT_DIR / "sales_simulation_latest.md"
    md_archived = RESULT_DIR / f"Sales_Simulation_{ts}.md"

    json_latest.write_text(json.dumps(simulation, ensure_ascii=False, indent=2), encoding="utf-8")
    json_archived.write_text(json.dumps(simulation, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Sales Simulation",
        "",
        f"- generated_at: {simulation.get('generated_at', '-')}",
        f"- runs: {simulation.get('runs', 0)}",
        f"- baseline_closed_revenue: {((simulation.get('baseline') or {}).get('closed_revenue_krw', 0)):,} KRW",
        "",
        "## Scenario Summary (8w P50)",
    ]
    scenarios = simulation.get("scenarios") or {}
    for name, data in scenarios.items():
        h = (data.get("horizons") or {}).get("8w") or {}
        r = h.get("revenue") or {}
        d = h.get("deals") or {}
        lines.append(
            f"- {name}: revenue_p50={r.get('p50_krw', 0):,} KRW (p10={r.get('p10_krw', 0):,}, p90={r.get('p90_krw', 0):,}), deals_p50={d.get('p50', 0)}"
        )
    lines += ["", "## Details"]
    for name, data in scenarios.items():
        lines.append(f"### {name}")
        for key, h in (data.get("horizons") or {}).items():
            r = h.get("revenue") or {}
            d = h.get("deals") or {}
            lines.append(
                f"- {key}: revenue mean={r.get('mean_krw', 0):,}, p50={r.get('p50_krw', 0):,} | deals mean={d.get('mean', 0)}, p50={d.get('p50', 0)}"
            )
        lines.append("")

    body = "\n".join(lines)
    md_latest.write_text(body, encoding="utf-8")
    md_archived.write_text(body, encoding="utf-8")
    return json_latest, json_archived, md_latest, md_archived


def write_weekly_report(kpi: dict, revenue_plan: dict, activity_rows: list[dict], queue: list[dict]):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = RESULT_DIR / "sales_weekly_report_latest.md"
    archived = RESULT_DIR / f"Sales_Weekly_Report_{ts}.md"

    rates = kpi.get("rates") or {}
    status_counts = kpi.get("status_counts") or {}
    pipeline = kpi.get("pipeline") or {}
    actions = []
    if rates.get("contacted_rate", 0) < 0.4:
        actions.append("Increase outreach volume: complete 50 first contacts this week.")
    if rates.get("meeting_rate", 0) < 0.35:
        actions.append("Improve qualification script and meeting CTA.")
    if rates.get("proposal_rate", 0) < 0.45:
        actions.append("Shorten proposal turnaround to within 24 hours after meeting.")
    if rates.get("close_rate", 0) < 0.2:
        actions.append("Add follow-up cadence at D+2 and D+5 for all proposals.")
    if not actions:
        actions.append("Maintain current funnel discipline and focus on proposal quality.")

    top20_expected = sum(parse_int(r.get(H_EXPECTED_REV, 0)) for r in queue[:20])
    lines = [
        "# Sales Weekly Report",
        "",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- total_leads: {kpi.get('total_leads', 0)}",
        f"- status: new={status_counts.get('new', 0)}, contacted={status_counts.get('contacted', 0)}, meeting={status_counts.get('meeting', 0)}, proposal={status_counts.get('proposal', 0)}, closed={status_counts.get('closed', 0)}, lost={status_counts.get('lost', 0)}",
        f"- rates: contacted={rates.get('contacted_rate', 0):.1%}, meeting={rates.get('meeting_rate', 0):.1%}, proposal={rates.get('proposal_rate', 0):.1%}, close={rates.get('close_rate', 0):.1%}",
        f"- pipeline: expected={pipeline.get('expected_revenue_sum_krw', 0):,} KRW, weighted={pipeline.get('weighted_pipeline_krw', 0):,} KRW, closed_actual={pipeline.get('actual_closed_revenue_krw', 0):,} KRW",
        f"- top20_expected: {top20_expected:,} KRW",
        "",
        "## This Week Actions",
    ]
    for i, a in enumerate(actions, start=1):
        lines.append(f"{i}. {a}")
    lines += [
        "",
        "## Revenue Scenarios",
    ]
    for name, s in (revenue_plan.get("scenarios") or {}).items():
        lines.append(f"- {name}: deals={s.get('expected_deals', 0)}, revenue={s.get('expected_revenue_krw', 0):,} KRW")
    lines += ["", "## Owners"]
    for owner in (kpi.get("owners") or [])[:10]:
        lines.append(
            f"- {owner.get('owner')}: leads={owner.get('count', 0)}, proposal={owner.get('proposal', 0)}, closed={owner.get('closed', 0)}"
        )
    lines.append("")

    body = "\n".join(lines)
    latest.write_text(body, encoding="utf-8")
    archived.write_text(body, encoding="utf-8")
    return latest, archived


def write_daily_plan(kpi: dict, queue: list[dict], targets: list[dict]):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = RESULT_DIR / "sales_daily_plan_latest.md"
    archived = RESULT_DIR / f"Sales_Daily_Plan_{ts}.md"

    status_counts = kpi.get("status_counts") or {}
    new_leads = [r for r in queue if str(r.get(H_NUMBER, "")).strip()][:15]
    new_targets = [t for t in targets if str(t.get(H_TARGET_STATUS, "new")).strip() == "new"][:10]

    lines = [
        "# Sales Daily Plan",
        "",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- backlog: new={status_counts.get('new', 0)}, contacted={status_counts.get('contacted', 0)}, proposal={status_counts.get('proposal', 0)}",
        "",
        "## Must-Do Today",
        "1. First contact 20 leads from sales_queue_latest.csv.",
        "2. Update all touched rows in sales_activity_latest.csv before end-of-day.",
        "3. Submit proposals within 24h after any meeting.",
        "",
        "## Top 15 Leads",
    ]
    for row in new_leads:
        lines.append(
            f"- {row.get(H_NUMBER, '')} | {row.get(H_BIZ, '')} | {row.get(H_ORG, '')} | score {row.get(H_LEAD_SCORE, '')} | expected {parse_int(row.get(H_EXPECTED_REV, 0)):,} KRW"
        )

    lines += ["", "## Top 10 Target Accounts"]
    for row in new_targets:
        lines.append(
            f"- {row.get(H_TARGET_ORG, '')} | leads {row.get(H_COUNT, 0)} | expected {parse_int(row.get(H_EXPECTED_SUM, 0)):,} KRW"
        )

    lines += [
        "",
        "## Call Script (Short)",
        "1. Mention relevant recent public project signal.",
        "2. Offer one concrete next step (monitoring pack or proposal support).",
        "3. Book a 15-minute follow-up immediately.",
        "",
    ]
    body = "\n".join(lines)
    latest.write_text(body, encoding="utf-8")
    archived.write_text(body, encoding="utf-8")
    return latest, archived


def write_brainstorm(summary: dict, revenue_plan: dict, queue: list[dict], accounts: list[dict], kpi: dict):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_latest = RESULT_DIR / "business_brainstorm_latest.md"
    out_archived = RESULT_DIR / f"Business_Brainstorm_{ts}.md"

    counts = summary.get("counts") or {}
    rates = (kpi.get("rates") or {})
    lines = [
        "# Business Brainstorm",
        "",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- run_id: {summary.get('run_id', '-')}",
        f"- all_count: {counts.get('all', 0)}",
        f"- disc_count: {counts.get('disc', 0)}",
        f"- funnel_close_rate: {rates.get('close_rate', 0):.1%}",
        "",
        "## Immediate Actions",
        "1. Call top 20 leads from sales_queue_latest.csv within 24 hours.",
        "2. Move each lead status in sales_activity_latest.csv.",
        "3. Review sales_weekly_report_latest.md every Friday.",
        "",
        "## Revenue Scenarios",
    ]
    for name, s in (revenue_plan.get("scenarios") or {}).items():
        lines.append(f"- {name}: deals={s.get('expected_deals', 0)}, monthly_revenue={s.get('expected_revenue_krw', 0):,} KRW")
    lines += ["", "## Top Accounts"]
    for row in accounts[:10]:
        lines.append(f"- {row[H_ORG]}: {row[H_COUNT]}건, 평균점수 {row[H_AVG_SCORE]}, 기대매출 {row[H_EXPECTED_SUM]:,}원")
    lines += [
        "",
        "## Weekly Experiment Ideas",
        "1. Outreach script A/B test by offer type.",
        "2. Proposal deck A/B test (cost-saving vs speed-first).",
        "3. Owner-level conversion coaching using KPI gaps.",
        "",
    ]
    body = "\n".join(lines)
    out_latest.write_text(body, encoding="utf-8")
    out_archived.write_text(body, encoding="utf-8")
    return out_latest, out_archived


def parse_args():
    p = argparse.ArgumentParser(description="Generate business outputs from latest G2B data.")
    p.add_argument("--top-n", type=int, default=150, help="Number of leads to keep in sales queue")
    p.add_argument("--sim-runs", type=int, default=2000, help="Monte Carlo simulation runs")
    p.add_argument("--sim-seed", type=int, default=42, help="Random seed for simulation")
    p.add_argument("--sim-horizons", default="4,8,12", help="Simulation horizons in weeks, e.g. 4,8,12")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    RESULT_DIR.mkdir(exist_ok=True)

    all_rows = load_json(LATEST_ALL, [])
    summary = load_json(LATEST_SUMMARY, {})
    clients_count = parse_clients_count()
    if not all_rows:
        print("[ERR] latest_all.json is missing or empty")
        return 1

    queue, accounts = build_sales_queue(all_rows, args.top_n)
    revenue_plan = build_revenue_plan(summary, queue, clients_count)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    queue_latest = RESULT_DIR / "sales_queue_latest.csv"
    queue_archived = RESULT_DIR / f"Sales_Queue_{ts}.csv"
    acc_latest = RESULT_DIR / "sales_accounts_latest.csv"
    acc_archived = RESULT_DIR / f"Sales_Accounts_{ts}.csv"
    rev_latest = RESULT_DIR / "revenue_plan_latest.json"
    rev_archived = RESULT_DIR / f"Revenue_Plan_{ts}.json"
    target_latest = RESULT_DIR / "client_targets_latest.csv"
    target_archived = RESULT_DIR / f"Client_Targets_{ts}.csv"
    kpi_latest = RESULT_DIR / "sales_kpi_latest.json"
    kpi_archived = RESULT_DIR / f"Sales_KPI_{ts}.json"

    queue_fields = [
        H_NUMBER,
        H_BIZ,
        H_ORG,
        H_CATEGORY,
        H_CONTRACT_TYPE,
        H_REGION,
        H_CONTACT_NAME,
        H_CONTACT_TEL,
        H_BUDGET_EOK,
        H_LEAD_SCORE,
        H_TIER,
        H_OFFER,
        H_OFFER_PRICE,
        H_CLOSE_PROB,
        H_EXPECTED_REV,
        H_REASON,
    ]
    write_csv(queue_latest, queue, queue_fields)
    write_csv(queue_archived, queue, queue_fields)

    acc_fields = [H_ORG, H_COUNT, H_AVG_SCORE, H_EXPECTED_SUM, H_TOP_CATEGORY, H_TOP_REGION]
    write_csv(acc_latest, accounts, acc_fields)
    write_csv(acc_archived, accounts, acc_fields)

    existing_targets = load_existing_targets(target_latest)
    targets = build_client_targets(accounts, existing_targets, limit=40)
    target_fields = [H_TARGET_ORG, H_COUNT, H_EXPECTED_SUM, H_TOP_CATEGORY, H_TOP_REGION, H_TARGET_STATUS, H_TARGET_MEMO, H_TARGET_UPDATED]
    write_csv(target_latest, targets, target_fields)
    write_csv(target_archived, targets, target_fields)

    rev_latest.write_text(json.dumps(revenue_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    rev_archived.write_text(json.dumps(revenue_plan, ensure_ascii=False, indent=2), encoding="utf-8")

    act_latest = RESULT_DIR / "sales_activity_latest.csv"
    act_archived = RESULT_DIR / f"Sales_Activity_{ts}.csv"
    existing = load_existing_activity(act_latest)
    activity_rows = build_activity_rows(queue, existing, top_n=50)
    act_fields = [
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
        H_ACTUAL_REV,
        H_MEMO,
        H_UPDATED_AT,
    ]
    write_csv(act_latest, activity_rows, act_fields)
    write_csv(act_archived, activity_rows, act_fields)

    kpi = build_sales_kpi(activity_rows)
    kpi_latest.write_text(json.dumps(kpi, ensure_ascii=False, indent=2), encoding="utf-8")
    kpi_archived.write_text(json.dumps(kpi, ensure_ascii=False, indent=2), encoding="utf-8")

    horizons = []
    for token in str(args.sim_horizons or "").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            w = int(token)
        except Exception:
            continue
        if w > 0:
            horizons.append(w)
    if not horizons:
        horizons = [4, 8, 12]

    simulation = simulate_pipeline(
        activity_rows=activity_rows,
        scenarios=revenue_plan.get("scenarios") or {},
        horizons_weeks=sorted(set(horizons)),
        runs=max(100, int(args.sim_runs)),
        seed=int(args.sim_seed),
    )
    sim_json_latest, sim_json_archived, sim_md_latest, sim_md_archived = write_simulation_report(simulation)

    daily_latest, daily_archived = write_daily_plan(kpi, queue, targets)
    weekly_latest, weekly_archived = write_weekly_report(kpi, revenue_plan, activity_rows, queue)
    bs_latest, bs_archived = write_brainstorm(summary, revenue_plan, queue, accounts, kpi)

    print(f"[OK] sales_queue: {queue_latest} ({len(queue)} rows)")
    print(f"[OK] sales_accounts: {acc_latest} ({len(accounts)} rows)")
    print(f"[OK] client_targets: {target_latest} ({len(targets)} rows)")
    print(f"[OK] sales_activity: {act_latest} ({len(activity_rows)} rows)")
    print(f"[OK] sales_kpi: {kpi_latest}")
    print(f"[OK] simulation_json: {sim_json_latest}")
    print(f"[OK] simulation_report: {sim_md_latest}")
    print(f"[OK] revenue_plan: {rev_latest}")
    print(f"[OK] daily_plan: {daily_latest}")
    print(f"[OK] weekly_report: {weekly_latest}")
    print(f"[OK] brainstorm: {bs_latest}")
    print(f"[ARCHIVE] {queue_archived}")
    print(f"[ARCHIVE] {acc_archived}")
    print(f"[ARCHIVE] {target_archived}")
    print(f"[ARCHIVE] {act_archived}")
    print(f"[ARCHIVE] {kpi_archived}")
    print(f"[ARCHIVE] {sim_json_archived}")
    print(f"[ARCHIVE] {sim_md_archived}")
    print(f"[ARCHIVE] {rev_archived}")
    print(f"[ARCHIVE] {daily_archived}")
    print(f"[ARCHIVE] {weekly_archived}")
    print(f"[ARCHIVE] {bs_archived}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
