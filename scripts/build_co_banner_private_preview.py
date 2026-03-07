import argparse
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urljoin, urlparse
import webbrowser

import requests


ROOT = Path(__file__).resolve().parents[1]
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
    "content-encoding",
}

CRITICAL_HEAD_STYLE_ID = "smna-critical-topgap-style"
CRITICAL_HEAD_STYLE = (
    f"<style id='{CRITICAL_HEAD_STYLE_ID}'>"
    "html,body{margin:0!important;padding:0!important;}"
    "#wrap{margin-top:0!important;padding-top:0!important;}"
    "#wrap > div:first-child{position:relative!important;height:0!important;min-height:0!important;"
    "margin:0!important;padding:0!important;overflow:visible!important;}"
    "#hd_pop{display:none!important;visibility:hidden!important;height:0!important;min-height:0!important;"
    "margin:0!important;padding:0!important;border:0!important;overflow:hidden!important;}"
    "#header{top:0!important;margin-top:0!important;}"
    "</style>"
)


def _read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _inject_snippet(html: str, snippet: str) -> str:
    src = str(html or "")
    s = str(snippet or "").strip()
    if not src or not s:
        return src

    global_pattern = re.compile(
        r"<!-- SEOULMNA GLOBAL BANNER START -->.*?<!-- SEOULMNA GLOBAL BANNER END -->",
        flags=re.S,
    )
    traffic_pattern = re.compile(
        r"<!-- SEOULMNA TRAFFIC COUNTER START -->.*?<!-- SEOULMNA TRAFFIC COUNTER END -->",
        flags=re.S,
    )

    out = traffic_pattern.sub("", src).strip()
    lowered = out.lower()
    if CRITICAL_HEAD_STYLE_ID.lower() not in lowered:
        if "</head>" in lowered:
            out = re.sub(r"</head>", lambda _m: CRITICAL_HEAD_STYLE + "\n</head>", out, count=1, flags=re.I)
        else:
            out = CRITICAL_HEAD_STYLE + "\n" + out

    marker_start = "<!-- SEOULMNA GLOBAL BANNER START -->"
    marker_end = "<!-- SEOULMNA GLOBAL BANNER END -->"
    if marker_start in out and marker_end in out:
        out = global_pattern.sub(lambda _m: s, out)
    elif marker_start in out and marker_end not in out:
        out = (out.split(marker_start, 1)[0].strip() + "\n" + s).strip()
    else:
        if "</body>" in out.lower():
            out = re.sub(r"</body>", lambda _m: s + "\n</body>", out, count=1, flags=re.I)
        else:
            out = out + "\n" + s

    return out


def _make_handler(origin: str, snippet: str):
    session = requests.Session()

    class ProxyHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            # quiet-ish output
            print("[proxy]", fmt % args)

        def _rewrite_location(self, value: str) -> str:
            if not value:
                return value
            try:
                loc = str(value)
                op = urlparse(origin)
                lp = urlparse(loc)
                if lp.scheme and lp.netloc and lp.scheme == op.scheme and lp.netloc == op.netloc:
                    path = lp.path or "/"
                    if lp.query:
                        path += "?" + lp.query
                    if lp.fragment:
                        path += "#" + lp.fragment
                    return path
                return loc
            except Exception:
                return value

        def _proxy_get(self):
            incoming_path = self.path if str(self.path or "").strip() else "/"
            target_url = urljoin(origin, incoming_path)

            base_headers = {}
            for k, v in self.headers.items():
                lk = str(k).lower().strip()
                if lk in {"host", "accept-encoding"}:
                    continue
                base_headers[k] = v
            base_headers["Accept-Encoding"] = "identity"

            def build_headers(url: str) -> dict:
                out = dict(base_headers)
                out["Host"] = urlparse(url).netloc
                return out

            try:
                seen = set()
                resp = None
                for _hop in range(8):
                    resp = session.get(
                        target_url,
                        headers=build_headers(target_url),
                        timeout=40,
                        allow_redirects=False,
                    )
                    status = int(resp.status_code or 0)
                    if status not in {301, 302, 303, 307, 308}:
                        break
                    loc = str(resp.headers.get("Location", "") or "").strip()
                    if not loc:
                        break
                    next_url = urljoin(target_url, loc)
                    if next_url in seen:
                        break
                    seen.add(next_url)
                    target_url = next_url
            except Exception as e:
                body = f"proxy error: {e}".encode("utf-8", errors="replace")
                self.send_response(502)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            raw = resp.content or b""
            ctype = str(resp.headers.get("Content-Type", "") or "")
            is_html = "text/html" in ctype.lower()

            if is_html:
                charset = resp.encoding or "utf-8"
                try:
                    text = raw.decode(charset, errors="replace")
                except Exception:
                    text = raw.decode("utf-8", errors="replace")
                modified = _inject_snippet(text, snippet)
                body = modified.encode("utf-8", errors="replace")
                out_ctype = "text/html; charset=utf-8"
            else:
                body = raw
                out_ctype = ctype or "application/octet-stream"

            self.send_response(resp.status_code)
            for k, v in resp.headers.items():
                lk = str(k).lower().strip()
                if lk in HOP_BY_HOP_HEADERS:
                    continue
                if is_html and lk in {"cache-control", "pragma", "expires"}:
                    continue
                if lk == "location":
                    self.send_header(k, self._rewrite_location(v))
                    continue
                if lk == "content-type":
                    continue
                self.send_header(k, v)

            self.send_header("Content-Type", out_ctype)
            if is_html:
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self._proxy_get()

        def do_HEAD(self):
            self.send_response(405)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_POST(self):
            self.send_response(405)
            self.send_header("Content-Length", "0")
            self.end_headers()

    return ProxyHandler


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Serve private localhost preview by reverse-proxying seoulmna site and injecting snippet."
    )
    parser.add_argument("--origin", default="https://seoulmna.co.kr")
    parser.add_argument("--snippet-file", default="snapshots/co_global_banner_test_working.html")
    parser.add_argument("--port", type=int, default=18778)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    origin = str(args.origin or "").strip().rstrip("/")
    if not origin.startswith("http"):
        raise SystemExit(f"invalid --origin: {origin}")

    snippet_path = (ROOT / str(args.snippet_file)).resolve()
    if not snippet_path.exists():
        raise SystemExit(f"snippet file not found: {snippet_path}")
    snippet = _read_text(snippet_path)

    handler = _make_handler(origin=origin, snippet=snippet)
    host = "127.0.0.1"
    port = int(args.port)
    url = f"http://{host}:{port}/"
    print("[preview-origin]", origin)
    print("[snippet-file]", snippet_path)
    print("[preview-url]", url)

    if not bool(args.no_open):
        try:
            webbrowser.open(url)
        except Exception:
            pass

    with ThreadingHTTPServer((host, port), handler) as server:
        print("[serve] localhost-only; Ctrl+C to stop")
        server.serve_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
