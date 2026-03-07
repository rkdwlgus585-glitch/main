import json
import tempfile
import unittest
from pathlib import Path

from scripts.tenant_policy_notify import run


class TenantPolicyNotifyTests(unittest.TestCase):
    def test_run_dry_mode_with_actions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            policy = root / "policy.json"
            report = root / "notify.json"
            policy.write_text(
                json.dumps(
                    {
                        "summary": {
                            "action_count": 2,
                            "unresolved_action_count": 1,
                            "high_severity_count": 1,
                            "warning_count": 0,
                            "applied_change_count": 0,
                        },
                        "actions": [
                            {
                                "tenant_id": "alpha",
                                "policy_action": "notify_disable_needed",
                                "recommended_action": "disabled_tenant_activity",
                                "message": "자동 제한 조건 충족",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            code = run(
                policy_path=policy,
                report_path=report,
                title="Tenant Policy Alert",
                send_on_ok=False,
                dry_run=True,
                strict=True,
            )

            self.assertEqual(code, 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["should_send"])
            self.assertFalse(payload["sent"])

    def test_run_no_actions_without_send_on_ok(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            policy = root / "policy.json"
            report = root / "notify.json"
            policy.write_text(
                json.dumps(
                    {
                        "summary": {
                            "action_count": 0,
                            "unresolved_action_count": 0,
                            "high_severity_count": 0,
                            "warning_count": 0,
                            "applied_change_count": 0,
                        },
                        "actions": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            code = run(
                policy_path=policy,
                report_path=report,
                title="Tenant Policy Alert",
                send_on_ok=False,
                dry_run=False,
                strict=False,
            )

            self.assertEqual(code, 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["should_send"])


if __name__ == "__main__":
    unittest.main()
