#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CRITERIA_PATH = ROOT / "config" / "permit_registration_criteria_expanded.json"
DEFAULT_SYNONYM_PATH = ROOT / "config" / "permit_law_query_synonyms.json"
AUTOCOM_URL = "https://www.law.go.kr/search/autocom?colname=LS_NM_KO_AUTO"
LAW_BASE = "https://www.law.go.kr/법령/"

DEFAULT_SYNONYMS: Dict[str, List[str]] = {
    "01_01_03_P": ["의료법", "의료법 시행규칙"],
    "01_01_04_P": ["모자보건법", "모자보건법 시행규칙"],
    "01_02_01_P": ["의료기사 등에 관한 법률", "의료기사 등에 관한 법률 시행규칙"],
    "01_01_05_P": ["약사법", "약사법 시행규칙"],
    "01_01_06_P": ["약사법", "약사법 시행규칙"],
    "01_01_07_P": ["응급의료에 관한 법률", "응급의료에 관한 법률 시행규칙"],
    "01_01_08_P": ["의료법", "의료법 시행규칙"],
    "01_01_02_P": ["의료법", "의료법 시행규칙"],
    "01_01_10_P": ["의료유사업자에 관한 규칙", "의료법", "의료법 시행규칙", "의료법 시행령"],
    "01_02_04_P": ["의료기사 등에 관한 법률", "의료기사 등에 관한 법률 시행규칙"],
    "02_03_11_P": ["동물보호법", "동물보호법 시행규칙"],
    "02_03_01_P": ["수의사법", "수의사법 시행규칙"],
    "02_03_06_P": ["동물보호법", "동물보호법 시행규칙"],
    "02_03_08_P": ["동물보호법", "동물보호법 시행규칙"],
    "02_03_12_P": ["동물보호법", "동물보호법 시행규칙"],
    "02_03_10_P": ["동물보호법", "동물보호법 시행규칙"],
    "02_03_05_P": ["동물보호법", "동물보호법 시행규칙"],
    "02_03_09_P": ["동물보호법", "동물보호법 시행규칙"],
    "01_01_01_P": ["의료법", "의료법 시행규칙"],
    "07_22_02_P": ["건강기능식품에 관한 법률", "건강기능식품에 관한 법률 시행규칙"],
    "07_22_03_P": ["건강기능식품에 관한 법률", "건강기능식품에 관한 법률 시행규칙"],
    "07_22_05_P": ["축산물 위생관리법", "축산물 위생관리법 시행규칙"],
    "07_22_14_P": ["식품위생법 시행규칙"],
    "07_22_15_P": ["식품위생법 시행규칙"],
    "07_22_16_P": ["고압가스 안전관리법", "고압가스 안전관리법 시행규칙"],
    "07_22_20_P": ["축산물 위생관리법", "축산물 위생관리법 시행규칙"],
    "07_22_24_P": ["축산물 위생관리법", "축산물 위생관리법 시행규칙"],
    "09_30_04_P": ["공중위생관리법", "공중위생관리법 시행규칙"],
    "09_30_08_P": ["대기환경보전법", "대기환경보전법 시행규칙"],
    "09_30_09_P": ["대기환경보전법", "대기환경보전법 시행규칙"],
    "09_30_10_P": ["하수도법", "하수도법 시행규칙"],
    "09_28_06_P": ["석탄산업법", "석탄산업법 시행규칙"],
    "09_30_11_P": ["감염병의 예방 및 관리에 관한 법률", "감염병의 예방 및 관리에 관한 법률 시행규칙"],
    "09_30_12_P": ["물환경보전법", "물환경보전법 시행규칙"],
    "09_30_13_P": ["폐기물관리법", "폐기물관리법 시행규칙"],
    "09_28_10_P": ["도시가스사업법", "도시가스사업법 시행규칙"],
    "09_30_14_P": ["수도법", "수도법 시행규칙"],
    "09_30_15_P": ["환경관리 대행기관의 지정 등에 관한 규칙"],
    "09_30_17_P": ["환경분야 시험검사 등에 관한 법률", "환경분야 시험검사 등에 관한 법률 시행규칙"],
    "09_30_18_P": ["환경기술 및 환경산업 지원법", "환경기술 및 환경산업 지원법 시행규칙"],
    "09_27_01_P": ["목재의 지속가능한 이용에 관한 법률", "목재의 지속가능한 이용에 관한 법률 시행규칙"],
    "09_27_02_P": ["산림자원의 조성 및 관리에 관한 법률", "산림자원의 조성 및 관리에 관한 법률 시행규칙"],
    "09_27_03_P": ["목재의 지속가능한 이용에 관한 법률", "목재의 지속가능한 이용에 관한 법률 시행규칙"],
    "11_49_01_P": ["노인복지법", "노인복지법 시행규칙"],
    "04_16_01_P": ["인쇄문화산업 진흥법", "인쇄문화산업 진흥법 시행령"],
    "11_49_02_P": ["장사 등에 관한 법률", "장사 등에 관한 법률 시행규칙"],
    "04_17_01_P": ["출판문화산업 진흥법", "출판문화산업 진흥법 시행규칙"],
    "11_50_01_P": ["직업안정법", "직업안정법 시행규칙"],
    "11_50_02_P": ["직업안정법", "직업안정법 시행규칙"],
    "01_01_05_P": [
        "약국 및 의약품 등의 제조업ㆍ수입자와 판매업의 시설 기준령",
        "약국 및 의약품 등의 제조업ㆍ수입자와 판매업의 시설 기준규칙",
        "약사법 시행규칙",
    ],
    "01_01_06_P": [
        "약국 및 의약품 등의 제조업ㆍ수입자와 판매업의 시설 기준령",
        "약국 및 의약품 등의 제조업ㆍ수입자와 판매업의 시설 기준규칙",
        "약사법 시행규칙",
    ],
    "01_02_02_P": ["의료기기법 시행규칙", "의료기기법 시행령"],
    "01_02_03_P": ["의료기기법 시행규칙", "의료기기법 시행령"],
    "02_03_03_P": ["동물용 의약품등 취급규칙"],
    "02_03_04_P": ["동물용 의약품등 취급규칙"],
    "02_03_07_P": ["동물보호법 시행규칙"],
    "02_04_05_P": ["사료관리법 시행규칙"],
    "03_07_04_P": ["관광진흥법", "관광진흥법 시행령"],
    "03_07_02_P": ["관광진흥법 시행령", "관광진흥법"],
    "03_08_01_P": ["관광진흥법", "관광진흥법 시행령"],
    "03_08_03_P": ["문화체육관광부 및 국가유산청 소관 비영리법인의 설립 및 감독에 관한 규칙", "민법"],
    "03_11_08_P": ["농어촌정비법", "농어촌정비법 시행규칙"],
    "07_22_04_P": ["축산물 위생관리법", "축산물 위생관리법 시행규칙"],
    "07_22_09_P": ["식품위생법 시행규칙"],
    "07_24_02_P": ["식품위생법 시행규칙"],
    "07_24_03_P": ["식품위생법 시행규칙"],
    "08_25_01_P": ["유통산업발전법", "유통산업발전법 시행규칙"],
    "08_26_01_P": ["방문판매 등에 관한 법률", "방문판매 등에 관한 법률 시행규칙"],
    "08_26_03_P": ["방문판매 등에 관한 법률", "방문판매 등에 관한 법률 시행규칙"],
    "08_26_05_P": ["방문판매 등에 관한 법률", "방문판매 등에 관한 법률 시행규칙"],
    "09_30_05_P": ["건설폐기물의 재활용촉진에 관한 법률", "건설폐기물의 재활용촉진에 관한 법률 시행규칙"],
    "11_43_01_P": ["담배사업법 시행규칙"],
    "11_43_02_P": ["담배사업법 시행규칙"],
    "11_47_01_P": ["할부거래에 관한 법률 시행령", "할부거래에 관한 법률 시행규칙"],
    "11_50_01_P": ["직업안정법 시행규칙"],
    "11_50_02_P": ["직업안정법 시행규칙"],
    "10_33_01_P": ["체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령"],
    "10_33_02_P": ["체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령"],
    "10_39_01_P": ["체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령"],
    "10_42_01_P": ["체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령"],
}


