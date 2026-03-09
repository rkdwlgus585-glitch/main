"""Unit tests for match.py pure functions (ConsultantAI methods)."""

import json
import sys
import types as _types
import unittest

# ---------------------------------------------------------------------------
# Lightweight stubs so we can import match.py without google-genai / gspread
# ---------------------------------------------------------------------------
_fake_genai = _types.ModuleType("google.genai")
_fake_genai.types = _types.ModuleType("google.genai.types")

_fake_google = _types.ModuleType("google")
_fake_google.genai = _fake_genai

sys.modules.setdefault("google", _fake_google)
sys.modules.setdefault("google.genai", _fake_genai)
sys.modules.setdefault("google.genai.types", _fake_genai.types)
sys.modules.setdefault("gspread", _types.ModuleType("gspread"))
_fake_oauth = _types.ModuleType("oauth2client")
_fake_sac = _types.ModuleType("oauth2client.service_account")

class _FakeCredentials:
    @classmethod
    def from_json_keyfile_name(cls, *a, **kw):
        return cls()

_fake_sac.ServiceAccountCredentials = _FakeCredentials
_fake_oauth.service_account = _fake_sac
sys.modules.setdefault("oauth2client", _fake_oauth)
sys.modules.setdefault("oauth2client.service_account", _fake_sac)

from match import ConsultantAI  # noqa: E402

# ---------------------------------------------------------------------------
# Helper: build a minimal ConsultantAI without API key
# ---------------------------------------------------------------------------

def _make_ai():
    """Create a ConsultantAI instance with a stubbed genai client."""
    ai = object.__new__(ConsultantAI)
    ai.credit_map = {
        'AAA': 30, 'AA+': 29, 'AA': 28, 'AA-': 27,
        'A+': 26, 'A': 25, 'A-': 24,
        'BBB+': 23, 'BBB': 22, 'BBB-': 21,
        'BB+': 20, 'BB': 19, 'BB-': 18,
        'B+': 17, 'B': 16, 'B-': 15,
        'CCC+': 14, 'CCC': 13, 'CCC-': 12,
        'CC': 11, 'C': 10, 'D': 0,
    }
    ai.client = None
    return ai


# ===================================================================
# _score_credit
# ===================================================================
class ScoreCreditTest(unittest.TestCase):
    def setUp(self):
        self.ai = _make_ai()

    def test_exact_grade(self):
        self.assertEqual(self.ai._score_credit("AAA"), 30)

    def test_grade_with_modifier(self):
        self.assertEqual(self.ai._score_credit("BB+"), 20)

    def test_grade_minus(self):
        self.assertEqual(self.ai._score_credit("A-"), 24)

    def test_grade_embedded_in_text(self):
        self.assertEqual(self.ai._score_credit("등급: BBB 양호"), 22)

    def test_grade_d(self):
        self.assertEqual(self.ai._score_credit("D"), 0)

    def test_empty_string(self):
        self.assertEqual(self.ai._score_credit(""), -99)

    def test_none(self):
        self.assertEqual(self.ai._score_credit(None), -99)

    def test_no_grade_found(self):
        self.assertEqual(self.ai._score_credit("양호한 상태"), -99)

    def test_lowercase_grade(self):
        # .upper() is applied, so lowercase should work
        self.assertEqual(self.ai._score_credit("bbb+"), 23)


# ===================================================================
# _get_cell
# ===================================================================
class GetCellTest(unittest.TestCase):
    def setUp(self):
        self.ai = _make_ai()

    def test_valid_index(self):
        self.assertEqual(self.ai._get_cell(["a", "b", "c"], 1), "b")

    def test_negative_index(self):
        self.assertEqual(self.ai._get_cell(["a", "b"], -1, "X"), "X")

    def test_out_of_range(self):
        self.assertEqual(self.ai._get_cell(["a"], 5, "default"), "default")

    def test_default_empty(self):
        self.assertEqual(self.ai._get_cell([], 0), "")

    def test_zero_index(self):
        self.assertEqual(self.ai._get_cell(["first"], 0), "first")


# ===================================================================
# _to_optional_float
# ===================================================================
class ToOptionalFloatTest(unittest.TestCase):
    def setUp(self):
        self.ai = _make_ai()

    def test_none(self):
        self.assertIsNone(self.ai._to_optional_float(None))

    def test_int_value(self):
        self.assertEqual(self.ai._to_optional_float(5), 5.0)

    def test_float_value(self):
        self.assertEqual(self.ai._to_optional_float(3.14), 3.14)

    def test_numeric_string(self):
        self.assertEqual(self.ai._to_optional_float("2.5"), 2.5)

    def test_empty_string(self):
        self.assertIsNone(self.ai._to_optional_float(""))

    def test_null_string(self):
        self.assertIsNone(self.ai._to_optional_float("null"))

    def test_none_string(self):
        self.assertIsNone(self.ai._to_optional_float("none"))

    def test_whitespace(self):
        self.assertIsNone(self.ai._to_optional_float("  "))

    def test_invalid_string(self):
        self.assertIsNone(self.ai._to_optional_float("abc"))

    def test_negative_float(self):
        self.assertEqual(self.ai._to_optional_float("-1.5"), -1.5)


