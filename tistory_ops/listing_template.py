from __future__ import annotations

import html
import re
import urllib.parse
from datetime import datetime
from typing import Any


def _pick(dct: dict[str, Any], keys: list[str], default: Any = "") -> Any:
    src = dct if isinstance(dct, dict) else {}
    for key in keys:
        if key in src:
            value = src.get(key)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
    return default


def _as_lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    return [x.strip() for x in text.split("\n") if x.strip()]


def _to_text(value: Any, default: str = "-") -> str:
    src = str(value or "").strip()
    return src if src else default


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _sales_value(sales: dict[str, Any], year: int) -> str:
    wanted = str(year)
    for key, val in (sales or {}).items():
        if _digits(key)[:4] == wanted:
            return _to_text(val, "-")
    return "-"


def _sum_if_blank(value: Any, sales: dict[str, Any], years: list[int]) -> str:
    txt = str(value or "").strip()
    if txt and txt not in {"-", "--"}:
        return txt
    total = 0.0
    found = False
    for year in years:
        raw = _sales_value(sales, year)
        m = re.search(r"-?\d+(?:\.\d+)?", raw.replace(",", ""))
        if not m:
            continue
        total += float(m.group(0))
        found = True
    if not found:
        return "-"
    if abs(total - round(total)) < 1e-9:
        return str(int(round(total)))
    return f"{total:.1f}"


def _extract_financial_ratio(note_lines: list[str], token: str) -> str:
    pat = re.compile(rf"{re.escape(token)}\s*[:：]?\s*([0-9]+(?:\.[0-9]+)?)\s*%")
    for line in note_lines:
        m = pat.search(str(line))
        if m:
            return f"{m.group(1)}%"
    return "-"


def _extract_first_match(note_lines: list[str], patterns: list[str]) -> str:
    for line in note_lines:
        for pattern in patterns:
            if re.search(pattern, str(line), flags=re.I):
                return str(line).strip()
    return "-"


def _escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _industry_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _pick(data, ["업종정보", "industry_rows", "rows", "?낆쥌?뺣낫"], [])
    return rows if isinstance(rows, list) else []


_INDUSTRY_ALIAS_TO_OFFICIAL = {
    "토목": "토목공사업",
    "건축": "건축공사업",
    "토건": "토목건축공사업",
    "상하": "상하수도설비공사업",
    "상하수도": "상하수도설비공사업",
    "상하수도설비": "상하수도설비공사업",
    "조경": "조경공사업",
    "실내": "실내건축공사업",
    "철콘": "철근·콘크리트공사업",
    "도장": "도장공사업",
    "습방": "습식·방수공사업",
    "습식방수": "습식·방수공사업",
    "석공": "석공사업",
    "비계": "비계·구조물해체공사업",
    "구조물해체": "비계·구조물해체공사업",
    "석면": "석면해체·제거공사업",
    "금속": "금속창호·지붕건축물조립공사업",
    "금속창호": "금속창호·지붕건축물조립공사업",
    "지붕판금": "금속창호·지붕건축물조립공사업",
    "기계설비": "기계설비·가스공사업",
    "가스시설": "기계설비·가스공사업",
    "난방": "기계설비·가스공사업",
    "전기": "전기공사업",
    "통신": "정보통신공사업",
    "소방": "소방시설공사업",
    "포장": "포장공사업",
    "철도궤도": "철도·궤도공사업",
    "수중": "수중·준설공사업",
    "준설": "수중·준설공사업",
    "삭도": "삭도설치공사업",
    "보링": "보링·그라우팅·파일공사업",
    "그라우팅": "보링·그라우팅·파일공사업",
    "파일": "보링·그라우팅·파일공사업",
    "철강": "철강구조물공사업",
}

_FORMAL_INDUSTRY_HINTS = ("공사업", "유지관리업", "설치공사업")
_INDUSTRY_ALIAS_SORTED = sorted(_INDUSTRY_ALIAS_TO_OFFICIAL.keys(), key=len, reverse=True)


def _normalize_industry_token(value: Any) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", str(value or "").strip().lower())


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = re.sub(r"\s+", "", str(item or "").lower())
        if (not key) or (key in seen):
            continue
        seen.add(key)
        out.append(item)
    return out


