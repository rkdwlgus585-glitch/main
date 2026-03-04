import argparse
import base64
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


def _wp_upsert_page(
    wp_url: str,
    headers: Dict[str, str],
    slug: str,
    title: str,
    content_html: str,
    status: str = "publish",
) -> Dict[str, Any]:
    find = requests.get(
        f"{wp_url}/pages",
        headers={"Authorization": headers["Authorization"]},
        params={"slug": slug, "context": "edit"},
        timeout=30,
    )
    find.raise_for_status()
    rows = list(find.json() or [])
    wrapped_html = content_html
    if "<!-- wp:html -->" not in wrapped_html:
        wrapped_html = f"<!-- wp:html -->\n{wrapped_html}\n<!-- /wp:html -->"
    payload = {
        "title": title,
        "slug": slug,
        "status": status,
        "content": wrapped_html,
    }
    headers_json = dict(headers or {})
    headers_json["Content-Type"] = "application/json"

    def _post_with_fallback(url: str) -> requests.Response:
        # WordPress installs behind WAF/CDN can intermittently 502 on JSON payloads.
        # Fallback to form-encoded updates, which have been more stable for this site.
        first = requests.post(url, headers=headers_json, json=payload, timeout=90)
        if int(first.status_code) < 500:
            first.raise_for_status()
            return first
        second = requests.post(url, headers=headers, data=payload, timeout=120)
        second.raise_for_status()
        return second

    if rows:
        page_id = int(rows[0].get("id", 0) or 0)
        res = _post_with_fallback(f"{wp_url}/pages/{page_id}")
        data = res.json()
        return {"mode": "update", "id": int(data.get("id", page_id)), "url": str(data.get("link", "")).strip()}
    res = _post_with_fallback(f"{wp_url}/pages")
    data = res.json()
    return {"mode": "create", "id": int(data.get("id", 0) or 0), "url": str(data.get("link", "")).strip()}


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


def _build_acquisition_html(output_path: Path, env_map: Dict[str, str]) -> Dict[str, Any]:
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
            "AI 인허가 사전검토 진단기(신규등록)",
        ]
    )
    return _run(cmd, timeout_sec=240)


def _size_bytes(path: Path) -> int:
    try:
        return int(path.stat().st_size)
    except Exception:
        return 0


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
    parser.add_argument("--customer-title", default="AI 양도가 산정 계산기")
    parser.add_argument("--acquisition-title", default="AI 인허가 사전검토 진단기(신규등록)")
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
    selected_cap = 0
    last_wp_error = None

    for cap in _candidate_caps(args.max_train_rows):
        s1 = _build_html("customer", out_customer, cap)
        s2 = _build_acquisition_html(out_acquisition, env)
        report["steps"].append({"name": f"build_customer_html_cap_{cap}", **s1})
        report["steps"].append({"name": f"build_acquisition_html_cap_{cap}", **s2})
        if not s1["ok"] or not s2["ok"] or not out_customer.exists() or not out_acquisition.exists():
            report["ok"] = False
            report["blocking_issues"].append(f"build_failed_cap_{cap}")
            _save_json(report_path, report)
            return 2

        c_size = _size_bytes(out_customer)
        o_size = _size_bytes(out_acquisition)
        report["steps"].append(
            {
                "name": f"payload_size_cap_{cap}",
                "customer_bytes": c_size,
                "acquisition_bytes": o_size,
            }
        )

        try:
            customer_html = out_customer.read_text(encoding="utf-8", errors="replace")
            acquisition_html = out_acquisition.read_text(encoding="utf-8", errors="replace")
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
                subject="AI 인허가 사전검토 진단기(신규등록)",
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

