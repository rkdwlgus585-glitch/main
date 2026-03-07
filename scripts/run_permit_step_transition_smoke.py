from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from scripts.run_calculator_browser_smoke import (  # type: ignore
        _browser_errors,
        _extract_fragment,
        _preview_server,
        _set_value_js,
        _setup_driver,
        _text,
        _wrap_preview,
    )
except ModuleNotFoundError:
    from run_calculator_browser_smoke import (  # type: ignore
        _browser_errors,
        _extract_fragment,
        _preview_server,
        _set_value_js,
        _setup_driver,
        _text,
        _wrap_preview,
    )

OUTPUT_DIR = ROOT / "output"
LOG_DIR = ROOT / "logs"
PERMIT_OUTPUT = OUTPUT_DIR / "ai_license_acquisition_calculator.html"
PERMIT_PREVIEW = OUTPUT_DIR / "_tmp_permit_step_transition_preview.html"
ARTIFACT_DIR = OUTPUT_DIR / "playwright"
FAIL_SCREENSHOT = ARTIFACT_DIR / "permit_step_transition_failure_latest.png"
FAIL_HTML = ARTIFACT_DIR / "permit_step_transition_failure_latest.html"
DEFAULT_REPORT = LOG_DIR / "permit_step_transition_smoke_latest.json"

EXPECTED_INDUSTRY = "\uC804\uAE30\uACF5\uC0AC\uC5C5"
SEARCH_TEXT = EXPECTED_INDUSTRY
STEP1_TITLE = "\uC5C5\uC885 \uAC80\uC0C9 \uC2DC\uC791"
STEP2_TITLE = "\uC5C5\uC885 \uD655\uC815"
STEP3_TITLE = "\uD604\uC7AC \uBCF4\uC720 \uD604\uD669"
STEP4_TITLE = "\uC120\uD0DD \uC900\uBE44 \uC0C1\uD0DC"
SUMMARY_SELECTED = f"\uC5C5\uC885 {EXPECTED_INDUSTRY}"
SUMMARY_FILLED = "\uD604\uC7AC \uBCF4\uC720 3/3 \uC785\uB825"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_permit_output() -> Dict[str, Any]:
    import permit_diagnosis_calculator

    html = permit_diagnosis_calculator.build_html(
        catalog=permit_diagnosis_calculator._load_catalog(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH),
        rule_catalog=permit_diagnosis_calculator._load_rule_catalog(permit_diagnosis_calculator.DEFAULT_RULES_PATH),
        title="\u0041\u0049 \uC778\uD5C8\uAC00 \uC0AC\uC804\uAC80\uD1A0 \uC9C4\uB2E8\uAE30(\uC2E0\uADDC\uB4F1\uB85D \uC804\uC6A9) | \uC11C\uC6B8\uAC74\uC124\uC815\uBCF4",
    )
    PERMIT_OUTPUT.write_text(html, encoding="utf-8")
    return {
        "path": str(PERMIT_OUTPUT),
        "bytes": PERMIT_OUTPUT.stat().st_size,
    }


def _build_preview() -> Dict[str, Any]:
    permit_html = PERMIT_OUTPUT.read_text(encoding="utf-8", errors="replace")
    fragment = _extract_fragment(permit_html)
    PERMIT_PREVIEW.write_text(_wrap_preview("permit step transition preview", fragment), encoding="utf-8")
    return {
        "path": str(PERMIT_PREVIEW),
        "bytes": PERMIT_PREVIEW.stat().st_size,
    }


def _click(driver, selector: str) -> None:
    driver.execute_script(
        """
const el = document.querySelector(arguments[0]);
if (el && !el.disabled) {
  el.click();
}
        """,
        selector,
    )


