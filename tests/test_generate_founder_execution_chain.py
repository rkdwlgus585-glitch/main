import unittest

from scripts.generate_founder_execution_chain import SOURCE_STEPS, build_payload, render_markdown


class GenerateFounderExecutionChainTests(unittest.TestCase):
    def test_source_steps_refresh_yangdo_audits_before_brainstorm(self):
        step_ids = [step_id for step_id, _ in SOURCE_STEPS]
        self.assertIn("yangdo_public_language_audit", step_ids)
        self.assertLess(step_ids.index("yangdo_service_copy_packet"), step_ids.index("yangdo_zero_display_recovery_audit"))
        self.assertLess(step_ids.index("yangdo_zero_display_recovery_audit"), step_ids.index("yangdo_next_action_brainstorm"))
        self.assertLess(step_ids.index("yangdo_public_language_audit"), step_ids.index("yangdo_next_action_brainstorm"))
        self.assertLess(step_ids.index("yangdo_next_action_brainstorm"), step_ids.index("founder_mode_prompt_bundle"))

    def test_build_payload_marks_successor_transition_and_convergence(self):
        payload = build_payload(
            step_results=[
                {"step_id": "founder_mode_prompt_bundle", "script": "generate_founder_mode_prompt_bundle.py", "returncode": 0, "ok": True},
                {"step_id": "pass_1:next_batch_focus_packet", "script": "generate_next_batch_focus_packet.py", "returncode": 0, "ok": True},
                {"step_id": "pass_1:next_execution_packet", "script": "generate_next_execution_packet.py", "returncode": 0, "ok": True},
            ],
            founder_bundle={
                "summary": {
                    "primary_system": "permit",
                    "primary_lane_id": "prompt_case_binding",
                }
            },
            next_batch_focus={
                "summary": {
                    "selected_track": "permit",
                    "selected_lane_id": "partner_binding_parity",
                    "selection_policy": "founder_successor_ready_now",
                    "founder_primary_ready": True,
                    "founder_successor_selected": True,
                    "selected_matches_founder": False,
                }
            },
            next_execution={
                "summary": {
                    "selected_track": "permit",
                    "selected_lane_id": "partner_binding_parity",
                    "founder_selected_matches_primary": False,
                }
            },
            operations={
                "decisions": {
                    "permit_prompt_case_binding_ready": True,
                    "permit_partner_binding_parity_ready": True,
                    "next_execution_ready": True,
                }
            },
            stabilization_passes=[
                {
                    "pass_index": 1,
                    "focus_track": "permit",
                    "focus_lane_id": "partner_binding_parity",
                    "execution_track": "permit",
                    "execution_lane_id": "partner_binding_parity",
                    "converged": True,
                }
            ],
        )

        summary = payload["summary"]
        self.assertTrue(summary["overall_ok"])
        self.assertTrue(summary["focus_matches_execution"])
        self.assertTrue(summary["founder_successor_transition"])
        self.assertTrue(summary["permit_prompt_case_binding_ready"])
        self.assertTrue(summary["permit_partner_binding_parity_ready"])
        self.assertEqual(summary["selection_policy"], "founder_successor_ready_now")
        self.assertEqual(summary["execution_selected_lane_id"], "partner_binding_parity")

        markdown = render_markdown(payload)
        self.assertIn("Founder Execution Chain", markdown)
        self.assertIn("founder_successor_transition", markdown)
        self.assertIn("partner_binding_parity", markdown)


if __name__ == "__main__":
    unittest.main()
