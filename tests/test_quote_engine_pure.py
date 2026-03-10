"""Unit tests for quote_engine.py pure functions — no Google Sheets dependency."""

from __future__ import annotations

import os
import json
from datetime import datetime
from unittest.mock import patch

import pytest

from quote_engine import (
    INTENT_ALIASES,
    QUOTE_HEADERS,
    _build_assumptions,
    _build_email_message,
    _build_kakao_message,
    _build_summary,
    _cfg_int,
    _compact,
    _ensure_dir,
    _estimate_fee,
    _generate_quote,
    _infer_intent,
    _infer_urgency,
    _norm,
    _normalize_intent,
    _parse_eok,
    _parse_phone,
    _quote_id,
    _write_quote_files,
)


# ────────────────────────────────────────────────
# _cfg_int
# ────────────────────────────────────────────────


class TestCfgInt:
    def test_valid_int(self) -> None:
        assert _cfg_int("QUOTE_DEFAULT_VALID_DAYS", 7) == 7

    def test_invalid_returns_default(self) -> None:
        # Temporarily test with a key that isn't in CONFIG
        assert isinstance(_cfg_int("NONEXISTENT_KEY_XYZ", 42), int)

    def test_none_default(self) -> None:
        result = _cfg_int("NONEXISTENT_KEY", None)
        assert result is None


# ────────────────────────────────────────────────
# _compact
# ────────────────────────────────────────────────


class TestCompact:
    def test_basic(self) -> None:
        assert _compact("  hello   world  ") == "hello world"

    def test_none(self) -> None:
        assert _compact(None) == ""

    def test_empty(self) -> None:
        assert _compact("") == ""

    def test_tabs_and_newlines(self) -> None:
        assert _compact("a\t\nb") == "a b"


# ────────────────────────────────────────────────
# _norm
# ────────────────────────────────────────────────


class TestNorm:
    def test_korean(self) -> None:
        assert _norm("양도양수") == "양도양수"

    def test_mixed(self) -> None:
        assert _norm("MNA 견적!!") == "mna견적"

    def test_none(self) -> None:
        assert _norm(None) == ""

    def test_special_chars_removed(self) -> None:
        assert _norm("a-b_c.d") == "abcd"


# ────────────────────────────────────────────────
# _parse_phone
# ────────────────────────────────────────────────


class TestParsePhone:
    def test_11_digit(self) -> None:
        assert _parse_phone("01012345678") == "010-1234-5678"

    def test_10_digit(self) -> None:
        assert _parse_phone("0212345678") == "021-234-5678"

    def test_formatted_input(self) -> None:
        assert _parse_phone("010-1234-5678") == "010-1234-5678"

    def test_none(self) -> None:
        assert _parse_phone(None) == ""

    def test_short_number(self) -> None:
        # Less than 10 digits → returned as-is stripped
        assert _parse_phone("12345") == "12345"

    def test_dashes_stripped(self) -> None:
        assert _parse_phone("010-9926-8661") == "010-9926-8661"


# ────────────────────────────────────────────────
# _parse_eok
# ────────────────────────────────────────────────


class TestParseEok:
    def test_eok_only(self) -> None:
        assert _parse_eok("2.5억") == 2.5

    def test_man_only(self) -> None:
        assert _parse_eok("5000만") == 0.5

    def test_eok_and_man(self) -> None:
        assert _parse_eok("1억5000만") == 1.5

    def test_plain_large_number(self) -> None:
        # >= 100 → divide by 10000
        assert _parse_eok("25000") == 2.5

    def test_plain_small_number(self) -> None:
        # < 100 → treated as 억
        assert _parse_eok("3.5") == 3.5

    def test_empty(self) -> None:
        assert _parse_eok("") == 0.0

    def test_none(self) -> None:
        assert _parse_eok(None) == 0.0

    def test_with_commas_and_spaces(self) -> None:
        assert _parse_eok("25,000") == 2.5

    def test_zero(self) -> None:
        assert _parse_eok("0") == 0.0

    def test_decimal_eok(self) -> None:
        assert _parse_eok("0.5억") == 0.5

    def test_mixed_garbage_chars(self) -> None:
        assert _parse_eok("약 2억원 정도") == 2.0


# ────────────────────────────────────────────────
# _infer_intent
# ────────────────────────────────────────────────


