"""Unit tests for yangdo_blackbox_api.py pure functions.

Covers: statistics, normalization, sector identification, policy resolution,
settlement mode, JSON serialization, and data extraction functions.
"""

import unittest
from collections import namedtuple

import yangdo_blackbox_api as api


# ===================================================================
# _plain_quantile
# ===================================================================
class PlainQuantileTest(unittest.TestCase):
    def test_empty_returns_none(self):
        self.assertIsNone(api._plain_quantile([], 0.5))

    def test_single_value(self):
        self.assertEqual(api._plain_quantile([7.0], 0.5), 7.0)

    def test_median_odd(self):
        self.assertAlmostEqual(api._plain_quantile([1, 2, 3], 0.5), 2.0)

    def test_median_even(self):
        self.assertAlmostEqual(api._plain_quantile([1, 2, 3, 4], 0.5), 2.5)

    def test_q0(self):
        self.assertAlmostEqual(api._plain_quantile([10, 20, 30], 0.0), 10.0)

    def test_q1(self):
        self.assertAlmostEqual(api._plain_quantile([10, 20, 30], 1.0), 30.0)

    def test_q_clamped_below(self):
        self.assertAlmostEqual(api._plain_quantile([10, 20], -0.5), 10.0)

    def test_q_clamped_above(self):
        self.assertAlmostEqual(api._plain_quantile([10, 20], 2.0), 20.0)

    def test_interpolation_025(self):
        result = api._plain_quantile([1, 2, 3, 4, 5], 0.25)
        self.assertAlmostEqual(result, 2.0)

    def test_unsorted_input(self):
        self.assertAlmostEqual(api._plain_quantile([5, 1, 3], 0.5), 3.0)


# ===================================================================
# _trimmed_plain_median
# ===================================================================
class TrimmedPlainMedianTest(unittest.TestCase):
    def test_empty_returns_zero(self):
        self.assertEqual(api._trimmed_plain_median([]), 0.0)

    def test_single_value(self):
        self.assertEqual(api._trimmed_plain_median([5.0]), 5.0)

    def test_outliers_trimmed(self):
        vals = [1, 2, 3, 4, 5, 100]
        result_trimmed = api._trimmed_plain_median(vals)
        result_raw = api._plain_quantile(vals, 0.5)
        # Trimmed median should be closer to center of bulk
        self.assertLessEqual(result_trimmed, result_raw)

    def test_uniform_values(self):
        self.assertAlmostEqual(api._trimmed_plain_median([3, 3, 3, 3]), 3.0)


# ===================================================================
# _sector_signal_value
# ===================================================================
class SectorSignalValueTest(unittest.TestCase):
    def test_both_present(self):
        result = api._sector_signal_value({"sales3_eok": 10.0, "specialty": 20.0})
        self.assertAlmostEqual(result, 0.65 * 10.0 + 0.35 * 20.0)

    def test_only_sales3(self):
        result = api._sector_signal_value({"sales3_eok": 5.0})
        self.assertAlmostEqual(result, 5.0)

    def test_only_specialty(self):
        result = api._sector_signal_value({"specialty": 8.0})
        self.assertAlmostEqual(result, 8.0)

    def test_none_source(self):
        self.assertIsNone(api._sector_signal_value(None))

    def test_empty_dict(self):
        self.assertIsNone(api._sector_signal_value({}))

    def test_non_numeric_values(self):
        self.assertIsNone(api._sector_signal_value({"sales3_eok": "abc"}))


