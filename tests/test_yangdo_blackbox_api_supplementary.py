"""Supplementary unit tests for yangdo_blackbox_api.py.

Covers: _apply_special_sector_publication_guard, _prioritize_display_neighbors.
"""

import unittest

import yangdo_blackbox_api as api


# ===================================================================
# _apply_special_sector_publication_guard
# ===================================================================
class ApplySpecialSectorPublicationGuardTest(unittest.TestCase):
    def _target(self, license_text="정보통신공사업"):
        return {"license_tokens": [license_text], "license_text": license_text}

    def _result(self, **overrides):
        base = {
            "publication_mode": "full",
            "estimate_center_eok": 3.0,
            "estimate_low_eok": 2.0,
            "estimate_high_eok": 4.0,
            "confidence_percent": 92,
            "risk_notes": [],
        }
        base.update(overrides)
        return base

    def test_non_telecom_unchanged(self):
        target = {"license_tokens": ["전기공사업"], "license_text": "전기공사업"}
        result = self._result()
        out = api._apply_special_sector_publication_guard(result, target)
        self.assertEqual(out["publication_mode"], "full")

    def test_not_full_mode_unchanged(self):
        result = self._result(publication_mode="range_only")
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "range_only")

    def test_high_confidence_wide_range_unchanged(self):
        """Confidence 92%, center=3, range 2-4 (span_ratio=0.67 < 0.70) → pass."""
        result = self._result()
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "full")

    def test_too_wide_range_downgrades(self):
        """span_ratio > 0.70 → range_only."""
        result = self._result(
            estimate_center_eok=1.0,
            estimate_low_eok=0.5,
            estimate_high_eok=1.8,  # span = 1.3, ratio = 1.3 > 0.70
            confidence_percent=95,
        )
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "range_only")
        self.assertIn("범위 폭이 넓음", out["publication_reason"])

    def test_too_small_center_downgrades(self):
        """center < 0.25 → range_only."""
        result = self._result(
            estimate_center_eok=0.2,
            estimate_low_eok=0.15,
            estimate_high_eok=0.25,
            confidence_percent=95,
        )
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "range_only")
        self.assertIn("절대 금액 구간이 작음", out["publication_reason"])

    def test_low_confidence_downgrades(self):
        """confidence < 90 → range_only."""
        result = self._result(confidence_percent=85)
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "range_only")
        self.assertIn("신뢰도 기준 미달", out["publication_reason"])

    def test_boundary_confidence_90_passes(self):
        """confidence == 90 is NOT < 90, so passes."""
        result = self._result(confidence_percent=90)
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "full")

    def test_boundary_span_070_passes(self):
        """span_ratio == 0.70 is NOT > 0.70, so passes."""
        result = self._result(
            estimate_center_eok=10.0,
            estimate_low_eok=6.5,
            estimate_high_eok=13.5,  # span=7, ratio=0.70 exactly
            confidence_percent=95,
        )
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "full")

    def test_multiple_triggers(self):
        """All three triggers → combined reason."""
        result = self._result(
            estimate_center_eok=0.1,
            estimate_low_eok=0.01,
            estimate_high_eok=0.5,
            confidence_percent=50,
        )
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "range_only")
        self.assertIn("범위 폭이 넓음", out["publication_reason"])
        self.assertIn("절대 금액 구간이 작음", out["publication_reason"])
        self.assertIn("신뢰도 기준 미달", out["publication_reason"])

    def test_risk_notes_appended_not_duplicated(self):
        """Reason appended to risk_notes, no duplicates."""
        result = self._result(confidence_percent=80)
        out = api._apply_special_sector_publication_guard(result, self._target())
        reason = out["publication_reason"]
        self.assertIn(reason, out["risk_notes"])
        # Call again — should not duplicate
        out2 = api._apply_special_sector_publication_guard(out, self._target())
        self.assertEqual(out2["risk_notes"].count(reason), 1)

    def test_none_result_handled(self):
        """None result → empty dict output."""
        out = api._apply_special_sector_publication_guard(None, self._target())
        self.assertIsInstance(out, dict)

    def test_does_not_mutate_input(self):
        """Returns new dict, doesn't mutate input."""
        result = self._result(confidence_percent=80)
        original_mode = result["publication_mode"]
        api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(result["publication_mode"], original_mode)


# ===================================================================
# _prioritize_display_neighbors
# ===================================================================
class PrioritizeDisplayNeighborsTest(unittest.TestCase):
    def _target(self, **overrides):
        base = {"sales3_eok": 5.0, "sales5_eok": 3.0}
        base.update(overrides)
        return base

    def _rec(self, number=100, sales3=4.0, sales5=2.0, **extra):
        r = {"number": number, "sales3_eok": sales3, "sales5_eok": sales5}
        r.update(extra)
        return r

    def test_empty_rows(self):
        self.assertEqual(api._prioritize_display_neighbors({}, []), [])

    def test_single_row(self):
        rows = [(90.0, self._rec())]
        result = api._prioritize_display_neighbors(self._target(), rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 90.0)

    def test_higher_similarity_preferred(self):
        """Higher similarity score ranks first, all else equal."""
        rows = [
            (80.0, self._rec(number=1)),
            (95.0, self._rec(number=2)),
        ]
        result = api._prioritize_display_neighbors(self._target(), rows)
        self.assertEqual(result[0][1]["number"], 2)

    def test_no_sales_target(self):
        """Target without sales data doesn't crash."""
        target = {"sales3_eok": 0, "sales5_eok": 0}
        rows = [(90.0, self._rec())]
        result = api._prioritize_display_neighbors(target, rows)
        self.assertEqual(len(result), 1)

    def test_preserves_all_rows(self):
        rows = [(90.0, self._rec(number=i)) for i in range(5)]
        result = api._prioritize_display_neighbors(self._target(), rows)
        self.assertEqual(len(result), 5)

    def test_non_dict_rec_handled(self):
        """Non-dict record doesn't crash."""
        rows = [(90.0, None), (85.0, "invalid")]
        result = api._prioritize_display_neighbors(self._target(), rows)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
