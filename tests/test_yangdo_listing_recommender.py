"""Unit tests for core_engine.yangdo_listing_recommender.

Pure-function tests that do NOT depend on yangdo_calculator internals.
ops-dependent helpers are tested with minimal stub callables.
"""
import unittest
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core_engine.yangdo_listing_recommender import (
    RecommendationOps,
    _build_recommendation_meta,
    _build_recommendation_reasons,
    _compare_recommendation_entries,
    _fit_summary,
    _infer_balance_excluded,
    _matched_axes,
    _price_overlap_score,
    _range_pair_from_record,
    _recommendation_focus_signature,
    _recommendation_label,
    _recommendation_price_band,
    _rerank_with_diversity,
    _score_candidate,
    _yearly_fit_score,
    build_recommendation_bundle,
)


# ── Minimal stubs ────────────────────────────────────────────────────


def _stub_to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        return None if f != f else f  # NaN → None
    except (ValueError, TypeError):
        return None


def _stub_derive_display_range(text_cur, text_claim, cur, claim):
    """Simple passthrough — just return current/claim as low/high."""
    return cur, claim


def _stub_canonical_tokens(t: Any) -> set:
    if isinstance(t, set):
        return t
    return set()


def _stub_single_token_target_core(tokens: set) -> str:
    return next(iter(tokens), "") if len(tokens) == 1 else ""


def _stub_is_single_token_same_core(target_tokens, cand_tokens, license_text):
    return target_tokens == cand_tokens


def _stub_company_type_key(ct: Any) -> str:
    return str(ct or "").strip()


def _stub_feature_scale_mismatch(target, rec, **kwargs) -> Tuple[int, int]:
    return 0, 0


