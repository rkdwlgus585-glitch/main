import tempfile
import unittest
from pathlib import Path

from scripts.generate_yangdo_special_sector_packet import build_yangdo_special_sector_packet, main


class GenerateYangdoSpecialSectorPacketTests(unittest.TestCase):
    def test_build_packet_marks_three_special_sectors_ready(self):
        precision = {
            "summary": {
                "special_sector_comprehensive_ok": True,
                "special_sector_split_ok": True,
            },
            "scenarios": [
                {"scenario_id": "special_sector_comprehensive_uses_sales_and_scale_without_balance", "ok": True, "observed": {"recommendation_focus": "scale", "precision_tier": "high"}},
                {"scenario_id": "special_sector_split_uses_sales_and_capital_without_balance", "ok": True, "observed": {"recommendation_focus": "sales_capital", "precision_tier": "high"}},
                {"scenario_id": "telecom_comprehensive_keeps_scale_focus_without_balance", "ok": True, "observed": {"recommendation_focus": "scale", "precision_tier": "high"}},
                {"scenario_id": "telecom_split_moves_focus_to_sales_and_capital", "ok": True, "observed": {"recommendation_focus": "sales_capital", "precision_tier": "high"}},
                {"scenario_id": "fire_split_moves_focus_to_sales_and_capital", "ok": True, "observed": {"recommendation_focus": "sales_capital", "precision_tier": "assist"}},
            ],
        }
        diversity = {"summary": {"diversity_ok": True}}
        contract = {"summary": {"contract_ok": True}}
        settlement = {
            "by_sector": {
                "전기": {
                    "포괄": {"auto": {"count": 10, "publication_counts": {"consult_only": 5, "range_only": 4, "full": 1}}},
                    "분할/합병": {"auto": {"count": 6, "publication_counts": {"consult_only": 4, "range_only": 2}}},
                },
                "정보통신": {
                    "포괄": {"auto": {"count": 8, "publication_counts": {"consult_only": 4, "range_only": 4}}},
                    "분할/합병": {"auto": {"count": 5, "publication_counts": {"consult_only": 3, "range_only": 2}}},
                },
                "소방": {
                    "분할/합병": {"auto": {"count": 4, "publication_counts": {"consult_only": 2, "range_only": 2}}},
                },
            }
        }

        payload = build_yangdo_special_sector_packet(
            precision_payload=precision,
            diversity_payload=diversity,
            contract_payload=contract,
            settlement_payload=settlement,
        )

        self.assertTrue(payload["summary"]["packet_ready"])
        self.assertEqual(payload["summary"]["special_sector_count"], 3)
        self.assertEqual(payload["summary"]["sector_ready_count"], 3)
        self.assertTrue(payload["summary"]["publication_safety_ok"])
        self.assertFalse(payload["summary"]["pricing_watch_required"])
        self.assertEqual(payload["summary"]["expansion_candidate_count"], 1)

    def test_cli_writes_files(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            precision = base / "precision.json"
            diversity = base / "diversity.json"
            contract = base / "contract.json"
            settlement = base / "settlement.json"
            out_json = base / "packet.json"
            out_md = base / "packet.md"

            precision.write_text(
                '{"summary":{"special_sector_comprehensive_ok":true,"special_sector_split_ok":true},"scenarios":[]}',
                encoding="utf-8",
            )
            diversity.write_text('{"summary":{"diversity_ok":true}}', encoding="utf-8")
            contract.write_text('{"summary":{"contract_ok":true}}', encoding="utf-8")
            settlement.write_text('{"by_sector":{}}', encoding="utf-8")

            from unittest.mock import patch
            import sys

            argv = [
                "generate_yangdo_special_sector_packet.py",
                "--precision", str(precision),
                "--diversity", str(diversity),
                "--contract", str(contract),
                "--settlement", str(settlement),
                "--json", str(out_json),
                "--md", str(out_md),
            ]
            with patch.object(sys, "argv", argv):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(out_json.exists())
            self.assertTrue(out_md.exists())


if __name__ == "__main__":
    unittest.main()
