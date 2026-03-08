import unittest

from scripts import generate_permit_release_bundle


class GeneratePermitReleaseBundleTests(unittest.TestCase):
    def test_build_step_specs_keeps_master_before_widget_and_api(self):
        steps = generate_permit_release_bundle.build_step_specs("py")
        names = [row["name"] for row in steps]

        self.assertEqual(names[0], "permit_focus_seed_catalog")
        self.assertLess(names.index("permit_focus_seed_catalog"), names.index("permit_focus_source_upgrade_packet"))
        self.assertLess(names.index("permit_focus_source_upgrade_packet"), names.index("permit_focus_family_registry"))
        self.assertLess(names.index("permit_focus_family_registry"), names.index("permit_precheck_html"))
        self.assertLess(names.index("permit_master_catalog"), names.index("permit_capital_registration_logic_packet"))
        self.assertLess(names.index("permit_capital_registration_logic_packet"), names.index("permit_provenance_audit"))
        self.assertLess(names.index("permit_master_catalog"), names.index("permit_provenance_audit"))
        self.assertLess(names.index("permit_provenance_audit"), names.index("permit_source_upgrade_backlog"))
        self.assertLess(names.index("permit_source_upgrade_backlog"), names.index("permit_patent_evidence_bundle"))
        self.assertLess(names.index("permit_patent_evidence_bundle"), names.index("permit_family_case_goldset"))
        self.assertLess(names.index("permit_family_case_goldset"), names.index("permit_runtime_case_assertions"))
        self.assertLess(names.index("permit_runtime_case_assertions"), names.index("permit_capital_registration_logic_packet_refresh"))
        self.assertLess(names.index("permit_capital_registration_logic_packet_refresh"), names.index("permit_review_case_presets"))
        self.assertLess(names.index("permit_runtime_case_assertions"), names.index("permit_review_case_presets"))
        self.assertLess(names.index("permit_review_case_presets"), names.index("permit_case_story_surface"))
        self.assertLess(names.index("permit_case_story_surface"), names.index("permit_operator_demo_packet"))
        self.assertLess(names.index("permit_operator_demo_packet"), names.index("permit_review_reason_decision_ladder"))
        self.assertLess(names.index("permit_review_reason_decision_ladder"), names.index("permit_prompt_case_binding_packet"))
        self.assertLess(names.index("permit_prompt_case_binding_packet"), names.index("permit_critical_prompt_surface_packet"))
        self.assertLess(names.index("permit_critical_prompt_surface_packet"), names.index("widget_rental_catalog"))
        self.assertLess(names.index("permit_review_reason_decision_ladder"), names.index("widget_rental_catalog"))
        self.assertLess(names.index("widget_rental_catalog"), names.index("api_contract_spec"))
        self.assertLess(names.index("api_contract_spec"), names.index("permit_partner_binding_parity_packet"))
        self.assertLess(names.index("permit_partner_binding_parity_packet"), names.index("permit_thinking_prompt_bundle_packet"))
        self.assertLess(names.index("permit_thinking_prompt_bundle_packet"), names.index("permit_partner_binding_observability"))
        self.assertLess(names.index("permit_partner_binding_observability"), names.index("permit_partner_gap_preview_digest"))
        self.assertLess(names.index("permit_partner_gap_preview_digest"), names.index("permit_case_release_guard"))
        self.assertLess(names.index("api_contract_spec"), names.index("permit_case_release_guard"))
        self.assertLess(names.index("permit_case_release_guard"), names.index("permit_preset_story_release_guard"))
        self.assertLess(names.index("permit_preset_story_release_guard"), names.index("permit_demo_surface_observability"))
        self.assertLess(names.index("permit_demo_surface_observability"), names.index("permit_surface_drift_digest"))
        self.assertLess(names.index("permit_surface_drift_digest"), names.index("permit_runtime_reasoning_guard"))
        self.assertLess(names.index("permit_surface_drift_digest"), names.index("permit_next_action_brainstorm"))
        self.assertLess(names.index("permit_runtime_reasoning_guard"), names.index("permit_next_action_brainstorm"))
        self.assertLess(names.index("permit_next_action_brainstorm"), names.index("founder_mode_prompt_bundle_refresh"))
        self.assertLess(names.index("founder_mode_prompt_bundle_refresh"), names.index("system_split_first_principles_packet_refresh"))
        self.assertLess(names.index("system_split_first_principles_packet_refresh"), names.index("permit_thinking_prompt_bundle_packet_refresh"))
        self.assertLess(names.index("permit_thinking_prompt_bundle_packet_refresh"), names.index("permit_closed_lane_stale_audit"))
        self.assertLess(names.index("permit_closed_lane_stale_audit"), names.index("permit_next_action_brainstorm_refresh"))
        self.assertLess(names.index("permit_operator_demo_packet"), names.index("permit_next_action_brainstorm"))
        self.assertLess(names.index("permit_provenance_audit"), names.index("widget_rental_catalog"))
        self.assertLess(names.index("permit_master_catalog"), names.index("widget_rental_catalog"))
        self.assertLess(names.index("permit_master_catalog"), names.index("api_contract_spec"))

    def test_build_manifest_marks_release_ready_when_all_steps_pass(self):
        manifest = generate_permit_release_bundle.build_manifest(
            python_executable="py",
            step_results=[
                {"name": "permit_master_catalog", "ok": True, "returncode": 0},
                {"name": "widget_rental_catalog", "ok": True, "returncode": 0},
            ],
            case_release_guard_report={
                "summary": {
                    "release_guard_ready": True,
                    "family_total": 6,
                    "case_total": 36,
                    "runtime_failed_case_total": 0,
                    "runtime_missing_case_total": 0,
                    "widget_missing_case_total": 0,
                    "api_missing_case_total": 0,
                    "runtime_extra_case_total": 0,
                    "widget_extra_case_total": 0,
                    "api_extra_case_total": 0,
                },
                "missing": {},
            },
            review_case_presets_report={
                "summary": {
                    "preset_ready": True,
                    "preset_total": 18,
                    "manual_review_expected_total": 6,
                }
            },
            case_story_surface_report={
                "summary": {
                    "story_ready": True,
                    "story_family_total": 6,
                    "review_reason_total": 3,
                    "manual_review_family_total": 6,
                }
            },
            preset_story_release_guard_report={
                "summary": {
                    "preset_story_guard_ready": True,
                    "runtime_review_preset_surface_ready": True,
                    "runtime_case_story_surface_ready": True,
                    "story_contract_parity_ready": True,
                }
            },
            operator_demo_packet_report={
                "summary": {
                    "operator_demo_ready": True,
                    "family_total": 6,
                    "demo_case_total": 18,
                }
            },
            review_reason_decision_ladder_report={
                "summary": {
                    "review_reason_total": 3,
                    "manual_review_gate_total": 1,
                    "prompt_bound_reason_total": 3,
                    "decision_ladder_ready": True,
                }
            },
            prompt_case_binding_packet_report={"summary": {"packet_ready": True}},
            critical_prompt_surface_packet_report={"summary": {"packet_ready": True}},
            partner_binding_parity_packet_report={"summary": {"packet_ready": True}},
            thinking_prompt_bundle_packet_report={
                "summary": {
                    "packet_ready": True,
                    "prompt_section_total": 9,
                    "operator_jump_case_total": 18,
                    "decision_ladder_row_total": 3,
                    "runtime_target_ready": True,
                    "release_target_ready": True,
                    "operator_target_ready": True,
                }
            },
            partner_binding_observability_report={
                "summary": {
                    "observability_ready": True,
                    "expected_family_total": 6,
                    "widget_binding_family_total": 6,
                    "api_binding_family_total": 6,
                    "widget_missing_family_total": 0,
                    "api_missing_family_total": 0,
                }
            },
            partner_gap_preview_digest_report={
                "summary": {
                    "digest_ready": True,
                    "blank_binding_preset_total": 0,
                    "widget_preset_mismatch_total": 0,
                    "api_preset_mismatch_total": 0,
                }
            },
            capital_registration_logic_packet_report={
                "summary": {
                    "packet_ready": True,
                    "focus_target_total": 51,
                    "family_total": 6,
                    "capital_evidence_missing_total": 50,
                    "technical_evidence_missing_total": 8,
                    "other_evidence_missing_total": 1,
                    "primary_gap_id": "capital_evidence_backfill",
                }
            },
            demo_surface_observability_report={
                "summary": {
                    "observability_ready": True,
                }
            },
            closed_lane_stale_audit_report={
                "summary": {
                    "audit_ready": True,
                    "closed_lane_id": "runtime_reasoning_guard",
                    "stale_reference_total": 0,
                    "stale_artifact_total": 0,
                    "stale_primary_lane_total": 0,
                    "stale_system_bottleneck_total": 0,
                    "stale_prompt_bundle_lane_total": 0,
                }
            },
            surface_drift_digest_report={
                "summary": {
                    "digest_ready": True,
                    "delta_ready": True,
                    "changed_surface_total": 2,
                    "readiness_flip_total": 1,
                    "reasoning_changed_surface_total": 1,
                    "reasoning_regression_total": 0,
                }
            },
            runtime_reasoning_guard_report={
                "summary": {
                    "guard_ready": False,
                    "binding_gap_total": 2,
                    "review_reason_total": 4,
                    "prompt_bound_reason_total": 2,
                }
            },
        )

        self.assertTrue(manifest["summary"]["release_ready"])
        self.assertEqual(manifest["summary"]["failed_total"], 0)
        self.assertEqual(manifest["summary"]["ok_total"], 2)
        self.assertTrue(manifest["summary"]["case_release_guard_ready"])
        self.assertEqual(manifest["summary"]["case_release_guard_family_total"], 6)
        self.assertEqual(manifest["summary"]["case_release_guard_case_total"], 36)
        self.assertEqual(manifest["summary"]["case_release_guard_failed_total"], 0)
        self.assertTrue(manifest["summary"]["case_release_guard_preview_ready"])
        self.assertEqual(manifest["summary"]["review_case_preset_total"], 18)
        self.assertEqual(manifest["summary"]["review_case_manual_review_total"], 6)
        self.assertEqual(manifest["summary"]["case_story_family_total"], 6)
        self.assertEqual(manifest["summary"]["case_story_review_reason_total"], 3)
        self.assertEqual(manifest["summary"]["case_story_manual_review_family_total"], 6)
        self.assertTrue(manifest["summary"]["preset_story_release_guard_ready"])
        self.assertTrue(manifest["summary"]["runtime_review_preset_surface_ready"])
        self.assertTrue(manifest["summary"]["runtime_case_story_surface_ready"])
        self.assertTrue(manifest["summary"]["story_contract_parity_ready"])
        self.assertTrue(manifest["summary"]["operator_demo_ready"])
        self.assertEqual(manifest["summary"]["operator_demo_family_total"], 6)
        self.assertEqual(manifest["summary"]["operator_demo_case_total"], 18)
        self.assertFalse(manifest["summary"]["operator_demo_release_surface_ready"])
        self.assertFalse(manifest["summary"]["partner_demo_surface_ready"])
        self.assertFalse(manifest["summary"]["partner_binding_surface_ready"])
        self.assertTrue(manifest["summary"]["prompt_case_binding_packet_ready"])
        self.assertTrue(manifest["summary"]["critical_prompt_surface_packet_ready"])
        self.assertTrue(manifest["summary"]["partner_binding_parity_packet_ready"])
        self.assertTrue(manifest["summary"]["thinking_prompt_bundle_ready"])
        self.assertEqual(manifest["summary"]["thinking_prompt_bundle_prompt_section_total"], 9)
        self.assertEqual(manifest["summary"]["thinking_prompt_bundle_operator_jump_case_total"], 18)
        self.assertEqual(manifest["summary"]["thinking_prompt_bundle_decision_ladder_row_total"], 3)
        self.assertTrue(manifest["summary"]["thinking_prompt_bundle_runtime_target_ready"])
        self.assertTrue(manifest["summary"]["thinking_prompt_bundle_release_target_ready"])
        self.assertTrue(manifest["summary"]["thinking_prompt_bundle_operator_target_ready"])
        self.assertTrue(manifest["summary"]["partner_binding_observability_ready"])
        self.assertEqual(manifest["summary"]["partner_binding_expected_family_total"], 6)
        self.assertEqual(manifest["summary"]["partner_binding_widget_family_total"], 6)
        self.assertEqual(manifest["summary"]["partner_binding_api_family_total"], 6)
        self.assertEqual(manifest["summary"]["partner_binding_widget_missing_total"], 0)
        self.assertEqual(manifest["summary"]["partner_binding_api_missing_total"], 0)
        self.assertTrue(manifest["summary"]["partner_gap_preview_digest_ready"])
        self.assertEqual(manifest["summary"]["partner_gap_preview_blank_binding_preset_total"], 0)
        self.assertEqual(manifest["summary"]["partner_gap_preview_widget_preset_mismatch_total"], 0)
        self.assertEqual(manifest["summary"]["partner_gap_preview_api_preset_mismatch_total"], 0)
        self.assertTrue(manifest["summary"]["capital_registration_logic_packet_ready"])
        self.assertEqual(manifest["summary"]["capital_registration_focus_total"], 51)
        self.assertEqual(manifest["summary"]["capital_registration_family_total"], 6)
        self.assertEqual(manifest["summary"]["capital_evidence_missing_total"], 50)
        self.assertEqual(manifest["summary"]["technical_evidence_missing_total"], 8)
        self.assertEqual(manifest["summary"]["other_evidence_missing_total"], 1)
        self.assertEqual(manifest["summary"]["capital_registration_primary_gap_id"], "capital_evidence_backfill")
        self.assertEqual(manifest["summary"]["review_reason_total"], 3)
        self.assertEqual(manifest["summary"]["review_reason_manual_review_gate_total"], 1)
        self.assertEqual(manifest["summary"]["review_reason_prompt_bound_total"], 3)
        self.assertTrue(manifest["summary"]["review_reason_decision_ladder_ready"])
        self.assertTrue(manifest["summary"]["demo_surface_observability_ready"])
        self.assertFalse(manifest["summary"]["runtime_reasoning_guard_ready"])
        self.assertEqual(manifest["summary"]["runtime_reasoning_binding_gap_total"], 2)
        self.assertEqual(manifest["summary"]["runtime_reasoning_review_reason_total"], 4)
        self.assertEqual(manifest["summary"]["runtime_reasoning_prompt_bound_total"], 2)
        self.assertTrue(manifest["summary"]["closed_lane_stale_audit_ready"])
        self.assertEqual(manifest["summary"]["closed_lane_id"], "runtime_reasoning_guard")
        self.assertEqual(manifest["summary"]["closed_lane_stale_reference_total"], 0)
        self.assertTrue(manifest["summary"]["surface_drift_digest_ready"])
        self.assertTrue(manifest["summary"]["surface_drift_digest_delta_ready"])
        self.assertEqual(manifest["summary"]["surface_drift_changed_surface_total"], 2)
        self.assertEqual(manifest["summary"]["surface_drift_readiness_flip_total"], 1)
        self.assertEqual(manifest["summary"]["surface_drift_reasoning_changed_surface_total"], 1)
        self.assertEqual(manifest["summary"]["surface_drift_reasoning_regression_total"], 0)
        self.assertTrue(manifest["summary"]["critical_prompt_doc_ready"])
        self.assertTrue(manifest["summary"]["critical_prompt_doc_excerpt"])

    def test_build_manifest_marks_first_failure_as_blocking(self):
        manifest = generate_permit_release_bundle.build_manifest(
            python_executable="py",
            step_results=[
                {"name": "permit_master_catalog", "ok": True, "returncode": 0},
                {"name": "widget_rental_catalog", "ok": False, "returncode": 1},
                {"name": "api_contract_spec", "ok": True, "returncode": 0},
            ],
        )

        self.assertFalse(manifest["summary"]["release_ready"])
        self.assertEqual(manifest["summary"]["failed_total"], 1)
        self.assertEqual(manifest["summary"]["blocking_failure_name"], "widget_rental_catalog")

    def test_build_manifest_includes_partner_qa_snapshot_preview(self):
        manifest = generate_permit_release_bundle.build_manifest(
            python_executable="py",
            step_results=[{"name": "permit_case_release_guard", "ok": True, "returncode": 0}],
            case_release_guard_report={
                "summary": {
                    "release_guard_ready": False,
                    "family_total": 6,
                    "case_total": 36,
                    "runtime_failed_case_total": 1,
                    "runtime_missing_case_total": 1,
                    "widget_missing_case_total": 0,
                    "api_missing_case_total": 2,
                    "runtime_extra_case_total": 0,
                    "widget_extra_case_total": 0,
                    "api_extra_case_total": 0,
                },
                "missing": {
                    "runtime_cases": ["case-r1"],
                    "widget_cases": [],
                    "api_cases": ["case-a1", "case-a2"],
                },
            },
            review_case_presets_report={
                "summary": {
                    "preset_ready": True,
                    "preset_total": 18,
                    "manual_review_expected_total": 6,
                }
            },
            case_story_surface_report={
                "summary": {
                    "story_ready": True,
                    "story_family_total": 6,
                    "review_reason_total": 3,
                    "manual_review_family_total": 6,
                }
            },
            preset_story_release_guard_report={
                "summary": {
                    "preset_story_guard_ready": True,
                    "runtime_review_preset_surface_ready": True,
                    "runtime_case_story_surface_ready": True,
                    "story_contract_parity_ready": True,
                }
            },
            operator_demo_packet_report={
                "summary": {
                    "operator_demo_ready": True,
                    "family_total": 6,
                    "demo_case_total": 18,
                }
            },
            review_reason_decision_ladder_report={
                "summary": {
                    "review_reason_total": 3,
                    "manual_review_gate_total": 1,
                    "prompt_bound_reason_total": 3,
                    "decision_ladder_ready": True,
                }
            },
            prompt_case_binding_packet_report={"summary": {"packet_ready": False}},
            critical_prompt_surface_packet_report={"summary": {"packet_ready": False}},
            partner_binding_parity_packet_report={"summary": {"packet_ready": False}},
            thinking_prompt_bundle_packet_report={
                "summary": {
                    "packet_ready": False,
                    "prompt_section_total": 0,
                    "operator_jump_case_total": 0,
                    "decision_ladder_row_total": 0,
                    "runtime_target_ready": False,
                    "release_target_ready": False,
                    "operator_target_ready": False,
                }
            },
            partner_binding_observability_report={
                "summary": {
                    "observability_ready": False,
                    "expected_family_total": 6,
                    "widget_binding_family_total": 5,
                    "api_binding_family_total": 4,
                    "widget_missing_family_total": 1,
                    "api_missing_family_total": 2,
                },
                "widget_missing_preview": [{"claim_id": "claim-w1"}],
                "api_missing_preview": [{"claim_id": "claim-a1"}, {"claim_id": "claim-a2"}],
            },
            partner_gap_preview_digest_report={
                "summary": {
                    "digest_ready": False,
                    "blank_binding_preset_total": 1,
                    "widget_preset_mismatch_total": 1,
                    "api_preset_mismatch_total": 2,
                },
                "blank_binding_preset_preview": [{"claim_id": "claim-gap"}],
            },
            capital_registration_logic_packet_report={
                "summary": {
                    "packet_ready": True,
                    "focus_target_total": 51,
                    "family_total": 6,
                    "capital_evidence_missing_total": 50,
                    "technical_evidence_missing_total": 8,
                    "other_evidence_missing_total": 1,
                    "primary_gap_id": "capital_evidence_backfill",
                }
            },
            demo_surface_observability_report={
                "summary": {
                    "observability_ready": False,
                }
            },
            closed_lane_stale_audit_report={
                "summary": {
                    "audit_ready": False,
                    "closed_lane_id": "runtime_reasoning_guard",
                    "stale_reference_total": 3,
                    "stale_artifact_total": 2,
                    "stale_primary_lane_total": 1,
                    "stale_system_bottleneck_total": 1,
                    "stale_prompt_bundle_lane_total": 1,
                }
            },
            surface_drift_digest_report={
                "summary": {
                    "digest_ready": False,
                    "delta_ready": False,
                    "changed_surface_total": 0,
                    "readiness_flip_total": 0,
                }
            },
        )

        self.assertEqual(manifest["partner_qa_snapshot"]["failed_total"], 4)
        self.assertEqual(manifest["partner_qa_snapshot"]["review_case_preset_total"], 18)
        self.assertEqual(manifest["partner_qa_snapshot"]["case_story_family_total"], 6)
        self.assertEqual(manifest["partner_qa_snapshot"]["case_story_review_reason_total"], 3)
        self.assertEqual(manifest["partner_qa_snapshot"]["case_story_manual_review_family_total"], 6)
        self.assertTrue(manifest["partner_qa_snapshot"]["preset_story_release_guard_ready"])
        self.assertTrue(manifest["partner_qa_snapshot"]["runtime_review_preset_surface_ready"])
        self.assertTrue(manifest["partner_qa_snapshot"]["runtime_case_story_surface_ready"])
        self.assertTrue(manifest["partner_qa_snapshot"]["story_contract_parity_ready"])
        self.assertTrue(manifest["partner_qa_snapshot"]["operator_demo_ready"])
        self.assertEqual(manifest["partner_qa_snapshot"]["operator_demo_family_total"], 6)
        self.assertEqual(manifest["partner_qa_snapshot"]["operator_demo_case_total"], 18)
        self.assertFalse(manifest["partner_qa_snapshot"]["operator_demo_release_surface_ready"])
        self.assertFalse(manifest["partner_qa_snapshot"]["partner_demo_surface_ready"])
        self.assertFalse(manifest["partner_qa_snapshot"]["partner_binding_surface_ready"])
        self.assertFalse(manifest["partner_qa_snapshot"]["thinking_prompt_bundle_ready"])
        self.assertFalse(manifest["partner_qa_snapshot"]["partner_binding_observability_ready"])
        self.assertEqual(manifest["partner_qa_snapshot"]["partner_binding_widget_missing_total"], 1)
        self.assertEqual(manifest["partner_qa_snapshot"]["partner_binding_api_missing_total"], 2)
        self.assertFalse(manifest["partner_qa_snapshot"]["partner_gap_preview_digest_ready"])
        self.assertEqual(manifest["partner_qa_snapshot"]["partner_gap_preview_blank_binding_preset_total"], 1)
        self.assertEqual(manifest["partner_qa_snapshot"]["partner_gap_preview_widget_preset_mismatch_total"], 1)
        self.assertEqual(manifest["partner_qa_snapshot"]["partner_gap_preview_api_preset_mismatch_total"], 2)
        self.assertTrue(manifest["partner_qa_snapshot"]["capital_registration_logic_packet_ready"])
        self.assertEqual(manifest["partner_qa_snapshot"]["capital_registration_focus_total"], 51)
        self.assertEqual(manifest["partner_qa_snapshot"]["capital_registration_family_total"], 6)
        self.assertEqual(manifest["partner_qa_snapshot"]["capital_evidence_missing_total"], 50)
        self.assertEqual(manifest["partner_qa_snapshot"]["technical_evidence_missing_total"], 8)
        self.assertEqual(manifest["partner_qa_snapshot"]["other_evidence_missing_total"], 1)
        self.assertEqual(manifest["partner_qa_snapshot"]["capital_registration_primary_gap_id"], "capital_evidence_backfill")
        self.assertEqual(manifest["partner_qa_snapshot"]["review_reason_total"], 3)
        self.assertEqual(manifest["partner_qa_snapshot"]["review_reason_manual_review_gate_total"], 1)
        self.assertEqual(manifest["partner_qa_snapshot"]["review_reason_prompt_bound_total"], 3)
        self.assertTrue(manifest["partner_qa_snapshot"]["review_reason_decision_ladder_ready"])
        self.assertFalse(manifest["partner_qa_snapshot"]["demo_surface_observability_ready"])
        self.assertFalse(manifest["partner_qa_snapshot"]["closed_lane_stale_audit_ready"])
        self.assertEqual(manifest["partner_qa_snapshot"]["closed_lane_stale_reference_total"], 3)
        self.assertFalse(manifest["partner_qa_snapshot"]["surface_drift_digest_ready"])
        self.assertFalse(manifest["partner_qa_snapshot"]["surface_drift_digest_delta_ready"])
        self.assertTrue(manifest["partner_qa_snapshot"]["critical_prompt_doc_ready"])
        self.assertEqual(manifest["partner_qa_snapshot"]["runtime_missing_cases"], ["case-r1"])
        self.assertEqual(manifest["partner_qa_snapshot"]["api_missing_cases"], ["case-a1", "case-a2"])
        self.assertEqual(manifest["partner_qa_snapshot"]["partner_binding_widget_missing_preview"], ["claim-w1"])
        self.assertEqual(manifest["partner_qa_snapshot"]["partner_binding_api_missing_preview"], ["claim-a1", "claim-a2"])
        self.assertEqual(manifest["partner_qa_snapshot"]["partner_gap_preview_blank_binding_preview"], ["claim-gap"])

    def test_render_markdown_includes_critical_prompt_excerpt_when_present(self):
        markdown = generate_permit_release_bundle.render_markdown(
            {
                "generated_at": "2026-03-08 00:00:00",
                "python_executable": "py",
                "summary": {
                    "step_total": 1,
                    "ok_total": 1,
                    "failed_total": 0,
                    "blocking_failure_name": "",
                    "release_ready": True,
                    "critical_prompt_doc_excerpt": "line one\nline two",
                },
                "steps": [],
                "partner_qa_snapshot": {},
            }
        )

        self.assertIn("## Critical Prompt Excerpt", markdown)
        self.assertIn("line one", markdown)
        self.assertIn("line two", markdown)


if __name__ == "__main__":
    unittest.main()
