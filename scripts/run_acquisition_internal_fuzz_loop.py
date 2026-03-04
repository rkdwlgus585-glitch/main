from __future__ import annotations

import argparse
import json
import random
import re
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from selenium import webdriver  # type: ignore
from selenium.webdriver.chrome.options import Options  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.support import expected_conditions as EC  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import acquisition_calculator


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_num(text: str) -> Optional[float]:
    vals = re.findall(r"-?\d+(?:\.\d+)?", str(text or "").replace(",", ""))
    if not vals:
        return None
    try:
        return float(vals[0])
    except Exception:
        return None


def parse_range_eok(text: str) -> Tuple[Optional[float], Optional[float]]:
    vals = re.findall(r"-?\d+(?:\.\d+)?", str(text or "").replace(",", ""))
    if len(vals) < 2:
        return None, None
    try:
        return float(vals[0]), float(vals[1])
    except Exception:
        return None, None


def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)


def set_value_js(driver: webdriver.Chrome, wait: WebDriverWait, element_id: str, value: str) -> None:
    el = wait.until(EC.presence_of_element_located((By.ID, element_id)))
    driver.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));"
        "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
        el,
        str(value),
    )


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args: Any) -> None:  # noqa: D401
        return


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    def handle_error(self, _request: Any, _client_address: Any) -> None:  # noqa: D401
        return


@dataclass
class LocalAcqServer:
    temp_dir: Path
    html_name: str = "acq_fuzz_page.html"
    _server: Optional[QuietThreadingHTTPServer] = None
    _thread: Optional[threading.Thread] = None
    base_url: str = ""

    def start(self) -> None:
        html = acquisition_calculator.build_page_html()
        target = self.temp_dir / self.html_name
        target.write_text(html, encoding="utf-8")

        # Bind ephemeral port on localhost.
        self._server = QuietThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        self._server.timeout = 1.0
        port = int(self._server.server_address[1])
        self.base_url = f"http://127.0.0.1:{port}/{self.html_name}"

        def _run() -> None:
            assert self._server is not None
            cwd = Path.cwd()
            try:
                # Serve from temp_dir.
                import os

                os.chdir(str(self.temp_dir))
                self._server.serve_forever(poll_interval=0.2)
            finally:
                os.chdir(str(cwd))

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        time.sleep(0.15)

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                pass
            try:
                self._server.server_close()
            except Exception:
                pass
        if self._thread is not None:
            try:
                self._thread.join(timeout=1.2)
            except Exception:
                pass


