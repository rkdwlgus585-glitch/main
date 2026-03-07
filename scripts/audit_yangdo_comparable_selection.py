from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yangdo_blackbox_api
from core_engine.yangdo_duplicate_cluster import collapse_duplicate_neighbors


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _to_float(value: Any) -> Optional[float]:
    return yangdo_blackbox_api._to_float(value)


def _round4(value: Any) -> Optional[float]:
    num = _to_float(value)
    if num is None:
        return None
    return round(num, 4)


def _record_key(rec: Dict[str, Any]) -> Tuple[str, int]:
    return (str(rec.get("uid") or "").strip(), int(rec.get("row") or 0))


def _combo_key_from_tokens(tokens: Iterable[str]) -> Tuple[str, ...]:
    return tuple(sorted(str(x).strip() for x in list(tokens or []) if str(x).strip()))


def _combo_key(rec: Dict[str, Any]) -> Tuple[str, ...]:
    return _combo_key_from_tokens(rec.get("license_tokens") or set())


def _group_key(rec: Dict[str, Any]) -> Tuple[str, ...]:
    combo = _combo_key(rec)
    if combo:
        return combo
    raw = yangdo_blackbox_api._normalize_license_key(rec.get("license_text") or rec.get("raw_license_key") or "")
    if raw:
        return (f"[raw]{raw}",)
    return ("[missing]",)


def _combo_label(combo: Iterable[str]) -> str:
    items = []
    for raw in list(combo or []):
        text = str(raw).strip()
        if not text:
            continue
        if text.startswith("[raw]"):
            text = text[5:]
        items.append(text)
    return " + ".join(items) if items else "(none)"


def _payload_from_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "license_text": rec.get("license_text"),
        "specialty": rec.get("specialty"),
        "sales3_eok": rec.get("sales3_eok"),
        "sales5_eok": rec.get("sales5_eok"),
        "balance_eok": rec.get("balance_eok"),
        "capital_eok": rec.get("capital_eok"),
        "surplus_eok": rec.get("surplus_eok"),
        "license_year": rec.get("license_year"),
        "debt_ratio": rec.get("debt_ratio"),
        "liq_ratio": rec.get("liq_ratio"),
        "company_type": rec.get("company_type") or "",
        "credit_level": rec.get("credit_level") or "",
        "admin_history": rec.get("admin_history") or "",
        "reorg_mode": "share",
        "source": "comparable_selection_audit",
    }


def _top_counter(counter: Counter, limit: int = 8) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for key, count in counter.most_common(limit):
        out.append({"key": str(key), "count": int(count)})
    return out


def _score_pool_instrumented(
    estimator: yangdo_blackbox_api.YangdoBlackboxEstimator,
    target: Dict[str, Any],
    pool: List[Dict[str, Any]],
    *,
    strict_same_core: bool,
    threshold: float,
    tokens: set,
    target_core_set: set,
    target_core_count: int,
) -> Tuple[List[Tuple[float, Dict[str, Any]]], Counter]:
    rejects: Counter = Counter()
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for cand in pool:
        price = cand.get("current_price_eok")
        if not isinstance(price, (int, float)) or float(price) <= 0:
            rejects["no_price"] += 1
            continue
        cand_tokens = estimator._canonical_tokens(cand.get("license_tokens") or set())
        cand_core = estimator._core_tokens(cand_tokens) | estimator._core_tokens_from_text(cand.get("license_text"))
        if target_core_count >= 2 and target_core_set and not (target_core_set & cand_core):
            rejects["multi_core_no_overlap"] += 1
            continue
        if strict_same_core and not estimator._is_single_token_same_core(tokens, cand_tokens, cand.get("license_text")):
            rejects["strict_same_core_miss"] += 1
            continue
        if estimator._is_single_token_cross_combo(tokens, cand_tokens, cand.get("license_text")):
            rejects["single_core_cross_combo"] += 1
            continue
        if estimator._is_single_token_profile_outlier(target, cand):
            rejects["single_core_profile_outlier"] += 1
            continue
        sim = estimator._neighbor_score(target, cand)
        if sim < threshold:
            rejects["below_similarity_threshold"] += 1
            continue
        scored.append((sim, cand))
    return scored, rejects


