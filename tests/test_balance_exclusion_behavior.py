import importlib
import unittest
from types import SimpleNamespace

import yangdo_blackbox_api

allmod = importlib.import_module("all")


class BalanceExclusionBehaviorTest(unittest.TestCase):
    def setUp(self):
        self.est = yangdo_blackbox_api.YangdoBlackboxEstimator()

    @staticmethod
    def _meta_from_records(records):
        def _avg(field):
            vals = [float(r.get(field)) for r in records if isinstance(r.get(field), (int, float))]
            if not vals:
                return None
            return sum(vals) / len(vals)

        def _median(field):
            vals = sorted(float(r.get(field)) for r in records if isinstance(r.get(field), (int, float)))
            if not vals:
                return None
            mid = len(vals) // 2
            if len(vals) % 2:
                return vals[mid]
            return (vals[mid - 1] + vals[mid]) / 2.0

        return {
            "avg_balance_eok": _avg("balance_eok"),
            "avg_capital_eok": _avg("capital_eok"),
            "avg_surplus_eok": _avg("surplus_eok"),
            "median_specialty": _median("specialty"),
            "median_sales3_eok": _median("sales3_eok"),
        }

    def _prime_estimator(self, records):
        self.est._records = list(records)
        self.est._train_records = list(records)
        self.est._token_index = allmod._build_neighbor_index(records)
        self.est._meta = self._meta_from_records(records)

    def _record(
        self,
        *,
        uid,
        specialty,
        sales3,
        balance,
        price,
        license_text="토목",
        row=1,
    ):
        base = self.est._target_from_payload(
            {
                "license_text": license_text,
                "specialty": specialty,
                "sales3_eok": sales3,
                "sales5_eok": sales3 * 1.35,
                "balance_eok": balance,
                "capital_eok": 3.0,
                "surplus_eok": 0.4,
                "license_year": 2016,
                "debt_ratio": 70.0,
                "liq_ratio": 220.0,
                "company_type": "주식회사",
                "credit_level": "보통",
                "admin_history": "없음",
                "provided_signals": 9,
            }
        )
        base.update(
            {
                "uid": str(uid),
                "row": int(row),
                "number": int(uid),
                "current_price_eok": float(price),
                "claim_price_eok": None,
                "current_price_text": f"{price}억",
                "claim_price_text": "",
                "years": {"y23": round(sales3 * 0.30, 4), "y24": round(sales3 * 0.33, 4), "y25": round(sales3 * 0.37, 4)},
            }
        )
        return base

    @staticmethod
    def _candidate(token_text: str):
        return {
            "license_text": token_text,
            "license_tokens": {token_text},
            "specialty": None,
            "sales3_eok": None,
            "sales5_eok": None,
            "license_year": None,
            "debt_ratio": None,
            "liq_ratio": None,
            "capital_eok": None,
            "balance_eok": 5.0,
            "surplus_eok": None,
            "company_type": "",
        }

    @staticmethod
    def _target(token_text: str, balance_eok: float):
        return {
            "license_text": token_text,
            "raw_license_key": token_text,
            "license_tokens": {token_text},
            "specialty": None,
            "sales3_eok": None,
            "sales5_eok": None,
            "license_year": None,
            "debt_ratio": None,
            "liq_ratio": None,
            "capital_eok": None,
            "balance_eok": float(balance_eok),
            "surplus_eok": None,
            "company_type": "",
        }

    def test_balance_change_does_not_affect_excluded_group_score(self):
        electric = "\uC804\uAE30"
        cand = self._candidate(electric)
        t1 = self._target(electric, 0.5)
        t2 = self._target(electric, 50.0)

        s1 = self.est._neighbor_score(t1, cand)
        s2 = self.est._neighbor_score(t2, cand)

        self.assertTrue(self.est._is_balance_separate_paid_group(t1))
        self.assertAlmostEqual(s1, s2, places=9)

    def test_balance_change_affects_non_excluded_group_score(self):
        civil = "\uD1A0\uBAA9"
        cand = self._candidate(civil)
        t1 = self._target(civil, 5.0)
        t2 = self._target(civil, 50.0)

        s1 = self.est._neighbor_score(t1, cand)
        s2 = self.est._neighbor_score(t2, cand)

        self.assertFalse(self.est._is_balance_separate_paid_group(t1))
        self.assertNotEqual(round(s1, 6), round(s2, 6))

    def test_project_estimate_result_converts_target_token_set_to_json_safe_list(self):
        server = SimpleNamespace(
            tenant_gateway_enabled=False,
        )
        resolution = SimpleNamespace(
            tenant=SimpleNamespace(
                tenant_id="seoul_main",
                plan="pro_internal",
            )
        )
        payload = {
            "ok": True,
            "publication_mode": "range_only",
            "target": {
                "license_text": "\uC804\uAE30\uACF5\uC0AC\uC5C5",
                "license_tokens": {"\uC804\uAE30\uACF5\uC0AC\uC5C5"},
            },
        }

        projected = yangdo_blackbox_api._project_estimate_result(server, resolution, payload)

        self.assertIsInstance(projected.get("target"), dict)
        self.assertEqual(projected.get("target", {}).get("license_tokens"), ["\uC804\uAE30\uACF5\uC0AC\uC5C5"])

    def test_split_mode_clears_optional_pricing_fields_for_separate_group(self):
        target = self.est._target_from_payload(
            {
                "license_text": "\uC804\uAE30",
                "reorg_mode": "\uBD84\uD560/\uD569\uBCD1",
                "specialty": 42.0,
                "sales3_eok": 18.0,
                "sales5_eok": 27.0,
                "capital_eok": 3.2,
                "surplus_eok": 6.4,
                "debt_ratio": 180.0,
                "liq_ratio": 3200.0,
                "credit_level": "high",
            }
        )

        self.assertTrue(target.get("split_optional_pricing"))
        self.assertIsNone(target.get("specialty"))
        self.assertIsNone(target.get("surplus_eok"))
        self.assertIsNone(target.get("debt_ratio"))
        self.assertIsNone(target.get("liq_ratio"))
        self.assertEqual(target.get("credit_level"), "")
        self.assertNotIn("\uC774\uC775\uC789\uC5EC\uAE08", list(target.get("missing_critical") or []))

    def test_split_mode_ignores_specialty_surplus_credit_and_ratio_inputs(self):
        electric = "\uC804\uAE30"
        records = [
            self._record(uid=8101, specialty=14.0, sales3=8.5, balance=0.5, price=1.72, license_text=electric, row=1),
            self._record(uid=8102, specialty=18.0, sales3=10.2, balance=0.7, price=1.94, license_text=electric, row=2),
            self._record(uid=8103, specialty=22.0, sales3=12.4, balance=0.8, price=2.18, license_text=electric, row=3),
            self._record(uid=8104, specialty=27.0, sales3=15.1, balance=0.9, price=2.41, license_text=electric, row=4),
        ]
        self._prime_estimator(records)

        base = {
            "license_text": electric,
            "reorg_mode": "\uBD84\uD560/\uD569\uBCD1",
            "specialty": 12.0,
            "sales3_eok": 9.0,
            "sales5_eok": 14.0,
            "capital_eok": 3.0,
            "surplus_eok": 0.5,
            "debt_ratio": 80.0,
            "liq_ratio": 240.0,
            "credit_level": "high",
            "admin_history": "none",
            "ok_capital": True,
            "ok_engineer": True,
            "ok_office": True,
        }
        changed = dict(base)
        changed.update(
            {
                "specialty": 65.0,
                "surplus_eok": 18.0,
                "debt_ratio": 420.0,
                "liq_ratio": 40.0,
                "credit_level": "low",
            }
        )

        base_out = self.est.estimate(base)
        changed_out = self.est.estimate(changed)

        self.assertTrue(base_out.get("ok"))
        self.assertTrue(changed_out.get("ok"))
        self.assertAlmostEqual(
            float(base_out.get("core_estimate_eok") or 0.0),
            float(changed_out.get("core_estimate_eok") or 0.0),
            places=9,
        )

    def test_merge_alias_is_treated_as_split_merge_group(self):
        target = self.est._target_from_payload(
            {
                "license_text": "\uC18C\uBC29",
                "reorg_mode": "\uD569\uBCD1",
                "specialty": 18.0,
                "sales3_eok": 9.0,
                "sales5_eok": 13.0,
                "capital_eok": 2.8,
                "surplus_eok": 1.6,
                "debt_ratio": 140.0,
                "liq_ratio": 180.0,
                "credit_level": "mid",
            }
        )

        self.assertEqual(target.get("reorg_mode"), "\uBD84\uD560/\uD569\uBCD1")
        self.assertTrue(target.get("split_optional_pricing"))
        self.assertIsNone(target.get("specialty"))
        self.assertEqual(target.get("credit_level"), "")

    def test_ambiguous_split_comprehensive_value_requires_explicit_selection(self):
        target = self.est._target_from_payload(
            {
                "license_text": "\uC804\uAE30",
                "reorg_mode": "\uBD84\uD560\uD3EC\uAD04",
                "sales3_eok": 9.0,
                "sales5_eok": 14.0,
                "capital_eok": 3.0,
                "balance_eok": 0.7,
            }
        )

        self.assertTrue(target.get("requires_reorg_mode"))
        self.assertEqual(target.get("reorg_mode"), "")

    def test_comprehensive_mode_keeps_optional_pricing_fields_active(self):
        electric = "\uC804\uAE30"
        records = [
            self._record(uid=8201, specialty=14.0, sales3=8.5, balance=0.5, price=1.72, license_text=electric, row=1),
            self._record(uid=8202, specialty=18.0, sales3=10.2, balance=0.7, price=1.94, license_text=electric, row=2),
            self._record(uid=8203, specialty=22.0, sales3=12.4, balance=0.8, price=2.18, license_text=electric, row=3),
            self._record(uid=8204, specialty=27.0, sales3=15.1, balance=0.9, price=2.41, license_text=electric, row=4),
        ]
        self._prime_estimator(records)

        base = {
            "license_text": electric,
            "reorg_mode": "\uD3EC\uAD04",
            "specialty": 12.0,
            "sales3_eok": 9.0,
            "sales5_eok": 14.0,
            "capital_eok": 3.0,
            "surplus_eok": 0.5,
            "debt_ratio": 80.0,
            "liq_ratio": 240.0,
            "credit_level": "high",
            "admin_history": "none",
            "ok_capital": True,
            "ok_engineer": True,
            "ok_office": True,
        }
        changed = dict(base)
        changed.update(
            {
                "specialty": 65.0,
                "surplus_eok": 18.0,
                "debt_ratio": 420.0,
                "liq_ratio": 40.0,
                "credit_level": "low",
            }
        )

        base_out = self.est.estimate(base)
        changed_out = self.est.estimate(changed)

        self.assertTrue(base_out.get("ok"))
        self.assertTrue(changed_out.get("ok"))
        self.assertNotAlmostEqual(
            float(base_out.get("core_estimate_eok") or 0.0),
            float(changed_out.get("core_estimate_eok") or 0.0),
            places=4,
        )

    def test_missing_core_scale_fields_are_counted_as_mismatch(self):
        target = {
            "license_text": "\uCCA0\uCF58\n\uC2B5\uC2DD",
            "raw_license_key": "\uCCA0\uCF58\n\uC2B5\uC2DD",
            "license_tokens": {"\uCCA0\uCF58", "\uC2B5\uC2DD"},
            "specialty": 24.0,
            "sales3_eok": 18.0,
            "sales5_eok": 26.0,
            "capital_eok": 2.5,
            "balance_eok": 0.5,
        }
        candidate = {
            "license_text": "\uCCA0\uCF58\n\uC2B5\uC2DD",
            "license_tokens": {"\uCCA0\uCF58", "\uC2B5\uC2DD"},
            "specialty": None,
            "sales3_eok": None,
            "sales5_eok": None,
            "capital_eok": 2.5,
            "balance_eok": 0.5,
        }

        signal_count, mismatch_count = self.est._feature_scale_mismatch(
            target,
            candidate,
            balance_excluded=False,
        )

        self.assertGreaterEqual(signal_count, 2)
        self.assertGreaterEqual(mismatch_count, 2)

    def test_single_core_publication_cap_consult_only_for_sparse_missing_scale(self):
        cap = yangdo_blackbox_api._single_core_publication_cap(
            center=0.62,
            target={
                "single_core_mode": True,
                "single_core_median_eok": 1.2,
                "single_core_support_count": 1,
                "single_core_dispersion_ratio": 1.0,
                "specialty": None,
                "sales3_eok": 7.0,
            },
        )

        self.assertEqual(cap.get("confidence_cap"), 50.0)
        self.assertTrue(cap.get("reason"))

    def test_publication_policy_uses_range_for_low_confidence_when_support_is_not_very_sparse(self):
        policy = yangdo_blackbox_api._build_publication_policy(
            center=1.8,
            low=1.5,
            high=2.1,
            confidence_score=50.0,
            effective_cluster_count=4,
            target={
                "license_text": "\uAC74\uCD95",
                "provided_signals": 3,
                "missing_critical": ["\uC790\uBCF8\uAE08", "\uC774\uC775\uC789\uC5EC\uAE08"],
                "single_core_mode": True,
                "single_core_support_count": 4,
            },
            risk_notes=[],
        )

        self.assertEqual(policy.get("publication_mode"), "range_only")

    def test_publication_policy_keeps_consult_only_for_very_sparse_support(self):
        policy = yangdo_blackbox_api._build_publication_policy(
            center=0.62,
            low=0.50,
            high=0.78,
            confidence_score=49.0,
            effective_cluster_count=2,
            target={
                "license_text": "\uAC15\uAD6C\uC870\uBB3C",
                "provided_signals": 2,
                "missing_critical": ["\uC790\uBCF8\uAE08", "\uC774\uC775\uC789\uC5EC\uAE08"],
                "single_core_mode": True,
                "single_core_support_count": 2,
            },
            risk_notes=[],
        )

        self.assertEqual(policy.get("publication_mode"), "consult_only")

    def test_special_sector_publication_guard_downgrades_telecom_full_when_public_range_is_too_wide(self):
        result = yangdo_blackbox_api._apply_special_sector_publication_guard(
            {
                "publication_mode": "full",
                "publication_label": "기준가 안내",
                "publication_reason": "",
                "estimate_center_eok": 0.4423,
                "estimate_low_eok": 0.05,
                "estimate_high_eok": 1.1472,
                "confidence_percent": 92,
                "risk_notes": [],
            },
            {"license_text": "정보통신", "license_tokens": {"정보통신"}},
        )

        self.assertEqual(result.get("publication_mode"), "range_only")
        self.assertEqual(result.get("publication_label"), "범위 먼저 안내")
        self.assertIn("정보통신 업종은 공개 안전도 기준상", str(result.get("publication_reason") or ""))

    def test_special_sector_publication_guard_keeps_telecom_full_when_range_is_tight_and_confident(self):
        result = yangdo_blackbox_api._apply_special_sector_publication_guard(
            {
                "publication_mode": "full",
                "publication_label": "기준가 안내",
                "publication_reason": "",
                "estimate_center_eok": 0.2799,
                "estimate_low_eok": 0.2216,
                "estimate_high_eok": 0.3409,
                "confidence_percent": 94,
                "risk_notes": [],
            },
            {"license_text": "정보통신", "license_tokens": {"정보통신"}},
        )

        self.assertEqual(result.get("publication_mode"), "full")

    def test_single_core_publication_cap_ranges_when_center_collapses(self):
        cap = yangdo_blackbox_api._single_core_publication_cap(
            center=0.48,
            target={
                "single_core_mode": True,
                "single_core_median_eok": 1.3,
                "single_core_support_count": 3,
                "single_core_dispersion_ratio": 1.1,
                "specialty": 11.0,
                "sales3_eok": None,
            },
        )

        self.assertEqual(cap.get("confidence_cap"), 66.0)
        self.assertTrue(cap.get("reason"))

    def test_single_core_publication_cap_ranges_when_support_is_thin(self):
        cap = yangdo_blackbox_api._single_core_publication_cap(
            center=0.41,
            target={
                "single_core_mode": True,
                "single_core_median_eok": 0.87,
                "single_core_support_count": 2,
                "single_core_dispersion_ratio": 1.0,
                "specialty": 15.0,
                "sales3_eok": 3.4,
            },
        )

        self.assertEqual(cap.get("confidence_cap"), 66.0)
        self.assertTrue(cap.get("reason"))

    def test_single_core_publication_cap_uses_plain_median_for_thin_support(self):
        cap = yangdo_blackbox_api._single_core_publication_cap(
            center=0.39,
            target={
                "single_core_mode": True,
                "single_core_median_eok": 0.30,
                "single_core_plain_median_eok": 0.60,
                "single_core_support_count": 2,
                "single_core_dispersion_ratio": 1.0,
                "specialty": 9.0,
                "sales3_eok": 4.2,
            },
        )

        self.assertEqual(cap.get("confidence_cap"), 66.0)
        self.assertTrue(cap.get("reason"))

    def test_single_core_publication_cap_ranges_electric_low_sales_high_dispersion(self):
        cap = yangdo_blackbox_api._single_core_publication_cap(
            center=0.35,
            target={
                "single_core_mode": True,
                "license_text": "\uC804\uAE30",
                "single_core_median_eok": 0.35,
                "single_core_plain_median_eok": 0.35,
                "single_core_support_count": 9,
                "single_core_dispersion_ratio": 2.0,
                "specialty": 12.0,
                "sales3_eok": 0.4,
            },
        )

        self.assertEqual(cap.get("confidence_cap"), 66.0)
        self.assertTrue(cap.get("reason"))

    def test_single_core_publication_cap_ranges_interior_low_scale_sparse_band(self):
        cap = yangdo_blackbox_api._single_core_publication_cap(
            center=0.62,
            target={
                "single_core_mode": True,
                "license_text": "\uC2E4\uB0B4",
                "single_core_median_eok": 0.7,
                "single_core_plain_median_eok": 0.7,
                "single_core_support_count": 3,
                "single_core_dispersion_ratio": 1.24,
                "specialty": 6.5,
                "sales3_eok": 3.7,
            },
        )

        self.assertEqual(cap.get("confidence_cap"), 66.0)
        self.assertTrue(cap.get("reason"))

    def test_single_core_publication_cap_ranges_building_sparse_mid_band(self):
        cap = yangdo_blackbox_api._single_core_publication_cap(
            center=2.15,
            target={
                "single_core_mode": True,
                "license_text": "\uAC74\uCD95",
                "single_core_median_eok": 2.25,
                "single_core_plain_median_eok": 2.45,
                "single_core_support_count": 2,
                "single_core_dispersion_ratio": 1.18,
                "specialty": 35.0,
                "sales3_eok": 33.0,
            },
        )

        self.assertEqual(cap.get("confidence_cap"), 66.0)
        self.assertTrue(cap.get("reason"))

    def test_single_core_publication_cap_ranges_building_sparse_high_band_dispersion(self):
        cap = yangdo_blackbox_api._single_core_publication_cap(
            center=2.37,
            target={
                "single_core_mode": True,
                "license_text": "\uAC74\uCD95",
                "single_core_median_eok": 0.55,
                "single_core_plain_median_eok": 1.4,
                "single_core_support_count": 2,
                "single_core_dispersion_ratio": 4.09,
                "specialty": 110.0,
                "sales3_eok": 70.0,
            },
        )

        self.assertEqual(cap.get("confidence_cap"), 66.0)
        self.assertTrue(cap.get("reason"))

    def test_single_core_publication_cap_ranges_when_dispersion_is_high(self):
        cap = yangdo_blackbox_api._single_core_publication_cap(
            center=0.92,
            target={
                "single_core_mode": True,
                "single_core_median_eok": 0.7,
                "single_core_support_count": 7,
                "single_core_dispersion_ratio": 2.4,
                "specialty": None,
                "sales3_eok": 114.0,
            },
        )

        self.assertEqual(cap.get("confidence_cap"), 66.0)
        self.assertTrue(cap.get("reason"))

    def test_infer_balance_pass_through_has_minimum_floor(self):
        info = self.est._infer_balance_pass_through(
            [
                (92.0, {"balance_eok": 1.0, "current_price_eok": 2.9}),
                (90.0, {"balance_eok": 2.0, "current_price_eok": 3.1}),
                (88.0, {"balance_eok": 3.0, "current_price_eok": 3.3}),
                (86.0, {"balance_eok": 4.0, "current_price_eok": 3.5}),
            ]
        )

        self.assertGreaterEqual(float(info.get("slope") or 0.0), 0.90)

    def test_feature_anchor_uses_core_price_not_total_price(self):
        anchor = self.est._build_feature_anchor(
            target={"specialty": 15.0, "sales3_eok": 15.0, "balance_eok": 1.0},
            neighbors=[
                (96.0, {"current_price_eok": 4.8, "balance_eok": 1.8, "specialty": 15.0, "sales3_eok": 15.0}),
                (94.0, {"current_price_eok": 4.9, "balance_eok": 1.9, "specialty": 15.5, "sales3_eok": 15.5}),
                (92.0, {"current_price_eok": 4.7, "balance_eok": 1.7, "specialty": 14.5, "sales3_eok": 14.5}),
            ],
            balance_slope=1.0,
            balance_excluded=False,
        )

        self.assertLess(float(anchor.get("anchor") or 0.0), 3.6)

    def test_sparse_core_guard_pulls_center_toward_lower_side(self):
        center, low, high = self.est._apply_sparse_core_guard(
            center=4.2,
            low=3.0,
            high=6.6,
            prices=[2.7, 2.9, 3.1],
            sims=[96.0, 94.0, 92.0],
            effective_cluster_count=2,
            target={"single_core_mode": True, "provided_signals": 3},
            notes=[],
        )

        self.assertLess(center, 4.0)
        self.assertLess(high, 6.0)

    def test_estimate_decomposes_core_and_balance_with_strong_pass_through(self):
        records = [
            self._record(uid=7001, specialty=14.0, sales3=14.2, balance=0.4, price=3.42, row=1),
            self._record(uid=7002, specialty=14.8, sales3=14.7, balance=0.5, price=3.50, row=2),
            self._record(uid=7003, specialty=15.2, sales3=15.1, balance=0.6, price=3.61, row=3),
            self._record(uid=7004, specialty=15.7, sales3=15.6, balance=0.7, price=3.69, row=4),
            self._record(uid=7005, specialty=15.0, sales3=15.0, balance=0.55, price=3.56, row=5),
            self._record(uid=7006, specialty=14.6, sales3=14.4, balance=0.45, price=3.46, row=6),
        ]
        self._prime_estimator(records)
        original_collapse = yangdo_blackbox_api.collapse_duplicate_neighbors
        try:
            yangdo_blackbox_api.collapse_duplicate_neighbors = lambda neighbors: {
                "collapsed_neighbors": list(neighbors),
                "raw_neighbor_count": len(list(neighbors)),
                "effective_cluster_count": len(list(neighbors)),
                "cluster_count": len(list(neighbors)),
                "duplicate_cluster_adjusted": False,
                "clusters": [],
            }
            out1 = self.est.estimate(
                {
                    "license_text": "토목",
                    "specialty": 15.0,
                    "sales3_eok": 15.0,
                    "sales5_eok": 20.0,
                    "balance_eok": 0.5,
                    "capital_eok": 3.0,
                    "surplus_eok": 0.4,
                    "license_year": 2016,
                    "debt_ratio": 70.0,
                    "liq_ratio": 220.0,
                    "company_type": "주식회사",
                    "credit_level": "보통",
                    "admin_history": "없음",
                }
            )
            out2 = self.est.estimate(
                {
                    "license_text": "토목",
                    "specialty": 15.0,
                    "sales3_eok": 15.0,
                    "sales5_eok": 20.0,
                    "balance_eok": 1.5,
                    "capital_eok": 3.0,
                    "surplus_eok": 0.4,
                    "license_year": 2016,
                    "debt_ratio": 70.0,
                    "liq_ratio": 220.0,
                    "company_type": "주식회사",
                    "credit_level": "보통",
                    "admin_history": "없음",
                }
            )
        finally:
            yangdo_blackbox_api.collapse_duplicate_neighbors = original_collapse

        total1 = float(out1.get("core_estimate_eok") or 0.0) + float(out1.get("balance_adjustment_eok") or 0.0)
        total2 = float(out2.get("core_estimate_eok") or 0.0) + float(out2.get("balance_adjustment_eok") or 0.0)

        self.assertTrue(out1.get("base_model_applied"))
        self.assertGreaterEqual(float(out1.get("balance_pass_through") or 0.0), 0.90)
        self.assertGreaterEqual(float(out1.get("balance_adjustment_eok") or 0.0), 0.45)
        self.assertGreater(total1, float(out1.get("core_estimate_eok") or 0.0))
        self.assertGreaterEqual(total2 - total1, 0.90)
        self.assertLessEqual(total2 - total1, 1.10)

    def test_display_neighbors_prioritize_7000_band_when_sales_are_comparable(self):
        target = self.est._target_from_payload(
            {
                "license_text": "\uD1A0\uBAA9",
                "specialty": 20.0,
                "sales3_eok": 15.0,
                "sales5_eok": 20.0,
                "capital_eok": 3.0,
                "balance_eok": 0.6,
            }
        )
        rows = [
            (99.0, self._record(uid=5201, specialty=20.0, sales3=15.0, balance=0.6, price=2.88, license_text="\uD1A0\uBAA9", row=1)),
            (98.0, self._record(uid=6201, specialty=20.5, sales3=15.2, balance=0.6, price=2.94, license_text="\uD1A0\uBAA9", row=2)),
            (96.0, self._record(uid=7201, specialty=19.8, sales3=15.1, balance=0.7, price=3.02, license_text="\uD1A0\uBAA9", row=3)),
            (97.0, self._record(uid=7208, specialty=21.0, sales3=16.0, balance=0.6, price=3.08, license_text="\uD1A0\uBAA9", row=4)),
        ]

        prioritized = yangdo_blackbox_api._prioritize_display_neighbors(target, rows)

        self.assertEqual(int(prioritized[0][1].get("number") or 0), 7208)
        self.assertEqual(int(prioritized[1][1].get("number") or 0), 7201)

    def test_display_neighbors_fall_back_to_6000_when_7000_sales_fit_is_weak(self):
        target = self.est._target_from_payload(
            {
                "license_text": "\uD1A0\uBAA9",
                "specialty": 20.0,
                "sales3_eok": 15.0,
                "sales5_eok": 20.0,
                "capital_eok": 3.0,
                "balance_eok": 0.6,
            }
        )
        rows = [
            (99.0, self._record(uid=5201, specialty=20.0, sales3=15.0, balance=0.6, price=2.88, license_text="\uD1A0\uBAA9", row=1)),
            (97.0, self._record(uid=6201, specialty=20.5, sales3=15.2, balance=0.6, price=2.94, license_text="\uD1A0\uBAA9", row=2)),
            (98.5, self._record(uid=7201, specialty=22.0, sales3=26.0, balance=0.7, price=3.35, license_text="\uD1A0\uBAA9", row=3)),
            (98.0, self._record(uid=7208, specialty=21.5, sales3=27.0, balance=0.7, price=3.42, license_text="\uD1A0\uBAA9", row=4)),
        ]

        prioritized = yangdo_blackbox_api._prioritize_display_neighbors(target, rows)

        self.assertEqual(int(prioritized[0][1].get("number") or 0), 6201)

    def test_recommended_listings_prioritize_7000_band_when_profile_is_similar(self):
        target = self.est._target_from_payload(
            {
                "license_text": "\uD1A0\uBAA9",
                "specialty": 20.0,
                "sales3_eok": 15.0,
                "sales5_eok": 20.0,
                "balance_eok": 0.6,
                "capital_eok": 3.0,
                "company_type": "\uC8FC\uC2DD\uD68C\uC0AC",
            }
        )
        rows = [
            (99.0, self._record(uid=5201, specialty=20.0, sales3=15.0, balance=0.6, price=2.88, license_text="\uD1A0\uBAA9", row=1)),
            (98.0, self._record(uid=6201, specialty=20.5, sales3=15.2, balance=0.6, price=2.94, license_text="\uD1A0\uBAA9", row=2)),
            (96.0, self._record(uid=7201, specialty=19.8, sales3=15.1, balance=0.7, price=3.02, license_text="\uD1A0\uBAA9", row=3)),
            (97.0, self._record(uid=7208, specialty=21.0, sales3=16.0, balance=0.6, price=3.08, license_text="\uD1A0\uBAA9", row=4)),
        ]

        recs = yangdo_blackbox_api._build_recommended_listings(
            target=target,
            rows=rows,
            center=3.0,
            low=2.8,
            high=3.2,
            limit=3,
        )

        self.assertEqual(int(recs[0].get("seoul_no") or 0), 7208)
        self.assertTrue(any("\uBE44\uC2B7" in str(x) for x in list(recs[0].get("reasons") or [])))

    def test_recommended_listings_fall_back_to_6000_when_7000_fit_is_weak(self):
        target = self.est._target_from_payload(
            {
                "license_text": "\uD1A0\uBAA9",
                "specialty": 20.0,
                "sales3_eok": 15.0,
                "sales5_eok": 20.0,
                "balance_eok": 0.6,
                "capital_eok": 3.0,
                "company_type": "\uC8FC\uC2DD\uD68C\uC0AC",
            }
        )
        rows = [
            (99.0, self._record(uid=5201, specialty=20.0, sales3=15.0, balance=0.6, price=2.88, license_text="\uD1A0\uBAA9", row=1)),
            (97.0, self._record(uid=6201, specialty=20.5, sales3=15.2, balance=0.6, price=2.94, license_text="\uD1A0\uBAA9", row=2)),
            (98.5, self._record(uid=7201, specialty=22.0, sales3=26.0, balance=0.7, price=3.35, license_text="\uD1A0\uBAA9", row=3)),
            (98.0, self._record(uid=7208, specialty=21.5, sales3=27.0, balance=0.7, price=3.42, license_text="\uD1A0\uBAA9", row=4)),
        ]

        recs = yangdo_blackbox_api._build_recommended_listings(
            target=target,
            rows=rows,
            center=2.95,
            low=2.8,
            high=3.1,
            limit=3,
        )

        self.assertEqual(int(recs[0].get("seoul_no") or 0), 6201)

    def test_special_balance_usage_defaults_to_none(self):
        target = self.est._target_from_payload(
            {
                "license_text": "\uC804\uAE30",
                "reorg_mode": "\uD3EC\uAD04",
                "balance_eok": 0.5,
                "capital_eok": 3.0,
                "sales3_eok": 9.0,
            }
        )

        self.assertEqual(target.get("balance_usage_mode_requested"), "")
        self.assertEqual(target.get("balance_usage_mode"), "loan_withdrawal")
        self.assertTrue(target.get("seller_withdraws_guarantee_loan"))
        self.assertFalse(target.get("buyer_takes_balance_as_credit"))
        self.assertAlmostEqual(float(target.get("input_balance_eok") or 0.0), 0.5, places=9)

    def test_special_sector_estimate_keeps_balance_separate_even_when_credit_transfer_requested(self):
        electric = "\uC804\uAE30"
        records = [
            self._record(uid=9101, specialty=14.0, sales3=8.5, balance=0.5, price=1.72, license_text=electric, row=1),
            self._record(uid=9102, specialty=18.0, sales3=10.2, balance=0.7, price=1.94, license_text=electric, row=2),
            self._record(uid=9103, specialty=22.0, sales3=12.4, balance=0.8, price=2.18, license_text=electric, row=3),
            self._record(uid=9104, specialty=27.0, sales3=15.1, balance=0.9, price=2.41, license_text=electric, row=4),
        ]
        self._prime_estimator(records)

        out = self.est.estimate(
            {
                "license_text": electric,
                "reorg_mode": "\uD3EC\uAD04",
                "balance_usage_mode": "credit_transfer",
                "specialty": 20.0,
                "sales3_eok": 11.0,
                "sales5_eok": 16.5,
                "balance_eok": 0.8,
                "capital_eok": 3.0,
                "surplus_eok": 0.4,
                "company_type": "\uC8FC\uC2DD\uD68C\uC0AC",
            }
        )

        self.assertTrue(out.get("ok"))
        self.assertTrue(out.get("balance_excluded"))
        self.assertEqual(out.get("balance_usage_mode_requested"), "credit_transfer")
        self.assertEqual(out.get("balance_usage_mode"), "credit_transfer")
        self.assertAlmostEqual(float(out.get("realizable_balance_eok") or 0.0), 0.8, places=6)
        self.assertAlmostEqual(
            float(out.get("estimated_cash_due_eok") or 0.0),
            float(out.get("total_transfer_value_eok") or 0.0) - 0.8,
            places=6,
        )
        self.assertEqual(str((out.get("settlement_breakdown") or {}).get("model") or ""), "credit_transfer")
        policy = out.get("settlement_policy") or {}
        self.assertEqual(str(policy.get("sector") or ""), electric)
        self.assertEqual(str(policy.get("auto_mode") or ""), "loan_withdrawal")
        scenarios = out.get("settlement_scenarios") or []
        self.assertEqual(len(scenarios), 3)
        self.assertEqual([str(x.get("input_mode") or "") for x in scenarios], ["auto", "credit_transfer", "none"])
        selected = [x for x in scenarios if x.get("is_selected")]
        self.assertEqual(len(selected), 1)
        self.assertEqual(str(selected[0].get("input_mode") or ""), "credit_transfer")
        self.assertEqual(str(selected[0].get("resolved_mode") or ""), "credit_transfer")

    def test_special_sector_estimate_keeps_balance_separate_in_auto_mode(self):
        telecom = "\uC815\uBCF4\uD1B5\uC2E0"
        records = [
            self._record(uid=9301, specialty=11.0, sales3=6.4, balance=0.3, price=0.96, license_text=telecom, row=1),
            self._record(uid=9302, specialty=14.0, sales3=7.5, balance=0.4, price=1.08, license_text=telecom, row=2),
            self._record(uid=9303, specialty=16.0, sales3=8.1, balance=0.5, price=1.15, license_text=telecom, row=3),
            self._record(uid=9304, specialty=19.0, sales3=9.2, balance=0.6, price=1.26, license_text=telecom, row=4),
        ]
        self._prime_estimator(records)

        out = self.est.estimate(
            {
                "license_text": telecom,
                "reorg_mode": "\uD3EC\uAD04",
                "balance_usage_mode": "auto",
                "specialty": 15.0,
                "sales3_eok": 8.0,
                "sales5_eok": 12.8,
                "balance_eok": 0.5,
                "capital_eok": 3.0,
                "surplus_eok": 0.2,
                "company_type": "\uC8FC\uC2DD\uD68C\uC0AC",
            }
        )

        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("balance_usage_mode_requested"), "auto")
        self.assertEqual(out.get("balance_usage_mode"), "loan_withdrawal")
        scenarios = out.get("settlement_scenarios") or []
        self.assertEqual(len(scenarios), 3)
        auto_row = next((x for x in scenarios if str(x.get("input_mode") or "") == "auto"), {})
        self.assertTrue(auto_row.get("is_selected"))
        self.assertTrue(auto_row.get("is_recommended"))
        self.assertEqual(str(auto_row.get("resolved_mode") or ""), "loan_withdrawal")
        self.assertAlmostEqual(float(auto_row.get("realizable_balance_eok") or 0.0), 0.3, places=6)

    def test_telecom_auto_mode_drops_to_none_when_balance_share_is_below_data_cutoff(self):
        telecom = "\uC815\uBCF4\uD1B5\uC2E0"
        records = [
            self._record(uid=9311, specialty=11.0, sales3=6.4, balance=0.3, price=0.96, license_text=telecom, row=1),
            self._record(uid=9312, specialty=14.0, sales3=7.5, balance=0.4, price=1.08, license_text=telecom, row=2),
            self._record(uid=9313, specialty=16.0, sales3=8.1, balance=0.5, price=1.15, license_text=telecom, row=3),
            self._record(uid=9314, specialty=19.0, sales3=9.2, balance=0.6, price=1.26, license_text=telecom, row=4),
        ]
        self._prime_estimator(records)

        out = self.est.estimate(
            {
                "license_text": telecom,
                "reorg_mode": "\uD3EC\uAD04",
                "balance_usage_mode": "auto",
                "specialty": 15.0,
                "sales3_eok": 8.0,
                "sales5_eok": 12.8,
                "balance_eok": 0.06,
                "capital_eok": 3.0,
                "surplus_eok": 0.2,
                "company_type": "\uC8FC\uC2DD\uD68C\uC0AC",
            }
        )

        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("balance_usage_mode_requested"), "auto")
        self.assertEqual(out.get("balance_usage_mode"), "none")
        policy = out.get("settlement_policy") or {}
        self.assertEqual(str(policy.get("resolved_auto_mode") or ""), "none")
        self.assertAlmostEqual(float(policy.get("min_auto_balance_share") or 0.0), 0.0625, places=6)
        self.assertAlmostEqual(float(policy.get("min_auto_balance_eok") or 0.0), 0.025, places=6)
        scenarios = out.get("settlement_scenarios") or []
        auto_row = next((x for x in scenarios if str(x.get("input_mode") or "") == "auto"), {})
        self.assertTrue(auto_row.get("is_selected"))
        self.assertEqual(str(auto_row.get("resolved_mode") or ""), "none")
        self.assertAlmostEqual(float(auto_row.get("realizable_balance_eok") or 0.0), 0.0, places=6)

    def test_fire_auto_mode_drops_to_none_when_balance_share_is_tiny(self):
        fire = "\uC18C\uBC29"
        records = [
            self._record(uid=9401, specialty=10.0, sales3=5.4, balance=0.05, price=0.82, license_text=fire, row=1),
            self._record(uid=9402, specialty=11.0, sales3=5.9, balance=0.06, price=0.88, license_text=fire, row=2),
            self._record(uid=9403, specialty=12.0, sales3=6.3, balance=0.07, price=0.95, license_text=fire, row=3),
            self._record(uid=9404, specialty=13.0, sales3=6.7, balance=0.08, price=1.02, license_text=fire, row=4),
        ]
        self._prime_estimator(records)

        out = self.est.estimate(
            {
                "license_text": fire,
                "reorg_mode": "\uD3EC\uAD04",
                "balance_usage_mode": "auto",
                "specialty": 11.0,
                "sales3_eok": 6.0,
                "sales5_eok": 9.4,
                "balance_eok": 0.05,
                "capital_eok": 3.0,
                "surplus_eok": 0.2,
                "company_type": "\uC8FC\uC2DD\uD68C\uC0AC",
            }
        )

        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("balance_usage_mode_requested"), "auto")
        self.assertEqual(out.get("balance_usage_mode"), "none")
        policy = out.get("settlement_policy") or {}
        self.assertEqual(str(policy.get("resolved_auto_mode") or ""), "none")
        self.assertIn("별도 정산 없음", str(policy.get("auto_decision_reason") or ""))
        scenarios = out.get("settlement_scenarios") or []
        self.assertEqual(len(scenarios), 3)
        auto_row = next((x for x in scenarios if str(x.get("input_mode") or "") == "auto"), {})
        self.assertTrue(auto_row.get("is_selected"))
        self.assertEqual(str(auto_row.get("input_mode") or ""), "auto")
        self.assertEqual(str(auto_row.get("resolved_mode") or ""), "none")

    def test_fire_split_auto_policy_uses_conservative_cutoffs(self):
        fire = "\uC18C\uBC29"
        records = [
            self._record(uid=9411, specialty=10.0, sales3=5.4, balance=0.05, price=0.82, license_text=fire, row=1),
            self._record(uid=9412, specialty=11.0, sales3=5.9, balance=0.06, price=0.88, license_text=fire, row=2),
            self._record(uid=9413, specialty=12.0, sales3=6.3, balance=0.07, price=0.95, license_text=fire, row=3),
            self._record(uid=9414, specialty=13.0, sales3=6.7, balance=0.08, price=1.02, license_text=fire, row=4),
        ]
        self._prime_estimator(records)

        out = self.est.estimate(
            {
                "license_text": fire,
                "reorg_mode": "\uBD84\uD560/\uD569\uBCD1",
                "balance_usage_mode": "auto",
                "specialty": 11.0,
                "sales3_eok": 6.0,
                "sales5_eok": 9.4,
                "balance_eok": 0.09,
                "capital_eok": 3.0,
                "surplus_eok": 0.2,
                "company_type": "\uC8FC\uC2DD\uD68C\uC0AC",
            }
        )

        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("balance_usage_mode_requested"), "auto")
        self.assertEqual(out.get("balance_usage_mode"), "none")
        policy = out.get("settlement_policy") or {}
        self.assertAlmostEqual(float(policy.get("min_auto_balance_share") or 0.0), 0.1758, places=6)
        self.assertAlmostEqual(float(policy.get("min_auto_balance_eok") or 0.0), 0.09, places=6)
        self.assertEqual(str(policy.get("resolved_auto_mode") or ""), "none")

    def test_non_special_sector_estimate_exposes_embedded_balance_settlement(self):
        civil = "\uD1A0\uBAA9"
        records = [
            self._record(uid=9201, specialty=18.0, sales3=11.0, balance=0.4, price=2.22, license_text=civil, row=1),
            self._record(uid=9202, specialty=19.5, sales3=12.2, balance=0.5, price=2.34, license_text=civil, row=2),
            self._record(uid=9203, specialty=21.0, sales3=13.4, balance=0.6, price=2.52, license_text=civil, row=3),
            self._record(uid=9204, specialty=22.0, sales3=14.1, balance=0.6, price=2.66, license_text=civil, row=4),
        ]
        self._prime_estimator(records)

        out = self.est.estimate(
            {
                "license_text": civil,
                "specialty": 20.0,
                "sales3_eok": 12.0,
                "sales5_eok": 17.0,
                "balance_eok": 0.6,
                "capital_eok": 3.0,
                "surplus_eok": 0.4,
                "company_type": "\uC8FC\uC2DD\uD68C\uC0AC",
            }
        )

        self.assertTrue(out.get("ok"))
        self.assertFalse(out.get("balance_excluded"))
        self.assertEqual(out.get("balance_usage_mode_requested"), "")
        self.assertEqual(out.get("balance_usage_mode"), "embedded_balance")
        self.assertGreater(float(out.get("realizable_balance_eok") or 0.0), 0.5)
        self.assertAlmostEqual(
            float(out.get("estimated_cash_due_eok") or 0.0),
            max(
                0.0,
                float(out.get("total_transfer_value_eok") or 0.0) - float(out.get("realizable_balance_eok") or 0.0),
            ),
            places=6,
        )
        self.assertEqual(out.get("settlement_scenarios") or [], [])
        self.assertEqual(str((out.get("settlement_policy") or {}).get("sector") or ""), "")


