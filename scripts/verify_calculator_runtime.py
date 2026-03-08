import argparse
import json
import os
import shutil
import subprocess
import tempfile
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.widget_health_contract import load_widget_health_contract

DEFAULT_BUNDLE_MANIFEST = ROOT / "output" / "widget" / "bundles" / "seoul_widget_internal" / "manifest.json"


def _is_kr_only_mode() -> bool:
    raw = str(os.getenv("SMNA_KR_ONLY_DEV", "")).strip().lower()
    if raw in {"1", "true", "yes", "on", "y"}:
        return True
    return (ROOT / "logs/kr_only_mode.lock").exists()


def _save_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _check_static(url: str, required: List[str], timeout_sec: int = 30, require_any: Optional[List[str]] = None) -> Dict:
    out = {
        "kind": "static",
        "url": url,
        "ok": False,
        "status_code": 0,
        "length": 0,
        "found": {},
        "found_any": {},
        "error": "",
    }
    try:
        res = requests.get(url, timeout=timeout_sec)
        txt = res.text or ""
        out["status_code"] = int(res.status_code)
        out["length"] = len(txt)
        for key in required:
            out["found"][key] = key in txt
        any_tokens = [str(x or "").strip() for x in (require_any or []) if str(x or "").strip()]
        for key in any_tokens:
            out["found_any"][key] = key in txt
        any_ok = True if not any_tokens else any(bool(v) for v in out["found_any"].values())
        out["ok"] = res.status_code == 200 and all(bool(v) for v in out["found"].values()) and any_ok
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    return out


def _find_chrome_exe() -> str:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
    ]
    for c in candidates:
        if not c:
            continue
        p = Path(str(c))
        if p.exists():
            return str(p)
    return ""


def _render_dom_with_chrome(chrome_exe: str, url: str, timeout_sec: int = 45) -> Dict:
    out = {
        "url": url,
        "ok": False,
        "length": 0,
        "dom": "",
        "error": "",
        "returncode": 0,
    }
    try:
        with tempfile.TemporaryDirectory(prefix="smna_chrome_") as user_data:
            cmd = [
                chrome_exe,
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                f"--user-data-dir={user_data}",
                "--virtual-time-budget=12000",
                "--dump-dom",
                url,
            ]
            p = subprocess.run(  # noqa: PLW1510
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                encoding="utf-8",
                errors="replace",
            )
            dom = p.stdout or ""
            out["returncode"] = int(p.returncode)
            out["dom"] = dom
            out["length"] = len(dom)
            out["ok"] = p.returncode == 0 and bool(dom)
            if p.returncode != 0:
                out["error"] = "\n".join((p.stderr or "").splitlines()[-15:])
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    return out


def _check_runtime(chrome_exe: str, url: str, required: List[str], timeout_sec: int = 45) -> Dict:
    dom_info = _render_dom_with_chrome(chrome_exe, url, timeout_sec=timeout_sec)
    out = {
        "kind": "runtime",
        "url": url,
        "ok": False,
        "length": int(dom_info.get("length", 0) or 0),
        "returncode": int(dom_info.get("returncode", 0) or 0),
        "found": {},
        "error": str(dom_info.get("error", "") or ""),
    }
    if not dom_info.get("ok"):
        return out
    dom = str(dom_info.get("dom", "") or "")
    for key in required:
        out["found"][key] = key in dom
    out["ok"] = all(bool(v) for v in out["found"].values())
    return out


def _runtime_frame_tokens(frame_url: str, mode: str) -> List[str]:
    src = str(frame_url or "").strip()
    if not src:
        return []
    parsed = urlparse(src)
    base = src.split("?", 1)[0].strip()
    tokens = [base]
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key in ("tenant_id", "from", "mode"):
        value = str(query.get(key) or "").strip()
        if value:
            tokens.append(f"{key}={value}")
    out: List[str] = []
    for tok in tokens:
        t = str(tok or "").strip()
        if not t or t in out:
            continue
        out.append(t)
    return out


def _load_widget_url(manifest_path: Path, widget: str) -> str:
    manifest = _load_json(manifest_path, {}) or {}
    rows = manifest.get("widgets") if isinstance(manifest, dict) else []
    wanted = str(widget or "").strip().lower()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("widget") or "").strip().lower() != wanted:
            continue
        return str(row.get("widget_url") or "").strip()
    return ""


