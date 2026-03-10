"""Unit tests for core_engine.api_contract.

Covers _compact (canonical in api_response), _dict, and normalize_v1_request.
"""
import unittest

from core_engine.api_contract import (
    RESERVED_WRAPPER_KEYS,
    _dict,
    normalize_v1_request,
)
from core_engine.api_response import _compact


# ── _compact ─────────────────────────────────────────────────────────


class CompactTest(unittest.TestCase):
    def test_collapses_whitespace(self):
        self.assertEqual(_compact("  hello   world  "), "hello world")

    def test_truncates_at_limit(self):
        self.assertEqual(_compact("abcdef", limit=3), "abc")

    def test_none_returns_empty(self):
        self.assertEqual(_compact(None), "")

    def test_zero_limit_no_truncation(self):
        self.assertEqual(_compact("abcdef", limit=0), "abcdef")


# ── _dict ────────────────────────────────────────────────────────────


class DictTest(unittest.TestCase):
    def test_dict_passthrough(self):
        self.assertEqual(_dict({"a": 1}), {"a": 1})

    def test_non_dict_returns_empty(self):
        self.assertEqual(_dict("not a dict"), {})

    def test_none_returns_empty(self):
        self.assertEqual(_dict(None), {})


# ── normalize_v1_request ─────────────────────────────────────────────


class NormalizeV1RequestTest(unittest.TestCase):
    def test_none_payload(self):
        result = normalize_v1_request(None)
        self.assertIn("request_meta", result)
        self.assertIn("fields", result)
        self.assertIn("inputs", result)

    def test_flat_fields_extracted(self):
        payload = {"license_key": "토목", "capital_eok": 3.0}
        result = normalize_v1_request(payload)
        self.assertEqual(result["fields"]["license_key"], "토목")
        self.assertEqual(result["inputs"]["capital_eok"], 3.0)

    def test_reserved_keys_excluded_from_flat(self):
        payload = {"request": {"source": "test"}, "license_key": "토목"}
        result = normalize_v1_request(payload)
        self.assertNotIn("request", result["fields"])
        self.assertIn("license_key", result["fields"])

    def test_request_meta_from_request_block(self):
        payload = {"request": {"source": "web_calc", "channel_id": "ch_01"}}
        result = normalize_v1_request(payload)
        self.assertEqual(result["request_meta"]["source"], "web_calc")
        self.assertEqual(result["request_meta"]["channel_id_hint"], "ch_01")

    def test_meta_fallback_to_context_block(self):
        payload = {"context": {"channel_id": "ch_02"}}
        result = normalize_v1_request(payload)
        self.assertEqual(result["request_meta"]["channel_id_hint"], "ch_02")

    def test_selector_fallback_to_target(self):
        payload = {"target": {"license_text": "전기공사업"}}
        result = normalize_v1_request(payload)
        self.assertEqual(result["selector"]["license_text"], "전기공사업")

    def test_inputs_fallback_to_input(self):
        payload = {"input": {"capital_eok": 1.5}}
        result = normalize_v1_request(payload)
        self.assertEqual(result["inputs"]["capital_eok"], 1.5)

    def test_headers_fallback_for_page_url(self):
        result = normalize_v1_request({}, headers={"Referer": "https://seoulmna.kr/yangdo"})
        self.assertEqual(result["request_meta"]["page_url"], "https://seoulmna.kr/yangdo")

    def test_headers_fallback_for_source(self):
        result = normalize_v1_request({}, headers={"Origin": "https://seoulmna.kr"})
        self.assertEqual(result["request_meta"]["source"], "https://seoulmna.kr")

    def test_request_id_from_headers(self):
        result = normalize_v1_request({}, headers={"X-Request-Id": "req-123"})
        self.assertEqual(result["request_meta"]["request_id_hint"], "req-123")

    def test_default_source(self):
        result = normalize_v1_request({}, default_source="api_gateway")
        self.assertEqual(result["request_meta"]["source"], "api_gateway")

    def test_default_page_url(self):
        result = normalize_v1_request({}, default_page_url="https://seoulmna.kr")
        self.assertEqual(result["request_meta"]["page_url"], "https://seoulmna.kr")

    def test_raw_preserved(self):
        payload = {"license_key": "토목", "request": {"source": "test"}}
        result = normalize_v1_request(payload)
        self.assertEqual(result["raw"], payload)

    def test_inputs_merges_selector_and_input(self):
        payload = {
            "target": {"license_text": "전기"},
            "input": {"capital_eok": 1.5},
            "custom_field": "value",
        }
        result = normalize_v1_request(payload)
        # inputs should contain all of: selector fields, flat fields, and input block
        self.assertEqual(result["inputs"]["license_text"], "전기")
        self.assertEqual(result["inputs"]["capital_eok"], 1.5)
        self.assertEqual(result["inputs"]["custom_field"], "value")


    def test_tenant_id_extracted(self):
        payload = {"request": {"tenant_id": "t_001"}}
        result = normalize_v1_request(payload)
        self.assertEqual(result["request_meta"]["tenant_id_hint"], "t_001")

    def test_tenant_id_from_flat(self):
        payload = {"tenant_id": "t_flat", "license_key": "전기"}
        result = normalize_v1_request(payload)
        self.assertEqual(result["request_meta"]["tenant_id_hint"], "t_flat")

    def test_requested_at_from_timestamp(self):
        payload = {"request": {"timestamp": "2026-03-10T12:00:00Z"}}
        result = normalize_v1_request(payload)
        self.assertEqual(result["request_meta"]["requested_at"], "2026-03-10T12:00:00Z")

    def test_x_correlation_id_fallback(self):
        result = normalize_v1_request({}, headers={"X-Correlation-Id": "corr-456"})
        self.assertEqual(result["request_meta"]["request_id_hint"], "corr-456")

    def test_long_page_url_truncated(self):
        long_url = "https://example.com/" + "x" * 600
        result = normalize_v1_request({}, default_page_url=long_url)
        self.assertLessEqual(len(result["request_meta"]["page_url"]), 500)

    def test_deeply_nested_payload_preserved(self):
        """Partner payloads may have unexpected nesting."""
        payload = {
            "request": {"source": "partner_api"},
            "input": {"nested": {"deep": {"value": 1}}},
        }
        result = normalize_v1_request(payload)
        self.assertEqual(result["inputs"]["nested"]["deep"]["value"], 1)


if __name__ == "__main__":
    unittest.main()
