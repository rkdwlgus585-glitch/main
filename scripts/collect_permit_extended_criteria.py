from __future__ import annotations

import argparse
import base64
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from html import unescape
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, quote, unquote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import permit_diagnosis_calculator
from core_engine.permit_mapping_pipeline import apply_mapping_pipeline


DEFAULT_OUTPUT_PATH = ROOT / "config" / "permit_registration_criteria_expanded.json"
LAW_BASE = "https://www.law.go.kr"
ARTICLE_SELECTION_RULES_VERSION = 6

CRITERIA_KEYWORDS = {
    "office": ["사무실", "영업소", "사업장", "소유권", "사용권", "임대차"],
    "guarantee": ["보증", "영업보증금", "보증보험", "예치", "출자"],
    "insurance": ["보험", "손해배상", "배상책임", "책임보험"],
    "personnel_misc": ["자격", "경력", "교육", "상근", "결격", "경력증명", "면허"],
    "facility_misc": ["시설", "면적", "차량", "창고", "객실", "화장실", "취사", "전용공간"],
    "environment_safety": ["오수", "폐기물", "안전", "방지시설", "위생", "소방"],
    "document": ["신청서", "서류", "증명서", "사업계획", "첨부", "제출", "신고"],
    "operations": ["관리체계", "운영규정", "업무규정", "내부통제", "유지관리"],
}

