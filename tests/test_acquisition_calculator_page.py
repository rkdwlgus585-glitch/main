import unittest

import acquisition_calculator


class AcquisitionCalculatorPageTest(unittest.TestCase):
    def test_required_fund_and_corp_registration_logic_are_present(self):
        html = acquisition_calculator.build_page_html()
        self.assertIn("const normalizeClassCode = (klass)", html)
        self.assertIn('id="acq-license-type"', html)
        self.assertIn('id="acq-corp-state"', html)
        self.assertIn('id="acq-capital"', html)
        self.assertIn('id="acq-guarantee"', html)
        self.assertIn("center_total_required_manwon", html)
        self.assertIn("총 필요자금(기준)", html)
        self.assertIn("공제조합 출자예치금(억, 자본금 내 배정)", html)
        self.assertIn('value="토목건축공사업(종합)"', html)
        self.assertIn('value="실내건축공사업(전문)"', html)
        self.assertNotIn('option value="general">', html)
        self.assertNotIn('option value="special">', html)


if __name__ == "__main__":
    unittest.main()
