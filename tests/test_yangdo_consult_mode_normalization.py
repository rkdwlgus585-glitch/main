import unittest

import yangdo_consult_api as api


class YangdoConsultModeNormalizationTest(unittest.TestCase):
    def test_permit_payload_is_canonicalized(self):
        payload = api._normalize_business_payload(
            {
                "source": "seoulmna_kr_acquisition_newreg",
                "page_mode": "acquisition",
                "subject": "인허가 사전검토 상담 요청",
            }
        )
        self.assertEqual(payload.get("page_mode"), api.CANONICAL_MODE_PERMIT)
        self.assertEqual(payload.get("source"), api.CANONICAL_SOURCE_PERMIT)
        self.assertEqual(payload.get("business_domain"), "permit_precheck")
        self.assertEqual(payload.get("service_track"), "permit_precheck_new_registration")
        self.assertEqual(payload.get("legacy_page_mode"), "acquisition")

    def test_yangdo_payload_keeps_transfer_track(self):
        payload = api._normalize_business_payload(
            {
                "source": "seoulmna_kr_yangdo_ai",
                "page_mode": "customer",
                "service_track": "transfer_price_estimation",
            }
        )
        self.assertEqual(payload.get("page_mode"), api.CANONICAL_MODE_YANGDO)
        self.assertEqual(payload.get("source"), api.CANONICAL_SOURCE_YANGDO)
        self.assertEqual(payload.get("business_domain"), "yangdo_transfer")
        self.assertEqual(payload.get("service_track"), "transfer_price_estimation")

    def test_tags_include_canonical_mode_and_service_track(self):
        tags = api._build_tags(
            {
                "source": "seoulmna_kr_acquisition_newreg",
                "page_mode": "acquisition",
                "license_text": "전기/소방",
            }
        )
        self.assertIn(api.CANONICAL_SOURCE_PERMIT, tags)
        self.assertIn(api.CANONICAL_MODE_PERMIT, tags)
        self.assertIn("permit_precheck_new_registration", tags)

    # ── Edge cases: empty / None / unknown payloads ──

    def test_empty_payload_returns_unknown_mode(self):
        payload = api._normalize_business_payload({})
        self.assertEqual(payload["page_mode"], "unknown")
        self.assertEqual(payload["business_domain"], "yangdo_transfer")

    def test_none_payload_no_crash(self):
        payload = api._normalize_business_payload(None)
        self.assertIn("page_mode", payload)
        self.assertIn("source", payload)

    def test_unrecognized_mode_preserves_original_page_mode_and_source(self):
        payload = api._normalize_business_payload(
            {"source": "custom_partner_api", "page_mode": "custom_flow"}
        )
        # Unrecognized mode → page_mode kept as-is, source not overwritten
        self.assertEqual(payload["source"], "custom_partner_api")
        self.assertEqual(payload["page_mode"], "custom_flow")

    def test_hot_match_source_detected(self):
        payload = api._normalize_business_payload(
            {"source": "seoulmna_kr_hot_match_page"}
        )
        self.assertEqual(payload["source"], api.CANONICAL_SOURCE_HOT_MATCH)

    def test_permit_keyword_in_subject_triggers_permit_mode(self):
        payload = api._normalize_business_payload(
            {"subject": "인허가 관련 상담 요청", "page_mode": "customer"}
        )
        self.assertEqual(payload["page_mode"], api.CANONICAL_MODE_PERMIT)
        self.assertEqual(payload["legacy_page_mode"], "customer")

    def test_yangdo_keyword_in_license_text(self):
        payload = api._normalize_business_payload(
            {"license_text": "양도양수 복합면허"}
        )
        self.assertEqual(payload["page_mode"], api.CANONICAL_MODE_YANGDO)

    def test_service_track_preserved_when_provided(self):
        payload = api._normalize_business_payload(
            {"service_track": "custom_track", "page_mode": "customer", "source": "seoulmna_kr_yangdo_ai"}
        )
        self.assertEqual(payload["service_track"], "custom_track")

    def test_legacy_fields_not_set_when_same(self):
        """legacy_page_mode should not appear if mode == original page_mode."""
        payload = api._normalize_business_payload(
            {"page_mode": "yangdo_calculator", "source": "seoulmna_kr_yangdo_ai"}
        )
        # page_mode is already yangdo_calculator, so no legacy
        self.assertNotIn("legacy_page_mode", payload)

    def test_tags_empty_payload_no_crash(self):
        tags = api._build_tags({})
        self.assertIsInstance(tags, list)

    def test_tags_deduplicate_none_values(self):
        tags = api._build_tags({"license_text": None, "source": None})
        # Should not contain None or "None" strings
        for tag in tags:
            self.assertNotEqual(tag, "None")
            self.assertIsNotNone(tag)


if __name__ == "__main__":
    unittest.main()
