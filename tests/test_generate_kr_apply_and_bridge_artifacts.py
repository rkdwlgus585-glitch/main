import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_co_listing_bridge_snippets import build_co_listing_bridge_snippets
from scripts.generate_kr_live_apply_packet import build_kr_live_apply_packet
from scripts.generate_kr_proxy_server_matrix import build_kr_proxy_server_matrix
from scripts.generate_listing_platform_bridge_policy import build_listing_platform_bridge_policy


class GenerateKrApplyAndBridgeArtifactsTests(unittest.TestCase):
    def test_listing_bridge_policy_emits_tracked_ctas(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            strategy = base / "strategy.json"
            proxy = base / "proxy.json"
            ia.write_text(json.dumps({"topology": {"platform_host": "seoulmna.kr", "listing_host": "seoulmna.co.kr"}}, ensure_ascii=False), encoding="utf-8")
            strategy.write_text(json.dumps({"calculator_mount_decision": {}}, ensure_ascii=False), encoding="utf-8")
            proxy.write_text(json.dumps({"topology": {"main_platform_host": "seoulmna.kr", "listing_market_host": "seoulmna.co.kr"}}, ensure_ascii=False), encoding="utf-8")

            payload = build_listing_platform_bridge_policy(ia_path=ia, strategy_path=strategy, proxy_spec_path=proxy)
            self.assertEqual(payload["summary"]["listing_runtime_policy"], "listing_domain_links_only_no_tool_embed")
            self.assertEqual(payload["ctas"][0]["placement"], "listing_detail_primary")
            self.assertIn("utm_source=co_listing", payload["ctas"][0]["target_url"])
            self.assertEqual(payload["ctas"][0]["copy"], "이 매물 기준 양도가 범위 먼저 보기")
            self.assertEqual(payload["policy"]["calculator_runtime_policy"], "never_embed_tools_on_listing_domain")

    def test_proxy_server_matrix_emits_nginx_and_apache_variants(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            proxy = base / "proxy.json"
            traffic = base / "traffic.json"
            cutover = base / "cutover.json"
            proxy.write_text(json.dumps({"topology": {"public_mount_path": "/_calc", "private_engine_origin": "https://calc.seoulmna.co.kr"}}, ensure_ascii=False), encoding="utf-8")
            traffic.write_text(json.dumps({"decision": {"traffic_leak_blocked": True}}, ensure_ascii=False), encoding="utf-8")
            cutover.write_text(json.dumps({"summary": {"cutover_ready": True}}, ensure_ascii=False), encoding="utf-8")

            payload = build_kr_proxy_server_matrix(proxy_spec_path=proxy, traffic_path=traffic, cutover_path=cutover)
            self.assertTrue(payload["summary"]["matrix_ready"])
            self.assertIn("location /_calc/", payload["nginx"]["snippet"])
            self.assertIn('ProxyPass "/_calc/"', payload["apache"]["snippet"])

    def test_live_apply_packet_combines_wordpress_and_server_steps(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            blueprints = base / "blueprints.json"
            assets = base / "assets.json"
            wp_apply = base / "wp_apply.json"
            cycle = base / "cycle.json"
            cutover = base / "cutover.json"
            proxy_matrix = base / "proxy_matrix.json"
            bridge = base / "bridge.json"
            ia.write_text(json.dumps({"pages": [{"calculator_policy": "lazy_gate_shortcode"}, {"calculator_policy": "cta_only_no_iframe"}], "summary": {"front_page_slug": "home"}}, ensure_ascii=False), encoding="utf-8")
            blueprints.write_text(json.dumps({"pages": [{"wordpress_page_slug": "home", "blueprint_file": "home.html"}]}, ensure_ascii=False), encoding="utf-8")
            assets.write_text(json.dumps({"theme": {"slug": "seoulmna-platform-child"}, "plugin": {"slug": "seoulmna-platform-bridge"}}, ensure_ascii=False), encoding="utf-8")
            wp_apply.write_text(json.dumps({"manifest": {"front_page_slug": "home", "menu": {"name": "?쒖슱嫄댁꽕?뺣낫 ?뚮옯??"}}}, ensure_ascii=False), encoding="utf-8")
            cycle.write_text(json.dumps({"summary": {"ok": True}}, ensure_ascii=False), encoding="utf-8")
            cutover.write_text(json.dumps({"summary": {"cutover_ready": True}}, ensure_ascii=False), encoding="utf-8")
            proxy_matrix.write_text(json.dumps({"nginx": {"snippet": "location /_calc/ {}"}, "apache": {"snippet": "ProxyPass \"/_calc/\""}, "cloudflare": {"cache_rules": []}}, ensure_ascii=False), encoding="utf-8")
            bridge.write_text(json.dumps({"ctas": [{"placement": "listing_detail_primary", "target_url": "https://seoulmna.kr/yangdo", "copy": "보기"}]}, ensure_ascii=False), encoding="utf-8")

            payload = build_kr_live_apply_packet(
                ia_path=ia,
                blueprints_path=blueprints,
                wp_assets_path=assets,
                wp_apply_path=wp_apply,
                wp_cycle_path=cycle,
                cutover_path=cutover,
                proxy_matrix_path=proxy_matrix,
                bridge_policy_path=bridge,
            )
            self.assertTrue(payload["summary"]["apply_packet_ready"])
            self.assertEqual(payload["summary"]["bridge_cta_count"], 1)
            self.assertEqual(payload["summary"]["menu_name"], "서울건설정보 플랫폼")
            self.assertEqual(payload["wordpress_steps"][1]["area"], "theme")
            self.assertEqual(payload["server_steps"][0]["stack"], "nginx")

    def test_co_listing_bridge_snippets_emit_files(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            policy = base / "policy.json"
            output_dir = base / "snippets"
            policy.write_text(
                json.dumps(
                    {
                        "summary": {"listing_host": "seoulmna.co.kr", "platform_host": "seoulmna.kr"},
                        "ctas": [
                            {
                                "placement": "listing_detail_primary",
                                "target_service": "yangdo",
                                "target_url": "https://seoulmna.kr/yangdo?utm_source=co_listing",
                                "copy": "이 매물 기준 양도가 범위 먼저 보기",
                                "reason": "상세 페이지에서 바로 이동한다.",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            payload = build_co_listing_bridge_snippets(policy_path=policy, output_dir=output_dir)
            self.assertEqual(payload["summary"]["placement_count"], 1)
            self.assertTrue((output_dir / "listing_detail_primary.html").exists())
            self.assertTrue((output_dir / "bridge-snippets.css").exists())
            self.assertTrue((output_dir / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
