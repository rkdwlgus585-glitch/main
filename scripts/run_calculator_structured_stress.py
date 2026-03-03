import argparse
import json
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from selenium import webdriver  # type: ignore
from selenium.webdriver.chrome.options import Options  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.support import expected_conditions as EC  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore


ROOT = Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _nums(text: str) -> List[float]:
    values = re.findall(r"-?\d+(?:\.\d+)?", str(text or "").replace(",", ""))
    out: List[float] = []
    for value in values:
        try:
            out.append(float(value))
        except Exception:
            continue
    return out


def _parse_center(text: str) -> Optional[float]:
    vals = _nums(text)
    return vals[0] if vals else None


def _parse_range(text: str) -> Tuple[Optional[float], Optional[float]]:
    vals = _nums(text)
    if len(vals) < 2:
        return None, None
    return vals[0], vals[1]


def _setup_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)


def _set_value_js(driver: webdriver.Chrome, wait: WebDriverWait, element_id: str, value: str) -> None:
    el = wait.until(EC.presence_of_element_located((By.ID, element_id)))
    driver.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));"
        "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
        el,
        value,
    )


def _run_yangdo(yangdo_url: str, iterations: int) -> Dict:
    random.seed()
    driver = _setup_driver()
    wait = WebDriverWait(driver, 35)
    licenses = ["전기", "토목", "건축", "실내건축", "상하수도", "철근콘크리트", "정보통신"]
    sales_modes = ["yearly", "sales3", "sales5"]
    anomalies: Dict[str, int] = {}
    sample_cases: List[Dict] = []

    def bump(key: str) -> None:
        anomalies[key] = int(anomalies.get(key, 0)) + 1

    try:
        for idx in range(iterations):
            driver.get(yangdo_url)
            license_name = random.choice(licenses)
            specialty = round(random.uniform(3, 90), 1)
            y23 = round(random.uniform(0.3, 40), 1)
            y24 = round(random.uniform(0.3, 45), 1)
            y25 = round(random.uniform(0.3, 50), 1)
            sales3 = round(y23 + y24 + y25, 1)
            sales5 = round(sales3 * random.uniform(1.2, 2.2), 1)
            balance = round(random.uniform(0.2, 8.0), 2)
            if random.random() < 0.12:
                balance = round(balance * random.choice([100, 1000]), 2)
            capital = round(random.uniform(0.8, 4.0), 2)
            surplus = round(random.uniform(-0.5, 8.0), 2)

            _set_value_js(driver, wait, "in-license", license_name)
            _set_value_js(driver, wait, "in-specialty", str(specialty))
            _set_value_js(driver, wait, "in-sales-input-mode", random.choice(sales_modes))
            _set_value_js(driver, wait, "in-y23", str(y23))
            _set_value_js(driver, wait, "in-y24", str(y24))
            _set_value_js(driver, wait, "in-y25", str(y25))
            _set_value_js(driver, wait, "in-sales3-total", str(sales3))
            _set_value_js(driver, wait, "in-sales5-total", str(sales5))
            _set_value_js(driver, wait, "in-balance", str(balance))
            _set_value_js(driver, wait, "in-capital", str(capital))
            _set_value_js(driver, wait, "in-surplus", str(surplus))
            _set_value_js(driver, wait, "in-company-type", random.choice(["주식회사", "유한회사", "개인"]))
            _set_value_js(driver, wait, "in-credit-level", random.choice(["high", "mid", "low"]))
            _set_value_js(driver, wait, "in-admin-history", random.choice(["none", "has"]))
            _set_value_js(driver, wait, "in-debt-level", random.choice(["auto", "below", "above"]))
            _set_value_js(driver, wait, "in-liq-level", random.choice(["auto", "above", "below"]))

            wait.until(EC.element_to_be_clickable((By.ID, "btn-estimate"))).click()
            wait.until(lambda d: (d.find_element(By.ID, "out-center").text or "").strip() not in {"", "-"})

            center_text = (driver.find_element(By.ID, "out-center").text or "").strip()
            range_text = (driver.find_element(By.ID, "out-range").text or "").strip()
            confidence_text = (driver.find_element(By.ID, "out-confidence").text or "").strip()
            neighbors_text = (driver.find_element(By.ID, "out-neighbors").text or "").strip()

            center = _parse_center(center_text)
            low, high = _parse_range(range_text)
            conf = _parse_center(confidence_text)
            neighbors = int(re.sub(r"\D+", "", neighbors_text) or "0")

            if center is None or center <= 0:
                bump("bad_center")
            if low is None or high is None or low > high:
                bump("bad_range")
            if center is not None and low is not None and high is not None and not (low <= center <= high):
                bump("center_outside")
            if conf is None or conf <= 0 or conf > 100:
                bump("bad_confidence")
            if neighbors <= 0:
                bump("no_neighbors")

            if idx < 40:
                sample_cases.append(
                    {
                        "iter": idx + 1,
                        "license": license_name,
                        "center": center_text,
                        "range": range_text,
                        "confidence": confidence_text,
                        "neighbors": neighbors_text,
                    }
                )
    finally:
        driver.quit()

    return {
        "iterations": iterations,
        "anomaly_counter": anomalies,
        "sample_cases": sample_cases,
    }


