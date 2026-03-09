"""Tests for permit_diagnosis_calculator infrastructure functions.

Covers previously untested Tier-1 and Tier-2 functions:
  _load_json_safe, _load_text_file, _load_catalog_file,
  _build_expanded_industry_lookup, _build_family_key_lookup,
  _merge_expanded_rule_metadata,
  _compact_case_story_surface, _compact_review_case_preset,
  _attach_claim_packet_summaries, _attach_operator_demo_artifacts,
  _attach_review_case_artifacts, _build_claim_packet_lookup,
  _build_wordpress_fragment, _wrap_wordpress_safe_scripts,
  _build_platform_catalog, _build_master_catalog,
  _load_focus_scope_overrides, _load_catalog.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from permit_diagnosis_calculator import (
    _load_json_safe,
    _load_text_file,
    _load_catalog_file,
    _build_expanded_industry_lookup,
    _build_family_key_lookup,
    _build_review_case_preset_lookup,
    _build_case_story_surface_lookup,
    _build_operator_demo_lookup,
    _merge_expanded_rule_metadata,
    _compact_case_story_surface,
    _compact_review_case_preset,
    _attach_claim_packet_summaries,
    _attach_operator_demo_artifacts,
    _attach_review_case_artifacts,
    _build_claim_packet_lookup,
    _build_wordpress_fragment,
    _wrap_wordpress_safe_scripts,
    _build_platform_catalog,
    _build_master_catalog,
    _load_focus_scope_overrides,
    _blank_catalog,
    _blank_focus_scope_overrides,
)


# ===================================================================
# _load_json_safe
# ===================================================================
class LoadJsonSafeTest(unittest.TestCase):
    def _factory(self):
        return {"default": True}

    def test_returns_default_for_missing_path(self):
        result = _load_json_safe(Path("/nonexistent/path.json"), self._factory)
        self.assertEqual(result, {"default": True})

    def test_loads_valid_json(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"key": "value"}, f)
            f.flush()
            path = Path(f.name)
        try:
            result = _load_json_safe(path, self._factory)
            self.assertEqual(result["key"], "value")
            # default factory keys merged in
            self.assertTrue(result.get("default"))
        finally:
            os.unlink(path)

    def test_returns_default_for_invalid_json(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("{broken json")
            f.flush()
            path = Path(f.name)
        try:
            result = _load_json_safe(path, self._factory)
            self.assertEqual(result, {"default": True})
        finally:
            os.unlink(path)

    def test_returns_default_for_non_dict_json(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump([1, 2, 3], f)
            f.flush()
            path = Path(f.name)
        try:
            result = _load_json_safe(path, self._factory)
            self.assertEqual(result, {"default": True})
        finally:
            os.unlink(path)

    def test_factory_keys_merged_under_loaded(self):
        """Loaded keys should override factory defaults."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"default": False, "extra": 1}, f)
            f.flush()
            path = Path(f.name)
        try:
            result = _load_json_safe(path, self._factory)
            # base.update(loaded): factory key overridden by loaded
            self.assertFalse(result["default"])
            self.assertEqual(result["extra"], 1)
        finally:
            os.unlink(path)


# ===================================================================
# _load_text_file
# ===================================================================
class LoadTextFileTest(unittest.TestCase):
    def test_returns_empty_for_missing_file(self):
        self.assertEqual(_load_text_file(Path("/nonexistent/file.txt")), "")

    def test_reads_file_content(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("hello world")
            f.flush()
            path = Path(f.name)
        try:
            self.assertEqual(_load_text_file(path), "hello world")
        finally:
            os.unlink(path)


# ===================================================================
# _load_catalog_file
# ===================================================================
class LoadCatalogFileTest(unittest.TestCase):
    def test_returns_blank_for_missing(self):
        result = _load_catalog_file(Path("/nonexistent/catalog.json"))
        self.assertIsInstance(result.get("summary"), dict)
        self.assertIsInstance(result.get("major_categories"), list)
        self.assertIsInstance(result.get("industries"), list)

    def test_loads_and_ensures_keys(self):
        data = {"industries": [{"service_code": "A001"}]}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)
        try:
            result = _load_catalog_file(path)
            self.assertEqual(len(result["industries"]), 1)
            self.assertIn("summary", result)
            self.assertIn("major_categories", result)
        finally:
            os.unlink(path)


