import unittest

from scripts import generate_yangdo_price_logic_brainstorm


class GenerateYangdoPriceLogicBrainstormTests(unittest.TestCase):
    def test_build_brainstorm_prioritizes_none_mode_replacement_when_underpricing_is_concentrated(self):
        none_rows = [
            {
                "combo_size": 1,
                "actual_price_eok": 1.0,
                "engine_internal_pred_eok": 0.42,
                "balance_model_mode": "none",
                "confidence_percent": 70,
                "neighbor_count": 1,
                "effective_cluster_count": 1,
            },
            {
                "combo_size": 1,
                "actual_price_eok": 1.0,
                "engine_internal_pred_eok": 0.50,
                "balance_model_mode": "none",
                "confidence_percent": 68,
                "neighbor_count": 1,
                "effective_cluster_count": 1,
            },
            {
                "combo_size": 1,
                "actual_price_eok": 1.0,
                "engine_internal_pred_eok": 0.61,
                "balance_model_mode": "none",
                "confidence_percent": 67,
                "neighbor_count": 1,
                "effective_cluster_count": 1,
            },
        ]
        record_rows = none_rows * 120 + [
            {
                "combo_size": 1,
                "actual_price_eok": 1.0,
                "engine_internal_pred_eok": 0.95,
                "balance_model_mode": "direct_balance_base",
                "confidence_percent": 81,
                "neighbor_count": 4,
                "effective_cluster_count": 4,
            },
        ]
        report = generate_yangdo_price_logic_brainstorm.build_brainstorm(
            balance_cv={
                "records_evaluated": 361,
                "overall_publication_modes": {"range_only": 3, "full": 1, "consult_only": 0},
                "engine_internal_metrics": {
                    "median_abs_pct": 40.0,
                    "median_signed_pct": -33.0,
                    "pred_lt_actual_0_67x": 360,
                    "pred_gt_actual_1_5x": 0,
                },
                "engine_public_metrics": {"count": 1, "pred_gt_actual_1_5x": 0},
                "record_rows": record_rows,
            },
            combo_audit={
                "overall": {
                    "records": 10,
                    "visible_estimate_count": 1,
                    "range_only_count": 8,
                    "consult_only_count": 1,
                }
            },
            comparable_overall={
                "records_one_or_less_display": 307,
                "records_zero_display": 18,
                "avg_display_neighbors": 3.3,
            },
            comparable_audit={
                "sparse_support_hotspots": [{"combo_label": "A"}],
                "broad_match_hotspots": [{"combo_label": "B"}],
            },
            settlement_matrix={"invariant_failures": {"total_invariant": 0, "cash_order": 0}},
            prompt_doc="# prompt",
            runtime_source_text="\n".join(
                [
                    "total_transfer_value_eok",
                    "estimated_cash_due_eok",
                    "settlement_breakdown",
                    "strict_same_core_miss",
                    "collapse_duplicate_neighbors",
                    "publication_mode",
                    "balance_model_mode",
                ]
            ),
        )

        self.assertEqual(report["current_execution_lane"]["id"], "balance_model_none_replacement")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "exact_combo_support_recovery")
        self.assertAlmostEqual(report["summary"]["none_mode_under_67_share"], 1.0)
        self.assertTrue(report["summary"]["settlement_split_ready"])
        self.assertTrue(report["summary"]["comparable_guard_ready"])

    def test_render_markdown_includes_price_logic_sections(self):
        report = generate_yangdo_price_logic_brainstorm.build_brainstorm(
            balance_cv={
                "records_evaluated": 2,
                "overall_publication_modes": {"range_only": 1, "full": 1, "consult_only": 0},
                "engine_internal_metrics": {
                    "median_abs_pct": 12.0,
                    "median_signed_pct": -8.0,
                    "pred_lt_actual_0_67x": 0,
                    "pred_gt_actual_1_5x": 0,
                },
                "engine_public_metrics": {"count": 1, "pred_gt_actual_1_5x": 0},
                "record_rows": [
                    {
                        "combo_size": 2,
                        "actual_price_eok": 1.0,
                        "engine_internal_pred_eok": 0.95,
                        "balance_model_mode": "direct_balance_base",
                    },
                    {
                        "combo_size": 2,
                        "actual_price_eok": 1.0,
                        "engine_internal_pred_eok": 1.02,
                        "balance_model_mode": "direct_balance_base",
                    },
                ],
            },
            combo_audit={"overall": {"records": 10, "visible_estimate_count": 1, "range_only_count": 8, "consult_only_count": 1}},
            comparable_overall={"records_one_or_less_display": 20, "records_zero_display": 1, "avg_display_neighbors": 4.2},
            comparable_audit={"sparse_support_hotspots": [], "broad_match_hotspots": []},
            settlement_matrix={"invariant_failures": {"total_invariant": 0}},
            prompt_doc="# prompt\nline two",
            runtime_source_text="publication_mode\nbalance_model_mode",
        )

        markdown = generate_yangdo_price_logic_brainstorm.render_markdown(report)
        self.assertIn("Yangdo Price Logic Brainstorm", markdown)
        self.assertIn("Critical Prompt", markdown)
        self.assertIn("First-Principles Prompt", markdown)
        self.assertIn("Musk-Style Questions", markdown)
        self.assertIn("Release Decision", markdown)


if __name__ == "__main__":
    unittest.main()
