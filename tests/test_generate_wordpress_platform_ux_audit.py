import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_wordpress_platform_ux_audit import build_wordpress_platform_ux_audit


class GenerateWordpressPlatformUxAuditTests(unittest.TestCase):
    def test_build_wordpress_platform_ux_audit_detects_missing_bridge_return(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            verify = base / "verify.json"
            blueprints = base / "blueprints"
            blueprints.mkdir(parents=True, exist_ok=True)

            ia.write_text(json.dumps({
                "pages": [
                    {
                        "page_id": "market_bridge",
                        "slug": "/mna-market",
                        "wordpress_page_slug": "mna-market",
                        "title": "양도양수 매물 보기",
                        "calculator_policy": "cta_only_no_iframe",
                    }
                ]
            }, ensure_ascii=False), encoding="utf-8")
            verify.write_text(json.dumps({
                "page_checks": [
                    {
                        "page_id": "market_bridge",
                        "reachable": True,
                        "route_matches_expected": True,
                        "contains_iframe_initial": False,
                        "contains_market_link": True,
                    }
                ]
            }, ensure_ascii=False), encoding="utf-8")
            (blueprints / "mna-market.html").write_text(
                '<a href="https://seoulmna.co.kr">매물 사이트</a>',
                encoding="utf-8",
            )

            payload = build_wordpress_platform_ux_audit(
                ia_path=ia,
                verify_path=verify,
                blueprint_root=blueprints,
            )

            self.assertFalse(payload["summary"]["ux_ok"])
            self.assertEqual(payload["summary"]["issue_count"], 1)
            self.assertIn("market_bridge:has_return_to_yangdo", payload["issues"])

    def test_build_wordpress_platform_ux_audit_accepts_query_fallback_and_recommendation_copy(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            verify = base / "verify.json"
            blueprints = base / "blueprints"
            blueprints.mkdir(parents=True, exist_ok=True)

            ia.write_text(json.dumps({
                "pages": [
                    {
                        "page_id": "yangdo",
                        "slug": "/yangdo",
                        "wordpress_page_slug": "yangdo",
                        "title": "AI 양도가 산정 · 유사매물 추천",
                        "calculator_policy": "lazy_gate_shortcode",
                    }
                ]
            }, ensure_ascii=False), encoding="utf-8")
            verify.write_text(json.dumps({
                "page_checks": [
                    {
                        "page_id": "yangdo",
                        "reachable": False,
                        "route_matches_expected": False,
                        "query_fallback_reachable": True,
                        "query_fallback_matches_expected": True,
                        "contains_iframe_initial": False,
                        "contains_calc_gate": True,
                    }
                ]
            }, ensure_ascii=False), encoding="utf-8")
            (blueprints / "yangdo.html").write_text(
                '유사매물 추천 가격 범위 추천 라벨 추천 정밀도 추천 이유 우선 추천 조건 유사 보조 검토 '
                '일치축 비일치축 공개 요약 상담형 상세 운영 검수 중복 매물 보정 '
                '추천 매물 실제 확인은 별도 매물 사이트(seoulmna.co.kr)에서 진행하고, 계산과 해석은 메인 플랫폼에서 유지합니다. '
                '추천 매물 흐름 보기 상담형 상세 요청 '
                '/mna-market /consult /consult?intent=yangdo '
                '[seoulmna_calc_gate type="yangdo"]',
                encoding="utf-8",
            )

            payload = build_wordpress_platform_ux_audit(
                ia_path=ia,
                verify_path=verify,
                blueprint_root=blueprints,
            )

            self.assertTrue(payload["summary"]["ux_ok"])
            self.assertEqual(payload["summary"]["issue_count"], 0)
            self.assertTrue(payload["summary"]["yangdo_recommendation_surface_ok"])
            self.assertEqual(payload["pages"][0]["failed_checks"], [])


if __name__ == "__main__":
    unittest.main()
