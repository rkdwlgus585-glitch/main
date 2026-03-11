from __future__ import annotations

from dataclasses import dataclass
from functools import cmp_to_key
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = ["RecommendationOps", "build_recommendation_bundle"]


@dataclass(frozen=True)
class RecommendationOps:
    canonical_tokens: Callable[[Any], set]
    single_token_target_core: Callable[[set], str]
    is_single_token_same_core: Callable[[set, set, Any], bool]
    company_type_key: Callable[[Any], str]
    feature_scale_mismatch: Callable[..., Tuple[int, int]]
    token_containment: Callable[[set, set], float]
    relative_closeness: Callable[[Any, Any], float]
    sales_fit_score: Callable[[Dict[str, Any], Dict[str, Any]], float]
    yearly_shape_similarity: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, float]]
    derive_display_range_eok: Callable[[Any, Any, Any, Any], Tuple[Any, Any]]
    listing_number_band: Callable[[Any], int]
    to_float: Callable[[Any], Optional[float]]
    compact: Callable[[Any, int], str]
    round4: Callable[[Any], Any]
    site_url: str


def _range_pair_from_record(
    rec: Dict[str, Any],
    *,
    to_float: Callable[[Any], Optional[float]],
    derive_display_range_eok: Callable[[Any, Any, Any, Any], Tuple[Any, Any]],
) -> Tuple[Optional[float], Optional[float]]:
    low = to_float(rec.get("display_low_eok"))
    high = to_float(rec.get("display_high_eok"))
    current_price = to_float(rec.get("current_price_eok"))
    claim_price = to_float(rec.get("claim_price_eok"))
    if low is None and high is None:
        derived_low, derived_high = derive_display_range_eok(
            rec.get("current_price_text"),
            rec.get("claim_price_text"),
            current_price,
            claim_price,
        )
        low = to_float(derived_low)
        high = to_float(derived_high)
    if low is None and high is None:
        center = current_price
        if center is None:
            center = to_float(rec.get("price_eok"))
        return center, center
    if low is None:
        low = high
    if high is None:
        high = low
    if low is not None and high is not None and high < low:
        low, high = high, low
    return low, high


def _price_overlap_score(
    left: Dict[str, Any],
    right: Dict[str, Any],
    *,
    ops: RecommendationOps,
) -> float:
    l1, h1 = _range_pair_from_record(left or {}, to_float=ops.to_float, derive_display_range_eok=ops.derive_display_range_eok)
    l2, h2 = _range_pair_from_record(right or {}, to_float=ops.to_float, derive_display_range_eok=ops.derive_display_range_eok)
    if None in {l1, h1, l2, h2}:
        return 0.0
    # None guard above guarantees all four values are non-None below
    overlap_low = max(l1, l2)
    overlap_high = min(h1, h2)
    if overlap_high >= overlap_low:
        overlap = overlap_high - overlap_low
        union = max(h1, h2) - min(l1, l2)
        if union <= 0:
            return 1.0
        return max(0.0, min(1.0, overlap / union))
    return ops.relative_closeness((l1 + h1) / 2.0, (l2 + h2) / 2.0)


def _yearly_fit_score(target: Dict[str, Any], rec: Dict[str, Any], *, ops: RecommendationOps) -> Tuple[float, float]:
    yearly = ops.yearly_shape_similarity(target, rec)
    strength = float(yearly.get("strength") or 0.0)
    if strength <= 0:
        return 0.0, 0.0
    yearly_fit = max(
        0.0,
        min(
            1.0,
            (float(yearly.get("shape") or 0.0) * 0.58)
            + (float(yearly.get("tail") or 0.0) * 0.24)
            + (float(yearly.get("trend") or 0.0) * 0.18),
        ),
    )
    return yearly_fit, strength


def _infer_balance_excluded(target: Dict[str, Any], *, target_tokens: set) -> bool:
    if bool(target.get("balance_excluded")):
        return True
    for token in target_tokens or set():
        if token in {"전기", "정보통신", "소방"}:
            return True
    license_text = str(target.get("license_text") or target.get("raw_license_key") or "").strip()
    if not license_text:
        return False
    return any(keyword in license_text for keyword in ("전기", "정보통신", "통신", "소방"))


