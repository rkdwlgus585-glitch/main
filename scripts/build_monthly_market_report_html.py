#!/usr/bin/env python3
"""
Build a monthly SeoulMNA market report HTML draft from the live keyword report snapshot.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_JSON = ROOT / "logs" / "monthly_notice_keyword_report_latest.json"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "monthly_market_report"
DEFAULT_KAKAO_URL = os.getenv("KAKAO_OPENCHAT_URL", "https://open.kakao.com/o/syWr1hIe")
DEFAULT_PHONE = "010-9926-8661"
DEFAULT_BIZCARD_IMAGE = (
    "https://seoulmna.co.kr/data/editor/2601/"
    "thumb-f7d3177d503f0aa4331e6b6472a02d36_1769753539_1509_835x835.jpg"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _month_key(year: int, month: int) -> str:
    return f"{int(year):04d}-{int(month):02d}"


def _yy(year: int) -> str:
    return f"{int(year) % 100:02d}"


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _suffix_particle_uro(text: str) -> str:
    src = _normalize_space(text)
    if not src:
        return "으로"
    last = src[-1]
    if not re.fullmatch(r"[가-힣]", last):
        return "으로"
    code = ord(last) - 0xAC00
    jong = code % 28
    if jong == 0 or jong == 8:
        return "로"
    return "으로"


def _suffix_particle_wa_gwa(text: str) -> str:
    src = _normalize_space(text)
    if not src:
        return "와"
    last = src[-1]
    if not re.fullmatch(r"[가-힣]", last):
        return "와"
    code = ord(last) - 0xAC00
    jong = code % 28
    return "와" if jong == 0 else "과"


def _pick_month_row(payload: dict, month_key: str) -> dict:
    for row in payload.get("monthly_plan", []) or []:
        if str(row.get("month", "")).strip() == month_key:
            return dict(row)
    raise KeyError(f"month row not found: {month_key}")


def _theme_keywords(payload: dict, theme_key: str, limit: int = 3) -> list[dict]:
    rows = list(payload.get("live_snapshot", {}).get("theme_rankings", {}).get(theme_key, []) or [])
    return [dict(row) for row in rows[: max(1, int(limit))]]


def _first_keyword(rows: list[dict], fallback: str) -> str:
    for row in rows:
        keyword = _normalize_space(row.get("keyword", ""))
        if keyword:
            return keyword
    return fallback


def _keyword_to_signal_label(keyword: str) -> str:
    src = _normalize_space(keyword)
    if not src:
        return ""
    if "기업진단" in src or "실질자본금" in src:
        return "기업진단·실질자본금"
    if "실태조사" in src or "행정처분" in src or "등록말소" in src:
        return "실태조사·행정 리스크"
    if "양도양수" in src:
        return "양도양수"
    if "신규등록" in src or "등록기준" in src or "기술인력" in src:
        return "신규등록"
    if "시공능력평가" in src or "입찰" in src or "공공 발주" in src:
        return "입찰·시공능력평가"
    if "경기" in src or "시장 리포트" in src or "상반기" in src:
        return "경기 전망"
    return src


def _unique_signal_labels(*keyword_groups: list[dict]) -> list[str]:
    out: list[str] = []
    for rows in keyword_groups:
        for row in rows:
            label = _keyword_to_signal_label(row.get("keyword", ""))
            if label and label not in out:
                out.append(label)
    return out


def _keyword_phrase(rows: list[dict], fallback: str) -> str:
    labels = _unique_signal_labels(rows)
    return "·".join(labels[:2]) if labels else fallback


def _build_core_question(theme_key: str) -> str:
    if theme_key == "license_transfer":
        return "기회는 보이는데 왜 진입 판단은 더 어려워질까?"
    if theme_key == "new_registration":
        return "등록 문의는 느는데 왜 준비 격차는 더 커질까?"
    if theme_key == "capital_diagnosis":
        return "왜 자금·진단 준비도가 이번 달 결정을 좌우할까?"
    if theme_key == "performance_bidding":
        return "면허 취득 이후 왜 입찰 활용까지 같이 봐야 할까?"
    if theme_key == "merger_split":
        return "확장보다 왜 구조 재편 판단이 더 중요해질까?"
    if theme_key == "compliance_risk":
        return "왜 유지 리스크를 먼저 봐야 할까?"
    return "기대감은 살아나는데 왜 대표 결정은 더 늦어질까?"


def _build_subject(year: int, month: int, core_question: str) -> str:
    return f"[{_yy(year)}년 {int(month)}월] 건설업 대표를 위한 건설업 전망 리포트 | {core_question}"


def build_report_html(
    payload: dict,
    *,
    year: int,
    month: int,
    run_date: date,
    kakao_url: str,
    phone: str,
    bizcard_image_url: str,
) -> tuple[str, str]:
    month_key = _month_key(year, month)
    month_label = f"{int(month)}월"
    month_row = _pick_month_row(payload, month_key)
    theme_key = _normalize_space(month_row.get("theme_key", "market_report")) or "market_report"
    primary_market = _normalize_space(month_row.get("current_live_primary_candidate", "건설업 경기 전망"))
    supporting_market = [
        _normalize_space(item)
        for item in list(month_row.get("current_live_supporting_candidates", []) or [])[:3]
        if _normalize_space(item)
    ]

    market_rows = _theme_keywords(payload, "market_report", limit=3)
    transfer_rows = _theme_keywords(payload, "license_transfer", limit=3)
    registration_rows = _theme_keywords(payload, "new_registration", limit=3)
    capital_rows = _theme_keywords(payload, "capital_diagnosis", limit=3)
    risk_rows = _theme_keywords(payload, "compliance_risk", limit=3)
    bidding_rows = _theme_keywords(payload, "performance_bidding", limit=3)

    today = run_date.strftime("%Y.%m.%d")
    phone_digits = re.sub(r"[^\d]", "", phone)

    market_signal_label = _keyword_phrase(
        [{"keyword": primary_market}] + [{"keyword": item} for item in supporting_market],
        "경기 전망",
    )
    capital_signal_label = _keyword_phrase(capital_rows, "기업진단·실질자본금")
    risk_signal_label = _keyword_phrase(risk_rows, "실태조사·행정 리스크")
    transfer_signal_label = _keyword_phrase(transfer_rows, "양도양수")
    registration_signal_label = _keyword_phrase(registration_rows, "신규등록")
    bidding_signal_label = _keyword_phrase(bidding_rows, "입찰·시공능력평가")
    signal_labels = _unique_signal_labels(
        [{"keyword": primary_market}] + [{"keyword": item} for item in supporting_market],
        capital_rows,
        risk_rows,
        transfer_rows,
        registration_rows,
        bidding_rows,
    )
    focus_badges_html = "".join(
        (
            f'<span style="display:inline-block; margin:0 8px 8px 0; padding:8px 14px; '
            f'border-radius:999px; background:#e0f2fe; color:#075985; font-size:14px; font-weight:700;">{label}</span>'
        )
        for label in signal_labels[:5]
    )

    primary_transfer = _keyword_to_signal_label(_first_keyword(transfer_rows, "양도양수"))
    primary_registration = _keyword_to_signal_label(_first_keyword(registration_rows, "신규등록"))
    primary_capital = _keyword_to_signal_label(_first_keyword(capital_rows, "기업진단"))
    primary_risk = _keyword_to_signal_label(_first_keyword(risk_rows, "실태조사"))
    primary_bidding = _keyword_to_signal_label(_first_keyword(bidding_rows, "입찰·시공능력평가"))

    core_question = _build_core_question(theme_key)
    subject = _build_subject(year, month, core_question)
    thesis = (
        f"{year}년 {month_label} 건설업 시장은 기대감은 살아나도 실제 의사결정은 "
        f"{capital_signal_label}과 {risk_signal_label} 검토 앞에서 더 보수적으로 움직이는 국면입니다."
    )
    quick_summary_items = [
        f"이번 달 시장 신호는 <strong>{market_signal_label}</strong> 쪽에서 먼저 움직이지만, 실제 계약 전환은 <strong>{capital_signal_label}</strong>과 <strong>{risk_signal_label}</strong> 준비도에서 갈립니다.",
        "공공과 민간의 체감 차이, 그리고 수주-착공-기성의 시간차 때문에 문의가 늘어도 현장 체감은 한 박자 늦게 따라옵니다.",
        f"따라서 대표는 이번 달에 경기 판단, <strong>{transfer_signal_label}</strong>와 <strong>{registration_signal_label}</strong> 중 진입 방식, 그리고 <strong>{bidding_signal_label}</strong>까지 이어질 활용 계획을 함께 정리해야 합니다.",
    ]
    quick_summary_html = "".join(
        f'<li style="margin-bottom:10px;">{item}</li>' for item in quick_summary_items
    )
    contents_items = [
        f"1. {year}년 {month_label} 시장 한 문장 정리",
        "2. 공공 vs 민간: 돈이 도는 곳이 갈렸다",
        "3. 현장 체감이 늦는 이유: 수주-착공-기성의 시간차",
        f"4. {year}년 상반기 변수 5가지",
        "5. 대표 실무 전략 7가지",
        "6. 면허/실적 전략: 양도양수·신규등록·분할합병 선택 기준",
        "7. FAQ : 대표님들이 가장 많이 묻는 질문 10선",
    ]
    contents_html = "".join(
        f'<li style="margin-bottom:8px;">{item}</li>' for item in contents_items
    )
    market_split_rows = [
        (
            "공공(관급)",
            "예산 집행 구간에서 준비된 회사 중심으로 기회가 먼저 보이는 구간",
            f"{bidding_signal_label}와 실적 활용 계획이 정리된 회사가 유리합니다.",
        ),
        (
            "민간(주택·개발)",
            "사업성·금리·자금조달 변수 때문에 의사결정이 여전히 보수적인 구간",
            "무리한 확장보다 수익이 남는 수주와 현금흐름 방어가 우선입니다.",
        ),
        (
            "민간(비주택·리모델링)",
            "규모는 작아도 수요가 유지되는 영역이 남아 있는 구간",
            "빠른 회전이 가능한 공사, 기존 거래처, 확실한 수금 구조를 기준으로 선별 접근하는 편이 안전합니다.",
        ),
    ]
    market_split_html = "".join(
        (
            "<tr>"
            f'<td style="padding:12px; border:1px solid #dbeafe; vertical-align:top;"><strong>{sector}</strong></td>'
            f'<td style="padding:12px; border:1px solid #dbeafe; vertical-align:top;">{flow}</td>'
            f'<td style="padding:12px; border:1px solid #dbeafe; vertical-align:top;">{meaning}</td>'
            "</tr>"
        )
        for sector, flow, meaning in market_split_rows
    )
    variable_sections = [
        (
            "(1) 금리·자금조달",
            "금리와 자금조달 여건은 민간 발주와 직결됩니다. 대표 입장에서는 시장 분위기보다 금융 흐름과 보증 한도가 실제 수주 속도를 좌우할 수 있습니다.",
        ),
        (
            "(2) 공사비·원가",
            "이번 달 핵심은 단순 매출이 아니라 원가 방어입니다. 저가 수주가 누적되면 매출이 늘어도 현금흐름은 더 악화될 수 있으므로 손익 기준선을 먼저 고정해야 합니다.",
        ),
        (
            "(3) 인력·기술자 공백",
            "기술자와 실무 인력 공백은 등록 유지, 영업, 입찰 활용까지 한 번에 흔듭니다. 인력은 줄었다가 다시 채우기 어렵기 때문에 상반기에는 특히 선제 관리가 중요합니다.",
        ),
        (
            "(4) 준법·실태조사",
            f"{capital_signal_label}과 {risk_signal_label} 흐름이 강하다는 것은, 이제 서류만 맞추는 수준이 아니라 실제 유지 가능한 구조인지까지 보는 구간이라는 뜻입니다.",
        ),
        (
            "(5) 공공 발주·입찰 활용",
            f"{bidding_signal_label} 신호가 붙는 달에는 면허 취득만으로 끝나지 않습니다. 취득 이후 실적·입찰·협력사 등록 계획까지 이어져야 투자 효율이 살아납니다.",
        ),
    ]
    variable_sections_html = "".join(
        (
            f'<div style="margin-bottom:18px;">'
            f'<p style="margin:0 0 8px 0; font-size:18px; font-weight:800; color:#0f172a;">{title}</p>'
            f'<p style="margin:0; font-size:16px; color:#334155;">{desc}</p>'
            f'</div>'
        )
        for title, desc in variable_sections
    )
    strategy_items = [
        "<strong>시장 판단 기준부터 고정</strong> 막연한 기대보다 우리 회사가 지금 실행 가능한 조건, 자금 여력, 목표 시장을 먼저 정리합니다.",
        f"<strong>{primary_capital} 자료를 월초에 선점검</strong> 실질자본금, 진단자료, 출자좌수, 결산 흐름을 먼저 정리해야 의사결정이 밀리지 않습니다.",
        f"<strong>{primary_risk} 대응자료를 미리 준비</strong> 거래 직전보다 거래 이후 유지 리스크가 더 크게 작동하므로 선제 점검이 효율적입니다.",
        f"<strong>진입 방식을 미리 결정</strong> {primary_transfer}{_suffix_particle_wa_gwa(primary_transfer)} {primary_registration} 중 무엇이 일정·비용·리스크에 맞는지 기준표를 먼저 세웁니다.",
        "<strong>기술인력 공백을 막음</strong> 등록 유지와 영업, 입찰에 흔들림이 없도록 기술자·4대보험·상근 이슈를 같이 점검합니다.",
        f"<strong>취득 이후 활용 계획까지 설계</strong> {primary_bidding}에 연결될 실적, 관급 활용, 협력사 등록 계획이 있어야 면허 취득 효과가 살아납니다.",
        "<strong>대표 의사결정 메모를 한 장으로 정리</strong> 목표, 일정, 자금, 리스크, 활용 계획 5가지를 한 장으로 정리하면 내부 결재 속도가 빨라집니다.",
    ]
    strategy_html = "".join(
        f'<li style="margin-bottom:10px;">{item}</li>' for item in strategy_items
    )
    choice_rows = [
        (
            "신규등록",
            "깨끗한 시작, 장기 성장, 내부 기준을 처음부터 설계하고 싶은 경우",
            "자본금·기술인력·사무실·조합 출자 요건을 처음부터 설계해야 반려와 일정 지연을 줄일 수 있습니다.",
        ),
        (
            "양도양수",
            "빠른 진입, 실적 필요, 관급·협력사 등록을 서둘러야 하는 경우",
            "부외부채, 자본금 실질성, 기술자 승계, 행정 리스크를 계약 특약과 실사로 방어해야 합니다.",
        ),
        (
            "분할합병",
            "리스크 선별, 구조 재편, 실적 이전까지 함께 설계해야 하는 경우",
            "속도만 보고 접근하면 실패하기 쉽습니다. 기간, 비용, 세무·회계 구조를 처음부터 설계해야 의미가 있습니다.",
        ),
    ]
    choice_rows_html = "".join(
        (
            "<tr>"
            f'<td style="padding:12px; border:1px solid #dbeafe; vertical-align:top;"><strong>{name}</strong></td>'
            f'<td style="padding:12px; border:1px solid #dbeafe; vertical-align:top;">{fit}</td>'
            f'<td style="padding:12px; border:1px solid #dbeafe; vertical-align:top;">{check}</td>'
            "</tr>"
        )
        for name, fit, check in choice_rows
    )
    faq_items = [
        (
            f"Q1. {month_label}은 지금 들어가도 되는 시기인가요?",
            f"무조건 좋다·나쁘다가 아니라, {primary_capital}{_suffix_particle_wa_gwa(primary_capital)} {primary_risk}를 감당할 준비가 된 회사인지가 먼저입니다. 준비된 회사는 기회를 볼 수 있지만, 준비가 약하면 결정을 늦추는 편이 안전합니다.",
        ),
        (
            "Q2. 왜 문의는 느는데 현장 체감은 여전히 약한가요?",
            "문의 증가는 기대감의 회복일 수 있지만, 실제 실행은 자금·실사·리스크 검토를 거치면서 늦어집니다. 그래서 대표 체감은 늘 한 박자 늦게 따라오는 경우가 많습니다.",
        ),
        (
            "Q3. 양도양수와 신규등록 중 무엇을 먼저 봐야 하나요?",
            f"속도와 실적이 급하면 {primary_transfer}, 구조와 비용 통제가 중요하면 {primary_registration}이 맞을 가능성이 큽니다. 결국 일정·자금·목표시장 3가지를 같이 봐야 합니다.",
        ),
        (
            "Q4. 자금·기업진단 쪽에서 가장 자주 막히는 부분은 무엇인가요?",
            "실질자본금 설명 부족, 진단자료 누락, 출자좌수 준비 미흡이 가장 흔합니다. 이 영역은 뒤늦게 맞추려 할수록 일정이 길어집니다.",
        ),
        (
            "Q5. 실태조사 리스크가 왜 이렇게 중요해졌나요?",
            "요건을 맞췄는지보다 실제 유지 가능한 구조인지 보는 흐름이 강해졌기 때문입니다. 거래 직전보다 거래 이후 문제가 더 크게 터질 수 있어, 선제 점검 가치가 높습니다.",
        ),
        (
            "Q6. 시공능력평가와 입찰 활용까지 왜 같이 봐야 하나요?",
            "면허 취득이 끝이 아니라 이후 실적과 입찰 활용으로 이어져야 비용 대비 효과가 나기 때문입니다. 취득만 하고 활용 계획이 없으면 투자 효율이 떨어집니다.",
        ),
        (
            "Q7. 지금은 공공 쪽만 봐도 되나요?",
            "공공 기대감만으로 판단하면 실제 현금흐름과 체감 시장을 놓치기 쉽습니다. 민간 발주, 협력사 수요, 자금 집행 계획까지 같이 봐야 대표 판단이 현실적입니다.",
        ),
        (
            "Q8. 시장이 좋아진다면 왜 여전히 상담이 길어지나요?",
            "대표들이 단순 문의보다 실사 범위와 유지 리스크를 더 깊게 보기 시작했기 때문입니다. 그래서 상담 단계는 늘어도 실제 계약은 더 보수적으로 진행될 수 있습니다.",
        ),
        (
            "Q9. 양도양수 실사에서 가장 자주 놓치는 부분은 무엇인가요?",
            "재무 수치 자체보다 부외부채, 미확인 채무, 기술자 승계, 행정처분 이력처럼 거래 이후 바로 문제가 되는 부분을 놓치는 경우가 많습니다. 속도보다 실사 범위를 먼저 정해야 합니다.",
        ),
        (
            "Q10. 이번 달 대표가 가장 먼저 해야 할 한 가지는 무엇인가요?",
            "시장 분위기를 묻기 전에 우리 회사의 목표, 일정, 자금, 리스크 수용 범위를 먼저 정리하는 일입니다. 이 기준이 있어야 신규등록, 양도양수, 분할합병 중 어떤 선택이 맞는지 빨리 결정할 수 있습니다.",
        ),
    ]
    faq_html = "".join(
        (
            f'<div style="margin-bottom:18px;">'
            f'<p style="margin:0 0 8px 0; font-size:17px; font-weight:800; color:#0f172a;">{q}</p>'
            f'<p style="margin:0; font-size:16px; color:#334155;">{a}</p>'
            f"</div>"
        )
        for q, a in faq_items
    )

    body = f"""<div style="font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif; max-width:100%; margin:0 auto; color:#1f2937; line-height:1.8;">
  <div style="padding:52px 22px 40px; text-align:center;">
    <p style="margin:0; color:#1d4ed8; font-size:14px; font-weight:700; letter-spacing:1px;">SEOUL CONSTRUCTION INFO REPORT</p>
    <h1 style="margin:14px 0 0 0; color:#0f172a; font-size:31px; line-height:1.35; font-weight:800;">
      [{_yy(year)}년 {int(month)}월] 건설업 대표를 위한 건설업 전망 리포트<br>
      <span style="font-size:20px; font-weight:700; color:#1e293b;">{core_question}</span>
    </h1>
    <p style="margin:16px 0 0 0; color:#334155; font-size:16px; font-weight:800;">{today} 작성 · {month_label} 경영 판단 참고</p>
  </div>

  <div style="padding:30px 22px; border:1px solid #dbeafe; border-top:none; background:#f8fafc;">
    <p style="margin:0 0 14px 0; font-size:22px; font-weight:800; color:#0f172a;">{thesis}</p>
    <p style="margin:0 0 14px 0; font-size:16px; color:#334155;">안녕하세요. 서울건설정보입니다. 이번 리포트는 {month_label}에 포착된 시장 신호를 바탕으로, 건설업 대표가 이번 달에 무엇을 먼저 결정해야 하는지 정리한 월간 전망 리포트입니다.</p>
    <p style="margin:0; font-size:15px; color:#475569;">{focus_badges_html}</p>
  </div>

  <div style="padding:28px 22px; border:1px solid #e5e7eb; border-top:none; background:#ffffff;">
    <h2 style="margin:0 0 16px 0; font-size:24px; color:#0f172a; font-weight:800; border-bottom:3px solid #2563eb; padding-bottom:12px;">30초 핵심 요약</h2>
    <ul style="margin:0; padding-left:22px; font-size:17px; color:#334155;">{quick_summary_html}</ul>
    <div style="margin-top:16px; padding:16px 18px; border-radius:12px; background:#eff6ff; border:1px solid #bfdbfe; color:#1e3a8a; font-size:15px;">
      <strong>리포트 성격 안내</strong> 본 글은 {month_label} 현재 시장이 어떤 구조로 움직이는지 대표 관점에서 쉽게 이해하도록 정리한 정보성 콘텐츠입니다. 개별 법인의 재무·인력·실적·관급 참여 여부에 따라 체감은 달라질 수 있습니다.
    </div>
  </div>

  <div style="padding:28px 22px; border:1px solid #e5e7eb; border-top:none; background:#f8fbff;">
    <h2 style="margin:0 0 16px 0; font-size:24px; color:#0f172a; font-weight:800; border-bottom:3px solid #14b8a6; padding-bottom:12px;">CONTENTS (목차)</h2>
    <ol style="margin:0; padding-left:22px; font-size:16px; color:#334155;">{contents_html}</ol>
  </div>

  <div style="padding:28px 22px; border:1px solid #e5e7eb; border-top:none; background:#ffffff;">
    <h2 style="margin:0 0 16px 0; font-size:24px; color:#0f172a; font-weight:800; border-bottom:3px solid #0ea5e9; padding-bottom:12px;">1. {year}년 {month_label} 시장 한 문장 정리</h2>
    <p style="margin:0 0 14px 0; font-size:17px; color:#334155;">{thesis}</p>
    <p style="margin:0 0 14px 0; font-size:16px; color:#334155;">이번 달에는 <strong>{market_signal_label}</strong> 쪽에서 먼저 관심이 살아나지만, 실제 경영 판단은 <strong>{capital_signal_label}</strong>과 <strong>{risk_signal_label}</strong> 검토를 지나야 합니다. 따라서 {month_label}은 낙관보다 준비도가 수주·거래 성사율을 가르는 달로 보는 편이 맞습니다.</p>
    <p style="margin:0; font-size:16px; color:#334155;"><strong>핵심 포인트</strong> 전체 시장이 좋으냐 나쁘냐보다 중요한 것은, 우리 회사가 이번 달 필요한 자금·실사·면허 전략을 감당할 수 있는 구조인지입니다. 시장 분위기를 묻기 전에 우리 회사의 준비 수준을 먼저 정리해야 하는 달입니다.</p>
  </div>

  <div style="padding:28px 22px; border:1px solid #e5e7eb; border-top:none; background:#f8fbff;">
    <h2 style="margin:0 0 16px 0; font-size:24px; color:#0f172a; font-weight:800; border-bottom:3px solid #1d4ed8; padding-bottom:12px;">2. 공공 vs 민간: 돈이 도는 곳이 갈렸다</h2>
    <p style="margin:0 0 14px 0; font-size:16px; color:#334155;">{month_label} 시장에서 가장 자주 듣는 질문은 "기회는 보이는데 왜 우리 회사는 아직 체감이 약하냐"입니다. 답은 단순합니다. 기회가 먼저 보이는 곳과, 실제 우리 회사가 영업하는 곳이 다를 수 있기 때문입니다.</p>
    <div style="overflow-x:auto;">
      <table style="width:100%; border-collapse:collapse; font-size:15px; color:#334155;">
        <thead>
          <tr style="background:#ecfeff; color:#155e75;">
            <th style="padding:12px; border:1px solid #a5f3fc; text-align:left;">구분</th>
            <th style="padding:12px; border:1px solid #a5f3fc; text-align:left;">현재 흐름</th>
            <th style="padding:12px; border:1px solid #a5f3fc; text-align:left;">대표 관점 해석</th>
          </tr>
        </thead>
        <tbody>{market_split_html}</tbody>
      </table>
    </div>
  </div>

  <div style="padding:28px 22px; border:1px solid #e5e7eb; border-top:none; background:#ffffff;">
    <h2 style="margin:0 0 16px 0; font-size:24px; color:#0f172a; font-weight:800; border-bottom:3px solid #2563eb; padding-bottom:12px;">3. 현장 체감이 늦는 이유: 수주-착공-기성의 시간차</h2>
    <p style="margin:0 0 14px 0; font-size:16px; color:#334155;">건설업은 "뉴스에 수주가 움직인다"가 곧바로 "우리 회사 매출이 좋아진다"로 연결되지 않습니다. 일반적으로 수주(계약)에서 착공, 그리고 기성(매출 인식)까지는 시간차가 생깁니다.</p>
    <p style="margin:0 0 14px 0; font-size:16px; color:#334155;">그래서 지금은 분위기보다 현금흐름, 공정률, 수금 속도를 같이 봐야 합니다. 체감이 없다는 이유로 더 싼 가격에 수주를 밀어 넣으면, 오히려 공사비와 인건비 부담 때문에 현금흐름이 더 악화될 수 있습니다.</p>
    <p style="margin:0; font-size:16px; color:#334155;"><strong>대표가 놓치면 손해 보는 포인트</strong> 지금은 수주량보다 수익이 남는 수주가 우선입니다. 시장 회복 기대보다, 수익성과 현금 회수 구조를 먼저 체크해야 합니다.</p>
  </div>

  <div style="padding:28px 22px; border:1px solid #e5e7eb; border-top:none; background:#f8fbff;">
    <h2 style="margin:0 0 16px 0; font-size:24px; color:#0f172a; font-weight:800; border-bottom:3px solid #7c3aed; padding-bottom:12px;">4. {year}년 상반기 변수 5가지</h2>
    {variable_sections_html}
  </div>

  <div style="padding:28px 22px; border:1px solid #e5e7eb; border-top:none; background:#ffffff;">
    <h2 style="margin:0 0 16px 0; font-size:24px; color:#0f172a; font-weight:800; border-bottom:3px solid #0f766e; padding-bottom:12px;">5. 대표 실무 전략 7가지</h2>
    <ul style="margin:0; padding-left:22px; font-size:17px; color:#334155;">{strategy_html}</ul>
  </div>

  <div style="padding:28px 22px; border:1px solid #e5e7eb; border-top:none; background:#f8fbff;">
    <h2 style="margin:0 0 16px 0; font-size:24px; color:#0f172a; font-weight:800; border-bottom:3px solid #1d4ed8; padding-bottom:12px;">6. 면허/실적 전략: 양도양수·신규등록·분할합병 선택 기준</h2>
    <p style="margin:0 0 14px 0; font-size:16px; color:#334155;">{month_label} 시장에서는 비용보다 <strong>시간·리스크·목표시장</strong>으로 방향을 정하는 편이 효율적입니다. 아래 기준으로 보면 의사결정이 빨라집니다.</p>
    <div style="overflow-x:auto;">
      <table style="width:100%; border-collapse:collapse; font-size:15px; color:#334155;">
        <thead>
          <tr style="background:#ecfeff; color:#155e75;">
            <th style="padding:12px; border:1px solid #a5f3fc; text-align:left;">방식</th>
            <th style="padding:12px; border:1px solid #a5f3fc; text-align:left;">유리한 경우</th>
            <th style="padding:12px; border:1px solid #a5f3fc; text-align:left;">{month_label} 핵심 체크</th>
          </tr>
        </thead>
        <tbody>{choice_rows_html}</tbody>
      </table>
    </div>
  </div>

  <div style="padding:28px 22px; border:1px solid #e5e7eb; border-top:none; background:#ffffff;">
    <h2 style="margin:0 0 16px 0; font-size:24px; color:#0f172a; font-weight:800; border-bottom:3px solid #dc2626; padding-bottom:12px;">7. FAQ : 대표님들이 가장 많이 묻는 질문 10선</h2>
    {faq_html}
    <div style="margin-top:16px; padding:16px 18px; border-radius:12px; background:#fff7ed; border:1px solid #fed7aa; color:#7c2d12; font-size:15px;">
      <strong>안내</strong> 본 리포트는 시장 흐름과 실무 포인트를 요약한 참고 자료입니다. 최종 법무·세무 판단과 거래 조건은 계약 및 실사 이후 확정됩니다.
    </div>
  </div>

  <div style="margin-top:18px; padding:34px 22px; text-align:center;">
    <p style="font-size:24px; font-weight:800; color:#0f172a; margin:0 0 12px 0;">{month_label} 대응 방향을 바로 확인해 드립니다</p>
    <p style="font-size:17px; font-weight:700; color:#334155; margin:0 0 20px 0;">양도양수, 신규등록, 기업진단, 실태조사 이슈를 고객 상황에 맞춰 바로 정리해 드립니다.</p>
    <p style="margin:0 0 14px 0;">
      <a href="{kakao_url}" target="_blank" rel="noopener nofollow" style="display:inline-block; background:#FEE500; color:#191919; padding:14px 28px; text-decoration:none; font-size:18px; font-weight:800; border-radius:999px; margin:0 6px 8px 6px;">카카오톡 1:1 상담</a>
      <a href="tel:{phone_digits}" style="display:inline-block; background:#3182F6; color:#fff; padding:14px 28px; text-decoration:none; font-size:18px; font-weight:800; border-radius:999px; margin:0 6px 8px 6px;">전화 바로 연결</a>
    </p>
    <p style="font-size:15px; color:#1d4ed8; margin:8px 0 18px 0;">대표 상담: {phone}</p>
    <p style="margin:0;">
      <img src="{bizcard_image_url}" alt="서울건설정보 상담 명함" style="max-width:100%; height:auto; border:1px solid #334155;">
    </p>
  </div>
