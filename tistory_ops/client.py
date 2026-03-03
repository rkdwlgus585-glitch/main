from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils import load_config, require_config

CONFIG = load_config(
    {
        "TISTORY_API_BASE": "https://www.tistory.com/apis",
        "TISTORY_ACCESS_TOKEN": "",
        "TISTORY_BLOG_NAME": "seoulmna",
        "TISTORY_DEFAULT_CATEGORY_ID": "",
        "TISTORY_DEFAULT_VISIBILITY": "3",
        "TISTORY_TIMEOUT_SEC": "20",
    }
)


def _to_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return int(default)


class TistoryClient:
    def __init__(self, access_token: str = "", blog_name: str = "", timeout_sec: int | None = None):
        self.access_token = str(access_token or CONFIG.get("TISTORY_ACCESS_TOKEN", "")).strip()
        self.blog_name = str(blog_name or CONFIG.get("TISTORY_BLOG_NAME", "")).strip()
        self.api_base = str(CONFIG.get("TISTORY_API_BASE", "https://www.tistory.com/apis")).rstrip("/")
        self.timeout_sec = int(timeout_sec or _to_int(CONFIG.get("TISTORY_TIMEOUT_SEC", 20), 20))
        require_config(
            {
                "TISTORY_ACCESS_TOKEN": self.access_token,
                "TISTORY_BLOG_NAME": self.blog_name,
            },
            ["TISTORY_ACCESS_TOKEN", "TISTORY_BLOG_NAME"],
            context="tistory",
        )

    def _url(self, endpoint: str) -> str:
        ep = str(endpoint or "").strip().lstrip("/")
        return f"{self.api_base}/{ep}"

    def _parse_json(self, resp: requests.Response) -> dict[str, Any]:
        try:
            payload = resp.json()
        except Exception as exc:
            body = (resp.text or "")[:500]
            raise RuntimeError(f"tistory response is not JSON: status={resp.status_code}, body={body}") from exc
        tistory_block = payload.get("tistory", {}) if isinstance(payload, dict) else {}
        status = str(tistory_block.get("status", ""))
        if resp.status_code >= 400 or status != "200":
            message = tistory_block.get("error_message") or tistory_block.get("message") or resp.text
            raise RuntimeError(f"tistory api error: http={resp.status_code}, status={status}, msg={message}")
        return payload

    def _auth_payload(self) -> dict[str, Any]:
        return {"access_token": self.access_token, "output": "json"}

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = self._auth_payload()
        if params:
            payload.update(params)
        resp = requests.get(self._url(endpoint), params=payload, timeout=self.timeout_sec)
        return self._parse_json(resp)

    def post(self, endpoint: str, data: dict[str, Any] | None = None, files: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = self._auth_payload()
        if data:
            payload.update(data)
        resp = requests.post(self._url(endpoint), data=payload, files=files, timeout=self.timeout_sec)
        return self._parse_json(resp)

    def blog_info(self) -> dict[str, Any]:
        return self.get("blog/info", {"blogName": self.blog_name})

    def list_categories(self) -> list[dict[str, Any]]:
        payload = self.get("category/list", {"blogName": self.blog_name})
        item = ((payload.get("tistory") or {}).get("item") or {}) if isinstance(payload, dict) else {}
        categories = item.get("categories", []) if isinstance(item, dict) else []
        return categories if isinstance(categories, list) else []

    def list_posts(self, page: int = 1, count: int = 10) -> list[dict[str, Any]]:
        payload = self.get("post/list", {"blogName": self.blog_name, "page": int(page), "count": int(count)})
        item = ((payload.get("tistory") or {}).get("item") or {}) if isinstance(payload, dict) else {}
        posts = item.get("posts", []) if isinstance(item, dict) else []
        return posts if isinstance(posts, list) else []

    def attach_file(self, filepath: str) -> dict[str, Any]:
        path = Path(filepath).resolve()
        if not path.exists():
            raise FileNotFoundError(f"file not found: {path}")
        with path.open("rb") as f:
            payload = self.post(
                "post/attach",
                data={"blogName": self.blog_name},
                files={"uploadedfile": (path.name, f)},
            )
        item = ((payload.get("tistory") or {}).get("replacer", "")) if isinstance(payload, dict) else ""
        url = ((payload.get("tistory") or {}).get("url", "")) if isinstance(payload, dict) else ""
        return {"replacer": str(item or ""), "url": str(url or ""), "raw": payload}

    def write_post(
        self,
        title: str,
        content: str,
        visibility: int = 3,
        category_id: int | None = None,
        published: str = "",
        tags: str = "",
        accept_comment: int = 1,
        password: str = "",
        slogan: str = "",
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "blogName": self.blog_name,
            "title": str(title or "").strip(),
            "content": str(content or ""),
            "visibility": int(visibility),
            "acceptComment": int(accept_comment),
        }
        if category_id not in (None, "", 0):
            data["category"] = int(category_id)
        if str(published or "").strip():
            data["published"] = str(published).strip()
        if str(tags or "").strip():
            data["tag"] = str(tags).strip()
        if str(password or "").strip():
            data["password"] = str(password).strip()
        if str(slogan or "").strip():
            data["slogan"] = str(slogan).strip()
        payload = self.post("post/write", data=data)
        item = (payload.get("tistory") or {}).get("postId", "")
        return {"post_id": str(item or ""), "raw": payload}

    def find_category_id(self, category_name: str) -> int | None:
        target = str(category_name or "").strip().lower()
        if not target:
            return None
        rows = self.list_categories()
        for row in rows:
            name = str(row.get("name", "")).strip().lower()
            if name == target:
                return _to_int(row.get("id"), 0) or None
        for row in rows:
            name = str(row.get("name", "")).strip().lower()
            if target in name:
                return _to_int(row.get("id"), 0) or None
        return None
