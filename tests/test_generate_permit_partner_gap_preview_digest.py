import unittest

from scripts import generate_permit_partner_gap_preview_digest


class GeneratePermitPartnerGapPreviewDigestTests(unittest.TestCase):
    def test_build_digest_is_ready_when_no_gap_or_mismatch_exists(self):
        report = generate_permit_partner_gap_preview_digest.build_digest(
            observability_report={
                "summary": {
                    "observability_ready": True,
                    "expected_family_total": 2,
                },
                "families": [
                    {
                        "claim_id": "permit-family-a",
                        "family_key": "family-a",
                        "binding_preset_id": "preset-a",
                        "widget_binding_preset_id": "preset-a",
                        "api_binding_preset_id": "preset-a",
                        "manual_review_expected": False,
                    },
                    {
                        "claim_id": "permit-family-b",
                        "family_key": "family-b",
                        "binding_preset_id": "preset-b",
                        "widget_binding_preset_id": "preset-b",
                        "api_binding_preset_id": "preset-b",
                        "manual_review_expected": True,
                    },
                ],
            }
        )

        summary = report["summary"]
        self.assertTrue(summary["digest_ready"])
        self.assertEqual(summary["blank_binding_preset_total"], 0)
        self.assertEqual(summary["widget_preset_mismatch_total"], 0)
        self.assertEqual(summary["api_preset_mismatch_total"], 0)
        self.assertEqual(summary["manual_review_binding_total"], 1)

    def test_build_digest_exposes_blank_and_mismatch_preview(self):
        report = generate_permit_partner_gap_preview_digest.build_digest(
            observability_report={
                "summary": {
                    "observability_ready": True,
                    "expected_family_total": 1,
                },
                "families": [
                    {
                        "claim_id": "permit-family-a",
                        "family_key": "family-a",
                        "binding_preset_id": "",
                        "widget_binding_preset_id": "preset-widget",
                        "api_binding_preset_id": "preset-api",
                        "manual_review_expected": False,
                        "service_code": "FOCUS::a",
                    }
                ],
            }
        )

        summary = report["summary"]
        self.assertFalse(summary["digest_ready"])
        self.assertEqual(summary["blank_binding_preset_total"], 1)
        self.assertEqual(report["blank_binding_preset_preview"][0]["claim_id"], "permit-family-a")
        markdown = generate_permit_partner_gap_preview_digest.render_markdown(report)
        self.assertIn("Permit Partner Gap Preview Digest", markdown)
        self.assertIn("blank_binding_preset_total", markdown)


if __name__ == "__main__":
    unittest.main()
