import unittest

import lead_intake


class LeadIntakeIntentTest(unittest.TestCase):
    def test_new_registration_is_normalized_to_permit_track(self):
        self.assertEqual(lead_intake._infer_intent("건설면허 신규등록 상담"), "인허가(신규등록)")
        self.assertEqual(lead_intake._normalize_intent_label("신규등록"), "인허가(신규등록)")
        self.assertEqual(lead_intake._normalize_intent_label("인허가 사전검토"), "인허가(신규등록)")

    def test_default_action_uses_permit_wording(self):
        action = lead_intake._default_next_action("인허가(신규등록)", "보통")
        self.assertIn("인허가 등록기준 체크리스트", action)


if __name__ == "__main__":
    unittest.main()
