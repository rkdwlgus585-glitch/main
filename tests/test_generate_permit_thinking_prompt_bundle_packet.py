import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_permit_thinking_prompt_bundle_packet import build_packet


class GeneratePermitThinkingPromptBundlePacketTests(unittest.TestCase):
    def test_build_packet_locks_runtime_release_and_operator_targets(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            brainstorm = base / "brainstorm.json"
            founder = base / "founder.json"
            copy_packet = base / "copy.json"
            ux_packet = base / "ux.json"
            alignment = base / "alignment.json"
            public_contract = base / "public_contract.json"
            case_binding = base / "case_binding.json"
            critical_prompt = base / "critical_prompt.json"
            partner_binding = base / "partner_binding.json"
            review_reason = base / "review_reason.json"
            system_split = base / "system_split.json"
            prompt_doc = base / "permit_prompt.md"

            brainstorm.write_text(json.dumps({
                "summary": {
                    "prompt_doc_ready": True,
                    "review_reason_decision_ladder_ready": True,
                },
                "current_execution_lane": {
                    "id": "thinking_prompt_bundle_lock",
                    "title": "thinking prompt bundle lock",
                    "current_gap": "runtime/release/operator reasoning drift",
                    "evidence": "prompt bundle missing",
                    "proposed_next_step": "unify permit thinking contract",
                    "success_metric": "one canonical prompt bundle drives runtime, release, and operator prioritization",
                },
                "critical_prompts": {
                    "execution_prompt": "permit execution prompt",
                    "brainstorm_prompt": "permit brainstorm prompt",
                    "first_principles_prompt": "permit first principles prompt",
                    "founder_mode_questions": [
                        "Does this change reduce both user input time and operator decision time?"
                    ],
                },
            }, ensure_ascii=False), encoding="utf-8")
            founder.write_text(json.dumps({
                "summary": {
                    "primary_system": "permit",
                    "primary_lane_id": "thinking_prompt_bundle_lock",
                },
                "primary_execution": {
                    "id": "thinking_prompt_bundle_lock",
                    "title": "thinking prompt bundle lock",
                    "current_gap": "runtime/release/operator reasoning drift",
                    "evidence": "prompt bundle missing",
                    "proposed_next_step": "unify permit thinking contract",
                    "success_metric": "one canonical prompt bundle drives runtime, release, and operator prioritization",
                },
                "unified_prompts": {
                    "execution_prompt": "fallback execution prompt",
                    "parallel_brainstorm_prompt": "fallback brainstorm prompt",
                    "first_principles_prompt": "fallback first principles prompt",
                },
                "founder_mode_questions": [
                    "Does this change reduce both user input time and operator decision time?"
                ],
            }, ensure_ascii=False), encoding="utf-8")
            copy_packet.write_text(json.dumps({"summary": {"service_copy_ready": True}}, ensure_ascii=False), encoding="utf-8")
            ux_packet.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            alignment.write_text(json.dumps({"summary": {"alignment_ok": True}}, ensure_ascii=False), encoding="utf-8")
            public_contract.write_text(json.dumps({"summary": {"contract_ok": True}}, ensure_ascii=False), encoding="utf-8")
            case_binding.write_text(json.dumps({
                "summary": {"packet_ready": True, "founder_lane_match": True},
                "question_bindings": [
                    {"question": "Does this change reduce both user input time and operator decision time?"}
                ],
                "operator_jump_table": [
                    {
                        "claim_id": "permit-family-a",
                        "family_key": "family-a",
                        "jump_targets": [
                            {"preset_id": "preset-a"},
                            {"preset_id": "preset-b"},
                        ],
                    }
                ],
            }, ensure_ascii=False), encoding="utf-8")
            critical_prompt.write_text(json.dumps({"summary": {"packet_ready": True, "operator_surface_ready": True, "release_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            partner_binding.write_text(json.dumps({"summary": {"packet_ready": True, "partner_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            review_reason.write_text(json.dumps({"summary": {"decision_ladder_ready": True}}, ensure_ascii=False), encoding="utf-8")
            system_split.write_text(json.dumps({"tracks": {"permit": {"current_bottleneck": "thinking_prompt_bundle_lock"}}}, ensure_ascii=False), encoding="utf-8")
            prompt_doc.write_text(
                "\n".join(
                    [
                        "# Permit Prompt",
                        "## Goal",
                        "- Reduce input burden first.",
                        "## Action Frame",
                        "- Prove the bottleneck before polishing wording.",
                        "## First Principles",
                        "- Separate fact, inference, and presentation.",
                        "## Musk First Principles",
                        "- What breaks if this step is deleted?",
                        "## Founder Questions",
                        "- Does this reduce both user and operator time?",
                        "## Anti Patterns",
                        "- Do not patch wording only.",
                        "## Parallel Brainstorm Filter",
                        "- Keep only candidates that tests can verify now.",
                        "## Output Contract",
                    ]
                ),
                encoding="utf-8",
            )

            payload = build_packet(
                brainstorm_path=brainstorm,
                founder_path=founder,
                copy_path=copy_packet,
                ux_path=ux_packet,
                alignment_path=alignment,
                public_contract_path=public_contract,
                case_binding_path=case_binding,
                critical_prompt_path=critical_prompt,
                partner_binding_path=partner_binding,
                review_reason_path=review_reason,
                system_split_path=system_split,
                prompt_doc_path=prompt_doc,
            )

            summary = payload["summary"]
            self.assertTrue(summary["packet_ready"])
            self.assertEqual(summary["lane_id"], "thinking_prompt_bundle_lock")
            self.assertTrue(summary["prompt_sections_ready"])
            self.assertTrue(summary["runtime_target_ready"])
            self.assertTrue(summary["release_target_ready"])
            self.assertTrue(summary["operator_target_ready"])
            self.assertTrue(summary["founder_transition_context_ready"])
            self.assertEqual(summary["execution_principle_total"], 1)
            self.assertEqual(summary["musk_question_total"], 1)
            self.assertEqual(summary["anti_pattern_total"], 1)
            self.assertEqual(summary["parallel_filter_total"], 1)
            self.assertEqual(summary["question_binding_total"], 1)
            self.assertEqual(summary["operator_jump_family_total"], 1)
            self.assertEqual(summary["operator_jump_case_total"], 2)
            self.assertIn(
                "permit_thinking_prompt_bundle_operator_target_ready == true",
                payload["verification_targets"],
            )
            self.assertIn(
                "permit_thinking_prompt_bundle_operator_jump_case_total > 0",
                payload["verification_targets"],
            )
            self.assertIn("Goal", payload["prompt_bundle"]["prompt_sections"])
            self.assertEqual(
                payload["prompt_bundle"]["execution_principles"],
                ["Prove the bottleneck before polishing wording."],
            )
            self.assertEqual(
                payload["prompt_bundle"]["musk_questions"],
                ["What breaks if this step is deleted?"],
            )
            self.assertEqual(
                payload["prompt_bundle"]["anti_patterns"],
                ["Do not patch wording only."],
            )
            self.assertEqual(payload["prompt_bundle"]["operator_jump_preview"][0]["jump_target_total"], 2)

    def test_build_packet_stays_ready_after_execution_lane_advances(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            brainstorm = base / "brainstorm.json"
            founder = base / "founder.json"
            copy_packet = base / "copy.json"
            ux_packet = base / "ux.json"
            alignment = base / "alignment.json"
            public_contract = base / "public_contract.json"
            case_binding = base / "case_binding.json"
            critical_prompt = base / "critical_prompt.json"
            partner_binding = base / "partner_binding.json"
            review_reason = base / "review_reason.json"
            system_split = base / "system_split.json"
            prompt_doc = base / "permit_prompt.md"

            brainstorm.write_text(json.dumps({
                "current_execution_lane": {
                    "id": "runtime_reasoning_card",
                    "title": "runtime reasoning card",
                    "current_gap": "operators still scan too many panels",
                    "evidence": "prompt bundle already locked",
                    "proposed_next_step": "collapse to one reasoning card",
                    "success_metric": "one runtime card is enough to move from result to operator action",
                },
                "critical_prompts": {
                    "execution_prompt": "permit execution prompt",
                    "brainstorm_prompt": "permit brainstorm prompt",
                    "first_principles_prompt": "permit first principles prompt",
                    "founder_mode_questions": [
                        "Does this change reduce both user input time and operator decision time?"
                    ],
                },
            }, ensure_ascii=False), encoding="utf-8")
            founder.write_text(json.dumps({
                "summary": {
                    "primary_system": "permit",
                    "primary_lane_id": "thinking_prompt_bundle_lock",
                },
                "primary_execution": {
                    "id": "thinking_prompt_bundle_lock",
                    "title": "thinking prompt bundle lock",
                    "current_gap": "reasoning framework is fragmented",
                    "evidence": "bundle not yet canonicalized",
                    "proposed_next_step": "unify permit thinking contract",
                    "success_metric": "one canonical prompt bundle drives runtime, release, and operator prioritization",
                },
                "founder_mode_questions": [
                    "Does this change reduce both user input time and operator decision time?"
                ],
            }, ensure_ascii=False), encoding="utf-8")
            copy_packet.write_text(json.dumps({"summary": {"service_copy_ready": True}}, ensure_ascii=False), encoding="utf-8")
            ux_packet.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            alignment.write_text(json.dumps({"summary": {"alignment_ok": True}}, ensure_ascii=False), encoding="utf-8")
            public_contract.write_text(json.dumps({"summary": {"contract_ok": True}}, ensure_ascii=False), encoding="utf-8")
            case_binding.write_text(json.dumps({
                "summary": {"packet_ready": True},
                "question_bindings": [{"question": "q1"}],
                "operator_jump_table": [{"claim_id": "claim-1", "family_key": "family-1", "jump_targets": [{"preset_id": "preset-1"}]}],
            }, ensure_ascii=False), encoding="utf-8")
            critical_prompt.write_text(json.dumps({"summary": {"packet_ready": True, "operator_surface_ready": True, "release_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            partner_binding.write_text(json.dumps({"summary": {"packet_ready": True, "partner_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            review_reason.write_text(json.dumps({
                "summary": {"decision_ladder_ready": True},
                "ladders": [{"review_reason": "capital_shortfall_only", "inspect_first": "capital", "next_action": "top-up", "manual_review_gate": False}],
            }, ensure_ascii=False), encoding="utf-8")
            system_split.write_text(json.dumps({"tracks": {"permit": {"current_bottleneck": "thinking_prompt_bundle_lock"}}}, ensure_ascii=False), encoding="utf-8")
            prompt_doc.write_text("# Permit Prompt\n## Goal\n- one bundle\n## Action Frame\n- prove the bottleneck\n## First Principles\n- separate fact\n## Anti Patterns\n- no wording only\n## Output Contract\n- bottleneck", encoding="utf-8")

            payload = build_packet(
                brainstorm_path=brainstorm,
                founder_path=founder,
                copy_path=copy_packet,
                ux_path=ux_packet,
                alignment_path=alignment,
                public_contract_path=public_contract,
                case_binding_path=case_binding,
                critical_prompt_path=critical_prompt,
                partner_binding_path=partner_binding,
                review_reason_path=review_reason,
                system_split_path=system_split,
                prompt_doc_path=prompt_doc,
            )

            summary = payload["summary"]
            self.assertTrue(summary["packet_ready"])
            self.assertTrue(summary["downstream_lane_progression_accepted"])
            self.assertTrue(summary["current_execution_lane_matches_packet"])
            self.assertTrue(summary["founder_transition_context_ready"])
            self.assertEqual(summary["current_execution_lane_id"], "runtime_reasoning_card")

    def test_build_packet_stays_ready_when_permit_is_founder_parallel_lane(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            brainstorm = base / "brainstorm.json"
            founder = base / "founder.json"
            copy_packet = base / "copy.json"
            ux_packet = base / "ux.json"
            alignment = base / "alignment.json"
            public_contract = base / "public_contract.json"
            case_binding = base / "case_binding.json"
            critical_prompt = base / "critical_prompt.json"
            partner_binding = base / "partner_binding.json"
            review_reason = base / "review_reason.json"
            system_split = base / "system_split.json"
            prompt_doc = base / "permit_prompt.md"

            brainstorm.write_text(json.dumps({
                "current_execution_lane": {
                    "id": "capital_registration_logic_lock",
                    "title": "capital and registration logic lock",
                    "current_gap": "core-only boundary drift",
                    "evidence": "permit stays parallel while yangdo is founder primary",
                    "proposed_next_step": "keep permit bundle alive as a parallel execution contract",
                    "success_metric": "permit release bundle stays green while yangdo is primary",
                },
                "critical_prompts": {
                    "execution_prompt": "permit execution prompt",
                    "brainstorm_prompt": "permit brainstorm prompt",
                    "first_principles_prompt": "permit first principles prompt",
                    "founder_mode_questions": [
                        "Does this change reduce both user input time and operator decision time?"
                    ],
                },
            }, ensure_ascii=False), encoding="utf-8")
            founder.write_text(json.dumps({
                "summary": {
                    "primary_system": "yangdo",
                    "primary_lane_id": "special_sector_publication_guard",
                    "parallel_system": "permit",
                    "parallel_lane_id": "capital_registration_logic_lock",
                },
                "unified_prompts": {
                    "execution_prompt": "fallback execution prompt",
                    "parallel_brainstorm_prompt": "fallback brainstorm prompt",
                    "first_principles_prompt": "fallback first principles prompt",
                },
                "founder_mode_questions": [
                    "Does this change reduce both user input time and operator decision time?"
                ],
            }, ensure_ascii=False), encoding="utf-8")
            copy_packet.write_text(json.dumps({"summary": {"service_copy_ready": True}}, ensure_ascii=False), encoding="utf-8")
            ux_packet.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            alignment.write_text(json.dumps({"summary": {"alignment_ok": True}}, ensure_ascii=False), encoding="utf-8")
            public_contract.write_text(json.dumps({"summary": {"contract_ok": True}}, ensure_ascii=False), encoding="utf-8")
            case_binding.write_text(json.dumps({
                "summary": {"packet_ready": True},
                "question_bindings": [{"question": "q1"}],
                "operator_jump_table": [{"claim_id": "claim-1", "family_key": "family-1", "jump_targets": [{"preset_id": "preset-1"}]}],
            }, ensure_ascii=False), encoding="utf-8")
            critical_prompt.write_text(json.dumps({"summary": {"packet_ready": True, "operator_surface_ready": True, "release_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            partner_binding.write_text(json.dumps({"summary": {"packet_ready": True, "partner_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            review_reason.write_text(json.dumps({
                "summary": {"decision_ladder_ready": True},
                "ladders": [{"review_reason": "capital_shortfall_only", "inspect_first": "capital", "next_action": "top-up", "manual_review_gate": False}],
            }, ensure_ascii=False), encoding="utf-8")
            system_split.write_text(json.dumps({"tracks": {"permit": {"current_bottleneck": "capital_registration_logic_lock"}}}, ensure_ascii=False), encoding="utf-8")
            prompt_doc.write_text("# Permit Prompt\n## Goal\n- one bundle\n## Action Frame\n- prove the bottleneck\n## First Principles\n- separate fact\n## Anti Patterns\n- no wording only\n## Output Contract\n- bottleneck", encoding="utf-8")

            payload = build_packet(
                brainstorm_path=brainstorm,
                founder_path=founder,
                copy_path=copy_packet,
                ux_path=ux_packet,
                alignment_path=alignment,
                public_contract_path=public_contract,
                case_binding_path=case_binding,
                critical_prompt_path=critical_prompt,
                partner_binding_path=partner_binding,
                review_reason_path=review_reason,
                system_split_path=system_split,
                prompt_doc_path=prompt_doc,
            )

            summary = payload["summary"]
            self.assertTrue(summary["packet_ready"])
            self.assertEqual(summary["lane_id"], "capital_registration_logic_lock")
            self.assertFalse(summary["founder_lane_match"])
            self.assertTrue(summary["founder_parallel_match"])
            self.assertTrue(summary["founder_lane_context_ok"])
            self.assertTrue(summary["current_execution_lane_matches_packet"])
            self.assertTrue(summary["founder_transition_context_ready"])

    def test_build_packet_stays_ready_when_non_permit_founder_parallel_lane_is_stale(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            brainstorm = base / "brainstorm.json"
            founder = base / "founder.json"
            copy_packet = base / "copy.json"
            ux_packet = base / "ux.json"
            alignment = base / "alignment.json"
            public_contract = base / "public_contract.json"
            case_binding = base / "case_binding.json"
            critical_prompt = base / "critical_prompt.json"
            partner_binding = base / "partner_binding.json"
            review_reason = base / "review_reason.json"
            system_split = base / "system_split.json"
            prompt_doc = base / "permit_prompt.md"

            brainstorm.write_text(json.dumps({
                "current_execution_lane": {
                    "id": "critical_prompt_surface_lock",
                    "title": "critical prompt surface lock",
                    "current_gap": "operators need a reusable block",
                    "evidence": "runtime reasoning guard is already green",
                    "proposed_next_step": "lock the prompt block into operator and release surfaces",
                    "success_metric": "prompt block is embedded in live surfaces",
                },
                "critical_prompts": {
                    "execution_prompt": "permit execution prompt",
                    "brainstorm_prompt": "permit brainstorm prompt",
                    "first_principles_prompt": "permit first principles prompt",
                    "founder_mode_questions": [
                        "Does this change reduce both user input time and operator decision time?"
                    ],
                },
            }, ensure_ascii=False), encoding="utf-8")
            founder.write_text(json.dumps({
                "summary": {
                    "primary_system": "yangdo",
                    "primary_lane_id": "special_sector_publication_guard",
                    "parallel_system": "permit",
                    "parallel_lane_id": "thinking_prompt_successor_alignment",
                },
                "unified_prompts": {
                    "execution_prompt": "fallback execution prompt",
                    "parallel_brainstorm_prompt": "fallback brainstorm prompt",
                    "first_principles_prompt": "fallback first principles prompt",
                },
                "founder_mode_questions": [
                    "Does this change reduce both user input time and operator decision time?"
                ],
            }, ensure_ascii=False), encoding="utf-8")
            copy_packet.write_text(json.dumps({"summary": {"service_copy_ready": True}}, ensure_ascii=False), encoding="utf-8")
            ux_packet.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            alignment.write_text(json.dumps({"summary": {"alignment_ok": True}}, ensure_ascii=False), encoding="utf-8")
            public_contract.write_text(json.dumps({"summary": {"contract_ok": True}}, ensure_ascii=False), encoding="utf-8")
            case_binding.write_text(json.dumps({
                "summary": {"packet_ready": True},
                "question_bindings": [{"question": "q1"}],
                "operator_jump_table": [{"claim_id": "claim-1", "family_key": "family-1", "jump_targets": [{"preset_id": "preset-1"}]}],
            }, ensure_ascii=False), encoding="utf-8")
            critical_prompt.write_text(json.dumps({"summary": {"packet_ready": True, "operator_surface_ready": True, "release_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            partner_binding.write_text(json.dumps({"summary": {"packet_ready": True, "partner_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            review_reason.write_text(json.dumps({
                "summary": {"decision_ladder_ready": True},
                "ladders": [{"review_reason": "capital_shortfall_only", "inspect_first": "capital", "next_action": "top-up", "manual_review_gate": False}],
            }, ensure_ascii=False), encoding="utf-8")
            system_split.write_text(json.dumps({"tracks": {"permit": {"current_bottleneck": "thinking_prompt_successor_alignment"}}}, ensure_ascii=False), encoding="utf-8")
            prompt_doc.write_text("# Permit Prompt\n## Goal\n- one bundle\n## Action Frame\n- prove the bottleneck\n## First Principles\n- separate fact\n## Anti Patterns\n- no wording only\n## Output Contract\n- bottleneck", encoding="utf-8")

            payload = build_packet(
                brainstorm_path=brainstorm,
                founder_path=founder,
                copy_path=copy_packet,
                ux_path=ux_packet,
                alignment_path=alignment,
                public_contract_path=public_contract,
                case_binding_path=case_binding,
                critical_prompt_path=critical_prompt,
                partner_binding_path=partner_binding,
                review_reason_path=review_reason,
                system_split_path=system_split,
                prompt_doc_path=prompt_doc,
            )

            summary = payload["summary"]
            self.assertTrue(summary["packet_ready"])
            self.assertEqual(summary["lane_id"], "critical_prompt_surface_lock")
            self.assertFalse(summary["founder_parallel_match"])
            self.assertTrue(summary["founder_lane_context_ok"])
            self.assertTrue(summary["current_execution_lane_matches_packet"])
            self.assertTrue(summary["founder_transition_context_ready"])

    def test_build_packet_accepts_successor_bottleneck_lineage(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            brainstorm = base / "brainstorm.json"
            founder = base / "founder.json"
            copy_packet = base / "copy.json"
            ux_packet = base / "ux.json"
            alignment = base / "alignment.json"
            public_contract = base / "public_contract.json"
            case_binding = base / "case_binding.json"
            critical_prompt = base / "critical_prompt.json"
            partner_binding = base / "partner_binding.json"
            review_reason = base / "review_reason.json"
            system_split = base / "system_split.json"
            prompt_doc = base / "permit_prompt.md"

            brainstorm.write_text(json.dumps({
                "current_execution_lane": {
                    "id": "partner_binding_observability",
                    "title": "partner binding observability",
                    "current_gap": "binding drift must be visible",
                    "evidence": "prompt bundle is already canonical",
                    "proposed_next_step": "surface family-level binding readiness",
                    "success_metric": "binding coverage is visible without raw JSON",
                },
                "critical_prompts": {
                    "execution_prompt": "permit execution prompt",
                    "brainstorm_prompt": "permit brainstorm prompt",
                    "first_principles_prompt": "permit first principles prompt",
                    "founder_mode_questions": [
                        "Does this change reduce both user input time and operator decision time?"
                    ],
                },
            }, ensure_ascii=False), encoding="utf-8")
            founder.write_text(json.dumps({
                "summary": {
                    "primary_system": "permit",
                    "primary_lane_id": "thinking_prompt_bundle_lock",
                },
                "primary_execution": {
                    "id": "thinking_prompt_bundle_lock",
                    "title": "thinking prompt bundle lock",
                    "current_gap": "reasoning framework is fragmented",
                    "evidence": "bundle not yet canonicalized",
                    "proposed_next_step": "unify permit thinking contract",
                    "success_metric": "one canonical prompt bundle drives runtime, release, and operator prioritization",
                },
            }, ensure_ascii=False), encoding="utf-8")
            copy_packet.write_text(json.dumps({"summary": {"service_copy_ready": True}}, ensure_ascii=False), encoding="utf-8")
            ux_packet.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            alignment.write_text(json.dumps({"summary": {"alignment_ok": True}}, ensure_ascii=False), encoding="utf-8")
            public_contract.write_text(json.dumps({"summary": {"contract_ok": True}}, ensure_ascii=False), encoding="utf-8")
            case_binding.write_text(json.dumps({
                "summary": {"packet_ready": True},
                "question_bindings": [{"question": "q1"}],
                "operator_jump_table": [{"claim_id": "claim-1", "family_key": "family-1", "jump_targets": [{"preset_id": "preset-1"}]}],
            }, ensure_ascii=False), encoding="utf-8")
            critical_prompt.write_text(json.dumps({"summary": {"packet_ready": True, "operator_surface_ready": True, "release_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            partner_binding.write_text(json.dumps({"summary": {"packet_ready": True, "partner_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            review_reason.write_text(json.dumps({
                "summary": {"decision_ladder_ready": True},
                "ladders": [{"review_reason": "capital_shortfall_only", "inspect_first": "capital", "next_action": "top-up", "manual_review_gate": False}],
            }, ensure_ascii=False), encoding="utf-8")
            system_split.write_text(json.dumps({"tracks": {"permit": {"current_bottleneck": "runtime_reasoning_card"}}}, ensure_ascii=False), encoding="utf-8")
            prompt_doc.write_text("# Permit Prompt\n## Goal\n- one bundle\n## Action Frame\n- prove the bottleneck\n## First Principles\n- separate fact\n## Anti Patterns\n- no wording only\n## Output Contract\n- bottleneck", encoding="utf-8")

            payload = build_packet(
                brainstorm_path=brainstorm,
                founder_path=founder,
                copy_path=copy_packet,
                ux_path=ux_packet,
                alignment_path=alignment,
                public_contract_path=public_contract,
                case_binding_path=case_binding,
                critical_prompt_path=critical_prompt,
                partner_binding_path=partner_binding,
                review_reason_path=review_reason,
                system_split_path=system_split,
                prompt_doc_path=prompt_doc,
            )

            summary = payload["summary"]
            self.assertTrue(summary["packet_ready"])
            self.assertEqual(summary["system_current_bottleneck"], "runtime_reasoning_card")
            self.assertIn("partner_binding_observability", summary["allowed_successor_lane_ids"])
            self.assertTrue(summary["downstream_lane_progression_accepted"])
            self.assertTrue(summary["founder_transition_context_ready"])

    def test_build_packet_accepts_post_guard_successor_lane(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            brainstorm = base / "brainstorm.json"
            founder = base / "founder.json"
            copy_packet = base / "copy.json"
            ux_packet = base / "ux.json"
            alignment = base / "alignment.json"
            public_contract = base / "public_contract.json"
            case_binding = base / "case_binding.json"
            critical_prompt = base / "critical_prompt.json"
            partner_binding = base / "partner_binding.json"
            review_reason = base / "review_reason.json"
            system_split = base / "system_split.json"
            prompt_doc = base / "permit_prompt.md"

            brainstorm.write_text(json.dumps({
                "current_execution_lane": {
                    "id": "thinking_prompt_successor_alignment",
                    "title": "thinking prompt successor alignment",
                    "current_gap": "closed lane still appears in downstream packets",
                    "evidence": "runtime reasoning guard is already green",
                    "proposed_next_step": "align prompt-bundle and founder successor rules",
                    "success_metric": "closed lane stops reappearing as active",
                },
                "critical_prompts": {
                    "execution_prompt": "permit execution prompt",
                    "brainstorm_prompt": "permit brainstorm prompt",
                    "first_principles_prompt": "permit first principles prompt",
                    "founder_mode_questions": [
                        "Does this change reduce both user input time and operator decision time?"
                    ],
                },
            }, ensure_ascii=False), encoding="utf-8")
            founder.write_text(json.dumps({
                "summary": {
                    "primary_system": "permit",
                    "primary_lane_id": "runtime_reasoning_guard",
                },
                "primary_execution": {
                    "id": "runtime_reasoning_guard",
                    "title": "runtime reasoning guard",
                    "current_gap": "reasoning contract not yet guarded",
                    "evidence": "reasoning card is live",
                    "proposed_next_step": "lock reasoning card into release and parity surfaces",
                    "success_metric": "reasoning regressions are caught before release",
                },
            }, ensure_ascii=False), encoding="utf-8")
            copy_packet.write_text(json.dumps({"summary": {"service_copy_ready": True}}, ensure_ascii=False), encoding="utf-8")
            ux_packet.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            alignment.write_text(json.dumps({"summary": {"alignment_ok": True}}, ensure_ascii=False), encoding="utf-8")
            public_contract.write_text(json.dumps({"summary": {"contract_ok": True}}, ensure_ascii=False), encoding="utf-8")
            case_binding.write_text(json.dumps({
                "summary": {"packet_ready": True},
                "question_bindings": [{"question": "q1"}],
                "operator_jump_table": [{"claim_id": "claim-1", "family_key": "family-1", "jump_targets": [{"preset_id": "preset-1"}]}],
            }, ensure_ascii=False), encoding="utf-8")
            critical_prompt.write_text(json.dumps({"summary": {"packet_ready": True, "operator_surface_ready": True, "release_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            partner_binding.write_text(json.dumps({"summary": {"packet_ready": True, "partner_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            review_reason.write_text(json.dumps({
                "summary": {"decision_ladder_ready": True},
                "ladders": [{"review_reason": "capital_shortfall_only", "inspect_first": "capital", "next_action": "top-up", "manual_review_gate": False}],
            }, ensure_ascii=False), encoding="utf-8")
            system_split.write_text(json.dumps({"tracks": {"permit": {"current_bottleneck": "thinking_prompt_successor_alignment"}}}, ensure_ascii=False), encoding="utf-8")
            prompt_doc.write_text("# Permit Prompt\n## Goal\n- one bundle\n## Action Frame\n- prove the bottleneck\n## First Principles\n- separate fact\n## Anti Patterns\n- no wording only\n## Output Contract\n- bottleneck", encoding="utf-8")

            payload = build_packet(
                brainstorm_path=brainstorm,
                founder_path=founder,
                copy_path=copy_packet,
                ux_path=ux_packet,
                alignment_path=alignment,
                public_contract_path=public_contract,
                case_binding_path=case_binding,
                critical_prompt_path=critical_prompt,
                partner_binding_path=partner_binding,
                review_reason_path=review_reason,
                system_split_path=system_split,
                prompt_doc_path=prompt_doc,
            )

            summary = payload["summary"]
            self.assertTrue(summary["packet_ready"])
            self.assertIn("thinking_prompt_successor_alignment", summary["allowed_successor_lane_ids"])
            self.assertTrue(summary["downstream_lane_progression_accepted"])
            self.assertTrue(summary["current_execution_lane_matches_packet"])
            self.assertEqual(summary["current_execution_lane_id"], "thinking_prompt_successor_alignment")

    def test_build_packet_accepts_capital_registration_successor_lane(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            brainstorm = base / "brainstorm.json"
            founder = base / "founder.json"
            copy_packet = base / "copy.json"
            ux_packet = base / "ux.json"
            alignment = base / "alignment.json"
            public_contract = base / "public_contract.json"
            case_binding = base / "case_binding.json"
            critical_prompt = base / "critical_prompt.json"
            partner_binding = base / "partner_binding.json"
            review_reason = base / "review_reason.json"
            system_split = base / "system_split.json"
            prompt_doc = base / "permit_prompt.md"

            brainstorm.write_text(json.dumps({
                "current_execution_lane": {
                    "id": "capital_registration_logic_lock",
                    "title": "capital and registration logic lock",
                    "current_gap": "capital and technician evidence lines are still missing",
                    "evidence": "prompt/demo surfaces are already green",
                    "proposed_next_step": "bind logic evidence into the canonical audit packet",
                    "success_metric": "evidence-missing totals move down without breaking release",
                },
                "critical_prompts": {
                    "execution_prompt": "permit execution prompt",
                    "brainstorm_prompt": "permit brainstorm prompt",
                    "first_principles_prompt": "permit first principles prompt",
                    "founder_mode_questions": [
                        "Does this change reduce both user input time and operator decision time?"
                    ],
                },
            }, ensure_ascii=False), encoding="utf-8")
            founder.write_text(json.dumps({
                "summary": {
                    "primary_system": "permit",
                    "primary_lane_id": "critical_prompt_surface_lock",
                },
                "primary_execution": {
                    "id": "critical_prompt_surface_lock",
                    "title": "critical prompt surface lock",
                    "current_gap": "surface lens is not canonicalized",
                    "evidence": "critical thinking contract exists",
                    "proposed_next_step": "lock the prompt bundle",
                    "success_metric": "one canonical prompt bundle drives the next lane",
                },
            }, ensure_ascii=False), encoding="utf-8")
            copy_packet.write_text(json.dumps({"summary": {"service_copy_ready": True}}, ensure_ascii=False), encoding="utf-8")
            ux_packet.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            alignment.write_text(json.dumps({"summary": {"alignment_ok": True}}, ensure_ascii=False), encoding="utf-8")
            public_contract.write_text(json.dumps({"summary": {"contract_ok": True}}, ensure_ascii=False), encoding="utf-8")
            case_binding.write_text(json.dumps({
                "summary": {"packet_ready": True},
                "question_bindings": [{"question": "q1"}],
                "operator_jump_table": [{"claim_id": "claim-1", "family_key": "family-1", "jump_targets": [{"preset_id": "preset-1"}]}],
            }, ensure_ascii=False), encoding="utf-8")
            critical_prompt.write_text(json.dumps({"summary": {"packet_ready": True, "operator_surface_ready": True, "release_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            partner_binding.write_text(json.dumps({"summary": {"packet_ready": True, "partner_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            review_reason.write_text(json.dumps({
                "summary": {"decision_ladder_ready": True},
                "ladders": [{"review_reason": "capital_and_technician_shortfall", "inspect_first": "capital and technicians", "next_action": "backfill both", "manual_review_gate": False}],
            }, ensure_ascii=False), encoding="utf-8")
            system_split.write_text(json.dumps({"tracks": {"permit": {"current_bottleneck": "capital_registration_logic_lock"}}}, ensure_ascii=False), encoding="utf-8")
            prompt_doc.write_text("# Permit Prompt\n## Goal\n- one bundle\n## Action Frame\n- prove the bottleneck\n## First Principles\n- separate fact\n## Anti Patterns\n- no wording only\n## Output Contract\n- bottleneck", encoding="utf-8")

            payload = build_packet(
                brainstorm_path=brainstorm,
                founder_path=founder,
                copy_path=copy_packet,
                ux_path=ux_packet,
                alignment_path=alignment,
                public_contract_path=public_contract,
                case_binding_path=case_binding,
                critical_prompt_path=critical_prompt,
                partner_binding_path=partner_binding,
                review_reason_path=review_reason,
                system_split_path=system_split,
                prompt_doc_path=prompt_doc,
            )

            summary = payload["summary"]
            self.assertTrue(summary["packet_ready"])
            self.assertIn("capital_registration_logic_lock", summary["allowed_successor_lane_ids"])
            self.assertTrue(summary["downstream_lane_progression_accepted"])
            self.assertTrue(summary["current_execution_lane_matches_packet"])
            self.assertEqual(summary["current_execution_lane_id"], "capital_registration_logic_lock")


if __name__ == "__main__":
    unittest.main()
