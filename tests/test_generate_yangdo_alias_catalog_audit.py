from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.generate_yangdo_alias_catalog_audit import build_report


class GenerateYangdoAliasCatalogAuditTests(unittest.TestCase):
    @patch("scripts.generate_yangdo_alias_catalog_audit.yangdo_blackbox_api.YangdoBlackboxEstimator")
    def test_marks_bundle_only_market_structure_when_alias_exists_without_exact(self, estimator_cls) -> None:
        estimator = estimator_cls.return_value
        estimator._snapshot.return_value = (
            [
                {"license_tokens": {"석면", "비계"}, "current_price_eok": 1.8},
                {"license_tokens": {"석면", "비계"}, "current_price_eok": 1.9},
            ],
            {},
            {},
        )
        payload = build_report(
            split_experiment={"sector_candidates": [{"sector": "석면", "decision": "alias_or_catalog_first"}]},
            unlock_experiment={"sector_results": []},
            sector_audit={"sectors": [{"sector": "석면", "aliases": ["석면"]}]},
        )
        self.assertEqual(payload["sector_results"][0]["decision"], "bundle_only_market_structure")

    @patch("scripts.generate_yangdo_alias_catalog_audit.yangdo_blackbox_api.YangdoBlackboxEstimator")
    def test_marks_canonical_alias_candidate_when_related_token_exists_without_alias(self, estimator_cls) -> None:
        estimator = estimator_cls.return_value
        estimator._snapshot.return_value = (
            [
                {"license_tokens": {"시설"}, "current_price_eok": 1.3},
                {"license_tokens": {"조경시설"}, "current_price_eok": 1.1},
            ],
            {},
            {},
        )
        payload = build_report(
            split_experiment={"sector_candidates": []},
            unlock_experiment={"sector_results": [{"sector": "시설물", "decision": "alias_or_catalog_first"}]},
            sector_audit={"sectors": [{"sector": "시설물", "aliases": ["시설물"]}]},
        )
        self.assertEqual(payload["sector_results"][0]["decision"], "canonical_alias_candidate")


if __name__ == "__main__":
    unittest.main()
