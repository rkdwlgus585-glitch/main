import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_next_execution_packet import build_packet


class GenerateNextExecutionPacketTests(unittest.TestCase):
    def test_build_packet_embeds_founder_contract_for_selected_lane(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            focus = base / "focus.json"
            operations = base / "operations.json"
            system_split = base / "split.json"
            yangdo_zero = base / "yangdo_zero.json"
            yangdo_copy = base / "yangdo_copy.json"
            permit_alignment = base / "permit_alignment.json"
            permit_critical_prompt = base / "permit_critical_prompt.json"
            permit_partner_binding = base / "permit_partner_binding.json"
            permit_thinking_prompt_bundle = base / "permit_thinking_prompt_bundle.json"
            partner_flow = base / "partner_flow.json"
            platform_review = base / "platform_review.json"
            founder_bundle = base / "founder_bundle.json"

            focus.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "selected_track": "yangdo",
                            "selected_lane_id": "zero_display_recovery_guard",
                        },
                        "selected_focus": {
                            "track": "yangdo",
                            "lane_id": "zero_display_recovery_guard",
                            "title": "zero-display recovery guard",
                            "execution_prompt": "yangdo prompt",
                            "next_move": "lock fallback CTA order",
                        },
                        "parallel_candidates": [
                            {
                                "track": "permit",
                                "lane_id": "demo_surface_observability",
                                "title": "permit parallel execution",
                                "actionability": "ready_now",
                                "next_move": "tighten permit operator observability",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            operations.write_text(
                json.dumps(
                    {
                        "decisions": {
                            "seoul_live_decision": "awaiting_live_confirmation",
                            "partner_activation_decision": "awaiting_partner_inputs",
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            system_split.write_text(
                json.dumps(
                    {
                        "tracks": {
                            "yangdo": {
                                "goal": "recommendation recovery lane",
                                "current_bottleneck": "zero_display_recovery_guard",
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            yangdo_zero.write_text(
                json.dumps(
                    {
                        "summary": {
                            "zero_display_guard_ok": True,
                            "zero_display_total": 3,
                            "selected_lane_ok": True,
                            "runtime_ready": True,
                            "market_bridge_route_ok": True,
                            "consult_first_ready": True,
                            "zero_policy_ready": True,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            yangdo_copy.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_alignment.write_text(json.dumps({"summary": {"alignment_ok": True}}, ensure_ascii=False), encoding="utf-8")
            permit_critical_prompt.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_partner_binding.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_thinking_prompt_bundle.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            partner_flow.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            platform_review.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            founder_bundle.write_text(
                json.dumps(
                    {
                        "summary": {
                            "primary_system": "yangdo",
                            "primary_lane_id": "zero_display_recovery_guard",
                            "parallel_system": "permit",
                            "parallel_lane_id": "demo_surface_observability",
                        },
                        "execution_checklist": [
                            "Do not expose price or price-band hints inside recommendation cards.",
                            "Lock one-or-less recommendation behavior in smoke/runtime tests.",
                        ],
                        "shipping_gates": [
                            "Recommendation cards must not expose price figures or price-band wording.",
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_packet(
                focus_path=focus,
                operations_path=operations,
                system_split_path=system_split,
                yangdo_zero_path=yangdo_zero,
                yangdo_copy_path=yangdo_copy,
                permit_alignment_path=permit_alignment,
                permit_critical_prompt_path=permit_critical_prompt,
                permit_partner_binding_path=permit_partner_binding,
                permit_thinking_prompt_bundle_path=permit_thinking_prompt_bundle,
                partner_flow_path=partner_flow,
                platform_review_path=platform_review,
                founder_bundle_path=founder_bundle,
            )

            self.assertTrue(payload["summary"]["packet_ready"])
            self.assertEqual(payload["summary"]["selected_track"], "yangdo")
            self.assertEqual(payload["summary"]["selected_lane_id"], "zero_display_recovery_guard")
            self.assertTrue(payload["summary"]["execution_ready"])
            self.assertTrue(payload["summary"]["founder_selected_matches_primary"])
            self.assertEqual(payload["summary"]["parallel_track"], "permit")
            self.assertEqual(payload["summary"]["parallel_lane_id"], "demo_surface_observability")
            self.assertTrue(payload["summary"]["parallel_matches_founder"])
            self.assertIn("yangdo_zero_display_guard_ok == true", payload["selected_execution"]["success_criteria"])
            self.assertEqual(payload["parallel_execution"]["lane_id"], "demo_surface_observability")
            self.assertTrue(payload["parallel_execution"]["matches_founder_parallel"])
            self.assertEqual(payload["founder_mode"]["primary_system"], "yangdo")
            self.assertEqual(payload["founder_mode"]["primary_lane_id"], "zero_display_recovery_guard")
            self.assertIn(
                "Do not expose price or price-band hints inside recommendation cards.",
                payload["founder_mode"]["execution_checklist"],
            )
            self.assertIn(
                "Recommendation cards must not expose price figures or price-band wording.",
                payload["founder_mode"]["shipping_gates"],
            )
            self.assertEqual(payload["context"]["track_goal"], "recommendation recovery lane")

    def test_build_packet_requires_permit_critical_prompt_surface_for_permit_lane(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            focus = base / "focus.json"
            operations = base / "operations.json"
            system_split = base / "split.json"
            yangdo_zero = base / "yangdo_zero.json"
            yangdo_copy = base / "yangdo_copy.json"
            permit_alignment = base / "permit_alignment.json"
            permit_critical_prompt = base / "permit_critical_prompt.json"
            permit_partner_binding = base / "permit_partner_binding.json"
            permit_thinking_prompt_bundle = base / "permit_thinking_prompt_bundle.json"
            partner_flow = base / "partner_flow.json"
            platform_review = base / "platform_review.json"
            founder_bundle = base / "founder_bundle.json"

            focus.write_text(json.dumps({
                "summary": {"packet_ready": True, "selected_track": "permit", "selected_lane_id": "prompt_case_binding"},
                "selected_focus": {
                    "track": "permit",
                    "lane_id": "prompt_case_binding",
                    "title": "prompt case binding",
                    "execution_prompt": "permit prompt",
                    "next_move": "bind founder prompts to representative cases",
                },
                "parallel_candidates": [{"track": "yangdo"}],
            }, ensure_ascii=False), encoding="utf-8")
            operations.write_text(json.dumps({"decisions": {"seoul_live_decision": "awaiting_live_confirmation", "partner_activation_decision": "awaiting_partner_inputs"}}, ensure_ascii=False), encoding="utf-8")
            system_split.write_text(json.dumps({"tracks": {"permit": {"goal": "prompt-to-case binding", "current_bottleneck": "operator packets do not expose founder jump targets"}}}, ensure_ascii=False), encoding="utf-8")
            yangdo_zero.write_text(json.dumps({"summary": {"zero_display_guard_ok": True}}, ensure_ascii=False), encoding="utf-8")
            yangdo_copy.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_alignment.write_text(json.dumps({"summary": {"alignment_ok": True, "service_story_ok": True, "lane_positioning_ok": True}}, ensure_ascii=False), encoding="utf-8")
            permit_critical_prompt.write_text(json.dumps({"summary": {"packet_ready": True, "lane_id": "prompt_case_binding", "founder_lane_match": True, "prompt_case_binding_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_partner_binding.write_text(json.dumps({"summary": {"packet_ready": True, "family_total": 2, "partner_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_thinking_prompt_bundle.write_text(json.dumps({"summary": {"packet_ready": False}}, ensure_ascii=False), encoding="utf-8")
            partner_flow.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            platform_review.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            founder_bundle.write_text(json.dumps({
                "summary": {
                    "primary_system": "permit",
                    "primary_lane_id": "prompt_case_binding",
                    "parallel_system": "yangdo",
                    "parallel_lane_id": "zero_display_recovery_guard",
                },
                "execution_checklist": ["keep founder questions bound to representative permit cases"],
                "shipping_gates": ["do not hide the founder prompt-to-case bridge"],
            }, ensure_ascii=False), encoding="utf-8")

            payload = build_packet(
                focus_path=focus,
                operations_path=operations,
                system_split_path=system_split,
                yangdo_zero_path=yangdo_zero,
                yangdo_copy_path=yangdo_copy,
                permit_alignment_path=permit_alignment,
                permit_critical_prompt_path=permit_critical_prompt,
                permit_partner_binding_path=permit_partner_binding,
                permit_thinking_prompt_bundle_path=permit_thinking_prompt_bundle,
                partner_flow_path=partner_flow,
                platform_review_path=platform_review,
                founder_bundle_path=founder_bundle,
            )

            self.assertEqual(payload["summary"]["selected_track"], "permit")
            self.assertTrue(payload["summary"]["execution_ready"])
            self.assertIn("permit_critical_prompt_surface_ready == true", payload["selected_execution"]["success_criteria"])
            self.assertIn("permit_prompt_case_binding_ready == true", payload["selected_execution"]["success_criteria"])
            self.assertIn("permit_partner_binding_parity_ready == true", payload["selected_execution"]["success_criteria"])
            self.assertIn("py -3 H:\\auto\\scripts\\generate_permit_critical_prompt_surface_packet.py", payload["selected_execution"]["verification_commands"])
            self.assertIn("py -3 H:\\auto\\scripts\\generate_permit_partner_binding_parity_packet.py", payload["selected_execution"]["verification_commands"])
            self.assertEqual(payload["founder_mode"]["primary_system"], "permit")
            self.assertTrue(payload["summary"]["founder_selected_matches_primary"])
            self.assertEqual(payload["summary"]["parallel_track"], "yangdo")

    def test_build_packet_supports_permit_review_reason_decision_ladder_lane(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            focus = base / "focus.json"
            operations = base / "operations.json"
            system_split = base / "split.json"
            yangdo_zero = base / "yangdo_zero.json"
            yangdo_copy = base / "yangdo_copy.json"
            permit_alignment = base / "permit_alignment.json"
            permit_critical_prompt = base / "permit_critical_prompt.json"
            permit_partner_binding = base / "permit_partner_binding.json"
            permit_thinking_prompt_bundle = base / "permit_thinking_prompt_bundle.json"
            partner_flow = base / "partner_flow.json"
            platform_review = base / "platform_review.json"
            founder_bundle = base / "founder_bundle.json"

            focus.write_text(json.dumps({
                "summary": {"packet_ready": True, "selected_track": "permit", "selected_lane_id": "review_reason_decision_ladder"},
                "selected_focus": {
                    "track": "permit",
                    "lane_id": "review_reason_decision_ladder",
                    "title": "review reason decision ladder",
                    "execution_prompt": "permit prompt",
                    "next_move": "compress review reasons into a shorter decision ladder",
                },
                "parallel_candidates": [{"track": "yangdo"}],
            }, ensure_ascii=False), encoding="utf-8")
            operations.write_text(json.dumps({"decisions": {"seoul_live_decision": "awaiting_live_confirmation", "partner_activation_decision": "awaiting_partner_inputs"}}, ensure_ascii=False), encoding="utf-8")
            system_split.write_text(json.dumps({"tracks": {"permit": {"goal": "review reasons lead directly to next action", "current_bottleneck": "review_reason_decision_ladder"}}}, ensure_ascii=False), encoding="utf-8")
            yangdo_zero.write_text(json.dumps({"summary": {"zero_display_guard_ok": True}}, ensure_ascii=False), encoding="utf-8")
            yangdo_copy.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_alignment.write_text(json.dumps({"summary": {"alignment_ok": True, "service_story_ok": True, "lane_positioning_ok": True, "permit_offering_count": 3}}, ensure_ascii=False), encoding="utf-8")
            permit_critical_prompt.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_partner_binding.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_thinking_prompt_bundle.write_text(json.dumps({"summary": {"packet_ready": False}}, ensure_ascii=False), encoding="utf-8")
            partner_flow.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            platform_review.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            founder_bundle.write_text(json.dumps({
                "summary": {
                    "primary_system": "permit",
                    "primary_lane_id": "review_reason_decision_ladder",
                    "parallel_system": "yangdo",
                    "parallel_lane_id": "public_language_normalization",
                },
            }, ensure_ascii=False), encoding="utf-8")

            payload = build_packet(
                focus_path=focus,
                operations_path=operations,
                system_split_path=system_split,
                yangdo_zero_path=yangdo_zero,
                yangdo_copy_path=yangdo_copy,
                permit_alignment_path=permit_alignment,
                permit_critical_prompt_path=permit_critical_prompt,
                permit_partner_binding_path=permit_partner_binding,
                permit_thinking_prompt_bundle_path=permit_thinking_prompt_bundle,
                partner_flow_path=partner_flow,
                platform_review_path=platform_review,
                founder_bundle_path=founder_bundle,
            )

            self.assertEqual(payload["summary"]["selected_track"], "permit")
            self.assertEqual(payload["summary"]["selected_lane_id"], "review_reason_decision_ladder")
            self.assertTrue(payload["summary"]["execution_ready"])
            self.assertEqual(payload["summary"]["parallel_track"], "yangdo")
            self.assertIn("permit_service_copy_ready == true", payload["selected_execution"]["success_criteria"])
            self.assertIn("permit_service_ux_ready == true", payload["selected_execution"]["success_criteria"])
            self.assertIn("py -3 H:\\auto\\scripts\\generate_permit_service_ux_packet.py", payload["selected_execution"]["verification_commands"])
            self.assertTrue(payload["summary"]["founder_selected_matches_primary"])

    def test_build_packet_supports_permit_partner_binding_observability_lane(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            focus = base / "focus.json"
            operations = base / "operations.json"
            system_split = base / "split.json"
            yangdo_zero = base / "yangdo_zero.json"
            yangdo_copy = base / "yangdo_copy.json"
            permit_alignment = base / "permit_alignment.json"
            permit_critical_prompt = base / "permit_critical_prompt.json"
            permit_partner_binding = base / "permit_partner_binding.json"
            permit_partner_binding_observability = base / "permit_partner_binding_observability.json"
            permit_thinking_prompt_bundle = base / "permit_thinking_prompt_bundle.json"
            partner_flow = base / "partner_flow.json"
            platform_review = base / "platform_review.json"
            founder_bundle = base / "founder_bundle.json"

            focus.write_text(json.dumps({
                "summary": {"packet_ready": True, "selected_track": "permit", "selected_lane_id": "partner_binding_observability"},
                "selected_focus": {
                    "track": "permit",
                    "lane_id": "partner_binding_observability",
                    "title": "partner binding observability",
                    "execution_prompt": "make partner-safe binding coverage visible",
                    "next_move": "publish missing-family preview into release and partner QA surfaces",
                },
                "parallel_candidates": [{"track": "yangdo"}],
            }, ensure_ascii=False), encoding="utf-8")
            operations.write_text(json.dumps({"decisions": {"seoul_live_decision": "awaiting_live_confirmation", "partner_activation_decision": "awaiting_partner_inputs"}}, ensure_ascii=False), encoding="utf-8")
            system_split.write_text(json.dumps({"tracks": {"permit": {"goal": "partner-safe coverage can be judged without raw logs", "current_bottleneck": "partner_binding_observability"}}}, ensure_ascii=False), encoding="utf-8")
            yangdo_zero.write_text(json.dumps({"summary": {"zero_display_guard_ok": True}}, ensure_ascii=False), encoding="utf-8")
            yangdo_copy.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_alignment.write_text(json.dumps({"summary": {"alignment_ok": True, "service_story_ok": True, "lane_positioning_ok": True}}, ensure_ascii=False), encoding="utf-8")
            permit_critical_prompt.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_partner_binding.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_partner_binding_observability.write_text(json.dumps({"summary": {"observability_ready": True, "parity_packet_ready": True, "expected_family_total": 3, "operator_binding_family_total": 3, "widget_binding_family_total": 3, "api_binding_family_total": 3, "partner_binding_surface_ready": True, "widget_missing_family_total": 0, "api_missing_family_total": 0, "widget_extra_family_total": 0, "api_extra_family_total": 0}}, ensure_ascii=False), encoding="utf-8")
            permit_thinking_prompt_bundle.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            partner_flow.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            platform_review.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            founder_bundle.write_text(json.dumps({
                "summary": {
                    "primary_system": "permit",
                    "primary_lane_id": "thinking_prompt_bundle_lock",
                    "parallel_system": "yangdo",
                    "parallel_lane_id": "prompt_loop_operationalization",
                },
            }, ensure_ascii=False), encoding="utf-8")

            payload = build_packet(
                focus_path=focus,
                operations_path=operations,
                system_split_path=system_split,
                yangdo_zero_path=yangdo_zero,
                yangdo_copy_path=yangdo_copy,
                permit_alignment_path=permit_alignment,
                permit_critical_prompt_path=permit_critical_prompt,
                permit_partner_binding_path=permit_partner_binding,
                permit_partner_binding_observability_path=permit_partner_binding_observability,
                permit_thinking_prompt_bundle_path=permit_thinking_prompt_bundle,
                partner_flow_path=partner_flow,
                platform_review_path=platform_review,
                founder_bundle_path=founder_bundle,
            )

            self.assertEqual(payload["summary"]["selected_track"], "permit")
            self.assertEqual(payload["summary"]["selected_lane_id"], "partner_binding_observability")
            self.assertTrue(payload["summary"]["execution_ready"])
            self.assertIn("permit_partner_binding_observability_ready == true", payload["selected_execution"]["success_criteria"])
            self.assertIn("py -3 H:\\auto\\scripts\\generate_permit_partner_binding_observability.py", payload["selected_execution"]["verification_commands"])

    def test_build_packet_supports_yangdo_special_sector_publication_guard_lane(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            focus = base / "focus.json"
            operations = base / "operations.json"
            system_split = base / "split.json"
            yangdo_zero = base / "yangdo_zero.json"
            yangdo_copy = base / "yangdo_copy.json"
            yangdo_special_sector = base / "yangdo_special_sector.json"
            permit_alignment = base / "permit_alignment.json"
            permit_critical_prompt = base / "permit_critical_prompt.json"
            permit_partner_binding = base / "permit_partner_binding.json"
            permit_thinking_prompt_bundle = base / "permit_thinking_prompt_bundle.json"
            partner_flow = base / "partner_flow.json"
            platform_review = base / "platform_review.json"
            founder_bundle = base / "founder_bundle.json"

            focus.write_text(json.dumps({
                "summary": {"packet_ready": True, "selected_track": "yangdo", "selected_lane_id": "special_sector_publication_guard"},
                "selected_focus": {
                    "track": "yangdo",
                    "lane_id": "special_sector_publication_guard",
                    "title": "telecom publication guard",
                    "execution_prompt": "yangdo special sector prompt",
                    "next_move": "tighten telecom publication policy",
                },
                "parallel_candidates": [{"track": "permit", "lane_id": "runtime_reasoning_guard", "title": "permit parallel"}],
            }, ensure_ascii=False), encoding="utf-8")
            operations.write_text(json.dumps({"decisions": {"seoul_live_decision": "awaiting_live_confirmation", "partner_activation_decision": "awaiting_partner_inputs"}}, ensure_ascii=False), encoding="utf-8")
            system_split.write_text(json.dumps({"tracks": {"yangdo": {"goal": "special sector public release safety", "current_bottleneck": "special_sector_publication_guard"}}}, ensure_ascii=False), encoding="utf-8")
            yangdo_zero.write_text(json.dumps({"summary": {"zero_display_guard_ok": True}}, ensure_ascii=False), encoding="utf-8")
            yangdo_copy.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            yangdo_special_sector.write_text(json.dumps({
                "summary": {
                    "packet_ready": False,
                    "publication_safety_ok": False,
                    "precision_green": True,
                    "diversity_green": True,
                    "contract_green": True,
                },
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
            }, ensure_ascii=False), encoding="utf-8")
            permit_alignment.write_text(json.dumps({"summary": {"alignment_ok": True}}, ensure_ascii=False), encoding="utf-8")
            permit_critical_prompt.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_partner_binding.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_thinking_prompt_bundle.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            partner_flow.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            platform_review.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            founder_bundle.write_text(json.dumps({
                "summary": {
                    "primary_system": "yangdo",
                    "primary_lane_id": "special_sector_publication_guard",
                    "parallel_system": "permit",
                    "parallel_lane_id": "runtime_reasoning_guard",
                }
            }, ensure_ascii=False), encoding="utf-8")

            payload = build_packet(
                focus_path=focus,
                operations_path=operations,
                system_split_path=system_split,
                yangdo_zero_path=yangdo_zero,
                yangdo_copy_path=yangdo_copy,
                yangdo_special_sector_path=yangdo_special_sector,
                permit_alignment_path=permit_alignment,
                permit_critical_prompt_path=permit_critical_prompt,
                permit_partner_binding_path=permit_partner_binding,
                permit_thinking_prompt_bundle_path=permit_thinking_prompt_bundle,
                partner_flow_path=partner_flow,
                platform_review_path=platform_review,
                founder_bundle_path=founder_bundle,
            )

            self.assertEqual(payload["summary"]["selected_track"], "yangdo")
            self.assertEqual(payload["summary"]["selected_lane_id"], "special_sector_publication_guard")
            self.assertTrue(payload["summary"]["execution_ready"])
            self.assertIn("yangdo_special_sector_publication_safe == true", payload["selected_execution"]["success_criteria"])
            self.assertIn("py -3 H:\\auto\\scripts\\generate_yangdo_special_sector_packet.py", payload["selected_execution"]["verification_commands"])
            self.assertIn("telecom_full_share=0.053", payload["selected_execution"]["evidence_points"])

    def test_build_packet_uses_permit_thinking_prompt_bundle_contract_for_thinking_lane(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            focus = base / "focus.json"
            operations = base / "operations.json"
            system_split = base / "split.json"
            yangdo_zero = base / "yangdo_zero.json"
            yangdo_copy = base / "yangdo_copy.json"
            permit_alignment = base / "permit_alignment.json"
            permit_critical_prompt = base / "permit_critical_prompt.json"
            permit_partner_binding = base / "permit_partner_binding.json"
            permit_thinking_prompt_bundle = base / "permit_thinking_prompt_bundle.json"
            partner_flow = base / "partner_flow.json"
            platform_review = base / "platform_review.json"
            founder_bundle = base / "founder_bundle.json"

            focus.write_text(json.dumps({
                "summary": {"packet_ready": True, "selected_track": "permit", "selected_lane_id": "thinking_prompt_bundle_lock"},
                "selected_focus": {
                    "track": "permit",
                    "lane_id": "thinking_prompt_bundle_lock",
                    "title": "thinking prompt bundle lock",
                    "execution_prompt": "permit bundle prompt",
                    "next_move": "lock the runtime-release-operator bundle",
                },
                "parallel_candidates": [{"track": "yangdo", "lane_id": "prompt_loop_operationalization"}],
            }, ensure_ascii=False), encoding="utf-8")
            operations.write_text(json.dumps({"decisions": {"seoul_live_decision": "awaiting_live_confirmation", "partner_activation_decision": "awaiting_partner_inputs"}}, ensure_ascii=False), encoding="utf-8")
            system_split.write_text(json.dumps({"tracks": {"permit": {"goal": "reasoning bundle", "current_bottleneck": "thinking_prompt_bundle_lock"}}}, ensure_ascii=False), encoding="utf-8")
            yangdo_zero.write_text(json.dumps({"summary": {"zero_display_guard_ok": True}}, ensure_ascii=False), encoding="utf-8")
            yangdo_copy.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            permit_alignment.write_text(json.dumps({"summary": {"alignment_ok": False}}, ensure_ascii=False), encoding="utf-8")
            permit_critical_prompt.write_text(json.dumps({"summary": {"packet_ready": False}}, ensure_ascii=False), encoding="utf-8")
            permit_partner_binding.write_text(json.dumps({"summary": {"packet_ready": False}}, ensure_ascii=False), encoding="utf-8")
            permit_thinking_prompt_bundle.write_text(json.dumps({
                "summary": {
                    "packet_ready": True,
                    "service_copy_ready": True,
                    "service_ux_ready": True,
                    "alignment_ok": True,
                    "public_contract_ok": True,
                    "review_reason_ready": True,
                    "prompt_case_binding_ready": True,
                    "critical_prompt_ready": True,
                    "partner_binding_ready": True,
                    "runtime_target_ready": True,
                    "release_target_ready": True,
                    "operator_target_ready": True,
                    "founder_transition_context_ready": True,
                },
                "verification_targets": [
                    "permit_thinking_prompt_bundle_runtime_target_ready == true",
                    "permit_thinking_prompt_bundle_release_target_ready == true",
                    "permit_thinking_prompt_bundle_operator_target_ready == true",
                ],
                "prompt_bundle": {
                    "execution_prompt": "permit bundle prompt",
                    "proposed_next_step": "lock the runtime-release-operator bundle",
                },
            }, ensure_ascii=False), encoding="utf-8")
            partner_flow.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            platform_review.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            founder_bundle.write_text(json.dumps({
                "summary": {
                    "primary_system": "permit",
                    "primary_lane_id": "thinking_prompt_bundle_lock",
                    "parallel_system": "yangdo",
                    "parallel_lane_id": "prompt_loop_operationalization",
                },
                "execution_checklist": ["keep runtime/release/operator reasoning aligned"],
                "shipping_gates": ["do not let permit reasoning drift across surfaces"],
            }, ensure_ascii=False), encoding="utf-8")

            payload = build_packet(
                focus_path=focus,
                operations_path=operations,
                system_split_path=system_split,
                yangdo_zero_path=yangdo_zero,
                yangdo_copy_path=yangdo_copy,
                permit_alignment_path=permit_alignment,
                permit_critical_prompt_path=permit_critical_prompt,
                permit_partner_binding_path=permit_partner_binding,
                permit_thinking_prompt_bundle_path=permit_thinking_prompt_bundle,
                partner_flow_path=partner_flow,
                platform_review_path=platform_review,
                founder_bundle_path=founder_bundle,
            )

            self.assertEqual(payload["summary"]["selected_track"], "permit")
            self.assertEqual(payload["summary"]["selected_lane_id"], "thinking_prompt_bundle_lock")
            self.assertTrue(payload["summary"]["execution_ready"])
            self.assertIn(
                "permit_thinking_prompt_bundle_runtime_target_ready == true",
                payload["selected_execution"]["success_criteria"],
            )
            self.assertIn(
                "py -3 H:\\auto\\scripts\\generate_permit_thinking_prompt_bundle_packet.py",
                payload["selected_execution"]["verification_commands"],
            )
            self.assertIn("runtime, release, and operator", payload["selected_execution"]["bottleneck"])


if __name__ == "__main__":
    unittest.main()
