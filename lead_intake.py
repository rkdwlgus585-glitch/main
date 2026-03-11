import argparse
import csv
import hashlib
import json
import os
import random
import subprocess
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Sequence, Tuple

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from utils import load_config, require_config, setup_logger

# =================================================================
# [설정]
# =================================================================
CONFIG = load_config(
    {
        "JSON_FILE": "service_account.json",
        "SHEET_NAME": "26양도매물",
        "TAB_CONSULT": "상담관리",
        "CONSULTANT_NAME": "강지현",
        "LEAD_STATE_FILE": "lead_intake_state.json",
        "LEAD_DUP_SCAN_ROWS": "250",
        "LEAD_DEFAULT_CHANNEL": "manual",
        "LEAD_FOLLOWUP_HOURS": "2",
    }
)

logger = setup_logger(name="lead_intake")

# 윈도우 콘솔 인코딩
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

CONSULT_HEADERS = [
    "접수일시",       # A
    "상담제목",       # B (match.py uses this)
    "상담내용",       # C (match.py uses this)
    "AI분석JSON",     # D (match.py uses this)
    "매칭결과",       # E (match.py uses this)
    "리드ID",         # F
    "상태",           # G
    "유입채널",       # H
    "고객명",         # I
    "연락처",         # J
    "업무유형",       # K
    "긴급도",         # L
    "다음액션",       # M
    "다음액션기한",   # N
    "담당자",         # O
    "원문출처",       # P
]


def _cfg_int(key: str, default: int) -> int:
    """Read *key* from CONFIG as ``int``; fall back to *default* on parse failure."""
    try:
        return int(str(CONFIG.get(key, default)).strip())
    except (ValueError, TypeError):
        return default


def _compact_text(text: object) -> str:
    """Collapse whitespace runs into a single space and strip."""
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _normalize_token(text: object) -> str:
    """Lower-case *text* and strip non-alphanumeric / non-Korean characters."""
    return re.sub(r"[^0-9a-z가-힣]+", "", str(text or "").lower())


def _safe_contact(value: object) -> str:
    """Format a Korean phone number with dashes (010-xxxx-xxxx) if valid."""
    s = str(value or "").strip()
    if not s:
        return ""
    only_num = re.sub(r"[^0-9]", "", s)
    if len(only_num) in (10, 11):
        if len(only_num) == 11:
            return f"{only_num[:3]}-{only_num[3:7]}-{only_num[7:]}"
        return f"{only_num[:3]}-{only_num[3:6]}-{only_num[6:]}"
    return s


def _lead_id(now: datetime | None = None) -> str:
    """Generate a timestamped lead identifier like ``LD20260311143012456``."""
    now = now or datetime.now()
    return f"LD{now.strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"


def _infer_intent(text: object) -> str:
    """Keyword-match *text* to a service intent (양도양수, 인허가, etc.)."""
    t = _normalize_token(text)
    rules = [
        ("양도양수", ["양도양수", "양도", "양수", "매물", "mna"]),
        ("인허가(신규등록)", ["인허가", "사전검토", "신규등록", "신규", "등록", "면허등록", "등록기준"]),
        ("기업진단", ["기업진단", "진단보고서", "재무진단"]),
        ("실질자본금", ["실질자본금", "자본금", "예치", "출자"]),
        ("분할합병", ["분할합병", "분할", "합병", "법인분할", "법인합병"]),
        ("행정처분", ["행정처분", "영업정지", "과징금", "처분"]),
        ("법인설립", ["법인설립", "법인", "정관", "등기"]),
        ("시평/기업진단", ["시공능력", "시평", "기업진단"]),
    ]
    for name, keys in rules:
        if any(k in t for k in keys):
            return name
    return "기타"


