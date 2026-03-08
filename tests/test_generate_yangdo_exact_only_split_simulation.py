from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.generate_yangdo_exact_only_split_simulation import build_report


class GenerateYangdoExactOnlySplitSimulationTests(unittest.TestCase):
    @patch("scripts.generate_yangdo_exact_only_split_simulation.yangdo_blackbox_api.YangdoBlackboxEstimator")
    def test_reports_candidate_when_bounded_prior_beats_baseline(self, estimator_cls) -> None:
        estimator = estimator_cls.return_value
        records = []
        prices = [2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6, 3.8, 4.0, 4.2]
        for i, price in enumerate(prices, start=1):
            records.append(
                {
                    "uid": f"u{i}",
                    "number": i,
                    "license_tokens": {"토목"},
                    "current_price_eok": price,
                    "sales3_eok": 10.0,
                    "specialty": 5.0,
                }
            )
        estimator._snapshot.return_value = (records, {}, {})

        payload = build_report(
            balance_cv={
                "record_rows": [
                    {"uid": f"u{i}", "number": i, "actual_price_eok": price, "engine_internal_pred_eok": 1.5}
                    for i, price in enumerate(prices, start=1)
                ]
            },
            split_experiment={
                "sector_candidates": [
                    {"sector": "토목", "decision": "run_split_simulation_now"}
                ]
            },
        )
        row = payload["sector_results"][0]
        self.assertEqual(row["decision"], "candidate_for_guarded_patch")

    @patch("scripts.generate_yangdo_exact_only_split_simulation.yangdo_blackbox_api.YangdoBlackboxEstimator")
    def test_skips_sector_without_enough_peers(self, estimator_cls) -> None:
        estimator = estimator_cls.return_value
        records = [
            {"uid": "u1", "number": 1, "license_tokens": {"토목"}, "current_price_eok": 2.0, "sales3_eok": 1.0, "specialty": 1.0},
            {"uid": "u2", "number": 2, "license_tokens": {"토목"}, "current_price_eok": 2.2, "sales3_eok": 1.0, "specialty": 1.0},
        ]
        estimator._snapshot.return_value = (records, {}, {})

        payload = build_report(
            balance_cv={
                "record_rows": [
                    {"uid": "u1", "number": 1, "actual_price_eok": 2.0, "engine_internal_pred_eok": 1.1},
                    {"uid": "u2", "number": 2, "actual_price_eok": 2.2, "engine_internal_pred_eok": 1.1},
                ]
            },
            split_experiment={
                "sector_candidates": [
                    {"sector": "토목", "decision": "run_split_simulation_now"}
                ]
            },
        )
        row = payload["sector_results"][0]
        self.assertEqual(row["simulated_record_count"], 0)
        self.assertEqual(row["decision"], "hold_insufficient_exact_pool")


if __name__ == "__main__":
    unittest.main()
