import argparse
import base64
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _env_map(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _py_cmd(args: List[str]) -> List[str]:
    if shutil.which("py"):
        return ["py", "-3", *args]
    return [sys.executable, *args]


def _run(cmd: List[str], timeout_sec: int = 300, extra_env: Dict[str, str] | None = None) -> Dict[str, Any]:
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    for k, v in dict(extra_env or {}).items():
        env[str(k)] = str(v)
    p = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        env=env,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "ok": p.returncode == 0,
        "returncode": int(p.returncode),
        "stdout_tail": "\n".join((p.stdout or "").splitlines()[-80:]),
        "stderr_tail": "\n".join((p.stderr or "").splitlines()[-80:]),
        "command": cmd,
    }


def _wp_headers(env: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    wp_url = str(env.get("WP_URL", "")).rstrip("/")
    user = str(env.get("WP_USER", "")).strip()
    pw = str(env.get("WP_APP_PASSWORD", "") or env.get("WP_PASSWORD", "")).strip()
    pw = re.sub(r"\s+", "", pw)
    if not wp_url or not user or not pw:
        raise ValueError("WP_URL / WP_USER / WP_APP_PASSWORD(or WP_PASSWORD) is required in .env")
    token = base64.b64encode(f"{user}:{pw}".encode("utf-8")).decode("ascii")
    return wp_url, {"Authorization": f"Basic {token}"}


def _wp_find_entries_by_slug(
    wp_url: str,
    headers: Dict[str, str],
    collection: str,
    slug: str,
) -> List[Dict[str, Any]]:
    find = requests.get(
        f"{wp_url}/{collection}",
        headers={"Authorization": headers["Authorization"]},
        params={"slug": slug, "context": "edit", "per_page": 100},
        timeout=30,
    )
    find.raise_for_status()
    return list(find.json() or [])


def _wp_post_with_fallback(
    headers: Dict[str, str],
    payload: Dict[str, Any],
    url: str,
) -> requests.Response:
    headers_json = dict(headers or {})
    headers_json["Content-Type"] = "application/json"
    # WordPress installs behind WAF/CDN can intermittently 502 on JSON payloads.
    # Fallback to form-encoded updates, which have been more stable for this site.
    first = requests.post(url, headers=headers_json, json=payload, timeout=90)
    if int(first.status_code) < 500:
        first.raise_for_status()
        return first
    second = requests.post(url, headers=headers, data=payload, timeout=120)
    second.raise_for_status()
    return second


def _wp_upsert_rest_entry(
    wp_url: str,
    headers: Dict[str, str],
    collection: str,
    slug: str,
    title: str,
    content_html: str,
    status: str = "publish",
    extra_payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    rows = _wp_find_entries_by_slug(
        wp_url=wp_url,
        headers=headers,
        collection=collection,
        slug=slug,
    )
    wrapped_html = content_html
    if "<!-- wp:html -->" not in wrapped_html:
        wrapped_html = f"<!-- wp:html -->\n{wrapped_html}\n<!-- /wp:html -->"
    payload = {
        "title": title,
        "slug": slug,
        "status": status,
        "content": wrapped_html,
    }
    payload.update(dict(extra_payload or {}))
    if rows:
        page_id = int(rows[0].get("id", 0) or 0)
        res = _wp_post_with_fallback(headers=headers, payload=payload, url=f"{wp_url}/{collection}/{page_id}")
        data = res.json()
        return {"mode": "update", "id": int(data.get("id", page_id)), "url": str(data.get("link", "")).strip()}
    res = _wp_post_with_fallback(headers=headers, payload=payload, url=f"{wp_url}/{collection}")
    data = res.json()
    return {"mode": "create", "id": int(data.get("id", 0) or 0), "url": str(data.get("link", "")).strip()}


def _wp_upsert_page(
    wp_url: str,
    headers: Dict[str, str],
    slug: str,
    title: str,
    content_html: str,
    status: str = "publish",
) -> Dict[str, Any]:
    return _wp_upsert_rest_entry(
        wp_url=wp_url,
        headers=headers,
        collection="pages",
        slug=slug,
        title=title,
        content_html=content_html,
        status=status,
    )


def _wp_upsert_post(
    wp_url: str,
    headers: Dict[str, str],
    slug: str,
    title: str,
    content_html: str,
    status: str = "publish",
) -> Dict[str, Any]:
    return _wp_upsert_rest_entry(
        wp_url=wp_url,
        headers=headers,
        collection="posts",
        slug=slug,
        title=title,
        content_html=content_html,
        status=status,
        extra_payload={
            "date": "2000-01-01T00:00:00",
            "date_gmt": "2000-01-01T00:00:00",
            "sticky": False,
            "comment_status": "closed",
            "ping_status": "closed",
        },
    )


def _wp_set_entry_status(
    wp_url: str,
    headers: Dict[str, str],
    collection: str,
    entry_id: int,
    status: str,
) -> Dict[str, Any]:
    payload = {"status": str(status or "").strip()}
    res = _wp_post_with_fallback(
        headers=headers,
        payload=payload,
        url=f"{wp_url}/{collection}/{int(entry_id)}",
    )
    data = res.json()
    return {
        "id": int(data.get("id", entry_id) or 0),
        "status": str(data.get("status", "")).strip(),
        "url": str(data.get("link", "")).strip(),
    }


def _wp_set_entries_status_by_slug(
    wp_url: str,
    headers: Dict[str, str],
    collection: str,
    slug: str,
    status: str,
) -> List[Dict[str, Any]]:
    rows = _wp_find_entries_by_slug(
        wp_url=wp_url,
        headers=headers,
        collection=collection,
        slug=slug,
    )
    changed: List[Dict[str, Any]] = []
    for row in rows:
        row_id = int(row.get("id", 0) or 0)
        row_status = str(row.get("status", "")).strip()
        if not row_id or row_status == status:
            continue
        next_row = _wp_set_entry_status(
            wp_url=wp_url,
            headers=headers,
            collection=collection,
            entry_id=row_id,
            status=status,
        )
        next_row["previous_status"] = row_status
        changed.append(next_row)
    return changed


def _wp_upload_media(
    wp_url: str,
    headers: Dict[str, str],
    file_path: Path,
    filename: str,
    content_type: str,
) -> Dict[str, Any]:
    media_url = f"{wp_url}/media"
    multipart_res = None
    with file_path.open("rb") as handle:
        multipart_res = requests.post(
            media_url,
            headers=dict(headers or {}),
            files={"file": (filename, handle, str(content_type or "application/octet-stream"))},
            timeout=300,
        )
    if int(multipart_res.status_code) >= 400:
        payload = file_path.read_bytes()
        upload_headers = dict(headers or {})
        upload_headers["Content-Type"] = str(content_type or "application/octet-stream")
        upload_headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        raw_res = requests.post(media_url, headers=upload_headers, data=payload, timeout=180)
        raw_res.raise_for_status()
        data = raw_res.json()
    else:
        data = multipart_res.json()
    return {
        "id": int(data.get("id", 0) or 0),
        "url": str(data.get("source_url", "")).strip(),
        "filename": str(data.get("media_details", {}).get("file", "")).strip() or filename,
    }


def _parse_wr_id_from_url(url: str) -> int:
    src = str(url or "").strip()
    if not src:
        return 0
    m = re.search(r"[?&]wr_id=(\d+)", src)
    if m:
        return int(m.group(1))
    m2 = re.search(r"/[A-Za-z0-9_]+/(\d+)(?:$|[/?#])", src)
    if m2:
        return int(m2.group(1))
    return 0


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_banner_html(target_url: str, subtitle: str) -> str:
    title = "AI 양도가 산정 계산기"
    desc = subtitle or "건설업 전 면허 양도양수/분할합병 고객용 계산기로 이동합니다."
    return (
        f'<div style="border:1px solid #d5e0ea;border-radius:14px;padding:18px;'
        f'background:#f4f7fb;max-width:980px;margin:8px auto;">'
        f'<div style="font-size:12px;color:#4b5e75;margin-bottom:6px;">서울건설정보 · SEOUL CONSTRUCTION INFO</div>'
        f'<div style="font-size:26px;font-weight:800;color:#003764;line-height:1.35;margin-bottom:8px;">{title}</div>'
        f'<div style="font-size:15px;color:#26374a;line-height:1.7;margin-bottom:14px;">{desc}</div>'
        f'<a href="{target_url}" target="_blank" rel="noopener noreferrer" '
        f'style="display:inline-block;background:#b87333;color:#fff;padding:12px 18px;'
        f'border-radius:10px;text-decoration:none;font-weight:700;">계산기 열기 (seoulmna.kr)</a>'
        f"</div>"
    )


def _publish_co_banner(
    board_slug: str,
    subject: str,
    html_content: str,
    wr_id: int = 0,
) -> Dict[str, Any]:
    from all import CONFIG, MnaBoardPublisher, SITE_URL  # noqa: WPS433

    admin_id = str(CONFIG.get("ADMIN_ID", "")).strip()
    admin_pw = str(CONFIG.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        raise RuntimeError("ADMIN_ID/ADMIN_PW missing")

    link1 = ""
    m = re.search(r'href="([^"]+)"', html_content)
    if m:
        link1 = str(m.group(1)).strip()

    pub = MnaBoardPublisher(SITE_URL, board_slug, admin_id, admin_pw)
    pub.login()
    res = pub.publish_custom_html(
        subject=subject,
        html_content=html_content,
        wr_id=int(wr_id or 0),
        link1=link1,
    )
    return {
        "mode": str(res.get("mode", "")),
        "url": str(res.get("url", "")).strip(),
        "wr_id": int(res.get("wr_id", 0) or _parse_wr_id_from_url(str(res.get("url", "")))),
    }


def _needs_smaller_payload(err: Exception) -> bool:
    text = str(err)
    return any(key in text for key in ("413", "414", "500", "502", "504", "Request Entity Too Large"))


def _build_html(mode: str, output_path: Path, max_train_rows: int) -> Dict[str, Any]:
    cmd = _py_cmd(
        [
            "all.py",
            "--build-yangdo-page",
            "--yangdo-page-mode",
            mode,
            "--yangdo-page-output",
            str(output_path),
            "--yangdo-page-max-train-rows",
            str(max_train_rows),
        ]
    )
    return _run(cmd, timeout_sec=420)


def _build_acquisition_html(
    output_path: Path,
    env_map: Dict[str, str],
    data_output: Path | None = None,
    data_url: str = "",
    data_encoding: str = "",
    fragment: bool = False,
) -> Dict[str, Any]:
    catalog_path = (ROOT / "config" / "kr_permit_industries_localdata.json").resolve()
    collect_step = _run(
        _py_cmd(
            [
                "scripts/collect_kr_permit_industries.py",
                "--output",
                str(catalog_path),
                "--strict",
            ]
        ),
        timeout_sec=240,
    )
    if not bool(collect_step.get("ok")):
        return collect_step
    cmd = _py_cmd(
        [
            "permit_diagnosis_calculator.py",
            "--catalog",
            str(catalog_path),
            "--output",
            str(output_path),
            "--title",
            "AI 인허가 사전검토 진단기(신규등록 전용)",
        ]
    )
    if data_output:
        cmd.extend(["--data-output", str(data_output)])
    if str(data_url or "").strip():
        cmd.extend(["--data-url", str(data_url).strip()])
    if str(data_encoding or "").strip():
        cmd.extend(["--data-encoding", str(data_encoding).strip()])
    if fragment:
        cmd.append("--fragment")
    return _run(cmd, timeout_sec=240)


def _size_bytes(path: Path) -> int:
    try:
        return int(path.stat().st_size)
    except Exception:
        return 0


def _write_gzip_copy(source_path: Path, target_path: Path) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(gzip.compress(source_path.read_bytes(), compresslevel=9, mtime=0))
    return target_path


def _gzip_file_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _build_payload_page_html(gzip_base64_text: str, canonical_url: str = "") -> str:
    payload = str(gzip_base64_text or "").strip()
    canonical = str(canonical_url or "").strip()
    return (
        "<style>"
        ".entry-title,.page-title,.ast-breadcrumbs,.site-below-footer-wrap{display:none!important;}"
        "#smna-permit-payload-page{display:none!important;}"
        "</style>"
        "<script>"
        "(function(){"
        "var applyMeta=function(){"
        "try{"
        "var head=document.head||document.getElementsByTagName('head')[0];"
        "if(!head){return;}"
        "var robotsList=Array.prototype.slice.call(document.querySelectorAll('meta[name=\"robots\"]'));"
        "if(!robotsList.length){var robots=document.createElement('meta');robots.name='robots';head.appendChild(robots);robotsList=[robots];}"
        "robotsList.forEach(function(node){node.setAttribute('content','noindex,nofollow,noarchive,max-snippet:0,max-image-preview:none');});"
        f"var canonicalHref={json.dumps(canonical, ensure_ascii=False)};"
        "if(canonicalHref){"
        "var canonicalList=Array.prototype.slice.call(document.querySelectorAll('link[rel=\"canonical\"]'));"
        "if(!canonicalList.length){var link=document.createElement('link');link.rel='canonical';head.appendChild(link);canonicalList=[link];}"
        "canonicalList.forEach(function(node){node.setAttribute('href', canonicalHref);});"
        "}"
        "}catch(_e){}};"
        "applyMeta();"
        "document.addEventListener('DOMContentLoaded', applyMeta);"
        "window.addEventListener('load', applyMeta);"
        "setTimeout(applyMeta, 0);"
        "setTimeout(applyMeta, 500);"
        "})();"
        "</script>"
        '<section id="smna-permit-payload-page" aria-hidden="true" style="display:none!important;">'
        '<script id="smna-permit-payload" type="application/octet-stream">'
        f"{payload}"
        "</script>"
        "</section>"
    )


def _build_payload_rest_data_url(wp_url: str, page_id: int, collection: str = "pages") -> str:
    base = str(wp_url or "").rstrip("/")
    resource = str(collection or "pages").strip().strip("/") or "pages"
    return f"{base}/{resource}/{int(page_id)}?_fields=content.rendered,modified&context=view"


def _candidate_caps(preferred: int) -> List[int]:
    pref = max(1, int(preferred or 1))
    vals = [
        pref,
        320,
        300,
        280,
        260,
        240,
        220,
        200,
        180,
        160,
        140,
        120,
        100,
        80,
        60,
        40,
        39,
        38,
        37,
        36,
        35,
        30,
        25,
        20,
        15,
        10,
    ]
    out = []
    seen = set()
    for v in vals:
        n = int(v or 0)
        if n > pref:
            continue
        if n <= 0 or n in seen:
            continue
        out.append(n)
        seen.add(n)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy calculator to seoulmna.kr and publish banner bridge on seoulmna.co.kr"
    )
    parser.add_argument("--customer-slug", default="yangdo-ai-customer")
    parser.add_argument("--acquisition-slug", default="ai-license-acquisition-calculator")
    parser.add_argument("--acquisition-payload-slug", default="")
    parser.add_argument("--customer-title", default="AI 양도가 산정 계산기")
    parser.add_argument("--acquisition-title", default="AI 인허가 사전검토 진단기(신규등록 전용)")
    parser.add_argument("--wp-status", default="publish")
    parser.add_argument("--customer-board", default="yangdo_ai")
    parser.add_argument("--acquisition-board", default="yangdo_ai_ops")
    parser.add_argument("--customer-wr-id", type=int, default=0)
    parser.add_argument("--acquisition-wr-id", type=int, default=0)
    parser.add_argument("--skip-co-publish", action="store_true")
    parser.add_argument(
        "--publish-co",
        action="store_true",
        help="Explicitly allow publishing bridge banners to seoulmna.co.kr",
    )
    parser.add_argument("--max-train-rows", type=int, default=260)
    parser.add_argument("--co-request-cap-override", type=int, default=0)
    parser.add_argument("--co-write-cap-override", type=int, default=0)
    parser.add_argument("--confirm-live", default="", help="실서비스 반영 승인 토큰 (`--confirm-live YES`)")
    parser.add_argument("--state", default="logs/yangdo_kr_bridge_state.json")
    parser.add_argument("--report", default="logs/yangdo_kr_bridge_latest.json")
    args = parser.parse_args()
    if str(args.confirm_live or "").strip().upper() != "YES":
        blocked = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ok": False,
            "steps": [],
            "wp": {},
            "co": {},
            "blocking_issues": ["confirm_live_missing"],
            "error": "live apply blocked: add --confirm-live YES",
        }
        report_path = (ROOT / args.report).resolve()
        _save_json(report_path, blocked)
        print(f"[saved] {report_path}")
        print("[overall_ok] False")
        print("- confirm_live_missing")
        return 2

    report: Dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": True,
        "steps": [],
        "wp": {},
        "co": {},
        "blocking_issues": [],
    }

    state_path = (ROOT / args.state).resolve()
    state = _load_json(state_path, {}) or {}
    report_path = (ROOT / args.report).resolve()

    out_customer = ROOT / "output" / "yangdo_price_calculator_customer_standalone.html"
    out_acquisition = ROOT / "output" / "ai_license_acquisition_calculator_standalone.html"
    out_acquisition_data = ROOT / "output" / "ai_license_acquisition_calculator_payload.json"
    out_acquisition_data_gzip = ROOT / "output" / "ai_license_acquisition_calculator_payload.json.gz"

    env = _env_map(ROOT / ".env")
    try:
        wp_url, wp_headers = _wp_headers(env)
    except Exception as e:
        report["ok"] = False
        report["blocking_issues"].append(f"wp_env_invalid:{e}")
        _save_json(report_path, report)
        return 2

    wp_customer = None
    wp_acquisition = None
    wp_acquisition_payload = None
    selected_cap = 0
    last_wp_error = None

    for cap in _candidate_caps(args.max_train_rows):
        s1 = _build_html("customer", out_customer, cap)
        s2 = _build_acquisition_html(
            out_acquisition,
            env,
            data_output=out_acquisition_data,
            fragment=True,
        )
        report["steps"].append({"name": f"build_customer_html_cap_{cap}", **s1})
        report["steps"].append({"name": f"build_acquisition_html_cap_{cap}", **s2})
        if not s1["ok"] or not s2["ok"] or not out_customer.exists() or not out_acquisition.exists():
            report["ok"] = False
            report["blocking_issues"].append(f"build_failed_cap_{cap}")
            _save_json(report_path, report)
            return 2

        c_size = _size_bytes(out_customer)
        o_size = _size_bytes(out_acquisition)
        acquisition_data_size = _size_bytes(out_acquisition_data)
        acquisition_data_gzip_size = 0
        if out_acquisition_data.exists():
            _write_gzip_copy(out_acquisition_data, out_acquisition_data_gzip)
            acquisition_data_gzip_size = _size_bytes(out_acquisition_data_gzip)
        report["steps"].append(
            {
                "name": f"payload_size_cap_{cap}",
                "customer_bytes": c_size,
                "acquisition_bytes": o_size,
                "acquisition_data_bytes": acquisition_data_size,
                "acquisition_data_gzip_bytes": acquisition_data_gzip_size,
            }
        )

        try:
            customer_html = out_customer.read_text(encoding="utf-8", errors="replace")
            acquisition_html = out_acquisition.read_text(encoding="utf-8", errors="replace")
            if out_acquisition_data.exists():
                payload_slug = str(args.acquisition_payload_slug or f"{args.acquisition_slug}-payload").strip()
                public_site_root = str(wp_url).replace("/wp-json/wp/v2", "").rstrip("/")
                acquisition_public_url = f"{public_site_root}/{str(args.acquisition_slug).strip().strip('/')}/"
                payload_page_html = _build_payload_page_html(
                    _gzip_file_to_base64(out_acquisition_data_gzip),
                    canonical_url=acquisition_public_url,
                )
                upload_candidates = [
                    {
                        "name": "post",
                        "kind": "post",
                        "slug": payload_slug,
                        "title": "Platform Resource",
                        "html": payload_page_html,
                        "data_encoding": "gzip-base64-rest-rendered",
                    },
                    {
                        "name": "page",
                        "kind": "page",
                        "slug": payload_slug,
                        "title": "Platform Resource",
                        "html": payload_page_html,
                        "data_encoding": "gzip-base64-html",
                    },
                    {
                        "name": "gzip",
                        "kind": "media",
                        "path": out_acquisition_data_gzip,
                        "filename": "ai-license-acquisition-payload.json.gz",
                        "content_type": "application/gzip",
                        "data_encoding": "gzip",
                    },
                    {
                        "name": "text",
                        "kind": "media",
                        "path": out_acquisition_data,
                        "filename": "ai-license-acquisition-payload.txt",
                        "content_type": "text/plain; charset=utf-8",
                        "data_encoding": "",
                    },
                    {
                        "name": "json",
                        "kind": "media",
                        "path": out_acquisition_data,
                        "filename": "ai-license-acquisition-payload.json",
                        "content_type": "application/json",
                        "data_encoding": "",
                    },
                ]
                for upload_candidate in upload_candidates:
                    try:
                        upload_kind = str(upload_candidate.get("kind") or "").strip()
                        if upload_kind == "post":
                            media = _wp_upsert_post(
                                wp_url=wp_url,
                                headers=wp_headers,
                                slug=str(upload_candidate["slug"]),
                                title=str(upload_candidate["title"]),
                                content_html=str(upload_candidate["html"]),
                                status=str(args.wp_status),
                            )
                            wp_acquisition_payload = media
                        elif upload_kind == "page":
                            media = _wp_upsert_page(
                                wp_url=wp_url,
                                headers=wp_headers,
                                slug=str(upload_candidate["slug"]),
                                title=str(upload_candidate["title"]),
                                content_html=str(upload_candidate["html"]),
                                status=str(args.wp_status),
                            )
                            wp_acquisition_payload = media
                        else:
                            media = _wp_upload_media(
                                wp_url=wp_url,
                                headers=wp_headers,
                                file_path=Path(upload_candidate["path"]),
                                filename=str(upload_candidate["filename"]),
                                content_type=str(upload_candidate["content_type"]),
                            )
                        report["steps"].append(
                            {
                                "name": f"upload_acquisition_payload_{upload_candidate['name']}_cap_{cap}",
                                "payload_bytes": _size_bytes(Path(upload_candidate["path"])) if upload_candidate.get("path") else len(payload_page_html.encode("utf-8")),
                                "data_encoding": str(upload_candidate["data_encoding"]),
                                **media,
                            }
                        )
                        shell_data_url = str(media.get("url", "")).strip()
                        shell_data_encoding = str(upload_candidate["data_encoding"])
                        if upload_kind in {"post", "page"}:
                            collection = "posts" if upload_kind == "post" else "pages"
                            shell_data_url = _build_payload_rest_data_url(
                                wp_url=wp_url,
                                page_id=int(media.get("id", 0) or 0),
                                collection=collection,
                            )
                            shell_data_encoding = "gzip-base64-rest-rendered"
                        s3 = _build_acquisition_html(
                            out_acquisition,
                            env,
                            data_output=out_acquisition_data,
                            data_url=shell_data_url,
                            data_encoding=shell_data_encoding,
                            fragment=True,
                        )
                        report["steps"].append(
                            {
                                "name": f"build_acquisition_shell_{upload_candidate['name']}_cap_{cap}",
                                **s3,
                            }
                        )
                        if upload_kind == "post" and bool(s3.get("ok")):
                            deactivated_pages = _wp_set_entries_status_by_slug(
                                wp_url=wp_url,
                                headers=wp_headers,
                                collection="pages",
                                slug=payload_slug,
                                status="draft",
                            )
                            report["steps"].append(
                                {
                                    "name": f"deactivate_payload_pages_cap_{cap}",
                                    "slug": payload_slug,
                                    "count": len(deactivated_pages),
                                    "rows": deactivated_pages,
                                }
                            )
                        if bool(s3.get("ok")) and out_acquisition.exists():
                            acquisition_html = out_acquisition.read_text(encoding="utf-8", errors="replace")
                            break
                    except Exception as acquisition_payload_error:
                        report["steps"].append(
                            {
                                "name": f"upload_acquisition_payload_failed_{upload_candidate['name']}_cap_{cap}",
                                "error": str(acquisition_payload_error),
                            }
                        )
            wp_customer = _wp_upsert_page(
                wp_url=wp_url,
                headers=wp_headers,
                slug=str(args.customer_slug),
                title=str(args.customer_title),
                content_html=customer_html,
                status=str(args.wp_status),
            )
            wp_acquisition = _wp_upsert_page(
                wp_url=wp_url,
                headers=wp_headers,
                slug=str(args.acquisition_slug),
                title=str(args.acquisition_title),
                content_html=acquisition_html,
                status=str(args.wp_status),
            )
            selected_cap = cap
            break
        except Exception as e:
            last_wp_error = e
            report["steps"].append({"name": f"wp_publish_failed_cap_{cap}", "error": str(e)})
            if not _needs_smaller_payload(e):
                break

    if not wp_customer or not wp_acquisition:
        report["ok"] = False
        report["blocking_issues"].append(f"wp_publish_failed:{last_wp_error}")
        _save_json(report_path, report)
        return 2

    report["wp"] = {
        "selected_max_train_rows": selected_cap,
        "customer": wp_customer,
        "acquisition": wp_acquisition,
    }
    if wp_acquisition_payload:
        report["wp"]["acquisition_payload"] = wp_acquisition_payload

    if int(args.co_request_cap_override or 0) > 0:
        os.environ["SEOUL_DAILY_REQUEST_CAP"] = str(int(args.co_request_cap_override))
    if int(args.co_write_cap_override or 0) > 0:
        os.environ["SEOUL_DAILY_WRITE_CAP"] = str(int(args.co_write_cap_override))

    publish_co = bool(args.publish_co) and (not bool(args.skip_co_publish))
    if publish_co:
        customer_target = str(wp_customer.get("url", "")).strip()
        acquisition_target = str(wp_acquisition.get("url", "")).strip()
        customer_wr = int(args.customer_wr_id or state.get("customer_wr_id", 0) or 0)
        acquisition_wr = int(args.acquisition_wr_id or state.get("acquisition_wr_id", 0) or 0)
        try:
            co_customer = _publish_co_banner(
                board_slug=str(args.customer_board),
                subject="AI 양도가 산정 계산기",
                html_content=_build_banner_html(customer_target, "건설업 전 면허 양도양수·분할합병 고객용 계산기로 이동합니다."),
                wr_id=customer_wr,
            )
            co_acquisition = _publish_co_banner(
                board_slug=str(args.acquisition_board),
                subject="AI 인허가 사전검토 진단기(신규등록 전용)",
                html_content=_build_banner_html(acquisition_target, "건설업 신규등록 준비 고객용 계산기로 이동합니다."),
                wr_id=acquisition_wr,
            )
            report["co"] = {"customer": co_customer, "acquisition": co_acquisition}
            state["customer_wr_id"] = int(co_customer.get("wr_id", 0) or customer_wr)
            state["acquisition_wr_id"] = int(co_acquisition.get("wr_id", 0) or acquisition_wr)
            _save_json(state_path, state)
        except Exception as e:
            report["ok"] = False
            report["blocking_issues"].append(f"co_banner_publish_failed:{e}")
            report["co"] = {
                "customer_pending_html": _build_banner_html(customer_target, "건설업 전 면허 양도양수·분할합병 고객용 계산기로 이동합니다."),
                "acquisition_pending_html": _build_banner_html(acquisition_target, "건설업 신규등록 준비 고객용 계산기로 이동합니다."),
            }
    else:
        report["co"] = {
            "skipped": True,
            "reason": "default_safe_mode" if not bool(args.publish_co) else "skip_flag_enabled",
        }

    _save_json(report_path, report)
    print(f"[saved] {report_path}")
    print(f"[overall_ok] {bool(report.get('ok'))}")
    print(f"[wp_customer] {report['wp'].get('customer', {}).get('url', '')}")
    print(f"[wp_acquisition] {report['wp'].get('acquisition', {}).get('url', '')}")
    if report.get("co", {}).get("customer", {}).get("url"):
        print(f"[co_customer] {report['co']['customer']['url']}")
    if report.get("co", {}).get("acquisition", {}).get("url"):
        print(f"[co_acquisition] {report['co']['acquisition']['url']}")
    if report.get("blocking_issues"):
        for issue in report["blocking_issues"]:
            print(f"- {issue}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())


