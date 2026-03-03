"""
maemul.py - 건설업 매물 자동 수집기 (v2)
seoulmna.co.kr/mna 목록 페이지에서 매물 정보를 수집하여 HTML 링크 목록을 생성합니다.

사용법:
  python maemul.py              # 기본 1페이지 수집
  python maemul.py --pages 3    # 3페이지 수집
"""

import re
import sys
import time
import argparse
import requests
from bs4 import BeautifulSoup

# ======================================================
# [설정]
BASE_URL = "https://seoulmna.co.kr"
LIST_URL = f"{BASE_URL}/mna"
DEFAULT_PAGES = 1           # 기본 수집 페이지 수 (1페이지 = 약 10개)
RETRY_COUNT = 3             # 네트워크 오류 시 재시도 횟수
TIMEOUT = 10                # 요청 타임아웃 (초)
# ======================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def fetch_page(url: str) -> BeautifulSoup | None:
    """URL을 가져와 BeautifulSoup 객체로 반환. 실패시 재시도."""
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            print(f"  [재시도 {attempt}/{RETRY_COUNT}] {url} -> {e}")
            if attempt < RETRY_COUNT:
                time.sleep(1)
    return None


def extract_listing_ids(soup: BeautifulSoup) -> list[int]:
    """목록 페이지에서 매물 ID 목록을 순서대로 추출 (중복 제거)."""
    seen = set()
    ids = []
    for link in soup.find_all("a", href=re.compile(r"/mna/\d+")):
        match = re.search(r"/mna/(\d+)", link.get("href", ""))
        if match:
            uid = int(match.group(1))
            if uid not in seen:
                seen.add(uid)
                ids.append(uid)
    return ids


def extract_listing_summary(soup: BeautifulSoup) -> dict[int, dict]:
    """목록 페이지 메인 테이블에서 매물별 요약 데이터 추출.
    
    메인 테이블(가장 큰 테이블)의 데이터 행에서:
      - 매물번호, 상태
      - 마지막 3셀: 출자금/잔고, 법인형태+양도가, 지역
    """
    summaries = {}

    # 가장 많은 mna 링크를 가진 테이블 = 메인 테이블
    tables = soup.find_all("table")
    main_table = None
    max_links = 0
    for table in tables:
        link_count = len(table.find_all("a", href=re.compile(r"/mna/\d+")))
        if link_count > max_links:
            max_links = link_count
            main_table = table

    if not main_table:
        return summaries

    for row in main_table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 10:
            continue

        # 첫 번째 셀에서 매물번호 찾기
        first_cell = cells[0].get_text(strip=True)
        if not re.match(r"^\d{4,}$", first_cell):
            continue

        uid = int(first_cell)
        cell_texts = [c.get_text(strip=True) for c in cells]

        info = {"id": uid, "상태": cell_texts[1] if len(cell_texts) > 1 else ""}

        # 마지막 3셀: 출자금/잔고, 법인형태+양도가, 지역
        if len(cell_texts) >= 3:
            last3 = cell_texts[-3:]
            for text in last3:
                if "좌" in text:
                    info["출자금"] = text
                elif "회사" in text or "억" in text:
                    info["법인_양도가"] = text
                elif text in ("서울", "지방", "경기", "인천", "세종", "수도권"):
                    info["지역"] = text

        summaries[uid] = info

    return summaries


def extract_detail_title(uid: int) -> str:
    """상세 페이지에서 실제 매물 제목(인라인 스타일 h1)을 추출."""
    detail_url = f"{LIST_URL}/{uid}"
    soup = fetch_page(detail_url)
    if not soup:
        return ""

    # 핵심: 인라인 style이 있는 h1이 진짜 제목
    # (사이트 공통 헤더 h1은 class='sub_title'를 가짐)
    for h1 in soup.find_all("h1"):
        # 사이트 공통 헤더 건너뜀
        parent = h1.parent
        if parent and parent.get("class") and "sub_title" in " ".join(parent.get("class", [])):
            continue
        if h1.get("class") and "sub_title" in " ".join(h1.get("class", [])):
            continue

        text = h1.get_text(strip=True).replace("\n", " ")

        # 사이트 공통 헤더 텍스트 필터링
        if "건설업 양도양수" in text and "실시간 매물" in text:
            continue
        if len(text) < 10:
            continue

        return text

    # fallback: 페이지 title에서 상태 추출
    if soup.title:
        title_text = soup.title.get_text(strip=True)
        parts = title_text.split(">")
        if len(parts) >= 2:
            status = parts[0].strip()
            return f"매물 {uid} ({status})"

    return ""


