from __future__ import annotations

import argparse
import json
import sys
import threading
import traceback
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterator, List

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUTPUT_DIR = ROOT / "output"
LOG_DIR = ROOT / "logs"
OWNER_OUTPUT = OUTPUT_DIR / "yangdo_price_calculator_owner_internal_v11.html"
PERMIT_OUTPUT = OUTPUT_DIR / "ai_license_acquisition_calculator.html"
YANGDO_PREVIEW = OUTPUT_DIR / "_tmp_yangdo_admin_preview.html"
PERMIT_PREVIEW = OUTPUT_DIR / "_tmp_permit_admin_preview.html"
ARTIFACT_DIR = OUTPUT_DIR / "playwright"
PERMIT_FAIL_SCREENSHOT = ARTIFACT_DIR / "permit_browser_smoke_failure_latest.png"
PERMIT_FAIL_HTML = ARTIFACT_DIR / "permit_browser_smoke_failure_latest.html"
DEFAULT_REPORT = LOG_DIR / "calculator_browser_smoke_latest.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _clear_artifacts(*paths: Path) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            continue


def _extract_fragment(html_text: str) -> str:
    txt = str(html_text or "").strip()
    if not txt:
        return ""
    lowered = txt.lower()
    if not lowered.startswith("<!doctype") and "<html" not in lowered:
        return txt
    soup = BeautifulSoup(txt, "html.parser")
    head_parts: List[str] = []
    for node in soup.select("head style, head script"):
        head_parts.append(str(node))
    body_parts: List[str] = []
    if soup.body:
        for node in soup.body.contents:
            body_parts.append(str(node))
    else:
        section = soup.select_one("section")
        if section:
            body_parts.append(str(section))
    return "\n".join(part for part in [*head_parts, *body_parts] if str(part).strip())


def _wrap_preview(title: str, fragment: str) -> str:
    return (
        "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{title}</title>"
        "<style>body{margin:0;padding:24px;background:#eef2f7;"
        "font-family:Pretendard,'Noto Sans KR',sans-serif;}</style>"
        f"</head><body>{fragment}</body></html>"
    )


def _build_outputs() -> Dict[str, Any]:
    import permit_diagnosis_calculator
    import all as all_module

    all_module.run_build_yangdo_calculator_page(
        output_path=str(OWNER_OUTPUT),
        publish=False,
        view_mode="owner",
    )
    permit_html = permit_diagnosis_calculator.build_html(
        catalog=permit_diagnosis_calculator._load_catalog(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH),
        rule_catalog=permit_diagnosis_calculator._load_rule_catalog(permit_diagnosis_calculator.DEFAULT_RULES_PATH),
        title="\u0041\u0049 \uc778\ud5c8\uac00 \uc0ac\uc804\uac80\ud1a0 \uc9c4\ub2e8\uae30(\uc2e0\uaddc\ub4f1\ub85d \uc804\uc6a9) | \uc11c\uc6b8\uac74\uc124\uc815\ubcf4"
    )
    PERMIT_OUTPUT.write_text(permit_html, encoding="utf-8")
    return {
        "generated_at": _now(),
        "owner_output": {
            "path": str(OWNER_OUTPUT),
            "bytes": OWNER_OUTPUT.stat().st_size,
        },
        "permit_output": {
            "path": str(PERMIT_OUTPUT),
            "bytes": PERMIT_OUTPUT.stat().st_size,
        },
    }


def _build_previews() -> Dict[str, Any]:
    owner_html = OWNER_OUTPUT.read_text(encoding="utf-8", errors="replace")
    permit_html = PERMIT_OUTPUT.read_text(encoding="utf-8", errors="replace")

    owner_fragment = _extract_fragment(owner_html)
    permit_fragment = _extract_fragment(permit_html)

    YANGDO_PREVIEW.write_text(_wrap_preview("yangdo preview", owner_fragment), encoding="utf-8")
    PERMIT_PREVIEW.write_text(_wrap_preview("permit preview", permit_fragment), encoding="utf-8")
    return {
        "generated_at": _now(),
        "yangdo_preview": {
            "path": str(YANGDO_PREVIEW),
            "bytes": YANGDO_PREVIEW.stat().st_size,
        },
        "permit_preview": {
            "path": str(PERMIT_PREVIEW),
            "bytes": PERMIT_PREVIEW.stat().st_size,
        },
    }


@contextmanager
def _preview_server(directory: Path) -> Iterator[str]:
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    class QuietThreadingHTTPServer(ThreadingHTTPServer):
        def handle_error(self, request, client_address) -> None:  # type: ignore[override]
            exc = sys.exc_info()[1]
            if isinstance(exc, ConnectionResetError):
                return
            super().handle_error(request, client_address)

    handler = partial(QuietHandler, directory=str(directory))
    server = QuietThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _setup_driver(headless: bool = True):
    from selenium import webdriver  # type: ignore
    from selenium.webdriver.chrome.options import Options  # type: ignore

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1440,2200")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    return webdriver.Chrome(options=options)


def _browser_errors(driver) -> List[str]:
    out: List[str] = []
    try:
        rows = driver.get_log("browser")
    except Exception:
        return out
    for row in rows or []:
        level = str(row.get("level") or "").upper()
        message = str(row.get("message") or "").strip()
        if level not in {"SEVERE", "ERROR"}:
            continue
        if "favicon.ico" in message:
            continue
        out.append(message)
    return out


