"""Supplementary unit tests for permit_diagnosis_calculator.py.

Covers: blank factory functions, _compact_operator_demo_family,
_compact_runtime_reasoning_ladder_map, _compact_industry_row_for_client,
_build_selector_entry.
"""

import unittest

from permit_diagnosis_calculator import (
    _blank_expanded_criteria_catalog,
    _blank_focus_scope_overrides,
    _blank_patent_evidence_bundle,
    _blank_review_case_presets_report,
    _blank_case_story_surface_report,
    _blank_operator_demo_packet_report,
    _blank_review_reason_decision_ladder_report,
    _blank_critical_prompt_surface_packet,
    _compact_operator_demo_family,
    _compact_runtime_reasoning_ladder_map,
    _compact_industry_row_for_client,
    _build_selector_entry,
)


# ===================================================================
# Blank factory functions — shape validation
# ===================================================================
class BlankExpandedCriteriaCatalogTest(unittest.TestCase):
    def test_structure(self):
        result = _blank_expanded_criteria_catalog()
        self.assertEqual(result["generated_at"], "")
        self.assertEqual(result["source"], {})
        self.assertEqual(result["summary"], {})
        self.assertEqual(result["industries"], [])
        self.assertEqual(result["rule_criteria_packs"], [])

    def test_independent_instances(self):
        a = _blank_expanded_criteria_catalog()
        b = _blank_expanded_criteria_catalog()
        a["industries"].append("test")
        self.assertEqual(b["industries"], [])


class BlankFocusScopeOverridesTest(unittest.TestCase):
    def test_structure(self):
        result = _blank_focus_scope_overrides()
        self.assertEqual(result["manual_rule_groups"], [])
        self.assertEqual(result["profile_overrides"], [])


class BlankPatentEvidenceBundleTest(unittest.TestCase):
    def test_structure(self):
        result = _blank_patent_evidence_bundle()
        self.assertEqual(result["summary"], {})
        self.assertEqual(result["families"], [])


class BlankReviewCasePresetsReportTest(unittest.TestCase):
    def test_structure(self):
        result = _blank_review_case_presets_report()
        self.assertEqual(result["summary"], {})
        self.assertEqual(result["families"], [])


class BlankCaseStorySurfaceReportTest(unittest.TestCase):
    def test_structure(self):
        result = _blank_case_story_surface_report()
        self.assertEqual(result["summary"], {})
        self.assertEqual(result["families"], [])


class BlankOperatorDemoPacketReportTest(unittest.TestCase):
    def test_structure(self):
        result = _blank_operator_demo_packet_report()
        self.assertEqual(result["summary"], {})
        self.assertEqual(result["source_paths"], {})
        self.assertEqual(result["families"], [])


class BlankReviewReasonDecisionLadderReportTest(unittest.TestCase):
    def test_structure(self):
        result = _blank_review_reason_decision_ladder_report()
        self.assertEqual(result["summary"], {})
        self.assertEqual(result["ladders"], [])


class BlankCriticalPromptSurfacePacketTest(unittest.TestCase):
    def test_structure(self):
        result = _blank_critical_prompt_surface_packet()
        self.assertEqual(result["summary"], {})
        self.assertEqual(result["critical_prompt_block"], {})
        self.assertEqual(result["compact_decision_lens"], {})


