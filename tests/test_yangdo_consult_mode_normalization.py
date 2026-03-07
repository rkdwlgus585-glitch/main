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


if __name__ == "__main__":
    unittest.main()
