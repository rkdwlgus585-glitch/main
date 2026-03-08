from __future__ import annotations

import unittest

from scripts.generate_yangdo_cohort_recovery_experiment import build_report


class GenerateYangdoCohortRecoveryExperimentTests(unittest.TestCase):
    def test_split_exact_vs_partial_is_prioritized_for_low_same_combo(self) -> None:
        payload = build_report(
            sector_audit={
                "sectors": [
                    {
                        "sector": "토목",
                        "status": "sparse_support_hotspot",
                        "observed_record_count": 50,
                        "visible_estimate_count": 0,
                        "price_metrics": {"under_67_share": 0.33, "over_150_share": 0.01},
                        "comparable_support": {
                            "avg_same_combo_ratio": 0.0,
                            "avg_display_neighbor_count": 0.0,
                            "avg_effective_cluster_count": 0.0,
                            "top_reject_reasons": [{"key": "single_core_cross_combo", "count": 165}],
                        },
                    }
                ]
            },
            comparable_audit={
                "combo_summaries": [
                    {"combo": ["토목"], "combo_label": "토목", "top_neighbor_combos": [{"key": "토건", "count": 40}]}
                ]
            },
            focus=["토목"],
        )
        self.assertEqual(payload["sector_candidates"][0]["decision"], "split_exact_vs_partial_now")

    def test_unlock_same_combo_support_is_selected_for_locked_single_combo(self) -> None:
        payload = build_report(
            sector_audit={
                "sectors": [
                    {
                        "sector": "포장",
                        "status": "sparse_support_hotspot",
                        "observed_record_count": 20,
                        "visible_estimate_count": 0,
                        "price_metrics": {"under_67_share": 0.18, "over_150_share": 0.03},
                        "comparable_support": {
                            "avg_same_combo_ratio": 1.0,
                            "avg_display_neighbor_count": 1.0,
                            "avg_effective_cluster_count": 1.0,
                            "top_reject_reasons": [{"key": "strict_same_core_miss", "count": 120}],
                        },
                    }
                ]
            },
            comparable_audit={
                "combo_summaries": [
                    {"combo": ["포장"], "combo_label": "포장", "top_neighbor_combos": [{"key": "포장", "count": 30}]}
                ]
            },
            focus=["포장"],
        )
        self.assertEqual(payload["sector_candidates"][0]["decision"], "unlock_same_combo_support_now")


if __name__ == "__main__":
    unittest.main()
