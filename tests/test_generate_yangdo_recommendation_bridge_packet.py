import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_yangdo_recommendation_bridge_packet import (
    build_yangdo_recommendation_bridge_packet,
)


class GenerateYangdoRecommendationBridgePacketTests(unittest.TestCase):
    def test_build_bridge_packet_combines_service_market_and_rental_contracts(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            bridge_policy = base / "bridge_policy.json"
            rental = base / "rental.json"
            precision = base / "precision.json"
            contract = base / "contract.json"

            ia.write_text(
                json.dumps(
                    {
                        "topology": {
                            "platform_host": "seoulmna.kr",
                            "listing_host": "seoulmna.co.kr",
                        },
                        "pages": [
                            {
                                "page_id": "yangdo",
                                "slug": "/yangdo",
                                "title": "AI 양도가 산정 · 유사매물 추천",
                                "primary_cta": '[seoulmna_calc_gate type="yangdo"]',
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            bridge_policy.write_text(
                json.dumps(
                    {
                        "summary": {
                            "platform_host": "seoulmna.kr",
                            "listing_host": "seoulmna.co.kr",
                            "listing_runtime_policy": "listing_domain_links_only_no_tool_embed",
                        },
                        "ctas": [
                            {
                                "placement": "listing_detail_primary",
                                "target_url": "https://seoulmna.kr/mna-market",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            rental.write_text(
                json.dumps(
                    {
                        "summary": {
                            "offering_count": 6,
                        },
                        "packaging": {
                            "partner_rental": {
                                "yangdo_recommendation": {
                                    "summary_offerings": ["yangdo_standard"],
                                    "detail_offerings": ["yangdo_pro", "combo_pro"],
                                    "internal_offerings": ["seoul_internal"],
                                    "summary_policy": "safe-summary",
                                    "detail_policy": "detail-explainable",
                                    "internal_policy": "internal-full",
                                    "supported_precision_labels": ["우선 추천", "조건 유사", "보조 검토"],
                                    "public_story": "공개 화면에는 요약만 노출합니다.",
                                    "detail_story": "상담형 상세에서만 설명축을 더 보여줍니다.",
                                }
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            precision.write_text(
                json.dumps({"summary": {"precision_ok": True, "scenario_count": 6}}, ensure_ascii=False),
                encoding="utf-8",
            )
            contract.write_text(
                json.dumps({"summary": {"contract_ok": True}}, ensure_ascii=False),
                encoding="utf-8",
            )

            payload = build_yangdo_recommendation_bridge_packet(
                ia_path=ia,
                bridge_policy_path=bridge_policy,
                rental_path=rental,
                precision_path=precision,
                contract_path=contract,
            )

            self.assertTrue(payload["summary"]["packet_ready"])
            self.assertTrue(payload["summary"]["market_bridge_ready"])
            self.assertTrue(payload["summary"]["rental_ready"])
            self.assertEqual(payload["summary"]["service_slug"], "/yangdo")
            self.assertEqual(payload["public_summary_contract"]["fields"][0], "display_low_eok")
            self.assertEqual(payload["public_summary_contract"]["primary_cta"]["target"], "https://seoulmna.kr/mna-market")
            self.assertEqual(payload["public_summary_contract"]["primary_cta"]["placement"], "service_market_bridge")
            self.assertEqual(payload["detail_contract"]["fields"][0], "precision_tier")
            self.assertEqual(payload["market_bridge_policy"]["listing_runtime_policy"], "listing_domain_links_only_no_tool_embed")
            self.assertEqual(payload["rental_packaging"]["summary_offerings"], ["yangdo_standard"])
            self.assertEqual(payload["rental_packaging"]["detail_offerings"], ["yangdo_pro", "combo_pro"])
            self.assertEqual(payload["rental_packaging"]["internal_offerings"], ["seoul_internal"])


if __name__ == "__main__":
    unittest.main()
