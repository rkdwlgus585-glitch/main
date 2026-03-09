"""Unit tests for permit_precheck_api.py pure functions.

Covers: string normalization, type coercion, boolean flags, data projection,
input canonicalization, and usage store helpers.
"""

import json
import math
import unittest

import permit_precheck_api as api


# ===================================================================
# _compact
# ===================================================================
class CompactTest(unittest.TestCase):
    def test_normal_string(self):
        self.assertEqual(api._compact("hello"), "hello")

    def test_none(self):
        self.assertEqual(api._compact(None), "")

    def test_whitespace_normalization(self):
        self.assertEqual(api._compact("  hello   world  "), "hello world")

    def test_multiline(self):
        self.assertEqual(api._compact("line1\n  line2\tline3"), "line1 line2 line3")

    def test_limit(self):
        result = api._compact("abcdef", limit=3)
        self.assertEqual(len(result), 3)

    def test_limit_zero_no_truncation(self):
        long = "x" * 5000
        self.assertEqual(api._compact(long, limit=0), long)

    def test_number_input(self):
        self.assertEqual(api._compact(42), "42")

    def test_empty_string(self):
        self.assertEqual(api._compact(""), "")


# ===================================================================
# _json_dumps_compact
# ===================================================================
class JsonDumpsCompactTest(unittest.TestCase):
    def test_dict(self):
        result = api._json_dumps_compact({"a": 1})
        self.assertIn('"a"', result)
        # No spaces in compact format
        self.assertNotIn(": ", result)

    def test_invalid_type(self):
        result = api._json_dumps_compact(set([1, 2]))
        self.assertEqual(result, "{}")

    def test_korean(self):
        result = api._json_dumps_compact({"이름": "테스트"})
        self.assertIn("이름", result)  # ensure_ascii=False


# ===================================================================
# _first_present
# ===================================================================
class FirstPresentTest(unittest.TestCase):
    def test_first_key_found(self):
        self.assertEqual(api._first_present({"a": 1, "b": 2}, "a", "b"), 1)

    def test_fallback_key(self):
        self.assertEqual(api._first_present({"b": 2}, "a", "b"), 2)

    def test_none_value_skipped(self):
        self.assertEqual(api._first_present({"a": None, "b": 2}, "a", "b"), 2)

    def test_no_match(self):
        self.assertIsNone(api._first_present({"a": 1}, "x", "y"))

    def test_non_dict(self):
        self.assertIsNone(api._first_present("not a dict", "a"))

    def test_empty_dict(self):
        self.assertIsNone(api._first_present({}, "a"))


# ===================================================================
# _coerce_bool_flag
# ===================================================================
class CoerceBoolFlagTest(unittest.TestCase):
    def test_true_bool(self):
        self.assertEqual(api._coerce_bool_flag(True), 1)

    def test_false_bool(self):
        self.assertEqual(api._coerce_bool_flag(False), 0)

    def test_none(self):
        self.assertIsNone(api._coerce_bool_flag(None))

    def test_int_1(self):
        self.assertEqual(api._coerce_bool_flag(1), 1)

    def test_int_0(self):
        self.assertEqual(api._coerce_bool_flag(0), 0)

    def test_string_true(self):
        self.assertEqual(api._coerce_bool_flag("true"), 1)

    def test_string_false(self):
        self.assertEqual(api._coerce_bool_flag("false"), 0)

    def test_string_yes(self):
        self.assertEqual(api._coerce_bool_flag("yes"), 1)

    def test_string_no(self):
        self.assertEqual(api._coerce_bool_flag("no"), 0)

    def test_string_on(self):
        self.assertEqual(api._coerce_bool_flag("on"), 1)

    def test_string_off(self):
        self.assertEqual(api._coerce_bool_flag("off"), 0)

    def test_string_1(self):
        self.assertEqual(api._coerce_bool_flag("1"), 1)

    def test_string_0(self):
        self.assertEqual(api._coerce_bool_flag("0"), 0)

    def test_unrecognized(self):
        self.assertIsNone(api._coerce_bool_flag("maybe"))

    def test_float_1(self):
        self.assertEqual(api._coerce_bool_flag(1.0), 1)

    def test_case_insensitive(self):
        self.assertEqual(api._coerce_bool_flag("TRUE"), 1)
        self.assertEqual(api._coerce_bool_flag("Yes"), 1)


