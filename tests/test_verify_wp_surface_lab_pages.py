import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify_wp_surface_lab_pages import build_wp_surface_lab_page_verification


class VerifyWpSurfaceLabPagesTests(unittest.TestCase):
    def test_returns_runtime_blocker_when_runtime_is_missing(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            runtime_validation = base / "runtime_validation.json"
            wp_apply = base / "wp_apply.json"
            ia.write_text(
                json.dumps({"pages": [{"page_id": "home", "slug": "/", "wordpress_page_slug": "home", "calculator_policy": "cta_only_no_iframe"}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            runtime_validation.write_text(
                json.dumps({"summary": {"runtime_ready": False, "runtime_running": False}, "handoff": {"localhost_url": "http://127.0.0.1:18080"}}, ensure_ascii=False),
                encoding="utf-8",
            )
            wp_apply.write_text(json.dumps({"summary": {"bundle_ready": True}}, ensure_ascii=False), encoding="utf-8")

            payload = build_wp_surface_lab_page_verification(
                ia_path=ia,
                runtime_validation_path=runtime_validation,
                wp_apply_path=wp_apply,
            )

            self.assertFalse(payload["summary"]["verification_ready"])
            self.assertIn("runtime_not_ready", payload["summary"]["blockers"])

    def test_verifies_lazy_gate_pages_without_initial_iframe(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            runtime_validation = base / "runtime_validation.json"
            wp_apply = base / "wp_apply.json"
            ia.write_text(
                json.dumps(
                    {
                        "pages": [
                            {"page_id": "home", "slug": "/", "wordpress_page_slug": "home", "title": "메인", "calculator_policy": "cta_only_no_iframe"},
                            {"page_id": "yangdo", "slug": "/yangdo", "wordpress_page_slug": "yangdo", "title": "양도가", "calculator_policy": "lazy_gate_shortcode"},
                            {"page_id": "market_bridge", "slug": "/mna-market", "wordpress_page_slug": "mna-market", "title": "매물", "calculator_policy": "cta_only_no_iframe"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            runtime_validation.write_text(
                json.dumps({"summary": {"runtime_ready": True, "runtime_running": True}, "handoff": {"localhost_url": "http://127.0.0.1:18080"}}, ensure_ascii=False),
                encoding="utf-8",
            )
            wp_apply.write_text(json.dumps({"summary": {"bundle_ready": True}}, ensure_ascii=False), encoding="utf-8")

            html_by_url = {
                "http://127.0.0.1:18080": '<html><head><title>메인 - Lab</title></head><body><h1>메인</h1><a href="/yangdo">go</a></body></html>',
                "http://127.0.0.1:18080/yangdo": '<html><head><title>양도가 - Lab</title></head><body><h1>양도가</h1><section data-smna-calc-gate="true"><button class="smna-calc-gate__button">open</button></section></body></html>',
                "http://127.0.0.1:18080/mna-market": '<html><head><title>매물 - Lab</title></head><body><h1>매물</h1><a href="https://seoulmna.co.kr">market</a></body></html>',
            }

            with patch("scripts.verify_wp_surface_lab_pages._fetch", side_effect=lambda url: {"ok": True, "status": 200, "body": html_by_url[url]}):
                payload = build_wp_surface_lab_page_verification(
                    ia_path=ia,
                    runtime_validation_path=runtime_validation,
                    wp_apply_path=wp_apply,
                )

            self.assertTrue(payload["summary"]["verification_ready"])
            self.assertTrue(payload["summary"]["verification_ok"])
            yangdo = next(row for row in payload["page_checks"] if row["page_id"] == "yangdo")
            self.assertTrue(yangdo["contains_calc_gate"])
            self.assertFalse(yangdo["contains_iframe_initial"])
            self.assertTrue(yangdo["route_matches_expected"])

    def test_flags_pretty_permalink_issue_when_query_fallback_matches(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            runtime_validation = base / "runtime_validation.json"
            wp_apply = base / "wp_apply.json"
            ia.write_text(
                json.dumps(
                    {
                        "pages": [
                            {"page_id": "knowledge", "slug": "/knowledge", "wordpress_page_slug": "knowledge", "title": "지식베이스", "calculator_policy": "cta_only_no_iframe"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            runtime_validation.write_text(
                json.dumps({"summary": {"runtime_ready": True, "runtime_running": True}, "handoff": {"localhost_url": "http://127.0.0.1:18080"}}, ensure_ascii=False),
                encoding="utf-8",
            )
            wp_apply.write_text(json.dumps({"summary": {"bundle_ready": True}}, ensure_ascii=False), encoding="utf-8")
            html_by_url = {
                "http://127.0.0.1:18080/knowledge": '<html><head><title>메인 - Lab</title></head><body><h1>메인</h1></body></html>',
                "http://127.0.0.1:18080/?pagename=knowledge": '<html><head><title>지식베이스 - Lab</title></head><body><h1>지식베이스</h1></body></html>',
            }

            with patch("scripts.verify_wp_surface_lab_pages._fetch", side_effect=lambda url: {"ok": True, "status": 200, "body": html_by_url[url]}):
                payload = build_wp_surface_lab_page_verification(
                    ia_path=ia,
                    runtime_validation_path=runtime_validation,
                    wp_apply_path=wp_apply,
                )

            page = payload["page_checks"][0]
            self.assertFalse(page["route_matches_expected"])
            self.assertTrue(page["query_fallback_matches_expected"])
            self.assertEqual(page["route_issue"], "pretty_permalink_mismatch")

    def test_live_probe_can_override_stale_runtime_running_flag(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            runtime_validation = base / "runtime_validation.json"
            wp_apply = base / "wp_apply.json"
            ia.write_text(
                json.dumps(
                    {
                        "pages": [
                            {"page_id": "home", "slug": "/", "wordpress_page_slug": "home", "title": "메인", "calculator_policy": "cta_only_no_iframe"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            runtime_validation.write_text(
                json.dumps({"summary": {"runtime_ready": True, "runtime_running": False}, "handoff": {"localhost_url": "http://127.0.0.1:18080"}}, ensure_ascii=False),
                encoding="utf-8",
            )
            wp_apply.write_text(json.dumps({"summary": {"bundle_ready": True}}, ensure_ascii=False), encoding="utf-8")

            html_by_url = {
                "http://127.0.0.1:18080": '<html><head><title>메인 - Lab</title></head><body><h1>메인</h1></body></html>',
            }

            with patch("scripts.verify_wp_surface_lab_pages._fetch", side_effect=lambda url: {"ok": True, "status": 200, "body": html_by_url[url]}):
                payload = build_wp_surface_lab_page_verification(
                    ia_path=ia,
                    runtime_validation_path=runtime_validation,
                    wp_apply_path=wp_apply,
                )

            self.assertTrue(payload["summary"]["verification_ok"])
            self.assertEqual(payload["summary"]["blockers"], [])


if __name__ == "__main__":
    unittest.main()
