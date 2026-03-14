#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "imported"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"

MANIFEST_FILES = {
    "listingSummaries": "listing-summaries.json",
    "listingDetails": "listing-details.json",
    "noticePosts": "notice-posts.json",
    "premiumPosts": "premium-posts.json",
    "newsPosts": "news-posts.json",
    "tlFaqPage": "tl-faq-page.json",
    "pages": "pages.json",
}

COUNT_MAP = {
    "mna": "listingSummaries",
    "notice": "noticePosts",
    "premium": "premiumPosts",
    "news": "newsPosts",
    "tl_faq": "tlFaqPage",
    "pages": "pages",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify imported seoulmna.co.kr content integrity.")
    parser.add_argument(
        "--sync-manifest",
        action="store_true",
        help="Rewrite manifest file metadata from current imported files before verification.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_records(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        return 1
    return 0


def compute_file_manifest() -> dict[str, dict[str, Any]]:
    files: dict[str, dict[str, Any]] = {}

    for key, filename in MANIFEST_FILES.items():
        path = OUTPUT_DIR / filename
        if not path.exists():
            continue

        payload = load_json(path)
        files[key] = {
            "path": f"data/imported/{filename}",
            "bytes": path.stat().st_size,
            "sha256": file_sha256(path),
            "records": count_records(payload),
        }

    return files


def expect_unique(values: list[str], label: str, errors: list[str]) -> None:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1

    duplicates = sorted(value for value, count in counts.items() if value and count > 1)
    if duplicates:
        sample = ", ".join(duplicates[:5])
        errors.append(f"{label} contains duplicate keys: {sample}")


def main() -> int:
    args = parse_args()

    if not MANIFEST_PATH.exists():
        print(f"[error] manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        return 1

    manifest = load_json(MANIFEST_PATH)

    if args.sync_manifest:
        manifest["files"] = compute_file_manifest()
        write_json(MANIFEST_PATH, manifest)
        print("[sync] manifest file metadata refreshed")

    counts = manifest.get("counts", {})
    files = manifest.get("files", {})
    errors: list[str] = []
    payloads: dict[str, Any] = {}

    for key, filename in MANIFEST_FILES.items():
        path = OUTPUT_DIR / filename
        if not path.exists():
            errors.append(f"missing imported file: data/imported/{filename}")
            continue

        payload = load_json(path)
        payloads[key] = payload
        file_entry = files.get(key)
        actual_path = f"data/imported/{filename}"
        actual_bytes = path.stat().st_size
        actual_sha256 = file_sha256(path)
        actual_records = count_records(payload)

        if not isinstance(file_entry, dict):
            errors.append(f"manifest missing file metadata for {key}")
            continue

        if file_entry.get("path") != actual_path:
            errors.append(f"{key} manifest path mismatch: {file_entry.get('path')} != {actual_path}")
        if file_entry.get("bytes") != actual_bytes:
            errors.append(f"{key} byte size mismatch: {file_entry.get('bytes')} != {actual_bytes}")
        if file_entry.get("sha256") != actual_sha256:
            errors.append(f"{key} sha256 mismatch")
        if file_entry.get("records") != actual_records:
            errors.append(f"{key} record count mismatch: {file_entry.get('records')} != {actual_records}")

    for count_key, file_key in COUNT_MAP.items():
        payload = payloads.get(file_key)
        if payload is None:
            continue

        actual_count = count_records(payload)
        manifest_count = counts.get(count_key)
        if manifest_count != actual_count:
            errors.append(f"manifest counts.{count_key} mismatch: {manifest_count} != {actual_count}")

    listing_summaries = payloads.get("listingSummaries", [])
    listing_details = payloads.get("listingDetails", [])
    if isinstance(listing_summaries, list) and isinstance(listing_details, list):
        summary_ids = [str(item.get("id", "")).strip() for item in listing_summaries]
        detail_ids = [str(item.get("id", "")).strip() for item in listing_details]
        expect_unique(summary_ids, "listing summaries", errors)
        expect_unique(detail_ids, "listing details", errors)
        if len(summary_ids) != len(detail_ids):
            errors.append(f"listing summary/detail length mismatch: {len(summary_ids)} != {len(detail_ids)}")
        elif summary_ids != detail_ids:
            errors.append("listing summary/detail ordering mismatch")

    for file_key, label in (
        ("noticePosts", "notice posts"),
        ("premiumPosts", "premium posts"),
        ("newsPosts", "news posts"),
    ):
        payload = payloads.get(file_key, [])
        if isinstance(payload, list):
            expect_unique([str(item.get("id", "")).strip() for item in payload], label, errors)

    pages_payload = payloads.get("pages", [])
    if isinstance(pages_payload, list):
        expect_unique([str(item.get("slug", "")).strip() for item in pages_payload], "legacy pages", errors)

    if errors:
        print("[fail] imported content verification failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    summary = {
        "counts": counts,
        "filesVerified": len(MANIFEST_FILES),
        "generatedAt": manifest.get("generatedAt"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