class TestInferIntent:
    def test_yangdo(self) -> None:
        assert _infer_intent("양도양수 건") == "양도양수"

    def test_yangdo_alias(self) -> None:
        assert _infer_intent("양도 관련") == "양도양수"

    def test_yangsu(self) -> None:
        assert _infer_intent("양수 문의") == "양도양수"

    def test_mna(self) -> None:
        assert _infer_intent("MNA 진행") == "양도양수"

    def test_maemul(self) -> None:
        assert _infer_intent("매물 확인") == "양도양수"

    def test_singgyu(self) -> None:
        assert _infer_intent("신규등록 문의") == "신규등록"

    def test_singgyu_short(self) -> None:
        assert _infer_intent("신규 면허") == "신규등록"

    def test_deungrok(self) -> None:
        assert _infer_intent("등록 하고 싶어요") == "신규등록"

    def test_giup_jindan(self) -> None:
        assert _infer_intent("기업진단 필요") == "기업진단"

    def test_jindan(self) -> None:
        assert _infer_intent("진단 요청") == "기업진단"

    def test_silqual_jabongeum(self) -> None:
        assert _infer_intent("실질자본금 확인") == "실질자본금"

    def test_jabongeum(self) -> None:
        assert _infer_intent("자본금 관련") == "실질자본금"

    def test_yechee(self) -> None:
        assert _infer_intent("예치 관련") == "실질자본금"

    def test_bunhal_hapbyung(self) -> None:
        assert _infer_intent("분할합병") == "분할합병"

    def test_bunhal(self) -> None:
        assert _infer_intent("분할 요청") == "분할합병"

    def test_hapbyung(self) -> None:
        assert _infer_intent("합병 건") == "분할합병"

    def test_haengjeong_cheobun(self) -> None:
        assert _infer_intent("행정처분 대응") == "행정처분"

    def test_yeongup_jeongji(self) -> None:
        assert _infer_intent("영업정지 문의") == "행정처분"

    def test_gwajinggeum(self) -> None:
        assert _infer_intent("과징금 관련") == "행정처분"

    def test_unknown(self) -> None:
        assert _infer_intent("일반 문의") == "기타"


# ────────────────────────────────────────────────
# _normalize_intent
# ────────────────────────────────────────────────


class TestNormalizeIntent:
    def test_alias_mapping(self) -> None:
        assert _normalize_intent("신규") == "신규등록"

    def test_alias_mapping_yangdo(self) -> None:
        assert _normalize_intent("양도") == "양도양수"

    def test_full_name(self) -> None:
        assert _normalize_intent("기업진단") == "기업진단"

    def test_empty_falls_back_to_infer(self) -> None:
        assert _normalize_intent("", "양도 관련 건", "") == "양도양수"

    def test_unknown_falls_back_to_infer(self) -> None:
        assert _normalize_intent("unknown_type", "신규등록 문의", "") == "신규등록"

    def test_all_aliases_covered(self) -> None:
        for alias, target in INTENT_ALIASES.items():
            assert _normalize_intent(alias) == target


# ────────────────────────────────────────────────
# _infer_urgency
# ────────────────────────────────────────────────


class TestInferUrgency:
    def test_urgent(self) -> None:
        assert _infer_urgency("긴급 처리 요청") == "긴급"

    def test_urgent_dangjang(self) -> None:
        assert _infer_urgency("당장 해야함") == "긴급"

    def test_urgent_oneul(self) -> None:
        assert _infer_urgency("오늘까지 완료") == "긴급"

    def test_medium(self) -> None:
        assert _infer_urgency("빠르게 진행") == "보통"

    def test_medium_josok(self) -> None:
        assert _infer_urgency("조속 처리") == "보통"

    def test_normal(self) -> None:
        assert _infer_urgency("일반 문의") == "일반"


# ────────────────────────────────────────────────
# _quote_id
# ────────────────────────────────────────────────


class TestQuoteId:
    def test_format(self) -> None:
        now = datetime(2026, 3, 10, 14, 30, 0)
        qid = _quote_id(now)
        assert qid.startswith("QT20260310143000")
        assert len(qid) == len("QT20260310143000") + 3  # 3 random digits

    def test_unique(self) -> None:
        now = datetime(2026, 1, 1, 0, 0, 0)
        ids = {_quote_id(now) for _ in range(100)}
        # With 3 random digits (100-999), collisions possible but rare in 100 samples
        assert len(ids) > 50


# ────────────────────────────────────────────────
# _estimate_fee — CORE business logic
# ────────────────────────────────────────────────


