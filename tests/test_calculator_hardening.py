import importlib
import unittest

import acquisition_calculator
import yangdo_blackbox_api


allmod = importlib.import_module("all")


def _make_row(number, uid, license_name, price):
    row = [""] * 41
    row[0] = str(number)
    row[2] = str(license_name)
    row[3] = "2020"
    row[4] = "20"
    row[8] = "3"
    row[9] = "4"
    row[12] = "5"
    row[18] = str(price)
    row[19] = "1.5"
    row[21] = "20"
    row[23] = "300"
    row[30] = "0.3"
    row[33] = "1.0억~1.2억 / 1.1억"
    row[34] = str(uid)
    return row


class CalculatorHardeningTest(unittest.TestCase):
    def test_acquisition_profile_matching_helpers_exist(self):
        html = acquisition_calculator.build_page_html()
        self.assertIn("const normalizeProfileKey = (v)", html)
        self.assertIn("const findProfileByText = (raw)", html)
        self.assertIn("기준값을 찾지 못했습니다.", html)

    def test_yangdo_consistency_and_sanitize_helpers_exist(self):
        header = [""] * 41
        rows = [
            _make_row(7001, 9001, "전기", "1.9억"),
            _make_row(7002, 9002, "전기", "2.2억"),
            _make_row(7003, 9003, "전기", "2.4억"),
            _make_row(7004, 9004, "전기", "2.6억"),
        ]
        records = allmod._build_estimate_records([header, *rows])
        train = allmod._build_yangdo_calculator_training_dataset(records)
        meta = allmod._build_yangdo_calculator_meta(records, train)
        html = allmod._build_yangdo_calculator_page_html(train, meta, view_mode="customer")
        self.assertIn("const applyNeighborConsistencyGuard = (center, low, high, neighbors", html)
        self.assertIn("const sanitizePhone = (v)", html)
        self.assertIn("const sanitizeEmail = (v)", html)
        self.assertIn("id=\"in-sales-input-mode\"", html)
        self.assertIn("const isSeparateBalanceGroupToken = (raw)", html)
        self.assertIn("const isSeparateBalanceGroupTarget = (target)", html)
        self.assertIn("const requiresReorgSelectionByLicense = (licenseRaw)", html)
        self.assertIn("const syncReorgModeRequirement = ()", html)

    def test_blackbox_balance_exclusion_groups(self):
        est = yangdo_blackbox_api.YangdoBlackboxEstimator()
        self.assertTrue(est._is_balance_separate_paid_group({"license_text": "전기공사업", "license_tokens": {"전기"}}))
        self.assertTrue(est._is_balance_separate_paid_group({"license_text": "정보통신공사업", "license_tokens": {"정보통신"}}))
        self.assertTrue(est._is_balance_separate_paid_group({"license_text": "전문소방시설공사업", "license_tokens": {"소방"}}))
        self.assertFalse(est._is_balance_separate_paid_group({"license_text": "토목공사업", "license_tokens": {"토목"}}))


if __name__ == "__main__":
    unittest.main()
