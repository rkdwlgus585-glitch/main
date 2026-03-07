#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAB_ROOT = ROOT / "workspace_partitions" / "site_session" / "wp_surface_lab"
DEFAULT_SURFACE_AUDIT = ROOT / "logs" / "surface_stack_audit_latest.json"

WP_CORE_API = "https://api.wordpress.org/core/version-check/1.7/"
WP_THEME_API = "https://api.wordpress.org/themes/info/1.2/"
WP_PLUGIN_API = "https://api.wordpress.org/plugins/info/1.2/"

PACKAGE_TARGETS = [
    {"kind": "core", "slug": "wordpress-core"},
    {"kind": "theme", "slug": "astra"},
    {"kind": "plugin", "slug": "astra-sites"},
    {"kind": "plugin", "slug": "ultimate-addons-for-gutenberg"},
    {"kind": "plugin", "slug": "wordpress-seo"},
    {"kind": "plugin", "slug": "seo-by-rank-math"},
    {"kind": "plugin", "slug": "sqlite-database-integration"},
]


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
    with requests.get(url, stream=True, timeout=timeout_sec, headers={"User-Agent": "Mozilla/5.0"}) as res:
        res.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in res.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)


def _fetch_core_meta(timeout_sec: int) -> Dict[str, Any]:
    res = requests.get(WP_CORE_API, timeout=timeout_sec, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    payload = res.json()
    offers = payload.get("offers") if isinstance(payload.get("offers"), list) else []
    first = offers[0] if offers else {}
    packages = first.get("packages") if isinstance(first.get("packages"), dict) else {}
    return {
        "kind": "core",
        "slug": "wordpress-core",
        "name": "WordPress Core",
        "version": str(first.get("version") or ""),
        "download_url": str(packages.get("full") or first.get("download") or ""),
        "homepage": "https://wordpress.org/download/",
    }


def _fetch_theme_meta(slug: str, timeout_sec: int) -> Dict[str, Any]:
    res = requests.get(
        WP_THEME_API,
        params={"action": "theme_information", "request[slug]": slug},
        timeout=timeout_sec,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    res.raise_for_status()
    payload = res.json()
    return {
        "kind": "theme",
        "slug": slug,
        "name": str(payload.get("name") or slug),
        "version": str(payload.get("version") or ""),
        "download_url": str(payload.get("download_link") or ""),
        "last_updated": str(payload.get("last_updated") or ""),
        "homepage": str(payload.get("homepage") or ""),
    }


def _fetch_plugin_meta(slug: str, timeout_sec: int) -> Dict[str, Any]:
    res = requests.get(
        WP_PLUGIN_API,
        params={"action": "plugin_information", "request[slug]": slug},
        timeout=timeout_sec,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    res.raise_for_status()
    payload = res.json()
    return {
        "kind": "plugin",
        "slug": slug,
        "name": str(payload.get("name") or slug),
        "version": str(payload.get("version") or ""),
        "download_url": str(payload.get("download_link") or ""),
        "last_updated": str(payload.get("last_updated") or ""),
        "active_installs": int(payload.get("active_installs") or 0),
        "homepage": str(payload.get("homepage") or ""),
    }


def fetch_package_meta(timeout_sec: int) -> List[Dict[str, Any]]:
    packages: List[Dict[str, Any]] = []
    for item in PACKAGE_TARGETS:
        kind = str(item.get("kind") or "")
        slug = str(item.get("slug") or "")
        if kind == "core":
            packages.append(_fetch_core_meta(timeout_sec))
        elif kind == "theme":
            packages.append(_fetch_theme_meta(slug, timeout_sec))
        elif kind == "plugin":
            packages.append(_fetch_plugin_meta(slug, timeout_sec))
    return packages


def _extract_zip(zip_path: Path, target_dir: Path) -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        temp_root = Path(td)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(temp_root)
        entries = [entry for entry in temp_root.iterdir()]
        source_root = temp_root
        if len(entries) == 1 and entries[0].is_dir():
            source_root = entries[0]
        shutil.copytree(source_root, target_dir)


def _runtime_probe() -> Dict[str, Any]:
    return {
        "php_available": shutil.which("php") is not None,
        "docker_available": shutil.which("docker") is not None,
    }


def _staging_target(base: Path, package: Dict[str, Any]) -> Path:
    kind = str(package.get("kind") or "")
    slug = str(package.get("slug") or "")
    if kind == "core":
        return base / "staging" / "wordpress"
    if kind == "theme":
        return base / "staging" / "wp-content" / "themes" / slug
    return base / "staging" / "wp-content" / "plugins" / slug


def build_wp_surface_lab(
    *,
    lab_root: Path,
    surface_audit_path: Path,
    timeout_sec: int,
    download_packages: bool,
) -> Dict[str, Any]:
    surface_audit = _load_json(surface_audit_path)
    packages = fetch_package_meta(timeout_sec)

    package_dir = lab_root / "packages"
    manifest_dir = lab_root / "manifests"
    package_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    package_rows: List[Dict[str, Any]] = []
    for row in packages:
        download_url = str(row.get("download_url") or "")
        slug = str(row.get("slug") or "")
        archive_path = package_dir / f"{slug}.zip"
        extracted_to = _staging_target(lab_root, row)
        item = dict(row)
        item["archive_path"] = str(archive_path)
        item["extracted_to"] = str(extracted_to)
        item["downloaded"] = False
        item["sha256"] = ""
        if download_packages and download_url:
            _download(download_url, archive_path, timeout_sec)
            item["downloaded"] = archive_path.exists()
            if archive_path.exists():
                item["sha256"] = _sha256(archive_path)
                _extract_zip(archive_path, extracted_to)
        item["staging_ready"] = extracted_to.exists()
        package_rows.append(item)

    runtime = _runtime_probe()
    blockers: List[str] = []
    if not runtime["php_available"]:
        blockers.append("php_missing")
    if not runtime["docker_available"]:
        blockers.append("docker_missing")

    readme_path = lab_root / "README.md"
    readme_path.write_text(
        "\n".join(
            [
                "# WordPress Surface Lab",
                "",
                "- Purpose: validate Astra and related WordPress assets inside an isolated lab before any live adoption.",
                "- Live reality: seoulmna.kr is the current WordPress/Astra public site, seoulmna.co.kr is the internal unlimited widget consumer, and the private engine remains hidden behind consumer channels.",
                "- Runtime policy: when PHP or Docker is missing, keep the lab in package extraction and static validation mode only.",
                "- Runtime scaffold: run `scripts/scaffold_wp_surface_lab_runtime.py` to generate a local-only Docker compose runtime under `runtime/` before any live change.",
                "- PHP fallback: run `scripts/prepare_wp_surface_lab_php_runtime.py` and `scripts/bootstrap_wp_surface_lab_php_fallback.py` to build a Docker-free local runtime using the official Windows PHP package and the official SQLite Database Integration plugin.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lab_root": str(lab_root),
        "surface_policy": {
            "kr_host": str(surface_audit.get("surfaces", {}).get("kr", {}).get("host") or "seoulmna.kr"),
            "co_host": str(surface_audit.get("surfaces", {}).get("co", {}).get("host") or "seoulmna.co.kr"),
            "decision": "wordpress_assets_sandbox_only",
        },
        "runtime": {
            **runtime,
            "runtime_ready": runtime["php_available"] or runtime["docker_available"],
            "blockers": blockers,
        },
        "packages": package_rows,
        "manifests": {
            "packages": str((manifest_dir / "packages.json").resolve()),
        },
        "summary": {
            "package_count": len(package_rows),
            "downloaded_count": sum(1 for row in package_rows if row.get("downloaded")),
            "staging_ready_count": sum(1 for row in package_rows if row.get("staging_ready")),
            "runtime_ready": runtime["php_available"] or runtime["docker_available"],
            "runtime_blockers": blockers,
        },
    }
    (manifest_dir / "packages.json").write_text(json.dumps({"packages": package_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    runtime = payload.get("runtime", {})
    lines = [
        "# WordPress Surface Lab",
        "",
        f"- lab_root: {payload.get('lab_root') or '(none)'}",
        f"- package_count: {summary.get('package_count')}",
        f"- downloaded_count: {summary.get('downloaded_count')}",
        f"- staging_ready_count: {summary.get('staging_ready_count')}",
        f"- runtime_ready: {summary.get('runtime_ready')}",
        f"- runtime_blockers: {', '.join(summary.get('runtime_blockers') or []) or '(none)'}",
        "",
        "## Packages",
    ]
    for row in payload.get("packages") or []:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('kind')} / {row.get('slug')} / v{row.get('version') or '(none)'} / downloaded={row.get('downloaded')} / staging_ready={row.get('staging_ready')}"
        )
    lines.extend(
        [
            "",
            "## Runtime",
            f"- php_available: {runtime.get('php_available')}",
            f"- docker_available: {runtime.get('docker_available')}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download official WordPress theme/plugin assets into an isolated lab.")
    parser.add_argument("--lab-root", type=Path, default=DEFAULT_LAB_ROOT)
    parser.add_argument("--surface-audit", type=Path, default=DEFAULT_SURFACE_AUDIT)
    parser.add_argument("--timeout-sec", type=int, default=30)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wp_surface_lab_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wp_surface_lab_latest.md")
    args = parser.parse_args()

    payload = build_wp_surface_lab(
        lab_root=args.lab_root,
        surface_audit_path=args.surface_audit,
        timeout_sec=max(5, int(args.timeout_sec)),
        download_packages=not args.skip_download,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