def _run_acquisition(acq_url: str, iterations: int) -> Dict:
    random.seed()
    driver = _setup_driver()
    wait = WebDriverWait(driver, 35)
    anomalies: Dict[str, int] = {}
    sample_cases: List[Dict] = []

    def bump(key: str) -> None:
        anomalies[key] = int(anomalies.get(key, 0)) + 1

    try:
        for idx in range(iterations):
            driver.get(acq_url)
            select = wait.until(EC.presence_of_element_located((By.ID, "acq-license-type")))
            options = [o for o in select.find_elements(By.TAG_NAME, "option") if str(o.get_attribute("value") or "").strip()]
            if not options:
                bump("no_license_options")
                continue
            primary = random.choice(options).get_attribute("value")
            driver.execute_script(
                "arguments[0].value = arguments[1];"
                "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
                select,
                primary,
            )
            _set_value_js(driver, wait, "acq-corp-state", random.choice(["new", "existing"]))
            _set_value_js(driver, wait, "acq-region-text", random.choice(["?? ??? ???", "?? ??? ???", "?? ??? ???", "?? ??? ???"]))
            _set_value_js(driver, wait, "acq-region-override", random.choice(["auto", "normal", "surcharge"]))

            # Wait for preset values to sync after license change.
            wait.until(lambda d: (d.find_element(By.ID, "acq-capital").get_attribute("value") or "").strip() != "")
            time.sleep(0.08)

            # baseline: single-license
            for el in driver.find_elements(By.CSS_SELECTOR, "#acq-license-extra-list input[name='acq-license-extra']:checked"):
                driver.execute_script("arguments[0].click();", el)
            wait.until(EC.element_to_be_clickable((By.ID, "acq-btn-calc"))).click()
            wait.until(lambda d: (d.find_element(By.ID, "acq-out-center").text or "").strip() not in {"", "-"})
            center_single_text = (driver.find_element(By.ID, "acq-out-center").text or "").strip()
            range_single_text = (driver.find_element(By.ID, "acq-out-range").text or "").strip()
            center_single = _parse_center(center_single_text)
            low_single, high_single = _parse_range(range_single_text)

            if center_single is None or center_single <= 0:
                bump("single_bad_center")
            if low_single is None or high_single is None or low_single > high_single:
                bump("single_bad_range")
            if center_single is not None and low_single is not None and high_single is not None and not (low_single <= center_single <= high_single):
                bump("single_center_outside")

            major_inputs = driver.find_elements(By.CSS_SELECTOR, "#acq-major-field-list input[name='acq-major-field']")
            eng_one = None
            eng_all = None
            if len(major_inputs) >= 2:
                for el in major_inputs:
                    if el.is_selected():
                        driver.execute_script("arguments[0].click();", el)
                driver.execute_script("arguments[0].click();", major_inputs[0])
                time.sleep(0.05)
                eng_one = float(driver.find_element(By.ID, "acq-engineer-count").get_attribute("value") or "0")
                for el in major_inputs[1:]:
                    if not el.is_selected():
                        driver.execute_script("arguments[0].click();", el)
                time.sleep(0.05)
                eng_all = float(driver.find_element(By.ID, "acq-engineer-count").get_attribute("value") or "0")
                if eng_all + 1e-9 < eng_one:
                    bump("major_engineer_direction_bad")

            # multi-license
            extra_inputs = driver.find_elements(By.CSS_SELECTOR, "#acq-license-extra-list input[name='acq-license-extra']")
            random.shuffle(extra_inputs)
            pick = random.randint(1, min(3, len(extra_inputs))) if extra_inputs else 0
            picked: List[str] = []
            for el in extra_inputs[:pick]:
                if not el.is_selected():
                    driver.execute_script("arguments[0].click();", el)
                    picked.append(str(el.get_attribute("value") or "").strip())
            time.sleep(0.08)
            wait.until(EC.element_to_be_clickable((By.ID, "acq-btn-calc"))).click()
            wait.until(lambda d: (d.find_element(By.ID, "acq-out-center").text or "").strip() not in {"", "-"})
            center_multi_text = (driver.find_element(By.ID, "acq-out-center").text or "").strip()
            range_multi_text = (driver.find_element(By.ID, "acq-out-range").text or "").strip()
            center_multi = _parse_center(center_multi_text)
            low_multi, high_multi = _parse_range(range_multi_text)

            if center_multi is None or center_multi <= 0:
                bump("multi_bad_center")
            if low_multi is None or high_multi is None or low_multi > high_multi:
                bump("multi_bad_range")
            if center_multi is not None and low_multi is not None and high_multi is not None and not (low_multi <= center_multi <= high_multi):
                bump("multi_center_outside")
            if center_single is not None and center_multi is not None and pick > 0 and center_multi < (center_single * 0.92):
                bump("multi_unexpected_drop")

            if idx < 40:
                sample_cases.append(
                    {
                        "iter": idx + 1,
                        "primary": primary,
                        "extra_picked": picked,
                        "single_center": center_single_text,
                        "single_range": range_single_text,
                        "multi_center": center_multi_text,
                        "multi_range": range_multi_text,
                        "major_engineers_one": eng_one,
                        "major_engineers_all": eng_all,
                    }
                )
    finally:
        driver.quit()

    return {
        "iterations": iterations,
        "anomaly_counter": anomalies,
        "sample_cases": sample_cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Structured stress test for Yangdo + Acquisition calculators")
    parser.add_argument("--yangdo-url", default="https://seoulmna.kr/yangdo-ai-customer/?from=co")
    parser.add_argument("--acq-url", default="https://seoulmna.kr/ai-license-acquisition-calculator/?from=co")
    parser.add_argument("--yangdo-iterations", type=int, default=120)
    parser.add_argument("--acq-iterations", type=int, default=120)
    parser.add_argument("--report", default="logs/calculator_structured_stress_latest.json")
    args = parser.parse_args()

    report_path = (ROOT / str(args.report)).resolve()
    started = time.time()
    yangdo = _run_yangdo(str(args.yangdo_url).strip(), max(10, int(args.yangdo_iterations)))
    acq = _run_acquisition(str(args.acq_url).strip(), max(10, int(args.acq_iterations)))
    summary = {
        "generated_at": _now(),
        "duration_sec": round(time.time() - started, 2),
        "yangdo": yangdo,
        "acquisition": acq,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[saved] {report_path}")
    print("[yangdo_anomaly_counter]", json.dumps(yangdo.get("anomaly_counter") or {}, ensure_ascii=False))
    print("[acq_anomaly_counter]", json.dumps(acq.get("anomaly_counter") or {}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
