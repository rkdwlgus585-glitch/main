import unittest

from scripts import generate_permit_surface_drift_digest


class GeneratePermitSurfaceDriftDigestTests(unittest.TestCase):
    def test_build_surface_drift_digest_detects_flips_and_shifts(self):
        report = generate_permit_surface_drift_digest.build_surface_drift_digest(
            permit_demo_surface_observability={
                "summary": {
                    "surface_total": 8,
                    "ready_surface_total": 8,
                    "missing_surface_total": 0,
                    "prompt_case_binding_total": 6,
                    "runtime_critical_prompt_surface_ready": True,
                    "runtime_prompt_case_binding_surface_ready": True,
                    "partner_demo_surface_ready": True,
                },
                "surfaces": [
                    {
                        "surface_id": "runtime_reasoning_card",
                        "label": "Runtime reasoning card",
                        "ready": True,
                        "coverage_total": 4,
                        "sample_total": 1,
                    },
                    {
                        "surface_id": "runtime_prompt_case_binding",
                        "label": "Runtime prompt-case binding",
                        "ready": True,
                        "coverage_total": 6,
                        "sample_total": 0,
                    },
                    {
                        "surface_id": "widget_partner_demo",
                        "label": "Widget partner demo surface",
                        "ready": True,
                        "coverage_total": 6,
                        "sample_total": 6,
                    },
                ],
            },
            permit_release_bundle={"summary": {"release_ready": True}},
            previous_digest={
                "current_snapshot": {
                    "surfaces": [
                        {
                            "surface_id": "runtime_reasoning_card",
                            "label": "Runtime reasoning card",
                            "ready": False,
                            "coverage_total": 3,
                            "sample_total": 0,
                        },
                        {
                            "surface_id": "runtime_prompt_case_binding",
                            "label": "Runtime prompt-case binding",
                            "ready": False,
                            "coverage_total": 0,
                            "sample_total": 0,
                        },
                        {
                            "surface_id": "widget_partner_demo",
                            "label": "Widget partner demo surface",
                            "ready": True,
                            "coverage_total": 6,
                            "sample_total": 4,
                        },
                    ]
                }
            },
        )

        summary = report["summary"]
        self.assertTrue(summary["digest_ready"])
        self.assertTrue(summary["previous_snapshot_ready"])
        self.assertTrue(summary["delta_ready"])
        self.assertEqual(summary["changed_surface_total"], 3)
        self.assertEqual(summary["readiness_flip_total"], 2)
        self.assertEqual(summary["coverage_shift_total"], 2)
        self.assertEqual(summary["sample_shift_total"], 2)
        self.assertEqual(summary["prompt_surface_regression_total"], 0)
        self.assertEqual(summary["reasoning_changed_surface_total"], 2)
        self.assertEqual(summary["reasoning_readiness_flip_total"], 2)
        self.assertEqual(summary["reasoning_coverage_shift_total"], 2)
        self.assertEqual(summary["reasoning_sample_shift_total"], 1)
        self.assertEqual(summary["reasoning_regression_total"], 0)

        markdown = generate_permit_surface_drift_digest.render_markdown(report)
        self.assertIn("Permit Surface Drift Digest", markdown)
        self.assertIn("runtime_reasoning_card", markdown)
        self.assertIn("runtime_prompt_case_binding", markdown)
        self.assertIn("widget_partner_demo", markdown)

    def test_build_surface_drift_digest_bootstraps_without_previous_snapshot(self):
        report = generate_permit_surface_drift_digest.build_surface_drift_digest(
            permit_demo_surface_observability={
                "summary": {
                    "surface_total": 8,
                    "ready_surface_total": 8,
                    "missing_surface_total": 0,
                },
                "surfaces": [],
            },
            permit_release_bundle={"summary": {"release_ready": True}},
            previous_digest={},
        )

        self.assertTrue(report["summary"]["digest_ready"])
        self.assertFalse(report["summary"]["previous_snapshot_ready"])
        self.assertFalse(report["summary"]["delta_ready"])
        self.assertEqual(report["summary"]["changed_surface_total"], 0)


if __name__ == "__main__":
    unittest.main()
