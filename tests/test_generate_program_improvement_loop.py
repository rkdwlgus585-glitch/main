import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_program_improvement_loop as module


class GenerateProgramImprovementLoopTests(unittest.TestCase):
    def test_main_generates_prioritized_sections(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            operations = base / "operations.json"
            attorney = base / "attorney.json"
            staging = base / "staging.json"
            wp_apply = base / "wp_apply.json"
            wp_verify = base / "wp_verify.json"
            rental = base / "rental.json"
            operations.write_text(
                json.dumps(
                    {
                        "topology": {"main_platform_host": "seoulmna.kr", "listing_market_host": "seoulmna.co.kr"},
                        "decisions": {
                            "seoul_live_decision": "awaiting_live_confirmation",
                            "wp_runtime_decision": "scaffold_ready_runtime_missing",
                            "partner_activation_decision": "awaiting_partner_inputs",
                        },
                        "required_inputs": {
                            "partner_common": [
                                "partner_proof_url",
                                "partner_api_key",
                                "partner_data_source_approval",
                            ]
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            attorney.write_text(
                json.dumps(
                    {
                        "tracks": [
                            {
                                "track_id": "A",
                                "system_id": "yangdo",
                                "title": "Yangdo",
                                "attorney_position": {
                                    "claim_focus": ["비교군 오염 제거", "신뢰도 공개 제어"],
                                    "avoid_in_claims": ["사이트명", "UI 문구"],
                                },
                            },
                            {
                                "track_id": "B",
                                "system_id": "permit",
                                "title": "Permit",
                                "attorney_position": {
                                    "claim_focus": ["규칙카탈로그 매핑", "manual review gate"],
                                    "avoid_in_claims": ["단순 체크리스트 UI", "서류 저장소"],
                                },
                            },
                            {
                                "track_id": "P",
                                "system_id": "platform",
                                "title": "Platform",
                                "attorney_position": {},
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            staging.write_text(json.dumps({"summary": {"cutover_ready": True}}, ensure_ascii=False), encoding="utf-8")
            wp_apply.write_text(json.dumps({"summary": {"bundle_ready": True}}, ensure_ascii=False), encoding="utf-8")
            wp_verify.write_text(json.dumps({"summary": {"verification_ready": False}}, ensure_ascii=False), encoding="utf-8")
            rental.write_text(
                json.dumps(
                    {
                        "summary": {"standard_offering_count": 3, "pro_offering_count": 3},
                        "packaging": {
                            "partner_rental": {
                                "widget_standard": ["yangdo_standard", "permit_standard"],
                                "api_or_detail_pro": ["yangdo_pro", "permit_pro"],
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            json_path = base / "loop.json"
            md_path = base / "loop.md"
            argv = [
                "generate_program_improvement_loop.py",
                "--operations", str(operations),
                "--attorney", str(attorney),
                "--wordpress-staging-apply-plan", str(staging),
                "--wp-surface-lab-apply", str(wp_apply),
                "--wp-surface-lab-page-verify", str(wp_verify),
                "--widget-rental-catalog", str(rental),
                "--json", str(json_path),
                "--md", str(md_path),
            ]
            with patch("sys.argv", argv):
                code = module.main()
            self.assertEqual(code, 0)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["immediate_blocker_count"], 3)
            self.assertTrue(any(item["category"] == "platform_launch" for item in payload["immediate_blockers"]))
            self.assertTrue(any(item["category"] == "patent_yangdo" for item in payload["patent_hardening"]))
            self.assertTrue(any(item["category"] == "rental_packaging" for item in payload["commercialization_gaps"]))
            self.assertGreaterEqual(len(payload["top_next_actions"]), 3)
            self.assertTrue(md_path.exists())

    def test_skips_runtime_blocker_when_pages_are_verified(self):
        priorities = module._build_priorities(
            operations={
                "topology": {"main_platform_host": "seoulmna.kr", "listing_market_host": "seoulmna.co.kr"},
                "decisions": {
                    "seoul_live_decision": "awaiting_live_confirmation",
                    "wp_runtime_decision": "runtime_running",
                    "wp_surface_apply_decision": "verified",
                    "partner_activation_decision": "ready",
                },
                "required_inputs": {"partner_common": []},
            },
            attorney={"tracks": []},
            staging_apply={"summary": {"cutover_ready": True}},
            wp_apply={"summary": {"bundle_ready": True}},
            wp_verify={"summary": {"verification_ready": True, "verification_ok": True}},
            widget_catalog={"summary": {"standard_offering_count": 3, "pro_offering_count": 3}, "packaging": {"partner_rental": {"widget_standard": [], "api_or_detail_pro": []}}},
            operations_path=Path("ops.json"),
            attorney_path=Path("attorney.json"),
            staging_apply_path=Path("staging.json"),
            wp_apply_path=Path("apply.json"),
            wp_verify_path=Path("verify.json"),
            widget_catalog_path=Path("catalog.json"),
        )

        self.assertEqual(priorities["summary"]["immediate_blocker_count"], 1)
        self.assertTrue(priorities["summary"]["wp_runtime_ready"])
        self.assertTrue(priorities["summary"]["wp_page_verification_ok"])
        self.assertFalse(any(item["category"] == "wordpress_runtime" for item in priorities["immediate_blockers"]))


if __name__ == "__main__":
    unittest.main()
