from __future__ import annotations

import base64
import gzip
import json
import unittest
from datetime import date, timedelta

from permit_diagnosis_calculator import (
    _blank_catalog,
    _blank_rule_catalog,
    _build_claim_packet_lookup,
    _build_major_categories_for_rows,
    _build_rule_index,
    _build_selector_catalog,
    _build_selector_catalog_row,
    _coerce_non_negative_float,
    _coerce_non_negative_int,
    _compact_candidate_law_rows,
    _compact_candidate_lines,
    _compact_critical_prompt_lens,
    _compact_raw_source_proof,
    _ensure_keys,
    _expand_rule_groups,
    _get_int,
    _get_str,
    _gzip_base64_json,
    _is_capital_technical_scope,
    _is_objective_source_url,
    _normalize_key,
    _normalize_selector_alias,
    _prompt_surface_excerpt_lines,
    _replace_first_block,
    _resolve_rule_for_industry,
    _row_claim_family_key,
    _safe_json,
    _scope_embed_css,
    _synthesize_document_templates,
    _synthesize_typed_criteria_from_pending,
    evaluate_registration_diagnosis,
)


# ---------------------------------------------------------------------------
# _ensure_keys
# ---------------------------------------------------------------------------
class EnsureKeysTest(unittest.TestCase):
    def test_adds_missing_dict_key(self):
        d = {}
        _ensure_keys(d, dict_keys=("a",))
        self.assertEqual(d["a"], {})

    def test_adds_missing_list_key(self):
        d = {}
        _ensure_keys(d, list_keys=("b",))
        self.assertEqual(d["b"], [])

    def test_preserves_existing(self):
        d = {"a": {"x": 1}, "b": [1, 2]}
        _ensure_keys(d, dict_keys=("a",), list_keys=("b",))
        self.assertEqual(d["a"], {"x": 1})
        self.assertEqual(d["b"], [1, 2])

    def test_fixes_wrong_type(self):
        d = {"a": "string", "b": 42}
        _ensure_keys(d, dict_keys=("a",), list_keys=("b",))
        self.assertEqual(d["a"], {})
        self.assertEqual(d["b"], [])


# ---------------------------------------------------------------------------
# _get_str / _get_int
# ---------------------------------------------------------------------------
class GetStrTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_get_str({"k": "hello"}, "k"), "hello")

    def test_strips(self):
        self.assertEqual(_get_str({"k": "  hi  "}, "k"), "hi")

    def test_missing(self):
        self.assertEqual(_get_str({}, "k"), "")

    def test_none_value(self):
        self.assertEqual(_get_str({"k": None}, "k"), "")

    def test_default(self):
        self.assertEqual(_get_str({}, "k", "fallback"), "fallback")

    def test_numeric_converted(self):
        self.assertEqual(_get_str({"k": 42}, "k"), "42")


class GetIntTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_get_int({"k": 5}, "k"), 5)

    def test_float_truncated(self):
        self.assertEqual(_get_int({"k": 3.9}, "k"), 3)

    def test_string_numeric(self):
        self.assertEqual(_get_int({"k": "7"}, "k"), 7)

    def test_negative_clamped(self):
        self.assertEqual(_get_int({"k": -3}, "k"), 0)

    def test_invalid(self):
        self.assertEqual(_get_int({"k": "abc"}, "k"), 0)

    def test_missing(self):
        self.assertEqual(_get_int({}, "k"), 0)

    def test_none(self):
        self.assertEqual(_get_int({"k": None}, "k"), 0)


# ---------------------------------------------------------------------------
# _safe_json / _gzip_base64_json
# ---------------------------------------------------------------------------
class SafeJsonTest(unittest.TestCase):
    def test_script_escape(self):
        result = _safe_json({"html": "</script>"})
        self.assertNotIn("</script>", result)

    def test_unicode_separators(self):
        result = _safe_json({"t": "a\u2028b"})
        self.assertNotIn("\u2028", result)


class GzipBase64JsonTest(unittest.TestCase):
    def test_roundtrip(self):
        data = {"key": "value", "num": 42}
        encoded = _gzip_base64_json(data)
        decoded = json.loads(gzip.decompress(base64.b64decode(encoded)))
        self.assertEqual(decoded, data)


