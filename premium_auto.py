# =================================================================
# Premium 매물 글 자동 생성기
# seoulmna.co.kr/premium 자동화
# =================================================================

from google import genai
from google.genai import types
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoAlertPresentException,
    NoSuchElementException,
    NoSuchWindowException,
    TimeoutException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import time
import os
import re
import json
import sys
import argparse
from datetime import datetime, timezone
from html import escape as html_escape
from urllib.parse import urljoin
from utils import load_config, require_config

# =================================================================
# [설정]
# =================================================================
CONFIG = load_config({
    "SITE_URL": "https://seoulmna.co.kr",
    "BRAND_NAME": "서울건설정보",
    "CONSULTANT": "강지현 행정사",
    "PHONE": "010-9926-8661",
    "MNA_SCAN_WINDOW": "220",
    "MNA_PAGE_SCAN_MAX": "120",
    "MNA_PAGE_SIZE_ESTIMATE": "8",
})

# 윈도우 콘솔 인코딩
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


def ensure_config(required_keys, context="premium_auto"):
    return require_config(CONFIG, required_keys, context=context)


def _safe_error_text(err):
    msg = str(err or "").strip()
    if msg and msg.lower() != "none":
        return msg
    if err is None:
        return "unknown error"
    return err.__class__.__name__


def _safe_html(value):
    return html_escape(str(value or ""), quote=True)


def _phone_href(value):
    raw = re.sub(r"[^0-9+]", "", str(value or ""))
    return raw or ""


