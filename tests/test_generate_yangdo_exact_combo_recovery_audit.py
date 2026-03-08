from __future__ import annotations

import unittest

from scripts.generate_yangdo_exact_combo_recovery_audit import build_report


class GenerateYangdoExactComboRecoveryAuditTests(unittest.TestCase):
    def test_flags_sparse_focus_sector_for_recovery(self) -> None:
        payload = build_report(
            sector_audit={
                "sectors": [
                    {
                        "sector": "토목",
                        "status": "sparse_support_hotspot",
                        "observed_record_count": 12,
                        "visible_estimate_count": 0,
                        "price_metrics": {"under_67_share": 0.42, "over_150_share": 0.0},
                        "comparable_support": {
                            "avg_same_combo_ratio": 0.55,
                            "avg_same_core_ratio": 0.70,
                            "avg_display_neighbor_count": 1.5,
                            "avg_effective_cluster_count": 1.2,
                            "top_reject_reasons": [{"key": "strict_same_core_miss", "count": 40}],
                        },
                        "recommended_action": "exact combo recovery",
                    },
                    {
                        "sector": "건축",
                        "status": "monitor",
                        "observed_record_count": 50,
                        "visible_estimate_count": 20,
                        "price_metrics": {"under_67_share": 0.10, "over_150_share": 0.01},
                        "comparable_support": {
                            "avg_same_combo_ratio": 1.0,
                            "avg_same_core_ratio": 1.0,
                            "avg_display_neighbor_count": 7.0,
                            "avg_effective_cluster_count": 7.0,
                            "top_reject_reasons": [],
                        },
                        "recommended_action": "monitor",
                    },
                ]
            },
            focus=["토목", "건축"],
        )
        summary = payload["summary"]
        self.assertEqual(summary["evaluated_sector_count"], 2)
        self.assertEqual(payload["sector_candidates"][0]["sector"], "토목")
        self.assertEqual(payload["sector_candidates"][0]["decision"], "exact_combo_recovery_now")

    def test_flags_same_combo_locked_support(self) -> None:
        payload = build_report(
            sector_audit={
                "sectors": [
                    {
                        "sector": "포장",
                        "status": "sparse_support_hotspot",
                        "observed_record_count": 20,
                        "visible_estimate_count": 0,
                        "price_metrics": {"under_67_share": 0.20, "over_150_share": 0.02},
                        "comparable_support": {
                            "avg_same_combo_ratio": 1.0,
                            "avg_same_core_ratio": 1.0,
                            "avg_display_neighbor_count": 1.0,
                            "avg_effective_cluster_count": 1.0,
                            "top_reject_reasons": [{"key": "strict_same_core_miss", "count": 120}],
                        },
                        "recommended_action": "recover locked support",
                    }
                ]
            },
            focus=["포장"],
        )
        self.assertEqual(payload["sector_candidates"][0]["decision"], "same_combo_locked_support")


if __name__ == "__main__":
    unittest.main()
