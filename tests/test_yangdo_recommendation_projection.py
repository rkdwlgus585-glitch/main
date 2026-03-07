import unittest
from types import SimpleNamespace

import yangdo_blackbox_api


class _FakeGateway:
    def __init__(self, features=None):
        self._features = set(features or [])

    def check_feature(self, resolution, feature):
        return feature in self._features

    def check_system(self, resolution, system):
        return True


class YangdoRecommendationProjectionTests(unittest.TestCase):
    def setUp(self):
        self.est = yangdo_blackbox_api.YangdoBlackboxEstimator()

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
                "years": {
                    "y23": round(sales3 * 0.30, 4),
                    "y24": round(sales3 * 0.33, 4),
                    "y25": round(sales3 * 0.37, 4),
                },
            }
        )
        return base

    def test_recommendation_result_exposes_precision_metadata(self):
        target = self.est._target_from_payload(
            {
                "license_text": "토목",
                "specialty": 20.0,
                "sales3_eok": 15.0,
                "sales5_eok": 20.0,
                "balance_eok": 0.6,
                "capital_eok": 3.0,
                "company_type": "주식회사",
            }
        )
        rows = [
            (99.0, self._record(uid=5201, specialty=20.0, sales3=15.0, balance=0.6, price=2.88, row=1)),
            (98.0, self._record(uid=6201, specialty=20.5, sales3=15.2, balance=0.6, price=2.94, row=2)),
            (96.0, self._record(uid=7201, specialty=19.8, sales3=15.1, balance=0.7, price=3.02, row=3)),
            (97.0, self._record(uid=7208, specialty=21.0, sales3=16.0, balance=0.6, price=3.08, row=4)),
        ]

        result = yangdo_blackbox_api._build_recommendation_result(
            target=target,
            rows=rows,
            center=3.0,
            low=2.8,
            high=3.2,
            limit=3,
        )

        self.assertIn("recommended_listings", result)
        self.assertIn("recommendation_meta", result)
        self.assertEqual(int(result["recommended_listings"][0].get("seoul_no") or 0), 7208)
        top = result["recommended_listings"][0]
        self.assertTrue(top.get("recommendation_focus"))
        self.assertTrue(top.get("fit_summary"))
        self.assertIn("precision_tier", top)
        self.assertTrue(isinstance(top.get("matched_axes"), list))
        meta = result["recommendation_meta"]
        self.assertEqual(meta.get("recommendation_version"), "listing_recommender_v2")
        self.assertGreaterEqual(int(meta.get("recommended_count") or 0), 1)

    def test_summary_projection_keeps_recommendation_summary_only(self):
        server = SimpleNamespace(
            tenant_gateway_enabled=True,
            tenant_gateway=_FakeGateway(features=[]),
        )
        resolution = SimpleNamespace(
            tenant=SimpleNamespace(plan="standard", tenant_id="tenant_standard"),
        )
        result = {
            "ok": True,
            "generated_at": "2026-03-07T10:00:00",
            "estimate_center_eok": 3.0,
            "estimate_low_eok": 2.8,
            "estimate_high_eok": 3.2,
            "confidence_score": 74.0,
            "confidence_percent": 74,
            "publication_mode": "full",
            "publication_label": "기준가+범위",
            "publication_reason": "",
            "price_source_tier": "B",
            "price_source_label": "비교 자료 보통",
            "price_sample_count": 6,
            "price_is_estimate": True,
            "price_range_kind": "AI_ESTIMATED_RANGE",
            "price_source_channel": "SHARED_MARKET_LISTING_DATASET",
            "price_disclaimer": "참고용 가격입니다.",
            "recommendation_meta": {
                "recommendation_version": "listing_recommender_v2",
                "recommended_count": 2,
                "precision_mode": "balanced",
            },
            "recommended_listings": [
                {
                    "seoul_no": 7208,
                    "license_text": "토목",
                    "display_low_eok": 2.9,
                    "display_high_eok": 3.1,
                    "recommendation_label": "우선 검토",
                    "recommendation_focus": "면허 일치, 실적 규모, 가격대",
                    "recommendation_score": 88.1,
                    "reasons": ["면허 구성이 같습니다", "최근 실적 규모가 비슷합니다"],
                    "url": "https://seoulmna.co.kr/mna/7208",
                }
            ],
            "neighbors": [{"seoul_no": 1}],
        }

        projected = yangdo_blackbox_api._project_estimate_result(server, resolution, result)

        self.assertIn("recommended_listings", projected)
        self.assertIn("recommendation_meta", projected)
        self.assertNotIn("neighbors", projected)
        first = projected["recommended_listings"][0]
        self.assertIn("recommendation_focus", first)
        self.assertNotIn("recommendation_score", first)
        self.assertNotIn("recommendation_focus_signature", first)
        self.assertNotIn("recommendation_price_band", first)

    def test_detail_projection_hides_internal_recommendation_fields(self):
        server = SimpleNamespace(
            tenant_gateway_enabled=True,
            tenant_gateway=_FakeGateway(features=["estimate_detail"]),
        )
        resolution = SimpleNamespace(
            tenant=SimpleNamespace(plan="pro", tenant_id="tenant_pro"),
        )
        result = {
            "ok": True,
            "generated_at": "2026-03-07T10:00:00",
            "estimate_center_eok": 3.0,
            "estimate_low_eok": 2.8,
            "estimate_high_eok": 3.2,
            "confidence_score": 74.0,
            "confidence_percent": 74,
            "publication_mode": "full",
            "publication_label": "기준가+범위",
            "publication_reason": "",
            "price_source_tier": "B",
            "price_source_label": "비교 자료 보통",
            "price_sample_count": 6,
            "price_is_estimate": True,
            "price_range_kind": "AI_ESTIMATED_RANGE",
            "price_source_channel": "SHARED_MARKET_LISTING_DATASET",
            "price_disclaimer": "참고용 가격입니다.",
            "recommendation_meta": {
                "recommendation_version": "listing_recommender_v2",
                "recommended_count": 1,
                "precision_mode": "balanced",
                "diversity_mode": "top1_locked_spread_v1",
                "unique_price_band_count": 1,
                "unique_focus_signature_count": 1,
                "unique_precision_tier_count": 1,
            },
            "recommended_listings": [
                {
                    "seoul_no": 7208,
                    "license_text": "토목",
                    "price_eok": 3.0,
                    "display_low_eok": 2.9,
                    "display_high_eok": 3.1,
                    "sales3_eok": 15.2,
                    "recommendation_label": "우선 검토",
                    "recommendation_focus": "면허 일치, 실적 규모, 가격대",
                    "recommendation_score": 88.1,
                    "precision_tier": "high",
                    "reasons": ["면허 구성이 같습니다", "최근 실적 규모가 비슷합니다"],
                    "fit_summary": "면허 일치와 가격대가 맞습니다.",
                    "matched_axes": ["면허 일치", "실적 규모", "가격대"],
                    "mismatch_flags": [],
                    "recommendation_focus_signature": "면허 일치|실적 규모",
                    "recommendation_price_band": "3_to_4",
                    "similarity": 98.2,
                    "url": "https://seoulmna.co.kr/mna/7208",
                }
            ],
            "neighbors": [{"seoul_no": 1}],
        }

        projected = yangdo_blackbox_api._project_estimate_result(server, resolution, result)

        self.assertIn("recommended_listings", projected)
        first = projected["recommended_listings"][0]
        self.assertIn("precision_tier", first)
        self.assertIn("fit_summary", first)
        self.assertNotIn("recommendation_score", first)
        self.assertNotIn("similarity", first)
        self.assertNotIn("recommendation_focus_signature", first)
        self.assertNotIn("recommendation_price_band", first)
        self.assertNotIn("neighbors", projected)


if __name__ == "__main__":
    unittest.main()
