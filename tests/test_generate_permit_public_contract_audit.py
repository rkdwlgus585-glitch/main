import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_permit_public_contract_audit import build_permit_public_contract_audit


class GeneratePermitPublicContractAuditTests(unittest.TestCase):
    def test_build_contract_audit_passes_when_public_detail_internal_boundaries_match(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ux = base / "ux.json"
            rental = base / "rental.json"
            operations = base / "operations.json"
            attorney = base / "attorney.json"

            ux.write_text(
                json.dumps(
                    {
                        "summary": {"packet_ready": True, "service_flow_policy": "public_summary_then_checklist_or_manual_review"},
                        "public_summary_experience": {
                            "visible_fields": ["overall_status", "required_summary", "next_actions"],
                            "allowed_offerings": ["permit_standard"],
                        },
                        "detail_checklist_experience": {
                            "visible_fields": ["criterion_results", "evidence_checklist", "document_templates", "legal_basis"],
                            "allowed_offerings": ["permit_pro"],
                        },
                        "manual_review_assist_experience": {
                            "visible_fields": ["criterion_results", "evidence_checklist", "document_templates", "legal_basis", "manual_review_required", "coverage_status"],
                            "allowed_offerings": ["permit_pro_assist"],
                        },
                        "internal_review_experience": {
                            "visible_fields": ["criterion_results", "evidence_checklist", "document_templates", "legal_basis", "manual_review_required", "coverage_status", "pending_criteria_lines", "mapping_confidence"],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            rental.write_text(
                json.dumps(
                    {
                        "packaging": {
                            "partner_rental": {
                                "permit_precheck": {
                                    "package_matrix": {
                                        "summary_self_check": {"offering_ids": ["permit_standard"]},
                                        "detail_checklist": {"offering_ids": ["permit_pro"]},
                                        "manual_review_assist": {"offering_ids": ["permit_pro_assist"]},
                                    }
                                }
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            operations.write_text(
                json.dumps(
                    {
                        "decisions": {"permit_service_ux_ready": True},
                        "summaries": {"permit_service_ux": {"service_flow_policy": "public_summary_then_checklist_or_manual_review"}},
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
                                        "typed criteria checklist coverage gate",
                                        "manual review escalation and mapping confidence control",
                                    ]
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_permit_public_contract_audit(
                ux_path=ux,
                rental_path=rental,
                operations_path=operations,
                attorney_path=attorney,
            )

            self.assertTrue(payload["summary"]["contract_ok"])
            self.assertTrue(payload["summary"]["public_summary_only_ok"])
            self.assertTrue(payload["summary"]["detail_checklist_contract_ok"])
            self.assertTrue(payload["summary"]["assist_contract_ok"])
            self.assertTrue(payload["summary"]["internal_visibility_ok"])
            self.assertTrue(payload["summary"]["offering_exposure_ok"])
            self.assertTrue(payload["summary"]["patent_handoff_ok"])


if __name__ == "__main__":
    unittest.main()
