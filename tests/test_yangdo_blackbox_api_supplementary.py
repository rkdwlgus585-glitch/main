"""Supplementary unit tests for yangdo_blackbox_api.py.

Covers: _apply_special_sector_publication_guard, _prioritize_display_neighbors.
"""

import unittest

import yangdo_blackbox_api as api


# ===================================================================
# _apply_special_sector_publication_guard
# ===================================================================
class ApplySpecialSectorPublicationGuardTest(unittest.TestCase):
    def _target(self, license_text="정보통신공사업"):
        return {"license_tokens": [license_text], "license_text": license_text}

    def _result(self, **overrides):
        base = {
            "publication_mode": "full",
            "estimate_center_eok": 3.0,
            "estimate_low_eok": 2.0,
            "estimate_high_eok": 4.0,
            "confidence_percent": 92,
            "risk_notes": [],
        }
        base.update(overrides)
        return base

    def test_non_telecom_unchanged(self):
        target = {"license_tokens": ["전기공사업"], "license_text": "전기공사업"}
        result = self._result()
        out = api._apply_special_sector_publication_guard(result, target)
        self.assertEqual(out["publication_mode"], "full")

    def test_not_full_mode_unchanged(self):
        result = self._result(publication_mode="range_only")
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "range_only")

    def test_high_confidence_wide_range_unchanged(self):
        """Confidence 92%, center=3, range 2-4 (span_ratio=0.67 < 0.70) → pass."""
        result = self._result()
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "full")

    def test_too_wide_range_downgrades(self):
        """span_ratio > 0.70 → range_only."""
        result = self._result(
            estimate_center_eok=1.0,
            estimate_low_eok=0.5,
            estimate_high_eok=1.8,  # span = 1.3, ratio = 1.3 > 0.70
            confidence_percent=95,
        )
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "range_only")
        self.assertIn("범위 폭이 넓음", out["publication_reason"])

    def test_too_small_center_downgrades(self):
        """center < 0.25 → range_only."""
        result = self._result(
            estimate_center_eok=0.2,
            estimate_low_eok=0.15,
            estimate_high_eok=0.25,
            confidence_percent=95,
        )
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "range_only")
        self.assertIn("절대 금액 구간이 작음", out["publication_reason"])

    def test_low_confidence_downgrades(self):
        """confidence < 90 → range_only."""
        result = self._result(confidence_percent=85)
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "range_only")
        self.assertIn("신뢰도 기준 미달", out["publication_reason"])

    def test_boundary_confidence_90_passes(self):
        """confidence == 90 is NOT < 90, so passes."""
        result = self._result(confidence_percent=90)
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "full")

    def test_boundary_span_070_passes(self):
        """span_ratio == 0.70 is NOT > 0.70, so passes."""
        result = self._result(
            estimate_center_eok=10.0,
            estimate_low_eok=6.5,
            estimate_high_eok=13.5,  # span=7, ratio=0.70 exactly
            confidence_percent=95,
        )
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "full")

    def test_multiple_triggers(self):
        """All three triggers → combined reason."""
        result = self._result(
            estimate_center_eok=0.1,
            estimate_low_eok=0.01,
            estimate_high_eok=0.5,
            confidence_percent=50,
        )
        out = api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(out["publication_mode"], "range_only")
        self.assertIn("범위 폭이 넓음", out["publication_reason"])
        self.assertIn("절대 금액 구간이 작음", out["publication_reason"])
        self.assertIn("신뢰도 기준 미달", out["publication_reason"])

    def test_risk_notes_appended_not_duplicated(self):
        """Reason appended to risk_notes, no duplicates."""
        result = self._result(confidence_percent=80)
        out = api._apply_special_sector_publication_guard(result, self._target())
        reason = out["publication_reason"]
        self.assertIn(reason, out["risk_notes"])
        # Call again — should not duplicate
        out2 = api._apply_special_sector_publication_guard(out, self._target())
        self.assertEqual(out2["risk_notes"].count(reason), 1)

    def test_none_result_handled(self):
        """None result → empty dict output."""
        out = api._apply_special_sector_publication_guard(None, self._target())
        self.assertIsInstance(out, dict)

    def test_does_not_mutate_input(self):
        """Returns new dict, doesn't mutate input."""
        result = self._result(confidence_percent=80)
        original_mode = result["publication_mode"]
        api._apply_special_sector_publication_guard(result, self._target())
        self.assertEqual(result["publication_mode"], original_mode)


