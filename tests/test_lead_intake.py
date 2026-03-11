"""Tests for lead_intake.py pure functions."""

from __future__ import annotations

import hashlib
import unittest
from datetime import datetime
from unittest.mock import patch

from lead_intake import (
    _cfg_int,
    _compact_text,
    _default_next_action,
    _defang_cell,
    _fingerprint,
    _infer_intent,
    _infer_urgency,
    _lead_id,
    _MAX_CELL_LEN,
    _normalize_intent_label,
    _normalize_token,
    _pick,
    _safe_contact,
    CONSULT_HEADERS,
)


class TestCfgInt(unittest.TestCase):
    """_cfg_int: parse CONFIG int with fallback."""

    @patch("lead_intake.CONFIG", {"k": "42"})
    def test_valid_int(self) -> None:
        assert _cfg_int("k", 0) == 42

    @patch("lead_intake.CONFIG", {"k": "abc"})
    def test_invalid_returns_default(self) -> None:
        assert _cfg_int("k", 10) == 10

    @patch("lead_intake.CONFIG", {})
    def test_missing_key_returns_default(self) -> None:
        assert _cfg_int("missing", 99) == 99

    @patch("lead_intake.CONFIG", {"k": ""})
    def test_empty_returns_default(self) -> None:
        assert _cfg_int("k", 7) == 7

    @patch("lead_intake.CONFIG", {"k": " 55 "})
    def test_whitespace_stripped(self) -> None:
        assert _cfg_int("k", 0) == 55


class TestCompactText(unittest.TestCase):
    """_compact_text: whitespace normalization."""

    def test_normal(self) -> None:
        assert _compact_text("hello  world") == "hello world"

    def test_tabs_and_newlines(self) -> None:
        assert _compact_text("a\t\nb") == "a b"

    def test_empty(self) -> None:
        assert _compact_text("") == ""

    def test_none(self) -> None:
        assert _compact_text(None) == ""

    def test_leading_trailing(self) -> None:
        assert _compact_text("  hi  ") == "hi"


class TestNormalizeToken(unittest.TestCase):
    """_normalize_token: lowercase + strip non-alphanum/hangul."""

    def test_korean(self) -> None:
        assert _normalize_token("양도 양수!") == "양도양수"

    def test_english(self) -> None:
        assert _normalize_token("Hello World") == "helloworld"

    def test_numbers(self) -> None:
        assert _normalize_token("abc 123") == "abc123"

    def test_special_chars_stripped(self) -> None:
        assert _normalize_token("(주)대한건설") == "주대한건설"

    def test_empty(self) -> None:
        assert _normalize_token("") == ""

    def test_none(self) -> None:
        assert _normalize_token(None) == ""


class TestSafeContact(unittest.TestCase):
    """_safe_contact: phone number formatting."""

    def test_11_digits(self) -> None:
        assert _safe_contact("01012345678") == "010-1234-5678"

    def test_10_digits(self) -> None:
        assert _safe_contact("0212345678") == "021-234-5678"

    def test_formatted_input(self) -> None:
        result = _safe_contact("010-1234-5678")
        assert result == "010-1234-5678"

    def test_short_number(self) -> None:
        assert _safe_contact("12345") == "12345"

    def test_empty(self) -> None:
        assert _safe_contact("") == ""

    def test_none(self) -> None:
        assert _safe_contact(None) == ""

    def test_with_spaces(self) -> None:
        result = _safe_contact("010 1234 5678")
        assert result == "010-1234-5678"


class TestLeadId(unittest.TestCase):
    """_lead_id: generates LD + timestamp + random suffix."""

    def test_starts_with_ld(self) -> None:
        assert _lead_id().startswith("LD")

    def test_deterministic_date(self) -> None:
        fixed = datetime(2026, 3, 10, 14, 30, 45)
        lid = _lead_id(now=fixed)
        assert lid.startswith("LD20260310143045")

    def test_length_range(self) -> None:
        lid = _lead_id()
        # LD + 14 digits + 3 random = 19 chars
        assert 19 <= len(lid) <= 20

    def test_unique_per_call(self) -> None:
        ids = {_lead_id() for _ in range(10)}
        # Random suffix should make most unique
        assert len(ids) >= 5