def _normalize_intent_label(value: object) -> str:
    """Canonicalize free-form intent text into a standard label (e.g. ``인허가(신규등록)``)."""
    text = _compact_text(value)
    token = _normalize_token(text)
    if any(k in token for k in ["인허가", "사전검토", "신규등록", "면허등록", "등록기준"]):
        return "인허가(신규등록)"
    if token == "신규":
        return "인허가(신규등록)"
    return text or "기타"


def _infer_urgency(text: object) -> str:
    """Classify *text* urgency as 긴급 / 보통 / 일반 via keyword matching."""
    t = _normalize_token(text)
    urgent = ["급함", "오늘", "당장", "바로", "긴급", "내일", "마감", "이번주"]
    medium = ["빠르게", "가능하면", "검토", "문의", "상담"]
    if any(k in t for k in urgent):
        return "긴급"
    if any(k in t for k in medium):
        return "보통"
    return "일반"


def _default_next_action(intent: str, urgency: str) -> str:
    """Return the recommended follow-up action for *intent* + *urgency*."""
    base = {
        "양도양수": "고객 조건(업종/예산/지역) 확인 후 추천 매물 3건 송부",
        "인허가(신규등록)": "업종별 인허가 등록기준 체크리스트와 필요서류 안내 송부",
        "신규등록": "업종별 인허가 등록기준 체크리스트와 필요서류 안내 송부",
        "기업진단": "재무자료 요청 후 기업진단 가능여부 사전 검토",
        "실질자본금": "예치/인정항목 점검표 전달 및 리스크 안내",
        "분할합병": "현재 법인 구조 확인 후 절차/비용 러프 견적 회신",
        "행정처분": "처분 이력/통지서 확인 후 대응 일정 제안",
        "법인설립": "설립 목적/업종 기준 확인 후 설립+등록 일정 안내",
        "시평/기업진단": "시평 목적 확인 후 기업진단/실적 전략 제안",
    }
    action = base.get(intent, "핵심 요구사항 재확인 후 맞춤 안내 회신")
    if urgency == "긴급":
        return action + " (당일 우선 응대)"
    return action


def _fingerprint(record: Dict[str, str]) -> str:
    """SHA-1 hash of normalised record fields for duplicate detection."""
    parts = [
        _normalize_token(record.get("title", "")),
        _normalize_token(record.get("content", "")),
        _normalize_token(record.get("contact", "")),
        _normalize_token(record.get("channel", "")),
    ]
    base = "|".join(parts)
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


_FORMULA_PREFIXES = frozenset("=+@-\t\r")
_MAX_CELL_LEN = 2000


def _defang_cell(value: str) -> str:
    """Escape spreadsheet formula prefixes to prevent formula injection."""
    if value and value[0] in _FORMULA_PREFIXES:
        return "'" + value
    return value


def _pick(source: Dict[str, Any], keys: Sequence[str]) -> str:
    """Return the first non-empty value from *source* for any of *keys*."""
    for key in keys:
        if key in source and str(source.get(key, "")).strip():
            return str(source[key]).strip()
    return ""