CORE_REQUIREMENT_KEYWORDS = ("자본금", "기술인력", "기술자", "장비", "기계")
CAPITAL_REQUIREMENT_KEYWORDS = ("자본금", "출자금")
TECHNICAL_PERSONNEL_KEYWORDS = (
    "기술인력",
    "기술자",
    "기술능력",
    "기술경력",
    "전문인력",
    "기사",
    "산업기사",
    "기능사",
)
OTHER_REQUIREMENT_CATEGORY_LABELS = {
    "office": "office",
    "guarantee": "guarantee",
    "insurance": "insurance",
    "facility_misc": "facility_equipment",
    "environment_safety": "safety_environment",
    "document": "document",
    "operations": "operations",
}
OTHER_REQUIREMENT_RULE_LABELS = {
    "equipment_count": "equipment",
    "deposit_days": "deposit",
}
PRESERVED_PENDING_MAPPING_STATUSES = {
    "candidate_collected",
    "queued_law_mapping_low_confidence",
    "queued_law_mapping_no_hit",
    "queued_law_mapping_failed",
}
PRESERVED_MAPPING_PIPELINE_KEYS = (
    "auto_collection_runs",
    "last_auto_collection",
)
REGISTRATION_SUMMARY_KEYWORDS = (
    "등록기준",
    "등록 요건",
    "등록요건",
    "허가기준",
    "허가 기준",
    "시설기준",
    "시설 기준",
    "자본금",
    "기술인력",
    "기술자",
    "시설",
    "장비",
    "사무실",
    "면적",
    "보증",
    "보험",
    "결격",
    "교육",
    "서류",
    "신청",
)
ACCEPTABLE_CANDIDATE_TITLE_KEYWORDS = (
    "등록기준",
    "등록 요건",
    "등록요건",
    "설립허가",
    "설립 허가",
    "허가기준",
    "허가 기준",
    "시설기준",
    "시설 기준",
    "지정기준",
    "등록 세부기준",
    "세부기준",
    "설치기준",
    "설치 기준",
    "설비기준",
    "설비 기준",
    "시설 및 설비기준",
    "시설·설비기준",
    "배치기준",
    "배치 기준",
    "인력요건",
    "자격요건",
    "지정요건",
    "요건",
    "영업기준",
    "시설ㆍ기술",
    "시설·기술",
    "시설ㆍ장비",
    "시설·장비",
    "산정기준",
    "산정 기준",
    "산정의 기준",
    "작성기준",
    "작성 기준",
    "보관 및 운반 기준",
    "보관기준",
    "운반기준",
)
SOFT_CANDIDATE_TITLE_KEYWORDS = (
    "준수사항",
    "준수 사항",
    "업무 범위",
    "유통품질 관리기준",
    "유통품질관리기준",
    "품질관리체계의 기준",
)
FALLBACK_ACCEPTABLE_CANDIDATE_TITLE_KEYWORDS = (
    "준수사항",
    "준수 사항",
    "유통품질 관리기준",
    "유통품질관리기준",
    "품질관리체계의 기준",
    "시설 및 품질관리체계의 기준",
    "시설과 제조 및 품질관리체계의 기준",
)
BLOCKED_CANDIDATE_TITLE_KEYWORDS = (
    "과태료",
    "행정처분",
    "응시제한",
    "수수료",
    "벌칙",
    "시험",
    "과징금",
    "취소",
    "정지",
    "처분",
    "삭제",
)
GENERIC_REVIEW_BASIS_TITLES = {
    "신고",
    "등록",
    "허가",
    "준수사항",
    "준수 사항",
    "교육",
    "업무 범위",
    "업무한계",
}
STRONG_ARTICLE_TITLE_KEYWORDS = (
    "설립허가",
    "설립 허가",
    "개설등록",
    "등록절차",
    "등록 기준",
    "등록기준",
    "등록",
    "신고",
    "허가",
    "시설 기준",
    "시설기준",
)
WEAK_ARTICLE_TITLE_KEYWORDS = (
    "준수사항",
    "준수 사항",
    "교육",
    "관리의무",
    "업무 범위",
    "업무한계",
)
SOFT_BLOCKED_ARTICLE_TITLE_KEYWORDS = (
    "양수",
    "위탁",
    "센터",
    "등록시스템",
    "수신거부",
    "안전교육",
    "착수",
    "준공",
)
ARTICLE_MATCH_ALIAS_HINTS: Dict[str, List[str]] = {
    "03_06_02_P": ["공연장"],
    "03_08_03_P": ["비영리법인"],
    "08_26_03_P": ["방문판매업자등", "방문판매업자"],
    "11_47_01_P": ["선불식 할부거래업자", "선불식 할부거래업"],
}
UMBRELLA_CATEGORY_SUBTYPE_TERMS: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...]], ...] = (
    (
        ("관광사업", "관광사업자"),
        (
            "테마파크업",
            "관광호텔업",
            "수상관광호텔업",
            "한국전통호텔업",
            "가족호텔업",
            "호스텔업",
            "소형호텔업",
            "전문휴양업",
            "종합휴양업",
            "일반야영장업",
            "자동차야영장업",
            "한옥체험업",
            "관광유람선업",
            "카지노업",
        ),
    ),
    (
        ("공중위생영업",),
        ("숙박업", "목욕장업", "이용업", "미용업", "세탁업", "위생관리용역업"),
    ),
    (
        ("체육시설업", "등록 체육시설업"),
        ("골프장", "골프연습장", "당구장", "빙상장", "수영장", "승마장", "요트장", "스키장", "체력단련장"),
    ),
)
UNRELATED_BASIS_TITLE_TERMS: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...]], ...] = (
    (("문화예술법인", "비영리법인"), ("문화예술교육사", "교육사")),
)
ARTICLE_MATCH_CATEGORY_HINTS: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...]], ...] = (
    (("관광", "민박", "야영장", "휴양", "테마파크", "국제회의"), ("관광사업", "관광사업자")),
    (("숙박",), ("공중위생영업",)),
    (
        ("골프", "당구", "빙상", "수영", "스키", "승마", "요트", "체육", "무도", "썰매"),
        ("체육시설업", "등록 체육시설업"),
    ),
    (("계량기",), ("계량기 제조업",)),
    (("전력기술", "감리", "설계"), ("설계업", "감리업")),
)
ARTICLE_ACCEPTABLE_TITLE_KEYWORDS = (
    "설립허가",
    "설립 허가",
    "개설등록",
    "등록절차",
    "등록 기준",
    "등록기준",
    "등록",
    "신고",
    "시설 기준",
    "시설기준",
    "준수사항",
    "준수 사항",
    "교육",
    "관리의무",
    "업무 범위",
    "업무한계",
)
BLOCKED_ARTICLE_TITLE_KEYWORDS = (
    "목적",
    "정의",
    "구분",
    "행사",
    "벌칙",
    "과태료",
    "과징금",
    "행정처분",
    "영업정지",
    "시정조치",
    "국가시험",
    "응시자격",
    "결격사유",
    "면허",
    "등록대장",
    "재발급",
    "정정",
    "해산",
    "청산",
    "준용규정",
    "관할 관청",
    "보고의무",
    "조사",
    "취소",
    "금지",
    "심사비용",
    "산출기준",
    "실제연간요율",
)
INDUSTRY_NAME_SUFFIXES = (
    "업체",
    "사업자",
    "사업",
    "업소",
    "소개소",
    "법인",
    "기관",
    "센터",
    "시설",
    "판매업",
    "임대업",
    "수리업",
    "운반업",
    "가공업",
    "제조업",
    "처리업",
    "영업",
    "도매업",
    "도매상",
    "소매업",
    "유통전문판매업",
    "일반판매업",
    "업",
    "소",
)
SEMANTIC_INDUSTRY_SUFFIXES = (
    "판매업",
    "임대업",
    "수리업",
    "운반업",
    "가공업",
    "제조업",
    "처리업",
    "도매업",
    "도매상",
    "소매업",
    "유통전문판매업",
    "일반판매업",
    "수입업",
    "기획업",
    "주선업",
)
PRESERVED_CANDIDATE_EXTRACTION_FIELDS = (
    "candidate_basis_title",
    "candidate_criteria_lines",
    "candidate_criteria_count",
    "candidate_additional_criteria_lines",
    "candidate_criteria_status",
    "candidate_legal_basis",
    "candidate_law_fetch_meta",
    "candidate_raw_text_preview",
    "candidate_extracted_at",
)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _powershell_fetch_bytes(url: str, timeout_sec: int = 45) -> bytes:
    safe_url = str(url or "").replace("'", "''").strip()
    if not safe_url:
        raise ValueError("empty url")
    command = (
        "$ProgressPreference='SilentlyContinue'; "
        f"$resp=Invoke-WebRequest -UseBasicParsing '{safe_url}' -TimeoutSec {max(5, int(timeout_sec))}; "
        "if($null -ne $resp.RawContentStream){"
        "$ms=New-Object System.IO.MemoryStream; "
        "$resp.RawContentStream.Position=0; "
        "$resp.RawContentStream.CopyTo($ms); "
        "$bytes=$ms.ToArray();"
        "} else {"
        "$bytes=[System.Text.Encoding]::UTF8.GetBytes([string]$resp.Content);"
        "}; "
        "[Convert]::ToBase64String($bytes)"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        stderr = _compact(proc.stderr)
        stdout = _compact(proc.stdout)
        detail = stderr or stdout or f"exit={proc.returncode}"
        raise RuntimeError(f"powershell fetch failed: {detail}")
    encoded = _compact(proc.stdout)
    if not encoded:
        raise RuntimeError("empty fetch payload")
    return base64.b64decode(encoded.encode("ascii"), validate=True)


def _powershell_fetch_text(url: str, timeout_sec: int = 45) -> str:
    return _powershell_fetch_bytes(url, timeout_sec=timeout_sec).decode("utf-8", errors="replace")


def _post_form_text(url: str, data: Dict[str, Any], timeout_sec: int = 45) -> str:
    payload = {
        str(key): str(value)
        for key, value in dict(data or {}).items()
        if value is not None and str(value) != ""
    }
    if not payload:
        raise ValueError("empty post payload")
    encoded = urlencode(payload).encode("utf-8")
    request = Request(
        str(url or "").strip(),
        data=encoded,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urlopen(request, timeout=max(5, int(timeout_sec))) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _extract_law_iframe_url(html: str) -> str:
    src = ""
    doc = str(html or "")
    patterns = [
        r'<iframe[^>]+id="lawService"[^>]+src="([^"]+)"',
        r'<iframe[^>]+src="([^"]*lsInfoP\.do[^"]*)"',
        r"(?:src=|href=)['\"]([^'\"]*lsInfoP\.do\?[^'\"]+)['\"]",
    ]
    for pattern in patterns:
        m = re.search(pattern, doc, flags=re.I)
        if m:
            src = str(m.group(1) or "")
            break
    if not src:
        return ""
    src = src.replace("&amp;", "&")
    return urljoin(LAW_BASE, src)


def _contains_hangul_addr_error(html: str) -> bool:
    doc = str(html or "")
    return ("해당 한글주소명을 찾을 수 없습니다." in doc) or ("국가법령정보센터 | 오류페이지" in doc)


def _is_law_service_busy(html: str) -> bool:
    doc = str(html or "")
    return ("오류페이지" in doc) and ("서비스 이용에 불편" in doc)


def _normalize_law_title_slug(law_title: str) -> str:
    title = str(law_title or "").strip()
    if not title:
        return ""
    slug = re.sub(r"\s+", "", title)
    slug = re.sub(r"[\[\](){}<>]", "", slug)
    return slug


def _extract_law_slug_from_url(law_url: str) -> str:
    parsed = urlparse(str(law_url or "").strip())
    path = unquote(parsed.path or "")
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "법령":
        return parts[1]
    return ""


def _candidate_law_urls(law_url: str, law_title: str) -> List[str]:
    candidates: List[str] = []
    raw = str(law_url or "").strip()
    if raw:
        candidates.append(raw)

    slug_from_url = _extract_law_slug_from_url(raw)
    if slug_from_url:
        candidates.append(f"{LAW_BASE}/법령/{slug_from_url}")

    slug_from_title = _normalize_law_title_slug(law_title)
    if slug_from_title:
        candidates.append(f"{LAW_BASE}/법령/{slug_from_title}")

    dedup: List[str] = []
    seen = set()
    for candidate in candidates:
        norm = _compact(candidate)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        dedup.append(norm)
    return dedup


def _parse_qs_value(url: str, key: str, default: str = "") -> str:
    qs = parse_qs(urlparse(str(url or "")).query or "")
    vals = qs.get(key) or []
    if not vals:
        return default
    return str(vals[0] or default)


def _resolve_law_landing_and_iframe(law_url: str, law_title: str, timeout_sec: int = 50) -> Dict[str, str]:
    tried: List[str] = []
    for candidate in _candidate_law_urls(law_url, law_title):
        tried.append(candidate)
        try:
            if "lsInfoP.do" in candidate and "/LSW/" in candidate:
                iframe_url = urljoin(LAW_BASE, candidate)
                iframe_html = _powershell_fetch_text(iframe_url, timeout_sec=timeout_sec)
                if _compact(iframe_html):
                    return {
                        "landing_url": candidate,
                        "iframe_url": iframe_url,
                        "iframe_html": iframe_html,
                    }
                continue

            landing_html = _powershell_fetch_text(candidate, timeout_sec=timeout_sec)
            if _contains_hangul_addr_error(landing_html):
                continue
            iframe_url = _extract_law_iframe_url(landing_html)
            if not iframe_url:
                continue
            iframe_html = _powershell_fetch_text(iframe_url, timeout_sec=timeout_sec)
            if _compact(iframe_html):
                return {
                    "landing_url": candidate,
                    "iframe_url": iframe_url,
                    "iframe_html": iframe_html,
                }
        except Exception:
            continue

    return {
        "landing_url": "",
        "iframe_url": "",
        "iframe_html": "",
        "error": f"iframe_not_found tried={'; '.join(tried)}",
    }


def _build_byl_tree_url(iframe_url: str) -> str:
    lsi_seq = _parse_qs_value(iframe_url, "lsiSeq", "")
    chr_cls = _parse_qs_value(iframe_url, "chrClsCd", "010202")
    ef_yd = _parse_qs_value(iframe_url, "efYd", "")
    anc_yn = _parse_qs_value(iframe_url, "ancYnChk", "0")
    if not lsi_seq:
        return ""
    query = (
        f"lsiSeq={lsi_seq}"
        f"&section=By"
        f"&chrClsCd={chr_cls}"
        f"&efYd={ef_yd}"
        f"&joEfYd={ef_yd}"
        f"&ancYnChk={anc_yn}"
    )
    return f"{LAW_BASE}/LSW/joListTreeRInc.do?{query}"


def _build_article_tree_url(iframe_url: str) -> str:
    lsi_seq = _parse_qs_value(iframe_url, "lsiSeq", "")
    chr_cls = _parse_qs_value(iframe_url, "chrClsCd", "010202")
    ef_yd = _parse_qs_value(iframe_url, "efYd", "")
    anc_yn = _parse_qs_value(iframe_url, "ancYnChk", "0")
    if not lsi_seq:
        return ""
    query = (
        f"lsiSeq={lsi_seq}"
        f"&section=Jo"
        f"&chrClsCd={chr_cls}"
        f"&efYd={ef_yd}"
        f"&joEfYd={ef_yd}"
        f"&ancYnChk={anc_yn}"
    )
    return f"{LAW_BASE}/LSW/joListTreeRInc.do?{query}"


def _parse_byl_entries(byl_tree_json: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    raw = str(byl_tree_json or "").lstrip("\ufeff").strip()
    if not raw:
        return out
    try:
        items = json.loads(raw)
    except Exception:
        return out
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        byl_seq = str(item.get("bylSeq", "") or "").strip()
        title = _compact(item.get("bylTtl", "") or item.get("bylTtlStr", ""))
        if not byl_seq:
            continue
        out.append(
            {
                "byl_seq": byl_seq,
                "title": title,
                "byl_no": str(item.get("bylNo", "") or "").strip(),
                "byl_br_no": str(item.get("bylBrNo", "") or "").strip(),
            }
        )
    return out


def _parse_article_entries(article_tree_json: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    raw = str(article_tree_json or "").lstrip("\ufeff").strip()
    if not raw:
        return out
    try:
        items = json.loads(raw)
    except Exception:
        return out
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("joYn", "") or "") != "Y":
            continue
        jo_no = str(item.get("joNo", "") or "").strip()
        jo_br_no = str(item.get("joBrNo", "") or "").strip()
        title = _compact(item.get("joTtl", "") or item.get("joTtlStr", ""))
        if not jo_no or not title:
            continue
        out.append(
            {
                "jo_no": jo_no,
                "jo_br_no": jo_br_no or "00",
                "title": title,
            }
        )
    return out


def _parse_article_annex_hint(article_hint: str) -> Tuple[str, str]:
    article = str(article_hint or "")
    m = re.search(r"별표\s*([0-9]+)(?:\s*의\s*([0-9]+))?", article)
    if not m:
        return "", ""
    no = str(m.group(1) or "").zfill(4)
    br = str(m.group(2) or "0").zfill(2)
    return no, br


def _build_candidate_name_keys(industry_name: str, aliases: List[str]) -> List[str]:
    values: List[str] = []
    seen = set()

    def _add(text: str) -> None:
        key = permit_diagnosis_calculator._normalize_key(text)
        if len(key) < 2 or key in seen:
            return
        seen.add(key)
        values.append(key)

    def _seed(text: str) -> None:
        raw = str(text or "").strip()
        if not raw:
            return
        _add(raw)
        cleaned = re.sub(r"\([^)]*\)", " ", raw)
        for token in re.split(r"[\s,/·ㆍ]+", cleaned):
            token = token.strip()
            if not token:
                continue
            _add(token)
            for suffix in INDUSTRY_NAME_SUFFIXES:
                if token.endswith(suffix) and len(token) > len(suffix) + 1:
                    _add(token[: -len(suffix)])
        for suffix in INDUSTRY_NAME_SUFFIXES:
            if raw.endswith(suffix) and len(raw) > len(suffix) + 1:
                _add(raw[: -len(suffix)])
        for suffix in SEMANTIC_INDUSTRY_SUFFIXES:
            if raw.endswith(suffix):
                _add(suffix)

    _seed(industry_name)
    for alias in list(aliases or []):
        _seed(str(alias or ""))
    return values


def _name_key_match_score(key: str) -> int:
    normalized = permit_diagnosis_calculator._normalize_key(key)
    if not normalized:
        return 0
    for suffix in SEMANTIC_INDUSTRY_SUFFIXES:
        suffix_key = permit_diagnosis_calculator._normalize_key(suffix)
        if normalized == suffix_key or normalized.endswith(suffix_key):
            return 42 if len(normalized) >= 3 else 24
    return 26 if len(normalized) >= 6 else 12 if len(normalized) >= 4 else 6


def _alias_context_relevant(industry_name: str, alias: Any) -> bool:
    alias_key = permit_diagnosis_calculator._normalize_key(alias)
    industry_key = permit_diagnosis_calculator._normalize_key(industry_name)
    if not alias_key or not industry_key:
        return False
    if alias_key in industry_key or industry_key in alias_key:
        return True
    for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", str(alias or "")):
        token_key = permit_diagnosis_calculator._normalize_key(token)
        if token_key and token_key in industry_key:
            return True
    return False


def _normalized_name_variants(value: str) -> List[str]:
    key = permit_diagnosis_calculator._normalize_key(value)
    if not key:
        return []
    variants = {key}
    for suffix in (
        "사업자",
        "사업",
        "업자",
        "업소",
        "업",
        "시설업",
        "시설",
        "법인",
        "기관",
        "센터",
        "장",
        "소",
    ):
        suffix_key = permit_diagnosis_calculator._normalize_key(suffix)
        if suffix_key and key.endswith(suffix_key) and len(key) > len(suffix_key) + 1:
            variants.add(key[: -len(suffix_key)])
    return sorted(variants, key=len, reverse=True)


def _title_term_matches_name_keys(term: str, name_keys: List[str]) -> bool:
    term_variants = _normalized_name_variants(term)
    if not term_variants:
        return False
    for key in name_keys:
        key_variants = _normalized_name_variants(key)
        for term_variant in term_variants:
            for key_variant in key_variants:
                if term_variant and key_variant and (
                    term_variant in key_variant
                    or key_variant in term_variant
                ):
                    return True
    return False


def _specific_title_penalty(name_keys: List[str], title: str) -> int:
    penalty = 0
    for category_keys, subtype_terms in UMBRELLA_CATEGORY_SUBTYPE_TERMS:
        if not any(_title_term_matches_name_keys(category, name_keys) for category in category_keys):
            continue
        for subtype in subtype_terms:
            if subtype in title and not _title_term_matches_name_keys(subtype, name_keys):
                penalty -= 140
                break
    for required_keys, blocked_terms in UNRELATED_BASIS_TITLE_TERMS:
        if not any(_title_term_matches_name_keys(required, name_keys) for required in required_keys):
            continue
        if any(term in title for term in blocked_terms):
            penalty -= 180
    for association_term in ("중앙회", "협회"):
        if association_term in title and not _title_term_matches_name_keys(association_term, name_keys):
            penalty -= 180
    return penalty


def _build_candidate_aliases(row: Dict[str, Any], industry_name: str) -> List[str]:
    aliases: List[str] = []
    seen = set()

    def _append(value: Any) -> None:
        text = str(value or "").strip()
        if not text or text == industry_name or text in seen:
            return
        seen.add(text)
        aliases.append(text)

    _append(row.get("service_name"))
    for value in (row.get("group_name"), row.get("major_name")):
        if _alias_context_relevant(industry_name, value):
            _append(value)

    service_code = str(row.get("service_code", "") or "").strip().upper()
    for value in list(ARTICLE_MATCH_ALIAS_HINTS.get(service_code) or []):
        _append(value)
    service_name = str(row.get("service_name", "") or industry_name).strip()
    for required_terms, hint_aliases in ARTICLE_MATCH_CATEGORY_HINTS:
        if any(term in service_name for term in required_terms):
            for value in hint_aliases:
                _append(value)
    return aliases


def _match_article_name_keys(
    industry_name: str,
    aliases: List[str],
    title: str,
    article_text: str,
) -> List[str]:
    name_keys = _build_candidate_name_keys(industry_name, aliases)
    title_key = permit_diagnosis_calculator._normalize_key(title)
    text_key = permit_diagnosis_calculator._normalize_key(article_text)
    matched: List[str] = []
    seen = set()
    for key in name_keys:
        if not key or key in seen:
            continue
        if key in title_key or key in text_key:
            seen.add(key)
            matched.append(key)
    return matched


def _match_basis_name_keys(
    industry_name: str,
    aliases: List[str],
    title: str,
) -> List[str]:
    name_keys = _build_candidate_name_keys(industry_name, aliases)
    title_key = permit_diagnosis_calculator._normalize_key(title)
    matched: List[str] = []
    seen = set()
    for key in name_keys:
        if not key or key in seen:
            continue
        if key in title_key:
            seen.add(key)
            matched.append(key)
    return matched


def _extract_hidden_input_value(html: str, field_name: str) -> str:
    if not field_name:
        return ""
    doc = str(html or "")
    patterns = [
        rf'id="{re.escape(field_name)}"[^>]*value="([^"]*)"',
        rf'name="{re.escape(field_name)}"[^>]*value="([^"]*)"',
        rf'value="([^"]*)"[^>]*id="{re.escape(field_name)}"',
        rf"value='([^']*)'[^>]*id='{re.escape(field_name)}'",
    ]
    for pattern in patterns:
        match = re.search(pattern, doc, flags=re.I)
        if match:
            return str(match.group(1) or "").strip()
    return ""


def _pick_relevant_byl(
    entries: List[Dict[str, str]],
    industry_name: str,
    aliases: List[str],
    article_hint: str = "",
) -> Dict[str, str] | None:
    if not entries:
        return None
    name_keys = _build_candidate_name_keys(industry_name, aliases)
    hint_no, hint_br = _parse_article_annex_hint(article_hint)
    candidates = []
    for row in entries:
        title = str(row.get("title", "") or "")
        title_key = permit_diagnosis_calculator._normalize_key(title)
        score = 0
        row_no = str(row.get("byl_no", "") or "").zfill(4)
        row_br = str(row.get("byl_br_no", "") or "").zfill(2)
        if any(keyword in title for keyword in BLOCKED_CANDIDATE_TITLE_KEYWORDS):
            score -= 120
        if any(keyword in title for keyword in ACCEPTABLE_CANDIDATE_TITLE_KEYWORDS):
            score += 90
        if any(keyword in title for keyword in SOFT_CANDIDATE_TITLE_KEYWORDS):
            score += 36
        if "등록기준" in title:
            score += 60
        if "등록요건" in title or "등록 요건" in title:
            score += 45
        if "허가기준" in title or "허가 기준" in title:
            score += 42
        if "시설기준" in title or "시설 기준" in title:
            score += 34
        if "기준" in title:
            score += 8
        if "요건" in title:
            score += 14
        if "세부기준" in title:
            score += 20
        if "설치기준" in title or "설치 기준" in title:
            score += 18
        if "설비기준" in title or "설비 기준" in title:
            score += 18
        if "배치기준" in title or "배치 기준" in title:
            score += 16
        if "인력요건" in title or "자격요건" in title:
            score += 16
        if "지정요건" in title or "요건" in title:
            score += 14
        if "시설ㆍ기술" in title or "시설·기술" in title or "시설ㆍ장비" in title or "시설·장비" in title:
            score += 18
        if "산정기준" in title or "산정 기준" in title or "산정의 기준" in title:
            score += 12
        if "작성기준" in title or "작성 기준" in title:
            score += 12
        if "시설 및 인력 기준" in title or "시설과 제조 및 품질관리체계의 기준" in title:
            score += 22
        if "시설 및 품질관리체계의 기준" in title or "유통품질 관리기준" in title:
            score += 18
        if "준수사항" in title or "준수 사항" in title:
            score += 10
        if "업무 범위" in title:
            score += 8
        if hint_no and row_no == hint_no:
            score += 18
            if hint_br and row_br == hint_br:
                score += 8
        for key in name_keys:
            if key and key in title_key:
                score += _name_key_match_score(key)
        score += _specific_title_penalty(name_keys, title)
        if "기준" in title:
            score += 3
        if "삭제" in title:
            score -= 20
        candidates.append((score, row))
    candidates.sort(key=lambda x: x[0], reverse=True)
    best = candidates[0][1]
    if candidates[0][0] <= 0:
        for row in entries:
            title = str(row.get("title", "") or "")
            if any(keyword in title for keyword in ACCEPTABLE_CANDIDATE_TITLE_KEYWORDS):
                return row
        return entries[0]
    return best


def _pick_relevant_article(
    entries: List[Dict[str, str]],
    industry_name: str,
    aliases: List[str],
) -> Dict[str, str] | None:
    if not entries:
        return None
    name_keys = _build_candidate_name_keys(industry_name, aliases)
    entity_establishment_context = any(
        _title_term_matches_name_keys(term, name_keys) for term in ("법인", "비영리법인", "협회", "중앙회")
    )
    candidates = []
    for row in entries:
        title = str(row.get("title", "") or "")
        title_key = permit_diagnosis_calculator._normalize_key(title)
        strong_keyword = any(keyword in title for keyword in STRONG_ARTICLE_TITLE_KEYWORDS)
        weak_keyword = any(keyword in title for keyword in WEAK_ARTICLE_TITLE_KEYWORDS)
        score = 0
        matched_keys: List[str] = []
        if any(keyword in title for keyword in BLOCKED_ARTICLE_TITLE_KEYWORDS):
            score -= 120
        if any(keyword in title for keyword in SOFT_BLOCKED_ARTICLE_TITLE_KEYWORDS):
            score -= 60
        if "개설등록" in title:
            score += 90
        if entity_establishment_context and ("설립허가" in title or "설립 허가" in title):
            score += 88
        if "등록절차" in title:
            score += 84
        if "시설 기준" in title or "시설기준" in title:
            score += 76
        if "등록기준" in title or "등록 기준" in title:
            score += 76
        if entity_establishment_context and "허가" in title:
            score += 44
        if "등록" in title:
            score += 54
        if "신고" in title:
            score += 48
        if entity_establishment_context and "신청" in title:
            score += 18
        if "준수사항" in title or "준수 사항" in title:
            score += 16
        if "교육" in title:
            score += 8
        if "관리의무" in title:
            score += 10
        if "업무 범위" in title or "업무한계" in title:
            score += 8
        for key in name_keys:
            if key and key in title_key:
                matched_keys.append(key)
                score += _name_key_match_score(key)
        score += _specific_title_penalty(name_keys, title)
        if any(len(key) >= 6 for key in matched_keys):
            score += 72
        elif any(len(key) >= 4 for key in matched_keys):
            score += 38
        if len(matched_keys) >= 2:
            score += 18
        if matched_keys and not strong_keyword:
            score -= 28 if weak_keyword else 72
        candidates.append((score, row))
    candidates.sort(key=lambda item: item[0], reverse=True)
    if candidates and candidates[0][0] > 0:
        return candidates[0][1]
    for row in entries:
        title = str(row.get("title", "") or "")
        if any(keyword in title for keyword in ARTICLE_ACCEPTABLE_TITLE_KEYWORDS):
            return row
    return entries[0]


def _augment_candidate_laws(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    expanded: List[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def _append(item: Dict[str, Any]) -> None:
        title = str(item.get("law_title", "") or "").strip()
        url = str(item.get("law_url", "") or "").strip()
        key = (title, url)
        if not title or not url or key in seen:
            return
        seen.add(key)
        expanded.append(item)

    for candidate in list(candidates or []):
        current = dict(candidate)
        _append(current)
        title = str(current.get("law_title", "") or "").strip()
        score = int(current.get("score") or 0)
        if not title or "시행" in title or not title.endswith(("법", "법률")):
            continue
        for offset, suffix in ((1, " 시행규칙"), (2, " 시행령")):
            derived_title = f"{title}{suffix}"
            derived = dict(current)
            derived["law_title"] = derived_title
            derived["law_url"] = f"{LAW_BASE}/법령/{quote(derived_title)}"
            derived["score"] = max(score - offset, 0)
            derived["query_used"] = str(current.get("query_used", "") or title)
            _append(derived)
    return expanded


def _extract_pdf_fl_seq(byl_contents_html: str) -> str:
    m = re.search(r'id="pdfFlSeq"\s+name="pdfFlSeq"\s+value="(\d+)"', str(byl_contents_html or ""), flags=re.I)
    if m:
        return str(m.group(1))
    m2 = re.search(r"flDownload\.do\?flSeq=(\d+)", str(byl_contents_html or ""))
    if m2:
        return str(m2.group(1))
    return ""


def _download_pdf_bytes(pdf_fl_seq: str, timeout_sec: int = 60) -> bytes:
    if not str(pdf_fl_seq or "").isdigit():
        return b""
    url = f"{LAW_BASE}/LSW/flDownload.do?flSeq={pdf_fl_seq}"
    return _powershell_fetch_bytes(url, timeout_sec=timeout_sec)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes:
        return ""
    temp_path = ROOT / "tmp" / f"law_pdf_tmp_{datetime.now().strftime('%H%M%S%f')}.pdf"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_bytes(pdf_bytes)
    try:
        reader = PdfReader(str(temp_path))
        chunks = []
        for page in reader.pages:
            chunks.append(str(page.extract_text() or ""))
        return "\n".join(chunks)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _extract_industry_windows(text: str, industry_name: str, aliases: List[str], window: int = 420) -> List[str]:
    src = str(text or "")
    if not src:
        return []
    terms = [str(industry_name or "").strip()] + [str(x or "").strip() for x in list(aliases or [])]
    terms = [x for x in terms if x]
    snippets: List[str] = []
    for term in terms:
        for m in re.finditer(re.escape(term), src):
            lo = max(0, m.start() - window)
            hi = min(len(src), m.end() + window)
            part = src[lo:hi]
            if part:
                snippets.append(part)
    if not snippets:
        snippets = [src]
    dedup: List[str] = []
    seen = set()
    for s in snippets:
        key = _compact(s)[:300]
        if key in seen:
            continue
        seen.add(key)
        dedup.append(s)
    return dedup[:8]


def _line_category(line: str) -> str:
    src = str(line or "")
    for category, keywords in CRITERIA_KEYWORDS.items():
        if any(keyword in src for keyword in keywords):
            return category
    return "other"


def _is_core_requirement_line(line: str) -> bool:
    src = str(line or "")
    if not src:
        return False
    return any(keyword in src for keyword in CORE_REQUIREMENT_KEYWORDS)


def _extract_additional_criteria_lines(text: str, industry_name: str, aliases: List[str]) -> List[Dict[str, str]]:
    windows = _extract_industry_windows(text, industry_name, aliases)
    lines: List[Dict[str, str]] = []
    seen = set()
    for chunk in windows:
        normalized = str(chunk or "")
        normalized = re.sub(r"(?<!\d)(\d+\.)", r"\n\1", normalized)
        normalized = re.sub(r"([가-하]\.)", r"\n\1", normalized)
        raw_lines = re.split(r"[\n\r]+|[·•ㆍ]\s*|(?<=\.)\s+|(?<=;)\s+|(?<=\))\s+(?=[0-9가-힣])", normalized)
        for raw in raw_lines:
            line = _compact(raw)
            if len(line) < 6:
                continue
            if _is_core_requirement_line(line):
                # 추가 등록기준은 자본금/기술인력/장비 중심 문장은 제외한다.
                continue
            if not any(keyword in line for keys in CRITERIA_KEYWORDS.values() for keyword in keys):
                continue
            key = line[:240]
            if key in seen:
                continue
            seen.add(key)
            if len(line) > 280:
                line = f"{line[:277]}..."
            lines.append(
                {
                    "category": _line_category(line),
                    "text": line,
                }
            )
    return lines[:40]


def _extract_registration_summary_lines(text: str, industry_name: str, aliases: List[str]) -> List[Dict[str, str]]:
    windows = _extract_industry_windows(text, industry_name, aliases, window=560)
    lines: List[Dict[str, str]] = []
    seen = set()
    for chunk in windows:
        normalized = str(chunk or "")
        normalized = re.sub(r"(?<!\d)(\d+\.)", r"\n\1", normalized)
        normalized = re.sub(r"([가-힣]\.)", r"\n\1", normalized)
        raw_lines = re.split(r"[\n\r]+|[·ㆍ]\s*|(?<=\.)\s+|(?<=;)\s+|(?<=\))\s+(?=[0-9가-힣])", normalized)
        for raw in raw_lines:
            line = _compact(raw)
            if len(line) < 6:
                continue
            if not any(keyword in line for keyword in REGISTRATION_SUMMARY_KEYWORDS):
                continue
            key = line[:240]
            if key in seen:
                continue
            seen.add(key)
            if len(line) > 320:
                line = f"{line[:317]}..."
            category = "core_requirement" if _is_core_requirement_line(line) else _line_category(line)
            lines.append({"category": category, "text": line})
    return lines[:60]


def _is_candidate_basis_title_acceptable(title: str) -> bool:
    src = str(title or "").strip()
    if not src:
        return False
    if any(keyword in src for keyword in BLOCKED_CANDIDATE_TITLE_KEYWORDS):
        return False
    return any(keyword in src for keyword in ACCEPTABLE_CANDIDATE_TITLE_KEYWORDS) or any(
        keyword in src for keyword in FALLBACK_ACCEPTABLE_CANDIDATE_TITLE_KEYWORDS
    )


def _format_article_basis_title(jo_no: str, jo_br_no: str, title: str) -> str:
    base_title = str(title or "").strip()
    try:
        jo_no_num = int(str(jo_no or "0"))
        jo_br_no_num = int(str(jo_br_no or "0"))
    except Exception:
        return base_title
    label = f"제{jo_no_num}조"
    if jo_br_no_num > 0:
        label = f"{label}의{jo_br_no_num}"
    if not base_title:
        return label
    return f"{label}({base_title})"


def _dedupe_line_items(
    primary_lines: List[Dict[str, str]],
    secondary_lines: List[Dict[str, str]],
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    normalized_primary: List[Dict[str, str]] = []
    normalized_secondary: List[Dict[str, str]] = []
    seen_primary = set()
    seen_all = set()

    for item in list(primary_lines or []):
        text = _compact((item or {}).get("text", ""))
        if not text or text in seen_primary:
            continue
        seen_primary.add(text)
        seen_all.add(text)
        normalized_primary.append(
            {
                "category": str((item or {}).get("category", "") or "other"),
                "text": text,
            }
        )

    for item in list(secondary_lines or []):
        text = _compact((item or {}).get("text", ""))
        if not text or text in seen_all:
            continue
        seen_all.add(text)
        normalized_secondary.append(
            {
                "category": str((item or {}).get("category", "") or "other"),
                "text": text,
            }
        )

    return normalized_primary, normalized_secondary


def _normalized_basis_rows(row: Dict[str, Any]) -> List[Dict[str, str]]:
    rows = [dict(item) for item in list(row.get("legal_basis") or []) if isinstance(item, dict)]
    if rows:
        return rows
    rows = [dict(item) for item in list(row.get("candidate_legal_basis") or []) if isinstance(item, dict)]
    if rows:
        return rows
    fallback_rows: List[Dict[str, str]] = []
    for item in list(row.get("auto_law_candidates") or []):
        if not isinstance(item, dict):
            continue
        law_title = str(item.get("law_title", "") or "").strip()
        law_url = str(item.get("law_url", "") or "").strip()
        if not law_title and not law_url:
            continue
        fallback_rows.append(
            {
                "law_title": law_title,
                "article": "",
                "url": law_url,
            }
        )
    return fallback_rows


def _promote_display_fields(row: Dict[str, Any]) -> None:
    basis_rows = _normalized_basis_rows(row)
    if basis_rows:
        row["legal_basis"] = deepcopy(basis_rows)
        primary_basis = basis_rows[0]
        row["law_title"] = str(primary_basis.get("law_title", "") or "").strip()
        article = str(primary_basis.get("article", "") or "").strip()
        if not article:
            article = str(row.get("candidate_basis_title", "") or "").strip()
        row["legal_basis_title"] = article

    if bool(row.get("has_rule")):
        summary_lines = [dict(item) for item in list(row.get("pending_criteria_lines") or []) if isinstance(item, dict)]
        additional_lines = [dict(item) for item in list(row.get("additional_criteria_lines") or []) if isinstance(item, dict)]
        if summary_lines:
            row["criteria_summary"] = deepcopy(summary_lines)
        elif additional_lines:
            row["criteria_summary"] = deepcopy(additional_lines)
        if additional_lines:
            row["criteria_additional"] = deepcopy(additional_lines)
        row["criteria_source_type"] = "rule_pack" if (summary_lines or additional_lines) else "rule_catalog"
        row["status"] = str(row.get("collection_status", "") or "rule_linked")
        return

    candidate_status = str(row.get("candidate_criteria_status", "") or "").strip()
    candidate_summary = [dict(item) for item in list(row.get("candidate_criteria_lines") or []) if isinstance(item, dict)]
    candidate_additional = [
        dict(item) for item in list(row.get("candidate_additional_criteria_lines") or []) if isinstance(item, dict)
    ]
    if candidate_status == "candidate_criteria_extracted" or candidate_summary or candidate_additional:
        if candidate_summary:
            row["criteria_summary"] = deepcopy(candidate_summary)
        elif candidate_additional:
            row["criteria_summary"] = deepcopy(candidate_additional)
        if candidate_additional:
            row["criteria_additional"] = deepcopy(candidate_additional)
        fetch_meta = dict(row.get("candidate_law_fetch_meta") or {})
        row["criteria_source_type"] = str(fetch_meta.get("basis_type", "") or "").strip() or "candidate_pack"
        row["status"] = "candidate_criteria_extracted"
        return

    if basis_rows:
        row["criteria_source_type"] = str(row.get("criteria_source_type", "") or "").strip() or "law_candidate"
        row["status"] = str(row.get("mapping_status", "") or row.get("collection_status", "") or "candidate_collected")


def _build_quality_flags(row: Dict[str, Any]) -> List[str]:
    flags: List[str] = []
    has_rule = bool(row.get("has_rule"))
    profile = dict(row.get("registration_requirement_profile") or {})
    has_candidate_law = bool(list(row.get("auto_law_candidates") or []))
    candidate_status = str(row.get("candidate_criteria_status", "") or "").strip()
    basis_title = str(row.get("candidate_basis_title", "") or "").strip()
    criteria_count = int(row.get("candidate_criteria_count", 0) or 0)
    fetch_meta = dict(row.get("candidate_law_fetch_meta") or {})

    if str(profile.get("profile_source", "") or "").strip() == "manual_scope_override":
        flags.append("manual_scope_override")
    if has_rule:
        return flags
    if (not has_rule) and has_candidate_law and candidate_status != "candidate_criteria_extracted":
        flags.append("law_only")
    if candidate_status == "candidate_criteria_extracted":
        mapping_status = str(row.get("mapping_status", "") or "").strip()
        if mapping_status in {
            "queued_law_mapping_no_hit",
            "queued_law_mapping_low_confidence",
            "queued_law_mapping_failed",
        }:
            flags.append("stale_candidate_source")
        if criteria_count <= 1:
            flags.append("sparse_criteria")
        if basis_title in GENERIC_REVIEW_BASIS_TITLES:
            flags.append("generic_basis_title")
        if str(fetch_meta.get("basis_type", "") or "").strip() == "article_body" and not int(
            fetch_meta.get("article_name_match_count", 0) or 0
        ):
            flags.append("article_name_unmatched")
    return flags


def _coerce_positive_float(value: Any) -> float:
    try:
        number = float(value or 0)
    except Exception:
        return 0.0
    return number if number > 0 else 0.0


def _coerce_positive_int(value: Any) -> int:
    try:
        number = int(value or 0)
    except Exception:
        return 0
    return number if number > 0 else 0


def _evidence_lines(items: List[Dict[str, str]], *, predicate, limit: int = 3) -> List[str]:
    evidence: List[str] = []
    seen = set()
    for item in items:
        text = _compact((item or {}).get("text", ""))
        if not text or text in seen:
            continue
        if not predicate(text, str((item or {}).get("category", "") or "")):
            continue
        seen.add(text)
        evidence.append(text)
        if len(evidence) >= limit:
            break
    return evidence


def _build_requirement_profile(row: Dict[str, Any]) -> Dict[str, Any]:
    items = [
        dict(item)
        for item in list(row.get("criteria_summary") or []) + list(row.get("criteria_additional") or [])
        if isinstance(item, dict)
    ]
    requirements = dict(row.get("requirements") or {})
    capital_eok = _coerce_positive_float(requirements.get("capital_eok"))
    technicians_required = _coerce_positive_int(requirements.get("technicians"))
    equipment_count = _coerce_positive_int(requirements.get("equipment_count"))
    deposit_days = _coerce_positive_int(requirements.get("deposit_days"))

    capital_evidence = _evidence_lines(
        items,
        predicate=lambda text, _category: any(keyword in text for keyword in CAPITAL_REQUIREMENT_KEYWORDS),
    )
    technical_evidence = _evidence_lines(
        items,
        predicate=lambda text, _category: any(keyword in text for keyword in TECHNICAL_PERSONNEL_KEYWORDS),
    )
    other_evidence = _evidence_lines(
        items,
        predicate=lambda text, category: category in OTHER_REQUIREMENT_CATEGORY_LABELS
        and not any(keyword in text for keyword in CAPITAL_REQUIREMENT_KEYWORDS)
        and not any(keyword in text for keyword in TECHNICAL_PERSONNEL_KEYWORDS),
    )

    capital_required = capital_eok > 0 or bool(capital_evidence)
    technical_personnel_required = technicians_required > 0 or bool(technical_evidence)

    other_components: List[str] = []
    seen_components = set()

    def _add_component(label: str) -> None:
        if label and label not in seen_components:
            seen_components.add(label)
            other_components.append(label)

    if equipment_count > 0:
        _add_component(OTHER_REQUIREMENT_RULE_LABELS["equipment_count"])
    if deposit_days > 0:
        _add_component(OTHER_REQUIREMENT_RULE_LABELS["deposit_days"])
    for item in items:
        category = str((item or {}).get("category", "") or "")
        label = OTHER_REQUIREMENT_CATEGORY_LABELS.get(category, "")
        text = _compact((item or {}).get("text", ""))
        if not label or not text:
            continue
        if any(keyword in text for keyword in CAPITAL_REQUIREMENT_KEYWORDS):
            continue
        if any(keyword in text for keyword in TECHNICAL_PERSONNEL_KEYWORDS):
            continue
        _add_component(label)

    other_required = bool(other_components)
    profile_source = (
        "structured_requirements"
        if any((capital_eok > 0, technicians_required > 0, equipment_count > 0, deposit_days > 0))
        else "text_inference"
    )
    inferred_focus_candidate = (
        profile_source != "structured_requirements"
        and capital_required
        and technical_personnel_required
    )
    focus_target = (
        profile_source == "structured_requirements"
        and capital_required
        and technical_personnel_required
    )
    focus_target_with_other = focus_target and other_required
    if focus_target_with_other:
        focus_bucket = "capital_technical_other"
    elif focus_target:
        focus_bucket = "capital_technical"
    elif inferred_focus_candidate and other_required:
        focus_bucket = "inferred_capital_technical_other"
    elif inferred_focus_candidate:
        focus_bucket = "inferred_capital_technical"
    elif capital_required or technical_personnel_required:
        focus_bucket = "partial_core"
    elif other_required:
        focus_bucket = "other_only"
    else:
        focus_bucket = "none"

    return {
        "capital_required": capital_required,
        "capital_eok": capital_eok,
        "technical_personnel_required": technical_personnel_required,
        "technicians_required": technicians_required,
        "other_required": other_required,
        "other_components": other_components,
        "equipment_count_required": equipment_count,
        "deposit_days_required": deposit_days,
        "profile_source": profile_source,
        "inferred_focus_candidate": inferred_focus_candidate,
        "focus_target": focus_target,
        "focus_target_with_other": focus_target_with_other,
        "focus_bucket": focus_bucket,
        "capital_evidence": capital_evidence,
        "technical_personnel_evidence": technical_evidence,
        "other_evidence": other_evidence,
    }


def _build_profile_override_lookup(overrides_catalog: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for item in list((overrides_catalog or {}).get("profile_overrides") or []):
        if not isinstance(item, dict):
            continue
        service_code = str(item.get("service_code", "") or "").strip()
        if not service_code:
            continue
        lookup[service_code] = dict(item)
    return lookup


def _apply_manual_profile_override(
    service_code: str,
    profile: Dict[str, Any],
    override_lookup: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    override = dict(override_lookup.get(str(service_code or "").strip()) or {})
    if not override:
        return dict(profile or {})

    patched = dict(profile or {})
    profile_patch = dict(override.get("profile_patch") or {})
    for key, value in profile_patch.items():
        patched[key] = deepcopy(value)
    patched["profile_source"] = str(
        patched.get("profile_source") or profile_patch.get("profile_source") or "manual_scope_override"
    ).strip() or "manual_scope_override"
    action = str(override.get("action", "") or "").strip()
    reason = str(override.get("reason", "") or "").strip()
    if action:
        patched["override_action"] = action
    if reason:
        patched["override_reason"] = reason
    return patched


def _build_law_body_request_data(iframe_url: str, iframe_html: str) -> Dict[str, str]:
    return {
        "lsId": _extract_hidden_input_value(iframe_html, "lsId"),
        "lsiSeq": _parse_qs_value(iframe_url, "lsiSeq", "") or _extract_hidden_input_value(iframe_html, "lsiSeq"),
        "ancNo": _extract_hidden_input_value(iframe_html, "ancNo"),
        "ancYd": _extract_hidden_input_value(iframe_html, "ancYd"),
        "efYd": _parse_qs_value(iframe_url, "efYd", "") or _extract_hidden_input_value(iframe_html, "efYd"),
        "chrClsCd": _parse_qs_value(iframe_url, "chrClsCd", "010202")
        or _extract_hidden_input_value(iframe_html, "lsBdyChrCls"),
        "nwYn": _extract_hidden_input_value(iframe_html, "nwYn") or "Y",
        "ancYnChk": _parse_qs_value(iframe_url, "ancYnChk", "0") or _extract_hidden_input_value(iframe_html, "ancYnChk"),
        "efGubun": "Y",
        "nwJoYnInfo": "N",
    }


def _fetch_law_body_html(iframe_url: str, iframe_html: str, timeout_sec: int = 50) -> str:
    payload = _build_law_body_request_data(iframe_url, iframe_html)
    required = ("lsId", "lsiSeq", "ancNo", "ancYd", "efYd", "chrClsCd")
    if any(not payload.get(key) for key in required):
        return ""
    return _post_form_text(f"{LAW_BASE}/LSW/lsInfoR.do", payload, timeout_sec=timeout_sec)


def _article_anchor_name(jo_no: str, jo_br_no: str) -> str:
    try:
        jo_no_num = int(str(jo_no or "0"))
        jo_br_no_num = int(str(jo_br_no or "0"))
    except Exception:
        return ""
    return f"J{jo_no_num}:{jo_br_no_num}"


def _html_to_text(fragment: str) -> str:
    src = str(fragment or "")
    if not src:
        return ""
    src = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", src)
    src = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", src)
    src = re.sub(r"(?i)<br\s*/?>", "\n", src)
    src = re.sub(r"(?i)</p\s*>", "\n", src)
    src = re.sub(r"(?i)</div\s*>", "\n", src)
    src = re.sub(r"(?i)</li\s*>", "\n", src)
    src = re.sub(r"(?is)<[^>]+>", " ", src)
    src = unescape(src)
    src = re.sub(r"\r\n?", "\n", src)
    src = re.sub(r"[ \t]+", " ", src)
    src = re.sub(r"\n{2,}", "\n", src)
    return src.strip()


def _extract_article_body_text(body_html: str, jo_no: str, jo_br_no: str) -> str:
    anchor = _article_anchor_name(jo_no, jo_br_no)
    if not anchor:
        return ""
    doc = str(body_html or "")
    if not doc:
        return ""
    anchor_pattern = re.compile(
        rf'<a[^>]+(?:name|id)=["\']{re.escape(anchor)}["\'][^>]*></a>',
        flags=re.I,
    )
    match = anchor_pattern.search(doc)
    if not match:
        return ""
    next_pattern = re.compile(r'<a[^>]+(?:name|id)=["\']J\d+:\d+["\'][^>]*></a>', flags=re.I)
    next_match = next_pattern.search(doc, match.end())
    fragment = doc[match.start() : next_match.start() if next_match else len(doc)]
    return _html_to_text(fragment)


def _extract_candidate_from_article_body(
    *,
    service_code: str,
    industry_name: str,
    aliases: List[str],
    law_url: str,
    law_title: str,
    candidate: Dict[str, Any],
    law_context: Dict[str, str],
    timeout_sec: int,
) -> CandidateExtraction | None:
    iframe_url = str(law_context.get("iframe_url", "") or "")
    iframe_html = str(law_context.get("iframe_html", "") or "")
    article_tree_url = _build_article_tree_url(iframe_url)
    if not article_tree_url:
        return None
    article_tree_json = _powershell_fetch_text(article_tree_url, timeout_sec=timeout_sec)
    article_entries = _parse_article_entries(article_tree_json)
    if not article_entries:
        return None
    picked = _pick_relevant_article(article_entries, industry_name, aliases)
    if not picked:
        return None
    body_html = _fetch_law_body_html(iframe_url, iframe_html, timeout_sec=max(45, timeout_sec))
    if not _compact(body_html):
        return None
    selected_title = str(picked.get("title", "") or "").strip()
    article_text = _extract_article_body_text(
        body_html,
        str(picked.get("jo_no", "") or ""),
        str(picked.get("jo_br_no", "") or ""),
    )
    if not _compact(article_text):
        return None
    matched_name_keys = _match_article_name_keys(industry_name, aliases, selected_title, article_text)
    article_aliases = [alias for alias in list(aliases or []) if alias]
    article_aliases.append(selected_title)
    text_for_extraction = f"{selected_title}\n{article_text}"
    summary_lines = _extract_registration_summary_lines(text_for_extraction, industry_name, article_aliases)
    additional_lines = _extract_additional_criteria_lines(text_for_extraction, industry_name, article_aliases)
    summary_lines, additional_lines = _dedupe_line_items(summary_lines, additional_lines)
    if not summary_lines and not additional_lines:
        return None
    extracted_at = now_iso()
    basis_title = _format_article_basis_title(
        str(picked.get("jo_no", "") or ""),
        str(picked.get("jo_br_no", "") or ""),
        selected_title,
    )
    return CandidateExtraction(
        ok=True,
        service_code=service_code,
        industry_name=industry_name,
        data={
            "service_code": service_code,
            "candidate_criteria_status": "candidate_criteria_extracted",
            "candidate_criteria_lines": summary_lines,
            "candidate_criteria_count": len(summary_lines) + len(additional_lines),
            "candidate_additional_criteria_lines": additional_lines,
            "candidate_basis_title": basis_title,
            "candidate_legal_basis": [
                {
                    "law_title": law_title,
                    "article": basis_title,
                    "url": str(law_context.get("landing_url", "") or law_url),
                }
            ],
            "candidate_law_fetch_meta": {
                "law_url": law_url,
                "law_title": law_title,
                "query_used": str(candidate.get("query_used", "") or ""),
                "score": int(candidate.get("score") or 0),
                "resolved_landing_url": str(law_context.get("landing_url", "") or ""),
                "iframe_url": iframe_url,
                "article_tree_url": article_tree_url,
                "selected_article_no": str(picked.get("jo_no", "") or ""),
                "selected_article_br_no": str(picked.get("jo_br_no", "") or ""),
                "selected_article_title": selected_title,
                "article_name_match_count": len(matched_name_keys),
                "article_name_match_keys": matched_name_keys[:8],
                "article_selection_rules_version": ARTICLE_SELECTION_RULES_VERSION,
                "basis_type": "article_body",
                "body_html_length": len(body_html),
                "body_text_length": len(article_text),
                "extracted_at": extracted_at,
            },
            "candidate_raw_text_preview": _compact(text_for_extraction)[:5000],
            "candidate_extracted_at": extracted_at,
        },
    )


def _needs_candidate_reextraction(row: Dict[str, Any]) -> bool:
    if bool(row.get("has_rule")) or not list(row.get("auto_law_candidates") or []):
        return False
    if str(row.get("candidate_criteria_status", "") or "").strip() != "candidate_criteria_extracted":
        return True
    fetch_meta = dict(row.get("candidate_law_fetch_meta") or {})
    basis_title = str(row.get("candidate_basis_title", "") or "").strip()
    criteria_count = int(row.get("candidate_criteria_count", 0) or 0)
    current_candidates = [dict(item) for item in list(row.get("auto_law_candidates") or []) if isinstance(item, dict)]
    current_titles = {str(item.get("law_title", "") or "").strip() for item in current_candidates if item.get("law_title")}
    current_urls = {str(item.get("law_url", "") or "").strip() for item in current_candidates if item.get("law_url")}
    fetched_title = str(fetch_meta.get("law_title", "") or "").strip()
    fetched_url = str(fetch_meta.get("law_url", "") or "").strip()
    current_top = current_candidates[0] if current_candidates else {}
    current_top_title = str(current_top.get("law_title", "") or "").strip()
    current_top_url = str(current_top.get("law_url", "") or "").strip()
    if fetched_title and fetched_title not in current_titles:
        return True
    if fetched_url and fetched_url not in current_urls:
        return True
    if current_top_title and fetched_title and current_top_title != fetched_title:
        return True
    if current_top_url and fetched_url and current_top_url != fetched_url:
        return True
    if criteria_count <= 1:
        return True
    if str(fetch_meta.get("basis_type", "") or "").strip() == "article_body":
        if int(fetch_meta.get("article_selection_rules_version", 0) or 0) < ARTICLE_SELECTION_RULES_VERSION:
            return True
        if "article_name_match_count" not in fetch_meta:
            return True
        if int(fetch_meta.get("article_name_match_count", 0) or 0) <= 0:
            return True
        if basis_title and not basis_title.startswith("제"):
            return True
        return False
    title = str(fetch_meta.get("selected_byl_title", "") or basis_title or "").strip()
    return not _is_candidate_basis_title_acceptable(title)


@dataclass
class RuleExtraction:
    ok: bool
    rule_id: str
    industry_name: str
    data: Dict[str, Any]
    error: str = ""


@dataclass
class CandidateExtraction:
    ok: bool
    service_code: str
    industry_name: str
    data: Dict[str, Any]
    error: str = ""


def _score_candidate_extraction(extraction: CandidateExtraction) -> int:
    if not extraction.ok:
        return -100000
    data = dict(extraction.data or {})
    fetch_meta = dict(data.get("candidate_law_fetch_meta") or {})
    basis_title = str(data.get("candidate_basis_title", "") or "").strip()
    criteria_count = int(data.get("candidate_criteria_count", 0) or 0)
    basis_type = str(fetch_meta.get("basis_type", "") or "").strip()
    law_title = str(fetch_meta.get("law_title", "") or "").strip()
    query_used = str(fetch_meta.get("query_used", "") or "").strip()
    score = criteria_count * 14
    if basis_title.startswith("제"):
        score += 12
    if _is_candidate_basis_title_acceptable(basis_title):
        score += 110
    if any(keyword in basis_title for keyword in STRONG_ARTICLE_TITLE_KEYWORDS):
        score += 90
    if any(keyword in basis_title for keyword in WEAK_ARTICLE_TITLE_KEYWORDS):
        score += 16
    if any(keyword in basis_title for keyword in SOFT_BLOCKED_ARTICLE_TITLE_KEYWORDS):
        score -= 120
    if any(keyword in basis_title for keyword in BLOCKED_ARTICLE_TITLE_KEYWORDS):
        score -= 220
    if "시행규칙" in law_title:
        score += 18
    elif "시행령" in law_title:
        score += 10
    if permit_diagnosis_calculator._normalize_key(query_used) == permit_diagnosis_calculator._normalize_key(law_title):
        score += 30
    match_keys = [
        str(item or "").strip()
        for item in list(
            fetch_meta.get("basis_name_match_keys")
            or fetch_meta.get("article_name_match_keys")
            or []
        )
    ]
    match_count = int(
        fetch_meta.get("basis_name_match_count", 0)
        or fetch_meta.get("article_name_match_count", 0)
        or 0
    )
    score += min(120, match_count * 40)
    score += sum(_name_key_match_score(key) for key in match_keys[:3])
    score += _specific_title_penalty(
        _build_candidate_name_keys(extraction.industry_name, _build_candidate_aliases(data, extraction.industry_name)),
        basis_title,
    )
    if basis_type == "article_body":
        score += 30
        if any(len(key) >= 6 for key in match_keys):
            score += 36
        elif any(len(key) >= 4 for key in match_keys):
            score += 18
    else:
        score += 140
        if not match_count:
            score -= 60
    return score


def _extract_rule_criteria(rule: Dict[str, Any], timeout_sec: int = 50) -> RuleExtraction:
    rule_id = str(rule.get("rule_id", "") or "")
    industry_name = str(rule.get("industry_name", "") or "")
    aliases = list(rule.get("aliases") or [])
    legal_basis = list(rule.get("legal_basis") or [])
    if not legal_basis:
        return RuleExtraction(ok=False, rule_id=rule_id, industry_name=industry_name, data={}, error="missing_legal_basis")

    primary_basis = legal_basis[0]
    law_url = str(primary_basis.get("url", "") or "").strip()
    law_title = str(primary_basis.get("law_title", "") or "").strip()
    article_hint = str(primary_basis.get("article", "") or "").strip()
    if not law_url:
        return RuleExtraction(ok=False, rule_id=rule_id, industry_name=industry_name, data={}, error="missing_law_url")

    try:
        law_context = _resolve_law_landing_and_iframe(law_url, law_title, timeout_sec=timeout_sec)
        iframe_url = str(law_context.get("iframe_url", "") or "")
        if not iframe_url:
            error_detail = str(law_context.get("error", "") or "iframe_not_found")
            return RuleExtraction(ok=False, rule_id=rule_id, industry_name=industry_name, data={}, error=error_detail)

        law_main_html = str(law_context.get("iframe_html", "") or "")
        if _is_law_service_busy(law_main_html):
            return RuleExtraction(ok=False, rule_id=rule_id, industry_name=industry_name, data={}, error="law_service_busy")

        by_tree_url = _build_byl_tree_url(iframe_url)
        if not by_tree_url:
            return RuleExtraction(ok=False, rule_id=rule_id, industry_name=industry_name, data={}, error="byl_tree_url_missing")
        byl_tree_json = _powershell_fetch_text(by_tree_url, timeout_sec=timeout_sec)
        entries = _parse_byl_entries(byl_tree_json)
        if not entries:
            return RuleExtraction(ok=False, rule_id=rule_id, industry_name=industry_name, data={}, error="byl_entries_not_found")

        picked = _pick_relevant_byl(entries, industry_name, aliases, article_hint=article_hint)
        if not picked:
            return RuleExtraction(ok=False, rule_id=rule_id, industry_name=industry_name, data={}, error="byl_pick_failed")

        byl_seq = str(picked.get("byl_seq", "") or "")
        chr_cls = _parse_qs_value(iframe_url, "chrClsCd", "010202")
        byl_contents_url = f"{LAW_BASE}/LSW/lsBylContentsInfoR.do?bylSeq={byl_seq}&chrClsCd={chr_cls}"
        byl_contents_html = _powershell_fetch_text(byl_contents_url, timeout_sec=timeout_sec)
        pdf_fl_seq = _extract_pdf_fl_seq(byl_contents_html)
        if not pdf_fl_seq:
            return RuleExtraction(ok=False, rule_id=rule_id, industry_name=industry_name, data={}, error="pdf_fl_seq_not_found")

        pdf_bytes = _download_pdf_bytes(pdf_fl_seq, timeout_sec=max(60, timeout_sec))
        pdf_text = _extract_pdf_text(pdf_bytes)
        if not _compact(pdf_text):
            return RuleExtraction(ok=False, rule_id=rule_id, industry_name=industry_name, data={}, error="pdf_text_empty")

        extra_lines = _extract_additional_criteria_lines(pdf_text, industry_name, aliases)
        return RuleExtraction(
            ok=True,
            rule_id=rule_id,
            industry_name=industry_name,
            data={
                "rule_id": rule_id,
                "industry_name": industry_name,
                "aliases": aliases,
                "requirements": dict(rule.get("requirements") or {}),
                "legal_basis": legal_basis,
                "law_fetch_meta": {
                    "law_url": law_url,
                    "law_title": law_title,
                    "article_hint": article_hint,
                    "resolved_landing_url": str(law_context.get("landing_url", "") or ""),
                    "iframe_url": iframe_url,
                    "byl_tree_url": by_tree_url,
                    "selected_byl_seq": byl_seq,
                    "selected_byl_title": str(picked.get("title", "") or ""),
                    "selected_byl_no": str(picked.get("byl_no", "") or ""),
                    "selected_byl_br_no": str(picked.get("byl_br_no", "") or ""),
                    "byl_contents_url": byl_contents_url,
                    "pdf_fl_seq": pdf_fl_seq,
                    "pdf_url": f"{LAW_BASE}/LSW/flDownload.do?flSeq={pdf_fl_seq}",
                    "extracted_at": now_iso(),
                    "pdf_text_length": len(pdf_text),
                },
                "additional_criteria_lines": extra_lines,
                "raw_text_preview": _compact(pdf_text)[:5000],
            },
        )
    except Exception as exc:  # noqa: BLE001
        return RuleExtraction(
            ok=False,
            rule_id=rule_id,
            industry_name=industry_name,
            data={},
            error=str(exc),
        )


def _extract_candidate_criteria(row: Dict[str, Any], timeout_sec: int = 50) -> CandidateExtraction:
    service_code = str(row.get("service_code", "") or "")
    industry_name = str(row.get("service_name", "") or "")
    aliases = _build_candidate_aliases(row, industry_name)
    candidates = [dict(item) for item in list(row.get("auto_law_candidates") or []) if isinstance(item, dict)]
    if not candidates:
        return CandidateExtraction(
            ok=False,
            service_code=service_code,
            industry_name=industry_name,
            data={},
            error="candidate_missing",
        )

    last_error = "candidate_extract_failed"
    augmented_candidates = _augment_candidate_laws(candidates)
    best_extraction: CandidateExtraction | None = None
    best_extraction_score = -100000
    best_fallback: CandidateExtraction | None = None
    best_fallback_score = -100000
    for candidate in augmented_candidates[:8]:
        law_url = str(candidate.get("law_url", "") or "").strip()
        law_title = str(candidate.get("law_title", "") or "").strip()
        if not law_url or not law_title:
            continue
        try:
            law_context = _resolve_law_landing_and_iframe(law_url, law_title, timeout_sec=timeout_sec)
            iframe_url = str(law_context.get("iframe_url", "") or "")
            if not iframe_url:
                last_error = str(law_context.get("error", "") or "iframe_not_found")
                continue

            law_main_html = str(law_context.get("iframe_html", "") or "")
            if _is_law_service_busy(law_main_html):
                last_error = "law_service_busy"
                continue

            by_tree_url = _build_byl_tree_url(iframe_url)
            if not by_tree_url:
                last_error = "byl_tree_url_missing"
                continue
            byl_tree_json = _powershell_fetch_text(by_tree_url, timeout_sec=timeout_sec)
            entries = _parse_byl_entries(byl_tree_json)
            if not entries:
                fallback = _extract_candidate_from_article_body(
                    service_code=service_code,
                    industry_name=industry_name,
                    aliases=aliases,
                    law_url=law_url,
                    law_title=law_title,
                    candidate=candidate,
                    law_context=law_context,
                    timeout_sec=timeout_sec,
                )
                if fallback:
                    fallback_score = _score_candidate_extraction(fallback)
                    if fallback_score > best_fallback_score:
                        best_fallback = fallback
                        best_fallback_score = fallback_score
                    if fallback_score > best_extraction_score:
                        best_extraction = fallback
                        best_extraction_score = fallback_score
                last_error = "byl_entries_not_found"
                continue

            picked = _pick_relevant_byl(entries, industry_name, aliases, article_hint="")
            if not picked:
                fallback = _extract_candidate_from_article_body(
                    service_code=service_code,
                    industry_name=industry_name,
                    aliases=aliases,
                    law_url=law_url,
                    law_title=law_title,
                    candidate=candidate,
                    law_context=law_context,
                    timeout_sec=timeout_sec,
                )
                if fallback:
                    fallback_score = _score_candidate_extraction(fallback)
                    if fallback_score > best_fallback_score:
                        best_fallback = fallback
                        best_fallback_score = fallback_score
                    if fallback_score > best_extraction_score:
                        best_extraction = fallback
                        best_extraction_score = fallback_score
                last_error = "byl_pick_failed"
                continue
            selected_byl_title = str(picked.get("title", "") or "")
            if not _is_candidate_basis_title_acceptable(selected_byl_title):
                fallback = _extract_candidate_from_article_body(
                    service_code=service_code,
                    industry_name=industry_name,
                    aliases=aliases,
                    law_url=law_url,
                    law_title=law_title,
                    candidate=candidate,
                    law_context=law_context,
                    timeout_sec=timeout_sec,
                )
                if fallback:
                    fallback_score = _score_candidate_extraction(fallback)
                    if fallback_score > best_fallback_score:
                        best_fallback = fallback
                        best_fallback_score = fallback_score
                    if fallback_score > best_extraction_score:
                        best_extraction = fallback
                        best_extraction_score = fallback_score
                last_error = f"candidate_basis_not_specific:{selected_byl_title}"
                continue

            byl_seq = str(picked.get("byl_seq", "") or "")
            chr_cls = _parse_qs_value(iframe_url, "chrClsCd", "010202")
            byl_contents_url = f"{LAW_BASE}/LSW/lsBylContentsInfoR.do?bylSeq={byl_seq}&chrClsCd={chr_cls}"
            byl_contents_html = _powershell_fetch_text(byl_contents_url, timeout_sec=timeout_sec)
            pdf_fl_seq = _extract_pdf_fl_seq(byl_contents_html)
            if not pdf_fl_seq:
                last_error = "pdf_fl_seq_not_found"
                continue

            pdf_bytes = _download_pdf_bytes(pdf_fl_seq, timeout_sec=max(60, timeout_sec))
            pdf_text = _extract_pdf_text(pdf_bytes)
            if not _compact(pdf_text):
                last_error = "pdf_text_empty"
                continue

            summary_lines = _extract_registration_summary_lines(pdf_text, industry_name, aliases)
            additional_lines = _extract_additional_criteria_lines(pdf_text, industry_name, aliases)
            summary_lines, additional_lines = _dedupe_line_items(summary_lines, additional_lines)
            if not summary_lines and not additional_lines:
                last_error = "criteria_lines_empty"
                continue

            extracted_at = now_iso()
            basis_name_match_keys = _match_basis_name_keys(industry_name, aliases, selected_byl_title)
            bylaw_extraction = CandidateExtraction(
                ok=True,
                service_code=service_code,
                industry_name=industry_name,
                data={
                    "service_code": service_code,
                    "candidate_criteria_status": "candidate_criteria_extracted",
                    "candidate_criteria_lines": summary_lines,
                    "candidate_criteria_count": len(summary_lines) + len(additional_lines),
                    "candidate_additional_criteria_lines": additional_lines,
                    "candidate_basis_title": selected_byl_title.strip(),
                    "candidate_legal_basis": [
                        {
                            "law_title": law_title,
                            "article": selected_byl_title.strip(),
                            "url": str(law_context.get("landing_url", "") or law_url),
                        }
                    ],
                    "candidate_law_fetch_meta": {
                        "law_url": law_url,
                        "law_title": law_title,
                        "query_used": str(candidate.get("query_used", "") or ""),
                        "score": int(candidate.get("score") or 0),
                        "basis_name_match_count": len(basis_name_match_keys),
                        "basis_name_match_keys": basis_name_match_keys[:8],
                        "resolved_landing_url": str(law_context.get("landing_url", "") or ""),
                        "iframe_url": iframe_url,
                        "byl_tree_url": by_tree_url,
                        "selected_byl_seq": byl_seq,
                        "selected_byl_title": selected_byl_title,
                        "selected_byl_no": str(picked.get("byl_no", "") or ""),
                        "selected_byl_br_no": str(picked.get("byl_br_no", "") or ""),
                        "byl_contents_url": byl_contents_url,
                        "pdf_fl_seq": pdf_fl_seq,
                        "pdf_url": f"{LAW_BASE}/LSW/flDownload.do?flSeq={pdf_fl_seq}",
                        "extracted_at": extracted_at,
                        "pdf_text_length": len(pdf_text),
                    },
                    "candidate_raw_text_preview": _compact(pdf_text)[:5000],
                    "candidate_extracted_at": extracted_at,
                },
            )
            extraction_score = _score_candidate_extraction(bylaw_extraction)
            if extraction_score > best_extraction_score:
                best_extraction = bylaw_extraction
                best_extraction_score = extraction_score
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            continue

    if best_extraction:
        return best_extraction
    if best_fallback:
        return best_fallback

    return CandidateExtraction(
        ok=False,
        service_code=service_code,
        industry_name=industry_name,
        data={},
        error=last_error,
    )


def _extract_rule_pack_batch(
    ordered_rules: List[Dict[str, Any]],
    *,
    timeout_sec: int = 50,
    workers: int = 4,
    extractor=None,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, str]]]:
    active_extractor = extractor or _extract_rule_criteria
    rules = [dict(rule) for rule in list(ordered_rules or []) if isinstance(rule, dict)]
    if not rules:
        return {}, []

    worker_count = max(1, int(workers or 1))

    def _run(rule: Dict[str, Any]) -> RuleExtraction:
        return active_extractor(rule, timeout_sec=timeout_sec)

    if worker_count == 1 or len(rules) == 1:
        results = [_run(rule) for rule in rules]
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            results = list(executor.map(_run, rules))

    packs: Dict[str, Dict[str, Any]] = {}
    extraction_errors: List[Dict[str, str]] = []
    for result in results:
        if result.ok:
            packs[result.rule_id] = result.data
        else:
            extraction_errors.append(
                {
                    "rule_id": result.rule_id,
                    "industry_name": result.industry_name,
                    "error": result.error,
                }
            )
    return packs, extraction_errors


def _extract_candidate_pack_batch(
    candidate_rows: List[Dict[str, Any]],
    *,
    timeout_sec: int = 50,
    workers: int = 4,
    extractor=None,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, str]]]:
    active_extractor = extractor or _extract_candidate_criteria
    rows = [dict(row) for row in list(candidate_rows or []) if isinstance(row, dict)]
    if not rows:
        return {}, []

    worker_count = max(1, int(workers or 1))

    def _run(row: Dict[str, Any]) -> CandidateExtraction:
        return active_extractor(row, timeout_sec=timeout_sec)

    if worker_count == 1 or len(rows) == 1:
        results = [_run(row) for row in rows]
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            results = list(executor.map(_run, rows))

    packs: Dict[str, Dict[str, Any]] = {}
    extraction_errors: List[Dict[str, str]] = []
    for result in results:
        if result.ok:
            packs[result.service_code] = result.data
        else:
            extraction_errors.append(
                {
                    "service_code": result.service_code,
                    "industry_name": result.industry_name,
                    "error": result.error,
                }
            )
    return packs, extraction_errors


def _build_previous_industry_lookup(previous_payload: Dict[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    previous_lookup: Dict[str, Dict[str, Any]] = {}
    if not isinstance(previous_payload, dict):
        return previous_lookup
    for row in list(previous_payload.get("industries") or []):
        if not isinstance(row, dict):
            continue
        service_code = str(row.get("service_code", "") or "").strip()
        if not service_code:
            continue
        previous_lookup[service_code] = dict(row)
    return previous_lookup


def _merge_previous_collection_state(row: Dict[str, Any], previous_row: Dict[str, Any] | None) -> Dict[str, Any]:
    if not previous_row:
        return row
    if bool(row.get("has_rule")) or str(row.get("rule_id", "") or "").strip():
        return row

    previous_mapping_status = str(previous_row.get("mapping_status", "") or "").strip()
    if previous_mapping_status not in PRESERVED_PENDING_MAPPING_STATUSES:
        return row

    for field in ("auto_law_candidates", "auto_collection_at", "auto_collection_error"):
        if field in previous_row:
            row[field] = deepcopy(previous_row.get(field))
    for field in PRESERVED_CANDIDATE_EXTRACTION_FIELDS:
        if field in previous_row:
            row[field] = deepcopy(previous_row.get(field))

    if previous_mapping_status == "candidate_collected":
        row["collection_status"] = "candidate_collected"
    row["mapping_status"] = previous_mapping_status
    return row


def _restore_pending_mapping_statuses(
    industries: List[Dict[str, Any]],
    previous_lookup: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    for row in industries:
        if not isinstance(row, dict):
            continue
        if bool(row.get("has_rule")) or str(row.get("rule_id", "") or "").strip():
            continue
        service_code = str(row.get("service_code", "") or "").strip()
        if not service_code:
            continue
        previous_row = previous_lookup.get(service_code)
        if not previous_row:
            continue
        previous_mapping_status = str(previous_row.get("mapping_status", "") or "").strip()
        if previous_mapping_status not in PRESERVED_PENDING_MAPPING_STATUSES:
            continue
        row["mapping_status"] = previous_mapping_status
        if previous_mapping_status == "candidate_collected":
            row["collection_status"] = "candidate_collected"
    return industries


def _merge_previous_mapping_pipeline_meta(
    mapping_meta: Dict[str, Any],
    previous_payload: Dict[str, Any] | None,
) -> Dict[str, Any]:
    previous_meta = dict((previous_payload or {}).get("mapping_pipeline") or {})
    for key in PRESERVED_MAPPING_PIPELINE_KEYS:
        if key in previous_meta:
            mapping_meta[key] = deepcopy(previous_meta[key])
    return mapping_meta


def build_expanded_catalog(
    max_rules: int = 0,
    timeout_sec: int = 50,
    workers: int = 4,
    extractor=None,
    candidate_workers: int | None = None,
    candidate_extractor=None,
    previous_payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    catalog = permit_diagnosis_calculator._load_catalog(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH)
    rule_catalog = permit_diagnosis_calculator._load_rule_catalog(permit_diagnosis_calculator.DEFAULT_RULES_PATH)
    focus_scope_overrides = permit_diagnosis_calculator._load_focus_scope_overrides(
        permit_diagnosis_calculator.DEFAULT_FOCUS_SCOPE_OVERRIDES_PATH
    )
    profile_override_lookup = _build_profile_override_lookup(focus_scope_overrides)
    payload = permit_diagnosis_calculator._prepare_ui_payload(catalog, rule_catalog)
    rule_lookup = dict(payload.get("rules_lookup") or {})
    previous_lookup = _build_previous_industry_lookup(previous_payload)

    # Deduplicate rules by rule_id for extraction workload.
    unique_rules: Dict[str, Dict[str, Any]] = {}
    for rule in rule_lookup.values():
        if not isinstance(rule, dict):
            continue
        rid = str(rule.get("rule_id", "") or "")
        if not rid:
            continue
        if rid not in unique_rules:
            unique_rules[rid] = rule
    ordered_rules = sorted(unique_rules.values(), key=lambda x: str(x.get("rule_id", "")))
    if max_rules > 0:
        ordered_rules = ordered_rules[: max(1, int(max_rules))]

    packs, extraction_errors = _extract_rule_pack_batch(
        ordered_rules,
        timeout_sec=timeout_sec,
        workers=max(1, int(workers or 1)),
        extractor=extractor,
    )

    # Build industry-wide coverage table.
    industries_out: List[Dict[str, Any]] = []
    for row in list(payload.get("industries") or []):
        service_code = str(row.get("service_code", "") or "")
        service_name = str(row.get("service_name", "") or "")
        major_code = str(row.get("major_code", "") or "")
        has_rule = bool(row.get("has_rule"))
        rule_ref = rule_lookup.get(service_code) if has_rule else None
        rule_id = str((rule_ref or {}).get("rule_id", "") or "")
        pack = packs.get(rule_id) if rule_id else None
        status = "pending_law_mapping"
        if has_rule:
            status = "rule_linked"
        if pack:
            status = "criteria_extracted"
        row_payload = {
            "service_code": service_code,
            "service_name": service_name,
            "major_code": major_code,
            "major_name": str(row.get("major_name", "") or ""),
            "group_code": str(row.get("group_code", "") or ""),
            "group_name": str(row.get("group_name", "") or ""),
            "group_description": str(row.get("group_description", "") or ""),
            "group_declared_total": int(row.get("group_declared_total", 0) or 0),
            "detail_url": str(row.get("detail_url", "") or ""),
            "has_rule": has_rule,
            "rule_id": rule_id,
            "collection_status": status,
            "additional_criteria_count": len(list((pack or {}).get("additional_criteria_lines") or [])),
            "rule_pack_ref": f"rule::{rule_id}" if rule_id else "",
        }
        if rule_ref:
            for field in (
                "industry_name",
                "aliases",
                "requirements",
                "typed_criteria",
                "pending_criteria_lines",
                "document_templates",
                "mapping_meta",
                "legal_basis",
            ):
                if field in rule_ref:
                    row_payload[field] = deepcopy(rule_ref.get(field))
        if pack:
            for field in (
                "industry_name",
                "aliases",
                "requirements",
                "legal_basis",
                "law_fetch_meta",
                "additional_criteria_lines",
            ):
                if field in pack:
                    row_payload[field] = deepcopy(pack.get(field))
        if not has_rule:
            for field in (
                "auto_law_candidates",
                "auto_collection_at",
                "auto_collection_error",
                "mapping_status",
                "mapping_batch_id",
                "mapping_batch_seq",
                "mapping_group_key",
            ):
                if field in row:
                    row_payload[field] = deepcopy(row.get(field))
            for field in PRESERVED_CANDIDATE_EXTRACTION_FIELDS:
                if field in row:
                    row_payload[field] = deepcopy(row.get(field))
        industries_out.append(
            _merge_previous_collection_state(
                row_payload,
                previous_lookup.get(service_code),
            )
        )

    candidate_target_rows = [
        row
        for row in industries_out
        if _needs_candidate_reextraction(row)
    ]
    candidate_target_codes = {str(row.get("service_code", "") or "").strip() for row in candidate_target_rows}
    candidate_error_by_code = {}
    candidate_packs, candidate_extraction_errors = _extract_candidate_pack_batch(
        candidate_target_rows,
        timeout_sec=timeout_sec,
        workers=max(1, int(candidate_workers or workers or 1)),
        extractor=candidate_extractor,
    )
    for item in candidate_extraction_errors:
        service_code = str(item.get("service_code", "") or "").strip()
        if service_code:
            candidate_error_by_code[service_code] = str(item.get("error", "") or "")
    for row in industries_out:
        if not isinstance(row, dict):
            continue
        service_code = str(row.get("service_code", "") or "").strip()
        if service_code in candidate_target_codes and service_code not in candidate_packs:
            for field in PRESERVED_CANDIDATE_EXTRACTION_FIELDS:
                row.pop(field, None)
            row["candidate_criteria_status"] = "candidate_criteria_failed"
            error_detail = candidate_error_by_code.get(service_code, "")
            if error_detail:
                row["candidate_criteria_error"] = error_detail
        candidate_pack = candidate_packs.get(service_code)
        if not candidate_pack:
            continue
        row.update(candidate_pack)

    for row in industries_out:
        if not isinstance(row, dict):
            continue
        if str(row.get("candidate_criteria_status", "") or "").strip() != "candidate_criteria_extracted":
            continue
        criteria_lines, additional_lines = _dedupe_line_items(
            list(row.get("candidate_criteria_lines") or []),
            list(row.get("candidate_additional_criteria_lines") or []),
        )
        row["candidate_criteria_lines"] = criteria_lines
        row["candidate_additional_criteria_lines"] = additional_lines
        row["candidate_criteria_count"] = len(criteria_lines) + len(additional_lines)
        if not str(row.get("candidate_basis_title", "") or "").strip():
            legal_basis = list(row.get("candidate_legal_basis") or [])
            if legal_basis:
                row["candidate_basis_title"] = str(legal_basis[0].get("article", "") or "").strip()

    industries_out, mapping_meta = apply_mapping_pipeline(industries_out, batch_size=12)
    industries_out = _restore_pending_mapping_statuses(industries_out, previous_lookup)
    mapping_meta = _merge_previous_mapping_pipeline_meta(mapping_meta, previous_payload)
    for row in industries_out:
        if not isinstance(row, dict):
            continue
        _promote_display_fields(row)
        service_code = str(row.get("service_code", "") or "").strip()
        profile = _build_requirement_profile(row)
        row["registration_requirement_profile"] = _apply_manual_profile_override(
            service_code,
            profile,
            profile_override_lookup,
        )
        row["quality_flags"] = _build_quality_flags(row)
    criteria_extracted_count = sum(1 for row in industries_out if row.get("collection_status") == "criteria_extracted")
    rule_linked_count = sum(1 for row in industries_out if bool(row.get("has_rule")))
    pending_count = int(mapping_meta.get("pending_total") or 0)
    candidate_collected_count = sum(1 for row in industries_out if row.get("mapping_status") == "candidate_collected")
    low_confidence_count = sum(
        1 for row in industries_out if row.get("mapping_status") == "queued_law_mapping_low_confidence"
    )
    no_hit_count = sum(1 for row in industries_out if row.get("mapping_status") == "queued_law_mapping_no_hit")
    failed_count = sum(1 for row in industries_out if row.get("mapping_status") == "queued_law_mapping_failed")
    candidate_criteria_extracted_count = sum(
        1 for row in industries_out if row.get("candidate_criteria_status") == "candidate_criteria_extracted"
    )
    quality_flag_counts = Counter()
    for row in industries_out:
        for flag in list(row.get("quality_flags") or []):
            quality_flag_counts[str(flag)] += 1
    real_industries = [
        row for row in industries_out if not str(row.get("service_code", "") or "").strip().startswith("RULE::")
    ]
    real_with_legal_basis_count = sum(
        1 for row in real_industries if list(row.get("legal_basis") or []) or str(row.get("law_title", "") or "").strip()
    )
    real_with_registration_criteria_count = sum(
        1
        for row in real_industries
        if list(row.get("criteria_summary") or []) or list(row.get("criteria_additional") or [])
    )
    real_blank_count = sum(
        1
        for row in real_industries
        if not (
            list(row.get("legal_basis") or [])
            or str(row.get("law_title", "") or "").strip()
            or list(row.get("criteria_summary") or [])
            or list(row.get("criteria_additional") or [])
        )
    )
    focus_profiles = [
        dict(row.get("registration_requirement_profile") or {})
        for row in industries_out
        if isinstance(row, dict)
    ]
    real_focus_profiles = [
        dict(row.get("registration_requirement_profile") or {})
        for row in real_industries
        if isinstance(row, dict)
    ]
    rule_only_focus_profiles = [
        dict(row.get("registration_requirement_profile") or {})
        for row in industries_out
        if str(row.get("service_code", "") or "").strip().startswith("RULE::")
    ]

    return {
        "generated_at": now_iso(),
        "source": {
            "localdata_catalog": str(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH),
            "rules_catalog": str(permit_diagnosis_calculator.DEFAULT_RULES_PATH),
            "focus_scope_overrides": str(permit_diagnosis_calculator.DEFAULT_FOCUS_SCOPE_OVERRIDES_PATH),
            "law_base": LAW_BASE,
        },
        "summary": {
            "industry_total": len(industries_out),
            "rule_linked_industry_total": rule_linked_count,
            "criteria_extracted_industry_total": criteria_extracted_count,
            "pending_industry_total": pending_count,
            "candidate_collected_industry_total": candidate_collected_count,
            "queued_law_mapping_low_confidence_total": low_confidence_count,
            "queued_law_mapping_no_hit_total": no_hit_count,
            "queued_law_mapping_failed_total": failed_count,
            "candidate_criteria_extracted_total": candidate_criteria_extracted_count,
            "rule_pack_total": len(packs),
            "extraction_error_total": len(extraction_errors),
            "candidate_extraction_error_total": len(candidate_extraction_errors),
            "real_industry_total": len(real_industries),
            "real_with_legal_basis_total": real_with_legal_basis_count,
            "real_with_registration_criteria_total": real_with_registration_criteria_count,
            "real_blank_total": real_blank_count,
            "max_rules_limit": int(max_rules or 0),
            "worker_count": max(1, int(workers or 1)),
            "mapping_major_group_total": int(mapping_meta.get("major_group_total") or 0),
            "mapping_batch_total": int(mapping_meta.get("batch_total") or 0),
            "mapping_batch_size": int(mapping_meta.get("batch_size") or 0),
        },
        "quality_audit": {
            "law_only_total": int(quality_flag_counts.get("law_only", 0)),
            "stale_candidate_source_total": int(quality_flag_counts.get("stale_candidate_source", 0)),
            "sparse_criteria_total": int(quality_flag_counts.get("sparse_criteria", 0)),
            "generic_basis_title_total": int(quality_flag_counts.get("generic_basis_title", 0)),
            "article_name_unmatched_total": int(quality_flag_counts.get("article_name_unmatched", 0)),
            "manual_scope_override_total": int(quality_flag_counts.get("manual_scope_override", 0)),
        },
        "requirement_focus_summary": {
            "capital_required_total": sum(1 for item in focus_profiles if item.get("capital_required")),
            "technical_personnel_required_total": sum(
                1 for item in focus_profiles if item.get("technical_personnel_required")
            ),
            "capital_and_technical_total": sum(1 for item in focus_profiles if item.get("focus_target")),
            "capital_and_technical_with_other_total": sum(
                1 for item in focus_profiles if item.get("focus_target_with_other")
            ),
            "inferred_capital_and_technical_total": sum(
                1 for item in focus_profiles if item.get("inferred_focus_candidate")
            ),
            "inferred_capital_and_technical_with_other_total": sum(
                1
                for item in focus_profiles
                if item.get("inferred_focus_candidate") and item.get("other_required")
            ),
            "real_capital_and_technical_total": sum(1 for item in real_focus_profiles if item.get("focus_target")),
            "real_capital_and_technical_with_other_total": sum(
                1 for item in real_focus_profiles if item.get("focus_target_with_other")
            ),
            "rules_only_capital_and_technical_total": sum(
                1 for item in rule_only_focus_profiles if item.get("focus_target")
            ),
            "rules_only_capital_and_technical_with_other_total": sum(
                1 for item in rule_only_focus_profiles if item.get("focus_target_with_other")
            ),
        },
        "industries": industries_out,
        "mapping_pipeline": mapping_meta,
        "rule_criteria_packs": [{"ref": f"rule::{rid}", **pack} for rid, pack in sorted(packs.items())],
        "extraction_errors": extraction_errors,
        "candidate_extraction_errors": candidate_extraction_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect extended permit registration criteria from law.go.kr bylaw PDFs.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--max-rules", type=int, default=0, help="0 means all linked rules")
    parser.add_argument("--timeout-sec", type=int, default=50)
    parser.add_argument("--workers", type=int, default=4, help="parallel workers for rule-level extraction")
    args = parser.parse_args()
    out_path = Path(args.output).expanduser().resolve()
    previous_payload = None
    if out_path.exists():
        try:
            previous_payload = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] failed to load previous payload: {exc}", file=sys.stderr)

    payload = build_expanded_catalog(
        max_rules=int(args.max_rules or 0),
        timeout_sec=max(20, int(args.timeout_sec)),
        workers=max(1, int(args.workers or 1)),
        previous_payload=previous_payload,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = payload.get("summary", {})
    print(f"[saved] {out_path}")
    print(f"[industry_total] {summary.get('industry_total')}")
    print(f"[rule_linked_industry_total] {summary.get('rule_linked_industry_total')}")
    print(f"[criteria_extracted_industry_total] {summary.get('criteria_extracted_industry_total')}")
    print(f"[candidate_collected_industry_total] {summary.get('candidate_collected_industry_total')}")
    print(f"[candidate_criteria_extracted_total] {summary.get('candidate_criteria_extracted_total')}")
    print(f"[queued_law_mapping_low_confidence_total] {summary.get('queued_law_mapping_low_confidence_total')}")
    print(f"[queued_law_mapping_no_hit_total] {summary.get('queued_law_mapping_no_hit_total')}")
    print(f"[extraction_error_total] {summary.get('extraction_error_total')}")
    print(f"[candidate_extraction_error_total] {summary.get('candidate_extraction_error_total')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