def _matched_axes(
    *,
    token_match: float,
    same_core: float,
    sales_fit: float,
    price_fit: float,
    specialty_fit: float,
    capital_fit: float,
    balance_fit: float,
    yearly_fit: float,
    company_match: float,
    balance_excluded: bool,
) -> Tuple[List[str], List[str]]:
    matched: List[str] = []
    weak: List[str] = []
    if token_match >= 0.999:
        matched.append("면허 일치")
    elif same_core >= 0.999:
        matched.append("핵심 업종 일치")
    else:
        weak.append("면허 축 약함")
    if sales_fit >= 0.72:
        matched.append("실적 규모")
    elif yearly_fit >= 0.70:
        matched.append("3개년 실적 흐름")
    else:
        weak.append("실적 축 약함")
    if price_fit >= 0.62:
        matched.append("가격대")
    elif price_fit <= 0.15:
        weak.append("가격대 차이")
    if specialty_fit >= 0.78:
        matched.append("시평 규모")
    elif 0.0 < specialty_fit <= 0.35:
        weak.append("시평 차이")
    if capital_fit >= 0.78:
        matched.append("자본금")
    elif 0.0 < capital_fit <= 0.35:
        weak.append("자본금 차이")
    if not balance_excluded:
        if balance_fit >= 0.72:
            matched.append("공제잔액")
        elif 0.0 < balance_fit <= 0.35:
            weak.append("공제잔액 차이")
    if company_match >= 0.999:
        matched.append("회사 형태")
    return matched[:4], weak[:4]


def _build_recommendation_reasons(
    *,
    token_match: float,
    same_core: float,
    sales_fit: float,
    price_fit: float,
    specialty_fit: float,
    capital_fit: float,
    balance_fit: float,
    yearly_fit: float,
    company_match: float,
    balance_excluded: bool,
) -> List[str]:
    matched, weak = _matched_axes(
        token_match=token_match,
        same_core=same_core,
        sales_fit=sales_fit,
        price_fit=price_fit,
        specialty_fit=specialty_fit,
        capital_fit=capital_fit,
        balance_fit=balance_fit,
        yearly_fit=yearly_fit,
        company_match=company_match,
        balance_excluded=balance_excluded,
    )
    reasons: List[str] = []
    if "면허 일치" in matched:
        reasons.append("면허 구성이 같습니다")
    elif "핵심 업종 일치" in matched:
        reasons.append("같은 핵심 업종입니다")
    if "실적 규모" in matched:
        reasons.append("최근 실적 규모가 비슷합니다")
    elif "3개년 실적 흐름" in matched:
        reasons.append("최근 3년 실적 흐름이 비슷합니다")
    if "가격대" in matched:
        reasons.append("예상 가격대와 매물 가격대가 가깝습니다")
    if "시평 규모" in matched:
        reasons.append("시평 규모가 비슷합니다")
    if "자본금" in matched:
        reasons.append("자본금 규모가 비슷합니다")
    if (not balance_excluded) and "공제잔액" in matched:
        reasons.append("공제조합 잔액 규모가 비슷합니다")
    if "회사 형태" in matched:
        reasons.append("회사 형태가 같습니다")
    if not reasons:
        if weak:
            reasons.append("면허는 유사하지만 일부 규모 축 차이가 있어 보조 검토용으로 추천합니다")
        else:
            reasons.append("입력한 면허와 가격대가 가까운 매물입니다")
    out: List[str] = []
    for reason in reasons:
        if reason and reason not in out:
            out.append(reason)
        if len(out) >= 3:
            break
    return out


def _fit_summary(
    matched_axes: List[str],
    mismatch_flags: List[str],
    *,
    score: float,
) -> str:
    if matched_axes and not mismatch_flags:
        return f"{', '.join(matched_axes[:3])} 축이 함께 맞아 우선 검토 후보입니다."
    if matched_axes and mismatch_flags:
        return f"{', '.join(matched_axes[:2])} 축은 맞지만 {', '.join(mismatch_flags[:2])} 차이를 함께 봐야 합니다."
    if score >= 0.70:
        return "면허와 핵심 규모는 유사하지만 보조 축 확인이 필요합니다."
    return "보조 검토용 유사 매물입니다."


