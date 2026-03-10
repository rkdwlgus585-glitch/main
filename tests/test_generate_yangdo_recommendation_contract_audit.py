import unittest

from scripts.generate_yangdo_recommendation_contract_audit import build_contract_audit


class GenerateYangdoRecommendationContractAuditTests(unittest.TestCase):
    def test_build_contract_audit_enforces_summary_detail_internal_separation(self):
        payload = build_contract_audit()
        summary = payload["summary"]
        self.assertTrue(summary["contract_ok"])
        self.assertTrue(summary["summary_safe"])
        self.assertTrue(summary["detail_explainable"])
        self.assertTrue(summary["internal_debug_visible"])

        tiers = payload["tiers"]
        self.assertNotIn("recommendation_score", tiers["summary"]["recommended_listing_keys"])
        self.assertNotIn("recommendation_score", tiers["detail"]["recommended_listing_keys"])
        self.assertNotIn("recommendation_focus_signature", tiers["detail"]["recommended_listing_keys"])
        self.assertNotIn("recommendation_price_band", tiers["detail"]["recommended_listing_keys"])
        self.assertNotIn("similarity", tiers["detail"]["recommended_listing_keys"])
        self.assertIn("precision_tier", tiers["detail"]["recommended_listing_keys"])
        self.assertIn("fit_summary", tiers["detail"]["recommended_listing_keys"])
        self.assertIn("matched_axes", tiers["detail"]["recommended_listing_keys"])
        self.assertIn("mismatch_flags", tiers["detail"]["recommended_listing_keys"])
        self.assertIn("recommendation_score", tiers["internal"]["recommended_listing_keys"])
        self.assertIn("recommendation_focus_signature", tiers["internal"]["recommended_listing_keys"])
        self.assertIn("recommendation_price_band", tiers["internal"]["recommended_listing_keys"])
        self.assertIn("similarity", tiers["internal"]["recommended_listing_keys"])


if __name__ == "__main__":
    unittest.main()