class TestInferIntent(unittest.TestCase):
    """_infer_intent: classify consultation text by intent."""

    def test_yangdo(self) -> None:
        assert _infer_intent("건설업 양도양수 문의") == "양도양수"

    def test_permit(self) -> None:
        assert _infer_intent("인허가 사전검토 요청") == "인허가(신규등록)"

    def test_new_registration(self) -> None:
        assert _infer_intent("신규등록 하고 싶어요") == "인허가(신규등록)"

    def test_corporate_diagnosis(self) -> None:
        assert _infer_intent("기업진단 필요합니다") == "기업진단"

    def test_capital(self) -> None:
        assert _infer_intent("실질자본금 점검") == "실질자본금"

    def test_split_merge(self) -> None:
        assert _infer_intent("법인분할 검토해주세요") == "분할합병"

    def test_administrative(self) -> None:
        assert _infer_intent("영업정지 처분 받았어요") == "행정처분"

    def test_incorporation(self) -> None:
        assert _infer_intent("법인설립 하려고요") == "법인설립"

    def test_sipy(self) -> None:
        assert _infer_intent("시공능력 평가") == "시평/기업진단"

    def test_unknown(self) -> None:
        assert _infer_intent("안녕하세요") == "기타"

    def test_empty(self) -> None:
        assert _infer_intent("") == "기타"

    def test_mna(self) -> None:
        assert _infer_intent("mna 문의") == "양도양수"

    def test_maemul(self) -> None:
        assert _infer_intent("매물 있나요") == "양도양수"


class TestNormalizeIntentLabel(unittest.TestCase):
    """_normalize_intent_label: standardize intent labels."""

    def test_permit_variants(self) -> None:
        assert _normalize_intent_label("인허가") == "인허가(신규등록)"
        assert _normalize_intent_label("사전검토") == "인허가(신규등록)"
        assert _normalize_intent_label("면허등록") == "인허가(신규등록)"

    def test_new_only(self) -> None:
        assert _normalize_intent_label("신규") == "인허가(신규등록)"

    def test_passthrough(self) -> None:
        assert _normalize_intent_label("양도양수") == "양도양수"

    def test_empty(self) -> None:
        assert _normalize_intent_label("") == "기타"

    def test_none_as_string(self) -> None:
        assert _normalize_intent_label(None) == "기타"


class TestInferUrgency(unittest.TestCase):
    """_infer_urgency: urgency classification."""

    def test_urgent_today(self) -> None:
        assert _infer_urgency("오늘 급합니다") == "긴급"

    def test_urgent_immediately(self) -> None:
        assert _infer_urgency("당장 처리 부탁") == "긴급"

    def test_medium(self) -> None:
        assert _infer_urgency("문의드립니다") == "보통"

    def test_normal(self) -> None:
        assert _infer_urgency("안녕하세요 건설업 관련") == "일반"

    def test_empty(self) -> None:
        assert _infer_urgency("") == "일반"

    def test_urgent_deadline(self) -> None:
        assert _infer_urgency("이번주 마감이에요") == "긴급"


class TestDefaultNextAction(unittest.TestCase):
    """_default_next_action: recommended next action per intent."""

    def test_yangdo(self) -> None:
        result = _default_next_action("양도양수", "일반")
        assert "매물" in result or "추천" in result

    def test_permit(self) -> None:
        result = _default_next_action("인허가(신규등록)", "일반")
        assert "등록기준" in result or "체크리스트" in result

    def test_urgent_suffix(self) -> None:
        result = _default_next_action("양도양수", "긴급")
        assert "당일" in result

    def test_normal_no_urgent_suffix(self) -> None:
        result = _default_next_action("양도양수", "일반")
        assert "당일" not in result

    def test_unknown_intent(self) -> None:
        result = _default_next_action("미분류", "보통")
        assert "확인" in result

    def test_capital(self) -> None:
        result = _default_next_action("실질자본금", "일반")
        assert "예치" in result or "자본금" in result


