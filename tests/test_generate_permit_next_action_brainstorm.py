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
        self.assertEqual(report["summary"]["execution_lane"], "focus_seed_source_upgrade")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "patent_evidence_bundle")
        self.assertEqual(report["summary"]["parallel_lane"], "patent_evidence_bundle")
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
        self.assertEqual(report["summary"]["execution_lane"], "focus_family_registry_hardening")
        self.assertEqual(report["summary"]["parallel_lane"], "patent_evidence_bundle")

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

    def test_build_brainstorm_ignores_stale_release_bundle_for_operator_demo_surface(self):
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
        release_bundle = {"summary": {"case_release_guard_preview_ready": True, "operator_demo_release_surface_ready": False}}
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

        self.assertTrue(report["summary"]["runtime_operator_demo_surface_ready"])
        self.assertTrue(report["summary"]["operator_demo_release_surface_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "critical_prompt_surface_lock")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "demo_surface_observability")

    def test_build_brainstorm_moves_to_demo_surface_observability_when_prompt_surface_is_ready(self):
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
        const criticalPromptMarker = "runtime_critical_prompt_excerpt";
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
            prompt_doc="# prompt",
        )

        self.assertTrue(report["summary"]["runtime_critical_prompt_surface_ready"])
        self.assertFalse(report["summary"]["demo_surface_observability_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "demo_surface_observability")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "prompt_case_binding")
        markdown = generate_permit_next_action_brainstorm.render_markdown(report)
        self.assertNotIn("\\nThe current execution lane", markdown)

    def test_build_brainstorm_moves_to_prompt_case_binding_when_observability_is_ready(self):
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
        observability_report = {"summary": {"observability_ready": True}}
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
        const criticalPromptMarker = "runtime_critical_prompt_excerpt";
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
            permit_demo_surface_observability=observability_report,
            permit_release_bundle=release_bundle,
            runtime_html=runtime_html,
            prompt_doc="# prompt",
        )

        self.assertTrue(report["summary"]["runtime_critical_prompt_surface_ready"])
        self.assertTrue(report["summary"]["demo_surface_observability_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "prompt_case_binding")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "surface_drift_digest")

    def test_build_brainstorm_moves_to_surface_drift_digest_when_prompt_binding_is_ready(self):
        master_catalog = {"summary": {"master_industry_total": 51, "master_focus_registry_row_total": 50}, "industries": []}
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
        api_contract_spec = {"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"partner_demo_surface_ready": True}}}}}}}
        case_release_guard = {"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}}
        review_case_presets = {"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}}
        case_story_surface = {"summary": {"story_family_total": 6, "review_reason_total": 3, "story_ready": True}}
        preset_story_guard = {"summary": {"preset_story_guard_ready": True}}
        operator_demo_packet = {"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 18, "prompt_case_binding_total": 6}}
        observability_report = {"summary": {"observability_ready": True}}
        runtime_html = """
        <div id="proofClaimBox"></div>
        <div id="reviewPresetBox"></div>
        <div id="operatorDemoBox"></div>
        <script>
        const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
        const applyReviewCasePreset = (preset) => { return preset; };
        const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
        const presetMarker = "data-review-preset-id";
        const getOperatorDemoSurface = (row) => (row && row.operator_demo_surface ? row.operator_demo_surface : null);
        const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
        const promptBindingMarker = "prompt_case_binding";
        const promptBindingTotal = "runtime_prompt_case_binding_total";
        const promptBindingButton = "data-prompt-preset-id";
        const criticalPromptMarker = "runtime_critical_prompt_excerpt";
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
            permit_demo_surface_observability=observability_report,
            runtime_html=runtime_html,
            prompt_doc="# prompt",
        )

        self.assertTrue(report["summary"]["runtime_prompt_case_binding_surface_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "surface_drift_digest")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "partner_binding_parity")

    def test_build_brainstorm_moves_to_partner_binding_parity_when_drift_digest_is_ready(self):
        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog={"summary": {"master_industry_total": 51, "master_focus_registry_row_total": 50}, "industries": []},
            provenance_audit={"summary": {"focus_family_registry_row_total": 50, "focus_seed_row_total": 0, "focus_family_registry_missing_raw_source_proof_total": 0, "candidate_pack_total": 0, "master_inferred_overlay_total": 0}},
            focus_report={"summary": {"real_focus_target_total": 51}},
            source_upgrade_backlog={"summary": {"focus_seed_group_total": 0, "absorbed_group_total": 0}},
            permit_patent_evidence_bundle={"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}},
            permit_family_case_goldset={"summary": {"goldset_complete_family_total": 6, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}},
            permit_runtime_case_assertions={"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}},
            widget_rental_catalog={"summary": {"permit_partner_demo_surface_ready": True}},
            api_contract_spec={"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"partner_demo_surface_ready": True}}}}}}},
            permit_case_release_guard={"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}},
            permit_review_case_presets={"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}},
            permit_case_story_surface={"summary": {"story_family_total": 6, "review_reason_total": 3, "story_ready": True}},
            permit_preset_story_release_guard={"summary": {"preset_story_guard_ready": True}},
            permit_operator_demo_packet={"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 18, "prompt_case_binding_total": 6}},
            permit_demo_surface_observability={"summary": {"observability_ready": True}},
            permit_surface_drift_digest={"summary": {"digest_ready": True, "delta_ready": True, "changed_surface_total": 2, "readiness_flip_total": 1}},
            runtime_html="""
            <div id="proofClaimBox"></div>
            <div id="reviewPresetBox"></div>
            <div id="operatorDemoBox"></div>
            <script>
            const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
            const applyReviewCasePreset = (preset) => { return preset; };
            const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
            const presetMarker = "data-review-preset-id";
            const getOperatorDemoSurface = (row) => (row && row.operator_demo_surface ? row.operator_demo_surface : null);
            const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
            const promptBindingMarker = "prompt_case_binding";
            const promptBindingTotal = "runtime_prompt_case_binding_total";
            const promptBindingButton = "data-prompt-preset-id";
            const criticalPromptMarker = "runtime_critical_prompt_excerpt";
            </script>
            """,
            prompt_doc="# prompt",
        )

        self.assertTrue(report["summary"]["surface_drift_digest_ready"])
        self.assertTrue(report["summary"]["surface_drift_delta_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "partner_binding_parity")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "review_reason_decision_ladder")

    def test_build_brainstorm_moves_to_review_reason_ladder_when_partner_binding_is_ready(self):
        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog={"summary": {"master_industry_total": 51, "master_focus_registry_row_total": 50}, "industries": []},
            provenance_audit={"summary": {"focus_family_registry_row_total": 50, "focus_seed_row_total": 0, "focus_family_registry_missing_raw_source_proof_total": 0, "candidate_pack_total": 0, "master_inferred_overlay_total": 0}},
            focus_report={"summary": {"real_focus_target_total": 51}},
            source_upgrade_backlog={"summary": {"focus_seed_group_total": 0, "absorbed_group_total": 0}},
            permit_patent_evidence_bundle={"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}},
            permit_family_case_goldset={"summary": {"goldset_complete_family_total": 6, "case_total": 36, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}},
            permit_runtime_case_assertions={"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}},
            widget_rental_catalog={"summary": {"permit_claim_packet_family_total": 6, "permit_checksum_sample_family_total": 6, "permit_widget_case_parity_family_total": 6, "permit_partner_demo_surface_ready": True, "permit_partner_binding_sample_total": 6, "permit_partner_binding_surface_ready": True}},
            api_contract_spec={"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"family_case_goldset_family_total": 6, "partner_demo_surface_ready": True, "partner_binding_sample_total": 6, "partner_binding_surface_ready": True}}}}}}},
            permit_case_release_guard={"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}},
            permit_review_case_presets={"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}},
            permit_case_story_surface={"summary": {"story_family_total": 6, "review_reason_total": 3, "manual_review_family_total": 6, "story_ready": True}},
            permit_preset_story_release_guard={"summary": {"preset_story_guard_ready": True, "runtime_review_preset_surface_ready": True, "runtime_case_story_surface_ready": True, "story_contract_parity_ready": True}},
            permit_operator_demo_packet={"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 18, "prompt_case_binding_total": 6}},
            permit_demo_surface_observability={"summary": {"observability_ready": True}},
            permit_surface_drift_digest={"summary": {"digest_ready": True, "delta_ready": True, "changed_surface_total": 0, "readiness_flip_total": 0}},
            runtime_html="""
            <div id="proofClaimBox"></div>
            <div id="reviewPresetBox"></div>
            <div id="operatorDemoBox"></div>
            <script>
            const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
            const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
            const applyReviewCasePreset = (preset) => { return preset; };
            const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
            const getOperatorDemoSurface = (row) => (row.operator_demo_surface);
            const promptBindingMarker = "prompt_case_binding";
            const promptBindingButton = "data-prompt-preset-id";
            const criticalPromptMarker = "runtime_critical_prompt_excerpt";
            const reviewPresetButton = "data-review-preset-id";
            </script>
            """,
            prompt_doc="# prompt",
        )

        self.assertTrue(report["summary"]["partner_binding_parity_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "review_reason_decision_ladder")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "thinking_prompt_bundle_lock")

    def test_build_brainstorm_moves_to_thinking_prompt_bundle_when_ladder_is_ready(self):
        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog={"summary": {"master_industry_total": 51, "master_focus_registry_row_total": 50}, "industries": []},
            provenance_audit={"summary": {"focus_family_registry_row_total": 50, "focus_seed_row_total": 0, "focus_family_registry_missing_raw_source_proof_total": 0, "candidate_pack_total": 0, "master_inferred_overlay_total": 0}},
            focus_report={"summary": {"real_focus_target_total": 51}},
            source_upgrade_backlog={"summary": {"focus_seed_group_total": 0, "absorbed_group_total": 0}},
            permit_patent_evidence_bundle={"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}},
            permit_family_case_goldset={"summary": {"goldset_complete_family_total": 6, "case_total": 36, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}},
            permit_runtime_case_assertions={"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}},
            widget_rental_catalog={"summary": {"permit_claim_packet_family_total": 6, "permit_checksum_sample_family_total": 6, "permit_widget_case_parity_family_total": 6, "permit_partner_demo_surface_ready": True, "permit_partner_binding_sample_total": 6, "permit_partner_binding_surface_ready": True}},
            api_contract_spec={"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"family_case_goldset_family_total": 6, "partner_demo_surface_ready": True, "partner_binding_sample_total": 6, "partner_binding_surface_ready": True}}}}}}},
            permit_case_release_guard={"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}},
            permit_review_case_presets={"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}},
            permit_case_story_surface={"summary": {"story_family_total": 6, "review_reason_total": 3, "manual_review_family_total": 6, "story_ready": True}},
            permit_preset_story_release_guard={"summary": {"preset_story_guard_ready": True, "runtime_review_preset_surface_ready": True, "runtime_case_story_surface_ready": True, "story_contract_parity_ready": True}},
            permit_operator_demo_packet={"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 18, "prompt_case_binding_total": 6}},
            permit_review_reason_decision_ladder={"summary": {"review_reason_total": 3, "manual_review_gate_total": 1, "prompt_bound_reason_total": 3, "decision_ladder_ready": True}},
            permit_demo_surface_observability={"summary": {"observability_ready": True}},
            permit_surface_drift_digest={"summary": {"digest_ready": True, "delta_ready": True, "changed_surface_total": 0, "readiness_flip_total": 0}},
            runtime_html="""
            <div id="proofClaimBox"></div>
            <div id="reviewPresetBox"></div>
            <div id="operatorDemoBox"></div>
            <script>
            const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
            const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
            const applyReviewCasePreset = (preset) => { return preset; };
            const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
            const getOperatorDemoSurface = (row) => (row.operator_demo_surface);
            const promptBindingMarker = "prompt_case_binding";
            const promptBindingButton = "data-prompt-preset-id";
            const criticalPromptMarker = "runtime_critical_prompt_excerpt";
            const reviewPresetButton = "data-review-preset-id";
            </script>
            """,
            prompt_doc="# prompt",
        )

        self.assertTrue(report["summary"]["review_reason_decision_ladder_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "thinking_prompt_bundle_lock")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "partner_binding_observability")

    def test_build_brainstorm_moves_to_partner_binding_observability_when_thinking_bundle_is_ready(self):
        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog={"summary": {"master_industry_total": 51, "master_focus_registry_row_total": 50}, "industries": []},
            provenance_audit={"summary": {"focus_family_registry_row_total": 50, "focus_seed_row_total": 0, "focus_family_registry_missing_raw_source_proof_total": 0, "candidate_pack_total": 0, "master_inferred_overlay_total": 0}},
            focus_report={"summary": {"real_focus_target_total": 51}},
            source_upgrade_backlog={"summary": {"focus_seed_group_total": 0, "absorbed_group_total": 0}},
            permit_patent_evidence_bundle={"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}},
            permit_family_case_goldset={"summary": {"goldset_complete_family_total": 6, "case_total": 36, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}},
            permit_runtime_case_assertions={"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}},
            widget_rental_catalog={"summary": {"permit_claim_packet_family_total": 6, "permit_checksum_sample_family_total": 6, "permit_widget_case_parity_family_total": 6, "permit_partner_demo_surface_ready": True, "permit_partner_binding_sample_total": 6, "permit_partner_binding_surface_ready": True}},
            api_contract_spec={"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"family_case_goldset_family_total": 6, "partner_demo_surface_ready": True, "partner_binding_sample_total": 6, "partner_binding_surface_ready": True}}}}}}},
            permit_case_release_guard={"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}},
            permit_review_case_presets={"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}},
            permit_case_story_surface={"summary": {"story_family_total": 6, "review_reason_total": 3, "manual_review_family_total": 6, "story_ready": True}},
            permit_preset_story_release_guard={"summary": {"preset_story_guard_ready": True, "runtime_review_preset_surface_ready": True, "runtime_case_story_surface_ready": True, "story_contract_parity_ready": True}},
            permit_operator_demo_packet={"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 18, "prompt_case_binding_total": 6}},
            permit_review_reason_decision_ladder={"summary": {"review_reason_total": 3, "manual_review_gate_total": 1, "prompt_bound_reason_total": 3, "decision_ladder_ready": True}},
            permit_thinking_prompt_bundle_packet={"summary": {"packet_ready": True, "prompt_section_total": 9, "operator_jump_case_total": 18, "decision_ladder_row_total": 3, "runtime_target_ready": True, "release_target_ready": True, "operator_target_ready": True}},
            permit_partner_binding_observability={"summary": {"observability_ready": False, "expected_family_total": 6, "widget_binding_family_total": 5, "api_binding_family_total": 6, "widget_missing_family_total": 1, "api_missing_family_total": 0}},
            permit_demo_surface_observability={"summary": {"observability_ready": True}},
            permit_surface_drift_digest={"summary": {"digest_ready": True, "delta_ready": True, "changed_surface_total": 0, "readiness_flip_total": 0}},
            runtime_html="""
            <div id="proofClaimBox"></div>
            <div id="reviewPresetBox"></div>
            <div id="operatorDemoBox"></div>
            <script>
            const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
            const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
            const applyReviewCasePreset = (preset) => { return preset; };
            const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
            const getOperatorDemoSurface = (row) => (row.operator_demo_surface);
            const promptBindingMarker = "prompt_case_binding";
            const promptBindingButton = "data-prompt-preset-id";
            const criticalPromptMarker = "runtime_critical_prompt_excerpt";
            const reviewPresetButton = "data-review-preset-id";
            </script>
            """,
            prompt_doc="# prompt",
        )

        self.assertTrue(report["summary"]["thinking_prompt_bundle_ready"])
        self.assertFalse(report["summary"]["partner_binding_observability_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "partner_binding_observability")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "runtime_reasoning_card")

    def test_build_brainstorm_moves_to_partner_gap_preview_digest_when_bundle_and_observability_are_ready(self):
        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog={"summary": {"master_industry_total": 51, "master_focus_registry_row_total": 50}, "industries": []},
            provenance_audit={"summary": {"focus_family_registry_row_total": 50, "focus_seed_row_total": 0, "focus_family_registry_missing_raw_source_proof_total": 0, "candidate_pack_total": 0, "master_inferred_overlay_total": 0}},
            focus_report={"summary": {"real_focus_target_total": 51}},
            source_upgrade_backlog={"summary": {"focus_seed_group_total": 0, "absorbed_group_total": 0}},
            permit_patent_evidence_bundle={"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}},
            permit_family_case_goldset={"summary": {"goldset_complete_family_total": 6, "case_total": 36, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}},
            permit_runtime_case_assertions={"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}},
            widget_rental_catalog={"summary": {"permit_claim_packet_family_total": 6, "permit_checksum_sample_family_total": 6, "permit_widget_case_parity_family_total": 6, "permit_partner_demo_surface_ready": True, "permit_partner_binding_sample_total": 6, "permit_partner_binding_surface_ready": True}},
            api_contract_spec={"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"family_case_goldset_family_total": 6, "partner_demo_surface_ready": True, "partner_binding_sample_total": 6, "partner_binding_surface_ready": True}}}}}}},
            permit_case_release_guard={"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}},
            permit_review_case_presets={"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}},
            permit_case_story_surface={"summary": {"story_family_total": 6, "review_reason_total": 3, "manual_review_family_total": 6, "story_ready": True}},
            permit_preset_story_release_guard={"summary": {"preset_story_guard_ready": True, "runtime_review_preset_surface_ready": True, "runtime_case_story_surface_ready": True, "story_contract_parity_ready": True}},
            permit_operator_demo_packet={"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 18, "prompt_case_binding_total": 6}},
            permit_review_reason_decision_ladder={"summary": {"review_reason_total": 3, "manual_review_gate_total": 1, "prompt_bound_reason_total": 3, "decision_ladder_ready": True}},
            permit_thinking_prompt_bundle_packet={"summary": {"packet_ready": True, "prompt_section_total": 9, "operator_jump_case_total": 18, "decision_ladder_row_total": 3, "runtime_target_ready": True, "release_target_ready": True, "operator_target_ready": True}},
            permit_partner_binding_observability={"summary": {"observability_ready": True, "expected_family_total": 6, "widget_binding_family_total": 6, "api_binding_family_total": 6, "widget_missing_family_total": 0, "api_missing_family_total": 0}},
            permit_demo_surface_observability={"summary": {"observability_ready": True}},
            permit_surface_drift_digest={"summary": {"digest_ready": True, "delta_ready": True, "changed_surface_total": 0, "readiness_flip_total": 0}},
            runtime_html="""
            <div id="proofClaimBox"></div>
            <div id="reviewPresetBox"></div>
            <div id="operatorDemoBox"></div>
            <script>
            const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
            const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
            const applyReviewCasePreset = (preset) => { return preset; };
            const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
            const getOperatorDemoSurface = (row) => (row.operator_demo_surface);
            const promptBindingMarker = "prompt_case_binding";
            const promptBindingButton = "data-prompt-preset-id";
            const criticalPromptMarker = "runtime_critical_prompt_excerpt";
            const reviewPresetButton = "data-review-preset-id";
            </script>
            """,
            prompt_doc="# prompt",
        )

        self.assertTrue(report["summary"]["thinking_prompt_bundle_ready"])
        self.assertTrue(report["summary"]["partner_binding_observability_ready"])
        self.assertFalse(report["summary"]["partner_gap_preview_digest_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "partner_gap_preview_digest")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "runtime_reasoning_card")

    def test_build_brainstorm_moves_to_runtime_reasoning_card_when_partner_gap_digest_is_ready(self):
        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog={"summary": {"master_industry_total": 51, "master_focus_registry_row_total": 50}, "industries": []},
            provenance_audit={"summary": {"focus_family_registry_row_total": 50, "focus_seed_row_total": 0, "focus_family_registry_missing_raw_source_proof_total": 0, "candidate_pack_total": 0, "master_inferred_overlay_total": 0}},
            focus_report={"summary": {"real_focus_target_total": 51}},
            source_upgrade_backlog={"summary": {"focus_seed_group_total": 0, "absorbed_group_total": 0}},
            permit_patent_evidence_bundle={"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}},
            permit_family_case_goldset={"summary": {"goldset_complete_family_total": 6, "case_total": 36, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}},
            permit_runtime_case_assertions={"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}},
            widget_rental_catalog={"summary": {"permit_claim_packet_family_total": 6, "permit_checksum_sample_family_total": 6, "permit_widget_case_parity_family_total": 6, "permit_partner_demo_surface_ready": True, "permit_partner_binding_sample_total": 6, "permit_partner_binding_surface_ready": True}},
            api_contract_spec={"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"family_case_goldset_family_total": 6, "partner_demo_surface_ready": True, "partner_binding_sample_total": 6, "partner_binding_surface_ready": True}}}}}}},
            permit_case_release_guard={"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}},
            permit_review_case_presets={"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}},
            permit_case_story_surface={"summary": {"story_family_total": 6, "review_reason_total": 3, "manual_review_family_total": 6, "story_ready": True}},
            permit_preset_story_release_guard={"summary": {"preset_story_guard_ready": True, "runtime_review_preset_surface_ready": True, "runtime_case_story_surface_ready": True, "story_contract_parity_ready": True}},
            permit_operator_demo_packet={"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 18, "prompt_case_binding_total": 6}},
            permit_review_reason_decision_ladder={"summary": {"review_reason_total": 3, "manual_review_gate_total": 1, "prompt_bound_reason_total": 3, "decision_ladder_ready": True}},
            permit_thinking_prompt_bundle_packet={"summary": {"packet_ready": True, "prompt_section_total": 9, "operator_jump_case_total": 18, "decision_ladder_row_total": 3, "runtime_target_ready": True, "release_target_ready": True, "operator_target_ready": True}},
            permit_partner_binding_observability={"summary": {"observability_ready": True, "expected_family_total": 6, "widget_binding_family_total": 6, "api_binding_family_total": 6, "widget_missing_family_total": 0, "api_missing_family_total": 0}},
            permit_partner_gap_preview_digest={"summary": {"digest_ready": True, "blank_binding_preset_total": 0, "widget_preset_mismatch_total": 0, "api_preset_mismatch_total": 0}},
            permit_demo_surface_observability={"summary": {"observability_ready": True}},
            permit_surface_drift_digest={"summary": {"digest_ready": True, "delta_ready": True, "changed_surface_total": 0, "readiness_flip_total": 0}},
            runtime_html="""
            <div id="proofClaimBox"></div>
            <div id="reviewPresetBox"></div>
            <div id="operatorDemoBox"></div>
            <script>
            const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
            const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
            const applyReviewCasePreset = (preset) => { return preset; };
            const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
            const getOperatorDemoSurface = (row) => (row.operator_demo_surface);
            const promptBindingMarker = "prompt_case_binding";
            const promptBindingButton = "data-prompt-preset-id";
            const criticalPromptMarker = "runtime_critical_prompt_excerpt";
            const reviewPresetButton = "data-review-preset-id";
            </script>
            """,
            prompt_doc="# prompt",
        )

        self.assertTrue(report["summary"]["partner_gap_preview_digest_ready"])
        self.assertFalse(report["summary"]["runtime_reasoning_card_surface_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "runtime_reasoning_card")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "demo_surface_observability")

    def test_build_brainstorm_moves_to_runtime_reasoning_guard_when_reasoning_card_is_live(self):
        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog={"summary": {"master_industry_total": 51, "master_focus_registry_row_total": 50}, "industries": []},
            provenance_audit={"summary": {"focus_family_registry_row_total": 50, "focus_seed_row_total": 0, "focus_family_registry_missing_raw_source_proof_total": 0, "candidate_pack_total": 0, "master_inferred_overlay_total": 0}},
            focus_report={"summary": {"real_focus_target_total": 51}},
            source_upgrade_backlog={"summary": {"focus_seed_group_total": 0, "absorbed_group_total": 0}},
            permit_patent_evidence_bundle={"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}},
            permit_family_case_goldset={"summary": {"goldset_complete_family_total": 6, "case_total": 36, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}},
            permit_runtime_case_assertions={"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}},
            widget_rental_catalog={"summary": {"permit_claim_packet_family_total": 6, "permit_checksum_sample_family_total": 6, "permit_widget_case_parity_family_total": 6, "permit_partner_demo_surface_ready": True, "permit_partner_binding_sample_total": 6, "permit_partner_binding_surface_ready": True}},
            api_contract_spec={"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"family_case_goldset_family_total": 6, "partner_demo_surface_ready": True, "partner_binding_sample_total": 6, "partner_binding_surface_ready": True}}}}}}},
            permit_case_release_guard={"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}},
            permit_review_case_presets={"summary": {"preset_total": 18, "preset_family_total": 6, "preset_ready": True}},
            permit_case_story_surface={"summary": {"story_family_total": 6, "review_reason_total": 3, "manual_review_family_total": 6, "story_ready": True}},
            permit_preset_story_release_guard={"summary": {"preset_story_guard_ready": True, "runtime_review_preset_surface_ready": True, "runtime_case_story_surface_ready": True, "story_contract_parity_ready": True}},
            permit_operator_demo_packet={"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 18, "prompt_case_binding_total": 6}},
            permit_review_reason_decision_ladder={"summary": {"review_reason_total": 3, "manual_review_gate_total": 1, "prompt_bound_reason_total": 3, "decision_ladder_ready": True}},
            permit_thinking_prompt_bundle_packet={"summary": {"packet_ready": True, "prompt_section_total": 9, "operator_jump_case_total": 18, "decision_ladder_row_total": 3, "runtime_target_ready": True, "release_target_ready": True, "operator_target_ready": True}},
            permit_partner_binding_observability={"summary": {"observability_ready": True, "expected_family_total": 6, "widget_binding_family_total": 6, "api_binding_family_total": 6, "widget_missing_family_total": 0, "api_missing_family_total": 0}},
            permit_partner_gap_preview_digest={"summary": {"digest_ready": True, "blank_binding_preset_total": 0, "widget_preset_mismatch_total": 0, "api_preset_mismatch_total": 0}},
            permit_demo_surface_observability={"summary": {"observability_ready": True}},
            permit_surface_drift_digest={"summary": {"digest_ready": True, "delta_ready": True, "changed_surface_total": 0, "readiness_flip_total": 0}},
            runtime_html="""
            <div id="proofClaimBox"></div>
            <div id="reviewPresetBox"></div>
            <div id="operatorDemoBox"></div>
            <div id="runtimeReasoningCardBox"></div>
            <script>
            const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
            const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
            const applyReviewCasePreset = (preset) => { return preset; };
            const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
            const getOperatorDemoSurface = (row) => (row.operator_demo_surface);
            const renderRuntimeReasoningCard = (industry, typedEval, context = {}) => { return [industry, typedEval, context]; };
            const promptBindingMarker = "prompt_case_binding";
            const promptBindingButton = "data-prompt-preset-id";
            const criticalPromptMarker = "runtime_critical_prompt_excerpt";
            const reviewPresetButton = "data-review-preset-id";
            const reasoningPresetButton = "data-runtime-preset-id";
            const reasoningLadderMap = "runtime_reasoning_ladder_map";
            </script>
            """,
            prompt_doc="# prompt",
        )

        self.assertTrue(report["summary"]["partner_gap_preview_digest_ready"])
        self.assertTrue(report["summary"]["runtime_reasoning_card_surface_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "runtime_reasoning_guard")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "surface_drift_digest")

    def test_build_brainstorm_advances_past_runtime_reasoning_guard_when_guard_is_closed(self):
        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog={"summary": {"master_industry_total": 51, "master_focus_registry_row_total": 50}, "industries": []},
            provenance_audit={"summary": {"focus_family_registry_row_total": 50, "focus_seed_row_total": 0, "focus_family_registry_missing_raw_source_proof_total": 0, "candidate_pack_total": 0, "master_inferred_overlay_total": 0}},
            focus_report={"summary": {"real_focus_target_total": 51}},
            source_upgrade_backlog={"summary": {"focus_seed_group_total": 0, "absorbed_group_total": 0}},
            permit_patent_evidence_bundle={"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}},
            permit_family_case_goldset={"summary": {"goldset_complete_family_total": 6, "case_total": 36, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}},
            permit_runtime_case_assertions={"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}},
            widget_rental_catalog={"summary": {"permit_claim_packet_family_total": 6, "permit_checksum_sample_family_total": 6, "permit_widget_case_parity_family_total": 6, "permit_partner_demo_surface_ready": True, "permit_partner_binding_sample_total": 6, "permit_partner_binding_surface_ready": True}},
            api_contract_spec={"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"family_case_goldset_family_total": 6, "partner_demo_surface_ready": True, "partner_binding_sample_total": 6, "partner_binding_surface_ready": True}}}}}}},
            permit_case_release_guard={"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}},
            permit_review_case_presets={"summary": {"preset_total": 24, "preset_family_total": 6, "preset_ready": True}},
            permit_case_story_surface={"summary": {"story_family_total": 6, "review_reason_total": 4, "manual_review_family_total": 6, "story_ready": True}},
            permit_preset_story_release_guard={"summary": {"preset_story_guard_ready": True, "runtime_review_preset_surface_ready": True, "runtime_case_story_surface_ready": True, "story_contract_parity_ready": True}},
            permit_operator_demo_packet={"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 24, "prompt_case_binding_total": 6}},
            permit_review_reason_decision_ladder={"summary": {"review_reason_total": 4, "manual_review_gate_total": 1, "prompt_bound_reason_total": 4, "decision_ladder_ready": True}},
            permit_thinking_prompt_bundle_packet={"summary": {"packet_ready": True, "prompt_section_total": 9, "operator_jump_case_total": 24, "decision_ladder_row_total": 4, "runtime_target_ready": True, "release_target_ready": True, "operator_target_ready": True}},
            permit_partner_binding_observability={"summary": {"observability_ready": True, "expected_family_total": 6, "widget_binding_family_total": 6, "api_binding_family_total": 6, "widget_missing_family_total": 0, "api_missing_family_total": 0}},
            permit_partner_gap_preview_digest={"summary": {"digest_ready": True, "blank_binding_preset_total": 0, "widget_preset_mismatch_total": 0, "api_preset_mismatch_total": 0}},
            permit_demo_surface_observability={"summary": {"observability_ready": True}},
            permit_surface_drift_digest={"summary": {"digest_ready": True, "delta_ready": True, "changed_surface_total": 0, "readiness_flip_total": 0, "reasoning_changed_surface_total": 0, "reasoning_regression_total": 0}},
            permit_runtime_reasoning_guard={"summary": {"guard_ready": True, "binding_gap_total": 0, "missing_binding_reason_total": 0}},
            runtime_html="""
            <div id="proofClaimBox"></div>
            <div id="reviewPresetBox"></div>
            <div id="operatorDemoBox"></div>
            <div id="runtimeReasoningCardBox"></div>
            <script>
            const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
            const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
            const applyReviewCasePreset = (preset) => { return preset; };
            const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
            const getOperatorDemoSurface = (row) => (row.operator_demo_surface);
            const renderRuntimeReasoningCard = (industry, typedEval, context = {}) => { return [industry, typedEval, context]; };
            const promptBindingMarker = "prompt_case_binding";
            const promptBindingButton = "data-prompt-preset-id";
            const criticalPromptMarker = "runtime_critical_prompt_excerpt";
            const reviewPresetButton = "data-review-preset-id";
            const reasoningPresetButton = "data-runtime-preset-id";
            const reasoningLadderMap = "runtime_reasoning_ladder_map";
            </script>
            """,
            prompt_doc="# prompt",
        )

        self.assertTrue(report["summary"]["runtime_reasoning_guard_ready"])
        self.assertTrue(report["summary"]["runtime_reasoning_guard_exit_ready"])
        self.assertEqual(report["current_execution_lane"]["id"], "thinking_prompt_successor_alignment")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "closed_lane_stale_audit")
        markdown = generate_permit_next_action_brainstorm.render_markdown(report)
        self.assertIn("runtime_reasoning_guard_exit_ready", markdown)

    def test_build_brainstorm_moves_to_capital_logic_lock_when_closed_lane_audit_is_green(self):
        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog={"summary": {"master_industry_total": 51, "master_focus_registry_row_total": 50}, "industries": []},
            provenance_audit={"summary": {"focus_family_registry_row_total": 50, "focus_seed_row_total": 0, "focus_family_registry_missing_raw_source_proof_total": 0, "candidate_pack_total": 0, "master_inferred_overlay_total": 0}},
            focus_report={"summary": {"real_focus_target_total": 51}},
            permit_capital_registration_logic_packet={"summary": {"packet_ready": True, "focus_target_total": 51, "family_total": 6, "capital_evidence_missing_total": 50, "technical_evidence_missing_total": 8, "other_evidence_missing_total": 1, "primary_gap_id": "capital_evidence_backfill"}},
            source_upgrade_backlog={"summary": {"focus_seed_group_total": 0, "absorbed_group_total": 0}},
            permit_patent_evidence_bundle={"summary": {"focus_source_family_total": 6, "claim_packet_family_total": 6, "claim_packet_complete_family_total": 6, "checksum_sample_family_total": 6}},
            permit_family_case_goldset={"summary": {"goldset_complete_family_total": 6, "case_total": 36, "edge_case_total": 18, "edge_case_family_total": 6, "manual_review_case_total": 6}},
            permit_runtime_case_assertions={"summary": {"asserted_family_total": 6, "failed_case_total": 0, "runtime_assertions_ready": True}},
            widget_rental_catalog={"summary": {"permit_claim_packet_family_total": 6, "permit_checksum_sample_family_total": 6, "permit_widget_case_parity_family_total": 6, "permit_partner_demo_surface_ready": True, "permit_partner_binding_sample_total": 6, "permit_partner_binding_surface_ready": True}},
            api_contract_spec={"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"family_case_goldset_family_total": 6, "partner_demo_surface_ready": True, "partner_binding_sample_total": 6, "partner_binding_surface_ready": True}}}}}}},
            permit_case_release_guard={"summary": {"family_total": 6, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}},
            permit_review_case_presets={"summary": {"preset_total": 24, "preset_family_total": 6, "preset_ready": True}},
            permit_case_story_surface={"summary": {"story_family_total": 6, "review_reason_total": 4, "manual_review_family_total": 6, "story_ready": True}},
            permit_preset_story_release_guard={"summary": {"preset_story_guard_ready": True, "runtime_review_preset_surface_ready": True, "runtime_case_story_surface_ready": True, "story_contract_parity_ready": True}},
            permit_operator_demo_packet={"summary": {"operator_demo_ready": True, "family_total": 6, "demo_case_total": 24, "prompt_case_binding_total": 6}},
            permit_review_reason_decision_ladder={"summary": {"review_reason_total": 4, "manual_review_gate_total": 1, "prompt_bound_reason_total": 4, "decision_ladder_ready": True}},
            permit_thinking_prompt_bundle_packet={"summary": {"packet_ready": True, "prompt_section_total": 9, "operator_jump_case_total": 24, "decision_ladder_row_total": 4, "runtime_target_ready": True, "release_target_ready": True, "operator_target_ready": True}},
            permit_partner_binding_observability={"summary": {"observability_ready": True, "expected_family_total": 6, "widget_binding_family_total": 6, "api_binding_family_total": 6, "widget_missing_family_total": 0, "api_missing_family_total": 0}},
            permit_partner_gap_preview_digest={"summary": {"digest_ready": True, "blank_binding_preset_total": 0, "widget_preset_mismatch_total": 0, "api_preset_mismatch_total": 0}},
            permit_demo_surface_observability={"summary": {"observability_ready": True, "critical_prompt_compact_lens_ready": True, "critical_prompt_runtime_contract_ready": True, "critical_prompt_release_contract_ready": True, "critical_prompt_operator_contract_ready": True, "surface_health_digest_ready": True}},
            permit_surface_drift_digest={"summary": {"digest_ready": True, "delta_ready": True, "changed_surface_total": 0, "readiness_flip_total": 0, "reasoning_changed_surface_total": 0, "reasoning_regression_total": 0}},
            permit_runtime_reasoning_guard={"summary": {"guard_ready": True, "binding_gap_total": 0, "missing_binding_reason_total": 0}},
            permit_closed_lane_stale_audit={"summary": {"audit_ready": True, "closed_lane_id": "runtime_reasoning_guard", "stale_reference_total": 0, "stale_artifact_total": 0, "stale_primary_lane_total": 0, "stale_system_bottleneck_total": 0, "stale_prompt_bundle_lane_total": 0}},
            runtime_html="""
            <div id="proofClaimBox"></div>
            <div id="reviewPresetBox"></div>
            <div id="operatorDemoBox"></div>
            <div id="runtimeReasoningCardBox"></div>
            <script>
            const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
            const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
            const applyReviewCasePreset = (preset) => { return preset; };
            const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
            const getOperatorDemoSurface = (row) => (row.operator_demo_surface);
            const renderRuntimeReasoningCard = (industry, typedEval, context = {}) => { return [industry, typedEval, context]; };
            const promptBindingMarker = "prompt_case_binding";
            const promptBindingButton = "data-prompt-preset-id";
            const criticalPromptMarker = "runtime_critical_prompt_excerpt";
            const reviewPresetButton = "data-review-preset-id";
            const reasoningPresetButton = "data-runtime-preset-id";
            const reasoningLadderMap = "runtime_reasoning_ladder_map";
            </script>
            """,
            prompt_doc="# prompt",
        )

        self.assertTrue(report["summary"]["closed_lane_stale_audit_ready"])
        self.assertEqual(report["summary"]["closed_lane_stale_reference_total"], 0)
        self.assertTrue(report["summary"]["capital_registration_logic_packet_ready"])
        self.assertEqual(report["summary"]["capital_evidence_missing_total"], 50)
        self.assertEqual(report["summary"]["technical_evidence_missing_total"], 8)
        self.assertEqual(report["summary"]["other_evidence_missing_total"], 1)
        self.assertEqual(report["summary"]["capital_registration_primary_gap_id"], "capital_evidence_backfill")
        self.assertEqual(report["current_execution_lane"]["id"], "capital_registration_logic_lock")
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "capital_registration_logic_brainstorm")

    def test_build_brainstorm_uses_family_threshold_formula_guard_when_evidence_gaps_are_closed(self):
        report = generate_permit_next_action_brainstorm.build_brainstorm(
            master_catalog={"summary": {"master_industry_total": 51, "master_focus_registry_row_total": 50}, "industries": []},
            provenance_audit={"summary": {"focus_family_registry_row_total": 50, "focus_seed_row_total": 0, "focus_family_registry_missing_raw_source_proof_total": 0, "candidate_pack_total": 0, "master_inferred_overlay_total": 0}},
            focus_report={"summary": {"real_focus_target_total": 51}},
            permit_capital_registration_logic_packet={"summary": {"packet_ready": True, "focus_target_total": 51, "family_total": 7, "capital_evidence_missing_total": 0, "technical_evidence_missing_total": 0, "other_evidence_missing_total": 0, "brainstorm_candidate_total": 1, "primary_gap_id": "family_threshold_formula_guard", "threshold_spread_family_total": 2, "threshold_spread_row_total": 42, "threshold_spread_top_service_code": "FOCUS::construction-general-geonchuk"}},
            source_upgrade_backlog={"summary": {"focus_seed_group_total": 0, "absorbed_group_total": 0}},
            permit_patent_evidence_bundle={"summary": {"focus_source_family_total": 7, "claim_packet_family_total": 7, "claim_packet_complete_family_total": 7, "checksum_sample_family_total": 7}},
            permit_family_case_goldset={"summary": {"goldset_complete_family_total": 7, "case_total": 42, "edge_case_total": 21, "edge_case_family_total": 7, "manual_review_case_total": 6}},
            permit_runtime_case_assertions={"summary": {"asserted_family_total": 7, "failed_case_total": 0, "runtime_assertions_ready": True}},
            widget_rental_catalog={"summary": {"permit_claim_packet_family_total": 7, "permit_checksum_sample_family_total": 7, "permit_widget_case_parity_family_total": 7, "permit_partner_demo_surface_ready": True, "permit_partner_binding_sample_total": 7, "permit_partner_binding_surface_ready": True}},
            api_contract_spec={"services": {"permit": {"response_contract": {"catalog_contracts": {"master_catalog": {"current_summary": {"family_case_goldset_family_total": 7, "partner_demo_surface_ready": True, "partner_binding_sample_total": 7, "partner_binding_surface_ready": True}}}}}}},
            permit_case_release_guard={"summary": {"family_total": 7, "runtime_failed_case_total": 0, "runtime_missing_case_total": 0, "widget_missing_case_total": 0, "api_missing_case_total": 0, "runtime_extra_case_total": 0, "widget_extra_case_total": 0, "api_extra_case_total": 0, "release_guard_ready": True}},
            permit_review_case_presets={"summary": {"preset_total": 28, "preset_family_total": 7, "preset_ready": True}},
            permit_case_story_surface={"summary": {"story_family_total": 7, "review_reason_total": 5, "manual_review_family_total": 6, "story_ready": True}},
            permit_preset_story_release_guard={"summary": {"preset_story_guard_ready": True, "runtime_review_preset_surface_ready": True, "runtime_case_story_surface_ready": True, "story_contract_parity_ready": True}},
            permit_operator_demo_packet={"summary": {"operator_demo_ready": True, "family_total": 7, "demo_case_total": 28, "prompt_case_binding_total": 7}},
            permit_review_reason_decision_ladder={"summary": {"review_reason_total": 5, "manual_review_gate_total": 1, "prompt_bound_reason_total": 5, "decision_ladder_ready": True}},
            permit_thinking_prompt_bundle_packet={"summary": {"packet_ready": True, "prompt_section_total": 9, "operator_jump_case_total": 28, "decision_ladder_row_total": 5, "runtime_target_ready": True, "release_target_ready": True, "operator_target_ready": True}},
            permit_partner_binding_observability={"summary": {"observability_ready": True, "expected_family_total": 7, "widget_binding_family_total": 7, "api_binding_family_total": 7, "widget_missing_family_total": 0, "api_missing_family_total": 0}},
            permit_partner_gap_preview_digest={"summary": {"digest_ready": True, "blank_binding_preset_total": 0, "widget_preset_mismatch_total": 0, "api_preset_mismatch_total": 0}},
            permit_demo_surface_observability={"summary": {"observability_ready": True, "critical_prompt_compact_lens_ready": True, "critical_prompt_runtime_contract_ready": True, "critical_prompt_release_contract_ready": True, "critical_prompt_operator_contract_ready": True, "surface_health_digest_ready": True}},
            permit_surface_drift_digest={"summary": {"digest_ready": True, "delta_ready": True, "changed_surface_total": 0, "readiness_flip_total": 0, "reasoning_changed_surface_total": 0, "reasoning_regression_total": 0}},
            permit_runtime_reasoning_guard={"summary": {"guard_ready": True, "binding_gap_total": 0, "missing_binding_reason_total": 0}},
            permit_closed_lane_stale_audit={"summary": {"audit_ready": True, "closed_lane_id": "runtime_reasoning_guard", "stale_reference_total": 0, "stale_artifact_total": 0, "stale_primary_lane_total": 0, "stale_system_bottleneck_total": 0, "stale_prompt_bundle_lane_total": 0}},
            runtime_html="""
            <div id="proofClaimBox"></div>
            <div id="reviewPresetBox"></div>
            <div id="operatorDemoBox"></div>
            <div id="runtimeReasoningCardBox"></div>
            <script>
            const renderProofClaim = (industry) => { const x = industry.claim_packet_summary; return x; };
            const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
            const applyReviewCasePreset = (preset) => { return preset; };
            const renderOperatorDemoSurface = (industry) => { return industry.operator_demo_surface; };
            const getOperatorDemoSurface = (row) => (row.operator_demo_surface);
            const renderRuntimeReasoningCard = (industry, typedEval, context = {}) => { return [industry, typedEval, context]; };
            const promptBindingMarker = "prompt_case_binding";
            const promptBindingButton = "data-prompt-preset-id";
            const criticalPromptMarker = "runtime_critical_prompt_excerpt";
            const reviewPresetButton = "data-review-preset-id";
            const reasoningPresetButton = "data-runtime-preset-id";
            const reasoningLadderMap = "runtime_reasoning_ladder_map";
            </script>
            """,
            prompt_doc="# prompt",
        )

        self.assertEqual(report["summary"]["capital_registration_primary_gap_id"], "family_threshold_formula_guard")
        self.assertEqual(report["summary"]["capital_registration_brainstorm_candidate_total"], 1)
        self.assertEqual(report["current_execution_lane"]["id"], "capital_registration_logic_lock")
        self.assertIn("subtype", report["current_execution_lane"]["current_gap"])
        self.assertIn("FOCUS::construction-general-geonchuk", report["current_execution_lane"]["proposed_next_step"])
        self.assertEqual(report["parallel_brainstorm_lane"]["id"], "capital_registration_logic_brainstorm")
        self.assertIn("threshold", report["parallel_brainstorm_lane"]["proposed_next_step"])
        self.assertIn("FOCUS::construction-general-geonchuk", report["parallel_brainstorm_lane"]["proposed_next_step"])


if __name__ == "__main__":
    unittest.main()
