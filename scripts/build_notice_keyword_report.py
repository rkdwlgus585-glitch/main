import argparse
import json
import re
import sys
from collections import OrderedDict
from datetime import date
from pathlib import Path
from typing import Dict, List

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_ALL_ROOT = ROOT.parent / "ALL"                    # H:\ALL (non-core modules)
if str(_ALL_ROOT) not in sys.path:
    sys.path.insert(0, str(_ALL_ROOT))

from trend_radar_v2 import TrendRadarV2

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
COMPACT_RE = re.compile(r"[^0-9A-Za-z가-힣]+")

THEME_SEEDS = OrderedDict(
    [
        ("market_report", ["건설업 시장 리포트", "건설업 경기 전망", "건설업 상반기 전망"]),
        ("license_transfer", ["건설업 양도양수", "건설면허 양도양수", "전문건설업 양도양수"]),
        ("new_registration", ["건설업 신규등록", "건설업 등록기준", "건설업 기술인력"]),
        ("capital_diagnosis", ["건설업 기업진단", "건설업 실질자본금", "건설업 기업진단지침"]),
        ("performance_bidding", ["건설업 시공능력평가", "건설업 입찰", "건설업 공공 발주"]),
        ("merger_split", ["건설업 분할합병", "건설업 실적 이전", "건설업 구조 재편"]),
        ("compliance_risk", ["건설업 행정처분", "건설업 실태조사", "건설업 등록말소"]),
    ]
)

MONTH_THEME_ORDER = [
    "market_report",
    "license_transfer",
    "new_registration",
    "capital_diagnosis",
    "performance_bidding",
    "market_report",
    "license_transfer",
    "merger_split",
    "compliance_risk",
    "license_transfer",
    "new_registration",
    "market_report",
]

THEME_LABELS = {
    "market_report": "시장 리포트 / 경기 전망",
    "license_transfer": "양도양수 / 실사 / 빠른 진입",
    "new_registration": "신규등록 / 등록기준 / 인력",
    "capital_diagnosis": "기업진단 / 실질자본금",
    "performance_bidding": "입찰 / 실적 / 시공능력평가",
    "merger_split": "분할합병 / 구조 재편 / 실적 이전",
    "compliance_risk": "준법 / 행정처분 / 유지 리스크",
}

INTENT_HINTS = {
    "market_report": "정보 탐색형 + 경영 판단형",
    "license_transfer": "비교 검토형 + 상담 전환형",
    "new_registration": "절차 탐색형 + 준비 서류형",
    "capital_diagnosis": "문제 해결형 + 실무 기준형",
    "performance_bidding": "실무 준비형 + 입찰 대응형",
    "merger_split": "구조 설계형 + 고관여 상담형",
    "compliance_risk": "리스크 점검형 + 예방 상담형",
}

CONSTRUCTION_ANCHORS = (
    "건설업",
    "전문건설업",
    "종합건설업",
    "건설면허",
    "건설기술인",
    "시공능력",
    "입찰",
    "기업진단",
    "실질자본금",
    "양도양수",
    "분할합병",
    "공공 발주",
    "공공발주",
    "등록말소",
    "행정처분",
    "실태조사",
)

NOISE_TOKENS = (
    "자동차",
    "하이패스",
    "수영장",
    "잠실",
    "올림픽",
    "영어로",
    "등기촉탁",
    "출생신고",
    "혼인신고",
    "등록기준지",
    "본적",
    "농업경영체",
    "가족관계",
    "주민등록",
)