def _save_failure_screenshot(driver, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    driver.save_screenshot(str(path))
    return str(path)


def _save_page_source(driver, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(driver.page_source or ""), encoding="utf-8", errors="replace")
    return str(path)


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


def _select_permit_industry_by_code(
    driver,
    wait,
    *,
    focus_mode: str,
    category_code: str,
    service_code: str,
    expected_name: str = "",
) -> None:
    def _selected_option_text() -> str:
        return str(
            driver.execute_script(
                """
const el = document.getElementById('industrySelect');
if (!el || el.selectedIndex < 0) return '';
const option = el.options[el.selectedIndex];
return option ? String(option.textContent || '').trim() : '';
                """
            )
            or ""
        ).strip()

    def _select_by_expected_name() -> None:
        if not expected_name:
            return
        wait.until(
            lambda d, name=expected_name: bool(
                d.execute_script(
                    """
const targetName = String(arguments[0] || '').trim();
const search = document.getElementById('industrySearchInput');
const category = document.getElementById('categorySelect');
const industry = document.getElementById('industrySelect');
if (!targetName || !category || !industry) return false;
const dispatch = (el) => {
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
};
const categoryOptions = Array.from(category.options || []).filter((option) => String(option.value || '').trim());
for (const categoryOption of categoryOptions) {
  if (String(category.value || '') !== String(categoryOption.value || '')) {
    category.value = categoryOption.value;
    dispatch(category);
  }
  const industryOptions = Array.from(industry.options || []);
  const targetOption = industryOptions.find((option) => String(option.textContent || '').includes(targetName));
  if (!targetOption) continue;
  if (search) {
    search.value = targetName;
    dispatch(search);
  }
  industry.value = String(targetOption.value || '');
  dispatch(industry);
  return true;
}
return false;
                    """
                    ,
                    name,
                )
            )
        )

    _set_value_js(driver, "industrySearchInput", "")
    _set_value_js(driver, "focusModeSelect", focus_mode)
    category_present = bool(
        driver.execute_script(
            """
const select = document.getElementById('categorySelect');
if (!select) return false;
return [...(select.options || [])].some((option) => String(option.value || '').trim() === arguments[0]);
            """,
            category_code,
        )
    )
    if category_present:
        _set_value_js(driver, "categorySelect", category_code)
        service_present = bool(
            driver.execute_script(
                """
const select = document.getElementById('industrySelect');
if (!select) return false;
return [...(select.options || [])].some((option) => String(option.value || '').trim() === arguments[0]);
                """,
                service_code,
            )
        )
        if service_present:
            _set_value_js(driver, "industrySelect", service_code)
            wait.until(
                lambda d, code=service_code: str(
                    d.execute_script(
                        "const el=document.getElementById('industrySelect'); return el ? String(el.value || '') : '';"
                    )
                    or ""
                ).strip()
                == code
            )
        else:
            _select_by_expected_name()
    else:
        _select_by_expected_name()

    if expected_name:
        wait.until(lambda d, name=expected_name: name in _selected_option_text())
        wait.until(
            lambda d, name=expected_name: name in str(
                d.execute_script(
                    "const el=document.getElementById('permitWizardSummary'); return el ? (el.innerText || '') : '';"
                )
                or ""
            )
        )


def _text(driver, element_id: str) -> str:
    try:
        return str(driver.find_element("id", element_id).text or "").strip()
    except Exception:
        return ""


def _text_fallback(driver, element_id: str) -> str:
    direct = _text(driver, element_id)
    if direct:
        return direct
    try:
        return str(
            driver.execute_script(
                """
const el = document.getElementById(arguments[0]);
if (!el) return '';
return String(el.innerText || el.textContent || '').trim();
                """,
                element_id,
            )
            or ""
        ).strip()
    except Exception:
        return ""


def _run_yangdo_smoke(page_url: str, headless: bool = True) -> Dict[str, Any]:
    from selenium.webdriver.common.by import By  # type: ignore
    from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
    from selenium.webdriver.support import expected_conditions as EC  # type: ignore

    scenarios: List[Dict[str, Any]] = [
        {
            "name": "electric_credit_transfer",
            "license": "\uC804\uAE30",
            "scale_search_mode": "sales",
            "reorg_mode": "\uD3EC\uAD04",
            "balance_usage_mode": "credit_transfer",
            "sales_mode": "\uCD5C\uADFC 3\uB144 \uC2E4\uC801 \uD569\uACC4(\uC5B5)",
            "sales3_eok": "12",
            "balance_eok": "0.8",
            "expected_selected_text": "1:1 \uCC28\uAC10",
            "expected_note_tokens": ["\uCD1D\uAC00\u00B7\uACF5\uC81C \uC815\uC0B0 \uBD84\uB9AC", "1:1 \uCC28\uAC10 \uAE30\uC900"],
        },
        {
            "name": "telecom_auto_none",
            "license": "\uC815\uBCF4\uD1B5\uC2E0",
            "scale_search_mode": "sales",
            "reorg_mode": "\uD3EC\uAD04",
            "balance_usage_mode": "auto",
            "sales_mode": "\uCD5C\uADFC 3\uB144 \uC2E4\uC801 \uD569\uACC4(\uC5B5)",
            "sales3_eok": "8",
            "balance_eok": "0.02",
            "expected_selected_text": "\uACF5\uC81C\uC870\uD569 \uC794\uC561 \uBCC4\uB3C4 \uC815\uC0B0 \uC5C6\uC74C",
            "expected_note_tokens": ["auto \uAE30\uC900", "0.03\uC5B5", "6.25%"],
            "expected_summary_text": "\uBCC4\uB3C4 \uACF5\uC81C\uC794\uC561",
        },
    ]
    result: Dict[str, Any] = {
        "page_url": page_url,
        "ok": False,
        "scenario": dict(scenarios[0]),
        "output": {},
        "subcases": [],
        "console_errors": [],
        "error": "",
        "trace": [],
    }
    driver = _setup_driver(headless=headless)
    try:
        wait = WebDriverWait(driver, 45)
        aggregate_console_errors: List[str] = []
        for case in scenarios:
            driver.get(page_url)
            wizard_exists = bool(
                driver.execute_script("return !!document.getElementById('yangdo-input-wizard') && !!document.getElementById('yangdoWizardStepTitle');")
            )
            wizard_step_count = int(
                driver.execute_script("return document.querySelectorAll('[data-yangdo-wizard-track]').length || 0;")
                or 0
            )
            wizard_initial_title = _text(driver, "yangdoWizardStepTitle")
            wizard_progress_initial = _text(driver, "yangdoWizardProgressLabel")
            wizard_progress_meta_initial = _text(driver, "yangdoWizardProgressMeta")
            wizard_next_action_initial = _text(driver, "yangdoWizardNextActionText")
            wizard_action_reason_initial = _text(driver, "yangdoWizardActionReason")
            wizard_step1_visible = bool(
                driver.execute_script("const el=document.getElementById('yangdoWizardStep1'); return !!el && el.hidden === false;")
            )
            wizard_summary_initial = str(
                driver.execute_script("const el=document.getElementById('yangdoWizardSummary'); return el ? (el.innerText || '') : '';")
                or ""
            ).strip()
            wizard_blocker_initial = _text(driver, "yangdoWizardBlocker")
            driver.execute_script(
                """
const note = document.getElementById('yangdoWizardActionReason');
if (note) note.click();
                """
            )
            wait.until(
                lambda d: str(
                    d.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                    or ""
                ).strip() == "in-license"
            )
            wizard_action_reason_initial_focus = str(
                driver.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                or ""
            ).strip()
            wizard_action_reason_initial_highlight = bool(
                driver.execute_script(
                    "const el=document.activeElement;"
                    " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                    " return !!box;"
                )
            )
            wizard_action_reason_initial_helper = str(
                driver.execute_script(
                    "const el=document.activeElement;"
                    " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                    " return box ? (box.getAttribute('data-guided-focus-copy') || '') : '';"
                )
                or ""
            ).strip()
            driver.execute_script(
                """
const btn = document.getElementById('yangdoWizardNextAction');
if (btn) btn.click();
                """
            )
            wait.until(
                lambda d: str(
                    d.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                    or ""
                ).strip() == "in-license"
            )
            wizard_next_action_initial_focus = str(
                driver.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                or ""
            ).strip()
            wizard_next_action_initial_highlight = bool(
                driver.execute_script(
                    "const el=document.activeElement;"
                    " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                    " return !!box;"
                )
            )
            driver.set_window_size(430, 1400)
            wait.until(
                lambda d: bool(
                    d.execute_script(
                        "const el=document.getElementById('yangdoWizardMobileSticky');"
                        " if (!el) return false;"
                        " const st=window.getComputedStyle(el);"
                        " return st.display !== 'none';"
                    )
                )
            )
            wizard_mobile_sticky_visible = bool(
                driver.execute_script(
                    "const el=document.getElementById('yangdoWizardMobileSticky');"
                    " if (!el) return false;"
                    " const st=window.getComputedStyle(el);"
                    " return st.display !== 'none';"
                )
            )
            wizard_mobile_sticky_label = _text(driver, "yangdoWizardMobileStickyLabel")
            wizard_mobile_sticky_action = _text(driver, "yangdoWizardMobileStickyAction")
            wizard_mobile_sticky_compact = _text(driver, "yangdoWizardMobileStickyCompact")
            wizard_mobile_sticky_reason = _text(driver, "yangdoWizardMobileStickyReason")
            driver.execute_script("if (document.activeElement && document.activeElement.blur) document.activeElement.blur();")
            driver.execute_script(
                """
const btn = document.getElementById('yangdoWizardMobileSticky');
if (btn) btn.click();
                """
            )
            wait.until(
                lambda d: str(
                    d.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                    or ""
                ).strip() == "in-license"
            )
            wizard_mobile_sticky_focus = str(
                driver.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                or ""
            ).strip()
            wizard_mobile_sticky_highlight = bool(
                driver.execute_script(
                    "const el=document.activeElement;"
                    " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                    " return !!box;"
                )
            )
            wizard_mobile_sticky_helper = str(
                driver.execute_script(
                    "const el=document.activeElement;"
                    " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                    " return box ? (box.getAttribute('data-guided-focus-copy') || '') : '';"
                )
                or ""
            ).strip()
            wizard_mobile_sticky_level = str(
                driver.execute_script(
                    "const el=document.activeElement;"
                    " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                    " return box ? (box.getAttribute('data-guided-focus-level') || '') : '';"
                )
                or ""
            ).strip()
            driver.set_window_size(1440, 2200)
            initial_share_hidden = bool(
                driver.execute_script(
                    "const el=document.getElementById('result-share-actions');"
                    " if (!el) return false;"
                    " const st=window.getComputedStyle(el);"
                    " return st.display === 'none';"
                )
            )
            _set_value_js(driver, "in-license", str(case.get("license") or ""))
            wait.until(
                lambda d: bool(
                    d.execute_script(
                        "const btn=document.querySelector('[data-yangdo-wizard-next=\"0\"]');"
                        " return !!btn && btn.disabled === false;"
                    )
                )
            )
            auto_balance_seed = str(
                driver.execute_script("const el=document.getElementById('in-balance'); return el ? (el.value || '') : '';")
                or ""
            ).strip()
            auto_capital_seed = str(
                driver.execute_script("const el=document.getElementById('in-capital'); return el ? (el.value || '') : '';")
                or ""
            ).strip()
            wizard_summary_after_license = str(
                driver.execute_script("const el=document.getElementById('yangdoWizardSummary'); return el ? (el.innerText || '') : '';")
                or ""
            ).strip()
            wizard_blocker_after_license = _text(driver, "yangdoWizardBlocker")
            wizard_next_action_after_license = _text(driver, "yangdoWizardNextActionText")
            wizard_action_reason_after_license = _text(driver, "yangdoWizardActionReason")
            driver.execute_script(
                """
const btn = document.getElementById('yangdoWizardNextAction');
if (btn) btn.click();
                """
            )
            wait.until(lambda d: "검색 기준 입력" in _text(d, "yangdoWizardStepTitle"))
            wait.until(
                lambda d: str(
                    d.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                    or ""
                ).strip() in {"in-specialty", "in-y23", "in-sales3-total", "in-sales5-total"}
            )
            wizard_next_action_after_license_focus = str(
                driver.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                or ""
            ).strip()
            wizard_next_action_after_license_highlight = bool(
                driver.execute_script(
                    "const el=document.activeElement;"
                    " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                    " return !!box;"
                )
            )
            driver.execute_script(
                """
const btn = document.querySelector('[data-yangdo-wizard-next="0"]');
if (btn && !btn.disabled) btn.click();
                """
            )
            wait.until(lambda d: "검색 기준 입력" in _text(d, "yangdoWizardStepTitle"))
            wizard_step2_title = _text(driver, "yangdoWizardStepTitle")
            wizard_progress_step2 = _text(driver, "yangdoWizardProgressLabel")
            driver.execute_script(
                """
const btn = document.querySelector('[data-scale-mode="sales"]');
if (btn) {
  btn.click();
}
                """
            )
            sales_panel_visible = bool(
                driver.execute_script(
                    "const panel=document.getElementById('sales-search-panel');"
                    " const specialty=document.getElementById('in-specialty');"
                    " if (!panel || !specialty) return false;"
                    " return !panel.classList.contains('is-hidden') && specialty.disabled === true;"
                )
            )
            _set_value_js(driver, "in-sales-input-mode", str(case.get("sales_mode") or ""))
            _set_value_js(driver, "in-sales3-total", str(case.get("sales3_eok") or ""))
            wizard_summary_after_scale = str(
                driver.execute_script("const el=document.getElementById('yangdoWizardSummary'); return el ? (el.innerText || '') : '';")
                or ""
            ).strip()
            wait.until(
                lambda d: bool(
                    d.execute_script(
                        "const btn=document.querySelector('[data-yangdo-wizard-next=\"1\"]');"
                        " return !!btn && btn.disabled === false;"
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
            wizard_step3_title = _text(driver, "yangdoWizardStepTitle")
            critical_hint_text = _text(driver, "yangdoCriticalHint")
            wizard_blocker_step3 = _text(driver, "yangdoWizardBlocker")
            if not auto_capital_seed:
                _set_value_js(driver, "in-capital", "1.5")
            _set_value_js(driver, "in-balance", str(case.get("balance_eok") or ""))
            step3_next_label = str(
                driver.execute_script(
                    "const btn=document.querySelector('[data-yangdo-wizard-next=\"2\"]'); return btn ? String(btn.textContent || '') : '';"
                )
                or ""
            ).strip()
            wait.until(
                lambda d: bool(
                    d.execute_script(
                        "const btn=document.querySelector('[data-yangdo-wizard-next=\"2\"]');"
                        " return !!btn && btn.disabled === false;"
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
            wizard_step4_title = _text(driver, "yangdoWizardStepTitle")
            wizard_progress_step4 = _text(driver, "yangdoWizardProgressLabel")
            structure_hint_text = _text(driver, "yangdoStructureHint")
            wizard_next_action_step4 = _text(driver, "yangdoWizardNextActionText")
            driver.execute_script(
                """
const btn = document.getElementById('yangdoWizardNextAction');
if (btn) btn.click();
                """
            )
            wait.until(
                lambda d: bool(
                    d.execute_script(
                        "const el=document.activeElement;"
                        " return !!el && String(el.getAttribute('data-reorg-choice') || '') === '포괄';"
                    )
                )
            )
            wizard_next_action_step4_focus = str(
                driver.execute_script("const el=document.activeElement; return el ? (el.getAttribute('data-reorg-choice') || el.id || '') : '';")
                or ""
            ).strip()
            step4_next_label = str(
                driver.execute_script(
                    "const btn=document.querySelector('[data-yangdo-wizard-next=\"3\"]'); return btn ? String(btn.textContent || '') : '';"
                )
                or ""
            ).strip()
            step4_alert_active = bool(
                driver.execute_script(
                    "const chip=document.querySelector('[data-yangdo-wizard-track=\"3\"]');"
                    "const step=document.getElementById('yangdoWizardStep4');"
                    "return !!chip && chip.classList.contains('is-alert') && !!step && step.classList.contains('is-alert');"
                )
            )
            reorg_choice_labels = list(
                driver.execute_script(
                    """
return Array.from(document.querySelectorAll('[data-reorg-choice]'))
  .map((el) => String(el.innerText || '').replace(/\\s+/g, ' ').trim());
                    """
                )
                or []
            )
            driver.execute_script(
                """
const wanted = arguments[0];
const btn = Array.from(document.querySelectorAll('[data-reorg-choice]'))
  .find((el) => String(el.getAttribute('data-reorg-choice') || '').trim() === wanted);
if (btn) btn.click();
                """,
                str(case.get("reorg_mode") or ""),
            )
            wait.until(
                lambda d, expected=str(case.get("reorg_mode") or ""): str(
                    d.execute_script("const el=document.getElementById('in-reorg-mode'); return el ? String(el.value || '') : '';")
                    or ""
                ).strip() == expected
            )
            reorg_choice_active = bool(
                driver.execute_script(
                    """
const wanted = arguments[0];
const btn = Array.from(document.querySelectorAll('[data-reorg-choice]'))
  .find((el) => String(el.getAttribute('data-reorg-choice') || '').trim() === wanted);
return !!btn && btn.classList.contains('is-active');
                    """,
                    str(case.get("reorg_mode") or ""),
                )
            )
            reorg_compare_texts = list(
                driver.execute_script(
                    """
return Array.from(document.querySelectorAll('[data-reorg-compare]'))
  .map((el) => String(el.innerText || '').replace(/\\s+/g, ' ').trim());
                    """
                )
                or []
            )
            reorg_compare_active = bool(
                driver.execute_script(
                    """
const wanted = arguments[0];
const card = Array.from(document.querySelectorAll('[data-reorg-compare]'))
  .find((el) => String(el.getAttribute('data-reorg-compare') || '').trim() === wanted);
return !!card && card.classList.contains('is-active');
                    """,
                    str(case.get("reorg_mode") or ""),
                )
            )
            reorg_compare_note = _text(driver, "reorg-compare-note")
            _set_value_js(driver, "in-balance-usage-mode", str(case.get("balance_usage_mode") or ""))
            wait.until(
                lambda d: bool(
                    d.execute_script(
                        "const btn=document.querySelector('[data-yangdo-wizard-next=\"3\"]');"
                        " return !!btn && btn.disabled === false;"
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
            wizard_step5_title = _text(driver, "yangdoWizardStepTitle")
            wizard_progress_step5 = _text(driver, "yangdoWizardProgressLabel")
            company_hint_text = _text(driver, "yangdoCompanyHint")
            wizard_optional_state = "선택" in wizard_step5_title

            driver.execute_script(
                """
const btn = document.querySelector('[data-yangdo-wizard-next="4"]');
if (btn && !btn.disabled) btn.click();
                """
            )
            wait.until(
                lambda d: (
                    _text(d, "out-confidence") not in {"", "-"}
                    or "AI \uC0B0\uC815 \uC644\uB8CC" in _text(d, "risk-note")
                    or _text(d, "out-center") not in {"", "-"}
                )
            )

            center_text = _text(driver, "out-center")
            range_text = _text(driver, "out-range")
            cash_due_text = _text(driver, "out-cash-due")
            realizable_balance_text = _text(driver, "out-realizable-balance")
            confidence_text = _text(driver, "out-confidence")
            neighbors_text = _text(driver, "out-neighbors")
            source_tier_text = _text(driver, "out-source-tier")
            risk_note = _text(driver, "risk-note")
            result_reason_chips_text = str(
                driver.execute_script("const el=document.getElementById('result-reason-chips'); return el ? (el.innerText || '') : '';")
                or ""
            ).strip()
            settlement_summary = _text(driver, "settlement-summary")
            settlement_notes = _text(driver, "settlement-notes")
            settlement_scenario_count = int(
                driver.execute_script("return document.querySelectorAll('#settlement-scenarios .settlement-scenario').length || 0;")
                or 0
            )
            settlement_scenarios_text = str(
                driver.execute_script("const el=document.getElementById('settlement-scenarios'); return el ? (el.innerText || '') : '';")
                or ""
            ).strip()
            result_brief_text = str(
                driver.execute_script("const el=document.getElementById('result-brief'); return el ? (el.value || '') : '';")
                or ""
            ).strip()
            recommended_listings_text = str(
                driver.execute_script("const el=document.getElementById('recommended-listings'); return el ? (el.innerText || '') : '';")
                or ""
            ).strip()
            selected_scenario_text = str(
                driver.execute_script(
                    "const el=document.querySelector('#settlement-scenarios .settlement-scenario.is-selected');"
                    " return el ? (el.innerText || '') : '';"
                )
                or ""
            ).strip()
            publication_chip_ok = any(
                token in result_reason_chips_text
                for token in (
                    "기준가 바로 보기",
                    "편차가 커 범위만 안내",
                    "범위 먼저 안내",
                    "면허부터 확인",
                    "자세히 확인 후 안내",
                )
            )
            settlement_chip_ok = "정산" in result_reason_chips_text
            share_visible_after_result = bool(
                driver.execute_script(
                    "const el=document.getElementById('result-share-actions');"
                    " if (!el) return false;"
                    " const st=window.getComputedStyle(el);"
                    " return st.display !== 'none';"
                )
            )
            synthetic_followup_output = dict(
                driver.execute_script(
                    """
const syntheticTarget = {
  scale_search_mode: "sales",
  requested_scale_search_mode: "sales",
  split_optional_pricing: false,
  balance_excluded: false,
};
const hooks = window.__yangdoQaHooks || {};
const available = typeof hooks.renderRecommendedListings === "function" && typeof hooks.renderActionSteps === "function";
if (available) {
  hooks.renderRecommendedListings([], {
    target: syntheticTarget,
    publicationMode: "consult_only",
    priceSourceTier: "표본 적음",
  });
  hooks.renderActionSteps({ target: syntheticTarget, publicationMode: "consult_only", priceSourceTier: "표본 적음" });
}
const primary = document.getElementById("recommend-panel-followup-action");
const secondary = document.getElementById("recommend-panel-followup-secondary-action");
const note = document.getElementById("recommend-panel-followup-note");
const text = document.getElementById("recommend-panel-followup-text");
const steps = document.getElementById("recommend-actions");
return {
  available,
  text: text ? String(text.innerText || "").trim() : "",
  note: note ? String(note.innerText || "").trim() : "",
  primary_text: primary ? String(primary.innerText || "").trim() : "",
  secondary_text: secondary ? String(secondary.innerText || "").trim() : "",
  primary_kind: primary ? String(primary.dataset.focusAction || "").trim() : "",
  secondary_kind: secondary ? String(secondary.dataset.focusAction || "").trim() : "",
  primary_visible: !!primary && window.getComputedStyle(primary).display !== "none",
  secondary_visible: !!secondary && window.getComputedStyle(secondary).display !== "none",
  steps_text: steps ? String(steps.innerText || "").replace(/\\s+/g, " ").trim() : "",
};
                    """
                )
                or {}
            )
            driver.execute_script(
                """
const hooks = window.__yangdoQaHooks || {};
if (typeof hooks.focusRecommendBalanceRefinement === 'function') {
  hooks.focusRecommendBalanceRefinement();
}
                """
            )
            wait.until(
                lambda d: "핵심 가격 영향 입력" in _text(d, "yangdoWizardStepTitle")
            )
            synthetic_primary_step_title = _text(driver, "yangdoWizardStepTitle")
            driver.execute_script(
                """
const hooks = window.__yangdoQaHooks || {};
if (typeof hooks.renderRecommendedListings === 'function') hooks.renderRecommendedListings([], {
  target: {
    scale_search_mode: "sales",
    requested_scale_search_mode: "sales",
    split_optional_pricing: false,
    balance_excluded: false,
  },
  publicationMode: "consult_only",
  priceSourceTier: "표본 적음",
});
if (typeof hooks.focusRecommendCapitalRefinement === 'function') {
  hooks.focusRecommendCapitalRefinement();
}
                """
            )
            wait.until(
                lambda d: "핵심 가격 영향 입력" in _text(d, "yangdoWizardStepTitle")
            )
            synthetic_secondary_step_title = _text(driver, "yangdoWizardStepTitle")
            driver.get(page_url)
            wait.until(
                lambda d: bool(
                    d.execute_script(
                        "const el=document.getElementById('draft-restore-note');"
                        " if (!el) return false;"
                        " const st=window.getComputedStyle(el);"
                        " return st.display !== 'none';"
                    )
                )
            )
            draft_restore_note_text = _text(driver, "draft-restore-note-text")
            draft_resume_title = _text(driver, "yangdoWizardStepTitle")
            draft_resume_summary = str(
                driver.execute_script("const el=document.getElementById('yangdoWizardSummary'); return el ? (el.innerText || '') : '';")
                or ""
            ).strip()
            driver.execute_script(
                """
const btn = document.getElementById('draft-restore-action');
if (btn) btn.click();
                """
            )
            wait.until(lambda d: "STEP 1" in _text(d, "yangdoWizardStepTitle"))
            draft_clear_step1 = "STEP 1" in _text(driver, "yangdoWizardStepTitle")
            draft_restore_hidden_after_clear = bool(
                driver.execute_script(
                    "const el=document.getElementById('draft-restore-note');"
                    " if (!el) return false;"
                    " const st=window.getComputedStyle(el);"
                    " return st.display === 'none';"
                )
            )
            console_errors = _browser_errors(driver)
            aggregate_console_errors.extend(console_errors)
            balance_seed_or_not_needed = (
                bool(auto_balance_seed)
                or settlement_scenario_count >= 2
                or "\uBCC4\uB3C4" in settlement_summary
                or "\uBCC4\uB3C4" in settlement_notes
            )
            has_credit_transfer_detail = "1:1 \uCC28\uAC10" in settlement_scenarios_text
            has_separate_settlement_detail = (
                "\uBCC4\uB3C4 \uC815\uC0B0 \uC5C6\uC74C" in settlement_scenarios_text
                or "\uBCC4\uB3C4\uC815\uC0B0 \uC5C6\uC74C" in settlement_scenarios_text
            )
            settlement_detail_ok = (
                (settlement_scenario_count >= 2 and has_credit_transfer_detail and has_separate_settlement_detail)
                or (bool(settlement_summary) and bool(settlement_notes))
            )
            publication_hidden = center_text in {"\uC0C1\uB2F4 \uAC80\uC99D \uD6C4 \uC548\uB0B4"} or range_text in {"\uC0C1\uB2F4 \uAC80\uC99D \uD544\uC694"}

            case_output = {
                "wizard_exists": wizard_exists,
                "wizard_step_count": wizard_step_count,
                "wizard_initial_title": wizard_initial_title,
                "wizard_progress_initial": wizard_progress_initial,
                "wizard_progress_meta_initial": wizard_progress_meta_initial,
                "wizard_next_action_initial": wizard_next_action_initial,
                "wizard_action_reason_initial": wizard_action_reason_initial,
                "wizard_action_reason_initial_focus": wizard_action_reason_initial_focus,
                "wizard_action_reason_initial_highlight": wizard_action_reason_initial_highlight,
                "wizard_action_reason_initial_helper": wizard_action_reason_initial_helper,
                "wizard_next_action_initial_focus": wizard_next_action_initial_focus,
                "wizard_next_action_initial_highlight": wizard_next_action_initial_highlight,
                "wizard_mobile_sticky_visible": wizard_mobile_sticky_visible,
                "wizard_mobile_sticky_label": wizard_mobile_sticky_label,
                "wizard_mobile_sticky_action": wizard_mobile_sticky_action,
                "wizard_mobile_sticky_compact": wizard_mobile_sticky_compact,
                "wizard_mobile_sticky_reason": wizard_mobile_sticky_reason,
                "wizard_mobile_sticky_focus": wizard_mobile_sticky_focus,
                "wizard_mobile_sticky_highlight": wizard_mobile_sticky_highlight,
                "wizard_mobile_sticky_helper": wizard_mobile_sticky_helper,
                "wizard_mobile_sticky_level": wizard_mobile_sticky_level,
                "wizard_step1_visible": wizard_step1_visible,
                "wizard_summary_initial": wizard_summary_initial,
                "wizard_blocker_initial": wizard_blocker_initial,
                "wizard_summary_after_license": wizard_summary_after_license,
                "wizard_blocker_after_license": wizard_blocker_after_license,
                "wizard_next_action_after_license": wizard_next_action_after_license,
                "wizard_action_reason_after_license": wizard_action_reason_after_license,
                "wizard_next_action_after_license_focus": wizard_next_action_after_license_focus,
                "wizard_next_action_after_license_highlight": wizard_next_action_after_license_highlight,
                "wizard_summary_after_scale": wizard_summary_after_scale,
                "wizard_step2_title": wizard_step2_title,
                "wizard_progress_step2": wizard_progress_step2,
                "wizard_step3_title": wizard_step3_title,
                "critical_hint_text": critical_hint_text,
                "wizard_blocker_step3": wizard_blocker_step3,
                "step3_next_label": step3_next_label,
                "wizard_step4_title": wizard_step4_title,
                "wizard_progress_step4": wizard_progress_step4,
                "structure_hint_text": structure_hint_text,
                "wizard_next_action_step4": wizard_next_action_step4,
                "wizard_next_action_step4_focus": wizard_next_action_step4_focus,
                "step4_next_label": step4_next_label,
                "step4_alert_active": step4_alert_active,
                "reorg_choice_labels": reorg_choice_labels,
                "reorg_choice_active": reorg_choice_active,
                "reorg_compare_texts": reorg_compare_texts,
                "reorg_compare_active": reorg_compare_active,
                "reorg_compare_note": reorg_compare_note,
                "wizard_step5_title": wizard_step5_title,
                "wizard_progress_step5": wizard_progress_step5,
                "company_hint_text": company_hint_text,
                "wizard_optional_state": wizard_optional_state,
                "initial_share_hidden": initial_share_hidden,
                "auto_balance_seed": auto_balance_seed,
                "auto_capital_seed": auto_capital_seed,
                "balance_seed_or_not_needed": balance_seed_or_not_needed,
                "sales_panel_visible": sales_panel_visible,
                "share_visible_after_result": share_visible_after_result,
                "center_text": center_text,
                "range_text": range_text,
                "cash_due_text": cash_due_text,
                "realizable_balance_text": realizable_balance_text,
                "confidence_text": confidence_text,
                "neighbors_text": neighbors_text,
                "source_tier_text": source_tier_text,
                "risk_note": risk_note,
                "result_reason_chips_text": result_reason_chips_text,
                "settlement_summary": settlement_summary,
                "settlement_notes": settlement_notes,
                "settlement_scenario_count": settlement_scenario_count,
                "settlement_scenarios_text": settlement_scenarios_text,
                "result_brief_text": result_brief_text,
                "recommended_listings_text": recommended_listings_text,
                "selected_scenario_text": selected_scenario_text,
                "publication_hidden": publication_hidden,
                "synthetic_followup_available": bool(synthetic_followup_output.get("available")),
                "synthetic_followup_text": str(synthetic_followup_output.get("text") or "").strip(),
                "synthetic_followup_note": str(synthetic_followup_output.get("note") or "").strip(),
                "synthetic_followup_primary_text": str(synthetic_followup_output.get("primary_text") or "").strip(),
                "synthetic_followup_secondary_text": str(synthetic_followup_output.get("secondary_text") or "").strip(),
                "synthetic_followup_primary_kind": str(synthetic_followup_output.get("primary_kind") or "").strip(),
                "synthetic_followup_secondary_kind": str(synthetic_followup_output.get("secondary_kind") or "").strip(),
                "synthetic_followup_primary_visible": bool(synthetic_followup_output.get("primary_visible")),
                "synthetic_followup_secondary_visible": bool(synthetic_followup_output.get("secondary_visible")),
                "synthetic_followup_steps_text": str(synthetic_followup_output.get("steps_text") or "").strip(),
                "synthetic_primary_step_title": synthetic_primary_step_title,
                "synthetic_secondary_step_title": synthetic_secondary_step_title,
                "draft_restore_note_text": draft_restore_note_text,
                "draft_resume_title": draft_resume_title,
                "draft_resume_summary": draft_resume_summary,
                "draft_clear_step1": draft_clear_step1,
                "draft_restore_hidden_after_clear": draft_restore_hidden_after_clear,
            }
            common_ok = (
                wizard_exists
                and wizard_step_count >= 5
                and "STEP 1" in wizard_initial_title
                and wizard_progress_initial == "현재 1/5 단계"
                and "업종부터 입력하면 자동 제안이 시작됩니다." in wizard_progress_meta_initial
                and wizard_next_action_initial == "면허/업종부터 선택하세요."
                and "통상 자본금" in wizard_action_reason_initial
                and wizard_action_reason_initial_focus == "in-license"
                and wizard_action_reason_initial_highlight
                and "자동 기준" in wizard_action_reason_initial_helper
                and wizard_next_action_initial_focus == "in-license"
                and wizard_next_action_initial_highlight
                and wizard_mobile_sticky_visible
                and wizard_mobile_sticky_label == "현재 1/5 단계"
                and "면허/업종" in wizard_mobile_sticky_action
                and wizard_mobile_sticky_compact == "업종 선택 후 자동 기준 시작"
                and wizard_mobile_sticky_focus == "in-license"
                and wizard_mobile_sticky_highlight
                and "지금은 업종만" in wizard_mobile_sticky_helper
                and wizard_mobile_sticky_level == "sticky"
                and wizard_step1_visible
                and bool(wizard_summary_initial)
                and "핵심 입력 준비 전" in wizard_summary_initial
                and "업종" in wizard_blocker_initial
                and str(case.get("license") or "") in wizard_summary_after_license
                and "검색 기준 먼저 입력" in wizard_summary_after_license
                and "시평 또는 실적" in wizard_blocker_after_license
                and wizard_next_action_after_license == "시평 또는 실적 중 한 축을 먼저 입력하세요."
                and "한 축만 입력" in wizard_action_reason_after_license
                and wizard_next_action_after_license_focus in {"in-specialty", "in-y23", "in-sales3-total", "in-sales5-total"}
                and wizard_next_action_after_license_highlight
                and "실적" in wizard_summary_after_scale
                and "검색 기준 입력" in wizard_step2_title
                and wizard_progress_step2 == "현재 2/5 단계"
                and "핵심 가격 영향 입력" in wizard_step3_title
                and bool(critical_hint_text)
                and (
                    "자본금" in wizard_blocker_step3
                    or "공제조합" in wizard_blocker_step3
                    or "포괄" in wizard_blocker_step3
                    or "분할/합병" in wizard_blocker_step3
                )
                and "구조·정산 정보" in wizard_step4_title
                and wizard_progress_step4 == "현재 4/5 단계"
                and "필수" in step3_next_label
                and bool(structure_hint_text)
                and ("구조" in structure_hint_text or "정산" in structure_hint_text)
                and wizard_next_action_step4 == "포괄 또는 분할/합병 중 구조를 선택하세요."
                and wizard_next_action_step4_focus == "포괄"
                and step4_next_label == "양도 구조 먼저 선택"
                and step4_alert_active
                and len(reorg_choice_labels) >= 2
                and any("포괄" in label for label in reorg_choice_labels)
                and any("분할/합병" in label for label in reorg_choice_labels)
                and reorg_choice_active
                and len(reorg_compare_texts) >= 2
                and any(("시평" in text and "재무" in text) for text in reorg_compare_texts)
                and any(("실적" in text and "자본금" in text) for text in reorg_compare_texts)
                and reorg_compare_active
                and bool(reorg_compare_note)
                and ("구조" in reorg_compare_note or "전기" in reorg_compare_note or "정보통신" in reorg_compare_note or "소방" in reorg_compare_note)
                and "재무·회사 선택 정보" in wizard_step5_title
                and wizard_progress_step5 == "현재 5/5 단계"
                and bool(company_hint_text)
                and ("재무" in company_hint_text or "회사" in company_hint_text)
                and wizard_optional_state
                and initial_share_hidden
                and balance_seed_or_not_needed
                and sales_panel_visible
                and share_visible_after_result
                and bool(result_brief_text)
                and str(case.get("license") or "") in result_brief_text
                and "가격" not in recommended_listings_text
                and "억" not in recommended_listings_text
                and confidence_text not in {"", "-"}
                and bool(neighbors_text)
                and realizable_balance_text not in {"", "-"}
                and bool(settlement_summary)
                and publication_chip_ok
                and settlement_chip_ok
                and settlement_detail_ok
                and bool(synthetic_followup_output.get("available"))
                and "공제조합 잔액" in str(synthetic_followup_output.get("text") or "")
                and "1순위는 공제조합 잔액, 2순위는 자본금입니다." in str(synthetic_followup_output.get("note") or "")
                and str(synthetic_followup_output.get("primary_text") or "").startswith("1순위 · 공제조합 잔액 보강")
                and str(synthetic_followup_output.get("secondary_text") or "").startswith("2순위 · 자본금 보강")
                and str(synthetic_followup_output.get("primary_kind") or "") == "balance"
                and str(synthetic_followup_output.get("secondary_kind") or "") == "capital"
                and bool(synthetic_followup_output.get("primary_visible"))
                and bool(synthetic_followup_output.get("secondary_visible"))
                and "추천 후보" in str(synthetic_followup_output.get("steps_text") or "")
                and "공제조합 잔액" in str(synthetic_followup_output.get("steps_text") or "")
                and "핵심 가격 영향 입력" in synthetic_primary_step_title
                and "핵심 가격 영향 입력" in synthetic_secondary_step_title
                and bool(draft_restore_note_text)
                and (
                    "핵심 가격 영향 입력" in draft_resume_title
                    or "재무·회사 선택 정보" in draft_resume_title
                    or "구조·정산 정보" in draft_resume_title
                )
                and str(case.get("license") or "") in draft_resume_summary
                and draft_clear_step1
                and draft_restore_hidden_after_clear
                and (
                    center_text not in {"", "-"}
                    or range_text not in {"", "-"}
                    or publication_hidden
                    or "\uACF5\uAC1C \uBC29\uC2DD" in risk_note
                )
                and not console_errors
                and "\uACC4\uC0B0 \uC911 \uC608\uC678\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4" not in risk_note
            )
            expected_selected_text = str(case.get("expected_selected_text") or "").strip()
            expected_note_tokens = [str(x).strip() for x in list(case.get("expected_note_tokens") or []) if str(x).strip()]
            expected_summary_text = str(case.get("expected_summary_text") or "").strip()
            expect_optional_summary = str(case.get("balance_usage_mode") or "").strip() not in {"", "auto"}
            scenario_ok = True
            if expected_selected_text:
                scenario_ok = scenario_ok and expected_selected_text in selected_scenario_text
            if expected_summary_text:
                scenario_ok = scenario_ok and expected_summary_text in settlement_summary
            if expected_note_tokens:
                scenario_ok = scenario_ok and all(token in settlement_notes for token in expected_note_tokens)
            if expect_optional_summary:
                scenario_ok = scenario_ok and "선택" in result_brief_text

            case_result = {
                "name": str(case.get("name") or ""),
                "scenario": dict(case),
                "output": case_output,
                "console_errors": console_errors,
                "ok": bool(common_ok and scenario_ok),
                "error": "",
            }
            result["subcases"].append(case_result)

        if result["subcases"]:
            result["scenario"] = dict((result["subcases"][0] or {}).get("scenario") or {})
            result["output"] = dict((result["subcases"][0] or {}).get("output") or {})
        deduped_console_errors: List[str] = []
        seen_console_errors = set()
        for item in aggregate_console_errors:
            text = str(item or "").strip()
            if not text or text in seen_console_errors:
                continue
            seen_console_errors.add(text)
            deduped_console_errors.append(text)
        result["console_errors"] = deduped_console_errors
        result["ok"] = bool(result["subcases"]) and all(bool((row or {}).get("ok")) for row in result["subcases"])
        return result
    except Exception as exc:  # noqa: BLE001
        result["console_errors"] = _browser_errors(driver)
        error_text = str(exc).strip()
        result["error"] = f"{type(exc).__name__}: {error_text}" if error_text else type(exc).__name__
        result["trace"].append(traceback.format_exc())
        return result
    finally:
        driver.quit()


def _run_permit_smoke(page_url: str, headless: bool = True) -> Dict[str, Any]:
    from selenium.webdriver.common.by import By  # type: ignore
    from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
    from selenium.webdriver.support import expected_conditions as EC  # type: ignore

    result: Dict[str, Any] = {
        "page_url": page_url,
        "ok": False,
        "scenario": {
            "license_type": "\ud1a0\ubaa9\uac74\ucd95\uacf5\uc0ac\uc5c5(\uc885\ud569)",
            "corp_state": "new",
            "region_text": "\uc11c\uc6b8 \uac15\ub0a8\uad6c \uc0bc\uc131\ub3d9",
        },
        "output": {},
        "console_errors": [],
        "error": "",
    }
    driver = _setup_driver(headless=headless)
    try:
        wait = WebDriverWait(driver, 45)
        driver.get(page_url)
        _set_value_js(driver, "acq-license-type", "\ud1a0\ubaa9\uac74\ucd95\uacf5\uc0ac\uc5c5(\uc885\ud569)")
        _set_value_js(driver, "acq-corp-state", "new")
        _set_value_js(driver, "acq-region-text", "\uc11c\uc6b8 \uac15\ub0a8\uad6c \uc0bc\uc131\ub3d9")

        wait.until(EC.element_to_be_clickable((By.ID, "acq-btn-calc"))).click()
        wait.until(lambda d: _text(d, "acq-out-center") not in {"", "-"})

        center_text = _text(driver, "acq-out-center")
        range_text = _text(driver, "acq-out-range")
        ready_text = _text(driver, "acq-out-ready")
        confidence_text = _text(driver, "acq-out-confidence")
        mid_settlement_text = _text(driver, "acq-mid-settlement")
        breakdown_text = _text(driver, "acq-breakdown")
        console_errors = _browser_errors(driver)

        result["output"] = {
            "center_text": center_text,
            "range_text": range_text,
            "ready_text": ready_text,
            "confidence_text": confidence_text,
            "mid_settlement_text": mid_settlement_text,
            "breakdown_text": breakdown_text,
        }
        result["console_errors"] = console_errors
        result["ok"] = (
            center_text not in {"", "-"}
            and range_text not in {"", "-"}
            and ready_text not in {"", "-"}
            and confidence_text not in {"", "-"}
            and bool(mid_settlement_text or breakdown_text)
            and not console_errors
        )
        return result
    except Exception as exc:  # noqa: BLE001
        result["console_errors"] = _browser_errors(driver)
        result["error"] = str(exc)
        return result
    finally:
        driver.quit()


def _run_permit_precheck_smoke(page_url: str, headless: bool = True) -> Dict[str, Any]:
    from selenium.webdriver.support.ui import WebDriverWait  # type: ignore

    result: Dict[str, Any] = {
        "page_url": page_url,
        "ok": False,
        "scenario": {
            "focus_mode": "focus_only",
            "industry_search": "전기공사업",
            "industry_value_hint": "exact-industry-search",
        },
        "output": {},
        "console_errors": [],
        "error": "",
        "trace": [],
        "artifacts": {},
    }
    driver = _setup_driver(headless=headless)
    try:
        _clear_artifacts(PERMIT_FAIL_SCREENSHOT, PERMIT_FAIL_HTML)
        def mark(step: str) -> None:
            result["trace"].append(step)

        wait = WebDriverWait(driver, 45)
        driver.get(page_url)
        mark("page_loaded")
        wizard_exists = bool(
            driver.execute_script("return !!document.getElementById('permitInputWizard') && !!document.getElementById('permitWizardStepTitle');")
        )
        wizard_step_count = int(
            driver.execute_script("return document.querySelectorAll('[data-permit-wizard-track]').length || 0;")
            or 0
        )
        wizard_initial_title = _text(driver, "permitWizardStepTitle")
        wizard_progress_initial = _text(driver, "permitWizardProgressLabel")
        wizard_progress_meta_initial = _text(driver, "permitWizardProgressMeta")
        wizard_next_action_initial = _text(driver, "permitWizardNextActionText")
        wizard_step1_visible = bool(
            driver.execute_script("const el=document.getElementById('permitWizardStep1'); return !!el && el.hidden === false;")
        )
        wizard_summary_initial = str(
            driver.execute_script("const el=document.getElementById('permitWizardSummary'); return el ? (el.innerText || '') : '';")
            or ""
        ).strip()
        wizard_blocker_initial = _text(driver, "permitWizardBlocker")
        driver.execute_script(
            """
const btn = document.getElementById('permitWizardNextAction');
if (btn) btn.click();
            """
        )
        wait.until(
            lambda d: str(
                d.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                or ""
            ).strip() == "industrySearchInput"
        )
        wizard_next_action_initial_focus = str(
            driver.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
            or ""
        ).strip()
        wizard_next_action_initial_highlight = bool(
            driver.execute_script(
                "const el=document.activeElement;"
                " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                " return !!box;"
            )
        )
        mark("initial_state_captured")

        initial_actions_hidden = bool(
            driver.execute_script(
                "const el=document.getElementById('resultActionButtons');"
                " if (!el) return false;"
                " const st=window.getComputedStyle(el);"
                " return st.display === 'none';"
            )
        )

        driver.execute_script(
            """
const btn = document.querySelector('[data-focus-mode="focus_only"]');
if (btn) btn.click();
            """
        )
        mode_pill_sync = bool(
            driver.execute_script(
                "const btn=document.querySelector('[data-focus-mode=\"focus_only\"]');"
                " const select=document.getElementById('focusModeSelect');"
                " return !!btn && !!select && btn.classList.contains('is-active') && select.value === 'focus_only';"
            )
        )
        _set_value_js(driver, "industrySearchInput", "\uC804\uAE30\uACF5\uC0AC\uC5C5")

        first_focus_option_text = str(
            driver.execute_script(
                """
const el = document.getElementById('focusQuickSelect');
if (!el) return '';
const rows = Array.from(el.options || []);
const option = rows.find((row) => String(row.value || '').trim());
if (!option) return '';
return String(option.textContent || '').trim();
                """
            )
            or ""
        ).strip()
        search_seed = "\uC804\uAE30\uACF5\uC0AC\uC5C5"
        wait.until(
            lambda d: search_seed in str(
                d.execute_script(
                    """
const el = document.getElementById('industrySelect');
if (!el) return '';
const option = el.options && el.selectedIndex >= 0 ? el.options[el.selectedIndex] : null;
return option ? String(option.textContent || '').trim() : '';
                    """
                )
                or ""
            )
        )
        exact_search_top_option_text = str(
            driver.execute_script(
                """
const el = document.getElementById('focusQuickSelect');
if (!el) return '';
const rows = Array.from(el.options || []);
const option = rows.find((row) => String(row.value || '').trim());
if (!option) return '';
return String(option.textContent || '').trim();
                """
            )
            or ""
        ).strip()
        focus_hint = _text(driver, "focusHint")

        wait.until(lambda d: _text(d, "requiredCapital") not in {"", "-"})
        wizard_step3_title = _text(driver, "permitWizardStepTitle")
        wizard_progress_step3 = _text(driver, "permitWizardProgressLabel")
        mark("search_auto_selected")
        wait.until(
            lambda d: bool(
                d.execute_script(
                    """
const quick = document.getElementById('focusQuickSelect');
const select = document.getElementById('industrySelect');
if (!quick || !select || quick.selectedIndex < 0 || select.selectedIndex < 0) return false;
const quickText = String(quick.options[quick.selectedIndex].textContent || '').split(' (', 1)[0].trim();
const selectText = String(select.options[select.selectedIndex].textContent || '').split(' (', 1)[0].trim();
return !!String(quick.value || '').trim() && !!quickText && quickText === selectText;
                    """
                )
            )
        )

        auto_selected_option_text = str(
            driver.execute_script(
                """
const el = document.getElementById('industrySelect');
if (!el) return '';
const option = el.options && el.selectedIndex >= 0 ? el.options[el.selectedIndex] : null;
return option ? String(option.textContent || '').trim() : '';
                """
            )
            or ""
        ).strip()
        industry_auto_reason = str(
            driver.execute_script("const el=document.getElementById('industryAutoReason'); return el ? (el.textContent || '') : '';")
            or ""
        ).strip()
        industry_auto_reason_kind = str(
            driver.execute_script("const el=document.getElementById('industryAutoReason'); return el ? (el.getAttribute('data-reason-kind') || '') : '';")
            or ""
        ).strip()
        industry_auto_reason_tone = str(
            driver.execute_script("const el=document.getElementById('industryAutoReason'); return el ? (el.getAttribute('data-reason-tone') || '') : '';")
            or ""
        ).strip()
        industry_auto_reason_icon = str(
            driver.execute_script("const el=document.getElementById('industryAutoReason'); return el ? (el.getAttribute('data-reason-icon') || '') : '';")
            or ""
        ).strip()
        industry_auto_reason_actionable = str(
            driver.execute_script("const el=document.getElementById('industryAutoReason'); return el ? (el.getAttribute('data-actionable') || '') : '';")
            or ""
        ).strip()
        industry_auto_reason_query = str(
            driver.execute_script(
                "const el=document.querySelector('#industryAutoReason .auto-selection-token');"
                " return el ? (el.textContent || '') : '';"
            )
            or ""
        ).strip()
        industry_auto_reason_field = str(
            driver.execute_script(
                "const el=document.querySelector('#industryAutoReason .auto-selection-field');"
                " return el ? (el.textContent || '') : '';"
            )
            or ""
        ).strip()
        driver.execute_script(
            """
const input = document.getElementById('capitalInput') || document.getElementById('categorySelect');
if (input && typeof input.focus === 'function') input.focus();
const note = document.getElementById('industryAutoReason');
if (note) note.click();
            """
        )
        wait.until(
            lambda d: str(
                d.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                or ""
            ).strip() == "industrySearchInput"
        )
        industry_auto_reason_refocus = str(
            driver.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
            or ""
        ).strip()
        industry_auto_reason_refocus_highlight = bool(
            driver.execute_script(
                "const el=document.activeElement;"
                " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                " return !!box;"
            )
        )
        industry_auto_reason_refocus_helper = str(
            driver.execute_script(
                "const el=document.activeElement;"
                " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                " return box ? (box.getAttribute('data-guided-focus-copy') || '') : '';"
            )
            or ""
        ).strip()
        permit_summary_after_select = str(
            driver.execute_script("const el=document.getElementById('permitWizardSummary'); return el ? (el.innerText || '') : '';")
            or ""
        ).strip()
        permit_blocker_after_select = _text(driver, "permitWizardBlocker")
        wizard_next_action_after_select = _text(driver, "permitWizardNextActionText")
        driver.execute_script(
            """
const btn = document.getElementById('permitWizardNextAction');
if (btn) btn.click();
            """
        )
        wait.until(
            lambda d: str(
                d.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                or ""
            ).strip() in {"capitalInput", "technicianInput", "equipmentInput"}
        )
        wizard_next_action_after_select_focus = str(
            driver.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
            or ""
        ).strip()
        wizard_next_action_after_select_highlight = bool(
            driver.execute_script(
                "const el=document.activeElement;"
                " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                " return !!box;"
            )
        )
        search_auto_selected = bool(search_seed) and search_seed in auto_selected_option_text
        smart_profile_text = str(
            driver.execute_script("const el=document.getElementById('smartIndustryProfile'); return el ? (el.innerText || '') : '';")
            or ""
        ).strip()
        holdings_priority_hint = _text(driver, "holdingsPriorityHint")
        desktop_fill_label = _text(driver, "fillRequirementPreset")
        capital_placeholder = str(
            driver.execute_script("const el=document.getElementById('capitalInput'); return el ? (el.getAttribute('placeholder') || '') : '';")
            or ""
        ).strip()
        result_actions_ready = bool(
            driver.execute_script(
                "const el=document.getElementById('resultActionWrap'); return !!el && el.classList.contains('ready');"
            )
        )
        result_brief_after_select = str(
            driver.execute_script("const el=document.getElementById('resultBrief'); return el ? (el.value || '') : '';")
            or ""
        ).strip()
        focus_quick_synced = bool(
            driver.execute_script(
                """
const quick = document.getElementById('focusQuickSelect');
const select = document.getElementById('industrySelect');
if (!quick || !select || quick.selectedIndex < 0 || select.selectedIndex < 0) return false;
const quickText = String(quick.options[quick.selectedIndex].textContent || '').split(' (', 1)[0].trim();
const selectText = String(select.options[select.selectedIndex].textContent || '').split(' (', 1)[0].trim();
return !!String(quick.value || '').trim() && !!quickText && quickText === selectText;
                """
            )
        )
        advanced_inputs_present = bool(
            driver.execute_script("return !!document.getElementById('advancedInputs');")
        )
        banner_title = _text(driver, "resultBannerTitle")
        banner_meta = _text(driver, "resultBannerMeta")
        required_capital_text = _text(driver, "requiredCapital")
        requirements_meta_text = _text(driver, "requirementsMeta")
        capital_status_text = _text(driver, "capitalGapStatus")
        preset_actions_present = bool(
            driver.execute_script(
                "return !!document.getElementById('fillRequirementPreset') && !!document.getElementById('resetHoldingsPreset');"
            )
        )
        driver.execute_script(
            """
const btn = document.querySelector('[data-permit-wizard-next="2"]');
if (btn && !btn.disabled) btn.click();
            """
        )
        wait.until(lambda d: "기타 준비 상태" in _text(d, "permitWizardStepTitle"))
        wizard_optional_title = _text(driver, "permitWizardStepTitle")
        wizard_progress_step4 = _text(driver, "permitWizardProgressLabel")
        wizard_optional_state = "기타" in wizard_optional_title
        optional_priority_hint = _text(driver, "optionalPriorityHint")
        optional_toggle_label_collapsed = _text(driver, "optionalChecklistToggle")
        optional_visible_count_collapsed = int(
            driver.execute_script(
                """
return Array.from(document.querySelectorAll('#advancedInputs .check-item'))
  .filter((el) => window.getComputedStyle(el).display !== 'none').length;
                """
            )
            or 0
        )
        optional_priority_labels = list(
            driver.execute_script(
                """
return Array.from(document.querySelectorAll('#advancedInputs .check-item'))
  .slice(0, 3)
  .map((el) => String(el.innerText || '').replace(/\\s+/g, ' ').trim());
                """
            )
            or []
        )
        driver.execute_script(
            """
const btn = document.getElementById('optionalChecklistToggle');
if (btn && !btn.hidden) btn.click();
            """
        )
        wait.until(
            lambda d: int(
                d.execute_script(
                    """
return Array.from(document.querySelectorAll('#advancedInputs .check-item'))
  .filter((el) => window.getComputedStyle(el).display !== 'none').length;
                    """
                )
                or 0
            ) > 3
        )
        optional_toggle_label_expanded = _text(driver, "optionalChecklistToggle")
        optional_visible_count_expanded = int(
            driver.execute_script(
                """
return Array.from(document.querySelectorAll('#advancedInputs .check-item'))
  .filter((el) => window.getComputedStyle(el).display !== 'none').length;
                """
            )
            or 0
        )
        optional_priority_badges = list(
            driver.execute_script(
                """
return Array.from(document.querySelectorAll('#advancedInputs .check-item.is-priority'))
  .slice(0, 3)
  .map((el) => String(el.getAttribute('data-priority-badge') || '').trim());
                """
            )
            or []
        )
        driver.execute_script(
            """
Array.from(document.querySelectorAll('#advancedInputs .check-item.is-priority input'))
  .slice(0, 2)
  .forEach((el) => {
    if (!el.checked) el.click();
  });
            """
        )
        wait.until(
            lambda d: "선택 준비" in str(
                d.execute_script("const el=document.getElementById('resultBrief'); return el ? (el.value || '') : '';")
                or ""
            )
        )
        optional_checked_labels = list(
            driver.execute_script(
                """
return Array.from(document.querySelectorAll('#advancedInputs .check-item input:checked'))
  .map((el) => {
    const row = el.closest('.check-item');
    return String(row ? (row.innerText || '') : '').replace(/\\s+/g, ' ').trim();
  });
                """
            )
            or []
        )
        banner_meta_after_optional = _text(driver, "resultBannerMeta")
        result_action_note_after_optional = _text_fallback(driver, "resultActionNote")
        result_brief_after_optional = str(
            driver.execute_script("const el=document.getElementById('resultBrief'); return el ? (el.value || '') : '';")
            or ""
        ).strip()
        copy_result_brief_label_after_optional = _text(driver, "btnCopyResultBrief")
        mark("optional_step_reached")
        driver.execute_script(
            """
const btn = document.querySelector('[data-permit-wizard-prev="3"]');
if (btn && !btn.disabled) btn.click();
            """
        )
        wait.until(lambda d: "현재 보유 현황" in _text(d, "permitWizardStepTitle"))
        driver.execute_script(
            """
const btn = document.getElementById('fillRequirementPreset');
if (btn && !btn.disabled) btn.click();
            """
        )
        wait.until(lambda d: _text(d, "capitalGapStatus") == "\uAE30\uC900 \uCDA9\uC871")
        wizard_post_fill_title = _text(driver, "permitWizardStepTitle")
        wizard_progress_after_fill = _text(driver, "permitWizardProgressLabel")
        permit_summary_after_fill = str(
            driver.execute_script("const el=document.getElementById('permitWizardSummary'); return el ? (el.innerText || '') : '';")
            or ""
        ).strip()
        permit_blocker_after_fill = _text(driver, "permitWizardBlocker")
        wizard_next_action_after_fill = _text(driver, "permitWizardNextActionText")
        driver.execute_script(
            """
const btn = document.getElementById('permitWizardNextAction');
if (btn) btn.click();
            """
        )
        wait.until(
            lambda d: str(
                d.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                or ""
            ).strip() == "btnCopyResultBrief"
        )
        wizard_next_action_after_fill_focus = str(
            driver.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
            or ""
        ).strip()
        wizard_next_action_after_fill_highlight = bool(
            driver.execute_script(
                "const el=document.activeElement;"
                " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                " return !!box;"
            )
        )
        filled_capital_value = str(
            driver.execute_script("const el=document.getElementById('capitalInput'); return el ? (el.value || '') : '';")
            or ""
        ).strip()
        filled_technician_value = str(
            driver.execute_script("const el=document.getElementById('technicianInput'); return el ? (el.value || '') : '';")
            or ""
        ).strip()
        filled_equipment_value = str(
            driver.execute_script("const el=document.getElementById('equipmentInput'); return el ? (el.value || '') : '';")
            or ""
        ).strip()
        post_fill_banner_title = _text(driver, "resultBannerTitle")
        post_fill_capital_status = _text(driver, "capitalGapStatus")
        post_fill_technician_status = _text(driver, "technicianGapStatus")
        post_fill_equipment_status = _text(driver, "equipmentGapStatus")
        result_brief_after_fill = str(
            driver.execute_script("const el=document.getElementById('resultBrief'); return el ? (el.value || '') : '';")
            or ""
        ).strip()
        result_brief_meta_after_fill = _text(driver, "resultBriefMeta")
        copy_result_brief_label_after_fill = _text(driver, "btnCopyResultBrief")
        mark("preset_fill_completed")
        driver.set_window_size(430, 1600)
        wait.until(
            lambda d: bool(
                d.execute_script(
                    "const el=document.getElementById('mobileQuickBar');"
                    " if (!el) return false;"
                    " const st=window.getComputedStyle(el);"
                    " return st.display !== 'none';"
                )
            )
        )
        mobile_quick_title = _text(driver, "mobileQuickTitle")
        mobile_quick_meta = _text(driver, "mobileQuickMeta")
        mobile_quick_preset_label = _text(driver, "mobileQuickPresetButton")
        permit_mobile_sticky_visible = bool(
            driver.execute_script(
                "const el=document.getElementById('permitWizardMobileSticky');"
                " if (!el) return false;"
                " const st=window.getComputedStyle(el);"
                " return st.display !== 'none';"
            )
        )
        permit_mobile_sticky_label = _text(driver, "permitWizardMobileStickyLabel")
        permit_mobile_sticky_action = _text(driver, "permitWizardMobileStickyAction")
        permit_mobile_sticky_compact = _text(driver, "permitWizardMobileStickyCompact")
        driver.execute_script("if (document.activeElement && document.activeElement.blur) document.activeElement.blur();")
        driver.execute_script(
            """
const btn = document.getElementById('permitWizardMobileSticky');
if (btn) btn.click();
                """
        )
        wait.until(
            lambda d: str(
                d.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
                or ""
            ).strip() == "btnCopyResultBrief"
        )
        permit_mobile_sticky_focus = str(
            driver.execute_script("const el=document.activeElement; return el ? (el.id || '') : '';")
            or ""
        ).strip()
        permit_mobile_sticky_highlight = bool(
            driver.execute_script(
                "const el=document.activeElement;"
                " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                " return !!box;"
            )
        )
        permit_mobile_sticky_helper = str(
            driver.execute_script(
                "const el=document.activeElement;"
                " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                " return box ? (box.getAttribute('data-guided-focus-copy') || '') : '';"
            )
            or ""
        ).strip()
        permit_mobile_sticky_level = str(
            driver.execute_script(
                "const el=document.activeElement;"
                " const box = el ? (el.closest('.guided-focus-target') || (el.classList && el.classList.contains('guided-focus-target') ? el : null)) : null;"
                " return box ? (box.getAttribute('data-guided-focus-level') || '') : '';"
            )
            or ""
        ).strip()
        mobile_quick_result_enabled = bool(
            driver.execute_script(
                "const btn=document.getElementById('mobileQuickResultButton'); return !!btn && btn.disabled === false;"
            )
        )
        if mobile_quick_result_enabled:
            driver.execute_script(
                """
const btn = document.getElementById('mobileQuickResultButton');
if (btn && !btn.disabled) btn.click();
                """
            )
        wait.until(
            lambda d: bool(
                d.execute_script(
                    """
const target = document.getElementById('resultBanner')
  || document.getElementById('result-title')
  || document.querySelector('.result-card');
if (!target) return false;
const rect = target.getBoundingClientRect();
return rect.top >= -8 && rect.top <= Math.max(220, window.innerHeight * 0.4);
                    """
                )
            )
        )
        mobile_quick_scroll_ok = bool(
            driver.execute_script(
                """
const target = document.getElementById('resultBanner')
  || document.getElementById('result-title')
  || document.querySelector('.result-card');
if (!target) return false;
const rect = target.getBoundingClientRect();
return rect.top >= -8 && rect.top <= Math.max(220, window.innerHeight * 0.4);
                """
            )
        )
        if mobile_quick_preset_label == "\uC785\uB825 \uCD08\uAE30\uD654":
            driver.execute_script(
                """
const btn = document.getElementById('mobileQuickPresetButton');
if (btn && !btn.disabled) btn.click();
                """
            )
            wait.until(
                lambda d: bool(
                    d.execute_script(
                        "const capital=document.getElementById('capitalInput');"
                        " const tech=document.getElementById('technicianInput');"
                        " const equip=document.getElementById('equipmentInput');"
                        " return !!capital && !!tech && !!equip"
                        " && String(capital.value || '') === ''"
                        " && String(tech.value || '') === ''"
                        " && String(equip.value || '') === '';"
                    )
                )
            )
        wizard_after_reset_title = _text(driver, "permitWizardStepTitle")
        permit_summary_after_reset = str(
            driver.execute_script("const el=document.getElementById('permitWizardSummary'); return el ? (el.innerText || '') : '';")
            or ""
        ).strip()
        permit_blocker_after_reset = _text(driver, "permitWizardBlocker")
        mobile_quick_preset_label_after_reset = _text(driver, "mobileQuickPresetButton")
        desktop_fill_label_after_reset = _text(driver, "fillRequirementPreset")
        mark("mobile_reset_completed")
        permit_family_cases = [
            {
                "name": "security_escort_family",
                "category_code": "34",
                "service_code": "FOCUS::security-escort",
                "query": "호송경비업",
                "expected_summary_after_fill": "현재 보유 3/3 입력",
                "expected_note_count": "3개",
                "expected_missing_tokens": ["자본금", "기술자", "장비"],
                "unexpected_missing_tokens": [],
                "expected_hint_tokens": ["호송경비업", "2억"],
                "expected_capital_value": "2",
                "expected_technician_value": "1",
                "expected_equipment_value": "1",
                "expected_requirements_tokens": ["기술인력 1명", "장비 1식", "예치 30일"],
                "unexpected_requirements_tokens": [],
                "expected_equipment_card_visible": True,
                "expected_profile_tokens": ["필수 3개만 확인", "장비/설비", "예치/보완 일정"],
                "unexpected_profile_tokens": [],
                "expected_fill_label": "필수 3개 채우기",
                "expected_equipment_input_visible": True,
            },
            {
                "name": "gas_facility_family",
                "category_code": "35",
                "service_code": "FOCUS::gas-facility-2",
                "query": "가스시설시공업2종",
                "expected_summary_after_fill": "현재 보유 3/3 입력",
                "expected_note_count": "3개",
                "expected_missing_tokens": ["자본금", "기술자", "장비"],
                "unexpected_missing_tokens": [],
                "expected_hint_tokens": ["가스시설시공업2종", "1억"],
                "expected_capital_value": "1",
                "expected_technician_value": "1",
                "expected_equipment_value": "1",
                "expected_requirements_tokens": ["기술인력 1명", "장비 1식", "예치 30일"],
                "unexpected_requirements_tokens": [],
                "expected_equipment_card_visible": True,
                "expected_profile_tokens": ["필수 3개만 확인", "장비/설비", "예치/보완 일정"],
                "unexpected_profile_tokens": [],
                "expected_fill_label": "필수 3개 채우기",
                "expected_equipment_input_visible": True,
            },
            {
                "name": "sawmill_two_core",
                "category_code": "09",
                "service_code": "09_27_03_P",
                "query": "제재업",
                "expected_summary_after_fill": "현재 보유 2/2 입력",
                "expected_note_count": "2개",
                "expected_missing_tokens": ["자본금", "기술자"],
                "unexpected_missing_tokens": ["장비"],
                "expected_hint_tokens": ["제재업", "0.3억", "기술자 1명"],
                "expected_capital_value": "0.3",
                "expected_technician_value": "1",
                "expected_equipment_value": "",
                "expected_requirements_tokens": ["기술인력 1명"],
                "unexpected_requirements_tokens": ["장비", "예치"],
                "expected_equipment_card_visible": False,
                "expected_profile_tokens": ["필수 2개만 확인"],
                "unexpected_profile_tokens": ["장비/설비", "예치/보완 일정"],
                "expected_fill_label": "필수 2개 채우기",
                "expected_equipment_input_visible": False,
            },
        ]
        permit_family_outputs = []
        driver.set_window_size(1440, 2200)
        for coverage_case in permit_family_cases:
            mark(f"family_case_select:{coverage_case['name']}")
            _select_permit_industry_by_code(
                driver,
                wait,
                focus_mode="all",
                category_code=str(coverage_case["category_code"]),
                service_code=str(coverage_case["service_code"]),
                expected_name=str(coverage_case["query"]),
            )
            mark(f"family_case_selected:{coverage_case['name']}")
            driver.execute_script(
                """
const title = document.getElementById('permitWizardStepTitle');
const currentTitle = title ? String(title.innerText || '') : '';
if (currentTitle.includes('현재 보유 현황')) return;
const prev = document.querySelector('[data-permit-wizard-prev="3"]');
const track = document.querySelector('[data-permit-wizard-track="2"]');
const target = prev && !prev.disabled ? prev : track;
if (target && !target.disabled) target.click();
                """
            )
            wait.until(lambda d: "현재 보유 현황" in _text(d, "permitWizardStepTitle"))
            mark(f"family_case_holdings_step:{coverage_case['name']}")
            driver.execute_script(
                """
for (const id of ['capitalInput', 'technicianInput', 'equipmentInput']) {
  const el = document.getElementById(id);
  if (!el) continue;
  el.value = '';
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}
                """
            )
            wait.until(lambda d: "현재 보유 미입력" in str(d.execute_script("const el=document.getElementById('permitWizardSummary'); return el ? (el.innerText || '') : '';") or ""))
            driver.execute_script(
                """
const btn = document.querySelector('[data-permit-wizard-track="2"]');
if (btn) btn.click();
                """
            )
            wait.until(lambda d: "현재 보유 현황" in _text(d, "permitWizardStepTitle"))
            mark(f"family_case_cleared:{coverage_case['name']}")
            case_step_note = _text(driver, "permitWizardStepNote")
            case_blocker = _text(driver, "permitWizardBlocker")
            case_hint = _text(driver, "holdingsPriorityHint")
            case_requirements_meta = _text(driver, "requirementsMeta")
            case_equipment_status = _text(driver, "equipmentGapStatus")
            case_equipment_card_visible = bool(
                driver.execute_script(
                    """
const el = document.getElementById('equipmentGapStatus');
const card = el ? el.closest('.status-card') : null;
return !!card && !card.hidden;
                    """
                )
            )
            case_equipment_input_visible = bool(
                driver.execute_script(
                    """
const el = document.getElementById('equipmentInput');
const field = el ? el.closest('.field') : null;
return !!field && !field.hidden;
                    """
                )
            )
            case_fill_label = _text(driver, "fillRequirementPreset")
            case_smart_profile = str(
                driver.execute_script("const el=document.getElementById('smartIndustryProfile'); return el ? (el.innerText || '') : '';")
                or ""
            ).strip()
            driver.execute_script(
                """
const btn = document.getElementById('fillRequirementPreset');
if (btn && !btn.disabled) btn.click();
                """
            )
            wait.until(
                lambda d, expected=str(coverage_case["expected_summary_after_fill"]): expected in str(
                    d.execute_script("const el=document.getElementById('permitWizardSummary'); return el ? (el.innerText || '') : '';")
                    or ""
                )
            )
            mark(f"family_case_filled:{coverage_case['name']}")
            case_summary_after_fill = str(
                driver.execute_script("const el=document.getElementById('permitWizardSummary'); return el ? (el.innerText || '') : '';")
                or ""
            ).strip()
            case_capital_value = str(
                driver.execute_script("const el=document.getElementById('capitalInput'); return el ? (el.value || '') : '';")
                or ""
            ).strip()
            case_technician_value = str(
                driver.execute_script("const el=document.getElementById('technicianInput'); return el ? (el.value || '') : '';")
                or ""
            ).strip()
            case_equipment_value = str(
                driver.execute_script("const el=document.getElementById('equipmentInput'); return el ? (el.value || '') : '';")
                or ""
            ).strip()
            case_ok = (
                all(token in case_blocker for token in coverage_case["expected_missing_tokens"])
                and all(token not in case_blocker for token in coverage_case["unexpected_missing_tokens"])
                and all(token in case_hint for token in coverage_case["expected_hint_tokens"])
                and coverage_case["expected_summary_after_fill"] in case_summary_after_fill
                and ("필수" in case_step_note and str(coverage_case["expected_note_count"]) in case_step_note)
                and case_capital_value == str(coverage_case["expected_capital_value"])
                and case_technician_value == str(coverage_case["expected_technician_value"])
                and case_equipment_value == str(coverage_case["expected_equipment_value"])
                and all(token in case_requirements_meta for token in coverage_case.get("expected_requirements_tokens", []))
                and all(token not in case_requirements_meta for token in coverage_case.get("unexpected_requirements_tokens", []))
                and case_equipment_card_visible is bool(coverage_case.get("expected_equipment_card_visible"))
                and case_equipment_input_visible is bool(coverage_case.get("expected_equipment_input_visible"))
                and all(token in case_smart_profile for token in coverage_case.get("expected_profile_tokens", []))
                and all(token not in case_smart_profile for token in coverage_case.get("unexpected_profile_tokens", []))
                and case_fill_label == str(coverage_case.get("expected_fill_label", ""))
            )
            permit_family_outputs.append(
                {
                    "name": str(coverage_case["name"]),
                    "query": str(coverage_case["query"]),
                    "category_code": str(coverage_case["category_code"]),
                    "service_code": str(coverage_case["service_code"]),
                    "step_note": case_step_note,
                    "blocker": case_blocker,
                    "hint": case_hint,
                    "requirements_meta": case_requirements_meta,
                    "equipment_status": case_equipment_status,
                    "equipment_card_visible": case_equipment_card_visible,
                    "equipment_input_visible": case_equipment_input_visible,
                    "fill_label": case_fill_label,
                    "smart_profile": case_smart_profile,
                    "summary_after_fill": case_summary_after_fill,
                    "capital_value": case_capital_value,
                    "technician_value": case_technician_value,
                    "equipment_value": case_equipment_value,
                    "ok": case_ok,
                }
            )
        console_errors = _browser_errors(driver)

        result["output"] = {
            "wizard_exists": wizard_exists,
            "wizard_step_count": wizard_step_count,
            "wizard_initial_title": wizard_initial_title,
            "wizard_progress_initial": wizard_progress_initial,
            "wizard_progress_meta_initial": wizard_progress_meta_initial,
            "wizard_next_action_initial": wizard_next_action_initial,
            "wizard_next_action_initial_focus": wizard_next_action_initial_focus,
            "wizard_next_action_initial_highlight": wizard_next_action_initial_highlight,
            "wizard_step1_visible": wizard_step1_visible,
            "wizard_summary_initial": wizard_summary_initial,
            "wizard_blocker_initial": wizard_blocker_initial,
            "wizard_step3_title": wizard_step3_title,
            "wizard_progress_step3": wizard_progress_step3,
            "wizard_optional_title": wizard_optional_title,
            "wizard_progress_step4": wizard_progress_step4,
            "wizard_optional_state": wizard_optional_state,
            "optional_priority_hint": optional_priority_hint,
            "optional_toggle_label_collapsed": optional_toggle_label_collapsed,
            "optional_visible_count_collapsed": optional_visible_count_collapsed,
            "optional_toggle_label_expanded": optional_toggle_label_expanded,
            "optional_visible_count_expanded": optional_visible_count_expanded,
            "optional_priority_labels": optional_priority_labels,
            "optional_priority_badges": optional_priority_badges,
            "optional_checked_labels": optional_checked_labels,
            "banner_meta_after_optional": banner_meta_after_optional,
            "result_action_note_after_optional": result_action_note_after_optional,
            "result_brief_after_optional": result_brief_after_optional,
            "copy_result_brief_label_after_optional": copy_result_brief_label_after_optional,
            "initial_actions_hidden": initial_actions_hidden,
            "mode_pill_sync": mode_pill_sync,
            "first_focus_option_text": first_focus_option_text,
            "search_seed": search_seed,
            "exact_search_top_option_text": exact_search_top_option_text,
            "focus_hint": focus_hint,
            "auto_selected_option_text": auto_selected_option_text,
            "industry_auto_reason": industry_auto_reason,
            "industry_auto_reason_kind": industry_auto_reason_kind,
            "industry_auto_reason_tone": industry_auto_reason_tone,
            "industry_auto_reason_icon": industry_auto_reason_icon,
            "industry_auto_reason_actionable": industry_auto_reason_actionable,
            "industry_auto_reason_query": industry_auto_reason_query,
            "industry_auto_reason_field": industry_auto_reason_field,
            "industry_auto_reason_refocus": industry_auto_reason_refocus,
            "industry_auto_reason_refocus_highlight": industry_auto_reason_refocus_highlight,
            "industry_auto_reason_refocus_helper": industry_auto_reason_refocus_helper,
            "search_auto_selected": search_auto_selected,
            "permit_summary_after_select": permit_summary_after_select,
            "permit_blocker_after_select": permit_blocker_after_select,
            "wizard_next_action_after_select": wizard_next_action_after_select,
            "wizard_next_action_after_select_focus": wizard_next_action_after_select_focus,
            "wizard_next_action_after_select_highlight": wizard_next_action_after_select_highlight,
            "smart_profile_text": smart_profile_text,
            "holdings_priority_hint": holdings_priority_hint,
            "desktop_fill_label": desktop_fill_label,
            "capital_placeholder": capital_placeholder,
            "result_actions_ready": result_actions_ready,
            "result_brief_after_select": result_brief_after_select,
            "focus_quick_synced": focus_quick_synced,
            "preset_actions_present": preset_actions_present,
            "advanced_inputs_present": advanced_inputs_present,
            "banner_title": banner_title,
            "banner_meta": banner_meta,
            "required_capital_text": required_capital_text,
            "requirements_meta_text": requirements_meta_text,
            "capital_status_text": capital_status_text,
            "filled_capital_value": filled_capital_value,
            "filled_technician_value": filled_technician_value,
            "filled_equipment_value": filled_equipment_value,
            "wizard_post_fill_title": wizard_post_fill_title,
            "wizard_progress_after_fill": wizard_progress_after_fill,
            "permit_summary_after_fill": permit_summary_after_fill,
            "permit_blocker_after_fill": permit_blocker_after_fill,
            "wizard_next_action_after_fill": wizard_next_action_after_fill,
            "wizard_next_action_after_fill_focus": wizard_next_action_after_fill_focus,
            "wizard_next_action_after_fill_highlight": wizard_next_action_after_fill_highlight,
            "post_fill_banner_title": post_fill_banner_title,
            "post_fill_capital_status": post_fill_capital_status,
            "post_fill_technician_status": post_fill_technician_status,
            "post_fill_equipment_status": post_fill_equipment_status,
            "result_brief_after_fill": result_brief_after_fill,
            "result_brief_meta_after_fill": result_brief_meta_after_fill,
            "copy_result_brief_label_after_fill": copy_result_brief_label_after_fill,
            "mobile_quick_title": mobile_quick_title,
            "mobile_quick_meta": mobile_quick_meta,
            "mobile_quick_preset_label": mobile_quick_preset_label,
            "permit_mobile_sticky_visible": permit_mobile_sticky_visible,
            "permit_mobile_sticky_label": permit_mobile_sticky_label,
            "permit_mobile_sticky_action": permit_mobile_sticky_action,
            "permit_mobile_sticky_compact": permit_mobile_sticky_compact,
            "permit_mobile_sticky_focus": permit_mobile_sticky_focus,
            "permit_mobile_sticky_highlight": permit_mobile_sticky_highlight,
            "permit_mobile_sticky_helper": permit_mobile_sticky_helper,
            "permit_mobile_sticky_level": permit_mobile_sticky_level,
            "mobile_quick_result_enabled": mobile_quick_result_enabled,
            "mobile_quick_scroll_ok": mobile_quick_scroll_ok,
            "wizard_after_reset_title": wizard_after_reset_title,
            "permit_summary_after_reset": permit_summary_after_reset,
            "permit_blocker_after_reset": permit_blocker_after_reset,
            "mobile_quick_preset_label_after_reset": mobile_quick_preset_label_after_reset,
            "desktop_fill_label_after_reset": desktop_fill_label_after_reset,
            "permit_family_cases": permit_family_outputs,
        }
        mark("output_captured")
        result["console_errors"] = console_errors
        result["ok"] = (
            wizard_exists
            and wizard_step_count >= 4
            and "STEP 1" in wizard_initial_title
            and wizard_progress_initial == "현재 1/4 단계"
            and wizard_progress_meta_initial == "필수 0/3 완료 · 업종 검색부터 시작합니다."
            and wizard_next_action_initial == "업종명 검색이나 빠른 선택으로 시작하세요."
            and wizard_next_action_initial_focus == "industrySearchInput"
            and wizard_next_action_initial_highlight
            and wizard_step1_visible
            and bool(wizard_summary_initial)
            and "검색" in wizard_blocker_initial
            and "현재 보유 현황" in wizard_step3_title
            and wizard_progress_step3 == "현재 3/4 단계"
            and "기타 준비 상태" in wizard_optional_title
            and wizard_progress_step4 == "현재 4/4 단계"
            and wizard_optional_state
            and "안전" in optional_priority_hint
            and "시설" in optional_priority_hint
            and "자격" in optional_priority_hint
            and "더 보기" in optional_toggle_label_collapsed
            and optional_visible_count_collapsed == 3
            and "우선 항목만 보기" == optional_toggle_label_expanded
            and optional_visible_count_expanded > optional_visible_count_collapsed
            and len(optional_priority_labels) >= 3
            and "안전" in optional_priority_labels[0]
            and "시설" in optional_priority_labels[1]
            and "자격" in optional_priority_labels[2]
            and optional_priority_badges[:2] == ["우선 1", "우선 2"]
            and len(optional_checked_labels) >= 2
            and "선택 준비" in banner_meta_after_optional
            and "안전" in banner_meta_after_optional
            and (
                "보완" in result_action_note_after_optional
                or "선택 준비" in result_action_note_after_optional
                or ("선택 준비" in result_brief_after_optional and copy_result_brief_label_after_optional == "보완 브리프 복사")
            )
            and "선택 준비" in result_brief_after_optional
            and "안전" in result_brief_after_optional
            and "시설" in result_brief_after_optional
            and copy_result_brief_label_after_optional == "보완 브리프 복사"
            and initial_actions_hidden
            and mode_pill_sync
            and bool(first_focus_option_text)
            and bool(search_seed)
            and exact_search_top_option_text.startswith(search_seed)
            and (focus_hint in {"", "-"} or "업종명 우선" in focus_hint)
            and bool(auto_selected_option_text)
            and search_auto_selected
            and "자동 선택" in industry_auto_reason
            and search_seed in industry_auto_reason
            and industry_auto_reason_tone in {"match", "search", "direct", "guide"}
            and industry_auto_reason_icon in {"=", "~", ">", "i"}
            and (industry_auto_reason_tone != "search" or industry_auto_reason_icon == "~")
            and industry_auto_reason_actionable == "1"
            and industry_auto_reason_query == search_seed
            and industry_auto_reason_kind in {"정확 일치", "접두 일치", "관련도 최고", "검색 1건", "선택 1건", "자동 선택"}
            and (
                industry_auto_reason_kind not in {"정확 일치", "접두 일치", "관련도 최고"}
                or bool(industry_auto_reason_field)
            )
            and industry_auto_reason_refocus == "industrySearchInput"
            and industry_auto_reason_refocus_highlight
            and "다시 정렬" in industry_auto_reason_refocus_helper
            and bool(permit_summary_after_select)
            and search_seed in permit_summary_after_select
            and ("자본금" in permit_blocker_after_select or "기술자" in permit_blocker_after_select)
            and wizard_next_action_after_select == "자본금, 기술자, 장비를 순서대로 입력하세요."
            and wizard_next_action_after_select_focus in {"capitalInput", "technicianInput", "equipmentInput"}
            and wizard_next_action_after_select_highlight
            and bool(smart_profile_text)
            and "필수 3개만 확인" in smart_profile_text
            and search_seed in holdings_priority_hint
            and desktop_fill_label == "\uD544\uC218 3\uAC1C \uCC44\uC6B0\uAE30"
            and bool(capital_placeholder)
            and result_actions_ready
            and bool(result_brief_after_select)
            and search_seed in result_brief_after_select
            and focus_quick_synced
            and preset_actions_present
            and advanced_inputs_present
            and required_capital_text not in {"", "-"}
            and requirements_meta_text not in {"", "-"}
            and banner_title not in {"", "-"}
            and banner_meta not in {"", "-"}
            and capital_status_text not in {"", "-"}
            and filled_capital_value not in {"", "-"}
            and filled_technician_value not in {"", "-"}
            and filled_equipment_value not in {"", "-"}
            and "기타 준비 상태" in wizard_post_fill_title
            and wizard_progress_after_fill == "현재 4/4 단계"
            and "현재 보유 3/3 입력" in permit_summary_after_fill
            and "필수 입력은 끝났습니다." in permit_blocker_after_fill
            and wizard_next_action_after_fill == "전달 브리프를 복사해 바로 전달하세요."
            and wizard_next_action_after_fill_focus == "btnCopyResultBrief"
            and wizard_next_action_after_fill_highlight
            and "\uCDA9\uC871 \uAC00\uB2A5\uC131" in post_fill_banner_title
            and post_fill_capital_status == "\uAE30\uC900 \uCDA9\uC871"
            and post_fill_technician_status == "\uAE30\uC900 \uCDA9\uC871"
            and post_fill_equipment_status == "\uAE30\uC900 \uCDA9\uC871"
            and "\uAE30\uC900 \uCDA9\uC871" in result_brief_after_fill
            and "전달 준비" in result_brief_meta_after_fill
            and copy_result_brief_label_after_fill == "전달 브리프 복사"
            and bool(mobile_quick_title)
            and bool(mobile_quick_meta)
            and mobile_quick_preset_label == "\uC785\uB825 \uCD08\uAE30\uD654"
            and permit_mobile_sticky_visible
            and permit_mobile_sticky_label == "현재 4/4 단계"
            and "전달 브리프" in permit_mobile_sticky_action
            and permit_mobile_sticky_compact == "브리프 복사 후 전달"
            and permit_mobile_sticky_focus == "btnCopyResultBrief"
            and permit_mobile_sticky_highlight
            and "지금은 브리프만" in permit_mobile_sticky_helper
            and permit_mobile_sticky_level == "sticky"
            and mobile_quick_result_enabled
            and mobile_quick_scroll_ok
            and "현재 보유 현황" in wizard_after_reset_title
            and "현재 보유 미입력" in permit_summary_after_reset
            and "선택 정보는 마지막 단계" in permit_summary_after_reset
            and "자본금" in permit_blocker_after_reset
            and mobile_quick_preset_label_after_reset == "\uD544\uC218 3\uAC1C \uCC44\uC6B0\uAE30"
            and desktop_fill_label_after_reset == "\uD544\uC218 3\uAC1C \uCC44\uC6B0\uAE30"
            and permit_family_outputs
            and all(bool((row or {}).get("ok")) for row in permit_family_outputs)
            and not console_errors
        )
        if not result["ok"]:
            result["artifacts"]["failure_screenshot"] = _save_failure_screenshot(driver, PERMIT_FAIL_SCREENSHOT)
            result["artifacts"]["failure_html"] = _save_page_source(driver, PERMIT_FAIL_HTML)
        mark("result_evaluated")
        return result
    except Exception as exc:  # noqa: BLE001
        result["console_errors"] = _browser_errors(driver)
        error_text = str(exc).strip()
        result["error"] = f"{type(exc).__name__}: {error_text}" if error_text else type(exc).__name__
        try:
            result["artifacts"]["failure_screenshot"] = _save_failure_screenshot(driver, PERMIT_FAIL_SCREENSHOT)
            result["artifacts"]["failure_html"] = _save_page_source(driver, PERMIT_FAIL_HTML)
        except Exception:
            pass
        return result
    finally:
        driver.quit()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="Run browser click smoke on local calculator previews before publish")
    parser.add_argument("--skip-build", action="store_true", default=False)
    parser.add_argument("--headful", action="store_true", default=False)
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    report: Dict[str, Any] = {
        "generated_at": _now(),
        "ok": False,
        "rebuilt": {},
        "previews": {},
        "checks": {},
        "blocking_issues": [],
    }

    try:
        if not args.skip_build:
            report["rebuilt"] = _build_outputs()
        report["previews"] = _build_previews()

        with _preview_server(OUTPUT_DIR) as base_url:
            yangdo_url = f"{base_url}/{YANGDO_PREVIEW.name}"
            permit_url = f"{base_url}/{PERMIT_PREVIEW.name}"
            report["preview_server"] = {"base_url": base_url}
            report["checks"]["yangdo"] = _run_yangdo_smoke(yangdo_url, headless=not args.headful)
            report["checks"]["permit"] = _run_permit_precheck_smoke(permit_url, headless=not args.headful)
    except Exception as exc:  # noqa: BLE001
        report["blocking_issues"].append(str(exc))

    for key in ("yangdo", "permit"):
        row = report.get("checks", {}).get(key) or {}
        if not row.get("ok"):
            report["blocking_issues"].append(f"{key}_smoke_failed")

    report["ok"] = not report["blocking_issues"]
    out_path = Path(str(args.report)).resolve()
    _save_json(out_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
