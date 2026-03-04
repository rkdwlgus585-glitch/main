import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
TARGET_HOST = "seoulmna.co.kr"
DEFAULT_HEAL_RULES = {"quickmenu", "login_signal", "global_banner", "traffic_counter", "footer_or_address"}


def _load_json(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"json root must be an object: {path}")
    return data


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _tail(text: str, lines: int = 40) -> List[str]:
    rows = (text or "").splitlines()
    return rows[-lines:]


def _run_cmd(cmd: List[str]) -> Tuple[int, List[str], List[str]]:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return int(proc.returncode), _tail(proc.stdout, 40), _tail(proc.stderr, 40)


def _co_result(report: Dict[str, Any]) -> Dict[str, Any]:
    for row in list(report.get("results") or []):
        url = str(row.get("url", "")).lower()
        if TARGET_HOST in url:
            return row
    return {}


def _failed_rules(result_row: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for rule in list(result_row.get("rules") or []):
        required = bool(rule.get("required", True))
        ok = bool(rule.get("ok", False))
        if required and (not ok):
            out.append(str(rule.get("id", "")).strip())
    return [x for x in out if x]


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-heal seoulmna.co.kr CX markers using banner admin snippet apply.")
    parser.add_argument("--probe-report", default="logs/site_cx_probe_latest.json")
    parser.add_argument("--summary-report", default="logs/site_cx_autoheal_latest.json")
    parser.add_argument("--apply-report", default="logs/co_global_banner_apply_latest.json")
    parser.add_argument("--snippet-file", default="logs/co_global_banner_snippet.html")
    parser.add_argument("--base-url", default="https://seoulmna.co.kr")
    parser.add_argument("--force", action="store_true", help="Pass --force to admin apply script.")
    parser.add_argument("--skip-reprobe", action="store_true", help="Do not rerun site_cx_probe after heal attempt.")
    parser.add_argument(
        "--heal-rules",
        default="quickmenu,login_signal,global_banner,traffic_counter,footer_or_address",
        help="Comma-separated rule ids to auto-heal.",
    )
    args = parser.parse_args()

    probe_path = (ROOT / str(args.probe_report)).resolve()
    summary_path = (ROOT / str(args.summary_report)).resolve()
    apply_report_path = (ROOT / str(args.apply_report)).resolve()
    snippet_rel = str(args.snippet_file).replace("\\", "/")
    heal_targets = {x.strip() for x in str(args.heal_rules).split(",") if x.strip()} or set(DEFAULT_HEAL_RULES)

    summary: Dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "probe_report": str(probe_path),
        "summary_report": str(summary_path),
        "apply_report": str(apply_report_path),
        "base_url": str(args.base_url).strip(),
        "heal_targets": sorted(heal_targets),
        "before": {},
        "after": {},
        "actions": [],
        "ok": False,
        "healed": False,
        "error": "",
    }

    try:
        if not probe_path.exists():
            raise RuntimeError(f"probe report missing: {probe_path}")

        before_report = _load_json(probe_path)
        before_row = _co_result(before_report)
        if not before_row:
            raise RuntimeError("seoulmna.co.kr probe result not found in report")

        before_failed_required = _failed_rules(before_row)
        before_failed_heal = [x for x in before_failed_required if x in heal_targets]
        summary["before"] = {
            "ok": bool(before_row.get("ok", False)),
            "status_code": int(before_row.get("status_code") or 0),
            "failed_required_rules": before_failed_required,
            "failed_heal_rules": before_failed_heal,
        }

        if not before_failed_heal:
            summary["ok"] = True
            summary["healed"] = True
            summary["actions"].append({"step": "noop", "reason": "no heal-target rule failure"})
            summary["after"] = dict(summary["before"])
            _save_json(summary_path, summary)
            print(f"[saved] {summary_path}")
            print("[summary] noop=true ok=true")
            return 0

        prep_cmd = [
            sys.executable,
            "scripts/prepare_co_global_banner_snippet.py",
            "--snippet-out",
            snippet_rel,
        ]
        prep_rc, prep_out, prep_err = _run_cmd(prep_cmd)
        summary["actions"].append(
            {
                "step": "prepare_snippet",
                "command": prep_cmd,
                "rc": prep_rc,
                "stdout_tail": prep_out,
                "stderr_tail": prep_err,
            }
        )
        if prep_rc != 0:
            raise RuntimeError("prepare_co_global_banner_snippet.py failed")

        apply_cmd = [
            sys.executable,
            "scripts/apply_co_global_banner_admin.py",
            "--base-url",
            str(args.base_url).strip(),
            "--snippet-file",
            snippet_rel,
            "--report",
            str(args.apply_report).replace("\\", "/"),
        ]
        if bool(args.force):
            apply_cmd.append("--force")
        apply_rc, apply_out, apply_err = _run_cmd(apply_cmd)
        summary["actions"].append(
            {
                "step": "apply_banner",
                "command": apply_cmd,
                "rc": apply_rc,
                "stdout_tail": apply_out,
                "stderr_tail": apply_err,
            }
        )
        if apply_report_path.exists():
            try:
                summary["apply_report_payload"] = _load_json(apply_report_path)
            except Exception as exc:
                summary["actions"].append({"step": "apply_report_parse", "error": str(exc)})
        if apply_rc != 0:
            raise RuntimeError("apply_co_global_banner_admin.py failed")

        if not bool(args.skip_reprobe):
            reprobe_cmd = [
                sys.executable,
                "scripts/site_cx_probe.py",
                "--report",
                str(args.probe_report).replace("\\", "/"),
            ]
            reprobe_rc, reprobe_out, reprobe_err = _run_cmd(reprobe_cmd)
            summary["actions"].append(
                {
                    "step": "reprobe",
                    "command": reprobe_cmd,
                    "rc": reprobe_rc,
                    "stdout_tail": reprobe_out,
                    "stderr_tail": reprobe_err,
                }
            )
            if reprobe_rc != 0:
                raise RuntimeError("site_cx_probe.py re-probe failed")

        after_report = _load_json(probe_path)
        after_row = _co_result(after_report)
        after_failed_required = _failed_rules(after_row) if after_row else ["co_result_missing_after_reprobe"]
        after_failed_heal = [x for x in after_failed_required if x in heal_targets]
        summary["after"] = {
            "ok": bool(after_row.get("ok", False)) if after_row else False,
            "status_code": int(after_row.get("status_code") or 0) if after_row else 0,
            "failed_required_rules": after_failed_required,
            "failed_heal_rules": after_failed_heal,
        }
        summary["ok"] = len(after_failed_heal) == 0
        summary["healed"] = summary["ok"]
    except Exception as exc:
        summary["error"] = str(exc)
        summary["ok"] = False
        summary["healed"] = False

    _save_json(summary_path, summary)
    print(f"[saved] {summary_path}")
    print(
        "[summary] "
        + f"ok={summary.get('ok')} "
        + f"healed={summary.get('healed')} "
        + f"error={'none' if not summary.get('error') else summary.get('error')}"
    )
    return 0 if summary.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