# ---------------------------------------------------------------------------
# _blank_catalog / _blank_rule_catalog
# ---------------------------------------------------------------------------
class BlankCatalogTest(unittest.TestCase):
    def test_catalog_structure(self):
        c = _blank_catalog()
        self.assertIn("summary", c)
        self.assertIn("major_categories", c)
        self.assertIn("industries", c)
        self.assertEqual(c["summary"]["industry_total"], 0)

    def test_rule_catalog_structure(self):
        rc = _blank_rule_catalog()
        self.assertIn("version", rc)
        self.assertIn("rule_groups", rc)
        self.assertIsInstance(rc["rule_groups"], list)


# ---------------------------------------------------------------------------
# _prompt_surface_excerpt_lines
# ---------------------------------------------------------------------------
class PromptSurfaceExcerptLinesTest(unittest.TestCase):
    def test_basic(self):
        text = "## Title\n- Item 1\n- Item 2\nParagraph"
        result = _prompt_surface_excerpt_lines(text, limit=4)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0], "Title")
        self.assertEqual(result[1], "Item 1")
        self.assertEqual(result[3], "Paragraph")

    def test_limit(self):
        text = "\n".join([f"Line {i}" for i in range(10)])
        result = _prompt_surface_excerpt_lines(text, limit=3)
        self.assertEqual(len(result), 3)

    def test_empty(self):
        self.assertEqual(_prompt_surface_excerpt_lines(""), [])

    def test_none(self):
        self.assertEqual(_prompt_surface_excerpt_lines(None), [])

    def test_blank_lines_skipped(self):
        text = "A\n\n\nB"
        result = _prompt_surface_excerpt_lines(text)
        self.assertEqual(result, ["A", "B"])


# ---------------------------------------------------------------------------
# _normalize_key
# ---------------------------------------------------------------------------
class NormalizeKeyTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_normalize_key("전기 공사업"), "전기공사업")

    def test_removes_special_chars(self):
        self.assertEqual(_normalize_key("A-B (C)"), "abc")

    def test_empty(self):
        self.assertEqual(_normalize_key(""), "")

    def test_none(self):
        self.assertEqual(_normalize_key(None), "")

    def test_numeric_preserved(self):
        self.assertEqual(_normalize_key("Type 1"), "type1")


# ---------------------------------------------------------------------------
# _is_objective_source_url
# ---------------------------------------------------------------------------
class IsObjectiveSourceUrlTest(unittest.TestCase):
    def test_law_go_kr(self):
        self.assertTrue(_is_objective_source_url("https://www.law.go.kr/some/path"))

    def test_localdata(self):
        self.assertTrue(_is_objective_source_url("https://localdata.go.kr/data"))

    def test_gov_kr(self):
        self.assertTrue(_is_objective_source_url("https://something.gov.kr/page"))

    def test_random_url(self):
        self.assertFalse(_is_objective_source_url("https://example.com"))

    def test_empty(self):
        self.assertFalse(_is_objective_source_url(""))

    def test_none(self):
        self.assertFalse(_is_objective_source_url(None))

    def test_no_http(self):
        self.assertFalse(_is_objective_source_url("ftp://law.go.kr"))


