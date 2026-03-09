"""Unit tests for core_engine.permit_criteria_schema.

This module is the typed_criteria evaluation engine used by the permit
diagnosis calculator.  Tests cover type coercion, input alias resolution,
criterion normalization, operator evaluation, and the full evaluation pipeline.
"""
import unittest
from datetime import date

from core_engine.permit_criteria_schema import (
    _coerce_value,
    _evaluate_operator,
    _normalize_criterion,
    _resolve_input,
    _safe_list,
    _to_bool,
    _to_float,
    _to_int,
    evaluate_typed_criteria,
)


# ── Type conversion helpers ──────────────────────────────────────────


class ToFloatTest(unittest.TestCase):
    def test_int(self):
        self.assertEqual(_to_float(5), 5.0)

    def test_string_number(self):
        self.assertEqual(_to_float("3.14"), 3.14)

    def test_none_returns_none(self):
        self.assertIsNone(_to_float(None))

    def test_nan_returns_none(self):
        self.assertIsNone(_to_float(float("nan")))

    def test_garbage_returns_none(self):
        self.assertIsNone(_to_float("abc"))


class ToIntTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_to_int(7), 7)

    def test_float_truncated(self):
        self.assertEqual(_to_int(3.9), 3)

    def test_string_number(self):
        self.assertEqual(_to_int("10"), 10)

    def test_none_returns_none(self):
        self.assertIsNone(_to_int(None))


class ToBoolTest(unittest.TestCase):
    def test_true_values(self):
        for val in [True, "1", "true", "yes", "on", "y"]:
            self.assertTrue(_to_bool(val), f"Expected True for {val!r}")

    def test_false_values(self):
        for val in [False, "0", "false", "no", "off", "n"]:
            self.assertFalse(_to_bool(val), f"Expected False for {val!r}")

    def test_none_returns_none(self):
        self.assertIsNone(_to_bool(None))

    def test_ambiguous_returns_none(self):
        self.assertIsNone(_to_bool("maybe"))


class SafeListTest(unittest.TestCase):
    def test_list_passthrough(self):
        self.assertEqual(_safe_list([1, 2]), [1, 2])

    def test_none_returns_empty(self):
        self.assertEqual(_safe_list(None), [])

    def test_scalar_wrapped(self):
        self.assertEqual(_safe_list("single"), ["single"])


# ── Input alias resolution ───────────────────────────────────────────


class ResolveInputTest(unittest.TestCase):
    def test_direct_key(self):
        self.assertEqual(_resolve_input({"capital_eok": 1.5}, "capital_eok"), 1.5)

    def test_alias_fallback(self):
        self.assertEqual(
            _resolve_input({"current_capital_eok": 2.0}, "capital_eok"), 2.0
        )

    def test_missing_returns_none(self):
        self.assertIsNone(_resolve_input({}, "capital_eok"))

    def test_empty_key_returns_none(self):
        self.assertIsNone(_resolve_input({"a": 1}, ""))


# ── Criterion normalization ──────────────────────────────────────────


class NormalizeCriterionTest(unittest.TestCase):
    def test_valid_criterion(self):
        raw = {
            "criterion_id": "capital",
            "input_key": "capital_eok",
            "operator": ">=",
            "required_value": 1.5,
            "category": "core_requirement",
            "label": "자본금",
            "value_type": "number",
            "unit": "억원",
            "blocking": True,
            "evidence_types": ["재무제표"],
            "basis_refs": ["전기공사업법 시행령 별표 1"],
        }
        result = _normalize_criterion(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result["criterion_id"], "capital")
        self.assertEqual(result["input_key"], "capital_eok")
        self.assertEqual(result["operator"], ">=")
        self.assertEqual(result["required_value"], 1.5)
        self.assertEqual(result["blocking"], True)

    def test_missing_criterion_id_returns_none(self):
        self.assertIsNone(_normalize_criterion({"input_key": "x"}))

    def test_missing_input_key_returns_none(self):
        self.assertIsNone(_normalize_criterion({"criterion_id": "x"}))

    def test_non_dict_returns_none(self):
        self.assertIsNone(_normalize_criterion("not a dict"))

    def test_operator_defaults_to_gte(self):
        result = _normalize_criterion({"criterion_id": "a", "input_key": "b"})
        self.assertEqual(result["operator"], ">=")

    def test_value_type_defaults_to_number(self):
        result = _normalize_criterion({"criterion_id": "a", "input_key": "b"})
        self.assertEqual(result["value_type"], "number")