def _score_candidate(
    *,
    similarity: float,
    token_match: float,
    same_core: float,
    sales_fit: float,
    price_fit: float,
    specialty_fit: float,
    capital_fit: float,
    balance_fit: float,
    yearly_fit: float,
    yearly_strength: float,
    company_match: float,
    signal_count: int,
    mismatch_count: int,
    matched_axes: List[str],
) -> float:
    score = 0.0
    score += (similarity / 100.0) * 0.27
    score += max(sales_fit, token_match, same_core) * 0.24
    score += price_fit * 0.17
    score += specialty_fit * 0.09
    score += capital_fit * 0.07
    score += balance_fit * 0.04
    score += yearly_fit * 0.08
    score += company_match * 0.02
    score += min(0.06, 0.015 * len(matched_axes))
    if token_match >= 0.999:
        score += 0.03
    elif same_core >= 0.999:
        score += 0.02
    if yearly_strength >= 0.65 and yearly_fit < 0.42:
        score -= 0.08
    if signal_count >= 2 and mismatch_count >= signal_count:
        score -= 0.18
    elif signal_count >= 3 and mismatch_count >= 2:
        score -= 0.10
    elif signal_count >= 2 and mismatch_count >= 1:
        score -= 0.05
    if price_fit < 0.16 and sales_fit < 0.48 and similarity < 88.0:
        score -= 0.10
    return max(0.0, min(1.0, score))


def _recommendation_label(
    score: float,
    *,
    token_match: float = 0.0,
    same_core: float = 0.0,
    matched_axes: Optional[List[str]] = None,
    mismatch_flags: Optional[List[str]] = None,
) -> Tuple[int, str, str]:
    matched_count = len(list(matched_axes or []))
    mismatch_count = len(list(mismatch_flags or []))
    if score >= 0.80:
        return 2, "우선 검토", "high"
    if score >= 0.78 and token_match >= 0.999 and matched_count >= 3 and mismatch_count <= 1:
        return 2, "우선 검토", "high"
    if score >= 0.76 and same_core >= 0.999 and matched_count >= 4 and mismatch_count == 0:
        return 2, "우선 검토", "high"
    if score >= 0.64:
        return 1, "조건 유사", "medium"
    return 0, "보조 검토", "assist"


