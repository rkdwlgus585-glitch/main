import argparse
import json
import random
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from selenium import webdriver  # type: ignore
from selenium.webdriver.chrome.options import Options  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.support import expected_conditions as EC  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore


ROOT = Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_eok(text: str) -> Optional[float]:
    s = str(text or "").replace(",", "").strip()
    m = re.search(r"(-?\d+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def parse_range_eok(text: str) -> Tuple[Optional[float], Optional[float]]:
    s = str(text or "").replace(",", " ").strip()
    vals = re.findall(r"-?\d+(?:\.\d+)?", s)
    if len(vals) < 2:
        return None, None
    try:
        return float(vals[0]), float(vals[1])
    except Exception:
        return None, None


def parse_percent(text: str) -> Optional[float]:
    s = str(text or "").strip().replace(",", "")
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*%", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def parse_manwon(text: str) -> Optional[float]:
    s = str(text or "").replace(",", "").strip()
    m = re.search(r"(-?\d+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def extract_amount_by_label(text: str, label: str, unit: str) -> Optional[float]:
    raw = str(text or "")
    key = re.escape(str(label or "").strip())
    if not key:
        return None
    m = re.search(key + r"[^\d-]*(-?\d[\d,]*(?:\.\d+)?)", raw)
    if not m:
        return None
    try:
        return float(str(m.group(1)).replace(",", ""))
    except Exception:
        return None


def setup_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
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
        value,
    )


def get_text(driver: webdriver.Chrome, element_id: str) -> str:
    try:
        return str(driver.find_element(By.ID, element_id).text or "").strip()
    except Exception:
        return ""


@dataclass
class AdaptivePolicy:
    """Simple adaptive pilot policy based on observed anomalies."""

    high_balance_stress_weight: float = 0.20
    custom_name_weight: float = 0.25
    anomaly_counts: Dict[str, int] = field(default_factory=dict)

    def bump(self, key: str) -> None:
        self.anomaly_counts[key] = int(self.anomaly_counts.get(key, 0)) + 1
        if key == "yangdo_center_too_high":
            self.high_balance_stress_weight = min(0.65, self.high_balance_stress_weight + 0.08)
        if key == "acq_preset_not_applied":
            self.custom_name_weight = min(0.65, self.custom_name_weight + 0.08)


@dataclass
class PilotEvent:
    pilot: str
    ts: str
    ok: bool
    anomalies: List[str]
    input_payload: Dict
    output_payload: Dict
    error: str = ""

    def to_dict(self) -> Dict:
        return {
            "pilot": self.pilot,
            "ts": self.ts,
            "ok": self.ok,
            "anomalies": list(self.anomalies),
            "input_payload": self.input_payload,
            "output_payload": self.output_payload,
            "error": self.error,
        }


class YangdoPilot:
    def __init__(self, url: str, policy: AdaptivePolicy, headless: bool = True):
        self.url = url
        self.policy = policy
        self.headless = bool(headless)
        self.driver = setup_driver(headless=self.headless)
        self.wait = WebDriverWait(self.driver, 45)
        self.random = random.Random()
        self.licenses = ["전기", "토목", "건축", "실내건축", "상하수도", "철근콘크리트", "정보통신"]

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass

    def recover(self) -> None:
        self.close()
        self.driver = setup_driver(headless=self.headless)
        self.wait = WebDriverWait(self.driver, 45)

    def _make_case(self) -> Dict:
        lic = self.random.choice(self.licenses)
        sales_mode = self.random.choices(["yearly", "sales3", "sales5"], weights=[0.56, 0.28, 0.16], k=1)[0]
        specialty = round(self.random.uniform(5, 90), 1)
        base = max(0.2, specialty * self.random.uniform(0.20, 0.65))
        y23 = round(base * self.random.uniform(0.6, 1.0), 1)
        y24 = round(base * self.random.uniform(0.8, 1.3), 1)
        y25 = round(base * self.random.uniform(0.85, 1.35), 1)
        sales3 = round(max(0.1, y23 + y24 + y25), 1)
        sales5 = round(sales3 * self.random.uniform(1.45, 1.85), 1)
        balance = round(self.random.uniform(0.2, 6.5), 2)
        if self.random.random() < self.policy.high_balance_stress_weight:
            # Inject a probable unit typo stress case.
            balance = round(balance * self.random.choice([100, 1000]), 2)
        return {
            "license": lic,
            "sales_mode": sales_mode,
            "specialty": specialty,
            "y23": y23,
            "y24": y24,
            "y25": y25,
            "sales3": sales3,
            "sales5": sales5,
            "balance": balance,
            "capital": round(self.random.uniform(0.8, 3.0), 2),
            "surplus": round(self.random.uniform(-0.3, 6.0), 2),
            "company_type": self.random.choice(["주식회사", "유한회사", "개인"]),
            "credit_level": self.random.choice(["high", "mid", "low"]),
            "admin_history": self.random.choice(["none", "has"]),
            "debt_level": self.random.choice(["auto", "below", "above"]),
            "liq_level": self.random.choice(["auto", "above", "below"]),
        }

    def run_once(self) -> PilotEvent:
        payload = self._make_case()
        anomalies: List[str] = []
        try:
            self.driver.get(self.url)
            set_value_js(self.driver, self.wait, "in-license", str(payload["license"]))
            set_value_js(self.driver, self.wait, "in-specialty", str(payload["specialty"]))
            set_value_js(self.driver, self.wait, "in-sales-input-mode", str(payload["sales_mode"]))
            set_value_js(self.driver, self.wait, "in-y23", str(payload["y23"]))
            set_value_js(self.driver, self.wait, "in-y24", str(payload["y24"]))
            set_value_js(self.driver, self.wait, "in-y25", str(payload["y25"]))
            set_value_js(self.driver, self.wait, "in-sales3-total", str(payload["sales3"]))
            set_value_js(self.driver, self.wait, "in-sales5-total", str(payload["sales5"]))
            set_value_js(self.driver, self.wait, "in-balance", str(payload["balance"]))
            set_value_js(self.driver, self.wait, "in-capital", str(payload["capital"]))
            set_value_js(self.driver, self.wait, "in-surplus", str(payload["surplus"]))
            set_value_js(self.driver, self.wait, "in-company-type", str(payload["company_type"]))
            set_value_js(self.driver, self.wait, "in-credit-level", str(payload["credit_level"]))
            set_value_js(self.driver, self.wait, "in-admin-history", str(payload["admin_history"]))
            set_value_js(self.driver, self.wait, "in-debt-level", str(payload["debt_level"]))
            set_value_js(self.driver, self.wait, "in-liq-level", str(payload["liq_level"]))

            btn = self.wait.until(EC.element_to_be_clickable((By.ID, "btn-estimate")))
            btn.click()
            self.wait.until(lambda d: get_text(d, "out-center") not in {"", "-"})

            center_text = get_text(self.driver, "out-center")
            range_text = get_text(self.driver, "out-range")
            confidence_text = get_text(self.driver, "out-confidence")
            neighbors_text = get_text(self.driver, "out-neighbors")
            risk_text = get_text(self.driver, "risk-note")

            center = parse_eok(center_text)
            low, high = parse_range_eok(range_text)
            confidence = parse_percent(confidence_text)
            neighbors = int(re.sub(r"\D+", "", neighbors_text) or "0")

            if center is None or center <= 0:
                anomalies.append("yangdo_no_center")
            if low is None or high is None or low > high:
                anomalies.append("yangdo_bad_range")
            if confidence is None:
                anomalies.append("yangdo_no_confidence")
            if neighbors <= 0:
                anomalies.append("yangdo_no_neighbors")
            if center is not None and high is not None and center > (high * 1.15):
                anomalies.append("yangdo_center_over_high_bound")
            if center is not None and center > 30:
                anomalies.append("yangdo_center_too_high")

            for a in anomalies:
                self.policy.bump(a)

            return PilotEvent(
                pilot="yangdo",
                ts=now_iso(),
                ok=(len(anomalies) == 0),
                anomalies=anomalies,
                input_payload=payload,
                output_payload={
                    "center": center_text,
                    "range": range_text,
                    "confidence": confidence_text,
                    "neighbors": neighbors_text,
                    "risk_note": risk_text,
                },
            )
        except Exception as e:  # noqa: BLE001
            return PilotEvent(
                pilot="yangdo",
                ts=now_iso(),
                ok=False,
                anomalies=["yangdo_runtime_exception"],
                input_payload=payload,
                output_payload={},
                error=str(e),
            )


class AcquisitionPilot:
    def __init__(self, url: str, policy: AdaptivePolicy, headless: bool = True):
        self.url = url
        self.policy = policy
        self.headless = bool(headless)
        self.driver = setup_driver(headless=self.headless)
        self.wait = WebDriverWait(self.driver, 45)
        self.random = random.Random()

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass

    def recover(self) -> None:
        self.close()
        self.driver = setup_driver(headless=self.headless)
        self.wait = WebDriverWait(self.driver, 45)

    def _pick_license_index(self) -> int:
        # index 0 is empty "?? ??"
        return self.random.randint(1, 13)

    def run_once(self) -> PilotEvent:
        anomalies: List[str] = []
        payload: Dict = {}
        try:
            self.driver.get(self.url)
            sel = self.wait.until(EC.presence_of_element_located((By.ID, "acq-license-type")))
            idx = self._pick_license_index()
            self.driver.execute_script(
                "arguments[0].selectedIndex = arguments[1];"
                "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
                sel,
                idx,
            )
            selected = str(sel.get_attribute("value") or "").strip()

            # Adaptive custom-name stress to validate fuzzy profile match.
            use_custom = self.random.random() < self.policy.custom_name_weight
            custom_name = ""
            if use_custom:
                custom_name = self.random.choice(["????", "??", "????", "??", "????"])
                set_value_js(self.driver, self.wait, "acq-license-custom", custom_name)

            set_value_js(self.driver, self.wait, "acq-corp-state", self.random.choice(["new", "existing"]))
            set_value_js(
                self.driver,
                self.wait,
                "acq-region-text",
                self.random.choice(["?? ??? ???", "?? ??? ???", "?? ??? ???", "?? ??? ???"]),
            )
            set_value_js(self.driver, self.wait, "acq-region-override", self.random.choice(["auto", "normal", "surcharge"]))

            # Wait preset sync after license selection.
            self.wait.until(lambda d: (d.find_element(By.ID, "acq-capital").get_attribute("value") or "").strip() != "")

            cap = self.wait.until(EC.presence_of_element_located((By.ID, "acq-capital"))).get_attribute("value") or ""
            gw = self.driver.find_element(By.ID, "acq-guarantee").get_attribute("value") or ""
            eng = self.driver.find_element(By.ID, "acq-engineer-count").get_attribute("value") or ""

            payload = {
                "selected_index": idx,
                "selected_license": selected,
                "custom_name": custom_name,
                "preset_capital": cap,
                "preset_guarantee": gw,
                "preset_engineer": eng,
            }

            if not cap or not gw or not eng:
                anomalies.append("acq_preset_not_applied")

            # Add realistic manual overrides around presets.
            try:
                cap_f = float(cap) if cap else 1.5
            except Exception:
                cap_f = 1.5
            try:
                gw_f = float(gw) if gw else 0.54
            except Exception:
                gw_f = 0.54
            try:
                eng_i = int(float(eng)) if eng else 2
            except Exception:
                eng_i = 2

            set_value_js(self.driver, self.wait, "acq-capital", str(round(max(0.5, cap_f * self.random.uniform(0.9, 1.15)), 2)))
            set_value_js(self.driver, self.wait, "acq-guarantee", str(round(max(0.1, gw_f * self.random.uniform(0.85, 1.2)), 2)))
            set_value_js(self.driver, self.wait, "acq-engineer-count", str(max(1, int(round(eng_i * self.random.uniform(0.8, 1.3))))))

            btn = self.wait.until(EC.element_to_be_clickable((By.ID, "acq-btn-calc")))
            btn.click()
            self.wait.until(lambda d: get_text(d, "acq-out-center") not in {"", "-"})

            center_text = get_text(self.driver, "acq-out-center")
            range_text = get_text(self.driver, "acq-out-range")
            ready_text = get_text(self.driver, "acq-out-ready")
            confidence_text = get_text(self.driver, "acq-out-confidence")
            breakdown_text = get_text(self.driver, "acq-breakdown")

            center = parse_eok(center_text)
            low, high = parse_range_eok(range_text)
            ready = parse_eok(ready_text)
            confidence = parse_percent(confidence_text)

            if center is None or center <= 0:
                anomalies.append("acq_no_center")
            if low is None or high is None or low > high:
                anomalies.append("acq_bad_range")
            if ready is None or center is None or ready < center:
                anomalies.append("acq_bad_ready_fund")
            if confidence is None:
                anomalies.append("acq_no_confidence")

            # Breakdown copy varies by view mode; skip strict text matching in behavior pilot.

            # Consistency checks from rendered breakdown labels.
            try:
                direct_cost = extract_amount_by_label(breakdown_text, "??? ??(???? ??)", "?")
                total_center = extract_amount_by_label(breakdown_text, "? ????(??)", "?")
                fees_sum = extract_amount_by_label(breakdown_text, "??/??? ??", "??")
                pro_sum = extract_amount_by_label(breakdown_text, "??? ??? ??", "??")
                if center is not None and total_center is not None and abs(float(center) - float(total_center)) > 0.05:
                    anomalies.append("acq_total_center_mismatch")
                if center is not None and direct_cost is not None and float(direct_cost) > float(center):
                    anomalies.append("acq_direct_cost_gt_total")
                if fees_sum is not None and pro_sum is not None and (float(fees_sum) < 0 or float(pro_sum) < 0):
                    anomalies.append("acq_negative_group_sum")
            except Exception:
                anomalies.append("acq_center_consistency_parse_fail")

            for a in anomalies:
                self.policy.bump(a)

            return PilotEvent(
                pilot="acquisition",
                ts=now_iso(),
                ok=(len(anomalies) == 0),
                anomalies=anomalies,
                input_payload=payload,
                output_payload={
                    "center": center_text,
                    "range": range_text,
                    "ready": ready_text,
                    "confidence": confidence_text,
                },
            )
        except Exception as e:  # noqa: BLE001
            return PilotEvent(
                pilot="acquisition",
                ts=now_iso(),
                ok=False,
                anomalies=["acq_runtime_exception"],
                input_payload=payload,
                output_payload={},
                error=str(e),
            )


def run_loop(
    duration_sec: int,
    yangdo_url: str,
    acq_url: str,
    event_jsonl: Path,
    sleep_sec: float,
    headless: bool = True,
) -> Dict:
    started = time.time()
    deadline = started + duration_sec
    policy = AdaptivePolicy()
    lock = threading.Lock()
    events: List[Dict] = []

    yangdo = YangdoPilot(yangdo_url, policy=policy, headless=headless)
    acq = AcquisitionPilot(acq_url, policy=policy, headless=headless)

    event_jsonl.parent.mkdir(parents=True, exist_ok=True)
    event_jsonl.write_text("", encoding="utf-8")

    try:
        while time.time() < deadline:
            for pilot in (yangdo, acq):
                evt = pilot.run_once().to_dict()
                anomalies = list(evt.get("anomalies") or [])
                runtime_failed = any(str(x).endswith("runtime_exception") for x in anomalies)
                if runtime_failed:
                    try:
                        pilot.recover()
                        evt = pilot.run_once().to_dict()
                        evt["retry_after_runtime_exception"] = True
                    except Exception as e:  # noqa: BLE001
                        evt["recovery_error"] = str(e)
                with lock:
                    events.append(evt)
                    with event_jsonl.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(evt, ensure_ascii=False) + "\n")
                # brief spacing between pilots
                time.sleep(0.6)
                if time.time() >= deadline:
                    break
            time.sleep(max(0.1, float(sleep_sec)))
    finally:
        yangdo.close()
        acq.close()

    total = len(events)
    ok_count = sum(1 for x in events if bool(x.get("ok")))
    fail_count = total - ok_count
    by_pilot: Dict[str, Dict] = {"yangdo": {"total": 0, "ok": 0, "fail": 0}, "acquisition": {"total": 0, "ok": 0, "fail": 0}}
    anomaly_counter: Dict[str, int] = {}
    for e in events:
        p = str(e.get("pilot") or "")
        if p not in by_pilot:
            by_pilot[p] = {"total": 0, "ok": 0, "fail": 0}
        by_pilot[p]["total"] += 1
        if bool(e.get("ok")):
            by_pilot[p]["ok"] += 1
        else:
            by_pilot[p]["fail"] += 1
        for a in list(e.get("anomalies") or []):
            anomaly_counter[a] = int(anomaly_counter.get(a, 0)) + 1

    summary = {
        "generated_at": now_iso(),
        "duration_sec": int(time.time() - started),
        "configured_duration_sec": int(duration_sec),
        "total_events": total,
        "ok_events": ok_count,
        "fail_events": fail_count,
        "ok_rate": round((ok_count / total) * 100, 2) if total else 0.0,
        "by_pilot": by_pilot,
        "anomaly_counter": dict(sorted(anomaly_counter.items(), key=lambda kv: (-kv[1], kv[0]))),
        "adaptive_policy": {
            "high_balance_stress_weight": round(policy.high_balance_stress_weight, 4),
            "custom_name_weight": round(policy.custom_name_weight, 4),
            "anomaly_counts": dict(policy.anomaly_counts),
        },
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 2 pilot agents for calculator behavior verification")
    parser.add_argument("--yangdo-url", default="https://seoulmna.kr/yangdo-ai-customer/?from=co")
    parser.add_argument("--acq-url", default="https://seoulmna.kr/ai-license-acquisition-calculator/?from=co")
    parser.add_argument("--duration-minutes", type=int, default=60)
    parser.add_argument("--sleep-sec", type=float, default=2.0)
    parser.add_argument("--report", default="logs/calculator_behavior_pilot_latest.json")
    parser.add_argument("--events", default="logs/calculator_behavior_pilot_events_latest.jsonl")
    parser.add_argument("--no-headless", action="store_true")
    args = parser.parse_args()

    duration_sec = max(60, int(args.duration_minutes) * 60)
    report_path = (ROOT / str(args.report)).resolve()
    events_path = (ROOT / str(args.events)).resolve()

    summary = run_loop(
        duration_sec=duration_sec,
        yangdo_url=str(args.yangdo_url).strip(),
        acq_url=str(args.acq_url).strip(),
        event_jsonl=events_path,
        sleep_sec=float(args.sleep_sec),
        headless=not bool(args.no_headless),
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[saved] {report_path}")
    print(f"[events] {events_path}")
    print(f"[duration_sec] {summary.get('duration_sec')}")
    print(f"[total] {summary.get('total_events')} ok={summary.get('ok_events')} fail={summary.get('fail_events')}")
    print(f"[ok_rate] {summary.get('ok_rate')}%")
    top = list((summary.get("anomaly_counter") or {}).items())[:8]
    for k, v in top:
        print(f"- anomaly {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
