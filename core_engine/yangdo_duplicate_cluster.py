from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        out = float(value)
    except (ValueError, TypeError):
        return None
    if out != out:
        return None
    return out


def _tokens(rec: Dict[str, Any]) -> set:
    raw = rec.get("license_tokens") or rec.get("tokens") or []
    if isinstance(raw, set):
        return set(x for x in raw if str(x).strip())
    if isinstance(raw, list):
        return set(str(x).strip() for x in raw if str(x).strip())
    return set()


def _jaccard(left: set, right: set) -> float:
    if not left or not right:
        return 0.0
    inter = len(left & right)
    union = len(left | right)
    return inter / float(max(1, union))


def _containment(left: set, right: set) -> float:
    if not left or not right:
        return 0.0
    inter = len(left & right)
    return inter / float(max(1, min(len(left), len(right))))


def _closeness(left: Any, right: Any) -> float:
    lv = _to_float(left)
    rv = _to_float(right)
    if lv is None or rv is None:
        return 0.0
    base = max(abs(lv), abs(rv), 0.1)
    score = 1.0 - (abs(lv - rv) / base)
    return max(0.0, min(1.0, score))


def _ratio(left: Any, right: Any) -> Optional[float]:
    lv = _to_float(left)
    rv = _to_float(right)
    if lv is None or rv is None or lv <= 0 or rv <= 0:
        return None
    a = max(lv, rv)
    b = min(lv, rv)
    return a / max(0.05, b)


