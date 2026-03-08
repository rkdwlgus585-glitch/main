import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_permit_runtime_reasoning_binding_audit import build_packet


class GeneratePermitRuntimeReasoningBindingAuditTests(unittest.TestCase):
    def test_build_packet_passes_when_runtime_service_and_operator_surfaces_align(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            copy_path = base / "copy.json"
            ux_path = base / "ux.json"
            critical_path = base / "critical.json"
            thinking_path = base / "thinking.json"
            brainstorm_path = base / "brainstorm.json"

            copy_path.write_text(
                json.dumps(
                    {
                        "summary": {"packet_ready": True},
                        "lane_ladder": {
                            "detail_checklist": {"upgrade_target": "manual_review_assist"},
                        },
                        "next_actions": [
                            "상세 체크리스트 lane과 수동 검토 보조 lane의 CTA와 설명 문구를 계속 분리합니다."
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            ux_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "service_flow_policy": "public_summary_then_checklist_or_manual_review",
                        },
                        "public_summary_experience": {
                            "cta_primary_label": "사전검토 시작",
                        },
                        "detail_checklist_experience": {
                            "cta_primary_label": "상세 체크리스트 보기",
                            "allowed_offerings": ["permit_pro"],
                        },
                        "manual_review_assist_experience": {
                            "cta_primary_label": "수동 검토 요청",
                            "allowed_offerings": ["permit_pro_assist"],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            critical_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "lane_id": "runtime_reasoning_guard",
                            "operator_surface_ready": True,
                            "release_surface_ready": True,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            thinking_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "lane_id": "runtime_reasoning_guard",
                            "runtime_target_ready": True,
                            "release_target_ready": True,
                            "operator_target_ready": True,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            brainstorm_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "execution_lane": "runtime_reasoning_guard",
                        },
                        "current_execution_lane": {
                            "id": "runtime_reasoning_guard",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_packet(
                copy_path=copy_path,
                ux_path=ux_path,
                critical_path=critical_path,
                thinking_path=thinking_path,
                brainstorm_path=brainstorm_path,
            )

            self.assertTrue(payload["summary"]["packet_ready"])
            self.assertEqual(payload["summary"]["lane_id"], "runtime_reasoning_guard")
            self.assertTrue(payload["summary"]["runtime_binding_ok"])
            self.assertTrue(payload["summary"]["service_binding_ok"])
            self.assertTrue(payload["summary"]["operator_binding_ok"])
            self.assertTrue(payload["summary"]["release_binding_ok"])
            self.assertEqual(payload["summary"]["issue_count"], 0)

    def test_build_packet_flags_collapsed_cta_and_offering_splits(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            copy_path = base / "copy.json"
            ux_path = base / "ux.json"
            critical_path = base / "critical.json"
            thinking_path = base / "thinking.json"
            brainstorm_path = base / "brainstorm.json"

            copy_path.write_text(
                json.dumps(
                    {
                        "summary": {"packet_ready": True},
                        "lane_ladder": {
                            "detail_checklist": {"upgrade_target": "manual_review_assist"},
                        },
                        "next_actions": ["운영 표면 정리"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            ux_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "service_flow_policy": "public_summary_then_checklist_or_manual_review",
                        },
                        "public_summary_experience": {"cta_primary_label": "사전검토 시작"},
                        "detail_checklist_experience": {
                            "cta_primary_label": "같은 CTA",
                            "allowed_offerings": ["permit_pro"],
                        },
                        "manual_review_assist_experience": {
                            "cta_primary_label": "같은 CTA",
                            "allowed_offerings": ["permit_pro"],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            critical_path.write_text(json.dumps({"summary": {"packet_ready": True, "lane_id": "runtime_reasoning_guard", "operator_surface_ready": True, "release_surface_ready": True}}, ensure_ascii=False), encoding="utf-8")
            thinking_path.write_text(json.dumps({"summary": {"packet_ready": True, "lane_id": "runtime_reasoning_guard", "runtime_target_ready": True, "release_target_ready": True, "operator_target_ready": True}}, ensure_ascii=False), encoding="utf-8")
            brainstorm_path.write_text(json.dumps({"summary": {"execution_lane": "runtime_reasoning_guard"}, "current_execution_lane": {"id": "runtime_reasoning_guard"}}, ensure_ascii=False), encoding="utf-8")

            payload = build_packet(
                copy_path=copy_path,
                ux_path=ux_path,
                critical_path=critical_path,
                thinking_path=thinking_path,
                brainstorm_path=brainstorm_path,
            )

            self.assertFalse(payload["summary"]["packet_ready"])
            self.assertIn("service_cta_split_missing", payload["issues"])
            self.assertIn("detail_assist_offering_split_missing", payload["issues"])

    def test_build_packet_allows_successor_lane_after_runtime_guard_turns_green(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            copy_path = base / "copy.json"
            ux_path = base / "ux.json"
            critical_path = base / "critical.json"
            thinking_path = base / "thinking.json"
            brainstorm_path = base / "brainstorm.json"

            copy_path.write_text(
                json.dumps(
                    {
                        "summary": {"packet_ready": True},
                        "lane_ladder": {
                            "detail_checklist": {"upgrade_target": "manual_review_assist"},
                        },
                        "next_actions": [
                            "?곸꽭 泥댄겕由ъ뒪??lane怨??섎룞 寃??蹂댁“ lane??CTA? ?ㅻ챸 臾멸뎄瑜?怨꾩냽 遺꾨━?⑸땲??"
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            ux_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "service_flow_policy": "public_summary_then_checklist_or_manual_review",
                        },
                        "public_summary_experience": {"cta_primary_label": "?ъ쟾寃???쒖옉"},
                        "detail_checklist_experience": {
                            "cta_primary_label": "?곸꽭 泥댄겕由ъ뒪??蹂닿린",
                            "allowed_offerings": ["permit_pro"],
                        },
                        "manual_review_assist_experience": {
                            "cta_primary_label": "?섎룞 寃???붿껌",
                            "allowed_offerings": ["permit_pro_assist"],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            critical_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "lane_id": "runtime_reasoning_guard",
                            "founder_primary_lane_id": "runtime_reasoning_guard",
                            "operator_surface_ready": True,
                            "release_surface_ready": True,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            thinking_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "lane_id": "thinking_prompt_successor_alignment",
                            "runtime_target_ready": True,
                            "release_target_ready": True,
                            "operator_target_ready": True,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            brainstorm_path.write_text(
                json.dumps(
                    {
                        "summary": {"execution_lane": "thinking_prompt_successor_alignment"},
                        "current_execution_lane": {"id": "thinking_prompt_successor_alignment"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_packet(
                copy_path=copy_path,
                ux_path=ux_path,
                critical_path=critical_path,
                thinking_path=thinking_path,
                brainstorm_path=brainstorm_path,
            )

            self.assertTrue(payload["summary"]["packet_ready"])
            self.assertTrue(payload["summary"]["runtime_binding_ok"])
            self.assertTrue(payload["summary"]["successor_transition_ok"])
            self.assertEqual(payload["summary"]["issue_count"], 0)

    def test_build_packet_allows_founder_parallel_successor_lane(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            copy_path = base / "copy.json"
            ux_path = base / "ux.json"
            critical_path = base / "critical.json"
            thinking_path = base / "thinking.json"
            brainstorm_path = base / "brainstorm.json"

            copy_path.write_text(
                json.dumps(
                    {
                        "summary": {"packet_ready": True},
                        "lane_ladder": {
                            "detail_checklist": {"upgrade_target": "manual_review_assist"},
                        },
                        "next_actions": [
                            "Keep permit lane and CTA split aligned with manual review assist detail handoff."
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ux_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "service_flow_policy": "public_summary_then_checklist_or_manual_review",
                        },
                        "public_summary_experience": {"cta_primary_label": "Start check"},
                        "detail_checklist_experience": {
                            "cta_primary_label": "Open checklist",
                            "allowed_offerings": ["permit_pro_detail"],
                        },
                        "manual_review_assist_experience": {
                            "cta_primary_label": "Request manual review",
                            "allowed_offerings": ["permit_pro_assist"],
                        },
                    }
                ),
                encoding="utf-8",
            )
            critical_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "lane_id": "critical_prompt_surface_lock",
                            "founder_primary_lane_id": "special_sector_publication_guard",
                            "operator_surface_ready": True,
                            "release_surface_ready": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            thinking_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "lane_id": "critical_prompt_surface_lock",
                            "founder_parallel_lane_id": "critical_prompt_surface_lock",
                            "allowed_successor_lane_ids": ["critical_prompt_surface_lock"],
                            "runtime_target_ready": True,
                            "release_target_ready": True,
                            "operator_target_ready": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            brainstorm_path.write_text(
                json.dumps(
                    {
                        "summary": {"execution_lane": "critical_prompt_surface_lock"},
                        "current_execution_lane": {"id": "critical_prompt_surface_lock"},
                    }
                ),
                encoding="utf-8",
            )

            payload = build_packet(
                copy_path=copy_path,
                ux_path=ux_path,
                critical_path=critical_path,
                thinking_path=thinking_path,
                brainstorm_path=brainstorm_path,
            )

            self.assertTrue(payload["summary"]["packet_ready"])
            self.assertTrue(payload["summary"]["successor_founder_ok"])
            self.assertEqual(
                payload["contracts"]["lane_match"]["founder_parallel_lane_id"],
                "critical_prompt_surface_lock",
            )


if __name__ == "__main__":
    unittest.main()
