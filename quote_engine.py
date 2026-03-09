import argparse
import json
import os
import random
import re
import sys
from datetime import datetime, timedelta

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from utils import load_config, require_config, setup_logger

CONFIG = load_config(
    {
        "JSON_FILE": "service_account.json",
        "SHEET_NAME": "26양도매물",
        "TAB_CONSULT": "상담관리",
        "TAB_QUOTE": "견적관리",
        "CONSULTANT_NAME": "강지현 행정사",
        "BRAND_NAME": "서울건설정보",
        "PHONE": "010-9926-8661",
        "KAKAO_OPENCHAT_URL": "",
        "QUOTE_OUTPUT_DIR": "quotes",
        "QUOTE_DEFAULT_VALID_DAYS": "7",
    }
)

logger = setup_logger(name="quote_engine")

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

CONSULT_MIN_HEADERS = ["접수일시", "상담제목", "상담내용", "AI분석JSON", "매칭결과"]
QUOTE_HEADERS = [
    "생성일시",          # A
    "견적ID",           # B
    "리드ID",           # C
    "업무유형",         # D
    "견적제목",         # E
    "예상수수료_최소(만원)",  # F
    "예상수수료_최대(만원)",  # G
    "착수금_권장(만원)",     # H
    "예상기간(영업일)",      # I
    "유효기한",         # J
    "고객명",           # K
    "연락처",           # L
    "유입채널",         # M
    "핵심요약",         # N
    "카카오발송문",      # O
    "메일발송문",        # P
    "가정/주의",         # Q
    "원문참조",          # R
]

INTENT_ALIASES = {
    "신규": "신규등록",
    "신규등록": "신규등록",
    "등록": "신규등록",
    "면허등록": "신규등록",
    "양도": "양도양수",
    "양수": "양도양수",
    "양도양수": "양도양수",
    "mna": "양도양수",
    "기업진단": "기업진단",
    "진단": "기업진단",
    "실질자본금": "실질자본금",
    "자본금": "실질자본금",
    "분할합병": "분할합병",
    "합병": "분할합병",
    "분할": "분할합병",
    "행정처분": "행정처분",
    "처분": "행정처분",
}


def _cfg_int(key, default):
    try:
        return int(str(CONFIG.get(key, default)).strip())
    except (ValueError, TypeError):
        return default


