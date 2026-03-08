from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUTPUT_DIR = ROOT / "output"
LOG_DIR = ROOT / "logs"
PERMIT_OUTPUT = OUTPUT_DIR / "ai_license_acquisition_calculator.html"
DEFAULT_REPORT = LOG_DIR / "permit_wizard_sanity_latest.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_permit_output() -> Dict[str, Any]:
    import permit_diagnosis_calculator

    html = permit_diagnosis_calculator.build_html(
        catalog=permit_diagnosis_calculator._load_catalog(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH),
        rule_catalog=permit_diagnosis_calculator._load_rule_catalog(permit_diagnosis_calculator.DEFAULT_RULES_PATH),
        title="AI 인허가 사전검토 진단기(신규등록 전용) | 서울건설정보",
    )
    PERMIT_OUTPUT.write_text(html, encoding="utf-8")
    return {
        "path": str(PERMIT_OUTPUT),
        "bytes": PERMIT_OUTPUT.stat().st_size,
    }


def _find_index(text: str, needle: str) -> int:
    idx = text.find(needle)
    return int(idx)


def _sample_context(text: str, start: int, end: int, radius: int = 40) -> str:
    left = max(0, int(start) - int(radius))
    right = min(len(text), int(end) + int(radius))
    return str(text[left:right]).replace("\n", "\\n")


def _run_integrity_checks(html: str) -> Dict[str, Any]:
    suspicious_specs = [
        ("raw_triple_quote", r"'''(?:const|let|function|<)"),
        ("garbled_question_run", r"\?{2,}"),
        ("broken_label_literal", r'label:\s*"\?{2,}'),
        ("broken_text_literal", r'(?:textContent|innerHTML)\s*=\s*[\"`]\?{2,}'),
        ("broken_html_text", r'>\?{2,}[^<]{0,120}<'),
    ]
    matches_summary: List[Dict[str, Any]] = []
    issues: List[str] = []
    for name, pattern in suspicious_specs:
        matches = list(re.finditer(pattern, html))
        if matches:
            issues.append(name)
        matches_summary.append(
            {
                "name": name,
                "count": len(matches),
                "samples": [
                    _sample_context(html, match.start(), match.end())
                    for match in matches[:5]
                ],
            }
        )
    return {
        "ok": not issues,
        "issues": issues,
        "matches": matches_summary,
    }


def _decode_wrapped_script_sources(html: str) -> List[str]:
    decoded: List[str] = []
    for match in re.finditer(r'const encoded="([A-Za-z0-9+/=]+)"', html):
        payload = str(match.group(1) or "").strip()
        if not payload:
            continue
        try:
            decoded.append(base64.b64decode(payload).decode("utf-8"))
        except Exception:
            continue
    return decoded


def _run_sanity(html: str) -> Dict[str, Any]:
    decoded_sources = _decode_wrapped_script_sources(html)
    search_text = "\n".join([html, *decoded_sources])
    required_markers = [
        'wizardShell.id = "permitInputWizard"',
        'wizardRail.id = "permitWizardRail"',
        'lookupBlock.id = "permitWizardStep1"',
        'categoryBlock.id = "permitWizardStep2"',
        'holdingsBlock.id = "permitWizardStep3"',
        'optionalBlock.id = "permitWizardStep4"',
        'id="permitWizardStepTitle"',
        'data-permit-wizard-track',
    ]
    counts = {
        "decoded_script_count": len(decoded_sources),
        "wizard_meta_decl": search_text.count("const permitWizardStepsMeta = ["),
        "apply_layout_decl": search_text.count("const applyExperienceLayout = () => {"),
        "sync_wizard_decl": search_text.count("const syncPermitWizard = () => {"),
        "set_wizard_decl": search_text.count("const setPermitWizardStep = ("),
    }
    indexes = {
        "wizard_meta_decl": _find_index(search_text, "const permitWizardStepsMeta = ["),
        "apply_layout_decl": _find_index(search_text, "const applyExperienceLayout = () => {"),
        "sync_wizard_decl": _find_index(search_text, "const syncPermitWizard = () => {"),
        "apply_layout_call": _find_index(search_text, "applyExperienceLayout();"),
        "sync_experience_decl": _find_index(search_text, "const syncExperienceLayer = () => {"),
    }
    missing_markers = [needle for needle in required_markers if needle not in search_text]
    issues: List[str] = []
    if counts["wizard_meta_decl"] != 1:
        issues.append("wizard_meta_decl_count_invalid")
    if counts["sync_wizard_decl"] != 1:
        issues.append("sync_wizard_decl_count_invalid")
    if counts["apply_layout_decl"] != 1:
        issues.append("apply_layout_decl_count_invalid")
    if counts["set_wizard_decl"] != 1:
        issues.append("set_wizard_decl_count_invalid")
    if missing_markers:
        issues.append("wizard_dom_markers_missing")

    order_keys = ["wizard_meta_decl", "apply_layout_decl", "sync_wizard_decl", "apply_layout_call"]
    if any(indexes[key] < 0 for key in order_keys):
        issues.append("wizard_scope_markers_missing")
    else:
        if not (indexes["wizard_meta_decl"] < indexes["apply_layout_decl"] < indexes["sync_wizard_decl"]):
            issues.append("wizard_meta_scope_order_invalid")
        if not (indexes["apply_layout_decl"] < indexes["apply_layout_call"]):
            issues.append("apply_layout_call_order_invalid")
    if indexes["sync_experience_decl"] >= 0 and indexes["wizard_meta_decl"] >= 0:
        if indexes["wizard_meta_decl"] > indexes["sync_experience_decl"]:
            issues.append("wizard_meta_after_sync_experience")
    integrity = _run_integrity_checks(html)
    if not integrity.get("ok"):
        issues.extend([f"integrity:{name}" for name in list(integrity.get("issues") or [])])

    return {
        "ok": not issues,
        "counts": counts,
        "indexes": indexes,
        "decoded_script_count": len(decoded_sources),
        "missing_markers": missing_markers,
        "integrity": integrity,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanity-check permit wizard scope and markers in the built permit calculator HTML")
    parser.add_argument("--skip-build", action="store_true", default=False)
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    report: Dict[str, Any] = {
        "generated_at": _now(),
        "ok": False,
        "rebuilt": {},
        "checks": {},
        "blocking_issues": [],
    }

    try:
        if not args.skip_build:
            report["rebuilt"] = _build_permit_output()
        html = PERMIT_OUTPUT.read_text(encoding="utf-8", errors="replace")
        report["checks"] = _run_sanity(html)
        if not report["checks"].get("ok"):
            report["blocking_issues"] = list(report["checks"].get("issues") or [])
    except Exception as exc:  # noqa: BLE001
        report["blocking_issues"].append(str(exc))

    report["ok"] = not report["blocking_issues"]
    out_path = Path(str(args.report)).resolve()
    _save_json(out_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
