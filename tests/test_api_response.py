from __future__ import annotations

import unittest

import re

from core_engine.api_response import _compact, build_response_envelope, now_iso, safe_json_for_script


class CompactTest(unittest.TestCase):
    def test_trims_whitespace(self):
        self.assertEqual(_compact("  hello   world  "), "hello world")

    def test_none_returns_empty(self):
        self.assertEqual(_compact(None), "")

    def test_limit_truncates(self):
        self.assertEqual(_compact("abcdefgh", limit=5), "abcde")

    def test_zero_limit_no_truncation(self):
        long = "x" * 5000
        self.assertEqual(_compact(long, limit=0), long)


class BuildResponseEnvelopeTest(unittest.TestCase):
    def _build(self, **kwargs):
        defaults = {
            "payload": {"ok": True, "value": 42},
            "service": "yangdo",
            "api_version": "v1",
            "request_id": "req-001",
        }
        defaults.update(kwargs)
        return build_response_envelope(**defaults)

    def test_basic_ok_response(self):
        result = self._build()
        self.assertEqual(result["service"], "yangdo")
        self.assertEqual(result["api_version"], "v1")
        self.assertEqual(result["request_id"], "req-001")
        meta = result["response_meta"]
        self.assertEqual(meta["status"], "ok")

    def test_error_status_when_not_ok(self):
        result = self._build(payload={"ok": False})
        self.assertEqual(result["response_meta"]["status"], "error")

    def test_channel_id_from_kwarg(self):
        result = self._build(channel_id="ch-001")
        self.assertEqual(result["response_meta"]["channel_id"], "ch-001")
        self.assertEqual(result["channel_id"], "ch-001")

    def test_tenant_plan_from_kwarg(self):
        result = self._build(tenant_plan="premium")
        self.assertEqual(result["response_meta"]["tenant_plan"], "premium")

    def test_response_tier_from_kwarg(self):
        result = self._build(response_tier="full")
        self.assertEqual(result["response_meta"]["response_tier"], "full")

    def test_data_key_populated(self):
        result = self._build()
        self.assertIn("data", result)
        self.assertEqual(result["data"]["ok"], True)
        self.assertEqual(result["data"]["value"], 42)

    def test_none_payload(self):
        result = self._build(payload=None)
        self.assertIn("response_meta", result)
        self.assertEqual(result["response_meta"]["status"], "error")

    def test_response_policy_tier_fallback(self):
        payload = {"ok": True, "response_policy": {"tier": "limited", "tenant_plan": "free"}}
        result = self._build(payload=payload)
        self.assertEqual(result["response_meta"]["response_tier"], "limited")
        self.assertEqual(result["response_meta"]["tenant_plan"], "free")

    def test_kwarg_overrides_policy(self):
        payload = {"ok": True, "response_policy": {"tier": "limited"}}
        result = self._build(payload=payload, response_tier="full")
        self.assertEqual(result["response_meta"]["response_tier"], "full")

    def test_channel_id_from_payload(self):
        payload = {"ok": True, "channel_id": "ch-from-payload"}
        result = self._build(payload=payload)
        self.assertEqual(result["channel_id"], "ch-from-payload")

    def test_non_dict_response_policy_ignored(self):
        payload = {"ok": True, "response_policy": "not-a-dict"}
        result = self._build(payload=payload)
        self.assertEqual(result["response_meta"]["response_tier"], "")


# ---------------------------------------------------------------------------
# now_iso
# ---------------------------------------------------------------------------
class NowIsoTest(unittest.TestCase):
    def test_utc_iso_format(self):
        iso = now_iso()
        self.assertRegex(iso, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")

    def test_returns_str(self):
        self.assertIsInstance(now_iso(), str)


# ---------------------------------------------------------------------------
# safe_json_for_script
# ---------------------------------------------------------------------------
class SafeJsonForScriptTest(unittest.TestCase):
    def test_script_tag_escape(self):
        result = safe_json_for_script({"html": "</script>"})
        self.assertNotIn("</script>", result)
        self.assertIn("<\\/script>", result)

    def test_unicode_line_separator(self):
        result = safe_json_for_script({"t": "a\u2028b"})
        self.assertNotIn("\u2028", result)

    def test_unicode_paragraph_separator(self):
        result = safe_json_for_script({"t": "a\u2029b"})
        self.assertNotIn("\u2029", result)

    def test_roundtrip(self):
        import json
        data = {"key": "value", "num": 42}
        result = safe_json_for_script(data)
        self.assertEqual(json.loads(result), data)


if __name__ == "__main__":
    unittest.main()