# ---------------------------------------------------------------------------
# _coerce_non_negative_float / _coerce_non_negative_int
# ---------------------------------------------------------------------------
class CoerceNonNegativeFloatTest(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(_coerce_non_negative_float(3.5), 3.5)

    def test_negative(self):
        self.assertEqual(_coerce_non_negative_float(-1.0), 0.0)

    def test_zero(self):
        self.assertEqual(_coerce_non_negative_float(0), 0.0)

    def test_nan(self):
        self.assertEqual(_coerce_non_negative_float(float("nan")), 0.0)

    def test_string(self):
        self.assertEqual(_coerce_non_negative_float("2.5"), 2.5)

    def test_invalid(self):
        self.assertEqual(_coerce_non_negative_float("abc"), 0.0)

    def test_none(self):
        self.assertEqual(_coerce_non_negative_float(None), 0.0)


class CoerceNonNegativeIntTest(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(_coerce_non_negative_int(5), 5)

    def test_negative(self):
        self.assertEqual(_coerce_non_negative_int(-3), 0)

    def test_float_truncated(self):
        self.assertEqual(_coerce_non_negative_int(3.9), 3)

    def test_string(self):
        self.assertEqual(_coerce_non_negative_int("7"), 7)

    def test_invalid(self):
        self.assertEqual(_coerce_non_negative_int("abc"), 0)


# ---------------------------------------------------------------------------
# _synthesize_typed_criteria_from_pending
# ---------------------------------------------------------------------------
class SynthesizeTypedCriteriaTest(unittest.TestCase):
    def test_office_category(self):
        pending = [{"category": "office", "text": "사무실 필요"}]
        result = _synthesize_typed_criteria_from_pending(pending)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["criterion_id"], "office.secured.auto")
        self.assertTrue(result[0]["blocking"])

    def test_other_maps_to_facility(self):
        pending = [{"category": "other", "text": "기타 요건"}]
        result = _synthesize_typed_criteria_from_pending(pending)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["criterion_id"], "facility.secured.auto")

    def test_unknown_category_skipped(self):
        pending = [{"category": "unknown_xyz"}]
        result = _synthesize_typed_criteria_from_pending(pending)
        self.assertEqual(len(result), 0)

    def test_duplicates_by_criterion_id(self):
        pending = [
            {"category": "office", "text": "A"},
            {"category": "office", "text": "B"},  # same criterion_id
        ]
        result = _synthesize_typed_criteria_from_pending(pending)
        self.assertEqual(len(result), 1)

    def test_empty(self):
        self.assertEqual(_synthesize_typed_criteria_from_pending([]), [])

    def test_none(self):
        self.assertEqual(_synthesize_typed_criteria_from_pending(None), [])

    def test_text_note_truncated(self):
        pending = [{"category": "insurance", "text": "X" * 300}]
        result = _synthesize_typed_criteria_from_pending(pending)
        self.assertLessEqual(len(result[0]["note"]), 200)


# ---------------------------------------------------------------------------
# _synthesize_document_templates
# ---------------------------------------------------------------------------
class SynthesizeDocumentTemplatesTest(unittest.TestCase):
    def test_basic(self):
        criteria = [{
            "criterion_id": "office.secured.auto",
            "label": "사무실 확보",
            "evidence_types": ["임대차계약서", "건축물대장"],
        }]
        result = _synthesize_document_templates(criteria)
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]["doc_id"].startswith("auto::"))

    def test_empty_evidence(self):
        criteria = [{"criterion_id": "x", "evidence_types": []}]
        result = _synthesize_document_templates(criteria)
        self.assertEqual(len(result), 0)

    def test_dedup_by_doc_id(self):
        criteria = [
            {"criterion_id": "x", "evidence_types": ["A"]},
            {"criterion_id": "x", "evidence_types": ["A"]},  # same id
        ]
        result = _synthesize_document_templates(criteria)
        self.assertEqual(len(result), 1)


# ---------------------------------------------------------------------------
# _compact_candidate_lines / _compact_candidate_law_rows
# ---------------------------------------------------------------------------
class CompactCandidateLinesTest(unittest.TestCase):
    def test_basic(self):
        rows = [{"text": "요건 A"}, {"text": "요건 B"}]
        result = _compact_candidate_lines(rows)
        self.assertEqual(len(result), 2)

    def test_empty_text_skipped(self):
        rows = [{"text": ""}, {"text": "OK"}]
        result = _compact_candidate_lines(rows)
        self.assertEqual(len(result), 1)

    def test_non_dict_skipped(self):
        result = _compact_candidate_lines(["string", None])
        self.assertEqual(len(result), 0)

    def test_none(self):
        self.assertEqual(_compact_candidate_lines(None), [])


