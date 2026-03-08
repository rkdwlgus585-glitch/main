import unittest

from scripts.generate_permit_closed_lane_stale_audit import build_audit, render_markdown


class GeneratePermitClosedLaneStaleAuditTests(unittest.TestCase):
    def test_build_audit_is_ready_when_closed_lane_is_absent(self):
        payload = build_audit(
            closed_lane_id="runtime_reasoning_guard",
            brainstorm={
                "summary": {
                    "execution_lane": "thinking_prompt_successor_alignment",
                    "parallel_lane": "closed_lane_stale_audit",
                },
                "current_execution_lane": {"id": "thinking_prompt_successor_alignment"},
                "parallel_brainstorm_lane": {"id": "closed_lane_stale_audit"},
            },
            founder_bundle={
                "summary": {"primary_lane_id": "thinking_prompt_successor_alignment"},
                "primary_execution": {"id": "thinking_prompt_successor_alignment"},
            },
            system_split_packet={
                "tracks": {"permit": {"current_bottleneck": "thinking_prompt_successor_alignment"}}
            },
            thinking_bundle={
                "summary": {
                    "lane_id": "thinking_prompt_successor_alignment",
                    "founder_primary_lane_id": "thinking_prompt_successor_alignment",
                    "current_execution_lane_id": "thinking_prompt_successor_alignment",
                    "system_current_bottleneck": "thinking_prompt_successor_alignment",
                }
            },
        )

        self.assertTrue(payload["summary"]["audit_ready"])
        self.assertEqual(payload["summary"]["stale_reference_total"], 0)
        self.assertEqual(payload["stale_references"], [])

        markdown = render_markdown(payload)
        self.assertIn("Permit Closed Lane Stale Audit", markdown)
        self.assertIn("`runtime_reasoning_guard`", markdown)
        self.assertIn("- none", markdown)

    def test_build_audit_collects_stale_authoritative_fields(self):
        payload = build_audit(
            closed_lane_id="runtime_reasoning_guard",
            brainstorm={
                "summary": {
                    "execution_lane": "runtime_reasoning_guard",
                    "parallel_lane": "closed_lane_stale_audit",
                    "runtime_reasoning_guard_exit_ready": True,
                },
                "current_execution_lane": {"id": "thinking_prompt_successor_alignment"},
                "parallel_brainstorm_lane": {"id": "runtime_reasoning_guard"},
            },
            founder_bundle={
                "summary": {"primary_lane_id": "runtime_reasoning_guard"},
                "primary_execution": {"id": "runtime_reasoning_guard"},
            },
            system_split_packet={
                "tracks": {"permit": {"current_bottleneck": "runtime_reasoning_guard"}}
            },
            thinking_bundle={
                "summary": {
                    "lane_id": "thinking_prompt_successor_alignment",
                    "founder_primary_lane_id": "runtime_reasoning_guard",
                    "current_execution_lane_id": "thinking_prompt_successor_alignment",
                    "system_current_bottleneck": "runtime_reasoning_guard",
                }
            },
        )

        summary = payload["summary"]
        self.assertFalse(summary["audit_ready"])
        self.assertEqual(summary["stale_reference_total"], 7)
        self.assertEqual(summary["stale_artifact_total"], 4)
        self.assertEqual(summary["stale_execution_lane_total"], 1)
        self.assertEqual(summary["stale_parallel_lane_total"], 1)
        self.assertEqual(summary["stale_primary_lane_total"], 2)
        self.assertEqual(summary["stale_system_bottleneck_total"], 2)
        self.assertEqual(summary["stale_prompt_bundle_lane_total"], 1)
        self.assertEqual(payload["stale_references"][0]["artifact"], "permit_next_action_brainstorm")

    def test_build_audit_skips_when_runtime_reasoning_guard_is_not_closed_yet(self):
        payload = build_audit(
            closed_lane_id="runtime_reasoning_guard",
            brainstorm={
                "summary": {
                    "execution_lane": "runtime_reasoning_guard",
                    "runtime_reasoning_guard_exit_ready": False,
                },
                "current_execution_lane": {"id": "runtime_reasoning_guard"},
            },
            founder_bundle={},
            system_split_packet={},
            thinking_bundle={},
        )

        summary = payload["summary"]
        self.assertTrue(summary["audit_ready"])
        self.assertTrue(summary["audit_skipped"])
        self.assertFalse(summary["runtime_reasoning_guard_exit_ready"])
        self.assertEqual(summary["stale_reference_total"], 0)
        self.assertEqual(payload["stale_references"], [])


if __name__ == "__main__":
    unittest.main()