# ===================================================================
# _special_balance_sector_name
# ===================================================================
class SpecialBalanceSectorNameTest(unittest.TestCase):
    def test_electric(self):
        self.assertEqual(api._special_balance_sector_name("전기공사업"), "전기")

    def test_telecom_full(self):
        self.assertEqual(api._special_balance_sector_name("정보통신공사업"), "정보통신")

    def test_telecom_short(self):
        self.assertEqual(api._special_balance_sector_name("통신"), "정보통신")

    def test_fire(self):
        self.assertEqual(api._special_balance_sector_name("소방시설공사업"), "소방")

    def test_non_special(self):
        self.assertEqual(api._special_balance_sector_name("토목공사업"), "")

    def test_empty(self):
        self.assertEqual(api._special_balance_sector_name(""), "")

    def test_none(self):
        self.assertEqual(api._special_balance_sector_name(None), "")

    def test_dict_input(self):
        self.assertEqual(
            api._special_balance_sector_name({"license_text": "전기공사업"}),
            "전기",
        )

    def test_set_input(self):
        self.assertEqual(api._special_balance_sector_name({"전기"}), "전기")

    def test_priority_telecom_over_electric(self):
        # 정보통신 contains 통신 — when both 전기 and 통신 present, 정보통신 wins (checked first)
        self.assertEqual(api._special_balance_sector_name("정보통신 전기"), "정보통신")


# ===================================================================
# _is_special_license_text
# ===================================================================
class IsSpecialLicenseTextTest(unittest.TestCase):
    def test_special(self):
        self.assertTrue(api._is_special_license_text("전기"))

    def test_non_special(self):
        self.assertFalse(api._is_special_license_text("토목"))

    def test_empty(self):
        self.assertFalse(api._is_special_license_text(""))


# ===================================================================
# _normalize_reorg_mode
# ===================================================================
class NormalizeReorgModeTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(api._normalize_reorg_mode(""), "")

    def test_none(self):
        self.assertEqual(api._normalize_reorg_mode(None), "")

    def test_split(self):
        self.assertEqual(api._normalize_reorg_mode("분할"), "분할/합병")

    def test_merge(self):
        self.assertEqual(api._normalize_reorg_mode("합병"), "분할/합병")

    def test_split_english(self):
        self.assertEqual(api._normalize_reorg_mode("split"), "분할/합병")

    def test_comprehensive(self):
        self.assertEqual(api._normalize_reorg_mode("포괄양도"), "포괄")

    def test_absorption_conflict(self):
        # "흡수합병" contains both "합병" (split/merge) and "흡수" (comprehensive) → conflict → ""
        self.assertEqual(api._normalize_reorg_mode("흡수합병"), "")

    def test_conflict_returns_empty(self):
        # Both 분할 and 포괄 → ambiguous → empty
        self.assertEqual(api._normalize_reorg_mode("분할포괄"), "")

    def test_comprehensive_english(self):
        self.assertEqual(api._normalize_reorg_mode("comprehensive"), "포괄")

    def test_passthrough(self):
        result = api._normalize_reorg_mode("일반양도")
        self.assertEqual(result, "일반양도")


# ===================================================================
# _normalize_balance_usage_mode
# ===================================================================
class NormalizeBalanceUsageModeTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(api._normalize_balance_usage_mode(""), "")

    def test_auto(self):
        self.assertEqual(api._normalize_balance_usage_mode("auto"), "auto")

    def test_auto_korean(self):
        self.assertEqual(api._normalize_balance_usage_mode("자동"), "auto")

    def test_loan(self):
        self.assertEqual(api._normalize_balance_usage_mode("융자인출"), "loan_withdrawal")

    def test_loan_english(self):
        self.assertEqual(api._normalize_balance_usage_mode("loan"), "loan_withdrawal")

    def test_credit_transfer(self):
        self.assertEqual(api._normalize_balance_usage_mode("잔액승계"), "credit_transfer")

    def test_credit_offset(self):
        self.assertEqual(api._normalize_balance_usage_mode("1:1차감"), "credit_transfer")

    def test_none_mode(self):
        self.assertEqual(api._normalize_balance_usage_mode("없음"), "none")

    def test_none_english(self):
        self.assertEqual(api._normalize_balance_usage_mode("none"), "none")

    def test_unrecognized(self):
        self.assertEqual(api._normalize_balance_usage_mode("기타"), "")


