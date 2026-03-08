import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_co_listing_bridge_apply_packet import build_co_listing_bridge_apply_packet


class GenerateCoListingBridgeApplyPacketTests(unittest.TestCase):
    def test_build_packet_aggregates_verified_assets(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            policy = base / "policy.json"
            snippets = base / "snippets.json"
            operator = base / "operator.json"
            plan = base / "plan.json"
            bundle = base / "bundle.json"

            policy.write_text(
                json.dumps(
                    {
                        "summary": {"listing_host": "seoulmna.co.kr", "platform_host": "seoulmna.kr"},
                        "ctas": [
                            {"placement": "listing_nav_service", "target_service": "yangdo", "target_url": "https://seoulmna.kr/yangdo", "copy": "AI valuation"},
                            {"placement": "listing_detail_primary", "target_service": "yangdo", "target_url": "https://seoulmna.kr/yangdo", "copy": "Open valuation"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            snippets.write_text(
                json.dumps(
                    {
                        "files": [
                            {"placement": "listing_nav_service", "path": str(base / "listing_nav_service.html")},
                            {"placement": "listing_detail_primary", "path": str(base / "listing_detail_primary.html")},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            operator.write_text(
                json.dumps(
                    {
                        "summary": {"checklist_ready": True, "css_file": str(base / "bridge.css")},
                        "placements": [
                            {"placement": "listing_nav_service", "location_hint": "global nav", "validation_hint": "link to .kr"},
                            {"placement": "listing_detail_primary", "location_hint": "detail top", "validation_hint": "link to .kr"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            plan.write_text(
                json.dumps(
                    {
                        "summary": {"plan_ready": True, "strict_live_ready": True},
                        "placements": [
                            {"placement": "listing_nav_service", "selector": "header#header ul.gnb", "selector_verified": True, "snippet_file": str(base / "listing_nav_service.html")},
                            {"placement": "listing_detail_primary", "selector": "article#bo_v .tbl_frm01.vtbl_wraps", "selector_verified": True, "snippet_file": str(base / "listing_detail_primary.html")},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            bundle.write_text(
                json.dumps(
                    {
                        "summary": {"bundle_ready": True, "output_dir": str(base / "bundle")},
                        "files": [
                            {"kind": "script", "path": str(base / "bundle" / "bridge.js")},
                            {"kind": "manifest", "path": str(base / "bundle" / "manifest.json")},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_co_listing_bridge_apply_packet(
                policy_path=policy,
                snippets_path=snippets,
                operator_path=operator,
                plan_path=plan,
                bundle_path=bundle,
            )

            self.assertTrue(payload["summary"]["apply_ready"])
            self.assertTrue(payload["summary"]["artifact_ready"])
            self.assertTrue(payload["summary"]["strict_live_ready"])
            self.assertEqual(payload["summary"]["placement_count"], 2)
            self.assertEqual(payload["summary"]["placement_asset_ready_count"], 2)
            self.assertEqual(payload["summary"]["placement_ready_count"], 2)
            self.assertIn("bridge.js", payload["summary"]["bundle_script"])
            self.assertEqual(len(payload["apply_order"]), 5)


if __name__ == "__main__":
    unittest.main()
