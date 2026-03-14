#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "imported"
PUBLIC_DIR = PROJECT_ROOT / "public"
REQUIRED_IMPORTED_FILES = [
    "manifest.json",
    "listing-summaries.json",
    "listing-details.json",
    "listing-sheet-rows.json",
    "notice-posts.json",
    "premium-posts.json",
    "pages.json",
]
RECOMMENDED_ENV_KEYS = [
    "NEXT_PUBLIC_SITE_HOST",
    "NEXT_PUBLIC_COMPANY_NAME",
    "NEXT_PUBLIC_REPRESENTATIVE_NAME",
    "NEXT_PUBLIC_BUSINESS_NUMBER",
    "NEXT_PUBLIC_MAIL_ORDER_NUMBER",
    "NEXT_PUBLIC_CONTACT_PHONE",
    "NEXT_PUBLIC_CONTACT_EMAIL",
    "NEXT_PUBLIC_KAKAO_URL",
]
PREVIEW_SAFE_HOST_SUFFIXES = [
    ".example.com",
    ".vercel.app",
    ".vercel.sh",
]


def run_command(cmd: list[str], *, cwd: Path, timeout_sec: int = 180) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.setdefault("CI", "1")
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "command": cmd,
    }


def resolve_vercel_runner() -> tuple[list[str], str]:
    vercel_path = shutil.which("vercel")
    if vercel_path:
        return [vercel_path], "vercel"
    npx_path = shutil.which("npx.cmd") or shutil.which("npx")
    if npx_path:
        return [npx_path, "--yes", "vercel"], "npx"
    return [], ""


def inspect_vercel_cli(*, cwd: Path, check_auth: bool = True) -> dict[str, Any]:
    runner, mode = resolve_vercel_runner()
    if not runner:
        return {
            "available": False,
            "mode": "",
            "version": "",
            "auth_ok": False,
            "identity": "",
            "errors": ["vercel_cli_missing"],
        }

    version_result = run_command([*runner, "--version"], cwd=cwd, timeout_sec=120)
    version_lines = ((version_result["stdout"] or "") + "\n" + (version_result["stderr"] or "")).strip().splitlines()
    version = version_lines[-1].strip() if version_lines else ""
    errors: list[str] = []
    if not version_result["ok"]:
        errors.append("vercel_cli_version_check_failed")

    auth_ok = False
    identity = ""
    auth_error = ""
    if check_auth:
        auth_result = run_command([*runner, "whoami"], cwd=cwd, timeout_sec=120)
        auth_text = ((auth_result["stdout"] or "") + "\n" + (auth_result["stderr"] or "")).strip()
        if auth_result["ok"] and auth_text:
            auth_ok = True
            identity = auth_text.splitlines()[-1].strip()
        else:
            auth_error = auth_text or "vercel_auth_missing"
            errors.append("vercel_auth_missing")
    else:
        auth_ok = True

    return {
        "available": True,
        "mode": mode,
        "version": version,
        "auth_ok": auth_ok,
        "identity": identity,
        "auth_error": auth_error,
        "errors": errors,
    }


def read_env_keys(path: Path) -> list[str]:
    if not path.exists():
        return []
    keys: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        text = str(line or "").strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key = text.split("=", 1)[0].strip().lstrip("\ufeff")
        if key and key not in keys:
            keys.append(key)
    return keys