# ===================================================================
# _compact_operator_demo_family
# ===================================================================
class CompactOperatorDemoFamilyTest(unittest.TestCase):
    def test_full_family(self):
        family = {
            "family_key": "FK001",
            "claim_id": "C001",
            "claim_title": "전기공사업 자본금 기준",
            "proof_coverage_ratio": "0.85",
            "operator_story_points": ["포인트1", "포인트2", "포인트3", "포인트4"],
            "prompt_case_binding": {"key1": "val1", "key2": ""},
            "demo_cases": [
                {
                    "preset_id": "P1",
                    "case_kind": "pass",
                    "service_code": "SC001",
                    "service_name": "전기공사업",
                    "review_reason": "자본금 미달",
                    "expected_status": "pass",
                    "manual_review_expected": True,
                    "proof_coverage_ratio": "0.9",
                    "operator_note": "테스트 노트",
                },
            ],
        }
        result = _compact_operator_demo_family(family)
        self.assertEqual(result["family_key"], "FK001")
        self.assertEqual(result["claim_id"], "C001")
        self.assertEqual(result["demo_case_total"], 1)
        self.assertEqual(result["manual_review_demo_total"], 1)
        self.assertEqual(result["review_reason_total"], 1)
        self.assertEqual(result["review_reasons"], ["자본금 미달"])
        self.assertEqual(result["representative_services"], ["전기공사업"])
        # operator_story_points truncated to 3
        self.assertEqual(len(result["operator_story_points"]), 3)
        # Empty values filtered from prompt_case_binding
        self.assertIn("key1", result["prompt_case_binding"])
        self.assertNotIn("key2", result["prompt_case_binding"])

    def test_empty_family(self):
        result = _compact_operator_demo_family({})
        self.assertEqual(result.get("demo_case_total", 0), 0)
        self.assertEqual(result.get("manual_review_demo_total", 0), 0)

    def test_non_dict_demo_cases_skipped(self):
        family = {
            "family_key": "FK002",
            "demo_cases": ["not_a_dict", None, 42],
        }
        result = _compact_operator_demo_family(family)
        self.assertEqual(result.get("demo_case_total", 0), 0)

    def test_demo_cases_limit_3(self):
        family = {
            "family_key": "FK003",
            "demo_cases": [
                {"preset_id": f"P{i}", "case_kind": "pass", "service_code": f"SC{i}",
                 "service_name": f"업종{i}", "review_reason": f"사유{i}",
                 "expected_status": "pass", "manual_review_expected": False,
                 "proof_coverage_ratio": "0.8", "operator_note": ""}
                for i in range(5)
            ],
        }
        result = _compact_operator_demo_family(family)
        # demo_case_total counts all, but demo_cases truncated to 3
        self.assertEqual(result["demo_case_total"], 5)
        self.assertEqual(len(result["demo_cases"]), 3)

    def test_deduplicates_review_reasons(self):
        family = {
            "family_key": "FK004",
            "demo_cases": [
                {"review_reason": "사유A", "service_name": ""},
                {"review_reason": "사유A", "service_name": ""},
                {"review_reason": "사유B", "service_name": ""},
            ],
        }
        result = _compact_operator_demo_family(family)
        self.assertEqual(result["review_reasons"], ["사유A", "사유B"])
        self.assertEqual(result["review_reason_total"], 2)


# ===================================================================
# _compact_runtime_reasoning_ladder_map
# ===================================================================
class CompactRuntimeReasoningLadderMapTest(unittest.TestCase):
    def test_basic(self):
        report = {
            "ladders": [
                {
                    "review_reason": "자본금 미달",
                    "inspect_first": "자본금 확인",
                    "next_action": "증자 필요",
                    "manual_review_gate": True,
                    "evidence_first": ["증빙1"],
                    "missing_input_focus": ["자본금"],
                    "binding_preset_ids": ["P1", "P2"],
                    "binding_questions": ["Q1"],
                },
            ],
        }
        result = _compact_runtime_reasoning_ladder_map(report)
        self.assertIn("자본금 미달", result)
        entry = result["자본금 미달"]
        self.assertEqual(entry["review_reason"], "자본금 미달")
        self.assertEqual(entry["inspect_first"], "자본금 확인")
        self.assertTrue(entry["manual_review_gate"])
        self.assertEqual(entry["evidence_first"], ["증빙1"])

    def test_empty_report(self):
        self.assertEqual(_compact_runtime_reasoning_ladder_map({}), {})

    def test_no_ladders(self):
        self.assertEqual(_compact_runtime_reasoning_ladder_map({"ladders": []}), {})

    def test_skip_non_dict(self):
        report = {"ladders": ["not_dict", None, 42]}
        self.assertEqual(_compact_runtime_reasoning_ladder_map(report), {})

    def test_skip_empty_review_reason(self):
        report = {"ladders": [{"review_reason": "", "inspect_first": "x"}]}
        self.assertEqual(_compact_runtime_reasoning_ladder_map(report), {})

    def test_empty_values_filtered(self):
        report = {
            "ladders": [
                {
                    "review_reason": "기술자 부족",
                    "inspect_first": "",
                    "next_action": "",
                    "manual_review_gate": False,
                    "evidence_first": [],
                    "missing_input_focus": [],
                    "binding_preset_ids": [],
                    "binding_questions": [],
                },
            ],
        }
        result = _compact_runtime_reasoning_ladder_map(report)
        entry = result["기술자 부족"]
        self.assertEqual(entry["review_reason"], "기술자 부족")
        # Empty strings and lists filtered
        self.assertNotIn("inspect_first", entry)
        self.assertNotIn("next_action", entry)
        self.assertNotIn("evidence_first", entry)

    def test_binding_preset_ids_limit_3(self):
        report = {
            "ladders": [
                {
                    "review_reason": "자본금 미달",
                    "binding_preset_ids": ["P1", "P2", "P3", "P4", "P5"],
                },
            ],
        }
        result = _compact_runtime_reasoning_ladder_map(report)
        self.assertEqual(len(result["자본금 미달"]["binding_preset_ids"]), 3)

    def test_binding_questions_limit_2(self):
        report = {
            "ladders": [
                {
                    "review_reason": "기술자 부족",
                    "binding_questions": ["Q1", "Q2", "Q3"],
                },
            ],
        }
        result = _compact_runtime_reasoning_ladder_map(report)
        self.assertEqual(len(result["기술자 부족"]["binding_questions"]), 2)


