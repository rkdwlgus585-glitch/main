#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import html
import json
import mimetypes
import os
import posixpath
import re
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://seoulmna.co.kr"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "imported"
PUBLIC_DIR = PROJECT_ROOT / "public"
ASSET_DIR = PUBLIC_DIR / "imported-assets"
TIMEOUT = 30
SAFE_ATTRS = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height", "loading", "decoding"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
    "table": {"summary"},
}
ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "del",
    "div",
    "em",
    "figcaption",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "section",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
ATTACHMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".csv",
    ".zip",
    ".hwp",
    ".hwpx",
    ".ppt",
    ".pptx",
}

PAGE_GROUPS = {
    "registration": {"n1s", "g1", "k1", "ks1"},
    "corporate": {"bs1"},
    "split-merger": {"h1", "h2", "h3", "h4", "h5"},
    "practice": {"ks2", "k3", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9"},
    "support": {"order", "map", "privacy"},
    "mna-info": {"mna", "mna01"},
}


@dataclass(slots=True)
class BoardConfig:
    name: str
    list_path: str
    detail_prefix: str | None
    render_selector: str | None = None
    max_pages: int | None = None
    detail_pattern: str | None = None


BOARD_CONFIGS = {
    "mna": BoardConfig(name="mna", list_path="/mna", detail_prefix="/mna/", detail_pattern=r"^/mna/\d+$"),
    "notice": BoardConfig(name="notice", list_path="/notice", detail_prefix="/notice/", render_selector="#bo_v_con", detail_pattern=r"^/notice/\d+$"),
    "premium": BoardConfig(name="premium", list_path="/premium", detail_prefix="/premium/", render_selector="#bo_v_con", detail_pattern=r"^/premium/\d+$"),
    "news": BoardConfig(name="news", list_path="/news", detail_prefix="/news/", render_selector="#bo_v_con", detail_pattern=r"^/news/\d+$"),
    "tl_faq": BoardConfig(name="tl_faq", list_path="/tl_faq", detail_prefix=None, render_selector="div.txtCon"),
}


def build_session() -> requests.Session:
    retry = Retry(
        total=3,
        read=3,
        connect=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; SeoulMnaLegacyImporter/1.0; +https://seoulmna.co.kr)",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        }
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)


def fetch(session: requests.Session, url: str) -> requests.Response:
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding or "utf-8"
    return response


def read_soup(session: requests.Session, url: str) -> tuple[requests.Response, BeautifulSoup]:
    response = fetch(session, url)
    return response, BeautifulSoup(response.text, "lxml")


def normalize_internal_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != urlparse(BASE_URL).netloc:
        return url
    query = f"?{parsed.query}" if parsed.query else ""
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    path = parsed.path or "/"
    return f"{path}{query}{fragment}"


def canonical_internal_url(url: str, base_url: str) -> str:
    absolute = absolute_url(url, base_url)
    if not is_internal_url(absolute):
        return absolute

    parsed = urlparse(absolute)
    path = parsed.path or "/"
    base = urlparse(BASE_URL)
    return urlunparse((base.scheme, base.netloc, path, "", "", ""))


def absolute_url(url: str, base_url: str) -> str:
    if not url:
        return base_url
    if url.startswith("//"):
        return f"https:{url}"
    return urljoin(base_url, url)


def is_internal_url(url: str) -> bool:
    parsed = urlparse(url)
    return not parsed.netloc or parsed.netloc == urlparse(BASE_URL).netloc


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def excerpt(text: str, *, max_length: int = 180) -> str:
    normalized = clean_text(text)
    if len(normalized) <= max_length:
        return normalized
    clipped = normalized[: max_length - 1].rsplit(" ", 1)[0].strip()
    return f"{clipped}…"


def slug_from_path(path: str) -> str:
    filename = posixpath.basename(urlparse(path).path)
    if filename.endswith(".php"):
        filename = filename[:-4]
    return filename or "index"


def get_group_for_slug(slug: str) -> str | None:
    for group, slugs in PAGE_GROUPS.items():
        if slug in slugs:
            return group
    return None


def sha_name(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def ensure_asset_downloaded(
    session: requests.Session,
    asset_url: str,
    asset_scope: str,
    *,
    skip_assets: bool,
) -> str:
    normalized = absolute_url(asset_url, BASE_URL)
    if not is_internal_url(normalized):
        return normalized
    if skip_assets:
        return normalize_internal_url(normalized)

    parsed = urlparse(normalized)
    ext = Path(parsed.path).suffix.lower()
    if not ext:
        ext = mimetypes.guess_extension(fetch_head_content_type(session, normalized)) or ".bin"

    digest = sha_name(normalized)
    filename = f"{digest}{ext}"
    target_dir = ASSET_DIR / asset_scope
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename

    if not target_file.exists():
        response = session.get(normalized, timeout=TIMEOUT, stream=True)
        response.raise_for_status()
        with target_file.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    handle.write(chunk)

    return f"/imported-assets/{asset_scope}/{filename}"


def fetch_head_content_type(session: requests.Session, url: str) -> str:
    try:
        response = session.head(url, timeout=TIMEOUT, allow_redirects=True)
        response.raise_for_status()
        return response.headers.get("Content-Type", "")
    except requests.RequestException:
        return ""


def sanitize_fragment(
    session: requests.Session,
    node: Tag,
    *,
    source_url: str,
    asset_scope: str,
    skip_assets: bool,
) -> tuple[str, str]:
    soup = BeautifulSoup(str(node), "lxml")
    root = soup.body or soup

    for comment in root.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    for tag in root.find_all(["script", "style", "noscript", "iframe", "form", "input", "button", "select", "option", "textarea", "svg", "canvas"]):
        tag.decompose()

    for tag in list(root.find_all(True)):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue

        allowed = SAFE_ATTRS.get(tag.name, set())
        for attr in list(tag.attrs):
            if attr not in allowed:
                del tag.attrs[attr]

        if tag.name == "a" and tag.get("href"):
            raw_href = clean_text(tag["href"])
            if re.fullmatch(r"[0-9+\-\s()]+", raw_href):
                phone_number = re.sub(r"\D", "", raw_href)
                if 8 <= len(phone_number) <= 13:
                    tag["href"] = f"tel:{phone_number}"
                    continue

            href = absolute_url(raw_href, source_url)
            parsed = urlparse(href)
            if parsed.scheme in {"tel", "mailto"}:
                tag["href"] = href
                continue
            if parsed.scheme and parsed.scheme not in {"http", "https"}:
                del tag["href"]
                continue
            suffix = Path(parsed.path).suffix.lower()
            if is_internal_url(href) and suffix in ATTACHMENT_EXTENSIONS:
                tag["href"] = ensure_asset_downloaded(session, href, f"{asset_scope}/files", skip_assets=skip_assets)
            elif is_internal_url(href):
                tag["href"] = normalize_internal_url(href)
            else:
                tag["href"] = href
                tag["rel"] = "noopener noreferrer"
                tag["target"] = "_blank"

        if tag.name == "img" and tag.get("src"):
            tag["src"] = ensure_asset_downloaded(session, tag["src"], f"{asset_scope}/images", skip_assets=skip_assets)
            tag["loading"] = "lazy"
            tag["decoding"] = "async"

    html_value = "".join(str(child) for child in root.contents).strip()
    text_value = clean_text(root.get_text(" ", strip=True))
    return html_value, text_value


def table_rows(table: Tag) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        row = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        if row:
            rows.append(row)
    return rows


def parse_listing_sections(root: Tag) -> tuple[dict[str, str], list[list[str]], dict[str, str], list[str], list[str], str]:
    overview: dict[str, str] = {}
    performance_rows: list[list[str]] = []
    finance: dict[str, str] = {}
    notes: list[str] = []
    guidance: list[str] = []

    for heading in root.find_all("h3"):
        title = clean_text(heading.get_text(" ", strip=True))
        table = heading.find_next_sibling("table")
        if title == "회사개요" and table:
            for row in table_rows(table):
                for index in range(0, len(row), 2):
                    if index + 1 < len(row):
                        overview[row[index]] = row[index + 1]
        elif title == "최근년도 매출실적" and table:
            performance_rows = table_rows(table)
        elif title == "재무제표" and table:
            for row in table_rows(table):
                for index in range(0, len(row), 2):
                    if index + 1 < len(row):
                        finance[row[index]] = row[index + 1]
        elif title == "주요체크사항" and table:
            note_text = " ".join(table.get_text(" ", strip=True).split())
            notes = [clean_text(item) for item in re.split(r"\s*\*\s*", note_text) if clean_text(item)]

    for paragraph in root.find_all("p"):
        text = clean_text(paragraph.get_text(" ", strip=True))
        if text.startswith("안내") or text.startswith("정밀한") or text.startswith("검색창에"):
            guidance.append(text)

    title_text = overview.get("양도가") or "건설업 양도양수 매물"
    return overview, performance_rows, finance, notes, guidance, title_text


def build_html_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    head = rows[0]
    body = rows[1:] if len(rows) > 1 else []
    head_html = "".join(f"<th>{html.escape(cell)}</th>" for cell in head)
    body_html = []
    for row in body:
        body_html.append("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>")
    if body:
        return f"<table><thead><tr>{head_html}</tr></thead><tbody>{''.join(body_html)}</tbody></table>"
    return f"<table><tbody><tr>{head_html}</tr></tbody></table>"


def build_pairs_table(pairs: dict[str, str]) -> str:
    rows = []
    for key, value in pairs.items():
        rows.append(f"<tr><th>{html.escape(key)}</th><td>{html.escape(value or '-')}</td></tr>")
    return f"<table><tbody>{''.join(rows)}</tbody></table>"


def build_listing_content_html(
    overview: dict[str, str],
    performance_rows: list[list[str]],
    finance: dict[str, str],
    notes: list[str],
    guidance: list[str],
) -> str:
    parts = ['<div class="legacy-listing-content">']
    if overview:
        parts.append("<section><h2>회사개요</h2>")
        parts.append(build_pairs_table(overview))
        parts.append("</section>")
    if performance_rows:
        parts.append("<section><h2>최근년도 매출실적</h2>")
        parts.append(build_html_table(performance_rows))
        parts.append("</section>")
    if finance:
        parts.append("<section><h2>재무제표</h2>")
        parts.append(build_pairs_table(finance))
        parts.append("</section>")
    if notes:
        parts.append("<section><h2>주요체크사항</h2><ul>")
        parts.extend(f"<li>{html.escape(note)}</li>" for note in notes)
        parts.append("</ul></section>")
    if guidance:
        parts.append('<section><h2>안내</h2><div class="legacy-guidance">')
        parts.extend(f"<p>{html.escape(item)}</p>" for item in guidance)
        parts.append("</div></section>")
    parts.append("</div>")
    return "".join(parts)


def derive_listing_summary(
    detail_url: str,
    imported_at: str,
    overview: dict[str, str],
    performance_rows: list[list[str]],
    notes: list[str],
) -> dict[str, Any]:
    sectors: list[str] = []
    license_years: list[str] = []
    capacities: list[str] = []
    performance3: list[str] = []
    performance5: list[str] = []
    annual_latest: list[str] = []

    if performance_rows:
        header = performance_rows[0]
        header_index = {cell: idx for idx, cell in enumerate(header)}
        for row in performance_rows[1:]:
            if not row:
                continue
            sectors.append(row[header_index.get("업종", 0)] if header_index.get("업종", 0) < len(row) else "")
            license_years.append(row[header_index.get("면허년도", 1)] if header_index.get("면허년도", 1) < len(row) else "")
            capacities.append(row[header_index.get("시공능력", 2)] if header_index.get("시공능력", 2) < len(row) else "")
            if "3년" in header_index and header_index["3년"] < len(row):
                performance3.append(row[header_index["3년"]])
            elif "3년실적" in header_index and header_index["3년실적"] < len(row):
                performance3.append(row[header_index["3년실적"]])
            if "5년" in header_index and header_index["5년"] < len(row):
                performance5.append(row[header_index["5년"]])
            elif "5년실적" in header_index and header_index["5년실적"] < len(row):
                performance5.append(row[header_index["5년실적"]])
            if "25" in header_index and header_index["25"] < len(row):
                annual_latest.append(row[header_index["25"]])
            elif "2025" in header_index and header_index["2025"] < len(row):
                annual_latest.append(row[header_index["2025"]])

    listing_id = re.search(r"/mna/(\d+)", detail_url)
    summary_note = notes[0] if notes else ""
    sector_label = " · ".join([value for value in sectors if value]) or "건설업"
    title = f"{sector_label} 양도양수 매물"
    headline_parts = [value for value in [overview.get("소재지"), overview.get("회사형태"), overview.get("양도가")] if value]
    return {
        "id": listing_id.group(1) if listing_id else detail_url.rsplit("/", 1)[-1],
        "title": title,
        "headline": " · ".join(headline_parts),
        "updatedAt": imported_at,
        "status": overview.get("상태", ""),
        "sectors": [value for value in sectors if value],
        "sectorLabel": sector_label,
        "region": overview.get("소재지", ""),
        "companyType": overview.get("회사형태", ""),
        "companyYear": overview.get("법인설립일", ""),
        "association": overview.get("공제조합 출자좌", ""),
        "capital": overview.get("자본금", ""),
        "balance": overview.get("대출후 남은잔액", ""),
        "price": overview.get("양도가", ""),
        "licenseYears": [value for value in license_years if value],
        "capacityLabel": " / ".join([value for value in capacities if value]) or "-",
        "performance3Year": " / ".join([value for value in performance3 if value]) or "-",
        "performance5Year": " / ".join([value for value in performance5 if value]) or "-",
        "performance2025": " / ".join([value for value in annual_latest if value]) or "-",
        "note": summary_note,
        "sourceUrl": normalize_internal_url(detail_url),
    }


def parse_listing_detail(
    session: requests.Session,
    detail_url: str,
    *,
    imported_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _, soup = read_soup(session, detail_url)
    root = soup.select_one("div.txtCon.txtboard")
    if root is None:
        raise ValueError(f"listing content root not found: {detail_url}")

    overview, performance_rows, finance, notes, guidance, title_text = parse_listing_sections(root)
    summary = derive_listing_summary(detail_url, imported_at, overview, performance_rows, notes)
    detail = {
        **summary,
        "sourceUrl": normalize_internal_url(detail_url),
        "contentHtml": build_listing_content_html(overview, performance_rows, finance, notes, guidance),
        "guidance": guidance,
        "legacyTitle": title_text,
        "overview": overview,
        "performanceRows": performance_rows,
        "finance": finance,
        "notes": notes,
    }
    return summary, detail


def pick_first_text(soup: BeautifulSoup, selectors: list[str]) -> str:
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = clean_text(node.get_text(" ", strip=True))
            if text:
                return text
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    return title.split(">")[0].strip()


def find_render_root(soup: BeautifulSoup, selector: str | None) -> Tag:
    if selector:
        node = soup.select_one(selector)
        if node:
            return node
    candidates = [
        "div.container-fluid.margin-top-20",
        "div.txtCon.txtboard",
        "#bo_v_con",
        "#fboardlist",
        "#bo_list",
    ]
    for candidate in candidates:
        node = soup.select_one(candidate)
        if node:
            return node
    raise ValueError("render root not found")


def parse_article_detail(
    session: requests.Session,
    board_name: str,
    detail_url: str,
    *,
    render_selector: str | None,
    imported_at: str,
    skip_assets: bool,
) -> dict[str, Any]:
    _, soup = read_soup(session, detail_url)
    root = find_render_root(soup, render_selector)
    content_html, content_text = sanitize_fragment(
        session,
        root,
        source_url=detail_url,
        asset_scope=f"{board_name}/{sha_name(detail_url)[:12]}",
        skip_assets=skip_assets,
    )

    title = pick_first_text(
        soup,
        ["#bo_v_title", ".bo_v_tit", "main h1:last-of-type", "h1:last-of-type", "h1", "h2:first-of-type"],
    )
    if not title:
        title = clean_text((soup.title.get_text(" ", strip=True) if soup.title else "").split(">")[0])

    date_match = re.search(r"작성일\s*[:：]?\s*(\d{2,4}[.\-/]\d{1,2}[.\-/]\d{1,2}(?:\s+\d{1,2}:\d{2})?)", soup.get_text(" ", strip=True))
    views_match = re.search(r"조회\s*(\d+)", soup.get_text(" ", strip=True))

    post_id_match = re.search(rf"/{re.escape(board_name)}/(\d+)", detail_url)
    return {
        "id": post_id_match.group(1) if post_id_match else detail_url.rsplit("/", 1)[-1],
        "board": board_name,
        "title": title,
        "summary": excerpt(content_text),
        "publishedAt": date_match.group(1).replace(".", "-").replace("/", "-") if date_match else imported_at[:10],
        "updatedAt": imported_at,
        "views": int(views_match.group(1)) if views_match else None,
        "sourceUrl": normalize_internal_url(detail_url),
        "contentHtml": content_html,
    }


def parse_static_page(
    session: requests.Session,
    page_url: str,
    *,
    imported_at: str,
    skip_assets: bool,
) -> dict[str, Any]:
    _, soup = read_soup(session, page_url)
    slug = slug_from_path(page_url)
    if slug == "map":
        iframe = soup.find("iframe")
        address = clean_text(
            soup.get_text(" ", strip=True).split("주소", 1)[-1]
        )
        iframe_src = iframe.get("src") if iframe else ""
        content_html = (
            "<div class=\"legacy-map-content\">"
            f"<p>{html.escape('서울건설정보 상담 오피스 위치 안내입니다.')}</p>"
            f"<p>{html.escape(address or '서울시 영등포구 국제금융로 8길 27-8 NH농협캐피탈 빌딩 4층')}</p>"
            f"<p><a href=\"{html.escape(iframe_src)}\" target=\"_blank\" rel=\"noopener noreferrer\">지도 크게 보기</a></p>"
            "</div>"
        )
        content_text = clean_text(address or "서울건설정보 오시는 길")
    elif slug == "order":
        intro = next(
            (clean_text(tag.get_text(" ", strip=True)) for tag in soup.find_all("p") if "건설업양도양수" in tag.get_text(" ", strip=True)),
            "상담 유형과 연락처를 남겨주시면 순차적으로 연락드리는 상담 안내 페이지입니다.",
        )
        form = soup.find("form")
        fields = []
        if form:
            for cell in form.find_all(["th", "td"]):
                text = clean_text(cell.get_text(" ", strip=True))
                if text and text not in fields:
                    fields.append(text)
        list_items = "".join(f"<li>{html.escape(item)}</li>" for item in fields[:12])
        content_html = (
            "<div class=\"legacy-order-content\">"
            f"<p>{html.escape(intro)}</p>"
            f"<ul>{list_items}</ul>"
            "</div>"
        )
        content_text = clean_text(f"{intro} {' '.join(fields[:12])}")
    else:
        root = find_render_root(soup, "div.container-fluid.margin-top-20")
        content_html, content_text = sanitize_fragment(
            session,
            root,
            source_url=page_url,
            asset_scope=f"pages/{slug}",
            skip_assets=skip_assets,
        )
    title = pick_first_text(soup, ["body h3:first-of-type", "body h2:first-of-type", "h1:first-of-type"])
    return {
        "slug": slug,
        "title": title or slug,
        "summary": excerpt(content_text),
        "contentHtml": content_html,
        "updatedAt": imported_at,
        "sourceUrl": normalize_internal_url(page_url),
        "group": get_group_for_slug(slug),
    }


def parse_page_count(list_url: str, soup: BeautifulSoup) -> int:
    max_page = 1
    list_path = urlparse(list_url).path
    for anchor in soup.find_all("a", href=True):
        href = absolute_url(anchor["href"], list_url)
        parsed = urlparse(href)
        if parsed.path != list_path:
            continue
        query = parse_qs(parsed.query)
        if "page" in query:
            try:
                max_page = max(max_page, int(query["page"][0]))
            except (ValueError, TypeError):
                continue
    return max_page


def crawl_board_detail_urls(
    session: requests.Session,
    config: BoardConfig,
    *,
    page_limit: int | None,
) -> list[str]:
    list_url = absolute_url(config.list_path, BASE_URL)
    _, soup = read_soup(session, list_url)
    max_page = parse_page_count(list_url, soup)
    if page_limit:
        max_page = min(max_page, page_limit)
    if config.max_pages:
        max_page = min(max_page, config.max_pages)

    urls: "OrderedDict[str, None]" = OrderedDict()
    for page_number in range(1, max_page + 1):
        page_url = list_url if page_number == 1 else f"{list_url}?&company_name=&page={page_number}"
        _, page_soup = read_soup(session, page_url)
        for anchor in page_soup.find_all("a", href=True):
            href = absolute_url(anchor["href"], page_url)
            if not is_internal_url(href):
                continue

            normalized_path = urlparse(href).path or "/"
            if config.detail_prefix and normalized_path.startswith(config.detail_prefix):
                if config.detail_pattern and not re.match(config.detail_pattern, normalized_path):
                    continue
                urls[canonical_internal_url(href, page_url)] = None
    return list(urls.keys())


def parse_tl_faq_page(
    session: requests.Session,
    config: BoardConfig,
    *,
    imported_at: str,
    skip_assets: bool,
) -> dict[str, Any]:
    page_url = absolute_url(config.list_path, BASE_URL)
    _, soup = read_soup(session, page_url)
    content_blocks: list[str] = []
    seen_blocks: set[str] = set()
    faq_items: list[dict[str, str]] = []
    for heading in soup.find_all(["h1", "h2"]):
        text = clean_text(heading.get_text(" ", strip=True))
        if not text or text == "자주하는 질문":
            continue

        container = heading.find_parent("div")
        if container is None:
            continue

        if heading.name == "h2":
            answer = next(
                (
                    clean_text(paragraph.get_text(" ", strip=True))
                    for paragraph in container.find_all("p")
                    if clean_text(paragraph.get_text(" ", strip=True))
                ),
                "",
            )
            if answer:
                faq_items.append({"question": text, "answer": answer})

        block_html = str(container)
        if block_html in seen_blocks:
            continue

        seen_blocks.add(block_html)
        content_blocks.append(block_html)

    synthetic_root = BeautifulSoup(f"<div>{''.join(content_blocks)}</div>", "lxml").div
    if synthetic_root is None:
        raise ValueError("faq content root not found")

    content_html, content_text = sanitize_fragment(
        session,
        synthetic_root,
        source_url=page_url,
        asset_scope="tl_faq/index",
        skip_assets=skip_assets,
    )
    hero_title = pick_first_text(soup, ["h1:last-of-type", "h1:first-of-type"])
    return {
        "id": "index",
        "board": "tl_faq",
        "title": hero_title,
        "summary": excerpt(content_text),
        "publishedAt": imported_at[:10],
        "updatedAt": imported_at,
        "views": None,
        "sourceUrl": normalize_internal_url(page_url),
        "contentHtml": content_html,
        "faqItems": faq_items,
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def import_mna(
    session: requests.Session,
    *,
    imported_at: str,
    workers: int,
    limit: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    detail_urls = crawl_board_detail_urls(session, BOARD_CONFIGS["mna"], page_limit=limit)
    summaries: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(parse_listing_detail, session, url, imported_at=imported_at) for url in detail_urls]
        for future in concurrent.futures.as_completed(futures):
            summary, detail = future.result()
            summaries.append(summary)
            details.append(detail)

    order = {
        re.search(r"/mna/(\d+)", url).group(1): index
        for index, url in enumerate(detail_urls)
        if re.search(r"/mna/(\d+)", url)
    }
    summaries.sort(key=lambda item: order.get(item["id"], 10**9))
    details.sort(key=lambda item: order.get(item["id"], 10**9))
    return summaries, details


def import_board_posts(
    session: requests.Session,
    board_name: str,
    *,
    imported_at: str,
    workers: int,
    limit: int | None,
    skip_assets: bool,
) -> list[dict[str, Any]]:
    config = BOARD_CONFIGS[board_name]
    detail_urls = crawl_board_detail_urls(session, config, page_limit=limit)
    posts: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                parse_article_detail,
                session,
                board_name,
                url,
                render_selector=config.render_selector,
                imported_at=imported_at,
                skip_assets=skip_assets,
            )
            for url in detail_urls
        ]
        for future in concurrent.futures.as_completed(futures):
            posts.append(future.result())

    order = {normalize_internal_url(url): index for index, url in enumerate(detail_urls)}
    posts.sort(key=lambda item: order.get(item["sourceUrl"], 10**9))
    return posts


def import_static_pages(
    session: requests.Session,
    *,
    imported_at: str,
    skip_assets: bool,
) -> list[dict[str, Any]]:
    sitemap_response = fetch(session, f"{BASE_URL}/sitemap.xml")
    sitemap = BeautifulSoup(sitemap_response.text, "xml")
    page_urls = []
    for loc in sitemap.find_all("loc"):
        value = clean_text(loc.get_text())
        if value.startswith(f"{BASE_URL}/pages/"):
            page_urls.append(value)

    pages = [
        parse_static_page(session, page_url, imported_at=imported_at, skip_assets=skip_assets)
        for page_url in sorted(set(page_urls))
    ]
    pages.sort(key=lambda item: item["slug"])
    return pages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import legacy seoulmna.co.kr content into local JSON files.")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers for detail fetches.")
    parser.add_argument("--limit", type=int, default=None, help="Limit paginated board pages for dry runs.")
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        choices=["mna", "notice", "premium", "news", "tl_faq", "pages"],
        help="Restrict import to specific content groups.",
    )
    parser.add_argument("--skip-assets", action="store_true", help="Do not mirror internal images/files locally.")
    return parser.parse_args()


