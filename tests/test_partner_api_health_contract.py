import unittest
from unittest.mock import patch

import permit_precheck_api
import yangdo_blackbox_api
from scripts import run_partner_api_smoke


class PartnerApiHealthContractTests(unittest.TestCase):
    def test_permit_health_payload_contains_health_contract(self):
        payload = permit_precheck_api._partner_health_payload()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "permit_precheck_api")
        self.assertIn("health_contract", payload)
        self.assertTrue(str((payload.get("health_contract") or {}).get("text") or "").strip())

    def test_yangdo_health_payload_contains_health_contract(self):
        payload = yangdo_blackbox_api._partner_health_payload()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "yangdo_blackbox_api")
        self.assertIn("health_contract", payload)
        self.assertTrue(str((payload.get("health_contract") or {}).get("text") or "").strip())

    def test_partner_smoke_health_checks_require_health_contract_match(self):
        expected_contract = {
            "ok": True,
            "text": "GREEN | secure=ok",
            "components": {"secure_stack": True},
        }
        body = {
            "ok": True,
            "health_contract": {
                "ok": True,
                "text": "GREEN | secure=ok",
                "components": {"secure_stack": True},
            },
        }
        with patch.object(run_partner_api_smoke, "load_widget_health_contract", return_value=expected_contract):
            checks = run_partner_api_smoke._health_checks(200, {"X-Api-Version": "v1", "X-Request-Id": "req"}, body)
        failed = [row["name"] for row in checks if not row["ok"]]
        self.assertEqual(failed, [])

    def test_partner_smoke_health_checks_fail_when_contract_missing(self):
        expected_contract = {
            "ok": True,
            "text": "GREEN | secure=ok",
            "components": {"secure_stack": True},
        }
        body = {"ok": True}
        with patch.object(run_partner_api_smoke, "load_widget_health_contract", return_value=expected_contract):
            checks = run_partner_api_smoke._health_checks(200, {"X-Api-Version": "v1", "X-Request-Id": "req"}, body)
        failed = [row["name"] for row in checks if not row["ok"]]
        self.assertIn("health_contract_present", failed)
        self.assertIn("health_contract_match_local", failed)


if __name__ == "__main__":
    unittest.main()