def _set_value_js(driver, element_id: str, value: str) -> None:
    driver.execute_script(
        """
const el = document.getElementById(arguments[0]);
if (!el) { return false; }
const val = String(arguments[1] ?? "");
const tag = String(el.tagName || "").toLowerCase();
if (tag === "select") {
  el.value = val;
  if (el.value !== val) {
    for (const opt of Array.from(el.options || [])) {
      if (String(opt.text || "").trim() === val) {
        el.value = opt.value;
        break;
      }
    }
  }
} else {
  el.focus();
  el.value = val;
}
el.dispatchEvent(new Event("input", { bubbles: true }));
el.dispatchEvent(new Event("change", { bubbles: true }));
return true;
        """,
        element_id,
        value,
    )


def _text(driver, element_id: str) -> str:
    try:
        return str(driver.find_element("id", element_id).text or "").strip()
    except Exception:
        return ""


def _permit_bootstrap_snapshot(driver) -> Dict[str, Any]:
    return dict(
        driver.execute_script(
            """
const count = (id) => {
  const el = document.getElementById(id);
  return el && el.options ? el.options.length : 0;
};
const stepTitle = document.getElementById('permitWizardStepTitle');
return {
  category_count: count('categorySelect'),
  focus_quick_count: count('focusQuickSelect'),
  industry_count: count('industrySelect'),
  step_title: stepTitle ? String(stepTitle.textContent || '').trim() : '',
};
            """
        )
        or {}
    )