# ===================================================================
# _normalize_credit_level
# ===================================================================
class NormalizeCreditLevelTest(unittest.TestCase):
    def test_high_korean(self):
        self.assertEqual(api._normalize_credit_level("우수"), "high")

    def test_high_grade(self):
        self.assertEqual(api._normalize_credit_level("AAA"), "high")

    def test_medium_korean(self):
        self.assertEqual(api._normalize_credit_level("보통"), "medium")

    def test_medium_grade(self):
        self.assertEqual(api._normalize_credit_level("BBB"), "medium")

    def test_low_korean(self):
        self.assertEqual(api._normalize_credit_level("낮음"), "low")

    def test_low_grade(self):
        self.assertEqual(api._normalize_credit_level("CCC"), "low")

    def test_empty(self):
        self.assertEqual(api._normalize_credit_level(""), "")

    def test_passthrough(self):
        self.assertEqual(api._normalize_credit_level("특수등급"), "특수등급")


# ===================================================================
# _normalize_admin_history
# ===================================================================
class NormalizeAdminHistoryTest(unittest.TestCase):
    def test_none_korean(self):
        self.assertEqual(api._normalize_admin_history("없음"), "none")

    def test_none_english(self):
        self.assertEqual(api._normalize_admin_history("clean"), "none")

    def test_has_korean(self):
        self.assertEqual(api._normalize_admin_history("있음"), "has")

    def test_has_penalty(self):
        self.assertEqual(api._normalize_admin_history("벌점"), "has")

    def test_empty(self):
        self.assertEqual(api._normalize_admin_history(""), "")

    def test_passthrough(self):
        self.assertEqual(api._normalize_admin_history("기타상태"), "기타상태")


# ===================================================================
# _get_special_balance_auto_policy
# ===================================================================
class GetSpecialBalanceAutoPolicyTest(unittest.TestCase):
    def test_electric_base(self):
        result = api._get_special_balance_auto_policy(license_text="전기", reorg_mode="")
        self.assertEqual(result["sector"], "전기")
        self.assertEqual(result["auto_mode"], "loan_withdrawal")
        self.assertAlmostEqual(result["min_auto_balance_share"], 0.10)
        self.assertAlmostEqual(result["min_auto_balance_eok"], 0.05)

    def test_electric_split_merge_override(self):
        result = api._get_special_balance_auto_policy(license_text="전기", reorg_mode="분할")
        self.assertEqual(result["reorg_mode"], "분할/합병")
        self.assertAlmostEqual(result["min_auto_balance_share"], 0.105)
        self.assertAlmostEqual(result["min_auto_balance_eok"], 0.05)

    def test_telecom_base(self):
        result = api._get_special_balance_auto_policy(license_text="정보통신", reorg_mode="")
        self.assertEqual(result["sector"], "정보통신")
        self.assertAlmostEqual(result["min_auto_balance_share"], 0.0625)
        self.assertAlmostEqual(result["min_auto_balance_eok"], 0.025)

    def test_telecom_split_merge_override(self):
        result = api._get_special_balance_auto_policy(license_text="정보통신", reorg_mode="합병")
        self.assertAlmostEqual(result["min_auto_balance_share"], 0.065)

    def test_fire_base(self):
        result = api._get_special_balance_auto_policy(license_text="소방", reorg_mode="")
        self.assertEqual(result["sector"], "소방")
        self.assertAlmostEqual(result["min_auto_balance_share"], 0.17)
        self.assertAlmostEqual(result["min_auto_balance_eok"], 0.09)

    def test_non_special_returns_empty(self):
        result = api._get_special_balance_auto_policy(license_text="토목", reorg_mode="")
        self.assertEqual(result["sector"], "")
        self.assertEqual(result["auto_mode"], "none")
        self.assertAlmostEqual(result["min_auto_balance_share"], 0.0)

    def test_summary_includes_sector(self):
        result = api._get_special_balance_auto_policy(license_text="전기", reorg_mode="")
        self.assertIn("전기", result["summary"])

    def test_summary_split_merge(self):
        result = api._get_special_balance_auto_policy(license_text="소방", reorg_mode="분할")
        self.assertIn("분할/합병", result["summary"])


