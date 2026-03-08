import argparse
import base64
import html
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
REPORT_PATH = ROOT / "logs" / "wp_private_ai_pages_latest.json"
HUB_REPORT_PATH = ROOT / "logs" / "wp_private_ai_hub_latest.json"
REGRESSION_REPORT_PATH = ROOT / "logs" / "yangdo_operational_regression_latest.json"
SECURE_STATUS_PATH = ROOT / "logs" / "secure_api_status_latest.json"
PERMIT_SANITY_PATH = ROOT / "logs" / "permit_wizard_sanity_latest.json"
PERMIT_STEP_SMOKE_PATH = ROOT / "logs" / "permit_step_transition_smoke_latest.json"
BROWSER_SMOKE_PATH = ROOT / "logs" / "calculator_browser_smoke_latest.json"
PARTNER_API_SMOKE_PATH = ROOT / "logs" / "partner_api_contract_smoke_latest.json"
HUB_DASHBOARD_PATH = ROOT / "logs" / "ai_admin_dashboard_latest.json"
PLAYWRIGHT_ARTIFACT_DIR = ROOT / "output" / "playwright"
PERMIT_STEP_FAIL_SCREENSHOT = PLAYWRIGHT_ARTIFACT_DIR / "permit_step_transition_failure_latest.png"
PERMIT_STEP_FAIL_HTML = PLAYWRIGHT_ARTIFACT_DIR / "permit_step_transition_failure_latest.html"
PERMIT_BROWSER_FAIL_SCREENSHOT = PLAYWRIGHT_ARTIFACT_DIR / "permit_browser_smoke_failure_latest.png"
PERMIT_BROWSER_FAIL_HTML = PLAYWRIGHT_ARTIFACT_DIR / "permit_browser_smoke_failure_latest.html"

OWNER_PAGE_ID = 1761
PERMIT_PAGE_ID = 1762
HUB_PAGE_ID = 1763

OWNER_SLUG = "yangdo-ai-admin"
PERMIT_SLUG = "ai-license-acquisition-admin"
HUB_SLUG = "ai-admin-hub"

OWNER_TITLE = "AI 양도가 산정 계산기 [관리자 전용]"
PERMIT_TITLE = "AI 인허가 사전검토 진단기 [관리자 전용]"
HUB_TITLE = "AI 계산기 관리자 허브"

OWNER_SOURCE = ROOT / "output" / "yangdo_price_calculator_owner_internal_v11.html"
PERMIT_SOURCE = ROOT / "output" / "ai_license_acquisition_calculator.html"


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


def _wp_auth_headers(env: Dict[str, str]) -> Tuple[str, Dict[str, str], Dict[str, str]]:
    wp_url = str(env.get("WP_URL", "")).rstrip("/")
    user = str(env.get("WP_USER", "")).strip()
    pw = str(env.get("WP_APP_PASSWORD", "") or env.get("WP_PASSWORD", "")).strip()
    pw = re.sub(r"\s+", "", pw)
    if not wp_url or not user or not pw:
        raise ValueError("WP_URL / WP_USER / WP_APP_PASSWORD(or WP_PASSWORD) missing")
    token = base64.b64encode(f"{user}:{pw}".encode("utf-8")).decode("ascii")
    auth = {"Authorization": f"Basic {token}"}
    auth_json = dict(auth)
    auth_json["Content-Type"] = "application/json; charset=utf-8"
    return wp_url, auth, auth_json


def _wrap_html_block(content_html: str) -> str:
    txt = str(content_html or "").strip()
    if "<!-- wp:html -->" in txt:
        return txt
    return f"<!-- wp:html -->\n{txt}\n<!-- /wp:html -->"


def _extract_fragment(html_text: str) -> str:
    txt = str(html_text or "").strip()
    if not txt:
        return ""
    if not txt.lower().startswith("<!doctype") and "<html" not in txt.lower():
        return txt

    soup = BeautifulSoup(txt, "html.parser")
    head_parts = []
    for node in soup.select("head style, head script"):
        head_parts.append(str(node))

    body_parts = []
    if soup.body:
        for node in soup.body.contents:
            body_parts.append(str(node))
    else:
        section = soup.select_one("section")
        if section:
            body_parts.append(str(section))

    return "\n".join(part for part in [*head_parts, *body_parts] if str(part).strip())


