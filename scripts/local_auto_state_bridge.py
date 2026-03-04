import argparse
import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
LOCK = threading.Lock()


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _compact(v) -> str:
    return " ".join(str(v or "").split()).strip()


def _safe_account(v: str) -> str:
    src = _compact(v).lower()
    if not src:
        return "guest"
    out = "".join(ch for ch in src if ch.isalnum() or ch in "._@-")
    return out[:80] or "guest"


def _safe_rows(rows, limit: int):
    out = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = _compact(row.get("url", ""))
        title = _compact(row.get("title", ""))
        if not url:
            continue
        item = {
            "url": url,
            "title": (title or f"listing {url.rstrip('/').split('/')[-1]}")[:80],
            "ts": int(row.get("ts", 0) or 0),
        }
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _load_db(path: Path):
    if not path.exists():
        return {"updated_at": _now_str(), "accounts": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"updated_at": _now_str(), "accounts": {}}


def _save_db(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_handler(data_file: Path):
    class Handler(BaseHTTPRequestHandler):
        def _allow_origin(self) -> str:
            origin = (self.headers.get("Origin") or "").strip()
            allow = {
                "https://seoulmna.co.kr",
                "https://www.seoulmna.co.kr",
                "http://seoulmna.co.kr",
                "http://www.seoulmna.co.kr",
                "null",
            }
            if origin in allow:
                return origin
            return "*"

        def _send(self, status: int, payload):
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Access-Control-Allow-Origin", self._allow_origin())
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Access-Control-Max-Age", "600")
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, fmt, *args):
            return

        def do_OPTIONS(self):
            self._send(200, {"ok": True})

        def do_GET(self):
            parsed = urlparse(self.path or "/")
            if parsed.path == "/health":
                self._send(200, {"ok": True, "now": _now_str()})
                return
            if parsed.path != "/v1/state":
                self._send(404, {"ok": False, "error": "not_found"})
                return
            qs = parse_qs(parsed.query or "")
            account = _safe_account((qs.get("account") or ["guest"])[0])
            with LOCK:
                db = _load_db(data_file)
            row = (db.get("accounts") or {}).get(account) or {}
            self._send(
                200,
                {
                    "ok": True,
                    "account": account,
                    "favorites": _safe_rows(row.get("favorites", []), 20),
                    "recent": _safe_rows(row.get("recent", []), 10),
                    "updated_at": row.get("updated_at", db.get("updated_at", "")),
                },
            )

        def do_POST(self):
            parsed = urlparse(self.path or "/")
            if parsed.path != "/v1/state":
                self._send(404, {"ok": False, "error": "not_found"})
                return
            try:
                n = int(self.headers.get("Content-Length", "0") or "0")
            except Exception:
                n = 0
            body = self.rfile.read(max(0, n)) if n > 0 else b"{}"
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                payload = {}
            account = _safe_account(payload.get("account", "guest"))
            favorites = _safe_rows(payload.get("favorites", []), 20)
            recent = _safe_rows(payload.get("recent", []), 10)
            with LOCK:
                db = _load_db(data_file)
                accounts = db.setdefault("accounts", {})
                cur = accounts.get(account, {})
                if "favorites" in payload:
                    cur["favorites"] = favorites
                if "recent" in payload:
                    cur["recent"] = recent
                cur["updated_at"] = _now_str()
                accounts[account] = cur
                db["updated_at"] = _now_str()
                _save_db(data_file, db)
            self._send(
                200,
                {
                    "ok": True,
                    "account": account,
                    "favorites_count": len(favorites),
                    "recent_count": len(recent),
                    "updated_at": _now_str(),
                },
            )

    return Handler


def main():
    ap = argparse.ArgumentParser(description="Local AUTO state bridge for seoulmna favorites/recent sync")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=18777)
    ap.add_argument("--data-file", default="logs/local_auto_state.json")
    args = ap.parse_args()

    data_file = (ROOT / args.data_file).resolve()
    server = ThreadingHTTPServer((args.host, int(args.port)), build_handler(data_file))
    print(f"[bridge] listening on http://{args.host}:{args.port}")
    print(f"[data] {data_file}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
