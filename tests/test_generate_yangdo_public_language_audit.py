import unittest

from scripts.generate_yangdo_public_language_audit import build_public_language_audit, render_markdown


class GenerateYangdoPublicLanguageAuditTests(unittest.TestCase):
    def test_build_public_language_audit_reports_remaining_phrases(self):
        payload = build_public_language_audit(
            source_text="\n".join(
                [
                    'title = "추천 액션 3단계"',
                    'label = "근거 표 상세 비교"',
                    'note = "확인 후 안내"',
                ]
            )
        )

        self.assertTrue(payload["summary"]["packet_ready"])
        self.assertEqual(payload["summary"]["remaining_phrase_count"], 3)
        self.assertEqual(payload["summary"]["jargon_total"], 3)
        self.assertFalse(payload["summary"]["public_language_ready"])
        phrases = {item["phrase"] for item in payload["top_blockers"]}
        self.assertIn("근거 표", phrases)
        self.assertIn("확인 후 안내", phrases)

        markdown = render_markdown(payload)
        self.assertIn("Yangdo Public Language Audit", markdown)
        self.assertIn("remaining_phrase_count", markdown)

    def test_build_public_language_audit_reports_ready_when_no_phrases_remain(self):
        payload = build_public_language_audit(
            source_text="\n".join(
                [
                    'title = "지금 하면 좋은 순서 3단계"',
                    'label = "비슷한 사례 표 자세히 보기"',
                    'note = "먼저 확인 필요"',
                ]
            )
        )

        self.assertEqual(payload["summary"]["remaining_phrase_count"], 0)
        self.assertEqual(payload["summary"]["jargon_total"], 0)
        self.assertTrue(payload["summary"]["public_language_ready"])


if __name__ == "__main__":
    unittest.main()