# ===================================================================
# _license_tokens
# ===================================================================
class LicenseTokensTest(unittest.TestCase):
    def setUp(self):
        self.ai = _make_ai()

    def test_none(self):
        self.assertEqual(self.ai._license_tokens(None), [])

    def test_single_token(self):
        self.assertEqual(self.ai._license_tokens("전기공사업"), ["전기공사업"])

    def test_comma_separated(self):
        tokens = self.ai._license_tokens("전기,토목,건축")
        self.assertEqual(tokens, ["전기", "토목", "건축"])

    def test_slash_separated(self):
        tokens = self.ai._license_tokens("전기/토목")
        self.assertEqual(tokens, ["전기", "토목"])

    def test_pipe_separated(self):
        tokens = self.ai._license_tokens("전기|토목")
        self.assertEqual(tokens, ["전기", "토목"])

    def test_dot_separator(self):
        tokens = self.ai._license_tokens("전기·토목")
        self.assertEqual(tokens, ["전기", "토목"])

    def test_list_input(self):
        tokens = self.ai._license_tokens(["전기", "토목", None])
        self.assertEqual(tokens, ["전기", "토목"])

    def test_short_tokens_filtered(self):
        # Single-char tokens are filtered out (len < 2)
        tokens = self.ai._license_tokens("A, 전기, B")
        self.assertEqual(tokens, ["전기"])

    def test_space_separated(self):
        tokens = self.ai._license_tokens("전기 토목")
        self.assertEqual(tokens, ["전기", "토목"])


# ===================================================================
# _parse_money
# ===================================================================
class ParseMoneyTest(unittest.TestCase):
    def setUp(self):
        self.ai = _make_ai()

    def test_empty(self):
        self.assertEqual(self.ai._parse_money(""), 0.0)

    def test_none(self):
        self.assertEqual(self.ai._parse_money(None), 0.0)

    def test_eok_unit(self):
        self.assertAlmostEqual(self.ai._parse_money("1.1억"), 1.1)

    def test_plain_eok(self):
        self.assertAlmostEqual(self.ai._parse_money("2억"), 2.0)

    def test_large_number_as_man(self):
        # 1800 → 0.18 (만원 단위)
        self.assertAlmostEqual(self.ai._parse_money("1800"), 0.18)

    def test_small_number_as_eok(self):
        # 12 → 12.0 (억 단위로 간주)
        self.assertAlmostEqual(self.ai._parse_money("12"), 12.0)

    def test_range_uses_last(self):
        # "2.5억-2.7억" → uses 2.7
        self.assertAlmostEqual(self.ai._parse_money("2.5억-2.7억"), 2.7)

    def test_range_tilde(self):
        self.assertAlmostEqual(self.ai._parse_money("1억~2억"), 2.0)

    def test_comma_removed(self):
        self.assertAlmostEqual(self.ai._parse_money("2,000"), 0.2)

    def test_invalid_string(self):
        self.assertEqual(self.ai._parse_money("협의"), 0.0)

    def test_zero(self):
        self.assertAlmostEqual(self.ai._parse_money("0"), 0.0)

    def test_boundary_100(self):
        # 100 → man unit → 0.01
        self.assertAlmostEqual(self.ai._parse_money("100"), 0.01)

    def test_just_under_100(self):
        # 99 → eok unit → 99.0
        self.assertAlmostEqual(self.ai._parse_money("99"), 99.0)

    def test_arrow_range(self):
        self.assertAlmostEqual(self.ai._parse_money("1억→2억"), 2.0)


# ===================================================================
# _is_numeric_price
# ===================================================================
class IsNumericPriceTest(unittest.TestCase):
    def setUp(self):
        self.ai = _make_ai()

    def test_empty(self):
        self.assertFalse(self.ai._is_numeric_price(""))

    def test_none(self):
        self.assertFalse(self.ai._is_numeric_price(None))

    def test_numeric(self):
        self.assertTrue(self.ai._is_numeric_price("1500"))

    def test_eok_format(self):
        self.assertTrue(self.ai._is_numeric_price("2.5억"))

    def test_hyeopui_only(self):
        self.assertFalse(self.ai._is_numeric_price("협의"))

    def test_hyeopui_with_number(self):
        # "1억 협의" has a digit → True
        self.assertTrue(self.ai._is_numeric_price("1억 협의"))


