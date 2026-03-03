import unittest

import acquisition_calculator


class AcquisitionCalculatorPageTest(unittest.TestCase):
    def test_required_fund_and_corp_registration_logic_are_present(self):
        html = acquisition_calculator.build_page_html()
        self.assertIn("const normalizeClassCode = (klass)", html)
        self.assertIn("option value=\"general\">종합건설업</option>", html)
        self.assertIn("option value=\"special\">전문건설업</option>", html)
        self.assertIn("세금/수수료 합계", html)
        self.assertIn("전문직 수임료 합계", html)
        self.assertIn("기업진단기관 수수료", html)
        self.assertIn("center_total_required_manwon", html)
        self.assertIn("법인 등기 유형", html)
        self.assertIn("자본금</span>", html)
        self.assertIn("공제조합 출자예치금</span>", html)
        self.assertIn("총 필요자금(기준)", html)
        self.assertNotIn("공제조합 준비자금 가중", html)


if __name__ == "__main__":
    unittest.main()