class SpecialBalanceAutoPoliciesTest(unittest.TestCase):
    """Verify all special sectors have required params (JS/Python parity)."""

    def test_electric_has_min_balance_params(self):
        policy = yangdo_blackbox_api._SPECIAL_BALANCE_AUTO_POLICIES["전기"]
        self.assertAlmostEqual(policy["min_auto_balance_share"], 0.10)
        self.assertAlmostEqual(policy["min_auto_balance_eok"], 0.05)

    def test_electric_has_reorg_overrides(self):
        policy = yangdo_blackbox_api._SPECIAL_BALANCE_AUTO_POLICIES["전기"]
        overrides = policy["reorg_overrides"]["분할/합병"]
        self.assertAlmostEqual(overrides["min_auto_balance_share"], 0.105)
        self.assertAlmostEqual(overrides["min_auto_balance_eok"], 0.05)

    def test_telecom_has_min_balance_params(self):
        policy = yangdo_blackbox_api._SPECIAL_BALANCE_AUTO_POLICIES["정보통신"]
        self.assertAlmostEqual(policy["min_auto_balance_share"], 0.0625)
        self.assertAlmostEqual(policy["min_auto_balance_eok"], 0.025)

    def test_telecom_has_reorg_overrides(self):
        policy = yangdo_blackbox_api._SPECIAL_BALANCE_AUTO_POLICIES["정보통신"]
        overrides = policy["reorg_overrides"]["분할/합병"]
        self.assertAlmostEqual(overrides["min_auto_balance_share"], 0.065)
        self.assertAlmostEqual(overrides["min_auto_balance_eok"], 0.025)

    def test_fire_has_min_balance_params(self):
        policy = yangdo_blackbox_api._SPECIAL_BALANCE_AUTO_POLICIES["소방"]
        self.assertAlmostEqual(policy["min_auto_balance_share"], 0.17)
        self.assertAlmostEqual(policy["min_auto_balance_eok"], 0.09)

    def test_fire_has_reorg_overrides(self):
        policy = yangdo_blackbox_api._SPECIAL_BALANCE_AUTO_POLICIES["소방"]
        overrides = policy["reorg_overrides"]["분할/합병"]
        self.assertAlmostEqual(overrides["min_auto_balance_share"], 0.1758)
        self.assertAlmostEqual(overrides["min_auto_balance_eok"], 0.09)

    def test_all_special_sectors_present(self):
        policies = yangdo_blackbox_api._SPECIAL_BALANCE_AUTO_POLICIES
        for sector in ("전기", "정보통신", "소방"):
            self.assertIn(sector, policies, f"{sector} missing from special balance policies")
            self.assertIn("min_auto_balance_share", policies[sector], f"{sector} missing min_auto_balance_share")
            self.assertIn("min_auto_balance_eok", policies[sector], f"{sector} missing min_auto_balance_eok")
            self.assertIn("reorg_overrides", policies[sector], f"{sector} missing reorg_overrides")


if __name__ == "__main__":
    unittest.main()