THEME_RULES = {
    "market_report": {
        "required": ("시장", "경기", "전망", "리포트", "동향", "판세", "수주"),
        "bonus": ("전망", "시장", "리포트", "동향", "수주"),
    },
    "license_transfer": {
        "required": ("양도양수", "면허양도", "면허 양도"),
        "bonus": ("양도양수", "실사", "계약", "프리미엄", "권리의무"),
    },
    "new_registration": {
        "required": ("신규등록", "등록기준", "기술인력"),
        "bonus": ("신규등록", "등록기준", "기술인력", "자본금", "준비서류"),
    },
    "capital_diagnosis": {
        "required": ("기업진단", "실질자본금", "출자좌수", "공제조합"),
        "bonus": ("기업진단", "실질자본금", "기업진단지침", "출자좌수", "진단보고서"),
    },
    "performance_bidding": {
        "required": ("입찰", "시공능력", "실적", "공공발주", "공공 발주"),
        "bonus": ("입찰", "참가자격", "시공능력", "실적", "평가"),
    },
    "merger_split": {
        "required": ("분할합병", "실적이전", "실적 이전", "구조재편", "법인전환"),
        "bonus": ("분할합병", "실적이전", "구조재편", "법인전환"),
    },
    "compliance_risk": {
        "required": ("행정처분", "실태조사", "등록말소", "영업정지"),
        "bonus": ("행정처분", "실태조사", "등록말소", "영업정지", "소명", "리스크"),
    },
}


def _month_iter(start_month: date, count: int) -> List[date]:
    out: List[date] = []
    year = int(start_month.year)
    month = int(start_month.month)
    for _ in range(max(1, int(count))):
        out.append(date(year, month, 1))
        month += 1
        if month > 12:
            year += 1
            month = 1
    return out


def _normalize_space(text: str) -> str:
    return SPACE_RE.sub(" ", str(text or "")).strip()


def _compact(text: str) -> str:
    return COMPACT_RE.sub("", str(text or ""))


def _fetch_notice(url: str) -> Dict[str, str]:
    res = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 (compatible; SeoulMNA-NoticeKeywordReport/2.0)"},
    )
    res.raise_for_status()
    html = res.text or ""
    title_match = TITLE_RE.search(html)
    title = _normalize_space(TAG_RE.sub(" ", title_match.group(1))) if title_match else ""
    text = _normalize_space(TAG_RE.sub(" ", html))
    return {"title": title, "text": text, "html": html}


def _verify_notice_positioning(title: str, text: str) -> Dict[str, object]:
    title_compact = _compact(title)
    text_compact = _compact(text)
    checks = OrderedDict(
        [
            ("title_market_report", "2026년2월건설업시장리포트" in title_compact),
            ("problem_statement", "수주는움직이는데왜현장은체감이없을까" in title_compact or "수주는움직이는데왜현장은체감이없을까" in text_compact),
            ("market_report_phrase", "시장리포트" in title_compact or "시장리포트" in text_compact),
            ("transfer_option", "양도양수" in text_compact),
            ("new_registration_option", "신규등록" in text_compact),
            ("merger_option", "분할합병" in text_compact),
        ]
    )
    is_verified = all(bool(v) for v in checks.values())
    summary = (
        "2월 시장 리포트형 글로 확인되며, 체감 경기 문제제기 뒤에 양도양수/신규등록/분할합병 선택지로 연결되는 구조"
        if is_verified
        else "공지 페이지는 2월 시장 리포트 성격은 확인되지만, 일부 핵심 시그널이 자동 검증에서 누락됨"
    )
    return {"verified": is_verified, "checks": checks, "summary": summary}


def _is_construction_keyword(keyword: str) -> bool:
    src = _normalize_space(keyword)
    if not src:
        return False
    if any(token in src for token in NOISE_TOKENS):
        return False
    return any(anchor in src for anchor in CONSTRUCTION_ANCHORS)


def _keyword_matches_theme(keyword: str, theme_key: str) -> bool:
    src = _normalize_space(keyword)
    if not _is_construction_keyword(src):
        return False
    rules = THEME_RULES.get(theme_key, {})
    required = rules.get("required", ())
    return any(token in src for token in required)


