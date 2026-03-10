from __future__ import annotations

import unittest

from core_engine.host_utils import host_from_origin, normalize_host, sanitize_endpoint, to_bool


class NormalizeHostTest(unittest.TestCase):
    def test_plain_host(self):
        self.assertEqual(normalize_host("example.com"), "example.com")

    def test_https_url(self):
        self.assertEqual(normalize_host("https://example.com/path"), "example.com")

    def test_http_with_port(self):
        self.assertEqual(normalize_host("http://example.com:8080"), "example.com")

    def test_protocol_relative(self):
        self.assertEqual(normalize_host("//example.com"), "example.com")

    def test_user_at_host(self):
        self.assertEqual(normalize_host("user@example.com"), "example.com")

    def test_host_with_port(self):
        self.assertEqual(normalize_host("example.com:443"), "example.com")

    def test_uppercase_normalized(self):
        self.assertEqual(normalize_host("EXAMPLE.COM"), "example.com")

    def test_empty_string(self):
        self.assertEqual(normalize_host(""), "")

    def test_none(self):
        self.assertEqual(normalize_host(None), "")

    def test_whitespace_only(self):
        self.assertEqual(normalize_host("  "), "")

    def test_ftp_scheme(self):
        self.assertEqual(normalize_host("ftp://files.example.com/dir"), "files.example.com")

    def test_subdomain(self):
        self.assertEqual(normalize_host("https://sub.example.com"), "sub.example.com")


class HostFromOriginTest(unittest.TestCase):
    def test_https_origin(self):
        self.assertEqual(host_from_origin("https://example.com"), "example.com")

    def test_http_origin_with_port(self):
        self.assertEqual(host_from_origin("http://localhost:3000"), "localhost")

    def test_empty(self):
        self.assertEqual(host_from_origin(""), "")

    def test_none(self):
        self.assertEqual(host_from_origin(None), "")

    def test_bare_host_no_scheme(self):
        # Without scheme, urlparse treats it as path, netloc is empty
        result = host_from_origin("example.com")
        self.assertEqual(result, "")

    def test_full_url_with_path(self):
        self.assertEqual(host_from_origin("https://api.example.com/v1/data"), "api.example.com")


class ToBoolTest(unittest.TestCase):
    def test_none_returns_default(self):
        self.assertTrue(to_bool(None, True))
        self.assertFalse(to_bool(None, False))

    def test_bool_passthrough(self):
        self.assertTrue(to_bool(True))
        self.assertFalse(to_bool(False))

    def test_truthy_strings(self):
        for val in ["1", "true", "True", "TRUE", "yes", "Yes", "on", "ON", "y", "Y"]:
            with self.subTest(val=val):
                self.assertTrue(to_bool(val))

    def test_falsy_strings(self):
        for val in ["0", "false", "False", "FALSE", "no", "No", "off", "OFF", "n", "N"]:
            with self.subTest(val=val):
                self.assertFalse(to_bool(val))

    def test_unknown_returns_default(self):
        self.assertTrue(to_bool("maybe", True))
        self.assertFalse(to_bool("maybe", False))

    def test_integer_zero(self):
        self.assertFalse(to_bool(0))

    def test_integer_one(self):
        self.assertTrue(to_bool(1))

    def test_whitespace_trimmed(self):
        self.assertTrue(to_bool("  true  "))
        self.assertFalse(to_bool("  false  "))

    def test_empty_string_returns_default(self):
        self.assertTrue(to_bool("", True))
        self.assertFalse(to_bool("", False))


class SanitizeEndpointCanonicalTest(unittest.TestCase):
    """Canonical sanitize_endpoint tests (core_engine.host_utils)."""

    def test_https_passes(self):
        self.assertEqual(sanitize_endpoint("https://example.com/api"), "https://example.com/api")

    def test_relative_passes(self):
        self.assertEqual(sanitize_endpoint("/api/v1"), "/api/v1")

    def test_javascript_blocked(self):
        self.assertEqual(sanitize_endpoint("javascript:alert(1)"), "")

    def test_data_uri_blocked(self):
        self.assertEqual(sanitize_endpoint("data:text/html,<h1>XSS</h1>"), "")

    def test_localhost_blocked(self):
        self.assertEqual(sanitize_endpoint("http://localhost:8080"), "")

    def test_link_local_blocked(self):
        self.assertEqual(sanitize_endpoint("http://169.254.169.254/metadata"), "")

    def test_unspecified_blocked(self):
        self.assertEqual(sanitize_endpoint("http://0.0.0.0:80"), "")

    def test_empty(self):
        self.assertEqual(sanitize_endpoint(""), "")

    def test_none(self):
        self.assertEqual(sanitize_endpoint(None), "")


if __name__ == "__main__":
    unittest.main()