def _compact(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _norm(text):
    return re.sub(r"[^0-9a-z가-힣]+", "", str(text or "").lower())


def _parse_phone(value):
    raw = re.sub(r"[^0-9]", "", str(value or ""))
    if len(raw) == 11:
        return f"{raw[:3]}-{raw[3:7]}-{raw[7:]}"
    if len(raw) == 10:
        return f"{raw[:3]}-{raw[3:6]}-{raw[6:]}"
    return str(value or "").strip()


def _parse_eok(value):
    s = str(value or "").replace(",", "").replace(" ", "")
    if not s:
        return 0.0

    eok = 0.0
    man = 0.0
    m1 = re.search(r"([0-9]+(?:\.[0-9]+)?)억", s)
    m2 = re.search(r"([0-9]+(?:\.[0-9]+)?)만", s)

    if m1:
        eok = float(m1.group(1))
    if m2:
        man = float(m2.group(1)) / 10000.0
    if m1 or m2:
        return round(eok + man, 4)

    plain = re.sub(r"[^0-9.]", "", s)
    if not plain:
        return 0.0
    val = float(plain)
    if val >= 100:
        return round(val / 10000.0, 4)
    return round(val, 4)


def _infer_intent(text):
    t = _norm(text)
    if any(x in t for x in ["양도양수", "양도", "양수", "mna", "매물"]):
        return "양도양수"
    if any(x in t for x in ["신규등록", "신규", "등록", "면허등록"]):
        return "신규등록"
    if any(x in t for x in ["기업진단", "진단"]):
        return "기업진단"
    if any(x in t for x in ["실질자본금", "자본금", "예치"]):
        return "실질자본금"
    if any(x in t for x in ["분할합병", "분할", "합병"]):
        return "분할합병"
    if any(x in t for x in ["행정처분", "영업정지", "과징금"]):
        return "행정처분"
    return "기타"


def _normalize_intent(intent, title="", content=""):
    v = _compact(intent)
    if v:
        mapped = INTENT_ALIASES.get(v.lower()) or INTENT_ALIASES.get(v)
        if mapped:
            return mapped
    return _infer_intent(f"{title} {content}")


def _infer_urgency(text):
    t = _norm(text)
    if any(x in t for x in ["긴급", "당장", "오늘", "내일", "마감", "급함"]):
        return "긴급"
    if any(x in t for x in ["빠르게", "가능하면", "조속", "이번주"]):
        return "보통"
    return "일반"


def _quote_id(now=None):
    now = now or datetime.now()
    return f"QT{now.strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}"


def _estimate_fee(intent, deal_value_eok=0.0, urgency="일반", license_count=1, with_due_diligence=False):
    base = {
        "신규등록": (120, 260, (12, 30)),
        "양도양수": (180, 420, (10, 35)),
        "기업진단": (80, 180, (5, 12)),
        "실질자본금": (90, 220, (7, 18)),
        "분할합병": (320, 900, (20, 50)),
        "행정처분": (150, 380, (10, 25)),
        "기타": (80, 220, (7, 20)),
    }
    fee_min, fee_max, period = base.get(intent, base["기타"])

    if intent == "양도양수" and deal_value_eok > 0:
        fee_min += int(min(260, deal_value_eok * 7))
        fee_max += int(min(420, deal_value_eok * 12))

    if intent == "신규등록" and license_count > 1:
        fee_min += (license_count - 1) * 35
        fee_max += (license_count - 1) * 65

    if with_due_diligence:
        fee_min += 70
        fee_max += 160

    if urgency == "긴급":
        fee_min = int(round(fee_min * 1.2))
        fee_max = int(round(fee_max * 1.25))
        period = (max(3, int(period[0] * 0.8)), max(7, int(period[1] * 0.9)))

    if urgency == "보통":
        period = (max(4, int(period[0] * 0.9)), period[1])

    retainer = int(round(fee_min * 0.5))
    return {
        "fee_min": fee_min,
        "fee_max": max(fee_min, fee_max),
        "retainer": retainer,
        "period_days": f"{period[0]}~{period[1]}",
    }


def _build_assumptions(intent):
    common = [
        "부가세 별도 기준입니다.",
        "실사 결과(행정처분/재무/서류누락)에 따라 범위가 조정될 수 있습니다.",
        "관할청 보완요청 횟수에 따라 일정이 변동될 수 있습니다.",
    ]
    intent_map = {
        "신규등록": ["법인/개인 기본 서류가 준비된 상태를 전제로 산정했습니다."],
        "양도양수": ["양도기업 기본 재무/법무 서류 확인 가능 상태를 전제로 산정했습니다."],
        "분할합병": ["조직/지배구조 및 세무 검토 범위에 따라 추가 협의가 필요합니다."],
    }
    return common + intent_map.get(intent, [])


def _build_summary(intent, title, fee):
    return (
        f"{intent} 기준 예상 수수료는 {fee['fee_min']}~{fee['fee_max']}만원(부가세 별도), "
        f"권장 착수금은 {fee['retainer']}만원, 예상 기간은 {fee['period_days']} 영업일입니다."
    )


def _build_kakao_message(quote, req):
    kakao_url = str(CONFIG.get("KAKAO_OPENCHAT_URL", "")).strip()
    lines = [
        f"[{CONFIG.get('BRAND_NAME','서울건설정보')}] {quote['quote_id']} 견적안",
        f"- 업무유형: {quote['intent']}",
        f"- 예상 수수료: {quote['fee_min']}~{quote['fee_max']}만원 (VAT 별도)",
        f"- 권장 착수금: {quote['retainer']}만원",
        f"- 예상 기간: {quote['period_days']} 영업일",
        f"- 유효기한: {quote['valid_until']}",
        f"- 담당: {CONFIG.get('CONSULTANT_NAME','담당자')} / {CONFIG.get('PHONE','')}",
    ]
    if kakao_url:
        lines.append(f"- 카카오 상담: {kakao_url}")
    return "\n".join(lines)


def _build_email_message(quote, req):
    assumptions = "\n".join([f"- {a}" for a in quote["assumptions"]])
    return (
        f"안녕하세요. {CONFIG.get('BRAND_NAME','서울건설정보')} {CONFIG.get('CONSULTANT_NAME','담당자')}입니다.\n\n"
        f"요청하신 {quote['intent']} 건에 대한 1차 견적안 전달드립니다.\n\n"
        f"1) 예상 수수료: {quote['fee_min']}~{quote['fee_max']}만원 (부가세 별도)\n"
        f"2) 권장 착수금: {quote['retainer']}만원\n"
        f"3) 예상 기간: {quote['period_days']} 영업일\n"
        f"4) 견적 유효기한: {quote['valid_until']}\n\n"
        f"[산정 가정 및 주의사항]\n{assumptions}\n\n"
        f"세부 범위 확정 후 최종 견적서를 다시 전달드리겠습니다.\n"
        f"감사합니다.\n"
        f"{CONFIG.get('CONSULTANT_NAME','담당자')} 드림 / {CONFIG.get('PHONE','')}"
    )


def _ensure_dir(path):
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def _write_quote_files(quote, req):
    out_dir = str(CONFIG.get("QUOTE_OUTPUT_DIR", "quotes")).strip() or "quotes"
    _ensure_dir(out_dir)

    quote_id = quote["quote_id"]
    json_path = os.path.join(out_dir, f"{quote_id}.json")
    md_path = os.path.join(out_dir, f"{quote_id}.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"request": req, "quote": quote}, f, ensure_ascii=False, indent=2)

    md = [
        f"# 견적안 {quote_id}",
        "",
        f"- 생성일시: {quote['created_at']}",
        f"- 업무유형: {quote['intent']}",
        f"- 제목: {quote['title']}",
        f"- 예상 수수료: {quote['fee_min']}~{quote['fee_max']}만원 (VAT 별도)",
        f"- 권장 착수금: {quote['retainer']}만원",
        f"- 예상 기간: {quote['period_days']} 영업일",
        f"- 유효기한: {quote['valid_until']}",
        "",
        "## 핵심 요약",
        quote["summary"],
        "",
        "## 가정/주의사항",
    ]
    md.extend([f"- {a}" for a in quote["assumptions"]])
    md.extend(["", "## 카카오 발송문", "```text", quote["kakao_message"], "```", "", "## 메일 발송문", "```text", quote["email_message"], "```"])

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    return json_path, md_path


class QuoteSheetStore:
    def __init__(self):
        require_config(CONFIG, ["JSON_FILE", "SHEET_NAME", "TAB_QUOTE"], context="quote_engine:sheet")
        self.json_file = str(CONFIG["JSON_FILE"]).strip()
        self.sheet_name = str(CONFIG["SHEET_NAME"]).strip()
        self.tab_quote = str(CONFIG["TAB_QUOTE"]).strip()
        self.tab_consult = str(CONFIG.get("TAB_CONSULT", "상담관리")).strip()

        self.client = None
        self.sheet = None
        self.ws_quote = None

    def connect(self):
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.json_file, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open(self.sheet_name)

        try:
            self.ws_quote = self.sheet.worksheet(self.tab_quote)
        except gspread.exceptions.WorksheetNotFound:
            self.ws_quote = self.sheet.add_worksheet(title=self.tab_quote, rows=1200, cols=24)

        self._ensure_quote_header()

    def _ensure_quote_header(self):
        row1 = self.ws_quote.row_values(1)
        if not row1:
            self.ws_quote.update(range_name="A1:R1", values=[QUOTE_HEADERS])
            return

        if len(row1) < len(QUOTE_HEADERS):
            fixed = row1 + [""] * (len(QUOTE_HEADERS) - len(row1))
            for i, h in enumerate(QUOTE_HEADERS):
                if not fixed[i]:
                    fixed[i] = h
            self.ws_quote.update(range_name="A1:R1", values=[fixed])

    def append_quote(self, quote, req):
        row = [
            quote["created_at"],
            quote["quote_id"],
            req.get("lead_id", ""),
            quote["intent"],
            quote["title"],
            quote["fee_min"],
            quote["fee_max"],
            quote["retainer"],
            quote["period_days"],
            quote["valid_until"],
            req.get("customer_name", ""),
            req.get("contact", ""),
            req.get("channel", ""),
            quote["summary"],
            quote["kakao_message"],
            quote["email_message"],
            " | ".join(quote["assumptions"]),
            req.get("source_ref", ""),
        ]
        self.ws_quote.append_row(row, value_input_option="USER_ENTERED")

    def load_consult_by_lead_id(self, lead_id):
        ws = self.sheet.worksheet(self.tab_consult)
        rows = ws.get_all_values()
        if len(rows) <= 1:
            return None
        for row in rows[1:]:
            if len(row) > 5 and str(row[5]).strip() == str(lead_id).strip():
                return self._row_to_req(row)
        return None

    def load_consult_by_row(self, row_num):
        ws = self.sheet.worksheet(self.tab_consult)
        row = ws.row_values(int(row_num))
        if not row:
            return None
        return self._row_to_req(row)

    def _row_to_req(self, row):
        return {
            "source_ref": f"{self.tab_consult}!{len(row)}cols",
            "title": row[1] if len(row) > 1 else "",
            "content": row[2] if len(row) > 2 else "",
            "lead_id": row[5] if len(row) > 5 else "",
            "channel": row[7] if len(row) > 7 else "",
            "customer_name": row[8] if len(row) > 8 else "",
            "contact": row[9] if len(row) > 9 else "",
            "intent": row[10] if len(row) > 10 else "",
            "urgency": row[11] if len(row) > 11 else "",
        }


def _build_request(args, sheet_store=None):
    req = {
        "lead_id": _compact(args.lead_id),
        "title": _compact(args.title),
        "content": _compact(args.content),
        "intent": _compact(args.intent),
        "channel": _compact(args.channel),
        "customer_name": _compact(args.customer),
        "contact": _parse_phone(args.contact),
        "deal_value_eok": _parse_eok(args.deal_value),
        "licenses": [x.strip() for x in str(args.licenses or "").split(",") if x.strip()],
        "urgency": _compact(args.urgency),
        "with_due_diligence": bool(args.due_diligence),
        "source_ref": "manual_cli",
    }

    if sheet_store and args.lead_id:
        row_req = sheet_store.load_consult_by_lead_id(args.lead_id)
        if row_req:
            req.update({k: v for k, v in row_req.items() if _compact(v)})

    if sheet_store and args.consult_row > 0:
        row_req = sheet_store.load_consult_by_row(args.consult_row)
        if row_req:
            req.update({k: v for k, v in row_req.items() if _compact(v)})

    req["intent"] = _normalize_intent(req.get("intent"), req.get("title"), req.get("content"))
    if not req.get("urgency"):
        req["urgency"] = _infer_urgency(f"{req.get('title','')} {req.get('content','')}")

    if not req.get("title"):
        req["title"] = f"{req['intent']} 견적 요청"

    if not req.get("contact"):
        req["contact"] = _parse_phone(args.contact)

    if not req.get("licenses"):
        blob = f"{req.get('title','')} {req.get('content','')}"
        lic = re.findall(r"[가-힣A-Za-z0-9]+공사업", blob)
        req["licenses"] = list(dict.fromkeys(lic))

    return req


def _generate_quote(req):
    now = datetime.now()
    quote_id = _quote_id(now)

    fee = _estimate_fee(
        intent=req["intent"],
        deal_value_eok=float(req.get("deal_value_eok", 0.0) or 0.0),
        urgency=req.get("urgency", "일반"),
        license_count=max(1, len(req.get("licenses", []))),
        with_due_diligence=bool(req.get("with_due_diligence", False)),
    )

    valid_days = max(1, _cfg_int("QUOTE_DEFAULT_VALID_DAYS", 7))
    valid_until = (now + timedelta(days=valid_days)).strftime("%Y-%m-%d")

    title = _compact(req.get("title", ""))
    if req.get("customer_name"):
        title = f"{req['customer_name']} 고객 - {title}"

    quote = {
        "quote_id": quote_id,
        "created_at": now.strftime("%Y-%m-%d %H:%M"),
        "intent": req["intent"],
        "title": title,
        "fee_min": fee["fee_min"],
        "fee_max": fee["fee_max"],
        "retainer": fee["retainer"],
        "period_days": fee["period_days"],
        "valid_until": valid_until,
        "assumptions": _build_assumptions(req["intent"]),
    }

    quote["summary"] = _build_summary(req["intent"], title, fee)
    quote["kakao_message"] = _build_kakao_message(quote, req)
    quote["email_message"] = _build_email_message(quote, req)
    return quote


def _print_result(quote, req, paths=None):
    print("=" * 62)
    print(f"견적ID: {quote['quote_id']}")
    print(f"업무유형: {quote['intent']}")
    print(f"제목: {quote['title']}")
    print(f"예상 수수료: {quote['fee_min']}~{quote['fee_max']}만원 (VAT 별도)")
    print(f"권장 착수금: {quote['retainer']}만원")
    print(f"예상 기간: {quote['period_days']} 영업일")
    print(f"유효기한: {quote['valid_until']}")
    print(f"고객명: {req.get('customer_name','')}")
    print(f"연락처: {req.get('contact','')}")
    if paths:
        print(f"파일 저장: {paths[0]} / {paths[1]}")
    print("=" * 62)


def _build_parser():
    p = argparse.ArgumentParser(description="견적 자동 생성기 (신규등록/양도양수/기업진단/분할합병)")

    p.add_argument("--lead-id", default="", help="상담관리 탭의 리드ID")
    p.add_argument("--consult-row", type=int, default=0, help="상담관리 탭의 행번호")

    p.add_argument("--intent", default="", help="업무유형")
    p.add_argument("--title", default="", help="견적 제목")
    p.add_argument("--content", default="", help="상담 내용")
    p.add_argument("--customer", default="", help="고객명")
    p.add_argument("--contact", default="", help="연락처")
    p.add_argument("--channel", default="", help="유입채널")
    p.add_argument("--deal-value", default="", help="딜 금액 (예: 2.5억, 25000만)")
    p.add_argument("--licenses", default="", help="면허 목록 콤마 구분")
    p.add_argument("--urgency", default="", help="긴급도 (일반/보통/긴급)")
    p.add_argument("--due-diligence", action="store_true", help="실사 범위 포함")

    p.add_argument("--no-sheet", action="store_true", help="견적관리 시트 저장 생략")
    p.add_argument("--no-files", action="store_true", help="json/md 파일 저장 생략")
    p.add_argument("--dry-run", action="store_true", help="저장 없이 결과만 출력")
    return p


def main():
    args = _build_parser().parse_args()

    use_sheet = not args.no_sheet
    save_files = not args.no_files

    sheet_store = None
    if use_sheet or args.lead_id or args.consult_row > 0:
        require_config(CONFIG, ["JSON_FILE", "SHEET_NAME", "TAB_QUOTE", "TAB_CONSULT"], context="quote_engine:main")
        sheet_store = QuoteSheetStore()
        sheet_store.connect()

    req = _build_request(args, sheet_store=sheet_store)
    quote = _generate_quote(req)

    paths = None
    if not args.dry_run and save_files:
        paths = _write_quote_files(quote, req)

    if not args.dry_run and use_sheet and sheet_store is not None:
        sheet_store.append_quote(quote, req)

    _print_result(quote, req, paths=paths)


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(str(e))
        raise SystemExit(1)