def _update_page(
    wp_url: str,
    auth: Dict[str, str],
    auth_json: Dict[str, str],
    page_id: int,
    title: str,
    slug: str,
    status: str,
    content: str | None = None,
    parent: int | None = None,
) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "title": title,
        "slug": slug,
        "status": status,
    }
    if content is not None:
        payload["content"] = _wrap_html_block(content)
    if parent is not None:
        payload["parent"] = int(parent)

    url = f"{wp_url}/pages/{int(page_id)}"
    res = requests.post(url, headers=auth_json, json=payload, timeout=90)
    if int(res.status_code) >= 500:
        res = requests.post(url, headers=auth, data=payload, timeout=120)
    res.raise_for_status()
    return dict(res.json() or {})


def _public_probe(url: str) -> Dict[str, object]:
    res = requests.get(url, timeout=30, allow_redirects=True)
    soup = BeautifulSoup(res.text, "html.parser")
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    return {
        "public_http_status": int(res.status_code),
        "public_final_url": str(res.url),
        "public_title": title,
    }


def _read_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            data = json.loads(path.read_text(encoding=encoding))
            return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


def _status_badge(ok: bool, good_label: str = "정상", bad_label: str = "확인 필요") -> str:
    bg = "#e8f7ef" if ok else "#fff0eb"
    fg = "#146a3b" if ok else "#a33a24"
    label = good_label if ok else bad_label
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;padding:4px 10px;'
        f'border-radius:999px;background:{bg};color:{fg};font-size:12px;font-weight:800;">{html.escape(label)}</span>'
    )


def _summary_line(label: str, value: str) -> str:
    return (
        f'<div style="display:flex;justify-content:space-between;gap:12px;padding:8px 0;'
        f'border-top:1px solid #e4ebf2;">'
        f'<span style="color:#5c7085;font-size:13px;">{html.escape(label)}</span>'
        f'<strong style="font-size:13px;color:#163047;text-align:right;">{html.escape(value)}</strong>'
        f'</div>'
    )


def _join_or_dash(items: List[str]) -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return ", ".join(cleaned) if cleaned else "-"


def _artifact_entry(label: str, kind: str, path: Path) -> Dict[str, Any]:
    exists = path.exists()
    updated_at = ""
    if exists:
        try:
            updated_at = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            updated_at = ""
    return {
        "label": label,
        "kind": kind,
        "path": str(path),
        "exists": bool(exists),
        "updated_at": updated_at,
    }


