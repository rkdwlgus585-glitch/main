#!/usr/bin/env python3
"""
Build SeoulMNA notice HTML drafts from mna board rows.

Single month:
  python scripts/build_monthly_notice_from_maemul.py --year 2026 --month 2 --min-uid 7684

Rolling monthly archive (new UIDs -> current run month):
  python scripts/build_monthly_notice_from_maemul.py --monthly-archive --pages 20
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import maemul  # noqa: E402
import all as listing_ops  # noqa: E402
from utils import load_config  # noqa: E402


DEFAULT_HERO_IMAGE = ""
DEFAULT_BIZCARD_IMAGE = (
    "https://seoulmna.co.kr/data/editor/2601/"
    "thumb-f7d3177d503f0aa4331e6b6472a02d36_1769753539_1509_835x835.jpg"
)
DEFAULT_KAKAO_URL = os.getenv("KAKAO_OPENCHAT_URL", "https://open.kakao.com/o/syWr1hIe")
DEFAULT_PHONE = "010-9926-8661"
DEFAULT_STATE_FILE = ROOT / "logs" / "notice_uid_month_state.json"
DEFAULT_CLAIM_SENDER = os.getenv("KAKAO_CLAIM_SENDER", "이우진")

SHEET_CONFIG = load_config(
    {
        "JSON_FILE": "service_account.json",
        "SHEET_NAME": "26양도매물",
    }
)
JSON_FILE = str(SHEET_CONFIG.get("JSON_FILE", "service_account.json")).strip() or "service_account.json"
SHEET_NAME = str(SHEET_CONFIG.get("SHEET_NAME", "26양도매물")).strip() or "26양도매물"


@dataclass
class ListingRow:
    uid: int
    status: str
    businesses: list[str]
    three_year: str
    five_year: str
    license_year: str
    capital_or_shares: str
    corp_and_transfer: str
    region: str
    now_uid: str = ""
    sheet_price: str = ""
    sheet_claim: str = ""
    transfer_display: str = ""


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _fmt_number_string(value: str) -> str:
    if not value:
        return ""
    if re.fullmatch(r"\d+\.0+", value):
        return str(int(float(value)))
    if "." in value:
        return value.rstrip("0").rstrip(".")
    return value


def _extract_metric(text: str) -> str:
    text = _clean_text(text).replace(",", "")
    if not text or text == "-":
        return ""
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return ""
    return _fmt_number_string(match.group(0))


def _pick_largest_metric(values: Iterable[str]) -> str:
    normalized = [v for v in values if v]
    if not normalized:
        return ""
    return max(normalized, key=lambda x: float(x))


def _join_businesses(values: list[str]) -> str:
    seen: list[str] = []
    for value in values:
        v = _clean_text(value)
        if not v or v in seen:
            continue
        seen.append(v)
    if not seen:
        return ""
    if len(seen) <= 3:
        return "+".join(seen)
    return f"{'+'.join(seen[:3])} 외 {len(seen) - 3}"


def _extract_transfer_amount(corp_and_transfer: str) -> str:
    text = _clean_text(corp_and_transfer)
    if not text:
        return ""
    text = re.sub(r"(주식회사|유한회사|합자회사|합명회사|법인)", "", text).strip()
    if not re.search(r"\d", text):
        return ""
    return text


def _extract_uid(cell_text: str) -> int | None:
    match = re.search(r"\b(\d{4,})\b", cell_text or "")
    if not match:
        return None
    return int(match.group(1))


def _parse_listing_rows(soup: BeautifulSoup) -> list[ListingRow]:
    rows: list[ListingRow] = []
    seen_uid: set[int] = set()

    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 8:
            continue

        uid = _extract_uid(_clean_text(tds[0].get_text(" ", strip=True)))
        if not uid or uid in seen_uid:
            continue
        seen_uid.add(uid)

        status = _clean_text(tds[1].get_text(" ", strip=True))
        businesses: list[str] = []
        metrics_3y: list[str] = []
        metrics_5y: list[str] = []

        nested = tds[2].find("table", class_="nmanss")
        if nested:
            for ntr in nested.find_all("tr", recursive=False):
                ncells = ntr.find_all("td", recursive=False)
                if not ncells:
                    continue
                first = _clean_text(ncells[0].get_text(" ", strip=True))
                if first:
                    businesses.append(first)
                if len(ncells) >= 10:
                    metric_3y = _extract_metric(ncells[8].get_text(" ", strip=True))
                    metric_5y = _extract_metric(ncells[9].get_text(" ", strip=True))
                    if metric_3y:
                        metrics_3y.append(metric_3y)
                    if metric_5y:
                        metrics_5y.append(metric_5y)

        if not businesses:
            fallback = _clean_text(tds[2].get_text(" ", strip=True))
            match = re.match(r"([가-힣A-Za-z0-9/+·]+)", fallback)
            if match:
                businesses = [match.group(1)]

        rows.append(
            ListingRow(
                uid=uid,
                status=status,
                businesses=businesses,
                three_year=_pick_largest_metric(metrics_3y),
                five_year=_pick_largest_metric(metrics_5y),
                license_year=_clean_text(tds[3].get_text(" ", strip=True)),
                capital_or_shares=_clean_text(tds[4].get_text(" ", strip=True)),
                corp_and_transfer=_clean_text(tds[5].get_text(" ", strip=True)),
                region=_clean_text(tds[6].get_text(" ", strip=True)),
            )
        )

    return rows


def collect_listings(pages: int, min_uid: int | None, include_completed: bool) -> list[ListingRow]:
    collected: dict[int, ListingRow] = {}
    list_url = maemul.LIST_URL

    for page_num in range(1, pages + 1):
        url = f"{list_url}?page={page_num}" if page_num > 1 else list_url
        soup = maemul.fetch_page(url)
        if not soup:
            continue

        parsed_rows = _parse_listing_rows(soup)
        if not parsed_rows:
            continue

        if min_uid is not None and all(row.uid < min_uid for row in parsed_rows):
            break

        for row in parsed_rows:
            if min_uid is not None and row.uid < min_uid:
                continue
            if not include_completed and row.status == "완료":
                continue
            collected.setdefault(row.uid, row)

    return sorted(collected.values(), key=lambda item: item.uid, reverse=True)


def _load_sheet_transfer_map() -> dict[int, dict[str, str]]:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
    ws = gspread.authorize(creds).open(SHEET_NAME).sheet1
    values = ws.get_all_values()
    out: dict[int, dict[str, str]] = {}
    for row in values[1:]:
        no = _clean_text(row[0] if len(row) > 0 else "")
        if not no.isdigit():
            continue
        uid = int(no)
        out[uid] = {
            "sheet_price": _clean_text(row[18] if len(row) > 18 else ""),
            "sheet_claim": _clean_text(row[33] if len(row) > 33 else ""),
            "now_uid": _clean_text(row[34] if len(row) > 34 else ""),
        }
    return out


def _clean_claim_value(raw: str) -> str:
    txt = _clean_text(raw).replace("-", "~")
    if "/" in txt:
        txt = _clean_text(txt.split("/")[-1])
    txt = re.sub(r"^\d{4,6}\s*", "", txt).strip()
    txt = txt.replace("에", "")
    txt = re.sub(r"\s+", "", txt)
    txt = txt.replace("억~", "억~")
    # 숫자 범위인데 단위가 빠진 끝값은 억 보정
    m = re.fullmatch(r"(\d+(?:\.\d+)?)억~(\d+(?:\.\d+)?)", txt)
    if m:
        txt = f"{m.group(1)}억~{m.group(2)}억"
    return txt


def _claim_to_public_price(raw: str) -> str:
    txt = _clean_claim_value(raw)
    if not txt:
        return ""
    if any(k in txt for k in ("협의", "보류", "완료", "삭제")):
        return "협의"

    # 범위형(입금가~양도가)인 경우 뒤쪽 값만 공개한다.
    m = re.fullmatch(r"(\d+(?:\.\d+)?)억~(\d+(?:\.\d+)?)억?", txt)
    if m:
        return f"{m.group(2)}억"

    # 숫자+억 단일값
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*억", txt)
    if m2:
        return f"{m2.group(1)}억"

    return txt


def _load_kakao_claim_updates(chat_file: str, sender_contains: str) -> dict[str, dict]:
    path = str(chat_file or "").strip()
    if not path:
        return {}
    try:
        return listing_ops._parse_kakao_claim_updates(path, sender_contains=sender_contains)  # noqa: SLF001
    except Exception:
        return {}


def _resolve_transfer_display(
    item: ListingRow,
    sheet_row: dict[str, str] | None,
    kakao_updates: dict[str, dict] | None,
) -> str:
    sheet_row = sheet_row or {}
    now_uid = _clean_text(sheet_row.get("now_uid", ""))
    sheet_price = _clean_text(sheet_row.get("sheet_price", ""))
    sheet_claim = _clean_claim_value(sheet_row.get("sheet_claim", ""))

    # 1) 카카오 원문이 있으면 최우선
    if now_uid and kakao_updates and now_uid in kakao_updates:
        claim_txt = _claim_to_public_price(str((kakao_updates[now_uid] or {}).get("claim", "")))
        if claim_txt and re.search(r"\d", claim_txt):
            return claim_txt
        if any(k in claim_txt for k in ("협의", "보류", "완료", "삭제")):
            return "협의"

    # 2) 시트 청구 양도가(AH) 범위
    if sheet_claim and re.search(r"\d", sheet_claim):
        public_claim = _claim_to_public_price(sheet_claim)
        if public_claim:
            return public_claim

    # 3) 시트 양도가(S)
    if sheet_price:
        return sheet_price

    # 4) 마지막 폴백(목록 원문)
    return _extract_transfer_amount(item.corp_and_transfer)


def _enrich_listings_with_transfer_source(
    listings: list[ListingRow],
    chat_file: str,
    chat_sender: str,
) -> tuple[list[ListingRow], int]:
    sheet_map = _load_sheet_transfer_map()
    kakao_updates = _load_kakao_claim_updates(chat_file, chat_sender)
    overridden = 0
    for item in listings:
        row = sheet_map.get(item.uid, {})
        item.now_uid = _clean_text(row.get("now_uid", ""))
        item.sheet_price = _clean_text(row.get("sheet_price", ""))
        item.sheet_claim = _clean_claim_value(row.get("sheet_claim", ""))
        resolved = _resolve_transfer_display(item, row, kakao_updates)
        if resolved and resolved != _extract_transfer_amount(item.corp_and_transfer):
            overridden += 1
        item.transfer_display = resolved
    return listings, overridden


def _metric_float(raw: str) -> float:
    txt = _clean_text(raw).replace(",", "")
    m = re.search(r"\d+(?:\.\d+)?", txt)
    if not m:
        return 0.0
    try:
        return float(m.group(0))
    except Exception:
        return 0.0


def _transfer_float(raw: str) -> float:
    txt = _clean_text(raw).replace(",", "")
    nums = re.findall(r"\d+(?:\.\d+)?", txt)
    if not nums:
        return 0.0
    try:
        return max(float(x) for x in nums)
    except Exception:
        return 0.0


def _build_meta_summary(listings: list[ListingRow]) -> str:
    if not listings:
        return ""
    perf_top = sorted(listings, key=lambda x: _metric_float(x.five_year or x.three_year), reverse=True)[:3]
    transfer_top = sorted(listings, key=lambda x: _transfer_float(x.transfer_display), reverse=True)[:2]

    perf_parts: list[str] = []
    for row in perf_top:
        metric = row.five_year or row.three_year
        if not metric:
            continue
        perf_parts.append(f"{row.uid}번 {metric}억")
    transfer_parts: list[str] = []
    for row in transfer_top:
        if not row.transfer_display:
            continue
        transfer_parts.append(f"{row.uid}번 {row.transfer_display}")

    summary = "핵심 요약: "
    if perf_parts:
        summary += "고실적 매물은 " + ", ".join(perf_parts) + " 중심입니다. "
    if transfer_parts:
        summary += "대표 양도가는 " + ", ".join(transfer_parts) + " 수준입니다."
    return summary.strip()[:240]


def _build_dynamic_hero_block(year: int, month: int, count: int, listings: list[ListingRow]) -> str:
    tags: list[str] = []
    for row in listings:
        for b in row.businesses:
            btxt = _clean_text(b)
            if btxt and btxt not in tags:
                tags.append(btxt)
            if len(tags) >= 4:
                break
        if len(tags) >= 4:
            break
    if not tags:
        tags = ["건축공사업", "토목/토건", "전기·통신", "전문건설"]

    pills = "".join(
        f'<span style="display:inline-block; margin:4px; padding:8px 12px; border-radius:999px; '
        f'background:#0b2545; color:#e5e7eb; font-size:13px; font-weight:700;">{t}</span>'
        for t in tags[:4]
    )
    return f"""
    <div style="margin: 0 0 18px 0; border-radius: 12px; overflow: hidden; border: 1px solid #dbeafe;">
      <div style="background: linear-gradient(135deg, #0f172a, #1d4ed8); padding: 20px; text-align: center;">
        <p style="margin: 0; color: #bfdbfe; font-size: 14px; font-weight: 700; letter-spacing: 1px;">{year}.{month:02d} MONTHLY REPORT</p>
        <p style="margin: 8px 0 0 0; color: #fff; font-size: 28px; font-weight: 800;">건설업 양도양수 {count}선</p>
      </div>
      <div style="padding: 12px; text-align: center; background: #f8fafc;">
        {pills}
      </div>
    </div>
    """


def _build_subject(listings: list[ListingRow], year: int, month: int, count: int) -> str:
    year_short = str(year)[2:]
    base = f"[{year_short}년 {month}월] 건설업 양도양수 신규 매물 {count}선"

    top_perf = max((_metric_float(x.five_year or x.three_year) for x in listings), default=0.0)
    top_price = max((_transfer_float(x.transfer_display) for x in listings), default=0.0)
    hooks: list[str] = []
    if top_perf > 0:
        hooks.append(f"최고 실적 {_fmt_number_string(str(top_perf))}억")
    if top_price > 0:
        hooks.append(f"대표 양도가 {_fmt_number_string(str(top_price))}억")

    if hooks:
        subject = f"{base} | {' · '.join(hooks[:2])} - 서울건설정보 엄선"
    else:
        subject = f"{base} (실적·양도가 핵심 정리) - 서울건설정보 엄선"

    # 길이 과다 시 핵심 문구 유지하면서 축약
    if len(subject) > 76:
        subject = f"{base} (실적·양도가 핵심 정리) - 서울건설정보 엄선"
    return subject


def _build_top_picks_html(listings: list[ListingRow]) -> str:
    if not listings:
        return ""
    sorted_rows = sorted(
        listings,
        key=lambda x: (_metric_float(x.five_year or x.three_year), _transfer_float(x.transfer_display)),
        reverse=True,
    )
    picks = sorted_rows[:4]
    lines: list[str] = []
    for row in picks:
        biz = _join_businesses(row.businesses) or "건설업"
        perf = row.five_year or row.three_year or "-"
        transfer = _clean_text(row.transfer_display) or "협의"
        lines.append(
            f'<li style="margin:8px 0; font-size:16px; color:#1f2937;">'
            f'<strong>매물 {row.uid}</strong> · {biz} · 실적 {perf}억 · 양도가 {transfer}</li>'
        )
    return (
        '<div style="margin: 16px 0 8px 0; padding: 14px; border-radius: 10px; background: #f9fbff; border:1px solid #dbeafe;">'
        '<p style="margin:0 0 8px 0; font-size:17px; font-weight:800; color:#0f172a;">이번 달 대표 매물 TOP</p>'
        '<ul style="margin:0; padding-left:18px;">'
        + "".join(lines)
        + "</ul></div>"
    )


def _detect_latest_kakao_claim_file(raw_path: str) -> str:
    path = _clean_text(raw_path)
    if path and Path(path).exists():
        return str(Path(path).resolve())

    env_path = _clean_text(os.getenv("KAKAO_CLAIM_FILE", ""))
    if env_path and Path(env_path).exists():
        return str(Path(env_path).resolve())

    desktop = Path(os.path.expanduser("~")) / "Desktop"
    if not desktop.exists():
        return ""
    candidates = sorted(
        desktop.glob("KakaoTalk_*_group.txt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return str(candidates[0].resolve())
    return ""


def build_item_title(item: ListingRow) -> str:
    parts: list[str] = [f"매물 {item.uid}"]

    business_text = _join_businesses(item.businesses)
    if business_text:
        parts.append(f"{business_text} 양도")

    if item.five_year:
        parts.append(f"5년 실적 {item.five_year}억")
    elif item.three_year:
        parts.append(f"3년 실적 {item.three_year}억")
    elif item.license_year:
        parts.append(f"면허년도 {item.license_year}")

    transfer_amount = _clean_text(item.transfer_display) or _extract_transfer_amount(item.corp_and_transfer)
    if transfer_amount:
        parts.append(f"양도가 {transfer_amount}")

    if item.status and item.status in {"완료", "보류"}:
        parts.append(item.status)
    if item.region:
        parts.append(item.region)

    return f"[{' | '.join(parts)}]"


def build_li_html(item: ListingRow) -> str:
    url = f"{maemul.LIST_URL}/{item.uid}"
    title = build_item_title(item)
    return (
        '<li style="margin-bottom: 12px; padding: 12px 14px; border: 1px solid #e2e8f0; '
        'border-radius: 10px; background: #f8fbff;">'
        '<span style="color: #1d4ed8; margin-right: 8px; font-weight: 700;">●</span>'
        f'<a href="{url}" target="_blank" '
        'style="text-decoration: none; color: #1f2937; font-size: 17px; font-weight: 700;">'
        f"{title}</a></li>"
    )


def build_notice_html(
    listings: list[ListingRow],
    year: int,
    month: int,
    hero_image_url: str,
    bizcard_image_url: str,
    kakao_url: str,
    phone: str,
    updated_date: date,
) -> tuple[str, str]:
    count = len(listings)
    year_short = str(year)[2:]
    today = updated_date.strftime("%Y.%m.%d")
    meta_summary = _build_meta_summary(listings)
    subject = _build_subject(listings=listings, year=year, month=month, count=count)

    li_block = "\n".join(build_li_html(item) for item in listings)
    top_pick_block = _build_top_picks_html(listings)
    phone_digits = re.sub(r"[^\d]", "", phone)
    hero_block = (
        f'<p style="margin: 0 0 18px 0; text-align: center;">'
        f'<img src="{hero_image_url}" alt="{month}월 건설업 양도양수 매물 추천" '
        f'style="max-width: 100%; height: auto; border-radius: 10px; border: 1px solid #e5e7eb;"></p>'
        if _clean_text(hero_image_url)
        else _build_dynamic_hero_block(year=year, month=month, count=count, listings=listings)
    )

    body = f"""<div style="font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; max-width: 100%; margin: 0 auto; color: #1f2937; line-height: 1.8;">
  <div style="background: linear-gradient(135deg, #0a3d62, #2563eb 58%, #3b82f6); padding: 48px 20px 38px; text-align: center; border-radius: 12px 12px 0 0;">
    <h1 style="color: #fff; font-size: 29px; margin: 0; font-weight: 800; letter-spacing: -1px; line-height: 1.32;">
      [{year_short}년 {month}월] 건설업 양도양수 신규 매물 {count}선<br>
      <span style="font-size: 20px; font-weight: 500; opacity: 0.96;">(실적·양도가 핵심 정리)</span>
    </h1>
    <p style="color: #dbeafe; font-size: 16px; margin-top: 15px; font-weight: 500;">
      서울건설정보 강지현 행정사 엄선 · {today} 기준
    </p>
    <p style="margin: 16px 0 0 0;">
      <span style="display:inline-block; margin:0 4px 6px 4px; padding:6px 12px; font-size:13px; font-weight:700; border-radius:999px; background:rgba(255,255,255,0.18); color:#fff;">신규 {count}건</span>
      <span style="display:inline-block; margin:0 4px 6px 4px; padding:6px 12px; font-size:13px; font-weight:700; border-radius:999px; background:rgba(255,255,255,0.18); color:#fff;">월별 자동 누적</span>
      <span style="display:inline-block; margin:0 4px 6px 4px; padding:6px 12px; font-size:13px; font-weight:700; border-radius:999px; background:rgba(255,255,255,0.18); color:#fff;">실시간 링크</span>
    </p>
  </div>

  <div style="padding: 26px 20px 24px; border: 1px solid #d1d5db; border-top: none; background-color: #f8fafc;">
    <p style="font-size: 19px; color: #111827; margin-bottom: 12px;">
      안녕하세요, <strong>서울건설정보 강지현 행정사</strong>입니다.
    </p>
    <p style="font-size: 17px; color: #334155; margin-bottom: 0;">
      {month}월 등록 매물을 검토 우선순위에 맞춰 빠르게 보실 수 있게 정리했습니다.<br>
      아래 <strong>[매물 제목]</strong>을 클릭하면 상세 페이지로 바로 이동합니다.
    </p>
    <p style="margin-top: 10px; font-size: 15px; color:#475569;">
      건설업 양도양수 · 건설면허 양도 · 토건/건축/전기/통신 주요 매물을 한 페이지에서 비교할 수 있습니다.
    </p>
    <p style="margin-top: 14px; font-size: 16px; color: #0f172a; background: #eef6ff; border: 1px solid #cfe4ff; border-radius: 10px; padding: 12px;">
      <strong>핵심 요약(메타)</strong> {meta_summary}
    </p>
    {top_pick_block}
  </div>

  <div style="padding: 24px 20px; border: 1px solid #e5e7eb; border-top: none; background: #fff;">
    {hero_block}

    <h2 style="font-size: 24px; color: #0f172a; border-bottom: 3px solid #2563eb; padding-bottom: 12px; margin-bottom: 22px; font-weight: 800;">
      ■ {month}월 신규 등록 매물 (전체 {count}건)
    </h2>

    <div style="font-size: 18px;">
      <ul style="list-style: none; padding-left: 0; margin: 0;">
{li_block}
      </ul>
    </div>
  </div>

  <div style="margin-top: 18px; background: linear-gradient(135deg, #0b1f35, #16324f); padding: 34px 20px; text-align: center; border-radius: 0 0 12px 12px;">
    <p style="font-size: 22px; font-weight: 800; color: #f8fafc; margin-bottom: 12px;">
      원하는 조건의 비공개 매물도 빠르게 안내해 드립니다
    </p>
    <p style="font-size: 17px; color: #cbd5e1; margin-bottom: 22px;">
      실적/지역/예산 기준을 알려주시면 매칭 가능한 매물을 정리해 드립니다.
    </p>
    <p style="margin: 0 0 14px 0;">
      <a href="{kakao_url}" target="_blank" rel="noopener nofollow" style="display: inline-block; background-color: #FEE500; color: #191919; padding: 14px 28px; text-decoration: none; font-size: 18px; font-weight: 800; border-radius: 999px; margin: 0 6px 8px 6px;">
        카카오톡 1:1 상담
      </a>
      <a href="tel:{phone_digits}" style="display: inline-block; background-color: #3182F6; color: #fff; padding: 14px 28px; text-decoration: none; font-size: 18px; font-weight: 800; border-radius: 999px; margin: 0 6px 8px 6px;">
        전화 바로 연결
      </a>
    </p>
    <p style="font-size: 15px; color: #93c5fd; margin: 8px 0 18px 0;">대표 상담: {phone}</p>
    <p style="margin: 0;">
      <img src="{bizcard_image_url}" alt="강지현 행정사 건설업 양도양수 전문 상담 명함" style="max-width: 100%; height: auto; border: 1px solid #334155;">
    </p>
  </div>
