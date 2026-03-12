"""Tests for utils.ProgressCallback — GUI progress tracking helper."""

from __future__ import annotations

import unittest

from utils import ProgressCallback


class ProgressCallbackTest(unittest.TestCase):
    """ProgressCallback step tracking and callback invocation."""

    def test_initial_state(self) -> None:
        cb = ProgressCallback()
        self.assertEqual(cb.current_step, 0)
        self.assertEqual(cb.total_steps, 5)

    def test_update_returns_progress_and_message(self) -> None:
        cb = ProgressCallback()
        progress, msg = cb.update(step=0)
        self.assertEqual(progress, 0.0)
        self.assertIn("키워드", msg)

    def test_update_step_2(self) -> None:
        cb = ProgressCallback()
        progress, msg = cb.update(step=2)
        self.assertAlmostEqual(progress, 40.0)
        self.assertIn("썸네일", msg)

    def test_update_final_step(self) -> None:
        cb = ProgressCallback()
        progress, msg = cb.update(step=4)
        self.assertAlmostEqual(progress, 80.0)
        self.assertIn("완료", msg)

    def test_custom_message_overrides_default(self) -> None:
        cb = ProgressCallback()
        _, msg = cb.update(step=1, message="커스텀 메시지")
        self.assertEqual(msg, "커스텀 메시지")

    def test_callback_func_invoked(self) -> None:
        calls: list[tuple[float, str]] = []
        cb = ProgressCallback(callback_func=lambda p, m: calls.append((p, m)))
        cb.update(step=3)
        self.assertEqual(len(calls), 1)
        self.assertAlmostEqual(calls[0][0], 60.0)

    def test_no_callback_does_not_raise(self) -> None:
        cb = ProgressCallback(callback_func=None)
        progress, msg = cb.update(step=1)
        self.assertAlmostEqual(progress, 20.0)

    def test_step_beyond_range_clamps(self) -> None:
        cb = ProgressCallback()
        _, msg = cb.update(step=99)
        # Should use last step message without IndexError
        self.assertIsInstance(msg, str)


if __name__ == "__main__":
    unittest.main()