def read_env_map(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    if not path.exists():
        return payload
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        text = str(line or "").strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        payload[key.strip().lstrip("\ufeff")] = value.strip()
    return payload


def is_preview_safe_host(host: str) -> bool:
    value = str(host or "").strip()
    if not value:
        return False
    try:
        hostname = value.split("://", 1)[-1].split("/", 1)[0].lower()
    except Exception:  # pragma: no cover - defensive
        return False
    return hostname == "example.com" or any(hostname.endswith(suffix) for suffix in PREVIEW_SAFE_HOST_SUFFIXES)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def imported_file_stats() -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    for filename in REQUIRED_IMPORTED_FILES:
        path = DATA_DIR / filename
        entry: dict[str, Any] = {
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
        }
        if path.exists():
            try:
                payload = load_json(path)
            except Exception as exc:  # pragma: no cover - defensive
                entry["loadError"] = str(exc)
            else:
                if isinstance(payload, list):
                    entry["records"] = len(payload)
                elif isinstance(payload, dict):
                    entry["records"] = 1
                else:
                    entry["records"] = 0
        stats[filename] = entry
    return stats


def public_asset_stats() -> dict[str, Any]:
    asset_dir = PUBLIC_DIR / "imported-assets"
    if not asset_dir.exists():
        return {"exists": False, "files": 0, "bytes": 0}
    total_bytes = 0
    total_files = 0
    for path in asset_dir.rglob("*"):
        if path.is_file():
            total_files += 1
            total_bytes += path.stat().st_size
    return {"exists": True, "files": total_files, "bytes": total_bytes}


def find_build_manifest() -> Path | None:
    candidates = [
        PROJECT_ROOT / ".next" / "build-manifest.json",
        *sorted(PROJECT_ROOT.glob(".next-*/build-manifest.json")),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def build_report(*, check_auth: bool = True) -> dict[str, Any]:
    env_path = PROJECT_ROOT / ".env.local"
    env_keys = read_env_keys(env_path)
    env_map = read_env_map(env_path)
    imported = imported_file_stats()
    assets = public_asset_stats()
    vercel = inspect_vercel_cli(cwd=PROJECT_ROOT, check_auth=check_auth)
    build_manifest_path = find_build_manifest()

    blockers: list[str] = []
    warnings: list[str] = []

    required_paths = {
        "package_json": PROJECT_ROOT / "package.json",
        "next_config": PROJECT_ROOT / "next.config.mjs",
        "vercel_config": PROJECT_ROOT / "vercel.json",
        "vercel_ignore": PROJECT_ROOT / ".vercelignore",
    }
    for label, path in required_paths.items():
        if not path.exists():
            blockers.append(f"missing_{label}")
    if build_manifest_path is None:
        blockers.append("missing_build_manifest")

    for filename, meta in imported.items():
        if not meta.get("exists"):
            blockers.append(f"missing_imported_{filename}")
        elif int(meta.get("records") or 0) <= 0:
            blockers.append(f"empty_imported_{filename}")

    if not assets["exists"] or int(assets["files"]) <= 0:
        blockers.append("missing_imported_assets")

    if not vercel["available"]:
        blockers.append("vercel_cli_missing")
    elif check_auth and not vercel["auth_ok"]:
        blockers.append("vercel_auth_missing")

    missing_env = [key for key in RECOMMENDED_ENV_KEYS if key not in env_keys]
    if not env_path.exists():
        warnings.append(".env.local is missing; run npm.cmd run sync:env to generate a preview-safe env file")
    elif missing_env:
        warnings.append(f".env.local is missing recommended keys: {', '.join(missing_env)}")

    site_host = str(env_map.get("NEXT_PUBLIC_SITE_HOST") or "").strip()
    if site_host and is_preview_safe_host(site_host):
        warnings.append(
            "NEXT_PUBLIC_SITE_HOST is using a preview-safe host, so metadata will stay noindex until you set the final production host"
        )

    listing_sheet_records = int(imported.get("listing-sheet-rows.json", {}).get("records") or 0)
    manifest_generated_at = ""
    manifest_path = DATA_DIR / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = load_json(manifest_path)
        except Exception:
            manifest = {}
        if isinstance(manifest, dict):
            manifest_generated_at = str(manifest.get("generatedAt") or "")

    next_actions: list[str] = []
    if any(item.startswith("missing_imported_") or item.startswith("empty_imported_") for item in blockers):
        next_actions.append("Run npm.cmd run import:legacy and npm.cmd run export:listings:sheet")
    if "missing_build_manifest" in blockers:
        next_actions.append("Run npm.cmd run build (or set BUILD_DIST_DIR if the default .next directory is locked)")
    if "vercel_cli_missing" in blockers:
        next_actions.append("Expose Vercel CLI via vercel or npx.cmd")
    if "vercel_auth_missing" in blockers:
        next_actions.append("Run npx.cmd --yes vercel login")
    if warnings:
        if not env_path.exists():
            next_actions.append("Run npm.cmd run sync:env")
        next_actions.append("Fill .env.local with the final public host and business contact values")
    if not blockers:
        next_actions.append("Run npm.cmd run deploy:preview")

    return {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": not blockers,
        "projectRoot": str(PROJECT_ROOT),
        "build": {
            "buildArtifactsReady": build_manifest_path is not None,
            "buildManifestPath": str(build_manifest_path) if build_manifest_path else "",
            "manifestGeneratedAt": manifest_generated_at,
        },
        "content": {
            "importedFiles": imported,
            "listingSheetRecords": listing_sheet_records,
            "publicImportedAssets": assets,
        },
        "env": {
            "envLocalExists": env_path.exists(),
            "envLocalPath": str(env_path),
            "siteHost": site_host,
            "siteHostPreviewSafe": is_preview_safe_host(site_host),
            "recommendedKeysMissing": missing_env,
        },
        "vercel": vercel,
        "blockingIssues": blockers,
        "warnings": warnings,
        "nextActions": next_actions,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate co_kr_public_site deploy readiness.")
    parser.add_argument("--skip-auth-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(check_auth=not args.skip_auth_check)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
