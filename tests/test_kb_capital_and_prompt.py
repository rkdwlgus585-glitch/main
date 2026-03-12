"""Tests for kb.get_capital_info() and kb.get_fact_prompt_injection().

These functions expose the CONSTRUCTION_STANDARDS data for consumers —
get_capital_info for programmatic lookups, get_fact_prompt_injection for
injecting authoritative facts into LLM prompts.
"""

from __future__ import annotations

import unittest

import kb


class GetCapitalInfoTest(unittest.TestCase):
    """kb.get_capital_info() — 업종별 자본금 조회."""

    def test_known_sector_returns_dict(self) -> None:
        result = kb.get_capital_info("토목건축공사업")
        self.assertIsInstance(result, dict)
        self.assertIn("법인_자본금", result)

    def test_known_sector_capital_value(self) -> None:
        result = kb.get_capital_info("토목건축공사업")
        self.assertEqual(result["법인_자본금"], 850_000_000)  # 8.5억원

    def test_unknown_sector_returns_empty(self) -> None:
        result = kb.get_capital_info("존재하지않는업종")
        self.assertEqual(result, {})

    def test_empty_string_returns_empty(self) -> None:
        result = kb.get_capital_info("")
        self.assertEqual(result, {})

    def test_all_three_sectors_present(self) -> None:
        for sector in ("토목건축공사업", "건축공사업", "토목공사업"):
            with self.subTest(sector=sector):
                info = kb.get_capital_info(sector)
                self.assertIn("법인_자본금", info)
                self.assertIn("기술인력_총원", info)


class GetFactPromptInjectionTest(unittest.TestCase):
    """kb.get_fact_prompt_injection() — LLM 프롬프트 팩트 주입."""

    def test_returns_non_empty_string(self) -> None:
        result = kb.get_fact_prompt_injection()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 100)

    def test_contains_sector_names(self) -> None:
        result = kb.get_fact_prompt_injection()
        for sector in ("토목건축공사업", "건축공사업", "토목공사업"):
            with self.subTest(sector=sector):
                self.assertIn(sector, result)

    def test_contains_capital_amounts(self) -> None:
        result = kb.get_fact_prompt_injection()
        self.assertIn("법인 자본금", result)
        self.assertIn("개인 자본금", result)

    def test_contains_common_rules(self) -> None:
        result = kb.get_fact_prompt_injection()
        self.assertIn("공제조합", result)
        self.assertIn("기술자 충원기한", result)
        self.assertIn("실질자본금 예치기간", result)
        self.assertIn("진단보고서 발급자격", result)

    def test_header_present(self) -> None:
        result = kb.get_fact_prompt_injection()
        self.assertIn("건설업 등록기준 법정 데이터", result)


if __name__ == "__main__":
    unittest.main()
