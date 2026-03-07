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
        self.assertLess(names.index("permit_patent_evidence_bundle"), names.index("widget_rental_catalog"))
        self.assertLess(names.index("widget_rental_catalog"), names.index("api_contract_spec"))
        self.assertLess(names.index("api_contract_spec"), names.index("permit_next_action_brainstorm"))
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
        )

        self.assertTrue(manifest["summary"]["release_ready"])
        self.assertEqual(manifest["summary"]["failed_total"], 0)
        self.assertEqual(manifest["summary"]["ok_total"], 2)

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


if __name__ == "__main__":
    unittest.main()
