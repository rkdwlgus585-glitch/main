import tempfile
import unittest
from pathlib import Path

from scripts.generate_yangdo_test_thread_handoff import build_packet, render_markdown


class GenerateYangdoTestThreadHandoffTests(unittest.TestCase):
    def test_build_packet_collects_current_state_and_live_url(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)

            def write(name: str, payload: str) -> Path:
                path = base / name
                path.write_text(payload, encoding="utf-8")
                return path

            operations = write(
                "operations.json",
                """{
                  "decisions": {
                    "yangdo_prompt_loop_execution_lane": "prompt_loop_operationalization",
                    "yangdo_prompt_loop_parallel_lane": "",
                    "yangdo_public_language_ready": true,
                    "yangdo_zero_display_guard_ok": true,
                    "next_execution_track": "permit",
                    "next_execution_lane_id": "partner_binding_observability"
                  }
                }""",
            )
            brainstorm = write(
                "brainstorm.json",
                """{
                  "summary": {
                    "execution_lane": "prompt_loop_operationalization",
                    "parallel_lane": "",
                    "autoloop_ready": true,
                    "public_language_remaining_phrase_count": 0,
                    "one_or_less_display_total": 307,
                    "zero_display_total": 18,
                    "avg_display_neighbors": 3.3477,
                    "special_sector_scenario_total": 6
                  }
                }""",
            )
            zero_display = write(
                "zero_display.json",
                """{"summary":{"zero_display_guard_ok":true,"zero_display_total":18}}""",
            )
            public_language = write(
                "public_language.json",
                """{"summary":{"packet_ready":true,"public_language_ready":true,"remaining_phrase_count":0}}""",
            )
            founder_chain = write(
                "founder_chain.json",
                """{"summary":{"focus_matches_execution":true}}""",
            )
            next_execution = write(
                "next_execution.json",
                """{"summary":{"selected_track":"permit","selected_lane_id":"partner_binding_observability"}}""",
            )
            bridge = write(
                "bridge.json",
                """{"url":"https://seoulmna.kr/yangdo-ai-customer-10/"}""",
            )
            service_copy = write(
                "service_copy.json",
                """{
                  "summary":{
                    "service_slug":"/yangdo",
                    "platform_host":"seoulmna.kr",
                    "listing_host":"seoulmna.co.kr",
                    "service_copy_ready":true,
                    "market_bridge_story_ready":true,
                    "market_fit_interpretation_ready":true,
                    "lane_stories_ready":true
                  },
                  "hero":{"title":"양도 테스트"},
                  "cta_ladder":{
                    "primary_market_bridge":{"label":"추천 매물 흐름 보기","target":"https://seoulmna.kr/mna-market"},
                    "secondary_consult":{"label":"상담형 상세 요청","target":"https://seoulmna.kr/consult?intent=yangdo"}
                  }
                }""",
            )

            packet = build_packet(
                operations_path=operations,
                brainstorm_path=brainstorm,
                zero_display_path=zero_display,
                public_language_path=public_language,
                founder_chain_path=founder_chain,
                next_execution_path=next_execution,
                bridge_path=bridge,
                service_copy_path=service_copy,
            )

            self.assertEqual(packet["target_thread"], "양도양수 테스트 스레드")
            self.assertEqual(packet["live_service"]["customer_url"], "https://seoulmna.kr/yangdo-ai-customer-10/")
            self.assertEqual(packet["current_state"]["yangdo_prompt_loop_execution_lane"], "prompt_loop_operationalization")
            self.assertEqual(packet["current_state"]["global_next_execution_lane_id"], "partner_binding_observability")
            self.assertTrue(packet["current_state"]["yangdo_autoloop_ready"])
            self.assertGreaterEqual(len(packet["implemented_rules"]), 6)

            markdown = render_markdown(packet)
            self.assertIn("Yangdo Test Thread Handoff", markdown)
            self.assertIn("양도양수 테스트 스레드", markdown)
            self.assertIn("https://seoulmna.kr/yangdo-ai-customer-10/", markdown)


if __name__ == "__main__":
    unittest.main()
