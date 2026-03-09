"""Unit tests for core_engine.yangdo_duplicate_cluster.

Covers pure helper functions and the collapse_duplicate_neighbors pipeline.
"""
import unittest

from core_engine.yangdo_duplicate_cluster import (
    _closeness,
    _completeness,
    _containment,
    _duplicate_affinity,
    _extreme_mismatch_count,
    _is_same_cluster,
    _jaccard,
    _location_match,
    _price_overlap_score,
    _range_pair,
    _ratio,
    _same_text,
    _text_key,
    _to_float,
    _tokens,
    collapse_duplicate_neighbors,
)


# ── _to_float ────────────────────────────────────────────────────────


class ToFloatTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_to_float(3.14), 3.14)

    def test_string(self):
        self.assertEqual(_to_float("5.0"), 5.0)

    def test_none(self):
        self.assertIsNone(_to_float(None))

    def test_nan(self):
        self.assertIsNone(_to_float(float("nan")))

    def test_garbage(self):
        self.assertIsNone(_to_float("abc"))


# ── _tokens ──────────────────────────────────────────────────────────


class TokensTest(unittest.TestCase):
    def test_set_input(self):
        self.assertEqual(_tokens({"license_tokens": {"토목", "건축"}}), {"토목", "건축"})

    def test_list_input(self):
        self.assertEqual(_tokens({"license_tokens": ["토목", "건축"]}), {"토목", "건축"})

    def test_fallback_to_tokens_key(self):
        self.assertEqual(_tokens({"tokens": {"전기"}}), {"전기"})

    def test_empty_record(self):
        self.assertEqual(_tokens({}), set())

    def test_whitespace_stripped(self):
        self.assertEqual(_tokens({"license_tokens": [" 토목 ", ""]}), {"토목"})


# ── _jaccard ─────────────────────────────────────────────────────────


class JaccardTest(unittest.TestCase):
    def test_identical(self):
        self.assertAlmostEqual(_jaccard({"a", "b"}, {"a", "b"}), 1.0)

    def test_disjoint(self):
        self.assertAlmostEqual(_jaccard({"a"}, {"b"}), 0.0)

    def test_partial_overlap(self):
        self.assertAlmostEqual(_jaccard({"a", "b", "c"}, {"b", "c", "d"}), 0.5)

    def test_empty_sets(self):
        self.assertAlmostEqual(_jaccard(set(), {"a"}), 0.0)


# ── _containment ─────────────────────────────────────────────────────


class ContainmentTest(unittest.TestCase):
    def test_subset(self):
        self.assertAlmostEqual(_containment({"a"}, {"a", "b", "c"}), 1.0)

    def test_disjoint(self):
        self.assertAlmostEqual(_containment({"a"}, {"b"}), 0.0)

    def test_empty(self):
        self.assertAlmostEqual(_containment(set(), {"a"}), 0.0)


# ── _closeness ───────────────────────────────────────────────────────


class ClosenessTest(unittest.TestCase):
    def test_same_value(self):
        self.assertAlmostEqual(_closeness(5, 5), 1.0)

    def test_different_values(self):
        score = _closeness(10, 5)
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)

    def test_none_returns_zero(self):
        self.assertAlmostEqual(_closeness(None, 5), 0.0)

    def test_clamped_0_1(self):
        score = _closeness(100, 1)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


# ── _ratio ───────────────────────────────────────────────────────────


class RatioTest(unittest.TestCase):
    def test_equal(self):
        self.assertAlmostEqual(_ratio(5, 5), 1.0)

    def test_double(self):
        self.assertAlmostEqual(_ratio(10, 5), 2.0)

    def test_none_input(self):
        self.assertIsNone(_ratio(None, 5))

    def test_zero_input(self):
        self.assertIsNone(_ratio(0, 5))


# ── _range_pair ──────────────────────────────────────────────────────


class RangePairTest(unittest.TestCase):
    def test_explicit_range(self):
        self.assertEqual(_range_pair({"display_low_eok": 2.0, "display_high_eok": 5.0}), (2.0, 5.0))

    def test_swaps_inverted(self):
        self.assertEqual(_range_pair({"display_low_eok": 8.0, "display_high_eok": 3.0}), (3.0, 8.0))

    def test_fallback_to_price(self):
        self.assertEqual(_range_pair({"current_price_eok": 4.0}), (4.0, 4.0))

    def test_empty_returns_none_pair(self):
        self.assertEqual(_range_pair({}), (None, None))


# ── _text_key ────────────────────────────────────────────────────────


class TextKeyTest(unittest.TestCase):
    def test_normalizes(self):
        self.assertEqual(_text_key("  서울  강남구  "), "서울 강남구")

    def test_lowercase(self):
        self.assertEqual(_text_key("ABC"), "abc")

    def test_none(self):
        self.assertEqual(_text_key(None), "")


# ── _location_match ──────────────────────────────────────────────────


class LocationMatchTest(unittest.TestCase):
    def test_exact_match(self):
        self.assertAlmostEqual(_location_match({"location": "서울"}, {"location": "서울"}), 1.0)

    def test_partial_match(self):
        self.assertAlmostEqual(_location_match({"location": "서울 강남"}, {"location": "서울 종로"}), 0.65)

    def test_no_match(self):
        self.assertAlmostEqual(_location_match({"location": "서울"}, {"location": "부산"}), 0.0)

    def test_empty(self):
        self.assertAlmostEqual(_location_match({}, {}), 0.0)


