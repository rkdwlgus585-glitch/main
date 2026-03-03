from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tistory_ops.client import TistoryClient


def run(args: argparse.Namespace) -> int:
    client = TistoryClient(blog_name=args.blog_name)
    if args.command == "info":
        payload = client.blog_info()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.command == "categories":
        rows = client.list_categories()
        print(json.dumps({"count": len(rows), "categories": rows}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "posts":
        rows = client.list_posts(page=args.page, count=args.count)
        print(json.dumps({"count": len(rows), "posts": rows}, ensure_ascii=False, indent=2))
        return 0
    raise ValueError(f"unknown command: {args.command}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Tistory admin helper")
    parser.add_argument("command", choices=["info", "categories", "posts"])
    parser.add_argument("--blog-name", default="", help="tistory blog name override")
    parser.add_argument("--page", type=int, default=1, help="post list page")
    parser.add_argument("--count", type=int, default=10, help="post list count")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

