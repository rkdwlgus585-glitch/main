import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_yangdo_recommendation_alignment_audit import build_yangdo_recommendation_alignment_audit


class GenerateYangdoRecommendationAlignmentAuditTests(unittest.TestCase):
    def test_build_alignment_audit_passes_when_bridge_ux_rental_and_attorney_match(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bridge = base / 'bridge.json'
            ux = base / 'ux.json'
            rental = base / 'rental.json'
            attorney = base / 'attorney.json'

            bridge.write_text(json.dumps({
                'summary': {'supported_precision_labels': ['우선 추천', '조건 유사', '보조 검토']},
                'public_summary_contract': {
                    'fields': ['display_low_eok', 'display_high_eok', 'recommendation_label', 'reasons'],
                    'story': 'Public shows only summary-safe recommendation fields.',
                    'primary_cta': {'label': '추천 매물 흐름 보기'},
                    'secondary_cta': {'label': '상담형 상세 요청'},
                },
                'detail_contract': {
                    'fields': ['precision_tier', 'matched_axes', 'mismatch_flags'],
                    'story': 'Detail explains fit and caution axes.',
                },
                'rental_packaging': {
                    'summary_offerings': ['yangdo_standard', 'combo_standard'],
                    'detail_offerings': ['yangdo_pro_detail', 'yangdo_pro', 'combo_pro_detail', 'combo_pro'],
                    'internal_offerings': [],
                },
                'market_bridge_policy': {'service_flow_policy': 'public_summary_then_market_or_consult'},
            }, ensure_ascii=False), encoding='utf-8')
            ux.write_text(json.dumps({
                'summary': {'service_flow_policy': 'public_summary_then_market_or_consult'},
                'public_summary_experience': {
                    'visible_fields': ['display_low_eok', 'display_high_eok', 'recommendation_label', 'reasons'],
                    'story': 'Public shows only summary-safe recommendation fields.',
                    'cta_primary_label': '추천 매물 흐름 보기',
                    'cta_secondary_label': '상담형 상세 요청',
                },
                'consult_detail_experience': {
                    'visible_fields': ['precision_tier', 'matched_axes', 'mismatch_flags'],
                    'story': 'Detail explains fit and caution axes.',
                },
                'rental_exposure_matrix': {
                    'standard': {'offerings': ['yangdo_standard', 'combo_standard']},
                    'pro_detail': {'offerings': ['yangdo_pro_detail', 'combo_pro_detail']},
                    'pro_consult': {'offerings': ['yangdo_pro', 'combo_pro']},
                    'internal': {'offerings': []},
                },
            }, ensure_ascii=False), encoding='utf-8')
            rental.write_text(json.dumps({
                'summary': {'yangdo_recommendation_offering_count': 6},
                'packaging': {
                    'partner_rental': {
                        'yangdo_recommendation': {
                            'summary_offerings': ['yangdo_standard', 'combo_standard'],
                            'detail_offerings': ['yangdo_pro_detail', 'yangdo_pro', 'combo_pro_detail', 'combo_pro'],
                            'internal_offerings': [],
                            'package_matrix': {
                                'summary_market_bridge': {'offering_ids': ['yangdo_standard', 'combo_standard']},
                                'detail_explainable': {'offering_ids': ['yangdo_pro_detail', 'combo_pro_detail']},
                                'consult_assist': {'offering_ids': ['yangdo_pro', 'combo_pro']},
                                'internal_full': {'offering_ids': []},
                            },
                            'public_story': 'Public shows only summary-safe recommendation fields.',
                            'detail_story': 'Detail explains fit and caution axes.',
                            'service_primary_cta': '추천 매물 흐름 보기',
                            'service_secondary_cta': '상담형 상세 요청',
                            'service_flow_policy': 'public_summary_then_market_or_consult',
                            'supported_precision_labels': ['우선 추천', '조건 유사', '보조 검토'],
                        }
                    }
                }
            }, ensure_ascii=False), encoding='utf-8')
            attorney.write_text(json.dumps({
                'tracks': [{
                    'track_id': 'A',
                    'attorney_position': {
                        'claim_focus': [
                            '추천 정밀도 요약과 일치축/비일치축 설명',
                            '공개 등급에 따른 추천 요약 필드와 상담형 상세 필드 분리',
                        ],
                        'commercial_positioning': [
                            '표준형은 가격범위와 추천 요약만, Pro/API는 추천 정밀도와 추천 이유까지 제공',
                        ],
                    },
                }]
            }, ensure_ascii=False), encoding='utf-8')

            payload = build_yangdo_recommendation_alignment_audit(
                bridge_path=bridge,
                ux_path=ux,
                rental_path=rental,
                attorney_path=attorney,
            )

            self.assertTrue(payload['summary']['alignment_ok'])
            self.assertEqual(payload['summary']['issue_count'], 0)
            self.assertTrue(payload['summary']['service_flow_policy_ok'])
            self.assertTrue(payload['summary']['cta_labels_ok'])
            self.assertTrue(payload['summary']['field_contract_ok'])
            self.assertTrue(payload['summary']['offering_exposure_ok'])
            self.assertTrue(payload['summary']['patent_handoff_ok'])
            self.assertEqual(payload['issues'], [])
            self.assertEqual(payload['contracts']['offering_exposure']['pro_detail']['ux'], ['yangdo_pro_detail', 'combo_pro_detail'])
            self.assertEqual(payload['contracts']['offering_exposure']['pro_consult']['ux'], ['yangdo_pro', 'combo_pro'])


if __name__ == '__main__':
    unittest.main()