class LeadIntakeHub:
    """Google Sheets-backed lead ingestion hub for consultation requests."""

    def __init__(self) -> None:
        """Initialise from CONFIG; call :meth:`connect` before ingesting leads."""
        require_config(CONFIG, ["JSON_FILE", "SHEET_NAME", "TAB_CONSULT"], context="lead_intake:init")
        self.json_file = str(CONFIG["JSON_FILE"]).strip()
        self.sheet_name = str(CONFIG["SHEET_NAME"]).strip()
        self.tab_consult = str(CONFIG["TAB_CONSULT"]).strip()
        self.consultant = str(CONFIG.get("CONSULTANT_NAME", "담당자")).strip() or "담당자"
        self.state_file = str(CONFIG.get("LEAD_STATE_FILE", "lead_intake_state.json")).strip()
        self.dup_scan_rows = max(50, _cfg_int("LEAD_DUP_SCAN_ROWS", 250))
        self.followup_hours = max(1, _cfg_int("LEAD_FOLLOWUP_HOURS", 2))

        self.client = None
        self.sheet = None
        self.ws = None

        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load the duplicate-fingerprint state from disk (returns empty on error)."""
        if not self.state_file or not os.path.exists(self.state_file):
            return {"fingerprints": {}}
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {"fingerprints": {}}
            if "fingerprints" not in data or not isinstance(data["fingerprints"], dict):
                data["fingerprints"] = {}
            return data
        except (json.JSONDecodeError, OSError):
            return {"fingerprints": {}}

    def _save_state(self) -> None:
        """Persist fingerprint state to disk with an ``updated_at`` timestamp."""
        self.state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def connect(self) -> None:
        """Authenticate via service-account credentials and open the target Google Sheet.

        Must be called before :meth:`intake_one` or :meth:`intake_csv`.
        Creates or validates the header row on the active worksheet.
        """
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.json_file, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open(self.sheet_name)
        self.ws = self.sheet.worksheet(self.tab_consult)
        self._ensure_header()

    def _ensure_header(self) -> None:
        """Ensure the worksheet header row matches ``CONSULT_HEADERS`` (auto-repair)."""
        row1 = self.ws.row_values(1)
        if not row1:
            self.ws.update(range_name="A1:P1", values=[CONSULT_HEADERS])
            return

        if len(row1) < len(CONSULT_HEADERS):
            fixed = row1 + [""] * (len(CONSULT_HEADERS) - len(row1))
            for i, head in enumerate(CONSULT_HEADERS):
                if not fixed[i]:
                    fixed[i] = head
            self.ws.update(range_name="A1:P1", values=[fixed])
            return

        if row1[:5] != CONSULT_HEADERS[:5]:
            # match.py 호환성 보장을 위해 최소 앞 5개는 강제 고정
            merged = row1[:]
            for i in range(5):
                merged[i] = CONSULT_HEADERS[i]
            self.ws.update(range_name="A1:P1", values=[merged[:16]])

    def _is_duplicate(self, record: Dict[str, str]) -> Tuple[bool, str]:
        """Check in-memory state + last *dup_scan_rows* sheet rows for duplicates."""
        fp = _fingerprint(record)
        if fp in self.state.get("fingerprints", {}):
            return True, fp

        rows = self.ws.get_all_values()
        if len(rows) > 1:
            scan_rows = rows[-self.dup_scan_rows :]
            for row in scan_rows:
                row_record = {
                    "title": row[1] if len(row) > 1 else "",
                    "content": row[2] if len(row) > 2 else "",
                    "channel": row[7] if len(row) > 7 else "",
                    "contact": row[9] if len(row) > 9 else "",
                }
                if _fingerprint(row_record) == fp:
                    self.state.setdefault("fingerprints", {})[fp] = {
                        "lead_id": row[5] if len(row) > 5 else "",
                        "timestamp": row[0] if len(row) > 0 else "",
                    }
                    self._save_state()
                    return True, fp

        return False, fp

    def intake_one(self, payload: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """Ingest a single lead record into the sheet.

        Checks for duplicates via content fingerprint, assigns a lead ID,
        and appends a row.  Returns ``{"status": "inserted", "lead_id": ...}``
        on success, or ``"skipped"``/``"duplicate"`` status dicts otherwise.
        """
        now = datetime.now()
        title = _compact_text(payload.get("title", ""))[:_MAX_CELL_LEN]
        content = _compact_text(payload.get("content", ""))[:_MAX_CELL_LEN]
        if not title and not content:
            return {"status": "skipped", "reason": "empty"}

        channel = (_compact_text(payload.get("channel", "")) or str(CONFIG.get("LEAD_DEFAULT_CHANNEL", "manual")))[:200]
        customer_name = _compact_text(payload.get("customer_name", ""))[:200]
        contact = _safe_contact(payload.get("contact", ""))[:50]
        source = _compact_text(payload.get("source", ""))[:500]

        merged_text = f"{title} {content}"
        intent_raw = _compact_text(payload.get("intent", "")) or _infer_intent(merged_text)
        intent = _normalize_intent_label(intent_raw)
        urgency = _compact_text(payload.get("urgency", "")) or _infer_urgency(merged_text)
        next_action = _compact_text(payload.get("next_action", "")) or _default_next_action(intent, urgency)

        due_hours = 1 if urgency == "긴급" else self.followup_hours
        due_at = (now + timedelta(hours=due_hours)).strftime("%Y-%m-%d %H:%M")
        lead_id = _lead_id(now)

        record = {
            "title": title,
            "content": content,
            "channel": channel,
            "contact": contact,
        }

        is_dup, fp = self._is_duplicate(record)
        if is_dup:
            return {"status": "duplicate", "lead_id": self.state.get("fingerprints", {}).get(fp, {}).get("lead_id", "")}

        row = [
            now.strftime("%Y-%m-%d %H:%M"),
            _defang_cell(title),
            _defang_cell(content),
            "",
            "",
            lead_id,
            "신규",
            _defang_cell(channel),
            _defang_cell(customer_name),
            _defang_cell(contact),
            intent,
            urgency,
            next_action,
            due_at,
            self.consultant,
            _defang_cell(source),
        ]

        if dry_run:
            return {"status": "dry_run", "lead_id": lead_id, "row": row}

        self.ws.append_row(row, value_input_option="RAW")

        self.state.setdefault("fingerprints", {})[fp] = {
            "lead_id": lead_id,
            "timestamp": row[0],
            "channel": channel,
        }
        self._save_state()

        return {"status": "inserted", "lead_id": lead_id}

    def intake_csv(self, path: str, default_channel: str = "", dry_run: bool = False, limit: int = 0) -> Dict[str, int]:
        """Batch-import lead records from a CSV file.

        Tries UTF-8-BOM, CP949, and UTF-8 encodings in order.  Maps
        Korean/English column headers to canonical field names.  Returns
        a summary dict with ``total``, ``inserted``, ``duplicated``,
        and ``skipped`` counts.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        encodings = ["utf-8-sig", "cp949", "utf-8"]
        data_rows = None
        last_error = None

        for enc in encodings:
            try:
                with open(path, "r", encoding=enc, newline="") as f:
                    reader = csv.DictReader(f)
                    data_rows = list(reader)
                break
            except (UnicodeDecodeError, csv.Error, OSError) as e:
                last_error = e

        if data_rows is None:
            raise RuntimeError(f"CSV 로드 실패: {last_error}")

        inserted = 0
        duplicated = 0
        skipped = 0

        for i, src in enumerate(data_rows, start=1):
            if limit and i > limit:
                break

            payload = {
                "title": _pick(src, ["상담제목", "제목", "title", "subject"]),
                "content": _pick(src, ["상담내용", "내용", "content", "body", "memo", "메모"]),
                "channel": _pick(src, ["유입채널", "채널", "channel"]) or default_channel,
                "customer_name": _pick(src, ["고객명", "이름", "name", "customer_name"]),
                "contact": _pick(src, ["연락처", "전화", "phone", "contact"]),
                "source": _pick(src, ["원문출처", "출처", "source"]),
                "intent": _pick(src, ["업무유형", "intent"]),
                "urgency": _pick(src, ["긴급도", "urgency"]),
                "next_action": _pick(src, ["다음액션", "next_action"]),
            }

            out = self.intake_one(payload, dry_run=dry_run)
            status = out.get("status")
            if status in {"inserted", "dry_run"}:
                inserted += 1
            elif status == "duplicate":
                duplicated += 1
            else:
                skipped += 1

        return {
            "inserted": inserted,
            "duplicated": duplicated,
            "skipped": skipped,
            "total": inserted + duplicated + skipped,
        }


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for single-record and CSV-batch modes."""
    parser = argparse.ArgumentParser(description="상담 인입 허브: 상담 기록을 Google Sheet 상담관리 탭에 적재")
    parser.add_argument("--title", help="상담 제목")
    parser.add_argument("--content", help="상담 내용")
    parser.add_argument("--channel", default="", help="유입 채널 (예: kakao, phone, mail, naver_ad)")
    parser.add_argument("--customer", default="", help="고객명")
    parser.add_argument("--contact", default="", help="연락처")
    parser.add_argument("--source", default="", help="원문 출처 URL/메모")

    parser.add_argument("--csv", dest="csv_path", default="", help="일괄 업로드용 CSV 파일 경로")
    parser.add_argument("--limit", type=int, default=0, help="CSV 처리 최대 건수")

    parser.add_argument("--dry-run", action="store_true", help="시트에 쓰지 않고 처리 결과만 확인")
    parser.add_argument("--run-match", action="store_true", help="run match.py after successful ingest")
    parser.add_argument("--sample-csv", action="store_true", help="샘플 CSV 템플릿 생성")
    parser.add_argument("--sample-path", default="lead_intake_sample.csv", help="샘플 CSV 저장 경로")
    return parser


def _write_sample_csv(path: str) -> None:
    """Generate a 2-row sample CSV template at *path* for batch import."""
    rows = [
        {
            "상담제목": "전기공사업 양도양수 문의",
            "상담내용": "서울권, 예산 2.5억 내외, 빠른 진행 희망",
            "유입채널": "kakao",
            "고객명": "홍길동",
            "연락처": "01012345678",
            "원문출처": "https://open.kakao.com/o/example",
        },
        {
            "상담제목": "인허가(신규등록) 절차 및 필요서류",
            "상담내용": "기계설비 업종 신규 등록 상담 원합니다.",
            "유입채널": "phone",
            "고객명": "김대표",
            "연락처": "010-2222-3333",
            "원문출처": "인바운드 전화",
        },
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["상담제목", "상담내용", "유입채널", "고객명", "연락처", "원문출처"],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """CLI entry point for lead intake — single record or CSV batch import."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.sample_csv:
        _write_sample_csv(args.sample_path)
        print(f"sample csv created: {args.sample_path}")
        return

    has_single = bool(_compact_text(args.title) or _compact_text(args.content))
    has_csv = bool(_compact_text(args.csv_path))

    if not has_single and not has_csv:
        parser.print_help()
        return

    hub = LeadIntakeHub()
    hub.connect()

    if has_csv:
        summary = hub.intake_csv(
            path=args.csv_path,
            default_channel=args.channel,
            dry_run=args.dry_run,
            limit=max(0, args.limit),
        )
        msg = (
            f"csv processed: total {summary['total']} / "
            f"inserted {summary['inserted']} / duplicate {summary['duplicated']} / skipped {summary['skipped']}"
        )
        print(msg)
        logger.info(msg)

    if has_single:
        out = hub.intake_one(
            {
                "title": args.title,
                "content": args.content,
                "channel": args.channel,
                "customer_name": args.customer,
                "contact": args.contact,
                "source": args.source,
            },
            dry_run=args.dry_run,
        )

        status = out.get("status")
        if status == "inserted":
            msg = f"intake inserted: lead_id={out.get('lead_id')}"
        elif status == "duplicate":
            msg = f"intake duplicate skipped: lead_id={out.get('lead_id')}"
        elif status == "dry_run":
            msg = f"dry-run ok: lead_id={out.get('lead_id')}"
        else:
            msg = "no valid payload; skipped"

        print(msg)
        logger.info(msg)

    if args.run_match:
        if args.dry_run:
            print("run-match skipped in dry-run mode")
        else:
            try:
                _match_path = str(Path(__file__).resolve().parent.parent / "ALL" / "match.py")
                result = subprocess.run([sys.executable, _match_path], check=False)
                print(f"match.py finished with exit code {result.returncode}")
            except (OSError, ValueError) as e:
                print(f"failed to run match.py: {e}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(str(e))
        raise SystemExit(1)