def _stub_token_containment(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _stub_relative_closeness(a: Any, b: Any) -> float:
    fa = _stub_to_float(a)
    fb = _stub_to_float(b)
    if fa is None or fb is None:
        return 0.0
    if fa == fb:
        return 1.0
    max_val = max(abs(fa), abs(fb), 1e-9)
    return max(0.0, 1.0 - abs(fa - fb) / max_val)


def _stub_sales_fit_score(target: dict, rec: dict) -> float:
    return 0.5


def _stub_yearly_shape_similarity(target: dict, rec: dict) -> dict:
    return {"shape": 0.0, "tail": 0.0, "trend": 0.0, "strength": 0.0}


def _stub_listing_number_band(n: Any) -> int:
    return int(_stub_to_float(n) or 0) // 1000


def _stub_compact(v: Any, max_len: int = 40) -> str:
    s = str(v or "")
    return s[:max_len] if len(s) > max_len else s


def _stub_round4(v: Any) -> Any:
    f = _stub_to_float(v)
    return round(f, 4) if f is not None else None


def _make_ops(**overrides) -> RecommendationOps:
    defaults = dict(
        canonical_tokens=_stub_canonical_tokens,
        single_token_target_core=_stub_single_token_target_core,
        is_single_token_same_core=_stub_is_single_token_same_core,
        company_type_key=_stub_company_type_key,
        feature_scale_mismatch=_stub_feature_scale_mismatch,
        token_containment=_stub_token_containment,
        relative_closeness=_stub_relative_closeness,
        sales_fit_score=_stub_sales_fit_score,
        yearly_shape_similarity=_stub_yearly_shape_similarity,
        derive_display_range_eok=_stub_derive_display_range,
        listing_number_band=_stub_listing_number_band,
        to_float=_stub_to_float,
        compact=_stub_compact,
        round4=_stub_round4,
        site_url="https://seoulmna.kr",
    )
    defaults.update(overrides)
    return RecommendationOps(**defaults)


# ── _infer_balance_excluded ──────────────────────────────────────────


class InferBalanceExcludedTest(unittest.TestCase):
    def test_explicit_flag(self):
        self.assertTrue(_infer_balance_excluded({"balance_excluded": True}, target_tokens=set()))

    def test_electrical_token(self):
        self.assertTrue(_infer_balance_excluded({}, target_tokens={"전기"}))

    def test_communication_token(self):
        self.assertTrue(_infer_balance_excluded({}, target_tokens={"정보통신"}))

    def test_fire_token(self):
        self.assertTrue(_infer_balance_excluded({}, target_tokens={"소방"}))

    def test_license_text_fallback_전기(self):
        self.assertTrue(
            _infer_balance_excluded({"license_text": "전기공사업"}, target_tokens=set())
        )

    def test_license_text_통신(self):
        self.assertTrue(
            _infer_balance_excluded({"license_text": "정보통신공사업"}, target_tokens=set())
        )

    def test_no_exclusion(self):
        self.assertFalse(
            _infer_balance_excluded({"license_text": "토목공사업"}, target_tokens={"토목"})
        )

    def test_empty_target(self):
        self.assertFalse(_infer_balance_excluded({}, target_tokens=set()))

    def test_raw_license_key_fallback(self):
        self.assertTrue(
            _infer_balance_excluded(
                {"raw_license_key": "소방시설공사업"}, target_tokens=set()
            )
        )


# ── _matched_axes ────────────────────────────────────────────────────


class MatchedAxesTest(unittest.TestCase):
    def _call(self, **overrides):
        defaults = dict(
            token_match=0.0, same_core=0.0, sales_fit=0.0, price_fit=0.0,
            specialty_fit=0.0, capital_fit=0.0, balance_fit=0.0,
            yearly_fit=0.0, company_match=0.0, balance_excluded=False,
        )
        defaults.update(overrides)
        return _matched_axes(**defaults)

    def test_perfect_match(self):
        matched, weak = self._call(
            token_match=1.0, sales_fit=0.9, price_fit=0.8,
            specialty_fit=0.9, capital_fit=0.9, balance_fit=0.8, company_match=1.0,
        )
        self.assertIn("면허 일치", matched)
        self.assertIn("실적 규모", matched)
        self.assertEqual(weak, [])

    def test_same_core_match(self):
        matched, _ = self._call(same_core=1.0, token_match=0.5)
        self.assertIn("핵심 업종 일치", matched)

    def test_no_license_match(self):
        _, weak = self._call(token_match=0.3, same_core=0.3)
        self.assertIn("면허 축 약함", weak)

    def test_yearly_fit_fallback(self):
        matched, _ = self._call(sales_fit=0.4, yearly_fit=0.85)
        self.assertIn("3개년 실적 흐름", matched)

    def test_balance_excluded_skips_balance(self):
        matched, weak = self._call(
            token_match=1.0, sales_fit=0.8, balance_fit=0.9, balance_excluded=True,
        )
        self.assertNotIn("공제잔액", matched)

    def test_max_4_matched(self):
        matched, _ = self._call(
            token_match=1.0, sales_fit=0.9, price_fit=0.9,
            specialty_fit=0.9, capital_fit=0.9, balance_fit=0.9, company_match=1.0,
        )
        self.assertLessEqual(len(matched), 4)

    def test_price_weak_when_very_low(self):
        _, weak = self._call(token_match=1.0, price_fit=0.10)
        self.assertIn("가격대 차이", weak)


# ── _fit_summary ─────────────────────────────────────────────────────


class FitSummaryTest(unittest.TestCase):
    def test_all_matched_no_mismatch(self):
        result = _fit_summary(["면허 일치", "실적 규모"], [], score=0.9)
        self.assertIn("우선 검토 후보", result)

    def test_matched_with_mismatch(self):
        result = _fit_summary(["면허 일치"], ["가격대 차이"], score=0.7)
        self.assertIn("맞지만", result)

    def test_high_score_no_matched(self):
        result = _fit_summary([], [], score=0.75)
        self.assertIn("유사하지만", result)

    def test_low_score(self):
        result = _fit_summary([], [], score=0.4)
        self.assertIn("보조 검토", result)


# ── _score_candidate ─────────────────────────────────────────────────


class ScoreCandidateTest(unittest.TestCase):
    def _call(self, **overrides):
        defaults = dict(
            similarity=90.0, token_match=1.0, same_core=1.0,
            sales_fit=0.8, price_fit=0.7, specialty_fit=0.7,
            capital_fit=0.6, balance_fit=0.5, yearly_fit=0.6,
            yearly_strength=0.3, company_match=1.0,
            signal_count=0, mismatch_count=0,
            matched_axes=["면허 일치", "실적 규모"],
        )
        defaults.update(overrides)
        return _score_candidate(**defaults)

    def test_high_quality_score(self):
        score = self._call()
        self.assertGreater(score, 0.7)

    def test_token_match_bonus(self):
        base = self._call(token_match=0.5, same_core=0.0)
        boosted = self._call(token_match=1.0, same_core=0.0)
        self.assertGreater(boosted, base)

    def test_same_core_bonus(self):
        base = self._call(token_match=0.5, same_core=0.0)
        boosted = self._call(token_match=0.5, same_core=1.0)
        self.assertGreater(boosted, base)

    def test_yearly_penalty(self):
        base = self._call(yearly_strength=0.7, yearly_fit=0.6)
        penalized = self._call(yearly_strength=0.7, yearly_fit=0.3)
        self.assertGreater(base, penalized)

    def test_mismatch_penalty(self):
        base = self._call(signal_count=3, mismatch_count=0)
        penalized = self._call(signal_count=3, mismatch_count=3)
        self.assertGreater(base, penalized)

    def test_score_clamped_0_1(self):
        low = self._call(similarity=10.0, token_match=0.0, sales_fit=0.0,
                         price_fit=0.0, specialty_fit=0.0, capital_fit=0.0,
                         balance_fit=0.0, yearly_fit=0.0, company_match=0.0,
                         signal_count=5, mismatch_count=5, matched_axes=[])
        self.assertGreaterEqual(low, 0.0)
        self.assertLessEqual(low, 1.0)


# ── _recommendation_label ────────────────────────────────────────────


class RecommendationLabelTest(unittest.TestCase):
    def test_high_score_returns_priority(self):
        bucket, label, tier = _recommendation_label(0.85)
        self.assertEqual(bucket, 2)
        self.assertEqual(label, "우선 검토")
        self.assertEqual(tier, "high")

    def test_medium_score_returns_similar(self):
        bucket, label, tier = _recommendation_label(0.70)
        self.assertEqual(bucket, 1)
        self.assertEqual(label, "조건 유사")
        self.assertEqual(tier, "medium")

    def test_low_score_returns_assist(self):
        bucket, label, tier = _recommendation_label(0.40)
        self.assertEqual(bucket, 0)
        self.assertEqual(label, "보조 검토")
        self.assertEqual(tier, "assist")

    def test_borderline_token_match_promotion(self):
        bucket, label, tier = _recommendation_label(
            0.79, token_match=1.0,
            matched_axes=["면허 일치", "실적 규모", "가격대"],
            mismatch_flags=[],
        )
        self.assertEqual(tier, "high")

    def test_borderline_same_core_promotion(self):
        bucket, label, tier = _recommendation_label(
            0.77, same_core=1.0,
            matched_axes=["핵심 업종 일치", "실적 규모", "가격대", "시평 규모"],
            mismatch_flags=[],
        )
        self.assertEqual(tier, "high")


# ── _build_recommendation_meta ───────────────────────────────────────


class BuildRecommendationMetaTest(unittest.TestCase):
    def test_empty_rows(self):
        meta = _build_recommendation_meta([])
        self.assertEqual(meta["recommended_count"], 0)
        self.assertEqual(meta["precision_mode"], "none")

    def test_strict_mode(self):
        rows = [
            {"precision_tier": "high", "recommendation_score": 85.0,
             "recommendation_price_band": "2_to_3",
             "recommendation_focus_signature": "면허|실적"},
            {"precision_tier": "high", "recommendation_score": 80.0,
             "recommendation_price_band": "3_to_4",
             "recommendation_focus_signature": "면허|가격"},
        ]
        meta = _build_recommendation_meta(rows)
        self.assertEqual(meta["precision_mode"], "strict")
        self.assertEqual(meta["strict_match_count"], 2)

    def test_assist_mode(self):
        rows = [
            {"precision_tier": "assist", "recommendation_score": 50.0,
             "recommendation_price_band": "1_to_2",
             "recommendation_focus_signature": "가격"},
        ]
        meta = _build_recommendation_meta(rows)
        self.assertEqual(meta["precision_mode"], "assist")
        self.assertEqual(meta["assist_count"], 1)

    def test_diversity_metrics(self):
        rows = [
            {"precision_tier": "high", "recommendation_score": 80.0,
             "recommendation_price_band": "2_to_3",
             "recommendation_focus_signature": "면허|실적"},
            {"precision_tier": "medium", "recommendation_score": 70.0,
             "recommendation_price_band": "3_to_4",
             "recommendation_focus_signature": "가격|시평"},
        ]
        meta = _build_recommendation_meta(rows)
        self.assertEqual(meta["unique_price_band_count"], 2)
        self.assertEqual(meta["unique_focus_signature_count"], 2)
        self.assertEqual(meta["unique_precision_tier_count"], 2)


# ── _recommendation_price_band ───────────────────────────────────────


class RecommendationPriceBandTest(unittest.TestCase):
    def setUp(self):
        self.ops = _make_ops()

    def test_under_1(self):
        self.assertEqual(_recommendation_price_band({"price_eok": 0.5}, ops=self.ops), "under_1")

    def test_1_to_2(self):
        self.assertEqual(_recommendation_price_band({"price_eok": 1.5}, ops=self.ops), "1_to_2")

    def test_2_to_3(self):
        self.assertEqual(_recommendation_price_band({"price_eok": 2.5}, ops=self.ops), "2_to_3")

    def test_6_plus(self):
        self.assertEqual(_recommendation_price_band({"price_eok": 10.0}, ops=self.ops), "6_plus")

    def test_unknown_when_no_price(self):
        self.assertEqual(_recommendation_price_band({}, ops=self.ops), "unknown")

    def test_display_range_center(self):
        row = {"display_low_eok": 3.0, "display_high_eok": 5.0}
        # center = (3+5)/2 = 4.0 → 4.0 is NOT < 4.0, so "4_to_6"
        self.assertEqual(_recommendation_price_band(row, ops=self.ops), "4_to_6")


# ── _recommendation_focus_signature ──────────────────────────────────


class RecommendationFocusSignatureTest(unittest.TestCase):
    def test_with_matched_and_mismatch(self):
        row = {
            "matched_axes": ["면허 일치", "실적 규모", "가격대"],
            "mismatch_flags": ["시평 차이"],
            "recommendation_price_band": "2_to_3",
            "recommendation_focus": "면허 일치, 실적 규모",
        }
        sig = _recommendation_focus_signature(row)
        self.assertIn("면허 일치", sig)
        self.assertIn("실적 규모", sig)
        self.assertIn("주의:시평 차이", sig)

    def test_no_matched_uses_focus(self):
        row = {"matched_axes": [], "mismatch_flags": [], "recommendation_focus": "가격대·면허 인접"}
        sig = _recommendation_focus_signature(row)
        self.assertIn("가격대·면허 인접", sig)

    def test_empty_row(self):
        sig = _recommendation_focus_signature({})
        self.assertEqual(sig, "")


# ── _compare_recommendation_entries ──────────────────────────────────


class CompareRecommendationEntriesTest(unittest.TestCase):
    def _entry(self, bucket=1, band=7, score=0.75, sim=90.0, num=7000.0, row=None):
        return (bucket, band, score, sim, num, row or {})

    def test_higher_bucket_wins(self):
        result = _compare_recommendation_entries(self._entry(bucket=2), self._entry(bucket=1))
        self.assertEqual(result, -1)

    def test_same_bucket_higher_score_wins(self):
        result = _compare_recommendation_entries(
            self._entry(score=0.80), self._entry(score=0.70),
        )
        self.assertEqual(result, -1)

    def test_same_score_higher_band_wins(self):
        result = _compare_recommendation_entries(
            self._entry(band=8, score=0.75), self._entry(band=7, score=0.75),
        )
        self.assertEqual(result, -1)

    def test_equal_entries(self):
        e = self._entry()
        result = _compare_recommendation_entries(e, e)
        self.assertEqual(result, 0)


# ── _range_pair_from_record ──────────────────────────────────────────


class RangePairFromRecordTest(unittest.TestCase):
    def test_explicit_low_high(self):
        rec = {"display_low_eok": 2.0, "display_high_eok": 5.0}
        low, high = _range_pair_from_record(
            rec, to_float=_stub_to_float, derive_display_range_eok=_stub_derive_display_range,
        )
        self.assertEqual(low, 2.0)
        self.assertEqual(high, 5.0)

    def test_swap_when_inverted(self):
        rec = {"display_low_eok": 8.0, "display_high_eok": 3.0}
        low, high = _range_pair_from_record(
            rec, to_float=_stub_to_float, derive_display_range_eok=_stub_derive_display_range,
        )
        self.assertEqual(low, 3.0)
        self.assertEqual(high, 8.0)

    def test_fallback_to_current_price(self):
        rec = {"current_price_eok": 4.0}
        low, high = _range_pair_from_record(
            rec, to_float=_stub_to_float, derive_display_range_eok=_stub_derive_display_range,
        )
        self.assertEqual(low, 4.0)
        self.assertEqual(high, 4.0)

    def test_empty_record_returns_none_pair(self):
        low, high = _range_pair_from_record(
            {}, to_float=_stub_to_float, derive_display_range_eok=_stub_derive_display_range,
        )
        self.assertIsNone(low)
        self.assertIsNone(high)

    def test_only_low_fills_high(self):
        rec = {"display_low_eok": 3.0}
        low, high = _range_pair_from_record(
            rec, to_float=_stub_to_float, derive_display_range_eok=_stub_derive_display_range,
        )
        self.assertEqual(low, 3.0)
        self.assertEqual(high, 3.0)


# ── _price_overlap_score ─────────────────────────────────────────────


class PriceOverlapScoreTest(unittest.TestCase):
    def setUp(self):
        self.ops = _make_ops()

    def test_full_overlap(self):
        a = {"display_low_eok": 2.0, "display_high_eok": 4.0}
        b = {"display_low_eok": 2.0, "display_high_eok": 4.0}
        self.assertAlmostEqual(_price_overlap_score(a, b, ops=self.ops), 1.0)

    def test_partial_overlap(self):
        a = {"display_low_eok": 1.0, "display_high_eok": 3.0}
        b = {"display_low_eok": 2.0, "display_high_eok": 4.0}
        score = _price_overlap_score(a, b, ops=self.ops)
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)

    def test_no_overlap_returns_relative_closeness(self):
        a = {"display_low_eok": 1.0, "display_high_eok": 2.0}
        b = {"display_low_eok": 8.0, "display_high_eok": 10.0}
        score = _price_overlap_score(a, b, ops=self.ops)
        self.assertGreaterEqual(score, 0.0)
        self.assertLess(score, 0.5)

    def test_none_values_return_zero(self):
        self.assertEqual(_price_overlap_score({}, {}, ops=self.ops), 0.0)