class CompactCandidateLawRowsTest(unittest.TestCase):
    def test_basic(self):
        rows = [{"law_title": "건설산업기본법", "article": "제9조", "url": "https://law.go.kr/x"}]
        result = _compact_candidate_law_rows(rows)
        self.assertEqual(len(result), 1)

    def test_empty_all_fields_skipped(self):
        rows = [{"law_title": "", "article": "", "url": ""}]
        result = _compact_candidate_law_rows(rows)
        self.assertEqual(len(result), 0)

    def test_url_from_law_url_fallback(self):
        rows = [{"law_title": "법", "law_url": "https://law.go.kr"}]
        result = _compact_candidate_law_rows(rows)
        self.assertEqual(result[0]["url"], "https://law.go.kr")


# ---------------------------------------------------------------------------
# _compact_raw_source_proof
# ---------------------------------------------------------------------------
class CompactRawSourceProofTest(unittest.TestCase):
    def test_basic(self):
        proof = {
            "proof_status": "verified",
            "source_urls": ["https://a.com", "https://b.com"],
            "source_url_total": 2,
            "official_snapshot_note": "note",
            "source_checksum": "abc123",
        }
        result = _compact_raw_source_proof(proof)
        self.assertEqual(result["proof_status"], "verified")
        self.assertEqual(len(result["source_urls"]), 2)

    def test_non_dict(self):
        self.assertEqual(_compact_raw_source_proof("string"), {})
        self.assertEqual(_compact_raw_source_proof(None), {})

    def test_empty_values_stripped(self):
        proof = {"proof_status": "", "source_urls": [], "source_url_total": 0}
        result = _compact_raw_source_proof(proof)
        self.assertNotIn("proof_status", result)
        self.assertNotIn("source_urls", result)

    def test_capture_meta_included(self):
        proof = {
            "proof_status": "ok",
            "source_urls": [],
            "source_url_total": 0,
            "capture_meta": {"captured_at": "2026-01-01", "family_key": "전기"},
        }
        result = _compact_raw_source_proof(proof)
        self.assertIn("capture_meta", result)
        self.assertEqual(result["capture_meta"]["family_key"], "전기")


# ---------------------------------------------------------------------------
# _build_claim_packet_lookup / _row_claim_family_key
# ---------------------------------------------------------------------------
class BuildClaimPacketLookupTest(unittest.TestCase):
    def test_basic(self):
        bundle = {
            "families": [
                {"family_key": "전기", "claim_packet": {"id": "c1"}},
                {"family_key": "소방", "claim_packet": {"id": "c2"}},
            ]
        }
        result = _build_claim_packet_lookup(bundle)
        self.assertEqual(len(result), 2)
        self.assertEqual(result["전기"]["id"], "c1")

    def test_empty_bundle(self):
        self.assertEqual(_build_claim_packet_lookup({}), {})

    def test_none_bundle(self):
        self.assertEqual(_build_claim_packet_lookup(None), {})


class RowClaimFamilyKeyTest(unittest.TestCase):
    def test_from_capture_meta(self):
        row = {"raw_source_proof": {"capture_meta": {"family_key": "전기"}}}
        self.assertEqual(_row_claim_family_key(row), "전기")

    def test_from_law_title(self):
        row = {"law_title": "건설산업기본법"}
        self.assertEqual(_row_claim_family_key(row), "건설산업기본법")

    def test_from_seed_law_family(self):
        row = {"seed_law_family": "소방법"}
        self.assertEqual(_row_claim_family_key(row), "소방법")

    def test_empty(self):
        self.assertEqual(_row_claim_family_key({}), "")


# ---------------------------------------------------------------------------
# _is_capital_technical_scope
# ---------------------------------------------------------------------------
class IsCapitalTechnicalScopeTest(unittest.TestCase):
    def test_both_true(self):
        row = {"registration_requirement_profile": {"capital_required": True, "technical_personnel_required": True}}
        self.assertTrue(_is_capital_technical_scope(row))

    def test_only_capital(self):
        row = {"registration_requirement_profile": {"capital_required": True, "technical_personnel_required": False}}
        self.assertFalse(_is_capital_technical_scope(row))

    def test_no_profile(self):
        self.assertFalse(_is_capital_technical_scope({}))