# =================================================================
# [크롤러] 매물 정보 수집
# =================================================================
class PremiumCrawler:
    def __init__(self, driver):
        self.driver = driver
        self.base_url = CONFIG["SITE_URL"]
        self.last_error_kind = ""

    @staticmethod
    def _int_config(name, default_value):
        raw = str(CONFIG.get(name, default_value) or "").strip()
        try:
            return int(raw)
        except (ValueError, TypeError):
            return int(default_value)

    @staticmethod
    def _extract_number_from_text(text):
        clean = " ".join(str(text or "").split())
        if not clean:
            return None
        patterns = [
            r"매물\s*(\d{4,5})",
            r"제\s*(\d{4,5})\s*호",
            r"(\d{4,5})\s*호",
        ]
        for pattern in patterns:
            m = re.search(pattern, clean, flags=re.IGNORECASE)
            if not m:
                continue
            num = int(m.group(1))
            if 7000 <= num <= 9999:
                return num
        for raw in re.findall(r"(?<!\d)(\d{4,5})(?!\d)", clean):
            num = int(raw)
            if 7000 <= num <= 9999:
                return num
        return None

    def _request_page_text(self, path, timeout=8):
        url = path if str(path).startswith("http") else f"{self.base_url}{path}"
        res = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code != 200:
            raise RuntimeError(f"request failed: {url} status={res.status_code}")
        return res.text

    def fetch_premium_posts_from_titles(self, limit=30):
        rows = []
        seen_urls = set()
        try:
            html = self._request_page_text("/premium", timeout=10)
        except Exception as e:
            print(f"⚠️ premium 목록 요청 실패: {_safe_error_text(e)}")
            return rows

        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a[href*='/premium/']"):
            href = str(a.get("href") or "").strip()
            if not href:
                continue
            abs_url = urljoin(self.base_url, href)
            if not re.search(r"/premium/\d+\b", abs_url):
                continue
            if abs_url in seen_urls:
                continue
            seen_urls.add(abs_url)
            title = " ".join(a.get_text(" ", strip=True).split())
            if not title:
                continue
            number = self._extract_number_from_text(title)
            rows.append({"number": number, "title": title, "url": abs_url})
            if len(rows) >= max(1, int(limit)):
                break
        return rows

    def get_latest_premium_post_info(self):
        rows = self.fetch_premium_posts_from_titles(limit=20)
        if not rows:
            return {"number": None, "title": "", "url": ""}
        for row in rows:
            if row.get("number"):
                return row
        return rows[0]

    def is_number_in_latest_premium(self, number, limit=20):
        target = int(number or 0)
        rows = self.fetch_premium_posts_from_titles(limit=limit)
        for row in rows:
            if int(row.get("number") or 0) == target:
                return True, row, rows
        return False, (rows[0] if rows else {}), rows

    def _estimate_required_pages(self, start_from, latest_mna):
        hard_limit = max(10, self._int_config("MNA_PAGE_SCAN_MAX", 120))
        page_size_est = max(1, self._int_config("MNA_PAGE_SIZE_ESTIMATE", 8))
        if not latest_mna or latest_mna <= 0:
            return min(20, hard_limit)
        span = max(0, int(latest_mna) - int(start_from))
        pages = (span // page_size_est) + 6
        return max(10, min(hard_limit, pages))

    def _get_latest_mna_number_via_requests(self):
        try:
            url = f"{self.base_url}/mna?page=1"
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return 0
            nums = [int(x) for x in re.findall(r"/mna/(\d+)", resp.text)]
            nums = [n for n in nums if 7000 <= n <= 9999]
            return max(nums) if nums else 0
        except (requests.RequestException, ValueError):
            return 0

    def get_existing_premium_numbers(self):
        existing_numbers = set()

        rows = self.fetch_premium_posts_from_titles(limit=60)
        for row in rows:
            num = int(row.get("number") or 0)
            if 7000 <= num <= 9999:
                existing_numbers.add(num)

        if not existing_numbers and self.driver is not None:
            try:
                self.driver.get(f"{self.base_url}/premium")
                time.sleep(2)
                page_text = self.driver.page_source
                patterns = [
                    r"\ub9e4\ubb3c\s*(\d{4,5})",
                    r"\uc81c\s*(\d{4,5})\s*\ud638",
                    r"(\d{4,5})\s*\ud638",
                ]
                for pattern in patterns:
                    for raw in re.findall(pattern, page_text):
                        num = int(raw)
                        if 7000 <= num <= 9999:
                            existing_numbers.add(num)
            except (WebDriverException, ValueError) as e:
                print(f"⚠️ premium 번호 fallback 수집 오류: {_safe_error_text(e)}")

        print(f"✅ premium에 이미 작성된 번호: {sorted(existing_numbers)}")
        return existing_numbers

    def get_all_mna_numbers(self, start_from=7611, scan_window=220):
        mna_numbers = set()

        start_from = int(start_from or 7611)
        scan_window = max(20, int(scan_window or 220))
        latest_mna = self._get_latest_mna_number_via_requests()
        required_pages = self._estimate_required_pages(start_from=start_from, latest_mna=latest_mna)

        print(f"🔎 mna 스캔 페이지 수: {required_pages} (latest={latest_mna}, start={start_from})")

        for page in range(1, required_pages + 1):
            url = f"{self.base_url}/mna?page={page}"
            try:
                resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    print(f"Warning: mna list request failed (page={page}, status={resp.status_code})")
                    break
                page_matches = re.findall(rf"/mna/(\d+)\?page={page}\\b", resp.text)
                matches = page_matches or re.findall(r"/mna/(\d+)", resp.text)
                for m in matches:
                    num = int(m)
                    if 7000 <= num <= 9999:
                        mna_numbers.add(num)

                if not matches:
                    break
            except (requests.RequestException, ValueError) as e:
                print(f"Warning: mna page scan failed (page={page}): {_safe_error_text(e)}")
                break

        print(f"✅ mna 전체 매물 번호 수: {len(mna_numbers)}")
        return mna_numbers

    def get_next_target_number(self, start_from=7611):
        scan_window = max(20, self._int_config("MNA_SCAN_WINDOW", 220))

        existing = self.get_existing_premium_numbers()
        latest_info = self.get_latest_premium_post_info()
        latest_title_num = int(latest_info.get("number") or 0)
        latest_title = str(latest_info.get("title") or "").strip()

        last_published = max(
            int(start_from) - 1,
            max(existing) if existing else 0,
            latest_title_num,
        )
        preferred_start = max(int(start_from), last_published + 1)

        if latest_title:
            print(f"📚 premium 최신 제목 기준: {latest_title}")
        print(f"📌 premium 마지막 작성 번호: {last_published} -> 다음 시작: {preferred_start}")

        mna_numbers = self.get_all_mna_numbers(start_from=preferred_start, scan_window=scan_window)

        print(f"🔍 {preferred_start}번부터 순차 확인 중...")
        missing_numbers = []
        for num in range(preferred_start, preferred_start + scan_window):
            if num in existing:
                continue
            if num not in mna_numbers:
                if len(missing_numbers) < 12:
                    missing_numbers.append(num)
                continue
            if missing_numbers:
                joined = ", ".join(str(x) for x in missing_numbers)
                print(f"ℹ️ 결번/미등록으로 건너뛴 번호: {joined}")
            print(f"🎯 다음 작성할 번호: {num}")
            return num

        fallback_start = int(start_from)
        if fallback_start < preferred_start:
            print(f"↩️ fallback 스캔: {fallback_start}번부터 재확인")
            for num in range(fallback_start, fallback_start + scan_window):
                if num in existing:
                    continue
                if num not in mna_numbers:
                    continue
                print(f"🎯 fallback 선택 번호: {num}")
                return num

        print("⚠️ 작성할 번호를 찾을 수 없습니다.")
        return None

    def get_latest_mna_number(self):
        latest = self._get_latest_mna_number_via_requests()
        if latest:
            print(f"✅ 최신 mna 번호: {latest}")
            return latest

        if self.driver is None:
            return None

        try:
            self.driver.get(f"{self.base_url}/mna")
            time.sleep(2)

            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/mna/']")
            numbers = []
            for link in links:
                href = link.get_attribute("href")
                match = re.search(r'/mna/(\d+)', href)
                if match:
                    numbers.append(int(match.group(1)))

            if numbers:
                latest = max(numbers)
                print(f"✅ 최신 mna 번호: {latest}")
                return latest
        except (WebDriverException, ValueError) as e:
            print(f"⚠️ mna 번호 검색 오류: {_safe_error_text(e)}")

        return None
    def fetch_mna_data(self, mna_number):
        """매물 상세 정보 수집"""
        url = f"{self.base_url}/mna/{mna_number}"
        print(f"📄 매물 정보 수집: {url}")
        
        self.driver.get(url)
        time.sleep(2)
        
        # 페이지 소스 파싱
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        data = {
            "번호": mna_number,
            "url": url,
            "제목": "",
            "업종": "",
            "설립년도": "",
            "자본금": "",
            "소재지": "",
            "양도가": "",
            "공제조합잔액": "",
            "시평": "",
            "매출실적": {},
            "비고": [],
            "특이사항": []
        }
        
        # 제목 추출
        title_el = soup.select_one("h1, .subject, .title")
        if title_el:
            data["제목"] = title_el.get_text(strip=True)
        
        # 테이블 데이터 추출
        tables = soup.select("table")
        for table in tables:
            rows = table.select("tr")
            for row in rows:
                cells = row.select("th, td")
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    val = cells[1].get_text(strip=True)
                    
                    if "업종" in key:
                        data["업종"] = val
                    elif "설립" in key or "법인" in key:
                        data["설립년도"] = val
                    elif "자본금" in key:
                        data["자본금"] = val
                    elif "소재지" in key or "지역" in key:
                        data["소재지"] = val
                    elif "양도가" in key or "가격" in key:
                        data["양도가"] = val
                    elif "공제" in key or "잔액" in key:
                        data["공제조합잔액"] = val
                    elif "시평" in key or "시공능력" in key:
                        data["시평"] = val
        
        # 본문 텍스트에서 추가 정보 추출
        content = soup.get_text()
        
        # 결손금 추출
        match = re.search(r'결손금[:\s]*([0-9,.]+)\s*억?', content)
        if match:
            data["결손금"] = match.group(1)
        
        # 부채비율/유동비율 추출
        match = re.search(r'부채[비율:\s]*([0-9,.]+)\s*%?', content)
        if match:
            data["부채비율"] = match.group(1)
        
        match = re.search(r'유동[비율:\s]*([0-9,.]+)\s*%?', content)
        if match:
            data["유동비율"] = match.group(1)
        
        # 행정처분 정보
        if "행정처분" in content:
            if "없음" in content or "無" in content:
                data["행정처분"] = "없음"
            else:
                data["행정처분"] = "있음"
        
        print(f"✅ 매물 정보 수집 완료: {data.get('업종', 'N/A')}")
        return data


# =================================================================
# [AI 글 생성기]
# =================================================================
class ContentGenerator:
    def __init__(self):
        self.client = genai.Client(api_key=CONFIG["GEMINI_API_KEY"])
    
    def generate_article(self, data):
        """SEO 최적화 글 생성"""
        
        prompt = f"""당신은 건설업 양도양수 전문 컨설턴트입니다.
아래 매물 정보를 바탕으로 SEO 최적화된 프리미엄 매물 소개글을 작성하세요.

[매물 정보]
- 매물번호: {data.get('번호')}
- 업종: {data.get('업종', 'N/A')}
- 설립년도: {data.get('설립년도', 'N/A')}
- 자본금: {data.get('자본금', 'N/A')}
- 소재지: {data.get('소재지', 'N/A')}
- 양도가: {data.get('양도가', 'N/A')}
- 공제조합잔액: {data.get('공제조합잔액', 'N/A')}
- 시평: {data.get('시평', 'N/A')}
- 결손금: {data.get('결손금', 'N/A')}
- 부채비율: {data.get('부채비율', 'N/A')}%
- 유동비율: {data.get('유동비율', 'N/A')}%
- 행정처분: {data.get('행정처분', 'N/A')}

[작성 규칙]
1. 제목: "{data.get('업종', '건설업')} 양도 (매물 {data.get('번호')}) | 핵심특징1, 핵심특징2, 핵심특징3" 형식
2. 핵심 장점 3-4가지를 요약 박스로 작성
3. 전문가 분석 의견 3개 섹션 작성
4. 연도별 실적 표 (있는 경우)
5. FAQ 2-3개
6. CTA (상담 연결)

[출력 형식]
JSON으로 출력:
{{
    "title": "SEO 최적화된 제목",
    "summary_points": ["핵심포인트1", "핵심포인트2", "핵심포인트3", "핵심포인트4"],
    "analysis": [
        {{"title": "분석제목1", "content": "분석내용1"}},
        {{"title": "분석제목2", "content": "분석내용2"}},
        {{"title": "분석제목3", "content": "분석내용3"}}
    ],
    "faq": [
        {{"q": "질문1", "a": "답변1"}},
        {{"q": "질문2", "a": "답변2"}}
    ]
}}"""
        
        # 모델 우선순위: Gemini 3 → Gemini 2.5
        models_to_try = ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-2.0-flash']
        
        for model_name in models_to_try:
            print(f"✍️ AI 글 생성 중... (모델: {model_name})")
            
            for attempt in range(3):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    
                    raw = response.text.strip()
                    if raw.startswith("```"):
                        raw = re.sub(r'^```\w*\n?', '', raw)
                        raw = re.sub(r'\n?```$', '', raw)
                    
                    content = json.loads(raw)
                    
                    # list로 반환된 경우 첫 번째 항목 사용
                    if isinstance(content, list):
                        content = content[0] if content else {}
                    print(f"✅ AI 글 생성 완료 (모델: {model_name})")
                    return content
                    
                except Exception as e:
                    error_msg = str(e)
                    
                    # 429 오류: 다음 모델 시도
                    if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                        print(f"⚠️ {model_name} 한도 초과, 다음 모델 시도...")
                        break  # 다음 모델로
                    # 404 오류: 다음 모델 시도
                    elif "404" in error_msg or "NOT_FOUND" in error_msg:
                        print(f"⚠️ {model_name} 사용 불가, 다음 모델 시도...")
                        break  # 다음 모델로
                    else:
                        print(f"❌ AI 생성 오류: {e}")
                        if attempt < 2:
                            time.sleep(3)
                            continue
                        return None
        
        print("❌ AI 글 생성 실패 (모든 모델 시도 완료)")
        return None
    
    def render_html(self, data, ai_content):
        """Render sanitized HTML for the premium post."""
        number_raw = str(data.get("\ubc88\ud638", "N/A")).strip()
        number = _safe_html(number_raw)
        number_slug = re.sub(r"[^0-9]", "", number_raw) or number
        industry = _safe_html(data.get("\uc5c5\uc885", "Construction"))

        points = ai_content.get("summary_points", []) if isinstance(ai_content, dict) else []
        summary_html = ""
        for i, point in enumerate(points):
            color = "#003764" if i == len(points) - 1 else "#AC9479"
            safe_point = _safe_html(point)
            summary_html += f'''
            <tr>
                <td width="30" valign="top" style="padding-bottom: 20px;"><span style="color: {color}; font-size: 22px; font-weight: bold;">?</span></td>
                <td style="padding-bottom: 20px; font-size: 24px; color: #333; font-weight: 700;">{safe_point}</td>
            </tr>'''

        analysis_html = ""
        analysis_items = ai_content.get("analysis", []) if isinstance(ai_content, dict) else []
        for item in analysis_items:
            safe_title = _safe_html(item.get('title', ''))
            safe_content = _safe_html(item.get('content', '')).replace('\n', '<br/>')
            analysis_html += f'''
        <div style="background-color: #FFFFFF; padding: 40px; border: 1px solid #E5E8EB; margin-bottom: 30px;">
            <h3 style="font-size: 26px; color: #003764; margin: 0 0 15px 0; font-weight: 700;">? {safe_title}</h3>
            <p style="font-size: 24px; color: #4E5968; margin: 0; font-weight: 300;">{safe_content}</p>
        </div>'''

        faq_html = ""
        faq_items = ai_content.get("faq", []) if isinstance(ai_content, dict) else []
        for faq in faq_items:
            safe_q = _safe_html(faq.get('q', ''))
            safe_a = _safe_html(faq.get('a', '')).replace('\n', '<br/>')
            faq_html += f'''
        <div style="background-color: #FFFFFF; border: 1px solid #E5E8EB; padding: 40px; margin-bottom: 25px;">
            <p style="font-size: 26px; font-weight: 700; color: #003764; margin-bottom: 15px;">Q: {safe_q}</p>
            <p style="font-size: 24px; color: #4E5968; line-height: 1.7; margin: 0; font-weight: 300;">A: {safe_a}</p>
        </div>'''

        raw_title = (
            str(ai_content.get("title", f"{data.get("\uc5c5\uc885", "Construction")} transfer (listing {number_raw})"))
            if isinstance(ai_content, dict)
            else f"{data.get("\uc5c5\uc885", "Construction")} transfer (listing {number_raw})"
        )
        safe_title = _safe_html(raw_title)
        safe_brand = _safe_html(CONFIG.get('BRAND_NAME', ''))
        safe_consultant = _safe_html(CONFIG.get('CONSULTANT', ''))
        safe_phone = _safe_html(CONFIG.get('PHONE', ''))
        phone_href = _phone_href(CONFIG.get('PHONE', ''))
        site_url = _safe_html(CONFIG.get('SITE_URL', ''))

        html = f'''<div style="width: 100%; max-width: 800px; margin: 0 auto; background-color: rgb(246, 246, 243); line-height: 1.8;">

    <div style="color: rgb(25, 31, 40); font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', dotum, sans-serif; letter-spacing: 0.02em; border-top: 3px solid rgb(0, 55, 100); border-bottom: 1px solid rgb(0, 55, 100); background-color: rgb(255, 255, 255); padding: 40px 30px;">
        <h3 style="margin: 0 0 25px 0; font-size: 26px; font-weight: 800; color: #003764; letter-spacing: -0.05em;">
            Premium listing summary: No. {number}
        </h3>
        <table width="100%" border="0" cellspacing="0" cellpadding="0">
            <tbody>{summary_html}</tbody>
        </table>
    </div>

    <div style="background-color: rgb(255, 255, 255); padding: 60px 30px; border-bottom: 1px solid rgb(229, 232, 235);">
        <span style="color: rgb(140, 123, 108); font-family: Malgun Gothic, sans-serif; letter-spacing: 0.1em; font-size: 20px; font-weight: bold; display: block; margin-bottom: 15px;">{industry} transfer report</span>
        <h1 style="color: rgb(0, 55, 100); font-family: Malgun Gothic, sans-serif; letter-spacing: 0.02em; font-size: 42px; font-weight: 800; margin: 0; line-height: 1.4; word-break: keep-all;">
            {safe_title}
        </h1>
    </div>

    <div style="color: rgb(25, 31, 40); font-family: Malgun Gothic, sans-serif; letter-spacing: 0.02em; padding: 60px 30px;">
        <h2 style="font-size: 34px; font-weight: 800; color: #003764; margin-bottom: 40px; border-bottom: 2px solid #003764; padding-bottom: 15px;">Expert analysis</h2>
        {analysis_html}
    </div>

    <div style="color: rgb(25, 31, 40); font-family: Malgun Gothic, sans-serif; letter-spacing: 0.02em; padding: 0 30px 60px;">
        <h2 style="font-size: 34px; font-weight: 800; color: #003764; margin-bottom: 35px; border-bottom: 2px solid #003764; padding-bottom: 15px;">FAQ</h2>
        {faq_html}
    </div>

    <div style="color: rgb(25, 31, 40); font-family: Malgun Gothic, sans-serif; letter-spacing: 0.02em; background-color: rgb(255, 255, 255); padding: 80px 30px; text-align: center; border-top: 1px solid rgb(229, 232, 235);">
        <p style="margin: 0; font-size: 22px; color: #8C7B6C; font-weight: 600; letter-spacing: 0.15em; margin-bottom: 20px;">Construction transfer advisory group</p>
        <p style="margin: 0 0 50px 0; font-size: 40px; color: #003764; font-weight: 800;">{safe_brand} {safe_consultant}</p>

        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 25px;">
            <tbody><tr>
                <td align="center" style="background-color: #003764; padding: 30px;">
                    <a href="tel:{phone_href}" style="color: #FFFFFF; text-decoration: none; font-size: 32px; font-weight: 800; display: block;">
                        Call now: {safe_phone}
                    </a>
                </td>
            </tr></tbody>
        </table>

        <table width="100%" border="0" cellspacing="0" cellpadding="0">
            <tbody><tr>
                <td align="center" style="background-color: #FFFFFF; border: 2px solid #003764; padding: 20px;">
                    <a href="{site_url}/mna" target="_blank" style="color: #003764; text-decoration: none; font-size: 22px; font-weight: 700; display: block;">
                        View all listings
                    </a>
                </td>
            </tr>
            <tr><td height="15"></td></tr>
            <tr>
                <td align="center" style="background-color: #F6F6F3; border: 1px solid #D1D1D1; padding: 20px;">
                    <a href="{site_url}/mna/{number_slug}" target="_blank" style="color: #4E5968; text-decoration: none; font-size: 22px; font-weight: 700; display: block;">
                        View this listing detail
                    </a>
                </td>
            </tr></tbody>
        </table>

        <p style="font-size: 18px; color: #B0B8C1; margin-top: 60px; font-weight: 500;">Provided by Harang Administrative Office</p>
    </div>

</div>'''

        return html, raw_title

# =================================================================
# [썸네일 생성기]
# =================================================================
class ThumbnailMaker:
    def __init__(self):
        pass
    
    def create_summary_image(self, data, ai_content, output_path="summary_thumb.png"):
        """Generate summary thumbnail and return image path."""
        number = data.get('번호', 'N/A')

        points = ai_content.get('summary_points', []) if isinstance(ai_content, dict) else []
        points_html = ""
        for i, point in enumerate(points):
            color = "#003764" if i == len(points) - 1 else "#AC9479"
            safe_point = _safe_html(point)
            points_html += f'''
            <tr>
                <td width="30" valign="top" style="padding-bottom: 20px;"><span style="color: {color}; font-size: 22px; font-weight: bold;">•</span></td>
                <td style="padding-bottom: 20px; font-size: 24px; color: #333; font-weight: 700;">{safe_point}</td>
            </tr>'''

        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ margin: 0; padding: 0; background: #f6f6f3; }}
        #container {{
            width: 800px;
            background: #fff;
            border-top: 3px solid #003764;
            border-bottom: 1px solid #003764;
            padding: 40px 30px;
            font-family: 'Malgun Gothic', sans-serif;
        }}
        h3 {{
            margin: 0 0 25px 0;
            font-size: 26px;
            font-weight: 800;
            color: #003764;
        }}
    </style>
