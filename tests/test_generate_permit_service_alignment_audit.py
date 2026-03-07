import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_permit_service_alignment_audit import build_permit_service_alignment_audit


class GeneratePermitServiceAlignmentAuditTests(unittest.TestCase):
    def test_build_alignment_audit_passes_when_copy_rental_operations_and_attorney_match(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            copy = base / "copy.json"
            rental = base / "rental.json"
            operations = base / "operations.json"
            attorney = base / "attorney.json"

            copy.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "service_copy_ready": True,
                            "checklist_story_ready": True,
                            "manual_review_story_ready": True,
                            "document_story_ready": True,
                        },
                        "cta_ladder": {
                            "primary_self_check": {"label": "사전검토 시작"},
                            "secondary_consult": {"label": "인허가 상담 연결"},
                            "supporting_knowledge": {"label": "등록기준 안내 보기"},
                        },
                        "proof_points": {
                            "permit_selector_entry_total": 51,
                            "permit_platform_industry_total": 51,
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            rental.write_text(
                json.dumps(
                    {
                        "summary": {
                            "permit_selector_entry_total": 51,
                            "permit_platform_industry_total": 51,
                        },
                        "packaging": {
                            "partner_rental": {
                                "widget_standard": ["permit_standard", "combo_standard"],
                                "api_or_detail_pro": ["permit_pro", "combo_pro"],
                            }
                        },
                        "offerings": [
                            {"offering_id": "permit_standard", "systems": ["permit"]},
                            {"offering_id": "permit_pro", "systems": ["permit"]},
                            {"offering_id": "combo_pro", "systems": ["yangdo", "permit"]},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            operations.write_text(
                json.dumps(
                    {
                        "decisions": {"permit_service_copy_ready": True},
                        "summaries": {
                            "permit_service_copy": {
                                "packet_ready": True,
                                "service_copy_ready": True,
                                "checklist_story_ready": True,
                                "manual_review_story_ready": True,
                                "document_story_ready": True,
                                "primary_self_check_cta": "사전검토 시작",
                                "secondary_consult_cta": "인허가 상담 연결",
                                "knowledge_cta": "등록기준 안내 보기",
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            attorney.write_text(
                json.dumps(
                    {
                        "tracks": [
                            {
                                "track_id": "B",
                                "attorney_position": {
                                    "claim_focus": [
                                        "typed criteria와 coverage/manual-review gate 결합",
                                        "기준항목별 증빙 체크리스트 생성",
                                    ],
                                    "commercial_positioning": [
                                        "인허가/신규등록 사전검토 API 공급",
                                        "업종별 추가 기준은 manual-review gate로 책임성 유지",
                                    ],
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_permit_service_alignment_audit(
                copy_path=copy,
                rental_path=rental,
                operations_path=operations,
                attorney_path=attorney,
            )

            self.assertTrue(payload["summary"]["alignment_ok"])
            self.assertEqual(payload["summary"]["issue_count"], 0)
            self.assertTrue(payload["summary"]["cta_contract_ok"])
            self.assertTrue(payload["summary"]["proof_point_contract_ok"])
            self.assertTrue(payload["summary"]["service_story_ok"])
            self.assertTrue(payload["summary"]["rental_positioning_ok"])
            self.assertTrue(payload["summary"]["patent_handoff_ok"])
            self.assertEqual(payload["issues"], [])


if __name__ == "__main__":
    unittest.main()
