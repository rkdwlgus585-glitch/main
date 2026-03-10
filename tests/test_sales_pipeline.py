"""Comprehensive tests for sales_pipeline.py — subprocess orchestrator."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock, call, patch

import pytest

from sales_pipeline import _build_parser, _run, main


# ────────────────────────────────────────────────
# _build_parser
# ────────────────────────────────────────────────


class TestBuildParser:
    def test_defaults(self) -> None:
        args = _build_parser().parse_args([])
        assert args.lead_id == ""
        assert args.consult_row == 0
        assert args.top == 5
        assert args.run_match is False
        assert args.skip_recommend is False
        assert args.skip_quote is False
        assert args.dry_run is False
        assert args.no_files is False
        assert args.no_sheet is False

    def test_lead_id(self) -> None:
        args = _build_parser().parse_args(["--lead-id", "abc123"])
        assert args.lead_id == "abc123"

    def test_consult_row(self) -> None:
        args = _build_parser().parse_args(["--consult-row", "7"])
        assert args.consult_row == 7

    def test_top(self) -> None:
        args = _build_parser().parse_args(["--top", "10"])
        assert args.top == 10

    def test_run_match_flag(self) -> None:
        args = _build_parser().parse_args(["--run-match"])
        assert args.run_match is True

    def test_skip_recommend_flag(self) -> None:
        args = _build_parser().parse_args(["--skip-recommend"])
        assert args.skip_recommend is True

    def test_skip_quote_flag(self) -> None:
        args = _build_parser().parse_args(["--skip-quote"])
        assert args.skip_quote is True

    def test_dry_run_flag(self) -> None:
        args = _build_parser().parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_no_files_flag(self) -> None:
        args = _build_parser().parse_args(["--no-files"])
        assert args.no_files is True

    def test_no_sheet_flag(self) -> None:
        args = _build_parser().parse_args(["--no-sheet"])
        assert args.no_sheet is True

    def test_all_flags_combined(self) -> None:
        args = _build_parser().parse_args([
            "--lead-id", "L1",
            "--consult-row", "3",
            "--top", "8",
            "--run-match",
            "--dry-run",
            "--no-files",
            "--no-sheet",
        ])
        assert args.lead_id == "L1"
        assert args.consult_row == 3
        assert args.top == 8
        assert args.run_match is True
        assert args.dry_run is True
        assert args.no_files is True
        assert args.no_sheet is True


# ────────────────────────────────────────────────
# _run
# ────────────────────────────────────────────────


class TestRunHelper:
    @patch("sales_pipeline.subprocess.run")
    def test_returns_exit_code_zero(self, mock_sub) -> None:
        mock_sub.return_value = MagicMock(returncode=0)
        assert _run(["echo", "hello"]) == 0

    @patch("sales_pipeline.subprocess.run")
    def test_returns_nonzero_exit_code(self, mock_sub) -> None:
        mock_sub.return_value = MagicMock(returncode=1)
        assert _run(["bad_cmd"]) == 1

    @patch("sales_pipeline.subprocess.run")
    def test_passes_check_false(self, mock_sub) -> None:
        mock_sub.return_value = MagicMock(returncode=0)
        _run(["test"])
        mock_sub.assert_called_once()
        _, kwargs = mock_sub.call_args
        assert kwargs.get("check") is False


# ────────────────────────────────────────────────
# main — command construction
# ────────────────────────────────────────────────


class TestMainCommandConstruction:
    """Verify main() constructs correct subprocess commands."""

    @patch("sales_pipeline.subprocess.run")
    @patch("sales_pipeline._build_parser")
    def _run_main(self, mock_parser, mock_sub, **kwargs):
        """Helper: run main() with given CLI args and return subprocess calls."""
        defaults = {
            "lead_id": "",
            "consult_row": 0,
            "top": 5,
            "run_match": False,
            "skip_recommend": False,
            "skip_quote": False,
            "dry_run": False,
            "no_files": False,
            "no_sheet": False,
        }
        defaults.update(kwargs)
        mock_args = MagicMock(**defaults)
        mock_parser.return_value.parse_args.return_value = mock_args
        mock_sub.return_value = MagicMock(returncode=0)
        main()
        return mock_sub

    def test_default_runs_recommend_and_quote(self) -> None:
        mock_sub = self._run_main()
        assert mock_sub.call_count == 2  # recommend + quote

    def test_run_match_adds_match_step(self) -> None:
        mock_sub = self._run_main(run_match=True)
        assert mock_sub.call_count == 3  # match + recommend + quote
        first_cmd = mock_sub.call_args_list[0][0][0]
        assert "match.py" in first_cmd[-1]

    def test_skip_recommend(self) -> None:
        mock_sub = self._run_main(skip_recommend=True)
        assert mock_sub.call_count == 1  # only quote
        cmd = mock_sub.call_args_list[0][0][0]
        assert "quote_engine.py" in cmd[-1]

    def test_skip_quote(self) -> None:
        mock_sub = self._run_main(skip_quote=True)
        assert mock_sub.call_count == 1  # only recommend
        cmd = mock_sub.call_args_list[0][0][0]
        assert any("listing_matcher.py" in c for c in cmd)

    def test_skip_both(self) -> None:
        mock_sub = self._run_main(skip_recommend=True, skip_quote=True)
        assert mock_sub.call_count == 0

    def test_lead_id_forwarded_to_recommend(self) -> None:
        mock_sub = self._run_main(lead_id="L42", skip_quote=True)
        cmd = mock_sub.call_args_list[0][0][0]
        assert "--lead-id" in cmd
        assert "L42" in cmd

    def test_lead_id_forwarded_to_quote(self) -> None:
        mock_sub = self._run_main(lead_id="L42", skip_recommend=True)
        cmd = mock_sub.call_args_list[0][0][0]
        assert "--lead-id" in cmd
        assert "L42" in cmd

    def test_consult_row_forwarded(self) -> None:
        mock_sub = self._run_main(consult_row=7, skip_quote=True)
        cmd = mock_sub.call_args_list[0][0][0]
        assert "--consult-row" in cmd
        assert "7" in cmd

    def test_consult_row_zero_not_forwarded(self) -> None:
        mock_sub = self._run_main(consult_row=0, skip_quote=True)
        cmd = mock_sub.call_args_list[0][0][0]
        assert "--consult-row" not in cmd

    def test_top_forwarded_to_recommend(self) -> None:
        mock_sub = self._run_main(top=10, skip_quote=True)
        cmd = mock_sub.call_args_list[0][0][0]
        assert "--top" in cmd
        assert "10" in cmd

    def test_top_minimum_clamp(self) -> None:
        """top=0 → str(max(1,0)) = '1'."""
        mock_sub = self._run_main(top=0, skip_quote=True)
        cmd = mock_sub.call_args_list[0][0][0]
        idx = cmd.index("--top")
        assert cmd[idx + 1] == "1"

    def test_dry_run_forwarded(self) -> None:
        mock_sub = self._run_main(dry_run=True, skip_quote=True)
        cmd = mock_sub.call_args_list[0][0][0]
        assert "--dry-run" in cmd

    def test_no_files_forwarded(self) -> None:
        mock_sub = self._run_main(no_files=True, skip_quote=True)
        cmd = mock_sub.call_args_list[0][0][0]
        assert "--no-files" in cmd

    def test_no_sheet_forwarded(self) -> None:
        mock_sub = self._run_main(no_sheet=True, skip_quote=True)
        cmd = mock_sub.call_args_list[0][0][0]
        assert "--no-sheet" in cmd


# ────────────────────────────────────────────────
# main — exit code aggregation
# ────────────────────────────────────────────────


class TestMainExitCodes:
    @patch("sales_pipeline.subprocess.run")
    @patch("sales_pipeline._build_parser")
    def test_all_success(self, mock_parser, mock_sub) -> None:
        mock_args = MagicMock(
            lead_id="", consult_row=0, top=5,
            run_match=False, skip_recommend=False, skip_quote=False,
            dry_run=False, no_files=False, no_sheet=False,
        )
        mock_parser.return_value.parse_args.return_value = mock_args
        mock_sub.return_value = MagicMock(returncode=0)
        # Should NOT raise
        main()

    @patch("sales_pipeline.subprocess.run")
    @patch("sales_pipeline._build_parser")
    def test_any_failure_raises_systemexit(self, mock_parser, mock_sub) -> None:
        mock_args = MagicMock(
            lead_id="", consult_row=0, top=5,
            run_match=False, skip_recommend=False, skip_quote=False,
            dry_run=False, no_files=False, no_sheet=False,
        )
        mock_parser.return_value.parse_args.return_value = mock_args
        # recommend succeeds, quote fails
        mock_sub.side_effect = [
            MagicMock(returncode=0),  # recommend
            MagicMock(returncode=1),  # quote
        ]
        with pytest.raises(SystemExit):
            main()

    @patch("sales_pipeline.subprocess.run")
    @patch("sales_pipeline._build_parser")
    def test_no_steps_no_exit(self, mock_parser, mock_sub) -> None:
        """Skip everything → empty pipeline → no SystemExit."""
        mock_args = MagicMock(
            lead_id="", consult_row=0, top=5,
            run_match=False, skip_recommend=True, skip_quote=True,
            dry_run=False, no_files=False, no_sheet=False,
        )
        mock_parser.return_value.parse_args.return_value = mock_args
        # Should NOT raise
        main()
        mock_sub.assert_not_called()

    @patch("sales_pipeline.subprocess.run")
    @patch("sales_pipeline._build_parser")
    def test_match_failure_raises(self, mock_parser, mock_sub) -> None:
        mock_args = MagicMock(
            lead_id="", consult_row=0, top=5,
            run_match=True, skip_recommend=True, skip_quote=True,
            dry_run=False, no_files=False, no_sheet=False,
        )
        mock_parser.return_value.parse_args.return_value = mock_args
        mock_sub.return_value = MagicMock(returncode=2)
        with pytest.raises(SystemExit):
            main()