# ===================================================================
# _resolve_special_auto_mode
# ===================================================================
class ResolveSpecialAutoModeTest(unittest.TestCase):
    def _policy(self, sector="전기"):
        return api._get_special_balance_auto_policy(license_text=sector, reorg_mode="")

    def test_zero_balance_returns_none(self):
        result = api._resolve_special_auto_mode(
            policy=self._policy(),
            total_transfer_value_eok=5.0,
            raw_balance_input_eok=0.0,
        )
        self.assertEqual(result["mode"], "none")

    def test_tiny_balance_returns_none(self):
        result = api._resolve_special_auto_mode(
            policy=self._policy(),
            total_transfer_value_eok=10.0,
            raw_balance_input_eok=0.01,  # share = 0.001, below 0.10
        )
        self.assertEqual(result["mode"], "none")

    def test_sufficient_balance_returns_mode(self):
        result = api._resolve_special_auto_mode(
            policy=self._policy(),
            total_transfer_value_eok=5.0,
            raw_balance_input_eok=1.0,  # share = 0.2 > 0.10
        )
        self.assertEqual(result["mode"], "loan_withdrawal")

    def test_none_policy_defaults_to_loan(self):
        # No policy → defaults to loan_withdrawal (base_mode fallback) with min_share=0.05
        result = api._resolve_special_auto_mode(
            policy=None,
            total_transfer_value_eok=5.0,
            raw_balance_input_eok=1.0,  # share=0.2 > 0.05 → sufficient
        )
        self.assertEqual(result["mode"], "loan_withdrawal")


# ===================================================================
# _resolve_balance_usage_mode
# ===================================================================
class ResolveBalanceUsageModeTest(unittest.TestCase):
    def test_explicit_mode(self):
        result = api._resolve_balance_usage_mode(
            requested_mode="융자인출",
            seller_withdraws_guarantee_loan=False,
            buyer_takes_balance_as_credit=False,
            balance_excluded=False,
        )
        self.assertEqual(result, "loan_withdrawal")

    def test_buyer_credit_flag(self):
        result = api._resolve_balance_usage_mode(
            requested_mode="",
            seller_withdraws_guarantee_loan=False,
            buyer_takes_balance_as_credit=True,
            balance_excluded=False,
        )
        self.assertEqual(result, "credit_transfer")

    def test_seller_loan_flag(self):
        result = api._resolve_balance_usage_mode(
            requested_mode="",
            seller_withdraws_guarantee_loan=True,
            buyer_takes_balance_as_credit=False,
            balance_excluded=False,
        )
        self.assertEqual(result, "loan_withdrawal")

    def test_not_excluded_returns_embedded(self):
        result = api._resolve_balance_usage_mode(
            requested_mode="",
            seller_withdraws_guarantee_loan=False,
            buyer_takes_balance_as_credit=False,
            balance_excluded=False,
        )
        self.assertEqual(result, "embedded_balance")

    def test_auto_with_special_sector(self):
        result = api._resolve_balance_usage_mode(
            requested_mode="auto",
            seller_withdraws_guarantee_loan=False,
            buyer_takes_balance_as_credit=False,
            balance_excluded=True,
            license_text="전기",
        )
        self.assertEqual(result, "loan_withdrawal")


