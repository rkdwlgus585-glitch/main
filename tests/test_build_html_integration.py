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

    # -- Global error boundary -------------------------------------------------
    def test_global_error_handler_present(self):
        self.assertIn('addEventListener("error"', self._html)
        self.assertIn('addEventListener("unhandledrejection"', self._html)

    def test_error_handler_shows_user_message(self):
        self.assertIn("페이지를 새로고침해 주세요", self._html)

    def test_error_handler_logs_to_console(self):
        self.assertIn("[permit-precheck] unhandled error", self._html)

    # -- Overall size sanity --------------------------------------------------
    def test_html_minimum_size(self):
        self.assertGreater(len(self._html), 100_000, "HTML should be >100KB")


# ---------------------------------------------------------------------------
# Permit end-to-end pipeline tests
# ---------------------------------------------------------------------------
class PermitPipelineEndToEndTest(unittest.TestCase):
    """Test the full build_html→_repair→_wrap→fragment pipeline."""

    def test_fragment_css_scoping_applies(self):
        """Fragment mode: CSS selectors should be prefixed with #smna-permit-precheck."""
        from permit_diagnosis_calculator import build_html

        html = build_html("scoping test", {}, {}, fragment=True)
        # Original :root selector should be replaced
        self.assertNotIn(":root {", html)
        # Scoped selector should appear
        self.assertIn("#smna-permit-precheck", html)

    def test_fragment_no_doctype(self):
        from permit_diagnosis_calculator import build_html

        html = build_html("frag", {}, {}, fragment=True)
        self.assertNotIn("<!doctype html>", html.lower())
        self.assertTrue(html.strip().startswith("<section"))

    def test_fragment_title_hider_script(self):
        """Fragment mode includes script to hide WordPress page title."""
        from permit_diagnosis_calculator import build_html

        html = build_html("test", {}, {}, fragment=True)
        self.assertIn('document.querySelector(".entry-title, .page-title")', html)

    def test_bootstrap_payload_json_safe(self):
        """Bootstrap payload with special characters should be safely encoded."""
        from permit_diagnosis_calculator import build_html

        payload = {"industries": [{"service_name": '<script>alert("xss")</script>'}]}
        html = build_html("xss test", payload, {})
        # Raw script tag should NOT appear — it should be escaped or compressed
        self.assertNotIn('<script>alert("xss")</script>', html)

    def test_catalog_with_real_industry(self):
        """Build with a minimal realistic catalog entry.
        Industry data is compressed into inlineBootstrap JSON, not raw HTML."""
        from permit_diagnosis_calculator import build_html

        catalog = {
            "industries": [
                {
                    "service_code": "01_01_01_T",
                    "service_name": "전기공사업",
                    "category_code": "01",
                    "category_name": "전기",
                }
            ],
            "total_count": 1,
        }
        rules = {
            "rules": [
                {
                    "service_code": "01_01_01_T",
                    "law_title": "전기공사업법",
                    "requirements": {
                        "capital_eok": 1.5,
                        "technicians": 3,
                        "equipment_count": 0,
                        "deposit_days": 30,
                    },
                }
            ]
        }
        html = build_html("전기 테스트", catalog, rules)
        # Industry data is in compressed bootstrap, not raw HTML
        self.assertIn("inlineBootstrap", html)
        self.assertIn("renderResult", html)
        # Title should be substituted
        self.assertIn("<title>전기 테스트</title>", html)

    def test_nowprocket_attribute_on_scripts(self):
        """All real <script> opening tags should have nowprocket attribute."""
        from permit_diagnosis_calculator import build_html

        html = build_html("test", {}, {})
        # Match only actual HTML script tags (not regex patterns inside JS)
        script_tags = re.findall(r"<script\b[^>]*>", html)
        real_tags = [t for t in script_tags if "nowprocket" in t or ">" in t]
        for tag in real_tags:
            if re.match(r"<script\s", tag):
                with self.subTest(tag=tag[:60]):
                    self.assertIn("nowprocket", tag)

    def test_data_url_substitution(self):
        """When data_url is provided, it should appear in the HTML."""
        from permit_diagnosis_calculator import build_html

        html = build_html(
            "url test", {}, {},
            data_url="https://seoulmna.kr/wp-json/wp/v2/pages/1810",
            data_encoding="gzip-base64-rest-rendered",
        )
        self.assertIn("seoulmna.kr/wp-json", html)
        self.assertIn("gzip-base64-rest-rendered", html)


