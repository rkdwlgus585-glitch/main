import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_co_listing_bridge_operator_checklist import build_co_listing_bridge_operator_checklist


class GenerateCoListingBridgeOperatorChecklistTests(unittest.TestCase):
    def test_build_checklist_uses_policy_and_snippet_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            policy = base / "policy.json"
            snippets = base / "snippets.json"

            policy.write_text(
                json.dumps(
                    {
                        "summary": {
                            "listing_host": "seoulmna.co.kr",
                            "platform_host": "seoulmna.kr",
                        },
                        "ctas": [
                            {
                                "placement": "listing_detail_primary",
                                "target_service": "yangdo",
                                "copy": "이 매물 기준 양도가 범위 먼저 보기",
                                "target_url": "https://seoulmna.kr/yangdo?utm_source=co_listing",
                            },
                            {
                                "placement": "listing_nav_permit",
                                "target_service": "permit",
                                "copy": "AI 인허가 사전검토",
                                "target_url": "https://seoulmna.kr/permit?utm_source=co_listing",
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            snippets.write_text(
                json.dumps(
                    {
                        "summary": {
                            "combined_file": str(base / "all-placements.html"),
                        },
                        "files": [
                            {"placement": "styles", "path": str(base / "bridge-snippets.css")},
                            {"placement": "listing_detail_primary", "path": str(base / "listing_detail_primary.html")},
                            {"placement": "listing_nav_permit", "path": str(base / "listing_nav_permit.html")},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_co_listing_bridge_operator_checklist(policy_path=policy, snippets_path=snippets)

            self.assertTrue(payload["summary"]["checklist_ready"])
            self.assertEqual(payload["summary"]["placement_count"], 2)
            self.assertEqual(payload["steps"][0]["asset"], str(base / "bridge-snippets.css"))
            self.assertEqual(payload["placements"][0]["location_hint"], "매물 상세 상단의 첫 번째 주요 CTA 영역")
            self.assertIn("utm_source", payload["validation"]["required_query_keys"])


if __name__ == "__main__":
    unittest.main()
