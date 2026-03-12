"""Cross-server consistency tests.

Verify that all 3 API servers (yangdo_blackbox, permit_precheck,
yangdo_consult) follow identical patterns for health checks, error
responses, security headers, and operational conventions.

These tests prevent "server drift" — where one server diverges from
the others in ways that break partner integrations or monitoring.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_SERVERS = {
    "yangdo_blackbox_api": ROOT / "yangdo_blackbox_api.py",
    "permit_precheck_api": ROOT / "permit_precheck_api.py",
    "yangdo_consult_api": ROOT / "yangdo_consult_api.py",
}


def _read_src(name: str) -> str:
    return _SERVERS[name].read_text(encoding="utf-8")


class TestHealthEndpointUnification(unittest.TestCase):
    """All 3 servers must accept /v1/health and return consistent fields."""

    def test_all_servers_accept_v1_health(self) -> None:
        """Each server must handle /v1/health in addition to /health."""
        for name, path in _SERVERS.items():
            with self.subTest(server=name):
                src = path.read_text(encoding="utf-8")
                self.assertIn("/v1/health", src,
                    f"{name} must handle /v1/health route")

    def test_all_servers_return_ok_and_service(self) -> None:
        """Health response must include 'ok' and 'service' keys."""
        for name in _SERVERS:
            with self.subTest(server=name):
                src = _read_src(name)
                # ok: True in health response
                ok_pattern = re.search(r'"ok":\s*True', src)
                self.assertIsNotNone(ok_pattern, f"{name}: missing ok: True")
                # service name
                self.assertIn('"service"', src,
                    f"{name}: missing service field in health")

    def test_all_servers_return_started_at(self) -> None:
        """Health response must include started_at timestamp."""
        for name in _SERVERS:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertIn("started_at", src,
                    f"{name}: missing started_at field")

    def test_all_servers_return_health_contract(self) -> None:
        """Health response must include health_contract."""
        for name in _SERVERS:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertIn("health_contract", src,
                    f"{name}: missing health_contract field")

    def test_all_servers_return_message_healthy(self) -> None:
        """Health response must include message: healthy."""
        for name in _SERVERS:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertIn('"healthy"', src,
                    f'{name}: missing "healthy" message')


class TestErrorResponseConsistency(unittest.TestCase):
    """Servers with visible source must use consistent error format.

    yangdo_blackbox_api error handling is in the compiled base module,
    so only check permit and consult servers directly.
    """

    def test_not_found_response_pattern(self) -> None:
        """Permit and consult must return 404 with ok:false, error:not_found."""
        for name in ["permit_precheck_api", "yangdo_consult_api"]:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertIn("not_found", src,
                    f"{name}: missing not_found error code")


class TestSecurityHeaderConsistency(unittest.TestCase):
    """All servers must set consistent security headers."""

    def test_cache_control_no_store(self) -> None:
        """All servers must set Cache-Control: no-store."""
        for name in _SERVERS:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertIn("no-store", src,
                    f"{name}: missing Cache-Control no-store")

    def test_x_request_id_header(self) -> None:
        """All servers must set X-Request-Id response header."""
        for name in _SERVERS:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertIn("X-Request-Id", src,
                    f"{name}: missing X-Request-Id header")

    def test_cors_expose_headers(self) -> None:
        """All servers must expose X-Request-Id via CORS."""
        for name in _SERVERS:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertIn("Access-Control-Expose-Headers", src,
                    f"{name}: missing CORS Expose-Headers")


class TestGracefulShutdownConsistency(unittest.TestCase):
    """All 3 servers must implement SIGTERM graceful shutdown."""

    def test_sigterm_handler_registered(self) -> None:
        """Each server must register a SIGTERM signal handler."""
        for name in _SERVERS:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertTrue(
                    "SIGTERM" in src,
                    f"{name}: missing SIGTERM handler",
                )

    def test_main_returns_int(self) -> None:
        """permit and consult main() must return int for SystemExit.

        yangdo_blackbox_api uses a compiled __main__ block pattern.
        """
        for name in ["permit_precheck_api", "yangdo_consult_api"]:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertIn("-> int", src,
                    f"{name}: main() must return int")


class TestRateLimiterConsistency(unittest.TestCase):
    """Servers with visible source must implement rate limiting.

    yangdo_blackbox_api rate limiting is in the compiled base + security_http.
    """

    def test_rate_limiter_present(self) -> None:
        """permit and consult must reference rate limiting."""
        for name in ["permit_precheck_api", "yangdo_consult_api"]:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertTrue(
                    "rate_limit" in src.lower() or "rate_limited" in src.lower(),
                    f"{name}: missing rate limiter",
                )

    def test_429_response_code(self) -> None:
        """permit and consult must handle 429 Too Many Requests."""
        for name in ["permit_precheck_api", "yangdo_consult_api"]:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertIn("429", src,
                    f"{name}: missing 429 response handling")

    def test_rate_limiter_in_shared_security(self) -> None:
        """security_http must provide rate limiting for all servers."""
        sec_src = (ROOT / "security_http.py").read_text(encoding="utf-8")
        self.assertIn("SlidingWindowRateLimiter", sec_src)


class TestInputValidationConsistency(unittest.TestCase):
    """All servers must validate request body size."""

    def test_max_body_bytes_enforced(self) -> None:
        """Each server handling POST must enforce max body size."""
        for name in ["permit_precheck_api", "yangdo_consult_api"]:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertIn("max_body_bytes", src,
                    f"{name}: missing body size limit")

    def test_json_content_type_validated(self) -> None:
        """Servers accepting JSON must validate Content-Type."""
        for name in ["permit_precheck_api", "yangdo_consult_api"]:
            with self.subTest(server=name):
                src = _read_src(name)
                self.assertIn("application/json", src,
                    f"{name}: missing Content-Type validation")


if __name__ == "__main__":
    unittest.main()
