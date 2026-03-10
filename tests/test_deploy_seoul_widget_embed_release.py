import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import deploy_seoul_widget_embed_release
from scripts.deploy_seoul_widget_embed_release import build_release_plan, main


class DeploySeoulWidgetEmbedReleaseTests(unittest.TestCase):
    def _write_ready_checklist(self, path: Path, *, ready: bool = True) -> None:
        path.write_text(json.dumps({
            "summary": {
                "checklist_ready": ready,
                "operator_input_count": 1,
                "blockers": [] if ready else ["traffic_gate_not_ready"],
            },
            "next_actions": ["Use this checklist as the single operator sequence before running the live release command."],
        }, ensure_ascii=False), encoding="utf-8")

    def test_build_release_plan_contains_expected_steps(self):
        plan = build_release_plan(
            channel_id="seoul_widget_internal",
            confirm_live="YES",
            bundle_manifest="output/widget/bundles/seoul_widget_internal/manifest.json",
            runtime_report="logs/verify_calculator_runtime_latest.json",
            content_report="logs/co_content_pages_deploy_latest.json",
            preflight_report="logs/live_release_readiness_latest.json",
        )
        self.assertEqual([step["name"] for step in plan], [
            "validate_live_release_ready",
            "validate_tenant_onboarding",
            "publish_widget_bundle",
            "deploy_co_content_pages",
            "verify_calculator_runtime",
        ])
        preflight_cmd = " ".join(plan[0]["command"])
        self.assertIn("validate_live_release_ready.py", preflight_cmd)
        self.assertIn("--channel-id", preflight_cmd)
        validate_cmd = " ".join(plan[1]["command"])
        self.assertIn("--strict", validate_cmd)
        deploy_cmd = " ".join(plan[3]["command"])
        self.assertIn("deploy_co_content_pages.py", deploy_cmd)
        self.assertIn("--bundle-manifest", deploy_cmd)

    def test_main_blocks_without_confirm_live(self):
        with tempfile.TemporaryDirectory() as td:
            report_path = Path(td) / "release_report.json"
            argv = [
                "deploy_seoul_widget_embed_release.py",
                "--report",
                str(report_path),
            ]
            stdout = io.StringIO()
            with patch("sys.argv", argv):
                with patch("sys.stdout", stdout):
                    exit_code = main()
            self.assertEqual(exit_code, 2)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertFalse(report["ok"])
            self.assertIn("confirm_live_missing", report["blocking_issues"])
            self.assertFalse(report["rollback"]["rollback_required"])
            self.assertEqual(report["rollback"]["rollback_reason"], "release_not_started")
            self.assertIn("operator_checklist", report["artifact_summary"])

    def test_main_blocks_when_operator_checklist_not_ready(self):
        with tempfile.TemporaryDirectory() as td:
            report_path = Path(td) / "release_report.json"
            checklist_path = Path(td) / "checklist.json"
            self._write_ready_checklist(checklist_path, ready=False)
            argv = [
                "deploy_seoul_widget_embed_release.py",
                "--confirm-live",
                "YES",
                "--kr-live-operator-checklist",
                str(checklist_path),
                "--report",
                str(report_path),
            ]
            stdout = io.StringIO()
            with patch("sys.argv", argv):
                with patch("sys.stdout", stdout):
                    exit_code = main()
            self.assertEqual(exit_code, 2)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertFalse(report["ok"])
            self.assertIn("kr_live_operator_checklist_not_ready", report["blocking_issues"])
            self.assertFalse(report["rollback"]["rollback_required"])
            self.assertFalse(report["handoff"]["operator_checklist_ready"])

    def test_main_attaches_preflight_and_handoff(self):
        with tempfile.TemporaryDirectory() as td:
            report_path = Path(td) / "release_report.json"
            preflight_path = Path(td) / "preflight.json"
            content_path = Path(td) / "content.json"
            runtime_path = Path(td) / "runtime.json"
            bundle_path = Path(td) / "manifest.json"
            checklist_path = Path(td) / "checklist.json"
            self._write_ready_checklist(checklist_path, ready=True)
            preflight_path.write_text(json.dumps({
                "ok": True,
                "handoff": {"release_ready": True, "next_actions": ["release orchestration 진행 가능"]},
                "blocking_issues": [],
            }, ensure_ascii=False), encoding="utf-8")
            content_path.write_text(json.dumps({
                "ok": True,
                "results": [
                    {"co_id": "ai_calc", "subject_ok": True, "content_ok": True},
                    {"co_id": "ai_acq", "subject_ok": True, "content_ok": True},
                ],
            }, ensure_ascii=False), encoding="utf-8")
            runtime_path.write_text(json.dumps({
                "ok": True,
                "checks": [{"kind": "runtime", "url": "https://example.com", "ok": True}],
                "warnings": [],
                "blocking_issues": [],
            }, ensure_ascii=False), encoding="utf-8")
            bundle_path.write_text(json.dumps({
                "widgets": [
                    {"widget": "yangdo", "ok": True},
                    {"widget": "permit", "ok": True},
                ],
            }, ensure_ascii=False), encoding="utf-8")
            argv = [
                "deploy_seoul_widget_embed_release.py",
                "--confirm-live",
                "YES",
                "--preflight-report",
                str(preflight_path),
                "--content-report",
                str(content_path),
                "--runtime-report",
                str(runtime_path),
                "--bundle-manifest",
                str(bundle_path),
                "--kr-live-operator-checklist",
                str(checklist_path),
                "--report",
                str(report_path),
            ]
            outputs = iter([
                {
                    "ok": True,
                    "returncode": 0,
                    "command": ["preflight"],
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "json": {
                        "ok": True,
                        "handoff": {
                            "release_ready": True,
                            "next_actions": ["release orchestration 진행 가능"],
                        },
                    },
                },
                {"ok": True, "returncode": 0, "command": ["validate"], "stdout_tail": "", "stderr_tail": "", "json": {"ok": True}},
                {"ok": True, "returncode": 0, "command": ["bundle"], "stdout_tail": "", "stderr_tail": "", "json": {"ok": True}},
                {"ok": True, "returncode": 0, "command": ["content"], "stdout_tail": "", "stderr_tail": "", "json": {"ok": True}},
                {"ok": True, "returncode": 0, "command": ["runtime"], "stdout_tail": "", "stderr_tail": "", "json": {"ok": True}},
            ])
            stdout = io.StringIO()
            with patch.object(deploy_seoul_widget_embed_release, "_run", side_effect=lambda cmd: next(outputs)):
                with patch("sys.argv", argv):
                    with patch("sys.stdout", stdout):
                        exit_code = main()
            self.assertEqual(exit_code, 0)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(report["ok"])
            self.assertTrue(report["preflight"]["ok"])
            self.assertTrue(report["handoff"]["release_ready"])
            self.assertTrue(report["handoff"]["operator_checklist_ready"])
            self.assertTrue(report["bundle_backup"]["created"])
            self.assertFalse(report["rollback"]["rollback_required"])
            self.assertEqual(report["rollback"]["rollback_reason"], "live_release_succeeded")
            self.assertTrue(report["rollback"]["backup_available"])
            self.assertEqual(report["artifact_summary"]["bundle"]["ok_widget_count"], 2)
            self.assertEqual(report["artifact_summary"]["content"]["ok_ids"], ["ai_calc", "ai_acq"])
            self.assertTrue(report["artifact_summary"]["runtime"]["ok"])
            self.assertTrue(report["artifact_summary"]["operator_checklist"]["checklist_ready"])


if __name__ == "__main__":
    unittest.main()
