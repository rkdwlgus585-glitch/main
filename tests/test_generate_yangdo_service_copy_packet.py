import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_yangdo_service_copy_packet import build_yangdo_service_copy_packet


class GenerateYangdoServiceCopyPacketTests(unittest.TestCase):
    def test_build_packet_combines_bridge_ux_precision_and_rental_contracts(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            bridge = base / "bridge.json"
            ux = base / "ux.json"
            precision = base / "precision.json"
            diversity = base / "diversity.json"
            rental = base / "rental.json"

            ia.write_text(
                json.dumps(
                    {
                        "topology": {"platform_host": "seoulmna.kr", "listing_host": "seoulmna.co.kr"},
                        "pages": [{"page_id": "yangdo", "slug": "/yangdo", "primary_cta": '[seoulmna_calc_gate type="yangdo"]'}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            bridge.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "service_slug": "/yangdo",
                            "platform_host": "seoulmna.kr",
                            "listing_host": "seoulmna.co.kr",
                            "supported_precision_labels": ["우선 추천", "조건 유사", "보조 검토"],
                        },
                        "service_surface": {"gate_shortcode": '[seoulmna_calc_gate type="yangdo"]'},
                        "public_summary_contract": {
                            "fields": ["display_low_eok", "recommendation_label", "reasons"],
                            "primary_cta": {"label": "추천 매물 흐름 보기", "target": "/mna-market"},
                            "secondary_cta": {"label": "상담형 상세 요청", "target": "/consult?intent=yangdo"},
                        },
                        "detail_contract": {
                            "fields": ["precision_tier", "matched_axes", "mismatch_flags"],
                        },
                        "market_bridge_policy": {
                            "service_flow_policy": "public_summary_then_market_or_consult",
                            "market_bridge_url": "/mna-market",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            ux.write_text(
                json.dumps(
                    {
                        "summary": {"packet_ready": True, "service_flow_policy": "public_summary_then_market_or_consult"},
                        "public_summary_experience": {
                            "story": "공개 화면은 가격 범위와 추천 요약만 보여줍니다.",
                            "cta_primary_label": "추천 매물 흐름 보기",
                            "cta_secondary_label": "상담형 상세 요청",
                        },
                        "consult_detail_experience": {
                            "story": "상담형 상세에서는 일치축과 비일치축을 함께 설명합니다."
                        },
                        "rental_exposure_matrix": {
                            "standard": {"offerings": ["yangdo_standard"]},
                            "pro_detail": {"offerings": ["yangdo_pro_detail"]},
                            "pro_consult": {"offerings": ["yangdo_pro"]},
                            "internal": {"offerings": ["seoul_internal"]},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            precision.write_text(json.dumps({"summary": {"precision_ok": True, "scenario_count": 6, "detail_explainability_ok": True}}, ensure_ascii=False), encoding="utf-8")
            diversity.write_text(json.dumps({"summary": {"diversity_ok": True, "scenario_count": 4}}, ensure_ascii=False), encoding="utf-8")
            rental.write_text(
                json.dumps(
                    {
                        "summary": {"yangdo_recommendation_offering_count": 4},
                        "packaging": {
                            "partner_rental": {
                                "yangdo_recommendation": {
                                    "public_story": "공개 화면은 가격 범위와 추천 요약만 보여줍니다.",
                                    "detail_story": "상담형 상세에서는 일치축과 비일치축을 함께 설명합니다.",
                                    "listing_runtime_policy": "never_embed_tools_on_listing_domain",
                                    "lane_positioning": {
                                        "summary_market_bridge": {
                                            "role": "public_entry_lane",
                                            "who_its_for": "공개 화면에서 시장 확인으로 바로 보내려는 파트너",
                                            "cta_bias": "market_first",
                                        },
                                        "detail_explainable": {
                                            "role": "standalone_explainable_lane",
                                            "who_its_for": "설명 가능한 추천 상세를 직접 제공하려는 파트너",
                                            "cta_bias": "explanation_first",
                                        },
                                        "consult_assist": {
                                            "role": "consult_connected_lane",
                                            "who_its_for": "설명과 상담 연결까지 함께 제공하려는 파트너",
                                            "cta_bias": "consult_first_when_precision_is_low",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_yangdo_service_copy_packet(
                ia_path=ia,
                bridge_path=bridge,
                ux_path=ux,
                precision_path=precision,
                diversity_path=diversity,
                rental_path=rental,
            )

            self.assertTrue(payload["summary"]["packet_ready"])
            self.assertTrue(payload["summary"]["service_copy_ready"])
            self.assertTrue(payload["summary"]["low_precision_consult_first_ready"])
            self.assertTrue(payload["summary"]["market_bridge_story_ready"])
            self.assertTrue(payload["summary"]["market_fit_interpretation_ready"])
            self.assertTrue(payload["summary"]["lane_stories_ready"])
            self.assertEqual(payload["cta_ladder"]["primary_market_bridge"]["label"], "추천 매물 흐름 보기")
            self.assertEqual(payload["cta_ladder"]["primary_market_bridge"]["target"], "/mna-market")
            self.assertEqual(payload["cta_ladder"]["secondary_consult"]["label"], "상담형 상세 요청")
            self.assertEqual(payload["offering_matrix"]["detail_explainable"], ["yangdo_pro_detail"])
            self.assertEqual(payload["offering_matrix"]["consult_assist"], ["yangdo_pro"])
            self.assertEqual(payload["precision_sections"][1]["preferred_lane"], "detail_explainable")
            self.assertEqual(payload["precision_sections"][2]["preferred_lane"], "consult_assist")
            self.assertEqual(payload["market_fit_interpretation"]["framing_title"], "시장 적합도 해석")
            self.assertEqual(payload["lane_stories"]["detail_explainable"]["cta_bias"], "explanation_first")
            self.assertEqual(payload["decision_paths"][1]["route"], "detail_explainable")
            self.assertEqual(payload["proof_points"]["precision_scenario_count"], 6)
            self.assertEqual(payload["proof_points"]["diversity_scenario_count"], 4)
            self.assertIn("보조 검토는 시장 브리지보다 상담 CTA를 먼저 강조한다.", payload["copy_guardrails"])


if __name__ == "__main__":
    unittest.main()
