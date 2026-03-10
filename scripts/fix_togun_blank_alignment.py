from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Sequence

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
_ALL_DIR = os.path.abspath(os.path.join(ROOT_DIR, "..", "ALL"))  # H:\ALL (non-core modules)
if _ALL_DIR not in sys.path:
    sys.path.insert(0, _ALL_DIR)

import all


TOK_TOGUN = "\ud1a0\uac74"
FIELD_TO_COL = {
    "license": 2,       # C
    "license_year": 3,  # D
    "specialty": 4,     # E
    "y20": 5,           # F
    "y21": 6,           # G
    "y22": 7,           # H
    "y23": 8,           # I
    "y24": 9,           # J
    "y25": 12,          # M
}
YEAR_FIELDS = ("y20", "y21", "y22", "y23", "y24", "y25")


@dataclass
class Candidate:
    row_idx: int
    uid: str
    wr_id: str
    row_values: List[str]


def _row_text(row: Sequence[str], idx: int) -> str:
    if idx < 0 or idx >= len(row):
        return ""
    return str(row[idx] or "")


def _split_lines(text: str) -> List[str]:
    src = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    return src.split("\n")


def _compact_lines(text: str) -> List[str]:
    return [x.strip() for x in _split_lines(text) if x.strip()]


def _contains_togun_first_line(license_text: str) -> bool:
    lines = _split_lines(license_text)
    if not lines:
        return False
    return TOK_TOGUN in (lines[0] or "")


def _parse_uids(raw: str) -> set[str]:
    txt = str(raw or "").strip()
    if not txt:
        return set()
    out = set()
    for token in txt.replace(",", " ").split():
        uid = token.strip()
        if uid:
            out.add(uid)
    return out


def _find_candidates(all_values: List[List[str]], uid_filter: set[str]) -> List[Candidate]:
    out: List[Candidate] = []
    for row_idx, row in enumerate(all_values[1:], start=2):
        uid = _row_text(row, 34).strip()
        if not uid:
            continue
        if uid_filter and uid not in uid_filter:
            continue
        license_text = _row_text(row, FIELD_TO_COL["license"])
        if not _contains_togun_first_line(license_text):
            continue

        # Candidate only when at least one year cell has multiple lines
        # and is missing a leading blank line.
        suspicious = False
        for field in YEAR_FIELDS:
            cell = _row_text(row, FIELD_TO_COL[field])
            if "\n" not in cell:
                continue
            if cell.startswith("\n"):
                continue
            suspicious = True
            break
        if not suspicious:
            continue

        out.append(
            Candidate(
                row_idx=row_idx,
                uid=uid,
                wr_id=_row_text(row, 0).strip(),
                row_values=list(row),
            )
        )
    return out


def _needs_blank_alignment_fix(row_values: Sequence[str], source_item: Dict[str, str]) -> bool:
    for field in YEAR_FIELDS:
        src = str(source_item.get(field, "") or "")
        cur = _row_text(row_values, FIELD_TO_COL[field])
        if not src.startswith("\n"):
            continue
        if cur.startswith("\n"):
            continue
        # We only treat this as blank-loss when non-empty values are otherwise aligned.
        if _compact_lines(src) == _compact_lines(cur):
            return True
    return False


def _build_c_to_m_segment(row_values: Sequence[str], source_item: Dict[str, str]) -> List[str]:
    base = list(row_values or [])
    if len(base) < 13:
        base.extend([""] * (13 - len(base)))
    for field, col in FIELD_TO_COL.items():
        base[col] = str(source_item.get(field, "") or "")
    return base[2:13]  # C..M


def _make_driver() -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1440,2400")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Repair Google Sheet rows where 토건 first-line blank sales got collapsed."
    )
    ap.add_argument("--uids", type=str, default="", help="Comma/space separated UID list to limit scope")
    ap.add_argument("--limit", type=int, default=0, help="Max candidate rows to inspect (0=all)")
    ap.add_argument("--delay-sec", type=float, default=0.0, help="Delay between apply updates")
    ap.add_argument("--apply", action="store_true", help="Apply updates (default is dry-run)")
    args = ap.parse_args()

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(all.JSON_FILE, scope)
    worksheet = gspread.authorize(creds).open(all.SHEET_NAME).sheet1
    all_values = worksheet.get_all_values()

    uid_filter = _parse_uids(args.uids)
    candidates = _find_candidates(all_values, uid_filter)
    if args.limit and args.limit > 0:
        candidates = candidates[: args.limit]

    print(f"candidates={len(candidates)} apply={bool(args.apply)}")
    if not candidates:
        return 0

    driver = _make_driver()
    inspected = 0
    planned = 0
    applied = 0
    skipped = 0
    failed = 0
    try:
        for idx, cand in enumerate(candidates, start=1):
            inspected += 1
            try:
                source_link = all._safe_nowmna_detail_link(cand.uid)
                source_item = all._extract_item_from_detail_link(driver, source_link)
                if not _needs_blank_alignment_fix(cand.row_values, source_item):
                    skipped += 1
                    print(f"[{idx}/{len(candidates)}] uid={cand.uid} row={cand.row_idx} skip=no-blank-loss")
                    continue

                segment = _build_c_to_m_segment(cand.row_values, source_item)
                planned += 1
                if not args.apply:
                    print(f"[{idx}/{len(candidates)}] uid={cand.uid} row={cand.row_idx} plan=update")
                    continue

                rng = f"C{cand.row_idx}:M{cand.row_idx}"
                worksheet.update(range_name=rng, values=[segment])
                applied += 1
                print(f"[{idx}/{len(candidates)}] uid={cand.uid} row={cand.row_idx} updated")
                if args.delay_sec > 0:
                    time.sleep(float(args.delay_sec))
            except Exception as ex:
                failed += 1
                print(f"[{idx}/{len(candidates)}] uid={cand.uid} row={cand.row_idx} failed={ex}")
    finally:
        all._safe_quit(driver)

    print(
        f"done inspected={inspected} planned={planned} applied={applied} "
        f"skipped={skipped} failed={failed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