def _build_dashboard_snapshot(*, regression_gate: Dict[str, Any], publish_generated_at: str) -> Dict[str, Any]:
    secure = _read_json_file(SECURE_STATUS_PATH)
    permit_sanity = _read_json_file(PERMIT_SANITY_PATH)
    permit_step_smoke = _read_json_file(PERMIT_STEP_SMOKE_PATH)
    browser_smoke = _read_json_file(BROWSER_SMOKE_PATH)
    partner_api_smoke = _read_json_file(PARTNER_API_SMOKE_PATH)
    regression = _read_json_file(REGRESSION_REPORT_PATH)
    permit_checks = dict(permit_sanity.get("checks") or {})
    permit_integrity = dict(permit_checks.get("integrity") or {})
    permit_integrity_matches = [row for row in list(permit_integrity.get("matches") or []) if isinstance(row, dict)]
    secure_rows = [row for row in list(secure.get("rows") or []) if isinstance(row, dict)]
    secure_ok = bool(secure_rows) and all(str(row.get("Status") or "") == "OK" for row in secure_rows)
    overall_ok = (
        secure_ok
        and bool(permit_sanity.get("ok"))
        and bool(permit_integrity.get("ok", True))
        and bool(permit_step_smoke.get("ok"))
        and bool(browser_smoke.get("ok"))
        and bool(partner_api_smoke.get("ok"))
        and bool(regression.get("ok"))
        and bool(regression_gate.get("ok"))
    )
    snapshot = {
        "generated_at": publish_generated_at,
        "secure_stack": {
            "checked_at": str(secure.get("checked_at") or ""),
            "ok": secure_ok,
            "rows": [
                {
                    "api": str(row.get("Api") or ""),
                    "port": int(row.get("Port") or 0),
                    "status": str(row.get("Status") or ""),
                    "health_status": int(row.get("HealthStatus") or 0),
                    "listener_pid": int(row.get("ListenerPid") or 0),
                }
                for row in secure_rows
            ],
        },
        "permit_wizard_sanity": {
            "generated_at": str(permit_sanity.get("generated_at") or ""),
            "ok": bool(permit_sanity.get("ok")),
            "issues": [str(x) for x in list(permit_checks.get("issues") or [])],
        },
        "permit_integrity": {
            "generated_at": str(permit_sanity.get("generated_at") or ""),
            "ok": bool(permit_integrity.get("ok", True)),
            "issues": [str(x) for x in list(permit_integrity.get("issues") or [])],
            "matches": [
                {
                    "name": str(row.get("name") or ""),
                    "count": int(row.get("count") or 0),
                }
                for row in permit_integrity_matches
            ],
            "excerpts": [
                {
                    "name": str(row.get("name") or ""),
                    "sample": str(sample or "").strip(),
                }
                for row in permit_integrity_matches
                for sample in list(row.get("samples") or [])[:2]
                if str(sample or "").strip()
            ],
        },
        "permit_step_transition_smoke": {
            "generated_at": str(permit_step_smoke.get("generated_at") or ""),
            "ok": bool(permit_step_smoke.get("ok")),
            "blocking_issues": [str(x) for x in list(permit_step_smoke.get("blocking_issues") or [])],
        },
        "browser_smoke": {
            "generated_at": str(browser_smoke.get("generated_at") or ""),
            "ok": bool(browser_smoke.get("ok")),
            "yangdo_ok": bool(((browser_smoke.get("checks") or {}).get("yangdo") or {}).get("ok")),
            "permit_ok": bool(((browser_smoke.get("checks") or {}).get("permit") or {}).get("ok")),
            "blocking_issues": [str(x) for x in list(browser_smoke.get("blocking_issues") or [])],
        },
        "partner_api_contract_smoke": {
            "generated_at": str(partner_api_smoke.get("generated_at") or ""),
            "ok": bool(partner_api_smoke.get("ok")),
            "live_blackbox_ok": bool((((partner_api_smoke.get("live_blackbox") or {}).get("ok")))),
            "ephemeral_permit_ok": bool((((partner_api_smoke.get("ephemeral_permit") or {}).get("ok")))),
            "blocking_issues": [str(x) for x in list(partner_api_smoke.get("blocking_issues") or [])],
        },
        "regression": {
            "generated_at": str(regression.get("generated_at") or ""),
            "ok": bool(regression.get("ok")),
            "live_smoke_ok": bool(((regression.get("live_blackbox_smoke") or {}).get("ok"))),
            "permit_wizard_ok": bool((((regression.get("permit_wizard_sanity") or {}).get("result") or {}).get("ok"))),
            "blocking_issues": [str(x) for x in list(regression.get("blocking_issues") or [])],
            "gate_ok": bool(regression_gate.get("ok")),
        },
        "publish": {
            "generated_at": publish_generated_at,
            "gate_ok": bool(regression_gate.get("ok")),
        },
        "permit_failure_artifacts": {
            "items": [
                _artifact_entry("permit step screenshot", "image", PERMIT_STEP_FAIL_SCREENSHOT),
                _artifact_entry("permit step html", "html", PERMIT_STEP_FAIL_HTML),
                _artifact_entry("permit browser screenshot", "image", PERMIT_BROWSER_FAIL_SCREENSHOT),
                _artifact_entry("permit browser html", "html", PERMIT_BROWSER_FAIL_HTML),
            ],
        },
    }
    snapshot["one_line_summary"] = {
        "ok": overall_ok,
        "text": (
            "GREEN"
            if overall_ok
            else "CHECK"
        )
        + " | "
        + f"secure={ 'ok' if secure_ok else 'check' }"
        + f" permitSanity={ 'ok' if bool(permit_sanity.get('ok')) else 'check' }"
        + f" permitIntegrity={ 'ok' if bool(permit_integrity.get('ok', True)) else 'check' }"
        + f" permitStep={ 'ok' if bool(permit_step_smoke.get('ok')) else 'check' }"
        + f" browser={ 'ok' if bool(browser_smoke.get('ok')) else 'check' }"
        + f" partnerApi={ 'ok' if bool(partner_api_smoke.get('ok')) else 'check' }"
        + f" regression={ 'ok' if bool(regression.get('ok')) else 'check' }"
        + f" publishGate={ 'ok' if bool(regression_gate.get('ok')) else 'check' }",
        "components": {
            "secure_stack": secure_ok,
            "permit_wizard_sanity": bool(permit_sanity.get("ok")),
            "permit_integrity": bool(permit_integrity.get("ok", True)),
            "permit_step_transition_smoke": bool(permit_step_smoke.get("ok")),
            "browser_smoke": bool(browser_smoke.get("ok")),
            "partner_api_contract_smoke": bool(partner_api_smoke.get("ok")),
            "regression": bool(regression.get("ok")),
            "publish_gate": bool(regression_gate.get("ok")),
        },
    }
    return snapshot


