import unittest

from scripts.run_wp_surface_lab_apply_verify_cycle import build_cycle_payload


class RunWpSurfaceLabApplyVerifyCycleTests(unittest.TestCase):
    def test_cycle_payload_flags_apply_step_failure(self):
        payload = build_cycle_payload(
            runtime_probe_before={"runtime_running": True, "runtime_ready": True, "runtime_mode": "php_fallback"},
            runtime_probe_after={"runtime_running": True, "runtime_ready": True, "runtime_mode": "php_fallback"},
            apply_payload={"apply_result": {"attempted": False, "ok": False, "blockers": []}},
            verify_payload={"summary": {"verification_ok": True, "blockers": []}},
            steps=[
                {"name": "validate_runtime", "ok": True},
                {"name": "apply_blueprints", "ok": False},
                {"name": "verify_pages", "ok": True},
            ],
        )

        self.assertFalse(payload["summary"]["ok"])
        self.assertFalse(payload["summary"]["apply_ok"])
        self.assertFalse(payload["summary"]["apply_step_ok"])
        self.assertIn("apply_execution_failed", payload["summary"]["blockers"])

    def test_cycle_payload_uses_page_verification_when_runtime_validation_is_stale(self):
        payload = build_cycle_payload(
            runtime_probe_before={"runtime_running": False, "runtime_ready": True, "runtime_mode": "php_fallback", "localhost_url": "http://127.0.0.1:18081"},
            runtime_probe_after={"runtime_running": False, "runtime_ready": True, "runtime_mode": "php_fallback", "localhost_url": "http://127.0.0.1:18081"},
            apply_payload={"apply_result": {"attempted": True, "ok": True, "blockers": []}},
            verify_payload={
                "summary": {"verification_ok": True, "blockers": []},
                "page_checks": [{"page_id": "home", "reachable": True}],
            },
            steps=[
                {"name": "validate_runtime", "ok": True},
                {"name": "apply_blueprints", "ok": True},
                {"name": "verify_pages", "ok": True},
            ],
        )

        self.assertTrue(payload["summary"]["ok"])
        self.assertTrue(payload["summary"]["runtime_running_after"])
        self.assertEqual(payload["summary"]["runtime_running_source"], "page_verification")
        self.assertNotIn("runtime_not_running", payload["summary"]["blockers"])


if __name__ == "__main__":
    unittest.main()