# ── Coerce value ─────────────────────────────────────────────────────


class CoerceValueTest(unittest.TestCase):
    def test_number_default(self):
        self.assertEqual(_coerce_value("5", "number"), 5.0)

    def test_int_type(self):
        self.assertEqual(_coerce_value("3.7", "int"), 3)

    def test_bool_type(self):
        self.assertTrue(_coerce_value("yes", "bool"))

    def test_string_type(self):
        self.assertEqual(_coerce_value(42, "string"), "42")

    def test_list_type(self):
        self.assertEqual(_coerce_value("a", "list"), ["a"])

    def test_none_passthrough(self):
        self.assertIsNone(_coerce_value(None, "number"))


# ── Operator evaluation ──────────────────────────────────────────────


class EvaluateOperatorTest(unittest.TestCase):
    def test_gte_pass(self):
        r = _evaluate_operator(2.0, 1.5, ">=", "number")
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], "pass")
        self.assertEqual(r["gap"], 0)

    def test_gte_fail(self):
        r = _evaluate_operator(1.0, 1.5, ">=", "number")
        self.assertFalse(r["ok"])
        self.assertEqual(r["status"], "fail")
        self.assertAlmostEqual(r["gap"], 0.5)

    def test_lte_pass(self):
        r = _evaluate_operator(1.0, 2.0, "<=", "number")
        self.assertTrue(r["ok"])

    def test_eq_pass(self):
        r = _evaluate_operator("a", "a", "==", "string")
        self.assertTrue(r["ok"])

    def test_neq_pass(self):
        r = _evaluate_operator("a", "b", "!=", "string")
        self.assertTrue(r["ok"])

    def test_truthy_pass(self):
        r = _evaluate_operator(True, None, "truthy", "bool")
        self.assertTrue(r["ok"])

    def test_truthy_fail(self):
        r = _evaluate_operator(False, None, "truthy", "bool")
        self.assertFalse(r["ok"])

    def test_contains_pass(self):
        r = _evaluate_operator(["a", "b", "c"], ["a", "b"], "contains", "list")
        self.assertTrue(r["ok"])

    def test_in_pass(self):
        r = _evaluate_operator("a", ["a", "b", "c"], "in", "list")
        self.assertTrue(r["ok"])

    def test_missing_input_returns_missing(self):
        r = _evaluate_operator(None, 1.5, ">=", "number")
        self.assertEqual(r["status"], "missing_input")
        self.assertIsNone(r["ok"])

    def test_required_none_comparison_returns_manual_review(self):
        r = _evaluate_operator(2.0, None, ">=", "number")
        self.assertEqual(r["status"], "manual_review")
        self.assertIsNone(r["ok"])

    def test_required_none_eq_returns_manual_review(self):
        r = _evaluate_operator("a", None, "==", "string")
        self.assertEqual(r["status"], "manual_review")

    def test_in_empty_current_fails(self):
        r = _evaluate_operator([], ["a", "b"], "in", "list")
        self.assertFalse(r["ok"])
        self.assertEqual(r["status"], "fail")

    def test_in_nonempty_current_pass(self):
        r = _evaluate_operator(["a"], ["a", "b"], "in", "list")
        self.assertTrue(r["ok"])

    def test_operator_case_insensitive_contains(self):
        r = _evaluate_operator(["a", "b", "c"], ["a"], "CONTAINS", "list")
        self.assertTrue(r["ok"])

    def test_operator_uppercase_truthy(self):
        r = _evaluate_operator(True, None, "TRUTHY", "bool")
        self.assertTrue(r["ok"])

    # -- Regression: Bug2 — contains/in with required=None → manual_review --
    def test_contains_required_none_returns_manual_review(self):
        r = _evaluate_operator(["a", "b"], None, "contains", "list")
        self.assertEqual(r["status"], "manual_review")
        self.assertIsNone(r["ok"])

    def test_in_required_none_returns_manual_review(self):
        r = _evaluate_operator("a", None, "in", "list")
        self.assertEqual(r["status"], "manual_review")
        self.assertIsNone(r["ok"])

    # -- Regression: Bug6 — float precision tolerance in >=/<= --
    def test_gte_float_precision_boundary(self):
        """1.4999999999999998 should pass >= 1.5 (IEEE 754 tolerance)."""
        r = _evaluate_operator(1.4999999999999998, 1.5, ">=", "number")
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], "pass")
        self.assertEqual(r["gap"], 0)

    def test_lte_float_precision_boundary(self):
        """1.5000000000000002 should pass <= 1.5 (IEEE 754 tolerance)."""
        r = _evaluate_operator(1.5000000000000002, 1.5, "<=", "number")
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], "pass")
        self.assertEqual(r["gap"], 0)

    def test_gte_genuine_fail_not_affected(self):
        """Genuine shortfall (1.0 vs 1.5) should still fail."""
        r = _evaluate_operator(1.0, 1.5, ">=", "number")
        self.assertFalse(r["ok"])
        self.assertEqual(r["status"], "fail")
        self.assertAlmostEqual(r["gap"], 0.5)

    def test_lte_genuine_fail_not_affected(self):
        """Genuine overshoot (2.0 vs 1.5) should still fail."""
        r = _evaluate_operator(2.0, 1.5, "<=", "number")
        self.assertFalse(r["ok"])
        self.assertEqual(r["status"], "fail")
        self.assertAlmostEqual(r["gap"], 0.5)


