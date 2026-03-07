import unittest
from pathlib import Path

from scripts.deploy_kr_platform_front_preview import build_preview_report


class DeployKrPlatformFrontPreviewTests(unittest.TestCase):
    def test_build_preview_report_surfaces_preview_url(self):
        payload = build_preview_report(
            sync_step={"ok": True, "json": {"ok": True}},
            readiness_payload={"blocking_issues": [], "handoff": {"preview_deploy_ready": True}, "traffic_gate": {"traffic_leak_blocked": True}},
            deploy_step={
                "ok": True,
                "returncode": 0,
                "stdout": "Inspect: https://seoulmna-kr-platform-front-preview.vercel.app",
                "stderr": "",
            },
            front_app_path=Path("C:/tmp/front"),
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(
            payload["handoff"]["preview_url"],
            "https://seoulmna-kr-platform-front-preview.vercel.app",
        )
        self.assertTrue(payload["handoff"]["preview_deployed"])
        self.assertTrue(payload["handoff"]["traffic_gate_ok"])

    def test_build_preview_report_respects_readiness_blockers(self):
        payload = build_preview_report(
            sync_step={"ok": True, "json": {"ok": True}},
            readiness_payload={"blocking_issues": ["vercel_auth_missing"], "handoff": {"preview_deploy_ready": False}, "traffic_gate": {"traffic_leak_blocked": False}},
            deploy_step={
                "ok": False,
                "returncode": 2,
                "stdout": "",
                "stderr": "preview deploy blocked by readiness validation",
            },
            front_app_path=Path("C:/tmp/front"),
        )
        self.assertFalse(payload["ok"])
        self.assertIn("vercel_auth_missing", payload["blocking_issues"])
        self.assertIn("Authenticate Vercel CLI and rerun the kr preview deploy", payload["handoff"]["next_actions"])


if __name__ == "__main__":
    unittest.main()