def _score_live_keyword(keyword: str, theme_key: str, channels: List[str], seed_hits: List[str], hit_count: int) -> int:
    src = _normalize_space(keyword)
    score = 40
    score += len(channels) * 12
    score += len(seed_hits) * 6
    score += int(hit_count) * 4
    if src.startswith("건설업") or src.startswith("전문건설업") or src.startswith("건설면허"):
        score += 10
    if 8 <= len(src) <= 26:
        score += 8
    rules = THEME_RULES.get(theme_key, {})
    for token in rules.get("bonus", ()):
        if token in src:
            score += 6
    if "2026" in src or "최신" in src:
        score += 4
    return score


def _serialize_ranked_entries(theme_key: str, bucket: Dict[str, Dict[str, object]]) -> List[Dict[str, object]]:
    ranked: List[Dict[str, object]] = []
    for keyword, entry in bucket.items():
        channels = sorted(entry.get("channels", set()))
        seed_hits = sorted(entry.get("seed_hits", set()))
        hit_count = int(entry.get("hit_count", 0) or 0)
        ranked.append(
            {
                "keyword": keyword,
                "channels": channels,
                "seed_hits": seed_hits,
                "hit_count": hit_count,
                "score": _score_live_keyword(keyword, theme_key, channels, seed_hits, hit_count),
            }
        )
    ranked.sort(key=lambda row: (-int(row["score"]), -len(row["channels"]), -len(row["seed_hits"]), len(str(row["keyword"]))))
    return ranked


def _collect_live_snapshot() -> Dict[str, object]:
    radar = TrendRadarV2()
    raw_suggestions: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
    theme_rankings: Dict[str, List[Dict[str, object]]] = {}
    overall_map: Dict[str, Dict[str, object]] = {}

    for theme_key, seeds in THEME_SEEDS.items():
        raw_suggestions[theme_key] = {}
        bucket: Dict[str, Dict[str, object]] = {}
        for seed in seeds:
            google: List[str] = []
            naver: List[str] = []
            try:
                google = [_normalize_space(row) for row in radar._get_google(seed) if _normalize_space(row)]
            except Exception:
                google = []
            try:
                naver = [_normalize_space(row) for row in radar._get_naver(seed) if _normalize_space(row)]
            except Exception:
                naver = []
            raw_suggestions[theme_key][seed] = {"google": google[:8], "naver": naver[:8]}

            for channel, rows in (("google", google), ("naver", naver)):
                for keyword in rows:
                    if not _keyword_matches_theme(keyword, theme_key):
                        continue
                    entry = bucket.setdefault(
                        keyword,
                        {"channels": set(), "seed_hits": set(), "hit_count": 0},
                    )
                    entry["channels"].add(channel)
                    entry["seed_hits"].add(seed)
                    entry["hit_count"] = int(entry.get("hit_count", 0) or 0) + 1

        if not bucket:
            for seed in seeds:
                if _keyword_matches_theme(seed, theme_key):
                    bucket[seed] = {"channels": set(), "seed_hits": {seed}, "hit_count": 0}

        ranked = _serialize_ranked_entries(theme_key, bucket)
        theme_rankings[theme_key] = ranked[:8]

        for row in theme_rankings[theme_key][:5]:
            keyword = str(row["keyword"])
            entry = overall_map.setdefault(
                keyword,
                {"keyword": keyword, "themes": set(), "channels": set(), "seed_hits": set(), "score": 0},
            )
            entry["themes"].add(theme_key)
            entry["channels"].update(row.get("channels", []))
            entry["seed_hits"].update(row.get("seed_hits", []))
            entry["score"] = max(int(entry["score"]), int(row["score"]))

    overall_ranked: List[Dict[str, object]] = []
    for row in overall_map.values():
        overall_ranked.append(
            {
                "keyword": row["keyword"],
                "themes": [THEME_LABELS[key] for key in sorted(row["themes"])],
                "channels": sorted(row["channels"]),
                "seed_hits": sorted(row["seed_hits"]),
                "score": int(row["score"]) + len(row["themes"]) * 4 + len(row["channels"]) * 3,
            }
        )
    overall_ranked.sort(key=lambda item: (-int(item["score"]), -len(item["themes"]), len(str(item["keyword"]))))

    return {
        "selection_basis": "발행 직전 건설업 관련 실시간 Naver/Google suggestion snapshot",
        "raw_suggestions": raw_suggestions,
        "theme_rankings": theme_rankings,
        "overall_ranked": overall_ranked[:15],
    }