# ---------------------------------------------------------------------------
# _build_major_categories_for_rows
# ---------------------------------------------------------------------------
class BuildMajorCategoriesTest(unittest.TestCase):
    def test_basic(self):
        rows = [
            {"major_code": "A", "major_name": "건설업"},
            {"major_code": "A", "major_name": "건설업"},
            {"major_code": "B", "major_name": "소방업"},
        ]
        result = _build_major_categories_for_rows(rows)
        self.assertEqual(len(result), 2)
        a = next(c for c in result if c["major_code"] == "A")
        self.assertEqual(a["industry_count"], 2)

    def test_empty(self):
        self.assertEqual(_build_major_categories_for_rows([]), [])

    def test_sorted_by_code(self):
        rows = [
            {"major_code": "B", "major_name": "소방"},
            {"major_code": "A", "major_name": "건설"},
        ]
        result = _build_major_categories_for_rows(rows)
        self.assertEqual(result[0]["major_code"], "A")


# ---------------------------------------------------------------------------
# _expand_rule_groups / _build_rule_index / _resolve_rule_for_industry
# ---------------------------------------------------------------------------
def _make_rule_catalog(names=None, service_codes=None, req_capital=1.5, req_tech=3):
    return {
        "rule_groups": [
            {
                "rule_id": "R001",
                "industry_names": names or ["전기공사업"],
                "aliases": ["전기업"],
                "service_codes": service_codes or ["SC001"],
                "legal_basis": [
                    {"law_title": "전기공사업법", "article": "제4조", "url": "https://www.law.go.kr/전기"},
                ],
                "requirements": {
                    "capital_eok": req_capital,
                    "technicians": req_tech,
                    "equipment_count": 0,
                    "deposit_days": 14,
                },
                "typed_criteria": [],
                "pending_criteria_lines": [],
                "document_templates": [],
            }
        ]
    }


class ExpandRuleGroupsTest(unittest.TestCase):
    def test_single_name(self):
        catalog = _make_rule_catalog(names=["전기공사업"])
        rows = _expand_rule_groups(catalog)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["industry_name"], "전기공사업")
        self.assertEqual(rows[0]["rule_id"], "R001")

    def test_multiple_names(self):
        catalog = _make_rule_catalog(names=["전기공사업", "정보통신공사업"])
        rows = _expand_rule_groups(catalog)
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]["rule_id"].endswith("-1"))
        self.assertTrue(rows[1]["rule_id"].endswith("-2"))

    def test_no_legal_basis_skipped(self):
        catalog = {"rule_groups": [{"rule_id": "X", "industry_names": ["A"], "legal_basis": []}]}
        rows = _expand_rule_groups(catalog)
        self.assertEqual(len(rows), 0)

    def test_non_objective_url_skipped(self):
        catalog = {
            "rule_groups": [{
                "rule_id": "X",
                "industry_names": ["A"],
                "legal_basis": [{"law_title": "법", "article": "1", "url": "https://example.com"}],
                "requirements": {},
            }]
        }
        rows = _expand_rule_groups(catalog)
        self.assertEqual(len(rows), 0)

    def test_empty_catalog(self):
        self.assertEqual(_expand_rule_groups({}), [])


class BuildRuleIndexTest(unittest.TestCase):
    def test_by_service_code(self):
        catalog = _make_rule_catalog(service_codes=["SC001"])
        index = _build_rule_index(catalog)
        self.assertIn("SC001", index["by_service_code"])

    def test_by_key(self):
        catalog = _make_rule_catalog(names=["전기공사업"])
        index = _build_rule_index(catalog)
        self.assertIn("전기공사업", index["by_key"])


