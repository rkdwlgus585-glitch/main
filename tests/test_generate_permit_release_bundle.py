import unittest

from scripts import generate_permit_release_bundle


class GeneratePermitReleaseBundleTests(unittest.TestCase):
    def test_build_step_specs_keeps_master_before_widget_and_api(self):
        steps = generate_permit_release_bundle.build_step_specs("py")
        names = [row["name"] for row in steps]

        self.assertEqual(names[0], "permit_focus_seed_catalog")
        self.assertLess(names.index("permit_focus_seed_catalog"), names.index("permit_focus_source_upgrade_packet"))
        self.assertLess(names.index("permit_focus_source_upgrade_packet"), names.index("permit_focus_family_registry"))
        self.assertLess(names.index("permit_focus_family_registry"), names.index("permit_precheck_html"))
        self.assertLess(names.index("permit_master_catalog"), names.index("permit_provenance_audit"))
        self.assertLess(names.index("permit_provenance_audit"), names.index("permit_source_upgrade_backlog"))
        self.assertLess(names.index("permit_source_upgrade_backlog"), names.index("permit_patent_evidence_bundle"))
        self.assertLess(names.index("permit_patent_evidence_bundle"), names.index("permit_family_case_goldset"))
        self.assertLess(names.index("permit_family_case_goldset"), names.index("permit_runtime_case_assertions"))
        self.assertLess(names.index("permit_runtime_case_assertions"), names.index("permit_review_case_presets"))
        self.assertLess(names.index("permit_review_case_presets"), names.index("permit_case_story_surface"))
        self.assertLess(names.index("permit_case_story_surface"), names.index("permit_operator_demo_packet"))
        self.assertLess(names.index("permit_operator_demo_packet"), names.index("widget_rental_catalog"))
        self.assertLess(names.index("widget_rental_catalog"), names.index("api_contract_spec"))
        self.assertLess(names.index("api_contract_spec"), names.index("permit_case_release_guard"))
        self.assertLess(names.index("permit_case_release_guard"), names.index("permit_preset_story_release_guard"))
        self.assertLess(names.index("permit_operator_demo_packet"), names.index("permit_next_action_brainstorm"))
        self.assertLess(names.index("permit_provenance_audit"), names.index("widget_rental_catalog"))
        self.assertLess(names.index("permit_master_catalog"), names.index("widget_rental_catalog"))
        self.assertLess(names.index("permit_master_catalog"), names.index("api_contract_spec"))

    def test_build_manifest_marks_release_ready_when_all_steps_pass(self):
        manifest = generate_permit_release_bundle.build_manifest(
            python_executable="py",
            step_results=[
                {"name": "permit_master_catalog", "ok": True, "returncode": 0},
                {"name": "widget_rental_catalog", "ok": True, "returncode": 0},
            ],
            case_release_guard_report={
                "summary": {
                    "release_guard_ready": True,
                    "family_total": 6,
                    "case_total": 36,
                    "runtime_failed_case_total": 0,
                    "runtime_missing_case_total": 0,
                    "widget_missing_case_total": 0,
                    "api_missing_case_total": 0,
                    "runtime_extra_case_total": 0,
                    "widget_extra_case_total": 0,
                    "api_extra_case_total": 0,
                },
                "missing": {},
            },
            review_case_presets_report={
                "summary": {
                    "preset_ready": True,
                    "preset_total": 18,
                    "manual_review_expected_total": 6,
                }
            },
            case_story_surface_report={
                "summary": {
                    "story_ready": True,
                    "story_family_total": 6,
                    "review_reason_total": 3,
                    "manual_review_family_total": 6,
                }
            },
            preset_story_release_guard_report={
                "summary": {
                    "preset_story_guard_ready": True,
                    "runtime_review_preset_surface_ready": True,
                    "runtime_case_story_surface_ready": True,
                    "story_contract_parity_ready": True,
                }
            },
            operator_demo_packet_report={
                "summary": {
                    "operator_demo_ready": True,
                    "family_total": 6,
                    "demo_case_total": 18,
                }
            },
        )

        self.assertTrue(manifest["summary"]["release_ready"])
        self.assertEqual(manifest["summary"]["failed_total"], 0)
        self.assertEqual(manifest["summary"]["ok_total"], 2)
        self.assertTrue(manifest["summary"]["case_release_guard_ready"])
        self.assertEqual(manifest["summary"]["case_release_guard_family_total"], 6)
        self.assertEqual(manifest["summary"]["case_release_guard_case_total"], 36)
        self.assertEqual(manifest["summary"]["case_release_guard_failed_total"], 0)
        self.assertTrue(manifest["summary"]["case_release_guard_preview_ready"])
        self.assertEqual(manifest["summary"]["review_case_preset_total"], 18)
        self.assertEqual(manifest["summary"]["review_case_manual_review_total"], 6)
        self.assertEqual(manifest["summary"]["case_story_family_total"], 6)
        self.assertEqual(manifest["summary"]["case_story_review_reason_total"], 3)
        self.assertEqual(manifest["summary"]["case_story_manual_review_family_total"], 6)
        self.assertTrue(manifest["summary"]["preset_story_release_guard_ready"])
        self.assertTrue(manifest["summary"]["runtime_review_preset_surface_ready"])
        self.assertTrue(manifest["summary"]["runtime_case_story_surface_ready"])
        self.assertTrue(manifest["summary"]["story_contract_parity_ready"])
        self.assertTrue(manifest["summary"]["operator_demo_ready"])
        self.assertEqual(manifest["summary"]["operator_demo_family_total"], 6)
        self.assertEqual(manifest["summary"]["operator_demo_case_total"], 18)
        self.assertFalse(manifest["summary"]["operator_demo_release_surface_ready"])
        self.assertFalse(manifest["summary"]["partner_demo_surface_ready"])
        self.assertTrue(manifest["summary"]["critical_prompt_doc_ready"])

    def test_build_manifest_marks_first_failure_as_blocking(self):
        manifest = generate_permit_release_bundle.build_manifest(
            python_executable="py",
            step_results=[
                {"name": "permit_master_catalog", "ok": True, "returncode": 0},
                {"name": "widget_rental_catalog", "ok": False, "returncode": 1},
                {"name": "api_contract_spec", "ok": True, "returncode": 0},
            ],
        )

        self.assertFalse(manifest["summary"]["release_ready"])
        self.assertEqual(manifest["summary"]["failed_total"], 1)
        self.assertEqual(manifest["summary"]["blocking_failure_name"], "widget_rental_catalog")

    def test_build_manifest_includes_partner_qa_snapshot_preview(self):
        manifest = generate_permit_release_bundle.build_manifest(
            python_executable="py",
            step_results=[{"name": "permit_case_release_guard", "ok": True, "returncode": 0}],
            case_release_guard_report={
                "summary": {
                    "release_guard_ready": False,
                    "family_total": 6,
                    "case_total": 36,
                    "runtime_failed_case_total": 1,
                    "runtime_missing_case_total": 1,
                    "widget_missing_case_total": 0,
                    "api_missing_case_total": 2,
                    "runtime_extra_case_total": 0,
                    "widget_extra_case_total": 0,
                    "api_extra_case_total": 0,
                },
                "missing": {
                    "runtime_cases": ["case-r1"],
                    "widget_cases": [],
                    "api_cases": ["case-a1", "case-a2"],
                },
            },
            review_case_presets_report={
                "summary": {
                    "preset_ready": True,
                    "preset_total": 18,
                    "manual_review_expected_total": 6,
                }
            },
            case_story_surface_report={
                "summary": {
                    "story_ready": True,
                    "story_family_total": 6,
                    "review_reason_total": 3,
                    "manual_review_family_total": 6,
                }
            },
            preset_story_release_guard_report={
                "summary": {
                    "preset_story_guard_ready": True,
                    "runtime_review_preset_surface_ready": True,
                    "runtime_case_story_surface_ready": True,
                    "story_contract_parity_ready": True,
                }
            },
            operator_demo_packet_report={
                "summary": {
                    "operator_demo_ready": True,
                    "family_total": 6,
                    "demo_case_total": 18,
                }
            },
        )

        self.assertEqual(manifest["partner_qa_snapshot"]["failed_total"], 4)
        self.assertEqual(manifest["partner_qa_snapshot"]["review_case_preset_total"], 18)
        self.assertEqual(manifest["partner_qa_snapshot"]["case_story_family_total"], 6)
        self.assertEqual(manifest["partner_qa_snapshot"]["case_story_review_reason_total"], 3)
        self.assertEqual(manifest["partner_qa_snapshot"]["case_story_manual_review_family_total"], 6)
        self.assertTrue(manifest["partner_qa_snapshot"]["preset_story_release_guard_ready"])
        self.assertTrue(manifest["partner_qa_snapshot"]["runtime_review_preset_surface_ready"])
        self.assertTrue(manifest["partner_qa_snapshot"]["runtime_case_story_surface_ready"])
        self.assertTrue(manifest["partner_qa_snapshot"]["story_contract_parity_ready"])
        self.assertTrue(manifest["partner_qa_snapshot"]["operator_demo_ready"])
        self.assertEqual(manifest["partner_qa_snapshot"]["operator_demo_family_total"], 6)
        self.assertEqual(manifest["partner_qa_snapshot"]["operator_demo_case_total"], 18)
        self.assertFalse(manifest["partner_qa_snapshot"]["operator_demo_release_surface_ready"])
        self.assertFalse(manifest["partner_qa_snapshot"]["partner_demo_surface_ready"])
        self.assertTrue(manifest["partner_qa_snapshot"]["critical_prompt_doc_ready"])
        self.assertEqual(manifest["partner_qa_snapshot"]["runtime_missing_cases"], ["case-r1"])
        self.assertEqual(manifest["partner_qa_snapshot"]["api_missing_cases"], ["case-a1", "case-a2"])


if __name__ == "__main__":
    unittest.main()
