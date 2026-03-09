"""Edge-case tests for yangdo_calculator and permit_diagnosis_calculator.

Covers boundary inputs, empty/None handling, extreme values, and the
permit double-brace SyntaxError fix.
"""
import base64
import re
import unittest

import yangdo_calculator
import permit_diagnosis_calculator


class YangdoPriceTokenEdgeCasesTest(unittest.TestCase):
    """Edge cases for _price_token_to_eok beyond basic tests."""

    def test_very_large_value_100억(self):
        result = yangdo_calculator._price_token_to_eok("100억")
        self.assertAlmostEqual(result, 100.0, places=4)

    def test_very_small_value_1만(self):
        result = yangdo_calculator._price_token_to_eok("1만")
        # 1만 = 10,000원 = 0.0001억
        self.assertAlmostEqual(result, 0.0001, places=6)

    def test_negative_value_parsed_as_positive(self):
        result = yangdo_calculator._price_token_to_eok("-1억")
        # Parser strips the sign; negative price inputs are uncommon in this domain
        self.assertAlmostEqual(result, 1.0, places=4)

    def test_whitespace_only_returns_none(self):
        self.assertIsNone(yangdo_calculator._price_token_to_eok("   "))

    def test_zero_만_returns_none_or_zero(self):
        result = yangdo_calculator._price_token_to_eok("0만")
        self.assertTrue(result is None or result == 0.0)

    def test_mixed_korean_numeric(self):
        result = yangdo_calculator._price_token_to_eok("50억 3000만")
        self.assertAlmostEqual(result, 50.3, places=4)


class YangdoTrainingDatasetEdgeCasesTest(unittest.TestCase):
    """Edge cases for build_training_dataset."""

    def test_empty_records_returns_empty(self):
        rows = yangdo_calculator.build_training_dataset([], site_url="https://seoulmna.kr")
        self.assertEqual(rows, [])

    def test_all_priced_records(self):
        records = [
            {
                "number": "7001",
                "uid": "93001",
                "license_text": "토목",
                "license_tokens": {"토목"},
                "years": {"y23": 5},
                "current_price_text": "3억",
                "current_price_eok": 3.0,
            },
            {
                "number": "7002",
                "uid": "93002",
                "license_text": "건축",
                "license_tokens": {"건축"},
                "years": {"y23": 2},
                "current_price_text": "1.5억",
                "current_price_eok": 1.5,
            },
        ]
        rows = yangdo_calculator.build_training_dataset(records, site_url="https://seoulmna.kr")
        self.assertEqual(len(rows), 2)

    def test_no_priced_records(self):
        records = [
            {
                "number": "7003",
                "uid": "93003",
                "license_text": "토목",
                "license_tokens": {"토목"},
                "years": {"y23": 1},
                "current_price_text": "협의",
                "current_price_eok": None,
            },
        ]
        rows = yangdo_calculator.build_training_dataset(records, site_url="https://seoulmna.kr")
        self.assertEqual(len(rows), 0)

    def test_claim_exceeds_current_price(self):
        records = [
            {
                "number": "7004",
                "uid": "93004",
                "license_text": "토목",
                "license_tokens": {"토목"},
                "years": {"y23": 3},
                "current_price_text": "1억",
                "current_price_eok": 1.0,
                "claim_price_text": "2억",
                "claim_price_eok": 2.0,
            },
        ]
        rows = yangdo_calculator.build_training_dataset(records, site_url="https://seoulmna.kr")
        self.assertEqual(len(rows), 1)


class YangdoMetaEdgeCasesTest(unittest.TestCase):
    """Edge cases for build_meta."""

    def test_meta_with_empty_dataset(self):
        records = []
        train_dataset = []
        meta = yangdo_calculator.build_meta(records, train_dataset)
        self.assertEqual(meta["all_record_count"], 0)
        self.assertEqual(meta["train_count"], 0)

    def test_meta_priced_ratio_all_priced(self):
        records = [
            {
                "number": "8001",
                "uid": "94001",
                "license_text": "토목",
                "license_tokens": {"토목"},
                "years": {"y23": 1},
                "current_price_text": "1억",
                "current_price_eok": 1.0,
            },
        ]
        train_dataset = yangdo_calculator.build_training_dataset(records, site_url="https://seoulmna.kr")
        meta = yangdo_calculator.build_meta(records, train_dataset)
        self.assertAlmostEqual(meta["priced_ratio"], 100.0, places=1)


class PermitDoubleBraceFixTest(unittest.TestCase):
    """Verify the permit SyntaxError fix: no ${{ in decoded JS output."""

    @staticmethod
    def _decode_all_scripts(html: str) -> str:
        pattern = re.compile(
            r'<script nowprocket>\(\(\)=>\{const encoded="(?P<encoded>[^"]+)";.*?\}\)\(\);</script>',
            flags=re.S,
        )
        decoded_parts = []
        for m in pattern.finditer(html):
            encoded = str(m.group("encoded") or "")
            decoded_parts.append(base64.b64decode(encoded).decode("utf-8"))
        return "\n".join(decoded_parts)

    def _build_permit_html(self) -> str:
        return permit_diagnosis_calculator.build_html(
            title="AI 인허가 사전검토 진단기(신규등록 전용)",
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._load_rule_catalog(
                permit_diagnosis_calculator.DEFAULT_RULES_PATH
            ),
        )

    def test_no_double_brace_template_literals(self):
        """${{ in JS template literals would cause [object Object] or SyntaxError."""
        html = self._build_permit_html()
        decoded_js = self._decode_all_scripts(html)
        double_brace_in_template = re.findall(r'\$\{\{', decoded_js)
        self.assertEqual(
            len(double_brace_in_template), 0,
            f"Found {len(double_brace_in_template)} occurrences of '${{{{' in decoded JS — "
            "these are f-string escapes that leaked into a regular string template",
        )

    def test_no_double_brace_control_flow(self):
        """{{ in control flow creates unnecessary nested blocks."""
        html = self._build_permit_html()
        decoded_js = self._decode_all_scripts(html)
        # Check for patterns like ") {{" or "} else if (...) {{"
        double_brace_flow = re.findall(r'[)\s]\s*\{\{(?!\{)', decoded_js)
        self.assertEqual(
            len(double_brace_flow), 0,
            f"Found {len(double_brace_flow)} double-brace control flow blocks in decoded JS",
        )

    def test_permit_html_builds_without_error(self):
        html = self._build_permit_html()
        decoded_js = self._decode_all_scripts(html)
        # ctaMode lives inside base64-encoded script blocks
        self.assertIn("ctaMode", decoded_js)
        self.assertIn("evidenceChecklistBox", decoded_js)
        self.assertIn("nextActionsBox", decoded_js)


if __name__ == "__main__":
    unittest.main()