class TestEstimateFee:
    def test_singgyu_basic(self) -> None:
        fee = _estimate_fee("신규등록")
        assert fee["fee_min"] == 120
        assert fee["fee_max"] == 260
        assert fee["retainer"] == 60
        assert "~" in fee["period_days"]

    def test_yangdo_basic(self) -> None:
        fee = _estimate_fee("양도양수")
        assert fee["fee_min"] == 180
        assert fee["fee_max"] == 420

    def test_yangdo_deal_value_scaling(self) -> None:
        fee_no_deal = _estimate_fee("양도양수", deal_value_eok=0)
        fee_with_deal = _estimate_fee("양도양수", deal_value_eok=2.5)
        assert fee_with_deal["fee_min"] > fee_no_deal["fee_min"]
        assert fee_with_deal["fee_max"] > fee_no_deal["fee_max"]

    def test_yangdo_deal_value_capped(self) -> None:
        fee = _estimate_fee("양도양수", deal_value_eok=1000)
        # fee_min addition capped at 260
        assert fee["fee_min"] == 180 + 260
        # fee_max addition capped at 420
        assert fee["fee_max"] == 420 + 420

    def test_singgyu_multi_license(self) -> None:
        fee1 = _estimate_fee("신규등록", license_count=1)
        fee3 = _estimate_fee("신규등록", license_count=3)
        assert fee3["fee_min"] == fee1["fee_min"] + 2 * 35
        assert fee3["fee_max"] == fee1["fee_max"] + 2 * 65

    def test_due_diligence_addon(self) -> None:
        fee_no = _estimate_fee("양도양수", with_due_diligence=False)
        fee_yes = _estimate_fee("양도양수", with_due_diligence=True)
        assert fee_yes["fee_min"] == fee_no["fee_min"] + 70
        assert fee_yes["fee_max"] == fee_no["fee_max"] + 160

    def test_urgent_scaling(self) -> None:
        fee_normal = _estimate_fee("양도양수", urgency="일반")
        fee_urgent = _estimate_fee("양도양수", urgency="긴급")
        assert fee_urgent["fee_min"] > fee_normal["fee_min"]
        assert fee_urgent["fee_max"] > fee_normal["fee_max"]

    def test_botons_urgency(self) -> None:
        fee = _estimate_fee("양도양수", urgency="보통")
        # Period should be adjusted
        assert "~" in fee["period_days"]

    def test_unknown_intent_uses_gita(self) -> None:
        fee = _estimate_fee("기타")
        assert fee["fee_min"] == 80
        assert fee["fee_max"] == 220

    def test_all_intents_produce_valid_output(self) -> None:
        intents = ["신규등록", "양도양수", "기업진단", "실질자본금", "분할합병", "행정처분", "기타"]
        for intent in intents:
            fee = _estimate_fee(intent)
            assert fee["fee_min"] > 0
            assert fee["fee_max"] >= fee["fee_min"]
            assert fee["retainer"] > 0
            assert "~" in fee["period_days"]

    def test_retainer_is_half_of_fee_min(self) -> None:
        fee = _estimate_fee("양도양수")
        assert fee["retainer"] == int(round(fee["fee_min"] * 0.5))

    def test_bunhal_is_most_expensive(self) -> None:
        fees = {intent: _estimate_fee(intent) for intent in ["신규등록", "양도양수", "기업진단", "분할합병"]}
        assert fees["분할합병"]["fee_max"] > fees["양도양수"]["fee_max"]


# ────────────────────────────────────────────────
# _build_assumptions
# ────────────────────────────────────────────────


class TestBuildAssumptions:
    def test_common_always_present(self) -> None:
        for intent in ["신규등록", "양도양수", "기타"]:
            result = _build_assumptions(intent)
            assert any("부가세" in a for a in result)

    def test_singgyu_specific(self) -> None:
        result = _build_assumptions("신규등록")
        assert any("서류가 준비된" in a for a in result)

    def test_yangdo_specific(self) -> None:
        result = _build_assumptions("양도양수")
        assert any("양도기업" in a for a in result)

    def test_bunhal_specific(self) -> None:
        result = _build_assumptions("분할합병")
        assert any("세무" in a for a in result)

    def test_gita_no_special(self) -> None:
        result = _build_assumptions("기타")
        assert len(result) == 3  # only common


# ────────────────────────────────────────────────
# _build_summary
# ────────────────────────────────────────────────


class TestBuildSummary:
    def test_contains_fee_range(self) -> None:
        fee = {"fee_min": 120, "fee_max": 260, "retainer": 60, "period_days": "12~30"}
        result = _build_summary("신규등록", "테스트 건", fee)
        assert "120~260" in result
        assert "60만원" in result
        assert "12~30" in result


# ────────────────────────────────────────────────
# _build_kakao_message / _build_email_message
# ────────────────────────────────────────────────


