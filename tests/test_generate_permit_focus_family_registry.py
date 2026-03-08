import unittest

from scripts import generate_permit_focus_family_registry


class GeneratePermitFocusFamilyRegistryTests(unittest.TestCase):
    def test_build_registry_merges_packet_rows_into_curated_registry(self):
        packet = {
            "summary": {
                "remaining_pending_after_apply_total": 1,
            },
            "target_family": {
                "family_key": "건설산업기본법 시행령",
                "law_title": "건설산업기본법 시행령",
                "major_name": "건설",
                "group_name": "건설업 등록기준",
                "row_total": 2,
            },
            "execution_packet": {
                "registry_rows": [
                    {
                        "service_code": "FOCUS::construction-general-geonchuk",
                        "service_name": "건축공사업(종합)",
                        "major_code": "31",
                        "major_name": "건설",
                        "law_title": "건설산업기본법 시행령",
                        "catalog_source_kind": "focus_family_registry",
                        "source_upgrade_family": "건설산업기본법 시행령",
                    },
                    {
                        "service_code": "FOCUS::construction-general-tomok",
                        "service_name": "토목공사업(종합)",
                        "major_code": "31",
                        "major_name": "건설",
                        "law_title": "건설산업기본법 시행령",
                        "catalog_source_kind": "focus_family_registry",
                        "source_upgrade_family": "건설산업기본법 시행령",
                    },
                ]
            },
        }
        existing_registry = {
            "industries": [
                {
                    "service_code": "FOCUS::electrical-construction",
                    "service_name": "전기공사업",
                    "major_code": "32",
                    "major_name": "전기·정보통신",
                    "law_title": "전기공사업법 시행령",
                    "catalog_source_kind": "focus_family_registry",
                    "source_upgrade_family": "전기공사업법 시행령",
                }
            ]
        }
        focus_seed_catalog = {
            "industries": [
                {
                    "service_code": "FOCUS::construction-general-geonchuk",
                    "service_name": "건축공사업(종합)",
                    "major_code": "31",
                    "major_name": "건설",
                    "law_title": "건설산업기본법 시행령",
                    "group_name": "건설업 등록기준",
                },
                {
                    "service_code": "FOCUS::construction-general-tomok",
                    "service_name": "토목공사업(종합)",
                    "major_code": "31",
                    "major_name": "건설",
                    "law_title": "건설산업기본법 시행령",
                    "group_name": "건설업 등록기준",
                },
                {
                    "service_code": "FOCUS::security-machine",
                    "service_name": "기계경비업",
                    "major_code": "34",
                    "major_name": "경비",
                    "law_title": "경비업법 시행령",
                    "group_name": "경비업 허가기준",
                },
            ]
        }

        registry = generate_permit_focus_family_registry.build_registry(
            packet=packet,
            existing_registry=existing_registry,
            focus_seed_catalog=focus_seed_catalog,
        )

        self.assertEqual(registry["summary"]["family_registry_row_total"], 3)
        self.assertEqual(registry["summary"]["newly_materialized_row_total"], 2)
        self.assertEqual(registry["summary"]["family_registry_group_total"], 2)
        self.assertEqual(registry["summary"]["applied_family_total"], 1)
        self.assertEqual(registry["summary"]["target_family_row_total"], 2)
        self.assertEqual(registry["summary"]["rows_with_raw_source_proof_total"], 3)
        self.assertEqual(registry["summary"]["focus_family_registry_with_raw_source_proof_total"], 3)
        self.assertEqual(registry["summary"]["focus_family_registry_missing_raw_source_proof_total"], 0)
        self.assertEqual(registry["summary"]["pending_focus_seed_row_total_after_apply"], 1)
        self.assertEqual(registry["last_target_family"]["family_key"], "건설산업기본법 시행령")
        self.assertEqual(registry["industries"][0]["catalog_source_kind"], "focus_family_registry")
        self.assertEqual(
            registry["industries"][0]["raw_source_proof"]["proof_status"],
            "raw_source_hardened",
        )
        self.assertTrue(registry["industries"][0]["raw_source_proof"]["source_checksum"])
        self.assertIn("건설산업기본법 시행령", registry["materialized_families"])
        self.assertEqual(registry["last_applied_families"], ["건설산업기본법 시행령"])

        markdown = generate_permit_focus_family_registry.render_markdown(registry)
        self.assertIn("Permit Focus Family Registry", markdown)
        self.assertIn("family_registry_row_total", markdown)
        self.assertIn("rows_with_raw_source_proof_total", markdown)
        self.assertIn("건설산업기본법 시행령", markdown)

    def test_build_registry_can_materialize_all_pending_families(self):
        packet = {
            "target_family": {
                "family_key": "건설산업기본법 시행령",
            }
        }
        existing_registry = {"industries": []}
        focus_seed_catalog = {
            "industries": [
                {
                    "service_code": "FOCUS::construction-general-geonchuk",
                    "service_name": "건축공사업(종합)",
                    "major_code": "31",
                    "major_name": "건설",
                    "law_title": "건설산업기본법 시행령",
                    "group_name": "건설업 등록기준",
                },
                {
                    "service_code": "FOCUS::security-machine",
                    "service_name": "기계경비업",
                    "major_code": "34",
                    "major_name": "경비",
                    "law_title": "경비업법 시행령",
                    "group_name": "경비업 허가기준",
                },
            ]
        }

        registry = generate_permit_focus_family_registry.build_registry(
            packet=packet,
            existing_registry=existing_registry,
            focus_seed_catalog=focus_seed_catalog,
            materialize_all_pending=True,
        )

        self.assertEqual(registry["summary"]["family_registry_row_total"], 2)
        self.assertEqual(registry["summary"]["applied_family_total"], 2)
        self.assertEqual(registry["summary"]["pending_focus_seed_row_total_after_apply"], 0)
        self.assertEqual(
            registry["last_applied_families"],
            ["건설산업기본법 시행령", "경비업법 시행령"],
        )


    def test_build_registry_backfills_structured_evidence_when_profile_lines_are_missing(self):
        packet = {"target_family": {"family_key": "전기공사업법 시행령"}}
        existing_registry = {"industries": []}
        focus_seed_catalog = {
            "industries": [
                {
                    "service_code": "FOCUS::electrical-construction",
                    "service_name": "전기공사업",
                    "major_code": "32",
                    "major_name": "전기전자정보통신",
                    "law_title": "전기공사업법 시행령",
                    "legal_basis_title": "별표 1 전기공사업 등록기준",
                    "group_name": "전기공사업 등록기준",
                    "registration_requirement_profile": {
                        "capital_required": True,
                        "capital_eok": 1.5,
                        "technical_personnel_required": True,
                        "technicians_required": 3,
                        "other_required": True,
                        "other_components": ["equipment", "deposit", "office"],
                        "equipment_count_required": 1,
                        "deposit_days_required": 30,
                        "capital_evidence": [],
                        "technical_personnel_evidence": [],
                        "other_evidence": [],
                    },
                }
            ]
        }

        registry = generate_permit_focus_family_registry.build_registry(
            packet=packet,
            existing_registry=existing_registry,
            focus_seed_catalog=focus_seed_catalog,
            materialize_all_pending=True,
        )

        profile = registry["industries"][0]["registration_requirement_profile"]
        self.assertEqual(
            profile["capital_evidence"],
            ["별표 1 전기공사업 등록기준 기준 전기공사업의 자본금은 1억 5000만원 이상이어야 한다."],
        )
        self.assertEqual(
            profile["technical_personnel_evidence"],
            ["별표 1 전기공사업 등록기준 기준 전기공사업의 기술인력은 3명 이상이어야 한다."],
        )
        self.assertEqual(
            profile["other_evidence"],
            ["별표 1 전기공사업 등록기준 기준 전기공사업의 기타 등록기준에는 장비 1종 이상, 보증가능금액 확인서 30일 이상, 사무실 확보 기준이 포함된다."],
        )
        self.assertEqual(
            profile["generated_evidence_fields"],
            ["capital_evidence", "technical_personnel_evidence", "other_evidence"],
        )
        self.assertEqual(profile["generated_evidence_kind"], "law_referenced_structured_template")


if __name__ == "__main__":
    unittest.main()