TRAILING_SERVICE_SUFFIXES = (
    "판매업체",
    "처리시설관리업",
    "설계시공업",
    "유지관리업체",
    "직업소개소",
    "공연장업",
    "유흥음식점업",
    "연습장업",
    "시설업",
    "관리업",
    "처리업",
    "판매업",
    "제조업",
    "운반업",
    "수입업",
    "도매업",
    "소매업",
    "대행업",
    "공사업",
    "사업자",
    "사업장",
    "업체",
    "영업",
    "업소",
    "장업",
    "업",
)

LOW_SIGNAL_QUERY_VARIANTS = {
    "유료",
    "무료",
    "일반",
    "국제",
    "종합",
    "복합",
    "전문",
    "기타",
    "등록",
    "특정",
}

KEYWORD_LAW_HINTS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("관광", "숙박"), ("관광진흥법", "관광진흥법 시행령")),
    (("관광", "식당"), ("관광진흥법", "식품위생법")),
    (("관광", "유흥"), ("관광진흥법", "식품위생법")),
    (("관광",), ("관광진흥법", "관광진흥법 시행령")),
    (("게임물",), ("게임산업진흥에 관한 법률", "게임산업진흥에 관한 법률 시행령")),
    (("공연장",), ("공연법", "공연법 시행령")),
    (("체육시설",), ("체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령")),
    (("골프",), ("체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령")),
    (("당구장",), ("체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령")),
    (("가축",), ("축산법", "축산법 시행규칙")),
    (("도축",), ("축산물 위생관리법", "축산물 위생관리법 시행규칙")),
    (("부화",), ("축산법", "축산법 시행규칙")),
    (("종축",), ("축산법", "축산법 시행규칙")),
    (("식육",), ("축산물 위생관리법", "축산물 위생관리법 시행규칙")),
    (("식품",), ("식품위생법", "식품위생법 시행규칙")),
    (("주점",), ("식품위생법", "식품위생법 시행규칙")),
    (("계량기",), ("계량에 관한 법률", "계량에 관한 법률 시행규칙")),
    (("하수",), ("하수도법", "하수도법 시행규칙")),
    (("정화조",), ("하수도법", "하수도법 시행규칙")),
    (("오수",), ("하수도법", "하수도법 시행규칙")),
    (("급수",), ("수도법", "수도법 시행규칙")),
    (("위생관리",), ("공중위생관리법", "공중위생관리법 시행규칙")),
    (("환경전문공사업",), ("환경기술 및 환경산업 지원법", "환경기술 및 환경산업 지원법 시행규칙")),
    (("건설폐기물",), ("건설폐기물의 재활용촉진에 관한 법률", "건설폐기물의 재활용촉진에 관한 법률 시행규칙")),
    (("폐기물",), ("폐기물관리법", "폐기물관리법 시행규칙")),
    (("국제물류",), ("물류정책기본법", "물류정책기본법 시행령")),
    (("담배",), ("담배사업법", "담배사업법 시행규칙")),
    (("직업소개",), ("직업안정법", "직업안정법 시행규칙")),
    (("상조",), ("할부거래에 관한 법률", "할부거래에 관한 법률 시행령")),
    (("승강기",), ("승강기 안전관리법", "승강기 안전관리법 시행규칙")),
)

