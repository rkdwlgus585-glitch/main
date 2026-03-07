import unittest

import acquisition_calculator


class AcquisitionDomainSeparationTest(unittest.TestCase):
    def test_permit_track_markers_are_embedded(self):
        html = acquisition_calculator.build_page_html()
        self.assertIn("permit_precheck_new_registration", html)
        self.assertIn("page_mode: PERMIT_PAGE_MODE", html)
        self.assertIn("legacy_page_mode: LEGACY_PAGE_MODE", html)
        self.assertIn("양도양수 산정 계산기와 별도 운영", html)
        self.assertIn("신규등록(인허가) 전용", html)


if __name__ == "__main__":
    unittest.main()
