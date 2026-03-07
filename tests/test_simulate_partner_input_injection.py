import json
import tempfile
import unittest
from pathlib import Path

from scripts.simulate_partner_input_injection import _inject_partner_inputs


class SimulatePartnerInputInjectionTests(unittest.TestCase):
    def test_inject_partner_inputs_updates_contract_source_and_env(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            registry_path = base / "tenant_registry.json"
            env_path = base / ".env"
            registry_path.write_text(
                json.dumps(
                    {
                        "tenants": [
                            {
                                "tenant_id": "partner_permit_standard",
                                "api_key_envs": ["TENANT_API_KEY_PARTNER_PERMIT_STANDARD"],
                                "data_sources": [
                                    {
                                        "source_id": "partner_source",
                                        "access_mode": "partner_contract",
                                        "status": "pending",
                                        "allows_commercial_use": False,
                                        "proof_url": "",
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            env_path.write_text("", encoding="utf-8")

            result = _inject_partner_inputs(
                registry_path=registry_path,
                env_path=env_path,
                tenant_id="partner_permit_standard",
                proof_url="https://example.com/proof",
                api_key_value="secret-key",
                approve_source=True,
            )

            self.assertTrue(result["ok"])
            self.assertTrue(result["proof_url_injected"])
            self.assertTrue(result["approval_injected"])
            self.assertTrue(result["api_key_injected"])
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            source = registry["tenants"][0]["data_sources"][0]
            self.assertEqual(source["proof_url"], "https://example.com/proof")
            self.assertEqual(source["status"], "approved")
            self.assertTrue(source["allows_commercial_use"])
            self.assertIn("TENANT_API_KEY_PARTNER_PERMIT_STANDARD=secret-key", env_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
