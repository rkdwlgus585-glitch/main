"""Unit tests for core_engine.channel_branding.

Covers _digits_only, _slugify, and resolve_channel_branding with
default/no-config scenarios.
"""
import unittest

from core_engine.channel_branding import (
    DEFAULT_BRANDING,
    _digits_only,
    _slugify,
    resolve_channel_branding,
)


# ── _digits_only ─────────────────────────────────────────────────────


class DigitsOnlyTest(unittest.TestCase):
    def test_phone_number(self):
        self.assertEqual(_digits_only("1668-3548"), "16683548")

    def test_no_digits(self):
        self.assertEqual(_digits_only("abc"), "")

    def test_none(self):
        self.assertEqual(_digits_only(None), "")

    def test_mixed(self):
        self.assertEqual(_digits_only("tel: 02-1234-5678"), "0212345678")


# ── _slugify ─────────────────────────────────────────────────────────


class SlugifyTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_slugify("Hello World"), "hello_world")

    def test_korean(self):
        result = _slugify("서울건설정보")
        self.assertEqual(result, "서울건설정보")

    def test_special_chars(self):
        result = _slugify("A&B (test)")
        self.assertEqual(result, "a_b_test")

    def test_empty(self):
        self.assertEqual(_slugify(""), "")

    def test_none(self):
        self.assertEqual(_slugify(None), "")

    def test_multiple_underscores_collapsed(self):
        result = _slugify("a---b   c")
        self.assertEqual(result, "a_b_c")


# ── resolve_channel_branding (no config file) ────────────────────────


class ResolveChannelBrandingNoConfigTest(unittest.TestCase):
    """When no config file exists, resolve to defaults."""

    def test_returns_defaults(self):
        branding = resolve_channel_branding(config_path="/nonexistent/path.json")
        self.assertEqual(branding["brand_name"], DEFAULT_BRANDING["brand_name"])
        self.assertEqual(branding["site_url"], DEFAULT_BRANDING["site_url"])

    def test_contact_phone_always_present(self):
        branding = resolve_channel_branding(config_path="/nonexistent/path.json")
        self.assertTrue(branding["contact_phone"])

    def test_contact_phone_digits_computed(self):
        branding = resolve_channel_branding(config_path="/nonexistent/path.json")
        self.assertEqual(branding["contact_phone_digits"], "16683548")

    def test_overrides_applied(self):
        branding = resolve_channel_branding(
            config_path="/nonexistent/path.json",
            overrides={"brand_name": "TestBrand"},
        )
        self.assertEqual(branding["brand_name"], "TestBrand")

    def test_none_override_ignored(self):
        branding = resolve_channel_branding(
            config_path="/nonexistent/path.json",
            overrides={"brand_name": None},
        )
        self.assertEqual(branding["brand_name"], DEFAULT_BRANDING["brand_name"])

    def test_empty_override_ignored(self):
        branding = resolve_channel_branding(
            config_path="/nonexistent/path.json",
            overrides={"brand_name": ""},
        )
        # Empty string is stripped; keep default
        self.assertEqual(branding["brand_name"], DEFAULT_BRANDING["brand_name"])

    def test_channel_id_empty_when_no_config(self):
        branding = resolve_channel_branding(config_path="/nonexistent/path.json")
        self.assertEqual(branding["channel_id"], "")


if __name__ == "__main__":
    unittest.main()