# ===================================================================
# _prioritize_display_neighbors
# ===================================================================
class PrioritizeDisplayNeighborsTest(unittest.TestCase):
    def _target(self, **overrides):
        base = {"sales3_eok": 5.0, "sales5_eok": 3.0}
        base.update(overrides)
        return base

    def _rec(self, number=100, sales3=4.0, sales5=2.0, **extra):
        r = {"number": number, "sales3_eok": sales3, "sales5_eok": sales5}
        r.update(extra)
        return r

    def test_empty_rows(self):
        self.assertEqual(api._prioritize_display_neighbors({}, []), [])

    def test_single_row(self):
        rows = [(90.0, self._rec())]
        result = api._prioritize_display_neighbors(self._target(), rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 90.0)

    def test_higher_similarity_preferred(self):
        """Higher similarity score ranks first, all else equal."""
        rows = [
            (80.0, self._rec(number=1)),
            (95.0, self._rec(number=2)),
        ]
        result = api._prioritize_display_neighbors(self._target(), rows)
        self.assertEqual(result[0][1]["number"], 2)

    def test_no_sales_target(self):
        """Target without sales data doesn't crash."""
        target = {"sales3_eok": 0, "sales5_eok": 0}
        rows = [(90.0, self._rec())]
        result = api._prioritize_display_neighbors(target, rows)
        self.assertEqual(len(result), 1)

    def test_preserves_all_rows(self):
        rows = [(90.0, self._rec(number=i)) for i in range(5)]
        result = api._prioritize_display_neighbors(self._target(), rows)
        self.assertEqual(len(result), 5)

    def test_non_dict_rec_handled(self):
        """Non-dict record doesn't crash."""
        rows = [(90.0, None), (85.0, "invalid")]
        result = api._prioritize_display_neighbors(self._target(), rows)
        self.assertEqual(len(result), 2)


# ===================================================================
# _round4
# ===================================================================
class Round4Test(unittest.TestCase):
    def test_normal_value(self):
        result = api._round4(1.23456)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 1.2346, places=4)

    def test_none_returns_none(self):
        self.assertIsNone(api._round4(None))

    def test_zero(self):
        self.assertEqual(api._round4(0), 0.0)

    def test_string_numeric(self):
        result = api._round4("3.5")
        self.assertAlmostEqual(result, 3.5)


# ===================================================================
# _normalize_license_text
# ===================================================================
class NormalizeLicenseTextTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(api._normalize_license_text("  전기공사업  "), "전기공사업")

    def test_none(self):
        self.assertEqual(api._normalize_license_text(None), "")


# ===================================================================
# _settlement_mode_label
# ===================================================================
class SettlementModeLabelTest(unittest.TestCase):
    def test_embedded_balance(self):
        result = api._settlement_mode_label("embedded_balance")
        self.assertIn("반영", result)

    def test_credit_transfer(self):
        result = api._settlement_mode_label("credit_transfer")
        self.assertIn("1:1", result)

    def test_loan_withdrawal(self):
        result = api._settlement_mode_label("loan_withdrawal")
        self.assertIn("융자", result)

    def test_none_mode(self):
        result = api._settlement_mode_label("none")
        self.assertIn("없음", result)

    def test_auto_default(self):
        result = api._settlement_mode_label("auto")
        self.assertIn("기본값", result)

    def test_empty(self):
        result = api._settlement_mode_label("")
        self.assertIn("기본값", result)


# ===================================================================
# _settlement_input_mode_label
# ===================================================================
class SettlementInputModeLabelTest(unittest.TestCase):
    def test_credit_transfer(self):
        result = api._settlement_input_mode_label("credit_transfer")
        self.assertIn("1:1", result)

    def test_none_mode(self):
        result = api._settlement_input_mode_label("none")
        self.assertIn("없음", result)

    def test_loan_withdrawal(self):
        result = api._settlement_input_mode_label("loan_withdrawal")
        self.assertIn("융자", result)

    def test_default_fallback(self):
        result = api._settlement_input_mode_label("")
        self.assertIn("기본값", result)


