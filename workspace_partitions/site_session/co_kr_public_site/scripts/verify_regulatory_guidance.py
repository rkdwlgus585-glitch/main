#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GUIDANCE_PATH = PROJECT_ROOT / "lib" / "regulatory-guidance.ts"
YEAR_SENSITIVE_FILES = [
    PROJECT_ROOT / "lib" / "regulatory-guidance.ts",
    PROJECT_ROOT / "components" / "public-home.tsx",
    PROJECT_ROOT / "components" / "legal-update-section.tsx",
    PROJECT_ROOT / "app" / "registration" / "page.tsx",
    PROJECT_ROOT / "app" / "corporate" / "page.tsx",
    PROJECT_ROOT / "app" / "split-merger" / "page.tsx",
    PROJECT_ROOT / "app" / "practice" / "page.tsx",
]
YEAR_SCAN_ROOTS = [
    PROJECT_ROOT / "app",
    PROJECT_ROOT / "components",
    PROJECT_ROOT / "lib",
]
YEAR_SCAN_EXCLUDED_FILES = {
    PROJECT_ROOT / "components" / "sample-data.ts",
    PROJECT_ROOT / "components" / "site-config.ts",
    PROJECT_ROOT / "lib" / "legacy-types.ts",
    PROJECT_ROOT / "lib" / "legacy-content.ts",
}
ALLOWED_HISTORICAL_YEARS = {
    PROJECT_ROOT / "lib" / "regulatory-guidance.ts": {2025},
    PROJECT_ROOT / "app" / "registration" / "page.tsx": {2025},
}
REVIEW_WINDOW_DAYS = 120


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify regulatory guidance freshness and official links.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="HTTP timeout per link in seconds.",
    )
    return parser.parse_args()


def build_session() -> requests.Session:
    retry = Retry(
        total=2,
        read=2,
        connect=2,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; SeoulMnaRegulatoryChecker/1.0)",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        }
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_reviewed_at(source: str) -> datetime:
    match = re.search(r'export const regulatoryReviewedAt = "(\d{4})\.(\d{2})\.(\d{2})";', source)
    if not match:
        raise ValueError("regulatoryReviewedAt not found in regulatory-guidance.ts")

    return datetime.strptime("".join(match.groups()), "%Y%m%d")


def parse_links(source: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r'label:\s*"(?P<label>[^"]+)"\s*,\s*href:\s*"(?P<href>https://[^"]+)"',
        re.MULTILINE,
    )
    return [match.groupdict() for match in pattern.finditer(source)]


def extract_year_tokens(path: Path) -> list[int]:
    content = read_text(path)
    content = re.sub(r"https://\S+", "", content)
    matches = re.findall(r"(?<![\d.])(20\d{2})(?![\d.])", content)
    return sorted({int(value) for value in matches})


def iter_year_scan_files() -> list[Path]:
    files: list[Path] = []
    for root in YEAR_SCAN_ROOTS:
        for path in root.rglob("*"):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            if path in YEAR_SCAN_EXCLUDED_FILES:
                continue
            files.append(path)
    return sorted(files)


def check_link(session: requests.Session, url: str, timeout: int) -> int:
    try:
        response = session.head(url, timeout=timeout, allow_redirects=True)
        if response.status_code >= 400 or response.status_code == 405:
            response = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
        return response.status_code
    except requests.RequestException as exc:
        raise RuntimeError(str(exc)) from exc


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    source = read_text(GUIDANCE_PATH)
    reviewed_at = parse_reviewed_at(source)
    links = parse_links(source)
    today = datetime.now()
    age_days = (today - reviewed_at).days
    review_due = age_days > REVIEW_WINDOW_DAYS
    session = build_session()

    if review_due:
        errors.append(
            f"regulatory guidance review is stale: reviewed {age_days} days ago on {reviewed_at.date()} "
            f"(limit {REVIEW_WINDOW_DAYS} days)"
        )
    elif age_days > REVIEW_WINDOW_DAYS - 30:
        warnings.append(
            f"regulatory guidance review is due soon: reviewed {age_days} days ago on {reviewed_at.date()}"
        )

    current_year = today.year
    for path in YEAR_SENSITIVE_FILES:
        years = extract_year_tokens(path)
        allowed_years = ALLOWED_HISTORICAL_YEARS.get(path, set())
        invalid_years = [year for year in years if year != current_year and year not in allowed_years]
        if invalid_years:
            errors.append(
                f"{path.relative_to(PROJECT_ROOT)} contains year-specific text not matching {current_year}: "
                + ", ".join(str(year) for year in invalid_years)
            )

    monitored_files = set(YEAR_SENSITIVE_FILES) | set(YEAR_SCAN_EXCLUDED_FILES)
    for path in iter_year_scan_files():
        if path in monitored_files:
            continue
        years = extract_year_tokens(path)
        if years:
            warnings.append(
                f"{path.relative_to(PROJECT_ROOT)} contains year-sensitive text outside the monitored set: "
                + ", ".join(str(year) for year in years)
            )

    link_results: list[dict[str, Any]] = []
    for link in links:
        try:
            status_code = check_link(session, link["href"], args.timeout)
            if status_code >= 400:
                errors.append(f"link check failed for {link['label']}: HTTP {status_code}")
            link_results.append({**link, "status": status_code})
        except RuntimeError as exc:
            errors.append(f"link check failed for {link['label']}: {exc}")
            link_results.append({**link, "status": "error", "error": str(exc)})

    payload = {
        "reviewedAt": reviewed_at.date().isoformat(),
        "ageDays": age_days,
        "reviewWindowDays": REVIEW_WINDOW_DAYS,
        "currentYear": current_year,
        "linksChecked": len(link_results),
        "warnings": warnings,
        "errors": errors,
    }

    if errors:
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
