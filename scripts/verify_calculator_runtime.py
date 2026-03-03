import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests


ROOT = Path(__file__).resolve().parents[1]


def _is_kr_only_mode() -> bool:
    raw = str(os.getenv("SMNA_KR_ONLY_DEV", "")).strip().lower()
    if raw in {"1", "true", "yes", "on", "y"}:
        return True
    return (ROOT / "logs/kr_only_mode.lock").exists()


def _save_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _check_static(url: str, required: List[str], timeout_sec: int = 30) -> Dict:
    out = {
        "kind": "static",
        "url": url,
        "ok": False,
        "status_code": 0,
        "length": 0,
        "found": {},
        "error": "",
    }
    try:
        res = requests.get(url, timeout=timeout_sec)
        txt = res.text or ""
        out["status_code"] = int(res.status_code)
        out["length"] = len(txt)
        for key in required:
            out["found"][key] = key in txt
        out["ok"] = res.status_code == 200 and all(bool(v) for v in out["found"].values())
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
    base = src.split("?", 1)[0].strip()
    tokens = [base, "from=co", f"mode={str(mode or '').strip()}"]
    out: List[str] = []
    for tok in tokens:
        t = str(tok or "").strip()
        if not t or t in out:
            continue
        out.append(t)
    return out


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
                pairs = {
                    "in-license": "철콘",
                    "in-specialty": "10",
                    "in-y23": "5",
                    "in-y24": "6",
                    "in-y25": "7",
                    "in-balance": "0.5",
                    "in-capital": "2",
                    "in-surplus": "1",
                }
                for fid, val in pairs.items():
                    el = wait.until(EC.presence_of_element_located((By.ID, fid)))
                    el.clear()
                    el.send_keys(val)
                wait.until(EC.element_to_be_clickable((By.ID, "btn-estimate"))).click()
                wait.until(lambda d: d.find_element(By.ID, "out-center").text.strip() not in {"", "-"})
                out["center_text"] = driver.find_element(By.ID, "out-center").text.strip()
                out["range_text"] = driver.find_element(By.ID, "out-range").text.strip()
                out["confidence_text"] = driver.find_element(By.ID, "out-confidence").text.strip()
                out["ok"] = bool(out["center_text"]) and out["center_text"] != "-"
                return out

            if mode == "acquisition":
                # Minimal deterministic input set.
                pairs = {
                    "acq-license-type": "전기공사업",
                    "acq-corp-state": "new",
                    "acq-region-text": "서울 강남구",
                    "acq-capital": "1.5",
                    "acq-guarantee-jwasu": "200",
                    "acq-guarantee": "0.6",
                    "acq-engineer-count": "3",
                }
                for fid, val in pairs.items():
                    el = wait.until(EC.presence_of_element_located((By.ID, fid)))
                    tag = (el.tag_name or "").lower()
                    if tag in {"input", "textarea"}:
                        el.clear()
                    el.send_keys(val)
                wait.until(EC.element_to_be_clickable((By.ID, "acq-btn-calc"))).click()
                wait.until(lambda d: d.find_element(By.ID, "acq-out-center").text.strip() not in {"", "-"})
                out["center_text"] = driver.find_element(By.ID, "acq-out-center").text.strip()
                out["range_text"] = driver.find_element(By.ID, "acq-out-range").text.strip()
                out["confidence_text"] = driver.find_element(By.ID, "acq-out-confidence").text.strip()
                out["ok"] = bool(out["center_text"]) and out["center_text"] != "-"
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
    parser.add_argument("--frame-customer", default="https://seoulmna.kr/yangdo-ai-customer/?from=co")
    parser.add_argument("--frame-acquisition", default="https://seoulmna.kr/ai-license-acquisition-calculator/?from=co")
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

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": True,
        "kr_only_mode": bool(kr_only),
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
                    str(args.frame_customer).replace("?from=co", ""),
                    str(args.frame_acquisition).replace("?from=co", ""),
                ],
            )
        )
        report["checks"].append(
            _check_static(
                customer_page,
                [
                    "SEOULMNA GLOBAL BANNER START",
                    "mountCalculatorBridge",
                    "smna-calc-bridge",
                ],
            )
        )
        report["checks"].append(
            _check_static(
                acquisition_page,
                [
                    "SEOULMNA GLOBAL BANNER START",
                    "mountCalculatorBridge",
                    "smna-calc-bridge",
                ],
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
            ["id=\"smna-acq-calculator\"", "id=\"acq-btn-calc\""],
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
                    required=["id=\"acq-btn-calc\"", "id=\"acq-out-center\""],
                )
            )
        else:
            report["checks"].append(
                _check_runtime(
                    chrome_exe=chrome_exe,
                    url=customer_page,
                    required=["id=\"smna-calc-bridge\"", *_runtime_frame_tokens(str(args.frame_customer), "customer")],
                )
            )
            report["checks"].append(
                _check_runtime(
                    chrome_exe=chrome_exe,
                    url=acquisition_page,
                    required=["id=\"smna-calc-bridge\"", *_runtime_frame_tokens(str(args.frame_acquisition), "acquisition")],
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