</div>
"""
    return subject, body


def infer_default_min_uid(year: int, month: int) -> int | None:
    month_start_uid = {
        (2026, 2): 7684,
    }
    return month_start_uid.get((year, month))


def _month_key(y: int, m: int) -> str:
    return f"{int(y):04d}-{int(m):02d}"


def _parse_month_key(key: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d{4})-(\d{2})", str(key or "").strip())
    if not m:
        raise ValueError(f"Invalid month key: {key}")
    return int(m.group(1)), int(m.group(2))


def _parse_run_date(raw: str) -> date:
    txt = str(raw or "").strip()
    if not txt:
        return datetime.now().date()
    return datetime.strptime(txt, "%Y-%m-%d").date()


def _load_month_state(path: Path) -> dict:
    base = {"uid_month_map": {}, "updated_at": ""}
    if not path.exists():
        return base
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return base
        uid_map = data.get("uid_month_map", {})
        if not isinstance(uid_map, dict):
            uid_map = {}
        normalized: dict[str, str] = {}
        for k, v in uid_map.items():
            uid = str(k).strip()
            month = str(v).strip()
            if not uid.isdigit():
                continue
            if not re.fullmatch(r"\d{4}-\d{2}", month):
                continue
            normalized[uid] = month
        return {"uid_month_map": normalized, "updated_at": str(data.get("updated_at", "")).strip()}
    except Exception:
        return base


def _save_month_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(state or {})
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _assign_uid_months(
    listings: list[ListingRow],
    uid_month_map: dict[str, str],
    assign_month_key: str,
) -> tuple[dict[str, str], int]:
    changed = 0
    out = dict(uid_month_map or {})
    for item in listings:
        uid = str(item.uid)
        if uid in out:
            continue
        out[uid] = assign_month_key
        changed += 1
    return out, changed


def _write_notice_bundle(base_dir: Path, prefix: str, listings: list[ListingRow], subject: str, body: str) -> dict:
    base_dir.mkdir(parents=True, exist_ok=True)
    subject_path = base_dir / f"{prefix}_subject.txt"
    body_path = base_dir / f"{prefix}_body.html"
    list_path = base_dir / f"{prefix}_list_only.html"
    ids_path = base_dir / f"{prefix}_uids.txt"

    subject_path.write_text(subject + "\n", encoding="utf-8")
    body_path.write_text(body, encoding="utf-8")
    list_path.write_text("\n".join(build_li_html(item) for item in listings) + "\n", encoding="utf-8")
    ids_path.write_text("\n".join(str(item.uid) for item in listings) + "\n", encoding="utf-8")

    return {
        "subject": str(subject_path),
        "body": str(body_path),
        "list": str(list_path),
        "uids": str(ids_path),
        "count": len(listings),
    }


def parse_args() -> argparse.Namespace:
    now = datetime.now()
    parser = argparse.ArgumentParser(description="Build monthly SeoulMNA notice draft(s) from maemul data.")
    parser.add_argument("--year", type=int, default=now.year)
    parser.add_argument("--month", type=int, default=now.month)
    parser.add_argument("--pages", type=int, default=10, help="How many MNA list pages to scan.")
    parser.add_argument(
        "--min-uid",
        type=int,
        default=None,
        help="Include rows with UID >= min_uid. If omitted, known month baseline is used when available.",
    )
    parser.add_argument("--include-completed", action="store_true", help="Include status='완료' rows.")
    parser.add_argument("--hero-image-url", default=DEFAULT_HERO_IMAGE)
    parser.add_argument("--bizcard-image-url", default=DEFAULT_BIZCARD_IMAGE)
    parser.add_argument("--kakao-url", default=DEFAULT_KAKAO_URL)
    parser.add_argument("--phone", default=DEFAULT_PHONE)
    parser.add_argument(
        "--kakao-claim-file",
        default="",
        help="카카오톡 대화 txt 경로. 입력 시 now_uid 기준 청구 양도가를 대조해 제목 양도가를 보정합니다.",
    )
    parser.add_argument("--kakao-claim-sender", default=DEFAULT_CLAIM_SENDER)
    parser.add_argument(
        "--no-sheet-transfer-sync",
        action="store_true",
        help="시트/카카오 대조를 비활성화하고 목록 원문 양도가만 사용합니다.",
    )
    parser.add_argument("--output-dir", default=str(ROOT / "output"))
    parser.add_argument("--monthly-archive", action="store_true", help="Generate rolling month-by-month bundles.")
    parser.add_argument(
        "--run-date",
        default="",
        help="Date used to assign new UIDs in monthly archive mode (YYYY-MM-DD, default=today).",
    )
    parser.add_argument(
        "--state-file",
        default=str(DEFAULT_STATE_FILE),
        help="State file path for UID->month mapping in monthly archive mode.",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Ignore existing state file and rebuild UID->month mapping from current run scope.",
    )
    parser.add_argument(
        "--archive-dir",
        default="",
        help="Output directory for monthly archive bundles (default: <output-dir>/notice_archive).",
    )
    return parser.parse_args()


def run_single_month(args: argparse.Namespace, listings: list[ListingRow]) -> int:
    subject, body = build_notice_html(
        listings=listings,
        year=args.year,
        month=args.month,
        hero_image_url=args.hero_image_url,
        bizcard_image_url=args.bizcard_image_url,
        kakao_url=args.kakao_url,
        phone=args.phone,
        updated_date=datetime.now().date(),
    )
    output_dir = Path(args.output_dir)
    prefix = f"notice_{args.year}_{args.month:02d}"
    bundle = _write_notice_bundle(output_dir, prefix, listings, subject, body)

    print(f"subject: {bundle['subject']}")
    print(f"body:    {bundle['body']}")
    print(f"list:    {bundle['list']}")
    print(f"uids:    {bundle['uids']}")
    print(f"count:   {bundle['count']}")
    return 0


def run_monthly_archive(args: argparse.Namespace, listings: list[ListingRow]) -> int:
    run_dt = _parse_run_date(args.run_date)
    current_month_key = _month_key(run_dt.year, run_dt.month)
    state_file = Path(args.state_file)
    state = {"uid_month_map": {}, "updated_at": ""} if args.reset_state else _load_month_state(state_file)
    uid_month_map, assigned = _assign_uid_months(
        listings=listings,
        uid_month_map=dict(state.get("uid_month_map", {}) or {}),
        assign_month_key=current_month_key,
    )
    state["uid_month_map"] = uid_month_map
    _save_month_state(state_file, state)

    grouped: dict[str, list[ListingRow]] = {}
    for item in listings:
        key = uid_month_map.get(str(item.uid), current_month_key)
        grouped.setdefault(key, []).append(item)

    archive_dir = Path(args.archive_dir) if str(args.archive_dir).strip() else (Path(args.output_dir) / "notice_archive")
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_date": run_dt.isoformat(),
        "assigned_new_uids": assigned,
        "state_file": str(state_file),
        "months": [],
    }

    for month_key in sorted(grouped.keys(), reverse=True):
        year, month = _parse_month_key(month_key)
        month_listings = sorted(grouped[month_key], key=lambda x: x.uid, reverse=True)
        subject, body = build_notice_html(
            listings=month_listings,
            year=year,
            month=month,
            hero_image_url=args.hero_image_url,
            bizcard_image_url=args.bizcard_image_url,
            kakao_url=args.kakao_url,
            phone=args.phone,
            updated_date=run_dt,
        )
        month_dir = archive_dir / f"{year}_{month:02d}"
        prefix = f"notice_{year}_{month:02d}"
        bundle = _write_notice_bundle(month_dir, prefix, month_listings, subject, body)
        manifest["months"].append(
            {
                "month_key": month_key,
                "count": len(month_listings),
                "subject": bundle["subject"],
                "body": bundle["body"],
                "list": bundle["list"],
                "uids": bundle["uids"],
            }
        )

    archive_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = archive_dir / "notice_archive_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"state:    {state_file}")
    print(f"manifest: {manifest_path}")
    print(f"months:   {len(manifest['months'])}")
    print(f"new_uids_assigned_to_{current_month_key}: {assigned}")
    for m in manifest["months"]:
        print(f" - {m['month_key']}: {m['count']}건 -> {m['body']}")
    return 0


def main() -> int:
    args = parse_args()
    min_uid = args.min_uid
    if args.monthly_archive:
        run_dt = _parse_run_date(args.run_date)
        if min_uid is None:
            min_uid = infer_default_min_uid(run_dt.year, run_dt.month)
        state_file = Path(args.state_file)
        if min_uid is None and not state_file.exists():
            print(
                "Bootstrap needed: first monthly-archive run requires --min-uid "
                "(or add infer_default_min_uid mapping for this month)."
            )
            return 1
    else:
        if min_uid is None:
            min_uid = infer_default_min_uid(args.year, args.month)

    listings = collect_listings(
        pages=args.pages,
        min_uid=min_uid,
        include_completed=args.include_completed,
    )
    if not listings:
        print("No listings found. Increase --pages or adjust --min-uid.")
        return 1

    if not args.no_sheet_transfer_sync:
        claim_file = _detect_latest_kakao_claim_file(args.kakao_claim_file)
        listings, overridden = _enrich_listings_with_transfer_source(
            listings=listings,
            chat_file=claim_file,
            chat_sender=args.kakao_claim_sender,
        )
        print(f"transfer_overrides_applied: {overridden}")
        if claim_file:
            print(f"kakao_claim_file: {claim_file}")

    if args.monthly_archive:
        return run_monthly_archive(args, listings)
    return run_single_month(args, listings)


if __name__ == "__main__":
    raise SystemExit(main())