</div>
"""
    return subject, body


def _write_bundle(base_dir: Path, prefix: str, subject: str, body: str, payload: dict) -> dict:
    base_dir.mkdir(parents=True, exist_ok=True)
    subject_path = base_dir / f"{prefix}_subject.txt"
    body_path = base_dir / f"{prefix}_body.html"
    source_path = base_dir / f"{prefix}_source_snapshot.json"
    subject_path.write_text(subject + "\n", encoding="utf-8")
    body_path.write_text(body, encoding="utf-8")
    source_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "subject": str(subject_path),
        "body": str(body_path),
        "source_snapshot": str(source_path),
    }


def parse_args() -> argparse.Namespace:
    now = datetime.now()
    parser = argparse.ArgumentParser(description="Build a monthly market report HTML draft from live keyword snapshot.")
    parser.add_argument("--year", type=int, default=now.year)
    parser.add_argument("--month", type=int, default=now.month)
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-date", default="")
    parser.add_argument("--kakao-url", default=DEFAULT_KAKAO_URL)
    parser.add_argument("--phone", default=DEFAULT_PHONE)
    parser.add_argument("--bizcard-image-url", default=DEFAULT_BIZCARD_IMAGE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = _load_json(Path(args.report_json))
    run_date = datetime.strptime(args.run_date, "%Y-%m-%d").date() if str(args.run_date).strip() else date.today()
    subject, body = build_report_html(
        payload,
        year=int(args.year),
        month=int(args.month),
        run_date=run_date,
        kakao_url=str(args.kakao_url),
        phone=str(args.phone),
        bizcard_image_url=str(args.bizcard_image_url),
    )
    month_dir = Path(args.output_dir) / f"{int(args.year):04d}_{int(args.month):02d}"
    prefix = f"market_report_{int(args.year):04d}_{int(args.month):02d}"
    bundle = _write_bundle(month_dir, prefix, subject, body, payload)
    print(json.dumps(bundle, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