# ===================================================================
# _compact_industry_row_for_client
# ===================================================================
class CompactIndustryRowForClientTest(unittest.TestCase):
    def test_basic_fields(self):
        row = {
            "service_code": "SC001",
            "service_name": "전기공사업",
            "major_code": "M01",
            "major_name": "전기",
            "group_name": "전기그룹",
            "has_rule": True,
            "is_rules_only": False,
            "candidate_criteria_count": 5,
        }
        result = _compact_industry_row_for_client(row)
        self.assertEqual(result["service_code"], "SC001")
        self.assertEqual(result["service_name"], "전기공사업")
        self.assertTrue(result["has_rule"])
        self.assertFalse(result["is_rules_only"])
        self.assertEqual(result["candidate_criteria_count"], 5)

    def test_empty_row(self):
        result = _compact_industry_row_for_client({})
        self.assertEqual(result["service_code"], "")
        self.assertEqual(result["service_name"], "")
        self.assertFalse(result["has_rule"])
        self.assertEqual(result["candidate_criteria_count"], 0)

    def test_optional_fields_omitted_when_empty(self):
        result = _compact_industry_row_for_client({})
        # Optional fields should not be in result when empty
        self.assertNotIn("law_title", result)
        self.assertNotIn("legal_basis_title", result)
        self.assertNotIn("catalog_source_kind", result)
        self.assertNotIn("quality_flags", result)

    def test_optional_fields_included_when_present(self):
        row = {
            "law_title": "건설산업기본법",
            "legal_basis_title": "시행령 제13조",
            "catalog_source_kind": "expanded",
            "quality_flags": ["checked", "verified"],
        }
        result = _compact_industry_row_for_client(row)
        self.assertEqual(result["law_title"], "건설산업기본법")
        self.assertEqual(result["legal_basis_title"], "시행령 제13조")
        self.assertEqual(result["quality_flags"], ["checked", "verified"])

    def test_registration_requirement_profile(self):
        row = {
            "registration_requirement_profile": {
                "capital_required": True,
                "technical_personnel_required": True,
            },
        }
        result = _compact_industry_row_for_client(row)
        self.assertTrue(result["registration_requirement_profile"]["capital_required"])

    def test_empty_profile_omitted(self):
        row = {"registration_requirement_profile": {}}
        result = _compact_industry_row_for_client(row)
        self.assertNotIn("registration_requirement_profile", result)


# ===================================================================
# _build_selector_entry
# ===================================================================
class BuildSelectorEntryTest(unittest.TestCase):
    def _row(self, **overrides):
        base = {
            "service_code": "SC001",
            "service_name": "전기공사업",
            "major_code": "M01",
            "major_name": "전기",
            "group_name": "전기그룹",
            "has_rule": True,
            "is_rules_only": False,
            "candidate_criteria_count": 3,
        }
        base.update(overrides)
        return base

    def test_focus_kind(self):
        result = _build_selector_entry(self._row(), "focus")
        self.assertEqual(result["selector_kind"], "focus")
        self.assertEqual(result["selector_code"], "SEL::FOCUS::SC001")
        self.assertEqual(result["selector_category_code"], "SEL-FOCUS")
        self.assertEqual(result["selector_category_name"], "핵심 업종군")

    def test_inferred_kind(self):
        result = _build_selector_entry(self._row(), "inferred")
        self.assertEqual(result["selector_kind"], "inferred")
        self.assertEqual(result["selector_code"], "SEL::INFERRED::SC001")
        self.assertEqual(result["selector_category_code"], "SEL-INFERRED")
        self.assertEqual(result["selector_category_name"], "추론 점검군")

    def test_focus_prefix_stripped(self):
        row = self._row(service_code="FOCUS::SC001")
        result = _build_selector_entry(row, "focus")
        self.assertEqual(result["selector_code"], "SEL::FOCUS::SC001")

    def test_default_kind_is_focus(self):
        result = _build_selector_entry(self._row(), "")
        self.assertEqual(result["selector_kind"], "focus")
        self.assertEqual(result["selector_category_code"], "SEL-FOCUS")

    def test_preserves_base_fields(self):
        result = _build_selector_entry(self._row(), "focus")
        self.assertEqual(result["service_name"], "전기공사업")
        self.assertEqual(result["canonical_service_code"], "SC001")


if __name__ == "__main__":
    unittest.main()
