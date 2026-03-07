import unittest

import yangdo_blackbox_api


class BalanceBaseTargetCenterTest(unittest.TestCase):
    def test_balance_base_target_center_uses_core_beta_and_full_balance_component(self):
        value = yangdo_blackbox_api._balance_base_target_center(1.0, 1.0, 0.92)
        self.assertAlmostEqual(value, 1.705, places=9)

    def test_balance_base_target_center_has_floor(self):
        value = yangdo_blackbox_api._balance_base_target_center(0.0, 0.0, 0.92)
        self.assertAlmostEqual(value, 0.05, places=9)


if __name__ == "__main__":
    unittest.main()
