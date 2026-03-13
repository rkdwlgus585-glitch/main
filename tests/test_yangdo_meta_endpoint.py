"""Tests for the /v1/meta endpoint in yangdo_blackbox_api.

Covers: meta_with_profiles method, _write_json_response helper,
and _patched_handler_do_get meta routing.
"""

import json
import threading
import unittest
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

import yangdo_blackbox_api as api


# ===================================================================
# meta_with_profiles — estimator method
# ===================================================================
class MetaWithProfilesTest(unittest.TestCase):
    """Test YangdoBlackboxEstimator.meta_with_profiles()."""

    def _estimator_with_data(self, records: list[dict] | None = None, train: list[dict] | None = None) -> api.YangdoBlackboxEstimator:
        est = api.YangdoBlackboxEstimator()
        with est._lock:
            est._records = records or []
            est._train_records = train or []
        return est

    def test_empty_data_returns_valid_structure(self) -> None:
        est = self._estimator_with_data()
        result = est.meta_with_profiles()
        self.assertIn("meta", result)
        self.assertIn("license_profiles", result)
        self.assertIn("profiles", result["license_profiles"])
        self.assertIn("quick_tokens", result["license_profiles"])
        self.assertEqual(result["meta"]["all_record_count"], 0)
        self.assertEqual(result["meta"]["train_count"], 0)

    def test_with_training_data(self) -> None:
        train = [
            {"tokens": ["전기공사"], "price_eok": 2.0, "specialty": 100, "sales3_eok": 5.0,
             "capital_eok": 1.5, "surplus_eok": 0.3, "balance_eok": 0.5, "debt_ratio": 0.3, "liq_ratio": 1.2},
            {"tokens": ["전기공사"], "price_eok": 3.0, "specialty": 150, "sales3_eok": 8.0,
             "capital_eok": 2.0, "surplus_eok": 0.5, "balance_eok": 0.8, "debt_ratio": 0.2, "liq_ratio": 1.5},
        ]
        est = self._estimator_with_data(records=train, train=train)
        result = est.meta_with_profiles()
        self.assertEqual(result["meta"]["all_record_count"], 2)
        self.assertEqual(result["meta"]["train_count"], 2)
        # Should have license profile for 전기공사
        profiles = result["license_profiles"]["profiles"]
        self.assertTrue(len(profiles) > 0)
        quick = result["license_profiles"]["quick_tokens"]
        self.assertTrue(len(quick) > 0)

    def test_meta_has_expected_keys(self) -> None:
        est = self._estimator_with_data()
        meta = est.meta_with_profiles()["meta"]
        expected_keys = {
            "generated_at", "all_record_count", "train_count", "priced_ratio",
            "median_price_eok", "p25_price_eok", "p75_price_eok",
            "avg_debt_ratio", "avg_liq_ratio", "avg_capital_eok", "p90_capital_eok",
            "avg_surplus_eok", "p90_surplus_eok", "avg_balance_eok", "p90_balance_eok",
            "median_specialty", "p90_specialty", "median_sales3_eok", "p90_sales3_eok",
            "top_license_tokens",
        }
        self.assertEqual(set(meta.keys()), expected_keys)

    def test_thread_safety(self) -> None:
        """meta_with_profiles must not crash under concurrent access."""
        train = [{"tokens": ["토목공사"], "price_eok": 5.0, "specialty": 200,
                  "capital_eok": 5.0, "balance_eok": 1.0, "surplus_eok": 0.5,
                  "sales3_eok": 10.0, "debt_ratio": 0.1, "liq_ratio": 2.0}]
        est = self._estimator_with_data(records=train, train=train)
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for _ in range(10):
                    result = est.meta_with_profiles()
                    assert "meta" in result
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])

    def test_quick_tokens_sorted_by_count_desc(self) -> None:
        train = [
            {"tokens": ["전기공사"], "price_eok": 2.0},
            {"tokens": ["전기공사"], "price_eok": 3.0},
            {"tokens": ["전기공사"], "price_eok": 4.0},
            {"tokens": ["소방시설공사"], "price_eok": 1.5},
        ]
        est = self._estimator_with_data(train=train)
        quick = est.meta_with_profiles()["license_profiles"]["quick_tokens"]
        # 전기공사 should be first (count=3 vs count=1)
        if len(quick) >= 2:
            self.assertGreaterEqual(quick[0]["sample_count"], quick[1]["sample_count"])


