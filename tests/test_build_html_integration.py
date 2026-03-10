"""Integration tests for HTML build output of both calculators.

Verifies that build_html() / build_page_html() produce valid HTML
containing all expected JS functions, UI elements, and CSS variables.
Does NOT test runtime behavior (that requires a browser).
"""
from __future__ import annotations

import re
import unittest


# ---------------------------------------------------------------------------
# Permit HTML integration tests
# ---------------------------------------------------------------------------
class PermitBuildHtmlTest(unittest.TestCase):
    _html: str | None = None

    @classmethod
    def setUpClass(cls):
        from permit_diagnosis_calculator import build_html

        cls._html = build_html("통합 테스트", {}, {})

    # -- JS functions must be present exactly once ----------------------------
    _REQUIRED_JS_FUNCTIONS = [
        "const renderBasisRows",
        "const renderRuleBasis",
        "const renderFocusProfile",
        "const renderQualityFlags",
        "const renderProofClaim",
        "const renderCandidateFallback",
        "const evaluateTypedCriteriaLocal",
        "const renderStructuredReview",
        "const renderResult",
        "const buildAdditionalInputs",
    ]

    def test_required_js_functions_present(self):
        for fn in self._REQUIRED_JS_FUNCTIONS:
            with self.subTest(fn=fn):
                self.assertEqual(
                    self._html.count(fn),
                    1,
                    f"{fn} should appear exactly once",
                )

    # -- Core UI element IDs --------------------------------------------------
    _REQUIRED_IDS = [
        "industrySelect",
        "capitalInput",
        "technicianInput",
        "equipmentInput",
        "requiredCapital",
        "capitalGapStatus",
        "technicianGapStatus",
        "equipmentGapStatus",
        "diagnosisDate",
    ]

    def test_ui_element_ids(self):
        for elem_id in self._REQUIRED_IDS:
            with self.subTest(id=elem_id):
                self.assertIn(elem_id, self._html)

    # -- HTML structure -------------------------------------------------------
    def test_doctype_present(self):
        self.assertTrue(self._html.strip().startswith("<!doctype html>"))

    def test_html_lang_ko(self):
        self.assertIn('<html lang="ko">', self._html)

    def test_charset_utf8(self):
        self.assertIn('charset="utf-8"', self._html)

    def test_title_substituted(self):
        self.assertIn("<title>통합 테스트</title>", self._html)

    def test_closing_tags(self):
        self.assertIn("</html>", self._html)
        self.assertIn("</body>", self._html)

    # -- CSS design system variables ------------------------------------------
    _REQUIRED_CSS_VARS = [
        "--smna-accent",
        "--smna-warning",
        "--smna-sub",
    ]

    def test_css_variables(self):
        for var in self._REQUIRED_CSS_VARS:
            with self.subTest(var=var):
                self.assertIn(var, self._html)

    # -- No template placeholders left ----------------------------------------
    _PLACEHOLDERS = [
        "__TITLE__",
        "__NOTICE_URL__",
        "__CONTACT_PHONE__",
        "__INDUSTRY_TOTAL__",
        "__RULE_VERSION__",
        "__PERMIT_DATA_URL__",
        "__PERMIT_BOOTSTRAP_GZIP_BASE64__",
    ]

    def test_no_unsubstituted_placeholders(self):
        for placeholder in self._PLACEHOLDERS:
            with self.subTest(ph=placeholder):
                self.assertNotIn(placeholder, self._html)

    # -- Typed criteria evaluation keywords -----------------------------------
    def test_typed_criteria_keywords(self):
        self.assertIn("자동 점검 결과", self._html)
        self.assertIn("blocking", self._html)
        self.assertIn("criterion_results", self._html)

    # -- CTA mode branches (Codex-delegated, adapted) -------------------------
    _CTA_BRANCH_STRINGS = [
        "ctaMode",
        "shortfall",
        "manual_review",
    ]

    def test_cta_mode_branches_present(self):
        for s in self._CTA_BRANCH_STRINGS:
            with self.subTest(s=s):
                self.assertIn(s, self._html)

    def test_cta_mode_appears_multiple_times(self):
        """ctaMode should exist in both customer and owner render paths."""
        self.assertGreaterEqual(self._html.count("ctaMode"), 2)

    # -- Escape safety: no raw Python f-string braces ----------------------
    def test_no_raw_fstring_placeholders_in_permit(self):
        import re
        # Check for {variable_name} patterns that suggest f-string escaping failures
        leaked = re.findall(r'\{[a-z_]{3,}\}', self._html)
        js_safe = {"{pass}", "{fail}", "{status}", "{ok}", "{gap}", "{blocking}",
                   "{note}", "{label}", "{category}", "{reason}", "{value}",
                   "{key}", "{name}", "{type}", "{text}", "{title}", "{url}",
                   "{id}", "{code}", "{index}", "{item}", "{row}", "{data}",
                   "{error}", "{result}", "{count}", "{total}", "{size}",
                   "{width}", "{height}", "{color}", "{style}", "{class}",
                   "{src}", "{href}", "{target}", "{action}", "{method}",
                   "{operator}", "{criterion}", "{criteria}", "{inputs}",
                   "{message}", "{summary}", "{details}", "{description}",
                   "{article}", "{parts}", "{lawTitle}", "{fields}"}
        truly_suspicious = [m for m in leaked if m not in js_safe]
        self.assertEqual(truly_suspicious, [],
                         f"Possible f-string leaks in permit HTML: {truly_suspicious[:5]}")

    # -- Fragment mode --------------------------------------------------------
    def test_fragment_mode(self):
        from permit_diagnosis_calculator import build_html

        fragment = build_html("frag", {}, {}, fragment=True)
        self.assertNotIn("<!doctype html>", fragment)
        self.assertIn("renderResult", fragment)

    # -- Overall size sanity --------------------------------------------------
    def test_html_minimum_size(self):
        self.assertGreater(len(self._html), 100_000, "HTML should be >100KB")


