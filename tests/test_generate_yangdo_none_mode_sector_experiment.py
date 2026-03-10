from __future__ import annotations

import unittest

from scripts.generate_yangdo_none_mode_sector_experiment import (
    SECTOR_ELECTRIC,
    SECTOR_FIRE,
    SECTOR_INFOCOMM,
    EvalRow,
    _candidate_prediction,
    _candidate_score,
    _focus_sectors_from_audit,
)


class FocusSectorTests(unittest.TestCase):
    def test_focus_sectors_come_from_sector_audit_action(self) -> None:
        report = {
            'next_actions': [
                {
                    'id': 'none_mode_sector_calibration',
                    'focus_sectors': [SECTOR_ELECTRIC, SECTOR_INFOCOMM, SECTOR_FIRE],
                }
            ]
        }
        self.assertEqual(_focus_sectors_from_audit(report), [SECTOR_ELECTRIC, SECTOR_INFOCOMM, SECTOR_FIRE])


class CandidatePredictionTests(unittest.TestCase):
    def test_candidate_prediction_respects_floor_and_cap(self) -> None:
        row = EvalRow(
            sector=SECTOR_ELECTRIC,
            uid='u1',
            number=1,
            actual_price_eok=1.0,
            current_pred_eok=0.5,
            signal_eok=10.0,
            prior_estimate_eok=1.8,
            q25_price_eok=0.9,
            q55_price_eok=1.0,
            q60_price_eok=1.05,
            q65_price_eok=1.1,
            q70_price_eok=1.2,
            q75_price_eok=1.3,
        )
        predicted = _candidate_prediction(row, blend=0.55, cap_quantile=0.55, cap_mult=0.98)
        self.assertAlmostEqual(predicted, 0.81, places=6)


class CandidateScoreTests(unittest.TestCase):
    def test_candidate_score_penalizes_excess_overpricing(self) -> None:
        baseline = {
            'pred_gt_actual_1_5x': 1,
            'median_abs_pct': 40.0,
        }
        safer = {
            'under_67_share': 0.40,
            'pred_gt_actual_1_5x': 2,
            'median_abs_pct': 30.0,
        }
        riskier = {
            'under_67_share': 0.35,
            'pred_gt_actual_1_5x': 6,
            'median_abs_pct': 30.0,
        }
        self.assertLess(_candidate_score(safer, baseline, SECTOR_INFOCOMM), _candidate_score(riskier, baseline, SECTOR_INFOCOMM))


if __name__ == '__main__':
    unittest.main()