class TestFingerprint(unittest.TestCase):
    """_fingerprint: SHA1 dedup fingerprint."""

    def test_deterministic(self) -> None:
        record = {"title": "A", "content": "B", "contact": "C", "channel": "D"}
        fp1 = _fingerprint(record)
        fp2 = _fingerprint(record)
        assert fp1 == fp2

    def test_different_records(self) -> None:
        r1 = {"title": "A", "content": "B", "contact": "", "channel": ""}
        r2 = {"title": "X", "content": "B", "contact": "", "channel": ""}
        assert _fingerprint(r1) != _fingerprint(r2)

    def test_empty_record(self) -> None:
        fp = _fingerprint({})
        assert len(fp) == 40  # SHA1 hex length

    def test_is_hex(self) -> None:
        fp = _fingerprint({"title": "test"})
        int(fp, 16)  # Should not raise

    def test_whitespace_normalized(self) -> None:
        r1 = {"title": "hello world", "content": "", "contact": "", "channel": ""}
        r2 = {"title": "helloworld", "content": "", "contact": "", "channel": ""}
        # _normalize_token strips spaces, so these should be equal
        assert _fingerprint(r1) == _fingerprint(r2)


class TestPick(unittest.TestCase):
    """_pick: select first non-empty value from dict by key priority."""

    def test_first_key(self) -> None:
        assert _pick({"a": "v1", "b": "v2"}, ["a", "b"]) == "v1"

    def test_fallback_to_second(self) -> None:
        assert _pick({"a": "", "b": "v2"}, ["a", "b"]) == "v2"

    def test_all_empty(self) -> None:
        assert _pick({"a": "", "b": ""}, ["a", "b"]) == ""

    def test_missing_keys(self) -> None:
        assert _pick({}, ["a", "b"]) == ""

    def test_strips_whitespace(self) -> None:
        assert _pick({"a": " hello "}, ["a"]) == "hello"

    def test_none_value_stringified(self) -> None:
        # _pick uses str(source[key]).strip(), so None → "None" (truthy)
        assert _pick({"a": None, "b": "ok"}, ["a", "b"]) == "None"


class TestConsultHeaders(unittest.TestCase):
    """CONSULT_HEADERS: validate structure."""

    def test_has_16_columns(self) -> None:
        assert len(CONSULT_HEADERS) == 16

    def test_first_is_date(self) -> None:
        assert CONSULT_HEADERS[0] == "접수일시"

    def test_lead_id_column(self) -> None:
        assert "리드ID" in CONSULT_HEADERS

    def test_status_column(self) -> None:
        assert "상태" in CONSULT_HEADERS


class TestDefangCell(unittest.TestCase):
    """_defang_cell: escape spreadsheet formula prefixes."""

    def test_normal_text_unchanged(self) -> None:
        assert _defang_cell("hello") == "hello"

    def test_equals_prefix_escaped(self) -> None:
        assert _defang_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"

    def test_plus_prefix_escaped(self) -> None:
        assert _defang_cell("+1234") == "'+1234"

    def test_minus_prefix_escaped(self) -> None:
        assert _defang_cell("-value") == "'-value"

    def test_at_prefix_escaped(self) -> None:
        assert _defang_cell("@mention") == "'@mention"

    def test_tab_prefix_escaped(self) -> None:
        assert _defang_cell("\tdata") == "'\tdata"

    def test_empty_string(self) -> None:
        assert _defang_cell("") == ""

    def test_space_prefix_not_escaped(self) -> None:
        assert _defang_cell(" safe") == " safe"

    def test_korean_text_unchanged(self) -> None:
        assert _defang_cell("전기공사업 양도양수 문의") == "전기공사업 양도양수 문의"


class TestMaxCellLen(unittest.TestCase):
    """_MAX_CELL_LEN constant for input size limits."""

    def test_constant_is_positive(self) -> None:
        assert _MAX_CELL_LEN > 0

    def test_constant_value(self) -> None:
        assert _MAX_CELL_LEN == 2000


if __name__ == "__main__":
    unittest.main()