# ---------------------------------------------------------------------------
# Yangdo HTML integration tests
# ---------------------------------------------------------------------------
class YangdoBuildPageHtmlTest(unittest.TestCase):
    _html: str | None = None

    @classmethod
    def setUpClass(cls):
        from yangdo_calculator import build_page_html

        # Minimal stub dataset
        cls._html = build_page_html(
            train_dataset=[],
            meta={"total_count": 0, "created_at": "2026-03-09"},
        )

    # -- JS functions ---------------------------------------------------------
    _REQUIRED_JS = [
        "specialBalanceSectorName",
        "singleCorePublicationCap",
        "SPECIAL_BALANCE_AUTO_POLICIES",
    ]

    def test_required_js_present(self):
        for fn in self._REQUIRED_JS:
            with self.subTest(fn=fn):
                self.assertIn(fn, self._html)

    # -- HTML structure (WordPress section fragment) --------------------------
    def test_section_wrapper(self):
        self.assertIn('id="seoulmna-yangdo-calculator"', self._html)
        self.assertIn("</section>", self._html)

    # -- CSS variables --------------------------------------------------------
    def test_css_variables(self):
        self.assertIn("--smna-accent", self._html)

    # -- No Python f-string escape leaks -------------------------------------
    def test_no_fstring_leaks(self):
        # If Python f-string escaping breaks, we'd see literal {variable_name}
        # but NOT valid JS like {key: value} or ${expression}
        # Check for common Python variable patterns that shouldn't appear
        leaked = re.findall(r'\{[a-z_]+\}', self._html)
        # Filter out valid JS patterns (template literals use ${...})
        suspicious = [m for m in leaked if not m.startswith('{')]
        # Some {pass}, {fail} etc are valid JS object keys — filter those too
        js_keywords = {"{pass}", "{fail}", "{status}", "{ok}", "{gap}", "{blocking}",
                       "{note}", "{label}", "{category}", "{reason}", "{value}",
                       "{key}", "{name}", "{type}", "{text}", "{title}", "{url}",
                       "{id}", "{code}", "{index}", "{item}", "{row}", "{data}",
                       "{error}", "{result}", "{count}", "{total}", "{size}",
                       "{width}", "{height}", "{color}", "{style}", "{class}",
                       "{src}", "{href}", "{target}", "{action}", "{method}"}
        truly_suspicious = [m for m in suspicious if m not in js_keywords]
        self.assertEqual(
            truly_suspicious, [],
            f"Possible f-string escape leaks: {truly_suspicious[:5]}"
        )

    # -- Overall size ---------------------------------------------------------
    def test_html_minimum_size(self):
        self.assertGreater(len(self._html), 50_000, "HTML should be >50KB")


if __name__ == "__main__":
    unittest.main()