# ── _same_text ───────────────────────────────────────────────────────


class SameTextTest(unittest.TestCase):
    def test_match(self):
        self.assertAlmostEqual(_same_text("법인", "법인"), 1.0)

    def test_no_match(self):
        self.assertAlmostEqual(_same_text("법인", "개인"), 0.0)

    def test_empty(self):
        self.assertAlmostEqual(_same_text("", ""), 0.0)


# ── _extreme_mismatch_count ──────────────────────────────────────────


class ExtremeMismatchCountTest(unittest.TestCase):
    def test_no_mismatch(self):
        a = {"specialty": 100, "sales3_eok": 5, "capital_eok": 3}
        b = {"specialty": 100, "sales3_eok": 5, "capital_eok": 3}
        self.assertEqual(_extreme_mismatch_count(a, b), 0)

    def test_extreme_mismatch(self):
        a = {"specialty": 100, "sales3_eok": 50, "capital_eok": 30}
        b = {"specialty": 1, "sales3_eok": 1, "capital_eok": 1}
        self.assertGreaterEqual(_extreme_mismatch_count(a, b), 2)


# ── _completeness ────────────────────────────────────────────────────


class CompletenessTest(unittest.TestCase):
    def test_full_record(self):
        rec = {
            "specialty": 100, "sales3_eok": 5, "capital_eok": 3,
            "license_year": 2020, "display_low_eok": 2, "display_high_eok": 4,
            "claim_price_eok": 3, "company_type": "법인",
            "location": "서울", "association": "건설공제",
        }
        self.assertEqual(_completeness(rec), 10)

    def test_empty_record(self):
        self.assertEqual(_completeness({}), 0)

    def test_partial_record(self):
        rec = {"specialty": 100, "company_type": "법인"}
        self.assertEqual(_completeness(rec), 2)


# ── _duplicate_affinity ──────────────────────────────────────────────


class DuplicateAffinityTest(unittest.TestCase):
    def test_identical_records(self):
        rec = {
            "license_tokens": {"토목"},
            "specialty": 100, "sales3_eok": 5, "capital_eok": 3,
            "company_type": "법인", "location": "서울",
        }
        score, secondary = _duplicate_affinity(rec, rec)
        self.assertGreater(score, 0.5)

    def test_disjoint_tokens_returns_zero(self):
        a = {"license_tokens": {"토목"}}
        b = {"license_tokens": {"전기"}}
        score, _ = _duplicate_affinity(a, b)
        self.assertAlmostEqual(score, 0.0)

    def test_extreme_mismatch_returns_zero(self):
        a = {"license_tokens": {"토목"}, "specialty": 100, "sales3_eok": 50, "capital_eok": 30}
        b = {"license_tokens": {"토목"}, "specialty": 1, "sales3_eok": 1, "capital_eok": 1}
        score, _ = _duplicate_affinity(a, b)
        self.assertAlmostEqual(score, 0.0)


# ── _is_same_cluster ────────────────────────────────────────────────


class IsSameClusterTest(unittest.TestCase):
    def test_identical_records(self):
        rec = {
            "license_tokens": {"토목"},
            "specialty": 100, "sales3_eok": 5, "capital_eok": 3,
            "company_type": "법인", "location": "서울",
            "current_price_eok": 3.0,
        }
        self.assertTrue(_is_same_cluster(rec, rec))

    def test_different_records(self):
        a = {"license_tokens": {"토목"}, "specialty": 100, "sales3_eok": 50, "capital_eok": 30}
        b = {"license_tokens": {"전기"}, "specialty": 10, "sales3_eok": 1, "capital_eok": 1}
        self.assertFalse(_is_same_cluster(a, b))


# ── collapse_duplicate_neighbors ─────────────────────────────────────


class CollapseDuplicateNeighborsTest(unittest.TestCase):
    def test_empty(self):
        result = collapse_duplicate_neighbors([])
        self.assertEqual(result["raw_neighbor_count"], 0)
        self.assertFalse(result["duplicate_cluster_adjusted"])

    def test_single_item(self):
        result = collapse_duplicate_neighbors([(0.95, {"license_tokens": {"토목"}, "uid": "1"})])
        self.assertEqual(result["raw_neighbor_count"], 1)
        self.assertEqual(result["effective_cluster_count"], 1)

    def test_duplicates_collapsed(self):
        rec = {
            "license_tokens": {"토목"},
            "specialty": 100, "sales3_eok": 5, "capital_eok": 3,
            "company_type": "법인", "location": "서울",
            "current_price_eok": 3.0, "uid": "u1",
        }
        rec2 = dict(rec)
        rec2["uid"] = "u2"
        result = collapse_duplicate_neighbors([(0.95, rec), (0.94, rec2)])
        self.assertEqual(result["raw_neighbor_count"], 2)
        # These should be in the same cluster
        self.assertTrue(result["duplicate_cluster_adjusted"])
        self.assertEqual(result["effective_cluster_count"], 1)

    def test_distinct_kept(self):
        a = {"license_tokens": {"토목"}, "specialty": 100, "uid": "a1"}
        b = {"license_tokens": {"전기"}, "specialty": 50, "uid": "b1"}
        result = collapse_duplicate_neighbors([(0.9, a), (0.8, b)])
        self.assertEqual(result["effective_cluster_count"], 2)
        self.assertFalse(result["duplicate_cluster_adjusted"])


if __name__ == "__main__":
    unittest.main()
