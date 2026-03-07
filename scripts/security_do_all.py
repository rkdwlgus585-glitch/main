import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]


def _run(name: str, cmd: List[str], timeout: int = 180) -> Dict[str, Any]:
    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=max(30, int(timeout)),
            check=False,
        )
        return {
            "name": name,
            "ok": proc.returncode == 0,
            "returncode": int(proc.returncode),
            "started_at": started,
            "stdout": (proc.stdout or "").strip()[-4000:],
            "stderr": (proc.stderr or "").strip()[-4000:],
            "command": cmd,
        }
    except Exception as e:
        return {
            "name": name,
            "ok": False,
            "returncode": -1,
            "started_at": started,
            "stdout": "",
            "stderr": str(e),
            "command": cmd,
        }


def _py_cmd(args: List[str]) -> List[str]:
    launcher = "py" if sys.platform.startswith("win") else sys.executable
    if launcher == "py":
        return ["py", "-3"] + args
    return [launcher] + args


def _pwsh_cmd(script_rel: str) -> List[str]:
    script = str((ROOT / script_rel).resolve())
    return [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        script,
        "-RepoRoot",
        str(ROOT),
    ]


def main() -> int:
    steps: List[Dict[str, Any]] = []

    steps.append(_run("security_key_bootstrap", _py_cmd(["scripts/security_key_manager.py", "--mode", "bootstrap"])))
    steps.append(_run("compile_security_modules", _py_cmd(["-m", "compileall", "security_http.py", "yangdo_consult_api.py", "yangdo_blackbox_api.py"]), timeout=120))
    steps.append(_run("ensure_secure_api_stack", _pwsh_cmd("scripts/run_secure_api_stack.ps1"), timeout=120))
    steps.append(_run("register_secure_api_startup_task", _pwsh_cmd("scripts/register_secure_api_startup_task.ps1"), timeout=120))
    steps.append(_run("register_security_watchdog_task", _pwsh_cmd("scripts/register_security_watchdog_task.ps1"), timeout=120))
    steps.append(_run("register_monthly_security_rehearsal_task", _pwsh_cmd("scripts/register_monthly_security_rehearsal_task.ps1"), timeout=120))
    steps.append(_run("security_watchdog_once", _py_cmd(["scripts/security_event_watchdog.py", "--lookback-min", "15"]), timeout=120))
    steps.append(_run("apply_cloudflare_baseline", _py_cmd(["scripts/apply_cloudflare_baseline.py"]), timeout=120))
    steps.append(_run("tenant_onboarding_validation", _py_cmd(["scripts/validate_tenant_onboarding.py"]), timeout=120))
    steps.append(_run("tenant_usage_billing_report", _py_cmd(["scripts/tenant_usage_billing_report.py", "--strict"]), timeout=120))
    steps.append(
        _run(
            "tenant_threshold_policy",
            _py_cmd(["scripts/enforce_tenant_threshold_policy.py", "--strict", "--apply-registry"]),
            timeout=120,
        )
    )
    steps.append(_run("tenant_policy_notify", _py_cmd(["scripts/tenant_policy_notify.py"]), timeout=120))
    steps.append(_run("build_ops_snapshot", _py_cmd(["scripts/build_ops_snapshot.py"]), timeout=120))

    ok = all(step.get("ok") for step in steps if step.get("name") != "apply_cloudflare_baseline")
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": bool(ok),
        "steps": steps,
    }

    out = ROOT / "logs" / "security_do_all_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "report": str(out), "step_count": len(steps)}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