# ===================================================================
# _resolve_price_source
# ===================================================================
class ResolvePriceSourceTest(unittest.TestCase):
    def setUp(self):
        self.ai = _make_ai()

    def test_primary_numeric(self):
        row = [""] * 34
        row[18] = "2.5억"
        row[33] = "3억"
        result = self.ai._resolve_price_source(row, 18, 33)
        self.assertEqual(result, "2.5억")

    def test_primary_non_numeric_claim_numeric(self):
        row = [""] * 34
        row[18] = "협의"
        row[33] = "3억"
        result = self.ai._resolve_price_source(row, 18, 33)
        self.assertEqual(result, "3억")

    def test_both_non_numeric_primary_nonempty(self):
        row = [""] * 34
        row[18] = "협의"
        row[33] = ""
        result = self.ai._resolve_price_source(row, 18, 33)
        self.assertEqual(result, "협의")

    def test_both_empty(self):
        row = [""] * 34
        result = self.ai._resolve_price_source(row, 18, 33)
        self.assertEqual(result, "")


# ===================================================================
# find_matches (core matching logic)
# ===================================================================
class FindMatchesTest(unittest.TestCase):
    def setUp(self):
        self.ai = _make_ai()
        # Build minimal inventory rows
        # IDX_ID=0, IDX_LIC=2, IDX_CAP=4, IDX_PRICE=18, IDX_REMARK=31, IDX_CLAIM_PRICE=33
        self.row_template = [""] * 34

    def _make_row(self, row_id, lic, cap, price, remark="", claim_price=""):
        row = list(self.row_template)
        row[0] = row_id
        row[2] = lic
        row[4] = cap
        row[18] = price
        row[31] = remark
        row[33] = claim_price
        return row

    def test_empty_req(self):
        self.assertEqual(self.ai.find_matches(None, []), [])

    def test_invalid_req_type(self):
        self.assertEqual(self.ai.find_matches('"just a string"', []), [])

    def test_basic_license_match(self):
        inventory = [
            self._make_row("001", "전기공사업", "10억", "2.5억"),
            self._make_row("002", "토목공사업", "10억", "2.5억"),
        ]
        req = {"license": "전기"}
        matches = self.ai.find_matches(req, inventory)
        self.assertEqual(matches, ["001"])

    def test_price_range_filter(self):
        inventory = [
            self._make_row("001", "전기", "10", "1.5억"),
            self._make_row("002", "전기", "10", "5억"),
        ]
        req = {"license": "전기", "price_max": 3.0}
        matches = self.ai.find_matches(req, inventory)
        self.assertEqual(matches, ["001"])

    def test_cap_range_filter(self):
        inventory = [
            self._make_row("001", "전기", "2000", "2억"),
            self._make_row("002", "전기", "500", "2억"),
        ]
        req = {"license": "전기", "cap_min": 0.1}
        matches = self.ai.find_matches(req, inventory)
        # 2000 → 0.2, 500 → 0.05; min 0.1 → only 001
        self.assertEqual(matches, ["001"])

    def test_empty_req_dict(self):
        """Empty dict is falsy → early return []."""
        inventory = [
            self._make_row("001", "전기", "10", "2억"),
        ]
        req = {}
        matches = self.ai.find_matches(req, inventory)
        self.assertEqual(matches, [])

    def test_license_only_no_other_filter(self):
        """With only license filter, all matching rows returned."""
        inventory = [
            self._make_row("001", "전기", "10", "2억"),
            self._make_row("002", "토목", "10", "2억"),
            self._make_row("003", "전기", "5", "1억"),
        ]
        req = {"license": "전기"}
        matches = self.ai.find_matches(req, inventory)
        self.assertEqual(matches, ["001", "003"])

    def test_empty_row_id_skipped(self):
        inventory = [
            self._make_row("", "전기", "10", "2억"),
        ]
        req = {}
        self.assertEqual(self.ai.find_matches(req, inventory), [])

    def test_perf_3_max_filter_high_price(self):
        """When perf_3_max <= 1.5 and price > 3.0, row is excluded."""
        inventory = [
            self._make_row("001", "전기", "10", "4억"),
        ]
        req = {"license": "전기", "perf_3_max": 1.0}
        matches = self.ai.find_matches(req, inventory)
        self.assertEqual(matches, [])

    def test_credit_min_filter(self):
        inventory = [
            self._make_row("001", "전기", "10", "2억", remark="등급: BBB"),
            self._make_row("002", "전기", "10", "2억", remark="등급: CCC"),
        ]
        req = {"license": "전기", "credit_min": "BB"}
        matches = self.ai.find_matches(req, inventory)
        self.assertEqual(matches, ["001"])

    def test_json_string_req(self):
        inventory = [
            self._make_row("001", "전기", "10", "2억"),
        ]
        req_str = json.dumps({"license": "전기"})
        matches = self.ai.find_matches(req_str, inventory)
        self.assertEqual(matches, ["001"])

    def test_claim_price_fallback(self):
        """When primary price is '협의', claim price is used."""
        inventory = [
            self._make_row("001", "전기", "10", "협의", claim_price="2억"),
        ]
        req = {"license": "전기", "price_max": 3.0}
        matches = self.ai.find_matches(req, inventory)
        self.assertEqual(matches, ["001"])


if __name__ == "__main__":
    unittest.main()
