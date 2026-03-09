"""Unit tests for premium_auto.py pure functions."""

import sys
import types as _types
import unittest

# ---------------------------------------------------------------------------
# Stubs for heavy dependencies (selenium, genai, webdriver_manager, tkinter)
# ---------------------------------------------------------------------------
for mod_name in [
    "selenium", "selenium.webdriver", "selenium.webdriver.chrome",
    "selenium.webdriver.chrome.service", "selenium.webdriver.chrome.options",
    "selenium.webdriver.common", "selenium.webdriver.common.by",
    "selenium.webdriver.common.keys", "selenium.webdriver.common.action_chains",
    "selenium.webdriver.support", "selenium.webdriver.support.ui",
    "selenium.webdriver.support.expected_conditions",
    "selenium.common", "selenium.common.exceptions",
    "webdriver_manager", "webdriver_manager.chrome",
    "google", "google.genai", "google.genai.types",
]:
    if mod_name not in sys.modules:
        m = _types.ModuleType(mod_name)
        sys.modules[mod_name] = m

# Provide required classes/attributes on the stubs
_exc_mod = sys.modules["selenium.common.exceptions"]
_exc_mod.InvalidSessionIdException = type("InvalidSessionIdException", (Exception,), {})
_exc_mod.WebDriverException = type("WebDriverException", (Exception,), {})

_by_mod = sys.modules["selenium.webdriver.common.by"]
_by_mod.By = type("By", (), {"CSS_SELECTOR": "css selector", "NAME": "name", "TAG_NAME": "tag name", "ID": "id"})

_opts_mod = sys.modules["selenium.webdriver.chrome.options"]
_opts_mod.Options = type("Options", (), {"add_argument": lambda s, *a: None})

_svc_mod = sys.modules["selenium.webdriver.chrome.service"]
_svc_mod.Service = type("Service", (), {"__init__": lambda s, *a, **k: None})

_wd_mod = sys.modules["selenium.webdriver"]
_wd_mod.Chrome = type("Chrome", (), {"__init__": lambda s, *a, **k: None})

_wdm_mod = sys.modules["webdriver_manager.chrome"]
_wdm_mod.ChromeDriverManager = type("ChromeDriverManager", (), {
    "__init__": lambda s, *a, **k: None,
    "install": lambda s: "chromedriver",
})

_keys_mod = sys.modules["selenium.webdriver.common.keys"]
_keys_mod.Keys = type("Keys", (), {})

_ac_mod = sys.modules["selenium.webdriver.common.action_chains"]
_ac_mod.ActionChains = type("ActionChains", (), {"__init__": lambda s, *a: None})

_wait_mod = sys.modules["selenium.webdriver.support.ui"]
_wait_mod.WebDriverWait = type("WebDriverWait", (), {"__init__": lambda s, *a, **k: None})

_ec_mod = sys.modules["selenium.webdriver.support.expected_conditions"]

_genai_mod = sys.modules["google.genai"]
_genai_mod.Client = type("Client", (), {"__init__": lambda s, *a, **k: None})
_genai_types = sys.modules["google.genai.types"]
_genai_types.GenerateContentConfig = type("GenerateContentConfig", (), {"__init__": lambda s, *a, **k: None})

# Now import
from premium_auto import (  # noqa: E402
    _safe_error_text,
    _safe_html,
    _phone_href,
    PremiumCrawler,
    ContentGenerator,
)


# ===================================================================
# _safe_error_text
# ===================================================================
class SafeErrorTextTest(unittest.TestCase):
    def test_normal_error(self):
        self.assertEqual(_safe_error_text(ValueError("bad value")), "bad value")

    def test_none_error(self):
        self.assertEqual(_safe_error_text(None), "unknown error")

    def test_empty_string_error(self):
        result = _safe_error_text(ValueError(""))
        self.assertEqual(result, "ValueError")

    def test_none_string_error(self):
        # str(err) == "None" → err.__class__.__name__
        result = _safe_error_text(Exception("none"))
        self.assertEqual(result, "Exception")

    def test_whitespace_only(self):
        result = _safe_error_text(Exception("   "))
        self.assertEqual(result, "Exception")


