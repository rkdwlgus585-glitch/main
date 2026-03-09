"""Tests for _PENDING_CRITERIA_TEMPLATES expansion and _synthesize_typed_criteria_from_pending.

Verifies that the 9-category template mapping (including core_requirement,
guarantee, operations, and the 'other' fallback) correctly synthesizes
typed_criteria from pending_criteria_lines.
"""

import unittest

import permit_diagnosis_calculator as pdc


class PendingCriteriaTemplatesTest(unittest.TestCase):
    """Verify _PENDING_CRITERIA_TEMPLATES has all required categories."""

    def test_templates_contain_original_six_categories(self):
        templates = pdc._PENDING_CRITERIA_TEMPLATES
        for cat in ("office", "facility_misc", "personnel_misc", "insurance", "document", "environment_safety"):
            self.assertIn(cat, templates, f"Missing original category: {cat}")

    def test_templates_contain_new_three_categories(self):
        templates = pdc._PENDING_CRITERIA_TEMPLATES
        for cat in ("core_requirement", "guarantee", "operations"):
            self.assertIn(cat, templates, f"Missing new category: {cat}")

    def test_each_template_has_required_keys(self):
        required_keys = {"criterion_id", "category", "label", "input_key", "value_type", "operator", "required_value", "blocking", "evidence_types"}
        for cat, template in pdc._PENDING_CRITERIA_TEMPLATES.items():
            for key in required_keys:
                self.assertIn(key, template, f"Template '{cat}' missing key: {key}")

    def test_guarantee_uses_guarantee_secured_input_key(self):
        """guarantee.secured.auto should map to guarantee_secured (JS sends both guarantee_secured and insurance_secured)."""
        tmpl = pdc._PENDING_CRITERIA_TEMPLATES["guarantee"]
        self.assertEqual(tmpl["input_key"], "guarantee_secured")

    def test_core_requirement_maps_to_facility_secured(self):
        """core_requirement is a facility variant, should use facility_secured."""
        tmpl = pdc._PENDING_CRITERIA_TEMPLATES["core_requirement"]
        self.assertEqual(tmpl["input_key"], "facility_secured")

    def test_operations_maps_to_facility_secured(self):
        """operations is a facility variant, should use facility_secured."""
        tmpl = pdc._PENDING_CRITERIA_TEMPLATES["operations"]
        self.assertEqual(tmpl["input_key"], "facility_secured")


class SynthesizeTypedCriteriaTest(unittest.TestCase):
    """Verify _synthesize_typed_criteria_from_pending handles all categories."""

    def test_synthesize_from_empty_pending_returns_empty(self):
        result = pdc._synthesize_typed_criteria_from_pending([])
        self.assertEqual(result, [])

    def test_synthesize_from_none_returns_empty(self):
        result = pdc._synthesize_typed_criteria_from_pending(None)
        self.assertEqual(result, [])

    def test_synthesize_office_category(self):
        pending = [{"category": "office", "text": "사무실 필요"}]
        result = pdc._synthesize_typed_criteria_from_pending(pending)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["criterion_id"], "office.secured.auto")
        self.assertEqual(result[0]["input_key"], "office_secured")
        self.assertTrue(result[0]["blocking"])

    def test_synthesize_core_requirement_category(self):
        pending = [{"category": "core_requirement", "text": "자본금 5억"}]
        result = pdc._synthesize_typed_criteria_from_pending(pending)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["criterion_id"], "facility.secured.auto")
        self.assertEqual(result[0]["input_key"], "facility_secured")

    def test_synthesize_guarantee_category(self):
        pending = [{"category": "guarantee", "text": "보증금 1000만원"}]
        result = pdc._synthesize_typed_criteria_from_pending(pending)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["criterion_id"], "guarantee.secured.auto")
        self.assertEqual(result[0]["input_key"], "guarantee_secured")

    def test_synthesize_operations_category(self):
        pending = [{"category": "operations", "text": "운영 계획서 필요"}]
        result = pdc._synthesize_typed_criteria_from_pending(pending)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["criterion_id"], "facility.secured.auto")

    def test_synthesize_other_category_falls_back_to_facility_misc(self):
        """'other' category should fallback to facility_misc template."""
        pending = [{"category": "other", "text": "기타 시설 요건"}]
        result = pdc._synthesize_typed_criteria_from_pending(pending)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["criterion_id"], "facility.secured.auto")
        self.assertEqual(result[0]["input_key"], "facility_secured")

    def test_synthesize_unknown_category_skipped(self):
        pending = [{"category": "unknown_xyz", "text": "something"}]
        result = pdc._synthesize_typed_criteria_from_pending(pending)
        self.assertEqual(result, [])

    def test_synthesize_deduplicates_by_criterion_id(self):
        """Multiple pending lines mapping to same criterion_id should be deduplicated."""
        pending = [
            {"category": "facility_misc", "text": "시설 A"},
            {"category": "core_requirement", "text": "시설 B"},
            {"category": "operations", "text": "시설 C"},
        ]
        result = pdc._synthesize_typed_criteria_from_pending(pending)
        # All three map to facility.secured.auto → should be 1
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["criterion_id"], "facility.secured.auto")

    def test_synthesize_multiple_distinct_categories(self):
        pending = [
            {"category": "office", "text": "사무실"},
            {"category": "facility_misc", "text": "장비"},
            {"category": "environment_safety", "text": "안전"},
            {"category": "document", "text": "서류"},
        ]
        result = pdc._synthesize_typed_criteria_from_pending(pending)
        ids = {r["criterion_id"] for r in result}
        self.assertIn("office.secured.auto", ids)
        self.assertIn("facility.secured.auto", ids)
        self.assertIn("safety.secured.auto", ids)
        self.assertIn("document.ready.auto", ids)
        self.assertEqual(len(result), 4)


class NormalizeKeyRegexTest(unittest.TestCase):
    """Verify _RE_NORMALIZE_KEY compiled regex works correctly."""

    def test_normalize_key_strips_whitespace_and_special_chars(self):
        self.assertEqual(pdc._normalize_key("전기 공사업(종합)"), "전기공사업종합")

    def test_normalize_key_lowercases_ascii(self):
        self.assertEqual(pdc._normalize_key("ABC-123"), "abc123")

    def test_normalize_key_handles_none(self):
        self.assertEqual(pdc._normalize_key(None), "")

    def test_normalize_key_preserves_korean(self):
        self.assertEqual(pdc._normalize_key("소방시설공사업"), "소방시설공사업")


if __name__ == "__main__":
    unittest.main()
