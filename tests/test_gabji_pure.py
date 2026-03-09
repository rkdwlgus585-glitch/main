"""Unit tests for gabji.py pure functions.

Covers: string normalization, price parsing/formatting, deduplication,
boolean coercion, license formatting, and Korean currency conversion.
"""

import unittest

import gabji


# ===================================================================
# _split_lines
# ===================================================================
class SplitLinesTest(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(gabji._split_lines("a\nb\nc"), ["a", "b", "c"])

    def test_empty(self):
        self.assertEqual(gabji._split_lines(""), [])

    def test_none(self):
        self.assertEqual(gabji._split_lines(None), [])

    def test_whitespace_stripped(self):
        self.assertEqual(gabji._split_lines("  a  \n  b  "), ["a", "b"])

    def test_blank_lines_removed(self):
        self.assertEqual(gabji._split_lines("a\n\n\nb"), ["a", "b"])

    def test_single_line(self):
        self.assertEqual(gabji._split_lines("hello"), ["hello"])

    def test_crlf(self):
        self.assertEqual(gabji._split_lines("a\r\nb"), ["a", "b"])


# ===================================================================
# _is_truthy
# ===================================================================
class IsTruthyTest(unittest.TestCase):
    def test_true_values(self):
        for val in ("1", "y", "yes", "true", "on", "TRUE", "Yes", "ON"):
            self.assertTrue(gabji._is_truthy(val), f"Expected truthy: {val!r}")

    def test_false_values(self):
        for val in ("0", "n", "no", "false", "off", "", None, "maybe"):
            self.assertFalse(gabji._is_truthy(val), f"Expected falsy: {val!r}")

    def test_whitespace(self):
        self.assertTrue(gabji._is_truthy("  yes  "))


# ===================================================================
# _normalize_site_base_url
# ===================================================================
class NormalizeSiteBaseUrlTest(unittest.TestCase):
    def test_default(self):
        self.assertEqual(gabji._normalize_site_base_url(""), "https://seoulmna.co.kr")

    def test_none(self):
        self.assertEqual(gabji._normalize_site_base_url(None), "https://seoulmna.co.kr")

    def test_with_protocol(self):
        self.assertEqual(gabji._normalize_site_base_url("http://example.com/"), "http://example.com")

    def test_without_protocol(self):
        self.assertEqual(gabji._normalize_site_base_url("example.com"), "https://example.com")

    def test_trailing_slash_stripped(self):
        self.assertEqual(gabji._normalize_site_base_url("https://x.com///"), "https://x.com")


# ===================================================================
# _dedupe_keep_order
# ===================================================================
class DedupeKeepOrderTest(unittest.TestCase):
    def test_no_dupes(self):
        self.assertEqual(gabji._dedupe_keep_order(["a", "b", "c"]), ["a", "b", "c"])

    def test_case_insensitive_dedup(self):
        self.assertEqual(gabji._dedupe_keep_order(["Hello", "hello", "HELLO"]), ["Hello"])

    def test_empty_filtered(self):
        self.assertEqual(gabji._dedupe_keep_order(["a", "", None, "  ", "b"]), ["a", "b"])

    def test_preserves_first(self):
        self.assertEqual(gabji._dedupe_keep_order(["B", "a", "b", "A"]), ["B", "a"])

    def test_empty_input(self):
        self.assertEqual(gabji._dedupe_keep_order([]), [])


# ===================================================================
# _digits_only
# ===================================================================
class DigitsOnlyTest(unittest.TestCase):
    def test_mixed(self):
        self.assertEqual(gabji._digits_only("abc123def456"), "123456")

    def test_none(self):
        self.assertEqual(gabji._digits_only(None), "")

    def test_no_digits(self):
        self.assertEqual(gabji._digits_only("hello"), "")

    def test_pure_digits(self):
        self.assertEqual(gabji._digits_only("12345"), "12345")

    def test_korean(self):
        self.assertEqual(gabji._digits_only("등록번호 2024-001"), "2024001")


# ===================================================================
# _extract_price_fragment
# ===================================================================
class ExtractPriceFragmentTest(unittest.TestCase):
    def test_eok(self):
        self.assertEqual(gabji._extract_price_fragment("2.5억"), "2.5억")

    def test_eok_man(self):
        self.assertEqual(gabji._extract_price_fragment("1억 5000만"), "1억5000만")

    def test_man(self):
        self.assertEqual(gabji._extract_price_fragment("3000만"), "3000만")

    def test_plain_number(self):
        self.assertEqual(gabji._extract_price_fragment("1500"), "1500")

    def test_prefix_stripped(self):
        self.assertEqual(gabji._extract_price_fragment("양도가: 2.5억"), "2.5억")

    def test_empty(self):
        self.assertEqual(gabji._extract_price_fragment(""), "")

    def test_none(self):
        self.assertEqual(gabji._extract_price_fragment(None), "")

    def test_no_number(self):
        self.assertEqual(gabji._extract_price_fragment("협의"), "")

    def test_number_with_eok_context(self):
        # "2.5" plain number in text with "억" elsewhere
        self.assertEqual(gabji._extract_price_fragment("약 2억"), "2억")


# ===================================================================
# extract_final_yangdo_price
# ===================================================================
class ExtractFinalYangdoPriceTest(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(gabji.extract_final_yangdo_price("2.5억"), "2.5억")

    def test_range_takes_last(self):
        self.assertEqual(gabji.extract_final_yangdo_price("2억~3억"), "3억")

    def test_none(self):
        self.assertEqual(gabji.extract_final_yangdo_price(None), "협의")

    def test_empty(self):
        self.assertEqual(gabji.extract_final_yangdo_price(""), "협의")

    def test_negotiation(self):
        self.assertEqual(gabji.extract_final_yangdo_price("협의"), "협의")

    def test_arrow_range(self):
        self.assertEqual(gabji.extract_final_yangdo_price("1억→2억"), "2억")

    def test_no_parseable(self):
        # Plain text with no numbers keeps the raw value
        self.assertEqual(gabji.extract_final_yangdo_price("문의"), "문의")


# ===================================================================
# _normalize_header
# ===================================================================
class NormalizeHeaderTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(gabji._normalize_header("양도 가격"), "양도가격")

    def test_none(self):
        self.assertEqual(gabji._normalize_header(None), "")

    def test_uppercase(self):
        self.assertEqual(gabji._normalize_header("Hello World"), "helloworld")

    def test_whitespace(self):
        self.assertEqual(gabji._normalize_header("  a  b  c  "), "abc")


# ===================================================================
# _coerce_yangdo_candidate
# ===================================================================
class CoerceYangdoCandidateTest(unittest.TestCase):
    def test_price(self):
        self.assertEqual(gabji._coerce_yangdo_candidate("2.5억"), "2.5억")

    def test_negotiation(self):
        self.assertEqual(gabji._coerce_yangdo_candidate("협의"), "협의")

    def test_empty(self):
        self.assertEqual(gabji._coerce_yangdo_candidate(""), "")

    def test_none(self):
        self.assertEqual(gabji._coerce_yangdo_candidate(None), "")

    def test_range(self):
        # Range "2억~3억" → extract_final takes last → "3억"
        self.assertEqual(gabji._coerce_yangdo_candidate("2억~3억"), "3억")

    def test_negotiation_with_no_digits(self):
        self.assertEqual(gabji._coerce_yangdo_candidate("가격 협의 중"), "협의")


# ===================================================================
# _is_price_hint_text
# ===================================================================
class IsPriceHintTextTest(unittest.TestCase):
    def test_yangdo_price(self):
        self.assertTrue(gabji._is_price_hint_text("양도가"))

    def test_claim_price(self):
        self.assertTrue(gabji._is_price_hint_text("청구양도가"))

    def test_range(self):
        self.assertTrue(gabji._is_price_hint_text("가격범위"))

    def test_not_price(self):
        self.assertFalse(gabji._is_price_hint_text("업종"))

    def test_empty(self):
        self.assertFalse(gabji._is_price_hint_text(""))

    def test_none(self):
        self.assertFalse(gabji._is_price_hint_text(None))


# ===================================================================
# _has_numeric_price
# ===================================================================
class HasNumericPriceTest(unittest.TestCase):
    def test_numeric(self):
        self.assertTrue(gabji._has_numeric_price("2.5억"))

    def test_negotiation(self):
        self.assertFalse(gabji._has_numeric_price("협의"))

    def test_empty(self):
        self.assertFalse(gabji._has_numeric_price(""))

    def test_none(self):
        self.assertFalse(gabji._has_numeric_price(None))

    def test_with_units(self):
        self.assertTrue(gabji._has_numeric_price("3000만"))


# ===================================================================
# _to_eok
# ===================================================================
class ToEokTest(unittest.TestCase):
    def test_eok(self):
        self.assertAlmostEqual(gabji._to_eok("2.5억"), 2.5)

    def test_eok_man(self):
        self.assertAlmostEqual(gabji._to_eok("1억 5000만"), 1.5)

    def test_man(self):
        self.assertAlmostEqual(gabji._to_eok("5000만"), 0.5)

    def test_plain_large_number(self):
        # Number >= 1000 without unit → treat as 만 → / 10000
        self.assertAlmostEqual(gabji._to_eok("15000"), 1.5)

    def test_none(self):
        self.assertIsNone(gabji._to_eok(None))

    def test_dash(self):
        self.assertIsNone(gabji._to_eok("-"))

    def test_none_string(self):
        self.assertIsNone(gabji._to_eok("None"))

    def test_empty(self):
        self.assertIsNone(gabji._to_eok(""))

    def test_small_number(self):
        # Number < 1000 without unit → raw value
        self.assertAlmostEqual(gabji._to_eok("5"), 5.0)

    def test_comma_stripped(self):
        self.assertAlmostEqual(gabji._to_eok("1,500만"), 0.15)


# ===================================================================
# _format_eok
# ===================================================================
class FormatEokTest(unittest.TestCase):
    def test_whole(self):
        self.assertEqual(gabji._format_eok(2.0), "2억")

    def test_decimal(self):
        self.assertEqual(gabji._format_eok(2.50), "2.5억")

    def test_none(self):
        self.assertEqual(gabji._format_eok(None), "-")

    def test_zero(self):
        self.assertEqual(gabji._format_eok(0), "0억")

    def test_precise(self):
        self.assertEqual(gabji._format_eok(1.23), "1.23억")


# ===================================================================
# _format_capital
# ===================================================================
class FormatCapitalTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(gabji._format_capital(""), "-")

    def test_none(self):
        self.assertEqual(gabji._format_capital(None), "-")

    def test_with_unit(self):
        self.assertEqual(gabji._format_capital("3억"), "3억")

    def test_plain_number(self):
        self.assertEqual(gabji._format_capital("4.6"), "4.6억")

    def test_already_formatted(self):
        self.assertEqual(gabji._format_capital("5,000만원"), "5,000만원")

    def test_non_numeric(self):
        self.assertEqual(gabji._format_capital("미입력"), "미입력")


# ===================================================================
# _format_balance
# ===================================================================
class FormatBalanceTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(gabji._format_balance(""), "-")

    def test_none(self):
        self.assertEqual(gabji._format_balance(None), "-")

    def test_with_unit(self):
        self.assertEqual(gabji._format_balance("5,000만원"), "5,000만원")

    def test_integer(self):
        self.assertEqual(gabji._format_balance("5500"), "5,500만원")

    def test_decimal(self):
        self.assertEqual(gabji._format_balance("5500.5"), "5500.5만원")

    def test_comma_number(self):
        self.assertEqual(gabji._format_balance("5,500"), "5,500만원")

    def test_non_numeric(self):
        self.assertEqual(gabji._format_balance("없음"), "없음")


# ===================================================================
# _format_founded_year
# ===================================================================
class FormatFoundedYearTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(gabji._format_founded_year(""), "-")

    def test_none(self):
        self.assertEqual(gabji._format_founded_year(None), "-")

    def test_year_number(self):
        self.assertEqual(gabji._format_founded_year("2020"), "2020년")

    def test_already_formatted(self):
        self.assertEqual(gabji._format_founded_year("2020년"), "2020년")

    def test_non_year(self):
        self.assertEqual(gabji._format_founded_year("unknown"), "unknown")


# ===================================================================
# _parse_percent_value
# ===================================================================
class ParsePercentValueTest(unittest.TestCase):
    def test_simple(self):
        self.assertAlmostEqual(gabji._parse_percent_value("50%"), 50.0)

    def test_without_symbol(self):
        self.assertAlmostEqual(gabji._parse_percent_value("75"), 75.0)

    def test_with_keyword(self):
        self.assertAlmostEqual(
            gabji._parse_percent_value("부채비율 17.5%", keyword="부채비율"), 17.5
        )

    def test_negative(self):
        self.assertAlmostEqual(gabji._parse_percent_value("-3.2%"), -3.2)

    def test_comma(self):
        self.assertAlmostEqual(gabji._parse_percent_value("1,234%"), 1234.0)

    def test_empty(self):
        self.assertIsNone(gabji._parse_percent_value(""))

    def test_none(self):
        self.assertIsNone(gabji._parse_percent_value(None))

    def test_no_match(self):
        self.assertIsNone(gabji._parse_percent_value("없음"))

    def test_keyword_not_found(self):
        self.assertIsNone(gabji._parse_percent_value("부채 50%", keyword="유동비율"))


# ===================================================================
# _format_license_name
# ===================================================================
class FormatLicenseNameTest(unittest.TestCase):
    def test_already_complete(self):
        self.assertEqual(gabji._format_license_name("전기공사업"), "전기공사업")

    def test_ends_with_gong(self):
        self.assertEqual(gabji._format_license_name("전기공"), "전기공사업")

    def test_plain_name(self):
        self.assertEqual(gabji._format_license_name("건축"), "건축공사업")

    def test_empty(self):
        self.assertEqual(gabji._format_license_name(""), "")

    def test_none(self):
        self.assertEqual(gabji._format_license_name(None), "")

    def test_ends_with_saup(self):
        self.assertEqual(gabji._format_license_name("소방시설공사업"), "소방시설공사업")

    def test_other_saup(self):
        # Ends with "사업" but not "공사업"
        self.assertEqual(gabji._format_license_name("가스사업"), "가스사업")


if __name__ == "__main__":
    unittest.main()
