import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_permit_rental_lane_packet import build_permit_rental_lane_packet


class GeneratePermitRentalLanePacketTests(unittest.TestCase):
    def test_build_packet_returns_ready_lane_story(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            rental = base / 'rental.json'
            copy = base / 'copy.json'
            alignment = base / 'alignment.json'
            attorney = base / 'attorney.json'

            rental.write_text(
                json.dumps(
                    {
                        'summary': {'permit_offering_count': 6},
                        'packaging': {
                            'partner_rental': {
                                'permit_precheck': {
                                    'lane_positioning': {
                                        'summary_self_check': {'upgrade_target': 'detail_checklist'},
                                        'detail_checklist': {'upgrade_target': 'manual_review_assist'},
                                        'manual_review_assist': {'upgrade_target': 'internal_full'},
                                    },
                                    'package_matrix': {
                                        'summary_self_check': {'offering_ids': ['permit_standard', 'combo_standard']},
                                        'detail_checklist': {'offering_ids': ['permit_pro']},
                                        'manual_review_assist': {'offering_ids': ['permit_pro_assist', 'combo_pro']},
                                        'internal_full': {'offering_ids': []},
                                    },
                                }
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )
            copy.write_text(
                json.dumps(
                    {
                        'summary': {
                            'service_flow_ready': True,
                            'lane_ladder_ready': True,
                            'platform_host': 'seoulmna.kr',
                            'service_slug': '/permit',
                            'consult_target': '/consult?intent=permit',
                        },
                        'hero': {'title': '등록기준을 단계별로 해석하는 AI 인허가 사전검토', 'body': 'body'},
                        'cta_ladder': {
                            'primary_self_check': {'label': '사전검토 시작'},
                            'secondary_consult': {'label': '수동 검토 요청'},
                            'supporting_knowledge': {'label': '등록기준 안내 보기'},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )
            alignment.write_text(json.dumps({'summary': {'alignment_ok': True}}, ensure_ascii=False), encoding='utf-8')
            attorney.write_text(
                json.dumps(
                    {
                        'tracks': [
                            {
                                'track_id': 'B',
                                'attorney_position': {
                                    'claim_focus': ['typed criteria', 'manual-review gate', 'checklist'],
                                    'commercial_positioning': ['self-check', 'checklist', 'manual-review assist'],
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )

            payload = build_permit_rental_lane_packet(
                rental_path=rental,
                copy_path=copy,
                alignment_path=alignment,
                attorney_path=attorney,
            )

            self.assertTrue(payload['summary']['packet_ready'])
            self.assertTrue(payload['summary']['commercial_story_ready'])
            self.assertTrue(payload['summary']['detail_checklist_lane_ready'])
            self.assertTrue(payload['summary']['manual_review_assist_lane_ready'])
            self.assertEqual(payload['lane_matrix']['detail_checklist']['offerings'], ['permit_pro'])
            self.assertEqual(payload['sales_ladder'][1]['to'], 'manual_review_assist')
            self.assertEqual(payload['cta_contract']['secondary_consult'], '수동 검토 요청')


if __name__ == '__main__':
    unittest.main()
