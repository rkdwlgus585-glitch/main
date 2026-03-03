# =================================================================
# TrendRadar v2 - construction keyword discovery with duplicate guard
# =================================================================

import json
import os
import random
import re
import time
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher

import requests

from utils import retry_request, setup_logger

logger = setup_logger()


class TrendRadarV2:
    """Keyword miner tuned for construction-license consultation topics."""

    HISTORY_FILE = "keyword_history.json"
    CACHE_FILE = "wp_posts_cache.json"
    CACHE_EXPIRY_HOURS = 6

    MANUAL_BOOSTS = [
        {"name": "신규등록", "boost": 18, "max_posts": 4, "keywords": ["신규등록", "등록기준", "준비서류"]},
        {"name": "양도양수", "boost": 18, "max_posts": 4, "keywords": ["양도양수", "실사", "계약서"]},
        {"name": "기업진단", "boost": 16, "max_posts": 3, "keywords": ["기업진단", "실질자본금"]},
        {"name": "기술인력", "boost": 14, "max_posts": 3, "keywords": ["기술인력", "등록기준"]},
        {"name": "행정처분", "boost": 14, "max_posts": 3, "keywords": ["행정처분", "청문", "소명"]},
    ]

    CONSTRUCTION_ANCHORS = [
        "건설업", "전문건설업", "종합건설업", "면허", "등록", "양도양수",
        "기업진단", "실질자본금", "공제조합", "출자좌수", "기술인력",
        "시공능력", "행정처분", "입찰", "키스콘", "KISCON",
    ]

    STOPWORDS = {
        "건설업", "건설", "가이드", "총정리", "방법", "기준", "체크", "실무",
        "그리고", "또는", "대한", "관련", "에서", "으로", "하기", "위한",
    }

    MAIN_KEYWORDS = {
        "핵심": [
            "건설업 신규등록", "건설업 양도양수", "건설업 기업진단", "건설업 실질자본금",
            "건설공제조합 출자좌수", "건설업 기술인력", "건설업 행정처분", "건설업 입찰",
        ],
        "업종": ["전문건설업", "종합건설업", "전기공사업", "정보통신공사업", "소방시설공사업"],
    }

    SUB_KEYWORDS = {
        "행동": ["절차", "요건", "서류", "비용", "기간", "체크리스트", "주의사항"],
        "리스크": ["반려", "미달", "행정처분", "분쟁", "세무", "실사"],
        "연도": ["2026", "최신", "개정"],
    }

    DYNAMIC_BOOST_SCORES = [16, 10, 6]
    DYNAMIC_MAX_POSTS = 4

    def __init__(self, wp_url=None, wp_headers=None):
        self.wp_url = wp_url
        self.wp_headers = wp_headers or {}
        self.history = self._load_history()
        self.existing_posts = []
        self._dynamic_boosts = {}

    def _generate_search_seeds(self, count=30):
        all_mains = [w for rows in self.MAIN_KEYWORDS.values() for w in rows]
        all_subs = [w for rows in self.SUB_KEYWORDS.values() for w in rows]
        if not all_mains or not all_subs:
            return []

        rng = random.Random(datetime.now().strftime("%Y%m%d"))
        seeds = set()

        for main in rng.sample(all_mains, min(len(all_mains), 12)):
            for sub in rng.sample(all_subs, min(len(all_subs), 5)):
                seeds.add(f"{main} {sub}")

        for boost in self.MANUAL_BOOSTS:
            for k in boost.get("keywords", []):
                seeds.add(k)
                for sub in rng.sample(all_subs, min(len(all_subs), 4)):
                    seeds.add(f"{k} {sub}")

        seeds_list = list(seeds)
        sampled = rng.sample(seeds_list, min(len(seeds_list), count)) if seeds_list else []
        logger.info(f"🔎 검색 시드: {len(seeds_list)}개 중 {len(sampled)}개 샘플")
        return sampled

    def _detect_dynamic_trends(self, candidates):
        counts = Counter()
        for kw in candidates:
            for boost in self.MANUAL_BOOSTS:
                if any(token in kw for token in boost.get("keywords", [])):
                    counts[boost["name"]] += 1

        self._dynamic_boosts = {}
        for rank, (name, _cnt) in enumerate(counts.most_common(len(self.DYNAMIC_BOOST_SCORES))):
            base = self.DYNAMIC_BOOST_SCORES[rank]
            existing = self._count_posts_by_detect(name)
            if existing >= self.DYNAMIC_MAX_POSTS:
                continue
            ratio = (self.DYNAMIC_MAX_POSTS - existing) / self.DYNAMIC_MAX_POSTS
            self._dynamic_boosts[name] = int(base * ratio)

    def _count_posts_by_detect(self, boost_name):
        boost = next((b for b in self.MANUAL_BOOSTS if b["name"] == boost_name), None)
        if not boost:
            return 0
        tokens = [t.replace(" ", "").lower() for t in boost.get("keywords", [])]
        count = 0
        for post in self.existing_posts:
            title = str(post.get("title", "")).replace(" ", "").lower()
            if any(t in title for t in tokens):
                count += 1
        return count

    def _count_manual_posts(self, boost):
        tokens = [t.replace(" ", "").lower() for t in boost.get("keywords", [])]
        count = 0
        for post in self.existing_posts:
            title = str(post.get("title", "")).replace(" ", "").lower()
            if any(t in title for t in tokens):
                count += 1
        return count

    def _get_trend_boost(self, keyword):
        kw_norm = str(keyword or "").replace(" ", "").lower()
        total = 0

        for boost in self.MANUAL_BOOSTS:
            tokens = [t.replace(" ", "").lower() for t in boost.get("keywords", [])]
            if any(t in kw_norm for t in tokens):
                existing = self._count_manual_posts(boost)
                if existing < boost["max_posts"]:
                    ratio = (boost["max_posts"] - existing) / boost["max_posts"]
                    total += int(boost["boost"] * ratio)
                break

        for boost_name, score in self._dynamic_boosts.items():
            boost = next((b for b in self.MANUAL_BOOSTS if b["name"] == boost_name), None)
            if not boost:
                continue
            tokens = [t.replace(" ", "").lower() for t in boost.get("keywords", [])]
            if any(t in kw_norm for t in tokens):
                total += score
                break

        return total

    def _is_construction_related(self, keyword):
        kw = str(keyword or "").replace(" ", "")
        return any(anchor.replace(" ", "") in kw for anchor in self.CONSTRUCTION_ANCHORS)

    def _load_history(self):
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {"keywords": [], "topics": {}}
        return {"keywords": [], "topics": {}}

    def _save_history(self, keyword):
        self.history.setdefault("keywords", [])
        self.history.setdefault("topics", {})
        self.history["keywords"].append({"keyword": keyword, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})

        for family, words in self.MAIN_KEYWORDS.items():
            for word in words:
                if word in keyword:
                    key = f"{family}:{word}"
                    self.history["topics"][key] = self.history["topics"].get(key, 0) + 1

        self.history["keywords"] = self.history["keywords"][-200:]
        with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    @retry_request(max_retries=2, delay=1, exceptions=(requests.RequestException,))
    def _fetch_existing_posts(self, config=None):
        posts = []

        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                ct = datetime.fromisoformat(cache.get("timestamp", "2000-01-01"))
                if (datetime.now() - ct).total_seconds() < self.CACHE_EXPIRY_HOURS * 3600:
                    cached = cache.get("posts", [])
                    if cached:
                        posts = cached
                        logger.info(f"cache hit: WP {len(posts)} posts")
            except Exception:
                pass

        if not posts:
            wp_base = ""
            if config and config.get("WP_URL"):
                wp_base = str(config.get("WP_URL", "")).strip()
            elif self.wp_url:
                wp_base = str(self.wp_url).strip()

            if wp_base:
                wp_posts_url = wp_base.rstrip("/")
                if not wp_posts_url.endswith("/posts"):
                    wp_posts_url = f"{wp_posts_url}/posts"

                page = 1
                wp_posts = []
                headers = self.wp_headers if isinstance(self.wp_headers, dict) else {}

                while True:
                    rows = None
                    total_pages = 1
                    for status_value in ("publish,draft,pending", "publish"):
                        res = requests.get(
                            wp_posts_url,
                            params={
                                "per_page": 100,
                                "page": page,
                                "status": status_value,
                                "_fields": "id,title,slug,status",
                            },
                            headers=headers or None,
                            timeout=10,
                        )
                        if res.status_code == 200:
                            rows = res.json()
                            total_pages = int(res.headers.get("X-WP-TotalPages", 1))
                            break
                        if res.status_code in (400, 401, 403):
                            continue
                        rows = []
                        break

                    if rows is None or not rows:
                        break

                    for item in rows:
                        wp_posts.append(
                            {
                                "id": item.get("id"),
                                "title": item.get("title", {}).get("rendered", ""),
                                "slug": item.get("slug", ""),
                                "status": item.get("status", ""),
                                "source": "wordpress",
                            }
                        )

                    if page >= total_pages:
                        break
                    page += 1

                if wp_posts:
                    posts = wp_posts
                    try:
                        with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                            json.dump({"timestamp": datetime.now().isoformat(), "posts": posts}, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.warning(f"WP cache write failed: {e}")

        for item in self.history.get("keywords", []):
            posts.append({"title": item.get("keyword", ""), "source": "history", "date": item.get("date", "")})

        return posts

    def _normalize(self, text):
        return re.sub(r"[^0-9a-zA-Z가-힣]+", "", str(text or "").lower()).strip()

    def _extract_tokens(self, text):
        tokens = set()
        for w in re.findall(r"[0-9a-zA-Z가-힣]{2,}", str(text or "")):
            if w in self.STOPWORDS:
                continue
            tokens.add(w)

        clean = re.sub(r"[^0-9a-zA-Z가-힣]+", "", str(text or ""))
        for n in (2, 3, 4):
            for i in range(max(0, len(clean) - n + 1)):
                g = clean[i : i + n]
                if g and not g.isdigit() and g not in self.STOPWORDS:
                    tokens.add(g)
        return tokens

    def _similarity(self, kw1, kw2):
        n1, n2 = self._normalize(kw1), self._normalize(kw2)
        if not n1 or not n2:
            return 0.0
        if n1 in n2 or n2 in n1:
            return 1.0

        seq = SequenceMatcher(None, n1, n2).ratio()
        t1, t2 = self._extract_tokens(kw1), self._extract_tokens(kw2)
        jac = len(t1 & t2) / len(t1 | t2) if (t1 and t2) else 0.0
        return seq * 0.3 + jac * 0.7

    def _is_duplicate(self, keyword, threshold=0.55):
        best = 0.0
        match = ""
        for post in self.existing_posts:
            title = post.get("title", "")
            if not title:
                continue
            score = self._similarity(keyword, title)
            if score > best:
                best = score
                match = title

        if best >= threshold:
            is_wp = any((p.get("title") == match and p.get("source") == "wordpress") for p in self.existing_posts)
            src = "기존글" if is_wp else "히스토리"
            return True, f"유사도 {best:.0%} ({src}: '{match[:30]}...')", best
        return False, "", best

    @retry_request(max_retries=2, delay=0.5, exceptions=(requests.RequestException,))
    def _get_google(self, q):
        r = requests.get(
            "https://suggestqueries.google.com/complete/search",
            params={"client": "firefox", "hl": "ko", "q": q},
            timeout=3,
        )
        if r.status_code != 200:
            return []
        try:
            data = r.json()
        except ValueError:
            data = json.loads(r.text)
        return data[1] if isinstance(data, list) and len(data) > 1 else []

    @retry_request(max_retries=2, delay=0.5, exceptions=(requests.RequestException,))
    def _get_naver(self, q):
        r = requests.get(
            "https://ac.search.naver.com/nx/ac",
            params={"q": q, "q_enc": "utf-8", "st": "100", "frm": "kin", "r_format": "json"},
            timeout=3,
        )
        if r.status_code != 200:
            return []
        try:
            items = r.json().get("items", [])
        except ValueError:
            return []
        return [row[0] for row in items[0] if row and isinstance(row[0], str)] if items else []

    def _score(self, keyword):
        kw = str(keyword or "")
        score = 50

        if any(x in kw for x in ["절차", "요건", "서류", "비용", "기간", "체크리스트", "주의사항"]):
            score += 20
        if any(x in kw for x in ["신규등록", "양도양수", "기업진단", "실질자본금", "기술인력"]):
            score += 15
        if "2026" in kw:
            score += 10
        if 8 <= len(kw) <= 28:
            score += 8
        elif len(kw) < 6:
            score -= 15

        score += self._get_trend_boost(kw)

        for family, words in self.MAIN_KEYWORDS.items():
            for w in words:
                if w in kw:
                    score -= self.history.get("topics", {}).get(f"{family}:{w}", 0) * 6

        return score

    def mine_hot_keyword(self, config=None):
        logger.info("🛰 [TrendRadar v2] 키워드 스캔 시작")
        self.existing_posts = self._fetch_existing_posts(config)

        seeds = self._generate_search_seeds(count=35)
        candidates = set()
        for seed in seeds:
            try:
                candidates.update(self._get_google(seed))
                candidates.update(self._get_naver(seed))
            except Exception:
                pass
            time.sleep(0.12)

        self._detect_dynamic_trends(candidates)

        ranked = []
        for kw in candidates:
            if len(kw) < 4 or len(kw) > 40:
                continue
            if not self._is_construction_related(kw):
                continue
            dup, _reason, sim = self._is_duplicate(kw)
            if dup:
                continue
            ranked.append((kw, self._score(kw) - int(sim * 30), sim))

        ranked.sort(key=lambda x: x[1], reverse=True)
        if not ranked:
            logger.warning("⚠ 발행 가능한 키워드가 없습니다")
            return None

        final = ranked[0][0]
        self._save_history(final)
        logger.info(f"🎯 최종 키워드: {final}")
        return final

    def get_top_keywords(self, count=10, config=None):
        self.existing_posts = self._fetch_existing_posts(config)
        seeds = self._generate_search_seeds(count=25)

        candidates = set()
        for seed in seeds:
            try:
                candidates.update(self._get_google(seed))
                candidates.update(self._get_naver(seed))
            except Exception as e:
                logger.debug(f"suggest fetch skipped for seed '{seed}': {e}")
            time.sleep(0.08)

        self._detect_dynamic_trends(candidates)

        ranked = []
        for kw in candidates:
            if len(kw) < 4 or len(kw) > 40:
                continue
            if not self._is_construction_related(kw):
                continue
            dup, _reason, sim = self._is_duplicate(kw)
            if dup:
                continue
            ranked.append((kw, self._score(kw) - int(sim * 30)))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in ranked[:count]]