# ── _yearly_fit_score ────────────────────────────────────────────────


class YearlyFitScoreTest(unittest.TestCase):
    def test_zero_strength_returns_zero(self):
        ops = _make_ops(yearly_shape_similarity=lambda t, r: {"shape": 0.8, "tail": 0.5, "trend": 0.6, "strength": 0.0})
        fit, strength = _yearly_fit_score({}, {}, ops=ops)
        self.assertEqual(fit, 0.0)
        self.assertEqual(strength, 0.0)

    def test_positive_strength(self):
        ops = _make_ops(yearly_shape_similarity=lambda t, r: {"shape": 0.8, "tail": 0.6, "trend": 0.7, "strength": 0.9})
        fit, strength = _yearly_fit_score({}, {}, ops=ops)
        self.assertGreater(fit, 0.0)
        self.assertLessEqual(fit, 1.0)
        self.assertEqual(strength, 0.9)


# ── _rerank_with_diversity ───────────────────────────────────────────


class RerankWithDiversityTest(unittest.TestCase):
    def _entry(self, bucket, band, score, sig="", pb="", tier="medium", label="조건 유사"):
        return (bucket, band, score, 90.0, 7000.0, {
            "recommendation_focus_signature": sig,
            "recommendation_price_band": pb,
            "precision_tier": tier,
            "recommendation_label": label,
        })

    def test_small_list_not_reranked(self):
        items = [self._entry(2, 7, 0.9), self._entry(1, 6, 0.7)]
        result = _rerank_with_diversity(items, limit=4)
        self.assertEqual(len(result), 2)

    def test_diversity_penalty_spreads_focus_signatures(self):
        items = [
            self._entry(2, 7, 0.90, sig="A", pb="2_to_3"),
            self._entry(1, 7, 0.85, sig="A", pb="2_to_3"),
            self._entry(1, 6, 0.84, sig="B", pb="3_to_4"),
            self._entry(1, 5, 0.83, sig="C", pb="4_to_6"),
        ]
        result = _rerank_with_diversity(items, limit=3)
        sigs = [entry[5]["recommendation_focus_signature"] for entry in result]
        # First item is always locked; diversity should prefer different sigs
        self.assertEqual(sigs[0], "A")
        # Among remaining, B or C should appear before the duplicate A
        self.assertIn("B", sigs[1:])

    def test_limit_respected(self):
        items = [self._entry(2, i, 0.9 - i * 0.01) for i in range(10)]
        result = _rerank_with_diversity(items, limit=4)
        self.assertEqual(len(result), 4)