def _dedupe_keywords(rows: List[str], *, exclude: str = "", limit: int = 4) -> List[str]:
    out: List[str] = []
    seen = set()
    blocked = _normalize_space(exclude)
    for row in rows:
        norm = _normalize_space(row)
        if not norm or norm == blocked or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
        if len(out) >= max(0, int(limit)):
            break
    return out


def _build_month_rows(start_month: date, months: int, theme_rankings: Dict[str, List[Dict[str, object]]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    schedule = _month_iter(start_month, months)
    for idx, month_row in enumerate(schedule):
        theme_key = MONTH_THEME_ORDER[idx % len(MONTH_THEME_ORDER)]
        ranking = theme_rankings.get(theme_key, [])
        primary = ranking[0]["keyword"] if ranking else THEME_SEEDS[theme_key][0]
        supporting_candidates = [row["keyword"] for row in ranking[1:8]]
        supporting_candidates.extend(THEME_SEEDS[theme_key])
        supporting = _dedupe_keywords(supporting_candidates, exclude=str(primary), limit=4)
        rows.append(
            {
                "month": month_row.strftime("%Y-%m"),
                "theme_key": theme_key,
                "theme_label": THEME_LABELS[theme_key],
                "search_intent": INTENT_HINTS[theme_key],
                "current_live_primary_candidate": primary,
                "current_live_supporting_candidates": supporting,
                "publication_rule": "해당 월 리포트 작성 직전에 실시간 snapshot을 재수집하고, 그 시점 top 1 + supporting 3~4개로 제목/본문을 확정",
            }
        )
    return rows


def _render_markdown(
    notice_url: str,
    notice_title: str,
    notice_verification: Dict[str, object],
    live_snapshot: Dict[str, object],
    month_rows: List[Dict[str, object]],
) -> str:
    lines: List[str] = []
    lines.append("# 월별 네이버/구글 상단 노출 키워드 리포트")
    lines.append("")
    lines.append(f"- 기준 공지: {notice_title}")
    lines.append(f"- URL: {notice_url}")
    lines.append(f"- 생성일: {date.today().isoformat()}")
    lines.append(f"- 키워드 선정 기준: {live_snapshot.get('selection_basis', '')}")
    lines.append("")
    lines.append("## notice/346 검증")
    lines.append("")
    lines.append(f"- 판정: {'verified' if notice_verification.get('verified') else 'needs-review'}")
    lines.append(f"- 해석: {notice_verification.get('summary', '')}")
    for name, ok in (notice_verification.get("checks", {}) or {}).items():
        lines.append(f"- {name}: {'ok' if ok else 'miss'}")
    lines.append("")
    lines.append("## 현재 실시간 상단 노출 후보")
    lines.append("")
    for row in live_snapshot.get("overall_ranked", [])[:12]:
        themes = ", ".join(row.get("themes", [])) or "-"
        channels = ", ".join(row.get("channels", [])) or "-"
        lines.append(f"- `{row.get('keyword', '')}` | theme={themes} | channel={channels} | score={row.get('score', 0)}")
    lines.append("")
    lines.append("## 주제별 실시간 후보")
    lines.append("")
    raw_suggestions = live_snapshot.get("raw_suggestions", {}) or {}
    theme_rankings = live_snapshot.get("theme_rankings", {}) or {}
    for theme_key, seeds in THEME_SEEDS.items():
        lines.append(f"### {THEME_LABELS[theme_key]}")
        top_rows = theme_rankings.get(theme_key, [])[:5]
        if top_rows:
            for row in top_rows:
                lines.append(
                    f"- `{row.get('keyword', '')}` | channel={', '.join(row.get('channels', [])) or '-'} | seed={', '.join(row.get('seed_hits', [])) or '-'} | score={row.get('score', 0)}"
                )
        else:
            lines.append("- 실시간 후보 없음")
        for seed in seeds:
            channels = raw_suggestions.get(theme_key, {}).get(seed, {})
            lines.append(f"- seed `{seed}`")
            lines.append(f"  Google: {', '.join(channels.get('google', [])[:4]) or '-'}")
            lines.append(f"  Naver: {', '.join(channels.get('naver', [])[:4]) or '-'}")
        lines.append("")
    lines.append("## 월별 운용 플랜")
    lines.append("")
    for row in month_rows:
        lines.append(f"### {row['month']} | {row['theme_label']}")
        lines.append(f"- 검색 의도: {row['search_intent']}")
        lines.append(f"- 현재 snapshot 기준 대표 후보: {row['current_live_primary_candidate']}")
        lines.append(
            f"- 현재 snapshot 기준 보조 후보: {', '.join(row['current_live_supporting_candidates']) if row['current_live_supporting_candidates'] else '-'}"
        )
        lines.append(f"- 실행 규칙: {row['publication_rule']}")
        lines.append("")
    lines.append("## 운용 메모")
    lines.append("")
    lines.append("- 월별 리포트의 대표 키워드는 미리 고정하지 않고, 발행 직전 실시간 snapshot으로 다시 뽑아야 합니다.")
    lines.append("- `notice/346`은 2월 시장 리포트형 기준 페이지로만 사용하고, 키워드 source of truth는 항상 발행 시점의 live snapshot입니다.")
    lines.append("- 제목은 `대표 키워드 1개`를 앞쪽에 배치하고, 본문에는 supporting 3~4개를 자연스럽게 분산 배치하는 방식이 안전합니다.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a monthly keyword report from a notice page and a live construction-keyword snapshot."
    )
    parser.add_argument("--notice-url", required=True)
    parser.add_argument("--start-month", default=date.today().strftime("%Y-%m"))
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--out-md", default="logs/monthly_notice_keyword_report_latest.md")
    parser.add_argument("--out-json", default="logs/monthly_notice_keyword_report_latest.json")
    args = parser.parse_args()

    start_month = date.fromisoformat(f"{str(args.start_month).strip()}-01")
    notice = _fetch_notice(str(args.notice_url).strip())
    notice_verification = _verify_notice_positioning(notice.get("title", ""), notice.get("text", ""))
    live_snapshot = _collect_live_snapshot()
    month_rows = _build_month_rows(
        start_month=start_month,
        months=int(args.months),
        theme_rankings=live_snapshot.get("theme_rankings", {}) or {},
    )

    payload = {
        "generated_at": date.today().isoformat(),
        "notice_url": str(args.notice_url).strip(),
        "notice_title": notice.get("title", ""),
        "notice_verification": {
            "verified": bool(notice_verification.get("verified")),
            "summary": notice_verification.get("summary", ""),
            "checks": dict(notice_verification.get("checks", {})),
        },
        "live_snapshot": live_snapshot,
        "monthly_plan": month_rows,
    }

    out_json = (ROOT / str(args.out_json)).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    out_md = (ROOT / str(args.out_md)).resolve()
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(
        _render_markdown(
            notice_url=str(args.notice_url).strip(),
            notice_title=notice.get("title", ""),
            notice_verification=notice_verification,
            live_snapshot=live_snapshot,
            month_rows=month_rows,
        ),
        encoding="utf-8",
    )

    print(f"[saved] {out_md}")
    print(f"[saved] {out_json}")
    print(
        f"[summary] verified={bool(notice_verification.get('verified'))} "
        f"overall_live={len(live_snapshot.get('overall_ranked', []))} months={len(month_rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
