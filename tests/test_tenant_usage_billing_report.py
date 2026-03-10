import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.tenant_usage_billing_report import build_report, run_report


class TenantUsageBillingReportTests(unittest.TestCase):
    def _write_registry(self, path: Path) -> None:
        payload = {
            "default_tenant_id": "seoul_main",
            "tenants": [
                {
                    "tenant_id": "seoul_main",
                    "display_name": "SeoulMNA",
                    "enabled": True,
                    "plan": "standard",
                    "hosts": ["seoulmna.kr", "www.seoulmna.kr"],
                }
            ],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _write_thresholds(self, path: Path, *, included_tokens: int = 1_000_000, max_usage_events: int = 4_000) -> None:
        payload = {
            "pricing": {
                "input_rate_per_1m": 0.4,
                "output_rate_per_1m": 1.6,
                "input_token_ratio": 0.7,
            },
            "token_estimates": {
                "yangdo_ok": 1200,
                "permit_ok": 900,
                "unknown_ok": 700,
                "error": 200,
            },
            "plans": {
                "standard": {
                    "included_tokens": included_tokens,
                    "warn_ratio": 0.8,
                    "max_usage_events": max_usage_events,
                    "overage_price_per_1k_usd": 0.002,
                    "upgrade_target": "pro",
                }
            },
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _write_db(self, path: Path, rows: list[tuple[str, str, str, str, str]]) -> None:
        conn = sqlite3.connect(str(path))
        try:
            conn.execute(
                """
                CREATE TABLE usage_events (
                    page_mode TEXT,
                    status TEXT,
                    source TEXT,
                    page_url TEXT,
                    received_at TEXT
                )
                """
            )
            conn.executemany(
                "INSERT INTO usage_events (page_mode, status, source, page_url, received_at) VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        finally:
            conn.close()

    def test_build_report_maps_tenant_and_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "tenant_registry.json"
            thresholds = root / "plan_thresholds.json"
            db_path = root / "usage.sqlite3"

            self._write_registry(registry)
            self._write_thresholds(thresholds)
            self._write_db(
                db_path,
                [
                    ("yangdo", "ok", "widget", "https://seoulmna.kr/tool", "2026-03-02T10:00:00"),
                    ("permit", "error", "widget", "https://unknown.example.com/tool", "2026-03-02T11:00:00"),
                ],
            )

            report = build_report(
                db_path=db_path,
                registry_path=registry,
                thresholds_path=thresholds,
                year=2026,
                month=3,
            )

            self.assertEqual(report["summary"]["usage_row_count"], 2)
            by_id = {row["tenant_id"]: row for row in report["tenants"]}
            self.assertEqual(by_id["seoul_main"]["usage_events"], 1)
            self.assertEqual(by_id["unknown"]["usage_events"], 1)
            self.assertEqual(by_id["unknown"]["recommended_action"], "investigate_unknown_host")

    def test_run_report_strict_fails_when_action_required(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "tenant_registry.json"
            thresholds = root / "plan_thresholds.json"
            db_path = root / "usage.sqlite3"
            report_path = root / "report.json"

            self._write_registry(registry)
            self._write_thresholds(thresholds, included_tokens=500)
            self._write_db(
                db_path,
                [("yangdo", "ok", "widget", "https://seoulmna.kr/tool", "2026-03-02T10:00:00")],
            )

            code = run_report(
                db_path=db_path,
                registry_path=registry,
                thresholds_path=thresholds,
                report_path=report_path,
                year=2026,
                month=3,
                strict=True,
            )

            self.assertEqual(code, 1)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertGreater(payload["summary"]["action_required_count"], 0)

    def test_build_report_handles_missing_db(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "tenant_registry.json"
            thresholds = root / "plan_thresholds.json"

            self._write_registry(registry)
            self._write_thresholds(thresholds)

            report = build_report(
                db_path=root / "missing.sqlite3",
                registry_path=registry,
                thresholds_path=thresholds,
                year=2026,
                month=3,
            )

            self.assertEqual(report["summary"]["usage_row_count"], 0)
            self.assertEqual(report["summary"]["total_estimated_tokens"], 0)
            self.assertEqual(report["summary"]["data_warning"], "")

    def test_build_report_handles_missing_table(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "tenant_registry.json"
            thresholds = root / "plan_thresholds.json"
            db_path = root / "usage.sqlite3"

            self._write_registry(registry)
            self._write_thresholds(thresholds)

            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("CREATE TABLE another_table (id INTEGER)")
                conn.commit()
            finally:
                conn.close()

            report = build_report(
                db_path=db_path,
                registry_path=registry,
                thresholds_path=thresholds,
                year=2026,
                month=3,
            )

            self.assertEqual(report["summary"]["usage_row_count"], 0)
            self.assertEqual(report["summary"]["data_warning"], "usage_events table not found")


if __name__ == "__main__":
    unittest.main()