KEYWORD_LAW_HINTS += (
    (("게임",), ("게임산업진흥에 관한 법률", "게임산업진흥에 관한 법률 시행령")),
    (("비디오",), ("영화 및 비디오물의 진흥에 관한 법률", "영화 및 비디오물의 진흥에 관한 법률 시행령")),
    (("영화",), ("영화 및 비디오물의 진흥에 관한 법률", "영화 및 비디오물의 진흥에 관한 법률 시행령")),
    (("음반",), ("음악산업진흥에 관한 법률", "음악산업진흥에 관한 법률 시행규칙")),
    (("음악",), ("음악산업진흥에 관한 법률", "음악산업진흥에 관한 법률 시행규칙")),
    (("노래연습장",), ("음악산업진흥에 관한 법률", "음악산업진흥에 관한 법률 시행규칙")),
    (("숙박",), ("공중위생관리법", "공중위생관리법 시행규칙")),
    (("민박",), ("관광진흥법", "농어촌정비법")),
    (("한옥체험",), ("관광진흥법", "한옥 등 건축자산의 진흥에 관한 법률")),
    (("야영장",), ("관광진흥법", "관광진흥법 시행령")),
    (("휴양",), ("관광진흥법", "관광진흥법 시행령")),
    (("테마파크",), ("관광진흥법", "관광진흥법 시행령")),
    (("체육",), ("체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령")),
    (("골프장",), ("체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령")),
    (("수영",), ("체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령")),
    (("빙상",), ("체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령")),
    (("스키",), ("체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령")),
    (("승마",), ("체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령")),
    (("요트",), ("체육시설의 설치ㆍ이용에 관한 법률", "체육시설의 설치ㆍ이용에 관한 법률 시행령")),
    (("건강기능식품",), ("건강기능식품에 관한 법률", "건강기능식품에 관한 법률 시행규칙")),
    (("일반음식점",), ("식품위생법", "식품위생법 시행규칙")),
    (("휴게음식점",), ("식품위생법", "식품위생법 시행규칙")),
    (("제과점",), ("식품위생법", "식품위생법 시행규칙")),
    (("집단급식소",), ("식품위생법", "식품위생법 시행규칙")),
    (("위탁급식",), ("식품위생법", "식품위생법 시행규칙")),
    (("즉석판매",), ("식품위생법", "식품위생법 시행규칙")),
    (("유통전문판매",), ("식품위생법", "식품위생법 시행규칙")),
    (("식용얼음",), ("식품위생법", "식품위생법 시행규칙")),
    (("미용",), ("공중위생관리법", "공중위생관리법 시행규칙")),
    (("이용",), ("공중위생관리법", "공중위생관리법 시행규칙")),
    (("목욕장",), ("공중위생관리법", "공중위생관리법 시행규칙")),
    (("세탁",), ("공중위생관리법", "공중위생관리법 시행규칙")),
    (("다단계",), ("방문판매 등에 관한 법률", "방문판매 등에 관한 법률 시행령")),
    (("전화권유",), ("방문판매 등에 관한 법률", "방문판매 등에 관한 법률 시행령")),
    (("후원방문",), ("방문판매 등에 관한 법률", "방문판매 등에 관한 법률 시행령")),
    (("고압가스",), ("고압가스 안전관리법", "고압가스 안전관리법 시행규칙")),
    (("액화석유가스",), ("액화석유가스의 안전관리 및 사업법", "액화석유가스의 안전관리 및 사업법 시행규칙")),
    (("전력기술",), ("전력기술관리법", "전력기술관리법 시행규칙")),
    (("물류창고",), ("물류시설의 개발 및 운영에 관한 법률", "물류창고업 등록에 관한 규칙")),
)

