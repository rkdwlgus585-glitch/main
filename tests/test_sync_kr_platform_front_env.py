import json
import tempfile
import unittest
from pathlib import Path

from scripts.sync_kr_platform_front_env import build_env_map, render_env


class SyncKrPlatformFrontEnvTests(unittest.TestCase):
    def test_build_env_map_uses_channel_values(self):
        channel = {
            'platform_front_host': 'seoulmna.kr',
            'legacy_content_host': 'seoulmna.co.kr',
            'public_calculator_mount_base': 'https://seoulmna.kr/_calc',
            'engine_origin': 'https://calc.seoulmna.co.kr',
            'default_tenant_id': 'seoul_main',
            'branding': {
                'contact_phone': '1668-3548',
                'contact_email': 'seoulmna@gmail.com',
            },
        }
        env_map = build_env_map(channel=channel)
        self.assertEqual(env_map['NEXT_PUBLIC_PLATFORM_FRONT_HOST'], 'https://seoulmna.kr')
        self.assertEqual(env_map['NEXT_PUBLIC_LISTING_HOST'], 'https://seoulmna.co.kr')
        self.assertEqual(env_map['NEXT_PUBLIC_CALCULATOR_MOUNT_BASE'], 'https://seoulmna.kr/_calc')
        self.assertEqual(env_map['NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN'], 'https://calc.seoulmna.co.kr')
        self.assertEqual(env_map['NEXT_PUBLIC_TENANT_ID'], 'seoul_main')

    def test_render_env_is_stable(self):
        out = render_env(
            {
                'NEXT_PUBLIC_PLATFORM_FRONT_HOST': 'https://seoulmna.kr',
                'NEXT_PUBLIC_LISTING_HOST': 'https://seoulmna.co.kr',
                'NEXT_PUBLIC_CALCULATOR_MOUNT_BASE': 'https://seoulmna.kr/_calc',
                'NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN': 'https://calc.seoulmna.co.kr',
                'NEXT_PUBLIC_CONTACT_PHONE': '1668-3548',
                'NEXT_PUBLIC_CONTACT_EMAIL': 'seoulmna@gmail.com',
                'NEXT_PUBLIC_TENANT_ID': 'seoul_main',
            }
        )
        self.assertIn('NEXT_PUBLIC_PLATFORM_FRONT_HOST=https://seoulmna.kr', out)
        self.assertIn('NEXT_PUBLIC_CALCULATOR_MOUNT_BASE=https://seoulmna.kr/_calc', out)
        self.assertTrue(out.endswith('\n'))


if __name__ == '__main__':
    unittest.main()
