# =================================================================
# [내부 링크 모듈] 기존 글과 자동 연결
# =================================================================

import re
import requests
import logging
import json
import os
from datetime import datetime
from html import escape, unescape
from difflib import SequenceMatcher
from urllib.parse import urlparse

class InternalLinker:
    """
    WordPress 기존 글과 새 콘텐츠를 자동으로 연결
    """
    
    def __init__(self, wp_url, auth_header=None):
        self.wp_url = wp_url
        self.auth_header = auth_header or {}
        self.logger = logging.getLogger("mnakr")
        self.cached_posts = []
        self.memory_file = "internal_link_memory.json"
        self.memory = self._load_memory()
        self.duplicate_link_penalty_start = 3
        self.duplicate_link_penalty_step = 4
        self.high_similarity_cutoff = 0.92
        self._wp_host = self._extract_host(wp_url)

    def _load_memory(self):
        if not os.path.exists(self.memory_file):
            return {"by_keyword": {}, "by_link": {}}
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("by_keyword", {})
                data.setdefault("by_link", {})
                return data
        except Exception:
            pass
        return {"by_keyword": {}, "by_link": {}}

    def _save_memory(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"내부링크 메모리 저장 실패: {e}")

    def _norm_key(self, text):
        return re.sub(r"[^0-9a-z가-힣]+", "", str(text or "").lower())

    def _extract_host(self, url):
        try:
            return urlparse(str(url or "")).netloc.lower().split(":")[0]
        except Exception:
            return ""

    def _is_same_host(self, host):
        host = str(host or "").lower().split(":")[0]
        base = str(self._wp_host or "").lower().split(":")[0]
        if not host or not base:
            return False
        return host == base or host.endswith("." + base) or base.endswith("." + host)

    def _safe_internal_url(self, url):
        candidate = str(url or "").strip()
        if not candidate:
            return ""
        parsed = urlparse(candidate)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return ""
        if self._wp_host and not self._is_same_host(parsed.netloc):
            return ""
        return candidate

    def _remember_links(self, keyword, related_posts):
        key = self._norm_key(keyword)
        if not key or not related_posts:
            return
        by_keyword = self.memory.setdefault("by_keyword", {})
        by_link = self.memory.setdefault("by_link", {})
        node = by_keyword.setdefault(key, {"links": {}, "updated_at": ""})
        for post in related_posts:
            link = self._safe_internal_url(post.get("link", ""))
            if not link:
                continue
            node["links"][link] = int(node["links"].get(link, 0)) + 1
            by_link[link] = int(by_link.get(link, 0)) + 1
        node["updated_at"] = datetime.now().isoformat()
        self._save_memory()
    
    def fetch_published_posts(self, limit=100):
        """
        발행된 글 목록 가져오기
        """
        if self.cached_posts:
            return self.cached_posts
        
        try:
            all_posts = []
            page = 1
            
            while len(all_posts) < limit:
                res = requests.get(
                    f"{self.wp_url}/posts",
                    params={
                        "per_page": min(100, limit - len(all_posts)),
                        "page": page,
                        "status": "publish",
                        "_fields": "id,title,link,slug,excerpt"
                    },
                    headers=self.auth_header,
                    timeout=10
                )
                
                if res.status_code != 200:
                    break
                
                posts = res.json()
                if not posts:
                    break
                
                for post in posts:
                    link = self._safe_internal_url(post.get("link", ""))
                    if not link:
                        continue
                    all_posts.append({
                        "id": post.get("id"),
                        "title": self._clean_html(post.get("title", {}).get("rendered", "")),
                        "link": link,
                        "slug": post.get("slug", ""),
                        "excerpt": self._clean_html(post.get("excerpt", {}).get("rendered", ""))
                    })
                
                page += 1
            
            self.cached_posts = all_posts
            self.logger.info(f"내부링크용 기존 글 {len(all_posts)}건 로드")
            return all_posts
            
        except Exception as e:
            self.logger.error(f"글 목록 조회 실패: {e}")
            return []
    
    def _clean_html(self, text):
        """HTML 태그 제거"""
        return re.sub(r'<[^>]+>', '', text).strip()

    def _koreanize_display_title(self, text):
        src = unescape(str(text or ""))
        src = re.sub(r"</?[A-Za-z][^>]*>", "", src).strip()
        if not src:
            return ""

        # Keep user-facing related-link labels fully Korean.
        src = re.sub(r"(?i)\bkiscon\b", "키스콘", src)
        src = re.sub(r"(?i)\btop\s*([0-9]+)\b", r"상위 \1", src)
        src = re.sub(r"(?i)\bcheck\s*list\b", "체크리스트", src)
        src = re.sub(r"(?i)\bguide\b", "가이드", src)

        # Drop parenthesized English fragments like "(Company Overview)".
        src = re.sub(r"\(([A-Za-z0-9 _/&+\-]{2,})\)", "", src)
        src = re.sub(r"\b[A-Za-z]{2,}\b", "", src)
        src = re.sub(r"([가-힣0-9]+)\(\s*\1\s*\)", r"\1", src)
        src = re.sub(r"\s{2,}", " ", src)
        src = re.sub(r"\(\s*\)", "", src)
        src = src.strip(" -|/\t\r\n")
        return src

    def _similarity(self, a, b):
        """두 문자열의 유사도 계산 (0~1)"""
        return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

    def _tokenize(self, text):
        return {
            w
            for w in re.findall(r"[0-9a-zA-Z가-힣]{2,}", str(text or "").lower())
            if len(w) >= 2
        }

    def _memory_penalty(self, link):
        used = int(self.memory.get("by_link", {}).get(str(link or ""), 0))
        over = max(0, used - self.duplicate_link_penalty_start)
        return over * self.duplicate_link_penalty_step

    def find_related_posts(self, keyword, content_text="", max_results=3):
        """
        키워드와 본문 기준으로 관련 기존 글 후보를 찾고,
        과도한 동일 링크 반복을 피하도록 다양성을 보장한다.
        """
        posts = self.fetch_published_posts()
        if not posts:
            return []

        keyword = str(keyword or "").strip()
        content_text = str(content_text or "")
        keyword_tokens = self._tokenize(keyword)
        content_tokens = self._tokenize(content_text)

        key_norm = self._norm_key(keyword)
        by_keyword = self.memory.get("by_keyword", {})
        memory_links = set(by_keyword.get(key_norm, {}).get("links", {}).keys())

        scored = []
        for post in posts:
            title = str(post.get("title", "")).strip()
            link = self._safe_internal_url(post.get("link", ""))
            if not title or not link:
                continue

            title_tokens = self._tokenize(title)
            common_kw = keyword_tokens & title_tokens
            common_content = content_tokens & title_tokens

            sim = self._similarity(keyword, title) if keyword else 0.0
            score = 0.0
            score += len(common_kw) * 22
            score += sim * 55
            score += min(20, len(common_content) * 4)

            if title in content_text:
                score += 12
            if link in memory_links:
                score += 8

            score -= self._memory_penalty(link)

            if score > 8:
                scored.append({
                    "title": title,
                    "link": link,
                    "relevance": round(score, 2),
                })

        scored.sort(key=lambda x: x["relevance"], reverse=True)

        selected = []
        seen_links = set()
        for cand in scored:
            if cand["link"] in seen_links:
                continue
            if any(self._similarity(cand["title"], picked["title"]) >= self.high_similarity_cutoff for picked in selected):
                continue
            selected.append(cand)
            seen_links.add(cand["link"])
            if len(selected) >= max_results:
                break

        if len(selected) < max_results:
            for cand in scored:
                if cand["link"] in seen_links:
                    continue
                selected.append(cand)
                seen_links.add(cand["link"])
                if len(selected) >= max_results:
                    break

        return selected[:max_results]

    def inject_links(self, html_content, related_posts, position="after_body2", keyword=""):
        """
        HTML 콘텐츠에 관련 글 링크 섹션 삽입
        
        Args:
            html_content: 원본 HTML
            related_posts: find_related_posts() 결과
            position: 삽입 위치 ("after_body2" 또는 "before_conclusion")
        
        Returns:
            링크가 삽입된 HTML
        """
        if not related_posts:
            return html_content

        if 'data-internal-links="1"' in html_content:
            return html_content

        if keyword:
            self._remember_links(keyword, related_posts)
        
        # 관련 글 섹션 HTML 생성
        link_rows = []
        for post in related_posts:
            safe_link = self._safe_internal_url(post.get("link", ""))
            link = escape(safe_link, quote=True)
            title_text = self._koreanize_display_title(post.get("title", ""))
            title = escape(title_text)
            if not link or not title:
                continue
            link_rows.append(
                '        <li style="padding:10px 0;border-bottom:1px solid #e2e8f0;">\n'
                f'            <a href="{link}" style="color:#003764;text-decoration:none;font-size:16px;font-weight:500;">\n'
                f'                → {title}\n'
                "            </a>\n"
                "        </li>\n"
            )

        if not link_rows:
            return html_content

        links_html = """
<div data-internal-links="1" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:24px 28px;margin:36px 0;">
    <div style="display:flex;align-items:center;margin-bottom:16px;">
        <span style="display:inline-block;width:24px;height:2px;background:#003764;margin-right:10px;"></span>
        <span style="font-size:15px;font-weight:600;color:#003764;letter-spacing:2px;">관련 글</span>
    </div>
    <ul style="list-style:none;padding:0;margin:0;">
"""
        links_html += "".join(link_rows)
        
        links_html += """    </ul>
</div>
"""
        
        insert_pos = None

        # mnakr 템플릿 기준: 본문1/2/3 섹션 래퍼는 동일한 스타일을 사용
        if position == "after_body2":
            sections = list(re.finditer(r'<div style="margin-bottom:56px;">', html_content))
            if len(sections) >= 3:
                insert_pos = sections[2].start()

        if insert_pos is None:
            conclusion_pattern = r'(<div style="background:#003764;padding:44px 48px;margin:56px 0;">)'
            match = re.search(conclusion_pattern, html_content)
            if match:
                insert_pos = match.start()

        if insert_pos is None:
            return html_content + links_html
        return html_content[:insert_pos] + links_html + html_content[insert_pos:]