def _expand_industry_name(name: Any) -> str:
    raw = _to_text(name, "-")
    if raw in {"", "-"}:
        return "-"
    if any(hint in raw for hint in _FORMAL_INDUSTRY_HINTS):
        return raw

    normalized = _normalize_industry_token(raw)
    if not normalized:
        return raw
    direct = _INDUSTRY_ALIAS_TO_OFFICIAL.get(normalized)
    if direct:
        return direct

    parts = [x for x in re.split(r"[+/,&|]|\s+", raw.replace("·", " ").replace("ㆍ", " ")) if str(x).strip()]
    expanded_parts: list[str] = []
    for part in parts:
        token = _normalize_industry_token(part)
        if not token:
            continue
        expanded = _INDUSTRY_ALIAS_TO_OFFICIAL.get(token)
        if expanded:
            expanded_parts.append(expanded)
    expanded_parts = _dedupe_keep_order(expanded_parts)
    if expanded_parts:
        return " / ".join(expanded_parts)

    hits: list[tuple[int, str]] = []
    for alias in _INDUSTRY_ALIAS_SORTED:
        if len(alias) < 2:
            continue
        pos = normalized.find(alias)
        if pos >= 0:
            hits.append((pos, _INDUSTRY_ALIAS_TO_OFFICIAL[alias]))
    if hits:
        hits.sort(key=lambda x: x[0])
        return " / ".join(_dedupe_keep_order([x[1] for x in hits]))
    return raw


def _listing_detail_url(registration_no: str) -> str:
    uid = _digits(registration_no)
    return f"https://seoulmna.co.kr/mna/{uid}" if uid else "https://seoulmna.co.kr/mna"


def _primary_industry_name(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "건설업"
    raw = _to_text(_pick(rows[0], ["업종", "industry", "?낆쥌"], "건설업"))
    return _expand_industry_name(raw)


def _extract_float(value: Any) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", str(value or "").replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _build_sales_commentary(rows: list[dict[str, Any]]) -> list[str]:
    comments: list[str] = []
    for row in rows[:3]:
        raw_name = _to_text(_pick(row, ["업종", "industry", "?낆쥌"], "업종"))
        name = _expand_industry_name(raw_name)
        sales = _pick(row, ["매출", "sales", "留ㅼ텧"], {})
        y23 = _extract_float(_sales_value(sales, 2023))
        y24 = _extract_float(_sales_value(sales, 2024))
        y25 = _extract_float(_sales_value(sales, 2025))
        trend = "추세 판단 보류"
        if y24 is not None and y25 is not None:
            if y25 > y24:
                trend = "최근 매출이 증가 추세"
            elif y25 < y24:
                trend = "최근 매출이 조정 구간"
            else:
                trend = "최근 매출이 보합 추세"
        elif y23 is not None and y24 is not None:
            if y24 > y23:
                trend = "직전 연도 대비 개선"
            elif y24 < y23:
                trend = "직전 연도 대비 감소"
            else:
                trend = "직전 연도와 유사"

        sum3 = _sum_if_blank(_pick(row, ["3년합계", "sum3", "3?꾪빀怨?"], "-"), sales, [2023, 2024, 2025])
        comments.append(f"{name}: 3년 합계 {sum3} 기준으로 {trend}입니다.")
    if not comments:
        comments.append("매출 데이터가 제한적이어서 보수적으로 검토가 필요합니다.")
    return comments


def _svg_data_uri(title: str, lines: list[str], accent: str = "#003764") -> str:
    safe_title = _escape(title)[:42]
    safe_lines = [(_escape(x)[:54]) for x in lines[:5]]
    text_rows = []
    # Keep body text well below the header bar to avoid overlap/clipping.
    y = 170
    for line in safe_lines:
        text_rows.append(
            f"<text x='40' y='{y}' font-size='26' fill='#1f2937' font-family='Malgun Gothic, Arial'>{line}</text>"
        )
        y += 52
    rows_html = "".join(text_rows)
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='700' viewBox='0 0 1200 700'>"
        "<rect width='1200' height='700' fill='#f8fbff'/>"
        f"<rect x='0' y='0' width='1200' height='84' fill='{accent}'/>"
        f"<text x='40' y='54' font-size='34' fill='white' font-family='Malgun Gothic, Arial' font-weight='700'>{safe_title}</text>"
        "<rect x='30' y='110' width='1140' height='560' rx='16' fill='white' stroke='#dbe7ff' stroke-width='2'/>"
        f"{rows_html}"
        "</svg>"
    )
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg, safe="")


def _remote_placeholder_image_url(title: str, lines: list[str], bg: str, fg: str) -> str:
    bg_hex = re.sub(r"[^0-9a-fA-F]", "", str(bg or ""))[:6] or "003764"
    fg_hex = re.sub(r"[^0-9a-fA-F]", "", str(fg or ""))[:6] or "ffffff"
    reg = _digits(title)
    head = f"SEOUL CONSTRUCTION INFO {reg}" if reg else "SEOUL CONSTRUCTION INFO"
    tail = "FINANCIAL CHECK" if ("재무" in str(title or "")) else "LISTING SUMMARY"
    text = f"{head}\n{tail}"
    return f"https://dummyimage.com/1200x520/{bg_hex}/{fg_hex}.png&text={urllib.parse.quote_plus(text)}"


