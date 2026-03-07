import unittest

from scripts import generate_permit_next_action_brainstorm


class GeneratePermitNextActionBrainstormTests(unittest.TestCase):
    def test_build_brainstorm_prioritizes_focus_seed_execution_and_parallel_candidate_pack_lane(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 53,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 0,
            },
            "industries": [
                {
                    "service_code": "FOCUS::construction-general-geonchuk",
                    "canonical_service_code": "FOCUS::construction-general-geonchuk",
                    "service_name": "건축공사업(종합)",
                    "major_name": "건설",
                    "group_name": "건설업 등록기준",
                    "law_title": "건설산업기본법 시행령",
                    "legal_basis_title": "별표 2",
                },
                {
                    "service_code": "FOCUS::construction-general-tomok",
                    "canonical_service_code": "FOCUS::construction-general-tomok",
                    "service_name": "토목공사업(종합)",
                    "major_name": "건설",
                    "group_name": "건설업 등록기준",
                    "law_title": "건설산업기본법 시행령",
                    "legal_basis_title": "별표 2",
                },
            ],
        }
        provenance_audit = {
            "summary": {
                "focus_family_registry_row_total": 0,
                "focus_seed_row_total": 50,
                "candidate_pack_total": 3,
                "master_inferred_overlay_total": 0,
            }
        }
        focus_report = {
            "summary": {
                "real_focus_target_total": 51,
            }
        }
        source_upgrade_backlog = {
            "summary": {
                "focus_seed_group_total": 6,
                "absorbed_group_total": 0,
            },
            "upgrade_tracks": {
                "focus_seed_source_groups": [
                    {"group_key": "건설산업기본법 시행령"},
                ],
                "candidate_pack_stabilization_groups": [
                    {"group_key": "목재의 지속가능한 이용에 관한 법률 시행령"},
                ],
            },
        }

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
        )

        self.assertEqual(report["summary"]["master_industry_total"], 53)
        self.assertEqual(report["summary"]["focus_family_registry_row_total"], 0)
        self.assertEqual(report["summary"]["focus_seed_row_total"], 50)
        self.assertEqual(report["summary"]["master_absorbed_row_total"], 0)
        self.assertEqual(report["summary"]["candidate_pack_total"], 3)
        self.assertEqual(report["summary"]["inferred_reverification_total"], 0)
        self.assertEqual(report["summary"]["real_focus_target_total"], 51)
        self.assertEqual(report["summary"]["real_high_confidence_focus_total"], 51)
        self.assertEqual(report["summary"]["focus_seed_group_total"], 6)
        self.assertEqual(report["current_execution_lane"]["id"], "focus_seed_source_upgrade")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "patent_evidence_bundle")
        self.assertEqual(report["brainstorm_items"][0]["parallelizable_with"][0], "candidate_pack_rule_upgrade")

        markdown = generate_permit_next_action_brainstorm.render_markdown(report)
        self.assertIn("Permit Next Action Brainstorm", markdown)
        self.assertIn("Active Execution Lane", markdown)
        self.assertIn("`focus_seed_source_upgrade`", markdown)
        self.assertIn("`patent_evidence_bundle`", markdown)
        self.assertIn("focus_seed_row_total", markdown)
        self.assertIn("focus_family_registry_row_total", markdown)
        self.assertIn("real_focus_target_total", markdown)

    def test_build_brainstorm_moves_to_family_registry_hardening_when_focus_seed_is_zero(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 0,
            },
            "industries": [],
        }
        provenance_audit = {
            "summary": {
                "focus_family_registry_row_total": 50,
                "focus_seed_row_total": 0,
                "focus_family_registry_missing_raw_source_proof_total": 50,
                "candidate_pack_total": 0,
                "master_inferred_overlay_total": 0,
            }
        }
        focus_report = {
            "summary": {
                "real_focus_target_total": 51,
            }
        }
        source_upgrade_backlog = {
            "summary": {
                "focus_seed_group_total": 0,
                "absorbed_group_total": 0,
            },
            "upgrade_tracks": {
                "focus_seed_source_groups": [],
                "candidate_pack_stabilization_groups": [],
            },
        }

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
        )

        self.assertEqual(report["summary"]["focus_family_registry_row_total"], 50)
        self.assertEqual(report["summary"]["focus_seed_row_total"], 0)
        self.assertEqual(report["current_execution_lane"]["id"], "focus_family_registry_hardening")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "patent_evidence_bundle")

    def test_build_brainstorm_moves_to_patent_bundle_lock_when_family_registry_proof_is_complete(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 0,
            },
            "industries": [],
        }
        provenance_audit = {
            "summary": {
                "focus_family_registry_row_total": 50,
                "focus_seed_row_total": 0,
                "focus_family_registry_missing_raw_source_proof_total": 0,
                "candidate_pack_total": 0,
                "master_inferred_overlay_total": 0,
            }
        }
        focus_report = {
            "summary": {
                "real_focus_target_total": 51,
            }
        }
        source_upgrade_backlog = {
            "summary": {
                "focus_seed_group_total": 0,
                "absorbed_group_total": 0,
            },
            "upgrade_tracks": {
                "focus_seed_source_groups": [],
                "candidate_pack_stabilization_groups": [],
            },
        }

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
        )

        self.assertEqual(report["current_execution_lane"]["id"], "patent_evidence_bundle_lock")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "platform_contract_proof_surface")

    def test_build_brainstorm_moves_to_contract_surface_when_claim_packets_are_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 0,
            },
            "industries": [],
        }
        provenance_audit = {
            "summary": {
                "focus_family_registry_row_total": 50,
                "focus_seed_row_total": 0,
                "focus_family_registry_missing_raw_source_proof_total": 0,
                "candidate_pack_total": 0,
                "master_inferred_overlay_total": 0,
            }
        }
        focus_report = {"summary": {"real_focus_target_total": 51}}
        source_upgrade_backlog = {"summary": {"focus_seed_group_total": 0, "absorbed_group_total": 0}}
        patent_bundle = {
            "summary": {
                "focus_source_family_total": 6,
                "claim_packet_family_total": 6,
                "claim_packet_complete_family_total": 6,
                "checksum_sample_family_total": 6,
            }
        }
        widget_catalog = {
            "summary": {
                "permit_claim_packet_family_total": 4,
                "permit_checksum_sample_family_total": 4,
            }
        }

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            widget_rental_catalog=widget_catalog,
        )

        self.assertEqual(report["current_execution_lane"]["id"], "platform_contract_proof_surface")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "family_case_goldset")
        self.assertEqual(report["summary"]["claim_packet_complete_family_total"], 6)
        self.assertEqual(report["summary"]["widget_checksum_sample_family_total"], 4)

    def test_build_brainstorm_moves_to_runtime_disclosure_after_contract_surface_is_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 0,
            },
            "industries": [],
        }
        provenance_audit = {
            "summary": {
                "focus_family_registry_row_total": 50,
                "focus_seed_row_total": 0,
                "focus_family_registry_missing_raw_source_proof_total": 0,
                "candidate_pack_total": 0,
                "master_inferred_overlay_total": 0,
            }
        }
        focus_report = {"summary": {"real_focus_target_total": 51}}
        source_upgrade_backlog = {"summary": {"focus_seed_group_total": 0, "absorbed_group_total": 0}}
        patent_bundle = {
            "summary": {
                "focus_source_family_total": 6,
                "claim_packet_family_total": 6,
                "claim_packet_complete_family_total": 6,
                "checksum_sample_family_total": 6,
            }
        }
        widget_catalog = {
            "summary": {
                "permit_claim_packet_family_total": 6,
                "permit_checksum_sample_family_total": 6,
            }
        }

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            widget_rental_catalog=widget_catalog,
        )

        self.assertEqual(report["current_execution_lane"]["id"], "runtime_proof_disclosure")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "family_case_goldset")


if __name__ == "__main__":
    unittest.main()