# ===================================================================
# _coerce_int_or_none
# ===================================================================
class CoerceIntOrNoneTest(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(api._coerce_int_or_none(None))

    def test_int(self):
        self.assertEqual(api._coerce_int_or_none(5), 5)

    def test_float(self):
        self.assertEqual(api._coerce_int_or_none(3.7), 3)

    def test_string(self):
        self.assertEqual(api._coerce_int_or_none("10"), 10)

    def test_invalid(self):
        self.assertIsNone(api._coerce_int_or_none("abc"))

    def test_empty_string(self):
        self.assertIsNone(api._coerce_int_or_none(""))

    def test_float_string(self):
        self.assertEqual(api._coerce_int_or_none("3.5"), 3)


# ===================================================================
# _coerce_float_or_none
# ===================================================================
class CoerceFloatOrNoneTest(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(api._coerce_float_or_none(None))

    def test_int(self):
        self.assertAlmostEqual(api._coerce_float_or_none(5), 5.0)

    def test_float(self):
        self.assertAlmostEqual(api._coerce_float_or_none(3.14), 3.14)

    def test_string(self):
        self.assertAlmostEqual(api._coerce_float_or_none("2.5"), 2.5)

    def test_nan_filtered(self):
        self.assertIsNone(api._coerce_float_or_none(float("nan")))

    def test_invalid(self):
        self.assertIsNone(api._coerce_float_or_none("abc"))

    def test_inf(self):
        result = api._coerce_float_or_none(float("inf"))
        self.assertTrue(math.isinf(result))


# ===================================================================
# _required_ok_flag
# ===================================================================
class RequiredOkFlagTest(unittest.TestCase):
    def test_ok_true(self):
        summary = {"capital": {"ok": True}}
        self.assertEqual(api._required_ok_flag(summary, "capital"), "1")

    def test_ok_false(self):
        summary = {"capital": {"ok": False}}
        self.assertEqual(api._required_ok_flag(summary, "capital"), "0")

    def test_missing_key(self):
        self.assertEqual(api._required_ok_flag({}, "capital"), "0")

    def test_none_summary(self):
        self.assertEqual(api._required_ok_flag(None, "capital"), "0")

    def test_nested_none(self):
        summary = {"capital": None}
        self.assertEqual(api._required_ok_flag(summary, "capital"), "0")

    def test_ok_string_true(self):
        summary = {"tech": {"ok": "true"}}
        self.assertEqual(api._required_ok_flag(summary, "tech"), "1")


# ===================================================================
# _canonical_permit_input_snapshot
# ===================================================================
class CanonicalPermitInputSnapshotTest(unittest.TestCase):
    def test_basic_fields(self):
        inputs = {
            "service_code": "SC001",
            "service_name": "전기공사업",
            "capital_eok": 1.5,
            "technicians_count": 3,
        }
        result = api._canonical_permit_input_snapshot(inputs, {})
        self.assertEqual(result["service_code"], "SC001")
        self.assertEqual(result["service_name"], "전기공사업")
        self.assertAlmostEqual(result["capital_eok"], 1.5)
        self.assertEqual(result["technicians_count"], 3)

    def test_fallback_keys(self):
        inputs = {"current_capital_eok": 2.0, "current_technicians": 5}
        result = api._canonical_permit_input_snapshot(inputs, {})
        self.assertAlmostEqual(result["capital_eok"], 2.0)
        self.assertEqual(result["technicians_count"], 5)

    def test_industry_name_from_result(self):
        inputs = {}
        result_dict = {"industry_name": "소방시설공사업"}
        snapshot = api._canonical_permit_input_snapshot(inputs, result_dict)
        self.assertEqual(snapshot["industry_name"], "소방시설공사업")

    def test_service_name_fallback_to_industry(self):
        inputs = {"industry_name": "토목공사업"}
        snapshot = api._canonical_permit_input_snapshot(inputs, {})
        self.assertEqual(snapshot["service_name"], "토목공사업")

    def test_bool_coercion(self):
        inputs = {"office_secured": "true", "facility_secured": 0}
        snapshot = api._canonical_permit_input_snapshot(inputs, {})
        self.assertEqual(snapshot["office_secured"], 1)
        self.assertEqual(snapshot["facility_secured"], 0)

    def test_empty_inputs(self):
        snapshot = api._canonical_permit_input_snapshot({}, {})
        self.assertEqual(snapshot["service_code"], "")
        self.assertIsNone(snapshot["capital_eok"])
        self.assertIsNone(snapshot["technicians_count"])


# ===================================================================
# _result_summary_payload
# ===================================================================
class ResultSummaryPayloadTest(unittest.TestCase):
    def test_full_result(self):
        result = {
            "ok": True,
            "industry_name": "전기공사업",
            "group_rule_id": "R001",
            "overall_status": "pass",
            "overall_ok": True,
            "manual_review_required": False,
            "coverage_status": "full",
            "mapping_confidence": 0.95,
            "typed_criteria_total": 5,
            "pending_criteria_count": 0,
            "blocking_failure_count": 0,
            "unknown_blocking_count": 0,
            "capital_input_suspicious": False,
            "next_actions": ["review_docs"],
        }
        payload = api._result_summary_payload(result)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["industry_name"], "전기공사업")
        self.assertTrue(payload["overall_ok"])
        self.assertEqual(payload["typed_criteria_total"], 5)
        self.assertEqual(payload["next_actions"], ["review_docs"])

    def test_empty_result(self):
        payload = api._result_summary_payload({})
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["industry_name"], "")
        self.assertFalse(payload["overall_ok"])
        self.assertEqual(payload["next_actions"], [])

    def test_none_next_actions(self):
        payload = api._result_summary_payload({"next_actions": None})
        self.assertEqual(payload["next_actions"], [])

    def test_type_coercion(self):
        payload = api._result_summary_payload({
            "typed_criteria_total": "7",
            "blocking_failure_count": 2.5,
        })
        self.assertEqual(payload["typed_criteria_total"], 7)
        self.assertEqual(payload["blocking_failure_count"], 2)