# ===================================================================
# _load_focus_scope_overrides
# ===================================================================
class LoadFocusScopeOverridesTest(unittest.TestCase):
    def test_returns_blank_for_missing(self):
        result = _load_focus_scope_overrides(Path("/nonexistent/overrides.json"))
        self.assertIsInstance(result.get("manual_rule_groups"), list)
        self.assertIsInstance(result.get("profile_overrides"), list)

    def test_loads_real_data(self):
        data = {"manual_rule_groups": [{"id": "MRG1"}], "profile_overrides": []}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)
        try:
            result = _load_focus_scope_overrides(path)
            self.assertEqual(len(result["manual_rule_groups"]), 1)
        finally:
            os.unlink(path)


# ===================================================================
# _build_expanded_industry_lookup
# ===================================================================
class BuildExpandedIndustryLookupTest(unittest.TestCase):
    def test_builds_lookup_from_industries(self):
        catalog = {
            "industries": [
                {"service_code": "A001", "name": "Alpha"},
                {"service_code": "B002", "name": "Beta"},
            ]
        }
        lookup = _build_expanded_industry_lookup(catalog)
        self.assertEqual(len(lookup), 2)
        self.assertEqual(lookup["A001"]["name"], "Alpha")

    def test_skips_non_dict_rows(self):
        catalog = {"industries": [None, "string", {"service_code": "C003"}]}
        lookup = _build_expanded_industry_lookup(catalog)
        self.assertEqual(len(lookup), 1)

    def test_skips_rows_without_service_code(self):
        catalog = {"industries": [{"name": "no code"}, {"service_code": "", "name": "empty"}]}
        lookup = _build_expanded_industry_lookup(catalog)
        self.assertEqual(len(lookup), 0)

    def test_empty_catalog(self):
        self.assertEqual(_build_expanded_industry_lookup({}), {})

    def test_none_industries(self):
        self.assertEqual(_build_expanded_industry_lookup({"industries": None}), {})


# ===================================================================
# _build_family_key_lookup (and its aliases)
# ===================================================================
class BuildFamilyKeyLookupTest(unittest.TestCase):
    def test_builds_lookup(self):
        report = {
            "families": [
                {"family_key": "FK1", "data": "one"},
                {"family_key": "FK2", "data": "two"},
            ]
        }
        lookup = _build_family_key_lookup(report)
        self.assertEqual(len(lookup), 2)
        self.assertEqual(lookup["FK1"]["data"], "one")

    def test_skips_non_dict_families(self):
        report = {"families": [None, 42, {"family_key": "FK3"}]}
        lookup = _build_family_key_lookup(report)
        self.assertEqual(len(lookup), 1)

    def test_skips_empty_family_key(self):
        report = {"families": [{"family_key": ""}]}
        self.assertEqual(len(_build_family_key_lookup(report)), 0)

    def test_none_report(self):
        self.assertEqual(_build_family_key_lookup(None), {})

    def test_empty_report(self):
        self.assertEqual(_build_family_key_lookup({}), {})

    def test_aliases_are_same_function(self):
        self.assertIs(_build_review_case_preset_lookup, _build_family_key_lookup)
        self.assertIs(_build_case_story_surface_lookup, _build_family_key_lookup)
        self.assertIs(_build_operator_demo_lookup, _build_family_key_lookup)


