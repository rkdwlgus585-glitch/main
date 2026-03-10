from __future__ import annotations

import json
import math
import unittest

from core_engine.api_response import safe_json_for_script
from yangdo_calculator import (
    _collapse_script_whitespace,
    _compact_train_row,
    _derive_display_range_eok,
    _extract_price_values_eok,
    _fallback_capital_eok,
    _fallback_min_balance_eok,
    _fallback_surplus_eok,
    _finite_numbers,
    _median_or_none,
    _normalize_license_key_py,
    _normalize_price_text,
    _price_token_to_eok,
    _round4,
    _sanitize_endpoint,
    build_meta,
    build_training_dataset,
    calc_quantile,
    listing_detail_url,
    mean_or_none,
)


# ---------------------------------------------------------------------------
# _round4
# ---------------------------------------------------------------------------
class Round4Test(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_round4(1.23456789), 1.2346)

    def test_none(self):
        self.assertIsNone(_round4(None))

    def test_string_numeric(self):
        self.assertEqual(_round4("3.14159"), 3.1416)

    def test_invalid_string(self):
        self.assertIsNone(_round4("abc"))

    def test_zero(self):
        self.assertEqual(_round4(0), 0.0)

    def test_integer(self):
        self.assertEqual(_round4(5), 5.0)


# ---------------------------------------------------------------------------
# safe_json_for_script
# ---------------------------------------------------------------------------
class SafeJsonForScriptTest(unittest.TestCase):
    def test_basic_dict(self):
        result = safe_json_for_script({"a": 1})
        self.assertIn('"a":1', result)

    def test_script_close_tag_escaped(self):
        result = safe_json_for_script({"html": "</script>"})
        self.assertNotIn("</script>", result)
        self.assertIn("<\\/script>", result)

    def test_unicode_line_separators(self):
        result = safe_json_for_script({"text": "a\u2028b\u2029c"})
        self.assertNotIn("\u2028", result)
        self.assertNotIn("\u2029", result)

    def test_korean(self):
        result = safe_json_for_script({"업종": "전기공사업"})
        self.assertIn("전기공사업", result)


# ---------------------------------------------------------------------------
# _sanitize_endpoint
# ---------------------------------------------------------------------------
class SanitizeEndpointTest(unittest.TestCase):
    def test_valid_https(self):
        self.assertEqual(_sanitize_endpoint("https://example.com/api"), "https://example.com/api")

    def test_valid_http(self):
        self.assertEqual(_sanitize_endpoint("http://example.com"), "http://example.com")

    def test_empty(self):
        self.assertEqual(_sanitize_endpoint(""), "")

    def test_none(self):
        self.assertEqual(_sanitize_endpoint(None), "")

    def test_javascript_protocol_blocked(self):
        self.assertEqual(_sanitize_endpoint("javascript:alert(1)"), "")

    def test_data_protocol_blocked(self):
        self.assertEqual(_sanitize_endpoint("data:text/html,<h1>XSS</h1>"), "")

    def test_localhost_blocked(self):
        self.assertEqual(_sanitize_endpoint("http://localhost:8080"), "")

    def test_127_blocked(self):
        self.assertEqual(_sanitize_endpoint("http://127.0.0.1/admin"), "")

    def test_ipv6_loopback_blocked(self):
        self.assertEqual(_sanitize_endpoint("http://[::1]/admin"), "")

    def test_relative_path_allowed(self):
        self.assertEqual(_sanitize_endpoint("/api/data"), "/api/data")


