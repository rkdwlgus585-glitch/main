import unittest

import kb


class KbFactValidationTest(unittest.TestCase):
    def test_validate_fact_accepts_korean_eok_thousand_format(self):
        text = (
            "토목건축공사업 법인 자본금은 8억 5천만원입니다. "
            "건축공사업 법인 자본금은 3억 5천만원입니다. "
            "토목공사업 법인 자본금은 5억원입니다."
        )
        errors = kb.validate_fact(text)
        self.assertEqual(errors, [])

    def test_validate_fact_avoids_substring_false_positive(self):
        text = "토목건축공사업 법인 자본금은 8억 5천만원입니다."
        errors = kb.validate_fact(text)
        self.assertFalse(any(e.get("업종") == "건축공사업" for e in errors))

    def test_validate_fact_detects_wrong_capital_amount(self):
        text = "건축공사업 법인 자본금은 3억원입니다."
        errors = kb.validate_fact(text)
        self.assertTrue(any(e.get("type") == "자본금_오류" for e in errors))


if __name__ == "__main__":
    unittest.main()