def _extract_image_urls(data: dict[str, Any], limit: int = 2) -> list[str]:
    src = data if isinstance(data, dict) else {}
    candidates = [
        "image_urls",
        "images",
        "image",
        "photo_urls",
        "photos",
        "photo",
        "img_urls",
        "img",
        "thumbnail",
        "thumbnail_url",
        "?????",
        "???",
        "??",
    ]
    out: list[str] = []
    for key in candidates:
        raw = src.get(key)
        if raw is None:
            continue
        if isinstance(raw, list):
            values = [str(x).strip() for x in raw if str(x).strip()]
        else:
            values = re.findall(r"https?://[^\s,'\"<>]+", str(raw))
            if (not values) and str(raw).strip().startswith(("http://", "https://")):
                values = [str(raw).strip()]
        for url in values:
            if not re.match(r"^https?://", url, flags=re.I):
                continue
            out.append(url)
            if len(out) >= max(0, int(limit)):
                return out
    return out


def build_auto_image_urls(data: dict[str, Any], max_images: int = 2) -> list[str]:
    src = data if isinstance(data, dict) else {}
    reg = _to_text(_pick(src, ["????", "registration_no", "registration", "??????"], ""))
    rows = _industry_rows(src)
    main_name = _primary_industry_name(rows)
    debt = _to_text(_pick(src, ["????", "debt_ratio"], "-"))
    current = _to_text(_pick(src, ["????", "current_ratio"], "-"))
    founded = _to_text(_pick(src, ["?????", "?????", "founded", "founded_year"], "-"))

    cap = max(0, int(max_images))
    if cap <= 0:
        return []

    # Prefer explicit listing photos when provided by upstream data.
    explicit_images = _extract_image_urls(src, limit=cap)
    if explicit_images:
        return explicit_images[:cap]

    lines_1 = [
        f"???? {reg}",
        f"?? ?? {main_name}",
        "?? ?? ?? ??",
        f"???? {founded}",
        "???? ?? ?? ??",
    ]
    lines_2 = [
        f"???? {debt}",
        f"???? {current}",
        _build_sales_commentary(rows)[0],
        datetime.now().strftime("??? %Y-%m-%d"),
    ]
    # Tistory post rendering may block/sanitize data URI images.
    # Use regular HTTPS image URLs for compatibility.
    urls = [
        _remote_placeholder_image_url(f"?? ?? {reg} ??", lines_1, bg="#003764", fg="#ffffff"),
        _remote_placeholder_image_url(f"?? {reg} ????? ???", lines_2, bg="#b0894f", fg="#102a43"),
    ]
    return urls[:cap]


def build_listing_title(data: dict[str, Any]) -> str:
    reg = _to_text(_pick(data, ["등록번호", "registration_no", "registration", "?깅줉踰덊샇"], ""), "")
    rows = _industry_rows(data)
    names = []
    seen = set()
    for row in rows:
        raw_name = _to_text(_pick(row, ["업종", "industry", "?낆쥌"], ""), "")
        name = _expand_industry_name(raw_name)
        if not name:
            continue
        key = re.sub(r"\s+", "", name.lower())
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    head = " / ".join(names[:2]) if names else "건설업"
    if reg:
        return f"건설업 양도양수 매물 {reg} | {head} | 재무·매출 해설"
    return f"건설업 양도양수 | {head} | 재무·매출 해설"