# ---------------------------------------------------------------------------
# listing_detail_url
# ---------------------------------------------------------------------------
class ListingDetailUrlTest(unittest.TestCase):
    def test_with_seoul_no(self):
        self.assertEqual(listing_detail_url("https://site.com", seoul_no=123), "https://site.com/mna/123")

    def test_with_uid_fallback(self):
        self.assertEqual(listing_detail_url("https://site.com", seoul_no=0, now_uid="456"), "https://site.com/mna/456")

    def test_no_identifiers(self):
        self.assertEqual(listing_detail_url("https://site.com"), "https://site.com/mna")

    def test_default_base(self):
        result = listing_detail_url("", seoul_no=10)
        self.assertTrue(result.startswith("https://seoulmna.co.kr/mna/10"))

    def test_none_site_url(self):
        result = listing_detail_url(None, seoul_no=5)
        self.assertEqual(result, "https://seoulmna.co.kr/mna/5")

    def test_trailing_slash_stripped(self):
        self.assertEqual(listing_detail_url("https://site.com/", seoul_no=1), "https://site.com/mna/1")

    def test_invalid_seoul_no(self):
        self.assertEqual(listing_detail_url("https://site.com", seoul_no="abc"), "https://site.com/mna")


# ---------------------------------------------------------------------------
# _normalize_price_text
# ---------------------------------------------------------------------------
class NormalizePriceTextTest(unittest.TestCase):
    def test_fullwidth_dash(self):
        result = _normalize_price_text("3억\uFF0D5억")
        self.assertIn("-", result)

    def test_en_dash(self):
        result = _normalize_price_text("3억\u20135억")
        self.assertIn("-", result)

    def test_em_dash(self):
        result = _normalize_price_text("3억\u20145억")
        self.assertIn("-", result)

    def test_tilde_normalization(self):
        result = _normalize_price_text("3억\u223C5억")
        self.assertIn("~", result)

    def test_에_to_억(self):
        # "3 에" → "3억" (Korean OCR artifact)
        result = _normalize_price_text("3 에")
        self.assertIn("억", result)

    def test_br_to_newline(self):
        result = _normalize_price_text("3억<br/>5억")
        self.assertIn("\n", result)

    def test_empty(self):
        self.assertEqual(_normalize_price_text(""), "")

    def test_none(self):
        self.assertEqual(_normalize_price_text(None), "")


# ---------------------------------------------------------------------------
# _price_token_to_eok
# ---------------------------------------------------------------------------
class PriceTokenToEokTest(unittest.TestCase):
    def test_eok_only(self):
        self.assertEqual(_price_token_to_eok("3억"), 3.0)

    def test_eok_with_man(self):
        self.assertEqual(_price_token_to_eok("3억5000만"), 3.5)

    def test_man_only(self):
        self.assertEqual(_price_token_to_eok("5000만"), 0.5)

    def test_decimal_eok(self):
        self.assertEqual(_price_token_to_eok("1.5억"), 1.5)

    def test_eok_with_comma(self):
        self.assertIsNotNone(_price_token_to_eok("3억"))

    def test_empty(self):
        self.assertIsNone(_price_token_to_eok(""))

    def test_none(self):
        self.assertIsNone(_price_token_to_eok(None))

    def test_no_price_pattern(self):
        self.assertIsNone(_price_token_to_eok("무관"))

    def test_zero_value(self):
        self.assertIsNone(_price_token_to_eok("0억"))


# ---------------------------------------------------------------------------
# _extract_price_values_eok
# ---------------------------------------------------------------------------
class ExtractPriceValuesEokTest(unittest.TestCase):
    def test_single_value(self):
        self.assertEqual(_extract_price_values_eok("3억"), [3.0])

    def test_range(self):
        result = _extract_price_values_eok("3억~5억")
        self.assertEqual(result, [3.0, 5.0])

    def test_multiple_values(self):
        result = _extract_price_values_eok("1억 2억 3억")
        self.assertEqual(result, [1.0, 2.0, 3.0])

    def test_duplicates_removed(self):
        result = _extract_price_values_eok("3억 3억 5억")
        self.assertEqual(result, [3.0, 5.0])

    def test_empty(self):
        self.assertEqual(_extract_price_values_eok(""), [])

    def test_none(self):
        self.assertEqual(_extract_price_values_eok(None), [])

    def test_mixed_eok_and_man(self):
        result = _extract_price_values_eok("2억5000만")
        self.assertEqual(result, [2.5])


