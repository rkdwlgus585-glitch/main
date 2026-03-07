import unittest

from scripts.generate_yangdo_recommendation_qa_matrix import build_yangdo_recommendation_qa_matrix


class GenerateYangdoRecommendationQaMatrixTests(unittest.TestCase):
    def test_build_matrix_returns_green_regression_summary(self):
        payload = build_yangdo_recommendation_qa_matrix()

        summary = payload.get("summary") or {}
        self.assertTrue(summary.get("qa_ok"))
        self.assertEqual(summary.get("scenario_count"), 5)
        self.assertEqual(summary.get("passed_count"), 5)
        self.assertEqual(summary.get("failed_count"), 0)
        self.assertTrue(summary.get("strict_profile_regression_ok"))
        self.assertTrue(summary.get("fallback_regression_ok"))
        self.assertTrue(summary.get("balance_exclusion_regression_ok"))
        self.assertTrue(summary.get("assistive_precision_regression_ok"))
        self.assertTrue(summary.get("summary_projection_regression_ok"))
        self.assertIn("high", summary.get("precision_counts") or {})

        scenarios = payload.get("scenarios") or []
        self.assertEqual(len(scenarios), 5)
        self.assertEqual(scenarios[0].get("scenario_id"), "strict_profile_match_7000_band")
        self.assertEqual(scenarios[-1].get("scenario_id"), "summary_tier_keeps_safe_recommendation_fields_only")


if __name__ == "__main__":
    unittest.main()