# ── _build_recommendation_reasons ────────────────────────────────────


class BuildRecommendationReasonsTest(unittest.TestCase):
    def _call(self, **overrides):
        defaults = dict(
            token_match=0.0, same_core=0.0, sales_fit=0.0, price_fit=0.0,
            specialty_fit=0.0, capital_fit=0.0, balance_fit=0.0,
            yearly_fit=0.0, company_match=0.0, balance_excluded=False,
        )
        defaults.update(overrides)
        return _build_recommendation_reasons(**defaults)

    def test_license_match_reason(self):
        reasons = self._call(token_match=1.0)
        self.assertTrue(any("면허" in r for r in reasons))

    def test_core_match_reason(self):
        reasons = self._call(same_core=1.0)
        self.assertTrue(any("핵심 업종" in r for r in reasons))

    def test_sales_reason(self):
        reasons = self._call(token_match=1.0, sales_fit=0.8)
        self.assertTrue(any("실적" in r for r in reasons))

    def test_max_3_reasons(self):
        reasons = self._call(
            token_match=1.0, sales_fit=0.9, price_fit=0.9,
            specialty_fit=0.9, capital_fit=0.9, company_match=1.0,
        )
        self.assertLessEqual(len(reasons), 3)

    def test_fallback_when_no_match(self):
        reasons = self._call()
        self.assertTrue(len(reasons) >= 1)

    def test_balance_excluded_no_balance_reason(self):
        reasons = self._call(balance_fit=0.9, balance_excluded=True)
        for reason in reasons:
            self.assertNotIn("공제조합", reason)