def run_one_cycle(
    cycle_index: int,
    iterations: int,
    seed: int,
    temp_dir: Path,
) -> Dict[str, Any]:
    randomizer = random.Random(seed + (cycle_index * 17))
    anomalies: Dict[str, int] = {}
    ok_count = 0
    sample_rows: List[Dict[str, Any]] = []
    heal_attempts = 0
    recoveries = 0

    def bump(key: str) -> None:
        anomalies[key] = int(anomalies.get(key, 0)) + 1

    def recover_server_and_driver(driver: Optional[webdriver.Chrome], server: LocalAcqServer) -> webdriver.Chrome:
        nonlocal heal_attempts, recoveries
        heal_attempts += 1
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass
        try:
            server.stop()
        except Exception:
            pass
        server.start()
        recoveries += 1
        return build_driver()

    server = LocalAcqServer(temp_dir=temp_dir)
    server.start()
    driver: Optional[webdriver.Chrome] = None
    wait: Optional[WebDriverWait] = None

    region_pool = [
        "서울 강남구 역삼동",
        "서울 중구 을지로",
        "경기 성남시 분당구",
        "부산 해운대구",
        "대구 달서구",
        "인천 연수구",
    ]
    corp_pool = ["new", "existing"]
    override_pool = ["auto", "normal", "surcharge"]

    try:
        driver = build_driver()
        wait = WebDriverWait(driver, 40)
        for idx in range(max(10, int(iterations))):
            case_ok = True
            case_anom: List[str] = []

            try:
                assert driver is not None and wait is not None
                driver.get(server.base_url)
                wait.until(EC.presence_of_element_located((By.ID, "smna-acq-calculator")))

                select = wait.until(EC.presence_of_element_located((By.ID, "acq-license-type")))
                options = [o for o in select.find_elements(By.TAG_NAME, "option") if str(o.get_attribute("value") or "").strip()]
                if not options:
                    bump("no_license_options")
                    continue

                primary = randomizer.choice(options).get_attribute("value")
                set_value_js(driver, wait, "acq-license-type", str(primary))
                set_value_js(driver, wait, "acq-corp-state", randomizer.choice(corp_pool))
                set_value_js(driver, wait, "acq-region-text", randomizer.choice(region_pool))
                set_value_js(driver, wait, "acq-region-override", randomizer.choice(override_pool))

                wait.until(lambda d: (d.find_element(By.ID, "acq-capital").get_attribute("value") or "").strip() != "")
                time.sleep(0.05)

                # Random extra licenses.
                extras = driver.find_elements(By.CSS_SELECTOR, "#acq-license-extra-list input[name='acq-license-extra']")
                randomizer.shuffle(extras)
                pick_count = randomizer.randint(0, min(3, len(extras))) if extras else 0
                for el in extras[:pick_count]:
                    if not el.is_selected():
                        driver.execute_script("arguments[0].click();", el)

                wait.until(EC.element_to_be_clickable((By.ID, "acq-btn-calc"))).click()
                wait.until(lambda d: (d.find_element(By.ID, "acq-out-center").text or "").strip() not in {"", "-"})

                center_text = (driver.find_element(By.ID, "acq-out-center").text or "").strip()
                range_text = (driver.find_element(By.ID, "acq-out-range").text or "").strip()
                conf_text = (driver.find_element(By.ID, "acq-out-confidence").text or "").strip()
                note_text = (driver.find_element(By.ID, "acq-note").text or "").strip()

                center = parse_num(center_text)
                low, high = parse_range_eok(range_text)
                confidence = parse_num(conf_text)

                if center is None or center <= 0:
                    case_ok = False
                    case_anom.append("bad_center")
                if low is None or high is None or low > high:
                    case_ok = False
                    case_anom.append("bad_range")
                if center is not None and low is not None and high is not None and not (low <= center <= high):
                    case_ok = False
                    case_anom.append("center_outside_range")
                if confidence is None or confidence <= 0 or confidence > 100:
                    case_ok = False
                    case_anom.append("bad_confidence")
                if not note_text:
                    case_ok = False
                    case_anom.append("empty_note")

                # Monotonic sanity: guarantee increase should not sharply reduce center.
                if idx % 7 == 0:
                    raw_g = (driver.find_element(By.ID, "acq-guarantee").get_attribute("value") or "0").strip()
                    g0 = parse_num(raw_g) or 0.0
                    g1 = round(g0 + 0.1, 2)
                    set_value_js(driver, wait, "acq-guarantee", f"{g1}")
                    wait.until(EC.element_to_be_clickable((By.ID, "acq-btn-calc"))).click()
                    wait.until(lambda d: (d.find_element(By.ID, "acq-out-center").text or "").strip() not in {"", "-"})
                    center2 = parse_num((driver.find_element(By.ID, "acq-out-center").text or "").strip())
                    if center is not None and center2 is not None and center2 < (center - 0.05):
                        case_ok = False
                        case_anom.append("guarantee_monotonic_violation")

                if not case_ok:
                    for key in case_anom:
                        bump(key)
                else:
                    ok_count += 1

                if idx < 24:
                    sample_rows.append(
                        {
                            "iter": idx + 1,
                            "primary": primary,
                            "extra_count": pick_count,
                            "center": center_text,
                            "range": range_text,
                            "confidence": conf_text,
                            "ok": case_ok,
                            "anomalies": list(case_anom),
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                bump("runtime_exception")
                if idx < 24:
                    sample_rows.append(
                        {
                            "iter": idx + 1,
                            "ok": False,
                            "anomalies": ["runtime_exception"],
                            "error": str(exc),
                        }
                    )
                driver = recover_server_and_driver(driver, server)
                wait = WebDriverWait(driver, 40)
    finally:
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass
        server.stop()

    total = max(1, int(iterations))
    anomaly_events = sum(int(v) for v in anomalies.values())
    return {
        "cycle_index": cycle_index,
        "generated_at": now_iso(),
        "iterations": int(iterations),
        "ok_count": int(ok_count),
        "ok_rate_pct": round((ok_count / total) * 100.0, 3),
        "anomaly_events": int(anomaly_events),
        "anomaly_rate_pct": round((anomaly_events / total) * 100.0, 3),
        "anomaly_counter": anomalies,
        "heal_attempts": heal_attempts,
        "recoveries": recoveries,
        "samples": sample_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal fuzz loop for acquisition calculator (local model / no KR publish).")
    parser.add_argument("--cycles", type=int, default=2)
    parser.add_argument("--iterations-per-cycle", type=int, default=400)
    parser.add_argument("--sleep-sec", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=20260304)
    parser.add_argument("--report", default="logs/acquisition_internal_fuzz_latest.json")
    parser.add_argument("--jsonl", default="logs/acquisition_internal_fuzz_cycles.jsonl")
    args = parser.parse_args()

    report_path = (ROOT / str(args.report)).resolve()
    jsonl_path = (ROOT / str(args.jsonl)).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.time()
    results: List[Dict[str, Any]] = []
    aggregate_anomaly: Dict[str, int] = {}
    total_iterations = 0
    total_ok = 0

    with tempfile.TemporaryDirectory(prefix="acq_fuzz_") as tdir:
        temp_dir = Path(tdir)
        for cycle in range(1, max(1, int(args.cycles)) + 1):
            row = run_one_cycle(
                cycle_index=cycle,
                iterations=max(10, int(args.iterations_per_cycle)),
                seed=int(args.seed),
                temp_dir=temp_dir,
            )
            results.append(row)
            total_iterations += int(row.get("iterations") or 0)
            total_ok += int(row.get("ok_count") or 0)
            for key, val in (row.get("anomaly_counter") or {}).items():
                aggregate_anomaly[str(key)] = int(aggregate_anomaly.get(str(key), 0)) + int(val or 0)
            with jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            if cycle < int(args.cycles):
                time.sleep(max(0.01, float(args.sleep_sec)))

    total_iterations = max(1, total_iterations)
    total_anomaly_events = sum(int(v) for v in aggregate_anomaly.values())
    summary = {
        "generated_at": now_iso(),
        "duration_sec": round(time.time() - started, 2),
        "cycles_done": len(results),
        "totals": {
            "iterations": int(total_iterations),
            "ok_count": int(total_ok),
            "ok_rate_pct": round((total_ok / total_iterations) * 100.0, 3),
            "anomaly_events": int(total_anomaly_events),
            "anomaly_rate_pct": round((total_anomaly_events / total_iterations) * 100.0, 3),
        },
        "aggregate_anomaly_counter": aggregate_anomaly,
        "cycle_results": results[-8:],
    }
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[saved] {report_path}")
    print(json.dumps(summary.get("totals") or {}, ensure_ascii=False))
    print(json.dumps(summary.get("aggregate_anomaly_counter") or {}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
