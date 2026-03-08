import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_permit_service_ux_packet import build_permit_service_ux_packet


class GeneratePermitServiceUxPacketTests(unittest.TestCase):
    def test_build_packet_returns_ready_ux_contract(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / 'ia.json'
            ux = base / 'ux.json'
            copy = base / 'copy.json'
            alignment = base / 'alignment.json'
            rental_lane = base / 'rental_lane.json'
            rental = base / 'rental.json'

            ia.write_text(
                json.dumps(
                    {
                        'topology': {'platform_host': 'seoulmna.kr'},
                        'pages': [{'page_id': 'permit', 'slug': '/permit', 'primary_cta': '[seoulmna_calc_gate type="permit"]'}],
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )
            ux.write_text(json.dumps({'summary': {'ux_ok': True, 'service_pages_ok': True}}, ensure_ascii=False), encoding='utf-8')
            copy.write_text(
                json.dumps(
                    {
                        'summary': {
                            'packet_ready': True,
                            'service_flow_ready': True,
                            'platform_host': 'seoulmna.kr',
                            'service_slug': '/permit',
                        },
                        'hero': {
                            'title': 'AI 인허가 사전검토',
                            'kicker': 'AI 인허가 사전검토',
                            'body': '기본 자가진단으로 시작합니다.',
                            'gate_shortcode': '[seoulmna_calc_gate type="permit"]',
                        },
                        'cta_ladder': {
                            'primary_self_check': {'label': '사전검토 시작'},
                            'secondary_consult': {'label': '수동 검토 요청'},
                        },
                        'lane_ladder': {
                            'summary_self_check': {'label': '자가진단 요약', 'offering_ids': ['permit_standard'], 'upgrade_target': 'detail_checklist'},
                            'detail_checklist': {'label': '상세 체크리스트', 'offering_ids': ['permit_pro'], 'upgrade_target': 'manual_review_assist'},
                            'manual_review_assist': {'label': '수동 검토 보조', 'offering_ids': ['permit_pro_assist'], 'upgrade_target': 'internal_full'},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )
            alignment.write_text(json.dumps({'summary': {'alignment_ok': True}}, ensure_ascii=False), encoding='utf-8')
            rental_lane.write_text(
                json.dumps(
                    {
                        'summary': {'packet_ready': True, 'lane_ladder_ready': True},
                        'lane_matrix': {
                            'summary_self_check': {'offerings': ['permit_standard']},
                            'detail_checklist': {'offerings': ['permit_pro']},
                            'manual_review_assist': {'offerings': ['permit_pro_assist']},
                            'internal_full': {'offerings': []},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )
            rental.write_text(
                json.dumps(
                    {
                        'summary': {'permit_selector_entry_total': 51, 'permit_offering_count': 3},
                        'packaging': {
                            'partner_rental': {
                                'permit_precheck': {
                                    'public_story': '기본 자가진단 결과와 부족 항목 요약만 먼저 보여줍니다.',
                                    'detail_story': '기준별 판정과 증빙 체크리스트를 구조화해 제공합니다.',
                                    'assist_story': '예외와 추가 기준이 많은 케이스를 수동 검토 보조로 연결합니다.',
                                }
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )

            payload = build_permit_service_ux_packet(
                ia_path=ia,
                ux_audit_path=ux,
                copy_path=copy,
                alignment_path=alignment,
                rental_lane_path=rental_lane,
                rental_path=rental,
            )

            summary = payload['summary']
            self.assertTrue(summary['packet_ready'])
            self.assertEqual(summary['service_flow_policy'], 'public_summary_then_checklist_or_manual_review')
            self.assertEqual(payload['public_summary_experience']['allowed_offerings'], ['permit_standard'])
            self.assertEqual(payload['detail_checklist_experience']['allowed_offerings'], ['permit_pro'])
            self.assertEqual(payload['manual_review_assist_experience']['allowed_offerings'], ['permit_pro_assist'])
            self.assertEqual(payload['manual_review_assist_experience']['cta_primary_label'], '수동 검토 요청')


if __name__ == '__main__':
    unittest.main()
