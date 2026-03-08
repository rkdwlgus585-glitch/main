from __future__ import annotations

import unittest

from yangdo_blackbox_api import _maybe_apply_fire_single_license_guarded_prior


class FireGuardedPriorTests(unittest.TestCase):
    def _fire_records(self):
        rows = []
        for idx, (sales3, specialty, price) in enumerate(
            [
                (1.0, 0.8, 0.34),
                (1.1, 0.9, 0.37),
                (1.2, 0.9, 0.39),
                (1.4, 1.0, 0.46),
                (1.5, 1.1, 0.5),
                (1.7, 1.2, 0.56),
                (1.8, 1.3, 0.59),
                (2.0, 1.4, 0.63),
                (2.2, 1.5, 0.68),
                (2.4, 1.6, 0.73),
            ],
            start=1,
        ):
            rows.append(
                {
                    'uid': f'f{idx}',
                    'number': idx,
                    'license_tokens': {'소방'},
                    'license_text': '소방',
                    'sales3_eok': sales3,
                    'specialty': specialty,
                    'current_price_eok': price,
                }
            )
        return rows

    def test_applies_for_fire_single_license_with_signal(self) -> None:
        adjusted = _maybe_apply_fire_single_license_guarded_prior(
            records=self._fire_records(),
            target={'license_tokens': {'소방'}, 'license_text': '소방', 'sales3_eok': 2.0, 'specialty': 1.4},
            total=0.38,
            low=0.30,
            high=0.50,
            public_total=0.38,
            public_low=0.30,
            public_high=0.50,
        )
        self.assertIsNotNone(adjusted)
        self.assertEqual(adjusted['mode'], 'fire_single_license_guarded_prior')
        self.assertGreater(adjusted['adjusted_total_transfer_value_eok'], 0.38)
        self.assertLessEqual(adjusted['adjusted_total_transfer_value_eok'], 0.5834)

    def test_does_not_apply_for_non_fire_sector(self) -> None:
        adjusted = _maybe_apply_fire_single_license_guarded_prior(
            records=self._fire_records(),
            target={'license_tokens': {'전기'}, 'license_text': '전기', 'sales3_eok': 2.0, 'specialty': 1.4},
            total=0.38,
            low=0.30,
            high=0.50,
            public_total=0.38,
            public_low=0.30,
            public_high=0.50,
        )
        self.assertIsNone(adjusted)

    def test_requires_signal_input(self) -> None:
        adjusted = _maybe_apply_fire_single_license_guarded_prior(
            records=self._fire_records(),
            target={'license_tokens': {'소방'}, 'license_text': '소방', 'sales3_eok': None, 'specialty': None},
            total=0.38,
            low=0.30,
            high=0.50,
            public_total=0.38,
            public_low=0.30,
            public_high=0.50,
        )
        self.assertIsNone(adjusted)


if __name__ == '__main__':
    unittest.main()
