import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from permit_precheck_api import PermitUsageStore


class PermitPrecheckUsageStoreTests(unittest.TestCase):
    def _write_thresholds(self, path: Path) -> None:
        payload = {
            "token_estimates": {
                "permit_ok": 900,
                "error": 200,
            },
            "plans": {
                "pro": {
                    "max_usage_events": 10,
                }
            },
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def test_insert_precheck_usage_persists_canonical_inputs_without_losing_zero_false(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db_path = root / "permit.sqlite3"
            thresholds_path = root / "thresholds.json"
            self._write_thresholds(thresholds_path)

            store = PermitUsageStore(db_path=str(db_path), thresholds_path=str(thresholds_path))
            snap = store.insert_precheck_usage(
                tenant_id="Tenant-A",
                plan="pro",
                request_id="req-permit-001",
                source="widget",
                page_url="https://seoulmna.kr/tools/permit",
                requested_at="2026-03-06T18:00:00",
                inputs={
                    "service_code": "P001",
                    "service_name": "테스트업",
                    "capital_eok": 0,
                    "raw_capital_input": "0",
                    "technicians_count": "0",
                    "equipment_count": 0,
                    "deposit_days": 0,
                    "qualification_count": "0",
                    "office_secured": "false",
                    "facility_secured": "0",
                    "guarantee_secured": False,
                    "insurance_secured": "1",
                    "qualification_secured": "true",
                    "document_ready": "no",
                    "safety_secured": "yes",
                },
                result={
                    "ok": True,
                    "industry_name": "테스트업",
                    "group_rule_id": "GR-01",
                    "overall_status": "shortfall",
                    "overall_ok": False,
                    "manual_review_required": True,
                    "coverage_status": "partial",
                    "mapping_confidence": 0.55,
                    "typed_criteria_total": 3,
                    "pending_criteria_count": 1,
                    "blocking_failure_count": 1,
                    "unknown_blocking_count": 0,
                    "capital_input_suspicious": False,
                    "required_summary": {
                        "capital": {"ok": False},
                        "technicians": {"ok": True},
                        "equipment": {"ok": False},
                    },
                    "next_actions": ["보완 필요"],
                },
                response_tier="detail",
            )

            self.assertEqual(snap["usage_events"], 1)
            self.assertEqual(snap["ok_events"], 1)
            self.assertEqual(snap["error_events"], 0)

            conn = sqlite3.connect(str(db_path))
            try:
                usage_row = conn.execute(
                    """
                    SELECT input_capital, ok_capital, ok_engineer, ok_office, raw_json
                    FROM usage_events
                    """
                ).fetchone()
                self.assertEqual(usage_row[0], "0")
                self.assertEqual(usage_row[1], "0")
                self.assertEqual(usage_row[2], "1")
                self.assertEqual(usage_row[3], "0")

                raw_payload = json.loads(usage_row[4])
                self.assertEqual(raw_payload["request_id"], "req-permit-001")
                self.assertEqual(raw_payload["inputs"]["capital_eok"], 0.0)
                self.assertEqual(raw_payload["inputs"]["office_secured"], 0)
                self.assertEqual(raw_payload["result"]["coverage_status"], "partial")

                detail_row = conn.execute(
                    """
                    SELECT request_id, tenant_id, capital_eok, raw_capital_input,
                           technicians_count, equipment_count, qualification_count,
                           office_secured, facility_secured, guarantee_secured, insurance_secured,
                           qualification_secured, document_ready, safety_secured,
                           manual_review_required, capital_input_suspicious
                    FROM permit_precheck_inputs
                    """
                ).fetchone()
                self.assertEqual(detail_row[0], "req-permit-001")
                self.assertEqual(detail_row[1], "tenant-a")
                self.assertEqual(detail_row[2], 0.0)
                self.assertEqual(detail_row[3], "0")
                self.assertEqual(detail_row[4], 0)
                self.assertEqual(detail_row[5], 0)
                self.assertEqual(detail_row[6], 0)
                self.assertEqual(detail_row[7], 0)
                self.assertEqual(detail_row[8], 0)
                self.assertEqual(detail_row[9], 0)
                self.assertEqual(detail_row[10], 1)
                self.assertEqual(detail_row[11], 1)
                self.assertEqual(detail_row[12], 0)
                self.assertEqual(detail_row[13], 1)
                self.assertEqual(detail_row[14], 1)
                self.assertEqual(detail_row[15], 0)
            finally:
                conn.close()

    def test_init_db_migrates_legacy_usage_tables_before_insert(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db_path = root / "legacy.sqlite3"
            thresholds_path = root / "thresholds.json"
            self._write_thresholds(thresholds_path)

            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("CREATE TABLE usage_events (received_at TEXT)")
                conn.execute(
                    """
                    CREATE TABLE tenant_usage_monthly (
                        tenant_id TEXT NOT NULL,
                        year_month TEXT NOT NULL,
                        service TEXT NOT NULL,
                        usage_events INTEGER NOT NULL DEFAULT 0,
                        estimated_tokens INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (tenant_id, year_month, service)
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

            store = PermitUsageStore(db_path=str(db_path), thresholds_path=str(thresholds_path))
            store.insert_precheck_usage(
                tenant_id="tenant-b",
                plan="pro",
                request_id="req-legacy-001",
                source="widget",
                page_url="https://example.com/permit",
                requested_at="2026-03-06T18:05:00",
                inputs={"service_code": "P002", "service_name": "레거시업", "capital_eok": 1.2},
                result={
                    "ok": False,
                    "error": "mapping_required",
                    "industry_name": "레거시업",
                    "overall_status": "manual_review",
                    "overall_ok": False,
                    "manual_review_required": True,
                    "coverage_status": "pending",
                    "typed_criteria_total": 0,
                    "pending_criteria_count": 0,
                    "blocking_failure_count": 0,
                    "unknown_blocking_count": 0,
                    "capital_input_suspicious": False,
                    "required_summary": {},
                },
                response_tier="summary",
            )

            conn = sqlite3.connect(str(db_path))
            try:
                usage_columns = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(usage_events)").fetchall()
                }
                self.assertIn("raw_json", usage_columns)
                self.assertIn("input_capital", usage_columns)
                self.assertIn("ok_office", usage_columns)

                monthly_columns = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(tenant_usage_monthly)").fetchall()
                }
                self.assertIn("ok_events", monthly_columns)
                self.assertIn("error_events", monthly_columns)

                detail_count = conn.execute("SELECT COUNT(*) FROM permit_precheck_inputs").fetchone()[0]
                self.assertEqual(detail_count, 1)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