# ── build_recommendation_bundle (integration) ────────────────────────


class BuildRecommendationBundleTest(unittest.TestCase):
    def setUp(self):
        self.ops = _make_ops()

    def test_empty_rows(self):
        result = build_recommendation_bundle(
            target={}, rows=[], center=3.0, low=2.0, high=4.0, ops=self.ops,
        )
        self.assertEqual(result["recommended_listings"], [])
        self.assertEqual(result["recommendation_meta"]["recommended_count"], 0)

    def test_basic_recommendation(self):
        target = {"license_tokens": {"토목"}, "company_type": "법인"}
        rec = {
            "number": "7001", "uid": "93001", "license_tokens": {"토목"},
            "license_text": "토목", "company_type": "법인",
            "current_price_eok": 3.0, "display_low_eok": 2.5, "display_high_eok": 3.5,
        }
        result = build_recommendation_bundle(
            target=target, rows=[(92.0, rec)], center=3.0, low=2.5, high=3.5, ops=self.ops,
        )
        listings = result["recommended_listings"]
        # May or may not be recommended depending on threshold,
        # but meta should always be present
        self.assertIn("recommendation_meta", result)

    def test_deduplication(self):
        target = {"license_tokens": {"토목"}, "company_type": "법인"}
        rec = {
            "number": "7001", "uid": "93001", "license_tokens": {"토목"},
            "license_text": "토목", "company_type": "법인",
            "current_price_eok": 3.0, "display_low_eok": 2.5, "display_high_eok": 3.5,
        }
        result = build_recommendation_bundle(
            target=target, rows=[(95.0, rec), (95.0, rec)],
            center=3.0, low=2.5, high=3.5, ops=self.ops,
        )
        # Same record twice → deduplicated
        listings = result["recommended_listings"]
        self.assertLessEqual(len(listings), 1)

    def test_url_generation(self):
        target = {"license_tokens": {"토목"}}
        rec = {
            "number": "7768", "uid": "95001", "license_tokens": {"토목"},
            "license_text": "토목", "current_price_eok": 3.0,
            "display_low_eok": 2.5, "display_high_eok": 3.5,
        }
        result = build_recommendation_bundle(
            target=target, rows=[(95.0, rec)],
            center=3.0, low=2.5, high=3.5, ops=self.ops,
        )
        for listing in result["recommended_listings"]:
            self.assertTrue(listing["url"].startswith("https://seoulmna.kr/mna/"))


if __name__ == "__main__":
    unittest.main()
