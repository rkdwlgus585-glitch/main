import argparse
import json
import re
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_EXCLUDES = [
    r"/adm/",
    r"/bbs/login\.php",
    r"/bbs/register\.php",
    r"/bbs/logout\.php",
    r"/bbs/password_lost\.php",
    r"/bbs/write\.php",
    r"/bbs/link\.php",
    r"/bbs/rss\.php",
    r"/bbs/sns_send\.php",
    r"/bbs/view_image\.php",
    r"/mna/write(?:/)?$",
    r"/shop/(?:cart|order|wishlist|personalpay|mypage)",
    r"/bbs/(?:memo|formmail|new\.php\?mb_id=)",
]

USER_AGENT = (
    "Mozilla/5.0 (compatible; SeoulMNA-Internal-Sitemap/1.0; +https://seoulmna.co.kr/)"
)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonicalize(url: str, expected_host: str) -> str:
    try:
        parsed = urlsplit((url or "").strip())
    except Exception:
        return ""
    if not parsed.scheme and not parsed.netloc:
        return ""

    host = (parsed.netloc or "").lower().strip()
    if host != expected_host:
        return ""

    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if not path.startswith("/"):
        path = "/" + path
    if path == "/index.php":
        path = "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    keep_params: List[Tuple[str, str]] = []
    query_pairs = parse_qsl(parsed.query or "", keep_blank_values=False)
    query_map = {k: v for k, v in query_pairs}

    if path == "/bbs/board.php":
        bo = query_map.get("bo_table", "").strip()
        wr = query_map.get("wr_id", "").strip()
        if bo and wr:
            keep_params = [("bo_table", bo), ("wr_id", wr)]
        elif bo:
            keep_params = [("bo_table", bo)]
    elif path == "/bbs/content.php":
        co_id = query_map.get("co_id", "").strip()
        if co_id:
            keep_params = [("co_id", co_id)]

    query = urlencode(keep_params, doseq=True)
    return urlunsplit(("https", expected_host, path, query, ""))


def _is_html_response(resp: requests.Response) -> bool:
    ctype = str(resp.headers.get("content-type", "")).lower()
    return ("text/html" in ctype) or ("application/xhtml+xml" in ctype) or ("charset" in ctype and "<html" in resp.text[:400].lower())


def _is_transfer_limit_page(text: str) -> bool:
    src = str(text or "")
    lower = src.lower()
    if "일일 데이터 전송량 초과안내" in src:
        return True
    if ("데이터 전송량" in src) and ("차단" in src):
        return True
    if "tle_info6.gif" in lower:
        return True
    return False