# ===================================================================
# _safe_html
# ===================================================================
class SafeHtmlTest(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(_safe_html("hello"), "hello")

    def test_html_chars(self):
        self.assertEqual(_safe_html('<script>alert("x")</script>'),
                         '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;')

    def test_none(self):
        # value or "" converts None to "" before str()
        self.assertEqual(_safe_html(None), "")

    def test_empty(self):
        self.assertEqual(_safe_html(""), "")

    def test_quotes(self):
        self.assertIn("&quot;", _safe_html('"quoted"'))

    def test_ampersand(self):
        self.assertIn("&amp;", _safe_html("A&B"))


# ===================================================================
# _phone_href
# ===================================================================
class PhoneHrefTest(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(_phone_href("010-9926-8661"), "01099268661")

    def test_with_plus(self):
        self.assertEqual(_phone_href("+82-10-1234-5678"), "+821012345678")

    def test_none(self):
        self.assertEqual(_phone_href(None), "")

    def test_empty(self):
        self.assertEqual(_phone_href(""), "")

    def test_already_clean(self):
        self.assertEqual(_phone_href("01012345678"), "01012345678")


# ===================================================================
# PremiumCrawler._extract_number_from_text (static)
# ===================================================================
class ExtractNumberTest(unittest.TestCase):
    def test_standard_format(self):
        self.assertEqual(PremiumCrawler._extract_number_from_text("매물 8001"), 8001)

    def test_je_ho_format(self):
        self.assertEqual(PremiumCrawler._extract_number_from_text("제 8100 호"), 8100)

    def test_ho_suffix(self):
        self.assertEqual(PremiumCrawler._extract_number_from_text("8200호"), 8200)

    def test_bare_number(self):
        self.assertEqual(PremiumCrawler._extract_number_from_text("건설업 8500 양도"), 8500)

    def test_out_of_range_low(self):
        self.assertIsNone(PremiumCrawler._extract_number_from_text("매물 1000"))

    def test_out_of_range_high(self):
        self.assertIsNone(PremiumCrawler._extract_number_from_text("매물 99999"))

    def test_empty(self):
        self.assertIsNone(PremiumCrawler._extract_number_from_text(""))

    def test_none(self):
        self.assertIsNone(PremiumCrawler._extract_number_from_text(None))

    def test_no_number(self):
        self.assertIsNone(PremiumCrawler._extract_number_from_text("전기공사업 양도"))

    def test_boundary_7000(self):
        self.assertEqual(PremiumCrawler._extract_number_from_text("7000호"), 7000)

    def test_boundary_9999(self):
        self.assertEqual(PremiumCrawler._extract_number_from_text("9999호"), 9999)

    def test_multiline_whitespace(self):
        self.assertEqual(PremiumCrawler._extract_number_from_text("  매물\n  8300  "), 8300)


# ===================================================================
# PremiumCrawler._int_config (static)
# ===================================================================
class IntConfigTest(unittest.TestCase):
    def test_valid(self):
        result = PremiumCrawler._int_config("MNA_SCAN_WINDOW", 220)
        self.assertIsInstance(result, int)

    def test_default_on_invalid(self):
        # When CONFIG value is invalid, falls back to default
        import premium_auto
        orig = premium_auto.CONFIG.get("MNA_SCAN_WINDOW")
        premium_auto.CONFIG["MNA_SCAN_WINDOW"] = "abc"
        try:
            result = PremiumCrawler._int_config("MNA_SCAN_WINDOW", 220)
            self.assertEqual(result, 220)
        finally:
            if orig is not None:
                premium_auto.CONFIG["MNA_SCAN_WINDOW"] = orig

    def test_missing_key(self):
        result = PremiumCrawler._int_config("NONEXISTENT_KEY_12345", 42)
        self.assertEqual(result, 42)


# ===================================================================
# PremiumCrawler._estimate_required_pages
# ===================================================================
class EstimateRequiredPagesTest(unittest.TestCase):
    def setUp(self):
        self.crawler = object.__new__(PremiumCrawler)

    def test_no_latest(self):
        result = self.crawler._estimate_required_pages(7611, 0)
        self.assertEqual(result, 20)

    def test_negative_latest(self):
        result = self.crawler._estimate_required_pages(7611, -1)
        self.assertEqual(result, 20)

    def test_normal_span(self):
        # span = 8000 - 7611 = 389, pages = (389 // 8) + 6 = 54
        result = self.crawler._estimate_required_pages(7611, 8000)
        self.assertEqual(result, 54)

    def test_minimum_10(self):
        # span very small
        result = self.crawler._estimate_required_pages(8000, 8005)
        self.assertGreaterEqual(result, 10)

    def test_capped_by_hard_limit(self):
        # Very large span should be capped
        result = self.crawler._estimate_required_pages(1000, 9999)
        self.assertLessEqual(result, 120)


# ===================================================================
# ContentGenerator.render_html
# ===================================================================
class RenderHtmlTest(unittest.TestCase):
    def setUp(self):
        self.gen = object.__new__(ContentGenerator)
        self.gen.client = None

    def test_basic_render(self):
        data = {"번호": 8001, "업종": "전기공사업"}
        ai_content = {
            "title": "전기공사업 양도 (매물 8001)",
            "summary_points": ["포인트1", "포인트2"],
            "analysis": [{"title": "분석1", "content": "내용1"}],
            "faq": [{"q": "질문1", "a": "답변1"}],
        }
        html, title = self.gen.render_html(data, ai_content)
        self.assertIn("8001", html)
        self.assertIn("전기공사업", html)
        self.assertIn("포인트1", html)
        self.assertIn("분석1", html)
        self.assertIn("질문1", html)
        self.assertEqual(title, "전기공사업 양도 (매물 8001)")

    def test_empty_ai_content(self):
        data = {"번호": 8002, "업종": "토목"}
        html, title = self.gen.render_html(data, {})
        self.assertIn("8002", html)

    def test_xss_prevention_number(self):
        """Script in number must be escaped everywhere including URL slug."""
        data = {"번호": '<script>alert("x")</script>', "업종": "건축"}
        ai_content = {"title": "test", "summary_points": [], "analysis": [], "faq": []}
        html, title = self.gen.render_html(data, ai_content)
        # Raw <script> must not appear unescaped
        self.assertNotIn("<script>", html)
        self.assertNotIn("</script>", html)

    def test_xss_prevention_summary(self):
        """XSS in summary_points is escaped via _safe_html."""
        data = {"번호": 8001, "업종": "건축"}
        ai_content = {
            "title": "test",
            "summary_points": ['<img onerror="hack">'],
            "analysis": [],
            "faq": [],
        }
        html, title = self.gen.render_html(data, ai_content)
        # Raw img tag must not appear — only entity-encoded version is safe
        self.assertNotIn('<img onerror', html)
        self.assertIn('&lt;img', html)

    def test_none_ai_content(self):
        data = {"번호": 8003}
        html, title = self.gen.render_html(data, None)
        self.assertIn("8003", html)


if __name__ == "__main__":
    unittest.main()