def _hub_html(snapshot: Dict[str, Any]) -> str:
    secure = dict(snapshot.get("secure_stack") or {})
    permit = dict(snapshot.get("permit_wizard_sanity") or {})
    permit_integrity = dict(snapshot.get("permit_integrity") or {})
    permit_step = dict(snapshot.get("permit_step_transition_smoke") or {})
    smoke = dict(snapshot.get("browser_smoke") or {})
    partner_api = dict(snapshot.get("partner_api_contract_smoke") or {})
    regression = dict(snapshot.get("regression") or {})
    publish = dict(snapshot.get("publish") or {})
    permit_failure_artifacts = dict(snapshot.get("permit_failure_artifacts") or {})
    one_line = dict(snapshot.get("one_line_summary") or {})
    secure_rows = [row for row in list(secure.get("rows") or []) if isinstance(row, dict)]
    integrity_matches = [row for row in list(permit_integrity.get("matches") or []) if isinstance(row, dict)]
    integrity_excerpts = [row for row in list(permit_integrity.get("excerpts") or []) if isinstance(row, dict)]
    failure_artifact_items = [row for row in list(permit_failure_artifacts.get("items") or []) if isinstance(row, dict)]
    secure_rows_html = "".join(
        (
            '<div style="display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-top:1px solid #e4ebf2;">'
            f'<span style="font-size:13px;color:#163047;">{html.escape(str(row.get("api") or "").upper())} '
            f'({html.escape(str(row.get("port") or ""))})</span>'
            f'<strong style="font-size:13px;color:#163047;">{html.escape(str(row.get("status") or ""))} / '
            f'HTTP {html.escape(str(row.get("health_status") or ""))}</strong>'
            '</div>'
        )
        for row in secure_rows
    ) or '<div style="padding:8px 0;border-top:1px solid #e4ebf2;font-size:13px;color:#7b8794;">secure stack snapshot 없음</div>'
    integrity_rows_html = "".join(
        _summary_line(str(row.get("name") or "-"), str(row.get("count") or 0))
        for row in integrity_matches
    )
    integrity_excerpt_html = "".join(
        (
            '<div style="padding:10px 12px;border-top:1px solid #e4ebf2;">'
            f'<div style="font-size:11px;font-weight:800;color:#8c6a3c;margin-bottom:6px;">{html.escape(str(row.get("name") or "-"))}</div>'
            f'<pre style="margin:0;white-space:pre-wrap;word-break:break-word;font:12px/1.55 Consolas,monospace;color:#163047;background:#f8fafc;border:1px solid #dbe3ec;border-radius:10px;padding:10px;">{html.escape(str(row.get("sample") or "-"))}</pre>'
            '</div>'
        )
        for row in integrity_excerpts[:4]
    )
    failure_artifact_rows_html = "".join(
        (
            '<div style="padding:10px 0;border-top:1px solid #e4ebf2;">'
            f'<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">'
            f'<strong style="font-size:13px;color:#163047;">{html.escape(str(row.get("label") or "-"))}</strong>'
            f'{_status_badge(bool(row.get("exists")), "존재", "없음")}'
            '</div>'
            f'<div style="margin-top:6px;font-size:12px;color:#5c7085;">{html.escape(str(row.get("updated_at") or "-"))}</div>'
            f'<div style="margin-top:6px;font:12px/1.55 Consolas,monospace;color:#163047;word-break:break-all;">{html.escape(str(row.get("path") or "-"))}</div>'
            '</div>'
        )
        for row in failure_artifact_items
    )
    smoke_blockers = _join_or_dash([str(x) for x in list(smoke.get("blocking_issues") or [])])
    partner_api_blockers = _join_or_dash([str(x) for x in list(partner_api.get("blocking_issues") or [])])
    regression_blockers = _join_or_dash([str(x) for x in list(regression.get("blocking_issues") or [])])
    permit_integrity_issues = _join_or_dash([str(x) for x in list(permit_integrity.get("issues") or [])])
    return f"""
<div style="max-width:1120px;margin:0 auto;padding:32px 20px;background:#f5f7fb;border:1px solid #dbe3ec;border-radius:20px;font-family:'Pretendard','Noto Sans KR',sans-serif;line-height:1.65;color:#163047;">
  <div style="font-size:13px;font-weight:700;color:#6b7d90;margin-bottom:8px;">SEOULMNA.KR PRIVATE</div>
  <h1 style="margin:0 0 12px;font-size:34px;line-height:1.25;color:#0d2f4f;">AI 계산기 관리자 허브</h1>
  <p style="margin:0 0 12px;font-size:17px;color:#334e68;">관리자 로그인 상태에서만 확인 가능합니다. 현재 운영 중인 관리자 전용 계산기 링크와 최신 QA 상태를 같은 화면에서 확인합니다.</p>
    <div style="display:flex;flex-wrap:wrap;gap:10px;margin:0 0 24px;">
      {_status_badge(bool(publish.get("gate_ok")), "배포 게이트 통과", "배포 게이트 실패")}
      {_status_badge(bool(regression.get("ok")), "운영 회귀 정상", "운영 회귀 확인 필요")}
      {_status_badge(bool(smoke.get("ok")), "브라우저 스모크 정상", "브라우저 스모크 실패")}
      {_status_badge(bool(permit.get("ok")), "인허가 wizard sanity 정상", "인허가 wizard sanity 실패")}
      {_status_badge(bool(permit_integrity.get("ok", True)), "permit integrity 정상", "permit integrity 실패")}
      {_status_badge(bool(permit_step.get("ok")), "인허가 step smoke 정상", "인허가 step smoke 실패")}
      {_status_badge(bool(partner_api.get("ok")), "partner contract smoke 정상", "partner contract smoke 실패")}
      {_status_badge(bool(secure.get("ok")), "secure stack 정상", "secure stack 확인 필요")}
    </div>
  <div style="margin:0 0 20px;padding:14px 16px;border-radius:14px;background:#0d2f4f;color:#f5f7fb;">
    <div style="font-size:12px;font-weight:800;opacity:.8;margin-bottom:6px;">ONE-LINE SUMMARY</div>
    <div style="font-size:14px;font-weight:700;line-height:1.6;">{html.escape(str(one_line.get("text") or "-"))}</div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-bottom:20px;">
    <div style="background:#ffffff;border:1px solid #d6e0ea;border-radius:16px;padding:18px 20px;box-shadow:0 10px 24px rgba(8,36,64,.06);">
      <div style="font-size:12px;font-weight:800;color:#8c6a3c;margin-bottom:6px;">OPERATIONS</div>
      <div style="font-size:22px;font-weight:800;margin-bottom:10px;">Live API / Secure Stack</div>
      <div style="font-size:14px;color:#50657a;">마지막 점검: {html.escape(str(secure.get("checked_at") or "-"))}</div>
      {secure_rows_html}
    </div>
    <div style="background:#ffffff;border:1px solid #d6e0ea;border-radius:16px;padding:18px 20px;box-shadow:0 10px 24px rgba(8,36,64,.06);">
      <div style="font-size:12px;font-weight:800;color:#8c6a3c;margin-bottom:6px;">QA</div>
      <div style="font-size:22px;font-weight:800;margin-bottom:10px;">Regression / Smoke</div>
      {_summary_line("운영 회귀", "정상" if bool(regression.get("ok")) else "확인 필요")}
      {_summary_line("live blackbox smoke", "정상" if bool(regression.get("live_smoke_ok")) else "실패")}
      {_summary_line("permit wizard sanity", "정상" if bool(regression.get("permit_wizard_ok")) else "실패")}
      {_summary_line("permit step smoke", "정상" if bool(permit_step.get("ok")) else "실패")}
      {_summary_line("브라우저 smoke", "양도/인허가 모두 정상" if bool(smoke.get("yangdo_ok")) and bool(smoke.get("permit_ok")) else "확인 필요")}
      {_summary_line("partner contract smoke", "live/emulated 모두 정상" if bool(partner_api.get("live_blackbox_ok")) and bool(partner_api.get("ephemeral_permit_ok")) else "확인 필요")}
      {_summary_line("회귀 blocking issues", regression_blockers)}
    </div>
    <div style="background:#ffffff;border:1px solid #d6e0ea;border-radius:16px;padding:18px 20px;box-shadow:0 10px 24px rgba(8,36,64,.06);">
      <div style="font-size:12px;font-weight:800;color:#8c6a3c;margin-bottom:6px;">PARTNER API</div>
      <div style="font-size:22px;font-weight:800;margin-bottom:10px;">Health Contract Smoke</div>
      {_summary_line("상태", "정상" if bool(partner_api.get("ok")) else "확인 필요")}
      {_summary_line("live blackbox", "정상" if bool(partner_api.get("live_blackbox_ok")) else "실패")}
      {_summary_line("ephemeral permit", "정상" if bool(partner_api.get("ephemeral_permit_ok")) else "실패")}
      {_summary_line("점검 시각", str(partner_api.get("generated_at") or "-"))}
      {_summary_line("blocking issues", partner_api_blockers)}
    </div>
    <div style="background:#ffffff;border:1px solid #d6e0ea;border-radius:16px;padding:18px 20px;box-shadow:0 10px 24px rgba(8,36,64,.06);">
      <div style="font-size:12px;font-weight:800;color:#8c6a3c;margin-bottom:6px;">PERMIT INTEGRITY</div>
      <div style="font-size:22px;font-weight:800;margin-bottom:10px;">Template Integrity</div>
      {_summary_line("상태", "정상" if bool(permit_integrity.get("ok", True)) else "확인 필요")}
      {_summary_line("이슈", permit_integrity_issues)}
      {_summary_line("점검 시각", str(permit_integrity.get("generated_at") or "-"))}
      {integrity_rows_html or _summary_line("패턴 카운트", "무결성 패턴 0건")}
      {integrity_excerpt_html}
    </div>
    <div style="background:#ffffff;border:1px solid #d6e0ea;border-radius:16px;padding:18px 20px;box-shadow:0 10px 24px rgba(8,36,64,.06);">
      <div style="font-size:12px;font-weight:800;color:#8c6a3c;margin-bottom:6px;">PUBLISH</div>
      <div style="font-size:22px;font-weight:800;margin-bottom:10px;">Last Private Publish</div>
      {_summary_line("허브/자식 page publish", "정상" if bool(publish.get("gate_ok")) else "확인 필요")}
      {_summary_line("마지막 배포 시각", str(publish.get("generated_at") or "-"))}
      {_summary_line("permit sanity 시각", str(permit.get("generated_at") or "-"))}
      {_summary_line("permit step smoke 시각", str(permit_step.get("generated_at") or "-"))}
      {_summary_line("browser smoke 시각", str(smoke.get("generated_at") or "-"))}
      {_summary_line("browser smoke issues", smoke_blockers)}
    </div>
    <div style="background:#ffffff;border:1px solid #d6e0ea;border-radius:16px;padding:18px 20px;box-shadow:0 10px 24px rgba(8,36,64,.06);">
      <div style="font-size:12px;font-weight:800;color:#8c6a3c;margin-bottom:6px;">PERMIT ARTIFACTS</div>
      <div style="font-size:22px;font-weight:800;margin-bottom:10px;">Latest Failure Files</div>
      {_summary_line("설명", "최근 실패 screenshot/html 경로")}
      {failure_artifact_rows_html or _summary_line("artifact", "저장된 실패 artifact 없음")}
    </div>
  </div>
  <div style="display:grid;grid-template-columns:1fr;gap:16px;">
    <a href="https://seoulmna.kr/ai-admin-hub/yangdo-ai-admin/" style="display:block;text-decoration:none;background:#ffffff;border:1px solid #d6e0ea;border-radius:16px;padding:18px 20px;color:#163047;box-shadow:0 10px 24px rgba(8,36,64,.06);">
      <div style="font-size:12px;font-weight:800;color:#8c6a3c;margin-bottom:6px;">ADMIN ONLY</div>
      <div style="font-size:24px;font-weight:800;margin-bottom:8px;">AI 양도가 산정 계산기</div>
      <div style="font-size:15px;color:#50657a;">양도양수 거래가 검토와 상담 기준 확인 화면</div>
    </a>
    <a href="https://seoulmna.kr/ai-admin-hub/ai-license-acquisition-admin/" style="display:block;text-decoration:none;background:#ffffff;border:1px solid #d6e0ea;border-radius:16px;padding:18px 20px;color:#163047;box-shadow:0 10px 24px rgba(8,36,64,.06);">
      <div style="font-size:12px;font-weight:800;color:#8c6a3c;margin-bottom:6px;">ADMIN ONLY</div>
      <div style="font-size:24px;font-weight:800;margin-bottom:8px;">AI 인허가 사전검토 진단기</div>
      <div style="font-size:15px;color:#50657a;">신규등록 인허가 요건 검토 화면</div>
    </a>
  </div>
  <p style="margin:20px 0 0;font-size:13px;color:#6b7d90;">비로그인 공개 접근 시에는 허브와 하위 계산기 페이지가 모두 노출되지 않도록 private 상태를 유지합니다. 현재 허브는 최근 regression/smoke 로그 스냅샷을 정적으로 표시합니다.</p>
</div>
""".strip()