UNRELATED_LAW_TITLE_PENALTIES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("직업소개",), ("도로",)),
    (("병원",), ("병원체자원",)),
    (("문화예술법인",), ("문화예술교육", "문화예술교육사")),
)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", str(value or "").strip().lower())


def _context_part_relevant(service_name: str, context_part: str) -> bool:
    service_key = _normalize_key(service_name)
    part_key = _normalize_key(context_part)
    if not service_key or not part_key:
        return False
    if part_key in service_key or service_key in part_key:
        return True
    for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", str(context_part or "")):
        token_key = _normalize_key(token)
        if len(token_key) < 2:
            continue
        if token_key in service_key:
            return True
    return False


def _context_text(
    service_name: str,
    *,
    group_name: str = "",
    group_description: str = "",
    major_name: str = "",
) -> str:
    parts: List[str] = [service_name]
    for extra in (group_name, group_description, major_name):
        text = _normalize_text(extra)
        if text and _context_part_relevant(service_name, text):
            parts.append(text)
    return _normalize_text(" ".join(parts))


def _is_high_signal_query_variant(query: str) -> bool:
    text = _normalize_text(query)
    if not text:
        return False
    if text in LOW_SIGNAL_QUERY_VARIANTS:
        return False
    return len(text) >= 2


def _run_powershell_base64(command: str, timeout_sec: int = 30) -> str:
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(10, int(timeout_sec)),
    )
    if proc.returncode != 0:
        detail = _normalize_text(proc.stderr) or _normalize_text(proc.stdout) or f"exit={proc.returncode}"
        raise RuntimeError(detail)
    payload = _normalize_text(proc.stdout)
    if not payload:
        return ""
    try:
        raw = base64.b64decode(payload.encode("ascii"), validate=True)
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _autocom_titles(keyword: str, *, outmax: int = 10) -> List[str]:
    key = str(keyword or "").replace("'", "''").strip()
    if not key:
        return []
    command = (
        "$ProgressPreference='SilentlyContinue'; "
        "$headers=@{'X-Requested-With'='XMLHttpRequest';'Referer'='https://www.law.go.kr/LSW/lsSc.do'}; "
        f"$body=@{{keyword='{key}';outmax='{max(1, int(outmax))}'}}; "
        f"$resp=Invoke-WebRequest -UseBasicParsing -Uri '{AUTOCOM_URL}' -Method POST -Headers $headers "
        "-Body $body -ContentType 'application/x-www-form-urlencoded; charset=UTF-8' -TimeoutSec 30; "
        "$txt=[string]$resp.Content; "
        "$bytes=[System.Text.Encoding]::UTF8.GetBytes($txt); "
        "[Convert]::ToBase64String($bytes)"
    )
    text = _run_powershell_base64(command, timeout_sec=35)
    if not text:
        return []
    parts = [re.sub(r"<[^>]+>", "", p).strip() for p in text.split("|")]
    titles: List[str] = []
    seen = set()
    for part in parts:
        if not part:
            continue
        if not any(token in part for token in ("법", "령", "규칙", "고시")):
            continue
        if part in seen:
            continue
        seen.add(part)
        titles.append(part)
    return titles