def read_existing_manifest_counts() -> dict[str, int]:
    manifest_path = OUTPUT_DIR / "manifest.json"
    if not manifest_path.exists():
        return {}

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}

    counts = manifest.get("counts", {})
    if not isinstance(counts, dict):
        return {}

    return {str(key): int(value) for key, value in counts.items() if isinstance(value, int)}


def main() -> int:
    args = parse_args()
    ensure_dirs()
    imported_at = datetime.now(UTC).astimezone().isoformat(timespec="seconds")
    session = build_session()

    only = set(args.only or ["mna", "notice", "premium", "news", "tl_faq", "pages"])
    manifest: dict[str, Any] = {
        "source": BASE_URL,
        "generatedAt": imported_at,
        "counts": read_existing_manifest_counts(),
        "options": {
            "workers": args.workers,
            "limit": args.limit,
            "skipAssets": args.skip_assets,
        },
    }

    if "mna" in only:
        print("[import] mna listings", flush=True)
        listing_summaries, listing_details = import_mna(
            session,
            imported_at=imported_at,
            workers=max(1, args.workers),
            limit=args.limit,
        )
        write_json(OUTPUT_DIR / "listing-summaries.json", listing_summaries)
        write_json(OUTPUT_DIR / "listing-details.json", listing_details)
        manifest["counts"]["mna"] = len(listing_summaries)

    for board_name in ("notice", "premium", "news"):
        if board_name not in only:
            continue
        print(f"[import] {board_name} posts", flush=True)
        posts = import_board_posts(
            session,
            board_name,
            imported_at=imported_at,
            workers=max(1, args.workers),
            limit=args.limit,
            skip_assets=args.skip_assets,
        )
        write_json(OUTPUT_DIR / f"{board_name}-posts.json", posts)
        manifest["counts"][board_name] = len(posts)

    if "tl_faq" in only:
        print("[import] tl_faq page", flush=True)
        faq_page = parse_tl_faq_page(
            session,
            BOARD_CONFIGS["tl_faq"],
            imported_at=imported_at,
            skip_assets=args.skip_assets,
        )
        write_json(OUTPUT_DIR / "tl-faq-page.json", faq_page)
        manifest["counts"]["tl_faq"] = 1

    if "pages" in only:
        print("[import] static pages", flush=True)
        pages = import_static_pages(
            session,
            imported_at=imported_at,
            skip_assets=args.skip_assets,
        )
        write_json(OUTPUT_DIR / "pages.json", pages)
        manifest["counts"]["pages"] = len(pages)

    write_json(OUTPUT_DIR / "manifest.json", manifest)
    print(f"[done] wrote imported content to {OUTPUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
