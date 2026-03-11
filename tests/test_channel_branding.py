"""Unit tests for core_engine.channel_branding.

Covers _digits_only, _slugify, _config_path, _load_raw_channel_config,
and resolve_channel_branding with full config-file scenarios.
"""
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from core_engine.channel_branding import (
    DEFAULT_BRANDING,
    _config_path,
    _digits_only,
    _load_raw_channel_config,
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


# ── _config_path ─────────────────────────────────────────────────────


class ConfigPathTest(unittest.TestCase):
    """Tests for _config_path() — config file resolution logic."""

    def test_explicit_relative_path_resolved_to_cwd(self):
        """Relative path is resolved against cwd."""
        path = _config_path("my_config.json")
        self.assertEqual(path, Path.cwd() / "my_config.json")

    def test_empty_string_falls_back_to_env_relative(self):
        """Empty config_path triggers env var lookup (relative)."""
        with patch.dict(os.environ, {"CHANNEL_PROFILES_CONFIG": "env/path.json"}):
            path = _config_path("")
            self.assertEqual(path, Path.cwd() / "env" / "path.json")

    def test_none_treated_as_empty(self):
        """None is coerced to empty and falls back to env → default."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CHANNEL_PROFILES_CONFIG", None)
            path = _config_path("")
            self.assertEqual(path, Path.cwd() / "tenant_config" / "channel_profiles.json")

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped."""
        path = _config_path("  my_cfg.json  ")
        self.assertEqual(path, Path.cwd() / "my_cfg.json")

    def test_default_path_when_no_env(self):
        """With no input and no env, uses default relative path."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CHANNEL_PROFILES_CONFIG", None)
            path = _config_path()
            expected = Path.cwd() / "tenant_config" / "channel_profiles.json"
            self.assertEqual(path, expected)

    def test_env_relative_path_resolved(self):
        """Env var with relative path is resolved against cwd."""
        with patch.dict(os.environ, {"CHANNEL_PROFILES_CONFIG": "rel/env.json"}):
            path = _config_path("")
            self.assertEqual(path, Path.cwd() / "rel" / "env.json")

    def test_result_is_always_absolute(self):
        """Return value is always an absolute Path."""
        path = _config_path("relative/path.json")
        self.assertTrue(path.is_absolute())

    def test_explicit_path_takes_priority_over_env(self):
        """Explicit config_path is used even when env var is set."""
        with patch.dict(os.environ, {"CHANNEL_PROFILES_CONFIG": "env_path.json"}):
            path = _config_path("explicit.json")
            self.assertEqual(path.name, "explicit.json")


# ── _load_raw_channel_config ─────────────────────────────────────────


def _tmp_json(data: object, *, binary: bytes | None = None) -> str:
    """Write data to a temp JSON file and return its path (closed handle)."""
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        if binary is not None:
            os.write(fd, binary)
        elif isinstance(data, str):
            os.write(fd, data.encode("utf-8"))
        else:
            os.write(fd, json.dumps(data).encode("utf-8"))
    finally:
        os.close(fd)
    return path


class LoadRawChannelConfigTest(unittest.TestCase):
    """Tests for _load_raw_channel_config() — JSON file loading."""

    def test_nonexistent_file_returns_empty_dict(self):
        result = _load_raw_channel_config("/no/such/file_xyz_nonexistent.json")
        self.assertEqual(result, {})

    def test_valid_json_loaded(self):
        """Valid JSON file is read and parsed."""
        path = _tmp_json({"channels": [{"channel_id": "test"}]})
        try:
            result = _load_raw_channel_config(path)
            self.assertIn("channels", result)
            self.assertEqual(result["channels"][0]["channel_id"], "test")
        finally:
            os.unlink(path)

    def test_invalid_json_returns_empty_dict(self):
        """Malformed JSON returns empty dict (no exception)."""
        path = _tmp_json("{invalid json!!")
        try:
            result = _load_raw_channel_config(path)
            self.assertEqual(result, {})
        finally:
            os.unlink(path)

    def test_empty_file_returns_empty_dict(self):
        """Empty file returns empty dict."""
        path = _tmp_json("")
        try:
            result = _load_raw_channel_config(path)
            self.assertEqual(result, {})
        finally:
            os.unlink(path)

    def test_utf8_bom_handled(self):
        """UTF-8 BOM encoded file is handled correctly."""
        content = json.dumps({"default_channel_id": "bom_test"}).encode("utf-8")
        path = _tmp_json(None, binary=b"\xef\xbb\xbf" + content)
        try:
            result = _load_raw_channel_config(path)
            self.assertEqual(result["default_channel_id"], "bom_test")
        finally:
            os.unlink(path)

    def test_json_array_returns_array(self):
        """JSON array is returned as-is (caller handles non-dict)."""
        path = _tmp_json([1, 2, 3])
        try:
            result = _load_raw_channel_config(path)
            self.assertEqual(result, [1, 2, 3])
        finally:
            os.unlink(path)


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


# ── resolve_channel_branding (with config file) ─────────────────────


def _write_config(data: dict) -> str:
    """Write channel config JSON to a temp file, return path."""
    return _tmp_json(data)


class ResolveWithDesiredChannelTest(unittest.TestCase):
    """Channel selection by desired_channel_id."""

    def setUp(self):
        self.config = {
            "default_channel_id": "alpha",
            "channels": [
                {
                    "channel_id": "alpha",
                    "display_name": "Alpha Channel",
                    "channel_hosts": ["alpha.example.com"],
                    "branding": {"brand_name": "Alpha Brand"},
                },
                {
                    "channel_id": "beta",
                    "display_name": "Beta Channel",
                    "channel_hosts": ["beta.example.com"],
                    "branding": {
                        "brand_name": "Beta Brand",
                        "site_url": "https://beta.example.com",
                        "contact_phone": "02-555-1234",
                    },
                },
            ],
        }
        self.path = _write_config(self.config)

    def tearDown(self):
        os.unlink(self.path)

    def test_desired_channel_selected(self):
        branding = resolve_channel_branding(channel_id="beta", config_path=self.path)
        self.assertEqual(branding["brand_name"], "Beta Brand")

    def test_desired_channel_case_insensitive(self):
        branding = resolve_channel_branding(channel_id="BETA", config_path=self.path)
        self.assertEqual(branding["brand_name"], "Beta Brand")

    def test_desired_channel_whitespace_stripped(self):
        branding = resolve_channel_branding(channel_id="  beta  ", config_path=self.path)
        self.assertEqual(branding["brand_name"], "Beta Brand")

    def test_desired_overrides_default(self):
        """Desired channel_id takes priority over default_channel_id."""
        branding = resolve_channel_branding(channel_id="beta", config_path=self.path)
        self.assertNotEqual(branding["brand_name"], "Alpha Brand")
        self.assertEqual(branding["brand_name"], "Beta Brand")

    def test_desired_not_found_falls_to_default(self):
        """If desired not in list, selects default_channel_id."""
        branding = resolve_channel_branding(channel_id="nonexistent", config_path=self.path)
        self.assertEqual(branding["brand_name"], "Alpha Brand")

    def test_channel_id_set_in_result(self):
        branding = resolve_channel_branding(channel_id="beta", config_path=self.path)
        self.assertEqual(branding["channel_id"], "beta")


class ResolveWithDefaultChannelTest(unittest.TestCase):
    """Channel selection by default_channel_id when no desired."""

    def setUp(self):
        self.config = {
            "default_channel_id": "gamma",
            "channels": [
                {
                    "channel_id": "gamma",
                    "display_name": "Gamma Channel",
                    "branding": {"brand_name": "Gamma Brand"},
                },
                {
                    "channel_id": "delta",
                    "display_name": "Delta Channel",
                    "branding": {"brand_name": "Delta Brand"},
                },
            ],
        }
        self.path = _write_config(self.config)

    def tearDown(self):
        os.unlink(self.path)

    def test_default_channel_selected(self):
        branding = resolve_channel_branding(config_path=self.path)
        self.assertEqual(branding["brand_name"], "Gamma Brand")

    def test_channel_id_set_from_default(self):
        branding = resolve_channel_branding(config_path=self.path)
        self.assertEqual(branding["channel_id"], "gamma")


class ResolveFirstChannelFallbackTest(unittest.TestCase):
    """When no desired and no default, fall back to first channel."""

    def setUp(self):
        self.config = {
            "channels": [
                {
                    "channel_id": "first",
                    "branding": {"brand_name": "First Brand"},
                },
                {
                    "channel_id": "second",
                    "branding": {"brand_name": "Second Brand"},
                },
            ],
        }
        self.path = _write_config(self.config)

    def tearDown(self):
        os.unlink(self.path)

    def test_first_channel_used(self):
        branding = resolve_channel_branding(config_path=self.path)
        self.assertEqual(branding["brand_name"], "First Brand")

    def test_channel_id_from_first(self):
        branding = resolve_channel_branding(config_path=self.path)
        self.assertEqual(branding["channel_id"], "first")


# ── Branding inheritance and field fallbacks ─────────────────────────


class BrandingInheritanceTest(unittest.TestCase):
    """Test profile branding merges with DEFAULT_BRANDING."""

    def setUp(self):
        self.config = {
            "channels": [
                {
                    "channel_id": "partial",
                    "display_name": "Partial Channel",
                    "channel_hosts": ["partial.example.com"],
                    "branding": {
                        "brand_name": "Partial Brand",
                        # site_url, notice_url, contact_phone not set → defaults
                    },
                },
            ],
        }
        self.path = _write_config(self.config)

    def tearDown(self):
        os.unlink(self.path)

    def test_brand_name_from_profile(self):
        branding = resolve_channel_branding(config_path=self.path)
        self.assertEqual(branding["brand_name"], "Partial Brand")

    def test_defaults_preserved_for_missing_keys(self):
        branding = resolve_channel_branding(config_path=self.path)
        self.assertEqual(branding["contact_phone"], DEFAULT_BRANDING["contact_phone"])
        self.assertEqual(branding["contact_email"], DEFAULT_BRANDING["contact_email"])

    def test_site_url_fallback_from_hosts(self):
        """When branding doesn't set site_url and DEFAULT has one, it keeps DEFAULT."""
        branding = resolve_channel_branding(config_path=self.path)
        # DEFAULT_BRANDING has site_url, so it stays
        self.assertTrue(branding["site_url"])

    def test_canonical_host_fallback_from_hosts(self):
        """canonical_public_host falls back to first channel_host if empty."""
        config = {
            "channels": [
                {
                    "channel_id": "nohost",
                    "channel_hosts": ["custom.example.com"],
                    "branding": {
                        "site_url": "",
                        "canonical_public_host": "",
                    },
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["canonical_public_host"], "custom.example.com")
            self.assertEqual(branding["site_url"], "https://custom.example.com")
        finally:
            os.unlink(path)

    def test_notice_url_from_site_url(self):
        """notice_url is derived from site_url when empty."""
        config = {
            "channels": [
                {
                    "channel_id": "notice",
                    "channel_hosts": ["notice.example.com"],
                    "branding": {
                        "site_url": "https://notice.example.com",
                        "notice_url": "",
                    },
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["notice_url"], "https://notice.example.com/notice")
        finally:
            os.unlink(path)

    def test_brand_label_fallback_to_brand_name(self):
        """brand_label falls back to brand_name when empty."""
        config = {
            "channels": [
                {
                    "channel_id": "lbl",
                    "branding": {
                        "brand_name": "LabelTest",
                        "brand_label": "",
                    },
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["brand_label"], "LabelTest")
        finally:
            os.unlink(path)

    def test_source_tag_prefix_from_channel_id(self):
        """source_tag_prefix derives from channel_id via _slugify."""
        config = {
            "channels": [
                {
                    "channel_id": "My Channel",
                    "branding": {"source_tag_prefix": ""},
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["source_tag_prefix"], "my_channel")
        finally:
            os.unlink(path)

    def test_source_tag_prefix_falls_back_to_brand_name(self):
        """source_tag_prefix falls back to slugified brand_name when channel_id empty."""
        config = {
            "channels": [
                {
                    "channel_id": "",
                    "branding": {
                        "brand_name": "",
                        "source_tag_prefix": "",
                    },
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            # brand_name falls back to DEFAULT; _slugify("서울건설정보") is non-empty
            self.assertEqual(branding["source_tag_prefix"], _slugify(DEFAULT_BRANDING["brand_name"]))
        finally:
            os.unlink(path)


# ── Explicit profile-level fields ────────────────────────────────────


class ExplicitProfileFieldsTest(unittest.TestCase):
    """Test canonical_public_host and public_host_policy from profile."""

    def test_explicit_canonical_host(self):
        config = {
            "channels": [
                {
                    "channel_id": "expl",
                    "canonical_public_host": "explicit.example.com",
                    "channel_hosts": ["fallback.example.com"],
                    "branding": {},
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["canonical_public_host"], "explicit.example.com")
        finally:
            os.unlink(path)

    def test_explicit_host_policy(self):
        config = {
            "channels": [
                {
                    "channel_id": "pol",
                    "public_host_policy": "kr_canonical",
                    "branding": {},
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["public_host_policy"], "kr_canonical")
        finally:
            os.unlink(path)


# ── Type safety / non-dict handling ──────────────────────────────────


class TypeSafetyTest(unittest.TestCase):
    """Robustness against malformed config structures."""

    def test_non_dict_channel_skipped(self):
        """Non-dict items in channels list are skipped."""
        config = {
            "channels": [
                "not a dict",
                42,
                None,
                {"channel_id": "valid", "branding": {"brand_name": "Valid"}},
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["brand_name"], "Valid")
        finally:
            os.unlink(path)

    def test_non_list_channels_ignored(self):
        """Non-list 'channels' field is handled gracefully."""
        config = {"channels": "not a list"}
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            # Falls back to defaults
            self.assertEqual(branding["brand_name"], DEFAULT_BRANDING["brand_name"])
        finally:
            os.unlink(path)

    def test_non_dict_branding_ignored(self):
        """Non-dict 'branding' in profile is ignored."""
        config = {
            "channels": [
                {"channel_id": "bad", "branding": [1, 2, 3]},
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            # Defaults preserved
            self.assertEqual(branding["brand_name"], DEFAULT_BRANDING["brand_name"])
        finally:
            os.unlink(path)

    def test_none_value_in_branding_skipped(self):
        """None values within branding dict are skipped."""
        config = {
            "channels": [
                {
                    "channel_id": "nv",
                    "branding": {
                        "brand_name": None,
                        "site_url": "https://valid.example.com",
                    },
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["site_url"], "https://valid.example.com")
            # brand_name stays default since None was skipped
            self.assertEqual(branding["brand_name"], DEFAULT_BRANDING["brand_name"])
        finally:
            os.unlink(path)

    def test_non_dict_root_returns_defaults(self):
        """JSON array at root level still returns defaults."""
        path = _tmp_json([1, 2, 3])
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["brand_name"], DEFAULT_BRANDING["brand_name"])
        finally:
            os.unlink(path)

    def test_empty_channels_list(self):
        """Empty channels list returns defaults."""
        config = {"channels": []}
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["brand_name"], DEFAULT_BRANDING["brand_name"])
        finally:
            os.unlink(path)


# ── Contact phone guarantees ─────────────────────────────────────────


class ContactPhoneGuaranteeTest(unittest.TestCase):
    """Contact phone and digits are always populated."""

    def test_custom_phone_from_profile(self):
        config = {
            "channels": [
                {
                    "channel_id": "ph",
                    "branding": {"contact_phone": "02-1234-5678"},
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["contact_phone"], "02-1234-5678")
            self.assertEqual(branding["contact_phone_digits"], "0212345678")
        finally:
            os.unlink(path)

    def test_empty_phone_falls_to_default(self):
        config = {
            "channels": [
                {
                    "channel_id": "ep",
                    "branding": {"contact_phone": ""},
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["contact_phone"], DEFAULT_BRANDING["contact_phone"])
        finally:
            os.unlink(path)

    def test_phone_override_applied(self):
        branding = resolve_channel_branding(
            config_path="/nonexistent/path.json",
            overrides={"contact_phone": "010-9999-8888"},
        )
        self.assertEqual(branding["contact_phone"], "010-9999-8888")
        self.assertEqual(branding["contact_phone_digits"], "01099998888")


# ── Return value integrity ───────────────────────────────────────────


class ReturnValueIntegrityTest(unittest.TestCase):
    """All returned values are strings; required keys always present."""

    def test_all_values_are_strings(self):
        branding = resolve_channel_branding(config_path="/nonexistent/path.json")
        for key, value in branding.items():
            self.assertIsInstance(value, str, f"Key '{key}' should be str")

    def test_required_keys_present(self):
        branding = resolve_channel_branding(config_path="/nonexistent/path.json")
        required = {
            "brand_name", "brand_label", "site_url", "canonical_public_host",
            "public_host_policy", "notice_url", "contact_phone",
            "contact_phone_digits", "channel_id", "source_tag_prefix",
        }
        for key in required:
            self.assertIn(key, branding, f"Missing required key: {key}")

    def test_all_values_strings_with_config(self):
        """Even with complex config, all values remain strings."""
        config = {
            "channels": [
                {
                    "channel_id": "str_test",
                    "branding": {
                        "brand_name": "Test",
                        "contact_phone": "1234",
                    },
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            for key, value in branding.items():
                self.assertIsInstance(value, str, f"Key '{key}' should be str")
        finally:
            os.unlink(path)


# ── Environment variable channel_id ──────────────────────────────────


class EnvChannelIdTest(unittest.TestCase):
    """CHANNEL_ID env var used when channel_id param is empty."""

    def setUp(self):
        self.config = {
            "channels": [
                {"channel_id": "env_ch", "branding": {"brand_name": "EnvBrand"}},
                {"channel_id": "other", "branding": {"brand_name": "Other"}},
            ],
        }
        self.path = _write_config(self.config)

    def tearDown(self):
        os.unlink(self.path)

    def test_env_channel_id_used(self):
        with patch.dict(os.environ, {"CHANNEL_ID": "env_ch"}):
            branding = resolve_channel_branding(config_path=self.path)
            self.assertEqual(branding["brand_name"], "EnvBrand")

    def test_param_overrides_env(self):
        with patch.dict(os.environ, {"CHANNEL_ID": "env_ch"}):
            branding = resolve_channel_branding(
                channel_id="other", config_path=self.path
            )
            self.assertEqual(branding["brand_name"], "Other")


# ── brand_name fallback chain ────────────────────────────────────────


class BrandNameFallbackTest(unittest.TestCase):
    """brand_name fallback: branding → display_name → channel_id → DEFAULT."""

    def test_display_name_fallback(self):
        config = {
            "channels": [
                {
                    "channel_id": "dn",
                    "display_name": "Display Fallback",
                    "branding": {"brand_name": ""},
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["brand_name"], "Display Fallback")
        finally:
            os.unlink(path)

    def test_channel_id_fallback(self):
        config = {
            "channels": [
                {
                    "channel_id": "cid_fallback",
                    "branding": {"brand_name": ""},
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["brand_name"], "cid_fallback")
        finally:
            os.unlink(path)

    def test_ultimate_default_fallback(self):
        config = {
            "channels": [
                {
                    "channel_id": "",
                    "branding": {"brand_name": ""},
                },
            ],
        }
        path = _write_config(config)
        try:
            branding = resolve_channel_branding(config_path=path)
            self.assertEqual(branding["brand_name"], DEFAULT_BRANDING["brand_name"])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
