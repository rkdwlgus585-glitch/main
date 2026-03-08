import unittest

from scripts import generate_permit_preset_story_release_guard


class GeneratePermitPresetStoryReleaseGuardTests(unittest.TestCase):
    def test_build_guard_passes_when_runtime_widget_and_api_cover_story_surface(self):
        runtime_html = """
        <div id="reviewPresetBox"></div>
        <div id="caseStoryBox"></div>
        <script>
        const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
        const applyReviewCasePreset = (preset) => { return preset; };
        const renderCaseStorySurface = (industry) => { return industry.case_story_surface; };
        const presetMarker = "data-review-preset-id";
        const storyMarker = "operator_story_points";
        </script>
        """
        review_case_presets = {
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "presets": [
                        {"preset_id": "preset-1"},
                        {"preset_id": "preset-2"},
                    ],
                }
            ]
        }
        case_story_surface = {
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "representative_cases": [
                        {"preset_id": "preset-1", "review_reason": "capital_shortfall_only"},
                        {"preset_id": "preset-2", "review_reason": "technician_shortfall_only"},
                    ],
                }
            ]
        }
        widget_catalog = {
            "packaging": {
                "partner_rental": {
                    "permit_widget_feeds": {
                        "case_story_samples": [
                            {
                                "family_key": "건설산업기본법 시행령",
                                "representative_preset_ids": ["preset-1", "preset-2"],
                                "review_reasons": ["capital_shortfall_only", "technician_shortfall_only"],
                            }
                        ]
                    }
                }
            }
        }
        api_contract = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "proof_surface_examples": {
                                    "case_story_samples": [
                                        {
                                            "family_key": "건설산업기본법 시행령",
                                            "representative_preset_ids": ["preset-1", "preset-2"],
                                            "review_reasons": ["capital_shortfall_only", "technician_shortfall_only"],
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        }

        report = generate_permit_preset_story_release_guard.build_preset_story_release_guard(
            runtime_html=runtime_html,
            permit_review_case_presets=review_case_presets,
            permit_case_story_surface=case_story_surface,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract,
        )

        self.assertTrue(report["summary"]["runtime_review_preset_surface_ready"])
        self.assertTrue(report["summary"]["runtime_case_story_surface_ready"])
        self.assertTrue(report["summary"]["story_contract_parity_ready"])
        self.assertTrue(report["summary"]["preset_story_guard_ready"])

    def test_build_guard_fails_when_widget_story_surface_drops_a_preset_id(self):
        runtime_html = """
        <div id="reviewPresetBox"></div>
        <div id="caseStoryBox"></div>
        <script>
        const renderReviewCasePresets = (industry) => { return industry.review_case_presets; };
        const applyReviewCasePreset = (preset) => { return preset; };
        const renderCaseStorySurface = (industry) => { return industry.case_story_surface; };
        const presetMarker = "data-review-preset-id";
        const storyMarker = "operator_story_points";
        </script>
        """
        review_case_presets = {
            "families": [
                {
                    "family_key": "정보통신공사업법 시행령",
                    "presets": [{"preset_id": "preset-1"}],
                }
            ]
        }
        case_story_surface = {
            "families": [
                {
                    "family_key": "정보통신공사업법 시행령",
                    "representative_cases": [{"preset_id": "preset-1", "review_reason": "capital_shortfall_only"}],
                }
            ]
        }
        widget_catalog = {
            "packaging": {
                "partner_rental": {
                    "permit_widget_feeds": {
                        "case_story_samples": [
                            {
                                "family_key": "정보통신공사업법 시행령",
                                "representative_preset_ids": [],
                                "review_reasons": ["capital_shortfall_only"],
                            }
                        ]
                    }
                }
            }
        }
        api_contract = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "proof_surface_examples": {
                                    "case_story_samples": [
                                        {
                                            "family_key": "정보통신공사업법 시행령",
                                            "representative_preset_ids": ["preset-1"],
                                            "review_reasons": ["capital_shortfall_only"],
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        }

        report = generate_permit_preset_story_release_guard.build_preset_story_release_guard(
            runtime_html=runtime_html,
            permit_review_case_presets=review_case_presets,
            permit_case_story_surface=case_story_surface,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract,
        )

        self.assertFalse(report["summary"]["story_contract_parity_ready"])
        self.assertFalse(report["summary"]["preset_story_guard_ready"])
        self.assertEqual(report["missing"]["widget_story_presets"], ["preset-1"])


if __name__ == "__main__":
    unittest.main()
