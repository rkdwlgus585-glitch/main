import argparse
import json
import locale
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _py_cmd(args: List[str]) -> List[str]:
    if shutil.which("py"):
        return ["py", "-3", *args]
    return [sys.executable, *args]


def _decode_best(data: bytes) -> str:
    if not data:
        return ""
    pref = locale.getpreferredencoding(False) or "utf-8"
    candidates = []
    seen = set()
    for enc in (pref, "utf-8", "utf-8-sig", "cp949", "euc-kr"):
        key = (enc or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        candidates.append(enc)
    best_txt = ""
    best_score = None
    for enc in candidates:
        try:
            txt = data.decode(enc, errors="replace")
        except LookupError:
            continue
        score = txt.count("\ufffd")
        if best_score is None or score < best_score:
            best_txt = txt
            best_score = score
            if score == 0:
                break
    return best_txt


def _tail(text: str, max_lines: int = 60) -> str:
    lines = (text or "").splitlines()
    if len(lines) <= max_lines:
        return text or ""
    return "\n".join(lines[-max_lines:])


def _run_step(name: str, cmd: List[str], timeout_sec: int = 300) -> Dict[str, Any]:
    started = time.time()
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=False,
            env=env,
            timeout=timeout_sec,
        )
        out = _decode_best(proc.stdout or b"")
        err = _decode_best(proc.stderr or b"")
        rc = int(proc.returncode)
        return {
            "name": name,
            "ok": rc == 0,
            "returncode": rc,
            "duration_sec": round(time.time() - started, 2),
            "command": cmd,
            "stdout_tail": _tail(out),
            "stderr_tail": _tail(err),
        }
    except subprocess.TimeoutExpired as exc:
        out = _decode_best((exc.stdout or b"") if isinstance(exc.stdout, (bytes, bytearray)) else b"")
        err = _decode_best((exc.stderr or b"") if isinstance(exc.stderr, (bytes, bytearray)) else b"")
        return {
            "name": name,
            "ok": False,
            "returncode": 124,
            "duration_sec": round(time.time() - started, 2),
            "command": cmd,
            "stdout_tail": _tail(out),
            "stderr_tail": _tail(err),
            "timed_out": True,
        }


def _parse_publish_url(step: Dict[str, Any]) -> str:
    text = f"{step.get('stdout_tail','')}\n{step.get('stderr_tail','')}"
    m = re.search(r"url=([^\s]+)", text)
    if m:
        return m.group(1).strip()
    return ""


def _parse_wr_id_from_url(url: str) -> int:
    src = str(url or "").strip()
    if not src:
        return 0
    m = re.search(r"[?&]wr_id=(\d+)", src)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return 0
    m2 = re.search(r"/[A-Za-z0-9_]+/(\d+)(?:$|[/?#])", src)
    if m2:
        try:
            return int(m2.group(1))
        except ValueError:
            return 0
    return 0


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
    except Exception:
        return {}
    return {}


def _save_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_report(report: Dict[str, Any], out_json: Path) -> Path:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_json


def _validate_customer_html(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"ok": False, "reason": "missing_file", "path": str(path)}
    txt = path.read_text(encoding="utf-8", errors="replace")
    has_btn = 'id="btn-estimate"' in txt
    has_name = "AI 양도가 산정 계산기" in txt
    return {
        "ok": has_btn and has_name,
        "path": str(path),
        "has_estimate_button": has_btn,
        "has_unified_name": has_name,
    }


