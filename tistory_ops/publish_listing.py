from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gabji
from utils import load_config

from tistory_ops.client import TistoryClient
from tistory_ops.listing_template import build_listing_content, build_listing_title

CONFIG = load_config(
    {
        "TISTORY_DEFAULT_CATEGORY_ID": "",
        "TISTORY_DEFAULT_VISIBILITY": "3",
        "TISTORY_DEFAULT_TAGS": "서울건설정보,건설양도양수,법인양도",
        "TISTORY_SOURCE_URL_TEMPLATE": "http://www.nowmna.com/yangdo_view1.php?uid={uid}&page_no=1",
    }
)


def _load_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig") as f:
        obj = json.load(f)
    return obj if isinstance(obj, dict) else {}


def _digits(value: Any) -> str:
    import re

    return re.sub(r"\D+", "", str(value or ""))


def _resolve_source_url(data: dict[str, Any], override_source: str = "") -> str:
    if str(override_source or "").strip():
        return str(override_source).strip()
    reg = str(
        data.get("등록번호")
        or data.get("registration_no")
        or data.get("registration")
        or data.get("?깅줉踰덊샇")
        or ""
    ).strip()
    uid = _digits(reg)
    if not uid:
        return ""
    template = str(CONFIG.get("TISTORY_SOURCE_URL_TEMPLATE", "")).strip()
    if "{uid}" not in template:
        template = "http://www.nowmna.com/yangdo_view1.php?uid={uid}&page_no=1"
    return template.format(uid=uid)


def _load_listing_data(args: argparse.Namespace) -> dict[str, Any]:
    if args.registration:
        lookup = gabji.ListingSheetLookup()
        return lookup.load_listing(args.registration)
    if args.image:
        generator = gabji.GabjiGenerator()
        return generator.analyze_image(args.image)
    if args.json_input:
        return _load_json(args.json_input)
    raise ValueError("one of --registration, --image, --json-input is required")


def _to_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return int(default)


def _resolve_category(client: TistoryClient | None, category_id: str, category_name: str) -> int | None:
    if str(category_id or "").strip():
        return _to_int(category_id, 0) or None
    fallback = str(CONFIG.get("TISTORY_DEFAULT_CATEGORY_ID", "")).strip()
    if fallback:
        return _to_int(fallback, 0) or None
    if client and str(category_name or "").strip():
        return client.find_category_id(category_name)
    return None


def run(args: argparse.Namespace) -> int:
    data = _load_listing_data(args)
    source_url = _resolve_source_url(data, args.source_url)
    title = str(args.title or "").strip() or build_listing_title(data)
    image_urls = [str(x).strip() for x in (args.image_url or []) if str(x).strip()]
    content = build_listing_content(data, source_url=source_url, image_urls=image_urls)

    out_html = str(args.out_html or "").strip()
    if out_html:
        out_path = Path(out_html)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(f"[saved] html: {out_path}")

    visibility = _to_int(args.visibility or CONFIG.get("TISTORY_DEFAULT_VISIBILITY", "3"), 3)
    payload_preview = {
        "title": title,
        "visibility": visibility,
        "category_id": args.category_id or CONFIG.get("TISTORY_DEFAULT_CATEGORY_ID", ""),
        "category_name": args.category_name,
        "published": args.published,
        "tags": args.tags or CONFIG.get("TISTORY_DEFAULT_TAGS", ""),
        "accept_comment": _to_int(args.accept_comment, 1),
        "source_url": source_url,
        "content_length": len(content),
    }
    if args.print_payload:
        print(json.dumps(payload_preview, ensure_ascii=False, indent=2))

    if args.dry_run:
        print("[dry-run] tistory publish skipped")
        return 0

    client = TistoryClient(blog_name=args.blog_name)
    upload_urls: list[str] = []
    for file_path in args.upload_file or []:
        attach = client.attach_file(file_path)
        if attach.get("url"):
            upload_urls.append(str(attach.get("url")))
        elif attach.get("replacer"):
            upload_urls.append(str(attach.get("replacer")))
    if upload_urls:
        content = build_listing_content(data, source_url=source_url, image_urls=image_urls + upload_urls)

    category = _resolve_category(client, args.category_id, args.category_name)
    result = client.write_post(
        title=title,
        content=content,
        visibility=visibility,
        category_id=category,
        published=str(args.published or "").strip(),
        tags=str(args.tags or CONFIG.get("TISTORY_DEFAULT_TAGS", "")).strip(),
        accept_comment=_to_int(args.accept_comment, 1),
        password=str(args.password or "").strip(),
        slogan=str(args.slogan or "").strip(),
    )
    print(
        json.dumps(
            {
                "ok": True,
                "post_id": result.get("post_id", ""),
                "category_id": category,
                "uploaded_count": len(upload_urls),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish listing post to Tistory (seoulmna.tistory.com)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--registration", help="sheet registration number (e.g. 7540)")
    group.add_argument("--json-input", help="gabji-like json input path")
    group.add_argument("--image", help="gabji screenshot image path (Gemini key required)")

    parser.add_argument("--blog-name", default="", help="tistory blog name (default from .env)")
    parser.add_argument("--title", default="", help="override post title")
    parser.add_argument("--source-url", default="", help="source url override")
    parser.add_argument("--category-id", default="", help="category id")
    parser.add_argument("--category-name", default="", help="category name to resolve automatically")
    parser.add_argument("--visibility", default="", help="0 private, 1 protected, 3 public")
    parser.add_argument("--published", default="", help="unix epoch or YYYYMMDDHHMM style value")
    parser.add_argument("--tags", default="", help="comma-separated tags")
    parser.add_argument("--accept-comment", default="1", help="1 allow, 0 disallow")
    parser.add_argument("--password", default="", help="protected post password")
    parser.add_argument("--slogan", default="", help="post permalink slug")
    parser.add_argument("--image-url", action="append", default=[], help="image URL to include in content (repeatable)")
    parser.add_argument("--upload-file", action="append", default=[], help="local image file upload to tistory attach API")
    parser.add_argument("--out-html", default="", help="save html preview to file")
    parser.add_argument("--print-payload", action="store_true", help="print publish payload preview")
    parser.add_argument("--dry-run", action="store_true", help="build html only; do not publish")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

