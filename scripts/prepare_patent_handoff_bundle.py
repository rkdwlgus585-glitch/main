#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = ROOT / "snapshots" / "patent_handoff"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        while True:
            chunk = fp.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _bundle_items() -> List[Dict[str, str]]:
    return [
        {"category": "patent_doc", "path": "docs/patent_package_yangdo_draft_20260305.md"},
        {"category": "patent_doc", "path": "docs/patent_package_permit_draft_20260305.md"},
        {"category": "patent_doc", "path": "docs/patent_handoff_checklist_20260305.md"},
        {"category": "ops_doc", "path": "docs/tenant_policy_recovery_runbook_20260305.md"},
        {"category": "ops_doc", "path": "docs/security_foundation_runbook_20260305.md"},
        {"category": "status_doc", "path": "docs/progress_to_100_20260305.md"},
        {"category": "code_ref", "path": "yangdo_blackbox_api.py"},
        {"category": "code_ref", "path": "yangdo_consult_api.py"},
        {"category": "code_ref", "path": "permit_diagnosis_calculator.py"},
        {"category": "code_ref", "path": "core_engine/tenant_gateway.py"},
        {"category": "data_ref", "path": "config/permit_registration_rules_law.json"},
        {"category": "data_ref", "path": "config/permit_registration_criteria_expanded.json"},
    ]


def build_bundle() -> Dict[str, object]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_dir = BUNDLE_ROOT / f"patent_handoff_{stamp}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    copied: List[Dict[str, object]] = []
    missing: List[str] = []
    for item in _bundle_items():
        rel = Path(item["path"])
        src = ROOT / rel
        if not src.exists() or not src.is_file():
            missing.append(str(rel))
            continue
        dst = bundle_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(
            {
                "category": item["category"],
                "path": str(rel).replace("\\", "/"),
                "size_bytes": int(dst.stat().st_size),
                "sha256": _sha256(dst),
            }
        )

    manifest = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bundle_dir": str(bundle_dir),
        "copied_count": len(copied),
        "missing_count": len(missing),
        "copied": copied,
        "missing": missing,
    }
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    zip_base = bundle_dir.parent / bundle_dir.name
    archive_path = shutil.make_archive(str(zip_base), "zip", root_dir=str(bundle_dir))

    result = {
        "ok": len(copied) > 0,
        "bundle_dir": str(bundle_dir),
        "archive": str(archive_path),
        "manifest": str(bundle_dir / "manifest.json"),
        "copied_count": len(copied),
        "missing_count": len(missing),
    }
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> int:
    out = build_bundle()
    return 0 if bool(out.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
