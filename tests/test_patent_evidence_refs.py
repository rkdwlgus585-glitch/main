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
    # Track A
    "yangdo_blackbox_api.py:781": "_estimate_response_tier",
    "core_engine/yangdo_listing_recommender.py:492": "build_recommendation_bundle",
    "yangdo_blackbox_api.py:1170": "def estimate",
    "yangdo_blackbox_api.py:1089": "usage_snapshot",
    # Track B
    "core_engine/permit_criteria_schema.py:196": "evaluate_typed_criteria",
    "permit_diagnosis_calculator.py:519": "_merge_expanded_rule_metadata",
    "permit_precheck_api.py:569": "usage_snapshot",
    "permit_precheck_api.py:264": "check_system",
    "permit_precheck_api.py:1301": "do_POST",
    "core_engine/permit_mapping_pipeline.py:40": "apply_mapping_pipeline",
    # Track P
    "core_engine/tenant_gateway.py:37": "TenantGateway",
    "core_engine/channel_profiles.py:47": "ChannelRouter",
    "core_engine/api_response.py:35": "build_response_envelope",
    # Track C — Production resilience (graceful shutdown + infrastructure)
    "yangdo_blackbox_api.py:1360": "_graceful_shutdown",
    "permit_precheck_api.py:1482": "_graceful_shutdown",
    "yangdo_consult_api.py:1064": "_graceful_shutdown",
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
        """Every ref in EVIDENCE_EXPECTATIONS should appear in the brief."""
        if not BRIEF.exists():
            self.skipTest("Brief file not found")
        content = BRIEF.read_text(encoding="utf-8")
        for ref in EVIDENCE_EXPECTATIONS:
            rel_path, lineno = ref.rsplit(":", 1)
            # Brief stores paths with backslashes (Windows)
            win_ref = f"{rel_path.replace('/', chr(92))}:{lineno}"
            fwd_ref = f"{rel_path}:{lineno}"
            self.assertTrue(
                win_ref in content or fwd_ref in content,
                f"Reference {ref} not found in patent brief",
            )


if __name__ == "__main__":
    unittest.main()
