import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_co_listing_live_injection_plan import build_co_listing_live_injection_plan


class GenerateCoListingLiveInjectionPlanTests(unittest.TestCase):
    def test_build_plan_verifies_live_selectors(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            policy = base / "policy.json"
            snippets = base / "snippets.json"
            operator = base / "operator.json"
            home = base / "home.html"
            list_html = base / "list.html"
            detail = base / "detail.html"

            policy.write_text(
                json.dumps(
                    {
                        "summary": {"listing_host": "seoulmna.co.kr", "platform_host": "seoulmna.kr"},
                        "ctas": [
                            {"placement": "listing_nav_service", "copy": "AI 양도가", "target_url": "https://seoulmna.kr/yangdo"},
                            {"placement": "listing_nav_permit", "copy": "AI 인허가 사전검토", "target_url": "https://seoulmna.kr/permit"},
                            {"placement": "listing_detail_primary", "copy": "양도가", "target_url": "https://seoulmna.kr/yangdo"},
                            {"placement": "listing_detail_secondary", "copy": "상담", "target_url": "https://seoulmna.kr/consult"},
                            {"placement": "listing_empty_state", "copy": "안내 보기", "target_url": "https://seoulmna.kr/mna-market"},
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
                            {"placement": "listing_nav_permit", "path": str(base / "listing_nav_permit.html")},
                            {"placement": "listing_detail_primary", "path": str(base / "listing_detail_primary.html")},
                            {"placement": "listing_detail_secondary", "path": str(base / "listing_detail_secondary.html")},
                            {"placement": "listing_empty_state", "path": str(base / "listing_empty_state.html")},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            operator.write_text(json.dumps({"summary": {"checklist_ready": True}}, ensure_ascii=False), encoding="utf-8")
            home.write_text('<header id="header"><ul class="gnb"></ul></header>', encoding="utf-8")
            list_html.write_text('<div id="bo_list"><div class="bo_list_innr"></div></div>', encoding="utf-8")
            detail.write_text('<article id="bo_v"><div class="bo_v_innr"><div class="tbl_frm01 vtbl_wraps"></div></div></article>', encoding="utf-8")

            payload = build_co_listing_live_injection_plan(
                policy_path=policy,
                snippets_path=snippets,
                operator_path=operator,
                home_html_path=home,
                list_html_path=list_html,
                detail_html_path=detail,
            )

            self.assertTrue(payload["summary"]["plan_ready"])
            self.assertEqual(payload["summary"]["selector_verified_count"], 5)
            self.assertEqual(len(payload["placements"]), 5)


if __name__ == "__main__":
    unittest.main()