def _strip_service_suffixes(service_name: str) -> List[str]:
    text = _normalize_text(service_name)
    out: List[str] = []
    current = text
    for _ in range(4):
        matched = False
        for suffix in TRAILING_SERVICE_SUFFIXES:
            if current.endswith(suffix) and len(current) > len(suffix) + 1:
                current = _normalize_text(current[: -len(suffix)])
                if current and current not in out:
                    out.append(current)
                matched = True
                break
        if not matched:
            break
    return out


def _keyword_hint_queries(
    service_name: str,
    *,
    group_name: str = "",
    group_description: str = "",
    major_name: str = "",
) -> List[str]:
    base = _normalize_text(service_name)
    if not base:
        return []
    context = _context_text(
        service_name,
        group_name=group_name,
        group_description=group_description,
        major_name=major_name,
    )
    hints: List[str] = []
    for required_terms, law_queries in KEYWORD_LAW_HINTS:
        if all(term in context for term in required_terms):
            for law_query in law_queries:
                txt = _normalize_text(law_query)
                if txt and txt not in hints:
                    hints.append(txt)
    return hints


def _build_query_variants(
    service_name: str,
    *,
    service_code: str = "",
    synonyms: Dict[str, List[str]] | None = None,
    group_name: str = "",
    group_description: str = "",
    major_name: str = "",
) -> List[str]:
    base = _normalize_text(service_name)
    if not base:
        return []
    variants: List[str] = [base]
    code_key = _normalize_text(service_code).upper()
    if code_key and isinstance(synonyms, dict):
        for token in list(synonyms.get(code_key) or []):
            txt = _normalize_text(token)
            if txt and txt not in variants:
                variants.append(txt)
    compact = re.sub(r"[()（）\[\]·,./]", " ", base)
    compact = _normalize_text(compact)
    if compact and compact != base and compact not in variants and _is_high_signal_query_variant(compact):
        variants.append(compact)
    for part in [_normalize_text(x) for x in re.split(r"[/,]", base) if _normalize_text(x)]:
        if part not in variants and _is_high_signal_query_variant(part):
            variants.append(part)
    for stripped in _strip_service_suffixes(compact):
        if stripped and stripped not in variants and _is_high_signal_query_variant(stripped):
            variants.append(stripped)
    trimmed = compact
    for suffix in TRAILING_SERVICE_SUFFIXES:
        if trimmed.endswith(suffix) and len(trimmed) > len(suffix) + 1:
            trimmed = _normalize_text(trimmed[: -len(suffix)])
            break
    if len(trimmed) >= 2 and trimmed not in variants and _is_high_signal_query_variant(trimmed):
        variants.append(trimmed)
    for hint in _keyword_hint_queries(
        base,
        group_name=group_name,
        group_description=group_description,
        major_name=major_name,
    ):
        if hint not in variants:
            variants.append(hint)
    if len(compact) >= 4:
        short = compact[:4]
        if short not in variants and _is_high_signal_query_variant(short):
            variants.append(short)
    return variants[:8]


