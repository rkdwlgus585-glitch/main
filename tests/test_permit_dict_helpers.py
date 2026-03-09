"""Unit tests for _get_str / _get_int dict extraction helpers.

These helpers replace ~178 instances of ``str(x.get("k","") or "").strip()``
and ``_coerce_non_negative_int(x.get("k", 0))`` boilerplate throughout
permit_diagnosis_calculator.py.
"""
import unittest

from permit_diagnosis_calculator import _get_str, _get_int


class GetStrTest(unittest.TestCase):
    """_get_str(data, key, default="") → stripped string."""

    def test_basic_extraction(self):
        self.assertEqual(_get_str({"a": "hello"}, "a"), "hello")

    def test_strips_whitespace(self):
        self.assertEqual(_get_str({"a": "  spaced  "}, "a"), "spaced")

    def test_missing_key_returns_empty(self):
        self.assertEqual(_get_str({}, "missing"), "")

    def test_none_value_returns_empty(self):
        self.assertEqual(_get_str({"a": None}, "a"), "")

    def test_integer_value_coerced_to_str(self):
        self.assertEqual(_get_str({"a": 42}, "a"), "42")

    def test_float_value_coerced_to_str(self):
        self.assertEqual(_get_str({"a": 3.14}, "a"), "3.14")

    def test_custom_default(self):
        self.assertEqual(_get_str({}, "missing", "fallback"), "fallback")

    def test_empty_string_value(self):
        self.assertEqual(_get_str({"a": ""}, "a"), "")

    def test_zero_value_returns_empty(self):
        # 0 is falsy → `or ""` triggers → returns empty string
        # This matches the original `str(d.get("k","") or "").strip()` behavior
        self.assertEqual(_get_str({"a": 0}, "a"), "")

    def test_false_value_returns_empty(self):
        # bool(False) is falsy → or "" kicks in → ""
        self.assertEqual(_get_str({"a": False}, "a"), "")

    def test_list_value_coerced(self):
        result = _get_str({"a": [1, 2]}, "a")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


class GetIntTest(unittest.TestCase):
    """_get_int(data, key, default=0) → non-negative int."""

    def test_basic_extraction(self):
        self.assertEqual(_get_int({"a": 5}, "a"), 5)

    def test_string_number_coerced(self):
        self.assertEqual(_get_int({"a": "10"}, "a"), 10)

    def test_float_truncated(self):
        self.assertEqual(_get_int({"a": 3.9}, "a"), 3)

    def test_missing_key_returns_zero(self):
        self.assertEqual(_get_int({}, "missing"), 0)

    def test_none_value_returns_zero(self):
        self.assertEqual(_get_int({"a": None}, "a"), 0)

    def test_negative_clamped_to_zero(self):
        self.assertEqual(_get_int({"a": -5}, "a"), 0)

    def test_garbage_string_returns_zero(self):
        self.assertEqual(_get_int({"a": "not a number"}, "a"), 0)

    def test_empty_string_returns_zero(self):
        self.assertEqual(_get_int({"a": ""}, "a"), 0)

    def test_custom_default(self):
        self.assertEqual(_get_int({}, "missing", 99), 99)

    def test_string_float_coerced(self):
        self.assertEqual(_get_int({"a": "7.8"}, "a"), 7)

    def test_zero_value(self):
        self.assertEqual(_get_int({"a": 0}, "a"), 0)

    def test_large_value(self):
        self.assertEqual(_get_int({"a": 999999}, "a"), 999999)


if __name__ == "__main__":
    unittest.main()