def _build_recommendation_meta(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    if not total:
        return {
            "recommendation_version": "listing_recommender_v2",
            "recommended_count": 0,
            "precision_mode": "none",
            "strict_match_count": 0,
            "assist_count": 0,
            "diversity_mode": "top1_locked_spread_v1",
            "unique_price_band_count": 0,
            "unique_focus_signature_count": 0,
            "unique_precision_tier_count": 0,
        }
    strict = sum(1 for row in rows if str(row.get("precision_tier") or "") == "high")
    assist = sum(1 for row in rows if str(row.get("precision_tier") or "") == "assist")
    avg_score = sum(float(row.get("recommendation_score") or 0.0) for row in rows) / float(max(1, total))
    price_bands = {
        str(row.get("recommendation_price_band") or "").strip()
        for row in rows
        if str(row.get("recommendation_price_band") or "").strip()
    }
    focus_signatures = {
        str(row.get("recommendation_focus_signature") or "").strip()
        for row in rows
        if str(row.get("recommendation_focus_signature") or "").strip()
    }
    precision_tiers = {
        str(row.get("precision_tier") or "").strip()
        for row in rows
        if str(row.get("precision_tier") or "").strip()
    }
    if strict >= 2 or avg_score >= 80.0:
        mode = "strict"
    elif strict >= 1 or avg_score >= 68.0:
        mode = "balanced"
    else:
        mode = "assist"
    return {
        "recommendation_version": "listing_recommender_v2",
        "recommended_count": total,
        "precision_mode": mode,
        "strict_match_count": strict,
        "assist_count": assist,
        "average_recommendation_score": round(avg_score, 4),
        "diversity_mode": "top1_locked_spread_v1",
        "unique_price_band_count": len(price_bands),
        "unique_focus_signature_count": len(focus_signatures),
        "unique_precision_tier_count": len(precision_tiers),
    }


def _recommendation_price_band(row: Dict[str, Any], *, ops: RecommendationOps) -> str:
    low = ops.to_float(row.get("display_low_eok"))
    high = ops.to_float(row.get("display_high_eok"))
    price = ops.to_float(row.get("price_eok"))
    center = price
    if center is None and low is not None and high is not None:
        center = (low + high) / 2.0
    elif center is None:
        center = low if low is not None else high
    if center is None:
        return "unknown"
    if center < 1.0:
        return "under_1"
    if center < 2.0:
        return "1_to_2"
    if center < 3.0:
        return "2_to_3"
    if center < 4.0:
        return "3_to_4"
    if center < 6.0:
        return "4_to_6"
    return "6_plus"


def _recommendation_focus_signature(row: Dict[str, Any]) -> str:
    parts: List[str] = []
    matched_axes = [str(axis).strip() for axis in (row.get("matched_axes") or []) if str(axis).strip()]
    mismatch_flags = [str(flag).strip() for flag in (row.get("mismatch_flags") or []) if str(flag).strip()]
    price_band = str(row.get("recommendation_price_band") or "").strip()
    if matched_axes:
        parts.extend(matched_axes[:2])
    focus = str(row.get("recommendation_focus") or "").strip()
    if not parts and focus:
        parts.append(focus)
    if mismatch_flags:
        parts.append(f"주의:{mismatch_flags[0]}")
    elif price_band:
        parts.append(f"가격:{price_band}")
    return "|".join(part for part in parts if part)


def _rerank_with_diversity(
    ranked: List[Tuple[int, int, float, float, float, Dict[str, Any]]],
    *,
    limit: int,
) -> List[Tuple[int, int, float, float, float, Dict[str, Any]]]:
    wanted = max(1, int(limit or 0))
    if len(ranked) <= 2 or wanted <= 2:
        return ranked[:wanted]

    selected: List[Tuple[int, int, float, float, float, Dict[str, Any]]] = [ranked[0]]
    remaining = list(ranked[1:])
    used_counts: Dict[str, Dict[str, int]] = {
        "price_band": {},
        "focus_signature": {},
        "precision_tier": {},
        "listing_band": {},
        "label": {},
    }

    def _remember(entry: Tuple[int, int, float, float, float, Dict[str, Any]]) -> None:
        row = entry[5]
        keys = {
            "price_band": str(row.get("recommendation_price_band") or "").strip(),
            "focus_signature": str(row.get("recommendation_focus_signature") or "").strip(),
            "precision_tier": str(row.get("precision_tier") or "").strip(),
            "listing_band": str(entry[1]),
            "label": str(row.get("recommendation_label") or "").strip(),
        }
        for group, value in keys.items():
            if not value:
                continue
            counts = used_counts[group]
            counts[value] = int(counts.get(value, 0) or 0) + 1

    _remember(ranked[0])

    while remaining and len(selected) < wanted:
        anchor_score = float(remaining[0][2] or 0.0)
        quality_floor = anchor_score - 0.12
        candidate_pool = [entry for entry in remaining if float(entry[2] or 0.0) >= quality_floor]
        if not candidate_pool:
            candidate_pool = [remaining[0]]

        best_entry = candidate_pool[0]
        best_adjusted = float("-inf")
        for entry in candidate_pool:
            row = entry[5]
            penalty = 0.0
            price_band = str(row.get("recommendation_price_band") or "").strip()
            focus_signature = str(row.get("recommendation_focus_signature") or "").strip()
            precision_tier = str(row.get("precision_tier") or "").strip()
            label = str(row.get("recommendation_label") or "").strip()
            listing_band = str(entry[1])
            if used_counts["focus_signature"].get(focus_signature, 0):
                penalty += 0.030 + (0.008 * used_counts["focus_signature"][focus_signature])
            if used_counts["price_band"].get(price_band, 0):
                penalty += 0.024 + (0.006 * used_counts["price_band"][price_band])
            if used_counts["precision_tier"].get(precision_tier, 0):
                penalty += 0.015
            if used_counts["listing_band"].get(listing_band, 0):
                penalty += 0.010
            if used_counts["label"].get(label, 0):
                penalty += 0.008
            adjusted = float(entry[2] or 0.0) - penalty
            if adjusted > best_adjusted:
                best_adjusted = adjusted
                best_entry = entry

        selected.append(best_entry)
        _remember(best_entry)
        remaining.remove(best_entry)

    return selected


def _compare_recommendation_entries(
    left: Tuple[int, int, float, float, float, Dict[str, Any]],
    right: Tuple[int, int, float, float, float, Dict[str, Any]],
) -> int:
    if left[0] != right[0]:
        return -1 if left[0] > right[0] else 1
    score_gap = abs(float(left[2] or 0.0) - float(right[2] or 0.0))
    if score_gap > 0.015 and left[2] != right[2]:
        return -1 if left[2] > right[2] else 1
    if left[1] != right[1]:
        return -1 if left[1] > right[1] else 1
    if left[3] != right[3]:
        return -1 if left[3] > right[3] else 1
    if left[2] != right[2]:
        return -1 if left[2] > right[2] else 1
    if left[4] != right[4]:
        return -1 if left[4] > right[4] else 1
    return 0


def build_recommendation_bundle(
    *,
    target: Dict[str, Any],
    rows: List[Tuple[float, Dict[str, Any]]],
    center: Any,
    low: Any,
    high: Any,
    ops: RecommendationOps,
    limit: int = 4,
) -> Dict[str, Any]:
    src = [(float(ops.to_float(sim) or 0.0), rec) for sim, rec in list(rows or []) if isinstance(rec, dict)]
    if not src:
        return {
            "recommended_listings": [],
            "recommendation_meta": _build_recommendation_meta([]),
        }

    estimate_ref = {
        "display_low_eok": ops.to_float(low),
        "display_high_eok": ops.to_float(high),
        "price_eok": ops.to_float(center),
    }
    target_tokens = ops.canonical_tokens(target.get("license_tokens") or set())
    target_company = ops.company_type_key(target.get("company_type"))
    balance_excluded = _infer_balance_excluded(target, target_tokens=target_tokens)
    target_has_sales = any((ops.to_float(target.get(field)) or 0.0) > 0.0 for field in ("sales3_eok", "sales5_eok"))
    ranked: List[Tuple[int, int, float, float, float, Dict[str, Any]]] = []
    seen = set()

    for sim, rec in src:
        marker = (
            int(ops.to_float(rec.get("number")) or 0),
            str(rec.get("uid", "")).strip(),
            int(ops.to_float(rec.get("row")) or 0),
        )
        if marker in seen:
            continue
        seen.add(marker)

        cand_tokens = ops.canonical_tokens(rec.get("license_tokens") or set())
        token_match = ops.token_containment(target_tokens, cand_tokens) if target_tokens and cand_tokens else 0.0
        same_core = 1.0 if (
            ops.single_token_target_core(target_tokens)
            and ops.is_single_token_same_core(target_tokens, cand_tokens, rec.get("license_text"))
        ) else 0.0
        rec_has_sales = any((ops.to_float(rec.get(field)) or 0.0) > 0.0 for field in ("sales3_eok", "sales5_eok"))
        sales_fit = ops.sales_fit_score(target, rec)
        specialty_fit = ops.relative_closeness(target.get("specialty"), rec.get("specialty"))
        capital_fit = ops.relative_closeness(target.get("capital_eok"), rec.get("capital_eok"))
        balance_fit = 0.0 if balance_excluded else ops.relative_closeness(target.get("balance_eok"), rec.get("balance_eok"))
        yearly_fit, yearly_strength = _yearly_fit_score(target, rec, ops=ops)
        price_fit = _price_overlap_score(estimate_ref, rec, ops=ops)
        est_low, est_high = _range_pair_from_record(estimate_ref, to_float=ops.to_float, derive_display_range_eok=ops.derive_display_range_eok)
        rec_low, rec_high = _range_pair_from_record(rec, to_float=ops.to_float, derive_display_range_eok=ops.derive_display_range_eok)
        if (
            est_low is not None
            and est_high is not None
            and rec_low is not None
            and rec_high is not None
            and min(est_high, rec_high) < max(est_low, rec_low)
        ):
            price_fit *= 0.35
        company_match = 1.0 if target_company and target_company == ops.company_type_key(rec.get("company_type")) else 0.0
        signal_count, mismatch_count = ops.feature_scale_mismatch(target, rec, balance_excluded=balance_excluded)
        matched_axes, mismatch_flags = _matched_axes(
            token_match=token_match,
            same_core=same_core,
            sales_fit=sales_fit,
            price_fit=price_fit,
            specialty_fit=specialty_fit,
            capital_fit=capital_fit,
            balance_fit=balance_fit,
            yearly_fit=yearly_fit,
            company_match=company_match,
            balance_excluded=balance_excluded,
        )
        score = _score_candidate(
            similarity=sim,
            token_match=token_match,
            same_core=same_core,
            sales_fit=sales_fit,
            price_fit=price_fit,
            specialty_fit=specialty_fit,
            capital_fit=capital_fit,
            balance_fit=balance_fit,
            yearly_fit=yearly_fit,
            yearly_strength=yearly_strength,
            company_match=company_match,
            signal_count=signal_count,
            mismatch_count=mismatch_count,
            matched_axes=matched_axes,
        )
        if target_has_sales and rec_has_sales:
            if sales_fit < 0.50:
                score -= 0.18
            elif sales_fit < 0.62:
                score -= 0.12
        score = max(0.0, min(1.0, score))
        bucket, label, precision_tier = _recommendation_label(
            score,
            token_match=token_match,
            same_core=same_core,
            matched_axes=matched_axes,
            mismatch_flags=mismatch_flags,
        )
        low_confidence_rescue = (token_match >= 0.999 or same_core >= 0.999) and sim >= 84.0
        if bucket <= 0 and score < 0.54:
            if not low_confidence_rescue:
                continue
            bucket, label, precision_tier = 0, "보조 검토", "assist"
            if not mismatch_flags:
                mismatch_flags = ["규모 차이"]

        display_low, display_high = _range_pair_from_record(rec, to_float=ops.to_float, derive_display_range_eok=ops.derive_display_range_eok)
        price_eok = ops.to_float(rec.get("current_price_eok"))
        if price_eok is None:
            price_eok = ops.to_float(rec.get("price_eok"))
        seoul_no = int(ops.to_float(rec.get("number")) or 0)
        reasons = _build_recommendation_reasons(
            token_match=token_match,
            same_core=same_core,
            sales_fit=sales_fit,
            price_fit=price_fit,
            specialty_fit=specialty_fit,
            capital_fit=capital_fit,
            balance_fit=balance_fit,
            yearly_fit=yearly_fit,
            company_match=company_match,
            balance_excluded=balance_excluded,
        )
        focus = ", ".join(matched_axes[:3]) if matched_axes else "가격대·면허 인접"
        fit_summary = _fit_summary(matched_axes, mismatch_flags, score=score)
        ranked.append(
            (
                bucket,
                ops.listing_number_band(rec.get("number")),
                score,
                sim,
                float(seoul_no),
                {
                    "seoul_no": seoul_no,
                    "now_uid": str(rec.get("uid", "")).strip(),
                    "license_text": ops.compact(rec.get("license_text")),
                    "price_eok": ops.round4(price_eok),
                    "display_low_eok": ops.round4(display_low),
                    "display_high_eok": ops.round4(display_high),
                    "sales3_eok": ops.round4(ops.to_float(rec.get("sales3_eok"))),
                    "recommendation_score": ops.round4(score * 100.0),
                    "recommendation_label": label,
                    "recommendation_focus": focus,
                    "precision_tier": precision_tier,
                    "similarity": ops.round4(sim),
                    "reasons": reasons,
                    "fit_summary": fit_summary,
                    "matched_axes": matched_axes,
                    "mismatch_flags": mismatch_flags,
                    "recommendation_focus_signature": "",
                    "recommendation_price_band": "",
                    "url": f"{str(ops.site_url).rstrip('/')}/mna/{seoul_no}" if seoul_no > 0 else f"{str(ops.site_url).rstrip('/')}/mna",
                },
            )
        )

    ranked.sort(key=cmp_to_key(_compare_recommendation_entries))
    for _, _, _, _, _, row in ranked:
        row["recommendation_price_band"] = _recommendation_price_band(row, ops=ops)
        row["recommendation_focus_signature"] = _recommendation_focus_signature(row)
    reranked = _rerank_with_diversity(ranked, limit=limit)
    recommended_rows = [entry[5] for entry in reranked]
    return {
        "recommended_listings": recommended_rows,
        "recommendation_meta": _build_recommendation_meta(recommended_rows),
    }
