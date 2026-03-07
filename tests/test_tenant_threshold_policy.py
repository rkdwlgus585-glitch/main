import json
import tempfile
import unittest
from pathlib import Path

from scripts.enforce_tenant_threshold_policy import build_policy_actions, run


class TenantThresholdPolicyTests(unittest.TestCase):
    def test_build_policy_actions_notify_when_not_applying(self):
        report = {
            "tenants": [
                {
                    "tenant_id": "alpha",
                    "display_name": "Alpha",
                    "recommended_action": "upgrade_or_overage_charge",
                    "action_reason": "포함 토큰 초과",
                    "usage_events": 10,
                    "estimated_tokens": 12000,
                    "upgrade_target": "pro",
                }
            ]
        }
        registry = {
            "tenants": [
                {"tenant_id": "alpha", "plan": "standard", "enabled": True},
            ]
        }

        payload, changed = build_policy_actions(
            report=report,
            registry=registry,
            auto_upgrade=False,
            auto_disable=False,
            auto_block_keys=False,
            disable_actions={"disabled_tenant_activity"},
            disable_min_usage_events=3,
            protected_tenants={"seoul_main"},
            env_values={},
            apply_registry=False,
        )

        self.assertFalse(changed)
        self.assertEqual(payload["summary"]["action_count"], 1)
        self.assertEqual(payload["actions"][0]["policy_action"], "notify_upgrade_needed")

    def test_build_policy_actions_applies_upgrade(self):
        report = {
            "tenants": [
                {
                    "tenant_id": "alpha",
                    "display_name": "Alpha",
                    "recommended_action": "upgrade_or_overage_charge",
                    "action_reason": "포함 토큰 초과",
                    "usage_events": 10,
                    "estimated_tokens": 12000,
                    "upgrade_target": "pro",
                }
            ]
        }
        registry = {
            "tenants": [
                {"tenant_id": "alpha", "plan": "standard", "enabled": True},
            ]
        }

        payload, changed = build_policy_actions(
            report=report,
            registry=registry,
            auto_upgrade=True,
            auto_disable=False,
            auto_block_keys=False,
            disable_actions={"disabled_tenant_activity"},
            disable_min_usage_events=3,
            protected_tenants={"seoul_main"},
            env_values={},
            apply_registry=True,
        )

        self.assertTrue(changed)
        self.assertEqual(payload["actions"][0]["policy_action"], "upgrade_plan")
        self.assertTrue(payload["actions"][0]["applied"])
        self.assertEqual(registry["tenants"][0]["plan"], "pro")

    def test_build_policy_actions_applies_disable_and_key_block(self):
        report = {
            "tenants": [
                {
                    "tenant_id": "alpha",
                    "display_name": "Alpha",
                    "recommended_action": "disabled_tenant_activity",
                    "action_reason": "비활성 테넌트 트래픽 감지",
                    "usage_events": 6,
                    "estimated_tokens": 1000,
                    "upgrade_target": "",
                }
            ]
        }
        registry = {
            "tenants": [
                {
                    "tenant_id": "alpha",
                    "plan": "standard",
                    "enabled": True,
                    "api_key_envs": ["TENANT_API_KEY_ALPHA"],
                }
            ]
        }
        env_values = {"TENANT_API_KEY_ALPHA": "token_alpha_1234567890"}

        payload, changed = build_policy_actions(
            report=report,
            registry=registry,
            auto_upgrade=False,
            auto_disable=True,
            auto_block_keys=True,
            disable_actions={"disabled_tenant_activity"},
            disable_min_usage_events=3,
            protected_tenants={"seoul_main"},
            env_values=env_values,
            apply_registry=True,
        )

        self.assertTrue(changed)
        self.assertEqual(payload["actions"][0]["policy_action"], "disable_tenant")
        self.assertTrue(payload["actions"][0]["applied"])
        self.assertFalse(registry["tenants"][0]["enabled"])
        self.assertIn("token_alpha_1234567890", registry["tenants"][0]["blocked_api_tokens"])

    def test_run_strict_returns_one_when_unresolved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report_path = root / "billing.json"
            registry_path = root / "registry.json"
            thresholds_path = root / "thresholds.json"
            env_path = root / ".env"
            output_path = root / "actions.json"

            report_path.write_text(
                json.dumps(
                    {
                        "tenants": [
                            {
                                "tenant_id": "unknown",
                                "display_name": "Unknown",
                                "recommended_action": "investigate_unknown_host",
                                "action_reason": "host/origin 매핑 누락",
                                "usage_events": 3,
                                "estimated_tokens": 1000,
                                "upgrade_target": "",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            registry_path.write_text(json.dumps({"tenants": []}), encoding="utf-8")
            thresholds_path.write_text(json.dumps({"policy": {"auto_upgrade": False}}), encoding="utf-8")
            env_path.write_text("", encoding="utf-8")

            code = run(
                report_path=report_path,
                registry_path=registry_path,
                thresholds_path=thresholds_path,
                env_path=env_path,
                output_path=output_path,
                auto_upgrade_override=None,
                auto_disable_override=None,
                auto_block_keys_override=None,
                disable_min_events_override=None,
                protected_tenants_override=None,
                apply_registry=False,
                strict=True,
            )

            self.assertEqual(code, 1)
            output = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertGreater(output["summary"]["unresolved_action_count"], 0)


if __name__ == "__main__":
    unittest.main()
