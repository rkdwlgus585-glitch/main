import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_partner_onboarding_flow import build_onboarding_plan, main


class RunPartnerOnboardingFlowTests(unittest.TestCase):
    def test_build_plan_dry_run_uses_temp_files_and_skips_smoke(self):
        plan, paths = build_onboarding_plan(
            offering_id="permit_standard",
            tenant_id="partner_permit_alpha",
            channel_id="partner_permit_alpha",
            host="permit-alpha.example.com",
            brand_name="Permit Alpha",
            apply=False,
        )
        self.assertIn("tempdir", paths)
        self.assertTrue(Path(paths["registry"]).exists())
        self.assertTrue(str(paths["validation_report"]).endswith("tenant_onboarding_validation.json"))
        self.assertIn("--skip-smoke", plan[2]["command"])
        self.assertIn("scaffold_partner_offering.py", " ".join(plan[0]["command"]))
        self.assertIn("--report", plan[1]["command"])
        self.assertIn(paths["validation_report"], plan[1]["command"])

    def test_build_plan_apply_uses_real_paths(self):
        with tempfile.TemporaryDirectory() as td:
            registry = Path(td) / "tenant_registry.json"
            channels = Path(td) / "channel_profiles.json"
            env_file = Path(td) / ".env"
            registry.write_text("{}", encoding="utf-8")
            channels.write_text("{}", encoding="utf-8")
            env_file.write_text("", encoding="utf-8")
            plan, paths = build_onboarding_plan(
                offering_id="yangdo_standard",
                tenant_id="partner_yangdo_alpha",
                channel_id="partner_yangdo_alpha",
                host="yangdo-alpha.example.com",
                brand_name="Yangdo Alpha",
                registry_path=str(registry),
                channels_path=str(channels),
                env_path=str(env_file),
                apply=True,
            )
            self.assertNotIn("tempdir", paths)
            self.assertEqual(paths["registry"], str(registry.resolve()))
            self.assertNotIn("--skip-smoke", plan[2]["command"])
            self.assertIn("--report", plan[1]["command"])

    def test_main_collects_embed_plans(self):
        with tempfile.TemporaryDirectory() as td:
            report_path = Path(td) / "flow.json"
            argv = [
                "run_partner_onboarding_flow.py",
                "--offering-id",
                "permit_standard",
                "--tenant-id",
                "partner_permit_alpha",
                "--channel-id",
                "partner_permit_alpha",
                "--host",
                "permit-alpha.example.com",
                "--brand-name",
                "Permit Alpha",
                "--report",
                str(report_path),
            ]
            results = iter([
                {
                    "ok": True,
                    "returncode": 0,
                    "command": ["scaffold"],
                    "stdout": "",
                    "stderr": "",
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "json": {"tenant": {"allowed_systems": ["permit"]}},
                },
                {
                    "ok": True,
                    "returncode": 0,
                    "command": ["validate"],
                    "stdout": "",
                    "stderr": "",
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "json": {"ok": True},
                },
                {
                    "ok": True,
                    "returncode": 0,
                    "command": ["activate"],
                    "stdout": "",
                    "stderr": "",
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "json": {"ok": True, "activation_blockers": [], "smoke_requested": False, "smoke_ok": None},
                },
                {
                    "ok": True,
                    "returncode": 0,
                    "command": ["embed"],
                    "stdout": "",
                    "stderr": "",
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "json": {"ok": True, "widget": "permit"},
                },
            ])
            stdout = io.StringIO()
            with patch("scripts.run_partner_onboarding_flow._run", side_effect=lambda cmd: next(results)):
                with patch("sys.argv", argv):
                    with patch("sys.stdout", stdout):
                        exit_code = main()
            self.assertEqual(exit_code, 0)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(report["ok"])
            self.assertIn("permit", report["embed_plans"])
            self.assertTrue(report["handoff"]["activation_ready"])
            self.assertIn("widget/API handoff", report["handoff"]["next_actions"][0])
            self.assertEqual(report["handoff"]["remaining_required_inputs"], [])

    def test_main_reports_handoff_actions_for_missing_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            report_path = Path(td) / "flow.json"
            argv = [
                "run_partner_onboarding_flow.py",
                "--offering-id",
                "permit_standard",
                "--tenant-id",
                "partner_permit_alpha",
                "--channel-id",
                "partner_permit_alpha",
                "--host",
                "permit-alpha.example.com",
                "--brand-name",
                "Permit Alpha",
                "--report",
                str(report_path),
            ]
            results = iter([
                {
                    "ok": True,
                    "returncode": 0,
                    "command": ["scaffold"],
                    "stdout": "",
                    "stderr": "",
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "json": {"tenant": {"allowed_systems": ["permit"]}},
                },
                {
                    "ok": True,
                    "returncode": 0,
                    "command": ["validate"],
                    "stdout": "",
                    "stderr": "",
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "json": {"ok": True},
                },
                {
                    "ok": False,
                    "returncode": 2,
                    "command": ["activate"],
                    "stdout": "",
                    "stderr": "",
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "json": {
                        "ok": False,
                        "activation_blockers": [
                            "missing_source_proof_url_pending",
                            "missing_api_key_value",
                        ],
                        "smoke_requested": False,
                        "smoke_ok": None,
                    },
                },
            ])
            stdout = io.StringIO()
            with patch("scripts.run_partner_onboarding_flow._run", side_effect=lambda cmd: next(results)):
                with patch("sys.argv", argv):
                    with patch("sys.stdout", stdout):
                        exit_code = main()
            self.assertEqual(exit_code, 2)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertFalse(report["ok"])
            self.assertIn("Provide partner contract proof URL", report["handoff"]["next_actions"])
            self.assertIn("Issue partner API key and inject env", report["handoff"]["next_actions"])
            self.assertEqual(
                report["handoff"]["remaining_required_inputs"],
                ["partner_proof_url", "partner_api_key"],
            )

    def test_main_reuses_existing_scope_when_scaffold_conflicts(self):
        with tempfile.TemporaryDirectory() as td:
            report_path = Path(td) / "flow.json"
            argv = [
                "run_partner_onboarding_flow.py",
                "--offering-id",
                "permit_standard",
                "--tenant-id",
                "partner_permit_standard",
                "--channel-id",
                "partner_permit_template",
                "--host",
                "partner-permit.example.com",
                "--brand-name",
                "Partner Permit",
                "--report",
                str(report_path),
            ]
            results = iter([
                {
                    "ok": False,
                    "returncode": 1,
                    "command": ["scaffold"],
                    "stdout": "",
                    "stderr": "",
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "json": {"ok": False, "error": "tenant_exists"},
                },
                {
                    "ok": True,
                    "returncode": 0,
                    "command": ["validate"],
                    "stdout": "",
                    "stderr": "",
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "json": {"ok": True},
                },
                {
                    "ok": False,
                    "returncode": 2,
                    "command": ["activate"],
                    "stdout": "",
                    "stderr": "",
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "json": {
                        "ok": False,
                        "activation_blockers": ["missing_source_proof_url_pending"],
                        "smoke_requested": False,
                        "smoke_ok": None,
                    },
                },
            ])
            stdout = io.StringIO()
            with patch("scripts.run_partner_onboarding_flow._run", side_effect=lambda cmd: next(results)):
                with patch("scripts.run_partner_onboarding_flow._is_reusable_scaffold_conflict", return_value=True):
                    with patch("scripts.run_partner_onboarding_flow._load_offering_systems", return_value=["permit"]):
                        with patch("sys.argv", argv):
                            with patch("sys.stdout", stdout):
                                exit_code = main()
            self.assertEqual(exit_code, 2)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["steps"][0]["name"], "scaffold_partner_offering")
            self.assertTrue(report["steps"][0]["handled_as_noop"])
            self.assertEqual(report["steps"][0]["noop_reason"], "tenant_exists")
            self.assertEqual(report["activation_blockers"], ["missing_source_proof_url_pending"])


if __name__ == "__main__":
    unittest.main()