# ===================================================================
# PermitUsageStore._token_estimate (via instance)
# ===================================================================
class TokenEstimateTest(unittest.TestCase):
    def _store(self, thresholds=None):
        store = object.__new__(api.PermitUsageStore)
        store._thresholds = thresholds or {}
        store._db_path = ":memory:"
        store._db = None
        return store

    def test_ok_default(self):
        self.assertEqual(self._store()._token_estimate(True), 900)

    def test_error_default(self):
        self.assertEqual(self._store()._token_estimate(False), 200)

    def test_custom_ok(self):
        store = self._store({"token_estimates": {"permit_ok": 500}})
        self.assertEqual(store._token_estimate(True), 500)

    def test_custom_error(self):
        store = self._store({"token_estimates": {"error": 100}})
        self.assertEqual(store._token_estimate(False), 100)


# ===================================================================
# PermitUsageStore._plan_config
# ===================================================================
class PlanConfigTest(unittest.TestCase):
    def _store(self, thresholds=None):
        store = object.__new__(api.PermitUsageStore)
        store._thresholds = thresholds or {}
        store._db_path = ":memory:"
        store._db = None
        return store

    def test_valid_plan(self):
        store = self._store({"plans": {"free": {"max_usage_events": 10}}})
        config = store._plan_config("free")
        self.assertEqual(config["max_usage_events"], 10)

    def test_missing_plan(self):
        store = self._store({"plans": {"free": {"max_usage_events": 10}}})
        config = store._plan_config("premium")
        self.assertEqual(config, {})

    def test_no_plans(self):
        config = self._store()._plan_config("free")
        self.assertEqual(config, {})

    def test_case_normalization(self):
        store = self._store({"plans": {"free": {"limit": 5}}})
        config = store._plan_config("FREE")
        self.assertEqual(config["limit"], 5)


# ===================================================================
# PermitUsageStore._protected_tenants
# ===================================================================
class ProtectedTenantsTest(unittest.TestCase):
    def _store(self, thresholds=None):
        store = object.__new__(api.PermitUsageStore)
        store._thresholds = thresholds or {}
        store._db_path = ":memory:"
        store._db = None
        return store

    def test_empty(self):
        self.assertEqual(self._store()._protected_tenants(), set())

    def test_with_tenants(self):
        store = self._store({
            "policy": {"protected_tenants": ["Admin", "internal"]}
        })
        result = store._protected_tenants()
        self.assertIn("admin", result)
        self.assertIn("internal", result)

    def test_non_list(self):
        store = self._store({"policy": {"protected_tenants": "not_list"}})
        self.assertEqual(store._protected_tenants(), set())

    def test_empty_strings_filtered(self):
        store = self._store({
            "policy": {"protected_tenants": ["valid", "", "  "]}
        })
        result = store._protected_tenants()
        self.assertEqual(result, {"valid"})


if __name__ == "__main__":
    unittest.main()
