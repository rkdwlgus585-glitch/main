from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.generate_yangdo_exact_pool_split_experiment import build_report


class GenerateYangdoExactPoolSplitExperimentTests(unittest.TestCase):
    @patch("scripts.generate_yangdo_exact_pool_split_experiment.yangdo_blackbox_api.YangdoBlackboxEstimator")
    def test_marks_run_split_for_large_divergence(self, estimator_cls) -> None:
        estimator = estimator_cls.return_value
        records = [
            {"license_tokens": {"토목"}, "current_price_eok": 2.0, "sales3_eok": 5.0, "specialty": 1.0},
            {"license_tokens": {"토목"}, "current_price_eok": 3.0, "sales3_eok": 4.0, "specialty": 1.0},
            {"license_tokens": {"토목"}, "current_price_eok": 2.8, "sales3_eok": 3.0, "specialty": 1.0},
            {"license_tokens": {"토목"}, "current_price_eok": 3.1, "sales3_eok": 2.0, "specialty": 1.0},
            {"license_tokens": {"토목"}, "current_price_eok": 2.7, "sales3_eok": 2.0, "specialty": 1.0},
            {"license_tokens": {"토목"}, "current_price_eok": 2.9, "sales3_eok": 2.0, "specialty": 1.0},
            {"license_tokens": {"토목"}, "current_price_eok": 3.2, "sales3_eok": 2.0, "specialty": 1.0},
            {"license_tokens": {"토목"}, "current_price_eok": 2.6, "sales3_eok": 2.0, "specialty": 1.0},
            {"license_tokens": {"토목", "건축"}, "current_price_eok": 6.0, "sales3_eok": 10.0, "specialty": 1.0},
            {"license_tokens": {"토목", "건축"}, "current_price_eok": 6.4, "sales3_eok": 10.0, "specialty": 1.0},
            {"license_tokens": {"토목", "건축"}, "current_price_eok": 6.1, "sales3_eok": 10.0, "specialty": 1.0},
            {"license_tokens": {"토목", "건축"}, "current_price_eok": 6.3, "sales3_eok": 10.0, "specialty": 1.0},
            {"license_tokens": {"토목", "건축"}, "current_price_eok": 6.5, "sales3_eok": 10.0, "specialty": 1.0},
            {"license_tokens": {"토목", "건축"}, "current_price_eok": 6.2, "sales3_eok": 10.0, "specialty": 1.0},
            {"license_tokens": {"토목", "건축"}, "current_price_eok": 6.6, "sales3_eok": 10.0, "specialty": 1.0},
            {"license_tokens": {"토목", "건축"}, "current_price_eok": 6.7, "sales3_eok": 10.0, "specialty": 1.0},
        ]
        estimator._snapshot.return_value = (records, {}, {})

        payload = build_report(
            sector_audit={"sectors": [{"sector": "토목", "aliases": ["토목"]}]},
            focus=["토목"],
        )
        self.assertEqual(payload["sector_candidates"][0]["decision"], "run_split_simulation_now")

    @patch("scripts.generate_yangdo_exact_pool_split_experiment.yangdo_blackbox_api.YangdoBlackboxEstimator")
    def test_marks_alias_or_catalog_first_when_exact_pool_missing(self, estimator_cls) -> None:
        estimator = estimator_cls.return_value
        records = [
            {"license_tokens": {"석면", "비계"}, "current_price_eok": 1.8, "sales3_eok": 1.0, "specialty": 0.5},
            {"license_tokens": {"석면", "비계"}, "current_price_eok": 1.9, "sales3_eok": 1.0, "specialty": 0.5},
        ]
        estimator._snapshot.return_value = (records, {}, {})

        payload = build_report(
            sector_audit={"sectors": [{"sector": "석면", "aliases": ["석면"]}]},
            focus=["석면"],
        )
        self.assertEqual(payload["sector_candidates"][0]["decision"], "alias_or_catalog_first")


if __name__ == "__main__":
    unittest.main()