# ===================================================================
# _write_json_response — helper function
# ===================================================================
class WriteJsonResponseTest(unittest.TestCase):
    """Test _write_json_response produces correct HTTP output."""

    def _mock_handler(self) -> MagicMock:
        handler = MagicMock()
        handler._request_id.return_value = "test-req-123"
        handler._channel_resolution.return_value = None
        handler._tenant_resolution.return_value = None
        handler._allow_origin.return_value = "https://seoulmna.kr"
        handler._channel_headers.return_value = {}
        handler.wfile = BytesIO()
        # Capture send_header calls
        handler._headers_sent: list[tuple[str, str]] = []

        def mock_send_header(k: str, v: str) -> None:
            handler._headers_sent.append((k, v))

        handler.send_header = mock_send_header
        return handler

    def test_200_meta_response(self) -> None:
        handler = self._mock_handler()
        data = {"ok": True, "meta": {"train_count": 42}}
        api._write_json_response(handler, 200, data, "meta")
        handler.send_response.assert_called_with(200)
        header_dict = dict(handler._headers_sent)
        self.assertEqual(header_dict["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(header_dict["X-Response-Tier"], "meta")
        self.assertEqual(header_dict["Cache-Control"], "no-store")

    def test_cors_headers_present(self) -> None:
        handler = self._mock_handler()
        api._write_json_response(handler, 200, {"ok": True}, "meta")
        header_dict = dict(handler._headers_sent)
        self.assertEqual(header_dict["Access-Control-Allow-Origin"], "https://seoulmna.kr")
        self.assertIn("Access-Control-Expose-Headers", header_dict)


# ===================================================================
# _patched_handler_do_get — /v1/meta routing
# ===================================================================
class PatchedHandlerMetaRoutingTest(unittest.TestCase):
    """Test that _patched_handler_do_get routes /v1/meta correctly."""

    def _mock_handler_for_get(self, path: str) -> MagicMock:
        handler = MagicMock()
        handler.path = path
        handler._allow_request.return_value = True
        handler._require_channel_ready.return_value = True
        handler._request_id.return_value = "get-req-1"
        handler._channel_resolution.return_value = None
        handler._tenant_resolution.return_value = None
        handler._allow_origin.return_value = ""
        handler._channel_headers.return_value = {}
        handler.wfile = BytesIO()
        handler._headers_sent = []

        def mock_send_header(k: str, v: str) -> None:
            handler._headers_sent.append((k, v))

        handler.send_header = mock_send_header

        # Server with estimator
        server = MagicMock()
        server.admin_api_keys = set()
        est = api.YangdoBlackboxEstimator()
        server.estimator = est
        handler.server = server
        return handler

    def test_v1_meta_returns_200(self) -> None:
        handler = self._mock_handler_for_get("/v1/meta")
        api._patched_handler_do_get(handler)
        handler.send_response.assert_called_with(200)

    def test_meta_without_version_prefix(self) -> None:
        handler = self._mock_handler_for_get("/meta")
        api._patched_handler_do_get(handler)
        handler.send_response.assert_called_with(200)

    def test_meta_with_query_string(self) -> None:
        handler = self._mock_handler_for_get("/v1/meta?foo=bar")
        api._patched_handler_do_get(handler)
        handler.send_response.assert_called_with(200)

    def test_meta_no_estimator_returns_503(self) -> None:
        handler = self._mock_handler_for_get("/v1/meta")
        handler.server.estimator = None
        api._patched_handler_do_get(handler)
        handler.send_response.assert_called_with(503)

    def test_health_still_works(self) -> None:
        handler = self._mock_handler_for_get("/v1/health")
        # Health uses _write_partner_health_json which calls send_response
        api._patched_handler_do_get(handler)
        handler.send_response.assert_called()

    def test_meta_no_admin_key_required(self) -> None:
        """Meta endpoint serves public catalog data — no admin auth gate."""
        handler = self._mock_handler_for_get("/v1/meta")
        handler.server.admin_api_keys = {"secret-key"}
        api._patched_handler_do_get(handler)
        # _require_api_key should NOT be called for /v1/meta
        handler._require_api_key.assert_not_called()
        handler.send_response.assert_called_with(200)


if __name__ == "__main__":
    unittest.main()
