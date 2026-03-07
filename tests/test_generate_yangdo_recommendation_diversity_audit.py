import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_yangdo_recommendation_diversity_audit import (
    build_yangdo_recommendation_diversity_audit,
    main,
)


class GenerateYangdoRecommendationDiversityAuditTests(unittest.TestCase):
    def test_build_diversity_audit_is_green(self):
        payload = build_yangdo_recommendation_diversity_audit()
        summary = payload.get("summary") or {}
        self.assertTrue(summary.get("diversity_ok"))
        self.assertTrue(summary.get("top1_stability_ok"))
        self.assertTrue(summary.get("price_band_spread_ok"))
        self.assertTrue(summary.get("focus_signature_spread_ok"))
        self.assertTrue(summary.get("detail_projection_contract_ok"))
        self.assertTrue(summary.get("precision_tier_spread_ok"))
        self.assertTrue(summary.get("unique_listing_ok"))
        self.assertTrue(summary.get("listing_bridge_ok"))
        self.assertTrue(summary.get("listing_band_spread_ok"))
        self.assertTrue(summary.get("cluster_concentration_ok"))
        self.assertTrue(summary.get("top_rank_signature_concentration_ok"))
        self.assertTrue(summary.get("price_band_concentration_ok"))
        self.assertEqual(int(summary.get("scenario_count") or 0), 7)

    def test_cli_writes_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            json_path = Path(td) / "diversity.json"
            md_path = Path(td) / "diversity.md"
            argv = [
                "generate_yangdo_recommendation_diversity_audit.py",
                "--json",
                str(json_path),
                "--md",
                str(md_path),
            ]
            with patch("sys.argv", argv):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("packet_id"), "yangdo_recommendation_diversity_audit_latest")
            self.assertIn("Yangdo Recommendation Diversity Audit", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
