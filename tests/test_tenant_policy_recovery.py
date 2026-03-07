import json
import tempfile
import unittest
from pathlib import Path

from scripts.tenant_policy_recovery import run_recovery


class TenantPolicyRecoveryTests(unittest.TestCase):
    def test_preview_mode_does_not_mutate_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "tenant_registry.json"
            report = root / "recovery.json"

            original = {
                "tenants": [
                    {
                        "tenant_id": "alpha",
                        "enabled": False,
                        "blocked_api_tokens": ["tok_1"],
                        "blocked_reason": "disabled_tenant_activity",
                        "blocked_at": "2026-03-05 10:00:00",
                    }
                ]
            }
            registry.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")

            code = run_recovery(
                registry_path=registry,
                report_path=report,
                tenant_ids=set(),
                all_disabled=True,
                with_blocked_keys=True,
                enable_tenant=True,
                clear_blocked_keys=True,
                clear_block_metadata=True,
                apply_changes=False,
                strict=False,
            )

            self.assertEqual(code, 0)
            after = json.loads(registry.read_text(encoding="utf-8"))
            self.assertEqual(after["tenants"][0]["enabled"], False)
            self.assertEqual(after["tenants"][0]["blocked_api_tokens"], ["tok_1"])

    def test_apply_mode_mutates_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "tenant_registry.json"
            report = root / "recovery.json"

            original = {
                "tenants": [
                    {
                        "tenant_id": "alpha",
                        "enabled": False,
                        "blocked_api_tokens": ["tok_1", "tok_2"],
                        "blocked_reason": "disabled_tenant_activity",
                        "blocked_at": "2026-03-05 10:00:00",
                    }
                ]
            }
            registry.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")

            code = run_recovery(
                registry_path=registry,
                report_path=report,
                tenant_ids={"alpha"},
                all_disabled=False,
                with_blocked_keys=False,
                enable_tenant=True,
                clear_blocked_keys=True,
                clear_block_metadata=True,
                apply_changes=True,
                strict=True,
            )

            self.assertEqual(code, 0)
            after = json.loads(registry.read_text(encoding="utf-8"))
            row = after["tenants"][0]
            self.assertTrue(row["enabled"])
            self.assertEqual(row["blocked_api_tokens"], [])
            self.assertNotIn("blocked_reason", row)
            self.assertNotIn("blocked_at", row)


if __name__ == "__main__":
    unittest.main()
