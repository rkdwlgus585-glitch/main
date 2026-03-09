import base64
import re
import unittest

import permit_diagnosis_calculator


class PermitCtaModeBranchesTest(unittest.TestCase):
    @staticmethod
    def _expand_wrapped_scripts(html: str) -> str:
        pattern = re.compile(
            r'<script nowprocket>\(\(\)=>\{const encoded="(?P<encoded>[^"]+)";.*?\}\)\(\);</script>',
            flags=re.S,
        )

        def repl(match: re.Match[str]) -> str:
            encoded = str(match.group("encoded") or "")
            decoded = base64.b64decode(encoded).decode("utf-8")
            return f"<script>{decoded}</script>"

        return pattern.sub(repl, html)

    def _build_html(self) -> str:
        return self._expand_wrapped_scripts(
            permit_diagnosis_calculator.build_html(
                title="AI 인허가 사전검토 진단기(신규등록 전용)",
                catalog=permit_diagnosis_calculator._blank_catalog(),
                rule_catalog=permit_diagnosis_calculator._load_rule_catalog(
                    permit_diagnosis_calculator.DEFAULT_RULES_PATH
                ),
            )
        )

    def test_build_html_contains_cta_mode_branch_strings(self):
        html = self._build_html()

        for snippet in (
            "ctaMode",
            "shortfall",
            "manual_review",
            "보완 필요 서류",
            "확인 권장 서류",
            "전문가 검토 안내",
            "#FFF8E1",
        ):
            self.assertIn(snippet, html)

    def test_build_html_contains_multiple_cta_mode_occurrences(self):
        html = self._build_html()
        self.assertGreaterEqual(html.count("ctaMode"), 2)


if __name__ == "__main__":
    unittest.main()