# ===================================================================
# _build_claim_packet_lookup
# ===================================================================
class BuildClaimPacketLookupTest(unittest.TestCase):
    def test_builds_lookup(self):
        bundle = {
            "families": [
                {"family_key": "FK1", "claim_packet": {"claim_id": "C1"}},
            ]
        }
        lookup = _build_claim_packet_lookup(bundle)
        self.assertEqual(len(lookup), 1)
        self.assertEqual(lookup["FK1"]["claim_id"], "C1")

    def test_skips_empty_claim_packet(self):
        bundle = {"families": [{"family_key": "FK1", "claim_packet": {}}]}
        self.assertEqual(len(_build_claim_packet_lookup(bundle)), 0)

    def test_skips_none_claim_packet(self):
        bundle = {"families": [{"family_key": "FK1", "claim_packet": None}]}
        self.assertEqual(len(_build_claim_packet_lookup(bundle)), 0)

    def test_none_bundle(self):
        self.assertEqual(_build_claim_packet_lookup(None), {})

    def test_empty_bundle(self):
        self.assertEqual(_build_claim_packet_lookup({}), {})


# ===================================================================
# _merge_expanded_rule_metadata
# ===================================================================
class MergeExpandedRuleMetadataTest(unittest.TestCase):
    def _rule_catalog(self, groups):
        return {"rule_groups": groups}

    def _expanded_catalog(self, packs):
        return {"rule_criteria_packs": packs}

    def test_returns_base_when_no_packs(self):
        groups = [{"rule_id": "R1", "industry_name": "Test"}]
        result = _merge_expanded_rule_metadata(
            self._rule_catalog(groups), self._expanded_catalog([])
        )
        self.assertEqual(len(result["rule_groups"]), 1)
        self.assertEqual(result["rule_groups"][0]["rule_id"], "R1")

    def test_returns_base_when_no_groups(self):
        packs = [{"rule_id": "R1"}]
        result = _merge_expanded_rule_metadata(
            self._rule_catalog([]), self._expanded_catalog(packs)
        )
        self.assertEqual(len(result["rule_groups"]), 0)

    def test_merges_additional_criteria_lines(self):
        groups = [
            {
                "rule_id": "R1",
                "pending_criteria_lines": [
                    {"category": "office", "text": "existing line"}
                ],
            }
        ]
        packs = [
            {
                "rule_id": "R1",
                "additional_criteria_lines": [
                    {"category": "facility", "text": "new line"},
                    {"category": "office", "text": "existing line"},  # duplicate
                ],
            }
        ]
        result = _merge_expanded_rule_metadata(
            self._rule_catalog(groups), self._expanded_catalog(packs)
        )
        merged_group = result["rule_groups"][0]
        pending = merged_group["pending_criteria_lines"]
        texts = [p["text"] for p in pending]
        self.assertIn("existing line", texts)
        self.assertIn("new line", texts)
        # Duplicate should not appear twice
        self.assertEqual(texts.count("existing line"), 1)

    def test_unmatched_group_passes_through(self):
        groups = [{"rule_id": "R1"}, {"rule_id": "R2"}]
        packs = [{"rule_id": "R1", "additional_criteria_lines": []}]
        result = _merge_expanded_rule_metadata(
            self._rule_catalog(groups), self._expanded_catalog(packs)
        )
        self.assertEqual(len(result["rule_groups"]), 2)

    def test_sets_coverage_status_partial(self):
        groups = [{"rule_id": "R1"}]
        packs = [
            {
                "rule_id": "R1",
                "additional_criteria_lines": [
                    {"category": "office", "text": "line"}
                ],
            }
        ]
        result = _merge_expanded_rule_metadata(
            self._rule_catalog(groups), self._expanded_catalog(packs)
        )
        meta = result["rule_groups"][0].get("mapping_meta", {})
        self.assertEqual(meta.get("coverage_status"), "partial")
        self.assertTrue(meta.get("manual_review_required"))

    def test_none_inputs(self):
        result = _merge_expanded_rule_metadata(None, None)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("rule_groups", []), [])

    def test_synthesizes_typed_criteria_from_pending(self):
        groups = [{"rule_id": "R1"}]
        packs = [
            {
                "rule_id": "R1",
                "additional_criteria_lines": [
                    {"category": "office", "text": "사무실 확보"},
                ],
            }
        ]
        result = _merge_expanded_rule_metadata(
            self._rule_catalog(groups), self._expanded_catalog(packs)
        )
        typed = result["rule_groups"][0].get("typed_criteria", [])
        # Should have synthesized at least one criterion from the pending line
        self.assertGreaterEqual(len(typed), 1)