def _collect_neighbors_instrumented(
    estimator: yangdo_blackbox_api.YangdoBlackboxEstimator,
    target: Dict[str, Any],
    train_records: List[Dict[str, Any]],
    token_index: Dict[str, List[Dict[str, Any]]],
    *,
    top_k: int,
) -> Dict[str, Any]:
    tokens = estimator._canonical_tokens(target.get("license_tokens") or set())
    candidates: List[Dict[str, Any]] = []
    seen = set()
    direct_token_hits = 0
    fuzzy_added = 0
    raw_hint_count = 0
    full_train_fallback = ""

    if tokens:
        for token in tokens:
            for rec in token_index.get(token, []):
                marker = _record_key(rec)
                if marker in seen:
                    continue
                seen.add(marker)
                candidates.append(rec)
                direct_token_hits += 1
    if tokens and len(candidates) < 40:
        for rec in train_records:
            marker = _record_key(rec)
            if marker in seen:
                continue
            cand_tokens = estimator._canonical_tokens(rec.get("license_tokens") or set())
            if estimator._has_fuzzy_token_overlap(tokens, cand_tokens):
                seen.add(marker)
                candidates.append(rec)
                fuzzy_added += 1

    raw_key = yangdo_blackbox_api._normalize_license_key(target.get("raw_license_key") or target.get("license_text"))
    raw_hint_used = False
    if (not tokens) and raw_key and len(raw_key) >= 2:
        hinted = []
        for rec in train_records:
            text = yangdo_blackbox_api._normalize_license_key(rec.get("license_text"))
            if not text:
                continue
            if (raw_key in text) or (text in raw_key) or (yangdo_blackbox_api._bigram_jaccard(raw_key, text) >= 0.55):
                hinted.append(rec)
        raw_hint_count = len(hinted)
        if hinted:
            candidates = hinted
            raw_hint_used = True
    if len(candidates) < 80 and not tokens:
        candidates = list(train_records)
        full_train_fallback = "no_token_sparse"
    elif tokens and not candidates:
        candidates = list(train_records)
        full_train_fallback = "token_empty"

    target_core_set = estimator._core_tokens(tokens)
    target_core_count = len(target_core_set)

    min_similarity = 26.0 if tokens else 12.0
    if target_core_count >= 2:
        min_similarity = 32.0
    if tokens and len(candidates) <= 16:
        min_similarity = max(20.0, min_similarity - 4.0)
    if int(target.get("provided_signals") or 0) <= 2:
        min_similarity += 6.0
    missing_critical = list(target.get("missing_critical") or [])
    if tokens and not missing_critical:
        min_similarity += 3.0

    strict_same_core = target_core_count == 1
    scored, rejects = _score_pool_instrumented(
        estimator,
        target,
        candidates,
        strict_same_core=strict_same_core,
        threshold=float(min_similarity),
        tokens=tokens,
        target_core_set=target_core_set,
        target_core_count=target_core_count,
    )
    lowered_threshold_used = False
    lowered_threshold = None
    if strict_same_core and not scored:
        lowered_threshold = max(12.0, float(min_similarity) - 8.0)
        scored, lowered_rejects = _score_pool_instrumented(
            estimator,
            target,
            candidates,
            strict_same_core=True,
            threshold=float(lowered_threshold),
            tokens=tokens,
            target_core_set=target_core_set,
            target_core_count=target_core_count,
        )
        rejects = lowered_rejects
        lowered_threshold_used = True

    coarse_used = False
    coarse_pool_size = 0
    if not scored:
        coarse_used = True
        coarse_pool = candidates if (tokens and candidates) else train_records
        coarse_pool_size = len(coarse_pool)
        coarse: List[Tuple[float, Dict[str, Any]]] = []
        for cand in coarse_pool:
            price = cand.get("current_price_eok")
            if not isinstance(price, (int, float)) or float(price) <= 0:
                continue
            cand_tokens = estimator._canonical_tokens(cand.get("license_tokens") or set())
            cand_core = estimator._core_tokens(cand_tokens) | estimator._core_tokens_from_text(cand.get("license_text"))
            if target_core_count >= 2 and target_core_set and not (target_core_set & cand_core):
                continue
            if strict_same_core and not estimator._is_single_token_same_core(tokens, cand_tokens, cand.get("license_text")):
                continue
            if estimator._is_single_token_cross_combo(tokens, cand_tokens, cand.get("license_text")):
                continue
            if estimator._is_single_token_profile_outlier(target, cand):
                continue
            sim = estimator._neighbor_score(target, cand)
            coarse.append((max(0.1, sim), cand))
        coarse.sort(key=lambda x: x[0], reverse=True)
        final = coarse[: max(18, min(22, top_k))]
        return {
            "tokens": list(sorted(tokens)),
            "target_core_tokens": list(sorted(target_core_set)),
            "target_core_count": int(target_core_count),
            "direct_token_hits": int(direct_token_hits),
            "fuzzy_added": int(fuzzy_added),
            "raw_hint_used": bool(raw_hint_used),
            "raw_hint_count": int(raw_hint_count),
            "full_train_fallback": full_train_fallback,
            "candidate_count": int(len(candidates)),
            "min_similarity": _round4(min_similarity),
            "strict_same_core": bool(strict_same_core),
            "lowered_threshold_used": bool(lowered_threshold_used),
            "lowered_threshold": _round4(lowered_threshold),
            "coarse_used": True,
            "coarse_pool_size": int(coarse_pool_size),
            "rejects": {str(k): int(v) for k, v in rejects.items()},
            "scored_count": 0,
            "returned": final,
            "returned_count": int(len(final)),
        }

    scored.sort(key=lambda x: x[0], reverse=True)
    if strict_same_core:
        strict_rows: List[Tuple[float, Dict[str, Any]]] = []
        for sim, cand in scored:
            cand_tokens = estimator._canonical_tokens(cand.get("license_tokens") or set())
            if estimator._is_single_token_cross_combo(tokens, cand_tokens, cand.get("license_text")):
                continue
            if not estimator._is_single_token_same_core(tokens, cand_tokens, cand.get("license_text")):
                continue
            if not cand_tokens:
                strict_rows.append((sim, cand))
                continue
            inter_count = len(tokens & cand_tokens)
            precision = inter_count / float(max(1, len(cand_tokens)))
            if len(cand_tokens) == 1 or precision >= 0.60:
                strict_rows.append((sim, cand))
        if len(strict_rows) >= max(10, top_k):
            scored = strict_rows
    elif target_core_count >= 2:
        strict_multi: List[Tuple[float, Dict[str, Any]]] = []
        for sim, cand in scored:
            cand_tokens = estimator._canonical_tokens(cand.get("license_tokens") or set())
            cand_core = estimator._core_tokens(cand_tokens) | estimator._core_tokens_from_text(cand.get("license_text"))
            if not cand_core:
                continue
            inter_core = len(target_core_set & cand_core)
            core_contain = inter_core / float(max(1, min(len(target_core_set), len(cand_core))))
            token_contain = yangdo_blackbox_api._token_containment(tokens, cand_tokens) if tokens else 0.0
            if inter_core >= min(2, target_core_count) or max(core_contain, token_contain) >= 0.60:
                strict_multi.append((sim, cand))
        if len(strict_multi) >= max(8, top_k):
            scored = strict_multi

    final = scored[: max(top_k, 12, 14 if tokens else 12)]
    return {
        "tokens": list(sorted(tokens)),
        "target_core_tokens": list(sorted(target_core_set)),
        "target_core_count": int(target_core_count),
        "direct_token_hits": int(direct_token_hits),
        "fuzzy_added": int(fuzzy_added),
        "raw_hint_used": bool(raw_hint_used),
        "raw_hint_count": int(raw_hint_count),
        "full_train_fallback": full_train_fallback,
        "candidate_count": int(len(candidates)),
        "min_similarity": _round4(min_similarity),
        "strict_same_core": bool(strict_same_core),
        "lowered_threshold_used": bool(lowered_threshold_used),
        "lowered_threshold": _round4(lowered_threshold),
        "coarse_used": False,
        "coarse_pool_size": 0,
        "rejects": {str(k): int(v) for k, v in rejects.items()},
        "scored_count": int(len(scored)),
        "returned": final,
        "returned_count": int(len(final)),
    }


