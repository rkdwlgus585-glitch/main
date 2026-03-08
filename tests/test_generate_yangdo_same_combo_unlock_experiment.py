from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.generate_yangdo_same_combo_unlock_experiment import build_report


class GenerateYangdoSameComboUnlockExperimentTests(unittest.TestCase):
    @patch("scripts.generate_yangdo_same_combo_unlock_experiment.yangdo_blackbox_api.YangdoBlackboxEstimator")
    def test_marks_alias_first_when_exact_single_missing(self, estimator_cls) -> None:
        estimator = estimator_cls.return_value
        estimator._snapshot.return_value = (
            [
                {"uid": "a", "number": 1, "license_tokens": {"시설물", "토목"}, "current_price_eok": 1.7, "sales3_eok": 1.0, "specialty": 0.5},
                {"uid": "b", "number": 2, "license_tokens": {"시설물", "건축"}, "current_price_eok": 1.9, "sales3_eok": 1.0, "specialty": 0.5},
            ],
            {},
            {},
        )
        payload = build_report(
            balance_cv={"record_rows": []},
            cohort_recovery={"sector_candidates": [{"sector": "시설물", "decision": "unlock_same_combo_support_now"}]},
            sector_audit={"sectors": [{"sector": "시설물", "aliases": ["시설물"]}]},
        )
        self.assertEqual(payload["sector_results"][0]["decision"], "alias_or_catalog_first")

    @patch("scripts.generate_yangdo_same_combo_unlock_experiment.yangdo_blackbox_api.YangdoBlackboxEstimator")
    def test_marks_micro_pool_when_exact_single_small(self, estimator_cls) -> None:
        estimator = estimator_cls.return_value
        records = [
            {"uid": "a", "number": 1, "license_tokens": {"석공"}, "current_price_eok": 0.6, "sales3_eok": 1.0, "specialty": 0.5},
            {"uid": "b", "number": 2, "license_tokens": {"석공"}, "current_price_eok": 0.7, "sales3_eok": 1.0, "specialty": 0.5},
            {"uid": "c", "number": 3, "license_tokens": {"석공"}, "current_price_eok": 0.8, "sales3_eok": 1.0, "specialty": 0.5},
            {"uid": "d", "number": 4, "license_tokens": {"석공"}, "current_price_eok": 0.9, "sales3_eok": 1.0, "specialty": 0.5},
        ]
        estimator._snapshot.return_value = (records, {}, {})
        payload = build_report(
            balance_cv={
                "record_rows": [
                    {"uid": "a", "number": 1, "actual_price_eok": 0.6, "engine_internal_pred_eok": 0.4},
                    {"uid": "b", "number": 2, "actual_price_eok": 0.7, "engine_internal_pred_eok": 0.4},
                    {"uid": "c", "number": 3, "actual_price_eok": 0.8, "engine_internal_pred_eok": 0.4},
                    {"uid": "d", "number": 4, "actual_price_eok": 0.9, "engine_internal_pred_eok": 0.4},
                ]
            },
            cohort_recovery={"sector_candidates": [{"sector": "석공", "decision": "unlock_same_combo_support_now"}]},
            sector_audit={"sectors": [{"sector": "석공", "aliases": ["석공"]}]},
        )
        self.assertEqual(payload["sector_results"][0]["decision"], "micro_pool_guard_only")


if __name__ == "__main__":
    unittest.main()
