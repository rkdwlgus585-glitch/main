import unittest

import yangdo_blackbox_api


class BalanceExclusionBehaviorTest(unittest.TestCase):
    def setUp(self):
        self.est = yangdo_blackbox_api.YangdoBlackboxEstimator()

    @staticmethod
    def _candidate(token_text: str):
        return {
            "license_text": token_text,
            "license_tokens": {token_text},
            "specialty": None,
            "sales3_eok": None,
            "sales5_eok": None,
            "license_year": None,
            "debt_ratio": None,
            "liq_ratio": None,
            "capital_eok": None,
            "balance_eok": 5.0,
            "surplus_eok": None,
            "company_type": "",
        }

    @staticmethod
    def _target(token_text: str, balance_eok: float):
        return {
            "license_text": token_text,
            "raw_license_key": token_text,
            "license_tokens": {token_text},
            "specialty": None,
            "sales3_eok": None,
            "sales5_eok": None,
            "license_year": None,
            "debt_ratio": None,
            "liq_ratio": None,
            "capital_eok": None,
            "balance_eok": float(balance_eok),
            "surplus_eok": None,
            "company_type": "",
        }

    def test_balance_change_does_not_affect_excluded_group_score(self):
        electric = "\uC804\uAE30"
        cand = self._candidate(electric)
        t1 = self._target(electric, 0.5)
        t2 = self._target(electric, 50.0)

        s1 = self.est._neighbor_score(t1, cand)
        s2 = self.est._neighbor_score(t2, cand)

        self.assertTrue(self.est._is_balance_separate_paid_group(t1))
        self.assertAlmostEqual(s1, s2, places=9)

    def test_balance_change_affects_non_excluded_group_score(self):
        civil = "\uD1A0\uBAA9"
        cand = self._candidate(civil)
        t1 = self._target(civil, 5.0)
        t2 = self._target(civil, 50.0)

        s1 = self.est._neighbor_score(t1, cand)
        s2 = self.est._neighbor_score(t2, cand)

        self.assertFalse(self.est._is_balance_separate_paid_group(t1))
        self.assertNotEqual(round(s1, 6), round(s2, 6))


if __name__ == "__main__":
    unittest.main()