class ResolveRuleForIndustryTest(unittest.TestCase):
    def test_by_service_code(self):
        catalog = _make_rule_catalog()
        index = _build_rule_index(catalog)
        rule = _resolve_rule_for_industry({"service_code": "SC001"}, index)
        self.assertIsNotNone(rule)

    def test_by_name(self):
        catalog = _make_rule_catalog()
        index = _build_rule_index(catalog)
        rule = _resolve_rule_for_industry({"service_name": "전기공사업"}, index)
        self.assertIsNotNone(rule)

    def test_by_alias(self):
        catalog = _make_rule_catalog()
        index = _build_rule_index(catalog)
        rule = _resolve_rule_for_industry({"service_name": "전기업"}, index)
        self.assertIsNotNone(rule)

    def test_no_match(self):
        catalog = _make_rule_catalog()
        index = _build_rule_index(catalog)
        rule = _resolve_rule_for_industry({"service_name": "미존재업종"}, index)
        self.assertIsNone(rule)


# ---------------------------------------------------------------------------
# evaluate_registration_diagnosis
# ---------------------------------------------------------------------------
class EvaluateRegistrationDiagnosisTest(unittest.TestCase):
    def _make_rule(self, capital=1.5, tech=3, equip=0, deposit=14):
        return {
            "requirements": {
                "capital_eok": capital,
                "technicians": tech,
                "equipment_count": equip,
                "deposit_days": deposit,
            },
            "typed_criteria": [],
            "pending_criteria_lines": [],
            "document_templates": [],
        }

    def test_all_met(self):
        result = evaluate_registration_diagnosis(
            self._make_rule(),
            current_capital_eok=2.0,
            current_technicians=5,
            current_equipment_count=0,
            base_date=date(2026, 1, 1),
        )
        self.assertTrue(result["capital"]["ok"])
        self.assertTrue(result["technicians"]["ok"])
        self.assertTrue(result["equipment"]["ok"])
        self.assertTrue(result["overall_ok"])

    def test_capital_gap(self):
        result = evaluate_registration_diagnosis(
            self._make_rule(capital=3.0),
            current_capital_eok=1.0,
            current_technicians=5,
            current_equipment_count=0,
            base_date=date(2026, 1, 1),
        )
        self.assertFalse(result["capital"]["ok"])
        self.assertEqual(result["capital"]["gap"], 2.0)
        self.assertFalse(result["overall_ok"])

    def test_technician_gap(self):
        result = evaluate_registration_diagnosis(
            self._make_rule(tech=5),
            current_capital_eok=2.0,
            current_technicians=2,
            current_equipment_count=0,
            base_date=date(2026, 1, 1),
        )
        self.assertFalse(result["technicians"]["ok"])
        self.assertEqual(result["technicians"]["gap"], 3)

    def test_expected_date(self):
        result = evaluate_registration_diagnosis(
            self._make_rule(deposit=30),
            current_capital_eok=2.0,
            current_technicians=5,
            current_equipment_count=0,
            base_date=date(2026, 3, 1),
        )
        self.assertEqual(result["expected_diagnosis_date"], "2026-03-31")

    def test_suspicious_capital_over_3x(self):
        result = evaluate_registration_diagnosis(
            self._make_rule(capital=1.0),
            current_capital_eok=5.0,
            current_technicians=3,
            current_equipment_count=0,
            raw_capital_input="5",
            base_date=date(2026, 1, 1),
        )
        self.assertTrue(result["capital_input_suspicious"])

    def test_zero_inputs(self):
        result = evaluate_registration_diagnosis(
            self._make_rule(),
            current_capital_eok=0,
            current_technicians=0,
            current_equipment_count=0,
            base_date=date(2026, 1, 1),
        )
        self.assertFalse(result["capital"]["ok"])
        self.assertFalse(result["technicians"]["ok"])


# ---------------------------------------------------------------------------
# _compact_critical_prompt_lens
# ---------------------------------------------------------------------------
class CompactCriticalPromptLensTest(unittest.TestCase):
    def test_basic(self):
        packet = {
            "compact_decision_lens": {
                "lane_id": "L1",
                "lane_title": "Title",
                "bottleneck_statement": "Problem",
                "founder_questions": ["Q1", "Q2", "Q3", "Q4"],
                "anti_patterns": ["A1", "A2", "A3", "A4"],
                "evidence_first": ["E1"],
            },
            "summary": {"compact_lens_ready": True},
        }
        result = _compact_critical_prompt_lens(packet)
        self.assertEqual(result["lane_id"], "L1")
        self.assertLessEqual(len(result["founder_questions"]), 3)
        self.assertLessEqual(len(result["anti_patterns"]), 3)
        self.assertTrue(result["lens_ready"])

    def test_empty(self):
        self.assertEqual(_compact_critical_prompt_lens({}), {})

    def test_none(self):
        self.assertEqual(_compact_critical_prompt_lens(None), {})


