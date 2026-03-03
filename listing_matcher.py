import argparse
import json
import os
import re
import sys
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from utils import load_config, require_config, setup_logger

CONFIG = load_config(
    {
        "JSON_FILE": "service_account.json",
        "SHEET_NAME": "26양도매물",
        "TAB_CONSULT": "상담관리",
        "TAB_ITEM": "26양도매물",
        "TAB_RECOMMEND": "추천발송",
        "BRAND_NAME": "서울건설정보",
        "CONSULTANT_NAME": "강지현 행정사",
        "PHONE": "010-9926-8661",
        "KAKAO_OPENCHAT_URL": "",
        "RECOMMEND_OUTPUT_DIR": "recommendations",
    }
)

logger = setup_logger(name="listing_matcher")

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RECOMMEND_HEADERS = [
    "생성일시",            # A
    "추천ID",             # B
    "리드ID",             # C
    "상담행",             # D
    "상담제목",           # E
    "추천매물ID",         # F
    "카카오발송문",       # G
    "메일발송문",         # H
    "상태",               # I
]


def _compact(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _norm(text):
    return re.sub(r"[^0-9a-z가-힣]+", "", str(text or "").lower())


def _ensure_dir(path):
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def _recommend_id(now=None):
    now = now or datetime.now()
    return f"RCM{now.strftime('%Y%m%d%H%M%S')}"


def _parse_ids(text):
    src = str(text or "")
    if not src or "매칭 매물 없음" in src:
        return []
    nums = re.findall(r"\d+", src)
    uniq = []
    seen = set()
    for n in nums:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


def _to_int(v, default=0):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _is_numeric_price(value):
    src = _compact(value)
    if not src:
        return False
    if "협의" in src and not re.search(r"\d", src):
        return False
    return bool(re.search(r"\d", src))


def _extract_final_price(value):
    src = _compact(value)
    if not src:
        return ""

    parts = re.split(r"\s*(?:~|〜|∼|–|—|-|→|->|to|TO)\s*", src)
    candidates = [x.strip() for x in parts if x.strip()] or [src]
    for cand in reversed(candidates):
        m = re.search(r"[0-9][0-9,]*(?:\.[0-9]+)?\s*억(?:\s*[0-9][0-9,]*(?:\.[0-9]+)?\s*만)?", cand)
        if m:
            return re.sub(r"\s+", "", m.group(0))
        m = re.search(r"[0-9][0-9,]*(?:\.[0-9]+)?\s*만", cand)
        if m:
            return re.sub(r"\s+", "", m.group(0))
        m = re.search(r"[0-9][0-9,]*(?:\.[0-9]+)?", cand)
        if m:
            n = m.group(0).replace(",", "")
            if "억" in cand:
                return f"{n}억"
            return n
    return src


def _resolve_listing_price(primary, claim):
    if _is_numeric_price(primary):
        return _extract_final_price(primary)
    if _is_numeric_price(claim):
        return _extract_final_price(claim)
    return _compact(primary) or _compact(claim) or ""


class ListingMatcher:
    def __init__(self):
        require_config(
            CONFIG,
            ["JSON_FILE", "SHEET_NAME", "TAB_CONSULT", "TAB_ITEM", "TAB_RECOMMEND"],
            context="listing_matcher:init",
        )
        self.json_file = str(CONFIG["JSON_FILE"]).strip()
        self.sheet_name = str(CONFIG["SHEET_NAME"]).strip()
        self.tab_consult = str(CONFIG["TAB_CONSULT"]).strip()
        self.tab_item = str(CONFIG["TAB_ITEM"]).strip()
        self.tab_recommend = str(CONFIG["TAB_RECOMMEND"]).strip()

        self.client = None
        self.sheet = None
        self.ws_consult = None
        self.ws_item = None
        self.ws_recommend = None

    def connect(self):
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.json_file, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open(self.sheet_name)

        self.ws_consult = self.sheet.worksheet(self.tab_consult)
        self.ws_item = self.sheet.worksheet(self.tab_item)

        try:
            self.ws_recommend = self.sheet.worksheet(self.tab_recommend)
        except Exception:
            self.ws_recommend = self.sheet.add_worksheet(title=self.tab_recommend, rows=1200, cols=12)
        self._ensure_recommend_header()

    def _ensure_recommend_header(self):
        row1 = self.ws_recommend.row_values(1)
        if not row1:
            self.ws_recommend.update(range_name="A1:I1", values=[RECOMMEND_HEADERS])
            return
        if len(row1) < len(RECOMMEND_HEADERS):
            fixed = row1 + [""] * (len(RECOMMEND_HEADERS) - len(row1))
            for i, h in enumerate(RECOMMEND_HEADERS):
                if not fixed[i]:
                    fixed[i] = h
            self.ws_recommend.update(range_name="A1:I1", values=[fixed])

    def _find_consult(self, lead_id="", consult_row=0):
        rows = self.ws_consult.get_all_values()
        if len(rows) <= 1:
            return None

        if consult_row > 1:
            row = self.ws_consult.row_values(int(consult_row))
            if row:
                return int(consult_row), row

        if lead_id:
            for idx, row in enumerate(rows[1:], start=2):
                if len(row) > 5 and _compact(row[5]) == _compact(lead_id):
                    return idx, row

        # fallback: latest non-empty consult row
        for idx in range(len(rows), 1, -1):
            row = rows[idx - 1]
            if len(row) > 1 and (_compact(row[1]) or _compact(row[2])):
                return idx, row
        return None

    def _item_index(self):
        rows = self.ws_item.get_all_values()
        if len(rows) <= 1:
            return {}
        idx = {}
        for row in rows[1:]:
            if not row:
                continue
            key = _compact(row[0] if len(row) > 0 else "")
            if key:
                idx[key] = row
        return idx

    def _row_to_listing(self, row):
        seq_id = _compact(row[0] if len(row) > 0 else "")
        license_name = _compact(row[2] if len(row) > 2 else "")
        license_year = _compact(row[3] if len(row) > 3 else "")
        specialty = _compact(row[4] if len(row) > 4 else "")
        location = _compact(row[16] if len(row) > 16 else "")
        price_primary = row[18] if len(row) > 18 else ""
        price_claim = row[33] if len(row) > 33 else ""
        price = _resolve_listing_price(price_primary, price_claim)
        capital = _compact(row[19] if len(row) > 19 else "")
        debt = _compact(row[21] if len(row) > 21 else "")
        liq = _compact(row[23] if len(row) > 23 else "")
        memo = _compact(row[31] if len(row) > 31 else "")
        origin_uid = _compact(row[34] if len(row) > 34 else "")

        source_url = ""
        if origin_uid.isdigit():
            source_url = f"http://www.nowmna.com/yangdo_view1.php?uid={origin_uid}&page_no=1"

        return {
            "seq_id": seq_id,
            "license": license_name,
            "license_year": license_year,
            "specialty": specialty,
            "location": location,
            "price": price,
            "capital": capital,
            "debt": debt,
            "liquidity": liq,
            "memo": memo,
            "origin_uid": origin_uid,
            "source_url": source_url,
        }

    def build_recommendation(self, lead_id="", consult_row=0, top_n=5):
        target = self._find_consult(lead_id=lead_id, consult_row=consult_row)
        if not target:
            raise RuntimeError("상담 데이터를 찾지 못했습니다.")

        row_num, consult = target
        consult_title = _compact(consult[1] if len(consult) > 1 else "")
        consult_body = _compact(consult[2] if len(consult) > 2 else "")
        consult_lead_id = _compact(consult[5] if len(consult) > 5 else "")
        consult_channel = _compact(consult[7] if len(consult) > 7 else "")
        consult_customer = _compact(consult[8] if len(consult) > 8 else "")

        matched_raw = _compact(consult[4] if len(consult) > 4 else "")
        matched_ids = _parse_ids(matched_raw)
        if not matched_ids:
            raise RuntimeError("매칭 결과가 없습니다. 먼저 python match.py를 실행하세요.")

        item_idx = self._item_index()
        listings = []
        for mid in matched_ids:
            row = item_idx.get(mid)
            if not row:
                continue
            listings.append(self._row_to_listing(row))
            if len(listings) >= max(1, top_n):
                break

        if not listings:
            raise RuntimeError("매칭된 매물 ID에 해당하는 실제 매물 데이터를 찾지 못했습니다.")

        now = datetime.now()
        recommend_id = _recommend_id(now)

        summary_lines = []
        for idx, it in enumerate(listings, start=1):
            line = (
                f"{idx}) #{it['seq_id']} | {it['license'] or '업종확인중'} | {it['location'] or '지역확인중'} | "
                f"양도가 {it['price'] or '협의'}"
            )
            summary_lines.append(line)

        base_header = f"[{CONFIG.get('BRAND_NAME','서울건설정보')}] 추천 매물 안내 ({recommend_id})"
        greet_name = consult_customer or "고객님"

        kakao_parts = [
            base_header,
            f"{greet_name} 요청 조건 기준으로 우선 검토 매물 {len(listings)}건을 정리했습니다.",
            "",
            *summary_lines,
            "",
            f"담당: {CONFIG.get('CONSULTANT_NAME','담당자')} / {CONFIG.get('PHONE','')}",
        ]
        if str(CONFIG.get("KAKAO_OPENCHAT_URL", "")).strip():
            kakao_parts.append(f"카카오 상담: {CONFIG['KAKAO_OPENCHAT_URL']}")

        email_parts = [
            f"안녕하세요, {greet_name}님.",
            f"요청하신 상담('{consult_title or '상담 요청'}') 기준으로 우선 검토 매물을 공유드립니다.",
            "",
            "[추천 매물]",
            *summary_lines,
            "",
            "상세자료(재무/행정처분/실사 체크리스트)는 회신 주시면 순차 전달드리겠습니다.",
            f"담당: {CONFIG.get('CONSULTANT_NAME','담당자')} / {CONFIG.get('PHONE','')}",
        ]

        output = {
            "created_at": now.strftime("%Y-%m-%d %H:%M"),
            "recommend_id": recommend_id,
            "lead_id": consult_lead_id,
            "consult_row": row_num,
            "consult_title": consult_title,
            "consult_body": consult_body,
            "channel": consult_channel,
            "matched_ids": [x["seq_id"] for x in listings],
            "listings": listings,
            "kakao_message": "\n".join(kakao_parts),
            "email_message": "\n".join(email_parts),
        }
        return output

    def save_recommend_sheet(self, out):
        row = [
            out["created_at"],
            out["recommend_id"],
            out.get("lead_id", ""),
            out.get("consult_row", ""),
            out.get("consult_title", ""),
            ",".join(out.get("matched_ids", [])),
            out.get("kakao_message", ""),
            out.get("email_message", ""),
            "생성",
        ]
        self.ws_recommend.append_row(row, value_input_option="USER_ENTERED")


def _save_files(out):
    out_dir = str(CONFIG.get("RECOMMEND_OUTPUT_DIR", "recommendations")).strip() or "recommendations"
    _ensure_dir(out_dir)

    rid = out["recommend_id"]
    json_path = os.path.join(out_dir, f"{rid}.json")
    md_path = os.path.join(out_dir, f"{rid}.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    md = [
        f"# 추천안 {rid}",
        "",
        f"- 생성일시: {out['created_at']}",
        f"- 리드ID: {out.get('lead_id','')}",
        f"- 상담행: {out.get('consult_row','')}",
        f"- 상담제목: {out.get('consult_title','')}",
        f"- 추천매물ID: {', '.join(out.get('matched_ids', []))}",
        "",
        "## 추천 매물",
    ]

    for idx, it in enumerate(out.get("listings", []), start=1):
        md.append(
            f"{idx}. #{it['seq_id']} | {it['license']} | {it['location']} | 양도가 {it['price']} | 링크: {it.get('source_url','-')}"
        )

    md.extend(["", "## 카카오 발송문", "```text", out.get("kakao_message", ""), "```", "", "## 메일 발송문", "```text", out.get("email_message", ""), "```"])

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    return json_path, md_path


def _print_summary(out, paths=None):
    print("=" * 62)
    print(f"추천ID: {out['recommend_id']}")
    print(f"상담행: {out.get('consult_row')}")
    print(f"상담제목: {out.get('consult_title')}")
    print(f"추천매물ID: {', '.join(out.get('matched_ids', []))}")
    if paths:
        print(f"파일 저장: {paths[0]} / {paths[1]}")
    print("=" * 62)


def _build_parser():
    p = argparse.ArgumentParser(description="매칭 결과 기반 추천 매물 발송문 생성기")
    p.add_argument("--lead-id", default="", help="상담관리 탭 리드ID")
    p.add_argument("--consult-row", type=int, default=0, help="상담관리 탭 행번호")
    p.add_argument("--top", type=int, default=5, help="추천 매물 수")
    p.add_argument("--dry-run", action="store_true", help="시트/파일 저장 없이 결과만 검증")
    p.add_argument("--no-sheet", action="store_true", help="추천발송 탭 저장 생략")
    p.add_argument("--no-files", action="store_true", help="파일 저장 생략")
    return p


def main():
    args = _build_parser().parse_args()

    matcher = ListingMatcher()
    matcher.connect()

    out = matcher.build_recommendation(
        lead_id=args.lead_id,
        consult_row=args.consult_row,
        top_n=max(1, args.top),
    )

    paths = None
    if not args.dry_run and not args.no_files:
        paths = _save_files(out)

    if not args.dry_run and not args.no_sheet:
        matcher.save_recommend_sheet(out)

    _print_summary(out, paths=paths)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as e:
        print(str(e))
        raise SystemExit(1)