def _check_click_interaction(page_url: str, mode: str) -> Dict:
    out = {
        "kind": "interaction",
        "url": page_url,
        "mode": mode,
        "ok": False,
        "error": "",
        "center_text": "",
        "range_text": "",
        "confidence_text": "",
        "preflight": {},
    }
    try:
        from selenium import webdriver  # type: ignore
        from selenium.webdriver.chrome.options import Options  # type: ignore
        from selenium.webdriver.common.by import By  # type: ignore
        from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
        from selenium.webdriver.support import expected_conditions as EC  # type: ignore

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)
        try:
            wait = WebDriverWait(driver, 35)
            driver.set_page_load_timeout(60)
            driver.get(page_url)

            # Bridge page (co.kr) may contain iframe, or it may redirect straight to kr page.
            if "seoulmna.co.kr" in str(driver.current_url):
                frame = wait.until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            '#smna-calc-bridge iframe, #ctt iframe[src*="yangdo-ai-customer"], #ctt iframe[src*="ai-license-acquisition-calculator"]',
                        )
                    )
                )
                driver.switch_to.frame(frame)

            if mode == "customer":
                wait.until(EC.presence_of_element_located((By.ID, "in-license")))
                _set_value_js(driver, "in-license", "전기")
                wait.until(
                    lambda d: bool(
                        d.execute_script(
                            "const btn=document.querySelector('[data-yangdo-wizard-next=\"0\"]'); return !!btn && btn.disabled === false;"
                        )
                    )
                )
                driver.execute_script(
                    """
const btn = document.querySelector('[data-yangdo-wizard-next="0"]');
if (btn && !btn.disabled) btn.click();
                    """
                )
                wait.until(lambda d: "검색 기준 입력" in _text(d, "yangdoWizardStepTitle"))
                driver.execute_script(
                    """
const btn = document.querySelector('[data-scale-mode="sales"]');
if (btn) btn.click();
                    """
                )
                _set_value_js(driver, "in-sales-input-mode", "최근 3년 실적 합계(억)")
                _set_value_js(driver, "in-sales3-total", "12")
                wait.until(
                    lambda d: bool(
                        d.execute_script(
                            "const btn=document.querySelector('[data-yangdo-wizard-next=\"1\"]'); return !!btn && btn.disabled === false;"
                        )
                    )
                )
                driver.execute_script(
                    """
const btn = document.querySelector('[data-yangdo-wizard-next="1"]');
if (btn && !btn.disabled) btn.click();
                    """
                )
                wait.until(lambda d: "핵심 가격 영향 입력" in _text(d, "yangdoWizardStepTitle"))
                _set_value_js(driver, "in-capital", "1.5")
                _set_value_js(driver, "in-balance", "0.8")
                wait.until(
                    lambda d: bool(
                        d.execute_script(
                            "const btn=document.querySelector('[data-yangdo-wizard-next=\"2\"]'); return !!btn && btn.disabled === false;"
                        )
                    )
                )
                driver.execute_script(
                    """
const btn = document.querySelector('[data-yangdo-wizard-next="2"]');
if (btn && !btn.disabled) btn.click();
                    """
                )
                wait.until(lambda d: "구조·정산 정보" in _text(d, "yangdoWizardStepTitle"))
                _set_value_js(driver, "in-reorg-mode", "포괄")
                _set_value_js(driver, "in-balance-usage-mode", "credit_transfer")
                wait.until(
                    lambda d: bool(
                        d.execute_script(
                            "const btn=document.querySelector('[data-yangdo-wizard-next=\"3\"]'); return !!btn && btn.disabled === false;"
                        )
                    )
                )
                driver.execute_script(
                    """
const btn = document.querySelector('[data-yangdo-wizard-next="3"]');
if (btn && !btn.disabled) btn.click();
                    """
                )
                wait.until(lambda d: "재무·회사 선택 정보" in _text(d, "yangdoWizardStepTitle"))
                driver.execute_script(
                    """
const btn = document.querySelector('[data-yangdo-wizard-next="4"]');
if (btn && !btn.disabled) btn.click();
                    """
                )
                wait.until(
                    lambda d: (
                        _text(d, "out-confidence") not in {"", "-"}
                        or _text(d, "out-center") not in {"", "-"}
                        or "상담 검증 후 안내" in _text(d, "out-center")
                    )
                )
                out["center_text"] = _text(driver, "out-center")
                out["range_text"] = _text(driver, "out-range") or _text(driver, "settlement-summary")
                out["confidence_text"] = _text(driver, "out-confidence") or _text(driver, "risk-note")
                out["ok"] = bool(out["center_text"]) and out["center_text"] != "-"
                return out

            if mode == "acquisition":
                wait.until(EC.presence_of_element_located((By.ID, "industrySearchInput")))
                wait.until(
                    lambda d: (
                        (snap := _permit_bootstrap_snapshot(d))
                        and int((snap.get("category_count") or 0)) > 0
                        and int((snap.get("focus_quick_count") or 0)) > 0
                        and bool(str(snap.get("step_title") or "").strip())
                    )
                )
                preflight = _permit_bootstrap_snapshot(driver)
                out["preflight"] = {
                    "category_count": int(preflight.get("category_count") or 0),
                    "focus_quick_count": int(preflight.get("focus_quick_count") or 0),
                    "industry_count": int(preflight.get("industry_count") or 0),
                    "step_title": str(preflight.get("step_title") or "").strip(),
                }
                if (
                    int(out["preflight"].get("category_count") or 0) <= 0
                    or int(out["preflight"].get("focus_quick_count") or 0) <= 0
                    or not str(out["preflight"].get("step_title") or "").strip()
                ):
                    out["error"] = "permit_bootstrap_preflight_failed"
                    return out
                driver.execute_script(
                    """
const btn = document.querySelector('[data-focus-mode="focus_only"]');
if (btn) btn.click();
                    """
                )
                _set_value_js(driver, "industrySearchInput", "전기공사업")
                wait.until(
                    lambda d: "전기공사업" in str(
                        d.execute_script(
                            """
const el = document.getElementById('industrySelect');
if (!el || el.selectedIndex < 0) return '';
const option = el.options[el.selectedIndex];
return option ? String(option.textContent || '').trim() : '';
                            """
                        )
                        or ""
                    )
                )
                wait.until(
                    lambda d: _text(d, "requiredCapital") not in {
                        "",
                        "-",
                        "확인 필요",
                        "법령 후보 확인",
                        "법령 추출본 확인",
                    }
                )
                if "현재 보유 현황" not in _text(driver, "permitWizardStepTitle"):
                    driver.execute_script(
                        """
const btn = document.querySelector('[data-permit-wizard-next="0"]');
if (btn && !btn.disabled) btn.click();
                        """
                    )
                    wait.until(
                        lambda d: (
                            "업종 확정" in _text(d, "permitWizardStepTitle")
                            or "현재 보유 현황" in _text(d, "permitWizardStepTitle")
                        )
                    )
                if "현재 보유 현황" not in _text(driver, "permitWizardStepTitle"):
                    driver.execute_script(
                        """
const btn = document.querySelector('[data-permit-wizard-next="1"]');
if (btn && !btn.disabled) btn.click();
                        """
                    )
                    wait.until(lambda d: "현재 보유 현황" in _text(d, "permitWizardStepTitle"))

                _set_value_js(driver, "capitalInput", "1.5")
                _set_value_js(driver, "technicianInput", "3")
                _set_value_js(driver, "equipmentInput", "1")
                wait.until(
                    lambda d: "3/3" in str(
                        d.execute_script(
                            "const el=document.getElementById('permitWizardSummary'); return el ? (el.innerText || '') : '';"
                        )
                        or ""
                    )
                )
                wait.until(lambda d: _text(d, "resultBannerTitle") not in {"", "-"})
                wait.until(
                    lambda d: str(
                        d.execute_script(
                            "const el=document.getElementById('resultBrief'); return el ? (el.value || '') : '';"
                        )
                        or ""
                    ).strip()
                    not in {"", "-"}
                )

                out["center_text"] = _text(driver, "requiredCapital")
                out["range_text"] = _text(driver, "resultBannerTitle") or _text(driver, "capitalGapStatus")
                out["confidence_text"] = str(
                    driver.execute_script(
                        "const el=document.getElementById('resultBrief'); return el ? (el.value || '') : '';"
                    )
                    or ""
                ).strip()
                out["preflight"]["industry_count_after_search"] = int(
                    driver.execute_script(
                        """
const el = document.getElementById('industrySelect');
return el && el.options ? el.options.length : 0;
                        """
                    )
                    or 0
                )
                out["ok"] = (
                    bool(out["center_text"])
                    and out["center_text"] != "-"
                    and bool(out["range_text"])
                    and out["range_text"] != "-"
                    and bool(out["confidence_text"])
                    and out["confidence_text"] != "-"
                    and int(out["preflight"].get("industry_count_after_search") or 0) > 0
                )
                return out

            out["error"] = f"unknown interaction mode: {mode}"
            return out
        finally:
            driver.quit()
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
        return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify SeoulMNA calculator runtime health")
    parser.add_argument("--co-base", default="https://seoulmna.co.kr")
    parser.add_argument("--customer-co-id", default="ai_calc")
    parser.add_argument("--acquisition-co-id", default="ai_acq")
    parser.add_argument("--bundle-manifest", default=str(DEFAULT_BUNDLE_MANIFEST))
    parser.add_argument("--frame-customer", default="")
    parser.add_argument("--frame-acquisition", default="")
    parser.add_argument("--kr-customer-url", default="https://seoulmna.kr/yangdo-ai-customer/")
    parser.add_argument("--kr-acquisition-url", default="https://seoulmna.kr/ai-license-acquisition-calculator/")
    parser.add_argument("--kr-only", action="store_true", help="Run KR-only checks and skip any co.kr access")
    parser.add_argument("--allow-no-browser", action="store_true")
    parser.add_argument("--skip-interaction", action="store_true")
    parser.add_argument("--report", default="logs/verify_calculator_runtime_latest.json")
    args = parser.parse_args()

    co_base = str(args.co_base).rstrip("/")
    customer_page = f"{co_base}/bbs/content.php?co_id={args.customer_co_id}"
    acquisition_page = f"{co_base}/bbs/content.php?co_id={args.acquisition_co_id}"
    kr_only = bool(args.kr_only or _is_kr_only_mode())
    manifest_path = Path(str(args.bundle_manifest)).resolve()
    frame_customer = str(args.frame_customer or "").strip() or _load_widget_url(manifest_path, "yangdo") or str(args.kr_customer_url)
    frame_acquisition = str(args.frame_acquisition or "").strip() or _load_widget_url(manifest_path, "permit") or str(args.kr_acquisition_url)

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": True,
        "kr_only_mode": bool(kr_only),
        "health_contract": load_widget_health_contract(),
        "checks": [],
        "warnings": [],
        "blocking_issues": [],
    }

    # Static checks
    if not kr_only:
        report["checks"].append(
            _check_static(
                f"{co_base}/",
                [
                    "SEOULMNA GLOBAL BANNER START",
                    "applyBannerTextBalance",
                    str(frame_customer).split("&from=co", 1)[0],
                    str(frame_acquisition).split("&from=co", 1)[0],
                ],
            )
        )
        report["checks"].append(
            _check_static(
                customer_page,
                [
                    "smna-calc-bridge",
                ],
                require_any=["mountCalculatorBridge", "SMNA_WIDGET_BRIDGE_CUSTOMER", "SMNA_BRIDGE_CUSTOMER"],
            )
        )
        report["checks"].append(
            _check_static(
                acquisition_page,
                [
                    "smna-calc-bridge",
                ],
                require_any=["mountCalculatorBridge", "SMNA_WIDGET_BRIDGE_ACQUISITION", "SMNA_BRIDGE_ACQUISITION"],
            )
        )

    report["checks"].append(
        _check_static(
            str(args.kr_customer_url),
            ["out-yoy-compare", "renderYoyCompare", "buildYoyInsight"],
        )
    )
    report["checks"].append(
        _check_static(
            str(args.kr_acquisition_url),
            ["id=\"industrySearchInput\"", "id=\"industrySelect\""],
            require_any=["id=\"permitWizardSummary\"", "id=\"resultBannerTitle\"", "id=\"requiredCapital\""],
        )
    )

    chrome_exe = _find_chrome_exe()
    if chrome_exe:
        if kr_only:
            report["checks"].append(
                _check_runtime(
                    chrome_exe=chrome_exe,
                    url=str(args.kr_customer_url),
                    required=["id=\"btn-estimate\"", "id=\"out-center\""],
                )
            )
            report["checks"].append(
                _check_runtime(
                    chrome_exe=chrome_exe,
                    url=str(args.kr_acquisition_url),
                    required=[
                        "id=\"industrySearchInput\"",
                        "id=\"industrySelect\"",
                        "id=\"permitWizardStepTitle\"",
                        "id=\"requiredCapital\"",
                        "id=\"resultBannerTitle\"",
                    ],
                )
            )
        else:
            report["checks"].append(
                _check_runtime(
                    chrome_exe=chrome_exe,
                    url=customer_page,
                    required=["id=\"smna-calc-bridge\"", *_runtime_frame_tokens(str(frame_customer), "customer")],
                )
            )
            report["checks"].append(
                _check_runtime(
                    chrome_exe=chrome_exe,
                    url=acquisition_page,
                    required=["id=\"smna-calc-bridge\"", *_runtime_frame_tokens(str(frame_acquisition), "acquisition")],
                )
            )
    else:
        msg = "chrome_not_found_runtime_checks_skipped"
        report["warnings"].append(msg)
        if not args.allow_no_browser:
            report["blocking_issues"].append(msg)

    if not args.skip_interaction:
        interaction_customer_url = str(args.kr_customer_url) if kr_only else customer_page
        interaction_acquisition_url = str(args.kr_acquisition_url) if kr_only else acquisition_page

        interaction_customer = _check_click_interaction(interaction_customer_url, mode="customer")
        report["checks"].append(interaction_customer)
        if not interaction_customer.get("ok"):
            report["blocking_issues"].append(f"interaction check failed: {interaction_customer_url}")

        interaction_acquisition = _check_click_interaction(interaction_acquisition_url, mode="acquisition")
        report["checks"].append(interaction_acquisition)
        if not interaction_acquisition.get("ok"):
            report["blocking_issues"].append(f"interaction check failed: {interaction_acquisition_url}")

    for row in report["checks"]:
        if not bool(row.get("ok")):
            report["blocking_issues"].append(f"{row.get('kind')} check failed: {row.get('url')}")

    report["ok"] = not report["blocking_issues"]
    out_path = (ROOT / args.report).resolve()
    _save_json(out_path, report)

    print(f"[saved] {out_path}")
    print(f"[ok] {report.get('ok')}")
    for row in report["checks"]:
        print(f"- {row.get('kind')} {row.get('url')} :: ok={row.get('ok')} len={row.get('length')}")
    if report.get("warnings"):
        for w in report["warnings"]:
            print(f"[warn] {w}")
    if report.get("blocking_issues"):
        for b in report["blocking_issues"]:
            print(f"[blocking] {b}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