# ===================================================================
# _range_pair_from_record
# ===================================================================
class RangePairFromRecordTest(unittest.TestCase):
    def test_explicit_low_high(self):
        rec = {"display_low_eok": 1.0, "display_high_eok": 3.0}
        low, high = api._range_pair_from_record(rec)
        self.assertAlmostEqual(low, 1.0)
        self.assertAlmostEqual(high, 3.0)

    def test_swaps_if_inverted(self):
        rec = {"display_low_eok": 5.0, "display_high_eok": 2.0}
        low, high = api._range_pair_from_record(rec)
        self.assertAlmostEqual(low, 2.0)
        self.assertAlmostEqual(high, 5.0)

    def test_falls_back_to_current_price(self):
        rec = {"current_price_eok": 4.0}
        low, high = api._range_pair_from_record(rec)
        self.assertAlmostEqual(low, 4.0)
        self.assertAlmostEqual(high, 4.0)

    def test_falls_back_to_price_eok(self):
        rec = {"price_eok": 2.5}
        low, high = api._range_pair_from_record(rec)
        self.assertAlmostEqual(low, 2.5)
        self.assertAlmostEqual(high, 2.5)

    def test_empty_record(self):
        low, high = api._range_pair_from_record({})
        self.assertIsNone(low)
        self.assertIsNone(high)


# ===================================================================
# _single_license_special_sector_rows
# ===================================================================
class SingleLicenseSpecialSectorRowsTest(unittest.TestCase):
    def _make_row(self, token, price=2.0):
        return {"license_tokens": [token], "current_price_eok": price, "license_text": token}

    def test_filters_matching_sector(self):
        rows = [self._make_row("전기공사업"), self._make_row("소방시설공사업")]
        result = api._single_license_special_sector_rows(rows, "전기")
        self.assertEqual(len(result), 1)

    def test_excludes_multi_token(self):
        rows = [{"license_tokens": ["전기공사업", "소방시설공사업"], "current_price_eok": 2.0}]
        result = api._single_license_special_sector_rows(rows, "전기")
        self.assertEqual(len(result), 0)

    def test_excludes_zero_price(self):
        rows = [self._make_row("전기공사업", price=0)]
        result = api._single_license_special_sector_rows(rows, "전기")
        self.assertEqual(len(result), 0)

    def test_empty_records(self):
        self.assertEqual(api._single_license_special_sector_rows([], "전기"), [])

    def test_none_records(self):
        self.assertEqual(api._single_license_special_sector_rows(None, "전기"), [])


# ===================================================================
# _partner_health_payload
# ===================================================================
class PartnerHealthPayloadTest(unittest.TestCase):
    def test_structure(self):
        payload = api._partner_health_payload()
        self.assertTrue(payload["ok"])
        self.assertIn("service", payload)
        self.assertEqual(payload["message"], "healthy")

    def test_has_health_contract(self):
        payload = api._partner_health_payload()
        self.assertIn("health_contract", payload)


# ===================================================================
# _build_single_settlement_view
# ===================================================================
class BuildSingleSettlementViewTest(unittest.TestCase):
    def _defaults(self, **overrides):
        base = {
            "total_transfer_value_eok": 10.0,
            "total_low_eok": 8.0,
            "total_high_eok": 12.0,
            "public_total_transfer_value_eok": 10.0,
            "public_total_low_eok": 8.0,
            "public_total_high_eok": 12.0,
            "raw_balance_input_eok": 2.0,
            "balance_excluded": False,
            "resolved_mode": "embedded_balance",
            "effective_balance_rate": 0.5,
        }
        base.update(overrides)
        return base

    def test_embedded_balance_mode(self):
        result = api._build_single_settlement_view(**self._defaults())
        self.assertEqual(result["mode"], "embedded_balance")
        self.assertIsNotNone(result["estimated_cash_due_eok"])
        self.assertIsNotNone(result["total_transfer_value_eok"])

    def test_credit_transfer_mode(self):
        result = api._build_single_settlement_view(**self._defaults(resolved_mode="credit_transfer"))
        self.assertEqual(result["mode"], "credit_transfer")
        # With 2.0 balance at rate 1.0, cash_due should be 10 - 2 = 8
        self.assertAlmostEqual(result["estimated_cash_due_eok"], 8.0, places=2)

    def test_none_mode_no_balance(self):
        result = api._build_single_settlement_view(**self._defaults(resolved_mode="none"))
        self.assertEqual(result["mode"], "none")
        # Balance has 0 realizable, so cash = total = 10
        self.assertAlmostEqual(result["estimated_cash_due_eok"], 10.0, places=2)

    def test_zero_balance(self):
        result = api._build_single_settlement_view(**self._defaults(raw_balance_input_eok=0))
        # No balance to deduct
        self.assertAlmostEqual(result["estimated_cash_due_eok"], 10.0, places=2)


