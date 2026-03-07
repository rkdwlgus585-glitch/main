from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import permit_diagnosis_calculator


DEFAULT_OUTPUT_PATH = ROOT / "config" / "permit_registration_criteria_expanded.json"
LAW_BASE = "https://www.law.go.kr"

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


def _parse_article_annex_hint(article_hint: str) -> Tuple[str, str]:
    article = str(article_hint or "")
    m = re.search(r"별표\s*([0-9]+)(?:\s*의\s*([0-9]+))?", article)
    if not m:
        return "", ""
    no = str(m.group(1) or "").zfill(4)
    br = str(m.group(2) or "0").zfill(2)
    return no, br


def _pick_relevant_byl(
    entries: List[Dict[str, str]],
    industry_name: str,
    aliases: List[str],
    article_hint: str = "",
) -> Dict[str, str] | None:
    if not entries:
        return None
    names = [str(industry_name or "").strip()] + [str(x or "").strip() for x in list(aliases or [])]
    names = [x for x in names if x]
    name_keys = [permit_diagnosis_calculator._normalize_key(x) for x in names]
    hint_no, hint_br = _parse_article_annex_hint(article_hint)
    candidates = []
    for row in entries:
        title = str(row.get("title", "") or "")
        title_key = permit_diagnosis_calculator._normalize_key(title)
        score = 0
        row_no = str(row.get("byl_no", "") or "").zfill(4)
        row_br = str(row.get("byl_br_no", "") or "").zfill(2)
        if "등록기준" in title:
            score += 60
        if "등록요건" in title or "등록 요건" in title:
            score += 45
        if hint_no and row_no == hint_no:
            score += 18
            if hint_br and row_br == hint_br:
                score += 8
        for key in name_keys:
            if key and key in title_key:
                score += 8
        if "기준" in title:
            score += 3
        if "삭제" in title:
            score -= 20
        candidates.append((score, row))
    candidates.sort(key=lambda x: x[0], reverse=True)
    best = candidates[0][1]
    if candidates[0][0] <= 0:
        for row in entries:
            if "등록기준" in str(row.get("title", "")):
                return row
        return entries[0]
    return best


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


@dataclass
class RuleExtraction:
    ok: bool
    rule_id: str
    industry_name: str
    data: Dict[str, Any]
    error: str = ""


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


def build_expanded_catalog(max_rules: int = 0, timeout_sec: int = 50) -> Dict[str, Any]:
    catalog = permit_diagnosis_calculator._load_catalog(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH)
    rule_catalog = permit_diagnosis_calculator._load_rule_catalog(permit_diagnosis_calculator.DEFAULT_RULES_PATH)
    payload = permit_diagnosis_calculator._prepare_ui_payload(catalog, rule_catalog)
    rule_lookup = dict(payload.get("rules_lookup") or {})

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

    packs: Dict[str, Dict[str, Any]] = {}
    extraction_errors: List[Dict[str, str]] = []
    for rule in ordered_rules:
        result = _extract_rule_criteria(rule, timeout_sec=timeout_sec)
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
        industries_out.append(
            {
                "service_code": service_code,
                "service_name": service_name,
                "major_code": major_code,
                "major_name": str(row.get("major_name", "") or ""),
                "has_rule": has_rule,
                "rule_id": rule_id,
                "collection_status": status,
                "additional_criteria_count": len(list((pack or {}).get("additional_criteria_lines") or [])),
                "rule_pack_ref": f"rule::{rule_id}" if rule_id else "",
            }
        )

    criteria_extracted_count = sum(1 for row in industries_out if row.get("collection_status") == "criteria_extracted")
    rule_linked_count = sum(1 for row in industries_out if bool(row.get("has_rule")))
    pending_count = sum(1 for row in industries_out if row.get("collection_status") != "criteria_extracted")

    return {
        "generated_at": now_iso(),
        "source": {
            "localdata_catalog": str(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH),
            "rules_catalog": str(permit_diagnosis_calculator.DEFAULT_RULES_PATH),
            "law_base": LAW_BASE,
        },
        "summary": {
            "industry_total": len(industries_out),
            "rule_linked_industry_total": rule_linked_count,
            "criteria_extracted_industry_total": criteria_extracted_count,
            "pending_industry_total": pending_count,
            "rule_pack_total": len(packs),
            "extraction_error_total": len(extraction_errors),
            "max_rules_limit": int(max_rules or 0),
        },
        "industries": industries_out,
        "rule_criteria_packs": [{"ref": f"rule::{rid}", **pack} for rid, pack in sorted(packs.items())],
        "extraction_errors": extraction_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect extended permit registration criteria from law.go.kr bylaw PDFs.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--max-rules", type=int, default=0, help="0 means all linked rules")
    parser.add_argument("--timeout-sec", type=int, default=50)
    args = parser.parse_args()

    payload = build_expanded_catalog(max_rules=int(args.max_rules or 0), timeout_sec=max(20, int(args.timeout_sec)))
    out_path = Path(args.output).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = payload.get("summary", {})
    print(f"[saved] {out_path}")
    print(f"[industry_total] {summary.get('industry_total')}")
    print(f"[rule_linked_industry_total] {summary.get('rule_linked_industry_total')}")
    print(f"[criteria_extracted_industry_total] {summary.get('criteria_extracted_industry_total')}")
    print(f"[extraction_error_total] {summary.get('extraction_error_total')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
