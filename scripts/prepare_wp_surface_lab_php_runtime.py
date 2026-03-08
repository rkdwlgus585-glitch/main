#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAB_ROOT = ROOT / "workspace_partitions" / "site_session" / "wp_surface_lab"
DEFAULT_WP_LAB = ROOT / "logs" / "wp_surface_lab_latest.json"
DEFAULT_TIMEOUT_SEC = 60
PHP_RELEASES_URL = "https://windows.php.net/downloads/releases/releases.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, dest: Path, timeout_sec: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout_sec, headers={"User-Agent": "Mozilla/5.0"}) as res:
        res.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in res.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)


def _extract(zip_path: Path, target_dir: Path) -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(target_dir)


def _version_tuple(text: str) -> Tuple[int, ...]:
    parts: List[int] = []
    for part in str(text or "").split("."):
        try:
            parts.append(int(part))
        except Exception:
            parts.append(0)
    return tuple(parts)


def _choose_php_package(releases: Dict[str, Any], *, preferred_major: str = "8.3") -> Dict[str, Any]:
    preferred_versions = [preferred_major] + sorted(
        (str(key) for key in releases.keys() if str(key) != preferred_major),
        key=_version_tuple,
        reverse=True,
    )
    runtime_keys = (
        "nts-vs17-x64",
        "nts-vs16-x64",
        "nts-vc17-x64",
        "nts-vc16-x64",
    )
    for version_key in preferred_versions:
        version_payload = releases.get(version_key)
        if not isinstance(version_payload, dict):
            continue
        for runtime_key in runtime_keys:
            runtime_payload = version_payload.get(runtime_key)
            if not isinstance(runtime_payload, dict):
                continue
            zip_payload = runtime_payload.get("zip") if isinstance(runtime_payload.get("zip"), dict) else {}
            archive_name = str(zip_payload.get("path") or "").strip()
            if not archive_name:
                continue
            archive_url = f"https://windows.php.net/downloads/releases/{archive_name}"
            return {
                "version_line": version_key,
                "runtime_key": runtime_key,
                "version": archive_name.replace("php-", "").replace(".zip", ""),
                "archive_name": archive_name,
                "archive_url": archive_url,
                "sha256": str(zip_payload.get("sha256") or ""),
                "mtime": str(runtime_payload.get("mtime") or ""),
            }
    return {}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _default_php_ini() -> str:
    return "\n".join(
        [
            "[PHP]",
            'extension_dir="ext"',
            "date.timezone=Asia/Seoul",
            "display_errors=On",
            "log_errors=On",
            "output_buffering=4096",
            "memory_limit=512M",
            "post_max_size=64M",
            "upload_max_filesize=64M",
            "max_execution_time=120",
            "default_charset=UTF-8",
            "extension=curl",
            "extension=mbstring",
            "extension=openssl",
            "extension=pdo_sqlite",
            "extension=sqlite3",
            "extension=zip",
            "",
        ]
    )


def _router_script() -> str:
    return """<?php
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/';
$full = __DIR__ . $path;
if ($path !== '/' && file_exists($full) && !is_dir($full)) {
    return false;
}
require __DIR__ . '/index.php';
"""


def _run_php_command(php_exe: Path, args: List[str]) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            [str(php_exe), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except Exception as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc), "returncode": -1}
    return {
        "ok": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "returncode": completed.returncode,
    }