def _score_title(
    service_name: str,
    law_title: str,
    *,
    group_name: str = "",
    group_description: str = "",
    major_name: str = "",
    query_used: str = "",
) -> int:
    context = _context_text(
        service_name,
        group_name=group_name,
        group_description=group_description,
        major_name=major_name,
    )
    title = _normalize_text(law_title)
    title_key = _normalize_key(law_title)
    service_key = _normalize_key(service_name)
    query_key = _normalize_key(query_used)
    score = 0
    for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", context):
        token_key = _normalize_key(token)
        if token_key and token_key in title_key:
            score += min(5, len(token_key))
    if service_key and (service_key in title_key or title_key in service_key):
        score += 6
    if query_key and query_key == title_key:
        score += 8
    elif query_key and query_key in title_key:
        score += 4
    if title.endswith("법"):
        score += 4
    if "시행령" in title:
        score += 2
    if "시행규칙" in title:
        score += 1
    for service_terms, law_terms in UNRELATED_LAW_TITLE_PENALTIES:
        if all(term in context for term in service_terms) and any(term in title for term in law_terms):
            score -= 12
    return score


def _law_url(law_title: str) -> str:
    slug = re.sub(r"\s+", "", _normalize_text(law_title))
    return LAW_BASE + quote(slug, safe="")


def _looks_like_law_title(text: str) -> bool:
    title = _normalize_text(text)
    if not title:
        return False
    return title.endswith(("법", "법률", "시행령", "시행규칙", "규칙", "기준령", "고시"))


def _collect_candidates_for_service(
    service_name: str,
    *,
    service_code: str = "",
    synonyms: Dict[str, List[str]] | None = None,
    max_candidates: int = 3,
    group_name: str = "",
    group_description: str = "",
    major_name: str = "",
) -> List[Dict[str, Any]]:
    variants = _build_query_variants(
        service_name,
        service_code=service_code,
        synonyms=synonyms,
        group_name=group_name,
        group_description=group_description,
        major_name=major_name,
    )
    titles: List[Tuple[str, str]] = []
    seen_title = set()
    for query in variants:
        if _looks_like_law_title(query):
            norm_query = _normalize_text(query)
            if norm_query and norm_query not in seen_title:
                seen_title.add(norm_query)
                titles.append((norm_query, query))
        for title in _autocom_titles(query, outmax=10):
            norm = _normalize_text(title)
            if not norm or norm in seen_title:
                continue
            seen_title.add(norm)
            titles.append((norm, query))
    ranked = sorted(
        (
            {
                "law_title": title,
                "law_url": _law_url(title),
                "query_used": query,
                "score": _score_title(
                    service_name,
                    title,
                    group_name=group_name,
                    group_description=group_description,
                    major_name=major_name,
                    query_used=query,
                ),
            }
            for title, query in titles
        ),
        key=lambda x: (-int(x.get("score", 0)), str(x.get("law_title", ""))),
    )
    return ranked[: max(1, int(max_candidates))]