def _range_pair(rec: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    low = _to_float(rec.get("display_low_eok"))
    high = _to_float(rec.get("display_high_eok"))
    if low is None and high is None:
        center = _to_float(rec.get("current_price_eok")) or _to_float(rec.get("price_eok"))
        return center, center
    if low is None:
        low = high
    if high is None:
        high = low
    if low is not None and high is not None and high < low:
        low, high = high, low
    return low, high


def _price_overlap_score(left: Dict[str, Any], right: Dict[str, Any]) -> float:
    l1, h1 = _range_pair(left)
    l2, h2 = _range_pair(right)
    if None in {l1, h1, l2, h2}:
        return 0.0
    overlap_low = max(float(l1), float(l2))
    overlap_high = min(float(h1), float(h2))
    if overlap_high >= overlap_low:
        overlap = overlap_high - overlap_low
        union = max(float(h1), float(h2)) - min(float(l1), float(l2))
        if union <= 0:
            return 1.0
        return max(0.0, min(1.0, overlap / union))
    c1 = (float(l1) + float(h1)) / 2.0
    c2 = (float(l2) + float(h2)) / 2.0
    return _closeness(c1, c2)


def _text_key(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _location_match(left: Dict[str, Any], right: Dict[str, Any]) -> float:
    a = _text_key(left.get("location"))
    b = _text_key(right.get("location"))
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    a1 = a.split(" ")[0]
    b1 = b.split(" ")[0]
    return 0.65 if a1 and a1 == b1 else 0.0


def _same_text(left: Any, right: Any) -> float:
    a = _text_key(left)
    b = _text_key(right)
    if not a or not b:
        return 0.0
    return 1.0 if a == b else 0.0


def _extreme_mismatch_count(left: Dict[str, Any], right: Dict[str, Any]) -> int:
    count = 0
    for key in ("specialty", "sales3_eok", "capital_eok"):
        ratio = _ratio(left.get(key), right.get(key))
        if ratio is not None and ratio > 4.0:
            count += 1
    return count


def _duplicate_affinity(left: Dict[str, Any], right: Dict[str, Any]) -> Tuple[float, int]:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    inter = left_tokens & right_tokens
    if not inter:
        return 0.0, 0
    if _extreme_mismatch_count(left, right) >= 2:
        return 0.0, 0

    token_jaccard = _jaccard(left_tokens, right_tokens)
    token_containment = _containment(left_tokens, right_tokens)
    specialty_close = _closeness(left.get("specialty"), right.get("specialty"))
    sales3_close = _closeness(left.get("sales3_eok"), right.get("sales3_eok"))
    capital_close = _closeness(left.get("capital_eok"), right.get("capital_eok"))
    year_close = _closeness(left.get("license_year"), right.get("license_year"))
    shares_close = _closeness(left.get("shares"), right.get("shares"))
    price_overlap = _price_overlap_score(left, right)
    company_match = _same_text(left.get("company_type"), right.get("company_type"))
    location_match = _location_match(left, right)
    association_match = _same_text(left.get("association"), right.get("association"))

    score = (
        token_jaccard * 0.24 +
        token_containment * 0.14 +
        specialty_close * 0.14 +
        sales3_close * 0.14 +
        capital_close * 0.10 +
        year_close * 0.06 +
        shares_close * 0.05 +
        price_overlap * 0.06 +
        company_match * 0.04 +
        location_match * 0.02 +
        association_match * 0.01
    )

    secondary_hits = 0
    for hit in (price_overlap >= 0.35, company_match >= 1.0, location_match >= 0.65, association_match >= 1.0, shares_close >= 0.85):
        if hit:
            secondary_hits += 1
    return float(score), int(secondary_hits)


def _is_same_cluster(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    score, secondary_hits = _duplicate_affinity(left, right)
    if score >= 0.82:
        return True
    if score >= 0.72 and secondary_hits >= 2:
        return True
    return False


def _completeness(rec: Dict[str, Any]) -> int:
    score = 0
    for key in ("specialty", "sales3_eok", "capital_eok", "license_year", "display_low_eok", "display_high_eok", "claim_price_eok"):
        if _to_float(rec.get(key)) is not None:
            score += 1
    for key in ("company_type", "location", "association"):
        if _text_key(rec.get(key)):
            score += 1
    return score


def _choose_representative(cluster_rows: List[Tuple[float, Dict[str, Any]]]) -> Tuple[float, Dict[str, Any]]:
    ranked = sorted(
        cluster_rows,
        key=lambda item: (
            -_completeness(item[1]),
            -float(item[0]),
            -int(item[1].get("row", 0) or 0),
        ),
    )
    return ranked[0]


def collapse_duplicate_neighbors(
    neighbors: List[Tuple[float, Dict[str, Any]]],
) -> Dict[str, Any]:
    rows = [(float(sim), dict(rec)) for sim, rec in list(neighbors or []) if isinstance(rec, dict)]
    raw_neighbor_count = len(rows)
    if raw_neighbor_count <= 1:
        return {
            "collapsed_neighbors": rows,
            "raw_neighbor_count": raw_neighbor_count,
            "effective_cluster_count": raw_neighbor_count,
            "cluster_count": raw_neighbor_count,
            "duplicate_cluster_adjusted": False,
            "clusters": [],
        }

    parent = list(range(raw_neighbor_count))

    def find(idx: int) -> int:
        while parent[idx] != idx:
            parent[idx] = parent[parent[idx]]
            idx = parent[idx]
        return idx

    def union(a: int, b: int) -> None:
        ra = find(a)
        rb = find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(raw_neighbor_count):
        for j in range(i + 1, raw_neighbor_count):
            if _is_same_cluster(rows[i][1], rows[j][1]):
                union(i, j)

    grouped: Dict[int, List[Tuple[float, Dict[str, Any]]]] = {}
    for idx, item in enumerate(rows):
        root = find(idx)
        grouped.setdefault(root, []).append(item)

    collapsed_neighbors: List[Tuple[float, Dict[str, Any]]] = []
    cluster_summaries: List[Dict[str, Any]] = []
    for cluster_rows in grouped.values():
        rep_sim, rep = _choose_representative(cluster_rows)
        rep_out = dict(rep)
        member_uids = [str(x[1].get("uid", "")).strip() for x in cluster_rows if str(x[1].get("uid", "")).strip()]
        rep_out["cluster_size"] = len(cluster_rows)
        rep_out["cluster_member_uids"] = member_uids[:12]
        collapsed_neighbors.append((float(rep_sim), rep_out))
        cluster_summaries.append(
            {
                "cluster_size": len(cluster_rows),
                "representative_uid": str(rep_out.get("uid", "")).strip(),
                "member_uids": member_uids[:12],
            }
        )

    collapsed_neighbors.sort(key=lambda item: float(item[0]), reverse=True)
    duplicate_cluster_adjusted = len(collapsed_neighbors) != raw_neighbor_count
    return {
        "collapsed_neighbors": collapsed_neighbors,
        "raw_neighbor_count": raw_neighbor_count,
        "effective_cluster_count": len(collapsed_neighbors),
        "cluster_count": len(grouped),
        "duplicate_cluster_adjusted": duplicate_cluster_adjusted,
        "clusters": cluster_summaries,
    }