def build_listing_content(data: dict[str, Any], source_url: str = "", image_urls: list[str] | None = None) -> str:
    src = data if isinstance(data, dict) else {}
    reg = _to_text(_pick(src, ["등록번호", "registration_no", "registration", "?깅줉踰덊샇"], ""))
    status = _to_text(_pick(src, ["상태", "status"], "가능"))
    founded = _to_text(_pick(src, ["법인설립일", "법인설립년", "founded", "founded_year", "踰뺤씤?ㅻ┰??"], "-"))
    capital = _to_text(_pick(src, ["자본금", "capital", "?먮낯湲?"], "-"))
    company_type = _to_text(_pick(src, ["회사형태", "company_type", "?뚯궗?뺥깭"], "-"))
    location = _to_text(_pick(src, ["소재지", "location", "?뚯옱吏"], "-"))
    assoc = _to_text(_pick(src, ["협회가입", "association", "?묓쉶媛??"], "-"))
    shares = _to_text(_pick(src, ["공제조합출자좌", "공제조합출자좌수", "shares", "怨듭젣議고빀異쒖옄醫뚯닔"], "-"))
    balance = _to_text(_pick(src, ["공제잔액", "공제조합잔액", "balance", "怨듭젣議고빀?붿븸"], "-"))
    loan_balance = _to_text(_pick(src, ["대출후 남은잔액", "loan_balance"], "-"))

    notes = _as_lines(_pick(src, ["비고", "notes", "鍮꾧퀬"], []))
    admin_notes = _as_lines(_pick(src, ["행정사항", "admin_notes", "?됱젙?ы빆"], []))
    all_notes = notes + [x for x in admin_notes if x not in notes]

    debt_ratio = _to_text(_pick(src, ["부채비율", "debt_ratio"], _extract_financial_ratio(all_notes, "부채")))
    current_ratio = _to_text(_pick(src, ["유동비율", "current_ratio"], _extract_financial_ratio(all_notes, "유동")))
    admin_status = _to_text(
        _pick(
            src,
            ["행정처분", "admin_disposition"],
            _extract_first_match(all_notes, [r"행정처분", r"처분"]),
        )
    )
    admin_detail = _to_text(_pick(src, ["처분내용", "admin_disposition_detail"], "-"))
    coop_credit = _to_text(_pick(src, ["조합신용", "coop_credit"], _extract_first_match(all_notes, [r"조합.*등급", r"조합신용"])))
    ext_credit = _to_text(_pick(src, ["외부신용", "external_credit"], _extract_first_match(all_notes, [r"외부신용", r"신용등급"])))
    retained = _to_text(_pick(src, ["이익잉여금", "retained_earnings"], _extract_first_match(all_notes, [r"잉여금"])))
    deficit = _to_text(_pick(src, ["결손금", "deficit"], _extract_first_match(all_notes, [r"결손"])))

    rows = _industry_rows(src)
    sales_table_rows = []
    for row in rows:
        sales = _pick(row, ["매출", "sales", "留ㅼ텧"], {})
        sum3 = _sum_if_blank(_pick(row, ["3년합계", "sum3", "3?꾪빀怨?"], "-"), sales, [2023, 2024, 2025])
        sum5 = _sum_if_blank(_pick(row, ["5년합계", "sum5", "5?꾪빀怨?"], "-"), sales, [2021, 2022, 2023, 2024, 2025])
        sales_table_rows.append(
            {
                "industry": _expand_industry_name(_pick(row, ["업종", "industry", "?낆쥌"], "-")),
                "license_year": _to_text(_pick(row, ["면허년도", "license_year", "硫댄뿀?꾨룄"], "-")),
                "capacity": _to_text(_pick(row, ["시공능력", "시공능력평가", "시공능력평가액", "capacity", "?쒓났?λ젰?됯???"], "-")),
                "y20": _sales_value(sales, 2020),
                "y21": _sales_value(sales, 2021),
                "y22": _sales_value(sales, 2022),
                "y23": _sales_value(sales, 2023),
                "y24": _sales_value(sales, 2024),
                "y25": _sales_value(sales, 2025),
                "sum3": sum3,
                "sum5": sum5,
            }
        )

    if not sales_table_rows:
        sales_table_rows.append(
            {
                "industry": "-",
                "license_year": "-",
                "capacity": "-",
                "y20": "-",
                "y21": "-",
                "y22": "-",
                "y23": "-",
                "y24": "-",
                "y25": "-",
                "sum3": "-",
                "sum5": "-",
            }
        )

    detail_url = _listing_detail_url(reg)
    escaped_notes = "".join([f"<li>{_escape(line)}</li>" for line in all_notes]) or "<li>특이사항 없음</li>"

    effective_images = [str(x).strip() for x in (image_urls or []) if str(x).strip()]
    image_cards: list[str] = []
    for idx, url in enumerate(effective_images[:2], start=1):
        alt = f"\uB9E4\uBB3C {reg} {idx}\uBC88 \uBD84\uC11D \uC774\uBBF8\uC9C0"
        image_cards.append(
            "<div style='flex:1 1 320px;min-width:260px;background:#ffffff;border:1px solid #d7e0ec;border-radius:14px;padding:10px;box-shadow:0 8px 20px rgba(0,55,100,0.08);'>"
            f"<img src='{_escape(url)}' alt='{_escape(alt)}' style='display:block;width:100%;aspect-ratio:16/9;object-fit:cover;height:auto;max-height:300px;border:1px solid #d7e0ec;border-radius:10px;background:#eef4fb;'/>"
            "</div>"
        )
    escaped_images = ""
    if image_cards:
        escaped_images = (
            "<div style='margin:6px 0 8px 0;color:#f1f7ff !important;font-weight:800;letter-spacing:0.2px;'>서울건설정보 시각 요약</div><div style='display:flex;flex-wrap:wrap;gap:12px;margin:10px 0 20px 0;'>"
            + "".join(image_cards)
            + "</div>"
        )

    sales_rows_html = "".join(
        [
            (
                "<tr>"
                f"<td style='padding:9px 8px;background:#f6f9fc;border-bottom:1px solid #d1deea;text-align:left;color:#102a43;font-weight:700;'>{_escape(r['industry'])}</td>"
                f"<td style='padding:9px 8px;background:#f6f9fc;border-bottom:1px solid #d1deea;text-align:center;color:#102a43;'>{_escape(r['license_year'])}</td>"
                f"<td style='padding:9px 8px;background:#f6f9fc;border-bottom:1px solid #d1deea;text-align:center;color:#102a43;'>{_escape(r['capacity'])}</td>"
                f"<td style='padding:9px 8px;background:#f6f9fc;border-bottom:1px solid #d1deea;text-align:center;color:#102a43;'>{_escape(r['y20'])}</td>"
                f"<td style='padding:9px 8px;background:#f6f9fc;border-bottom:1px solid #d1deea;text-align:center;color:#102a43;'>{_escape(r['y21'])}</td>"
                f"<td style='padding:9px 8px;background:#f6f9fc;border-bottom:1px solid #d1deea;text-align:center;color:#102a43;'>{_escape(r['y22'])}</td>"
                f"<td style='padding:9px 8px;background:#f6f9fc;border-bottom:1px solid #d1deea;text-align:center;color:#102a43;'>{_escape(r['y23'])}</td>"
                f"<td style='padding:9px 8px;background:#f6f9fc;border-bottom:1px solid #d1deea;text-align:center;color:#102a43;'>{_escape(r['y24'])}</td>"
                f"<td style='padding:9px 8px;background:#f6f9fc;border-bottom:1px solid #d1deea;text-align:center;color:#102a43;'>{_escape(r['y25'])}</td>"
                f"<td style='padding:9px 8px;background:#e4ebf2;border-bottom:1px solid #d1deea;text-align:center;color:#0f3a61;font-weight:800;'>{_escape(r['sum3'])}</td>"
                f"<td style='padding:9px 8px;background:#f5ede2;border-bottom:1px solid #d1deea;text-align:center;color:#7a5a24;font-weight:800;'>{_escape(r['sum5'])}</td>"
                "</tr>"
            )
            for r in sales_table_rows
        ]
    )

    commentary = _build_sales_commentary(rows)
    commentary_html = "".join([f"<li>{_escape(line)}</li>" for line in commentary])

    intro_industry = _primary_industry_name(rows)
    intro = (
        f"매물번호 {reg} 건설업 양도양수 매물 분석입니다. "
        f"주요 업종은 {intro_industry}이며, 상태는 {status} 기준으로 정리했습니다. "
        "아래 표와 체크포인트를 통해 재무·매출·행정 리스크를 한 번에 검토할 수 있도록 구성했습니다."
    )
    regulation_links_html = (
        "<a href='https://www.law.go.kr' target='_blank' rel='nofollow noopener noreferrer' style='color:#003764;font-weight:700;'>국가법령정보센터</a>"
        " · "
        "<a href='https://www.kiscon.net' target='_blank' rel='nofollow noopener noreferrer' style='color:#003764;font-weight:700;'>건설산업지식정보시스템(KISCON)</a>"
    )

    return f"""
<div style="font-family:'Pretendard','Segoe UI','Malgun Gothic',sans-serif;line-height:1.72;color:#ffffff;--gm-primary:#003764;--gm-neutral:#e4ebf2;--gm-accent:#b0894f;background:linear-gradient(160deg,#003764 0%,#0d4d82 62%,#003764 100%);padding:20px;border-radius:22px;border:1px solid #0f4f80;box-shadow:0 18px 34px rgba(0,30,62,0.28);">
  <div style="background:linear-gradient(160deg,#003764 0%,#095996 70%,#0b4374 100%);border:1px solid rgba(228,235,242,0.26);border-radius:18px;padding:20px 20px 16px 20px;margin-bottom:14px;">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
      <span style="font-size:12px;letter-spacing:1.3px;font-weight:800;color:#f1f7ff !important;">\uc11c\uc6b8\uac74\uc124\uc815\ubcf4 / SEOUL CONSTRUCTION INFO</span>
      <span style="font-size:12px;letter-spacing:1px;font-weight:700;color:#b0894f;">LISTING {_escape(reg)}</span>
    </div>
    <h2 style="margin:0;font-size:34px;line-height:1.22;font-weight:850;color:#ffffff;">매물 {_escape(reg)} 핵심 요약</h2>
    <p style="margin:10px 0 0 0;color:#f1f7ff !important;font-size:18px;line-height:1.65;font-weight:600;text-shadow:0 1px 0 rgba(0,0,0,0.18);">{_escape(intro)}</p>
  </div>

  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:0 0 14px 0;">
    <div style="background:var(--gm-neutral);border:1px solid #c8d8e8;border-radius:14px;padding:12px;"><div style="font-size:11px;color:#4c637a;">상태</div><div style="font-size:23px;font-weight:850;color:#003764;">{_escape(status)}</div></div>
    <div style="background:var(--gm-neutral);border:1px solid #c8d8e8;border-radius:14px;padding:12px;"><div style="font-size:11px;color:#4c637a;">주요 업종</div><div style="font-size:23px;font-weight:850;color:#003764;">{_escape(intro_industry)}</div></div>
    <div style="background:var(--gm-neutral);border:1px solid #c8d8e8;border-radius:14px;padding:12px;"><div style="font-size:11px;color:#4c637a;">공제잔액</div><div style="font-size:23px;font-weight:850;color:#003764;">{_escape(balance)}</div></div>
    <div style="background:var(--gm-neutral);border:1px solid #c8d8e8;border-radius:14px;padding:12px;"><div style="font-size:11px;color:#4c637a;">법인설립일</div><div style="font-size:23px;font-weight:850;color:#003764;">{_escape(founded)}</div></div>
  </div>

  {escaped_images}

  <p style="margin:8px 0 14px 0;">
    <a href="{_escape(detail_url)}" target="_blank" rel="noopener nofollow" style="display:inline-block;padding:12px 16px;border-radius:12px;background:#b0894f;color:#102a43;font-weight:850;text-decoration:none;letter-spacing:0.1px;border:1px solid rgba(0,55,100,0.24);">
      seoulmna.co.kr/mna/{_escape(_digits(reg))} 상세 페이지 바로가기
    </a>
  </p>

  <div style="background:rgba(0,55,100,0.84);border:1px solid rgba(228,235,242,0.3);border-radius:15px;padding:12px;margin-bottom:12px;">
    <h2 style="margin:2px 0 10px 0;font-size:24px;font-weight:850;color:#ffffff;">회사개요</h2>
    <table style="width:100%;table-layout:fixed;border-collapse:separate;border-spacing:0;background:var(--gm-neutral);font-size:14px;border:1px solid #c8d8e8;border-radius:12px;overflow:hidden;color:#102a43;">
      <colgroup><col style="width:16%;"/><col style="width:34%;"/><col style="width:16%;"/><col style="width:34%;"/></colgroup>
      <tr><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">매물번호</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(reg)}</td><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">상태</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(status)}</td></tr>
      <tr><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">회사형태</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(company_type)}</td><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">법인설립일</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(founded)}</td></tr>
      <tr><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">공제조합 출자좌</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(shares)}</td><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">자본금</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(capital)}</td></tr>
      <tr><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">대출후 남은잔액</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(loan_balance)}</td><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">협회가입</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(assoc)}</td></tr>
      <tr><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">소재지</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(location)}</td><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">공제잔액</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(balance)}</td></tr>
    </table>
  </div>

  <div style="background:rgba(0,55,100,0.84);border:1px solid rgba(228,235,242,0.3);border-radius:15px;padding:12px;margin-bottom:12px;">
    <h2 style="margin:2px 0 10px 0;font-size:24px;font-weight:850;color:#ffffff;">최근년도 매출실적</h2>
    <table style="width:100%;table-layout:fixed;border-collapse:separate;border-spacing:0;background:var(--gm-neutral);font-size:14px;border:1px solid #c8d8e8;border-radius:12px;overflow:hidden;color:#102a43;">
      <tr style="background:#003764;color:#ffffff;">
        <th style="padding:10px 8px;">업종</th><th style="padding:10px 8px;">면허년도</th><th style="padding:10px 8px;">시공능력</th><th style="padding:10px 8px;">20</th><th style="padding:10px 8px;">21</th><th style="padding:10px 8px;">22</th><th style="padding:10px 8px;">23</th><th style="padding:10px 8px;">24</th><th style="padding:10px 8px;">25</th><th style="padding:10px 8px;background:#205381;">3년</th><th style="padding:10px 8px;background:#b0894f;color:#102a43;">5년</th>
      </tr>
      {sales_rows_html}
    </table>
  </div>

  <div style="background:rgba(0,55,100,0.84);border:1px solid rgba(228,235,242,0.3);border-radius:15px;padding:12px;margin-bottom:12px;">
    <h2 style="margin:2px 0 10px 0;font-size:24px;font-weight:850;color:#ffffff;">매출 추이 해설</h2>
    <div style="background:var(--gm-neutral);border:1px solid #c8d8e8;border-radius:12px;padding:12px 14px;color:#102a43;">
      <ul style="margin:0;padding-left:18px;">{commentary_html}</ul>
    </div>
  </div>

  <div style="background:rgba(0,55,100,0.84);border:1px solid rgba(228,235,242,0.3);border-radius:15px;padding:12px;margin-bottom:12px;">
    <h2 style="margin:2px 0 10px 0;font-size:24px;font-weight:850;color:#ffffff;">법률·실사 안내</h2>
    <div style="background:var(--gm-neutral);border:1px solid #c8d8e8;border-radius:12px;padding:12px 14px;color:#102a43;">
      <ul style="margin:0;padding-left:20px;">
        <li>본 콘텐츠는 매물 정보 요약이며 투자·법률 자문을 대체하지 않습니다.</li>
        <li>최종 계약 전 재무·세무·노무·행정 리스크에 대한 실사를 반드시 진행해야 합니다.</li>
        <li><a href="{_escape(detail_url)}" target="_blank" rel="nofollow noopener noreferrer" style="color:#003764;font-weight:700;">매물 상세 정보 확인하기</a></li>
        <li>관련 제도 안내: {regulation_links_html}</li>
      </ul>
    </div>
  </div>

  <div style="background:rgba(0,55,100,0.84);border:1px solid rgba(228,235,242,0.3);border-radius:15px;padding:12px;margin-bottom:12px;">
    <h2 style="margin:2px 0 10px 0;font-size:24px;font-weight:850;color:#ffffff;">재무지표</h2>
    <table style="width:100%;table-layout:fixed;border-collapse:separate;border-spacing:0;background:var(--gm-neutral);font-size:14px;border:1px solid #c8d8e8;border-radius:12px;overflow:hidden;color:#102a43;">
      <colgroup><col style="width:18%;"/><col style="width:32%;"/><col style="width:18%;"/><col style="width:32%;"/></colgroup>
      <tr><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">부채비율</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(debt_ratio)}</td><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">조합신용</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(coop_credit)}</td></tr>
      <tr><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">유동비율</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(current_ratio)}</td><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">외부신용</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(ext_credit)}</td></tr>
      <tr><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">행정처분</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(admin_status)}</td><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">이익잉여금</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(retained)}</td></tr>
      <tr><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">처분 내용</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(admin_detail)}</td><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">결손금</th><td style="padding:10px 12px;background:#f7fafd;">{_escape(deficit)}</td></tr>
      <tr><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">공제잔액</th><td style="padding:10px 12px;background:#f7fafd;color:#7a5a24;font-weight:800;">{_escape(balance)}</td><th style="text-align:left;background:#d6e3f0;padding:10px 12px;">-</th><td style="padding:10px 12px;background:#f7fafd;">-</td></tr>
    </table>
  </div>

  <div style="background:rgba(0,55,100,0.84);border:1px solid rgba(228,235,242,0.3);border-radius:15px;padding:12px;">
    <h2 style="margin:2px 0 10px 0;font-size:24px;font-weight:850;color:#ffffff;">주요 체크사항</h2>
    <div style="background:var(--gm-neutral);border:1px solid #c8d8e8;border-radius:12px;padding:12px 14px;color:#102a43;">
      <ul style="margin:0;padding-left:20px;">{escaped_notes}</ul>
    </div>
  </div>
</div>
""".strip()