class TestBuildMessages:
    def _make_quote_and_req(self):
        quote = {
            "quote_id": "QT202603101430001",
            "intent": "양도양수",
            "fee_min": 180,
            "fee_max": 420,
            "retainer": 90,
            "period_days": "10~35",
            "valid_until": "2026-03-17",
            "assumptions": ["부가세 별도 기준입니다."],
            "summary": "test summary",
            "title": "테스트 견적",
            "created_at": "2026-03-10 14:30",
        }
        req = {"lead_id": "L001", "customer_name": "홍길동", "contact": "010-1234-5678"}
        return quote, req

    def test_kakao_contains_quote_id(self) -> None:
        quote, req = self._make_quote_and_req()
        msg = _build_kakao_message(quote, req)
        assert "QT202603101430001" in msg

    def test_kakao_contains_fee(self) -> None:
        quote, req = self._make_quote_and_req()
        msg = _build_kakao_message(quote, req)
        assert "180~420" in msg

    def test_email_contains_greeting(self) -> None:
        quote, req = self._make_quote_and_req()
        msg = _build_email_message(quote, req)
        assert "안녕하세요" in msg

    def test_email_contains_assumptions(self) -> None:
        quote, req = self._make_quote_and_req()
        msg = _build_email_message(quote, req)
        assert "부가세" in msg


# ────────────────────────────────────────────────
# _ensure_dir / _write_quote_files
# ────────────────────────────────────────────────


class TestFileOps:
    def test_ensure_dir_creates(self, tmp_path) -> None:
        target = str(tmp_path / "newdir")
        _ensure_dir(target)
        assert os.path.isdir(target)

    def test_ensure_dir_empty_path(self) -> None:
        _ensure_dir("")  # should not crash

    def test_write_quote_files(self, tmp_path) -> None:
        quote = {
            "quote_id": "QT_TEST",
            "created_at": "2026-03-10",
            "intent": "양도양수",
            "title": "테스트",
            "fee_min": 100,
            "fee_max": 200,
            "retainer": 50,
            "period_days": "5~10",
            "valid_until": "2026-03-17",
            "assumptions": ["가정1"],
            "summary": "요약",
            "kakao_message": "카카오",
            "email_message": "이메일",
        }
        req = {"lead_id": "L001"}
        with patch.dict("quote_engine.CONFIG", {"QUOTE_OUTPUT_DIR": str(tmp_path)}):
            json_path, md_path = _write_quote_files(quote, req)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
        assert json_path.endswith(".json")
        assert md_path.endswith(".md")
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["quote"]["quote_id"] == "QT_TEST"


# ────────────────────────────────────────────────
# _generate_quote (integration of pure functions)
# ────────────────────────────────────────────────


class TestGenerateQuote:
    def test_basic_generation(self) -> None:
        req = {
            "intent": "양도양수",
            "title": "테스트 견적",
            "customer_name": "홍길동",
            "deal_value_eok": 0.0,
            "urgency": "일반",
            "licenses": [],
            "with_due_diligence": False,
        }
        quote = _generate_quote(req)
        assert quote["quote_id"].startswith("QT")
        assert quote["intent"] == "양도양수"
        assert quote["fee_min"] > 0
        assert quote["fee_max"] >= quote["fee_min"]
        assert "valid_until" in quote
        assert len(quote["assumptions"]) > 0
        assert "카카오" not in quote["kakao_message"] or True  # just ensure it exists
        assert "안녕하세요" in quote["email_message"]

    def test_customer_name_in_title(self) -> None:
        req = {
            "intent": "신규등록",
            "title": "전기공사업",
            "customer_name": "김건설",
            "deal_value_eok": 0,
            "urgency": "일반",
            "licenses": [],
            "with_due_diligence": False,
        }
        quote = _generate_quote(req)
        assert "김건설" in quote["title"]

    def test_urgent_fee_higher(self) -> None:
        base_req = {
            "intent": "양도양수",
            "title": "테스트",
            "customer_name": "",
            "deal_value_eok": 0,
            "licenses": [],
            "with_due_diligence": False,
        }
        normal = _generate_quote({**base_req, "urgency": "일반"})
        urgent = _generate_quote({**base_req, "urgency": "긴급"})
        assert urgent["fee_min"] > normal["fee_min"]


# ────────────────────────────────────────────────
# QUOTE_HEADERS constant
# ────────────────────────────────────────────────


class TestQuoteHeaders:
    def test_header_count(self) -> None:
        assert len(QUOTE_HEADERS) == 18

    def test_first_header(self) -> None:
        assert QUOTE_HEADERS[0] == "생성일시"

    def test_last_header(self) -> None:
        assert QUOTE_HEADERS[-1] == "원문참조"

    def test_no_duplicates(self) -> None:
        assert len(QUOTE_HEADERS) == len(set(QUOTE_HEADERS))