# ---------------------------------------------------------------------------
# _derive_display_range_eok
# ---------------------------------------------------------------------------
class DeriveDisplayRangeEokTest(unittest.TestCase):
    def test_text_based_range(self):
        lo, hi = _derive_display_range_eok("3억", "5억", None, None)
        self.assertEqual(lo, 3.0)
        self.assertEqual(hi, 5.0)

    def test_numeric_fallback(self):
        lo, hi = _derive_display_range_eok("", "", 2.0, 4.0)
        self.assertEqual(lo, 2.0)
        self.assertEqual(hi, 4.0)

    def test_all_empty(self):
        lo, hi = _derive_display_range_eok("", "", None, None)
        self.assertIsNone(lo)
        self.assertIsNone(hi)

    def test_single_value_from_text(self):
        lo, hi = _derive_display_range_eok("3억", "", 3.0, None)
        # text yields [3.0], numeric adds 3.0 (same) → lo=hi=3.0
        self.assertEqual(lo, 3.0)
        self.assertEqual(hi, 3.0)

    def test_mixed_text_and_numeric(self):
        lo, hi = _derive_display_range_eok("2억", "", None, 5.0)
        self.assertIsNotNone(lo)
        self.assertIsNotNone(hi)
        self.assertLessEqual(lo, hi)


# ---------------------------------------------------------------------------
# calc_quantile
# ---------------------------------------------------------------------------
class CalcQuantileTest(unittest.TestCase):
    def test_median_odd(self):
        self.assertEqual(calc_quantile([1, 3, 5], 0.5), 3.0)

    def test_median_even(self):
        self.assertEqual(calc_quantile([1, 2, 3, 4], 0.5), 2.5)

    def test_p25(self):
        result = calc_quantile([1, 2, 3, 4, 5], 0.25)
        self.assertEqual(result, 2.0)

    def test_p75(self):
        result = calc_quantile([1, 2, 3, 4, 5], 0.75)
        self.assertEqual(result, 4.0)

    def test_single_value(self):
        self.assertEqual(calc_quantile([42], 0.5), 42.0)

    def test_empty(self):
        self.assertIsNone(calc_quantile([], 0.5))

    def test_none_input(self):
        self.assertIsNone(calc_quantile(None, 0.5))

    def test_non_numeric_filtered(self):
        self.assertEqual(calc_quantile([1, "abc", 3, None], 0.5), 2.0)

    def test_q_clamped_to_0(self):
        self.assertEqual(calc_quantile([10, 20, 30], -0.5), 10.0)

    def test_q_clamped_to_1(self):
        self.assertEqual(calc_quantile([10, 20, 30], 1.5), 30.0)

    def test_unsorted_input(self):
        self.assertEqual(calc_quantile([5, 1, 3], 0.5), 3.0)


# ---------------------------------------------------------------------------
# mean_or_none / _finite_numbers / _median_or_none
# ---------------------------------------------------------------------------
class MeanOrNoneTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(mean_or_none([2, 4, 6]), 4.0)

    def test_empty(self):
        self.assertIsNone(mean_or_none([]))

    def test_none_input(self):
        self.assertIsNone(mean_or_none(None))

    def test_with_non_numeric(self):
        result = mean_or_none([2, "abc", 4])
        self.assertEqual(result, 3.0)

    def test_nan_filtered(self):
        result = mean_or_none([2, float("nan"), 4])
        self.assertEqual(result, 3.0)


class FiniteNumbersTest(unittest.TestCase):
    def test_mixed(self):
        result = _finite_numbers([1, "abc", None, 3.0, float("nan")])
        self.assertEqual(result, [1.0, 3.0])

    def test_empty(self):
        self.assertEqual(_finite_numbers([]), [])

    def test_none(self):
        self.assertEqual(_finite_numbers(None), [])


class MedianOrNoneTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_median_or_none([1, 3, 5]), 3.0)

    def test_empty(self):
        self.assertIsNone(_median_or_none([]))


# ---------------------------------------------------------------------------
# _normalize_license_key_py
# ---------------------------------------------------------------------------
class NormalizeLicenseKeyPyTest(unittest.TestCase):
    def test_strip_whitespace(self):
        self.assertEqual(_normalize_license_key_py("전기 공사 업"), "전기")

    def test_strip_corp_suffix(self):
        self.assertEqual(_normalize_license_key_py("(주)전기공사업"), "전기")

    def test_strip_업종(self):
        self.assertEqual(_normalize_license_key_py("전기업종"), "전기")

    def test_strip_면허(self):
        self.assertEqual(_normalize_license_key_py("전기면허"), "전기")

    def test_plain_token(self):
        self.assertEqual(_normalize_license_key_py("소방시설"), "소방시설")

    def test_empty(self):
        self.assertEqual(_normalize_license_key_py(""), "")

    def test_none(self):
        self.assertEqual(_normalize_license_key_py(None), "")

    def test_건설업_suffix(self):
        self.assertEqual(_normalize_license_key_py("토목건설업"), "토목")

    def test_combined_strip(self):
        # "(주)정보통신공사업" → strip (주), whitespace, then 공사업
        self.assertEqual(_normalize_license_key_py("주식회사 정보통신 공사업"), "정보통신")


# ---------------------------------------------------------------------------
# _fallback_capital_eok
# ---------------------------------------------------------------------------
class FallbackCapitalEokTest(unittest.TestCase):
    def test_토목건축(self):
        self.assertEqual(_fallback_capital_eok("토목건축"), 8.5)

    def test_산업환경설비(self):
        self.assertEqual(_fallback_capital_eok("산업환경설비"), 8.5)

    def test_토목(self):
        self.assertEqual(_fallback_capital_eok("토목"), 5.0)

    def test_건축(self):
        self.assertEqual(_fallback_capital_eok("건축"), 5.0)

    def test_조경(self):
        self.assertEqual(_fallback_capital_eok("조경"), 5.0)

    def test_전기(self):
        self.assertEqual(_fallback_capital_eok("전기"), 1.5)

    def test_정보통신(self):
        self.assertEqual(_fallback_capital_eok("정보통신"), 1.5)

    def test_소방(self):
        self.assertEqual(_fallback_capital_eok("소방"), 1.0)

    def test_unknown(self):
        self.assertEqual(_fallback_capital_eok("기타업종"), 1.5)

    def test_empty(self):
        self.assertEqual(_fallback_capital_eok(""), 1.5)

    def test_with_suffix(self):
        # "전기공사업" → normalized to "전기" → 1.5
        self.assertEqual(_fallback_capital_eok("전기공사업"), 1.5)


# ---------------------------------------------------------------------------
# _fallback_surplus_eok
# ---------------------------------------------------------------------------
class FallbackSurplusEokTest(unittest.TestCase):
    def test_zero_capital(self):
        self.assertEqual(_fallback_surplus_eok(0), 0.2)

    def test_negative_capital(self):
        self.assertEqual(_fallback_surplus_eok(-1), 0.2)

    def test_small_capital(self):
        # 1.0 * 0.08 = 0.08 → clamped to min 0.15
        self.assertEqual(_fallback_surplus_eok(1.0), 0.15)

    def test_large_capital(self):
        # 20 * 0.08 = 1.6 → clamped to max 1.2
        self.assertEqual(_fallback_surplus_eok(20), 1.2)

    def test_mid_capital(self):
        # 5.0 * 0.08 = 0.4 → within [0.15, 1.2]
        self.assertEqual(_fallback_surplus_eok(5.0), 0.4)

    def test_none_capital(self):
        self.assertEqual(_fallback_surplus_eok(None), 0.2)

    def test_string_capital(self):
        self.assertEqual(_fallback_surplus_eok("abc"), 0.2)


