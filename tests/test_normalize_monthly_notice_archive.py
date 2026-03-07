import tempfile
import unittest
from pathlib import Path

from scripts import normalize_monthly_notice_archive as normalize_notice


class NormalizeMonthlyNoticeArchiveTest(unittest.TestCase):
    def test_normalizer_inserts_legal_notice_and_business_label(self) -> None:
        temp_dir = Path(tempfile.mkdtemp(prefix="notice-normalize-"))
        body_path = temp_dir / "body.html"
        body_path.write_text(
            """
            <div>
              <p>소개 문구</p>
              <h2>목록</h2>
              <ul>
                <li><a href="https://seoulmna.co.kr/mna/1">[매물 1 | 면허년도 2023 | 양도가 협의 | 지방]</a></li>
              </ul>
              <img src="https://example.com/a.jpg">
            </div>
            """,
            encoding="utf-8",
        )

        result = normalize_notice._ensure_body_compliance(body_path)
        body = body_path.read_text(encoding="utf-8")

        self.assertEqual(result["changed"], 1)
        self.assertEqual(result["legal_inserted"], 1)
        self.assertEqual(result["listing_titles_fixed"], 1)
        self.assertEqual(result["image_alt_fixed"], 1)
        self.assertIn("최종 거래 조건과 양도가", body)
        self.assertIn("건설업 양도", body)
        self.assertIn("alt=", body)


if __name__ == "__main__":
    unittest.main()
