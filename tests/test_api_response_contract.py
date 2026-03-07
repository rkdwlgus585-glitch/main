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


if __name__ == "__main__":
    unittest.main()
