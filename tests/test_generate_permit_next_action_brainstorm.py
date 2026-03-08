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
            prompt_doc="# permit prompt",
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
        self.assertTrue(report["summary"]["prompt_doc_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "focus_seed_source_upgrade")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "patent_evidence_bundle")
        self.assertEqual(report["brainstorm_items"][0]["parallelizable_with"][0], "candidate_pack_rule_upgrade")

        markdown = generate_permit_next_action_brainstorm.render_markdown(report)
        self.assertIn("Permit Next Action Brainstorm", markdown)
        self.assertIn("Active Execution Lane", markdown)
        self.assertIn("Critical Prompt", markdown)
        self.assertIn("First-Principles Prompt", markdown)
        self.assertIn("Founder Mode Questions", markdown)
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
        self.assertFalse(report["summary"]["prompt_doc_ready"])
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

    def test_build_brainstorm_moves_to_family_case_goldset_when_runtime_surface_is_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 50,
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
            runtime_html='<div id="proofClaimBox"></div><script>const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; }; const y = "법령군 증빙";</script>',
        )

        self.assertEqual(report["current_execution_lane"]["id"], "family_case_goldset")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "runtime_proof_regression_lock")
        self.assertTrue(report["summary"]["runtime_proof_surface_ready"])

    def test_build_brainstorm_moves_to_runtime_assertions_when_goldset_is_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 50,
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
        goldset_bundle = {
            "summary": {
                "goldset_complete_family_total": 6,
            }
        }

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            permit_family_case_goldset=goldset_bundle,
            widget_rental_catalog=widget_catalog,
            runtime_html='<div id="proofClaimBox"></div><script>const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; }; const y = "법령군 증빙";</script>',
        )

        self.assertEqual(report["current_execution_lane"]["id"], "family_case_runtime_assertions")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "widget_case_parity")
        self.assertEqual(report["summary"]["family_case_goldset_family_total"], 6)

    def test_build_brainstorm_moves_to_widget_case_parity_when_runtime_assertions_are_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 50,
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
        goldset_bundle = {"summary": {"goldset_complete_family_total": 6}}
        runtime_assertions = {
            "summary": {
                "asserted_family_total": 6,
                "failed_case_total": 0,
                "runtime_assertions_ready": True,
            }
        }
        widget_catalog = {
            "summary": {
                "permit_claim_packet_family_total": 6,
                "permit_checksum_sample_family_total": 6,
                "permit_widget_case_parity_family_total": 4,
            }
        }
        api_contract_spec = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "current_summary": {
                                    "family_case_goldset_family_total": 4,
                                }
                            }
                        }
                    }
                }
            }
        }

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            permit_family_case_goldset=goldset_bundle,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract_spec,
            runtime_html='<div id="proofClaimBox"></div><script>const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; }; const y = "법령군 증빙";</script>',
        )

        self.assertEqual(report["current_execution_lane"]["id"], "widget_case_parity")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "case_release_guard")
        self.assertEqual(report["summary"]["runtime_asserted_family_total"], 6)
        self.assertEqual(report["summary"]["widget_case_parity_family_total"], 4)
        self.assertEqual(report["summary"]["api_case_parity_family_total"], 4)

    def test_build_brainstorm_moves_to_case_release_guard_when_runtime_and_contract_parity_are_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 50,
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
        goldset_bundle = {"summary": {"goldset_complete_family_total": 6}}
        runtime_assertions = {
            "summary": {
                "asserted_family_total": 6,
                "failed_case_total": 0,
                "runtime_assertions_ready": True,
            }
        }
        widget_catalog = {
            "summary": {
                "permit_claim_packet_family_total": 6,
                "permit_checksum_sample_family_total": 6,
                "permit_widget_case_parity_family_total": 6,
            }
        }
        api_contract_spec = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "current_summary": {
                                    "family_case_goldset_family_total": 6,
                                }
                            }
                        }
                    }
                }
            }
        }

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            permit_family_case_goldset=goldset_bundle,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract_spec,
            runtime_html='<div id="proofClaimBox"></div><script>const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; }; const y = "법령군 증빙";</script>',
        )

        self.assertEqual(report["current_execution_lane"]["id"], "case_release_guard")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "family_case_edge_expansion")
        self.assertEqual(report["summary"]["widget_case_parity_family_total"], 6)
        self.assertEqual(report["summary"]["api_case_parity_family_total"], 6)

    def test_build_brainstorm_moves_to_edge_expansion_when_case_release_guard_is_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 50,
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
        goldset_bundle = {"summary": {"goldset_complete_family_total": 6}}
        runtime_assertions = {
            "summary": {
                "asserted_family_total": 6,
                "failed_case_total": 0,
                "runtime_assertions_ready": True,
            }
        }
        widget_catalog = {
            "summary": {
                "permit_claim_packet_family_total": 6,
                "permit_checksum_sample_family_total": 6,
                "permit_widget_case_parity_family_total": 6,
            }
        }
        api_contract_spec = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "current_summary": {
                                    "family_case_goldset_family_total": 6,
                                }
                            }
                        }
                    }
                }
            }
        }
        case_release_guard = {
            "summary": {
                "family_total": 6,
                "runtime_failed_case_total": 0,
                "runtime_missing_case_total": 0,
                "widget_missing_case_total": 0,
                "api_missing_case_total": 0,
                "runtime_extra_case_total": 0,
                "widget_extra_case_total": 0,
                "api_extra_case_total": 0,
                "release_guard_ready": True,
            }
        }

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            permit_family_case_goldset=goldset_bundle,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract_spec,
            permit_case_release_guard=case_release_guard,
            runtime_html='<div id="proofClaimBox"></div><script>const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; }; const y = "법령군 증빙";</script>',
        )

        self.assertEqual(report["current_execution_lane"]["id"], "family_case_edge_expansion")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "case_release_observability")
        self.assertTrue(report["summary"]["case_release_guard_ready"])
        self.assertEqual(report["summary"]["case_release_guard_family_total"], 6)

    def test_build_brainstorm_moves_to_review_case_presets_when_edge_cases_and_release_preview_are_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 50,
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
        goldset_bundle = {
            "summary": {
                "goldset_complete_family_total": 6,
                "edge_case_total": 18,
                "edge_case_family_total": 6,
                "manual_review_case_total": 6,
            }
        }
        runtime_assertions = {
            "summary": {
                "asserted_family_total": 6,
                "failed_case_total": 0,
                "runtime_assertions_ready": True,
            }
        }
        widget_catalog = {
            "summary": {
                "permit_claim_packet_family_total": 6,
                "permit_checksum_sample_family_total": 6,
                "permit_widget_case_parity_family_total": 6,
            }
        }
        api_contract_spec = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "current_summary": {
                                    "family_case_goldset_family_total": 6,
                                }
                            }
                        }
                    }
                }
            }
        }
        case_release_guard = {
            "summary": {
                "family_total": 6,
                "runtime_failed_case_total": 0,
                "runtime_missing_case_total": 0,
                "widget_missing_case_total": 0,
                "api_missing_case_total": 0,
                "runtime_extra_case_total": 0,
                "widget_extra_case_total": 0,
                "api_extra_case_total": 0,
                "release_guard_ready": True,
            }
        }
        release_bundle = {
            "summary": {
                "case_release_guard_preview_ready": True,
            }
        }

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            permit_family_case_goldset=goldset_bundle,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract_spec,
            permit_case_release_guard=case_release_guard,
            permit_release_bundle=release_bundle,
            runtime_html='<div id="proofClaimBox"></div><script>const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; }; const y = "법령군 증빙";</script>',
        )

        self.assertEqual(report["current_execution_lane"]["id"], "review_case_input_presets")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "case_story_surface")
        self.assertTrue(report["summary"]["case_release_guard_preview_ready"])
        self.assertEqual(report["summary"]["edge_case_family_total"], 6)

    def test_build_brainstorm_moves_to_case_story_surface_when_presets_are_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 50,
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
        patent_bundle = {"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}}
        goldset_bundle = {"summary": {"goldset_complete_family_total": 6, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}}
        runtime_assertions = {"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}}
        widget_catalog = {"summary": {"permit_claim_packet_family_total": 6, "permit_checksum_sample_family_total": 6, "permit_widget_case_parity_family_total": 6}}
        api_contract_spec = {"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"family_case_goldset_family_total": 6}}}}}}}
        case_release_guard = {"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}}
        release_bundle = {"summary": {"case_release_guard_preview_ready": True}}
        review_case_presets = {"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}}

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            permit_family_case_goldset=goldset_bundle,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract_spec,
            permit_case_release_guard=case_release_guard,
            permit_review_case_presets=review_case_presets,
            permit_release_bundle=release_bundle,
            runtime_html='<div id="proofClaimBox"></div><script>const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; }; const y = "법령군 증빙";</script>',
        )

        self.assertEqual(report["current_execution_lane"]["id"], "case_story_surface")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "runtime_review_preset_surface")
        self.assertTrue(report["summary"]["review_case_preset_ready"])

    def test_build_brainstorm_moves_to_runtime_review_surface_when_presets_and_story_are_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 50,
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
        patent_bundle = {"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}}
        goldset_bundle = {"summary": {"goldset_complete_family_total": 6, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}}
        runtime_assertions = {"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}}
        widget_catalog = {"summary": {"permit_claim_packet_family_total": 6, "permit_checksum_sample_family_total": 6, "permit_widget_case_parity_family_total": 6}}
        api_contract_spec = {"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"family_case_goldset_family_total": 6}}}}}}}
        case_release_guard = {"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}}
        release_bundle = {"summary": {"case_release_guard_preview_ready": True}}
        review_case_presets = {"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}}
        case_story_surface = {"summary": {"story_family_total": 6, "review_reason_total": 3, "story_ready": True}}

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            permit_family_case_goldset=goldset_bundle,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract_spec,
            permit_case_release_guard=case_release_guard,
            permit_review_case_presets=review_case_presets,
            permit_case_story_surface=case_story_surface,
            permit_release_bundle=release_bundle,
            runtime_html='<div id="proofClaimBox"></div><script>const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; }; const y = "법령군 증빙";</script>',
        )

        self.assertEqual(report["current_execution_lane"]["id"], "runtime_review_preset_surface")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "story_contract_surface")
        self.assertTrue(report["summary"]["case_story_surface_ready"])

    def test_build_brainstorm_moves_to_preset_story_release_guard_when_runtime_and_contract_surfaces_are_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 50,
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
        patent_bundle = {"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}}
        goldset_bundle = {"summary": {"goldset_complete_family_total": 6, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}}
        runtime_assertions = {"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}}
        widget_catalog = {
            "summary": {
                "permit_claim_packet_family_total": 6,
                "permit_checksum_sample_family_total": 6,
                "permit_widget_case_parity_family_total": 6,
                "permit_case_story_family_total": 6,
            }
        }
        api_contract_spec = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "current_summary": {
                                    "family_case_goldset_family_total": 6,
                                    "case_story_surface_family_total": 6,
                                }
                            }
                        }
                    }
                }
            }
        }
        case_release_guard = {"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}}
        release_bundle = {"summary": {"case_release_guard_preview_ready": True, "case_story_family_total": 6, "case_story_review_reason_total": 3}}
        review_case_presets = {"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}}
        case_story_surface = {"summary": {"story_family_total": 6, "review_reason_total": 3, "story_ready": True}}
        runtime_html = """
        <div id="proofClaimBox"></div>
        <div id="reviewPresetBox"></div>
        <script>
        const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
        const applyReviewCasePreset = (preset) => { return preset; };
        const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
        const y = "data-review-preset-id";
        </script>
        """

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            permit_family_case_goldset=goldset_bundle,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract_spec,
            permit_case_release_guard=case_release_guard,
            permit_review_case_presets=review_case_presets,
            permit_case_story_surface=case_story_surface,
            permit_release_bundle=release_bundle,
            runtime_html=runtime_html,
        )

        self.assertEqual(report["current_execution_lane"]["id"], "preset_story_release_guard")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "operator_demo_packet")
        self.assertTrue(report["summary"]["runtime_review_preset_surface_ready"])
        self.assertTrue(report["summary"]["story_contract_surface_ready"])

    def test_build_brainstorm_moves_to_operator_demo_packet_after_preset_story_guard_is_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 50,
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
        patent_bundle = {"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}}
        goldset_bundle = {"summary": {"goldset_complete_family_total": 6, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}}
        runtime_assertions = {"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}}
        widget_catalog = {
            "summary": {
                "permit_claim_packet_family_total": 6,
                "permit_checksum_sample_family_total": 6,
                "permit_widget_case_parity_family_total": 6,
                "permit_case_story_family_total": 6,
            }
        }
        api_contract_spec = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "current_summary": {
                                    "family_case_goldset_family_total": 6,
                                    "case_story_surface_family_total": 6,
                                }
                            }
                        }
                    }
                }
            }
        }
        case_release_guard = {"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}}
        release_bundle = {"summary": {"case_release_guard_preview_ready": True, "case_story_family_total": 6, "case_story_review_reason_total": 3}}
        review_case_presets = {"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}}
        case_story_surface = {"summary": {"story_family_total": 6, "review_reason_total": 3, "story_ready": True}}
        preset_story_guard = {"summary": {"preset_story_guard_ready": True}}
        runtime_html = """
        <div id="proofClaimBox"></div>
        <div id="reviewPresetBox"></div>
        <script>
        const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
        const applyReviewCasePreset = (preset) => { return preset; };
        const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
        const y = "data-review-preset-id";
        </script>
        """

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            permit_family_case_goldset=goldset_bundle,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract_spec,
            permit_case_release_guard=case_release_guard,
            permit_review_case_presets=review_case_presets,
            permit_case_story_surface=case_story_surface,
            permit_preset_story_release_guard=preset_story_guard,
            permit_release_bundle=release_bundle,
            runtime_html=runtime_html,
        )

        self.assertEqual(report["current_execution_lane"]["id"], "operator_demo_packet")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "operator_demo_surface")
        self.assertTrue(report["summary"]["preset_story_guard_ready"])

    def test_build_brainstorm_moves_to_operator_demo_surface_when_packet_is_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_absorbed_row_total": 0,
                "master_focus_registry_row_total": 50,
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
        patent_bundle = {"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}}
        goldset_bundle = {"summary": {"goldset_complete_family_total": 6, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}}
        runtime_assertions = {"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}}
        widget_catalog = {
            "summary": {
                "permit_claim_packet_family_total": 6,
                "permit_checksum_sample_family_total": 6,
                "permit_widget_case_parity_family_total": 6,
                "permit_case_story_family_total": 6,
            }
        }
        api_contract_spec = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "current_summary": {
                                    "family_case_goldset_family_total": 6,
                                    "case_story_surface_family_total": 6,
                                }
                            }
                        }
                    }
                }
            }
        }
        case_release_guard = {"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}}
        release_bundle = {"summary": {"case_release_guard_preview_ready": True, "case_story_family_total": 6, "case_story_review_reason_total": 3}}
        review_case_presets = {"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}}
        case_story_surface = {"summary": {"story_family_total": 6, "review_reason_total": 3, "story_ready": True}}
        preset_story_guard = {"summary": {"preset_story_guard_ready": True}}
        operator_demo_packet = {"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 18}}
        runtime_html = """
        <div id="proofClaimBox"></div>
        <div id="reviewPresetBox"></div>
        <script>
        const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
        const applyReviewCasePreset = (preset) => { return preset; };
        const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
        const y = "data-review-preset-id";
        </script>
        """

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            permit_family_case_goldset=goldset_bundle,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract_spec,
            permit_case_release_guard=case_release_guard,
            permit_review_case_presets=review_case_presets,
            permit_case_story_surface=case_story_surface,
            permit_preset_story_release_guard=preset_story_guard,
            permit_operator_demo_packet=operator_demo_packet,
            permit_release_bundle=release_bundle,
            runtime_html=runtime_html,
        )

        self.assertEqual(report["current_execution_lane"]["id"], "operator_demo_surface")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "partner_demo_surface")
        self.assertTrue(report["summary"]["operator_demo_packet_ready"])
        self.assertEqual(report["summary"]["operator_demo_family_total"], 6)
        self.assertEqual(report["summary"]["operator_demo_case_total"], 18)
        self.assertFalse(report["summary"]["runtime_operator_demo_surface_ready"])
        self.assertFalse(report["summary"]["operator_demo_release_surface_ready"])

    def test_build_brainstorm_moves_to_partner_demo_surface_when_operator_surface_is_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_focus_registry_row_total": 50,
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
        patent_bundle = {"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}}
        goldset_bundle = {"summary": {"goldset_complete_family_total": 6, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}}
        runtime_assertions = {"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}}
        widget_catalog = {"summary": {"permit_partner_demo_surface_ready": False}}
        api_contract_spec = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "current_summary": {
                                    "partner_demo_surface_ready": False,
                                }
                            }
                        }
                    }
                }
            }
        }
        case_release_guard = {"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}}
        release_bundle = {"summary": {"case_release_guard_preview_ready": True, "operator_demo_release_surface_ready": True}}
        review_case_presets = {"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}}
        case_story_surface = {"summary": {"story_family_total": 6, "review_reason_total": 3, "story_ready": True}}
        preset_story_guard = {"summary": {"preset_story_guard_ready": True}}
        operator_demo_packet = {"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 18}}
        runtime_html = """
        <div id="proofClaimBox"></div>
        <div id="reviewPresetBox"></div>
        <div id="operatorDemoBox"></div>
        <script>
        const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
        const applyReviewCasePreset = (preset) => { return preset; };
        const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
        const getOperatorDemoSurface = (row) => (row && row.operator_demo_surface ? row.operator_demo_surface : null);
        const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
        const marker = "data-review-preset-id";
        const operatorDemoMarker = "operator_demo_surface";
        </script>
        """

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            permit_family_case_goldset=goldset_bundle,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract_spec,
            permit_case_release_guard=case_release_guard,
            permit_review_case_presets=review_case_presets,
            permit_case_story_surface=case_story_surface,
            permit_preset_story_release_guard=preset_story_guard,
            permit_operator_demo_packet=operator_demo_packet,
            permit_release_bundle=release_bundle,
            runtime_html=runtime_html,
        )

        self.assertEqual(report["current_execution_lane"]["id"], "partner_demo_surface")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "critical_prompt_surface_lock")
        self.assertTrue(report["summary"]["runtime_operator_demo_surface_ready"])
        self.assertTrue(report["summary"]["operator_demo_release_surface_ready"])
        self.assertFalse(report["summary"]["partner_demo_surface_ready"])

    def test_build_brainstorm_moves_to_critical_prompt_surface_when_demo_surfaces_are_ready(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 51,
                "master_focus_registry_row_total": 50,
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
        patent_bundle = {"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}}
        goldset_bundle = {"summary": {"goldset_complete_family_total": 6, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}}
        runtime_assertions = {"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}}
        widget_catalog = {"summary": {"permit_partner_demo_surface_ready": True}}
        api_contract_spec = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "current_summary": {
                                    "partner_demo_surface_ready": True,
                                }
                            }
                        }
                    }
                }
            }
        }
        case_release_guard = {"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}}
        release_bundle = {"summary": {"case_release_guard_preview_ready": True, "operator_demo_release_surface_ready": True}}
        review_case_presets = {"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}}
        case_story_surface = {"summary": {"story_family_total": 6, "review_reason_total": 3, "story_ready": True}}
        preset_story_guard = {"summary": {"preset_story_guard_ready": True}}
        operator_demo_packet = {"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 18}}
        runtime_html = """
        <div id="proofClaimBox"></div>
        <div id="reviewPresetBox"></div>
        <div id="operatorDemoBox"></div>
        <script>
        const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
        const applyReviewCasePreset = (preset) => { return preset; };
        const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
        const getOperatorDemoSurface = (row) => (row && row.operator_demo_surface ? row.operator_demo_surface : null);
        const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
        const marker = "data-review-preset-id";
        const operatorDemoMarker = "operator_demo_surface";
        </script>
        """

        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog=master_catalog,
            provenance_audit=provenance_audit,
            focus_report=focus_report,
            source_upgrade_backlog=source_upgrade_backlog,
            permit_patent_evidence_bundle=patent_bundle,
            permit_family_case_goldset=goldset_bundle,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract_spec,
            permit_case_release_guard=case_release_guard,
            permit_review_case_presets=review_case_presets,
            permit_case_story_surface=case_story_surface,
            permit_preset_story_release_guard=preset_story_guard,
            permit_operator_demo_packet=operator_demo_packet,
            permit_release_bundle=release_bundle,
            runtime_html=runtime_html,
        )

        self.assertEqual(report["current_execution_lane"]["id"], "critical_prompt_surface_lock")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "demo_surface_observability")
        self.assertTrue(report["summary"]["partner_demo_surface_ready"])


if __name__ == "__main__":
    unittest.main()