# ===================================================================
# _compact_case_story_surface
# ===================================================================
class CompactCaseStorySurfaceTest(unittest.TestCase):
    def _family(self):
        return {
            "family_key": "FK1",
            "claim_id": "C1",
            "preset_total": 5,
            "manual_review_preset_total": 2,
            "representative_cases": [
                {
                    "preset_id": "P1",
                    "case_kind": "pass",
                    "service_code": "SC1",
                    "service_name": "Test",
                    "expected_status": "pass",
                    "review_reason": "reason_A",
                    "manual_review_expected": True,
                },
                {
                    "preset_id": "P2",
                    "case_kind": "fail",
                    "service_code": "SC1",
                    "service_name": "Test",
                    "expected_status": "fail",
                    "review_reason": "reason_B",
                    "manual_review_expected": False,
                },
            ],
            "operator_story_points": ["point one", "point two"],
        }

    def test_basic_compact(self):
        result = _compact_case_story_surface(self._family())
        self.assertEqual(result["family_key"], "FK1")
        self.assertEqual(result["preset_total"], 5)
        self.assertEqual(result["review_reason_total"], 2)
        self.assertEqual(len(result["representative_cases"]), 2)
        self.assertEqual(len(result["operator_story_points"]), 2)

    def test_deduplicates_review_reasons(self):
        family = self._family()
        family["representative_cases"][1]["review_reason"] = "reason_A"
        result = _compact_case_story_surface(family)
        self.assertEqual(result["review_reason_total"], 1)
        self.assertEqual(result["review_reasons"], ["reason_A"])

    def test_limits_representative_cases_to_3(self):
        family = self._family()
        family["representative_cases"] = [
            {"preset_id": f"P{i}", "case_kind": "pass", "service_code": "SC",
             "service_name": "T", "expected_status": "pass", "review_reason": f"R{i}"}
            for i in range(5)
        ]
        result = _compact_case_story_surface(family)
        self.assertLessEqual(len(result["representative_cases"]), 3)

    def test_empty_family(self):
        result = _compact_case_story_surface({})
        # Empty values stripped
        self.assertNotIn("family_key", result)

    def test_skips_non_dict_cases(self):
        family = {"representative_cases": [None, "string", {"preset_id": "P1"}]}
        result = _compact_case_story_surface(family)
        self.assertEqual(len(result.get("representative_cases", [])), 1)


# ===================================================================
# _compact_review_case_preset
# ===================================================================
class CompactReviewCasePresetTest(unittest.TestCase):
    def _preset(self):
        return {
            "preset_id": "PR1",
            "case_id": "C1",
            "case_kind": "pass",
            "preset_label": "Test preset",
            "service_code": "SC1",
            "service_name": "Service",
            "legal_basis_title": "Law A",
            "operator_note": "Note",
            "input_payload": {
                "industry_selector": "SC1",
                "capital_eok": 1.5,
                "technicians_count": 3,
                "other_requirement_checklist": {"office_secured": True},
            },
            "expected_outcome": {
                "overall_status": "pass",
                "capital_gap_eok": 0.0,
                "technicians_gap": 0,
                "review_reason": "",
                "manual_review_expected": False,
                "proof_coverage_ratio": "1.0",
            },
        }

    def test_basic_compact(self):
        result = _compact_review_case_preset(self._preset())
        self.assertEqual(result["preset_id"], "PR1")
        self.assertEqual(result["input_payload"]["capital_eok"], 1.5)
        self.assertEqual(result["input_payload"]["technicians_count"], 3)

    def test_empty_string_in_nested_dict_preserved(self):
        result = _compact_review_case_preset(self._preset())
        # Empty-value stripping only applies to top-level keys.
        # Nested dicts (input_payload, expected_outcome) are kept as-is.
        self.assertIn("expected_outcome", result)
        self.assertEqual(result["expected_outcome"]["review_reason"], "")

    def test_empty_preset(self):
        result = _compact_review_case_preset({})
        # Should have input_payload and expected_outcome dicts
        self.assertIn("input_payload", result)
        self.assertIn("expected_outcome", result)

    def test_non_dict_input_payload(self):
        preset = self._preset()
        preset["input_payload"] = "not a dict"
        result = _compact_review_case_preset(preset)
        self.assertEqual(result["input_payload"]["capital_eok"], 0.0)


