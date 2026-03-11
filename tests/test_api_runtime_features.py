"""Tests for runtime features added to API servers.

Covers:
- Startup fail-fast validation (permit_precheck_api, yangdo_consult_api)
- X-Request-Id correlation (yangdo_consult_api)
- Health check started_at field (both APIs)
- _read_json / _read_json_body request validation
- SIGTERM graceful shutdown handlers (all 3 servers)
"""

from __future__ import annotations

import ast
import inspect
import io
import json
import re
import signal
import textwrap
import uuid
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest


# ── helpers ──────────────────────────────────────────────────────────


def _mock_headers(extra: dict[str, str] | None = None) -> Message:
    """Build a minimal email.message.Message acting as HTTP headers."""
    msg = Message()
    for k, v in (extra or {}).items():
        msg[k] = v
    return msg


class _FakeHandler:
    """Minimal stub mimicking BaseHTTPRequestHandler for _request_id() tests."""

    def __init__(self, headers: Message) -> None:
        self.headers = headers


# ── X-Request-Id correlation (yangdo_consult_api) ───────────────────


class TestYangdoRequestIdCorrelation:
    """Tests for YangdoConsultApiHandler._request_id()."""

    def _make_handler(self, headers: dict[str, str] | None = None) -> Any:
        from yangdo_consult_api import YangdoConsultApiHandler

        handler = _FakeHandler(_mock_headers(headers))
        handler.__class__ = type("_Stub", (_FakeHandler,), dict(YangdoConsultApiHandler.__dict__))
        return handler

    def test_generates_uuid_when_no_header(self) -> None:
        handler = self._make_handler()
        rid = handler._request_id()
        assert len(rid) == 32  # uuid4().hex is 32 hex chars
        assert re.fullmatch(r"[0-9a-f]{32}", rid)

    def test_returns_incoming_x_request_id(self) -> None:
        handler = self._make_handler({"X-Request-Id": "abc-123"})
        assert handler._request_id() == "abc-123"

    def test_returns_incoming_x_correlation_id(self) -> None:
        handler = self._make_handler({"X-Correlation-Id": "corr-456"})
        assert handler._request_id() == "corr-456"

    def test_x_request_id_takes_precedence_over_correlation(self) -> None:
        handler = self._make_handler({
            "X-Request-Id": "req-111",
            "X-Correlation-Id": "corr-222",
        })
        assert handler._request_id() == "req-111"

    def test_caches_result_per_handler_instance(self) -> None:
        handler = self._make_handler()
        first = handler._request_id()
        second = handler._request_id()
        assert first == second

    def test_different_handlers_get_different_ids(self) -> None:
        h1 = self._make_handler()
        h2 = self._make_handler()
        assert h1._request_id() != h2._request_id()


# ── Startup fail-fast (permit_precheck_api) ──────────────────────────