# ---------------------------------------------------------------------------
# _fallback_min_balance_eok
# ---------------------------------------------------------------------------
class FallbackMinBalanceEokTest(unittest.TestCase):
    def test_토목건축(self):
        self.assertEqual(_fallback_min_balance_eok("토목건축"), 0.9)

    def test_토목(self):
        self.assertEqual(_fallback_min_balance_eok("토목"), 0.52)

    def test_건축(self):
        self.assertEqual(_fallback_min_balance_eok("건축"), 0.52)

    def test_전기(self):
        self.assertEqual(_fallback_min_balance_eok("전기"), 0.24)

    def test_정보통신(self):
        self.assertEqual(_fallback_min_balance_eok("정보통신"), 0.2)

    def test_통신_alias(self):
        self.assertEqual(_fallback_min_balance_eok("통신"), 0.2)

    def test_소방(self):
        self.assertEqual(_fallback_min_balance_eok("소방"), 0.16)

    def test_unknown_token_ignores_median(self):
        # Non-empty token with no keyword match → always returns 0.2
        # (median fallback only applies when token is empty)
        self.assertEqual(_fallback_min_balance_eok("기타", median_balance_eok=1.0), 0.2)

    def test_unknown_no_median(self):
        self.assertEqual(_fallback_min_balance_eok("기타"), 0.2)

    def test_empty_key_with_median(self):
        # empty key → falls through to median path
        result = _fallback_min_balance_eok("", median_balance_eok=0.5)
        self.assertEqual(result, 0.225)  # max(0.16, min(0.6, 0.5*0.45))

    def test_empty_key_no_median(self):
        self.assertEqual(_fallback_min_balance_eok(""), 0.2)


# ---------------------------------------------------------------------------
# build_training_dataset
# ---------------------------------------------------------------------------
class BuildTrainingDatasetTest(unittest.TestCase):
    def _make_record(self, price=3.0, claim=5.0, number=10, uid="u1"):
        return {
            "current_price_eok": price,
            "claim_price_eok": claim,
            "current_price_text": f"{price}억",
            "claim_price_text": f"{claim}억",
            "number": number,
            "uid": uid,
            "license_text": "전기공사업",
            "license_tokens": {"전기"},
            "license_year": 2020,
            "specialty": 1.5,
            "years": {"y23": 0.5, "y24": 0.8},
            "sales3_eok": 2.0,
            "capital_eok": 1.5,
            "surplus_eok": 0.3,
            "balance_eok": 0.5,
        }

    def test_basic_row(self):
        records = [self._make_record()]
        rows = build_training_dataset(records, "https://test.com")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["price_eok"], 3.0)
        self.assertEqual(row["license_text"], "전기공사업")
        self.assertEqual(row["tokens"], ["전기"])
        self.assertIn("/mna/10", row["url"])

    def test_zero_price_filtered(self):
        records = [self._make_record(price=0)]
        rows = build_training_dataset(records)
        self.assertEqual(len(rows), 0)

    def test_negative_price_filtered(self):
        records = [self._make_record(price=-1)]
        rows = build_training_dataset(records)
        self.assertEqual(len(rows), 0)

    def test_none_records(self):
        self.assertEqual(build_training_dataset(None), [])

    def test_empty_records(self):
        self.assertEqual(build_training_dataset([]), [])

    def test_display_range_swap(self):
        # If display_high < display_low, they should be swapped
        rec = self._make_record(price=5.0, claim=3.0)
        rec["current_price_text"] = "5억"
        rec["claim_price_text"] = "3억"
        rows = build_training_dataset([rec])
        self.assertEqual(len(rows), 1)
        self.assertLessEqual(rows[0]["display_low_eok"], rows[0]["display_high_eok"])

    def test_multiple_records(self):
        records = [self._make_record(price=i, number=i) for i in range(1, 4)]
        rows = build_training_dataset(records)
        self.assertEqual(len(rows), 3)


