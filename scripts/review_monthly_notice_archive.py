#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "output" / "notice_archive" / "notice_archive_manifest.json"
DEFAULT_REPORT_JSON = ROOT / "logs" / "notice_archive_review_latest.json"
DEFAULT_REPORT_MD = ROOT / "logs" / "notice_archive_review_latest.md"
QUALITY_WEIGHTS: dict[str, int] = {
    "subject_length_ok": 5,
    "month_token_ok": 10,
    "listing_link_coverage_ok": 20,
    "cta_ok": 10,
    "heading_ok": 5,
    "brand_ok": 5,
    "summary_section_ok": 10,
    "seo_core_terms_ok": 10,
    "click_guidance_ok": 10,
    "private_listing_cta_ok": 5,
    "image_alt_ok": 10,
}


def _read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(_read_text(path))
    except Exception:
        return default


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _subject_has_month(subject: str, month_key: str) -> bool:
    match = re.fullmatch(r"(\d{4})-(\d{2})", month_key)
    if not match:
        return False
    year = int(match.group(1))
    month = int(match.group(2))
    year_short = year % 100
    tokens = [
        f"{year}-{month:02d}",
        f"{year}년 {month}월",
        f"{year}년 {month:02d}월",
        f"{year_short}년 {month}월",
        f"{year_short}년 {month:02d}월",
        f"{year} {month}",
    ]
    haystack = re.sub(r"\s+", " ", subject or "")
    return any(token in haystack for token in tokens)


def _has_any(text: str, keywords: list[str]) -> bool:
    src = str(text or "").lower()
    return any(keyword.lower() in src for keyword in keywords)


def _has_all(text: str, keywords: list[str]) -> bool:
    src = str(text or "").lower()
    return all(keyword.lower() in src for keyword in keywords)