def generate_faq_schema(faqs):
    """
    FAQ 목록을 JSON-LD 스키마로 변환
    
    Args:
        faqs: [{"question": "...", "answer": "..."}, ...]
    
    Returns:
        JSON-LD 스크립트 태그 문자열
    """
    if not faqs:
        return ""
    
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": []
    }
    
    for faq in faqs:
        schema["mainEntity"].append({
            "@type": "Question",
            "name": faq.get("question", ""),
            "acceptedAnswer": {
                "@type": "Answer",
                "text": faq.get("answer", "")
            }
        })
    
    import json
    return f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'


def extract_faqs_from_content(html_content):
    """
    HTML 콘텐츠에서 FAQ 추출 (Q/A 패턴 기반)
    """
    faqs = []
    
    # mnakr FAQ 렌더 결과 기준:
    # <span ...>Q|질문</span><span ...>질문본문</span><br><span ...>A|답변</span>답변본문</div>
    pattern = (
        r'<span[^>]*>\s*(?:Q|질문)\s*</span>\s*<span[^>]*>(.*?)</span>\s*'
        r'<br\s*/?>\s*<span[^>]*>\s*(?:A|답변)\s*</span>\s*(.*?)</div>'
    )
    matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)

    for q_raw, a_raw in matches:
        q = re.sub(r'<[^>]+>', '', unescape(q_raw)).strip()
        a = re.sub(r'<[^>]+>', '', unescape(a_raw)).strip()
        if q and a:
            faqs.append({
                "question": q,
                "answer": a
            })
    
    return faqs