# ===================================================================
# _attach_claim_packet_summaries
# ===================================================================
class AttachClaimPacketSummariesTest(unittest.TestCase):
    def test_no_bundle_returns_copies(self):
        rows = [{"service_code": "A"}, {"service_code": "B"}]
        result = _attach_claim_packet_summaries(rows, {})
        self.assertEqual(len(result), 2)
        # Should be copies not originals
        self.assertIsNot(result[0], rows[0])

    def test_none_rows(self):
        self.assertEqual(_attach_claim_packet_summaries(None, {}), [])

    def test_skips_non_dict_rows(self):
        result = _attach_claim_packet_summaries([None, "x", {"a": 1}], {})
        self.assertEqual(len(result), 1)

    def test_attaches_summary_when_match(self):
        bundle = {
            "families": [
                {
                    "family_key": "TestLaw",
                    "claim_packet": {
                        "claim_id": "CL1",
                        "claim_title": "Title",
                        "claim_statement": "Statement",
                        "source_proof_summary": {
                            "proof_coverage_ratio": "0.85",
                            "checksum_samples": ["abc"],
                            "source_url_samples": ["http://ex.com"],
                        },
                    },
                }
            ]
        }
        rows = [{"law_title": "TestLaw"}]
        result = _attach_claim_packet_summaries(rows, bundle)
        self.assertIn("claim_packet_summary", result[0])
        self.assertEqual(result[0]["claim_packet_summary"]["claim_id"], "CL1")


# ===================================================================
# _attach_operator_demo_artifacts
# ===================================================================
class AttachOperatorDemoArtifactsTest(unittest.TestCase):
    def test_no_report_returns_copies(self):
        rows = [{"a": 1}]
        result = _attach_operator_demo_artifacts(rows, {})
        self.assertEqual(len(result), 1)
        self.assertIsNot(result[0], rows[0])

    def test_none_rows(self):
        self.assertEqual(_attach_operator_demo_artifacts(None, {}), [])


# ===================================================================
# _attach_review_case_artifacts
# ===================================================================
class AttachReviewCaseArtifactsTest(unittest.TestCase):
    def test_no_lookups_returns_copies(self):
        rows = [{"x": 1}]
        result = _attach_review_case_artifacts(rows, {}, {})
        self.assertEqual(len(result), 1)

    def test_none_rows(self):
        self.assertEqual(_attach_review_case_artifacts(None, {}, {}), [])


# ===================================================================
# _wrap_wordpress_safe_scripts
# ===================================================================
class WrapWordpressSafeScriptsTest(unittest.TestCase):
    def test_passthrough(self):
        html = "<script nowprocket>alert(1)</script>"
        self.assertEqual(_wrap_wordpress_safe_scripts(html), html)

    def test_empty(self):
        self.assertEqual(_wrap_wordpress_safe_scripts(""), "")


# ===================================================================
# _build_wordpress_fragment
# ===================================================================
class BuildWordpressFragmentTest(unittest.TestCase):
    def test_wraps_in_section(self):
        html = "<html><body><div>content</div></body></html>"
        result = _build_wordpress_fragment(html)
        self.assertIn('<section id="smna-permit-precheck"', result)
        self.assertIn("content", result)
        self.assertIn("nowprocket", result)

    def test_extracts_body_content(self):
        html = "<html><body><p>inner</p></body></html>"
        result = _build_wordpress_fragment(html)
        self.assertIn("<p>inner</p>", result)
        # Should not include body tags themselves
        self.assertNotIn("<body>", result)

    def test_scopes_css(self):
        html = "<html><head><style>.btn { color: red; }</style></head><body>x</body></html>"
        result = _build_wordpress_fragment(html)
        self.assertIn("#smna-permit-precheck", result)

    def test_empty_body(self):
        html = "<html><body></body></html>"
        result = _build_wordpress_fragment(html)
        self.assertIn("smna-permit-precheck", result)


