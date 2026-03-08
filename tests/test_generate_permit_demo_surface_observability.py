import unittest

from scripts import generate_permit_demo_surface_observability


class GeneratePermitDemoSurfaceObservabilityTests(unittest.TestCase):
    def test_build_observability_report_summarizes_runtime_and_partner_surfaces(self):
        report = generate_permit_demo_surface_observability.build_observability_report(
            brainstorm={
                "summary": {
                    "execution_lane": "critical_prompt_surface_lock",
                    "parallel_lane": "demo_surface_observability",
                    "closed_lane_stale_audit_ready": True,
                    "closed_lane_id": "runtime_reasoning_guard",
                    "closed_lane_stale_reference_total": 0,
                }
            },
            operator_demo_packet={
                "summary": {
                    "operator_demo_ready": True,
                    "family_total": 6,
                    "demo_case_total": 18,
                    "prompt_case_binding_total": 6,
                }
            },
            permit_review_reason_decision_ladder={
                "summary": {
                    "review_reason_total": 4,
                    "prompt_bound_reason_total": 4,
                }
            },
            permit_critical_prompt_surface_packet={
                "summary": {
                    "packet_ready": True,
                    "compact_lens_ready": True,
                    "runtime_surface_contract_ready": True,
                    "release_surface_contract_ready": True,
                    "operator_surface_contract_ready": True,
                    "founder_question_total": 3,
                }
            },
            widget_rental_catalog={
                "summary": {
                    "permit_partner_demo_surface_ready": True,
                    "permit_operator_demo_family_total": 6,
                    "permit_partner_demo_sample_total": 6,
                }
            },
            api_contract_spec={
                "services": {
                    "permit": {
                        "response_contract": {
                            "catalog_contracts": {
                                "master_catalog": {
                                    "current_summary": {
                                        "partner_demo_surface_ready": True,
                                        "partner_demo_family_total": 6,
                                        "partner_demo_sample_total": 6,
                                    }
                                }
                            }
                        }
                    }
                }
            },
            permit_case_release_guard={"summary": {"release_guard_ready": True, "family_total": 6, "case_total": 36}},
            permit_preset_story_release_guard={"summary": {"preset_story_guard_ready": True}},
            permit_closed_lane_stale_audit={"summary": {"audit_ready": True, "stale_reference_total": 0}},
            runtime_html="""
            <div id="operatorDemoBox"></div>
            <div id="runtimeReasoningCardBox"></div>
            <script>
            const getOperatorDemoSurface = (row) => (row && row.operator_demo_surface ? row.operator_demo_surface : null);
            const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
            const renderRuntimeReasoningCard = (industry, typedEval, context = {}) => { return [industry, typedEval, context]; };
            const marker = "operator_demo_surface";
            const promptMarker = "runtime_critical_prompt_excerpt";
            const promptLensMarker = "runtime_critical_prompt_lens";
            const promptBindingMarker = "prompt_case_binding";
            const promptBindingTotal = "runtime_prompt_case_binding_total";
            const promptBindingButton = "data-prompt-preset-id";
            const reasoningPresetButton = "data-runtime-preset-id";
            const reasoningLadderMap = "runtime_reasoning_ladder_map";
            </script>
            """,
            prompt_doc_text="# prompt\n- first principles",
        )

        summary = report["summary"]
        self.assertEqual(summary["surface_total"], 11)
        self.assertEqual(summary["ready_surface_total"], 11)
        self.assertEqual(summary["missing_surface_total"], 0)
        self.assertEqual(summary["active_execution_lane_id"], "critical_prompt_surface_lock")
        self.assertEqual(summary["active_parallel_lane_id"], "demo_surface_observability")
        self.assertTrue(summary["runtime_operator_demo_surface_ready"])
        self.assertTrue(summary["runtime_critical_prompt_surface_ready"])
        self.assertTrue(summary["critical_prompt_packet_ready"])
        self.assertTrue(summary["critical_prompt_compact_lens_ready"])
        self.assertTrue(summary["critical_prompt_runtime_contract_ready"])
        self.assertTrue(summary["critical_prompt_release_contract_ready"])
        self.assertTrue(summary["critical_prompt_operator_contract_ready"])
        self.assertTrue(summary["runtime_prompt_case_binding_surface_ready"])
        self.assertTrue(summary["runtime_reasoning_card_surface_ready"])
        self.assertEqual(summary["runtime_reasoning_review_reason_total"], 4)
        self.assertEqual(summary["runtime_reasoning_prompt_bound_total"], 4)
        self.assertEqual(summary["runtime_reasoning_binding_gap_total"], 0)
        self.assertEqual(summary["prompt_case_binding_total"], 6)
        self.assertTrue(summary["widget_partner_demo_surface_ready"])
        self.assertTrue(summary["api_partner_demo_surface_ready"])
        self.assertTrue(summary["partner_demo_surface_ready"])
        self.assertTrue(summary["closed_lane_stale_audit_ready"])
        self.assertEqual(summary["closed_lane_stale_reference_total"], 0)
        self.assertEqual(summary["surface_health_digest_total"], 4)
        self.assertTrue(summary["surface_health_digest_ready"])
        self.assertTrue(summary["observability_ready"])
        self.assertEqual(report["missing_surfaces"], [])
        self.assertEqual(len(report["surface_health_digest"]), 4)

        markdown = generate_permit_demo_surface_observability.render_markdown(report)
        self.assertIn("Permit Demo Surface Observability", markdown)
        self.assertIn("runtime_critical_prompt_surface_ready", markdown)
        self.assertIn("critical_prompt_compact_lens_ready", markdown)
        self.assertIn("runtime_prompt_case_binding_surface_ready", markdown)
        self.assertIn("runtime_reasoning_card_surface_ready", markdown)
        self.assertIn("widget_partner_demo_surface_ready", markdown)
        self.assertIn("Surface Health Digest", markdown)

    def test_build_observability_report_does_not_block_on_skipped_closed_lane_audit(self):
        report = generate_permit_demo_surface_observability.build_observability_report(
            brainstorm={"summary": {"execution_lane": "runtime_reasoning_guard", "parallel_lane": "surface_drift_digest"}},
            operator_demo_packet={"summary": {"operator_demo_ready": True, "family_total": 1, "demo_case_total": 1, "prompt_case_binding_total": 1}},
            permit_review_reason_decision_ladder={"summary": {"review_reason_total": 1, "prompt_bound_reason_total": 1}},
            permit_critical_prompt_surface_packet={
                "summary": {
                    "packet_ready": True,
                    "compact_lens_ready": True,
                    "runtime_surface_contract_ready": True,
                    "release_surface_contract_ready": True,
                    "operator_surface_contract_ready": True,
                }
            },
            widget_rental_catalog={"summary": {"permit_partner_demo_surface_ready": True}},
            api_contract_spec={
                "services": {
                    "permit": {
                        "response_contract": {
                            "catalog_contracts": {
                                "master_catalog": {"current_summary": {"partner_demo_surface_ready": True}}
                            }
                        }
                    }
                }
            },
            permit_case_release_guard={"summary": {"release_guard_ready": True}},
            permit_preset_story_release_guard={"summary": {"preset_story_guard_ready": True}},
            permit_closed_lane_stale_audit={
                "summary": {
                    "audit_ready": True,
                    "audit_skipped": True,
                    "runtime_reasoning_guard_exit_ready": False,
                    "stale_reference_total": 0,
                }
            },
            runtime_html="""
            <div id="operatorDemoBox"></div>
            <div id="runtimeReasoningCardBox"></div>
            <script>
            const getOperatorDemoSurface = (row) => (row && row.operator_demo_surface ? row.operator_demo_surface : null);
            const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
            const renderRuntimeReasoningCard = (industry, typedEval, context = {}) => { return [industry, typedEval, context]; };
            const marker = "operator_demo_surface";
            const promptMarker = "runtime_critical_prompt_excerpt";
            const promptLensMarker = "runtime_critical_prompt_lens";
            const promptBindingMarker = "prompt_case_binding";
            const promptBindingButton = "data-prompt-preset-id";
            const reasoningPresetButton = "data-runtime-preset-id";
            const reasoningLadderMap = "runtime_reasoning_ladder_map";
            </script>
            """,
            prompt_doc_text="# prompt",
        )

        summary = report["summary"]
        self.assertTrue(summary["closed_lane_stale_audit_ready"])
        self.assertTrue(summary["surface_health_digest_ready"])
        self.assertTrue(summary["observability_ready"])


if __name__ == "__main__":
    unittest.main()
