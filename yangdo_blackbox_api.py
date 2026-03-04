import argparse
import json
import math
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

import all as core
from yangdo_calculator import _derive_display_range_eok


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        txt = str(value).replace(',', '').strip()
        if not txt:
            return None
        num = float(txt)
        if num != num:
            return None
        return num
    except Exception:
        return None


def _compact(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_license_key(raw: Any) -> str:
    txt = _compact(raw).replace(" ", "")
    if not txt:
        return ""
    txt = txt.replace("(주)", "").replace("주식회사", "")
    for suffix in ("업종", "면허", "공사업", "건설업", "공사", "사업"):
        if txt.endswith(suffix):
            txt = txt[: -len(suffix)]
    return txt


def _char_bigrams(raw: Any) -> set:
    src = _normalize_license_key(raw)
    if not src:
        return set()
    if len(src) < 2:
        return {src}
    return {src[i : i + 2] for i in range(len(src) - 1)}


def _bigram_jaccard(left: Any, right: Any) -> float:
    a = _char_bigrams(left)
    b = _char_bigrams(right)
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    if union <= 0:
        return 0.0
    return inter / union


def _token_containment(left: set, right: set) -> float:
    if not left or not right:
        return 0.0
    inter = len(left & right)
    return inter / float(max(1, min(len(left), len(right))))


def _relative_closeness(left: Any, right: Any) -> float:
    lv = _to_float(left)
    rv = _to_float(right)
    if lv is None and rv is None:
        return 0.0
    if lv is None or rv is None:
        return 0.08
    denom = max(abs(float(lv)), abs(float(rv)), 1.0)
    rel = abs(float(lv) - float(rv)) / denom
    return max(0.0, 1.0 - min(rel, 1.0))


def _safe_ratio(num_value: Any, den_value: Any) -> Optional[float]:
    num = _to_float(num_value)
    den = _to_float(den_value)
    if num is None or den is None or den <= 0:
        return None
    val = num / den
    if val <= 0:
        return None
    return float(val)


def _year_value(source: Dict[str, Any], key: str) -> Optional[float]:
    direct = _to_float(source.get(key))
    if direct is not None:
        return direct
    years = source.get("years")
    if isinstance(years, dict):
        return _to_float(years.get(key))
    return None


def _yearly_shape_similarity(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, float]:
    ly = [_year_value(left, "y23"), _year_value(left, "y24"), _year_value(left, "y25")]
    ry = [_year_value(right, "y23"), _year_value(right, "y24"), _year_value(right, "y25")]
    common_idx = [i for i in range(3) if ly[i] is not None and ry[i] is not None]
    if len(common_idx) < 2:
        return {"shape": 0.55, "trend": 0.55, "tail": 0.55, "strength": 0.0}

    l_vals = [max(0.0, float(ly[i])) for i in common_idx]
    r_vals = [max(0.0, float(ry[i])) for i in common_idx]
    l_sum = sum(l_vals)
    r_sum = sum(r_vals)
    if l_sum <= 0 or r_sum <= 0:
        return {"shape": 0.55, "trend": 0.55, "tail": 0.55, "strength": 0.0}

    l_share = [v / l_sum for v in l_vals]
    r_share = [v / r_sum for v in r_vals]
    l1 = sum(abs(a - b) for a, b in zip(l_share, r_share))
    shape = max(0.0, 1.0 - min(1.0, l1 / 2.0))

    tail = max(0.0, 1.0 - min(1.0, abs(l_share[-1] - r_share[-1]) * 2.0))

    def growth(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        denom = max(abs(float(a)), 0.3)
        return (float(b) - float(a)) / denom

    trend_scores: List[float] = []
    for a_idx, b_idx in ((0, 1), (1, 2)):
        if a_idx not in common_idx or b_idx not in common_idx:
            continue
        lg = growth(ly[a_idx], ly[b_idx])
        rg = growth(ry[a_idx], ry[b_idx])
        if lg is None or rg is None:
            continue
        rel = abs(lg - rg) / max(1.0, abs(lg), abs(rg))
        trend_scores.append(max(0.0, 1.0 - min(1.0, rel)))
    trend = sum(trend_scores) / float(len(trend_scores)) if trend_scores else 0.55

    pair_strength = float(len(trend_scores)) / 2.0
    value_strength = float(len(common_idx)) / 3.0
    strength = max(0.0, min(1.0, (value_strength * 0.55) + (pair_strength * 0.45)))
    return {"shape": shape, "trend": trend, "tail": tail, "strength": strength}


class YangdoBlackboxEstimator:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: List[Dict[str, Any]] = []
        self._train_records: List[Dict[str, Any]] = []
        self._token_index: Dict[str, List[Dict[str, Any]]] = {}
        self._meta: Dict[str, Any] = {}
        self._loaded_at = ""

    _ALIAS_MAP = {
        "상하": "상하수도설비",
        "상하수도": "상하수도설비",
        "의장": "실내건축",
        "실내": "실내건축",
        "통신": "정보통신",
        "기계": "기계설비",
        "토목건축": "토건",
        "토목건축공사업": "토건",
        "철콘": "철근콘크리트",
        "미장방수": "미장방수조적",
        "단종토목": "토목",
        "토건": "토목건축",
        "금속": "금속구조물창호온실",
        "비계": "비계구조물해체",
        "석면": "석면해체제거",
        "습식": "습식방수석공",
    }
    _CORE_LICENSE_TOKENS = {
        "전기", "정보통신", "소방", "기계설비", "가스",
        "토건", "토목", "건축", "조경", "실내",
        "토공", "포장", "철콘", "상하", "석공", "비계", "석면", "습식", "도장",
        "조경식재", "조경시설", "산림토목", "도시정비", "보링", "수중", "금속",
    }
    _CORE_LICENSE_TOKENS_SORTED = sorted(_CORE_LICENSE_TOKENS, key=len, reverse=True)
    _CORE_TEXT_ALIAS_MAP = {
        "실내건축": "실내",
        "철근콘크리트": "철콘",
        "상하수도설비": "상하",
        "토목건축": "토건",
        "금속구조물창호온실": "금속",
        "비계구조물해체": "비계",
        "석면해체제거": "석면",
        "습식방수석공": "습식",
        "소방시설": "소방",
        "정보통신공사업": "정보통신",
        "통신공사업": "정보통신",
        "기계설비공사업": "기계설비",
        "기계가스설비공사업": "기계설비",
        "기계가스": "기계설비",
        "전기공사업": "전기",
        "소방공사업": "소방",
    }

    @classmethod
    def _canonical_tokens(cls, tokens: Any) -> set:
        out = set()
        for raw in set(tokens or set()):
            norm = _normalize_license_key(raw)
            if not norm:
                continue
            mapped = cls._ALIAS_MAP.get(norm, norm)
            out.add(norm)
            out.add(_normalize_license_key(mapped))
        return {x for x in out if x}

    @staticmethod
    def _company_type_key(raw: Any) -> str:
        txt = _normalize_license_key(raw)
        if not txt:
            return ""
        if "주식" in txt:
            return "주식회사"
        if "유한" in txt:
            return "유한회사"
        if "개인" in txt:
            return "개인"
        return txt

    @staticmethod
    def _is_separate_balance_group_token(raw: Any) -> bool:
        txt = _normalize_license_key(raw)
        if not txt:
            return False
        return ("전기" in txt) or ("정보통신" in txt) or ("통신" in txt) or ("소방" in txt)

    def _is_balance_separate_paid_group(self, target: Dict[str, Any]) -> bool:
        tokens = self._canonical_tokens(target.get("license_tokens") or set())
        if tokens:
            for tok in tokens:
                if self._is_separate_balance_group_token(tok):
                    return True
        return self._is_separate_balance_group_token(
            target.get("license_text") or target.get("raw_license_key") or ""
        )

    @classmethod
    def _core_tokens_from_text(cls, raw: Any) -> set:
        key = _normalize_license_key(raw)
        if not key:
            return set()
        alias = cls._CORE_TEXT_ALIAS_MAP.get(key)
        if alias:
            return {alias}
        hits = set()
        for token in cls._CORE_LICENSE_TOKENS_SORTED:
            if token and token in key:
                hits.add(token)
        return hits

    @classmethod
    def _core_tokens(cls, tokens: set) -> set:
        out = set()
        for raw in set(tokens or set()):
            token = str(raw or "").strip()
            if not token:
                continue
            if token in cls._CORE_LICENSE_TOKENS:
                out.add(token)
            out.update(cls._core_tokens_from_text(token))
        return out

    @classmethod
    def _is_single_token_cross_combo(cls, target_tokens: set, candidate_tokens: set, candidate_license_text: Any = "") -> bool:
        tset = set(target_tokens or set())
        cset = set(candidate_tokens or set())
        target = cls._single_token_target_core(tset)
        if not target:
            return False
        cand_core = cls._core_tokens(cset) | cls._core_tokens_from_text(candidate_license_text)
        if target not in cset and target not in cand_core:
            return False
        if len(cand_core) <= 1:
            return False
        return any(tok != target for tok in cand_core)

    @classmethod
    def _single_token_target_core(cls, target_tokens: set) -> str:
        tset = set(target_tokens or set())
        core = cls._core_tokens(tset)
        if len(core) == 1:
            return next(iter(sorted(core)))
        if len(tset) == 1:
            return next(iter(tset))
        return ""

    @classmethod
    def _is_single_token_same_core(cls, target_tokens: set, candidate_tokens: set, candidate_license_text: Any = "") -> bool:
        target = cls._single_token_target_core(target_tokens)
        if not target:
            return False
        cset = set(candidate_tokens or set())
        cand_core = cls._core_tokens(cset) | cls._core_tokens_from_text(candidate_license_text)
        if len(cand_core) >= 2:
            return False
        if len(cand_core) == 1:
            return target in cand_core
        if len(cset) == 1:
            tok = next(iter(cset))
            return (target in tok) or (tok in target)
        return False

    @staticmethod
    def _is_single_token_profile_outlier(target: Dict[str, Any], candidate: Dict[str, Any]) -> bool:
        tokens = set(target.get("license_tokens") or set())
        if not YangdoBlackboxEstimator._single_token_target_core(tokens):
            return False
        spec_ratio = _safe_ratio(target.get("specialty"), candidate.get("specialty"))
        sales_ratio = _safe_ratio(target.get("sales3_eok"), candidate.get("sales3_eok"))
        if spec_ratio is not None and (spec_ratio < 0.30 or spec_ratio > 3.30):
            return True
        if sales_ratio is not None and (sales_ratio < 0.30 or sales_ratio > 3.30):
            return True
        yearly = _yearly_shape_similarity(target, candidate)
        if yearly["strength"] >= 0.65 and yearly["shape"] < 0.22:
            return True
        if yearly["strength"] >= 0.65 and yearly["trend"] < 0.18 and yearly["tail"] < 0.25:
            return True
        return False

    def _has_fuzzy_token_overlap(self, left_tokens: set, right_tokens: set) -> bool:
        if not left_tokens or not right_tokens:
            return False
        if left_tokens & right_tokens:
            return True
        for lt in left_tokens:
            for rt in right_tokens:
                score = _bigram_jaccard(lt, rt)
                if score >= 0.62:
                    return True
        return False

    def _neighbor_score(self, target: Dict[str, Any], candidate: Dict[str, Any]) -> float:
        balance_excluded = self._is_balance_separate_paid_group(target)
        tokens_t = self._canonical_tokens(target.get("license_tokens") or set())
        tokens_c = self._canonical_tokens(candidate.get("license_tokens") or set())
        target_core_tokens = self._core_tokens(tokens_t)
        single_core_target = len(target_core_tokens) == 1
        multi_core_target = len(target_core_tokens) >= 2
        inter = tokens_t & tokens_c
        token_jaccard = core._jaccard_similarity(tokens_t, tokens_c)
        token_contain = _token_containment(tokens_t, tokens_c)
        token_precision = (len(inter) / float(max(1, len(tokens_c)))) if tokens_c else 0.0
        raw_key = _normalize_license_key(target.get("raw_license_key") or target.get("license_text"))
        raw_license_similarity = _bigram_jaccard(raw_key, candidate.get("license_text")) if (not tokens_t and raw_key) else 0.0
        s_specialty = _relative_closeness(target.get("specialty"), candidate.get("specialty"))
        s_sales3 = _relative_closeness(target.get("sales3_eok"), candidate.get("sales3_eok"))
        s_sales5 = _relative_closeness(target.get("sales5_eok"), candidate.get("sales5_eok"))
        s_license_year = _relative_closeness(target.get("license_year"), candidate.get("license_year"))
        s_debt = _relative_closeness(target.get("debt_ratio"), candidate.get("debt_ratio"))
        s_liq = _relative_closeness(target.get("liq_ratio"), candidate.get("liq_ratio"))
        s_capital = _relative_closeness(target.get("capital_eok"), candidate.get("capital_eok"))
        s_balance = _relative_closeness(target.get("balance_eok"), candidate.get("balance_eok"))
        s_surplus = _relative_closeness(target.get("surplus_eok"), candidate.get("surplus_eok"))
        yearly = _yearly_shape_similarity(target, candidate)
        s_year_shape = float(yearly["shape"])
        s_year_trend = float(yearly["trend"])
        s_year_tail = float(yearly["tail"])
        s_year_strength = float(yearly["strength"])

        score = 0.0
        score += token_jaccard * 42.0
        score += token_contain * 24.0
        score += token_precision * 18.0
        score += min(14.0, 3.5 * len(inter))
        score += raw_license_similarity * 26.0
        score += s_specialty * 8.0
        score += s_sales3 * 7.0
        score += s_sales5 * 5.0
        score += s_license_year * 2.0
        score += s_debt * 2.5
        score += s_liq * 2.5
        score += s_capital * 10.0
        if not balance_excluded:
            score += s_balance * 12.0
        score += s_surplus * 10.0
        if s_year_strength > 0:
            score += s_year_shape * (6.0 + 8.0 * s_year_strength)
            score += s_year_trend * (3.0 + 4.0 * s_year_strength)
            score += s_year_tail * (2.0 + 3.0 * s_year_strength)

        if s_specialty >= 0.90 and s_sales3 >= 0.90:
            score += 4.5
        if tokens_t and len(inter) == len(tokens_t):
            score += 8.0

        target_comp = self._company_type_key(target.get("company_type"))
        cand_comp = self._company_type_key(candidate.get("company_type"))
        if target_comp and cand_comp:
            score += 3.5 if target_comp == cand_comp else -1.2

        specialty_ratio = _safe_ratio(target.get("specialty"), candidate.get("specialty"))
        if specialty_ratio is not None:
            if specialty_ratio < 0.08 or specialty_ratio > 12.0:
                score *= 0.78
            elif specialty_ratio < 0.20 or specialty_ratio > 5.0:
                score *= 0.90
        sales_ratio = _safe_ratio(target.get("sales3_eok"), candidate.get("sales3_eok"))
        if sales_ratio is not None:
            if sales_ratio < 0.08 or sales_ratio > 12.0:
                score *= 0.78
            elif sales_ratio < 0.20 or sales_ratio > 5.0:
                score *= 0.90
        if s_year_strength >= 0.60:
            if s_year_shape < 0.28:
                score *= 0.55
            elif s_year_shape < 0.42:
                score *= 0.72
            elif s_year_shape < 0.56:
                score *= 0.86

            if s_year_tail < 0.22:
                score *= 0.72
            elif s_year_tail < 0.38:
                score *= 0.86

            if s_year_trend < 0.22:
                score *= 0.80
            elif s_year_trend < 0.36:
                score *= 0.90

            if single_core_target and s_year_shape < 0.48:
                score *= 0.82

            # 동일 3년합계라도 연도별 분포/추이가 다르면 유사도를 강하게 낮춘다.
            shape_penalty = (0.45 + (0.55 * s_year_shape))
            shape_penalty *= (0.55 + (0.45 * s_year_tail))
            shape_penalty *= (0.65 + (0.35 * s_year_trend))
            if single_core_target:
                shape_penalty *= (0.90 + (0.10 * s_year_shape))
            score *= max(0.35, min(1.0, shape_penalty))

        if tokens_t and tokens_c:
            if not inter:
                score *= 0.08
            elif multi_core_target and len(inter) <= 1:
                score *= 0.55
            if single_core_target and token_precision < 0.28:
                score *= 0.74
            elif multi_core_target and token_precision < 0.36:
                score *= 0.80
            if single_core_target and len(tokens_c) >= 2:
                # 단일 업종 검색에서 복합면허(예: 전기+소방) 과대매칭 억제
                extra_tokens = len(tokens_c - tokens_t)
                if extra_tokens >= 1:
                    score *= 0.62
                    if token_precision < 0.60:
                        score *= 0.72
                    spec_ratio = _safe_ratio(target.get("specialty"), candidate.get("specialty"))
                    sales_ratio = _safe_ratio(target.get("sales3_eok"), candidate.get("sales3_eok"))
                    if (
                        (spec_ratio is not None and (spec_ratio < 0.35 or spec_ratio > 2.85))
                        or (sales_ratio is not None and (sales_ratio < 0.35 or sales_ratio > 2.85))
                    ):
                        score *= 0.72
            if self._is_single_token_cross_combo(tokens_t, tokens_c, candidate.get("license_text")):
                # 단일 업종 입력 시 타 핵심업종이 섞인 복합면허는 하드 감점
                score *= 0.10
        elif (not tokens_t) and raw_key:
            if raw_license_similarity < 0.28:
                score *= 0.55
            elif raw_license_similarity < 0.42:
                score *= 0.78

        return max(0.0, min(100.0, float(score)))

    def refresh(self) -> Dict[str, Any]:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = core.ServiceAccountCredentials.from_json_keyfile_name(core.JSON_FILE, scope)
        client = core.gspread.authorize(creds)
        book = client.open(core.SHEET_NAME)
        ws = book.sheet1
        all_values = ws.get_all_values()

        records = core._build_estimate_records(all_values)
        train_records = [
            r
            for r in records
            if isinstance(r.get("current_price_eok"), (int, float)) and float(r.get("current_price_eok") or 0) > 0
        ]
        token_index = core._build_neighbor_index(train_records)
        loaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        balance_vals = [float(r["balance_eok"]) for r in train_records if isinstance(r.get("balance_eok"), (int, float))]
        capital_vals = [float(r["capital_eok"]) for r in train_records if isinstance(r.get("capital_eok"), (int, float))]
        surplus_vals = [float(r["surplus_eok"]) for r in train_records if isinstance(r.get("surplus_eok"), (int, float))]
        debt_vals = [float(r["debt_ratio"]) for r in train_records if isinstance(r.get("debt_ratio"), (int, float))]
        liq_vals = [float(r["liq_ratio"]) for r in train_records if isinstance(r.get("liq_ratio"), (int, float))]
        specialty_vals = [float(r["specialty"]) for r in train_records if isinstance(r.get("specialty"), (int, float))]
        sales3_vals = [float(r["sales3_eok"]) for r in train_records if isinstance(r.get("sales3_eok"), (int, float))]

        def _quantile(vals: List[float], q: float) -> Optional[float]:
            nums = [float(x) for x in list(vals or []) if isinstance(x, (int, float))]
            if not nums:
                return None
            nums.sort()
            if len(nums) == 1:
                return nums[0]
            qv = max(0.0, min(1.0, float(q)))
            idx = qv * (len(nums) - 1)
            lo = int(idx)
            hi = min(len(nums) - 1, lo + 1)
            frac = idx - lo
            return nums[lo] + (nums[hi] - nums[lo]) * frac

        meta = {
            "loaded_at": loaded_at,
            "all_record_count": len(records),
            "train_count": len(train_records),
            "avg_balance_eok": core._round4(sum(balance_vals) / len(balance_vals)) if balance_vals else None,
            "avg_capital_eok": core._round4(sum(capital_vals) / len(capital_vals)) if capital_vals else None,
            "avg_surplus_eok": core._round4(sum(surplus_vals) / len(surplus_vals)) if surplus_vals else None,
            "avg_debt_ratio": core._round4(sum(debt_vals) / len(debt_vals)) if debt_vals else None,
            "avg_liq_ratio": core._round4(sum(liq_vals) / len(liq_vals)) if liq_vals else None,
            "median_specialty": core._round4(_quantile(specialty_vals, 0.5)),
            "p90_specialty": core._round4(_quantile(specialty_vals, 0.9)),
            "median_sales3_eok": core._round4(_quantile(sales3_vals, 0.5)),
            "p90_sales3_eok": core._round4(_quantile(sales3_vals, 0.9)),
        }

        with self._lock:
            self._records = records
            self._train_records = train_records
            self._token_index = token_index
            self._meta = meta
            self._loaded_at = loaded_at
        return meta

    def _snapshot(self) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
        with self._lock:
            return list(self._train_records), dict(self._token_index), dict(self._meta)

    def _target_from_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        license_text = _compact(payload.get("license_text") or payload.get("license") or "")
        y23 = _to_float(payload.get("y23"))
        y24 = _to_float(payload.get("y24"))
        y25 = _to_float(payload.get("y25"))
        sales3 = _to_float(payload.get("sales3_eok"))
        if sales3 is None:
            vals = [v for v in [y23, y24, y25] if isinstance(v, float)]
            sales3 = sum(vals) if vals else None

        return {
            "uid": "",
            "row": 0,
            "license_text": license_text,
            "raw_license_key": _normalize_license_key(license_text),
            "license_tokens": core._license_token_set_for_estimate(license_text),
            "license_year": _to_float(payload.get("license_year")),
            "specialty": _to_float(payload.get("specialty")),
            "y23": y23,
            "y24": y24,
            "y25": y25,
            "sales3_eok": sales3,
            "sales5_eok": _to_float(payload.get("sales5_eok")) if _to_float(payload.get("sales5_eok")) is not None else sales3,
            "balance_eok": _to_float(payload.get("balance_eok")),
            "claim_price_eok": _to_float(
                payload.get("claim_price_eok")
                if payload.get("claim_price_eok") is not None
                else (payload.get("claim_eok") if payload.get("claim_eok") is not None else payload.get("claim_price"))
            ),
            "capital_eok": _to_float(payload.get("capital_eok")),
            "surplus_eok": _to_float(payload.get("surplus_eok")),
            "debt_ratio": _to_float(payload.get("debt_ratio")),
            "liq_ratio": _to_float(payload.get("liq_ratio")),
            "debt_level": _compact(payload.get("debt_level")).lower(),
            "liq_level": _compact(payload.get("liq_level")).lower(),
            "company_type": _compact(payload.get("company_type")),
            "credit_level": _compact(payload.get("credit_level")),
            "admin_history": _compact(payload.get("admin_history")),
            "ok_capital": bool(payload.get("ok_capital", True)),
            "ok_engineer": bool(payload.get("ok_engineer", True)),
            "ok_office": bool(payload.get("ok_office", True)),
            "provided_signals": int(payload.get("provided_signals") or 0),
            "missing_critical": list(payload.get("missing_critical") or []),
            "missing_guide": list(payload.get("missing_guide") or []),
        }

    def _collect_neighbors(
        self,
        target: Dict[str, Any],
        train_records: List[Dict[str, Any]],
        token_index: Dict[str, List[Dict[str, Any]]],
        top_k: int,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        tokens = self._canonical_tokens(target.get("license_tokens") or set())
        candidates: List[Dict[str, Any]] = []
        seen = set()
        if tokens:
            for token in tokens:
                for rec in token_index.get(token, []):
                    marker = (str(rec.get("uid", "")), int(rec.get("row", 0) or 0))
                    if marker in seen:
                        continue
                    seen.add(marker)
                    candidates.append(rec)
        if tokens and len(candidates) < 40:
            # Direct token hit is 부족할 때 형태가 유사한 업종까지 확장한다.
            for rec in train_records:
                marker = (str(rec.get("uid", "")), int(rec.get("row", 0) or 0))
                if marker in seen:
                    continue
                cand_tokens = self._canonical_tokens(rec.get("license_tokens") or set())
                if self._has_fuzzy_token_overlap(tokens, cand_tokens):
                    seen.add(marker)
                    candidates.append(rec)
        raw_key = _normalize_license_key(target.get("raw_license_key") or target.get("license_text"))
        if (not tokens) and raw_key and len(raw_key) >= 2:
            hinted = []
            for rec in train_records:
                text = _normalize_license_key(rec.get("license_text"))
                if not text:
                    continue
                if (raw_key in text) or (text in raw_key) or (_bigram_jaccard(raw_key, text) >= 0.55):
                    hinted.append(rec)
            if len(hinted) > 0:
                candidates = hinted
        if len(candidates) < 80 and not tokens:
            candidates = list(train_records)
        elif tokens and not candidates:
            candidates = list(train_records)

        target_core_set = self._core_tokens(tokens)
        target_core_count = len(target_core_set)

        min_similarity = 26.0 if tokens else 12.0
        if target_core_count >= 2:
            min_similarity = 32.0
        if tokens and len(candidates) <= 16:
            min_similarity = max(20.0, min_similarity - 4.0)
        if int(target.get("provided_signals") or 0) <= 2:
            min_similarity = min_similarity + 6.0
        missing_critical = list(target.get("missing_critical") or [])
        if tokens and not missing_critical:
            min_similarity += 3.0

        def _score_pool(pool: List[Dict[str, Any]], strict_same_core: bool, threshold: float) -> List[Tuple[float, Dict[str, Any]]]:
            out: List[Tuple[float, Dict[str, Any]]] = []
            for cand in pool:
                p = cand.get("current_price_eok")
                if not isinstance(p, (int, float)) or float(p) <= 0:
                    continue
                cand_tokens = self._canonical_tokens(cand.get("license_tokens") or set())
                cand_core = self._core_tokens(cand_tokens) | self._core_tokens_from_text(cand.get("license_text"))
                if target_core_count >= 2 and target_core_set and not (target_core_set & cand_core):
                    continue
                if strict_same_core and not self._is_single_token_same_core(tokens, cand_tokens, cand.get("license_text")):
                    continue
                if self._is_single_token_cross_combo(tokens, cand_tokens, cand.get("license_text")):
                    continue
                if self._is_single_token_profile_outlier(target, cand):
                    continue
                sim = self._neighbor_score(target, cand)
                if sim < threshold:
                    continue
                out.append((sim, cand))
            return out

        strict_same_core = target_core_count == 1
        scored: List[Tuple[float, Dict[str, Any]]] = _score_pool(candidates, strict_same_core, float(min_similarity))
        if strict_same_core and not scored:
            scored = _score_pool(candidates, True, max(12.0, float(min_similarity) - 8.0))

        if not scored:
            coarse: List[Tuple[float, Dict[str, Any]]] = []
            coarse_pool = candidates if (tokens and candidates) else train_records
            for cand in coarse_pool:
                p = cand.get("current_price_eok")
                if not isinstance(p, (int, float)) or float(p) <= 0:
                    continue
                cand_tokens = self._canonical_tokens(cand.get("license_tokens") or set())
                cand_core = self._core_tokens(cand_tokens) | self._core_tokens_from_text(cand.get("license_text"))
                if target_core_count >= 2 and target_core_set and not (target_core_set & cand_core):
                    continue
                if strict_same_core and not self._is_single_token_same_core(tokens, cand_tokens, cand.get("license_text")):
                    continue
                if self._is_single_token_cross_combo(tokens, cand_tokens, cand.get("license_text")):
                    continue
                if self._is_single_token_profile_outlier(target, cand):
                    continue
                sim = self._neighbor_score(target, cand)
                coarse.append((max(0.1, sim), cand))
            coarse.sort(key=lambda x: x[0], reverse=True)
            return coarse[: max(18, min(22, top_k))]

        scored.sort(key=lambda x: x[0], reverse=True)
        if strict_same_core:
            strict: List[Tuple[float, Dict[str, Any]]] = []
            for sim, cand in scored:
                cand_tokens = self._canonical_tokens(cand.get("license_tokens") or set())
                if self._is_single_token_cross_combo(tokens, cand_tokens, cand.get("license_text")):
                    continue
                if not self._is_single_token_same_core(tokens, cand_tokens, cand.get("license_text")):
                    continue
                if not cand_tokens:
                    strict.append((sim, cand))
                    continue
                inter_count = len(tokens & cand_tokens)
                precision = (inter_count / float(max(1, len(cand_tokens))))
                if len(cand_tokens) == 1 or precision >= 0.60:
                    strict.append((sim, cand))
            if len(strict) >= max(10, top_k):
                scored = strict
        return scored[: max(top_k, 12, 14 if tokens else 12)]

    @staticmethod
    def _weighted_mean(values: List[float], weights: List[float]) -> Optional[float]:
        total_w = 0.0
        total_v = 0.0
        for v, w in zip(values or [], weights or []):
            vv = _to_float(v)
            ww = _to_float(w)
            if vv is None or ww is None or ww <= 0:
                continue
            total_w += ww
            total_v += vv * ww
        if total_w <= 0:
            return None
        return total_v / total_w

    def _build_feature_anchor(
        self,
        target: Dict[str, Any],
        neighbors: List[Tuple[float, Dict[str, Any]]],
    ) -> Dict[str, Any]:
        components: List[float] = []
        comp_weights: List[float] = []
        max_samples = 0
        notes: List[str] = []

        def build_component(
            target_field: str,
            candidate_field: str,
            weight: float,
            label: str,
            ratio_lo: float = 0.004,
            ratio_hi: float = 9.0,
        ) -> None:
            nonlocal max_samples
            target_value = _to_float(target.get(target_field))
            if target_value is None or target_value <= 0:
                return
            ratios: List[float] = []
            ratio_weights: List[float] = []
            for sim, rec in neighbors[:10]:
                price = _to_float(rec.get("current_price_eok"))
                base = _to_float(rec.get(candidate_field))
                if price is None or base is None or base <= 0:
                    continue
                ratio = price / base
                if ratio < ratio_lo or ratio > ratio_hi:
                    continue
                ratios.append(ratio)
                ratio_weights.append(max(0.2, float(sim) / 45.0))
            if len(ratios) < 3:
                return
            max_samples = max(max_samples, len(ratios))
            ratio_mid = core._weighted_quantile(ratios, ratio_weights, 0.5)
            if ratio_mid is None:
                return
            anchor = target_value * float(ratio_mid)
            if anchor <= 0:
                return
            components.append(anchor)
            comp_weights.append(weight)
            notes.append(f"{label} 앵커 반영")

        build_component("specialty", "specialty", 0.44, "시평")
        build_component("sales3_eok", "sales3_eok", 0.26, "3개년 실적")
        build_component("capital_eok", "capital_eok", 0.12, "자본금", ratio_lo=0.02, ratio_hi=15.0)
        build_component("balance_eok", "balance_eok", 0.18, "공제조합 잔액", ratio_lo=0.02, ratio_hi=40.0)

        if not components:
            return {"anchor": None, "reliability": 0.0, "notes": notes}

        anchor = self._weighted_mean(components, comp_weights)
        if anchor is None or anchor <= 0:
            return {"anchor": None, "reliability": 0.0, "notes": notes}

        reliability = min(1.0, float(max_samples) / 8.0)
        provided_signals = int(target.get("provided_signals") or 0)
        if provided_signals >= 6:
            reliability *= 1.0
        elif provided_signals >= 4:
            reliability *= 0.88
        else:
            reliability *= 0.68
        return {"anchor": float(anchor), "reliability": float(reliability), "notes": notes}

    def _apply_anchor_guard(
        self,
        center: float,
        low: float,
        high: float,
        anchor_info: Dict[str, Any],
        notes: List[str],
    ) -> Tuple[float, float, float]:
        anchor = _to_float(anchor_info.get("anchor"))
        reliability = max(0.0, min(1.0, float(_to_float(anchor_info.get("reliability")) or 0.0)))
        if anchor is None or anchor <= 0 or reliability <= 0:
            return center, low, high
        ratio = center / anchor if anchor > 0 else 1.0
        if 0.58 <= ratio <= 1.72:
            return center, low, high
        deviation = abs((ratio if ratio > 0 else 1e-6) - 1.0)
        pull = max(0.18, min(0.58, deviation * 0.35)) * reliability
        adjusted_center = (center * (1.0 - pull)) + (anchor * pull)
        if adjusted_center <= 0:
            return center, low, high
        scale = adjusted_center / max(center, 0.05)
        adjusted_low = max(0.05, low * scale)
        adjusted_high = max(adjusted_low, high * scale)
        # Guard 적용 시 불확실성 증가를 반영해 범위를 소폭 확대한다.
        widen = max(0.03, (adjusted_high - adjusted_low) * 0.08)
        adjusted_low = max(0.05, adjusted_low - widen)
        adjusted_high = max(adjusted_low, adjusted_high + widen)
        notes.append(
            f"입력 스케일(시평/실적) 기반 보정 적용: {core._round4(center)}억 → {core._round4(adjusted_center)}억"
        )
        return adjusted_center, adjusted_low, adjusted_high

    @staticmethod
    def _apply_uncertainty_discount(
        center: float,
        low: float,
        high: float,
        avg_sim: float,
        neighbor_count: int,
        avg_token_match: float,
        notes: List[str],
    ) -> Tuple[float, float, float, float]:
        if center <= 0:
            return center, low, high, 0.0
        discount = 0.0
        if avg_sim < 55:
            discount += min(0.18, (55.0 - float(avg_sim)) / 260.0)
        if neighbor_count < 4:
            discount += min(0.12, (4 - int(neighbor_count)) * 0.03)
        if avg_token_match < 0.60:
            discount += min(0.08, (0.60 - float(avg_token_match)) * 0.20)
        discount = max(0.0, min(0.22, discount))
        if discount <= 0.01:
            return center, low, high, 0.0
        next_center = center * (1.0 - discount)
        next_low = max(0.05, low * (1.0 - discount * 0.85))
        next_high = max(next_low, high * (1.0 - discount * 0.65))
        notes.append(f"유사도 불확실성 보정: {int(round(discount * 100))}% 보수 조정")
        return float(next_center), float(next_low), float(next_high), float(discount)

    @staticmethod
    def _apply_upper_guard_by_similarity(
        center: float,
        low: float,
        high: float,
        prices: List[float],
        sims: List[float],
        avg_token_match: float,
        neighbor_count: int,
        notes: List[str],
    ) -> Tuple[float, float, float]:
        if center <= 0:
            return center, low, high
        safe_prices = [float(v) for v in list(prices or []) if isinstance(v, (int, float)) and float(v) > 0]
        if not safe_prices:
            return center, low, high
        safe_sims = [float(v) for v in list(sims or []) if isinstance(v, (int, float)) and float(v) > 0]
        if len(safe_sims) != len(safe_prices):
            safe_sims = [1.0 for _ in safe_prices]
        p80 = core._weighted_quantile(safe_prices, safe_sims, 0.80)
        p90 = core._weighted_quantile(safe_prices, safe_sims, 0.90)
        ref = p80 if isinstance(p80, (int, float)) and float(p80) > 0 else p90
        if not isinstance(ref, (int, float)) or float(ref) <= 0:
            ref = max(safe_prices)
        token = float(avg_token_match) if isinstance(avg_token_match, (int, float)) else 1.0
        n = int(neighbor_count or len(safe_prices))
        cap_multiplier = 1.24
        if token >= 0.80 and n >= 6:
            cap_multiplier = 1.36
        elif token >= 0.70 and n >= 4:
            cap_multiplier = 1.28
        elif token < 0.60 or n <= 3:
            cap_multiplier = 1.12
        upper_cap = float(ref) * cap_multiplier
        trigger_ratio = 1.08
        if token >= 0.70 and n >= 6:
            trigger_ratio = 1.22
        elif token >= 0.60 and n >= 4:
            trigger_ratio = 1.15
        if center <= (upper_cap * trigger_ratio):
            return center, low, high
        excess = (center / max(upper_cap, 0.05)) - 1.0
        pull_gain = 0.42 if (token >= 0.70 and n >= 6) else (0.75 if n <= 3 else 0.58)
        pull = max(0.16, min(0.68, excess * pull_gain))
        next_center = (center * (1.0 - pull)) + (upper_cap * pull)
        scale = next_center / max(center, 0.05)
        next_low = max(0.05, float(low) * scale)
        next_high = max(next_low, min(float(high) * scale, upper_cap * (1.26 if n <= 3 else 1.34)))
        notes.append(
            f"고가 이상치 억제: 상위 분위 대비 초과분 {int(round(max(0.0, excess) * 100))}%를 점진 보정했습니다."
        )
        return float(next_center), float(next_low), float(next_high)

    def _build_yoy_insight(
        self,
        target: Dict[str, Any],
        center: float,
        neighbors: List[Tuple[float, Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        if center <= 0:
            return None
        trend_vals: List[float] = []
        trend_wts: List[float] = []
        basis_parts: List[str] = []

        def push_trend(val: Optional[float], wt: float, basis: str) -> None:
            if val is None:
                return
            vv = max(-0.85, min(0.85, float(val)))
            trend_vals.append(vv)
            trend_wts.append(max(0.1, float(wt)))
            if basis:
                basis_parts.append(str(basis))

        y24 = _to_float(target.get("y24"))
        y25 = _to_float(target.get("y25"))
        y23 = _to_float(target.get("y23"))
        if y24 is not None and y25 is not None and abs(y24) > 0.1:
            g = (y25 - y24) / max(abs(y24), 0.1)
            if abs(g) >= 0.005:
                push_trend(g, 2.4 if abs(g) >= 0.03 else 1.0, "입력 실적(2024→2025)")
        elif y23 is not None and y24 is not None and abs(y23) > 0.1:
            g = (y24 - y23) / max(abs(y23), 0.1)
            if abs(g) >= 0.005:
                push_trend(g, 1.8 if abs(g) >= 0.03 else 0.9, "입력 실적(2023→2024)")

        for sim, rec in neighbors[:8]:
            s23 = _to_float(rec.get("years", {}).get("y23"))
            s24 = _to_float(rec.get("years", {}).get("y24"))
            s25 = _to_float(rec.get("years", {}).get("y25"))
            if s24 is not None and s25 is not None and abs(s24) > 0.1:
                g = (s25 - s24) / max(abs(s24), 0.1)
                push_trend(g, max(0.35, float(sim) / 42.0), "업종·실적 유사군")
            elif s23 is not None and s24 is not None and abs(s23) > 0.1:
                g = (s24 - s23) / max(abs(s23), 0.1)
                push_trend(g, max(0.30, float(sim) / 52.0), "업종·실적 유사군")

        if not trend_vals:
            return None
        trend_mid = core._weighted_quantile(trend_vals, trend_wts, 0.5)
        trend_avg = self._weighted_mean(trend_vals, trend_wts)
        if trend_mid is None and trend_avg is None:
            return None
        trend = (
            ((float(trend_mid) * 0.6) + (float(trend_avg) * 0.4))
            if trend_mid is not None and trend_avg is not None
            else float(trend_mid if trend_mid is not None else trend_avg)
        )
        ratio = max(0.72, min(1.28, 1.0 + (max(-0.48, min(0.48, trend)) * 0.28)))
        prev_center = center / ratio
        if prev_center <= 0:
            return None
        now_year = datetime.now().year
        basis = " + ".join(sorted(set(basis_parts))) if basis_parts else "업종·실적 유사군"
        return {
            "current_year": int(now_year),
            "previous_year": int(now_year - 1),
            "previous_center": core._round4(prev_center),
            "change_pct": core._round4(((center / prev_center) - 1.0) * 100.0),
            "basis": basis,
        }

    def estimate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        train_records, token_index, meta = self._snapshot()
        if not train_records:
            return {"ok": False, "error": "학습 데이터가 비어 있습니다. /reload 후 다시 시도해 주세요."}

        target = self._target_from_payload(payload)
        balance_excluded = self._is_balance_separate_paid_group(target)
        if balance_excluded:
            target["balance_eok"] = None
            target["missing_critical"] = [
                x
                for x in list(target.get("missing_critical") or [])
                if "공제조합" not in str(x)
            ]
        has_any_signal = bool(target.get("license_text")) or any(
            isinstance(target.get(k), (int, float))
            for k in ["specialty", "sales3_eok", "balance_eok", "capital_eok", "surplus_eok", "license_year"]
        )
        if not has_any_signal:
            return {"ok": False, "error": "입력된 정보가 없습니다. 면허/업종 또는 숫자 항목 1개 이상 입력해 주세요."}

        top_k = max(5, min(20, int(_to_float(payload.get("top_k")) or 12)))
        display_neighbors = self._collect_neighbors(target, train_records, token_index, top_k=top_k)
        if not display_neighbors:
            return {"ok": False, "error": "유사 매물이 부족합니다."}

        stat_scan_k = max(180, min(1200, top_k * 24))
        stat_candidates = self._collect_neighbors(target, train_records, token_index, top_k=stat_scan_k)
        if not stat_candidates:
            stat_candidates = list(display_neighbors)

        seed_neighbors = list(stat_candidates[: min(18, len(stat_candidates))])
        seed_prices = [float(rec.get("current_price_eok")) for _sim, rec in seed_neighbors]
        seed_sims = [float(sim) for sim, _rec in seed_neighbors]
        seed_center = core._weighted_quantile(seed_prices, seed_sims, 0.5)
        if seed_center is not None and seed_center > 0 and len(seed_neighbors) >= 8:
            filtered: List[Tuple[float, Dict[str, Any]]] = []
            for sim, rec in stat_candidates:
                p = _to_float(rec.get("current_price_eok"))
                if p is None or p <= 0:
                    continue
                ratio = p / float(seed_center)
                lower = 0.22 if target.get("license_tokens") else 0.12
                upper = 4.8 if target.get("license_tokens") else 7.0
                if float(sim) >= 88:
                    lower = min(lower, 0.16)
                    upper = max(upper, 5.5)
                if lower <= ratio <= upper:
                    filtered.append((sim, rec))
            if len(filtered) >= max(8, top_k):
                stat_candidates = filtered

        token_set = self._canonical_tokens(target.get("license_tokens") or set())
        token_count = len(self._core_tokens(token_set))
        if token_count <= 0:
            token_count = len(token_set)
        sim_window = 18.0 if token_count >= 2 else (14.0 if token_count == 1 else 10.0)
        best_sim = float(stat_candidates[0][0])
        stat_floor = max(20.0 if token_count >= 2 else (14.0 if token_count == 1 else 10.0), best_sim - sim_window)
        stat_neighbors = [(sim, rec) for sim, rec in stat_candidates if float(sim) >= stat_floor]
        min_stat_size = max(10, top_k)
        if len(stat_neighbors) < min_stat_size:
            stat_neighbors = stat_candidates[: max(min_stat_size, top_k * 4)]

        single_core = self._single_token_target_core(token_set)
        if single_core:
            strict_neighbors: List[Tuple[float, Dict[str, Any]]] = []
            for sim, rec in stat_neighbors:
                cand_tokens = self._canonical_tokens(rec.get("license_tokens") or set())
                if self._is_single_token_cross_combo(token_set, cand_tokens, rec.get("license_text")):
                    continue
                if not self._is_single_token_same_core(token_set, cand_tokens, rec.get("license_text")):
                    continue
                yearly = _yearly_shape_similarity(target, rec)
                if yearly["strength"] >= 0.65 and yearly["shape"] < 0.32:
                    continue
                strict_neighbors.append((sim, rec))

            if len(strict_neighbors) >= max(8, top_k):
                stat_neighbors = strict_neighbors
            elif len(strict_neighbors) >= 4 and len(stat_neighbors) >= max(8, top_k):
                selected: List[Tuple[float, Dict[str, Any]]] = list(strict_neighbors)
                picked = {
                    (int(x[1].get("row", 0) or 0), str(x[1].get("uid", "")).strip())
                    for x in strict_neighbors
                }
                for sim, rec in stat_neighbors:
                    marker = (int(rec.get("row", 0) or 0), str(rec.get("uid", "")).strip())
                    if marker in picked:
                        continue
                    selected.append((sim, rec))
                    if len(selected) >= max(8, top_k):
                        break
                stat_neighbors = selected

        display_neighbors = stat_neighbors[: max(top_k, 12)]

        prices = [float(rec.get("current_price_eok")) for _sim, rec in stat_neighbors]
        sims = [float(sim) for sim, _rec in stat_neighbors]
        center = core._weighted_quantile(prices, sims, 0.5)
        p25 = core._weighted_quantile(prices, sims, 0.25)
        p75 = core._weighted_quantile(prices, sims, 0.75)
        p10 = core._weighted_quantile(prices, sims, 0.10)
        p90 = core._weighted_quantile(prices, sims, 0.90)
        p95 = core._weighted_quantile(prices, sims, 0.95)
        if center is None:
            return {"ok": False, "error": "산정 실패"}
        if p25 is None:
            p25 = min(prices)
        if p75 is None:
            p75 = max(prices)
        if p10 is None:
            p10 = min(prices)
        if p90 is None:
            p90 = max(prices)
        if p95 is None:
            p95 = max(prices)

        abs_dev = [abs(x - center) for x in prices]
        mad = float(core._weighted_quantile(abs_dev, sims, 0.5) or 0.0)
        spread = max(float(p75) - float(p25), mad * 1.8, float(center) * 0.08, 0.08)
        low = max(0.05, float(center) - spread * 0.55)
        high = max(low, float(center) + spread * 0.55)
        avg_sim = sum(sims) / max(1.0, len(sims))

        claim_eok = _to_float(target.get("claim_price_eok"))
        if claim_eok is not None and claim_eok > 0:
            base_center = float(center)
            gap_ratio = abs(float(claim_eok) - base_center) / max(base_center, 0.1)
            claim_weight = min(0.35, 0.18 + max(0.0, gap_ratio - 0.15) * 0.20)
            p90_safe = max(float(p90), 0.1)
            p10_safe = max(float(p10), 0.1)
            if float(claim_eok) > (p90_safe * 1.25) and avg_sim >= 52:
                uplift = min(0.40, max(0.0, ((float(claim_eok) / p90_safe) - 1.25) * 0.28))
                if len(stat_neighbors) <= 6:
                    uplift *= 1.15
                if token_count >= 2:
                    uplift *= 1.10
                claim_weight = min(0.72, claim_weight + uplift)
            elif float(claim_eok) < (p10_safe * 0.80) and avg_sim >= 52:
                down = min(0.20, max(0.0, (0.80 - (float(claim_eok) / p10_safe)) * 0.18))
                claim_weight = max(0.10, claim_weight - down)

            center = (base_center * (1.0 - claim_weight)) + (float(claim_eok) * claim_weight)
            low = min(low, center)
            high = max(high, center)
            if float(claim_eok) >= 20 and avg_sim >= 55:
                high_gap = (float(claim_eok) / max(float(center), 0.1)) - 1.0
                if high_gap > 0.22:
                    sparse_pull = min(0.34, max(0.10, ((high_gap - 0.22) * 0.28) + 0.10))
                    center = (float(center) * (1.0 - sparse_pull)) + (float(claim_eok) * sparse_pull)
                    low = min(low, center)
                    high = max(high, center)
            if float(claim_eok) > high * 1.18:
                extra = min(float(claim_eok) - high, max(float(center) * 0.45, (high - low) * 0.80))
                extra_w = 0.55
                if float(claim_eok) >= 20 and avg_sim >= 55:
                    extra_w = 0.86
                high = high + max(0.0, extra * extra_w)
            if float(claim_eok) >= 20 and avg_sim >= 55 and float(claim_eok) > max(float(p90) * 1.20, float(center) * 1.18):
                high = max(high, float(claim_eok))

        upper_cap = max(float(p95) * 1.35, float(p90) * 1.45, float(p75) * 1.60, 0.15)
        claim_allows_high = isinstance(claim_eok, float) and claim_eok > (upper_cap * 1.05)
        if float(center) > upper_cap and not claim_allows_high:
            ratio = (float(center) / max(upper_cap, 0.1)) - 1.0
            pull = min(0.65, max(0.18, ratio * 0.55 + 0.18))
            next_center = (float(center) * (1.0 - pull)) + (upper_cap * pull)
            scale = next_center / max(float(center), 0.1)
            center = next_center
            low = max(0.05, float(low) * scale)
            high = max(low, float(high) * scale)

        notes: List[str] = []
        if not target.get("license_text"):
            notes.append("면허/업종 미입력: 전체 DB 유사도 기준으로 추정되어 오차 범위가 넓어질 수 있습니다.")
        if list(target.get("missing_critical") or []):
            notes.append(
                "핵심 항목 미입력: " + " · ".join([str(x) for x in list(target.get("missing_critical") or []) if str(x).strip()])
            )
        if list(target.get("missing_guide") or []):
            notes.append(
                "추가 입력 권장: " + " · ".join([str(x) for x in list(target.get("missing_guide") or []) if str(x).strip()])
            )

        def apply_relative(label: str, value: Optional[float], avg: Optional[float], weight: float, max_adj: float) -> float:
            if value is None or avg is None or avg <= 0:
                return 0.0
            rel = (float(value) - float(avg)) / max(float(avg), 0.1)
            adj = max(-max_adj, min(max_adj, rel * weight))
            if abs(adj) >= 0.01:
                notes.append(f"{label} 반영: {'+' if adj >= 0 else ''}{adj * 100:.1f}%")
            return adj

        def apply_neighbor_percentile(
            label: str,
            value: Optional[float],
            field: str,
            direction: int,
            weight: float,
            max_adj: float,
            min_samples: int = 6,
        ) -> float:
            vv = _to_float(value)
            if vv is None:
                return 0.0
            vals: List[float] = []
            for _sim, rec in stat_neighbors:
                rv = _to_float(rec.get(field))
                if rv is None:
                    continue
                vals.append(float(rv))
            if len(vals) < int(min_samples):
                return 0.0
            vals.sort()
            le = 0
            for x in vals:
                if x <= vv:
                    le += 1
            pct = float(le) / max(1.0, float(len(vals)))
            centered = (pct - 0.5) * 2.0
            adj_raw = centered * float(weight) * (1.0 if int(direction) >= 0 else -1.0)
            adj = max(-float(max_adj), min(float(max_adj), adj_raw))
            if abs(adj) >= 0.008:
                notes.append(f"{label} 유사군 분위 반영: {'+' if adj >= 0 else ''}{adj * 100:.1f}%")
            return float(adj)

        def apply_sales_trend() -> float:
            y23 = _to_float(target.get("y23"))
            y24 = _to_float(target.get("y24"))
            y25 = _to_float(target.get("y25"))
            if y23 is None and y24 is None and y25 is None:
                return 0.0
            growth = 0.0
            weight_sum = 0.0
            if y24 is not None and y25 is not None and abs(float(y24)) > 0.1:
                growth += ((float(y25) - float(y24)) / max(abs(float(y24)), 0.1)) * 0.62
                weight_sum += 0.62
            if y23 is not None and y25 is not None and abs(float(y23)) > 0.1:
                growth += ((float(y25) - float(y23)) / max(abs(float(y23)), 0.1)) * 0.38
                weight_sum += 0.38
            if weight_sum <= 0:
                return 0.0
            trend = max(-0.9, min(0.9, growth / weight_sum))
            adj = max(-0.06, min(0.06, trend * 0.06))
            if abs(adj) >= 0.008:
                notes.append(f"실적 추이 반영: {'+' if adj >= 0 else ''}{adj * 100:.1f}%")
            return float(adj)

        factor = 1.0
        if not balance_excluded:
            factor += apply_relative("공제조합 잔액", target.get("balance_eok"), _to_float(meta.get("avg_balance_eok")), 0.18, 0.22)
        factor += apply_relative("자본금", target.get("capital_eok"), _to_float(meta.get("avg_capital_eok")), 0.14, 0.18)
        factor += apply_relative("이익잉여금", target.get("surplus_eok"), _to_float(meta.get("avg_surplus_eok")), -0.14, 0.20)
        if not balance_excluded:
            factor += apply_neighbor_percentile("공제조합 잔액", target.get("balance_eok"), "balance_eok", 1, 0.12, 0.16, 5)
        factor += apply_neighbor_percentile("자본금", target.get("capital_eok"), "capital_eok", 1, 0.08, 0.10, 5)
        factor += apply_neighbor_percentile("이익잉여금", target.get("surplus_eok"), "surplus_eok", -1, 0.10, 0.12, 5)
        factor += apply_neighbor_percentile("면허연도", target.get("license_year"), "license_year", 1, 0.06, 0.08, 5)
        factor += apply_neighbor_percentile("시평", target.get("specialty"), "specialty", 1, 0.04, 0.06, 6)
        factor += apply_neighbor_percentile("최근 3개년 매출", target.get("sales3_eok"), "sales3_eok", 1, 0.05, 0.07, 6)
        factor += apply_neighbor_percentile("부채비율", target.get("debt_ratio"), "debt_ratio", -1, 0.07, 0.09, 5)
        factor += apply_neighbor_percentile("유동비율", target.get("liq_ratio"), "liq_ratio", 1, 0.07, 0.09, 5)
        factor = max(0.70, min(1.24, factor))
        center = float(center) * factor
        low = float(low) * factor
        high = float(high) * factor
        if balance_excluded:
            notes.append("전기/정보통신/소방 업종은 공제조합 잔액 별도 정산 관행을 반영해 가격 반영에서 제외했습니다.")

        # 유사군 스케일(시평/실적/자본금)과 산정치가 크게 벌어지면 안전 보정한다.
        anchor_info = self._build_feature_anchor(target, stat_neighbors)
        center, low, high = self._apply_anchor_guard(center, low, high, anchor_info, notes)
        for note in list(anchor_info.get("notes") or []):
            if note not in notes:
                notes.append(note)

        post_factor = 1.0
        if not target.get("ok_capital", True):
            post_factor -= 0.12
            notes.append("자본금 기준 미충족: 보수 하향")
        if not target.get("ok_engineer", True):
            post_factor -= 0.16
            notes.append("기술자 기준 미충족: 리스크 증가")
        if not target.get("ok_office", True):
            post_factor -= 0.10
            notes.append("사무실 기준 미충족: 리스크 증가")
        if target.get("ok_capital", True) and target.get("ok_engineer", True) and target.get("ok_office", True):
            post_factor += 0.03

        debt_level = str(target.get("debt_level") or "").lower()
        liq_level = str(target.get("liq_level") or "").lower()
        if debt_level == "above":
            post_factor -= 0.06
            notes.append("부채비율 평균 이상: 보수 하향")
        elif debt_level == "below":
            post_factor += 0.03
        if liq_level == "above":
            post_factor += 0.05
        elif liq_level == "below":
            post_factor -= 0.07
            notes.append("유동비율 평균 이하: 리스크 반영")

        company_type = self._company_type_key(target.get("company_type"))
        if company_type == "개인":
            post_factor -= 0.05
            notes.append("회사형태(개인사업자) 반영: 보수 하향")
        elif company_type == "주식회사":
            post_factor += 0.01
        elif company_type == "유한회사":
            post_factor -= 0.01

        credit_level = str(target.get("credit_level") or "").lower()
        admin_history = str(target.get("admin_history") or "").lower()
        if credit_level == "high":
            post_factor += 0.05
            notes.append("외부신용등급 우수: 가산 반영")
        elif credit_level == "low":
            post_factor -= 0.06
            notes.append("외부신용등급 주의: 감산 반영")
        if admin_history == "none":
            post_factor += 0.03
        elif admin_history == "has":
            post_factor -= 0.11
            notes.append("행정처분 이력 있음: 리스크 반영")

        def post_percentile_adj(
            label: str,
            value: Optional[float],
            field: str,
            direction: int,
            weight: float,
            max_adj: float,
            min_samples: int = 6,
        ) -> float:
            vv = _to_float(value)
            if vv is None:
                return 0.0
            vals: List[float] = []
            for _sim, rec in stat_neighbors:
                rv = _to_float(rec.get(field))
                if rv is None:
                    continue
                vals.append(float(rv))
            if len(vals) < int(min_samples):
                return 0.0
            vals.sort()
            le = 0
            for x in vals:
                if x <= vv:
                    le += 1
            pct = float(le) / max(1.0, float(len(vals)))
            centered = (pct - 0.5) * 2.0
            adj = max(-float(max_adj), min(float(max_adj), centered * float(weight) * (1.0 if int(direction) >= 0 else -1.0)))
            if abs(adj) >= 0.008:
                notes.append(f"{label} 세부 분위 보정: {'+' if adj >= 0 else ''}{adj * 100:.1f}%")
            return float(adj)

        post_factor += post_percentile_adj("시평", target.get("specialty"), "specialty", 1, 0.05, 0.06, 6)
        post_factor += post_percentile_adj("최근 3개년 매출", target.get("sales3_eok"), "sales3_eok", 1, 0.04, 0.05, 6)
        specialty_val = _to_float(target.get("specialty"))
        specialty_med = _to_float(meta.get("median_specialty"))
        if specialty_val is not None and specialty_med is not None and float(specialty_med) > 0:
            ratio = float(specialty_val) / max(float(specialty_med), 0.1)
            specialty_adj = 0.0
            if ratio > 0:
                specialty_adj = max(-0.06, min(0.08, math.log(ratio) * 0.045))
            post_factor += specialty_adj
            if abs(specialty_adj) >= 0.008:
                notes.append(f"시평 레벨 반영: {'+' if specialty_adj >= 0 else ''}{specialty_adj * 100:.1f}%")

        license_year = _to_float(target.get("license_year"))
        if license_year is not None and 1950 <= float(license_year) <= 2100:
            age = max(0.0, float(datetime.now().year) - float(license_year))
            license_adj = 0.0
            if age >= 12:
                license_adj += 0.03
            elif age >= 7:
                license_adj += 0.015
            elif age <= 2:
                license_adj -= 0.03
            elif age <= 4:
                license_adj -= 0.015
            post_factor += license_adj
            if abs(license_adj) >= 0.008:
                notes.append(f"면허 업력 반영: {'+' if license_adj >= 0 else ''}{license_adj * 100:.1f}%")

        surplus_val = _to_float(target.get("surplus_eok"))
        if surplus_val is not None:
            capital_val = _to_float(target.get("capital_eok"))
            surplus_adj = 0.0
            if capital_val is not None and float(capital_val) > 0.05:
                ratio = float(surplus_val) / max(0.05, float(capital_val))
                if ratio >= 1.2:
                    surplus_adj -= min(0.08, (ratio - 1.2) * 0.04 + 0.02)
                elif ratio >= 0.8:
                    surplus_adj -= min(0.05, (ratio - 0.8) * 0.05)
            elif float(surplus_val) >= 2.0:
                surplus_adj -= 0.03
            post_factor += surplus_adj
            if abs(surplus_adj) >= 0.008:
                notes.append(f"이익잉여금 리스크 반영: {'+' if surplus_adj >= 0 else ''}{surplus_adj * 100:.1f}%")

        post_factor += apply_sales_trend()
        post_factor = max(0.72, min(1.24, post_factor))
        center = float(center) * post_factor
        low = float(low) * post_factor
        high = float(high) * post_factor
        if abs(post_factor - 1.0) >= 0.01:
            notes.append(f"정성/리스크 종합 보정: {'+' if post_factor >= 1 else ''}{(post_factor - 1.0) * 100:.1f}%")

        # 입력 정보가 부족할수록 보수적으로 범위를 확장한다.
        if not target.get("license_text"):
            extra = (high - low) * 0.12
            low = max(0.05, low - extra)
            high = high + extra
        if list(target.get("missing_critical") or []):
            missing_count = len(list(target.get("missing_critical") or []))
            extra = (high - low) * (0.05 + (missing_count * 0.04))
            low = max(0.05, low - extra)
            high = high + extra
        token_match_ratios: List[float] = []
        target_tokens = self._canonical_tokens(target.get("license_tokens") or set())
        for _sim, rec in stat_neighbors:
            cand_tokens = self._canonical_tokens(rec.get("license_tokens") or set())
            token_match_ratios.append(_token_containment(target_tokens, cand_tokens) if target_tokens else 1.0)
        avg_token_match = sum(token_match_ratios) / max(1, len(token_match_ratios))

        center, low, high, discount = self._apply_uncertainty_discount(
            float(center),
            float(low),
            float(high),
            float(avg_sim),
            len(stat_neighbors),
            float(avg_token_match),
            notes,
        )
        center, low, high = self._apply_upper_guard_by_similarity(
            float(center),
            float(low),
            float(high),
            prices,
            sims,
            float(avg_token_match),
            len(stat_neighbors),
            notes,
        )
        retained_nudge = max(0.92, min(1.08, 1.0 + ((float(post_factor) - 1.0) * 0.35)))
        if abs(retained_nudge - 1.0) >= 0.005:
            center = float(center) * retained_nudge
            low = float(low) * retained_nudge
            high = float(high) * retained_nudge
            notes.append(
                f"상한 보정 후 입력값 반영 유지: {'+' if retained_nudge >= 1 else ''}{(retained_nudge - 1.0) * 100:.1f}%"
            )
        if len(stat_neighbors) <= 2:
            extra = max(float(center) * 0.18, (float(high) - float(low)) * 0.45)
            low = max(0.05, float(low) - (extra * 0.45))
            high = max(float(low), float(high) + extra)
            notes.append("근거 매물 수가 적어 오차 범위를 보수적으로 확장했습니다.")
        if float(center) < float(low):
            low = float(center)
        if float(center) > float(high):
            high = float(center)
        if high < low:
            high = low

        coverage = min(1.0, len(stat_neighbors) / 8.0)
        dispersion = mad / max(float(center), 0.1)
        confidence_score = (avg_sim * 0.60) + (coverage * 24.0) + max(0.0, 20.0 - dispersion * 60.0)
        if avg_sim >= 80:
            confidence_score += 3.0
        if len(stat_neighbors) >= 8:
            confidence_score += 4.0
        if avg_token_match >= 0.75:
            confidence_score += 8.0
        elif avg_token_match >= 0.60:
            confidence_score += 4.0
        confidence_score -= len(list(target.get("missing_critical") or [])) * 7.0
        if not target.get("license_text"):
            confidence_score -= 10.0
        if int(target.get("provided_signals") or 0) <= 2:
            confidence_score -= 8.0
        confidence_score -= abs(factor - 1.0) * 24.0
        if len(stat_neighbors) <= 2:
            confidence_score -= 14.0
        elif len(stat_neighbors) <= 4:
            confidence_score -= 6.0
        confidence_score -= discount * 40.0
        confidence_score = max(0.0, min(100.0, confidence_score))

        neighbor_rows: List[Dict[str, Any]] = []
        hot_match_count = 0
        for sim, rec in display_neighbors[:8]:
            cur = rec.get("current_price_eok")
            claim = rec.get("claim_price_eok")
            low_eok, high_eok = _derive_display_range_eok(rec.get("current_price_text"), rec.get("claim_price_text"), cur, claim)
            if not isinstance(low_eok, (int, float)):
                low_eok = cur
            if not isinstance(high_eok, (int, float)):
                high_eok = cur
            if isinstance(sim, (int, float)) and float(sim) >= 90:
                hot_match_count += 1
            seoul_no = int(rec.get("number", 0) or 0)
            neighbor_rows.append(
                {
                    "seoul_no": seoul_no,
                    "now_uid": str(rec.get("uid", "")).strip(),
                    "license_text": str(rec.get("license_text", "")).strip(),
                    "price_eok": core._round4(cur),
                    "display_low_eok": core._round4(low_eok),
                    "display_high_eok": core._round4(high_eok),
                    "y23": core._round4(_to_float(rec.get("years", {}).get("y23"))),
                    "y24": core._round4(_to_float(rec.get("years", {}).get("y24"))),
                    "y25": core._round4(_to_float(rec.get("years", {}).get("y25"))),
                    "sales3_eok": core._round4(_to_float(rec.get("sales3_eok"))),
                    "sales5_eok": core._round4(_to_float(rec.get("sales5_eok"))),
                    "similarity": core._round4(sim),
                    "url": f"{str(core.SITE_URL).rstrip('/')}/mna/{seoul_no}" if seoul_no > 0 else f"{str(core.SITE_URL).rstrip('/')}/mna",
                }
            )

        if not notes:
            notes.append("유사 매물 기반 기본 산정 결과입니다.")

        yoy = self._build_yoy_insight(target, float(center), stat_neighbors)
        previous_center = yoy.get("previous_center") if isinstance(yoy, dict) else None
        yoy_change_pct = yoy.get("change_pct") if isinstance(yoy, dict) else None

        return {
            "ok": True,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "estimate_center_eok": core._round4(center),
            "estimate_low_eok": core._round4(low),
            "estimate_high_eok": core._round4(high),
            "confidence_score": core._round4(confidence_score),
            "confidence_percent": int(round(confidence_score)),
            "avg_similarity": core._round4(avg_sim),
            "neighbor_count": len(stat_neighbors),
            "display_neighbor_count": len(neighbor_rows),
            "hot_match_count": int(hot_match_count),
            "balance_excluded": bool(balance_excluded),
            "risk_notes": notes,
            "neighbors": neighbor_rows,
            "previous_estimate_eok": previous_center,
            "yoy_change_pct": yoy_change_pct,
            "yoy_basis": yoy.get("basis") if isinstance(yoy, dict) else "",
            "current_year": yoy.get("current_year") if isinstance(yoy, dict) else datetime.now().year,
            "previous_year": yoy.get("previous_year") if isinstance(yoy, dict) else (datetime.now().year - 1),
        }

    @property
    def meta(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._meta)


class Handler(BaseHTTPRequestHandler):
    estimator: YangdoBlackboxEstimator = None  # type: ignore

    def _send(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # noqa: N802
        self._send(200, {"ok": True})

    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send(200, {"ok": True, "service": "yangdo_blackbox_api", "meta": self.estimator.meta})
            return
        if path == "/meta":
            self._send(200, {"ok": True, "meta": self.estimator.meta})
            return
        self._send(404, {"ok": False, "error": "not_found"})

    def do_POST(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            payload = {}

        if path == "/reload":
            try:
                meta = self.estimator.refresh()
                self._send(200, {"ok": True, "meta": meta})
            except Exception as e:
                self._send(500, {"ok": False, "error": str(e)})
            return

        if path == "/estimate":
            try:
                result = self.estimator.estimate(payload if isinstance(payload, dict) else {})
                self._send(200 if result.get("ok") else 422, result)
            except Exception as e:
                self._send(500, {"ok": False, "error": str(e)})
            return

        self._send(404, {"ok": False, "error": "not_found"})


def main() -> int:
    parser = argparse.ArgumentParser(description="SeoulMNA blackbox estimate API server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args()

    estimator = YangdoBlackboxEstimator()
    meta = estimator.refresh()
    print(f"[loaded] records={meta.get('all_record_count', 0)} train={meta.get('train_count', 0)} at={meta.get('loaded_at')}")

    Handler.estimator = estimator
    server = ThreadingHTTPServer((args.host, int(args.port)), Handler)
    print(f"[serving] http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