def _save_failure_screenshot(driver, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    driver.save_screenshot(str(path))
    return str(path)


def _save_page_source(driver, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(driver.page_source or ""), encoding="utf-8", errors="replace")
    return str(path)


def _clear_artifacts(*paths: Path) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            continue


def _run_step_transition_smoke(page_url: str, headless: bool = True) -> Dict[str, Any]:
    from selenium.webdriver.support.ui import WebDriverWait  # type: ignore

    result: Dict[str, Any] = {
        "page_url": page_url,
        "ok": False,
        "scenario": {
            "focus_mode": "focus_only",
            "search_text": SEARCH_TEXT,
            "expected_industry": EXPECTED_INDUSTRY,
        },
        "output": {},
        "console_errors": [],
        "error": "",
        "artifacts": {},
    }
    driver = _setup_driver(headless=headless)
    try:
        _clear_artifacts(FAIL_SCREENSHOT, FAIL_HTML)
        wait = WebDriverWait(driver, 45)
        driver.get(page_url)

        wizard_exists = bool(
            driver.execute_script("return !!document.getElementById('permitInputWizard') && !!document.getElementById('permitWizardStepTitle');")
        )
        wizard_step_count = int(
            driver.execute_script("return document.querySelectorAll('[data-permit-wizard-track]').length || 0;")
            or 0
        )
        wizard_initial_title = _text(driver, "permitWizardStepTitle")
        wizard_step1_visible = bool(
            driver.execute_script("const el=document.getElementById('permitWizardStep1'); return !!el && el.hidden === false;")
        )

        _click(driver, '[data-focus-mode="focus_only"]')
        _set_value_js(driver, "industrySearchInput", SEARCH_TEXT)
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
        search_seed = EXPECTED_INDUSTRY
        wait.until(
            lambda d: EXPECTED_INDUSTRY in str(
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
        selected_option_text = str(
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
        summary_after_select = str(
            driver.execute_script("const el=document.getElementById('permitWizardSummary'); return el ? (el.innerText || '') : '';")
            or ""
        ).strip()

        _click(driver, '[data-permit-wizard-next="0"]')
        wait.until(lambda d: STEP2_TITLE in _text(d, "permitWizardStepTitle"))
        step2_title = _text(driver, "permitWizardStepTitle")

        _click(driver, '[data-permit-wizard-prev="1"]')
        wait.until(lambda d: STEP1_TITLE in _text(d, "permitWizardStepTitle"))
        back_to_step1_title = _text(driver, "permitWizardStepTitle")

        _click(driver, '[data-permit-wizard-next="0"]')
        wait.until(lambda d: STEP2_TITLE in _text(d, "permitWizardStepTitle"))
        _click(driver, '[data-permit-wizard-next="1"]')
        wait.until(lambda d: STEP3_TITLE in _text(d, "permitWizardStepTitle"))
        step3_title = _text(driver, "permitWizardStepTitle")

        _set_value_js(driver, "capitalInput", "1.5")
        _set_value_js(driver, "technicianInput", "3")
        _set_value_js(driver, "equipmentInput", "1")
        wait.until(
            lambda d: SUMMARY_FILLED in str(
                d.execute_script("const el=document.getElementById('permitWizardSummary'); return el ? (el.innerText || '') : '';") or ""
            )
        )
        summary_after_fill = str(
            driver.execute_script("const el=document.getElementById('permitWizardSummary'); return el ? (el.innerText || '') : '';")
            or ""
        ).strip()

        _click(driver, '[data-permit-wizard-next="2"]')
        wait.until(lambda d: STEP4_TITLE in _text(d, "permitWizardStepTitle"))
        step4_title = _text(driver, "permitWizardStepTitle")

        _click(driver, '[data-permit-wizard-prev="3"]')
        wait.until(lambda d: STEP3_TITLE in _text(d, "permitWizardStepTitle"))
        return_to_step3_title = _text(driver, "permitWizardStepTitle")
        retained_capital = str(driver.execute_script("const el=document.getElementById('capitalInput'); return el ? (el.value || '') : '';" ) or "").strip()
        retained_technician = str(driver.execute_script("const el=document.getElementById('technicianInput'); return el ? (el.value || '') : '';" ) or "").strip()
        retained_equipment = str(driver.execute_script("const el=document.getElementById('equipmentInput'); return el ? (el.value || '') : '';" ) or "").strip()

        _click(driver, '[data-permit-wizard-track="0"]')
        wait.until(lambda d: STEP1_TITLE in _text(d, "permitWizardStepTitle"))
        track_step1_title = _text(driver, "permitWizardStepTitle")
        _click(driver, '[data-permit-wizard-track="3"]')
        wait.until(lambda d: STEP4_TITLE in _text(d, "permitWizardStepTitle"))
        track_step4_title = _text(driver, "permitWizardStepTitle")

        console_errors = _browser_errors(driver)
        result["output"] = {
            "wizard_exists": wizard_exists,
            "wizard_step_count": wizard_step_count,
            "wizard_initial_title": wizard_initial_title,
            "wizard_step1_visible": wizard_step1_visible,
            "first_focus_option_text": first_focus_option_text,
            "search_seed": search_seed,
            "selected_option_text": selected_option_text,
            "summary_after_select": summary_after_select,
            "step2_title": step2_title,
            "back_to_step1_title": back_to_step1_title,
            "step3_title": step3_title,
            "summary_after_fill": summary_after_fill,
            "step4_title": step4_title,
            "return_to_step3_title": return_to_step3_title,
            "retained_capital": retained_capital,
            "retained_technician": retained_technician,
            "retained_equipment": retained_equipment,
            "track_step1_title": track_step1_title,
            "track_step4_title": track_step4_title,
        }
        result["console_errors"] = console_errors
        result["ok"] = (
            wizard_exists
            and wizard_step_count >= 4
            and "STEP 1" in wizard_initial_title
            and wizard_step1_visible
            and EXPECTED_INDUSTRY in selected_option_text
            and SUMMARY_SELECTED in summary_after_select
            and STEP2_TITLE in step2_title
            and STEP1_TITLE in back_to_step1_title
            and STEP3_TITLE in step3_title
            and SUMMARY_FILLED in summary_after_fill
            and STEP4_TITLE in step4_title
            and STEP3_TITLE in return_to_step3_title
            and retained_capital == "1.5"
            and retained_technician == "3"
            and retained_equipment == "1"
            and STEP1_TITLE in track_step1_title
            and STEP4_TITLE in track_step4_title
            and not console_errors
        )
        if not result["ok"]:
            result["artifacts"]["failure_screenshot"] = _save_failure_screenshot(driver, FAIL_SCREENSHOT)
            result["artifacts"]["failure_html"] = _save_page_source(driver, FAIL_HTML)
        return result
    except Exception as exc:  # noqa: BLE001
        result["console_errors"] = _browser_errors(driver)
        result["error"] = f"{type(exc).__name__}: {exc}"
        try:
            result["artifacts"]["failure_screenshot"] = _save_failure_screenshot(driver, FAIL_SCREENSHOT)
            result["artifacts"]["failure_html"] = _save_page_source(driver, FAIL_HTML)
        except Exception:
            pass
        return result
    finally:
        driver.quit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a focused browser smoke for permit wizard next/prev step transitions")
    parser.add_argument("--skip-build", action="store_true", default=False)
    parser.add_argument("--headful", action="store_true", default=False)
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    report: Dict[str, Any] = {
        "generated_at": _now(),
        "ok": False,
        "rebuilt": {},
        "preview": {},
        "check": {},
        "blocking_issues": [],
    }

    try:
        if not args.skip_build:
            report["rebuilt"] = _build_permit_output()
        report["preview"] = _build_preview()
        with _preview_server(OUTPUT_DIR) as base_url:
            page_url = f"{base_url}/{PERMIT_PREVIEW.name}"
            report["check"] = _run_step_transition_smoke(page_url, headless=not args.headful)
            report["preview_server"] = {"base_url": base_url}
        if not bool((report.get("check") or {}).get("ok")):
            report["blocking_issues"] = [
                str((report.get("check") or {}).get("error") or "permit_step_transition_failed")
            ]
    except Exception as exc:  # noqa: BLE001
        report["blocking_issues"] = [str(exc)]

    report["ok"] = not report["blocking_issues"]
    out_path = Path(str(args.report)).resolve()
    _save_json(out_path, report)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    try:
        sys.stdout.write(rendered)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(rendered.encode("utf-8", errors="replace"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
