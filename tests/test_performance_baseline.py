"""Performance regression baselines for HTML build functions.

Ensures build_page_html (yangdo) and build_html (permit) stay within
acceptable latency bounds.  These are NOT micro-benchmarks — they are
coarse guardrails that catch accidental O(n²) regressions, not
minor constant-factor changes.

Thresholds are intentionally generous (5 s / 8 s) so the suite stays
green in CI and on slow hardware, while still catching regressions
that would noticeably degrade user-perceived page-load time.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

# ── paths ─────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "permit_registration_criteria_expanded.json"


# ── minimal fixtures ──────────────────────────────────────────────
@pytest.fixture(scope="module")
def permit_catalog() -> dict:
    """Lightweight permit catalog for build_html."""
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    industries = raw.get("industries", [])[:5]  # 5 industries is enough
    return {
        "industries": industries,
        "summary": {"total_industries": len(industries)},
    }


@pytest.fixture(scope="module")
def permit_rule_catalog() -> dict:
    """Minimal rule catalog."""
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    packs = raw.get("rule_criteria_packs", [])[:5]
    return {"rule_criteria_packs": packs}


@pytest.fixture(scope="module")
def yangdo_dataset() -> list:
    """Synthetic dataset for build_page_html (10 rows)."""
    return [
        {
            "license": "일반건설업",
            "specialty_eok": 10.0 + i,
            "y23_eok": 5.0,
            "y24_eok": 6.0,
            "y25_eok": 7.0,
            "sales3_eok": 18.0,
            "sales5_eok": 29.0,
            "balance_eok": 3.0,
            "capital_eok": 5.0,
            "surplus_eok": 1.5,
            "price_eok": 12.0,
        }
        for i in range(10)
    ]


@pytest.fixture(scope="module")
def yangdo_meta() -> dict:
    """Minimal meta for build_page_html."""
    return {
        "median_specialty": 15.0,
        "p90_specialty": 50.0,
        "median_sales3_eok": 20.0,
        "p90_sales3_eok": 60.0,
        "count": 10,
    }


# ── latency assertions ───────────────────────────────────────────
class TestPermitBuildHtmlLatency:
    """permit_diagnosis_calculator.build_html must complete within 8 s."""

    THRESHOLD_SEC = 8.0

    def test_build_html_under_threshold(
        self, permit_catalog: dict, permit_rule_catalog: dict
    ) -> None:
        from permit_diagnosis_calculator import build_html

        start = time.perf_counter()
        html = build_html(
            title="AI 인허가 사전검토",
            catalog=permit_catalog,
            rule_catalog=permit_rule_catalog,
        )
        elapsed = time.perf_counter() - start
        assert isinstance(html, str)
        assert len(html) > 1000, "build_html produced suspiciously short output"
        assert elapsed < self.THRESHOLD_SEC, (
            f"permit build_html took {elapsed:.2f}s (threshold {self.THRESHOLD_SEC}s)"
        )


class TestYangdoBuildPageHtmlLatency:
    """yangdo_calculator.build_page_html must complete within 5 s."""

    THRESHOLD_SEC = 5.0

    def test_build_page_html_under_threshold(
        self, yangdo_dataset: list, yangdo_meta: dict
    ) -> None:
        from yangdo_calculator import build_page_html

        start = time.perf_counter()
        html = build_page_html(
            train_dataset=yangdo_dataset,
            meta=yangdo_meta,
        )
        elapsed = time.perf_counter() - start
        assert isinstance(html, str)
        assert len(html) > 1000, "build_page_html produced suspiciously short output"
        assert elapsed < self.THRESHOLD_SEC, (
            f"yangdo build_page_html took {elapsed:.2f}s (threshold {self.THRESHOLD_SEC}s)"
        )


class TestHtmlOutputBasicStructure:
    """Sanity checks on the generated HTML."""

    def test_permit_html_has_doctype(
        self, permit_catalog: dict, permit_rule_catalog: dict
    ) -> None:
        from permit_diagnosis_calculator import build_html

        html = build_html(
            title="AI 인허가 사전검토",
            catalog=permit_catalog,
            rule_catalog=permit_rule_catalog,
        )
        assert html.lstrip().lower().startswith("<!doctype html")

    def test_yangdo_html_has_section_root(
        self, yangdo_dataset: list, yangdo_meta: dict
    ) -> None:
        """yangdo produces a <section> fragment (WordPress widget), not a full page."""
        from yangdo_calculator import build_page_html

        html = build_page_html(
            train_dataset=yangdo_dataset,
            meta=yangdo_meta,
        )
        assert html.lstrip().lower().startswith("<section")

    def test_permit_html_contains_script(
        self, permit_catalog: dict, permit_rule_catalog: dict
    ) -> None:
        from permit_diagnosis_calculator import build_html

        html = build_html(
            title="AI 인허가 사전검토",
            catalog=permit_catalog,
            rule_catalog=permit_rule_catalog,
        )
        assert "<script" in html.lower()

    def test_yangdo_html_contains_script(
        self, yangdo_dataset: list, yangdo_meta: dict
    ) -> None:
        from yangdo_calculator import build_page_html

        html = build_page_html(
            train_dataset=yangdo_dataset,
            meta=yangdo_meta,
        )
        assert "<script" in html.lower()


class TestYangdoEstimatePayloadSanitization:
    """Ensure estimateRemote payload text fields are wrapped with sanitizePlain."""

    def test_estimate_payload_uses_sanitize_plain(
        self, yangdo_dataset: list, yangdo_meta: dict
    ) -> None:
        """The generated JS must apply sanitizePlain to all text fields in payload."""
        from yangdo_calculator import build_page_html

        html = build_page_html(
            train_dataset=yangdo_dataset,
            meta=yangdo_meta,
            estimate_endpoint="https://test.example.com/api",
        )
        # All text fields in estimateRemote payload must use sanitizePlain
        expected_sanitized = [
            "sanitizePlain(target.license_raw",
            "sanitizePlain(target.sales_input_mode",
            "sanitizePlain(target.reorg_mode",
            "sanitizePlain(target.balance_usage_mode",
            "sanitizePlain(target.company_type",
            "sanitizePlain(target.credit_level",
            "sanitizePlain(target.admin_history",
        ]
        for fragment in expected_sanitized:
            assert fragment in html, (
                f"estimateRemote payload missing sanitizePlain for: {fragment}"
            )