# ---------------------------------------------------------------------------
# _build_selector_catalog
# ---------------------------------------------------------------------------
class BuildSelectorCatalogTest(unittest.TestCase):
    def _make_entry(self, code="SC001", name="전기공사업"):
        return {
            "service_code": code,
            "service_name": name,
            "major_code": "A",
            "major_name": "건설",
            "group_name": "",
            "has_rule": True,
            "is_rules_only": False,
            "candidate_criteria_count": 0,
            "selector_kind": "focus",
            "selector_code": f"SEL::FOCUS::{code}",
            "canonical_service_code": code,
            "selector_category_code": "SEL-FOCUS",
            "selector_category_name": "핵심 업종군",
        }

    def test_focus_only(self):
        entries = [self._make_entry()]
        result = _build_selector_catalog(entries, [])
        self.assertEqual(len(result["major_categories"]), 1)
        self.assertEqual(result["summary"]["selector_focus_total"], 1)
        self.assertEqual(result["summary"]["selector_inferred_total"], 0)

    def test_both(self):
        focus = [self._make_entry("F1", "전기")]
        inferred = [self._make_entry("I1", "소방")]
        result = _build_selector_catalog(focus, inferred)
        self.assertEqual(len(result["major_categories"]), 2)
        self.assertEqual(result["summary"]["selector_entry_total"], 2)

    def test_empty(self):
        result = _build_selector_catalog([], [])
        self.assertEqual(len(result["industries"]), 0)


# ---------------------------------------------------------------------------
# _normalize_selector_alias
# ---------------------------------------------------------------------------
class NormalizeSelectorAliasTest(unittest.TestCase):
    def test_basic(self):
        row = {"service_code": "SC001", "service_name": "전기공사업", "selector_kind": "focus", "major_code": "A", "major_name": "건설"}
        result = _normalize_selector_alias(row)
        self.assertEqual(result["selector_code"], "SC001")
        self.assertEqual(result["selector_category_code"], "A")


# ---------------------------------------------------------------------------
# _replace_first_block
# ---------------------------------------------------------------------------
class ReplaceFirstBlockTest(unittest.TestCase):
    def test_basic(self):
        result = _replace_first_block("hello world", r"world", "there")
        self.assertEqual(result, "hello there")

    def test_only_first(self):
        result = _replace_first_block("a b a b", r"a", "x")
        self.assertEqual(result, "x b a b")

    def test_no_match(self):
        result = _replace_first_block("hello", r"xyz", "abc")
        self.assertEqual(result, "hello")


# ---------------------------------------------------------------------------
# _scope_embed_css
# ---------------------------------------------------------------------------
class ScopeEmbedCssTest(unittest.TestCase):
    def test_basic_selector(self):
        css = ".button { color: red; }"
        result = _scope_embed_css(css, "#wrap")
        self.assertIn("#wrap .button", result)

    def test_root_replaced(self):
        css = ":root { --color: blue; }"
        result = _scope_embed_css(css, "#wrap")
        self.assertIn("#wrap {", result)
        self.assertNotIn(":root", result)

    def test_body_replaced(self):
        css = "body { margin: 0; }"
        result = _scope_embed_css(css, "#wrap")
        self.assertIn("#wrap {", result)

    def test_star_expanded(self):
        css = "* { box-sizing: border-box; }"
        result = _scope_embed_css(css, "#wrap")
        self.assertIn("#wrap", result)
        self.assertIn("#wrap *", result)

    def test_media_query_not_scoped(self):
        css = "@media (max-width: 768px) {\n  .x { color: red; }\n}"
        result = _scope_embed_css(css, "#wrap")
        # @media should not be prefixed with #wrap
        self.assertNotIn("#wrap @media", result)


if __name__ == "__main__":
    unittest.main()