def _neighbor_combo_breakdown(
    estimator: yangdo_blackbox_api.YangdoBlackboxEstimator,
    target_tokens: set,
    target_core_tokens: set,
    rows: List[Tuple[float, Dict[str, Any]]],
) -> Dict[str, Any]:
    combo_counter: Counter = Counter()
    same_combo = 0
    same_core = 0
    cross_combo = 0
    samples: List[Dict[str, Any]] = []
    for sim, rec in rows:
        cand_tokens = estimator._canonical_tokens(rec.get("license_tokens") or set())
        combo = _combo_key_from_tokens(cand_tokens)
        combo_counter[_combo_label(combo)] += 1
        cand_core = estimator._core_tokens(cand_tokens) | estimator._core_tokens_from_text(rec.get("license_text"))
        if cand_tokens == target_tokens:
            same_combo += 1
        if target_core_tokens and cand_core == target_core_tokens:
            same_core += 1
        if estimator._is_single_token_cross_combo(target_tokens, cand_tokens, rec.get("license_text")):
            cross_combo += 1
        if len(samples) < 5:
            samples.append(
                {
                    "sim": _round4(sim),
                    "uid": str(rec.get("uid") or ""),
                    "number": int(rec.get("number") or 0),
                    "license_text": str(rec.get("license_text") or ""),
                    "combo_label": _combo_label(combo),
                    "current_price_eok": _round4(rec.get("current_price_eok")),
                }
            )
    total = max(1, len(rows))
    return {
        "same_combo_count": int(same_combo),
        "same_combo_ratio": _round4(float(same_combo) / float(total)),
        "same_core_count": int(same_core),
        "same_core_ratio": _round4(float(same_core) / float(total)),
        "cross_combo_count": int(cross_combo),
        "top_neighbor_combos": _top_counter(combo_counter, limit=8),
        "neighbor_samples": samples,
    }