# ===================================================================
# _build_settlement_output
# ===================================================================
class BuildSettlementOutputTest(unittest.TestCase):
    def _defaults(self, **overrides):
        base = {
            "total_transfer_value_eok": 10.0,
            "total_low_eok": 8.0,
            "total_high_eok": 12.0,
            "public_total_transfer_value_eok": 10.0,
            "public_total_low_eok": 8.0,
            "public_total_high_eok": 12.0,
            "raw_balance_input_eok": 2.0,
            "balance_excluded": False,
            "balance_usage_mode": "embedded_balance",
            "effective_balance_rate": 0.5,
            "split_optional_pricing": False,
        }
        base.update(overrides)
        return base

    def test_basic_output_structure(self):
        result = api._build_settlement_output(**self._defaults())
        self.assertIn("balance_usage_mode", result)
        self.assertIn("estimated_cash_due_eok", result)
        self.assertIn("settlement_policy", result)

    def test_balance_excluded_with_special_sector(self):
        result = api._build_settlement_output(**self._defaults(
            balance_excluded=True,
            license_text="전기공사업",
        ))
        self.assertIn("settlement_policy", result)
        policy = result["settlement_policy"]
        self.assertEqual(policy["sector"], "전기")


# ===================================================================
# Tenant/gateway functions (with mock objects)
# ===================================================================
class _MockTenant:
    def __init__(self, tenant_id="", plan=""):
        self.tenant_id = tenant_id
        self.plan = plan


class _MockResolution:
    def __init__(self, tenant=None):
        self.tenant = tenant


class _MockGateway:
    def __init__(self, features=None):
        self._features = features or set()

    def check_feature(self, resolution, feature):
        return feature in self._features


class _MockServer:
    def __init__(self, gw_enabled=False, gateway=None):
        self.tenant_gateway_enabled = gw_enabled
        self.tenant_gateway = gateway


class TenantPlanKeyTest(unittest.TestCase):
    def test_with_plan(self):
        res = _MockResolution(tenant=_MockTenant(plan="PRO"))
        self.assertEqual(api._tenant_plan_key(res), "pro")

    def test_no_tenant(self):
        res = _MockResolution(tenant=None)
        self.assertEqual(api._tenant_plan_key(res), "")

    def test_empty_plan(self):
        res = _MockResolution(tenant=_MockTenant(plan=""))
        self.assertEqual(api._tenant_plan_key(res), "")


class TenantIdValueTest(unittest.TestCase):
    def test_with_id(self):
        res = _MockResolution(tenant=_MockTenant(tenant_id="t-123"))
        self.assertEqual(api._tenant_id_value(res), "t-123")

    def test_no_tenant(self):
        res = _MockResolution(tenant=None)
        self.assertEqual(api._tenant_id_value(res), "")


class TenantHasFeatureTest(unittest.TestCase):
    def test_gateway_disabled_returns_true(self):
        server = _MockServer(gw_enabled=False)
        self.assertTrue(api._tenant_has_feature(server, None, "any_feature"))

    def test_feature_present(self):
        gw = _MockGateway(features={"estimate_detail"})
        server = _MockServer(gw_enabled=True, gateway=gw)
        res = _MockResolution()
        self.assertTrue(api._tenant_has_feature(server, res, "estimate_detail"))

    def test_feature_absent(self):
        gw = _MockGateway(features=set())
        server = _MockServer(gw_enabled=True, gateway=gw)
        res = _MockResolution()
        self.assertFalse(api._tenant_has_feature(server, res, "estimate_detail"))


class EstimateResponseTierTest(unittest.TestCase):
    def test_gateway_disabled_returns_internal(self):
        server = _MockServer(gw_enabled=False)
        self.assertEqual(api._estimate_response_tier(server, None), "internal")

    def test_internal_feature(self):
        gw = _MockGateway(features={"estimate_internal"})
        server = _MockServer(gw_enabled=True, gateway=gw)
        res = _MockResolution()
        self.assertEqual(api._estimate_response_tier(server, res), "internal")

    def test_detail_feature(self):
        gw = _MockGateway(features={"estimate_detail"})
        server = _MockServer(gw_enabled=True, gateway=gw)
        res = _MockResolution()
        self.assertEqual(api._estimate_response_tier(server, res), "detail")

    def test_summary_default(self):
        gw = _MockGateway(features=set())
        server = _MockServer(gw_enabled=True, gateway=gw)
        res = _MockResolution()
        self.assertEqual(api._estimate_response_tier(server, res), "summary")


