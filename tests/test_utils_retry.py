"""Unit tests for utils.retry_request decorator.

Covers: success path, retry backoff, max retries exhausted,
no_retry flag, custom exception filter, and functools.wraps metadata.
All sleep calls are mocked — no real delays.
"""

import unittest
from unittest.mock import patch, call

from utils import retry_request


class _TransientError(Exception):
    """Simulated transient failure (e.g. network timeout)."""


class _PermanentError(Exception):
    """Simulated non-recoverable failure (e.g. auth error)."""


class _NoRetryError(Exception):
    """Error with no_retry flag set."""

    def __init__(self, msg="no retry"):
        super().__init__(msg)
        self.no_retry = True


class RetrySuccessTest(unittest.TestCase):
    """Success-path tests."""

    @patch("utils.time.sleep")
    def test_success_on_first_call(self, mock_sleep):
        call_count = 0

        @retry_request(max_retries=3, delay=1, backoff=2)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeed()
        self.assertEqual(result, "ok")
        self.assertEqual(call_count, 1)
        mock_sleep.assert_not_called()

    @patch("utils.time.sleep")
    def test_success_after_one_retry(self, mock_sleep):
        attempts = 0

        @retry_request(max_retries=3, delay=1, backoff=2)
        def flaky():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise _TransientError("try again")
            return "recovered"

        result = flaky()
        self.assertEqual(result, "recovered")
        self.assertEqual(attempts, 2)
        self.assertEqual(mock_sleep.call_count, 1)

    @patch("utils.time.sleep")
    def test_success_after_all_retries(self, mock_sleep):
        attempts = 0

        @retry_request(max_retries=3, delay=1, backoff=2)
        def succeed_on_last():
            nonlocal attempts
            attempts += 1
            if attempts <= 3:
                raise _TransientError("not yet")
            return "finally"

        result = succeed_on_last()
        self.assertEqual(result, "finally")
        self.assertEqual(attempts, 4)  # initial + 3 retries
        self.assertEqual(mock_sleep.call_count, 3)

    @patch("utils.time.sleep")
    def test_preserves_return_value(self, mock_sleep):
        @retry_request(max_retries=1, delay=0, backoff=1)
        def returns_dict():
            return {"key": "value", "items": [1, 2, 3]}

        self.assertEqual(returns_dict(), {"key": "value", "items": [1, 2, 3]})


class RetryExhaustedTest(unittest.TestCase):
    """Tests for when all retries are exhausted."""

    @patch("utils.time.sleep")
    def test_raises_last_exception(self, mock_sleep):
        @retry_request(max_retries=2, delay=1, backoff=1)
        def always_fail():
            raise _TransientError("boom")

        with self.assertRaises(_TransientError) as cm:
            always_fail()
        self.assertIn("boom", str(cm.exception))

    @patch("utils.time.sleep")
    def test_total_attempts_equals_max_plus_one(self, mock_sleep):
        attempts = 0

        @retry_request(max_retries=3, delay=1, backoff=1)
        def count_calls():
            nonlocal attempts
            attempts += 1
            raise _TransientError("fail")

        with self.assertRaises(_TransientError):
            count_calls()
        self.assertEqual(attempts, 4)  # 1 initial + 3 retries

    @patch("utils.time.sleep")
    def test_zero_retries_calls_once(self, mock_sleep):
        attempts = 0

        @retry_request(max_retries=0, delay=1, backoff=1)
        def no_retry():
            nonlocal attempts
            attempts += 1
            raise _TransientError("once")

        with self.assertRaises(_TransientError):
            no_retry()
        self.assertEqual(attempts, 1)
        mock_sleep.assert_not_called()


class RetryBackoffTest(unittest.TestCase):
    """Tests for exponential backoff timing."""

    @patch("utils.time.sleep")
    def test_exponential_backoff(self, mock_sleep):
        @retry_request(max_retries=3, delay=2, backoff=3)
        def always_fail():
            raise _TransientError("fail")

        with self.assertRaises(_TransientError):
            always_fail()

        # delay * backoff^attempt: 2*3^0=2, 2*3^1=6, 2*3^2=18
        expected = [call(2), call(6), call(18)]
        self.assertEqual(mock_sleep.call_args_list, expected)

    @patch("utils.time.sleep")
    def test_linear_backoff(self, mock_sleep):
        @retry_request(max_retries=3, delay=5, backoff=1)
        def always_fail():
            raise _TransientError("fail")

        with self.assertRaises(_TransientError):
            always_fail()

        # delay * 1^attempt = 5 each time
        expected = [call(5), call(5), call(5)]
        self.assertEqual(mock_sleep.call_args_list, expected)


class NoRetryFlagTest(unittest.TestCase):
    """Tests for the no_retry exception attribute."""

    @patch("utils.time.sleep")
    def test_no_retry_flag_skips_retries(self, mock_sleep):
        attempts = 0

        @retry_request(max_retries=5, delay=1, backoff=1)
        def abort_fast():
            nonlocal attempts
            attempts += 1
            raise _NoRetryError("stop immediately")

        with self.assertRaises(_NoRetryError):
            abort_fast()
        self.assertEqual(attempts, 1)
        mock_sleep.assert_not_called()

    @patch("utils.time.sleep")
    def test_no_retry_flag_false_retries_normally(self, mock_sleep):
        attempts = 0

        @retry_request(max_retries=2, delay=1, backoff=1)
        def normal_error():
            nonlocal attempts
            attempts += 1
            e = _TransientError("retryable")
            e.no_retry = False
            raise e

        with self.assertRaises(_TransientError):
            normal_error()
        self.assertEqual(attempts, 3)  # initial + 2 retries


class CustomExceptionFilterTest(unittest.TestCase):
    """Tests for custom exception type filtering."""

    @patch("utils.time.sleep")
    def test_only_retries_specified_exceptions(self, mock_sleep):
        attempts = 0

        @retry_request(max_retries=3, delay=1, backoff=1, exceptions=(_TransientError,))
        def wrong_error():
            nonlocal attempts
            attempts += 1
            raise _PermanentError("not retryable")

        with self.assertRaises(_PermanentError):
            wrong_error()
        self.assertEqual(attempts, 1)
        mock_sleep.assert_not_called()

    @patch("utils.time.sleep")
    def test_retries_matching_exception(self, mock_sleep):
        attempts = 0

        @retry_request(max_retries=2, delay=1, backoff=1, exceptions=(_TransientError,))
        def transient_then_ok():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise _TransientError("still failing")
            return "ok"

        result = transient_then_ok()
        self.assertEqual(result, "ok")
        self.assertEqual(attempts, 3)


class FuncMetadataTest(unittest.TestCase):
    """Tests that @wraps preserves function metadata."""

    @patch("utils.time.sleep")
    def test_preserves_name(self, _):
        @retry_request(max_retries=1, delay=0, backoff=1)
        def my_api_call():
            """Fetch data from the API."""
            return True

        self.assertEqual(my_api_call.__name__, "my_api_call")

    @patch("utils.time.sleep")
    def test_preserves_docstring(self, _):
        @retry_request(max_retries=1, delay=0, backoff=1)
        def documented_fn():
            """This is the docstring."""
            return True

        self.assertEqual(documented_fn.__doc__, "This is the docstring.")

    @patch("utils.time.sleep")
    def test_passes_args_and_kwargs(self, _):
        @retry_request(max_retries=1, delay=0, backoff=1)
        def add(a, b, extra=0):
            return a + b + extra

        self.assertEqual(add(3, 4), 7)
        self.assertEqual(add(3, 4, extra=10), 17)


if __name__ == "__main__":
    unittest.main()