def _extract_http_links(content: str) -> list[str]:
    return re.findall(r"""href\s*=\s*["'](https?://[^"']+)["']""", str(content or ""), flags=re.I)


def _is_internal_link(url: str) -> bool:
    low = str(url or "").strip().lower()
    if not low:
        return False
    return any(
        host in low
        for host in (
            "seoulmna.co.kr",
            "seoulmna.kr",
            "seoulmna.tistory.com",
        )
    )


def evaluate_seo_quality(title: str, content: str, registration_no: str) -> dict[str, Any]:
    reg = _digits(registration_no)
    text_title = str(title or "")
    text_content = str(content or "")
    links = _extract_http_links(text_content)
    external_links = [x for x in links if not _is_internal_link(x)]

    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, weight: int, detail: str):
        checks.append({"name": name, "ok": bool(ok), "weight": int(weight), "detail": detail})

    add("title_length", 20 <= len(text_title) <= 68, 10, f"len={len(text_title)}")
    add("title_keyword", ("건설" in text_title and "양도" in text_title), 10, "title has 건설/양도")
    add("title_registration", (reg and reg in text_title), 10, f"registration={reg}")
    add("h2_count", len(re.findall(r"<h2\b", text_content, flags=re.I)) >= 6, 10, ">=6 sections")
    add("content_length", len(re.sub(r"<[^>]+>", " ", text_content)) >= 420, 10, "text>=420 chars")
    add("image_count", len(re.findall(r"<img\b", text_content, flags=re.I)) >= 2, 12, ">=2 images")
    add(
        "internal_link",
        bool(re.search(r"https://seoulmna\.co\.kr/mna/\d+", text_content)),
        14,
        "has listing detail link",
    )
    add("external_link", len(external_links) >= 1, 10, f"external_links={len(external_links)}")
    add("no_source_phrase", ("출처" not in text_content), 8, "source phrase removed")
    add("unique_marker", (f"매물번호 {reg}" in text_content if reg else True), 6, "contains unique marker")

    total_weight = sum(x["weight"] for x in checks)
    earned = sum(x["weight"] for x in checks if x["ok"])
    score = int(round((earned / total_weight) * 100)) if total_weight else 0
    return {"score": score, "checks": checks, "ok": score >= 90}


