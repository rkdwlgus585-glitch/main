import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_surface_stack_audit import build_surface_stack_audit


class GenerateSurfaceStackAuditTests(unittest.TestCase):
    @patch("scripts.generate_surface_stack_audit._fetch_html")
    def test_detects_live_wordpress_kr_and_gnuboard_weaver_co(self, mock_fetch):
        mock_fetch.side_effect = [
            {
                "url": "https://seoulmna.kr",
                "ok": True,
                "server": "openresty",
                "title": "서울건설정보",
                "html": '<html><head><meta name="generator" content="WordPress 6.9.1" /><link rel="stylesheet" href="/wp-content/themes/astra/assets/css/minified/main.min.css?ver=4.12.3" /></head></html>',
            },
            {
                "url": "https://seoulmna.co.kr",
                "ok": True,
                "server": "nginx",
                "title": "건설업 명가",
                "html": '<script>var g5_url="https://seoulmna.co.kr";</script><link rel="stylesheet" href="/plugin/weaver_plugin/assets/plugin/weaver/css/weaver.css">',
            },
        ]
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            front_app = base / "kr_platform_front"
            (front_app / ".next").mkdir(parents=True)
            (front_app / ".next" / "build-manifest.json").write_text("{}", encoding="utf-8")
            (front_app / "package.json").write_text(
                json.dumps(
                    {
                        "dependencies": {"next": "16.1.6", "react": "19.2.4"},
                        "devDependencies": {"typescript": "5.9.3"},
                        "scripts": {"build": "next build"},
                    }
                ),
                encoding="utf-8",
            )
            (front_app / "vercel.json").write_text('{"framework":"nextjs"}', encoding="utf-8")
            theme_html = base / "adm_theme.html"
            service_html = base / "adm_service.html"
            theme_html.write_text(
                '<link rel="stylesheet" href="/plugin/weaver_plugin/assets/plugin/weaver/css/weaver.css">'
                '<script>var g5_url="https://seoulmna.co.kr";</script>',
                encoding="utf-8",
            )
            service_html.write_text('<a href="/adm/service.php">service</a>', encoding="utf-8")
            platform_audit = base / "platform_audit.json"
            platform_audit.write_text(
                json.dumps(
                    {"front": {"channel_role": "platform_front", "engine_origin": "https://engine.internal"}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            wp_lab = base / "wp_lab.json"
            wp_lab.write_text(
                json.dumps({"packages": [{"slug": "astra"}, {"slug": "wordpress-seo"}]}, ensure_ascii=False),
                encoding="utf-8",
            )

            out = build_surface_stack_audit(
                front_app_path=front_app,
                theme_html_path=theme_html,
                service_html_path=service_html,
                platform_audit_path=platform_audit,
                wp_lab_path=wp_lab,
            )

            self.assertEqual(out["surfaces"]["kr"]["stack"], "wordpress_astra_live")
            self.assertTrue(out["surfaces"]["kr"]["wordpress_applicable_live"])
            self.assertEqual(out["surfaces"]["kr"]["target_platform_stack"], "nextjs_vercel_front")
            self.assertEqual(out["surfaces"]["co"]["stack"], "gnuboard_weaver_like")
            self.assertIn("/plugin/weaver_plugin/", out["surfaces"]["co"]["evidence"]["weaver_markers"])
            self.assertEqual(out["decisions"]["kr_platform_strategy"], "wordpress_live_with_next_cutover_target")
            self.assertEqual(out["wordpress"]["live_applicability"]["decision"], "sandbox_only")
            self.assertTrue(out["wordpress"]["live_applicability"]["kr"])
            self.assertEqual(out["wordpress"]["candidate_package_slugs"], ["astra", "wordpress-seo"])


if __name__ == "__main__":
    unittest.main()
