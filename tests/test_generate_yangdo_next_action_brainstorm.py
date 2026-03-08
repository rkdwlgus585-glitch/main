import unittest

from scripts import generate_yangdo_next_action_brainstorm


class GenerateYangdoNextActionBrainstormTests(unittest.TestCase):
    def test_build_brainstorm_prioritizes_single_recommendation_lane_when_audits_are_green(self):
        report = generate_yangdo_next_action_brainstorm.build_brainstorm(
            precision_matrix={
                "summary": {
                    "scenario_count": 6,
                    "failed_count": 0,
                    "sector_groups": {
                        "balance_excluded_sector": {
                            "scenario_count": 1,
                        }
                    },
                }
            },
            qa_matrix={"summary": {"scenario_count": 5, "failed_count": 0}},
            diversity_audit={"summary": {"scenario_count": 7, "failed_count": 0}},
            alignment_audit={"summary": {"issue_count": 0}},
            comparable_selection_overall={
                "records_one_or_less_display": 307,
                "records_zero_display": 18,
                "avg_display_neighbors": 3.3476,
            },
            ux_packet={"summary": {"packet_ready": True}},
            service_copy_packet={
                "summary": {
                    "service_copy_ready": True,
                    "precision_label_count": 3,
                }
            },
            prompt_doc="# prompt",
        )

        self.assertEqual(
            report["current_execution_lane"]["id"],
            "single_recommendation_autoloop",
        )
        self.assertEqual(report["summary"]["execution_lane"], "single_recommendation_autoloop")
        self.assertEqual(
            report["parallel_brainstorm_lane"]["id"],
            "special_sector_split_precision_expansion",
        )
        self.assertEqual(report["summary"]["parallel_lane"], "special_sector_split_precision_expansion")
        self.assertEqual(report["summary"]["one_or_less_display_total"], 307)
        self.assertEqual(report["summary"]["special_sector_scenario_total"], 1)
        self.assertTrue(report["summary"]["prompt_doc_ready"])

        markdown = generate_yangdo_next_action_brainstorm.render_markdown(report)
        self.assertIn("Yangdo Next Action Brainstorm", markdown)
        self.assertIn("`single_recommendation_autoloop`", markdown)
        self.assertIn("`special_sector_split_precision_expansion`", markdown)
        self.assertIn("Critical Prompt", markdown)
        self.assertIn("First-Principles Prompt", markdown)
        self.assertIn("Founder Mode Questions", markdown)
        self.assertIn("Prompt Doc Excerpt", markdown)

    def test_build_brainstorm_keeps_zero_display_guard_when_guard_audit_is_not_ready(self):
        report = generate_yangdo_next_action_brainstorm.build_brainstorm(
            precision_matrix={
                "summary": {
                    "scenario_count": 11,
                    "failed_count": 0,
                    "sector_groups": {
                        "balance_excluded_sector": {
                            "scenario_count": 6,
                        }
                    },
                }
            },
            qa_matrix={"summary": {"scenario_count": 5, "failed_count": 0}},
            diversity_audit={"summary": {"scenario_count": 7, "failed_count": 0}},
            alignment_audit={"summary": {"issue_count": 0}},
            comparable_selection_overall={
                "records_one_or_less_display": 307,
                "records_zero_display": 18,
                "avg_display_neighbors": 3.3476,
            },
            ux_packet={"summary": {"packet_ready": True}},
            service_copy_packet={"summary": {"service_copy_ready": True}},
            zero_display_audit={
                "summary": {
                    "packet_ready": True,
                    "zero_display_guard_ok": False,
                    "selected_lane_ok": False,
                }
            },
            prompt_doc="# prompt",
            runtime_source_text="\n".join(
                [
                    "recommendAutoLoopFieldId",
                    "scheduleRecommendAutoLoopEstimate",
                    "maybeRunRecommendAutoLoop",
                    "recommend-panel-followup-secondary-action",
                ]
            ),
        )

        self.assertEqual(
            report["current_execution_lane"]["id"],
            "zero_display_recovery_guard",
        )
        self.assertEqual(report["summary"]["execution_lane"], "zero_display_recovery_guard")
        self.assertEqual(
            report["parallel_brainstorm_lane"]["id"],
            "public_language_normalization",
        )
        self.assertEqual(report["summary"]["parallel_lane"], "public_language_normalization")
        self.assertTrue(report["summary"]["autoloop_ready"])
        self.assertTrue(report["summary"]["zero_recovery_ready"])
        self.assertTrue(report["summary"]["zero_display_audit_ready"])
        self.assertFalse(report["summary"]["zero_display_guard_ready"])
        self.assertFalse(report["summary"]["public_language_ready"])

    def test_build_brainstorm_advances_when_zero_display_guard_audit_is_ready(self):
        report = generate_yangdo_next_action_brainstorm.build_brainstorm(
            precision_matrix={
                "summary": {
                    "scenario_count": 11,
                    "failed_count": 0,
                    "sector_groups": {
                        "balance_excluded_sector": {
                            "scenario_count": 6,
                        }
                    },
                }
            },
            qa_matrix={"summary": {"scenario_count": 5, "failed_count": 0}},
            diversity_audit={"summary": {"scenario_count": 7, "failed_count": 0}},
            alignment_audit={"summary": {"issue_count": 0}},
            comparable_selection_overall={
                "records_one_or_less_display": 307,
                "records_zero_display": 18,
                "avg_display_neighbors": 3.3476,
            },
            ux_packet={"summary": {"packet_ready": True}},
            service_copy_packet={"summary": {"service_copy_ready": True}},
            zero_display_audit={
                "summary": {
                    "packet_ready": True,
                    "zero_display_guard_ok": True,
                    "selected_lane_ok": True,
                }
            },
            public_language_audit={
                "summary": {
                    "packet_ready": True,
                    "public_language_ready": True,
                    "remaining_phrase_count": 0,
                }
            },
            prompt_doc="# prompt",
            runtime_source_text="\n".join(
                [
                    "recommendAutoLoopFieldId",
                    "scheduleRecommendAutoLoopEstimate",
                    "maybeRunRecommendAutoLoop",
                    "recommend-panel-followup-secondary-action",
                ]
            ),
        )

        self.assertEqual(
            report["current_execution_lane"]["id"],
            "prompt_loop_operationalization",
        )
        self.assertEqual(report["summary"]["execution_lane"], "prompt_loop_operationalization")
        self.assertEqual(
            report["parallel_brainstorm_lane"]["id"],
            "service_explainability_upgrade",
        )
        self.assertEqual(report["summary"]["parallel_lane"], "service_explainability_upgrade")
        self.assertTrue(report["summary"]["zero_display_audit_ready"])
        self.assertTrue(report["summary"]["zero_display_guard_ready"])
        self.assertTrue(report["summary"]["zero_display_selected_lane_ok"])
        self.assertTrue(report["summary"]["public_language_audit_ready"])
        self.assertTrue(report["summary"]["public_language_ready"])
        self.assertEqual(report["summary"]["public_language_remaining_phrase_count"], 0)

    def test_build_brainstorm_prioritizes_regression_repair_when_any_audit_is_red(self):
        report = generate_yangdo_next_action_brainstorm.build_brainstorm(
            precision_matrix={
                "summary": {
                    "scenario_count": 6,
                    "failed_count": 1,
                    "sector_groups": {
                        "balance_excluded_sector": {
                            "scenario_count": 4,
                        }
                    },
                }
            },
            qa_matrix={"summary": {"scenario_count": 5, "failed_count": 0}},
            diversity_audit={"summary": {"scenario_count": 7, "failed_count": 0}},
            alignment_audit={"summary": {"issue_count": 0}},
            comparable_selection_overall={
                "records_one_or_less_display": 20,
                "records_zero_display": 2,
                "avg_display_neighbors": 4.2,
            },
            ux_packet={"summary": {"packet_ready": True}},
            service_copy_packet={"summary": {"service_copy_ready": True}},
            prompt_doc="# prompt",
        )

        self.assertEqual(
            report["current_execution_lane"]["id"],
            "recommendation_regression_repair",
        )
        self.assertEqual(
            report["parallel_brainstorm_lane"]["id"],
            "special_sector_split_precision_expansion",
        )
        self.assertFalse(report["summary"]["all_green"])

    def test_build_brainstorm_moves_to_special_sector_lane_when_single_recommendation_pressure_is_low(self):
        report = generate_yangdo_next_action_brainstorm.build_brainstorm(
            precision_matrix={
                "summary": {
                    "scenario_count": 6,
                    "failed_count": 0,
                    "sector_groups": {
                        "balance_excluded_sector": {
                            "scenario_count": 2,
                        }
                    },
                }
            },
            qa_matrix={"summary": {"scenario_count": 5, "failed_count": 0}},
            diversity_audit={"summary": {"scenario_count": 7, "failed_count": 0}},
            alignment_audit={"summary": {"issue_count": 0}},
            comparable_selection_overall={
                "records_one_or_less_display": 50,
                "records_zero_display": 0,
                "avg_display_neighbors": 4.8,
            },
            ux_packet={"summary": {"packet_ready": True}},
            service_copy_packet={"summary": {"service_copy_ready": True}},
            prompt_doc="",
        )

        self.assertEqual(
            report["current_execution_lane"]["id"],
            "special_sector_split_precision_expansion",
        )
        self.assertEqual(
            report["parallel_brainstorm_lane"]["id"],
            "public_language_normalization",
        )
        self.assertFalse(report["summary"]["prompt_doc_ready"])

    def test_build_brainstorm_prioritizes_special_sector_publication_guard_when_telecom_is_not_safe(self):
        report = generate_yangdo_next_action_brainstorm.build_brainstorm(
            precision_matrix={
                "summary": {
                    "scenario_count": 6,
                    "failed_count": 0,
                    "sector_groups": {
                        "balance_excluded_sector": {
                            "scenario_count": 6,
                        }
                    },
                }
            },
            qa_matrix={"summary": {"scenario_count": 5, "failed_count": 0}},
            diversity_audit={"summary": {"scenario_count": 7, "failed_count": 0}},
            alignment_audit={"summary": {"issue_count": 0}},
            comparable_selection_overall={
                "records_one_or_less_display": 50,
                "records_zero_display": 0,
                "avg_display_neighbors": 4.8,
            },
            special_sector_packet={
                "summary": {"publication_safety_ok": False},
                "sectors": [
                    {
                        "sector": "정보통신",
                        "aliases": ["통신"],
                        "publication_metrics": {
                            "publication_safety_ok": False,
                            "full_count": 7,
                            "full_share": 0.053,
                        },
                    }
                ],
            },
            ux_packet={"summary": {"packet_ready": True}},
            service_copy_packet={"summary": {"service_copy_ready": True}},
            prompt_doc="",
        )

        self.assertEqual(report["current_execution_lane"]["id"], "special_sector_publication_guard")
        self.assertEqual(report["summary"]["execution_lane"], "special_sector_publication_guard")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "public_language_normalization")
        self.assertFalse(report["summary"]["special_sector_publication_safety_ok"])
        self.assertFalse(report["summary"]["telecom_publication_safety_ok"])
        self.assertEqual(report["summary"]["telecom_full_count"], 7)
        self.assertAlmostEqual(report["summary"]["telecom_full_share"], 0.053, places=4)


if __name__ == "__main__":
    unittest.main()