def _print_json_console(data: Dict[str, Any]) -> None:
    try:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        print(json.dumps(data, ensure_ascii=True, indent=2))


def _trim_text(value: str, *, limit: int = 1600) -> str:
    txt = str(value or "")
    if len(txt) <= limit:
        return txt
    half = max(200, limit // 2)
    return txt[:half] + "\n... [trimmed] ...\n" + txt[-half:]


def _run_regression_gate(*, skip_regression: bool) -> Dict[str, Any]:
    if skip_regression:
        return {
            "skipped": True,
            "ok": True,
            "report_path": str(REGRESSION_REPORT_PATH),
        }

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_yangdo_operational_regression.py"),
        "--skip-restart",
        "--report",
        str(REGRESSION_REPORT_PATH),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    report: Dict[str, Any] = {}
    if REGRESSION_REPORT_PATH.exists():
        try:
            report = json.loads(REGRESSION_REPORT_PATH.read_text(encoding="utf-8"))
        except Exception:
            report = {}
    result: Dict[str, Any] = {
        "skipped": False,
        "ok": proc.returncode == 0 and bool(report.get("ok")),
        "command": cmd,
        "returncode": int(proc.returncode),
        "stdout_preview": _trim_text(proc.stdout or ""),
        "stderr_preview": _trim_text(proc.stderr or ""),
        "report_path": str(REGRESSION_REPORT_PATH),
        "blocking_issues": list(report.get("blocking_issues") or []),
    }
    if report:
        result["report_summary"] = {
            "generated_at": report.get("generated_at"),
            "ok": report.get("ok"),
            "blocking_issues": list(report.get("blocking_issues") or []),
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the private SeoulMNA AI admin pages after regression checks.")
    parser.add_argument("--skip-regression", action="store_true", default=False)
    args = parser.parse_args()

    regression_gate = _run_regression_gate(skip_regression=bool(args.skip_regression))
    publish_generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dashboard_snapshot = _build_dashboard_snapshot(
        regression_gate=regression_gate,
        publish_generated_at=publish_generated_at,
    )
    if not regression_gate.get("ok"):
        fail_report = {
            "generated_at": publish_generated_at,
            "ok": False,
            "stage": "regression_gate",
            "regression_gate": regression_gate,
            "dashboard_snapshot": dashboard_snapshot,
        }
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(fail_report, ensure_ascii=False, indent=2), encoding="utf-8")
        HUB_DASHBOARD_PATH.write_text(json.dumps(dashboard_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        _print_json_console(fail_report)
        return 1

    env = _env_map(ENV_PATH)
    wp_url, auth, auth_json = _wp_auth_headers(env)

    owner_html = OWNER_SOURCE.read_text(encoding="utf-8", errors="replace")
    permit_html = PERMIT_SOURCE.read_text(encoding="utf-8", errors="replace")
    permit_fragment = _extract_fragment(permit_html)

    owner_page = _update_page(
        wp_url=wp_url,
        auth=auth,
        auth_json=auth_json,
        page_id=OWNER_PAGE_ID,
        title=OWNER_TITLE,
        slug=OWNER_SLUG,
        status="private",
        content=owner_html,
        parent=HUB_PAGE_ID,
    )
    permit_page = _update_page(
        wp_url=wp_url,
        auth=auth,
        auth_json=auth_json,
        page_id=PERMIT_PAGE_ID,
        title=PERMIT_TITLE,
        slug=PERMIT_SLUG,
        status="private",
        content=permit_fragment,
        parent=HUB_PAGE_ID,
    )
    hub_page = _update_page(
        wp_url=wp_url,
        auth=auth,
        auth_json=auth_json,
        page_id=HUB_PAGE_ID,
        title=HUB_TITLE,
        slug=HUB_SLUG,
        status="private",
        content=_hub_html(dashboard_snapshot),
        parent=0,
    )

    page_report = {
        "generated_at": publish_generated_at,
        "wp_url": wp_url,
        "ok": True,
        "regression_gate": regression_gate,
        "dashboard_snapshot": dashboard_snapshot,
        "pages": {
            "yangdo_owner": {
                "id": OWNER_PAGE_ID,
                "slug": OWNER_SLUG,
                "title": OWNER_TITLE,
                "source": str(OWNER_SOURCE),
                "bytes": OWNER_SOURCE.stat().st_size,
                "wp_status": str(owner_page.get("status", "")),
                "url": str(owner_page.get("link", "")),
                **_public_probe(str(owner_page.get("link", ""))),
            },
            "permit_private": {
                "id": PERMIT_PAGE_ID,
                "slug": PERMIT_SLUG,
                "title": PERMIT_TITLE,
                "source": str(PERMIT_SOURCE),
                "bytes": PERMIT_SOURCE.stat().st_size,
                "wp_status": str(permit_page.get("status", "")),
                "url": str(permit_page.get("link", "")),
                **_public_probe(str(permit_page.get("link", ""))),
            },
        },
    }

    hub_report = {
        "generated_at": publish_generated_at,
        "ok": True,
        "regression_gate": regression_gate,
        "dashboard_snapshot": dashboard_snapshot,
        "hub": {
            "id": HUB_PAGE_ID,
            "slug": HUB_SLUG,
            "title": HUB_TITLE,
            "status": str(hub_page.get("status", "")),
            "url": str(hub_page.get("link", "")),
            **_public_probe(str(hub_page.get("link", ""))),
        },
        "children": {
            "yangdo": {
                "id": OWNER_PAGE_ID,
                "slug": OWNER_SLUG,
                "title": OWNER_TITLE,
                "status": str(owner_page.get("status", "")),
                "parent": int(owner_page.get("parent", 0) or 0),
                "link": str(owner_page.get("link", "")),
            },
            "permit": {
                "id": PERMIT_PAGE_ID,
                "slug": PERMIT_SLUG,
                "title": PERMIT_TITLE,
                "status": str(permit_page.get("status", "")),
                "parent": int(permit_page.get("parent", 0) or 0),
                "link": str(permit_page.get("link", "")),
            },
        },
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(page_report, ensure_ascii=False, indent=2), encoding="utf-8")
    HUB_REPORT_PATH.write_text(json.dumps(hub_report, ensure_ascii=False, indent=2), encoding="utf-8")
    HUB_DASHBOARD_PATH.write_text(json.dumps(dashboard_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    _print_json_console(page_report)
    _print_json_console(hub_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

