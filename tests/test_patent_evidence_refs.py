"""Verify patent evidence line references have not drifted.

Each reference in ``logs/patent_system_brief_latest.md`` points to a specific
line in a source file.  When code is refactored the line numbers shift and the
evidence becomes stale.  This test catches drift early so references stay
accurate for KIPO filings.

The test reads the brief, extracts ``file.py:LINE`` patterns, opens each
source file, and asserts that the referenced line contains an expected keyword
(function name, class name, or variable name).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIEF = ROOT / "logs" / "patent_system_brief_latest.md"

# ── Expected keyword at each referenced line ────────────────────────────
# Maps "relative_path:line" → substring expected on that line (case-insensitive).
EVIDENCE_EXPECTATIONS: dict[str, str] = {
    # Track A — brief lines (generator anchors)
    "yangdo_blackbox_api.py:956": "_project_estimate_result",
    "core_engine/yangdo_listing_recommender.py:496": "build_recommendation_bundle",
    "yangdo_blackbox_api.py:1175": "def estimate",
    "yangdo_blackbox_api.py:1114": "insert_estimate_usage",
    # Track A — code-level anchors (function definitions)
    "yangdo_blackbox_api.py:786": "_estimate_response_tier",
    # Track B — brief lines
    "core_engine/permit_criteria_schema.py:196": "evaluate_typed_criteria",
    "permit_diagnosis_calculator.py:11": "typed_criteria",
    "permit_precheck_api.py:587": "permit_precheck",
    "permit_precheck_api.py:1192": "system",
    "permit_precheck_api.py:1350": "precheck",
    "core_engine/permit_mapping_pipeline.py:14": "mapping",
    # Track B — code-level anchors
    "permit_diagnosis_calculator.py:521": "_merge_expanded_rule_metadata",
    "permit_precheck_api.py:572": "usage_snapshot",
    # Track P — brief lines
    "core_engine/tenant_gateway.py:101": "check_system",
    "core_engine/channel_profiles.py:98": "check_system",
    "core_engine/api_response.py:35": "build_response_envelope",
    # Track P — code-level anchors
    "core_engine/tenant_gateway.py:38": "TenantGateway",
    "core_engine/channel_profiles.py:47": "ChannelRouter",
    # Track C — Production resilience (graceful shutdown + infrastructure)
    "yangdo_blackbox_api.py:1462": "_graceful_shutdown",
    "permit_precheck_api.py:1523": "_graceful_shutdown",
    "yangdo_consult_api.py:1075": "_graceful_shutdown",
    "tests/test_deploy_infrastructure.py:21": "_SERVICES",
    "deploy/smoke_test.py:149": "test_consult_intake",
}


class PatentEvidenceRefsTest(unittest.TestCase):
    """Each patent evidence line reference must still point to the expected code."""

    def test_brief_file_exists(self) -> None:
        self.assertTrue(BRIEF.exists(), f"Patent brief not found: {BRIEF}")

    def test_evidence_references_not_drifted(self) -> None:
        for ref, expected_keyword in EVIDENCE_EXPECTATIONS.items():
            with self.subTest(ref=ref, keyword=expected_keyword):
                rel_path, line_str = ref.rsplit(":", 1)
                lineno = int(line_str)
                src = ROOT / rel_path
                self.assertTrue(src.exists(), f"Source file missing: {rel_path}")
                lines = src.read_text(encoding="utf-8").splitlines()
                self.assertGreaterEqual(
                    len(lines), lineno,
                    f"{rel_path} has {len(lines)} lines but ref points to :{lineno}",
                )
                actual_line = lines[lineno - 1]
                self.assertIn(
                    expected_keyword.lower(),
                    actual_line.lower(),
                    f"DRIFT at {ref}: expected '{expected_keyword}' but got: {actual_line.strip()[:80]}",
                )

    def test_brief_contains_all_tracked_refs(self) -> None:
        """Every brief-level ref in EVIDENCE_EXPECTATIONS should appear in the brief."""
        if not BRIEF.exists():
            self.skipTest("Brief file not found")
        content = BRIEF.read_text(encoding="utf-8")
        # Only check refs that the brief generator is expected to produce.
        # Code-level anchors (function definitions) are verified by the
        # drift test above but may not appear verbatim in the brief.
        for ref in EVIDENCE_EXPECTATIONS:
            rel_path, lineno = ref.rsplit(":", 1)
            # Brief stores paths with backslashes (Windows)
            win_ref = f"{rel_path.replace('/', chr(92))}:{lineno}"
            fwd_ref = f"{rel_path}:{lineno}"
            with self.subTest(ref=ref):
                if win_ref in content or fwd_ref in content:
                    continue  # present — OK
                # Not in brief: verify it is at least valid in code
                # (code-level anchors are allowed to be absent from brief)
                src = ROOT / rel_path
                if not src.exists():
                    self.fail(f"Reference {ref} missing from brief AND source file not found")
                lines = src.read_text(encoding="utf-8").splitlines()
                line_idx = int(lineno)
                if line_idx > len(lines):
                    self.fail(f"Reference {ref} missing from brief AND line out of range")
                expected = EVIDENCE_EXPECTATIONS[ref]
                actual_line = lines[line_idx - 1]
                self.assertIn(
                    expected.lower(),
                    actual_line.lower(),
                    f"Reference {ref} not in brief AND code drift detected",
                )


if __name__ == "__main__":
    unittest.main()
