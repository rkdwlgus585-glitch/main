import unittest
from unittest.mock import Mock, patch

from scripts.verify_calculator_runtime import _check_static, _runtime_frame_tokens


class VerifyCalculatorRuntimeTests(unittest.TestCase):
    @patch("scripts.verify_calculator_runtime.requests.get")
    def test_check_static_accepts_any_marker_variant(self, mock_get):
        response = Mock()
        response.status_code = 200
        response.text = '<div id="smna-calc-bridge"></div><!-- SMNA_WIDGET_BRIDGE_CUSTOMER -->'
        mock_get.return_value = response
        out = _check_static(
            "https://example.com/page",
            ["smna-calc-bridge"],
            require_any=["mountCalculatorBridge", "SMNA_WIDGET_BRIDGE_CUSTOMER"],
        )
        self.assertTrue(out["ok"])
        self.assertTrue(out["found_any"]["SMNA_WIDGET_BRIDGE_CUSTOMER"])

    def test_runtime_frame_tokens_follow_actual_query(self):
        out = _runtime_frame_tokens(
            "https://calc.seoulmna.co.kr/widgets/permit?tenant_id=seoul_main&from=co&mode=acquisition",
            "acquisition",
        )
        self.assertIn("https://calc.seoulmna.co.kr/widgets/permit", out)
        self.assertIn("tenant_id=seoul_main", out)
        self.assertIn("from=co", out)
        self.assertIn("mode=acquisition", out)


if __name__ == "__main__":
    unittest.main()
