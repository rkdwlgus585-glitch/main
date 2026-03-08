import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_permit_partner_binding_parity_packet import build_packet


class GeneratePermitPartnerBindingParityPacketTests(unittest.TestCase):
    def test_build_packet_creates_partner_safe_family_surface(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            operator_demo = base / "operator_demo.json"
            public_contract = base / "public_contract.json"
            widget_catalog = base / "widget_catalog.json"

            operator_demo.write_text(
                json.dumps(
                    {
                        "summary": {"operator_demo_ready": True},
                        "families": [
                            {
                                "claim_id": "P-001",
                                "claim_title": "electric checklist",
                                "family_key": "electric",
                                "prompt_case_binding": {
                                    "service_code": "ELEC001",
                                    "service_name": "Electrical contractor",
                                    "expected_status": "detail_checklist",
                                    "review_reason": "baseline_match",
                                    "manual_review_expected": False,
                                    "binding_focus": "capital+technician",
                                },
                            },
                            {
                                "claim_id": "P-002",
                                "claim_title": "interior review",
                                "family_key": "interior",
                                "prompt_case_binding": {
                                    "service_code": "INTR001",
                                    "service_name": "Interior contractor",
                                    "expected_status": "manual_review_assist",
                                    "review_reason": "document_interpretation_needed",
                                    "manual_review_expected": True,
                                    "binding_focus": "document+manual_review",
                                },
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            public_contract.write_text(
                json.dumps(
                    {
                        "summary": {
                            "contract_ok": True,
                            "offering_exposure_ok": True,
                            "detail_checklist_contract_ok": True,
                            "assist_contract_ok": True,
                        },
                        "contracts": {
                            "detail_allowed_offerings": ["permit_pro"],
                            "assist_allowed_offerings": ["permit_pro_assist"],
                            "public_fields": ["status"],
                            "detail_fields": ["criterion_results"],
                            "assist_fields": ["manual_review_reason"],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            widget_catalog.write_text(
                json.dumps({"summary": {"permit_offering_count": 3}}, ensure_ascii=False),
                encoding="utf-8",
            )

            payload = build_packet(
                operator_demo_path=operator_demo,
                public_contract_path=public_contract,
                widget_catalog_path=widget_catalog,
            )

            self.assertTrue(payload["summary"]["packet_ready"])
            self.assertEqual(payload["summary"]["family_total"], 2)
            self.assertEqual(payload["summary"]["detail_checklist_family_total"], 1)
            self.assertEqual(payload["summary"]["manual_review_family_total"], 1)
            self.assertTrue(payload["summary"]["partner_surface_ready"])
            self.assertEqual(payload["partner_surface"][0]["cta_label"], "View detailed checklist")
            self.assertEqual(payload["partner_surface"][0]["allowed_offerings"], ["permit_pro"])
            self.assertEqual(payload["partner_surface"][1]["cta_label"], "Request manual review")
            self.assertEqual(payload["partner_surface"][1]["allowed_offerings"], ["permit_pro_assist"])

    def test_build_packet_prefers_prompt_case_binding_as_public_partner_contract(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            operator_demo = base / "operator_demo.json"
            public_contract = base / "public_contract.json"
            widget_catalog = base / "widget_catalog.json"

            operator_demo.write_text(
                json.dumps(
                    {
                        "summary": {"operator_demo_ready": True},
                        "families": [
                            {
                                "claim_id": "P-101",
                                "claim_title": "electrical precheck",
                                "family_key": "electric",
                                "prompt_case_binding": {
                                    "preset_id": "P-101:document_missing_review",
                                    "service_code": "ELEC001",
                                    "service_name": "Electrical contractor",
                                    "expected_status": "shortfall",
                                    "review_reason": "other_requirement_documents_missing",
                                    "manual_review_expected": True,
                                    "binding_focus": "manual_review_gate",
                                },
                                "demo_cases": [
                                    {
                                        "preset_id": "P-101:document_missing_review",
                                        "case_kind": "document_missing_review",
                                        "service_code": "ELEC001",
                                        "service_name": "Electrical contractor",
                                        "expected_status": "shortfall",
                                        "review_reason": "other_requirement_documents_missing",
                                        "manual_review_expected": True,
                                        "binding_focus": "manual_review_gate",
                                    },
                                    {
                                        "preset_id": "P-101:capital_only_fail",
                                        "case_kind": "capital_only_fail",
                                        "service_code": "ELEC001",
                                        "service_name": "Electrical contractor",
                                        "expected_status": "shortfall",
                                        "review_reason": "capital_shortfall_only",
                                        "manual_review_expected": False,
                                        "binding_focus": "capital_gap_first",
                                    },
                                ],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            public_contract.write_text(
                json.dumps(
                    {
                        "summary": {
                            "contract_ok": True,
                            "offering_exposure_ok": True,
                            "detail_checklist_contract_ok": True,
                            "assist_contract_ok": True,
                        },
                        "contracts": {
                            "detail_allowed_offerings": ["permit_pro"],
                            "assist_allowed_offerings": ["permit_pro_assist"],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            widget_catalog.write_text(
                json.dumps({"summary": {"permit_offering_count": 3}}, ensure_ascii=False),
                encoding="utf-8",
            )

            payload = build_packet(
                operator_demo_path=operator_demo,
                public_contract_path=public_contract,
                widget_catalog_path=widget_catalog,
            )

            self.assertTrue(payload["summary"]["packet_ready"])
            self.assertEqual(payload["summary"]["detail_checklist_family_total"], 0)
            self.assertEqual(payload["summary"]["manual_review_family_total"], 1)
            self.assertEqual(payload["partner_surface"][0]["exposure_lane"], "manual_review_assist")
            self.assertEqual(payload["partner_surface"][0]["cta_label"], "Request manual review")
            self.assertEqual(payload["partner_surface"][0]["source_case_kind"], "document_missing_review")
            self.assertEqual(payload["partner_surface"][0]["binding_focus"], "manual_review_gate")

    def test_build_packet_derives_combined_shortfall_focus_when_prompt_binding_is_missing(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            operator_demo = base / "operator_demo.json"
            public_contract = base / "public_contract.json"
            widget_catalog = base / "widget_catalog.json"

            operator_demo.write_text(
                json.dumps(
                    {
                        "summary": {"operator_demo_ready": True},
                        "families": [
                            {
                                "claim_id": "P-201",
                                "claim_title": "network precheck",
                                "family_key": "network",
                                "demo_cases": [
                                    {
                                        "preset_id": "P-201:shortfall_fail",
                                        "case_kind": "shortfall_fail",
                                        "service_code": "NET001",
                                        "service_name": "정보통신공사업",
                                        "expected_status": "shortfall",
                                        "review_reason": "capital_and_technician_shortfall",
                                        "manual_review_expected": False,
                                    },
                                    {
                                        "preset_id": "P-201:capital_only_fail",
                                        "case_kind": "capital_only_fail",
                                        "service_code": "NET001",
                                        "service_name": "정보통신공사업",
                                        "expected_status": "shortfall",
                                        "review_reason": "capital_shortfall_only",
                                        "manual_review_expected": False,
                                    },
                                ],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            public_contract.write_text(
                json.dumps(
                    {
                        "summary": {
                            "contract_ok": True,
                            "offering_exposure_ok": True,
                            "detail_checklist_contract_ok": True,
                            "assist_contract_ok": True,
                        },
                        "contracts": {
                            "detail_allowed_offerings": ["permit_pro"],
                            "assist_allowed_offerings": ["permit_pro_assist"],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            widget_catalog.write_text(
                json.dumps({"summary": {"permit_offering_count": 3}}, ensure_ascii=False),
                encoding="utf-8",
            )

            payload = build_packet(
                operator_demo_path=operator_demo,
                public_contract_path=public_contract,
                widget_catalog_path=widget_catalog,
            )

            self.assertTrue(payload["summary"]["packet_ready"])
            self.assertEqual(payload["partner_surface"][0]["binding_preset_id"], "P-201:shortfall_fail")
            self.assertEqual(payload["partner_surface"][0]["source_case_kind"], "shortfall_fail")
            self.assertEqual(payload["partner_surface"][0]["binding_focus"], "capital_and_technician_gap_first")


if __name__ == "__main__":
    unittest.main()
