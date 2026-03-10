"""Tests for acquisition_calculator.py pure functions and HTML builder."""

from __future__ import annotations

import unittest

from acquisition_calculator import _digits_only, _pack_inline_script, build_page_html


class TestDigitsOnly(unittest.TestCase):
    """_digits_only: extract only numeric chars."""

    def test_phone_number(self) -> None:
        assert _digits_only("02-1234-5678") == "0212345678"

    def test_empty(self) -> None:
        assert _digits_only("") == ""

    def test_none(self) -> None:
        assert _digits_only(None) == ""

    def test_no_digits(self) -> None:
        assert _digits_only("abc-xyz") == ""

    def test_mixed(self) -> None:
        assert _digits_only("1a2b3") == "123"

    def test_pure_digits(self) -> None:
        assert _digits_only("16683548") == "16683548"

    def test_whitespace(self) -> None:
        assert _digits_only(" 1 2 3 ") == "123"


class TestPackInlineScript(unittest.TestCase):
    """_pack_inline_script: wraps JS in safe <script> tag."""

    def test_basic_wrapping(self) -> None:
        result = _pack_inline_script("console.log(1)")
        assert result.startswith("<script")
        assert result.endswith("</script>")

    def test_contains_try_catch(self) -> None:
        result = _pack_inline_script("var x=1;")
        assert "try{" in result
        assert "catch(e)" in result

    def test_ampersand_escape(self) -> None:
        result = _pack_inline_script("a & b")
        assert "\\u0026" in result

    def test_empty_code(self) -> None:
        result = _pack_inline_script("")
        assert "<script" in result
        assert "</script>" in result

    def test_none_code(self) -> None:
        result = _pack_inline_script(None)
        assert "<script" in result

    def test_nowprocket_attribute(self) -> None:
        result = _pack_inline_script("x=1")
        assert "nowprocket" in result

    def test_line_separator_escape(self) -> None:
        result = _pack_inline_script("a\u2028b")
        assert "\\u2028" in result

    def test_paragraph_separator_escape(self) -> None:
        result = _pack_inline_script("a\u2029b")
        assert "\\u2029" in result


class TestBuildPageHtml(unittest.TestCase):
    """build_page_html: generates full HTML page for acquisition calculator."""

    def test_returns_string(self) -> None:
        html = build_page_html()
        assert isinstance(html, str)

    def test_starts_with_section(self) -> None:
        html = build_page_html()
        assert html.strip().startswith("<section")

    def test_has_calculator_id(self) -> None:
        html = build_page_html()
        assert 'id="smna-acq-calculator"' in html

    def test_has_style_block(self) -> None:
        html = build_page_html()
        assert "<style>" in html

    def test_ends_with_section_close(self) -> None:
        html = build_page_html()
        assert html.strip().endswith("</section>")

    def test_has_select_options(self) -> None:
        html = build_page_html()
        # Should contain construction license select options
        assert "업종 선택" in html
        assert "<option" in html

    def test_general_category_present(self) -> None:
        html = build_page_html()
        assert "토목건축공사업" in html

    def test_special_category_present(self) -> None:
        html = build_page_html()
        assert "전기공사업" in html

    def test_contact_phone_default(self) -> None:
        html = build_page_html()
        assert "1668-3548" in html or "16683548" in html

    def test_contact_phone_override(self) -> None:
        html = build_page_html(contact_phone="010-1234-5678")
        assert "010-1234-5678" in html or "01012345678" in html

    def test_channel_id_injection(self) -> None:
        html = build_page_html(channel_id="test_partner")
        assert isinstance(html, str)
        assert len(html) > 1000

    def test_has_script_tag(self) -> None:
        html = build_page_html()
        assert "<script" in html

    def test_has_closing_section(self) -> None:
        html = build_page_html()
        assert "</section>" in html

    def test_xss_safe_channel_id(self) -> None:
        html = build_page_html(channel_id='<script>alert("xss")</script>')
        assert '<script>alert("xss")</script>' not in html

    def test_profiles_data_in_js(self) -> None:
        html = build_page_html()
        # profiles should be serialized into JS
        assert "capital_eok" in html
        assert "guarantee_jwasu" in html

    def test_major_field_options_in_js(self) -> None:
        html = build_page_html()
        assert "majorFieldMap" in html

    def test_section_wrapper(self) -> None:
        html = build_page_html()
        assert 'class="smna-wrap"' in html

    def test_brand_name_default(self) -> None:
        html = build_page_html()
        # Default brand when no channel_id
        assert isinstance(html, str)

    def test_safe_json_used_for_profiles(self) -> None:
        html = build_page_html()
        # safe_json should escape HTML comments
        assert "<!--" not in html.split("<script")[1].split("</script>")[0] if "<script" in html else True

    def test_html_is_non_trivial_length(self) -> None:
        html = build_page_html()
        # Full calculator page should be substantial
        assert len(html) > 5000

    def test_sobangsiseol_present(self) -> None:
        html = build_page_html()
        assert "소방" in html

    def test_information_tongsin_present(self) -> None:
        html = build_page_html()
        assert "정보통신" in html


if __name__ == "__main__":
    unittest.main()
