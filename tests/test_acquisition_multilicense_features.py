import unittest

import acquisition_calculator


class AcquisitionMultiLicenseFeatureTest(unittest.TestCase):
    def test_multilicense_and_major_field_blocks_exist(self):
        html = acquisition_calculator.build_page_html()
        self.assertIn('id="acq-license-extra-wrap"', html)
        self.assertIn('id="acq-license-extra-list"', html)
        self.assertIn('id="acq-major-field-wrap"', html)
        self.assertIn('id="acq-corp-state"', html)
        self.assertIn('id="acq-region-text"', html)
        self.assertIn('id="acq-region-override"', html)
        self.assertIn('id="acq-region-result"', html)
        self.assertIn('법인 상태', html)
        self.assertIn('중과세 자동판정', html)
        self.assertNotIn('id="acq-license-class"', html)
        self.assertNotIn('id="acq-corp-reg-type"', html)
        self.assertNotIn('법인 등기 유형', html)

    def test_special_rule_logic_markers_exist(self):
        html = acquisition_calculator.build_page_html()
        self.assertIn('calcCapitalSpecialCreditMeta', html)
        self.assertIn('calcInterLicenseTechCredit', html)
        self.assertIn('calcDiagnosisLawMeta', html)
        self.assertIn('buildLicenseBundle', html)
        self.assertIn('inferRegionStatus', html)
        self.assertIn('syncRegionInference', html)
        self.assertIn('taxSurchargeMultiplier', html)
        self.assertIn('admin_fee_extra_license_count', html)
        self.assertIn('capital_special_general_special_credit_eok', html)
        self.assertIn('engineer_inter_general_special_credit', html)
        self.assertIn('ensureViewModeBar', html)
        self.assertIn('applyViewMode', html)
        self.assertIn('renderMidSettlement', html)


if __name__ == '__main__':
    unittest.main()