def build_wp_surface_lab_php_runtime(
    *,
    lab_root: Path,
    wp_lab_path: Path,
    timeout_sec: int,
    download_runtime: bool,
    refresh_existing_runtime: bool = False,
) -> Dict[str, Any]:
    wp_lab = _load_json(wp_lab_path)
    releases_res = requests.get(PHP_RELEASES_URL, timeout=timeout_sec, headers={"User-Agent": "Mozilla/5.0"})
    releases_res.raise_for_status()
    releases = releases_res.json()
    php_package = _choose_php_package(releases if isinstance(releases, dict) else {})
    runtime_root = lab_root / "runtime" / "php_fallback"
    packages_root = runtime_root / "packages"
    extract_root = runtime_root / "php"
    archive_path = packages_root / str(php_package.get("archive_name") or "php-runtime.zip")
    php_exe = extract_root / "php.exe"
    php_ini = extract_root / "php.ini"
    router_php = runtime_root / "router.php"
    start_ps1 = runtime_root / "start-php-surface-lab.ps1"
    stop_ps1 = runtime_root / "stop-php-surface-lab.ps1"
    run_port = 18081
    localhost_url = f"http://127.0.0.1:{run_port}"

    skipped_extract = False
    if download_runtime and php_package.get("archive_url"):
        if php_exe.exists() and not refresh_existing_runtime:
            skipped_extract = True
        else:
            _download(str(php_package["archive_url"]), archive_path, timeout_sec)
            _extract(archive_path, extract_root)

    if extract_root.exists():
        template_ini = extract_root / "php.ini-production"
        if template_ini.exists():
            shutil.copyfile(template_ini, php_ini)
            php_ini.write_text(_default_php_ini(), encoding="utf-8")
        else:
            _write_text(php_ini, _default_php_ini())
        _write_text(router_php, _router_script())
        _write_text(
            start_ps1,
            "\n".join(
                [
                    "$ErrorActionPreference = 'Stop'",
                    f"$php = '{php_exe.as_posix()}'",
                    f"$ini = '{php_ini.as_posix()}'",
                    "$root = Split-Path -Parent $PSScriptRoot",
                    "$site = Join-Path $root 'site'",
                    f"$router = '{router_php.as_posix()}'",
                    "$proc = Start-Process -FilePath $php -ArgumentList @('-c', $ini, '-q', '-S', '127.0.0.1:18081', $router) -WorkingDirectory $site -PassThru",
                    "$proc.Id | Set-Content -Path (Join-Path $PSScriptRoot 'php-server.pid') -Encoding ASCII",
                    "Write-Output $proc.Id",
                    "",
                ]
            ),
        )
        _write_text(
            stop_ps1,
            "\n".join(
                [
                    "$pidFile = Join-Path $PSScriptRoot 'php-server.pid'",
                    "if (Test-Path $pidFile) {",
                    "  $pid = Get-Content $pidFile -Raw",
                    "  if ($pid) { Stop-Process -Id ([int]$pid) -Force -ErrorAction SilentlyContinue }",
                    "  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue",
                    "}",
                    "",
                ]
            ),
        )

    version_probe = _run_php_command(php_exe, ["-v"]) if php_exe.exists() else {"ok": False, "stdout": "", "stderr": "php_executable_missing", "returncode": -1}
    module_probe = _run_php_command(php_exe, ["-m"]) if php_exe.exists() else {"ok": False, "stdout": "", "stderr": "php_executable_missing", "returncode": -1}
    modules = {line.strip().lower() for line in str(module_probe.get("stdout") or "").splitlines() if line.strip()}
    required_modules = ["pdo_sqlite", "sqlite3", "openssl"]
    missing_modules = [name for name in required_modules if name not in modules]
    php_binary_ready = bool(version_probe.get("ok"))
    php_module_ready = php_binary_ready and not missing_modules

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "php_release_source": PHP_RELEASES_URL,
        "package": {
            **php_package,
            "archive_path": str(archive_path.resolve()),
            "downloaded": archive_path.exists(),
            "archive_sha256": _sha256(archive_path) if archive_path.exists() else "",
        },
        "paths": {
            "runtime_root": str(runtime_root.resolve()),
            "extract_root": str(extract_root.resolve()),
            "php_executable": str(php_exe.resolve()) if php_exe.exists() else str(php_exe),
            "php_ini": str(php_ini.resolve()) if php_ini.exists() else str(php_ini),
            "router": str(router_php.resolve()),
            "start_script": str(start_ps1.resolve()),
            "stop_script": str(stop_ps1.resolve()),
        },
        "runtime": {
            "localhost_url": localhost_url,
            "port": run_port,
            "required_modules": required_modules,
            "missing_modules": missing_modules,
            "php_binary_ready": php_binary_ready,
            "php_module_ready": php_module_ready,
            "php_version_probe": version_probe,
            "php_module_probe": module_probe,
        },
        "summary": {
            "package_ready": archive_path.exists(),
            "php_binary_ready": php_binary_ready,
            "php_module_ready": php_module_ready,
            "runtime_ready": php_module_ready,
            "skipped_extract": skipped_extract,
            "staging_ready_count": int((wp_lab.get("summary") or {}).get("staging_ready_count") or 0),
        },
        "commands": {
            "version": f'"{php_exe}" -v',
            "modules": f'"{php_exe}" -m',
            "start_server": f'powershell -ExecutionPolicy Bypass -File "{start_ps1}"',
            "stop_server": f'powershell -ExecutionPolicy Bypass -File "{stop_ps1}"',
        },
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    package = payload.get("package") if isinstance(payload.get("package"), dict) else {}
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    lines = [
        "# WordPress Surface Lab PHP Runtime",
        "",
        f"- archive_name: {package.get('archive_name') or '(none)'}",
        f"- runtime_key: {package.get('runtime_key') or '(none)'}",
        f"- downloaded: {package.get('downloaded')}",
        f"- package_ready: {summary.get('package_ready')}",
        f"- php_binary_ready: {summary.get('php_binary_ready')}",
        f"- php_module_ready: {summary.get('php_module_ready')}",
        f"- skipped_extract: {summary.get('skipped_extract')}",
        f"- localhost_url: {runtime.get('localhost_url') or '(none)'}",
        f"- missing_modules: {', '.join(runtime.get('missing_modules') or []) or '(none)'}",
        "",
        "## Commands",
    ]
    for key, value in (payload.get("commands") or {}).items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and scaffold an official Windows PHP runtime for the WordPress surface lab.")
    parser.add_argument("--lab-root", type=Path, default=DEFAULT_LAB_ROOT)
    parser.add_argument("--wp-lab", type=Path, default=DEFAULT_WP_LAB)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wp_surface_lab_php_runtime_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wp_surface_lab_php_runtime_latest.md")
    args = parser.parse_args()

    payload = build_wp_surface_lab_php_runtime(
        lab_root=args.lab_root,
        wp_lab_path=args.wp_lab,
        timeout_sec=max(10, int(args.timeout_sec)),
        download_runtime=not args.skip_download,
        refresh_existing_runtime=bool(args.force_refresh),
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if payload.get("summary", {}).get("package_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
