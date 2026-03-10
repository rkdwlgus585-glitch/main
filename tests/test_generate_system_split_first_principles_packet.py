import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_system_split_first_principles_packet import build_packet, main


class GenerateSystemSplitFirstPrinciplesPacketTests(unittest.TestCase):
    def test_build_packet_tracks_platform_yangdo_and_permit(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            platform = base / 'platform.json'
            yangdo = base / 'yangdo.json'
            permit = base / 'permit.json'
            yangdo_copy = base / 'yangdo_copy.json'
            permit_copy = base / 'permit_copy.json'

            platform.write_text(json.dumps({
                'summary': {'packet_ready': True, 'current_bottleneck': 'publish gate split'},
                'first_principles_prompt': 'Reduce branches first.'
            }, ensure_ascii=False), encoding='utf-8')
            yangdo.write_text(json.dumps({
                'summary': {'prompt_doc_ready': True},
                'current_execution_lane': {'id': 'yangdo_lane'},
                'execution_prompt': ['Interpret market fit', 'Tighten recommendation flow'],
            }, ensure_ascii=False), encoding='utf-8')
            permit.write_text(json.dumps({
                'summary': {'prompt_doc_ready': True},
                'current_execution_lane': {'id': 'permit_lane'},
                'execution_prompt': 'Separate checklist from manual review.',
            }, ensure_ascii=False), encoding='utf-8')
            yangdo_copy.write_text(json.dumps({'summary': {'service_copy_ready': True}}, ensure_ascii=False), encoding='utf-8')
            permit_copy.write_text(json.dumps({'summary': {'service_copy_ready': True}}, ensure_ascii=False), encoding='utf-8')

            payload = build_packet(
                platform_path=platform,
                yangdo_path=yangdo,
                permit_path=permit,
                yangdo_copy_path=yangdo_copy,
                permit_copy_path=permit_copy,
            )

        self.assertTrue(payload['summary']['packet_ready'])
        self.assertEqual(payload['summary']['prompt_count'], 3)
        self.assertTrue(payload['tracks']['yangdo']['service_copy_ready'])
        self.assertTrue(payload['tracks']['permit']['service_copy_ready'])
        self.assertEqual(payload['tracks']['platform']['current_bottleneck'], 'publish gate split')
        self.assertEqual(payload['tracks']['yangdo']['current_bottleneck'], 'yangdo_lane')
        self.assertIn('Interpret market fit', payload['tracks']['yangdo']['execution_prompt'])
        self.assertEqual(payload['tracks']['permit']['current_bottleneck'], 'permit_lane')

    def test_main_writes_json_and_md(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            platform = base / 'platform.json'
            yangdo = base / 'yangdo.json'
            permit = base / 'permit.json'
            yangdo_copy = base / 'yangdo_copy.json'
            permit_copy = base / 'permit_copy.json'
            for path in (platform, yangdo, permit, yangdo_copy, permit_copy):
                path.write_text(json.dumps({'summary': {'packet_ready': True, 'prompt_doc_ready': True, 'service_copy_ready': True}}), encoding='utf-8')
            out_json = base / 'packet.json'
            out_md = base / 'packet.md'
            with patch('sys.argv', [
                'generate_system_split_first_principles_packet.py',
                '--platform', str(platform),
                '--yangdo', str(yangdo),
                '--permit', str(permit),
                '--yangdo-copy', str(yangdo_copy),
                '--permit-copy', str(permit_copy),
                '--json', str(out_json),
                '--md', str(out_md),
            ]):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(out_json.exists())
            self.assertTrue(out_md.exists())


if __name__ == '__main__':
    unittest.main()