def _analyze_record(
    estimator: yangdo_blackbox_api.YangdoBlackboxEstimator,
    rec: Dict[str, Any],
    train_records: List[Dict[str, Any]],
    token_index: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    payload = _payload_from_record(rec)
    target = estimator._target_from_payload(payload)
    balance_excluded = estimator._is_balance_separate_paid_group(target)
    split_optional_pricing = bool(target.get("split_optional_pricing"))
    target["balance_excluded"] = bool(balance_excluded)
    if balance_excluded:
        target["balance_eok"] = None
        target["missing_critical"] = [x for x in list(target.get("missing_critical") or []) if "공제조합" not in str(x)]
    if split_optional_pricing:
        target["specialty"] = None
        target["surplus_eok"] = None
        target["debt_ratio"] = None
        target["liq_ratio"] = None
        target["credit_level"] = ""
        target["missing_critical"] = [
            x for x in list(target.get("missing_critical") or []) if ("이익잉여금" not in str(x)) and ("시평" not in str(x))
        ]

    top_k = 12
    seed = _collect_neighbors_instrumented(estimator, target, train_records, token_index, top_k=top_k)
    stat_scan_k = max(180, min(1200, top_k * 24))
    stat = _collect_neighbors_instrumented(estimator, target, train_records, token_index, top_k=stat_scan_k)
    stat_candidates = list(stat.get("returned") or [])
    if not stat_candidates:
        stat_candidates = list(seed.get("returned") or [])

    seed_neighbors = list(stat_candidates[: min(18, len(stat_candidates))])
    seed_prices = [float(x[1].get("current_price_eok")) for x in seed_neighbors]
    seed_sims = [float(x[0]) for x in seed_neighbors]
    seed_center = None
    outlier_trim_kept = len(stat_candidates)
    outlier_trim_dropped = 0
    if seed_neighbors:
        seed_center = yangdo_blackbox_api.core._weighted_quantile(seed_prices, seed_sims, 0.5)
    if seed_center is not None and seed_center > 0 and len(seed_neighbors) >= 8:
        filtered: List[Tuple[float, Dict[str, Any]]] = []
        for sim, row in stat_candidates:
            price = _to_float(row.get("current_price_eok"))
            if price is None or price <= 0:
                continue
            ratio = price / float(seed_center)
            lower = 0.22 if target.get("license_tokens") else 0.12
            upper = 4.8 if target.get("license_tokens") else 7.0
            if float(sim) >= 88:
                lower = min(lower, 0.16)
                upper = max(upper, 5.5)
            if lower <= ratio <= upper:
                filtered.append((sim, row))
        if len(filtered) >= max(8, top_k):
            outlier_trim_kept = len(filtered)
            outlier_trim_dropped = max(0, len(stat_candidates) - len(filtered))
            stat_candidates = filtered

    target_tokens = estimator._canonical_tokens(target.get("license_tokens") or set())
    target_core_tokens = estimator._core_tokens(target_tokens)
    token_count = len(target_core_tokens) if target_core_tokens else len(target_tokens)
    sim_window = 18.0 if token_count >= 2 else (14.0 if token_count == 1 else 10.0)
    best_sim = float(stat_candidates[0][0]) if stat_candidates else 0.0
    stat_floor = max(20.0 if token_count >= 2 else (14.0 if token_count == 1 else 10.0), best_sim - sim_window)
    stat_neighbors = [(sim, row) for sim, row in stat_candidates if float(sim) >= stat_floor]
    min_stat_size = max(10, top_k)
    if len(stat_neighbors) < min_stat_size:
        stat_neighbors = stat_candidates[: max(min_stat_size, top_k * 4)]
    single_core_reference_pool = list(stat_neighbors)

    feature_dropped = 0
    feature_consistent: List[Tuple[float, Dict[str, Any]]] = []
    for sim, row in stat_neighbors:
        signal_count, mismatch_count = estimator._feature_scale_mismatch(target, row, balance_excluded=bool(balance_excluded))
        hard_scale_mismatch = signal_count >= 2 and mismatch_count >= signal_count
        if hard_scale_mismatch:
            feature_dropped += 1
            continue
        mismatch_sim_cap = 94.0 if token_count >= 2 else 96.0
        if signal_count >= 2 and mismatch_count >= 2 and float(sim) < mismatch_sim_cap:
            feature_dropped += 1
            continue
        feature_consistent.append((sim, row))
    feature_floor = 4 if token_count == 1 else (3 if token_count >= 2 else 6)
    feature_filter_applied = len(feature_consistent) >= max(feature_floor, min(8, top_k))
    if feature_filter_applied:
        stat_neighbors = feature_consistent

    yearly_filter_applied = False
    yearly_dropped = 0
    target_profile = yangdo_blackbox_api._yearly_share_profile(target)
    if target_profile.get("count", 0) >= 2 and len(stat_neighbors) >= max(10, top_k):
        target_dom_idx = target_profile.get("dominant_idx")
        target_dom_share = float(target_profile.get("dominant_share") or 0.0)
        skewed_target = (target_dom_idx is not None) and target_dom_share >= 0.76
        prof_filtered: List[Tuple[float, Dict[str, Any]]] = []
        for sim, row in stat_neighbors:
            cand_profile = yangdo_blackbox_api._yearly_share_profile(row)
            if cand_profile.get("count", 0) < 2:
                if float(sim) >= 92:
                    prof_filtered.append((sim, row))
                else:
                    yearly_dropped += 1
                continue
            yearly = yangdo_blackbox_api._yearly_shape_similarity(target, row)
            shape = float(yearly.get("shape") or 0.0)
            strength = float(yearly.get("strength") or 0.0)
            cand_dom_idx = cand_profile.get("dominant_idx")
            cand_dom_share = float(cand_profile.get("dominant_share") or 0.0)
            same_dom = (target_dom_idx is not None) and (cand_dom_idx == target_dom_idx)
            if skewed_target:
                if same_dom and cand_dom_share >= 0.56 and shape >= 0.30:
                    prof_filtered.append((sim, row))
                    continue
                if shape >= 0.52 and strength >= 0.55:
                    prof_filtered.append((sim, row))
                    continue
                if float(sim) >= 96 and shape >= 0.42:
                    prof_filtered.append((sim, row))
                    continue
                yearly_dropped += 1
                continue
            if strength >= 0.60 and shape < 0.24:
                yearly_dropped += 1
                continue
            prof_filtered.append((sim, row))
        if len(prof_filtered) >= max(8, top_k):
            stat_neighbors = prof_filtered
            yearly_filter_applied = True

    def _single_core_strict(rows: List[Tuple[float, Dict[str, Any]]]) -> List[Tuple[float, Dict[str, Any]]]:
        out: List[Tuple[float, Dict[str, Any]]] = []
        for sim, row in rows:
            cand_tokens = estimator._canonical_tokens(row.get("license_tokens") or set())
            if estimator._is_single_token_cross_combo(target_tokens, cand_tokens, row.get("license_text")):
                continue
            if not estimator._is_single_token_same_core(target_tokens, cand_tokens, row.get("license_text")):
                continue
            yearly = yangdo_blackbox_api._yearly_shape_similarity(target, row)
            if yearly["strength"] >= 0.60 and yearly["shape"] < 0.44:
                continue
            out.append((sim, row))
        return out

    single_core = estimator._single_token_target_core(target_tokens)
    single_core_reference_neighbors: List[Tuple[float, Dict[str, Any]]] = []
    single_core_strict_count = 0
    if single_core:
        single_core_reference_neighbors = _single_core_strict(list(seed.get("returned") or []))
        strict_neighbors = _single_core_strict(stat_neighbors)
        single_core_strict_count = len(strict_neighbors)
        if not single_core_reference_neighbors:
            single_core_reference_neighbors = list(strict_neighbors)
        if not single_core_reference_neighbors and single_core_reference_pool:
            single_core_reference_neighbors = _single_core_strict(single_core_reference_pool)
        if len(strict_neighbors) >= max(8, top_k):
            stat_neighbors = strict_neighbors
        elif len(strict_neighbors) >= 4 and len(stat_neighbors) >= max(8, top_k):
            selected = list(strict_neighbors)
            picked = {(_record_key(x[1])) for x in strict_neighbors}
            for sim, row in stat_neighbors:
                marker = _record_key(row)
                if marker in picked:
                    continue
                cand_tokens = estimator._canonical_tokens(row.get("license_tokens") or set())
                if estimator._is_single_token_cross_combo(target_tokens, cand_tokens, row.get("license_text")):
                    continue
                if not estimator._is_single_token_same_core(target_tokens, cand_tokens, row.get("license_text")):
                    continue
                selected.append((sim, row))
                if len(selected) >= max(8, top_k):
                    break
            stat_neighbors = selected

    cluster_meta = collapse_duplicate_neighbors(stat_neighbors)
    raw_neighbor_count = int(cluster_meta.get("raw_neighbor_count", len(stat_neighbors)) or len(stat_neighbors))
    effective_cluster_count = int(cluster_meta.get("effective_cluster_count", len(stat_neighbors)) or len(stat_neighbors))
    if list(cluster_meta.get("collapsed_neighbors") or []):
        stat_neighbors = list(cluster_meta.get("collapsed_neighbors") or [])
    display_neighbors = stat_neighbors[: max(top_k, 12)]

    result = estimator.estimate(dict(payload))
    neighbor_breakdown = _neighbor_combo_breakdown(estimator, target_tokens, target_core_tokens, display_neighbors)
    return {
        "number": int(rec.get("number") or 0),
        "uid": str(rec.get("uid") or ""),
        "license_text": str(rec.get("license_text") or ""),
        "combo": list(_group_key(rec)),
        "combo_label": _combo_label(_group_key(rec)),
        "price_eok": _round4(rec.get("current_price_eok")),
        "seed": {
            k: v for k, v in seed.items() if k != "returned"
        },
        "stat": {
            "requested_top_k": int(stat_scan_k),
            "collector": {k: v for k, v in stat.items() if k != "returned"},
            "seed_center_eok": _round4(seed_center),
            "outlier_trim_kept": int(outlier_trim_kept),
            "outlier_trim_dropped": int(outlier_trim_dropped),
            "similarity_floor": _round4(stat_floor),
            "after_similarity_floor": int(len(stat_neighbors)),
            "feature_filter_applied": bool(feature_filter_applied),
            "feature_dropped": int(feature_dropped),
            "yearly_filter_applied": bool(yearly_filter_applied),
            "yearly_dropped": int(yearly_dropped),
            "single_core_reference_count": int(len(single_core_reference_neighbors)),
            "single_core_strict_count": int(single_core_strict_count),
            "raw_neighbor_count": int(raw_neighbor_count),
            "effective_cluster_count": int(effective_cluster_count),
            "display_neighbor_count": int(len(display_neighbors)),
        },
        "result": {
            "ok": bool(result.get("ok")),
            "publication_mode": str(result.get("publication_mode") or ""),
            "confidence_percent": int(result.get("confidence_percent") or 0),
            "avg_similarity": _round4(result.get("avg_similarity")),
            "neighbor_count": int(result.get("neighbor_count") or 0),
            "raw_neighbor_count": int(result.get("raw_neighbor_count") or 0),
            "effective_cluster_count": int(result.get("effective_cluster_count") or 0),
            "display_neighbor_count": int(result.get("display_neighbor_count") or 0),
            "base_model_applied": bool(result.get("base_model_applied")),
            "balance_pass_through": _round4(result.get("balance_pass_through")),
        },
        "neighbor_breakdown": neighbor_breakdown,
    }


def _render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Yangdo Comparable Selection Audit")
    lines.append("")
    lines.append(f"- generated_at: {report['generated_at']}")
    lines.append(f"- priced_records_analyzed: {report['priced_records_analyzed']}")
    lines.append(f"- observed_unique_combos: {report['observed_unique_combos']}")
    lines.append(f"- overall_publication_modes: {json.dumps(report['overall_publication_modes'], ensure_ascii=False)}")
    lines.append(f"- overall_source_usage: {json.dumps(report['overall_source_usage'], ensure_ascii=False)}")
    lines.append("")
    lines.append("## Broad Match Hotspots")
    for item in report.get("broad_match_hotspots", [])[:20]:
        lines.append(
            f"- {item['combo_label']} | records={item['records']} | exact_share={item['avg_same_combo_ratio']} | "
            f"same_core={item['avg_same_core_ratio']} | fuzzy_avg={item['avg_fuzzy_added']} | full_train={item['full_train_fallback_records']}"
        )
    lines.append("")
    lines.append("## Sparse Support Hotspots")
    for item in report.get("sparse_support_hotspots", [])[:20]:
        lines.append(
            f"- {item['combo_label']} | records={item['records']} | effective_clusters={item['avg_effective_cluster_count']} | "
            f"display_neighbors={item['avg_display_neighbor_count']} | publication={json.dumps(item['publication_modes'], ensure_ascii=False)}"
        )
    lines.append("")
    lines.append("## Top Combo Summaries")
    for item in report.get("combo_summaries", [])[:30]:
        lines.append(
            f"- {item['combo_label']} | n={item['records']} | source={json.dumps(item['source_usage'], ensure_ascii=False)} | "
            f"exact={item['avg_same_combo_ratio']} | same_core={item['avg_same_core_ratio']} | top_neighbors={json.dumps(item['top_neighbor_combos'], ensure_ascii=False)}"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit yangdo comparable selection across all priced industries")
    parser.add_argument("--report-json", default="logs/yangdo_comparable_selection_audit_latest.json")
    parser.add_argument("--report-md", default="logs/yangdo_comparable_selection_audit_latest.md")
    args = parser.parse_args()

    estimator = yangdo_blackbox_api.YangdoBlackboxEstimator()
    estimator.refresh()
    train_records, token_index, _meta = estimator._snapshot()
    combo_groups: Dict[Tuple[str, ...], List[Dict[str, Any]]] = defaultdict(list)
    analyses: List[Dict[str, Any]] = []
    overall_publication_modes: Counter = Counter()
    overall_source_usage: Counter = Counter()

    for rec in train_records:
        combo = _group_key(rec)
        if not combo or len(combo) > 6:
            continue
        combo_groups[combo].append(rec)
        analysis = _analyze_record(estimator, rec, train_records, token_index)
        analyses.append(analysis)
        overall_publication_modes[str(analysis["result"]["publication_mode"] or "")] += 1
        seed_info = analysis["seed"]
        if seed_info.get("full_train_fallback"):
            overall_source_usage[f"full_train:{seed_info['full_train_fallback']}"] += 1
        elif seed_info.get("raw_hint_used"):
            overall_source_usage["raw_hint"] += 1
        elif int(seed_info.get("fuzzy_added") or 0) > 0:
            overall_source_usage["token_plus_fuzzy"] += 1
        else:
            overall_source_usage["direct_token_only"] += 1

    combo_summaries: List[Dict[str, Any]] = []
    for combo, rows in sorted(combo_groups.items(), key=lambda x: (len(x[0]), x[0])):
        row_map = {str(item["uid"]): item for item in analyses if tuple(item["combo"]) == combo}
        selected = [row_map[str(rec.get("uid") or "")] for rec in rows if str(rec.get("uid") or "") in row_map]
        if not selected:
            continue
        neighbor_combo_counter: Counter = Counter()
        reject_counter: Counter = Counter()
        publication_counter: Counter = Counter()
        source_counter: Counter = Counter()
        same_combo_vals: List[float] = []
        same_core_vals: List[float] = []
        fuzzy_vals: List[float] = []
        effective_vals: List[float] = []
        display_vals: List[float] = []
        full_train_count = 0
        raw_hint_count = 0
        for item in selected:
            for entry in item["neighbor_breakdown"]["top_neighbor_combos"]:
                neighbor_combo_counter[str(entry["key"])] += int(entry["count"])
            for key, value in dict(item["seed"].get("rejects") or {}).items():
                reject_counter[str(key)] += int(value)
            publication_counter[str(item["result"]["publication_mode"] or "")] += 1
            same_combo_vals.append(float(item["neighbor_breakdown"].get("same_combo_ratio") or 0.0))
            same_core_vals.append(float(item["neighbor_breakdown"].get("same_core_ratio") or 0.0))
            fuzzy_vals.append(float(item["seed"].get("fuzzy_added") or 0.0))
            effective_vals.append(float(item["stat"].get("effective_cluster_count") or 0.0))
            display_vals.append(float(item["stat"].get("display_neighbor_count") or 0.0))
            if item["seed"].get("full_train_fallback"):
                full_train_count += 1
                source_counter[f"full_train:{item['seed']['full_train_fallback']}"] += 1
            elif item["seed"].get("raw_hint_used"):
                raw_hint_count += 1
                source_counter["raw_hint"] += 1
            elif int(item["seed"].get("fuzzy_added") or 0) > 0:
                source_counter["token_plus_fuzzy"] += 1
            else:
                source_counter["direct_token_only"] += 1
        combo_summaries.append(
            {
                "combo": list(combo),
                "combo_label": _combo_label(combo),
                "combo_size": len(combo),
                "records": len(selected),
                "publication_modes": {str(k): int(v) for k, v in publication_counter.items()},
                "source_usage": {str(k): int(v) for k, v in source_counter.items()},
                "full_train_fallback_records": int(full_train_count),
                "raw_hint_records": int(raw_hint_count),
                "avg_same_combo_ratio": _round4(sum(same_combo_vals) / max(1, len(same_combo_vals))),
                "avg_same_core_ratio": _round4(sum(same_core_vals) / max(1, len(same_core_vals))),
                "avg_fuzzy_added": _round4(sum(fuzzy_vals) / max(1, len(fuzzy_vals))),
                "avg_effective_cluster_count": _round4(sum(effective_vals) / max(1, len(effective_vals))),
                "avg_display_neighbor_count": _round4(sum(display_vals) / max(1, len(display_vals))),
                "top_neighbor_combos": _top_counter(neighbor_combo_counter, limit=8),
                "top_reject_reasons": _top_counter(reject_counter, limit=8),
            }
        )

    broad_match_hotspots = sorted(
        [x for x in combo_summaries if x["records"] >= 3],
        key=lambda x: (float(x["avg_same_combo_ratio"] or 0.0), float(x["avg_same_core_ratio"] or 0.0), -x["records"]),
    )[:30]
    sparse_support_hotspots = sorted(
        [x for x in combo_summaries if x["records"] >= 2],
        key=lambda x: (float(x["avg_effective_cluster_count"] or 0.0), float(x["avg_display_neighbor_count"] or 0.0), -x["records"]),
    )[:30]

    report = {
        "generated_at": _now_str(),
        "priced_records_analyzed": len(analyses),
        "observed_unique_combos": len(combo_groups),
        "overall_publication_modes": {str(k): int(v) for k, v in overall_publication_modes.items()},
        "overall_source_usage": {str(k): int(v) for k, v in overall_source_usage.items()},
        "combo_summaries": combo_summaries,
        "broad_match_hotspots": broad_match_hotspots,
        "sparse_support_hotspots": sparse_support_hotspots,
        "record_summaries": analyses,
    }

    report_json = ROOT / args.report_json
    report_md = ROOT / args.report_md
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md.write_text(_render_markdown(report), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "generated_at": report["generated_at"],
        "priced_records_analyzed": report["priced_records_analyzed"],
        "observed_unique_combos": report["observed_unique_combos"],
        "report_json": str(report_json),
        "report_md": str(report_md),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
