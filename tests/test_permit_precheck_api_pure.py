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


# ===================================================================
# _env_str / _env_int / _env_bool
# ===================================================================
class EnvStrTest(unittest.TestCase):
    def test_existing_key(self):
        # CONFIG always has PERMIT_PRECHECK_API_HOST
        result = api._env_str("PERMIT_PRECHECK_API_HOST")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_missing_key_default(self):
        self.assertEqual(api._env_str("__NONEXISTENT_KEY__", "fallback"), "fallback")


class EnvIntTest(unittest.TestCase):
    def test_valid_int(self):
        result = api._env_int("PERMIT_PRECHECK_API_PORT", 9999)
        self.assertEqual(result, 8792)

    def test_missing_key_default(self):
        result = api._env_int("__NONEXISTENT_INT_KEY__", 42)
        self.assertEqual(result, 42)


class EnvBoolTest(unittest.TestCase):
    def test_true_values(self):
        orig = api.CONFIG.get("__TEST_BOOL__")
        for val in ("1", "true", "yes", "on", "y"):
            api.CONFIG["__TEST_BOOL__"] = val
            self.assertTrue(api._env_bool("__TEST_BOOL__", False))
        if orig is None:
            api.CONFIG.pop("__TEST_BOOL__", None)

    def test_false_values(self):
        orig = api.CONFIG.get("__TEST_BOOL__")
        for val in ("0", "false", "no", "off", "n"):
            api.CONFIG["__TEST_BOOL__"] = val
            self.assertFalse(api._env_bool("__TEST_BOOL__", True))
        if orig is None:
            api.CONFIG.pop("__TEST_BOOL__", None)

    def test_default_fallback(self):
        result = api._env_bool("__NONEXISTENT_BOOL__", True)
        self.assertTrue(result)


# ===================================================================
# _month_key / _now_iso
# ===================================================================
class MonthKeyTest(unittest.TestCase):
    def test_format(self):
        import re
        key = api._month_key()
        self.assertRegex(key, r"^\d{4}-\d{2}$")


class NowIsoTest(unittest.TestCase):
    def test_format(self):
        import re
        iso = api._now_iso()
        self.assertRegex(iso, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


# ===================================================================
# _channel_id_value / _tenant_id_value / _tenant_plan_key
# ===================================================================
class _MockProfile:
    def __init__(self, channel_id=""):
        self.channel_id = channel_id

class _MockTenant:
    def __init__(self, tenant_id="", plan=""):
        self.tenant_id = tenant_id
        self.plan = plan

class _MockResolution:
    def __init__(self, profile=None, tenant=None):
        self.profile = profile
        self.tenant = tenant


class ChannelIdValueTest(unittest.TestCase):
    def test_with_profile(self):
        res = _MockResolution(profile=_MockProfile("ch-123"))
        self.assertEqual(api._channel_id_value(res), "ch-123")

    def test_none_profile(self):
        res = _MockResolution(profile=None)
        self.assertEqual(api._channel_id_value(res), "")

    def test_no_profile_attr(self):
        self.assertEqual(api._channel_id_value(object()), "")


class TenantIdValueTest(unittest.TestCase):
    def test_with_tenant(self):
        res = _MockResolution(tenant=_MockTenant(tenant_id="t-001"))
        self.assertEqual(api._tenant_id_value(res), "t-001")

    def test_none_tenant(self):
        res = _MockResolution(tenant=None)
        self.assertEqual(api._tenant_id_value(res), "")


class TenantPlanKeyTest(unittest.TestCase):
    def test_with_plan(self):
        res = _MockResolution(tenant=_MockTenant(plan="Premium"))
        self.assertEqual(api._tenant_plan_key(res), "premium")

    def test_none_tenant(self):
        res = _MockResolution(tenant=None)
        self.assertEqual(api._tenant_plan_key(res), "")


# ===================================================================
# _tenant_has_feature / _tenant_has_system / _channel_exposes_system
# ===================================================================
class _MockGateway:
    def check_feature(self, resolution, feature):
        return feature == "allowed_feature"
    def check_system(self, resolution, system):
        return system == "allowed_system"

class _MockChannelRouter:
    def check_system(self, resolution, system):
        return system == "exposed_system"

class _MockServer:
    def __init__(self, gw_enabled=False, gateway=None, router=None):
        self.tenant_gateway_enabled = gw_enabled
        self.tenant_gateway = gateway
        self.channel_router = router


class TenantHasFeatureTest(unittest.TestCase):
    def test_gateway_disabled_returns_true(self):
        server = _MockServer(gw_enabled=False)
        res = _MockResolution()
        self.assertTrue(api._tenant_has_feature(server, res, "anything"))

    def test_gateway_enabled_feature_allowed(self):
        server = _MockServer(gw_enabled=True, gateway=_MockGateway())
        res = _MockResolution()
        self.assertTrue(api._tenant_has_feature(server, res, "allowed_feature"))

    def test_gateway_enabled_feature_denied(self):
        server = _MockServer(gw_enabled=True, gateway=_MockGateway())
        res = _MockResolution()
        self.assertFalse(api._tenant_has_feature(server, res, "denied_feature"))


class TenantHasSystemTest(unittest.TestCase):
    def test_gateway_disabled(self):
        server = _MockServer(gw_enabled=False)
        self.assertTrue(api._tenant_has_system(server, _MockResolution(), "x"))

    def test_gateway_enabled_allowed(self):
        server = _MockServer(gw_enabled=True, gateway=_MockGateway())
        self.assertTrue(api._tenant_has_system(server, _MockResolution(), "allowed_system"))


class ChannelExposesSystemTest(unittest.TestCase):
    def test_no_router_returns_true(self):
        server = _MockServer(router=None)
        self.assertTrue(api._channel_exposes_system(server, _MockResolution(), "x"))

    def test_router_exposed(self):
        server = _MockServer(router=_MockChannelRouter())
        self.assertTrue(api._channel_exposes_system(server, _MockResolution(), "exposed_system"))

    def test_router_not_exposed(self):
        server = _MockServer(router=_MockChannelRouter())
        self.assertFalse(api._channel_exposes_system(server, _MockResolution(), "hidden_system"))


# ===================================================================
# _permit_response_tier
# ===================================================================
class PermitResponseTierTest(unittest.TestCase):
    def test_gateway_disabled(self):
        server = _MockServer(gw_enabled=False)
        self.assertEqual(api._permit_response_tier(server, _MockResolution()), "internal")

    def test_gateway_enabled_internal_feature(self):
        class GW:
            def check_feature(self, res, feat):
                return feat == "permit_precheck_internal"
        server = _MockServer(gw_enabled=True, gateway=GW())
        self.assertEqual(api._permit_response_tier(server, _MockResolution()), "internal")


# ===================================================================
# _partner_health_payload
# ===================================================================
class PartnerHealthPayloadTest(unittest.TestCase):
    def test_structure(self):
        payload = api._partner_health_payload()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], api.SERVICE_NAME)
        self.assertEqual(payload["message"], "healthy")
        self.assertIn("health_contract", payload)