# ── Full evaluation pipeline ─────────────────────────────────────────


class EvaluateTypedCriteriaTest(unittest.TestCase):
    """Integration test for evaluate_typed_criteria."""

    def _make_rule(self, typed_criteria, **kwargs):
        rule = {"typed_criteria": typed_criteria}
        rule.update(kwargs)
        return rule

    def test_all_pass(self):
        rule = self._make_rule([
            {"criterion_id": "capital", "input_key": "capital_eok", "operator": ">=", "required_value": 1.5, "blocking": True},
            {"criterion_id": "technicians", "input_key": "technicians", "operator": ">=", "required_value": 3, "blocking": True},
        ])
        inputs = {"capital_eok": 2.0, "technicians": 5}
        result = evaluate_typed_criteria(rule, inputs, base_date=date(2026, 3, 9))
        self.assertEqual(result["overall_status"], "pass")
        self.assertEqual(result["blocking_failure_count"], 0)
        self.assertEqual(result["typed_criteria_total"], 2)

    def test_shortfall_when_below_requirement(self):
        rule = self._make_rule([
            {"criterion_id": "capital", "input_key": "capital_eok", "operator": ">=", "required_value": 1.5, "blocking": True},
        ])
        inputs = {"capital_eok": 0.5}
        result = evaluate_typed_criteria(rule, inputs)
        self.assertEqual(result["overall_status"], "shortfall")
        self.assertEqual(result["blocking_failure_count"], 1)
        criterion = result["criterion_results"][0]
        self.assertAlmostEqual(criterion["gap"], 1.0)

    def test_manual_review_when_missing_input(self):
        rule = self._make_rule([
            {"criterion_id": "capital", "input_key": "capital_eok", "operator": ">=", "required_value": 1.5, "blocking": True},
        ])
        inputs = {}  # No capital_eok provided
        result = evaluate_typed_criteria(rule, inputs)
        self.assertEqual(result["overall_status"], "manual_review")
        self.assertEqual(result["unknown_blocking_count"], 1)

    def test_evidence_checklist_generated_on_failure(self):
        rule = self._make_rule([
            {
                "criterion_id": "office",
                "input_key": "office_secured",
                "operator": "truthy",
                "value_type": "bool",
                "blocking": True,
                "evidence_types": ["임대차계약서", "사업장 사진"],
            },
        ])
        inputs = {"office_secured": False}
        result = evaluate_typed_criteria(rule, inputs)
        self.assertTrue(len(result["evidence_checklist"]) >= 2)
        labels = [item["label"] for item in result["evidence_checklist"]]
        self.assertIn("임대차계약서", labels)
        self.assertIn("사업장 사진", labels)

    def test_expected_date_calculated(self):
        rule = self._make_rule([])
        inputs = {"deposit_days": 30}
        result = evaluate_typed_criteria(rule, inputs, base_date=date(2026, 3, 9))
        self.assertEqual(result["expected_diagnosis_date"], "2026-04-08")

    def test_empty_typed_criteria(self):
        rule = self._make_rule([])
        result = evaluate_typed_criteria(rule, {})
        self.assertEqual(result["overall_status"], "pass")
        self.assertEqual(result["typed_criteria_total"], 0)

    def test_alias_resolution_works(self):
        """current_capital_eok should be resolved as alias for capital_eok."""
        rule = self._make_rule([
            {"criterion_id": "capital", "input_key": "capital_eok", "operator": ">=", "required_value": 1.0, "blocking": True},
        ])
        inputs = {"current_capital_eok": 2.0}
        result = evaluate_typed_criteria(rule, inputs)
        self.assertEqual(result["overall_status"], "pass")

    def test_pending_criteria_trigger_manual_review(self):
        rule = self._make_rule(
            [],
            pending_criteria_lines=[{"text": "추가기준", "category": "etc"}],
        )
        result = evaluate_typed_criteria(rule, {})
        self.assertTrue(result["manual_review_required"])
        self.assertIn("추가 등록기준 구조화가 완료될 때까지 전문가 검토가 필요합니다.", result["next_actions"])

    # -- Regression: Bug8 — blocking manual_review counted as unknown --
    def test_blocking_manual_review_counted(self):
        """Blocking criterion with required=None + user input → manual_review overall."""
        rule = self._make_rule([
            {
                "criterion_id": "tech_check",
                "input_key": "technicians",
                "operator": ">=",
                "required_value": None,  # threshold undefined
                "blocking": True,
            },
        ])
        inputs = {"technicians": 3}
        result = evaluate_typed_criteria(rule, inputs)
        self.assertEqual(result["unknown_blocking_count"], 1)
        self.assertEqual(result["overall_status"], "manual_review")

    # -- Regression: Bug4 — doc_id includes input_key to avoid collision --
    def test_doc_id_includes_input_key(self):
        """Two criteria with same criterion_id but different input_key → distinct doc_ids."""
        rule = self._make_rule([
            {
                "criterion_id": "facility.secured.auto",
                "input_key": "office_secured",
                "operator": "truthy",
                "value_type": "bool",
                "blocking": True,
                "evidence_types": ["임대차계약서"],
            },
            {
                "criterion_id": "facility.secured.auto",
                "input_key": "facility_secured",
                "operator": "truthy",
                "value_type": "bool",
                "blocking": True,
                "evidence_types": ["시설확인서"],
            },
        ])
        inputs = {"office_secured": False, "facility_secured": False}
        result = evaluate_typed_criteria(rule, inputs)
        doc_ids = [item["doc_id"] for item in result["evidence_checklist"]]
        # Should have 2 distinct doc_ids despite same criterion_id
        self.assertEqual(len(doc_ids), 2)
        self.assertNotEqual(doc_ids[0], doc_ids[1])
        self.assertIn("office_secured", doc_ids[0])
        self.assertIn("facility_secured", doc_ids[1])


if __name__ == "__main__":
    unittest.main()
