"""Unit tests for utils.py pure functions.

Covers: _parse_bool, require_config, Notifier._compact_message.
"""

import unittest

from utils import _parse_bool, require_config, Notifier


# ===================================================================
# _parse_bool
# ===================================================================
class ParseBoolTest(unittest.TestCase):
    def test_true_values(self):
        for val in ("1", "true", "yes", "on", "TRUE", "Yes", "ON"):
            self.assertTrue(_parse_bool(val), f"Expected True: {val!r}")

    def test_false_values(self):
        for val in ("0", "false", "no", "off", "FALSE", "No", "OFF"):
            self.assertFalse(_parse_bool(val), f"Expected False: {val!r}")

    def test_none_returns_default(self):
        self.assertFalse(_parse_bool(None))
        self.assertTrue(_parse_bool(None, default=True))

    def test_unknown_returns_default(self):
        self.assertFalse(_parse_bool("maybe"))
        self.assertTrue(_parse_bool("maybe", default=True))

    def test_whitespace(self):
        self.assertTrue(_parse_bool("  true  "))
        self.assertFalse(_parse_bool("  false  "))

    def test_empty_string_returns_default(self):
        self.assertFalse(_parse_bool(""))
        self.assertTrue(_parse_bool("", default=True))

    def test_integer_input(self):
        self.assertTrue(_parse_bool(1))
        self.assertFalse(_parse_bool(0))

    def test_bool_input(self):
        self.assertTrue(_parse_bool(True))
        self.assertFalse(_parse_bool(False))


# ===================================================================
# require_config
# ===================================================================
class RequireConfigTest(unittest.TestCase):
    def test_all_present(self):
        config = {"KEY_A": "val_a", "KEY_B": "val_b"}
        result = require_config(config, ["KEY_A", "KEY_B"])
        self.assertIs(result, config)

    def test_missing_key_raises(self):
        config = {"KEY_A": "val_a"}
        with self.assertRaises(ValueError) as cm:
            require_config(config, ["KEY_A", "KEY_B"], context="test")
        self.assertIn("KEY_B", str(cm.exception))
        self.assertIn("[test]", str(cm.exception))

    def test_empty_value_raises(self):
        config = {"KEY_A": ""}
        with self.assertRaises(ValueError):
            require_config(config, ["KEY_A"])

    def test_whitespace_only_raises(self):
        config = {"KEY_A": "   "}
        with self.assertRaises(ValueError):
            require_config(config, ["KEY_A"])

    def test_none_value_passes_as_string_none(self):
        """str(None) == 'None' which is non-empty, so it passes."""
        config = {"KEY_A": None}
        result = require_config(config, ["KEY_A"])
        self.assertIs(result, config)

    def test_empty_required_keys(self):
        config = {"KEY_A": "val"}
        result = require_config(config, [])
        self.assertIs(result, config)

    def test_default_context(self):
        config = {}
        with self.assertRaises(ValueError) as cm:
            require_config(config, ["MISSING"])
        self.assertIn("[app]", str(cm.exception))

    def test_multiple_missing(self):
        config = {}
        with self.assertRaises(ValueError) as cm:
            require_config(config, ["A", "B", "C"])
        msg = str(cm.exception)
        self.assertIn("A", msg)
        self.assertIn("B", msg)
        self.assertIn("C", msg)


# ===================================================================
# Notifier._compact_message
# ===================================================================
class CompactMessageTest(unittest.TestCase):
    def _make_notifier(self):
        """Create Notifier with dummy URLs to avoid real HTTP."""
        return Notifier(discord_url="", slack_url="")

    def test_short_message_unchanged(self):
        n = self._make_notifier()
        self.assertEqual(n._compact_message("hello"), "hello")

    def test_none_becomes_empty(self):
        n = self._make_notifier()
        self.assertEqual(n._compact_message(None), "")

    def test_empty_string(self):
        n = self._make_notifier()
        self.assertEqual(n._compact_message(""), "")

    def test_long_message_truncated(self):
        n = self._make_notifier()
        msg = "A" * 2000
        result = n._compact_message(msg)
        self.assertIn("(truncated)", result)
        self.assertLessEqual(len(result), Notifier.MAX_MESSAGE_LEN)

    def test_exact_limit_unchanged(self):
        n = self._make_notifier()
        msg = "B" * Notifier.MAX_MESSAGE_LEN
        self.assertEqual(n._compact_message(msg), msg)

    def test_one_over_limit_truncated(self):
        n = self._make_notifier()
        msg = "C" * (Notifier.MAX_MESSAGE_LEN + 1)
        result = n._compact_message(msg)
        self.assertIn("(truncated)", result)

    def test_whitespace_stripped(self):
        n = self._make_notifier()
        self.assertEqual(n._compact_message("  hello  "), "hello")


if __name__ == "__main__":
    unittest.main()