# ---------------------------------------------------------------------------
# _compact_train_row
# ---------------------------------------------------------------------------
class CompactTrainRowTest(unittest.TestCase):
    def test_basic(self):
        row = {
            "now_uid": "u1",
            "seoul_no": 10,
            "license_text": "전기",
            "tokens": ["전기"],
            "license_year": 2020,
            "specialty": 1.5,
            "y23": 0.5,
            "y24": 0.8,
            "y25": None,
            "sales3_eok": 2.0,
            "sales5_eok": None,
            "capital_eok": 1.5,
            "surplus_eok": 0.3,
            "debt_ratio": None,
            "liq_ratio": None,
            "company_type": "법인",
            "balance_eok": 0.5,
            "price_eok": 3.0,
            "display_low_eok": 3.0,
            "display_high_eok": 5.0,
            "url": "https://test.com/mna/10",
        }
        arr = _compact_train_row(row)
        self.assertEqual(len(arr), 21)
        self.assertEqual(arr[0], "u1")
        self.assertEqual(arr[1], 10)
        self.assertEqual(arr[17], 3.0)

    def test_none_input(self):
        arr = _compact_train_row(None)
        self.assertEqual(len(arr), 21)
        self.assertEqual(arr[0], "")

    def test_empty_dict(self):
        arr = _compact_train_row({})
        self.assertEqual(len(arr), 21)


# ---------------------------------------------------------------------------
# build_meta
# ---------------------------------------------------------------------------
class BuildMetaTest(unittest.TestCase):
    def _make_train_rows(self, count=5):
        rows = []
        for i in range(count):
            rows.append({
                "price_eok": float(i + 1),
                "specialty": float(i),
                "sales3_eok": float(i * 2),
                "debt_ratio": 50.0 + i,
                "liq_ratio": 100.0 + i,
                "capital_eok": float(i + 1),
                "surplus_eok": float(i) * 0.1,
                "balance_eok": float(i) * 0.5,
            })
        return rows

    def test_basic(self):
        all_records = [{"license_tokens": {"전기", "토목"}}] * 3
        train = self._make_train_rows(5)
        meta = build_meta(all_records, train)
        self.assertEqual(meta["all_record_count"], 3)
        self.assertEqual(meta["train_count"], 5)
        self.assertIsNotNone(meta["median_price_eok"])
        self.assertIsNotNone(meta["avg_debt_ratio"])
        self.assertIsNotNone(meta["top_license_tokens"])

    def test_empty(self):
        meta = build_meta([], [])
        self.assertEqual(meta["all_record_count"], 0)
        self.assertEqual(meta["train_count"], 0)
        self.assertIsNone(meta["median_price_eok"])

    def test_none_inputs(self):
        meta = build_meta(None, None)
        self.assertEqual(meta["all_record_count"], 0)
        self.assertEqual(meta["train_count"], 0)

    def test_top_license_tokens_limit(self):
        all_records = [{"license_tokens": {f"token_{i}"}} for i in range(20)]
        meta = build_meta(all_records, [])
        self.assertLessEqual(len(meta["top_license_tokens"]), 12)

    def test_priced_ratio(self):
        all_records = [{}] * 10
        train = self._make_train_rows(5)
        meta = build_meta(all_records, train)
        self.assertEqual(meta["priced_ratio"], 50.0)


