import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.refresh_wordpress_platform_artifacts import refresh_wordpress_platform_artifacts


class RefreshWordpressPlatformArtifactsTests(unittest.TestCase):
    def test_refresh_runs_in_fixed_order_and_stops_on_failure(self):
        calls = []

        def fake_run(script):
            calls.append(Path(script).name)
            return {"script": str(script), "ok": Path(script).name != "generate_kr_reverse_proxy_cutover.py", "returncode": 0 if Path(script).name != "generate_kr_reverse_proxy_cutover.py" else 1, "stdout": "", "stderr": ""}

        with patch("scripts.refresh_wordpress_platform_artifacts._run", side_effect=fake_run):
            payload = refresh_wordpress_platform_artifacts()

        self.assertFalse(payload["ok"])
        self.assertEqual(
            calls,
            [
                "generate_wordpress_platform_strategy.py",
                "generate_wordpress_platform_ia.py",
                "scaffold_wp_surface_lab_runtime.py",
                "prepare_wp_surface_lab_php_runtime.py",
                "bootstrap_wp_surface_lab_php_fallback.py",
                "validate_wp_surface_lab_runtime.py",
                "generate_private_engine_proxy_spec.py",
                "generate_listing_platform_bridge_policy.py",
                "generate_co_listing_bridge_snippets.py",
                "generate_co_listing_bridge_operator_checklist.py",
                "generate_co_listing_live_injection_plan.py",
                "generate_co_listing_injection_bundle.py",
                "generate_co_listing_bridge_apply_packet.py",
                "generate_kr_proxy_server_matrix.py",
                "generate_kr_proxy_server_bundle.py",
                "generate_kr_reverse_proxy_cutover.py",
            ],
        )
        self.assertEqual(payload["step_count"], 16)

    def test_refresh_rebuilds_operations_packet_after_improvement_loop(self):
        calls = []

        def fake_run(script):
            calls.append(Path(script).name)
            return {"script": str(script), "ok": True, "returncode": 0, "stdout": "", "stderr": ""}

        with patch("scripts.refresh_wordpress_platform_artifacts._run", side_effect=fake_run):
            payload = refresh_wordpress_platform_artifacts()

        self.assertTrue(payload["ok"])
        self.assertEqual(
            calls[-20:],
            [
                "generate_yangdo_recommendation_diversity_audit.py",
                "generate_yangdo_recommendation_contract_audit.py",
                "generate_widget_rental_catalog.py",
                "generate_yangdo_recommendation_bridge_packet.py",
                "generate_yangdo_service_copy_packet.py",
                "generate_permit_service_copy_packet.py",
                "generate_permit_service_alignment_audit.py",
                "scaffold_wp_platform_blueprints.py",
                "apply_wp_surface_lab_blueprints.py",
                "generate_wordpress_staging_apply_plan.py",
                "run_wp_surface_lab_apply_verify_cycle.py",
                "verify_wp_surface_lab_pages.py",
                "generate_wordpress_platform_encoding_audit.py",
                "generate_wordpress_platform_ux_audit.py",
                "generate_yangdo_recommendation_ux_packet.py",
                "generate_yangdo_recommendation_alignment_audit.py",
                "generate_kr_live_apply_packet.py",
                "generate_kr_live_operator_checklist.py",
                "generate_program_improvement_loop.py",
                "generate_operations_packet.py",
            ],
        )
        self.assertEqual(payload["step_count"], len(calls))


if __name__ == "__main__":
    unittest.main()