def _publish_custom_html(board_slug: str, subject: str, html_content: str, wr_id: int = 0) -> Dict[str, Any]:
    from all import CONFIG, MnaBoardPublisher, SITE_URL  # noqa: WPS433

    admin_id = str(CONFIG.get("ADMIN_ID", "")).strip()
    admin_pw = str(CONFIG.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        raise RuntimeError("ADMIN_ID/ADMIN_PW missing")

    pub = MnaBoardPublisher(SITE_URL, board_slug, admin_id, admin_pw)
    pub.login()
    res = pub.publish_custom_html(
        subject=subject,
        html_content=html_content,
        wr_id=int(wr_id or 0),
        link1=f"{str(SITE_URL).rstrip('/')}/{board_slug}",
    )
    return {
        "mode": str(res.get("mode", "")),
        "url": str(res.get("url", "")).strip(),
        "wr_id": int(res.get("wr_id", 0) or _parse_wr_id_from_url(str(res.get("url", "")))),
    }


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy SeoulMNA AI calculators to website boards (customer/acquisition)."
    )
    parser.add_argument("--estimate-limit", type=int, default=30)
    parser.add_argument("--estimate-top-k", type=int, default=12)
    parser.add_argument("--estimate-min-score", type=float, default=22.0)
    parser.add_argument("--skip-estimate", action="store_true")

    parser.add_argument("--customer-board", default="yangdo_ai")
    parser.add_argument("--customer-wr-id", type=int, default=0)
    parser.add_argument("--customer-subject", default="AI 양도가 산정 계산기 | 서울건설정보")

    parser.add_argument("--acquisition-board", default="yangdo_ai_ops")
    parser.add_argument("--acquisition-wr-id", type=int, default=0)
    parser.add_argument("--acquisition-subject", default="AI 인허가 사전검토 진단기(신규등록) | 서울건설정보")

    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--confirm-live", default="", help="실서비스 반영 승인 토큰 (`--confirm-live YES`)")
    parser.add_argument("--skip-customer-publish", action="store_true")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--report", default="logs/yangdo_site_release_latest.json")
    parser.add_argument("--state", default="logs/yangdo_site_release_state.json")
    args = parser.parse_args()
    confirm_live = str(args.confirm_live or "").strip().upper()
    if bool(args.publish) and confirm_live != "YES":
        blocked = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ok": False,
            "steps": [],
            "blocking_issues": ["confirm_live_missing"],
            "error": "publish blocked: add --confirm-live YES",
        }
        report_path = (ROOT / args.report).resolve()
        _write_report(blocked, report_path)
        print(f"[saved] {report_path}")
        print("[overall_ok] False")
        print("- confirm_live_missing")
        return 2

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out_dir = (ROOT / args.output_dir).resolve()
    customer_html = out_dir / "yangdo_price_calculator_customer.html"
    acquisition_html = out_dir / "ai_license_acquisition_calculator.html"

    steps: List[Dict[str, Any]] = []
    blocking: List[str] = []
    state_path = (ROOT / args.state).resolve()
    state = _load_state(state_path)
    env = _env_map(ROOT / ".env")

    if not args.skip_estimate:
        steps.append(
            _run_step(
                "estimate_dry_run",
                _py_cmd(
                    [
                        "all.py",
                        "--estimate-yangdo",
                        "--estimate-limit",
                        str(max(1, int(args.estimate_limit))),
                        "--estimate-no-sheet-sync",
                        "--estimate-top-k",
                        str(max(1, int(args.estimate_top_k))),
                        "--estimate-min-score",
                        str(float(args.estimate_min_score)),
                    ]
                ),
                timeout_sec=420,
            )
        )

    steps.append(
        _run_step(
            "build_customer_html",
            _py_cmd(
                [
                    "all.py",
                    "--build-yangdo-page",
                    "--yangdo-page-mode",
                    "customer",
                    "--yangdo-page-output",
                    str(customer_html),
                ]
            ),
            timeout_sec=300,
        )
    )

    steps.append(
        _run_step(
            "collect_permit_industries",
            _py_cmd(
                [
                    "scripts/collect_kr_permit_industries.py",
                    "--output",
                    str((ROOT / "config" / "kr_permit_industries_localdata.json").resolve()),
                    "--strict",
                ]
            ),
            timeout_sec=240,
        )
    )

    steps.append(
        _run_step(
            "build_acquisition_html",
            _py_cmd(
                [
                    "permit_diagnosis_calculator.py",
                    "--catalog",
                    str((ROOT / "config" / "kr_permit_industries_localdata.json").resolve()),
                    "--output",
                    str(acquisition_html),
                    "--title",
                    "AI 인허가 사전검토 진단기(신규등록)",
                ]
            ),
            timeout_sec=300,
        )
    )

    customer_html_check = _validate_customer_html(customer_html)
    if not customer_html_check.get("ok"):
        blocking.append("customer_html_policy_check_failed")

    publish_urls: Dict[str, str] = {}
    resolved_customer_wr_id = int(args.customer_wr_id or 0) or int(state.get("customer_wr_id", 0) or 0)
    resolved_acquisition_wr_id = int(args.acquisition_wr_id or 0) or int(state.get("acquisition_wr_id", 0) or 0)
    state_saved = False

    if args.publish and not blocking:
        if not args.skip_customer_publish:
            st = _run_step(
                "publish_customer",
                _py_cmd(
                    [
                        "all.py",
                        "--publish-yangdo-page",
                        "--yangdo-page-mode",
                        "customer",
                        "--yangdo-page-board-slug",
                        str(args.customer_board),
                        "--yangdo-page-wr-id",
                        str(int(resolved_customer_wr_id)),
                        "--yangdo-page-subject",
                        str(args.customer_subject),
                    ]
                ),
                timeout_sec=420,
            )
            steps.append(st)
            customer_url = _parse_publish_url(st)
            publish_urls["customer"] = customer_url
            if not customer_url:
                blocking.append("publish_customer_url_missing")
            out_wr_id = _parse_wr_id_from_url(customer_url)
            if out_wr_id > 0:
                resolved_customer_wr_id = int(out_wr_id)
                state["customer_wr_id"] = int(out_wr_id)
        else:
            publish_urls["customer"] = "SKIPPED"

        if int(resolved_acquisition_wr_id or 0) > 0:
            try:
                acq_html_text = acquisition_html.read_text(encoding="utf-8", errors="replace")
                acq_res = _publish_custom_html(
                    board_slug=str(args.acquisition_board),
                    subject=str(args.acquisition_subject),
                    html_content=acq_html_text,
                    wr_id=int(resolved_acquisition_wr_id),
                )
                publish_urls["acquisition"] = str(acq_res.get("url", ""))
                acq_wr = int(acq_res.get("wr_id", 0) or 0)
                if acq_wr > 0:
                    resolved_acquisition_wr_id = acq_wr
                    state["acquisition_wr_id"] = acq_wr
            except Exception as e:
                blocking.append(f"publish_acquisition_failed:{e}")

        if int(state.get("customer_wr_id", 0) or 0) > 0 or int(state.get("acquisition_wr_id", 0) or 0) > 0:
            _save_state(state_path, state)
            state_saved = True

    for step in steps:
        if not step.get("ok"):
            blocking.append(f"step_failed:{step['name']}")

    ok = len(blocking) == 0
    report = {
        "generated_at": ts,
        "workspace": str(ROOT),
        "publish_mode": bool(args.publish),
        "ok": ok,
        "blocking_issues": blocking,
        "customer_html_check": customer_html_check,
        "publish_urls": publish_urls,
        "state": {
            "path": str(state_path),
            "saved": bool(state_saved),
            "customer_wr_id": int(state.get("customer_wr_id", 0) or 0),
            "acquisition_wr_id": int(state.get("acquisition_wr_id", 0) or 0),
        },
        "steps": steps,
        "inputs": {
            "customer_board": args.customer_board,
            "customer_wr_id": int(args.customer_wr_id or 0),
            "acquisition_board": args.acquisition_board,
            "acquisition_wr_id": int(args.acquisition_wr_id or 0),
            "resolved_customer_wr_id": int(resolved_customer_wr_id or 0),
            "resolved_acquisition_wr_id": int(resolved_acquisition_wr_id or 0),
        },
    }
    report_path = _write_report(report, (ROOT / args.report).resolve())
    print(f"[saved] {report_path}")
    print(f"[overall_ok] {ok}")
    if publish_urls:
        for k, v in publish_urls.items():
            print(f"[url] {k}={v}")
    if blocking:
        for b in blocking:
            print(f"- {b}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

