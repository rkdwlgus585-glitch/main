import unittest

from scripts import generate_yangdo_sector_price_audit


class GenerateYangdoSectorPriceAuditTests(unittest.TestCase):
    def test_build_report_matches_exact_combo_alias(self):
        report = generate_yangdo_sector_price_audit.build_report(
            balance_cv={
                "records_evaluated": 2,
                "record_rows": [
                    {
                        "combo": ["건축", "토목"],
                        "combo_label": "건축 + 토목",
                        "actual_price_eok": 1.0,
                        "engine_internal_pred_eok": 0.8,
                        "publication_mode": "range_only",
                        "balance_model_mode": "none",
                        "confidence_percent": 70,
                        "neighbor_count": 1,
                        "effective_cluster_count": 1,
                    }
                ],
            },
            combo_audit={
                "combo_summaries": [
                    {
                        "combo": ["건축", "토목"],
                        "combo_label": "건축 + 토목",
                        "visible_estimate_count": 0,
                        "range_only_count": 1,
                        "consult_only_count": 0,
                    }
                ]
            },
            comparable_audit={
                "combo_summaries": [
                    {
                        "combo": ["건축", "토목"],
                        "combo_label": "건축 + 토목",
                        "avg_same_combo_ratio": 1.0,
                        "avg_same_core_ratio": 1.0,
                        "avg_effective_cluster_count": 1.0,
                        "avg_display_neighbor_count": 1.0,
                        "top_reject_reasons": [],
                    }
                ]
            },
            settlement_report={"invariant_failures": {"total_invariant": 0}},
        )
        row = next(item for item in report["sectors"] if item["sector"] == "토건")
        self.assertEqual(row["observed_record_count"], 1)
        self.assertTrue(row["exact_combo_observed"])

    def test_build_report_keeps_special_sector_settlement_snapshot(self):
        report = generate_yangdo_sector_price_audit.build_report(
            balance_cv={
                "records_evaluated": 1,
                "record_rows": [
                    {
                        "combo": ["전기"],
                        "combo_label": "전기",
                        "actual_price_eok": 1.0,
                        "engine_internal_pred_eok": 0.9,
                        "publication_mode": "range_only",
                        "balance_model_mode": "none",
                    }
                ],
            },
            combo_audit={"combo_summaries": [{"combo": ["전기"], "combo_label": "전기", "visible_estimate_count": 0, "range_only_count": 1, "consult_only_count": 0}]},
            comparable_audit={"combo_summaries": [{"combo": ["전기"], "combo_label": "전기", "avg_same_combo_ratio": 1.0, "avg_same_core_ratio": 1.0, "avg_effective_cluster_count": 2.0, "avg_display_neighbor_count": 2.0, "top_reject_reasons": []}]},
            settlement_report={
                "invariant_failures": {"total_invariant": 0, "publication_drift": 0},
                "by_sector": {
                    "전기": {
                        "포괄": {
                            "auto": {"count": 10},
                        }
                    }
                },
            },
        )
        row = next(item for item in report["sectors"] if item["sector"] == "전기")
        self.assertTrue(row["inherited_special_tests"])
        self.assertIn("포괄", row["settlement_snapshot"])


if __name__ == "__main__":
    unittest.main()
