"""Security tests for _sanitize_endpoint protocol whitelist.

Verifies that only http(s) and relative URLs are allowed, blocking
javascript:, data:, vbscript:, and localhost/loopback patterns.
"""
import unittest

from yangdo_calculator import _sanitize_endpoint


class SanitizeEndpointWhitelistTest(unittest.TestCase):
    """Protocol whitelist: only http(s) and relative paths pass through."""

    # ── Allowed ──────────────────────────────────────────────────────
    def test_https_url_passes(self):
        self.assertEqual(
            _sanitize_endpoint("https://seoulmna.co.kr/api"),
            "https://seoulmna.co.kr/api",
        )

    def test_http_url_passes(self):
        self.assertEqual(
            _sanitize_endpoint("http://example.com/path"),
            "http://example.com/path",
        )

    def test_relative_path_passes(self):
        self.assertEqual(_sanitize_endpoint("/api/v1/data"), "/api/v1/data")

    def test_root_relative_passes(self):
        self.assertEqual(_sanitize_endpoint("/"), "/")

    def test_protocol_relative_passes(self):
        self.assertEqual(
            _sanitize_endpoint("//cdn.example.com/lib.js"),
            "//cdn.example.com/lib.js",
        )

    # ── Blocked: dangerous protocols ─────────────────────────────────
    def test_javascript_protocol_blocked(self):
        self.assertEqual(_sanitize_endpoint("javascript:alert(1)"), "")

    def test_javascript_uppercase_blocked(self):
        self.assertEqual(_sanitize_endpoint("JAVASCRIPT:alert(1)"), "")

    def test_data_protocol_blocked(self):
        self.assertEqual(_sanitize_endpoint("data:text/html,<script>alert(1)</script>"), "")

    def test_vbscript_protocol_blocked(self):
        self.assertEqual(_sanitize_endpoint("vbscript:MsgBox(1)"), "")

    def test_file_protocol_blocked(self):
        self.assertEqual(_sanitize_endpoint("file:///etc/passwd"), "")

    def test_ftp_protocol_blocked(self):
        self.assertEqual(_sanitize_endpoint("ftp://attacker.com/payload"), "")

    # ── Blocked: localhost/loopback ──────────────────────────────────
    def test_localhost_blocked(self):
        self.assertEqual(_sanitize_endpoint("http://localhost:8080"), "")

    def test_127_0_0_1_blocked(self):
        self.assertEqual(_sanitize_endpoint("http://127.0.0.1:3000"), "")

    def test_ipv6_loopback_blocked(self):
        self.assertEqual(_sanitize_endpoint("http://[::1]:8080"), "")

    # ── Blocked: link-local / unspecified addresses (SSRF) ──────────
    def test_link_local_169_254_blocked(self):
        self.assertEqual(_sanitize_endpoint("http://169.254.169.254/metadata"), "")

    def test_link_local_with_path_blocked(self):
        self.assertEqual(_sanitize_endpoint("http://169.254.1.1/admin"), "")

    def test_unspecified_0000_blocked(self):
        self.assertEqual(_sanitize_endpoint("http://0.0.0.0:8080"), "")

    # ── Edge cases ───────────────────────────────────────────────────
    def test_empty_string_returns_empty(self):
        self.assertEqual(_sanitize_endpoint(""), "")

    def test_none_returns_empty(self):
        self.assertEqual(_sanitize_endpoint(None), "")

    def test_whitespace_only_returns_empty(self):
        self.assertEqual(_sanitize_endpoint("   "), "")

    def test_preserves_query_params(self):
        url = "https://seoulmna.co.kr/api?page=1&size=10"
        self.assertEqual(_sanitize_endpoint(url), url)

    def test_preserves_hash_fragment(self):
        url = "https://seoulmna.co.kr/page#section"
        self.assertEqual(_sanitize_endpoint(url), url)


if __name__ == "__main__":
    unittest.main()
