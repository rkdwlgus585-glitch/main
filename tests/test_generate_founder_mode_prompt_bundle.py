import unittest

from scripts import generate_founder_mode_prompt_bundle


class GenerateFounderModePromptBundleTests(unittest.TestCase):
    def test_build_bundle_prioritizes_yangdo_when_single_recommendation_pressure_is_higher(self):
        permit_report = {
            "summary": {
                "runtime_failed_case_total": 0,
                "case_release_guard_failed_total": 0,
                "case_release_guard_ready": True,
                "story_contract_surface_ready": True,
                "runtime_review_preset_surface_ready": True,
            },
            "current_execution_lane": {
                "id": "preset_story_release_guard",
                "priority": "P1",
                "track": "execution",
                "title": "preset/story release guard",
                "current_gap": "release parity gap",
                "proposed_next_step": "lock release guard",
                "success_metric": "guard green",
            },
            "parallel_brainstorm_lane": {
                "id": "operator_demo_packet",
                "priority": "P2",
                "track": "research",
                "title": "operator demo packet",
                "current_gap": "demo packet missing",
                "proposed_next_step": "generate demo packet",
                "success_metric": "packet ready",
            },
            "critical_prompts": {
                "founder_mode_questions": ["permit question"],
            },
        }
        yangdo_report = {
            "summary": {
                "precision_failed_count": 0,
                "qa_failed_count": 0,
                "diversity_failed_count": 0,
                "alignment_issue_count": 0,
                "one_or_less_display_total": 307,
                "zero_display_total": 18,
                "special_sector_scenario_total": 1,
            },
            "current_execution_lane": {
                "id": "single_recommendation_autoloop",
                "priority": "P1",
                "track": "execution",
                "title": "single recommendation autoloop",
                "current_gap": "one or less recommendation pressure",
                "proposed_next_step": "connect fallback CTA",
                "success_metric": "runtime green",
            },
            "parallel_brainstorm_lane": {
                "id": "special_sector_split_precision_expansion",
                "priority": "P1",
                "track": "quality",
                "title": "special sector split precision expansion",
                "current_gap": "special sector scenario shortage",
                "proposed_next_step": "expand scenarios",
                "success_metric": "scenario_count >= 6",
            },
            "critical_prompts": {
                "founder_mode_questions": ["yangdo question"],
            },
        }

        bundle = generate_founder_mode_prompt_bundle.build_bundle(
            permit_report=permit_report,
            yangdo_report=yangdo_report,
            permit_prompt_doc="# permit doc",
            yangdo_prompt_doc="# yangdo doc",
        )

        self.assertEqual(bundle["summary"]["primary_system"], "yangdo")
        self.assertEqual(bundle["summary"]["primary_lane_id"], "single_recommendation_autoloop")
        self.assertEqual(bundle["summary"]["parallel_system"], "permit")
        self.assertEqual(bundle["summary"]["parallel_lane_id"], "preset_story_release_guard")
        self.assertGreater(bundle["summary"]["yangdo_pressure_score"], bundle["summary"]["permit_pressure_score"])
        self.assertIn("permit question", bundle["founder_mode_questions"])
        self.assertIn("yangdo question", bundle["founder_mode_questions"])
        self.assertTrue(bundle["execution_checklist"])
        self.assertTrue(bundle["shipping_gates"])
        self.assertIn("ranked fallback CTAs", " ".join(bundle["execution_checklist"]))

        markdown = generate_founder_mode_prompt_bundle.render_markdown(bundle)
        self.assertIn("Founder Mode Prompt Bundle", markdown)
        self.assertIn("Unified Execution Prompt", markdown)
        self.assertIn("Anti-Patterns", markdown)
        self.assertIn("Execution Checklist", markdown)
        self.assertIn("Shipping Gates", markdown)
        self.assertIn("single_recommendation_autoloop", markdown)
        self.assertIn("preset_story_release_guard", markdown)

    def test_build_bundle_prioritizes_permit_when_release_guard_is_red(self):
        permit_report = {
            "summary": {
                "runtime_failed_case_total": 1,
                "case_release_guard_failed_total": 2,
                "case_release_guard_ready": False,
                "story_contract_surface_ready": False,
                "runtime_review_preset_surface_ready": False,
            },
            "current_execution_lane": {
                "id": "preset_story_release_guard",
                "priority": "P1",
                "track": "execution",
                "title": "preset/story release guard",
                "current_gap": "release parity gap",
                "proposed_next_step": "lock release guard",
                "success_metric": "guard green",
            },
            "parallel_brainstorm_lane": {},
            "critical_prompts": {},
        }
        yangdo_report = {
            "summary": {
                "precision_failed_count": 0,
                "qa_failed_count": 0,
                "diversity_failed_count": 0,
                "alignment_issue_count": 0,
                "one_or_less_display_total": 10,
                "zero_display_total": 0,
                "special_sector_scenario_total": 6,
            },
            "current_execution_lane": {
                "id": "single_recommendation_autoloop",
                "priority": "P1",
                "track": "execution",
                "title": "single recommendation autoloop",
                "current_gap": "one or less recommendation pressure",
                "proposed_next_step": "connect fallback CTA",
                "success_metric": "runtime green",
            },
            "parallel_brainstorm_lane": {},
            "critical_prompts": {},
        }

        bundle = generate_founder_mode_prompt_bundle.build_bundle(
            permit_report=permit_report,
            yangdo_report=yangdo_report,
        )

        self.assertEqual(bundle["summary"]["primary_system"], "permit")
        self.assertEqual(bundle["summary"]["primary_lane_id"], "preset_story_release_guard")
        self.assertIn("release-level parity guard", " ".join(bundle["execution_checklist"]))


if __name__ == "__main__":
    unittest.main()
