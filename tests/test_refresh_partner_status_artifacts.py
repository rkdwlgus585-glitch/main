import unittest

from scripts.refresh_partner_status_artifacts import build_refresh_plan


class RefreshPartnerStatusArtifactsTests(unittest.TestCase):
    def test_build_refresh_plan_orders_dependent_steps(self):
        plan = build_refresh_plan(
            offering_id="permit_standard",
            tenant_id="partner_permit_standard",
            channel_id="partner_permit_template",
            host="partner-permit.example.com",
            brand_name="Partner Permit",
        )
        names = [row["name"] for row in plan]
        self.assertEqual(
            names,
            [
                "partner_onboarding_flow",
                "partner_activation_preview",
                "partner_preview_alignment",
                "partner_activation_resolution",
                "partner_input_snapshot",
                "partner_activation_simulation_matrix",
                "operations_packet",
            ],
        )

    def test_build_refresh_plan_uses_custom_paths(self):
        plan = build_refresh_plan(
            offering_id="permit_standard",
            tenant_id="partner_permit_standard",
            channel_id="partner_permit_template",
            host="partner-permit.example.com",
            brand_name="Partner Permit",
            registry_path="X:/tmp/tenant_registry.json",
            channels_path="X:/tmp/channel_profiles.json",
            env_path="X:/tmp/.env",
            log_dir="X:/tmp/logs",
        )
        first_cmd = " ".join(plan[0]["command"])
        self.assertIn("--registry X:/tmp/tenant_registry.json", first_cmd)
        self.assertIn("--channels X:/tmp/channel_profiles.json", first_cmd)
        self.assertIn("--env-file X:/tmp/.env", first_cmd)
        self.assertIn("X:/tmp/logs/partner_onboarding_flow_latest.json", first_cmd)
        matrix_cmd = " ".join(plan[5]["command"])
        self.assertIn("scripts/generate_partner_activation_simulation_matrix.py", matrix_cmd)
        self.assertIn("--json X:/tmp/logs/partner_activation_simulation_matrix_latest.json", matrix_cmd)
        operations_cmd = " ".join(plan[6]["command"])
        self.assertIn("--partner-simulation-matrix X:/tmp/logs/partner_activation_simulation_matrix_latest.json", operations_cmd)

    def test_build_refresh_plan_can_skip_simulation_matrix(self):
        plan = build_refresh_plan(
            offering_id="permit_standard",
            tenant_id="partner_permit_standard",
            channel_id="partner_permit_template",
            host="partner-permit.example.com",
            brand_name="Partner Permit",
            include_simulation_matrix=False,
        )
        names = [row["name"] for row in plan]
        self.assertNotIn("partner_activation_simulation_matrix", names)
        self.assertEqual(names[-1], "operations_packet")
        operations_cmd = " ".join(plan[-1]["command"])
        self.assertNotIn("--partner-simulation-matrix", operations_cmd)


if __name__ == "__main__":
    unittest.main()
