"""Tests for core_engine.sandbox — partner sandbox/demo mode."""
from __future__ import annotations

from core_engine.sandbox import (
    is_sandbox_request,
    sandbox_permit_response,
    sandbox_yangdo_response,
)


class FakeHeaders:
    """Minimal mock for HTTP headers."""

    def __init__(self, data=None):
        self._data = dict(data or {})

    def get(self, key, default=""):
        return self._data.get(key, default)


# ── is_sandbox_request ────────────────────────────────────────────


def test_sandbox_header_true():
    assert is_sandbox_request(FakeHeaders({"X-Sandbox": "true"})) is True


def test_sandbox_header_one():
    assert is_sandbox_request(FakeHeaders({"X-Sandbox": "1"})) is True


def test_sandbox_header_yes():
    assert is_sandbox_request(FakeHeaders({"X-Sandbox": "yes"})) is True


def test_sandbox_header_false():
    assert is_sandbox_request(FakeHeaders({"X-Sandbox": "false"})) is False


def test_sandbox_header_empty():
    assert is_sandbox_request(FakeHeaders({})) is False


def test_sandbox_header_none():
    assert is_sandbox_request(None) is False


def test_sandbox_api_key_prefix():
    assert is_sandbox_request(FakeHeaders({}), api_key="sandbox_test123") is True


def test_sandbox_api_key_normal():
    assert is_sandbox_request(FakeHeaders({}), api_key="real_key_123") is False


def test_sandbox_api_key_empty():
    assert is_sandbox_request(FakeHeaders({}), api_key="") is False


def test_sandbox_both_header_and_key():
    """Both header and key trigger sandbox."""
    assert is_sandbox_request(FakeHeaders({"X-Sandbox": "true"}), api_key="sandbox_x") is True


def test_sandbox_header_case_insensitive():
    assert is_sandbox_request(FakeHeaders({"X-Sandbox": "TRUE"})) is True
    assert is_sandbox_request(FakeHeaders({"X-Sandbox": "True"})) is True
    assert is_sandbox_request(FakeHeaders({"X-Sandbox": "Yes"})) is True


# ── sandbox_permit_response ───────────────────────────────────────


def test_permit_response_structure():
    resp = sandbox_permit_response()
    assert resp["ok"] is True
    assert resp["sandbox"] is True
    assert "result" in resp
    assert "timestamp" in resp


def test_permit_response_result_fields():
    result = sandbox_permit_response()["result"]
    assert result["verdict"] == "conditional_pass"
    assert result["service_code"] == "4111"
    assert "criteria_summary" in result
    assert "recommendation" in result


def test_permit_response_isolation():
    """Each call returns an independent copy."""
    r1 = sandbox_permit_response()
    r2 = sandbox_permit_response()
    r1["result"]["verdict"] = "mutated"
    assert r2["result"]["verdict"] == "conditional_pass"


# ── sandbox_yangdo_response ───────────────────────────────────────


def test_yangdo_response_structure():
    resp = sandbox_yangdo_response()
    assert resp["ok"] is True
    assert resp["sandbox"] is True
    assert "result" in resp
    assert "timestamp" in resp


def test_yangdo_response_result_fields():
    result = sandbox_yangdo_response()["result"]
    assert isinstance(result["center_eok"], (int, float))
    assert isinstance(result["range_low_eok"], (int, float))
    assert isinstance(result["range_high_eok"], (int, float))
    assert isinstance(result["confidence"], (int, float))
    assert isinstance(result["neighbors"], list)
    assert len(result["neighbors"]) >= 1


def test_yangdo_response_isolation():
    """Each call returns an independent copy."""
    r1 = sandbox_yangdo_response()
    r2 = sandbox_yangdo_response()
    r1["result"]["center_eok"] = -999
    assert r2["result"]["center_eok"] > 0