def evaluate_legal_quality(title: str, content: str, registration_no: str) -> dict[str, Any]:
    text_title = str(title or "")
    text_content = str(content or "")
    links = _extract_http_links(text_content)

    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, weight: int, detail: str):
        checks.append({"name": name, "ok": bool(ok), "weight": int(weight), "detail": detail})

    aggressive_claim = bool(
        re.search(
            r"(100%\s*보장|무조건\s*수익|확정\s*수익|원금\s*보장|손해\s*없음|절대\s*안전)",
            text_content,
            flags=re.I,
        )
    )
    credential_leak = bool(re.search(r"(password|비밀번호|@gmail\.com|@naver\.com)", text_content, flags=re.I))
    has_reg_notice = bool(re.search(r"(투자·법률 자문|최종 계약 전|실사)", text_content))
    has_law_link = any(re.search(r"(law\.go\.kr|kiscon\.net)", x, flags=re.I) for x in links)
    has_listing_identity = bool(re.search(r"매물번호\s*\d+", text_content)) and ("양도양수" in text_title)

    add("advisory_notice", has_reg_notice, 30, "contains legal/advisory notice")
    add("no_aggressive_claim", not aggressive_claim, 25, "no guaranteed-profit style phrase")
    add("law_reference_link", has_law_link, 25, "has law.go.kr or kiscon.net link")
    add("no_credential_leak", not credential_leak, 10, "no password/email leak")
    add("listing_identity", has_listing_identity, 10, "keeps listing identity context")

    total_weight = sum(x["weight"] for x in checks)
    earned = sum(x["weight"] for x in checks if x["ok"])
    score = int(round((earned / total_weight) * 100)) if total_weight else 0
    return {"score": score, "checks": checks, "ok": score >= 85}


