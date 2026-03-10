import unittest

from core_engine.api_response import build_response_envelope


class ApiResponseContractTests(unittest.TestCase):
    def test_envelope_adds_response_meta_and_data_copy(self):
        payload = {
            "ok": True,
            "estimate_center_eok": 1.8,
            "response_policy": {
                "tier": "detail",
                "tenant_plan": "pro",
            },
        }

        result = build_response_envelope(
            payload,
            service="yangdo_blackbox_api",
            api_version="v1",
            request_id="req_123",
            channel_id="seoul_web",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["service"], "yangdo_blackbox_api")
        self.assertEqual(result["api_version"], "v1")
        self.assertEqual(result["request_id"], "req_123")
        self.assertEqual(result["channel_id"], "seoul_web")
        self.assertIn("data", result)
        self.assertIsNot(result["data"], payload)
        self.assertEqual(result["data"]["estimate_center_eok"], 1.8)
        self.assertEqual(result["response_meta"]["tenant_plan"], "pro")
        self.assertEqual(result["response_meta"]["response_tier"], "detail")
        self.assertEqual(result["response_meta"]["status"], "ok")

    def test_explicit_args_override_policy_and_error_status(self):
        payload = {
            "ok": False,
            "response_policy": {
                "tier": "summary",
                "tenant_plan": "standard",
            },
        }

        result = build_response_envelope(
            payload,
            service="permit_precheck_api",
            api_version="v1",
            request_id="req_err",
            channel_id="partner_template",
            tenant_plan="pro_internal",
            response_tier="internal",
        )

        self.assertEqual(result["response_meta"]["tenant_plan"], "pro_internal")
        self.assertEqual(result["response_meta"]["response_tier"], "internal")
        self.assertEqual(result["response_meta"]["channel_id"], "partner_template")
        self.assertEqual(result["response_meta"]["status"], "error")


    def test_none_payload_returns_valid_envelope(self):
        result = build_response_envelope(
            None,
            service="yangdo_blackbox_api",
            api_version="v1",
            request_id="req_nil",
        )
        self.assertIn("response_meta", result)
        self.assertIn("data", result)
        self.assertEqual(result["response_meta"]["service"], "yangdo_blackbox_api")
        self.assertEqual(result["response_meta"]["status"], "error")

    def test_empty_payload_returns_valid_envelope(self):
        result = build_response_envelope(
            {},
            service="permit_precheck_api",
            api_version="v1",
            request_id="req_empty",
        )
        self.assertIn("response_meta", result)
        self.assertEqual(result["response_meta"]["status"], "error")
        self.assertEqual(result["response_meta"]["channel_id"], "")

    def test_channel_id_from_payload_when_arg_absent(self):
        payload = {"ok": True, "channel_id": "payload_ch"}
        result = build_response_envelope(
            payload,
            service="test",
            api_version="v1",
            request_id="req_ch",
        )
        self.assertEqual(result["channel_id"], "payload_ch")

    def test_data_is_deep_copy(self):
        """Mutating the returned data block must not affect the original."""
        payload = {"ok": True, "nested": {"key": "value"}}
        result = build_response_envelope(
            payload,
            service="test",
            api_version="v1",
            request_id="req_copy",
        )
        result["data"]["nested"]["key"] = "mutated"
        self.assertEqual(payload["nested"]["key"], "value")

    def test_response_meta_keys_complete(self):
        """Ensure response_meta always contains all required fields."""
        result = build_response_envelope(
            {"ok": True},
            service="svc",
            api_version="v2",
            request_id="req_meta",
        )
        meta = result["response_meta"]
        required_keys = {"service", "api_version", "request_id", "channel_id", "tenant_plan", "response_tier", "status"}
        self.assertEqual(required_keys, set(meta.keys()))

    def test_long_channel_id_truncated(self):
        long_channel = "x" * 200
        result = build_response_envelope(
            {"ok": True},
            service="svc",
            api_version="v1",
            request_id="req_trunc",
            channel_id=long_channel,
        )
        self.assertLessEqual(len(result["response_meta"]["channel_id"]), 80)


if __name__ == "__main__":
    unittest.main()
