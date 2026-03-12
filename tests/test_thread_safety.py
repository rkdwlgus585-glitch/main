"""Verify thread-safety of shared mutable state in API servers.

The permit and consult API servers use ``ThreadingHTTPServer``, which
spawns a new thread per request.  Shared objects (engine, usage writer,
CRM bridge) must protect concurrent access with locks.

These tests verify:
1. Lock existence and type.
2. ``refresh()`` swaps state atomically under lock.
3. Double-checked locking in ``_connect()`` methods.
4. Concurrent calls do not corrupt state.
"""

from __future__ import annotations

import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from unittest.mock import MagicMock, patch


class PermitEngineThreadSafetyTest(unittest.TestCase):
    """Thread-safety of PermitPrecheckEngine.refresh()."""

    def _make_engine(self) -> Any:
        """Create an engine with mocked file loaders."""
        from permit_precheck_api import PermitPrecheckEngine

        with (
            patch("permit_precheck_api._load_catalog", return_value={"industries": []}),
            patch("permit_precheck_api._load_rule_catalog", return_value={}),
            patch("permit_precheck_api._build_rule_index", return_value={}),
            patch("permit_precheck_api._prepare_ui_payload", return_value={"summary": {}, "rule_catalog_meta": {}}),
        ):
            engine = PermitPrecheckEngine(catalog_path="/dev/null", rules_path="/dev/null")
        return engine

    def test_lock_exists_and_is_lock(self) -> None:
        engine = self._make_engine()
        self.assertIsInstance(engine._lock, type(threading.Lock()))

    def test_refresh_acquires_lock(self) -> None:
        """refresh() must acquire _lock when swapping state."""
        engine = self._make_engine()
        acquire_count = 0
        real_lock = engine._lock

        class TrackingLock:
            """Wrapper that tracks lock acquisition."""

            def acquire(self, *a: Any, **kw: Any) -> Any:
                nonlocal acquire_count
                acquire_count += 1
                return real_lock.acquire(*a, **kw)

            def release(self) -> None:
                return real_lock.release()

            def __enter__(self) -> Any:
                self.acquire()
                return self

            def __exit__(self, *a: Any) -> None:
                self.release()

        engine._lock = TrackingLock()  # type: ignore[assignment]

        with (
            patch("permit_precheck_api._load_catalog", return_value={"industries": []}),
            patch("permit_precheck_api._load_rule_catalog", return_value={}),
            patch("permit_precheck_api._build_rule_index", return_value={}),
            patch("permit_precheck_api._prepare_ui_payload", return_value={"summary": {"industry_total": 42}, "rule_catalog_meta": {}}),
        ):
            engine.refresh()

        self.assertGreaterEqual(acquire_count, 1, "refresh() did not acquire _lock")

    def test_refresh_state_is_consistent(self) -> None:
        """After refresh(), all state fields must reflect the same data generation."""
        engine = self._make_engine()

        payloads = [
            {"summary": {"industry_total": i}, "rule_catalog_meta": {"version": f"v{i}"}}
            for i in range(10)
        ]

        def do_refresh(idx: int) -> dict[str, Any]:
            with (
                patch("permit_precheck_api._load_catalog", return_value={"industries": [{"idx": idx}]}),
                patch("permit_precheck_api._load_rule_catalog", return_value={"v": idx}),
                patch("permit_precheck_api._build_rule_index", return_value={"idx": idx}),
                patch("permit_precheck_api._prepare_ui_payload", return_value=payloads[idx]),
            ):
                return engine.refresh()

        # Run 10 concurrent refreshes — result should always be consistent
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(do_refresh, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]

        # Final state must correspond to ONE of the 10 refreshes (not a mix)
        final_industry_total = engine._meta.get("industry_total")
        final_version = engine._meta.get("rule_catalog_version")
        # Both fields must come from the same refresh call
        self.assertIsNotNone(final_industry_total)
        self.assertIsNotNone(final_version)
        # version should be "v{industry_total}" if state is consistent
        self.assertEqual(final_version, f"v{final_industry_total}")

    def test_meta_property_returns_copy(self) -> None:
        """meta property must return a copy, not the internal dict."""
        engine = self._make_engine()
        meta1 = engine.meta
        meta2 = engine.meta
        self.assertEqual(meta1, meta2)
        self.assertIsNot(meta1, meta2)


class UsageSheetWriterThreadSafetyTest(unittest.TestCase):
    """Thread-safety of UsageSheetWriter._connect() and append_usage()."""

    def _make_writer(self) -> Any:
        from yangdo_consult_api import UsageSheetWriter

        writer = UsageSheetWriter(enabled=False)
        return writer

    def test_lock_exists(self) -> None:
        writer = self._make_writer()
        self.assertIsInstance(writer._lock, type(threading.Lock()))

    def test_connect_uses_double_checked_locking(self) -> None:
        """_connect() must check _ws inside the lock to avoid duplicate init."""
        writer = self._make_writer()
        writer.enabled = True
        # Pre-set _ws to simulate already-connected state
        mock_ws = MagicMock()
        writer._ws = mock_ws
        result = writer._connect()
        # Should return existing _ws without re-initializing
        self.assertIs(result, mock_ws)

    def test_disabled_writer_returns_immediately(self) -> None:
        writer = self._make_writer()
        writer.enabled = False
        result = writer.append_usage({"source": "test"})
        self.assertEqual(result, {"ok": False, "reason": "disabled"})


class CrmBridgeThreadSafetyTest(unittest.TestCase):
    """Thread-safety of CrmBridge._connect()."""

    def _make_bridge(self) -> Any:
        from yangdo_consult_api import CrmBridge

        bridge = CrmBridge(enabled=False)
        return bridge

    def test_lock_exists(self) -> None:
        bridge = self._make_bridge()
        self.assertIsInstance(bridge._hub_lock, type(threading.Lock()))

    def test_connect_returns_none_when_disabled(self) -> None:
        bridge = self._make_bridge()
        self.assertIsNone(bridge._connect())

    def test_connect_reuses_cached_hub(self) -> None:
        """_connect() must reuse _hub under lock if already initialized."""
        bridge = self._make_bridge()
        bridge.enabled = True
        mock_hub = MagicMock()
        bridge._hub = mock_hub
        result = bridge._connect()
        self.assertIs(result, mock_hub)

    def test_disabled_submit_returns_status(self) -> None:
        bridge = self._make_bridge()
        result = bridge.submit({}, [], "normal")
        self.assertEqual(result["status"], "disabled")


if __name__ == "__main__":
    unittest.main()
