import unittest

from scripts.generate_permit_capital_registration_logic_packet import build_packet


class GeneratePermitCapitalRegistrationLogicPacketTests(unittest.TestCase):
    def test_build_packet_surfaces_evidence_gaps_and_candidates(self):
        master_catalog = {
            "industries": [
                {
                    "service_code": "FOCUS::alpha",
                    "service_name": "Alpha",
                    "law_title": "Family A",
                    "registration_requirement_profile": {
                        "focus_target": True,
                        "capital_required": True,
                        "capital_eok": 5.0,
                        "technical_personnel_required": True,
                        "technicians_required": 3,
                        "other_required": True,
                        "capital_evidence": [],
                        "technical_personnel_evidence": ["tech line"],
                        "other_evidence": [],
                    },
                },
                {
                    "service_code": "FOCUS::beta",
                    "service_name": "Beta",
                    "law_title": "Family B",
                    "registration_requirement_profile": {
                        "focus_target": True,
                        "capital_required": True,
                        "capital_eok": 1.0,
                        "technical_personnel_required": True,
                        "technicians_required": 1,
                        "other_required": False,
                        "capital_evidence": ["capital line"],
                        "technical_personnel_evidence": [],
                        "other_evidence": [],
                    },
                },
            ]
        }
        focus_report = {
            "summary": {
                "focus_target_total": 2,
                "real_focus_target_total": 2,
            }
        }

        packet = build_packet(master_catalog=master_catalog, focus_report=focus_report)
        summary = packet["summary"]

        self.assertTrue(summary["packet_ready"])
        self.assertEqual(summary["focus_target_total"], 2)
        self.assertEqual(summary["family_total"], 2)
        self.assertEqual(summary["with_other_total"], 1)
        self.assertEqual(summary["core_only_total"], 1)
        self.assertEqual(summary["capital_evidence_missing_total"], 1)
        self.assertEqual(summary["technical_evidence_missing_total"], 1)
        self.assertEqual(summary["other_evidence_missing_total"], 1)
        self.assertEqual(summary["capital_min_eok"], 1.0)
        self.assertEqual(summary["capital_max_eok"], 5.0)
        self.assertEqual(summary["technicians_min"], 1)
        self.assertEqual(summary["technicians_max"], 3)
        self.assertEqual(summary["brainstorm_candidate_total"], 4)
        self.assertEqual(summary["primary_gap_total"], 1)

        family_gaps = packet["family_gaps"]
        self.assertEqual(family_gaps[0]["family_key"], "Family A")
        self.assertEqual(family_gaps[0]["capital_evidence_missing_total"], 1)
        self.assertEqual(family_gaps[0]["other_evidence_missing_total"], 1)
        self.assertEqual(family_gaps[1]["family_key"], "Family B")
        self.assertEqual(family_gaps[1]["technical_evidence_missing_total"], 1)

        candidate_ids = [item["candidate_id"] for item in packet["brainstorm_candidates"]]
        self.assertIn("capital_evidence_backfill", candidate_ids)
        self.assertIn("technical_evidence_backfill", candidate_ids)
        self.assertIn("other_requirement_evidence_backfill", candidate_ids)
        self.assertIn("core_only_boundary_guard", candidate_ids)

    def test_build_packet_closes_core_only_candidate_when_runtime_guard_exists(self):
        packet = build_packet(
            master_catalog={
                "industries": [
                    {
                        "service_code": "09_27_03_P",
                        "service_name": "제재업",
                        "law_title": "목재의 지속가능한 이용에 관한 법률 시행령",
                        "registration_requirement_profile": {
                            "focus_target": True,
                            "capital_required": True,
                            "capital_eok": 0.3,
                            "technical_personnel_required": True,
                            "technicians_required": 1,
                            "other_required": False,
                            "capital_evidence": ["capital line"],
                            "technical_personnel_evidence": ["tech line"],
                            "other_evidence": [],
                        },
                    }
                ]
            },
            focus_report={"summary": {"focus_target_total": 1, "real_focus_target_total": 1}},
            runtime_case_assertions={
                "families": [
                    {
                        "family_key": "목재의 지속가능한 이용에 관한 법률 시행령",
                        "cases": [
                            {
                                "service_code": "09_27_03_P",
                                "case_kind": "document_missing_review",
                                "expected_status": "pass",
                                "actual_status": "pass",
                                "ok": True,
                            }
                        ],
                    }
                ]
            },
        )

        summary = packet["summary"]
        self.assertEqual(summary["core_only_total"], 1)
        self.assertEqual(summary["core_only_guarded_total"], 1)
        candidate_ids = [item["candidate_id"] for item in packet["brainstorm_candidates"]]
        self.assertNotIn("core_only_boundary_guard", candidate_ids)

    def test_build_packet_adds_threshold_formula_candidate_when_evidence_is_complete(self):
        packet = build_packet(
            master_catalog={
                "industries": [
                    {
                        "service_code": "FOCUS::alpha-1",
                        "service_name": "Alpha 1",
                        "law_title": "Family Spread",
                        "registration_requirement_profile": {
                            "focus_target": True,
                            "capital_required": True,
                            "capital_eok": 1.5,
                            "technical_personnel_required": True,
                            "technicians_required": 2,
                            "other_required": True,
                            "capital_evidence": ["capital line"],
                            "technical_personnel_evidence": ["tech line"],
                            "other_evidence": ["other line"],
                        },
                    },
                    {
                        "service_code": "FOCUS::alpha-2",
                        "service_name": "Alpha 2",
                        "law_title": "Family Spread",
                        "registration_requirement_profile": {
                            "focus_target": True,
                            "capital_required": True,
                            "capital_eok": 8.5,
                            "technical_personnel_required": True,
                            "technicians_required": 12,
                            "other_required": True,
                            "capital_evidence": ["capital line"],
                            "technical_personnel_evidence": ["tech line"],
                            "other_evidence": ["other line"],
                        },
                    },
                ]
            },
            focus_report={"summary": {"focus_target_total": 2, "real_focus_target_total": 2}},
            runtime_case_assertions={"families": []},
        )

        summary = packet["summary"]
        self.assertEqual(summary["capital_evidence_missing_total"], 0)
        self.assertEqual(summary["technical_evidence_missing_total"], 0)
        self.assertEqual(summary["other_evidence_missing_total"], 0)
        self.assertEqual(summary["threshold_spread_family_total"], 1)
        self.assertEqual(summary["threshold_spread_row_total"], 2)
        self.assertEqual(summary["threshold_spread_priority_family_total"], 1)
        self.assertEqual(summary["threshold_spread_top_service_code"], "FOCUS::alpha-1")
        self.assertEqual(summary["brainstorm_candidate_total"], 1)
        self.assertEqual(summary["primary_gap_id"], "family_threshold_formula_guard")

        candidate = packet["brainstorm_candidates"][0]
        self.assertEqual(candidate["candidate_id"], "family_threshold_formula_guard")
        self.assertEqual(candidate["affected_total"], 2)
        self.assertIn("FOCUS::alpha-1", candidate["next_action"])
        self.assertEqual(packet["threshold_spread_priority"][0]["sample_service_codes"][0], "FOCUS::alpha-1")


if __name__ == "__main__":
    unittest.main()