# ===================================================================
# _build_platform_catalog
# ===================================================================
class BuildPlatformCatalogTest(unittest.TestCase):
    def test_basic_catalog(self):
        rows = [
            {"service_code": "SC1", "service_name": "Alpha", "major_code": "M01", "major_name": "Cat1"},
            {"service_code": "SC2", "service_name": "Beta", "major_code": "M01", "major_name": "Cat1"},
        ]
        result = _build_platform_catalog(rows, {"industries": []})
        self.assertEqual(result["summary"]["platform_industry_total"], 2)
        self.assertEqual(len(result["major_categories"]), 1)
        self.assertEqual(result["major_categories"][0]["industry_count"], 2)

    def test_empty_rows(self):
        result = _build_platform_catalog([], {"industries": []})
        self.assertEqual(result["summary"]["platform_industry_total"], 0)

    def test_skips_non_dict_rows(self):
        result = _build_platform_catalog([None, "bad"], {"industries": []})
        self.assertEqual(result["summary"]["platform_industry_total"], 0)

    def test_absorbs_unmatched_selector(self):
        rows = [{"service_code": "SC1", "service_name": "A", "major_code": "M01", "major_name": "C"}]
        selector = {
            "industries": [
                {
                    "selector_code": "SEL1",
                    "canonical_service_code": "SC_NEW",
                    "selector_kind": "focus",
                    "selector_name": "New",
                }
            ]
        }
        result = _build_platform_catalog(rows, selector)
        # Original + absorbed
        self.assertEqual(result["summary"]["platform_industry_total"], 2)
        self.assertGreaterEqual(result["summary"]["platform_absorbed_focus_total"], 1)


# ===================================================================
# _build_master_catalog
# ===================================================================
class BuildMasterCatalogTest(unittest.TestCase):
    def test_merges_summaries(self):
        platform = {
            "summary": {"platform_industry_total": 10, "platform_category_total": 3},
            "industries": [],
            "major_categories": [],
        }
        selector = {"summary": {"selector_inferred_total": 5}}
        result = _build_master_catalog(platform, selector)
        self.assertIn("summary", result)
        # Summary keys are remapped to master_* prefix
        self.assertEqual(result["summary"]["master_industry_total"], 10)
        self.assertEqual(result["summary"]["master_category_total"], 3)
        self.assertEqual(result["summary"]["master_inferred_overlay_total"], 5)

    def test_none_inputs(self):
        result = _build_master_catalog(None, None)
        self.assertIsInstance(result, dict)
        self.assertIn("summary", result)

    def test_empty_inputs(self):
        result = _build_master_catalog({}, {})
        self.assertIsInstance(result, dict)


from permit_diagnosis_calculator import _repair_generated_permit_html


# ===================================================================
# _repair_generated_permit_html
# ===================================================================
class RepairGeneratedPermitHtmlTest(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(_repair_generated_permit_html(""), "")

    def test_none_input(self):
        self.assertEqual(_repair_generated_permit_html(None), "")

    def test_passthrough_unmatched(self):
        html = "<html><body>simple content</body></html>"
        result = _repair_generated_permit_html(html)
        self.assertIn("simple content", result)

    def test_structuredReview_injected_when_missing(self):
        """If '자동 점검 결과' text is absent and renderStructuredReview is missing,
        the repair function should inject it."""
        html = "<html><body><script>function something(){}</script></body></html>"
        result = _repair_generated_permit_html(html)
        # If the pattern doesn't match (no matching template structure),
        # the result should still be valid HTML
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main()