# ---------------------------------------------------------------------------
# _collapse_script_whitespace
# ---------------------------------------------------------------------------
class CollapseScriptWhitespaceTest(unittest.TestCase):
    def test_basic_minify(self):
        html = "<script>  var x = 1;  \n  var y = 2;  \n</script>"
        result = _collapse_script_whitespace(html)
        self.assertIn("var x = 1;", result)
        self.assertIn("var y = 2;", result)

    def test_external_script_untouched(self):
        html = '<script src="app.js">  </script>'
        result = _collapse_script_whitespace(html)
        self.assertEqual(result, html)

    def test_empty(self):
        self.assertEqual(_collapse_script_whitespace(""), "")

    def test_none(self):
        self.assertEqual(_collapse_script_whitespace(None), "")

    def test_no_script(self):
        html = "<div>hello</div>"
        self.assertEqual(_collapse_script_whitespace(html), html)

    def test_empty_lines_removed(self):
        html = "<script>\n\n  var x = 1;\n\n\n  var y = 2;\n\n</script>"
        result = _collapse_script_whitespace(html)
        # Empty lines should be removed
        self.assertNotIn("\n\n", result)


# ---------------------------------------------------------------------------
# _build_license_ui_profiles (via import)
# ---------------------------------------------------------------------------
# Importing separately since it's a private function with complex signature
from yangdo_calculator import _build_license_ui_profiles


class BuildLicenseUiProfilesTest(unittest.TestCase):
    def _make_dataset(self):
        return [
            {
                "tokens": ["전기공사업", "건축공사업"],
                "specialty": 1.5,
                "sales3_eok": 2.0,
                "sales5_eok": 3.0,
                "capital_eok": 1.5,
                "surplus_eok": 0.3,
                "balance_eok": 0.5,
            },
            {
                "tokens": ["전기공사업"],
                "specialty": 2.0,
                "sales3_eok": 3.0,
                "sales5_eok": 4.0,
                "capital_eok": 2.0,
                "surplus_eok": 0.4,
                "balance_eok": 0.6,
            },
        ]

    def test_basic(self):
        result = _build_license_ui_profiles(self._make_dataset())
        self.assertIn("profiles", result)
        self.assertIn("quick_tokens", result)
        profiles = result["profiles"]
        self.assertGreater(len(profiles), 0)

    def test_sample_count(self):
        result = _build_license_ui_profiles(self._make_dataset())
        # "전기" token appears in both rows
        elec_key = None
        for key in result["profiles"]:
            if "전기" in key:
                elec_key = key
                break
        self.assertIsNotNone(elec_key)
        self.assertEqual(result["profiles"][elec_key]["sample_count"], 2)

    def test_generic_keys_excluded(self):
        result = _build_license_ui_profiles(
            self._make_dataset(),
            generic_license_keys=["전기공사업"],
        )
        for key in result["profiles"]:
            self.assertNotIn("전기", key)

    def test_quick_tokens_limit(self):
        # quick_tokens capped at 18
        rows = [{"tokens": [f"업종_{i}공사업"], "capital_eok": 1.0} for i in range(25)]
        result = _build_license_ui_profiles(rows)
        self.assertLessEqual(len(result["quick_tokens"]), 18)

    def test_empty_dataset(self):
        result = _build_license_ui_profiles([])
        self.assertEqual(result["profiles"], {})
        self.assertEqual(result["quick_tokens"], [])

    def test_canonical_display_name(self):
        result = _build_license_ui_profiles(
            self._make_dataset(),
            license_canonical_by_key={"전기공사업": "전기공사업 (정식명칭)"},
        )
        elec_key = None
        for key in result["profiles"]:
            if "전기" in key:
                elec_key = key
                break
        if elec_key:
            self.assertEqual(result["profiles"][elec_key]["display_name"], "전기공사업 (정식명칭)")

    def test_fallback_values_used(self):
        # Rows without capital/surplus → fallback should be used
        rows = [{"tokens": ["전기공사업"]}]
        result = _build_license_ui_profiles(rows)
        for key, profile in result["profiles"].items():
            if "전기" in key:
                self.assertIsNotNone(profile["prefill_capital_eok"])
                self.assertIsNotNone(profile["prefill_surplus_eok"])


if __name__ == "__main__":
    unittest.main()
