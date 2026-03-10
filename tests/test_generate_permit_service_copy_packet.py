import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_permit_service_copy_packet import build_permit_service_copy_packet


class GeneratePermitServiceCopyPacketTests(unittest.TestCase):
    def test_build_packet_returns_ready_service_copy_with_lane_ladder(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia_path = base / 'ia.json'
            ux_path = base / 'ux.json'
            rental_path = base / 'rental.json'

            ia_path.write_text(
                json.dumps(
                    {
                        'topology': {'platform_host': 'seoulmna.kr'},
                        'pages': [
                            {'page_id': 'permit', 'slug': '/permit', 'primary_cta': '[seoulmna_calc_gate type="permit"]'},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )
            ux_path.write_text(
                json.dumps({'summary': {'ux_ok': True, 'service_pages_ok': True, 'market_bridge_ok': True}}, ensure_ascii=False),
                encoding='utf-8',
            )
            rental_path.write_text(
                json.dumps(
                    {
                        'summary': {'permit_selector_entry_total': 51, 'permit_platform_industry_total': 51},
                        'packaging': {
                            'partner_rental': {
                                'permit_precheck': {
                                    'lane_positioning': {
                                        'summary_self_check': {'upgrade_target': 'detail_checklist'},
                                        'detail_checklist': {'upgrade_target': 'manual_review_assist'},
                                        'manual_review_assist': {'upgrade_target': 'internal_full'},
                                    },
                                    'package_matrix': {
                                        'summary_self_check': {'offering_ids': ['permit_standard']},
                                        'detail_checklist': {'offering_ids': ['permit_pro']},
                                        'manual_review_assist': {'offering_ids': ['permit_pro_assist']},
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

            payload = build_permit_service_copy_packet(ia_path=ia_path, ux_path=ux_path, rental_path=rental_path)

            summary = payload.get('summary') or {}
            self.assertTrue(summary.get('packet_ready'))
            self.assertTrue(summary.get('lane_ladder_ready'))
            self.assertTrue(summary.get('service_flow_ready'))
            self.assertEqual(summary.get('service_slug'), '/permit')
            self.assertTrue(summary.get('checklist_story_ready'))
            self.assertTrue(summary.get('manual_review_story_ready'))
            self.assertTrue(summary.get('document_story_ready'))

            hero = payload.get('hero') or {}
            self.assertIn('등록기준', hero.get('title', ''))
            self.assertIn('[seoulmna_calc_gate type="permit"]', hero.get('gate_shortcode', ''))

            lanes = payload.get('lane_ladder') or {}
            self.assertEqual((lanes.get('summary_self_check') or {}).get('offering_ids'), ['permit_standard'])
            self.assertEqual((lanes.get('detail_checklist') or {}).get('upgrade_target'), 'manual_review_assist')
            self.assertEqual((lanes.get('manual_review_assist') or {}).get('offering_ids'), ['permit_pro_assist'])

            compare_rows = payload.get('lane_compare_table') or []
            self.assertEqual(len(compare_rows), 3)
            self.assertEqual(compare_rows[1].get('lane'), 'detail_checklist')
            self.assertIn('upgrade_reasons', payload)
            self.assertIn('summary_to_detail', payload.get('upgrade_reasons') or {})

            ctas = payload.get('cta_ladder') or {}
            self.assertEqual((ctas.get('primary_self_check') or {}).get('label'), '사전검토 시작')
            self.assertEqual((ctas.get('secondary_consult') or {}).get('target'), '/consult?intent=permit')
            self.assertEqual((ctas.get('supporting_knowledge') or {}).get('target'), '/knowledge')


if __name__ == '__main__':
    unittest.main()
