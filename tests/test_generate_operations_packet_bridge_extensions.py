import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_operations_packet import build_operations_packet


class GenerateOperationsPacketBridgeExtensionsTests(unittest.TestCase):
    def test_packet_includes_bridge_proxy_live_apply_and_operator_summaries(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            readiness = base / "readiness.json"
            release = base / "release.json"
            risk = base / "risk.json"
            attorney = base / "attorney.json"
            bridge = base / "bridge.json"
            proxy_matrix = base / "proxy_matrix.json"
            live_apply = base / "live_apply.json"
            live_operator = base / "live_operator.json"

            readiness.write_text(json.dumps({"ok": True, "blocking_issues": [], "handoff": {"release_ready": True}}, ensure_ascii=False), encoding="utf-8")
            release.write_text(json.dumps({"ok": True, "blocking_issues": [], "handoff": {"runtime_verified": True}, "artifact_summary": {}}, ensure_ascii=False), encoding="utf-8")
            risk.write_text(json.dumps({"business_core_status": "green", "run_summary": {"issue_count": 0}}, ensure_ascii=False), encoding="utf-8")
            attorney.write_text(json.dumps({"executive_summary": {"independent_systems": ["yangdo", "permit"]}}, ensure_ascii=False), encoding="utf-8")
            bridge.write_text(
                json.dumps(
                    {
                        "summary": {
                            "platform_host": "seoulmna.kr",
                            "listing_host": "seoulmna.co.kr",
                            "cta_count": 5,
                            "routing_rule_count": 3,
                            "listing_runtime_policy": "listing_domain_links_only_no_tool_embed",
                        },
                        "policy": {"calculator_runtime_policy": "never_embed_tools_on_listing_domain"},
                        "ctas": [{"target_url": "https://seoulmna.kr/yangdo?utm_source=co_listing"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            proxy_matrix.write_text(
                json.dumps(
                    {
                        "summary": {
                            "matrix_ready": True,
                            "traffic_gate_ok": True,
                            "cutover_ready": True,
                            "public_mount_path": "/_calc",
                            "upstream_origin": "https://calc.seoulmna.co.kr",
                        },
                        "nginx": {"snippet": "location /_calc/ {}"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            live_apply.write_text(
                json.dumps(
                    {
                        "summary": {
                            "apply_packet_ready": True,
                            "page_count": 6,
                            "service_page_count": 2,
                            "front_page_slug": "home",
                            "menu_name": "서울건설정보 플랫폼",
                            "bridge_cta_count": 5,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            live_operator.write_text(
                json.dumps(
                    {
                        "summary": {
                            "checklist_ready": True,
                            "platform_host": "seoulmna.kr",
                            "listing_host": "seoulmna.co.kr",
                            "public_mount_path": "/_calc",
                            "preflight_item_count": 4,
                            "validation_step_count": 4,
                            "operator_input_count": 1,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            packet = build_operations_packet(
                readiness_path=readiness,
                release_path=release,
                risk_map_path=risk,
                attorney_path=attorney,
                listing_platform_bridge_policy_path=bridge,
                kr_proxy_server_matrix_path=proxy_matrix,
                kr_live_apply_packet_path=live_apply,
                kr_live_operator_checklist_path=live_operator,
            )

            self.assertEqual(packet["summaries"]["listing_platform_bridge_policy"]["cta_count"], 5)
            self.assertEqual(packet["summaries"]["kr_proxy_server_matrix"]["public_mount_path"], "/_calc")
            self.assertEqual(packet["summaries"]["kr_live_apply_packet"]["front_page_slug"], "home")
            self.assertTrue(packet["summaries"]["kr_live_operator_checklist"]["checklist_ready"])
            self.assertEqual(packet["artifacts"]["kr_live_apply_packet"], str(live_apply.resolve()))
            self.assertEqual(packet["artifacts"]["kr_live_operator_checklist"], str(live_operator.resolve()))


if __name__ == "__main__":
    unittest.main()