# ===================================================================
# _project_precheck_result — response tier filtering
# ===================================================================
class ProjectPrecheckResultTest(unittest.TestCase):
    def _server_tier(self, tier):
        """Create a mock server that returns a fixed tier."""
        class GW:
            def check_feature(self, res, feat):
                if tier == "internal":
                    return feat == "permit_precheck_internal"
                if tier == "detail":
                    return feat == "permit_precheck_detail"
                return False
        return _MockServer(gw_enabled=True, gateway=GW())

    def _resolution(self):
        return _MockResolution(
            tenant=_MockTenant(tenant_id="t-001", plan="pro"),
        )

    def test_error_result_includes_policy(self):
        server = _MockServer(gw_enabled=False)
        result = api._project_precheck_result(
            server, self._resolution(), {"ok": False, "error": "test"}
        )
        self.assertIn("response_policy", result)
        self.assertFalse(result["ok"])

    def test_summary_tier_trims_fields(self):
        server = self._server_tier("summary")
        # Use a resolution with plan != "pro"/"pro_internal" to get summary tier
        res = _MockResolution(tenant=_MockTenant(tenant_id="t-001", plan="basic"))
        full_result = {
            "ok": True,
            "service_code": "SC1",
            "industry_name": "Test",
            "overall_status": "pass",
            "overall_ok": True,
            "manual_review_required": False,
            "coverage_status": "full",
            "typed_overall_status": "pass",
            "typed_criteria_total": 3,
            "pending_criteria_count": 0,
            "blocking_failure_count": 0,
            "unknown_blocking_count": 0,
            "capital_input_suspicious": False,
            "next_actions": [],
            # Fields that should be trimmed in summary tier:
            "criterion_results": [{"id": "1"}],
            "evidence_checklist": [{"id": "2"}],
            "pending_criteria_lines": [{"text": "x"}],
        }
        result = api._project_precheck_result(server, res, full_result)
        # criterion_results should NOT be in summary tier
        self.assertNotIn("criterion_results", result)
        self.assertNotIn("evidence_checklist", result)
        self.assertEqual(result["response_policy"]["tier"], "summary")

    def test_internal_tier_includes_tenant_id(self):
        server = _MockServer(gw_enabled=False)  # disabled → internal
        result = api._project_precheck_result(
            server, self._resolution(), {"ok": True, "data": "full"}
        )
        self.assertEqual(result.get("tenant_id"), "t-001")
        self.assertEqual(result["response_policy"]["tier"], "internal")

    def test_detail_tier_strips_pending_lines(self):
        server = self._server_tier("detail")
        result = api._project_precheck_result(
            server, self._resolution(),
            {"ok": True, "pending_criteria_lines": [{"text": "x"}], "data": "y"},
        )
        self.assertNotIn("pending_criteria_lines", result)
        self.assertEqual(result["response_policy"]["tier"], "detail")

    def test_none_result(self):
        server = _MockServer(gw_enabled=False)
        result = api._project_precheck_result(server, self._resolution(), None)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
