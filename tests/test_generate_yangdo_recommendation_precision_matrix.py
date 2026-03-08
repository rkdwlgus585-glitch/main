import unittest

from scripts.generate_yangdo_recommendation_precision_matrix import build_yangdo_recommendation_precision_matrix


class GenerateYangdoRecommendationPrecisionMatrixTests(unittest.TestCase):
    def test_build_precision_matrix_covers_sector_band_and_tier_axes(self):
        payload = build_yangdo_recommendation_precision_matrix()
        summary = payload["summary"]

        self.assertTrue(summary["precision_ok"])
        self.assertTrue(summary["high_precision_ok"])
        self.assertTrue(summary["fallback_precision_ok"])
        self.assertTrue(summary["balance_excluded_precision_ok"])
        self.assertTrue(summary["special_sector_comprehensive_ok"])
        self.assertTrue(summary["special_sector_split_ok"])
        self.assertTrue(summary["assist_precision_ok"])
        self.assertTrue(summary["summary_publication_ok"])
        self.assertTrue(summary["detail_explainability_ok"])
        self.assertIn("general", summary["sector_groups"])
        self.assertIn("balance_excluded_sector", summary["sector_groups"])
        self.assertGreaterEqual(summary["sector_groups"]["balance_excluded_sector"]["scenario_count"], 6)
        self.assertIn("mid_2_to_4_eok", summary["price_bands"])
        self.assertIn("sub_1_eok", summary["price_bands"])
        self.assertIn("summary", summary["response_tiers"])
        self.assertIn("detail", summary["response_tiers"])


if __name__ == "__main__":
    unittest.main()