# ===================================================================
# _json_ready
# ===================================================================
class JsonReadyTest(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(api._json_ready(None))

    def test_string(self):
        self.assertEqual(api._json_ready("hello"), "hello")

    def test_int(self):
        self.assertEqual(api._json_ready(42), 42)

    def test_dict(self):
        result = api._json_ready({"a": 1, "b": {2, 3}})
        self.assertEqual(result["a"], 1)
        self.assertIsInstance(result["b"], list)

    def test_set_sorted(self):
        result = api._json_ready({3, 1, 2})
        self.assertEqual(result, [1, 2, 3])

    def test_list(self):
        self.assertEqual(api._json_ready([1, "a"]), [1, "a"])

    def test_namedtuple_as_tuple(self):
        # namedtuples are tuples first → isinstance(value, tuple) matches before _asdict
        Point = namedtuple("Point", ["x", "y"])
        result = api._json_ready(Point(1, 2))
        self.assertEqual(result, [1, 2])

    def test_custom_object(self):
        class Obj:
            def __init__(self):
                self.val = 99
        result = api._json_ready(Obj())
        self.assertEqual(result["val"], 99)

    def test_fallback_to_str(self):
        result = api._json_ready(complex(1, 2))
        self.assertEqual(result, "(1+2j)")


# ===================================================================
# _pick_total_value
# ===================================================================
class PickTotalValueTest(unittest.TestCase):
    def test_total_transfer_value(self):
        self.assertEqual(api._pick_total_value({"total_transfer_value_eok": 5.0}), 5.0)

    def test_internal_estimate(self):
        self.assertEqual(api._pick_total_value({"internal_estimate_eok": 3.0}), 3.0)

    def test_priority_order(self):
        result = api._pick_total_value({
            "estimate_center_eok": 2.0,
            "internal_estimate_eok": 3.0,
        })
        self.assertEqual(result, 3.0)  # internal_estimate_eok comes first

    def test_fallback_to_average(self):
        result = api._pick_total_value({
            "estimate_low_eok": 2.0,
            "estimate_high_eok": 4.0,
        })
        self.assertAlmostEqual(result, 3.0)

    def test_empty_returns_zero(self):
        self.assertEqual(api._pick_total_value({}), 0.0)


# ===================================================================
# _clean_row_license_text
# ===================================================================
class CleanRowLicenseTextTest(unittest.TestCase):
    def test_valid_text_unchanged(self):
        row = {"license_text": "전기공사업"}
        result = api._clean_row_license_text(row, "fallback")
        self.assertEqual(result["license_text"], "전기공사업")

    def test_empty_uses_fallback(self):
        row = {"license_text": ""}
        result = api._clean_row_license_text(row, "토목")
        self.assertEqual(result["license_text"], "토목")

    def test_question_marks_uses_fallback(self):
        row = {"license_text": "???"}
        result = api._clean_row_license_text(row, "건축")
        self.assertEqual(result["license_text"], "건축")

    def test_none_row(self):
        result = api._clean_row_license_text(None, "전기")
        self.assertEqual(result["license_text"], "전기")

    def test_missing_key(self):
        result = api._clean_row_license_text({}, "소방")
        self.assertEqual(result["license_text"], "소방")

    def test_original_not_mutated(self):
        row = {"license_text": "", "other": "data"}
        result = api._clean_row_license_text(row, "전기")
        self.assertEqual(row["license_text"], "")  # original unchanged
        self.assertEqual(result["license_text"], "전기")


# ===================================================================
# _license_text_parts
# ===================================================================
class LicenseTextPartsTest(unittest.TestCase):
    def test_string(self):
        self.assertEqual(api._license_text_parts("전기공사업"), ["전기공사업"])

    def test_dict(self):
        parts = api._license_text_parts({
            "license_text": "전기",
            "raw_license_key": "EL",
            "license_tokens": ["전기공사업"],
        })
        self.assertIn("전기", parts)
        self.assertIn("EL", parts)
        self.assertIn("전기공사업", parts)

    def test_list(self):
        parts = api._license_text_parts(["전기", "토목"])
        self.assertEqual(parts, ["전기", "토목"])

    def test_empty(self):
        self.assertEqual(api._license_text_parts(""), [])

    def test_none(self):
        self.assertEqual(api._license_text_parts(None), [])

    def test_set(self):
        parts = api._license_text_parts({"전기", "토목"})
        self.assertEqual(len(parts), 2)


if __name__ == "__main__":
    unittest.main()
