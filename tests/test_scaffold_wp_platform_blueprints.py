import json
import tempfile
import unittest
from pathlib import Path

from scripts.scaffold_wp_platform_blueprints import build_wp_platform_blueprints


class ScaffoldWpPlatformBlueprintsTests(unittest.TestCase):
    def test_scaffold_blueprints_creates_html_files(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia_path = base / "ia.json"
            yangdo_copy_path = base / "yangdo_copy.json"
            permit_copy_path = base / "permit_copy.json"
            ia_path.write_text(
                json.dumps(
                    {
                        "topology": {"listing_host": "seoulmna.co.kr"},
                        "pages": [
                            {"page_id": "home", "slug": "/", "title": "홈", "calculator_policy": "cta_only_no_iframe"},
                            {"page_id": "yangdo", "slug": "/yangdo", "title": "양도가", "calculator_policy": "lazy_gate_shortcode"},
                            {"page_id": "permit", "slug": "/permit", "title": "인허가", "calculator_policy": "lazy_gate_shortcode"},
                        ],
                        "navigation": {"primary": [{"label": "홈", "href": "/"}]},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            yangdo_copy_path.write_text(
                json.dumps(
                    {
                        "summary": {"packet_ready": True},
                        "hero": {
                            "kicker": "AI 양도가 산정 시스템",
                            "title": "가격 범위와 유사매물 추천을 함께 설명합니다.",
                            "body": "시장 적합도 해석과 다음 행동을 함께 제공합니다.",
                            "gate_shortcode": '[seoulmna_calc_gate type="yangdo"]',
                        },
                        "explanation_cards": [
                            {"title": "가격 범위", "body": "가격 범위를 먼저 보여줍니다."},
                            {"title": "유사매물 추천", "body": "추천 강도를 설명합니다."},
                            {"title": "시장 확인과 상담 분기", "body": "시장 확인과 상담을 분리합니다."},
                        ],
                        "precision_sections": [
                            {"label": "우선 추천", "description": "강하게 맞는 추천", "preferred_cta": "추천 매물 흐름 보기", "preferred_lane": "summary_market_bridge"},
                            {"label": "조건 유사", "description": "일부 차이가 있는 추천", "preferred_cta": "상담형 상세 요청", "preferred_lane": "detail_explainable"},
                            {"label": "보조 검토", "description": "상담을 먼저 권하는 추천", "preferred_cta": "상담형 상세 요청", "preferred_lane": "consult_assist"},
                        ],
                        "cta_ladder": {
                            "primary_market_bridge": {"label": "추천 매물 흐름 보기", "target": "/mna-market"},
                            "secondary_consult": {"label": "상담형 상세 요청", "target": "/consult?intent=yangdo"},
                        },
                        "public_detail_split": {
                            "public_story": "공개 요약만 먼저 보여줍니다.",
                            "detail_story": "상담형 상세에서는 일치축과 비일치축을 설명합니다.",
                        },
                        "copy_guardrails": [
                            "홈에서는 계산기를 직접 띄우지 않는다.",
                            "보조 검토는 시장 브리지보다 상담 CTA를 먼저 강조한다.",
                        ],
                        "offering_matrix": {
                            "summary_market_bridge": ["yangdo_standard"],
                            "detail_explainable": ["yangdo_pro_detail"],
                            "consult_assist": ["yangdo_pro"],
                            "internal_full": [],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            permit_copy_path.write_text(
                json.dumps(
                    {
                        "summary": {"packet_ready": True},
                        "hero": {
                            "kicker": "AI 인허가 사전검토",
                            "title": "등록기준과 부족 항목을 먼저 분리합니다.",
                            "body": "증빙 체크리스트와 수동 검토 전환을 함께 안내합니다.",
                            "gate_shortcode": '[seoulmna_calc_gate type="permit"]',
                        },
                        "explanation_cards": [
                            {"title": "부족 항목", "body": "무엇이 부족한지 먼저 보여줍니다."},
                            {"title": "증빙 체크리스트", "body": "필요 서류를 단계별로 정리합니다."},
                            {"title": "수동 검토", "body": "복잡한 기준은 상담형 검토로 전환합니다."},
                        ],
                        "decision_paths": [
                            {"when": "핵심 기준 명확", "decision": "사전검토 결과 확인"},
                            {"when": "추가 기준 복잡", "decision": "수동 검토 전환"},
                        ],
                        "cta_ladder": {
                            "secondary_consult": {"label": "인허가 상담 연결", "target": "/consult?intent=permit"},
                            "supporting_knowledge": {"label": "등록기준 안내 보기", "target": "/knowledge"},
                        },
                        "copy_guardrails": ["서비스 페이지에서만 lazy gate를 사용한다."],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_wp_platform_blueprints(
                lab_root=base / "lab",
                ia_path=ia_path,
                yangdo_service_copy_path=yangdo_copy_path,
                permit_service_copy_path=permit_copy_path,
            )

            root = base / "lab" / "staging" / "wp-content" / "themes" / "seoulmna-platform-child" / "blueprints"
            self.assertTrue((root / "home.html").exists())
            self.assertTrue((root / "yangdo.html").exists())
            self.assertTrue((root / "permit.html").exists())
            self.assertTrue((root / "navigation.json").exists())
            self.assertEqual(payload["summary"]["blueprint_count"], 3)
            self.assertEqual(payload["summary"]["lazy_gate_pages_count"], 2)
            self.assertTrue(payload["summary"]["navigation_ready"])
            self.assertTrue(payload["service_copy_packet_used"])
            self.assertTrue(payload["permit_service_copy_packet_used"])

            home = (root / "home.html").read_text(encoding="utf-8")
            yangdo = (root / "yangdo.html").read_text(encoding="utf-8")
            permit = (root / "permit.html").read_text(encoding="utf-8")

            self.assertNotIn("[seoulmna_calc_gate", home)
            self.assertIn('[seoulmna_calc_gate type="yangdo"]', yangdo)
            self.assertIn('/consult?intent=yangdo', yangdo)
            self.assertIn('유사매물 추천', yangdo)
            self.assertIn('추천 매물 흐름 보기', yangdo)
            self.assertIn('[seoulmna_calc_gate type="permit"]', permit)
            self.assertIn('/consult?intent=permit', permit)
            self.assertIn('증빙 체크리스트', permit)
            self.assertIn('/knowledge', permit)


if __name__ == "__main__":
    unittest.main()
