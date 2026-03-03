import tempfile
import unittest
from pathlib import Path

import yangdo_consult_api as api


class YangdoConsultApiTest(unittest.TestCase):
    def test_priority_info_with_urgent_text(self):
        priority, urgency = api._priority_info(
            {
                "summary_text": "긴급 진행 요청",
                "customer_note": "오늘 안에 연락 부탁",
                "estimated_confidence": "보통 (66.0)",
                "customer_phone": "010-1234-5678",
            }
        )
        self.assertEqual(priority, "우선")
        self.assertEqual(urgency, "긴급")

    def test_build_tags_contains_license_tokens(self):
        tags = api._build_tags(
            {
                "source": "seoulmna_kr_yangdo_ai",
                "page_mode": "customer",
                "license_text": "전기/소방",
                "estimated_neighbors": "8건",
            }
        )
        self.assertIn("전기", tags)
        self.assertIn("소방", tags)
        self.assertIn("ai산정", tags)

    def test_store_insert_and_update(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "consult.sqlite3"
            store = api.ConsultStore(str(db_path))
            req_id = store.insert(
                {
                    "source": "test",
                    "page_mode": "customer",
                    "subject": "제목",
                    "summary_text": "본문",
                    "customer_name": "홍길동",
                    "customer_phone": "010-0000-0000",
                    "license_text": "토목",
                },
                tags=["토목", "ai산정"],
                priority="우선",
                urgency="긴급",
            )
            self.assertGreater(req_id, 0)
            store.update_crm_result(req_id, "inserted", "LD123")

            usage_id = store.insert_usage(
                {
                    "source": "seoulmna_kr_yangdo_ai",
                    "page_mode": "customer",
                    "status": "ok",
                    "license_text": "건축",
                    "output_range": "1.2억~1.4억",
                }
            )
            self.assertGreater(usage_id, 0)


if __name__ == "__main__":
    unittest.main()