def _should_exclude(url: str, exclude_regexes: Iterable[re.Pattern[str]]) -> bool:
    target = (url or "").strip().lower()
    if not target:
        return True
    if any(target.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf", ".zip", ".js", ".css")):
        return True
    for rex in exclude_regexes:
        if rex.search(target):
            return True
    return False


def _fetch(session: requests.Session, url: str, timeout: int) -> requests.Response | None:
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        if resp.status_code >= 400:
            return None
        return resp
    except Exception:
        return None


def _collect_links_from_html(base_url: str, html: str) -> List[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    out: List[str] = []
    for a in soup.select("a[href]"):
        href = str(a.get("href", "")).strip()
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        out.append(urljoin(base_url, href))
    return out


def _parse_live_sitemap(session: requests.Session, base_url: str, timeout: int) -> List[str]:
    def parse_urls(text: str) -> List[str]:
        if "<urlset" not in text:
            return []
        try:
            root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
        except Exception:
            try:
                root = ET.fromstring(text)
            except Exception:
                return []
        urls: List[str] = []
        for loc in root.findall(".//{*}loc"):
            val = (loc.text or "").strip()
            if val:
                urls.append(val)
        return urls

    resp = _fetch(session, f"{base_url}/sitemap.xml", timeout=timeout)
    if not resp:
        return []
    text = resp.text or ""
    if _is_transfer_limit_page(text):
        return []
    return parse_urls(text)


def _parse_live_sitemap_from_file(path: Path) -> List[str]:
    if not path.exists():
        return []
    text = ""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except Exception:
            try:
                text = path.read_text(encoding="cp949")
            except Exception:
                text = path.read_text(encoding="utf-8", errors="replace")
    if "<urlset" not in text:
        return []
    try:
        root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    except Exception:
        try:
            root = ET.fromstring(text)
        except Exception:
            return []
    urls: List[str] = []
    for loc in root.findall(".//{*}loc"):
        val = (loc.text or "").strip()
        if val:
            urls.append(val)
    return urls


def _collect_board_posts_from_cached_html(
    cache_path: Path,
    host: str,
    board_slug: str,
    exclude_regexes: Iterable[re.Pattern[str]],
) -> Set[str]:
    if not cache_path.exists():
        return set()
    text = cache_path.read_text(encoding="utf-8", errors="replace")
    href_re = re.compile(rf"https?://{re.escape(host)}/{re.escape(board_slug)}/\d+", re.I)
    found: Set[str] = set()
    for m in href_re.finditer(text):
        c = _canonicalize(m.group(0), host)
        if c and not _should_exclude(c, exclude_regexes):
            found.add(c)
    return found


def _crawl_static(
    session: requests.Session,
    base_url: str,
    host: str,
    exclude_regexes: Iterable[re.Pattern[str]],
    timeout: int,
    max_pages: int,
) -> Set[str]:
    seeds = [
        f"{base_url}/",
        f"{base_url}/mna",
        f"{base_url}/notice",
        f"{base_url}/bbs/content.php?co_id=ai_calc",
        f"{base_url}/bbs/content.php?co_id=ai_acq",
    ]
    queue = deque((seed, 0) for seed in seeds)
    visited: Set[str] = set()
    found: Set[str] = set()

    while queue and len(visited) < max_pages:
        current, depth = queue.popleft()
        canonical_current = _canonicalize(current, host)
        if not canonical_current or canonical_current in visited:
            continue
        visited.add(canonical_current)

        if not _should_exclude(canonical_current, exclude_regexes):
            found.add(canonical_current)

        resp = _fetch(session, current, timeout=timeout)
        if not resp or not _is_html_response(resp):
            continue

        links = _collect_links_from_html(resp.url, resp.text)
        for raw in links:
            c = _canonicalize(raw, host)
            if not c or c in visited:
                continue
            if _should_exclude(c, exclude_regexes):
                continue
            found.add(c)
            if depth < 1:
                queue.append((c, depth + 1))

    return found


def _crawl_board_posts(
    session: requests.Session,
    base_url: str,
    host: str,
    board_slug: str,
    exclude_regexes: Iterable[re.Pattern[str]],
    timeout: int,
    max_pages: int,
) -> Set[str]:
    board_slug = str(board_slug or "").strip()
    if not board_slug:
        return set()

    found: Set[str] = set()
    board_rewrite = _canonicalize(f"{base_url}/{board_slug}", host)
    board_legacy = _canonicalize(f"{base_url}/bbs/board.php?bo_table={board_slug}", host)
    if board_rewrite and not _should_exclude(board_rewrite, exclude_regexes):
        found.add(board_rewrite)
    if board_legacy and not _should_exclude(board_legacy, exclude_regexes):
        found.add(board_legacy)

    post_re = re.compile(rf"/{re.escape(board_slug)}/(\d+)$")
    wr_link_re = re.compile(rf"/bbs/board\.php\?bo_table={re.escape(board_slug)}&wr_id=\d+", re.I)

    def page_number_from_link(raw_url: str) -> int | None:
        try:
            parsed = urlsplit((raw_url or "").strip())
        except Exception:
            return None
        if (parsed.netloc or "").lower().strip() != host:
            return None
        path = re.sub(r"/{2,}", "/", parsed.path or "/")
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        qs = {k: v for k, v in parse_qsl(parsed.query or "", keep_blank_values=False)}
        if path == f"/{board_slug}":
            page_raw = str(qs.get("page", "1") or "1").strip()
            if not page_raw.isdigit():
                return 1
            return max(1, int(page_raw))
        if path == "/bbs/board.php" and str(qs.get("bo_table", "")).strip() == board_slug:
            page_raw = str(qs.get("page", "1") or "1").strip()
            if not page_raw.isdigit():
                return 1
            return max(1, int(page_raw))
        return None

    pending_pages = deque([1])
    seen_pages: Set[int] = set()

    while pending_pages and len(seen_pages) < max_pages:
        page = pending_pages.popleft()
        if page in seen_pages:
            continue
        seen_pages.add(page)

        list_url = f"{base_url}/{board_slug}" if page == 1 else f"{base_url}/{board_slug}?page={page}"
        resp = _fetch(session, list_url, timeout=timeout)
        if not resp or not _is_html_response(resp):
            continue

        links = _collect_links_from_html(resp.url, resp.text)
        for raw in links:
            page_num = page_number_from_link(raw)
            if page_num is not None and page_num <= max_pages and page_num not in seen_pages:
                pending_pages.append(page_num)
            if not (post_re.search(urlsplit(raw).path) or wr_link_re.search(raw)):
                continue
            c = _canonicalize(raw, host)
            if not c or _should_exclude(c, exclude_regexes):
                continue
            found.add(c)

    return found


def _build_xml(urls: Iterable[str], lastmod_iso: str) -> str:
    entries = sorted({str(u).strip() for u in urls if str(u).strip()})
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{u}</loc>")
        lines.append(f"    <lastmod>{lastmod_iso}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def _save_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an internal sitemap.xml without external sitemap generator dependencies."
    )
    parser.add_argument("--base-url", default="https://seoulmna.co.kr")
    parser.add_argument("--boards", default="mna,notice", help="Comma-separated board slugs to crawl")
    parser.add_argument("--max-board-pages", type=int, default=120)
    parser.add_argument("--max-static-pages", type=int, default=120)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--out", default="output/sitemap.xml")
    parser.add_argument("--report", default="logs/internal_sitemap_report_latest.json")
    parser.add_argument("--no-live-merge", action="store_true", help="Do not merge URLs from current live sitemap.xml")
    parser.add_argument(
        "--live-sitemap-cache",
        default="tmp/seoulmna_sitemap.xml",
        help="Fallback local sitemap.xml file when live site is blocked/unreachable.",
    )
    parser.add_argument(
        "--board-cache-html",
        default="tmp/seoulmna_mna.html,tmp/seoulmna_notice.html",
        help="Comma-separated cached board HTML files to recover post URLs when live crawling is blocked.",
    )
    args = parser.parse_args()

    base_url = str(args.base_url or "").strip().rstrip("/")
    if not base_url.startswith("http"):
        raise SystemExit("--base-url must include protocol, e.g. https://seoulmna.co.kr")
    host = urlsplit(base_url).netloc.lower().strip()
    if not host:
        raise SystemExit("invalid --base-url")

    exclude_regexes = [re.compile(p, re.I) for p in DEFAULT_EXCLUDES]
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    sources: Dict[str, str] = {}
    excluded_samples: List[str] = []

    if not bool(args.no_live_merge):
        live_urls = _parse_live_sitemap(session, base_url=base_url, timeout=int(args.timeout))
        if not live_urls:
            cache_path = (ROOT / str(args.live_sitemap_cache)).resolve()
            live_urls = _parse_live_sitemap_from_file(cache_path)
        for raw in live_urls:
            c = _canonicalize(raw, host)
            if not c:
                continue
            if _should_exclude(c, exclude_regexes):
                if len(excluded_samples) < 30:
                    excluded_samples.append(c)
                continue
            sources[c] = "live_sitemap"

    for c in _crawl_static(
        session=session,
        base_url=base_url,
        host=host,
        exclude_regexes=exclude_regexes,
        timeout=int(args.timeout),
        max_pages=max(20, int(args.max_static_pages)),
    ):
        sources[c] = sources.get(c) or "static_crawl"

    board_slugs = [x.strip() for x in str(args.boards or "").split(",") if x.strip()]
    for slug in board_slugs:
        for c in _crawl_board_posts(
            session=session,
            base_url=base_url,
            host=host,
            board_slug=slug,
            exclude_regexes=exclude_regexes,
            timeout=int(args.timeout),
            max_pages=max(5, int(args.max_board_pages)),
        ):
            sources[c] = sources.get(c) or f"board:{slug}"
        cache_files = [x.strip() for x in str(args.board_cache_html or "").split(",") if x.strip()]
        for rel in cache_files:
            for c in _collect_board_posts_from_cached_html(
                cache_path=(ROOT / rel).resolve(),
                host=host,
                board_slug=slug,
                exclude_regexes=exclude_regexes,
            ):
                sources[c] = sources.get(c) or f"cache_board:{slug}"

    lastmod_iso = _now_utc_iso()
    xml_text = _build_xml(sources.keys(), lastmod_iso=lastmod_iso)

    out_path = (ROOT / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(xml_text, encoding="utf-8")

    source_counter = Counter(sources.values())
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "base_url": base_url,
        "host": host,
        "output_file": str(out_path),
        "total_urls": len(sources),
        "source_counts": dict(source_counter),
        "excluded_sample_count": len(excluded_samples),
        "excluded_samples": excluded_samples,
        "boards": board_slugs,
        "max_board_pages": int(args.max_board_pages),
        "max_static_pages": int(args.max_static_pages),
        "note": "Deploy this file to webroot /sitemap.xml via hosting file manager/SFTP to replace external-generator output.",
    }
    report_path = (ROOT / args.report).resolve()
    _save_json(report_path, report)

    print(f"[sitemap] {out_path}")
    print(f"[report] {report_path}")
    print(f"[urls] {len(sources)}")
    if excluded_samples:
        print("[excluded_sample]")
        for u in excluded_samples[:10]:
            print(f"- {u}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