def build_display_text(uid: int, title: str, summary: dict) -> str:
    """매물 정보를 표시 텍스트로 변환."""
    if title:
        # 제목이 너무 길면 요약
        if len(title) > 70:
            title = title[:67] + "..."
        return f"[{title}]"

    # 제목이 없으면 테이블 요약 데이터로 구성
    parts = [f"매물 {uid}"]
    법인가 = summary.get("법인_양도가", "")
    지역 = summary.get("지역", "")

    if 법인가:
        parts.append(법인가)
    if 지역:
        parts.append(지역)

    return f"[{' | '.join(parts)}]"


def generate_html(items: list[dict]) -> list[str]:
    """매물 목록을 HTML <li> 태그로 변환."""
    html_lines = []
    for item in items:
        url = f"{LIST_URL}/{item['id']}"
        html_line = (
            f'<li style="margin-bottom: 10px; border-bottom: 1px dashed #eee; padding-bottom: 10px;">'
            f'<span style="color: #2980b9; margin-right: 5px;">●</span>'
            f'<a href="{url}" target="_blank" '
            f'style="text-decoration: none; color: #333; font-size: 17px; font-weight: bold;">'
            f'{item["display"]}'
            f'</a></li>'
        )
        html_lines.append(html_line)
    return html_lines


def run():
    parser = argparse.ArgumentParser(description="건설업 매물 자동 수집기")
    parser.add_argument("--pages", type=int, default=DEFAULT_PAGES,
                        help=f"수집할 페이지 수 (기본값: {DEFAULT_PAGES})")
    args = parser.parse_args()

    print("=" * 55)
    print("  건설업 매물 자동 수집기 v2  (seoulmna.co.kr)")
    print("=" * 55)

    # 1단계: 목록 페이지에서 매물 ID 및 요약 수집
    all_ids = []
    all_summaries = {}

    for page_num in range(1, args.pages + 1):
        page_url = f"{LIST_URL}?page={page_num}" if page_num > 1 else LIST_URL
        print(f"\n[페이지 {page_num}] 수집 -> {page_url}")

        soup = fetch_page(page_url)
        if not soup:
            print(f"  [X] 로드 실패")
            continue

        ids = extract_listing_ids(soup)
        summaries = extract_listing_summary(soup)
        print(f"  [O] {len(ids)}개 매물 발견")

        all_ids.extend(uid for uid in ids if uid not in all_summaries)
        all_summaries.update(summaries)

        if page_num < args.pages:
            time.sleep(0.5)

    if not all_ids:
        print("\n수집된 매물이 없습니다.")
        return

    # 2단계: 상세 페이지에서 실제 제목 추출
    print(f"\n[상세 제목 수집] {len(all_ids)}개 매물...")
    results = []

    for i, uid in enumerate(all_ids, 1):
        title = extract_detail_title(uid)
        summary = all_summaries.get(uid, {})
        display = build_display_text(uid, title, summary)

        results.append({"id": uid, "title": title, "display": display})

        status = title[:45] + "..." if title and len(title) > 45 else title or "(테이블 데이터)"
        print(f"  ({i}/{len(all_ids)}) #{uid} -> {status}")
        time.sleep(0.3)

    # 3단계: HTML 출력
    html_lines = generate_html(results)

    print("\n" + "=" * 55)
    print(" [아래 코드를 복사하세요]")
    print("=" * 55 + "\n")

    for line in html_lines:
        print(line)

    print("\n" + "=" * 55)
    print(f"  총 {len(html_lines)}개의 링크 생성 완료!")
    print("=" * 55)


if __name__ == "__main__":
    run()