"""Tests for scripts.widget_health_contract — load_widget_health_contract()."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.widget_health_contract import _read_json, load_widget_health_contract


# ── _read_json ──────────────────────────────────────────────────────


class TestReadJson:
    def test_missing_file_returns_empty_dict(self, tmp_path: Path) -> None:
        result = _read_json(tmp_path / "nonexistent.json")
        assert result == {}

    def test_valid_json_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "data.json"
        p.write_text('{"a": 1}', encoding="utf-8")
        assert _read_json(p) == {"a": 1}

    def test_non_dict_json_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "list.json"
        p.write_text("[1, 2, 3]", encoding="utf-8")
        assert _read_json(p) == {}

    def test_corrupted_json_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{not valid json!!!}", encoding="utf-8")
        assert _read_json(p) == {}

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.json"
        p.write_text("", encoding="utf-8")
        assert _read_json(p) == {}


# ── load_widget_health_contract ─────────────────────────────────────


class TestLoadWidgetHealthContract:
    def _write_dashboard(self, tmp_path: Path, data: dict) -> Path:
        p = tmp_path / "dashboard.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return p

    def test_missing_file_returns_fallback(self, tmp_path: Path) -> None:
        result = load_widget_health_contract(tmp_path / "missing.json")
        assert result["ok"] is False
        assert "missing-dashboard" in result["text"]
        assert result["components"] == {}
        assert result["generated_at"] == ""

    def test_valid_dashboard_extracts_fields(self, tmp_path: Path) -> None:
        data = {
            "generated_at": "2026-03-11T12:00:00+00:00",
            "one_line_summary": {
                "ok": True,
                "text": "ALL GREEN | 245/245 pass",
                "components": {"permit": True, "yangdo": True, "platform": True},
            },
        }
        result = load_widget_health_contract(self._write_dashboard(tmp_path, data))
        assert result["ok"] is True
        assert result["text"] == "ALL GREEN | 245/245 pass"
        assert result["components"] == {"permit": True, "yangdo": True, "platform": True}
        assert result["generated_at"] == "2026-03-11T12:00:00+00:00"

    def test_empty_text_triggers_fallback(self, tmp_path: Path) -> None:
        data = {
            "one_line_summary": {"ok": True, "text": "", "components": {}},
        }
        result = load_widget_health_contract(self._write_dashboard(tmp_path, data))
        assert result["ok"] is False
        assert "missing-dashboard" in result["text"]

    def test_missing_one_line_summary_triggers_fallback(self, tmp_path: Path) -> None:
        data = {"generated_at": "2026-03-11"}
        result = load_widget_health_contract(self._write_dashboard(tmp_path, data))
        assert result["ok"] is False
        assert "missing-dashboard" in result["text"]

    def test_none_components_returns_empty_dict(self, tmp_path: Path) -> None:
        data = {
            "one_line_summary": {"ok": True, "text": "healthy", "components": None},
        }
        result = load_widget_health_contract(self._write_dashboard(tmp_path, data))
        assert result["ok"] is True
        assert result["components"] == {}

    def test_component_values_coerced_to_bool(self, tmp_path: Path) -> None:
        data = {
            "one_line_summary": {
                "ok": True,
                "text": "partial",
                "components": {"permit": 1, "yangdo": 0, "platform": "yes"},
            },
        }
        result = load_widget_health_contract(self._write_dashboard(tmp_path, data))
        assert result["components"]["permit"] is True
        assert result["components"]["yangdo"] is False
        assert result["components"]["platform"] is True

    def test_corrupted_json_triggers_fallback(self, tmp_path: Path) -> None:
        p = tmp_path / "corrupt.json"
        p.write_text("{{bad json}}", encoding="utf-8")
        result = load_widget_health_contract(p)
        assert result["ok"] is False
        assert "missing-dashboard" in result["text"]

    def test_source_field_contains_path(self, tmp_path: Path) -> None:
        data = {"one_line_summary": {"ok": True, "text": "ok"}}
        path = self._write_dashboard(tmp_path, data)
        result = load_widget_health_contract(path)
        assert "dashboard.json" in result["source"]

    def test_custom_path_overrides_default(self, tmp_path: Path) -> None:
        data = {"one_line_summary": {"ok": True, "text": "custom"}}
        path = tmp_path / "custom_path" / "health.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        result = load_widget_health_contract(path)
        assert result["text"] == "custom"
        assert "custom_path" in result["source"]
