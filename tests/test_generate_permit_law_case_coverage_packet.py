import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_permit_law_case_coverage_packet import build_permit_law_case_coverage_packet


class GeneratePermitLawCaseCoveragePacketTests(unittest.TestCase):
    def test_build_packet_reports_green_when_law_case_chain_is_complete(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            expanded = base / "expanded.json"
            provenance = base / "provenance.json"
            family = base / "family.json"
            goldset = base / "goldset.json"
            presets = base / "presets.json"
            story = base / "story.json"
            binding = base / "binding.json"

            expanded.write_text(
                json.dumps(
                    {
                        "summary": {
                            "real_industry_total": 195,
                            "real_with_legal_basis_total": 195,
                            "real_with_registration_criteria_total": 195,
                            "pending_industry_total": 0,
                            "rule_pack_total": 54,
                        },
                        "requirement_focus_summary": {
                            "capital_and_technical_with_other_total": 50,
                        },
                        "quality_audit": {
                            "manual_scope_override_total": 2,
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            provenance.write_text(
                json.dumps(
                    {
                        "summary": {
                            "rows_missing_legal_basis_total": 0,
                            "rows_with_raw_source_proof_total": 50,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            family.write_text(
                json.dumps({"summary": {"family_registry_row_total": 50}}, ensure_ascii=False),
                encoding="utf-8",
            )
            goldset.write_text(
                json.dumps(
                    {
                        "summary": {
                            "goldset_ready": True,
                            "family_total": 6,
                            "case_total": 36,
                            "manual_review_case_total": 6,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            presets.write_text(json.dumps({"summary": {"preset_ready": True}}, ensure_ascii=False), encoding="utf-8")
            story.write_text(json.dumps({"summary": {"story_ready": True}}, ensure_ascii=False), encoding="utf-8")
            binding.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")

            payload = build_permit_law_case_coverage_packet(
                expanded_criteria_path=expanded,
                provenance_audit_path=provenance,
                focus_family_registry_path=family,
                family_case_goldset_path=goldset,
                review_case_presets_path=presets,
                case_story_surface_path=story,
                prompt_case_binding_path=binding,
            )

            summary = payload["summary"]
            self.assertTrue(summary["packet_ready"])
            self.assertTrue(summary["law_basis_coverage_ok"])
            self.assertTrue(summary["criteria_coverage_ok"])
            self.assertTrue(summary["provenance_ok"])
            self.assertTrue(summary["exception_tracking_ready"])
            self.assertTrue(summary["case_goldset_ready"])
            self.assertTrue(summary["story_surface_ready"])
            self.assertTrue(summary["prompt_binding_ready"])
            self.assertEqual(summary["real_industry_total"], 195)
            self.assertEqual(summary["case_total"], 36)
            self.assertEqual(summary["blocker_count"], 0)
            self.assertEqual(payload["blockers"], [])


if __name__ == "__main__":
    unittest.main()