def _collect_candidates_batch(
    jobs: List[Dict[str, Any]],
    *,
    synonyms: Dict[str, List[str]] | None = None,
    max_candidates: int = 3,
    workers: int = 4,
    collector=None,
) -> List[Dict[str, Any]]:
    active_collector = collector or _collect_candidates_for_service
    normalized_jobs = [dict(job) for job in list(jobs or []) if isinstance(job, dict)]
    if not normalized_jobs:
        return []

    worker_count = max(1, int(workers or 1))

    def _run(job: Dict[str, Any]) -> Dict[str, Any]:
        code = _normalize_text(job.get("service_code"))
        service_name = _normalize_text(job.get("service_name"))
        major_name = _normalize_text(job.get("major_name"))
        group_name = _normalize_text(job.get("group_name"))
        group_description = _normalize_text(job.get("group_description"))
        try:
            candidates = active_collector(
                service_name,
                service_code=code,
                synonyms=synonyms,
                max_candidates=max(1, int(max_candidates)),
                major_name=major_name,
                group_name=group_name,
                group_description=group_description,
            )
            return {
                "service_code": code,
                "service_name": service_name,
                "candidates": list(candidates or []),
                "error": "",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "service_code": code,
                "service_name": service_name,
                "candidates": [],
                "error": str(exc),
            }

    if worker_count == 1 or len(normalized_jobs) == 1:
        return [_run(job) for job in normalized_jobs]

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        return list(executor.map(_run, normalized_jobs))


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _load_synonyms(path: Path) -> Dict[str, List[str]]:
    merged: Dict[str, List[str]] = {k: list(v) for k, v in DEFAULT_SYNONYMS.items()}
    loaded = _load_json(path)
    raw = loaded.get("service_code_queries") if isinstance(loaded, dict) else None
    if not isinstance(raw, dict):
        return merged
    for key, values in raw.items():
        code = _normalize_text(key).upper()
        if not code:
            continue
        if not isinstance(values, list):
            continue
        queries: List[str] = []
        for item in values:
            txt = _normalize_text(item)
            if txt:
                queries.append(txt)
        if queries:
            merged[code] = queries
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-collect law candidates for mapping batches.")
    parser.add_argument("--criteria", default=str(DEFAULT_CRITERIA_PATH))
    parser.add_argument("--output", default="", help="Optional output path. Default overwrites criteria.")
    parser.add_argument("--top-batches", type=int, default=3, help="How many top batches to process.")
    parser.add_argument("--max-candidates", type=int, default=3, help="Max candidates per service.")
    parser.add_argument("--min-score", type=int, default=3, help="Minimum top candidate score to mark as collected.")
    parser.add_argument(
        "--synonyms",
        default=str(DEFAULT_SYNONYM_PATH),
        help="optional service-code synonym JSON path",
    )
    parser.add_argument(
        "--only-status",
        default="",
        help="optional status filter(csv). ex: queued_law_mapping_no_hit,queued_law_mapping_low_confidence",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="parallel workers for service-level law candidate collection",
    )
    args = parser.parse_args()

    criteria_path = Path(str(args.criteria)).expanduser().resolve()
    output_path = Path(str(args.output)).expanduser().resolve() if str(args.output or "").strip() else criteria_path
    payload = _load_json(criteria_path)
    synonym_path = Path(str(args.synonyms)).expanduser().resolve() if str(args.synonyms or "").strip() else DEFAULT_SYNONYM_PATH
    synonyms = _load_synonyms(synonym_path)
    only_status = {s.strip() for s in str(args.only_status or "").split(",") if s.strip()}
    industries = list(payload.get("industries") or [])
    by_code: Dict[str, Dict[str, Any]] = {}
    for row in industries:
        if not isinstance(row, dict):
            continue
        code = _normalize_text(row.get("service_code"))
        if code:
            by_code[code] = row

    mapping_pipeline = dict(payload.get("mapping_pipeline") or {})
    batches = list(mapping_pipeline.get("batches") or [])
    selected = batches[: max(1, int(args.top_batches))]
    selected_ids = [str(batch.get("batch_id") or "") for batch in selected]
    selected_codes: List[str] = []
    for batch in selected:
        for code in list(batch.get("service_codes") or []):
            norm = _normalize_text(code)
            if norm:
                selected_codes.append(norm)

    jobs: List[Dict[str, Any]] = []
    for code in selected_codes:
        row = by_code.get(code)
        if row is None:
            continue
        status_now = _normalize_text(row.get("mapping_status"))
        if only_status and status_now not in only_status:
            continue
        service_name = _normalize_text(row.get("service_name"))
        if not service_name:
            continue
        jobs.append(
            {
                "service_code": code,
                "service_name": service_name,
                "major_name": _normalize_text(row.get("major_name")),
                "group_name": _normalize_text(row.get("group_name")),
                "group_description": _normalize_text(row.get("group_description")),
            }
        )

    target_total = len(jobs)
    processed = 0
    success = 0
    empty_hits = 0
    low_confidence = 0
    failures = 0
    results = _collect_candidates_batch(
        jobs,
        synonyms=synonyms,
        max_candidates=max(1, int(args.max_candidates)),
        workers=max(1, int(args.workers or 1)),
    )
    for item in results:
        code = _normalize_text(item.get("service_code"))
        row = by_code.get(code)
        if row is None:
            continue
        processed += 1
        error = _normalize_text(item.get("error"))
        candidates = list(item.get("candidates") or [])
        if error:
            failures += 1
            row["auto_law_candidates"] = []
            row["auto_collection_error"] = error
            row["mapping_status"] = "queued_law_mapping_failed"
            continue

        row["auto_collection_error"] = ""
        row["auto_law_candidates"] = candidates
        row["auto_collection_at"] = _now_iso()
        top_score = int((candidates[0] or {}).get("score") or 0) if candidates else 0
        if candidates and top_score >= max(0, int(args.min_score)):
            success += 1
            row["mapping_status"] = "candidate_collected"
            if str(row.get("collection_status") or "").strip() != "criteria_extracted":
                row["collection_status"] = "candidate_collected"
        elif candidates:
            low_confidence += 1
            row["mapping_status"] = "queued_law_mapping_low_confidence"
        else:
            empty_hits += 1
            row["mapping_status"] = "queued_law_mapping_no_hit"

    run_meta = {
        "run_at": _now_iso(),
        "selected_batch_ids": selected_ids,
        "service_target_total": target_total,
        "service_processed_total": processed,
        "success_total": success,
        "no_hit_total": empty_hits,
        "low_confidence_total": low_confidence,
        "failure_total": failures,
        "max_candidates": max(1, int(args.max_candidates)),
        "min_score": max(0, int(args.min_score)),
        "worker_count": max(1, int(args.workers or 1)),
        "only_status": sorted(only_status),
        "synonym_path": str(synonym_path),
    }
    runs = list(mapping_pipeline.get("auto_collection_runs") or [])
    runs.append(run_meta)
    mapping_pipeline["auto_collection_runs"] = runs[-20:]
    mapping_pipeline["last_auto_collection"] = run_meta
    payload["mapping_pipeline"] = mapping_pipeline
    payload["industries"] = industries

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "criteria_path": str(criteria_path),
                "output_path": str(output_path),
                "selected_batch_ids": selected_ids,
                "service_target_total": target_total,
                "service_processed_total": processed,
                "success_total": success,
                "no_hit_total": empty_hits,
                "low_confidence_total": low_confidence,
                "failure_total": failures,
                "worker_count": max(1, int(args.workers or 1)),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