# ===================================================================
# _project_estimate_result  (3-tier response projection)
# ===================================================================
class ProjectEstimateResultTest(unittest.TestCase):
    def _make_result(self, ok=True):
        return {
            "ok": ok,
            "generated_at": "2026-03-10",
            "estimate_center_eok": 5.0,
            "estimate_low_eok": 4.0,
            "estimate_high_eok": 6.0,
            "confidence_score": 80,
            "confidence_percent": 80,
            "publication_mode": "auto",
            "publication_label": "공개",
            "publication_reason": "충분 데이터",
            "price_source_tier": "primary",
            "price_source_label": "실거래 기반",
            "price_sample_count": 10,
            "price_is_estimate": False,
            "price_range_kind": "normal",
            "price_source_channel": "seoul",
            "price_disclaimer": "참고용",
            "recommendation_meta": {"strategy": "standard"},
            "recommended_listings": [
                {
                    "seoul_no": 1234,
                    "license_text": "전기공사업",
                    "price_eok": 3.0,
                    "display_low_eok": 2.5,
                    "display_high_eok": 3.5,
                    "sales3_eok": 1.0,
                    "recommendation_label": "추천",
                    "recommendation_focus": "가격 유사",
                    "precision_tier": "A",
                    "reasons": ["가격 범위 일치"],
                    "fit_summary": "적합",
                    "matched_axes": ["price"],
                    "mismatch_flags": [],
                    "url": "https://example.com/1234",
                },
            ],
            "neighbors": [{"id": 1}],
            "settlement_output": {"mode": "embedded_balance"},
        }

    def test_summary_trims_heavy_fields(self):
        """Summary tier strips neighbors, settlement_output, etc."""
        gw = _MockGateway(features=set())
        server = _MockServer(gw_enabled=True, gateway=gw)
        res = _MockResolution(tenant=_MockTenant(plan="basic"))
        result = api._project_estimate_result(server, res, self._make_result())
        self.assertTrue(result["ok"])
        self.assertNotIn("neighbors", result)
        self.assertNotIn("settlement_output", result)
        self.assertIn("response_policy", result)
        self.assertEqual(result["response_policy"]["tier"], "summary")

    def test_summary_limits_recommended_listings(self):
        """Summary recommended listings trimmed to 3 and simplified."""
        gw = _MockGateway(features=set())
        server = _MockServer(gw_enabled=True, gateway=gw)
        res = _MockResolution(tenant=_MockTenant(plan="basic"))
        result = api._project_estimate_result(server, res, self._make_result())
        listings = result.get("recommended_listings", [])
        self.assertLessEqual(len(listings), 3)
        if listings:
            # Summary listings should NOT have detailed fields like precision_tier
            self.assertNotIn("precision_tier", listings[0])
            self.assertIn("recommendation_label", listings[0])

    def test_detail_strips_neighbors(self):
        """Detail tier removes neighbors but keeps more fields."""
        gw = _MockGateway(features={"estimate_detail"})
        server = _MockServer(gw_enabled=True, gateway=gw)
        res = _MockResolution(tenant=_MockTenant(plan="pro"))
        result = api._project_estimate_result(server, res, self._make_result())
        self.assertNotIn("neighbors", result)
        self.assertIn("response_policy", result)
        self.assertEqual(result["response_policy"]["tier"], "detail")

    def test_internal_includes_tenant_id(self):
        """Internal tier exposes tenant_id."""
        server = _MockServer(gw_enabled=False)
        res = _MockResolution(tenant=_MockTenant(tenant_id="t-999"))
        result = api._project_estimate_result(server, res, self._make_result())
        self.assertEqual(result["response_policy"]["tier"], "internal")
        self.assertEqual(result["tenant_id"], "t-999")

    def test_error_result_still_has_policy(self):
        """Error result gets response_policy attached."""
        server = _MockServer(gw_enabled=False)
        res = _MockResolution()
        result = api._project_estimate_result(server, res, {"ok": False, "error": "no_data"})
        self.assertFalse(result["ok"])
        self.assertIn("response_policy", result)


if __name__ == "__main__":
    unittest.main()
