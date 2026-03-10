import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_yangdo_recommendation_ux_packet import build_yangdo_recommendation_ux_packet


class GenerateYangdoRecommendationUxPacketTests(unittest.TestCase):
    def test_build_packet_combines_surface_bridge_and_rental_exposure(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / 'ia.json'
            ux = base / 'ux.json'
            bridge = base / 'bridge.json'
            rental = base / 'rental.json'
            precision = base / 'precision.json'
            contract = base / 'contract.json'

            ia.write_text(json.dumps({
                'topology': {'platform_host': 'seoulmna.kr', 'listing_host': 'seoulmna.co.kr'},
                'pages': [{'page_id': 'yangdo', 'slug': '/yangdo', 'title': 'AI Yangdo', 'primary_cta': '[seoulmna_calc_gate type="yangdo"]'}],
            }, ensure_ascii=False), encoding='utf-8')
            ux.write_text(json.dumps({'summary': {'ux_ok': True, 'yangdo_recommendation_surface_ok': True}}, ensure_ascii=False), encoding='utf-8')
            bridge.write_text(json.dumps({
                'summary': {
                    'packet_ready': True,
                    'platform_host': 'seoulmna.kr',
                    'listing_host': 'seoulmna.co.kr',
                    'service_slug': '/yangdo',
                    'market_bridge_ready': True,
                },
                'service_surface': {
                    'page_title': 'AI Yangdo',
                    'service_url': 'https://seoulmna.kr/yangdo',
                    'gate_shortcode': '[seoulmna_calc_gate type="yangdo"]',
                    'ui_rules': ['Public summary stays on kr.'],
                },
                'public_summary_contract': {
                    'fields': ['display_low_eok', 'recommendation_label', 'reasons'],
                    'story': 'Public shows only summary-safe recommendation fields.',
                    'primary_cta': {'label': '추천 매물 흐름 보기', 'target': 'https://seoulmna.kr/mna-market'},
                    'secondary_cta': {'label': '상담형 상세 요청', 'target': 'https://seoulmna.kr/consult?intent=yangdo'},
                },
                'detail_contract': {
                    'fields': ['precision_tier', 'matched_axes', 'mismatch_flags'],
                    'story': 'Detail explains fit and caution axes.',
                    'operator_only_fields': ['recommendation_score'],
                },
                'market_bridge_policy': {
                    'service_flow_policy': 'public_summary_then_market_or_consult',
                    'market_bridge_url': 'https://seoulmna.kr/mna-market',
                },
                'rental_packaging': {
                    'summary_offerings': ['yangdo_standard'],
                    'detail_offerings': ['yangdo_pro_detail', 'yangdo_pro'],
                    'internal_offerings': ['seoul_internal'],
                    'summary_policy': 'safe-summary',
                    'detail_policy': 'detail-explainable',
                    'internal_policy': 'internal-full',
                },
            }, ensure_ascii=False), encoding='utf-8')
            rental.write_text(json.dumps({
                'summary': {'yangdo_recommendation_offering_count': 3},
                'packaging': {
                    'partner_rental': {
                        'yangdo_recommendation': {
                            'public_story': 'Public shows summary-safe recommendation fields only.',
                            'detail_story': 'Detail explains fit, mismatch, and precision tier.',
                            'operator_story': 'Internal review keeps raw diagnostics.',
                            'service_flow_policy': 'public_summary_then_market_or_consult',
                            'service_primary_cta': '추천 매물 흐름 보기',
                            'service_secondary_cta': '상담형 상세 요청',
                            'package_matrix': {
                                'summary_market_bridge': {'offering_ids': ['yangdo_standard']},
                                'detail_explainable': {'offering_ids': ['yangdo_pro_detail']},
                                'consult_assist': {'offering_ids': ['yangdo_pro']},
                                'internal_full': {'offering_ids': ['seoul_internal']},
                            },
                        }
                    }
                }
            }, ensure_ascii=False), encoding='utf-8')
            precision.write_text(json.dumps({'summary': {'precision_ok': True, 'detail_explainability_ok': True, 'scenario_count': 6}}, ensure_ascii=False), encoding='utf-8')
            contract.write_text(json.dumps({'summary': {'contract_ok': True}}, ensure_ascii=False), encoding='utf-8')

            payload = build_yangdo_recommendation_ux_packet(
                ia_path=ia,
                ux_audit_path=ux,
                bridge_path=bridge,
                rental_path=rental,
                precision_path=precision,
                contract_path=contract,
            )

            self.assertTrue(payload['summary']['packet_ready'])
            self.assertEqual(payload['summary']['service_flow_policy'], 'public_summary_then_market_or_consult')
            self.assertEqual(payload['public_summary_experience']['cta_primary_label'], '추천 매물 흐름 보기')
            self.assertEqual(payload['public_summary_experience']['cta_secondary_label'], '상담형 상세 요청')
            self.assertEqual(payload['detail_explainable_experience']['allowed_offerings'], ['yangdo_pro_detail'])
            self.assertEqual(payload['consult_detail_experience']['allowed_offerings'], ['yangdo_pro'])
            self.assertEqual(payload['internal_review_experience']['allowed_offerings'], ['seoul_internal'])
            self.assertEqual(payload['rental_exposure_matrix']['standard']['offerings'], ['yangdo_standard'])
            self.assertEqual(payload['rental_exposure_matrix']['pro_detail']['offerings'], ['yangdo_pro_detail'])
            self.assertEqual(payload['rental_exposure_matrix']['pro_consult']['offerings'], ['yangdo_pro'])
            self.assertEqual(payload['rental_exposure_matrix']['internal']['offerings'], ['seoul_internal'])


if __name__ == '__main__':
    unittest.main()