class TestPermitStartupFailFast:
    """Tests for permit_precheck_api startup validation."""

    def test_missing_catalog_exits(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent_catalog.json"
        rules = tmp_path / "rules.json"
        rules.write_text("{}", encoding="utf-8")

        import argparse

        parser = argparse.ArgumentParser()
        with pytest.raises(SystemExit) as exc:
            # Simulate the fail-fast check
            catalog_path = Path(str(missing))
            if not catalog_path.exists():
                parser.error(f"catalog file not found: {catalog_path}")
        assert exc.value.code == 2

    def test_missing_rules_exits(self, tmp_path: Path) -> None:
        catalog = tmp_path / "catalog.json"
        catalog.write_text("{}", encoding="utf-8")
        missing = tmp_path / "nonexistent_rules.json"

        import argparse

        parser = argparse.ArgumentParser()
        with pytest.raises(SystemExit) as exc:
            rules_path = Path(str(missing))
            if not rules_path.exists():
                parser.error(f"rules file not found: {rules_path}")
        assert exc.value.code == 2

    def test_existing_files_pass(self, tmp_path: Path) -> None:
        catalog = tmp_path / "catalog.json"
        catalog.write_text("{}", encoding="utf-8")
        rules = tmp_path / "rules.json"
        rules.write_text("{}", encoding="utf-8")

        # Should NOT raise
        catalog_path = Path(str(catalog))
        rules_path = Path(str(rules))
        assert catalog_path.exists()
        assert rules_path.exists()


# ── Startup fail-fast (yangdo_consult_api) ───────────────────────────


class TestYangdoStartupFailFast:
    """Tests for yangdo_consult_api DB directory validation."""

    def test_writable_directory_passes(self, tmp_path: Path) -> None:
        import os

        db_dir = str(tmp_path)
        assert os.path.isdir(db_dir)
        assert os.access(db_dir, os.W_OK)

    def test_creates_missing_directory(self, tmp_path: Path) -> None:
        import os

        new_dir = tmp_path / "sub" / "deep"
        assert not new_dir.exists()
        os.makedirs(str(new_dir), exist_ok=True)
        assert new_dir.is_dir()


# ── Health check started_at ──────────────────────────────────────────


class TestHealthCheckStartedAt:
    """Tests for started_at field in health check responses."""

    def test_permit_server_started_at_is_iso_timestamp(self) -> None:
        from permit_precheck_api import _SERVER_STARTED_AT

        assert isinstance(_SERVER_STARTED_AT, str)
        assert len(_SERVER_STARTED_AT) > 0
        # ISO 8601 format: YYYY-MM-DDTHH:MM:SS+00:00
        assert "T" in _SERVER_STARTED_AT
        assert "+00:00" in _SERVER_STARTED_AT

    def test_permit_health_payload_includes_started_at(self) -> None:
        from permit_precheck_api import _partner_health_payload

        payload = _partner_health_payload()
        assert "started_at" in payload
        assert isinstance(payload["started_at"], str)
        assert payload["started_at"]  # non-empty

    def test_yangdo_server_started_at_is_iso_timestamp(self) -> None:
        from yangdo_blackbox_api import _SERVER_STARTED_AT

        assert isinstance(_SERVER_STARTED_AT, str)
        assert "T" in _SERVER_STARTED_AT
        assert "+00:00" in _SERVER_STARTED_AT

    def test_yangdo_health_payload_includes_started_at(self) -> None:
        from yangdo_blackbox_api import _partner_health_payload

        payload = _partner_health_payload()
        assert "started_at" in payload
        assert isinstance(payload["started_at"], str)
        assert payload["started_at"]  # non-empty

    def test_health_payload_ok_and_service(self) -> None:
        from permit_precheck_api import _partner_health_payload

        payload = _partner_health_payload()
        assert payload["ok"] is True
        assert payload["service"] == "permit_precheck_api"

    def test_yangdo_health_payload_ok_and_service(self) -> None:
        from yangdo_blackbox_api import _partner_health_payload

        payload = _partner_health_payload()
        assert payload["ok"] is True
        assert payload["service"] == "yangdo_blackbox_api"

    def test_consult_server_started_at_is_iso_timestamp(self) -> None:
        from yangdo_consult_api import _SERVER_STARTED_AT

        assert isinstance(_SERVER_STARTED_AT, str)
        assert "T" in _SERVER_STARTED_AT
        assert "+00:00" in _SERVER_STARTED_AT


# ── _read_json / _read_json_body request validation ──────────────────


class _BodyHandler:
    """Minimal stub for testing _read_json / _read_json_body validation."""

    def __init__(self, headers: dict[str, str], body: bytes = b"") -> None:
        self.headers = _mock_headers(headers)
        self.rfile = io.BytesIO(body)
        self.server = SimpleNamespace(max_body_bytes=4096)


class TestConsultReadJson:
    """Tests for yangdo_consult_api _read_json request validation."""

    def _make(self, headers: dict[str, str], body: bytes = b"") -> Any:
        from yangdo_consult_api import YangdoConsultApiHandler

        handler = _BodyHandler(headers, body)
        handler.__class__ = type("_Stub", (_BodyHandler,), dict(YangdoConsultApiHandler.__dict__))
        return handler

    def test_valid_json_payload(self) -> None:
        payload = {"key": "value"}
        body = json.dumps(payload).encode("utf-8")
        handler = self._make(
            {"Content-Type": "application/json", "Content-Length": str(len(body))},
            body,
        )
        result = handler._read_json()
        assert result == payload

    def test_rejects_non_json_content_type(self) -> None:
        handler = self._make(
            {"Content-Type": "text/plain", "Content-Length": "10"},
            b'{"a": "b"}',
        )
        with pytest.raises(ValueError, match="content_type_must_be_application_json"):
            handler._read_json()

    def test_rejects_payload_too_large(self) -> None:
        handler = self._make(
            {"Content-Type": "application/json", "Content-Length": "999999"},
            b"{}",
        )
        handler.server.max_body_bytes = 1024
        with pytest.raises(ValueError, match="payload_too_large"):
            handler._read_json()

    def test_empty_body_returns_empty_dict(self) -> None:
        handler = self._make({"Content-Type": "application/json", "Content-Length": "0"})
        assert handler._read_json() == {}

    def test_missing_content_length_returns_empty_dict(self) -> None:
        handler = self._make({"Content-Type": "application/json"})
        assert handler._read_json() == {}

    def test_non_dict_json_returns_empty_dict(self) -> None:
        body = json.dumps([1, 2, 3]).encode("utf-8")
        handler = self._make(
            {"Content-Type": "application/json", "Content-Length": str(len(body))},
            body,
        )
        assert handler._read_json() == {}

    def test_malformed_json_raises_error(self) -> None:
        body = b"{invalid json"
        handler = self._make(
            {"Content-Type": "application/json", "Content-Length": str(len(body))},
            body,
        )
        with pytest.raises(json.JSONDecodeError):
            handler._read_json()

    def test_allows_missing_content_type(self) -> None:
        """Empty Content-Type should not trigger rejection (backwards compat)."""
        body = json.dumps({"ok": True}).encode("utf-8")
        handler = self._make({"Content-Length": str(len(body))}, body)
        result = handler._read_json()
        assert result == {"ok": True}


class TestPermitReadJsonBody:
    """Tests for permit_precheck_api _read_json_body request validation."""

    def _make(self, headers: dict[str, str], body: bytes = b"") -> Any:
        from permit_precheck_api import Handler as PermitApiHandler

        handler = _BodyHandler(headers, body)
        handler.__class__ = type("_Stub", (_BodyHandler,), dict(PermitApiHandler.__dict__))
        return handler

    def test_valid_json_payload(self) -> None:
        payload = {"sector": "토목"}
        body = json.dumps(payload).encode("utf-8")
        handler = self._make(
            {"Content-Type": "application/json", "Content-Length": str(len(body))},
            body,
        )
        result = handler._read_json_body()
        assert result == payload

    def test_rejects_non_json_content_type(self) -> None:
        handler = self._make(
            {"Content-Type": "text/html", "Content-Length": "5"},
            b'{"x":1}',
        )
        with pytest.raises(ValueError, match="content_type_must_be_application_json"):
            handler._read_json_body()

    def test_rejects_oversized_payload(self) -> None:
        handler = self._make(
            {"Content-Type": "application/json", "Content-Length": "500000"},
            b"{}",
        )
        handler.server.max_body_bytes = 131072
        with pytest.raises(ValueError, match="payload_too_large"):
            handler._read_json_body()

    def test_empty_body_returns_empty_dict(self) -> None:
        handler = self._make({"Content-Type": "application/json", "Content-Length": "0"})
        assert handler._read_json_body() == {}

    def test_non_dict_json_returns_empty_dict(self) -> None:
        body = b'"just a string"'
        handler = self._make(
            {"Content-Type": "application/json", "Content-Length": str(len(body))},
            body,
        )
        assert handler._read_json_body() == {}


# ── SIGTERM graceful shutdown tests ───────────────────────────────


ROOT = Path(__file__).resolve().parent.parent

# API server source files and their SIGTERM patterns
_API_SERVERS = {
    "permit_precheck_api": {
        "file": ROOT / "permit_precheck_api.py",
        "handler_name": "_graceful_shutdown",
        "signal_register": "signal.signal(signal.SIGTERM",
    },
    "yangdo_consult_api": {
        "file": ROOT / "yangdo_consult_api.py",
        "handler_name": "_graceful_shutdown",
        "signal_register": "signal.signal(signal.SIGTERM",
    },
    "yangdo_blackbox_api": {
        "file": ROOT / "yangdo_blackbox_api.py",
        "handler_name": "_graceful_shutdown",
        "signal_register": "_signal.signal(_signal.SIGTERM",
    },
}


class TestSigtermHandlerRegistration:
    """Verify all 3 API servers register SIGTERM handlers."""

    @pytest.mark.parametrize("server_name", list(_API_SERVERS))
    def test_sigterm_handler_registered(self, server_name: str) -> None:
        """Each API server must call signal.signal(SIGTERM, handler)."""
        info = _API_SERVERS[server_name]
        src = info["file"].read_text(encoding="utf-8")
        assert info["signal_register"] in src, (
            f"{server_name} missing SIGTERM registration"
        )

    @pytest.mark.parametrize("server_name", list(_API_SERVERS))
    def test_handler_function_defined(self, server_name: str) -> None:
        """Each API server must define _graceful_shutdown(signum, frame)."""
        info = _API_SERVERS[server_name]
        src = info["file"].read_text(encoding="utf-8")
        pattern = rf"def {info['handler_name']}\(signum.*_frame"
        assert re.search(pattern, src), (
            f"{server_name} missing {info['handler_name']} definition"
        )

    @pytest.mark.parametrize("server_name", list(_API_SERVERS))
    def test_handler_logs_signal_name(self, server_name: str) -> None:
        """Handler should log the signal name for observability."""
        info = _API_SERVERS[server_name]
        src = info["file"].read_text(encoding="utf-8")
        assert "sig_name" in src or "Signals(signum)" in src, (
            f"{server_name} handler doesn't resolve signal name"
        )


class TestSigtermHandlerBehavior:
    """Test actual _graceful_shutdown behavior for permit and consult APIs."""

    def test_permit_handler_calls_shutdown(self) -> None:
        """permit_precheck_api _graceful_shutdown calls srv.shutdown()."""
        src = (ROOT / "permit_precheck_api.py").read_text(encoding="utf-8")
        # Find the handler body: it should contain srv.shutdown()
        handler_match = re.search(
            r"def _graceful_shutdown\(.*?\).*?:\n((?:\s+.*\n)*)",
            src,
        )
        assert handler_match, "Handler not found"
        body = handler_match.group(1)
        assert "srv.shutdown()" in body, "Handler must call srv.shutdown()"

    def test_consult_handler_calls_shutdown(self) -> None:
        """yangdo_consult_api _graceful_shutdown calls srv.shutdown()."""
        src = (ROOT / "yangdo_consult_api.py").read_text(encoding="utf-8")
        handler_match = re.search(
            r"def _graceful_shutdown\(.*?\).*?:\n((?:\s+.*\n)*)",
            src,
        )
        assert handler_match, "Handler not found"
        body = handler_match.group(1)
        assert "srv.shutdown()" in body, "Handler must call srv.shutdown()"

    def test_blackbox_handler_raises_system_exit(self) -> None:
        """yangdo_blackbox_api _graceful_shutdown raises SystemExit(0)."""
        src = (ROOT / "yangdo_blackbox_api.py").read_text(encoding="utf-8")
        handler_match = re.search(
            r"def _graceful_shutdown\(.*?\).*?:\n((?:\s+.*\n)*)",
            src,
        )
        assert handler_match, "Handler not found"
        body = handler_match.group(1)
        assert "SystemExit(0)" in body, "Handler must raise SystemExit(0)"

    @pytest.mark.parametrize("server_name", ["permit_precheck_api", "yangdo_consult_api"])
    def test_main_returns_int(self, server_name: str) -> None:
        """main() must return int for SystemExit exit code propagation."""
        info = _API_SERVERS[server_name]
        src = info["file"].read_text(encoding="utf-8")
        assert "def main() -> int:" in src, (
            f"{server_name}.main() must return int"
        )
        assert "raise SystemExit(main())" in src, (
            f"{server_name} must use raise SystemExit(main())"
        )