def _review_month(month_row: dict[str, Any], quality_relax_pct: float = 0.0) -> dict[str, Any]:
    month_key = str(month_row.get("month_key", "")).strip()
    subject_path = Path(str(month_row.get("subject", "")).strip())
    body_path = Path(str(month_row.get("body", "")).strip())
    declared_count = int(month_row.get("count", 0) or 0)

    blocking: list[str] = []
    warnings: list[str] = []
    stats: dict[str, Any] = {
        "subject_chars": 0,
        "body_chars": 0,
        "declared_count": declared_count,
        "listing_link_count": 0,
        "unique_listing_link_count": 0,
        "heading_count": 0,
        "cta_phone": False,
        "cta_kakao": False,
        "has_brand": False,
        "has_month_token": False,
        "has_legal_notice": False,
        "has_summary_section": False,
        "has_seo_core_terms": False,
        "has_click_guidance": False,
        "has_private_listing_cta": False,
        "image_count": 0,
        "image_alt_coverage": 0,
        "listing_titles_without_yangdo": 0,
        "listing_titles_without_business_label": 0,
        "listing_link_coverage_ratio": 0.0,
        "quality_score": 0,
        "quality_required_score": 100,
        "quality_relax_pct": 0.0,
    }

    if not month_key:
        blocking.append("month_key_missing")
    if not subject_path.exists():
        blocking.append("subject_file_missing")
    if not body_path.exists():
        blocking.append("body_file_missing")
    if blocking:
        return {
            "month_key": month_key,
            "status": "fail",
            "blocking_issues": blocking,
            "warnings": warnings,
            "stats": stats,
        }

    subject = _read_text(subject_path).strip()
    body = _read_text(body_path)
    soup = BeautifulSoup(body, "html.parser")
    plain_text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))

    listing_links = []
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href", "")).strip()
        if "/mna/" in href:
            listing_links.append(href)

    unique_listing_links = sorted(set(listing_links))
    headings = soup.select("h1, h2, h3")
    images = soup.select("img")
    listing_title_without_yangdo = 0
    listing_title_without_business_label = 0
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href", "")).strip()
        if "/mna/" not in href:
            continue
        title = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))
        if "양도" not in title:
            listing_title_without_yangdo += 1
        if not re.search(r"\|\s*[^|\]]+양도\s*\|", title):
            listing_title_without_business_label += 1

    stats["subject_chars"] = len(subject)
    stats["body_chars"] = len(body)
    stats["listing_link_count"] = len(listing_links)
    stats["unique_listing_link_count"] = len(unique_listing_links)
    stats["heading_count"] = len(headings)
    stats["cta_phone"] = bool(re.search(r"tel:\d{8,}", body))
    stats["cta_kakao"] = "open.kakao.com" in body
    stats["image_count"] = len(images)
    stats["image_alt_coverage"] = sum(1 for img in images if str(img.get("alt", "")).strip())
    stats["listing_titles_without_yangdo"] = listing_title_without_yangdo
    stats["listing_titles_without_business_label"] = listing_title_without_business_label
    stats["listing_link_coverage_ratio"] = (
        (float(stats["unique_listing_link_count"]) / float(declared_count)) if declared_count > 0 else 1.0
    )
    stats["has_brand"] = _has_any(subject + " " + plain_text, ["서울건설정보"])
    stats["has_month_token"] = _subject_has_month(subject, month_key)
    stats["has_legal_notice"] = _has_any(plain_text, ["최종 거래 조건", "법무", "세무", "계약", "실사"]) and _has_any(
        plain_text,
        ["확정", "안내", "참고"],
    )
    stats["has_summary_section"] = _has_any(plain_text, ["핵심 요약", "대표 매물", "top", "요약"])
    stats["has_seo_core_terms"] = _has_any(subject + " " + plain_text, ["건설업", "양도양수", "신규 매물"])
    stats["has_click_guidance"] = _has_all(plain_text, ["클릭", "상세 페이지"])
    stats["has_private_listing_cta"] = _has_any(plain_text, ["비공개 매물", "1:1 상담", "카카오톡", "전화 바로 연결"])

    if not subject:
        blocking.append("subject_empty")
    if not body.strip():
        blocking.append("body_empty")
    if not stats["has_legal_notice"]:
        blocking.append("legal_notice_missing")

    quality_checks = {
        "subject_length_ok": 24 <= stats["subject_chars"] <= 90,
        "month_token_ok": stats["has_month_token"],
        "listing_link_coverage_ok": (
            stats["unique_listing_link_count"] > 0
            and (declared_count <= 0 or stats["unique_listing_link_count"] >= declared_count)
        ),
        "cta_ok": stats["cta_phone"] or stats["cta_kakao"],
        "heading_ok": stats["heading_count"] > 0,
        "brand_ok": stats["has_brand"],
        "summary_section_ok": stats["has_summary_section"],
        "seo_core_terms_ok": stats["has_seo_core_terms"],
        "click_guidance_ok": stats["has_click_guidance"],
        "private_listing_cta_ok": stats["has_private_listing_cta"],
        "image_alt_ok": stats["image_count"] <= 0 or stats["image_alt_coverage"] >= stats["image_count"],
    }
    relax_pct = min(1.0, max(0.0, float(quality_relax_pct or 0.0)))
    quality_score = sum(weight for key, weight in QUALITY_WEIGHTS.items() if quality_checks.get(key))
    quality_required_score = max(0, int(round(100 * (1.0 - relax_pct))))
    stats["quality_score"] = int(quality_score)
    stats["quality_required_score"] = int(quality_required_score)
    stats["quality_relax_pct"] = relax_pct
    stats["quality_checks"] = quality_checks

    if not blocking and quality_score < quality_required_score:
        blocking.append("quality_score_below_threshold")

    if stats["subject_chars"] < 24:
        warnings.append("subject_too_short")
    if stats["subject_chars"] > 90:
        warnings.append("subject_too_long")
    if not stats["has_brand"]:
        warnings.append("brand_term_missing")
    if not stats["has_private_listing_cta"]:
        warnings.append("private_listing_cta_missing")
    if stats["listing_titles_without_yangdo"] > 0:
        warnings.append("listing_titles_without_yangdo")
    if stats["listing_titles_without_business_label"] > 0:
        warnings.append("listing_titles_without_business_label")
    for key, passed in quality_checks.items():
        if not passed:
            warnings.append(key)

    return {
        "month_key": month_key,
        "status": "pass" if not blocking else "fail",
        "blocking_issues": blocking,
        "warnings": warnings,
        "stats": stats,
        "subject_path": str(subject_path),
        "body_path": str(body_path),
    }


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Notice Archive Review ({report['generated_at']})",
        "",
        f"- manifest: {report['manifest']}",
        f"- overall_ok: {report['ok']}",
        f"- reviewed_months: {len(report['months'])}",
        "",
    ]
    for row in report["months"]:
        lines.append(f"## {row['month_key']} [{row['status']}]")
        lines.append("")
        lines.append(f"- blocking_issues: {', '.join(row['blocking_issues']) if row['blocking_issues'] else 'none'}")
        lines.append(f"- warnings: {', '.join(row['warnings']) if row['warnings'] else 'none'}")
        stats = row.get("stats", {})
        lines.append(
            "- stats: "
            + ", ".join(
                [
                    f"quality_score={stats.get('quality_score', 0)}",
                    f"quality_required={stats.get('quality_required_score', 0)}",
                    f"quality_relax_pct={stats.get('quality_relax_pct', 0.0):.2f}",
                    f"subject_chars={stats.get('subject_chars', 0)}",
                    f"body_chars={stats.get('body_chars', 0)}",
                    f"declared_count={stats.get('declared_count', 0)}",
                    f"listing_links={stats.get('unique_listing_link_count', 0)}",
                    f"headings={stats.get('heading_count', 0)}",
                    f"cta_phone={stats.get('cta_phone', False)}",
                    f"cta_kakao={stats.get('cta_kakao', False)}",
                    f"has_legal_notice={stats.get('has_legal_notice', False)}",
                    f"has_click_guidance={stats.get('has_click_guidance', False)}",
                    f"image_alt_coverage={stats.get('image_alt_coverage', 0)}/{stats.get('image_count', 0)}",
                    f"listing_titles_without_yangdo={stats.get('listing_titles_without_yangdo', 0)}",
                    f"listing_titles_without_business_label={stats.get('listing_titles_without_business_label', 0)}",
                ]
            )
        )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review monthly notice archive bundles before co.kr publish.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--month-key", default="", help="Only review one month key (YYYY-MM).")
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    parser.add_argument(
        "--quality-relax-pct",
        type=float,
        default=0.0,
        help="Relax non-legal quality threshold by ratio (0.05 lowers pass threshold by 5%%).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(str(args.manifest)).resolve()
    report_json_path = Path(str(args.report_json)).resolve()
    report_md_path = Path(str(args.report_md)).resolve()
    only_month = str(args.month_key or "").strip()
    quality_relax_pct = min(1.0, max(0.0, float(args.quality_relax_pct or 0.0)))

    manifest = _load_json(manifest_path, {})
    months = list(manifest.get("months", []) or [])
    if only_month:
        months = [row for row in months if str(row.get("month_key", "")).strip() == only_month]

    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "manifest": str(manifest_path),
        "ok": False,
        "months": [],
    }

    if not months:
        report["error"] = "manifest months empty"
        _save_json(report_json_path, report)
        report_md_path.parent.mkdir(parents=True, exist_ok=True)
        report_md_path.write_text(_build_markdown(report), encoding="utf-8")
        print(f"[saved] {report_json_path}")
        print(f"[saved] {report_md_path}")
        print("[fail] manifest months empty")
        return 2

    reviewed = [_review_month(row, quality_relax_pct=quality_relax_pct) for row in months]
    report["months"] = reviewed
    report["ok"] = all(str(row.get("status", "")) == "pass" for row in reviewed)

    _save_json(report_json_path, report)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.write_text(_build_markdown(report), encoding="utf-8")

    print(f"[saved] {report_json_path}")
    print(f"[saved] {report_md_path}")
    for row in reviewed:
        print(
            f"[review] {row['month_key']} status={row['status']} "
            f"blocking={len(row['blocking_issues'])} warnings={len(row['warnings'])}"
        )
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