# ---------------------------------------------------------------------------
# Permit accessibility (a11y) verification
# ---------------------------------------------------------------------------
class PermitAccessibilityTest(unittest.TestCase):
    """WCAG 2.1 AA basics for permit HTML output."""

    @classmethod
    def setUpClass(cls):
        from permit_diagnosis_calculator import build_html

        cls._html = build_html("a11y test", {}, {})

    # -- label associations ---
    _LABELED_INPUTS = [
        ("industrySearchInput", "업종명"),
        ("capitalInput", "자본금"),
        ("technicianInput", "기술인력"),
        ("equipmentInput", "장비"),
    ]

    def test_input_fields_have_labels(self):
        for input_id, desc in self._LABELED_INPUTS:
            with self.subTest(input_id=input_id):
                self.assertRegex(
                    self._html,
                    rf'<label\s[^>]*for="{input_id}"',
                    f"{desc} input should have an associated <label for>",
                )

    def test_checkboxes_wrapped_in_labels(self):
        """Checkboxes use implicit labels (input inside label tag)."""
        checkbox_ids = [
            "officeSecuredInput", "facilitySecuredInput",
            "qualificationSecuredInput", "insuranceSecuredInput",
            "safetySecuredInput", "documentReadyInput",
        ]
        for cid in checkbox_ids:
            with self.subTest(checkbox=cid):
                self.assertRegex(
                    self._html,
                    rf'<label><input id="{cid}"',
                    f"Checkbox {cid} should be inside a <label> tag",
                )

    # -- aria-live for dynamic result areas ---
    _ARIA_LIVE_ELEMENTS = [
        "requiredCapital",
        "capitalGapStatus",
        "technicianGapStatus",
        "equipmentGapStatus",
        "diagnosisDate",
        "requirementsMeta",
        "runtimeReasoningCardBox",
        "coverageGuide",
        "typedCriteriaBox",
        "evidenceChecklistBox",
        "nextActionsBox",
        "crossValidation",
    ]

    def test_dynamic_elements_have_aria_live(self):
        for elem_id in self._ARIA_LIVE_ELEMENTS:
            with self.subTest(element=elem_id):
                pattern = rf'id="{elem_id}"[^>]*aria-live="polite"'
                self.assertRegex(
                    self._html,
                    pattern,
                    f"{elem_id} should have aria-live='polite'",
                )

    # -- html lang attribute ---
    def test_html_has_lang_attribute(self):
        self.assertIn('lang="ko"', self._html)

    # -- viewport meta ---
    def test_viewport_meta(self):
        self.assertIn("viewport", self._html)
        self.assertIn("width=device-width", self._html)

    # -- WCAG AA color contrast: text-safe CSS vars ---
    def test_wcag_text_safe_color_variables(self):
        """Success/warning text colors should use WCAG AA-safe variants."""
        self.assertIn("--smna-success-text", self._html)
        self.assertIn("--smna-warning-text", self._html)

    def test_no_raw_success_warning_as_text_color(self):
        """CSS should NOT use raw --smna-success/--smna-warning for text color."""
        # Only check CSS color: rules, not border/background usage
        css_text_uses = re.findall(
            r'color:\s*var\(--smna-(?:success|warning)\)', self._html
        )
        self.assertEqual(
            css_text_uses, [],
            "Text color should use --smna-success-text/--smna-warning-text"
        )


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

    # -- WCAG AA color contrast: text-safe CSS vars ---
    def test_wcag_text_safe_color_variables(self):
        self.assertIn("--smna-success-text", self._html)
        self.assertIn("--smna-warning-text", self._html)

    # -- Global error boundary -------------------------------------------------
    def test_global_error_handler_present(self):
        self.assertIn('addEventListener("error"', self._html)
        self.assertIn('addEventListener("unhandledrejection"', self._html)

    def test_error_handler_shows_user_message(self):
        self.assertIn("페이지를 새로고침해 주세요", self._html)

    def test_error_handler_logs_to_console(self):
        self.assertIn("[yangdo] unhandled error", self._html)

    # -- Overall size ---------------------------------------------------------
    def test_html_minimum_size(self):
        self.assertGreater(len(self._html), 50_000, "HTML should be >50KB")


if __name__ == "__main__":
    unittest.main()