</head>
<body>
    <div id="container">
        <h3>프리미엄 매물 요약 : 제 {number}호</h3>
        <table width="100%" border="0" cellspacing="0" cellpadding="0">
            <tbody>{points_html}</tbody>
        </table>
    </div>
</body>
</html>'''

        temp_html = "temp_summary.html"
        driver = None
        abs_output = os.path.abspath(output_path)

        try:
            with open(temp_html, "w", encoding="utf-8") as f:
                f.write(html)

            opts = Options()
            opts.add_argument("--headless")
            opts.add_argument("--window-size=900,600")
            opts.add_argument("--hide-scrollbars")
            opts.add_argument("--force-device-scale-factor=2")

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
            driver.get(f"file://{os.path.abspath(temp_html)}")
            time.sleep(1)

            container = driver.find_element(By.ID, "container")
            container.screenshot(abs_output)
            print(f"✅ 썸네일 생성: {abs_output}")
            return abs_output
        except (WebDriverException, OSError, ValueError) as e:
            fallback = os.path.abspath("summary_thumb.jpg")
            if os.path.exists(fallback):
                print(f"⚠️ 썸네일 생성 실패, fallback 사용: {fallback} ({_safe_error_text(e)})")
                return fallback
            print(f"⚠️ 썸네일 생성 실패: {_safe_error_text(e)}")
            return abs_output
        finally:
            try:
                if driver:
                    driver.quit()
            except WebDriverException:
                pass
            try:
                if os.path.exists(temp_html):
                    os.remove(temp_html)
            except OSError:
                pass

class PremiumPublisher:
    def __init__(self, headless=False):
        opts = Options()
        if headless:
            opts.add_argument("--headless")
        opts.add_argument("--window-size=1400,900")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
        self.wait = WebDriverWait(self.driver, 10)
        self.base_url = CONFIG["SITE_URL"]
        self.last_error_kind = ""

    def _set_error(self, kind):
        self.last_error_kind = str(kind or "")

    def _session_alive(self):
        try:
            if self.driver is None:
                return False
            if not getattr(self.driver, "session_id", None):
                return False
            _ = self.driver.title
            return True
        except (WebDriverException, AttributeError):
            return False

    def _ensure_session(self, step_name):
        if self._session_alive():
            return True
        self._set_error("session")
        print(f"⚠️ 브라우저 세션이 종료되어 '{step_name}' 단계를 진행할 수 없습니다.")
        return False

    def _js_click(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.3)
        self.driver.execute_script("arguments[0].click();", element)

    def _safe_send_keys(self, element, text):
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.3)
        element.clear()
        element.send_keys(text)

    def _dismiss_alert(self):
        if not self._session_alive():
            return False
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            print(f"⚠️ 알림창 발견: {alert_text}")
            alert.accept()
            time.sleep(0.5)
            return True
        except (NoAlertPresentException, WebDriverException):
            return False

    def login(self):
        self._set_error("")
        if not self._ensure_session("login"):
            return False
        print("🔐 로그인 시도...")

        try:
            self.driver.get(self.base_url)
            time.sleep(2)
            self._dismiss_alert()

            login_links = self.driver.find_elements(
                By.CSS_SELECTOR,
                "a[href*='login'], a[href*='member'], .login_link",
            )
            if login_links:
                self._js_click(login_links[0])
                time.sleep(1)
            else:
                self.driver.get(f"{self.base_url}/bbs/login.php")
                time.sleep(1)
            self._dismiss_alert()

            id_input = None
            for name in ["mb_id", "user_id", "id", "login_id"]:
                try:
                    cand = self.driver.find_element(By.NAME, name)
                    if cand and cand.is_displayed():
                        id_input = cand
                        break
                except (NoSuchElementException, WebDriverException):
                    continue
            if id_input is None:
                for cand in self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']"):
                    if cand.is_displayed():
                        id_input = cand
                        break
            if id_input is None:
                print("⚠️ 로그인 ID 입력창을 찾지 못했습니다.")
                return False
            self._safe_send_keys(id_input, CONFIG["ADMIN_ID"])

            pw_input = None
            for name in ["mb_password", "password", "user_pw", "pw"]:
                try:
                    cand = self.driver.find_element(By.NAME, name)
                    if cand and cand.is_displayed():
                        pw_input = cand
                        break
                except (NoSuchElementException, WebDriverException):
                    continue
            if pw_input is None:
                for cand in self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']"):
                    if cand.is_displayed():
                        pw_input = cand
                        break
            if pw_input is None:
                print("⚠️ 로그인 비밀번호 입력창을 찾지 못했습니다.")
                return False
            self._safe_send_keys(pw_input, CONFIG["ADMIN_PW"])

            clicked = False
            for btn in self.driver.find_elements(
                By.CSS_SELECTOR,
                "button[type='submit'], input[type='submit'], .btn_submit, .login_btn, button.submit",
            ):
                if btn.is_displayed():
                    self._js_click(btn)
                    clicked = True
                    break
            if not clicked:
                print("⚠️ 로그인 버튼을 찾지 못했습니다.")
                return False

            time.sleep(2)
            self._dismiss_alert()
            print("✅ 로그인 성공")
            return True
        except (InvalidSessionIdException, WebDriverException) as e:
            self._set_error("session")
            print(f"⚠️ 로그인 중 세션 오류: {_safe_error_text(e)}")
            return False
        except Exception as e:
            print(f"⚠️ 로그인 실패: {_safe_error_text(e)}")
            self._dismiss_alert()
            return False

    def open_write_page(self):
        self._set_error("")
        if not self._ensure_session("open_write_page"):
            return False
        try:
            self._dismiss_alert()
            self.driver.get(f"{self.base_url}/premium/write")
            time.sleep(2)
            self._dismiss_alert()
            print("✅ 글쓰기 페이지 열림")
            return True
        except (InvalidSessionIdException, WebDriverException) as e:
            self._set_error("session")
            print(f"⚠️ 글쓰기 페이지 이동 실패(세션): {_safe_error_text(e)}")
            return False
        except Exception as e:
            print(f"⚠️ 글쓰기 페이지 이동 실패: {_safe_error_text(e)}")
            return False

    def set_title(self, title):
        self._set_error("")
        if not self._ensure_session("set_title"):
            return False
        try:
            title_input = self.wait.until(EC.presence_of_element_located((By.NAME, "wr_subject")))
            title_input.clear()
            title_input.send_keys(title)
            print(f"✅ 제목 입력: {title[:50]}...")
            return True
        except (TimeoutException, WebDriverException) as e:
            print(f"⚠️ 제목 입력 실패: {_safe_error_text(e)}")
            return False

    def set_content_smarteditor(self, html_content):
        self._set_error("")
        if not self._ensure_session("set_content_smarteditor"):
            return False
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    if body.get_attribute("contenteditable") == "true":
                        self.driver.execute_script("arguments[0].innerHTML = arguments[1];", body, html_content)
                        print("✅ 본문 HTML 입력 완료")
                        self.driver.switch_to.default_content()
                        return True
                except (NoSuchElementException, WebDriverException):
                    self.driver.switch_to.default_content()
                    continue

            self.driver.switch_to.default_content()
            textarea = self.driver.find_element(By.NAME, "wr_content")
            self.driver.execute_script("arguments[0].value = arguments[1];", textarea, html_content)
            print("✅ 본문 HTML 입력 완료 (textarea)")
            return True
        except Exception as e:
            print(f"⚠️ 본문 입력 실패: {_safe_error_text(e)}")
            return False

    def upload_image(self, image_path):
        self._set_error("")
        if not self._ensure_session("upload_image"):
            return False

        main_window = None
        try:
            abs_path = os.path.abspath(image_path)
            if not os.path.exists(abs_path):
                print(f"⚠️ 이미지 파일이 존재하지 않습니다: {abs_path}")
                return False

            print(f"🖼 이미지 업로드 시작: {abs_path}")
            main_window = self.driver.current_window_handle

            photo_btn = None
            selectors = [
                "button[class*='photo']",
                "a[class*='photo']",
                "[title*='사진']",
                "img[src*='photo']",
                ".se2_photo",
                "#se2_photo",
            ]
            for sel in selectors:
                try:
                    cand = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if cand:
                        photo_btn = cand
                        break
                except (NoSuchElementException, WebDriverException):
                    continue

            if photo_btn is None:
                toolbar = self.driver.find_elements(By.CSS_SELECTOR, ".se2_tool_bar button, .se2_tool_bar a")
                for btn in toolbar:
                    title = btn.get_attribute("title") or ""
                    class_name = btn.get_attribute("class") or ""
                    if ("사진" in title) or ("photo" in class_name.lower()):
                        photo_btn = btn
                        break

            if photo_btn is not None:
                photo_btn.click()
                print("✅ 사진 버튼 클릭")
                time.sleep(1.5)
            else:
                print("⚠️ 사진 버튼을 찾지 못해 팝업 URL 직접 접근")
                popup_url = f"{self.base_url}/plugin/editor/smarteditor2/photo_uploader/popup/index.html"
                self.driver.execute_script(f"window.open('{popup_url}', 'photo_popup', 'width=500,height=400');")
                time.sleep(1.5)

            popup_window = None
            for handle in self.driver.window_handles:
                if handle != main_window:
                    popup_window = handle
                    break

            if popup_window:
                self.driver.switch_to.window(popup_window)
                print("✅ 팝업 창으로 전환")
                time.sleep(1)

                file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                if not file_inputs:
                    print("⚠️ 파일 input을 찾지 못했습니다.")
                    self.driver.switch_to.window(main_window)
                    return False

                file_inputs[0].send_keys(abs_path)
                print(f"✅ 파일 선택 완료: {abs_path}")
                time.sleep(1.5)

                confirm_btns = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "button, input[type='submit'], input[type='button'], a[class*='btn']",
                )
                for btn in confirm_btns:
                    text = (btn.text or btn.get_attribute("value") or "").strip()
                    if any(word in text for word in ["확인", "삽입", "적용", "업로드", "등록"]):
                        btn.click()
                        print(f"✅ '{text}' 버튼 클릭")
                        time.sleep(1.5)
                        break

                try:
                    if popup_window in self.driver.window_handles:
                        self.driver.close()
                except WebDriverException:
                    pass

                self.driver.switch_to.window(main_window)
                print("✅ 메인 창으로 복귀")
            else:
                print("ℹ️ 업로더가 동일 창/모달 방식일 수 있어 직접 file input 시도")
                file_input = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
                file_input.send_keys(abs_path)
                time.sleep(1.5)

            print("✅ 이미지 업로드 완료")
            return True
        except (InvalidSessionIdException, WebDriverException) as e:
            self._set_error("session")
            print(f"⚠️ 이미지 업로드 중 세션 오류: {_safe_error_text(e)}")
            return False
        except (NoSuchElementException, TimeoutException, WebDriverException, OSError) as e:
            print(f"⚠️ 이미지 업로드 실패: {_safe_error_text(e)}")
            try:
                if main_window and self._session_alive():
                    self.driver.switch_to.window(main_window)
            except (NoSuchWindowException, WebDriverException):
                pass
            return False

    def submit(self, as_draft=True):
        self._set_error("")
        if not self._ensure_session("submit"):
            return False
        try:
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            submit_btn.click()
            time.sleep(2)
            print("✅ 글 제출 완료")
            return True
        except (NoSuchElementException, WebDriverException) as e:
            print(f"⚠️ 제출 실패: {_safe_error_text(e)}")
            return False

    def close(self):
        if self.driver is None:
            return
        try:
            self.driver.quit()
        except WebDriverException:
            pass
        finally:
            self.driver = None

def resolve_next_target(start_from=7611):
    crawler = PremiumCrawler(driver=None)
    latest = crawler.get_latest_premium_post_info()
    next_number = crawler.get_next_target_number(start_from=start_from)
    return {
        "start_from": int(start_from),
        "latest_premium": latest,
        "next_target": next_number,
        "ok": bool(next_number),
    }


def _write_premium_run_report(report):
    try:
        logs_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(logs_dir, f"premium_run_{stamp}.json")
        latest_path = os.path.join(logs_dir, "premium_run_latest.json")
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(payload)
        with open(latest_path, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"[premium-run] report saved: {out_path}")
    except (OSError, TypeError, ValueError) as e:
        print(f"[premium-run] report save failed: {_safe_error_text(e)}")


def run_automation(start_from=7611, headless=False, verify_publish=True):
    ensure_config(["GEMINI_API_KEY", "SITE_URL", "ADMIN_ID", "ADMIN_PW"], "premium_auto:run")
    print("=" * 60)
    print(f"[{CONFIG['BRAND_NAME']}] Premium auto writer")
    print("=" * 60)

    publisher = None
    thumb_path = ""
    remove_thumb = False
    retry_used = False
    final_result = {"ok": False, "reason": "unknown"}

    run_report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "start_from": int(start_from),
        "headless": bool(headless),
        "verify_publish": bool(verify_publish),
        "events": [],
    }

    def _event(step, ok=None, **extra):
        row = {
            "at": datetime.now(timezone.utc).isoformat(),
            "step": str(step),
        }
        if ok is not None:
            row["ok"] = bool(ok)
        if extra:
            row.update(extra)
        run_report["events"].append(row)

    def _finish(result):
        nonlocal final_result
        final_result = dict(result or {})
        return final_result

    def _publish_steps(active_publisher, title, html_content, image_path, target_number):
        if not active_publisher.open_write_page():
            return False, "open_write_failed", str(getattr(active_publisher, "last_error_kind", "") or "")
        if not active_publisher.set_title(title):
            return False, "set_title_failed", str(getattr(active_publisher, "last_error_kind", "") or "")
        if not active_publisher.set_content_smarteditor(html_content):
            return False, "set_content_failed", str(getattr(active_publisher, "last_error_kind", "") or "")
        if not active_publisher.upload_image(image_path):
            return False, "image_upload_failed", str(getattr(active_publisher, "last_error_kind", "") or "")
        return True, "ok", ""

    try:
        _event("publisher_boot")
        publisher = PremiumPublisher(headless=headless)

        if not publisher.login():
            _event("login", ok=False)
            return _finish({"ok": False, "reason": "login_failed"})
        _event("login", ok=True)

        crawler = PremiumCrawler(publisher.driver)
        target_number = crawler.get_next_target_number(start_from=start_from)
        if not target_number:
            _event("target_resolve", ok=False)
            return _finish({"ok": False, "reason": "target_not_found"})
        _event("target_resolve", ok=True, target_number=int(target_number))
        print(f"Target listing number: {target_number}")

        mna_data = crawler.fetch_mna_data(target_number)
        if not isinstance(mna_data, dict) or not mna_data:
            _event("fetch_mna", ok=False)
            return _finish({"ok": False, "reason": "mna_fetch_failed", "target_number": target_number})
        _event("fetch_mna", ok=True)

        generator = ContentGenerator()
        ai_content = generator.generate_article(mna_data)
        if not ai_content:
            _event("generate_content", ok=False)
            return _finish({"ok": False, "reason": "ai_generate_failed", "target_number": target_number})
        _event("generate_content", ok=True)

        html_content, title = generator.render_html(mna_data, ai_content)
        _event("render_html", ok=True)

        thumbnail = ThumbnailMaker()
        thumb_path = thumbnail.create_summary_image(mna_data, ai_content)
        remove_thumb = os.path.basename(str(thumb_path or "")).lower() == "summary_thumb.png"
        _event("thumbnail", ok=os.path.exists(str(thumb_path or "")), thumb_path=str(thumb_path))

        publish_ok, publish_reason, publish_error_kind = _publish_steps(
            publisher, title, html_content, thumb_path, target_number
        )
        _event(
            "publish_steps",
            ok=publish_ok,
            reason=publish_reason,
            error_kind=publish_error_kind,
        )

        if (not publish_ok) and (publish_error_kind == "session"):
            retry_used = True
            print("Session dropped during publish steps. Re-login and retry once.")
            _event("publish_retry_prepare", ok=True)
            try:
                publisher.close()
            except Exception:
                pass
            publisher = PremiumPublisher(headless=headless)
            if not publisher.login():
                _event("publish_retry_login", ok=False)
                return _finish({
                    "ok": False,
                    "reason": "publish_retry_login_failed",
                    "target_number": target_number,
                })
            _event("publish_retry_login", ok=True)
            publish_ok, publish_reason, publish_error_kind = _publish_steps(
                publisher, title, html_content, thumb_path, target_number
            )
            _event(
                "publish_steps_retry",
                ok=publish_ok,
                reason=publish_reason,
                error_kind=publish_error_kind,
            )

        if not publish_ok:
            return _finish({
                "ok": False,
                "reason": publish_reason,
                "error_kind": publish_error_kind,
                "target_number": target_number,
                "retry_used": retry_used,
            })

        print("=" * 60)
        print("Preview is ready in browser.")
        print(f"- title: {title}")
        print(f"- thumbnail: {thumb_path}")
        print("- click '????' in browser, then press Enter here")
        print("=" * 60)

        input("[Enter] after save to continue publish verification...")

        published_confirmed = None
        latest_after = {}
        if verify_publish:
            checker = PremiumCrawler(driver=None)
            ok, latest_row, _rows = checker.is_number_in_latest_premium(target_number, limit=30)
            published_confirmed = bool(ok)
            latest_after = latest_row or {}
            _event("verify_publish", ok=published_confirmed, latest=latest_after)
            if published_confirmed:
                print(f"Publish verified on premium list: {target_number}")
            else:
                print("Publish was not verified on premium list. Check write completion status.")
                latest_title = str(latest_after.get("title") or "").strip()
                if latest_title:
                    print(f"Latest premium title now: {latest_title}")

        return _finish({
            "ok": True,
            "target_number": target_number,
            "title": title,
            "published_confirmed": published_confirmed,
            "latest_after": latest_after,
            "retry_used": retry_used,
        })
    except Exception as e:
        _event("runtime_exception", ok=False, error=_safe_error_text(e))
        return _finish({"ok": False, "reason": "runtime_exception", "error": _safe_error_text(e)})
    finally:
        try:
            if remove_thumb and thumb_path and os.path.exists(thumb_path):
                os.remove(thumb_path)
        except OSError:
            pass
        try:
            if publisher:
                publisher.close()
        except WebDriverException:
            pass

        run_report["finished_at"] = datetime.now(timezone.utc).isoformat()
        run_report["result"] = final_result
        _write_premium_run_report(run_report)


import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

class PremiumAutoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Premium 매물 글 자동 생성기")
        self.root.geometry("700x500")
        
        self._create_widgets()
    
    def _create_widgets(self):
        # 헤더
        ttk.Label(self.root, text="📝 Premium 매물 글 자동 생성기", font=("맑은 고딕", 14, "bold")).pack(pady=15)
        
        # 매물 번호 입력
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.X)
        
        ttk.Label(frame, text="매물 번호:").pack(side=tk.LEFT)
        self.number_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.number_var, width=15).pack(side=tk.LEFT, padx=10)
        ttk.Button(frame, text="최신 번호 조회", command=self._fetch_latest).pack(side=tk.LEFT)
        
        # 실행 버튼
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="▶ 글 생성 시작", command=self._run).pack(side=tk.LEFT, padx=5)
        
        # 로그
        log_frame = ttk.LabelFrame(self.root, text="실행 로그", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def _log(self, msg):
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def _fetch_latest(self):
        self._log("최신 번호 조회 중...")
        try:
            status = resolve_next_target(start_from=7611)
            latest = status.get("latest_premium", {}) or {}
            next_target = status.get("next_target")
            latest_title = str(latest.get("title") or "").strip()
            latest_num = latest.get("number")
            if latest_title:
                self._log(f"최신 premium 제목: {latest_title}")
            if latest_num:
                self._log(f"최신 premium 번호: {latest_num}")
            self._log(f"다음 타겟 번호: {next_target}")
            if next_target:
                self.number_var.set(str(next_target))
        except (ValueError, AttributeError, KeyError) as e:
            self._log(f"조회 실패: {_safe_error_text(e)}")
    def _run(self):
        number = self.number_var.get().strip()
        if not number:
            messagebox.showwarning("경고", "매물 번호를 입력하세요.")
            return

        self._log(f"매물 {number} 자동화를 콘솔에서 실행하세요.")
        messagebox.showinfo("안내", f"콘솔 실행:\npython premium_auto.py --start-from {number}")

def _parse_cli_args():
    parser = argparse.ArgumentParser(description="Premium listing auto writer")
    parser.add_argument("--gui", action="store_true", help="Run GUI mode")
    parser.add_argument("--status", action="store_true", help="Print latest premium + next target only")
    parser.add_argument("--start-from", type=int, default=7611, help="Minimum starting listing number")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument(
        "--no-verify-publish",
        action="store_true",
        help="Skip post-save premium list verification step",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_cli_args()
    try:
        if args.gui:
            ensure_config(["GEMINI_API_KEY", "SITE_URL", "ADMIN_ID", "ADMIN_PW"], "premium_auto:gui")
            root = tk.Tk()
            app = PremiumAutoApp(root)
            root.mainloop()
            sys.exit(0)

        if args.status:
            require_config(CONFIG, ["SITE_URL"], context="premium_auto:status")
            status = resolve_next_target(start_from=args.start_from)
            print(json.dumps(status, ensure_ascii=False, indent=2))
            sys.exit(0 if status.get("ok") else 1)

        result = run_automation(
            start_from=args.start_from,
            headless=bool(args.headless),
            verify_publish=not bool(args.no_verify_publish),
        )
        if not result.get("ok"):
            sys.exit(1)
        if result.get("published_confirmed") is False:
            # Explicitly signal "run completed but publish not confirmed".
            sys.exit(2)
        sys.exit(0)
    except ValueError as e:
        msg = str(e)
        if args.gui:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("환경 설정 오류", msg)
            root.destroy()
        else:
            print(msg)
        sys.exit(1)