def evaluate_cx_quality(title: str, content: str, registration_no: str) -> dict[str, Any]:
    _ = title
    _ = registration_no
    text_content = str(content or "")
    links = _extract_http_links(text_content)
    external_links = [x for x in links if not _is_internal_link(x)]

    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, weight: int, detail: str):
        checks.append({"name": name, "ok": bool(ok), "weight": int(weight), "detail": detail})

    add(
        "quick_scan_cards",
        all(token in text_content for token in ("상태", "주요 업종", "공제잔액", "법인설립일")),
        20,
        "has summary cards",
    )
    add("section_count", len(re.findall(r"<h2\b", text_content, flags=re.I)) >= 6, 18, ">=6 sections")
    add(
        "table_alignment",
        len(re.findall(r"table-layout\s*:\s*fixed", text_content, flags=re.I)) >= 2,
        16,
        ">=2 fixed-layout tables",
    )
    add("image_alt_count", len(re.findall(r"<img\b[^>]*\balt=", text_content, flags=re.I)) >= 2, 16, ">=2 alt images")
    add("cta_internal_link", bool(re.search(r"https://seoulmna\.co\.kr/mna/\d+", text_content)), 15, "has CTA link")
    add("external_help_links", len(external_links) >= 1, 15, f"external_links={len(external_links)}")

    total_weight = sum(x["weight"] for x in checks)
    earned = sum(x["weight"] for x in checks if x["ok"])
    score = int(round((earned / total_weight) * 100)) if total_weight else 0
    return {"score": score, "checks": checks, "ok": score >= 85}
