import argparse
import base64
import gzip
import json
import re
from datetime import date, timedelta
from html import escape
from pathlib import Path
from typing import Any, Dict

from core_engine.channel_branding import resolve_channel_branding
from core_engine.permit_criteria_schema import evaluate_typed_criteria


ROOT = Path(__file__).resolve().parent
DEFAULT_CATALOG_PATH = ROOT / "config" / "kr_permit_industries_localdata.json"
DEFAULT_RULES_PATH = ROOT / "config" / "permit_registration_rules_law.json"
DEFAULT_EXPANDED_CRITERIA_PATH = ROOT / "config" / "permit_registration_criteria_expanded.json"
DEFAULT_FOCUS_SCOPE_OVERRIDES_PATH = ROOT / "config" / "permit_focus_scope_overrides.json"
DEFAULT_FOCUS_SEED_CATALOG_PATH = ROOT / "config" / "permit_focus_seed_catalog.json"
DEFAULT_FOCUS_FAMILY_REGISTRY_PATH = ROOT / "config" / "permit_focus_family_registry.json"
DEFAULT_PATENT_EVIDENCE_BUNDLE_PATH = ROOT / "logs" / "permit_patent_evidence_bundle_latest.json"
DEFAULT_REVIEW_CASE_PRESETS_PATH = ROOT / "logs" / "permit_review_case_presets_latest.json"
DEFAULT_CASE_STORY_SURFACE_PATH = ROOT / "logs" / "permit_case_story_surface_latest.json"
DEFAULT_OPERATOR_DEMO_PACKET_PATH = ROOT / "logs" / "permit_operator_demo_packet_latest.json"
DEFAULT_REVIEW_REASON_DECISION_LADDER_PATH = ROOT / "logs" / "permit_review_reason_decision_ladder_latest.json"
DEFAULT_CRITICAL_PROMPT_SURFACE_PACKET_PATH = ROOT / "logs" / "permit_critical_prompt_surface_packet_latest.json"
DEFAULT_CRITICAL_PROMPT_DOC_PATH = ROOT / "docs" / "permit_critical_thinking_prompt.md"
RULES_ONLY_CATEGORY_CODE = "RG"
RULES_ONLY_CATEGORY_NAME = "등록기준 업종군"
OBJECTIVE_SOURCE_HOSTS = (
    "law.go.kr",
    "localdata.go.kr",
    "gov.kr",
)


def _safe_json(data) -> str:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (
        text.replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _gzip_base64_json(data) -> str:
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    return base64.b64encode(compressed).decode("ascii")


def _blank_catalog() -> dict:
    return {
        "summary": {"industry_total": 0, "major_category_total": 0},
        "major_categories": [],
        "industries": [],
    }


def _blank_rule_catalog() -> dict:
    return {
        "version": "",
        "effective_date": "",
        "source": {},
        "rule_groups": [],
    }


def _blank_expanded_criteria_catalog() -> dict:
    return {
        "generated_at": "",
        "source": {},
        "summary": {},
        "industries": [],
        "rule_criteria_packs": [],
    }


def _blank_focus_scope_overrides() -> dict:
    return {
        "manual_rule_groups": [],
        "profile_overrides": [],
    }


def _load_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return ""


def _prompt_surface_excerpt_lines(text: str, limit: int = 4) -> list[str]:
    lines: list[str] = []
    for raw_line in str(text or "").splitlines():
        line = str(raw_line or "").strip()
        if not line:
            continue
        line = re.sub(r"^#+\s*", "", line)
        if line.startswith("- "):
            line = line[2:].strip()
        if not line:
            continue
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def _compact_critical_prompt_lens(packet: dict) -> dict:
    lens = dict((packet or {}).get("compact_decision_lens") or {})
    summary = dict((packet or {}).get("summary") or {})
    if not lens:
        return {}
    return {
        "lane_id": str(lens.get("lane_id", "") or "").strip(),
        "lane_title": str(lens.get("lane_title", "") or "").strip(),
        "bottleneck_statement": str(lens.get("bottleneck_statement", "") or "").strip(),
        "why_now": str(lens.get("why_now", "") or "").strip(),
        "inspect_first": str(lens.get("inspect_first", "") or "").strip(),
        "next_action": str(lens.get("next_action", "") or "").strip(),
        "success_metric": str(lens.get("success_metric", "") or "").strip(),
        "falsification_test": str(lens.get("falsification_test", "") or "").strip(),
        "founder_questions": [
            str(item or "").strip()
            for item in list(lens.get("founder_questions") or [])
            if str(item or "").strip()
        ][:3],
        "anti_patterns": [
            str(item or "").strip()
            for item in list(lens.get("anti_patterns") or [])
            if str(item or "").strip()
        ][:3],
        "evidence_first": [
            str(item or "").strip()
            for item in list(lens.get("evidence_first") or [])
            if str(item or "").strip()
        ],
        "lens_ready": bool(summary.get("compact_lens_ready", False)),
        "runtime_surface_contract_ready": bool(summary.get("runtime_surface_contract_ready", False)),
        "release_surface_contract_ready": bool(summary.get("release_surface_contract_ready", False)),
        "operator_surface_contract_ready": bool(summary.get("operator_surface_contract_ready", False)),
    }


def _blank_patent_evidence_bundle() -> dict:
    return {
        "summary": {},
        "families": [],
    }


def _blank_review_case_presets_report() -> dict:
    return {
        "summary": {},
        "families": [],
    }


def _blank_case_story_surface_report() -> dict:
    return {
        "summary": {},
        "families": [],
    }


def _blank_operator_demo_packet_report() -> dict:
    return {
        "summary": {},
        "source_paths": {},
        "families": [],
    }


def _blank_review_reason_decision_ladder_report() -> dict:
    return {
        "summary": {},
        "ladders": [],
    }


def _blank_critical_prompt_surface_packet() -> dict:
    return {
        "summary": {},
        "critical_prompt_block": {},
        "compact_decision_lens": {},
    }


def _load_catalog_file(path: Path) -> dict:
    if not path.exists():
        return _blank_catalog()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank_catalog()
    if not isinstance(loaded, dict):
        return _blank_catalog()
    base = _blank_catalog()
    base.update(loaded)
    if not isinstance(base.get("major_categories"), list):
        base["major_categories"] = []
    if not isinstance(base.get("industries"), list):
        base["industries"] = []
    if not isinstance(base.get("summary"), dict):
        base["summary"] = {"industry_total": 0, "major_category_total": 0}
    return base


def _merge_catalog_payloads(base_catalog: dict, *overlay_layers: tuple[str, dict]) -> dict:
    base = dict(base_catalog or {})
    base_summary = dict(base.get("summary") or {})
    merged_rows: list[dict] = []
    seen_codes: dict[str, int] = {}

    def _append_rows(rows: list[Any], source_name: str) -> None:
        for raw in list(rows or []):
            if not isinstance(raw, dict):
                continue
            row = dict(raw)
            service_code = str(row.get("service_code", "") or "").strip()
            if not service_code:
                continue
            if source_name in {"focus_seed_catalog", "focus_family_registry"}:
                row.setdefault("catalog_source_kind", source_name)
            index = seen_codes.get(service_code)
            if index is None:
                seen_codes[service_code] = len(merged_rows)
                merged_rows.append(row)
            else:
                merged_rows[index] = row

    _append_rows(list((base_catalog or {}).get("industries") or []), "base_catalog")
    for source_name, catalog in overlay_layers:
        _append_rows(list((catalog or {}).get("industries") or []), source_name)

    category_meta: dict[str, dict[str, str]] = {}
    category_counts: dict[str, int] = {}
    for row in merged_rows:
        major_code = str(row.get("major_code", "") or "").strip()
        major_name = str(row.get("major_name", "") or "").strip()
        if not major_code or not major_name:
            continue
        category_meta[major_code] = {"major_code": major_code, "major_name": major_name}
        category_counts[major_code] = int(category_counts.get(major_code, 0) or 0) + 1

    major_categories = [
        {
            "major_code": code,
            "major_name": str(meta.get("major_name", "") or "").strip(),
            "industry_count": int(category_counts.get(code, 0) or 0),
        }
        for code, meta in category_meta.items()
    ]
    major_categories.sort(key=lambda row: str(row.get("major_code", "")))
    merged_rows.sort(key=lambda row: (str(row.get("major_code", "")), str(row.get("service_name", ""))))

    catalog_source_counts: dict[str, int] = {}
    for row in merged_rows:
        kind = str(row.get("catalog_source_kind", "") or "").strip()
        if not kind:
            continue
        catalog_source_counts[kind] = int(catalog_source_counts.get(kind, 0) or 0) + 1

    base["industries"] = merged_rows
    base["major_categories"] = major_categories
    base_summary["industry_total"] = len(merged_rows)
    base_summary["major_category_total"] = len(major_categories)
    if catalog_source_counts.get("focus_seed_catalog"):
        base_summary["focus_seed_total"] = int(catalog_source_counts.get("focus_seed_catalog", 0) or 0)
    else:
        base_summary.pop("focus_seed_total", None)
    if catalog_source_counts.get("focus_family_registry"):
        base_summary["focus_family_registry_total"] = int(
            catalog_source_counts.get("focus_family_registry", 0) or 0
        )
    else:
        base_summary.pop("focus_family_registry_total", None)
    base["summary"] = base_summary
    return base


def _load_catalog(
    path: Path,
    *,
    merge_focus_seed: bool = True,
    merge_focus_family_registry: bool = True,
) -> dict:
    base = _load_catalog_file(path)
    overlay_layers: list[tuple[str, dict]] = []
    if merge_focus_seed:
        focus_seed_catalog = _load_catalog_file(DEFAULT_FOCUS_SEED_CATALOG_PATH)
        if list(focus_seed_catalog.get("industries") or []):
            overlay_layers.append(("focus_seed_catalog", focus_seed_catalog))
    if merge_focus_family_registry:
        focus_family_registry = _load_catalog_file(DEFAULT_FOCUS_FAMILY_REGISTRY_PATH)
        if list(focus_family_registry.get("industries") or []):
            overlay_layers.append(("focus_family_registry", focus_family_registry))
    if not overlay_layers:
        return base
    return _merge_catalog_payloads(base, *overlay_layers)


def _load_rule_catalog(path: Path) -> dict:
    if not path.exists():
        return _blank_rule_catalog()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank_rule_catalog()
    if not isinstance(loaded, dict):
        return _blank_rule_catalog()
    base = _blank_rule_catalog()
    base.update(loaded)
    groups = loaded.get("rule_groups")
    if not isinstance(groups, list):
        groups = loaded.get("rules")
    if not isinstance(groups, list):
        groups = []
    base["rule_groups"] = groups
    merged = _merge_expanded_rule_metadata(base, _load_expanded_criteria_catalog(DEFAULT_EXPANDED_CRITERIA_PATH))
    return _merge_manual_rule_groups(merged, _load_focus_scope_overrides(DEFAULT_FOCUS_SCOPE_OVERRIDES_PATH))


def _load_expanded_criteria_catalog(path: Path) -> dict:
    if not path.exists():
        return _blank_expanded_criteria_catalog()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank_expanded_criteria_catalog()
    if not isinstance(loaded, dict):
        return _blank_expanded_criteria_catalog()
    base = _blank_expanded_criteria_catalog()
    base.update(loaded)
    packs = loaded.get("rule_criteria_packs")
    if not isinstance(packs, list):
        packs = []
    industries = loaded.get("industries")
    if not isinstance(industries, list):
        industries = []
    base["industries"] = industries
    base["rule_criteria_packs"] = packs
    return base


def _load_focus_scope_overrides(path: Path) -> dict:
    if not path.exists():
        return _blank_focus_scope_overrides()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank_focus_scope_overrides()
    if not isinstance(loaded, dict):
        return _blank_focus_scope_overrides()
    base = _blank_focus_scope_overrides()
    base.update(loaded)
    if not isinstance(base.get("manual_rule_groups"), list):
        base["manual_rule_groups"] = []
    if not isinstance(base.get("profile_overrides"), list):
        base["profile_overrides"] = []
    return base


def _load_patent_evidence_bundle(path: Path) -> dict:
    if not path.exists():
        return _blank_patent_evidence_bundle()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank_patent_evidence_bundle()
    if not isinstance(loaded, dict):
        return _blank_patent_evidence_bundle()
    base = _blank_patent_evidence_bundle()
    base.update(loaded)
    if not isinstance(base.get("summary"), dict):
        base["summary"] = {}
    if not isinstance(base.get("families"), list):
        base["families"] = []
    return base


def _load_review_case_presets_report(path: Path) -> dict:
    if not path.exists():
        return _blank_review_case_presets_report()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank_review_case_presets_report()
    if not isinstance(loaded, dict):
        return _blank_review_case_presets_report()
    base = _blank_review_case_presets_report()
    base.update(loaded)
    if not isinstance(base.get("summary"), dict):
        base["summary"] = {}
    if not isinstance(base.get("families"), list):
        base["families"] = []
    return base


def _load_case_story_surface_report(path: Path) -> dict:
    if not path.exists():
        return _blank_case_story_surface_report()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank_case_story_surface_report()
    if not isinstance(loaded, dict):
        return _blank_case_story_surface_report()
    base = _blank_case_story_surface_report()
    base.update(loaded)
    if not isinstance(base.get("summary"), dict):
        base["summary"] = {}
    if not isinstance(base.get("families"), list):
        base["families"] = []
    return base


def _load_operator_demo_packet_report(path: Path) -> dict:
    if not path.exists():
        return _blank_operator_demo_packet_report()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank_operator_demo_packet_report()
    if not isinstance(loaded, dict):
        return _blank_operator_demo_packet_report()
    base = _blank_operator_demo_packet_report()
    base.update(loaded)
    if not isinstance(base.get("summary"), dict):
        base["summary"] = {}
    if not isinstance(base.get("source_paths"), dict):
        base["source_paths"] = {}
    if not isinstance(base.get("families"), list):
        base["families"] = []
    return base


def _load_review_reason_decision_ladder_report(path: Path) -> dict:
    if not path.exists():
        return _blank_review_reason_decision_ladder_report()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank_review_reason_decision_ladder_report()
    if not isinstance(loaded, dict):
        return _blank_review_reason_decision_ladder_report()
    base = _blank_review_reason_decision_ladder_report()
    base.update(loaded)
    if not isinstance(base.get("summary"), dict):
        base["summary"] = {}
    ladders = base.get("ladders")
    if not isinstance(ladders, list):
        base["ladders"] = list(base.get("decision_ladder") or []) if isinstance(base.get("decision_ladder"), list) else []
    return base


def _load_critical_prompt_surface_packet(path: Path) -> dict:
    if not path.exists():
        return _blank_critical_prompt_surface_packet()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank_critical_prompt_surface_packet()
    if not isinstance(loaded, dict):
        return _blank_critical_prompt_surface_packet()
    base = _blank_critical_prompt_surface_packet()
    base.update(loaded)
    if not isinstance(base.get("summary"), dict):
        base["summary"] = {}
    if not isinstance(base.get("critical_prompt_block"), dict):
        base["critical_prompt_block"] = {}
    if not isinstance(base.get("compact_decision_lens"), dict):
        base["compact_decision_lens"] = {}
    return base


def _build_expanded_industry_lookup(expanded_catalog: dict) -> dict:
    lookup = {}
    for row in list(expanded_catalog.get("industries") or []):
        if not isinstance(row, dict):
            continue
        code = str(row.get("service_code", "") or "").strip()
        if code:
            lookup[code] = dict(row)
    return lookup


def _merge_expanded_rule_metadata(rule_catalog: dict, expanded_catalog: dict) -> dict:
    base = dict(rule_catalog or {})
    groups = [dict(x) for x in list(base.get("rule_groups") or []) if isinstance(x, dict)]
    packs = [dict(x) for x in list(expanded_catalog.get("rule_criteria_packs") or []) if isinstance(x, dict)]
    if not groups or not packs:
        base["rule_groups"] = groups
        return base

    pack_by_rule_id = {}
    for pack in packs:
        rule_id = str(pack.get("rule_id", "") or "").strip()
        if rule_id and rule_id not in pack_by_rule_id:
            pack_by_rule_id[rule_id] = pack

    merged = []
    for group in groups:
        rule_id = str(group.get("rule_id", "") or "").strip()
        pack = pack_by_rule_id.get(rule_id)
        if not pack:
            merged.append(group)
            continue

        out = dict(group)
        pending = [x for x in list(out.get("pending_criteria_lines") or []) if isinstance(x, dict)]
        if pending:
            seen_pending = {
                (str(item.get("category", "") or "").strip(), str(item.get("text", "") or "").strip())
                for item in pending
            }
        else:
            seen_pending = set()
        for item in list(pack.get("additional_criteria_lines") or []):
            if not isinstance(item, dict):
                continue
            key = (
                str(item.get("category", "") or "").strip(),
                str(item.get("text", "") or "").strip(),
            )
            if key in seen_pending:
                continue
            seen_pending.add(key)
            pending.append(item)
        if pending:
            out["pending_criteria_lines"] = pending

        typed_existing = [x for x in list(out.get("typed_criteria") or []) if isinstance(x, dict)]
        typed_by_id = {
            str(item.get("criterion_id", "") or "").strip(): dict(item)
            for item in typed_existing
            if str(item.get("criterion_id", "") or "").strip()
        }
        for item in _synthesize_typed_criteria_from_pending(pending):
            typed_by_id.setdefault(str(item.get("criterion_id", "") or "").strip(), dict(item))
        if typed_by_id:
            out["typed_criteria"] = list(typed_by_id.values())

        docs_existing = [x for x in list(out.get("document_templates") or []) if isinstance(x, dict)]
        doc_by_id = {
            str(item.get("doc_id", "") or "").strip(): dict(item)
            for item in docs_existing
            if str(item.get("doc_id", "") or "").strip()
        }
        for item in _synthesize_document_templates(list(typed_by_id.values())):
            doc_by_id.setdefault(str(item.get("doc_id", "") or "").strip(), dict(item))
        if doc_by_id:
            out["document_templates"] = list(doc_by_id.values())

        mapping_meta = dict(out.get("mapping_meta") or {})
        if pending:
            mapping_meta.setdefault("coverage_status", "partial")
            mapping_meta.setdefault("manual_review_required", True)
        out["mapping_meta"] = mapping_meta
        merged.append(out)

    base["rule_groups"] = merged
    return base


def _merge_manual_rule_groups(rule_catalog: dict, overrides_catalog: dict) -> dict:
    base = dict(rule_catalog or {})
    groups = [dict(x) for x in list(base.get("rule_groups") or []) if isinstance(x, dict)]
    manual_groups = [dict(x) for x in list((overrides_catalog or {}).get("manual_rule_groups") or []) if isinstance(x, dict)]
    if not manual_groups:
        base["rule_groups"] = groups
        return base

    group_index = {}
    for idx, group in enumerate(groups):
        rule_id = str(group.get("rule_id", "") or "").strip()
        if rule_id and rule_id not in group_index:
            group_index[rule_id] = idx

    for raw_group in manual_groups:
        rule_id = str(raw_group.get("rule_id", "") or "").strip()
        if not rule_id:
            continue
        legal_basis = []
        for item in list(raw_group.get("legal_basis") or []):
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "") or "").strip()
            if not _is_objective_source_url(url):
                continue
            legal_basis.append(
                {
                    "law_title": str(item.get("law_title", "") or "").strip(),
                    "article": str(item.get("article", "") or "").strip(),
                    "url": url,
                }
            )
        if not legal_basis:
            continue

        out = dict(raw_group)
        out["rule_id"] = rule_id
        out["legal_basis"] = legal_basis
        out["aliases"] = [
            str(alias or "").strip() for alias in list(raw_group.get("aliases") or []) if str(alias or "").strip()
        ]
        out["service_codes"] = [
            str(code or "").strip() for code in list(raw_group.get("service_codes") or []) if str(code or "").strip()
        ]
        req_src = dict(raw_group.get("requirements") or {})
        out["requirements"] = {
            "capital_eok": _coerce_non_negative_float(req_src.get("capital_eok", 0)),
            "technicians": _coerce_non_negative_int(req_src.get("technicians", 0)),
            "equipment_count": _coerce_non_negative_int(req_src.get("equipment_count", 0)),
            "deposit_days": _coerce_non_negative_int(req_src.get("deposit_days", 0)),
        }

        pending = [dict(x) for x in list(raw_group.get("pending_criteria_lines") or []) if isinstance(x, dict)]
        if pending:
            out["pending_criteria_lines"] = pending

        typed_existing = [dict(x) for x in list(raw_group.get("typed_criteria") or []) if isinstance(x, dict)]
        typed_by_id = {
            str(item.get("criterion_id", "") or "").strip(): dict(item)
            for item in typed_existing
            if str(item.get("criterion_id", "") or "").strip()
        }
        for item in _synthesize_typed_criteria_from_pending(pending):
            typed_by_id.setdefault(str(item.get("criterion_id", "") or "").strip(), dict(item))
        if typed_by_id:
            out["typed_criteria"] = list(typed_by_id.values())

        docs_existing = [dict(x) for x in list(raw_group.get("document_templates") or []) if isinstance(x, dict)]
        doc_by_id = {
            str(item.get("doc_id", "") or "").strip(): dict(item)
            for item in docs_existing
            if str(item.get("doc_id", "") or "").strip()
        }
        for item in _synthesize_document_templates(list(typed_by_id.values())):
            doc_by_id.setdefault(str(item.get("doc_id", "") or "").strip(), dict(item))
        if doc_by_id:
            out["document_templates"] = list(doc_by_id.values())

        mapping_meta = dict(raw_group.get("mapping_meta") or {})
        if pending:
            mapping_meta.setdefault("coverage_status", "partial")
            mapping_meta.setdefault("manual_review_required", True)
        out["mapping_meta"] = mapping_meta

        if rule_id in group_index:
            groups[group_index[rule_id]] = out
        else:
            group_index[rule_id] = len(groups)
            groups.append(out)

    base["rule_groups"] = groups
    return base


_RE_NORMALIZE_KEY = re.compile(r"[^0-9a-z가-힣]+")


def _normalize_key(value) -> str:
    return _RE_NORMALIZE_KEY.sub("", str(value or "").strip().lower())


def _is_objective_source_url(url: str) -> bool:
    src = str(url or "").strip().lower()
    if not src.startswith("http"):
        return False
    return any(host in src for host in OBJECTIVE_SOURCE_HOSTS)


def _coerce_non_negative_float(value) -> float:
    try:
        out = float(value)
    except Exception:
        return 0.0
    if out != out or out < 0:
        return 0.0
    return out


def _coerce_non_negative_int(value) -> int:
    try:
        out = int(float(value))
    except Exception:
        return 0
    if out < 0:
        return 0
    return out


_PENDING_CRITERIA_TEMPLATES = {
    "office": {
        "criterion_id": "office.secured.auto",
        "category": "occupancy",
        "label": "사무실 또는 영업소 확보",
        "input_key": "office_secured",
        "value_type": "boolean",
        "operator": "==",
        "required_value": True,
        "blocking": True,
        "evidence_types": ["임대차계약서", "사업장 사진", "건축물대장"],
    },
    "facility_misc": {
        "criterion_id": "facility.secured.auto",
        "category": "facility",
        "label": "시설·장비·보관공간 확인",
        "input_key": "facility_secured",
        "value_type": "boolean",
        "operator": "==",
        "required_value": True,
        "blocking": False,
        "evidence_types": ["시설 보유 증빙", "장비 보유 명세", "현장 사진"],
    },
    "personnel_misc": {
        "criterion_id": "qualification.secured.auto",
        "category": "qualification",
        "label": "자격·교육·경력 요건 확인",
        "input_key": "qualification_secured",
        "value_type": "boolean",
        "operator": "==",
        "required_value": True,
        "blocking": False,
        "evidence_types": ["자격증", "교육이수증", "경력증명서"],
    },
    "insurance": {
        "criterion_id": "insurance.secured.auto",
        "category": "insurance",
        "label": "보험·보증 가입 확인",
        "input_key": "insurance_secured",
        "value_type": "boolean",
        "operator": "==",
        "required_value": True,
        "blocking": False,
        "evidence_types": ["보험가입 증명서", "보증서"],
    },
    "document": {
        "criterion_id": "document.ready.auto",
        "category": "document",
        "label": "필수 신고·등록·서류 준비",
        "input_key": "document_ready",
        "value_type": "boolean",
        "operator": "==",
        "required_value": True,
        "blocking": False,
        "evidence_types": ["신고증", "등록증", "신청서"],
    },
    "environment_safety": {
        "criterion_id": "safety.secured.auto",
        "category": "environment_safety",
        "label": "안전·환경 요건 확인",
        "input_key": "safety_secured",
        "value_type": "boolean",
        "operator": "==",
        "required_value": True,
        "blocking": False,
        "evidence_types": ["안전관리 계획서", "환경·안전 교육 증빙"],
    },
    "core_requirement": {
        "criterion_id": "facility.secured.auto",
        "category": "facility",
        "label": "시설·장비·보관공간 확인",
        "input_key": "facility_secured",
        "value_type": "boolean",
        "operator": "==",
        "required_value": True,
        "blocking": False,
        "evidence_types": ["시설 보유 증빙", "사업장 사진", "장비 명세"],
    },
    "guarantee": {
        "criterion_id": "guarantee.secured.auto",
        "category": "guarantee",
        "label": "보증금·이행보증 확인",
        "input_key": "insurance_secured",
        "value_type": "boolean",
        "operator": "==",
        "required_value": True,
        "blocking": False,
        "evidence_types": ["보증보험 증권", "이행보증서", "보증금 납부 영수증"],
    },
    "operations": {
        "criterion_id": "facility.secured.auto",
        "category": "facility",
        "label": "시설·장비·보관공간 확인",
        "input_key": "facility_secured",
        "value_type": "boolean",
        "operator": "==",
        "required_value": True,
        "blocking": False,
        "evidence_types": ["운영 계획서", "업무 매뉴얼", "관리 체계 증빙"],
    },
}


def _synthesize_typed_criteria_from_pending(pending_lines) -> list:
    out = []
    seen = set()
    for item in list(pending_lines or []):
        if not isinstance(item, dict):
            continue
        category = str(item.get("category", "") or "").strip()
        template = _PENDING_CRITERIA_TEMPLATES.get(category)
        if not template and category == "other":
            template = _PENDING_CRITERIA_TEMPLATES.get("facility_misc")
        if not template:
            continue
        criterion_id = str(template.get("criterion_id", "") or "").strip()
        if not criterion_id or criterion_id in seen:
            continue
        seen.add(criterion_id)
        row = dict(template)
        note = str(item.get("text", "") or "").strip()
        if note:
            row["label"] = str(row.get("label", criterion_id) or criterion_id).strip()
            row["note"] = note[:200]
        out.append(row)
    return out


def _synthesize_document_templates(typed_criteria) -> list:
    out = []
    seen = set()
    for criterion in list(typed_criteria or []):
        if not isinstance(criterion, dict):
            continue
        criterion_id = str(criterion.get("criterion_id", "") or "").strip()
        label = str(criterion.get("label", "") or criterion_id).strip()
        for idx, evidence in enumerate(list(criterion.get("evidence_types") or []), 1):
            evidence_label = str(evidence or "").strip()
            if not evidence_label:
                continue
            doc_id = f"auto::{criterion_id}::{idx}"
            if doc_id in seen:
                continue
            seen.add(doc_id)
            out.append(
                {
                    "doc_id": doc_id,
                    "label": evidence_label,
                    "linked_criteria": [criterion_id],
                    "subtitle": label,
                }
            )
    return out


def _expand_rule_groups(rule_catalog: dict) -> list:
    rows = []
    groups = list(rule_catalog.get("rule_groups") or [])
    for group in groups:
        if not isinstance(group, dict):
            continue
        rule_id = str(group.get("rule_id", "") or "").strip()
        if not rule_id:
            continue

        legal_basis = []
        for item in list(group.get("legal_basis") or []):
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "") or "").strip()
            if not _is_objective_source_url(url):
                continue
            legal_basis.append(
                {
                    "law_title": str(item.get("law_title", "") or "").strip(),
                    "article": str(item.get("article", "") or "").strip(),
                    "url": url,
                }
            )
        if not legal_basis:
            continue

        req_src = dict(group.get("requirements") or {})
        requirements = {
            "capital_eok": _coerce_non_negative_float(req_src.get("capital_eok", 0)),
            "technicians": _coerce_non_negative_int(req_src.get("technicians", 0)),
            "equipment_count": _coerce_non_negative_int(req_src.get("equipment_count", 0)),
            "deposit_days": _coerce_non_negative_int(req_src.get("deposit_days", 0)),
        }
        mapping_meta = dict(group.get("mapping_meta") or {})
        typed_criteria = [x for x in list(group.get("typed_criteria") or []) if isinstance(x, dict)]
        pending_criteria_lines = [x for x in list(group.get("pending_criteria_lines") or []) if isinstance(x, dict)]
        document_templates = [x for x in list(group.get("document_templates") or []) if isinstance(x, dict)]

        names = []
        single = str(group.get("industry_name", "") or "").strip()
        if single:
            names.append(single)
        for name in list(group.get("industry_names") or []):
            txt = str(name or "").strip()
            if txt:
                names.append(txt)
        dedup_names = []
        seen = set()
        for name in names:
            key = _normalize_key(name)
            if not key or key in seen:
                continue
            seen.add(key)
            dedup_names.append(name)
        if not dedup_names:
            continue

        aliases = [str(x or "").strip() for x in list(group.get("aliases") or []) if str(x or "").strip()]
        service_codes = [str(x or "").strip() for x in list(group.get("service_codes") or []) if str(x or "").strip()]
        include_in_selector = bool(group.get("include_in_selector", True))

        for idx, name in enumerate(dedup_names):
            rows.append(
                {
                    "rule_id": f"{rule_id}-{idx + 1}" if len(dedup_names) > 1 else rule_id,
                    "group_rule_id": rule_id,
                    "industry_name": name,
                    "aliases": list(aliases),
                    "service_codes": list(service_codes),
                    "requirements": dict(requirements),
                    "requirements_legacy": dict(requirements),
                    "legal_basis": list(legal_basis),
                    "mapping_meta": mapping_meta,
                    "typed_criteria": typed_criteria,
                    "pending_criteria_lines": pending_criteria_lines,
                    "document_templates": document_templates,
                    "include_in_selector": include_in_selector,
                }
            )
    return rows


def _build_rule_index(rule_catalog: dict) -> dict:
    rules = _expand_rule_groups(rule_catalog)
    by_service_code = {}
    by_key = {}
    for rule in rules:
        for code in list(rule.get("service_codes") or []):
            by_service_code[str(code)] = rule
        keys = [_normalize_key(rule.get("industry_name", ""))]
        keys.extend(_normalize_key(alias) for alias in list(rule.get("aliases") or []))
        for key in keys:
            if not key:
                continue
            if key not in by_key:
                by_key[key] = rule
    return {
        "rules": rules,
        "by_service_code": by_service_code,
        "by_key": by_key,
    }


def _resolve_rule_for_industry(industry: dict, rule_index: dict):
    service_code = str(industry.get("service_code", "") or "").strip()
    if service_code and service_code in rule_index.get("by_service_code", {}):
        return rule_index["by_service_code"][service_code]
    service_name = str(industry.get("service_name", "") or "").strip()
    if service_name:
        key = _normalize_key(service_name)
        hit = rule_index.get("by_key", {}).get(key)
        if hit:
            return hit
    return None


def evaluate_registration_diagnosis(
    rule: dict,
    current_capital_eok,
    current_technicians,
    current_equipment_count,
    raw_capital_input="",
    base_date: date | None = None,
    extra_inputs: Dict[str, Any] | None = None,
) -> dict:
    req = dict(rule.get("requirements") or {})

    required_capital = _coerce_non_negative_float(req.get("capital_eok", 0))
    required_technicians = _coerce_non_negative_int(req.get("technicians", 0))
    required_equipment = _coerce_non_negative_int(req.get("equipment_count", 0))
    deposit_days = _coerce_non_negative_int(req.get("deposit_days", 0))

    current_capital = _coerce_non_negative_float(current_capital_eok)
    current_tech = _coerce_non_negative_int(current_technicians)
    current_equipment = _coerce_non_negative_int(current_equipment_count)

    capital_gap = max(0.0, required_capital - current_capital)
    technician_gap = max(0, required_technicians - current_tech)
    equipment_gap = max(0, required_equipment - current_equipment)

    baseline = base_date or date.today()
    expected_date = baseline + timedelta(days=deposit_days)
    date_label = expected_date.strftime("%Y-%m-%d")

    raw_capital = str(raw_capital_input or "").strip().replace(",", "")
    suspicious = False
    if raw_capital:
        over_three_x = required_capital > 0 and current_capital > required_capital * 3
        decimal_pattern_odd = re.match(r"^\d+(\.\d{1,2})?$", raw_capital) is None
        likely_unit_mistake = re.match(r"^\d{2,}$", raw_capital) is not None and current_capital >= 10
        suspicious = bool(over_three_x or decimal_pattern_odd or likely_unit_mistake)

    capital_ok = capital_gap <= 0
    technicians_ok = technician_gap <= 0
    equipment_ok = equipment_gap <= 0
    typed_inputs = {
        "capital_eok": current_capital,
        "current_capital_eok": current_capital,
        "technicians": current_tech,
        "current_technicians": current_tech,
        "technicians_count": current_tech,
        "equipment_count": current_equipment,
        "current_equipment_count": current_equipment,
        "deposit_days": deposit_days,
        "raw_capital_input": raw_capital_input,
    }
    if isinstance(extra_inputs, dict):
        typed_inputs.update(extra_inputs)

    typed_eval = evaluate_typed_criteria(rule, typed_inputs, base_date=baseline)
    typed_status = str(typed_eval.get("overall_status") or "").strip().lower()
    typed_ok = typed_status in {"", "pass"}
    overall_ok = bool(capital_ok and technicians_ok and equipment_ok and typed_ok)

    return {
        "capital": {
            "required": required_capital,
            "current": current_capital,
            "gap": round(capital_gap, 4),
            "ok": capital_ok,
        },
        "technicians": {
            "required": required_technicians,
            "current": current_tech,
            "gap": technician_gap,
            "ok": technicians_ok,
        },
        "equipment": {
            "required": required_equipment,
            "current": current_equipment,
            "gap": equipment_gap,
            "ok": equipment_ok,
        },
        "deposit_days": deposit_days,
        "expected_diagnosis_date": date_label,
        "capital_input_suspicious": suspicious,
        "overall_ok": overall_ok,
        "typed_criteria_total": int(typed_eval.get("typed_criteria_total", 0) or 0),
        "criterion_results": list(typed_eval.get("criterion_results") or []),
        "evidence_checklist": list(typed_eval.get("evidence_checklist") or []),
        "manual_review_required": bool(typed_eval.get("manual_review_required", False)),
        "coverage_status": str(typed_eval.get("coverage_status") or ""),
        "mapping_confidence": typed_eval.get("mapping_confidence"),
        "typed_overall_status": str(typed_eval.get("overall_status") or ""),
        "pending_criteria_count": int(typed_eval.get("pending_criteria_count", 0) or 0),
        "blocking_failure_count": int(typed_eval.get("blocking_failure_count", 0) or 0),
        "unknown_blocking_count": int(typed_eval.get("unknown_blocking_count", 0) or 0),
        "next_actions": list(typed_eval.get("next_actions") or []),
    }


def _prepare_ui_payload(catalog: dict, rule_catalog: dict) -> dict:
    rule_index = _build_rule_index(rule_catalog)
    expanded_catalog = _load_expanded_criteria_catalog(DEFAULT_EXPANDED_CRITERIA_PATH)
    expanded_lookup = _build_expanded_industry_lookup(expanded_catalog)
    major_categories = []
    for row in list(catalog.get("major_categories") or []):
        if not isinstance(row, dict):
            continue
        major_code = str(row.get("major_code", "") or "").strip()
        major_name = str(row.get("major_name", "") or "").strip()
        if not major_code or not major_name:
            continue
        major_categories.append(
            {
                "major_code": major_code,
                "major_name": major_name,
                "industry_count": _coerce_non_negative_int(row.get("industry_count", 0)),
            }
        )

    industries = []
    rules_lookup = {}
    seen_codes = set()
    seen_rule_names = set()
    for row in list(catalog.get("industries") or []):
        if not isinstance(row, dict):
            continue
        service_code = str(row.get("service_code", "") or "").strip()
        service_name = str(row.get("service_name", "") or "").strip()
        major_code = str(row.get("major_code", "") or "").strip()
        major_name = str(row.get("major_name", "") or "").strip()
        if not service_code or not service_name or not major_code:
            continue
        if service_code in seen_codes:
            continue
        seen_codes.add(service_code)
        industry = {
            "service_code": service_code,
            "service_name": service_name,
            "major_code": major_code,
            "major_name": major_name,
            "group_code": str(row.get("group_code", "") or "").strip(),
            "group_name": str(row.get("group_name", "") or "").strip(),
            "group_description": str(row.get("group_description", "") or "").strip(),
            "group_declared_total": _coerce_non_negative_int(row.get("group_declared_total", 0)),
            "detail_url": str(row.get("detail_url", "") or "").strip(),
            "catalog_source_kind": str(row.get("catalog_source_kind", "") or "").strip(),
            "catalog_source_label": str(row.get("catalog_source_label", "") or "").strip(),
            "has_rule": bool(row.get("has_rule", False)),
        }
        for key in (
            "collection_status",
            "status",
            "mapping_status",
            "mapping_batch_id",
            "mapping_batch_seq",
            "mapping_group_key",
            "additional_criteria_count",
            "rule_pack_ref",
            "law_title",
            "legal_basis_title",
            "legal_basis",
            "criteria_summary",
            "criteria_additional",
            "criteria_source_type",
            "auto_law_candidates",
            "auto_collection_at",
            "auto_collection_error",
            "candidate_criteria_status",
            "candidate_criteria_count",
            "candidate_criteria_lines",
            "candidate_additional_criteria_lines",
            "candidate_legal_basis",
            "candidate_law_fetch_meta",
            "candidate_raw_text_preview",
            "candidate_extracted_at",
            "quality_flags",
            "registration_requirement_profile",
            "seed_rule_service_code",
            "seed_rule_id",
            "seed_law_family",
            "raw_source_proof",
        ):
            if key in row:
                industry[key] = row.get(key)
        expanded_row = expanded_lookup.get(service_code) or {}
        if expanded_row:
            for key in (
                "collection_status",
                "status",
                "mapping_status",
                "mapping_batch_id",
                "mapping_batch_seq",
                "mapping_group_key",
                "additional_criteria_count",
                "rule_pack_ref",
                "law_title",
                "legal_basis_title",
                "legal_basis",
                "criteria_summary",
                "criteria_additional",
                "criteria_source_type",
                "auto_law_candidates",
                "auto_collection_at",
                "auto_collection_error",
                "candidate_criteria_status",
                "candidate_criteria_count",
                "candidate_criteria_lines",
                "candidate_additional_criteria_lines",
                "candidate_legal_basis",
                "candidate_law_fetch_meta",
                "candidate_raw_text_preview",
                "candidate_extracted_at",
                "quality_flags",
                "registration_requirement_profile",
                "seed_rule_service_code",
                "seed_rule_id",
                "seed_law_family",
                "raw_source_proof",
            ):
                if key in expanded_row:
                    industry[key] = expanded_row.get(key)
        rule = _resolve_rule_for_industry(industry, rule_index)
        if rule:
            industry["has_rule"] = True
            rules_lookup[service_code] = rule
            seen_rule_names.add(_normalize_key(rule.get("industry_name", "")))
        industries.append(industry)

    rules_only_rows = []
    for rule in list(rule_index.get("rules") or []):
        if not bool(rule.get("include_in_selector", True)):
            continue
        key = _normalize_key(rule.get("industry_name", ""))
        if key and key in seen_rule_names:
            continue
        virtual_code = f"RULE::{rule.get('rule_id', '')}"
        if virtual_code in seen_codes:
            continue
        seen_codes.add(virtual_code)
        seen_rule_names.add(key)
        rules_only_rows.append(
            {
                "service_code": virtual_code,
                "service_name": str(rule.get("industry_name", "") or "").strip(),
                "major_code": RULES_ONLY_CATEGORY_CODE,
                "major_name": RULES_ONLY_CATEGORY_NAME,
                "group_code": "",
                "group_name": RULES_ONLY_CATEGORY_NAME,
                "group_description": "",
                "group_declared_total": 0,
                "detail_url": "",
                "has_rule": True,
                "is_rules_only": True,
            }
        )
        expanded_row = expanded_lookup.get(virtual_code) or {}
        if expanded_row:
            rules_only_rows[-1].update(
                {
                    key: expanded_row.get(key)
                    for key in (
                        "collection_status",
                        "status",
                        "mapping_status",
                        "mapping_batch_id",
                        "mapping_batch_seq",
                        "mapping_group_key",
                        "additional_criteria_count",
                        "rule_pack_ref",
                        "law_title",
                        "legal_basis_title",
                        "legal_basis",
                        "criteria_summary",
                        "criteria_additional",
                        "criteria_source_type",
                        "quality_flags",
                        "registration_requirement_profile",
                    )
                    if key in expanded_row
                }
            )
        rules_lookup[virtual_code] = rule

    if rules_only_rows:
        major_categories.append(
            {
                "major_code": RULES_ONLY_CATEGORY_CODE,
                "major_name": RULES_ONLY_CATEGORY_NAME,
                "industry_count": len(rules_only_rows),
            }
        )
        industries.extend(rules_only_rows)

    major_categories.sort(key=lambda x: str(x.get("major_code", "")))
    industries.sort(key=lambda x: (str(x.get("major_code", "")), str(x.get("service_name", ""))))

    summary = dict(catalog.get("summary") or {})
    real_industries = [row for row in industries if str(row.get("major_code", "") or "") != RULES_ONLY_CATEGORY_CODE]
    focus_target_rows = [
        row
        for row in industries
        if bool((row.get("registration_requirement_profile") or {}).get("focus_target"))
    ]
    focus_target_with_other_rows = [
        row
        for row in industries
        if bool((row.get("registration_requirement_profile") or {}).get("focus_target_with_other"))
    ]
    inferred_focus_rows = [
        row
        for row in industries
        if bool((row.get("registration_requirement_profile") or {}).get("inferred_focus_candidate"))
    ]
    real_focus_target_rows = [
        row
        for row in real_industries
        if bool((row.get("registration_requirement_profile") or {}).get("focus_target"))
    ]
    real_focus_target_with_other_rows = [
        row
        for row in real_industries
        if bool((row.get("registration_requirement_profile") or {}).get("focus_target_with_other"))
    ]
    real_with_rule_total = sum(1 for row in real_industries if bool(row.get("has_rule")))
    summary["industry_total"] = len(real_industries)
    summary["selector_industry_total"] = len(industries)
    summary["major_category_total"] = len(major_categories)
    summary["with_registration_rule_total"] = real_with_rule_total
    summary["rules_only_industry_total"] = len(rules_only_rows)
    summary["law_rule_total"] = len(list(rule_index.get("rules") or []))
    summary["candidate_law_total"] = sum(1 for row in real_industries if list(row.get("auto_law_candidates") or []))
    summary["candidate_criteria_total"] = sum(
        1 for row in real_industries if int(row.get("candidate_criteria_count", 0) or 0) > 0
    )
    summary["focus_target_total"] = len(focus_target_rows)
    summary["focus_target_with_other_total"] = len(focus_target_with_other_rows)
    summary["real_focus_target_total"] = len(real_focus_target_rows)
    summary["real_focus_target_with_other_total"] = len(real_focus_target_with_other_rows)
    summary["rules_only_focus_target_total"] = max(0, len(focus_target_rows) - len(real_focus_target_rows))
    summary["rules_only_focus_target_with_other_total"] = max(
        0,
        len(focus_target_with_other_rows) - len(real_focus_target_with_other_rows),
    )
    summary["inferred_focus_target_total"] = len(inferred_focus_rows)
    summary["focus_default_mode"] = "focus_only" if focus_target_rows else "all"
    industry_total = _coerce_non_negative_int(summary.get("industry_total", 0))
    with_rule_total = _coerce_non_negative_int(real_with_rule_total)
    pending_rule_total = max(0, industry_total - with_rule_total)
    coverage_pct = round((with_rule_total / industry_total) * 100.0, 2) if industry_total > 0 else 0.0
    summary["pending_rule_total"] = pending_rule_total
    summary["coverage_pct"] = coverage_pct
    summary["public_claim_level"] = "full" if coverage_pct >= 95.0 else "phased"
    if summary["public_claim_level"] == "full":
        summary["public_claim_message"] = "법령 연동 업종 커버리지가 95% 이상입니다."
    else:
        summary["public_claim_message"] = (
            f"현재 법령 연동 업종 중심으로 제공합니다. 미연동 업종 {pending_rule_total}건은 전문가 검토로 안내합니다."
        )

    return {
        "summary": summary,
        "major_categories": major_categories,
        "industries": industries,
        "rules_lookup": rules_lookup,
        "rule_catalog_meta": {
            "version": str(rule_catalog.get("version", "") or ""),
            "effective_date": str(rule_catalog.get("effective_date", "") or ""),
            "source": dict(rule_catalog.get("source") or {}),
        },
    }


def _compact_candidate_lines(rows) -> list:
    compact_rows = []
    for row in list(rows or []):
        if not isinstance(row, dict):
            continue
        text = str(row.get("text", "") or "").strip()
        if not text:
            continue
        compact_rows.append({"text": text})
    return compact_rows


def _compact_candidate_law_rows(rows) -> list:
    compact_rows = []
    for row in list(rows or []):
        if not isinstance(row, dict):
            continue
        law_title = str(row.get("law_title", "") or "").strip()
        article = str(row.get("article", "") or "").strip()
        url = str(row.get("url", "") or row.get("law_url", "") or "").strip()
        if not (law_title or article or url):
            continue
        compact_rows.append(
            {
                "law_title": law_title,
                "article": article,
                "url": url,
            }
        )
    return compact_rows


def _compact_raw_source_proof(proof: Any) -> dict:
    if not isinstance(proof, dict):
        return {}
    source_urls = [
        str(url or "").strip()
        for url in list(proof.get("source_urls") or [])
        if str(url or "").strip()
    ]
    compact = {
        "proof_status": str(proof.get("proof_status", "") or "").strip(),
        "official_snapshot_note": str(proof.get("official_snapshot_note", "") or "").strip(),
        "source_checksum": str(proof.get("source_checksum", "") or "").strip(),
        "source_urls": source_urls,
        "source_url_total": _coerce_non_negative_int(proof.get("source_url_total", len(source_urls))),
    }
    capture_meta = proof.get("capture_meta") or {}
    if isinstance(capture_meta, dict) and capture_meta:
        compact["capture_meta"] = {
            "captured_at": str(capture_meta.get("captured_at", "") or "").strip(),
            "capture_kind": str(capture_meta.get("capture_kind", "") or "").strip(),
            "scope_policy": str(capture_meta.get("scope_policy", "") or "").strip(),
            "family_key": str(capture_meta.get("family_key", "") or "").strip(),
            "catalog_source_kind": str(capture_meta.get("catalog_source_kind", "") or "").strip(),
        }
    return {key: value for key, value in compact.items() if value not in ("", [], {})}


def _build_claim_packet_lookup(bundle: dict) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for family in list((bundle or {}).get("families") or []):
        if not isinstance(family, dict):
            continue
        family_key = str(family.get("family_key", "") or "").strip()
        claim_packet = family.get("claim_packet") or {}
        if family_key and isinstance(claim_packet, dict) and claim_packet:
            lookup[family_key] = claim_packet
    return lookup


def _row_claim_family_key(row: dict) -> str:
    proof = row.get("raw_source_proof") or {}
    capture_meta = proof.get("capture_meta") or {} if isinstance(proof, dict) else {}
    candidates = (
        capture_meta.get("family_key"),
        row.get("law_title"),
        row.get("seed_law_family"),
    )
    for value in candidates:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _build_row_claim_packet_summary(row: dict, claim_packet_lookup: dict[str, dict]) -> dict:
    family_key = _row_claim_family_key(row)
    claim_packet = claim_packet_lookup.get(family_key) or {}
    if not isinstance(claim_packet, dict) or not claim_packet:
        return {}
    source_proof_summary = claim_packet.get("source_proof_summary") or {}
    raw_source_proof = _compact_raw_source_proof(row.get("raw_source_proof"))
    checksum_samples = [
        str(item or "").strip()
        for item in list(source_proof_summary.get("checksum_samples") or [])
        if str(item or "").strip()
    ][:3]
    source_url_samples = [
        str(item or "").strip()
        for item in list(source_proof_summary.get("source_url_samples") or [])
        if str(item or "").strip()
    ][:2]
    required_input_domains = [
        str(item or "").strip()
        for item in list(claim_packet.get("required_input_domains") or [])
        if str(item or "").strip()
    ]
    optional_input_domains = [
        str(item or "").strip()
        for item in list(claim_packet.get("optional_input_domains") or [])
        if str(item or "").strip()
    ]
    compact = {
        "family_key": family_key,
        "claim_id": str(claim_packet.get("claim_id", "") or "").strip(),
        "claim_title": str(claim_packet.get("claim_title", "") or "").strip(),
        "claim_statement": str(claim_packet.get("claim_statement", "") or "").strip(),
        "required_input_domains": required_input_domains,
        "optional_input_domains": optional_input_domains,
        "proof_coverage_ratio": str(source_proof_summary.get("proof_coverage_ratio", "") or "").strip(),
        "checksum_sample_total": _coerce_non_negative_int(
            source_proof_summary.get("checksum_sample_total", len(checksum_samples))
        ),
        "checksum_samples": checksum_samples,
        "source_url_total": _coerce_non_negative_int(
            source_proof_summary.get("source_url_total", len(source_url_samples))
        ),
        "source_url_samples": source_url_samples,
        "official_snapshot_note": str(
            raw_source_proof.get("official_snapshot_note", "")
            or claim_packet.get("official_snapshot_note", "")
        ).strip(),
    }
    return {key: value for key, value in compact.items() if value not in ("", [], {})}


def _attach_claim_packet_summaries(rows: list[dict], patent_bundle: dict) -> list[dict]:
    claim_packet_lookup = _build_claim_packet_lookup(patent_bundle)
    if not claim_packet_lookup:
        return [dict(row) for row in list(rows or []) if isinstance(row, dict)]
    enriched_rows: list[dict] = []
    for row in list(rows or []):
        if not isinstance(row, dict):
            continue
        enriched = dict(row)
        summary = _build_row_claim_packet_summary(enriched, claim_packet_lookup)
        if summary:
            enriched["claim_packet_summary"] = summary
        enriched_rows.append(enriched)
    return enriched_rows


def _build_review_case_preset_lookup(report: dict) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for family in list((report or {}).get("families") or []):
        if not isinstance(family, dict):
            continue
        family_key = str(family.get("family_key", "") or "").strip()
        if family_key:
            lookup[family_key] = family
    return lookup


def _build_case_story_surface_lookup(report: dict) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for family in list((report or {}).get("families") or []):
        if not isinstance(family, dict):
            continue
        family_key = str(family.get("family_key", "") or "").strip()
        if family_key:
            lookup[family_key] = family
    return lookup


def _build_operator_demo_lookup(report: dict) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for family in list((report or {}).get("families") or []):
        if not isinstance(family, dict):
            continue
        family_key = str(family.get("family_key", "") or "").strip()
        if family_key:
            lookup[family_key] = family
    return lookup


def _compact_review_case_preset(preset: dict) -> dict:
    input_payload = preset.get("input_payload") if isinstance(preset.get("input_payload"), dict) else {}
    expected_outcome = preset.get("expected_outcome") if isinstance(preset.get("expected_outcome"), dict) else {}
    compact = {
        "preset_id": str(preset.get("preset_id", "") or "").strip(),
        "case_id": str(preset.get("case_id", "") or "").strip(),
        "case_kind": str(preset.get("case_kind", "") or "").strip(),
        "preset_label": str(preset.get("preset_label", "") or "").strip(),
        "service_code": str(preset.get("service_code", "") or "").strip(),
        "service_name": str(preset.get("service_name", "") or "").strip(),
        "legal_basis_title": str(preset.get("legal_basis_title", "") or "").strip(),
        "operator_note": str(preset.get("operator_note", "") or "").strip(),
        "input_payload": {
            "industry_selector": str(input_payload.get("industry_selector", "") or "").strip(),
            "capital_eok": round(_coerce_non_negative_float(input_payload.get("capital_eok", 0)), 2),
            "technicians_count": _coerce_non_negative_int(input_payload.get("technicians_count", 0)),
            "other_requirement_checklist": (
                dict(input_payload.get("other_requirement_checklist"))
                if isinstance(input_payload.get("other_requirement_checklist"), dict)
                else {}
            ),
        },
        "expected_outcome": {
            "overall_status": str(expected_outcome.get("overall_status", "") or "").strip(),
            "capital_gap_eok": round(_coerce_non_negative_float(expected_outcome.get("capital_gap_eok", 0)), 2),
            "technicians_gap": _coerce_non_negative_int(expected_outcome.get("technicians_gap", 0)),
            "review_reason": str(expected_outcome.get("review_reason", "") or "").strip(),
            "manual_review_expected": bool(expected_outcome.get("manual_review_expected", False)),
            "proof_coverage_ratio": str(expected_outcome.get("proof_coverage_ratio", "") or "").strip(),
        },
    }
    return {
        key: value
        for key, value in compact.items()
        if value not in ("", [], {}) and value is not None
    }


def _compact_case_story_surface(family: dict) -> dict:
    representative_cases = []
    review_reasons: list[str] = []
    for item in list(family.get("representative_cases") or []):
        if not isinstance(item, dict):
            continue
        review_reason = str(item.get("review_reason", "") or "").strip()
        if review_reason and review_reason not in review_reasons:
            review_reasons.append(review_reason)
        representative_cases.append(
            {
                "preset_id": str(item.get("preset_id", "") or "").strip(),
                "case_kind": str(item.get("case_kind", "") or "").strip(),
                "service_code": str(item.get("service_code", "") or "").strip(),
                "service_name": str(item.get("service_name", "") or "").strip(),
                "expected_status": str(item.get("expected_status", "") or "").strip(),
                "review_reason": review_reason,
                "manual_review_expected": bool(item.get("manual_review_expected", False)),
            }
        )
    compact = {
        "family_key": str(family.get("family_key", "") or "").strip(),
        "claim_id": str(family.get("claim_id", "") or "").strip(),
        "preset_total": _coerce_non_negative_int(family.get("preset_total", 0)),
        "manual_review_preset_total": _coerce_non_negative_int(family.get("manual_review_preset_total", 0)),
        "review_reason_total": len(review_reasons),
        "review_reasons": review_reasons,
        "representative_cases": representative_cases[:3],
        "operator_story_points": [
            str(item or "").strip()
            for item in list(family.get("operator_story_points") or [])
            if str(item or "").strip()
        ][:3],
    }
    return {
        key: value
        for key, value in compact.items()
        if value not in ("", [], {}) and value is not None
    }


def _compact_operator_demo_family(family: dict) -> dict:
    demo_cases = []
    review_reasons: list[str] = []
    representative_services: list[str] = []
    manual_review_demo_total = 0
    for item in list(family.get("demo_cases") or []):
        if not isinstance(item, dict):
            continue
        review_reason = str(item.get("review_reason", "") or "").strip()
        if review_reason and review_reason not in review_reasons:
            review_reasons.append(review_reason)
        service_name = str(item.get("service_name", "") or item.get("service_code", "") or "").strip()
        if service_name and service_name not in representative_services:
            representative_services.append(service_name)
        manual_review_expected = bool(item.get("manual_review_expected", False))
        if manual_review_expected:
            manual_review_demo_total += 1
        demo_cases.append(
            {
                "preset_id": str(item.get("preset_id", "") or "").strip(),
                "case_kind": str(item.get("case_kind", "") or "").strip(),
                "service_code": str(item.get("service_code", "") or "").strip(),
                "service_name": str(item.get("service_name", "") or "").strip(),
                "review_reason": review_reason,
                "expected_status": str(item.get("expected_status", "") or "").strip(),
                "manual_review_expected": manual_review_expected,
                "proof_coverage_ratio": str(item.get("proof_coverage_ratio", "") or "").strip(),
                "operator_note": str(item.get("operator_note", "") or "").strip(),
            }
        )
    compact = {
        "family_key": str(family.get("family_key", "") or "").strip(),
        "claim_id": str(family.get("claim_id", "") or "").strip(),
        "claim_title": str(family.get("claim_title", "") or "").strip(),
        "proof_coverage_ratio": str(family.get("proof_coverage_ratio", "") or "").strip(),
        "demo_case_total": len(demo_cases),
        "manual_review_demo_total": manual_review_demo_total,
        "review_reason_total": len(review_reasons),
        "review_reasons": review_reasons,
        "representative_services": representative_services[:3],
        "operator_story_points": [
            str(item or "").strip()
            for item in list(family.get("operator_story_points") or [])
            if str(item or "").strip()
        ][:3],
        "prompt_case_binding": {
            key: value
            for key, value in dict(family.get("prompt_case_binding") or {}).items()
            if value not in ("", [], {}) and value is not None
        },
        "demo_cases": demo_cases[:3],
    }
    return {
        key: value
        for key, value in compact.items()
        if value not in ("", [], {}) and value is not None
    }


def _compact_runtime_reasoning_ladder_map(report: dict) -> dict:
    ladder_map: dict[str, dict] = {}
    for item in list(report.get("ladders") or []):
        if not isinstance(item, dict):
            continue
        review_reason = str(item.get("review_reason", "") or "").strip()
        if not review_reason:
            continue
        ladder_map[review_reason] = {
            key: value
            for key, value in {
                "review_reason": review_reason,
                "inspect_first": str(item.get("inspect_first", "") or "").strip(),
                "next_action": str(item.get("next_action", "") or "").strip(),
                "manual_review_gate": bool(item.get("manual_review_gate", False)),
                "evidence_first": [
                    str(token or "").strip()
                    for token in list(item.get("evidence_first") or [])
                    if str(token or "").strip()
                ],
                "missing_input_focus": [
                    str(token or "").strip()
                    for token in list(item.get("missing_input_focus") or [])
                    if str(token or "").strip()
                ],
                "binding_preset_ids": [
                    str(token or "").strip()
                    for token in list(item.get("binding_preset_ids") or [])
                    if str(token or "").strip()
                ][:3],
                "binding_questions": [
                    str(token or "").strip()
                    for token in list(item.get("binding_questions") or [])
                    if str(token or "").strip()
                ][:2],
            }.items()
            if value not in ("", [], {}) and value is not None
        }
    return ladder_map


def _attach_review_case_artifacts(
    rows: list[dict],
    review_case_presets_report: dict,
    case_story_surface_report: dict,
) -> list[dict]:
    preset_lookup = _build_review_case_preset_lookup(review_case_presets_report)
    story_lookup = _build_case_story_surface_lookup(case_story_surface_report)
    if not preset_lookup and not story_lookup:
        return [dict(row) for row in list(rows or []) if isinstance(row, dict)]

    enriched_rows: list[dict] = []
    for row in list(rows or []):
        if not isinstance(row, dict):
            continue
        enriched = dict(row)
        family_key = _row_claim_family_key(enriched)
        if family_key:
            preset_family = preset_lookup.get(family_key) or {}
            story_family = story_lookup.get(family_key) or {}
            compact_presets = [
                _compact_review_case_preset(item)
                for item in list(preset_family.get("presets") or [])
                if isinstance(item, dict)
            ]
            compact_presets = [item for item in compact_presets if item]
            if compact_presets:
                enriched["review_case_presets"] = compact_presets
            compact_story = _compact_case_story_surface(story_family) if isinstance(story_family, dict) else {}
            if compact_story:
                enriched["case_story_surface"] = compact_story
        enriched_rows.append(enriched)
    return enriched_rows


def _attach_operator_demo_artifacts(rows: list[dict], operator_demo_packet_report: dict) -> list[dict]:
    demo_lookup = _build_operator_demo_lookup(operator_demo_packet_report)
    if not demo_lookup:
        return [dict(row) for row in list(rows or []) if isinstance(row, dict)]

    enriched_rows: list[dict] = []
    for row in list(rows or []):
        if not isinstance(row, dict):
            continue
        enriched = dict(row)
        family_key = _row_claim_family_key(enriched)
        if family_key:
            demo_family = demo_lookup.get(family_key) or {}
            compact_demo = _compact_operator_demo_family(demo_family) if isinstance(demo_family, dict) else {}
            if compact_demo:
                enriched["operator_demo_surface"] = compact_demo
        enriched_rows.append(enriched)
    return enriched_rows


def _compact_industry_row_for_client(row: dict) -> dict:
    compact = {
        "service_code": str(row.get("service_code", "") or "").strip(),
        "service_name": str(row.get("service_name", "") or "").strip(),
        "major_code": str(row.get("major_code", "") or "").strip(),
        "major_name": str(row.get("major_name", "") or "").strip(),
        "group_name": str(row.get("group_name", "") or "").strip(),
        "has_rule": bool(row.get("has_rule")),
        "is_rules_only": bool(row.get("is_rules_only")),
        "candidate_criteria_count": _coerce_non_negative_int(row.get("candidate_criteria_count", 0)),
    }
    catalog_source_kind = str(row.get("catalog_source_kind", "") or "").strip()
    if catalog_source_kind:
        compact["catalog_source_kind"] = catalog_source_kind
    catalog_source_label = str(row.get("catalog_source_label", "") or "").strip()
    if catalog_source_label:
        compact["catalog_source_label"] = catalog_source_label
    law_title = str(row.get("law_title", "") or "").strip()
    if law_title:
        compact["law_title"] = law_title
    legal_basis_title = str(row.get("legal_basis_title", "") or "").strip()
    if legal_basis_title:
        compact["legal_basis_title"] = legal_basis_title
    criteria_source_type = str(row.get("criteria_source_type", "") or "").strip()
    if criteria_source_type:
        compact["criteria_source_type"] = criteria_source_type
    quality_flags = [str(flag).strip() for flag in list(row.get("quality_flags") or []) if str(flag).strip()]
    if quality_flags:
        compact["quality_flags"] = quality_flags
    registration_requirement_profile = row.get("registration_requirement_profile") or {}
    if isinstance(registration_requirement_profile, dict) and registration_requirement_profile:
        compact["registration_requirement_profile"] = dict(registration_requirement_profile)
    auto_law_candidates = _compact_candidate_law_rows(row.get("auto_law_candidates"))
    if auto_law_candidates:
        compact["auto_law_candidates"] = auto_law_candidates
    candidate_criteria_lines = _compact_candidate_lines(row.get("candidate_criteria_lines"))
    if candidate_criteria_lines:
        compact["candidate_criteria_lines"] = candidate_criteria_lines
    candidate_additional = _compact_candidate_lines(row.get("candidate_additional_criteria_lines"))
    if candidate_additional:
        compact["candidate_additional_criteria_lines"] = candidate_additional
    candidate_legal_basis = _compact_candidate_law_rows(row.get("candidate_legal_basis"))
    if candidate_legal_basis:
        compact["candidate_legal_basis"] = candidate_legal_basis
    seed_rule_service_code = str(row.get("seed_rule_service_code", "") or "").strip()
    if seed_rule_service_code:
        compact["seed_rule_service_code"] = seed_rule_service_code
    seed_rule_id = str(row.get("seed_rule_id", "") or "").strip()
    if seed_rule_id:
        compact["seed_rule_id"] = seed_rule_id
    seed_law_family = str(row.get("seed_law_family", "") or "").strip()
    if seed_law_family:
        compact["seed_law_family"] = seed_law_family
    raw_source_proof = _compact_raw_source_proof(row.get("raw_source_proof"))
    if raw_source_proof:
        compact["raw_source_proof"] = raw_source_proof
    claim_packet_summary = row.get("claim_packet_summary") or {}
    if isinstance(claim_packet_summary, dict) and claim_packet_summary:
        compact["claim_packet_summary"] = {
            key: value
            for key, value in claim_packet_summary.items()
            if value not in ("", [], {})
        }
    review_case_presets = [
        item
        for item in list(row.get("review_case_presets") or [])
        if isinstance(item, dict) and item
    ]
    if review_case_presets:
        compact["review_case_presets"] = review_case_presets
    case_story_surface = row.get("case_story_surface") or {}
    if isinstance(case_story_surface, dict) and case_story_surface:
        compact["case_story_surface"] = {
            key: value
            for key, value in case_story_surface.items()
            if value not in ("", [], {})
        }
    operator_demo_surface = row.get("operator_demo_surface") or {}
    if isinstance(operator_demo_surface, dict) and operator_demo_surface:
        compact["operator_demo_surface"] = {
            key: value
            for key, value in operator_demo_surface.items()
            if value not in ("", [], {})
        }
    return compact


def _is_capital_technical_scope(row: dict) -> bool:
    profile = row.get("registration_requirement_profile") or {}
    if not isinstance(profile, dict):
        return False
    return bool(profile.get("capital_required")) and bool(profile.get("technical_personnel_required"))


def _build_major_categories_for_rows(rows: list[dict]) -> list[dict]:
    category_meta: dict[str, dict[str, str]] = {}
    category_counts: dict[str, int] = {}
    for row in list(rows or []):
        if not isinstance(row, dict):
            continue
        code = str(row.get("major_code", "") or "").strip()
        name = str(row.get("major_name", "") or "").strip()
        if not code or not name:
            continue
        category_counts[code] = int(category_counts.get(code, 0) or 0) + 1
        category_meta[code] = {"major_code": code, "major_name": name}
    out = [
        {
            "major_code": str(meta.get("major_code", "") or "").strip(),
            "major_name": str(meta.get("major_name", "") or "").strip(),
            "industry_count": int(category_counts.get(code, 0) or 0),
        }
        for code, meta in category_meta.items()
    ]
    out.sort(key=lambda row: str(row.get("major_code", "")))
    return out


def _build_selector_entry(row: dict, selector_kind: str) -> dict:
    compact = _compact_industry_row_for_client(row)
    canonical_service_code = str(compact.get("service_code", "") or "").strip()
    selector_suffix = canonical_service_code
    if selector_suffix.startswith("FOCUS::"):
        selector_suffix = selector_suffix.split("FOCUS::", 1)[1]
    kind = str(selector_kind or "").strip().lower()
    if kind == "inferred":
        selector_category_code = "SEL-INFERRED"
        selector_category_name = "추론 점검군"
        selector_code = f"SEL::INFERRED::{selector_suffix}"
    else:
        selector_category_code = "SEL-FOCUS"
        selector_category_name = "핵심 업종군"
        selector_code = f"SEL::FOCUS::{selector_suffix}"
    compact["selector_kind"] = kind or "focus"
    compact["selector_code"] = selector_code
    compact["canonical_service_code"] = canonical_service_code
    compact["selector_category_code"] = selector_category_code
    compact["selector_category_name"] = selector_category_name
    return compact


def _build_selector_catalog_row(selector_entry: dict) -> dict:
    row = dict(selector_entry or {})
    selector_code = str(row.get("selector_code", "") or "").strip()
    selector_category_code = str(row.get("selector_category_code", "") or "").strip()
    selector_category_name = str(row.get("selector_category_name", "") or "").strip()
    canonical_service_code = str(
        row.get("canonical_service_code", row.get("service_code", "")) or ""
    ).strip()
    row["service_code"] = selector_code
    row["major_code"] = selector_category_code
    row["major_name"] = selector_category_name
    row["canonical_service_code"] = canonical_service_code
    row["is_selector_row"] = True
    return row


def _build_selector_catalog(
    focus_selector_entries: list[dict], inferred_selector_entries: list[dict]
) -> dict:
    categories = []
    rows = []
    if focus_selector_entries:
        categories.append(
            {
                "major_code": "SEL-FOCUS",
                "major_name": "핵심 업종군",
                "industry_count": len(focus_selector_entries),
            }
        )
        rows.extend(_build_selector_catalog_row(row) for row in focus_selector_entries)
    if inferred_selector_entries:
        categories.append(
            {
                "major_code": "SEL-INFERRED",
                "major_name": "추론 점검군",
                "industry_count": len(inferred_selector_entries),
            }
        )
        rows.extend(_build_selector_catalog_row(row) for row in inferred_selector_entries)
    rows.sort(key=lambda row: (str(row.get("major_code", "")), str(row.get("service_name", ""))))
    return {
        "major_categories": categories,
        "industries": rows,
        "summary": {
            "selector_category_total": len(categories),
            "selector_entry_total": len(rows),
            "selector_focus_total": len(focus_selector_entries),
            "selector_inferred_total": len(inferred_selector_entries),
            "selector_real_entry_total": sum(1 for row in rows if not bool(row.get("is_rules_only"))),
            "selector_rules_only_entry_total": sum(1 for row in rows if bool(row.get("is_rules_only"))),
        },
    }


def _normalize_selector_alias(row: dict) -> dict:
    return {
        "selector_code": str(row.get("service_code", row.get("selector_code", "")) or "").strip(),
        "service_name": str(row.get("service_name", "") or "").strip(),
        "selector_kind": str(row.get("selector_kind", "") or "").strip(),
        "selector_category_code": str(row.get("selector_category_code", row.get("major_code", "")) or "").strip(),
        "selector_category_name": str(row.get("selector_category_name", row.get("major_name", "")) or "").strip(),
    }


def _build_platform_catalog(compact_rows: list[dict], selector_catalog: dict) -> dict:
    platform_rows = []
    real_rows = []
    focus_registry_rows = []
    target_rows_by_code: dict[str, dict] = {}

    for row in list(compact_rows or []):
        if not isinstance(row, dict):
            continue
        out = dict(row)
        canonical_service_code = str(out.get("service_code", "") or "").strip()
        out["canonical_service_code"] = canonical_service_code
        out["platform_selector_aliases"] = []
        out["platform_has_focus_alias"] = False
        out["platform_has_inferred_alias"] = False
        out["is_platform_row"] = True
        major_code = str(out.get("major_code", "") or "").strip()
        if major_code == RULES_ONLY_CATEGORY_CODE:
            out["platform_row_origin"] = "focus_registry_source"
            focus_registry_rows.append(out)
        else:
            out["platform_row_origin"] = "real_catalog"
            real_rows.append(out)
        platform_rows.append(out)
        if canonical_service_code:
            target_rows_by_code[canonical_service_code] = out

    selector_alias_total = 0
    absorbed_rows = []
    for selector_row in list((selector_catalog.get("industries") or []) if isinstance(selector_catalog, dict) else []):
        if not isinstance(selector_row, dict):
            continue
        alias = _normalize_selector_alias(selector_row)
        selector_code = str(alias.get("selector_code", "") or "").strip()
        selector_kind = str(alias.get("selector_kind", "") or "").strip()
        canonical_service_code = str(
            selector_row.get("canonical_service_code", selector_row.get("service_code", "")) or ""
        ).strip()
        if not selector_code:
            continue
        selector_alias_total += 1
        target = target_rows_by_code.get(canonical_service_code)
        if target:
            aliases = list(target.get("platform_selector_aliases") or [])
            aliases.append(alias)
            target["platform_selector_aliases"] = aliases
            if selector_kind == "focus":
                target["platform_has_focus_alias"] = True
            if selector_kind == "inferred":
                target["platform_has_inferred_alias"] = True
            continue

        absorbed = dict(selector_row)
        absorbed["service_code"] = canonical_service_code or selector_code
        absorbed["canonical_service_code"] = canonical_service_code or selector_code
        absorbed["platform_row_origin"] = "focus_source_absorbed"
        absorbed["platform_selector_aliases"] = [alias]
        absorbed["platform_has_focus_alias"] = selector_kind == "focus"
        absorbed["platform_has_inferred_alias"] = selector_kind == "inferred"
        absorbed["is_platform_row"] = True
        platform_rows.append(absorbed)
        absorbed_rows.append(absorbed)

    category_meta: dict[str, dict] = {}
    category_counts: dict[str, int] = {}
    for row in platform_rows:
        code = str(row.get("major_code", "") or "").strip()
        name = str(row.get("major_name", "") or "").strip()
        if not code or not name:
            continue
        category_counts[code] = int(category_counts.get(code, 0) or 0) + 1
        category_meta[code] = {"major_code": code, "major_name": name}
    major_categories = [
        {
            "major_code": str(meta.get("major_code", "") or "").strip(),
            "major_name": str(meta.get("major_name", "") or "").strip(),
            "industry_count": int(category_counts.get(code, 0) or 0),
        }
        for code, meta in category_meta.items()
    ]
    major_categories.sort(key=lambda row: str(row.get("major_code", "")))
    platform_rows.sort(key=lambda row: (str(row.get("major_code", "")), str(row.get("service_name", ""))))

    return {
        "major_categories": major_categories,
        "industries": platform_rows,
        "summary": {
            "platform_category_total": len(major_categories),
            "platform_industry_total": len(platform_rows),
            "platform_real_row_total": len(real_rows),
            "platform_focus_registry_row_total": len(focus_registry_rows),
            "platform_promoted_selector_total": 0,
            "platform_absorbed_focus_total": len(absorbed_rows),
            "platform_real_with_selector_alias_total": sum(
                1 for row in real_rows if list(row.get("platform_selector_aliases") or [])
            ),
            "platform_focus_registry_with_alias_total": sum(
                1 for row in focus_registry_rows if list(row.get("platform_selector_aliases") or [])
            ),
            "platform_focus_alias_total": sum(1 for row in platform_rows if bool(row.get("platform_has_focus_alias"))),
            "platform_inferred_alias_total": sum(
                1 for row in platform_rows if bool(row.get("platform_has_inferred_alias"))
            ),
            "platform_focus_absorbed_total": sum(
                1 for row in absorbed_rows if bool(row.get("platform_has_focus_alias"))
            ),
            "platform_inferred_absorbed_total": sum(
                1 for row in absorbed_rows if bool(row.get("platform_has_inferred_alias"))
            ),
            "platform_selector_alias_total": selector_alias_total,
        },
    }


def _build_master_catalog(platform_catalog: dict, selector_catalog: dict) -> dict:
    platform_summary = (
        dict(platform_catalog.get("summary") or {}) if isinstance(platform_catalog, dict) else {}
    )
    selector_summary = (
        dict(selector_catalog.get("summary") or {}) if isinstance(selector_catalog, dict) else {}
    )
    master_rows = []
    for row in list(platform_catalog.get("industries") or []) if isinstance(platform_catalog, dict) else []:
        if not isinstance(row, dict):
            continue
        out = dict(row)
        origin = str(out.get("platform_row_origin", "") or "").strip()
        canonical_service_code = str(
            out.get("canonical_service_code", out.get("service_code", "")) or ""
        ).strip()
        if origin == "selector_promoted" and canonical_service_code:
            out["service_code"] = canonical_service_code
            out["master_row_origin"] = "canonicalized_selector_promoted"
        elif origin == "focus_registry_source":
            out["service_code"] = canonical_service_code or str(out.get("service_code", "") or "").strip()
            out["canonical_service_code"] = canonical_service_code or str(out.get("service_code", "") or "").strip()
            out["master_row_origin"] = "focus_registry_source"
        elif origin == "focus_source_absorbed":
            out["service_code"] = canonical_service_code or str(out.get("service_code", "") or "").strip()
            out["canonical_service_code"] = canonical_service_code or str(out.get("service_code", "") or "").strip()
            out["master_row_origin"] = "focus_source_absorbed"
        else:
            out["master_row_origin"] = origin or "real_catalog"
        master_rows.append(out)
    return {
        "major_categories": list(platform_catalog.get("major_categories") or [])
        if isinstance(platform_catalog, dict)
        else [],
        "industries": master_rows,
        "feed_contract": {
            "primary_feed_name": "master_catalog",
            "overlay_feed_name": "selector_catalog",
            "primary_row_key": "service_code",
            "canonical_row_key": "canonical_service_code",
            "alias_list_field": "platform_selector_aliases",
            "focus_category_code": "SEL-FOCUS",
            "inferred_overlay_category_code": "SEL-INFERRED",
            "focus_registry_row_key_policy": "focus_registry_source rows use canonical_service_code as primary service_code",
            "absorbed_row_key_policy": "focus_source_absorbed rows use canonical_service_code as primary service_code",
        },
        "summary": {
            "master_category_total": int(platform_summary.get("platform_category_total", 0) or 0),
            "master_industry_total": int(platform_summary.get("platform_industry_total", 0) or 0),
            "master_real_row_total": int(platform_summary.get("platform_real_row_total", 0) or 0),
            "master_focus_registry_row_total": int(
                platform_summary.get("platform_focus_registry_row_total", 0) or 0
            ),
            "master_promoted_row_total": 0,
            "master_absorbed_row_total": int(
                platform_summary.get("platform_absorbed_focus_total", 0) or 0
            ),
            "master_real_with_alias_total": int(
                platform_summary.get("platform_real_with_selector_alias_total", 0) or 0
            ),
            "master_focus_row_total": int(platform_summary.get("platform_focus_alias_total", 0) or 0),
            "master_inferred_overlay_total": int(
                selector_summary.get("selector_inferred_total", 0) or 0
            ),
            "master_selector_alias_total": int(
                platform_summary.get("platform_selector_alias_total", 0) or 0
            ),
            "master_canonicalized_promoted_total": 0,
        },
    }


def build_bootstrap_payload(catalog: dict, rule_catalog: dict) -> dict:
    payload = _prepare_ui_payload(catalog, rule_catalog)
    summary = dict(payload.get("summary") or {})
    scoped_source_rows = [
        row
        for row in list(payload.get("industries") or [])
        if isinstance(row, dict) and _is_capital_technical_scope(row)
    ]
    patent_bundle = _load_patent_evidence_bundle(DEFAULT_PATENT_EVIDENCE_BUNDLE_PATH)
    review_case_presets_report = _load_review_case_presets_report(DEFAULT_REVIEW_CASE_PRESETS_PATH)
    case_story_surface_report = _load_case_story_surface_report(DEFAULT_CASE_STORY_SURFACE_PATH)
    operator_demo_packet_report = _load_operator_demo_packet_report(DEFAULT_OPERATOR_DEMO_PACKET_PATH)
    review_reason_decision_ladder_report = _load_review_reason_decision_ladder_report(
        DEFAULT_REVIEW_REASON_DECISION_LADDER_PATH
    )
    critical_prompt_surface_packet = _load_critical_prompt_surface_packet(
        DEFAULT_CRITICAL_PROMPT_SURFACE_PACKET_PATH
    )
    critical_prompt_excerpt = _prompt_surface_excerpt_lines(
        _load_text_file(DEFAULT_CRITICAL_PROMPT_DOC_PATH)
    )
    review_case_presets_summary = dict(review_case_presets_report.get("summary") or {})
    case_story_surface_summary = dict(case_story_surface_report.get("summary") or {})
    operator_demo_summary = dict(operator_demo_packet_report.get("summary") or {})
    review_reason_decision_ladder_summary = dict(review_reason_decision_ladder_report.get("summary") or {})
    critical_prompt_surface_summary = dict(critical_prompt_surface_packet.get("summary") or {})
    critical_prompt_lens = _compact_critical_prompt_lens(critical_prompt_surface_packet)
    runtime_reasoning_ladder_map = _compact_runtime_reasoning_ladder_map(review_reason_decision_ladder_report)
    scoped_source_rows = _attach_claim_packet_summaries(scoped_source_rows, patent_bundle)
    scoped_source_rows = _attach_review_case_artifacts(
        scoped_source_rows,
        review_case_presets_report,
        case_story_surface_report,
    )
    scoped_source_rows = _attach_operator_demo_artifacts(scoped_source_rows, operator_demo_packet_report)
    compact_rows = [
        _compact_industry_row_for_client(row)
        for row in scoped_source_rows
    ]
    scoped_major_categories = _build_major_categories_for_rows(compact_rows)
    scoped_real_rows = [row for row in compact_rows if not bool(row.get("is_rules_only"))]
    scoped_focus_target_rows = [
        row
        for row in compact_rows
        if bool((row.get("registration_requirement_profile") or {}).get("focus_target"))
    ]
    scoped_focus_with_other_rows = [
        row
        for row in compact_rows
        if bool((row.get("registration_requirement_profile") or {}).get("focus_target_with_other"))
    ]
    scoped_inferred_rows = [
        row
        for row in compact_rows
        if bool((row.get("registration_requirement_profile") or {}).get("inferred_focus_candidate"))
    ]
    focus_selector_entries = [
        _build_selector_entry(row, "focus")
        for row in scoped_source_rows
        if bool((row.get("registration_requirement_profile") or {}).get("focus_target"))
    ]
    inferred_selector_entries = [
        _build_selector_entry(row, "inferred")
        for row in scoped_source_rows
        if bool((row.get("registration_requirement_profile") or {}).get("inferred_focus_candidate"))
    ]
    selector_catalog = _build_selector_catalog(focus_selector_entries, inferred_selector_entries)
    platform_catalog = _build_platform_catalog(compact_rows, selector_catalog)
    master_catalog = _build_master_catalog(platform_catalog, selector_catalog)
    scoped_rule_keys = {str(row.get("service_code", "") or "").strip() for row in compact_rows if str(row.get("service_code", "") or "").strip()}
    summary["focus_selector_entry_total"] = len(focus_selector_entries)
    summary["inferred_selector_entry_total"] = len(inferred_selector_entries)
    summary["scope_policy"] = "capital_and_technical_only"
    summary["scope_industry_total"] = len(compact_rows)
    summary["scope_real_industry_total"] = len(scoped_real_rows)
    summary["scope_rules_only_industry_total"] = max(0, len(compact_rows) - len(scoped_real_rows))
    summary["industry_total"] = len(compact_rows)
    summary["major_category_total"] = len(scoped_major_categories)
    summary["with_registration_rule_total"] = sum(1 for row in compact_rows if bool(row.get("has_rule")))
    summary["rules_only_industry_total"] = sum(1 for row in compact_rows if bool(row.get("is_rules_only")))
    summary["candidate_law_total"] = sum(1 for row in compact_rows if list(row.get("auto_law_candidates") or []))
    summary["candidate_criteria_total"] = sum(
        1 for row in compact_rows if int(row.get("candidate_criteria_count", 0) or 0) > 0
    )
    summary["runtime_claim_packet_total"] = sum(
        1 for row in compact_rows if isinstance(row.get("claim_packet_summary"), dict) and row.get("claim_packet_summary")
    )
    summary["runtime_raw_source_proof_total"] = sum(
        1 for row in compact_rows if isinstance(row.get("raw_source_proof"), dict) and row.get("raw_source_proof")
    )
    summary["runtime_review_case_preset_total"] = int(
        review_case_presets_summary.get("preset_total", 0) or 0
    )
    summary["runtime_review_case_family_total"] = int(
        review_case_presets_summary.get("preset_family_total", 0) or 0
    )
    summary["runtime_case_story_family_total"] = int(
        case_story_surface_summary.get("story_family_total", 0) or 0
    )
    summary["runtime_case_story_review_reason_total"] = int(
        case_story_surface_summary.get("review_reason_total", 0) or 0
    )
    summary["runtime_operator_demo_family_total"] = int(
        operator_demo_summary.get("family_total", 0) or 0
    )
    summary["runtime_operator_demo_case_total"] = int(
        operator_demo_summary.get("demo_case_total", 0) or 0
    )
    summary["runtime_operator_demo_manual_review_total"] = int(
        operator_demo_summary.get("manual_review_demo_total", 0) or 0
    )
    summary["runtime_prompt_case_binding_total"] = sum(
        1
        for row in compact_rows
        if isinstance(((row.get("operator_demo_surface") or {}).get("prompt_case_binding")), dict)
        and ((row.get("operator_demo_surface") or {}).get("prompt_case_binding"))
    )
    summary["runtime_operator_demo_ready"] = bool(
        operator_demo_summary.get("operator_demo_ready", False)
    )
    summary["runtime_operator_demo_packet_path"] = str(DEFAULT_OPERATOR_DEMO_PACKET_PATH.resolve())
    summary["runtime_review_reason_decision_ladder_path"] = str(
        DEFAULT_REVIEW_REASON_DECISION_LADDER_PATH.resolve()
    )
    summary["runtime_review_reason_total"] = int(
        review_reason_decision_ladder_summary.get("review_reason_total", 0) or 0
    )
    summary["runtime_review_reason_decision_ladder_ready"] = bool(
        review_reason_decision_ladder_summary.get("decision_ladder_ready", False)
    )
    summary["runtime_reasoning_ladder_map"] = runtime_reasoning_ladder_map
    summary["runtime_critical_prompt_packet_ready"] = bool(
        critical_prompt_surface_summary.get("packet_ready", False)
    )
    summary["runtime_critical_prompt_packet_path"] = str(
        DEFAULT_CRITICAL_PROMPT_SURFACE_PACKET_PATH.resolve()
    )
    summary["runtime_critical_prompt_lens_ready"] = bool(critical_prompt_lens.get("lens_ready"))
    summary["runtime_critical_prompt_lens"] = critical_prompt_lens
    summary["runtime_critical_prompt_lane_id"] = str(
        critical_prompt_surface_summary.get("lane_id", "") or ""
    ).strip()
    summary["runtime_critical_prompt_runtime_contract_ready"] = bool(
        critical_prompt_lens.get("runtime_surface_contract_ready")
    )
    summary["runtime_critical_prompt_release_contract_ready"] = bool(
        critical_prompt_lens.get("release_surface_contract_ready")
    )
    summary["runtime_critical_prompt_operator_contract_ready"] = bool(
        critical_prompt_lens.get("operator_surface_contract_ready")
    )
    summary["runtime_critical_prompt_doc_ready"] = bool(critical_prompt_excerpt)
    summary["runtime_critical_prompt_doc_path"] = str(DEFAULT_CRITICAL_PROMPT_DOC_PATH.resolve())
    summary["runtime_critical_prompt_excerpt"] = critical_prompt_excerpt
    summary["focus_target_total"] = len(scoped_focus_target_rows)
    summary["focus_target_with_other_total"] = len(scoped_focus_with_other_rows)
    summary["real_focus_target_total"] = sum(
        1 for row in scoped_real_rows if bool((row.get("registration_requirement_profile") or {}).get("focus_target"))
    )
    summary["real_focus_target_with_other_total"] = sum(
        1 for row in scoped_real_rows if bool((row.get("registration_requirement_profile") or {}).get("focus_target_with_other"))
    )
    summary["rules_only_focus_target_total"] = max(
        0,
        summary["focus_target_total"] - summary["real_focus_target_total"],
    )
    summary["rules_only_focus_target_with_other_total"] = max(
        0,
        summary["focus_target_with_other_total"] - summary["real_focus_target_with_other_total"],
    )
    summary["inferred_focus_target_total"] = len(scoped_inferred_rows)
    summary["focus_default_mode"] = "focus_only" if scoped_focus_target_rows else ("inferred_only" if scoped_inferred_rows else "all")
    pending_rule_total = max(0, int(summary["industry_total"]) - int(summary["with_registration_rule_total"]))
    coverage_pct = round((int(summary["with_registration_rule_total"]) / int(summary["industry_total"])) * 100.0, 2) if int(summary["industry_total"]) > 0 else 0.0
    summary["pending_rule_total"] = pending_rule_total
    summary["coverage_pct"] = coverage_pct
    summary["public_claim_level"] = "full" if coverage_pct >= 95.0 else "phased"
    if summary["public_claim_level"] == "full":
        summary["public_claim_message"] = "자본금·기술인력 동시 요구 업종 범위에서 법령 연동 업종 커버리지가 95% 이상입니다."
    else:
        summary["public_claim_message"] = (
            f"자본금·기술인력 동시 요구 업종만 제공합니다. 미연동 업종 {pending_rule_total}건은 추가 구조화 대상으로 남아 있습니다."
        )
    summary["selector_category_total"] = int(
        (selector_catalog.get("summary") or {}).get("selector_category_total", 0) or 0
    )
    summary["selector_entry_total"] = int(
        (selector_catalog.get("summary") or {}).get("selector_entry_total", 0) or 0
    )
    summary["selector_real_entry_total"] = int(
        (selector_catalog.get("summary") or {}).get("selector_real_entry_total", 0) or 0
    )
    summary["selector_rules_only_entry_total"] = int(
        (selector_catalog.get("summary") or {}).get("selector_rules_only_entry_total", 0) or 0
    )
    summary["platform_industry_total"] = int(
        (platform_catalog.get("summary") or {}).get("platform_industry_total", 0) or 0
    )
    summary["platform_focus_registry_row_total"] = int(
        (platform_catalog.get("summary") or {}).get("platform_focus_registry_row_total", 0) or 0
    )
    summary["platform_promoted_selector_total"] = int(
        (platform_catalog.get("summary") or {}).get("platform_promoted_selector_total", 0) or 0
    )
    summary["platform_absorbed_focus_total"] = int(
        (platform_catalog.get("summary") or {}).get("platform_absorbed_focus_total", 0) or 0
    )
    summary["platform_real_with_selector_alias_total"] = int(
        (platform_catalog.get("summary") or {}).get("platform_real_with_selector_alias_total", 0) or 0
    )
    summary["platform_selector_alias_total"] = int(
        (platform_catalog.get("summary") or {}).get("platform_selector_alias_total", 0) or 0
    )
    summary["master_industry_total"] = int(
        (master_catalog.get("summary") or {}).get("master_industry_total", 0) or 0
    )
    summary["master_focus_registry_row_total"] = int(
        (master_catalog.get("summary") or {}).get("master_focus_registry_row_total", 0) or 0
    )
    summary["master_promoted_row_total"] = int(
        (master_catalog.get("summary") or {}).get("master_promoted_row_total", 0) or 0
    )
    summary["master_absorbed_row_total"] = int(
        (master_catalog.get("summary") or {}).get("master_absorbed_row_total", 0) or 0
    )
    summary["master_real_with_alias_total"] = int(
        (master_catalog.get("summary") or {}).get("master_real_with_alias_total", 0) or 0
    )
    summary["master_canonicalized_promoted_total"] = int(
        (master_catalog.get("summary") or {}).get("master_canonicalized_promoted_total", 0) or 0
    )
    permit_catalog = {
        "major_categories": scoped_major_categories,
        "industries": compact_rows,
        "focus_entries": scoped_focus_target_rows,
        "inferred_focus_entries": scoped_inferred_rows,
        "focus_selector_entries": focus_selector_entries,
        "inferred_selector_entries": inferred_selector_entries,
        "selector_entries": focus_selector_entries + inferred_selector_entries,
        "selector_catalog": selector_catalog,
        "platform_catalog": platform_catalog,
        "master_catalog": master_catalog,
        "summary": summary,
    }
    return {
        "permitCatalog": permit_catalog,
        "ruleLookup": {
            key: value
            for key, value in dict(payload.get("rules_lookup") or {}).items()
            if str(key or "").strip() in scoped_rule_keys
        },
        "ruleCatalogMeta": payload.get("rule_catalog_meta", {}),
    }


def build_html(
    title: str,
    catalog: dict,
    rule_catalog: dict,
    channel_id: str = "",
    contact_phone: str = "",
    notice_url: str = "",
    bootstrap_payload: dict | None = None,
    data_url: str = "",
    data_encoding: str = "",
    fragment: bool = False,
) -> str:
    bundle = dict(bootstrap_payload or build_bootstrap_payload(catalog, rule_catalog))
    permit_catalog = dict(bundle.get("permitCatalog") or {})
    rules_lookup = dict(bundle.get("ruleLookup") or {})
    rule_catalog_meta = dict(bundle.get("ruleCatalogMeta") or {})
    summary = dict(permit_catalog.get("summary") or {})
    branding = resolve_channel_branding(
        channel_id=str(channel_id or "").strip(),
        overrides={
            "contact_phone": str(contact_phone or "").strip(),
            "notice_url": str(notice_url or "").strip(),
        },
    )
    resolved_notice_url = str(branding.get("notice_url") or "").strip() or "https://seoulmna.co.kr/notice"
    resolved_phone = str(branding.get("contact_phone") or "").strip() or "1668-3548"
    resolved_phone_digits = "".join(ch for ch in resolved_phone if ch.isdigit()) or "16683548"
    resolved_data_url = str(data_url or "").strip()
    resolved_data_encoding = str(data_encoding or "").strip().lower()
    inline_bootstrap_json = {}
    inline_bootstrap_gzip_base64 = ""
    if not resolved_data_url:
        inline_bootstrap_gzip_base64 = _gzip_base64_json(bundle)

    html_template = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>__TITLE__</title>
  <style>
    :root {
      /* ── shared design-system tokens ── */
      --smna-primary: #003764;
      --smna-primary-strong: #002244;
      --smna-primary-soft: #0A4D8C;
      --smna-neutral: #F8FAFB;
      --smna-accent: #00A3FF;
      --smna-accent-strong: #0080CC;
      --smna-text: #1A1A2E;
      --smna-sub: #4B5563;
      --smna-warning: #FFB800;
      --smna-success: #00C48C;
      --smna-error: #FF4757;
      --smna-border: #E5E7EB;
      /* ── local aliases ── */
      --navy: var(--smna-primary);
      --navy-deep: var(--smna-primary-strong);
      --navy-soft: var(--smna-primary-soft);
      --sky: var(--smna-neutral);
      --sky-strong: #9bb9d1;
      --sand: var(--smna-warning);
      --sand-soft: #efe3d4;
      --bg: var(--smna-neutral);
      --bg-deep: var(--smna-neutral);
      --card: rgba(255, 255, 255, 0.94);
      --card-strong: #ffffff;
      --ink: var(--smna-text);
      --muted: var(--smna-sub);
      --line: var(--smna-border);
      --line-strong: var(--smna-border);
      --ok: var(--smna-success);
      --warn: var(--smna-warning);
      --info: var(--smna-primary-soft);
      --shadow-soft: 0 18px 44px rgba(4, 36, 60, 0.08);
      --shadow-strong: 0 28px 64px rgba(4, 36, 60, 0.18);
      --radius: 24px;
      --radius-sm: 16px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Pretendard", "Noto Sans KR", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(15, 82, 127, 0.12), transparent 34%),
        radial-gradient(circle at left 18%, rgba(183, 150, 114, 0.16), transparent 28%),
        linear-gradient(180deg, #f7fafc 0%, var(--bg) 38%, var(--bg-deep) 100%);
      line-height: 1.58;
    }
    .container {
      max-width: 1240px;
      margin: 0 auto;
      padding: 24px 16px 56px;
    }
    .hero {
      position: relative;
      overflow: hidden;
      display: grid;
      gap: 18px;
      background: linear-gradient(142deg, var(--navy-deep) 0%, var(--navy) 58%, #24608c 100%);
      color: #f4f8fc;
      border-radius: calc(var(--radius) + 4px);
      padding: 26px 22px;
      box-shadow: var(--shadow-strong);
      margin-bottom: 18px;
    }
    .hero::after {
      content: "";
      position: absolute;
      inset: auto -60px -90px auto;
      width: 260px;
      height: 260px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0) 72%);
      pointer-events: none;
    }
    .hero-main {
      position: relative;
      z-index: 1;
      max-width: 760px;
    }
    .hero-kicker {
      margin: 0 0 10px;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #d5e8f7;
    }
    .hero h1 {
      margin: 0 0 10px;
      font-size: clamp(28px, 4vw, 40px);
      line-height: 1.18;
      letter-spacing: -0.03em;
    }
    .hero p {
      margin: 0;
      color: #dceaf5;
      font-size: clamp(15px, 2.5vw, 18px);
    }
    .priority-badges {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 16px;
    }
    .priority-badge {
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 7px 12px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.12);
      border: 1px solid rgba(255, 255, 255, 0.18);
      color: #f7fbff;
      font-size: 13px;
      font-weight: 800;
      backdrop-filter: blur(6px);
    }
    .hero-stats {
      position: relative;
      z-index: 1;
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    }
    .hero-stat {
      min-height: 102px;
      padding: 16px 16px 14px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.09);
      border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
      backdrop-filter: blur(10px);
    }
    .hero-stat-label {
      display: block;
      margin-bottom: 8px;
      color: #d4e6f4;
      font-size: 13px;
      font-weight: 700;
    }
    .hero-stat strong {
      display: block;
      font-size: 24px;
      line-height: 1.2;
      letter-spacing: -0.02em;
    }
    .hero-stat span:last-child {
      display: block;
      margin-top: 8px;
      font-size: 13px;
      color: #d5e5f3;
    }
    .hero.is-enhanced > h1,
    .hero.is-enhanced > p,
    .hero.is-enhanced > .meta {
      display: none;
    }
    .grid {
      display: grid;
      gap: 18px;
      grid-template-columns: 1fr;
      align-items: start;
    }
    .card {
      background: var(--card);
      border: 1px solid rgba(182, 200, 215, 0.9);
      border-radius: var(--radius);
      box-shadow: var(--shadow-soft);
      padding: 20px 18px;
      backdrop-filter: blur(14px);
    }
    .input-card {
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(247, 250, 253, 0.98) 100%);
    }
    .result-card {
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.97) 0%, rgba(243, 248, 252, 0.98) 100%);
    }
    .card-topline {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid rgba(15, 82, 127, 0.14);
      background: rgba(15, 82, 127, 0.06);
      color: var(--navy);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    .card h2 {
      margin: 12px 0 8px;
      font-size: 24px;
      color: var(--navy-deep);
      letter-spacing: -0.02em;
      line-height: 1.22;
    }
    .section-lead {
      margin: 0 0 16px;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.48;
      font-weight: 700;
    }
    .section-block {
      margin-bottom: 16px;
      padding: 16px;
      border-radius: 20px;
      border: 1px solid rgba(182, 200, 215, 0.75);
      background: rgba(244, 248, 252, 0.86);
    }
    .section-block.priority {
      background: linear-gradient(180deg, rgba(244, 249, 253, 0.96) 0%, rgba(239, 245, 250, 0.96) 100%);
    }
    .section-kicker {
      margin: 0 0 6px;
      color: var(--navy-soft);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }
    .section-title {
      margin: 0;
      font-size: 20px;
      line-height: 1.3;
      letter-spacing: -0.02em;
      color: var(--navy-deep);
    }
    .step-choice-tag {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      margin-left: 8px;
      padding: 4px 9px;
      border-radius: 999px;
      background: rgba(183, 150, 114, 0.14);
      color: var(--smna-warning);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      vertical-align: middle;
    }
    .wizard-shell {
      display: grid;
      gap: 14px;
    }
    .wizard-rail {
      display: grid;
      gap: 10px;
    }
    .wizard-rail-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 15px;
      border-radius: 20px;
      border: 1px solid rgba(15, 82, 127, 0.12);
      background: linear-gradient(180deg, rgba(241, 247, 252, 0.98) 0%, rgba(250, 252, 255, 0.98) 100%);
    }
    .wizard-rail-kicker {
      margin: 0 0 4px;
      color: var(--navy-soft);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    .wizard-rail-title {
      margin: 0;
      color: var(--navy-deep);
      font-size: 18px;
      font-weight: 900;
      line-height: 1.32;
      letter-spacing: -0.02em;
    }
    .wizard-rail-note {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.48;
      font-weight: 700;
    }
    .wizard-summary {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 0 2px 2px;
    }
    .wizard-summary-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 34px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(15, 82, 127, 0.12);
      background: rgba(255, 255, 255, 0.96);
      color: var(--navy-deep);
      font-size: 12px;
      font-weight: 800;
      line-height: 1.35;
      box-shadow: 0 10px 20px rgba(4, 36, 60, 0.05);
    }
    .wizard-summary-chip.is-empty {
      color: var(--muted);
      border-style: dashed;
      box-shadow: none;
    }
    .wizard-blocker {
      padding: 11px 13px;
      border-radius: 16px;
      border: 1px solid rgba(183, 150, 114, 0.28);
      background: linear-gradient(180deg, rgba(250, 245, 238, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
      color: var(--smna-warning);
      font-size: 13px;
      line-height: 1.48;
      font-weight: 800;
    }
    .wizard-blocker.is-ready {
      border-color: rgba(17, 117, 71, 0.22);
      background: linear-gradient(180deg, rgba(237, 248, 241, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
      color: var(--smna-success);
    }
    .wizard-priority-hint {
      margin-top: 12px;
      padding: 12px 13px;
      border-radius: 16px;
      border: 1px solid rgba(15, 82, 127, 0.12);
      background: linear-gradient(180deg, rgba(244, 249, 253, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
      color: var(--ink);
      font-size: 13px;
      line-height: 1.5;
      font-weight: 700;
    }
    .wizard-progress {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      margin-top: 14px;
      padding: 14px 15px;
      border-radius: 18px;
      border: 1px solid rgba(15, 82, 127, 0.12);
      background: linear-gradient(180deg, rgba(244, 249, 253, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
      box-shadow: 0 12px 22px rgba(4, 36, 60, 0.06);
    }
    .wizard-progress-copy {
      flex: 1 1 220px;
      min-width: 0;
    }
    .wizard-progress-label {
      color: var(--ink);
      font-size: 13px;
      font-weight: 900;
      line-height: 1.4;
    }
    .wizard-progress-track {
      position: relative;
      width: 100%;
      height: 8px;
      margin: 9px 0 8px;
      border-radius: 999px;
      background: rgba(15, 82, 127, 0.12);
      overflow: hidden;
    }
    .wizard-progress-fill {
      display: block;
      height: 100%;
      width: 0%;
      border-radius: inherit;
      background: linear-gradient(90deg, #0f5f75 0%, #003764 100%);
      transition: width 0.22s ease;
    }
    .wizard-progress-meta {
      color: var(--smna-sub);
      font-size: 12px;
      line-height: 1.5;
      font-weight: 700;
    }
    .wizard-progress-action {
      appearance: none;
      display: inline-flex;
      align-items: center;
      justify-content: flex-start;
      flex-wrap: wrap;
      gap: 7px;
      width: 100%;
      margin-top: 10px;
      padding: 8px 11px;
      border-radius: 14px;
      background: rgba(15, 82, 127, 0.06);
      border: 1px solid rgba(15, 82, 127, 0.10);
      cursor: pointer;
      text-align: left;
    }
    .wizard-progress-action-label {
      color: var(--navy);
      font-size: 11px;
      line-height: 1.3;
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .wizard-progress-action-text {
      color: var(--ink);
      font-size: 12px;
      line-height: 1.5;
      font-weight: 800;
    }
    .guided-focus-target {
      position: relative;
      box-shadow: 0 0 0 3px rgba(15, 82, 127, 0.16), 0 18px 34px rgba(15, 82, 127, 0.14);
      border-color: var(--smna-accent-strong) !important;
      animation: permitGuidedFocusPulse 0.9s ease-out 1;
    }
    .guided-focus-target[data-guided-focus-copy]::after {
      content: attr(data-guided-focus-copy);
      position: absolute;
      top: 10px;
      right: 10px;
      max-width: min(240px, calc(100% - 20px));
      padding: 7px 10px;
      border-radius: 999px;
      background: rgba(15, 82, 127, 0.92);
      color: #f8fbff;
      font-size: 11px;
      line-height: 1.35;
      font-weight: 900;
      letter-spacing: -0.01em;
      box-shadow: 0 12px 22px rgba(15, 82, 127, 0.18);
      z-index: 3;
      pointer-events: none;
      white-space: normal;
    }
    .guided-focus-target[data-guided-focus-level="sticky"] {
      box-shadow: 0 0 0 4px rgba(15, 82, 127, 0.20), 0 24px 44px rgba(15, 82, 127, 0.20);
    }
    .guided-focus-target[data-guided-focus-level="sticky"][data-guided-focus-copy]::after {
      top: -12px;
      right: auto;
      left: 12px;
      max-width: min(280px, calc(100% - 24px));
      padding: 9px 12px;
      background: linear-gradient(135deg, rgba(15, 82, 127, 0.96), rgba(46, 125, 176, 0.94));
      font-size: 12px;
      box-shadow: 0 16px 28px rgba(15, 82, 127, 0.24);
    }
    @keyframes permitGuidedFocusPulse {
      0% {
        box-shadow: 0 0 0 0 rgba(46, 125, 176, 0.30), 0 10px 20px rgba(15, 82, 127, 0.10);
      }
      100% {
        box-shadow: 0 0 0 3px rgba(15, 82, 127, 0.16), 0 18px 34px rgba(15, 82, 127, 0.14);
      }
    }
    .wizard-progress-count {
      flex: 0 0 auto;
      min-width: 54px;
      padding: 8px 10px;
      border-radius: 14px;
      background: rgba(15, 82, 127, 0.08);
      color: var(--navy);
      font-size: 15px;
      font-weight: 900;
      letter-spacing: -0.01em;
      text-align: center;
    }
    .wizard-mobile-sticky {
      display: none;
      appearance: none;
      width: 100%;
      padding: 11px 13px;
      border-radius: 18px;
      border: 1px solid rgba(15, 82, 127, 0.14);
      background: rgba(255, 255, 255, 0.94);
      backdrop-filter: blur(14px);
      text-align: left;
      box-shadow: 0 12px 24px rgba(4, 36, 60, 0.10);
      cursor: pointer;
    }
    .wizard-mobile-sticky-label {
      color: var(--navy);
      font-size: 11px;
      line-height: 1.3;
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .wizard-mobile-sticky-action {
      margin-top: 3px;
      color: var(--ink);
      font-size: 14px;
      line-height: 1.45;
      font-weight: 900;
      letter-spacing: -0.02em;
      word-break: keep-all;
    }
    .wizard-mobile-sticky-compact {
      margin-top: 4px;
      color: var(--smna-sub);
      font-size: 12px;
      line-height: 1.42;
      font-weight: 800;
      word-break: keep-all;
    }
    .wizard-mobile-sticky-meta {
      display: none;
      color: var(--smna-sub);
      font-size: 12px;
      line-height: 1.45;
      font-weight: 700;
      word-break: keep-all;
    }
    .wizard-mobile-sticky-count {
      margin-top: 8px;
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 5px 10px;
      border-radius: 999px;
      background: rgba(15, 82, 127, 0.08);
      color: var(--navy);
      font-size: 12px;
      font-weight: 900;
      letter-spacing: -0.01em;
    }
    .wizard-steps {
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
    .wizard-step-chip {
      appearance: none;
      border: 1px solid rgba(15, 82, 127, 0.12);
      background: rgba(255, 255, 255, 0.98);
      border-radius: 18px;
      padding: 12px 10px;
      text-align: left;
      cursor: pointer;
      transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
    }
    .wizard-step-chip:hover {
      border-color: rgba(15, 82, 127, 0.28);
      box-shadow: 0 12px 22px rgba(4, 36, 60, 0.08);
      transform: translateY(-1px);
    }
    .wizard-step-chip.is-active {
      border-color: rgba(0, 55, 100, 0.4);
      background: linear-gradient(180deg, rgba(0, 55, 100, 0.08) 0%, rgba(255, 255, 255, 1) 100%);
      box-shadow: 0 16px 28px rgba(4, 36, 60, 0.10);
    }
    .wizard-step-chip.is-complete {
      border-color: rgba(17, 117, 71, 0.26);
      background: linear-gradient(180deg, rgba(17, 117, 71, 0.08) 0%, rgba(255, 255, 255, 1) 100%);
    }
    .wizard-step-chip.is-optional {
      border-style: dashed;
    }
    .wizard-step-chip-label {
      display: block;
      margin-bottom: 6px;
      color: var(--navy-soft);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    .wizard-step-chip-title {
      display: block;
      color: var(--ink);
      font-size: 14px;
      font-weight: 900;
      line-height: 1.36;
    }
    .wizard-step-chip-meta {
      display: block;
      margin-top: 4px;
      color: var(--smna-sub);
      font-size: 12px;
      line-height: 1.42;
      font-weight: 700;
    }
    .wizard-step-card {
      display: none;
    }
    .wizard-step-card.is-active {
      display: block;
    }
    .wizard-step-card.optional-step {
      border-style: dashed;
      background: linear-gradient(180deg, rgba(249, 245, 239, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
    }
    .wizard-nav {
      margin-top: 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }
    .wizard-nav-copy {
      flex: 1 1 180px;
      color: var(--smna-sub);
      font-size: 13px;
      line-height: 1.46;
      font-weight: 700;
    }
    .wizard-nav-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      flex: 0 0 auto;
      flex-wrap: wrap;
    }
    .wizard-nav-btn {
      appearance: none;
      border: 1px solid rgba(15, 82, 127, 0.18);
      background: rgba(255, 255, 255, 0.98);
      color: var(--navy);
      min-height: 42px;
      padding: 10px 14px;
      border-radius: 999px;
      font-size: 14px;
      font-weight: 800;
      cursor: pointer;
      transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
    }
    .wizard-nav-btn:hover {
      border-color: rgba(15, 82, 127, 0.34);
      box-shadow: 0 12px 22px rgba(4, 36, 60, 0.08);
      transform: translateY(-1px);
    }
    .wizard-nav-btn.is-primary {
      border-color: rgba(0, 55, 100, 0.88);
      background: linear-gradient(145deg, var(--navy) 0%, var(--navy-soft) 100%);
      color: #fff;
    }
    .wizard-nav-btn:disabled {
      opacity: 0.46;
      cursor: not-allowed;
      box-shadow: none;
      transform: none;
    }
    .field {
      margin-bottom: 14px;
    }
    .field:last-child {
      margin-bottom: 0;
    }
    .field-grid {
      display: grid;
      gap: 12px;
      grid-template-columns: 1fr;
    }
    .field label {
      display: block;
      margin-bottom: 8px;
      font-size: 15px;
      font-weight: 800;
      line-height: 1.35;
    }
    .control {
      width: 100%;
      min-height: 54px;
      border: 1px solid var(--line-strong);
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.98);
      color: var(--ink);
      padding: 13px 14px;
      font-size: 17px;
      line-height: 1.3;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
      transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
    }
    .control:hover {
      border-color: var(--smna-border);
    }
    .control:focus {
      outline: none;
      border-color: var(--smna-accent-strong);
      box-shadow: 0 0 0 4px rgba(15, 82, 127, 0.12);
      transform: translateY(-1px);
    }
    button:focus-visible,
    .chip:focus-visible,
    .cta-btn:focus-visible {
      outline: 3px solid var(--smna-accent-strong);
      outline-offset: 2px;
    }
    .assist {
      margin-top: 8px;
      color: var(--smna-sub);
      font-size: 14px;
      line-height: 1.46;
      font-weight: 700;
    }
    .assist.auto-selection-reason {
      margin-top: 6px;
      color: var(--navy);
      font-size: 13px;
      line-height: 1.48;
      font-weight: 800;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      cursor: pointer;
      transition: transform 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
    }
    .assist.auto-selection-reason:hover,
    .assist.auto-selection-reason:focus-visible {
      outline: none;
      transform: translateY(-1px);
    }
    .assist.auto-selection-reason[data-actionable="1"]:hover,
    .assist.auto-selection-reason[data-actionable="1"]:focus-visible {
      box-shadow: 0 0 0 3px rgba(15, 82, 127, 0.10);
      border-radius: 14px;
      background: rgba(0, 55, 100, 0.03);
    }
    .assist.auto-selection-reason::before {
      content: attr(data-reason-icon) " " attr(data-reason-kind);
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 0 9px;
      border-radius: 999px;
      background: rgba(0, 55, 100, 0.08);
      border: 1px solid rgba(0, 55, 100, 0.14);
      color: var(--smna-primary);
      font-size: 11px;
      line-height: 1;
      font-weight: 900;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .assist.auto-selection-reason[data-reason-icon="="]::before,
    .assist.auto-selection-reason[data-reason-icon="~"]::before,
    .assist.auto-selection-reason[data-reason-icon=">"]::before,
    .assist.auto-selection-reason[data-reason-icon="i"]::before {
      letter-spacing: 0.03em;
    }
    .assist.auto-selection-reason[data-reason-tone="match"]::before {
      background: rgba(16, 132, 92, 0.10);
      border-color: rgba(16, 132, 92, 0.18);
      color: var(--smna-success);
    }
    .assist.auto-selection-reason[data-reason-tone="search"]::before {
      background: rgba(0, 55, 100, 0.08);
      border-color: rgba(0, 55, 100, 0.14);
      color: var(--smna-primary);
    }
    .assist.auto-selection-reason[data-reason-tone="direct"]::before {
      background: rgba(15, 82, 127, 0.10);
      border-color: rgba(15, 82, 127, 0.18);
      color: var(--smna-primary-soft);
    }
    .assist.auto-selection-reason[data-reason-tone="guide"]::before {
      background: rgba(84, 100, 118, 0.10);
      border-color: rgba(84, 100, 118, 0.16);
      color: var(--smna-sub);
    }
    .assist.auto-selection-reason[data-actionable="1"]::after {
      content: "검색 수정";
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 0 8px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.94);
      border: 1px solid rgba(0, 55, 100, 0.12);
      color: var(--smna-sub);
      font-size: 11px;
      line-height: 1;
      font-weight: 900;
      letter-spacing: 0.02em;
    }
    .auto-selection-reason-body {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }
    .auto-selection-reason-copy {
      color: var(--smna-sub);
      font-size: 13px;
      line-height: 1.48;
      font-weight: 700;
    }
    .auto-selection-token,
    .auto-selection-field {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 0 10px;
      border-radius: 999px;
      font-size: 12px;
      line-height: 1;
      font-weight: 900;
      letter-spacing: -0.01em;
    }
    .auto-selection-token {
      background: linear-gradient(180deg, rgba(0, 55, 100, 0.12), rgba(0, 55, 100, 0.05));
      color: var(--smna-primary);
      border: 1px solid rgba(0, 55, 100, 0.14);
    }
    .auto-selection-field {
      background: rgba(15, 82, 127, 0.08);
      color: var(--smna-primary-soft);
      border: 1px solid rgba(15, 82, 127, 0.12);
    }
    .guide {
      margin: 10px 0 0;
      color: var(--smna-sub);
      font-size: 13px;
      line-height: 1.5;
      font-weight: 700;
    }
    .mode-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 12px 0 14px;
    }
    .mode-pill {
      appearance: none;
      border: 1px solid rgba(15, 82, 127, 0.16);
      background: rgba(255, 255, 255, 0.92);
      color: var(--navy);
      min-height: 38px;
      padding: 8px 14px;
      border-radius: 999px;
      font-size: 14px;
      font-weight: 800;
      line-height: 1.2;
      cursor: pointer;
      transition: all 0.16s ease;
    }
    .mode-pill:hover {
      border-color: rgba(15, 82, 127, 0.36);
      transform: translateY(-1px);
    }
    .mode-pill.is-active {
      background: linear-gradient(145deg, var(--navy) 0%, var(--navy-soft) 100%);
      border-color: rgba(0, 55, 100, 0.88);
      color: #ffffff;
      box-shadow: 0 12px 24px rgba(0, 55, 100, 0.22);
    }
    .smart-profile {
      margin-top: 12px;
      padding: 16px;
      border-radius: 18px;
      border: 1px solid rgba(15, 82, 127, 0.12);
      background: linear-gradient(180deg, rgba(6, 56, 96, 0.04) 0%, rgba(255, 255, 255, 0.98) 100%);
      color: var(--ink);
    }
    .smart-profile.is-empty {
      border-style: dashed;
      color: var(--muted);
      background: rgba(250, 252, 254, 0.92);
    }
    .smart-profile-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }
    .smart-profile-head strong {
      font-size: 18px;
      line-height: 1.3;
      letter-spacing: -0.02em;
      color: var(--navy-deep);
    }
    .smart-profile-tag {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(15, 82, 127, 0.08);
      color: var(--navy);
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }
    .smart-profile-grid {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      margin-bottom: 10px;
    }
    .smart-profile-item {
      padding: 11px 12px;
      border-radius: 14px;
      background: rgba(240, 246, 251, 0.96);
      border: 1px solid rgba(182, 200, 215, 0.64);
    }
    .smart-profile-label {
      display: block;
      margin-bottom: 4px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    .smart-profile-value {
      display: block;
      color: var(--navy-deep);
      font-size: 17px;
      font-weight: 900;
      line-height: 1.3;
      letter-spacing: -0.02em;
    }
    .smart-chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 10px;
    }
    .smart-chip {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(2, 38, 64, 0.06);
      color: var(--smna-primary);
      font-size: 12px;
      font-weight: 800;
    }
    .preset-actions {
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid rgba(182, 200, 215, 0.74);
    }
    .preset-action-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .preset-action {
      appearance: none;
      border: 1px solid rgba(15, 82, 127, 0.16);
      background: rgba(255, 255, 255, 0.94);
      color: var(--navy);
      min-height: 40px;
      padding: 9px 14px;
      border-radius: 999px;
      font-size: 14px;
      font-weight: 800;
      line-height: 1.2;
      cursor: pointer;
      transition: all 0.16s ease;
    }
    .preset-action:hover:not(:disabled) {
      border-color: rgba(15, 82, 127, 0.34);
      transform: translateY(-1px);
    }
    .preset-action.is-primary {
      background: linear-gradient(145deg, var(--navy) 0%, var(--navy-soft) 100%);
      border-color: rgba(0, 55, 100, 0.88);
      color: #ffffff;
      box-shadow: 0 12px 24px rgba(0, 55, 100, 0.18);
    }
    .preset-action:disabled {
      cursor: not-allowed;
      opacity: 0.46;
      transform: none;
      box-shadow: none;
    }
    .preset-hint {
      margin: 10px 0 0;
      color: var(--smna-sub);
      font-size: 13px;
      line-height: 1.46;
      font-weight: 700;
    }
    .collapsible {
      margin-top: 16px;
      border-radius: 20px;
      border: 1px solid rgba(182, 200, 215, 0.8);
      background: rgba(249, 252, 254, 0.95);
      overflow: hidden;
    }
    .collapsible summary {
      cursor: pointer;
      list-style: none;
      padding: 16px;
      font-size: 15px;
      font-weight: 800;
      color: var(--navy-deep);
    }
    .collapsible summary::-webkit-details-marker {
      display: none;
    }
    .collapsible-body {
      padding: 0 16px 16px;
    }
    .check-grid {
      display: grid;
      gap: 10px;
      grid-template-columns: 1fr;
    }
    .check-grid.is-collapsed .check-item.is-secondary {
      display: none;
    }
    .check-item {
      position: relative;
      display: flex;
      align-items: flex-start;
      gap: 10px;
      min-height: 52px;
      padding: 12px 14px;
      border-radius: 16px;
      border: 1px solid rgba(182, 200, 215, 0.74);
      background: rgba(243, 248, 252, 0.96);
      font-size: 14px;
      font-weight: 700;
      line-height: 1.45;
      color: var(--smna-primary);
      transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease, background 0.16s ease, opacity 0.16s ease;
    }
    .check-item.is-priority {
      border-color: rgba(0, 55, 100, 0.26);
      background: linear-gradient(180deg, rgba(238, 246, 252, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
      box-shadow: 0 16px 26px rgba(4, 36, 60, 0.08);
      transform: translateY(-1px);
    }
    .check-item.is-priority::after {
      content: attr(data-priority-badge);
      position: absolute;
      top: 10px;
      right: 12px;
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 4px 9px;
      border-radius: 999px;
      background: rgba(0, 55, 100, 0.08);
      border: 1px solid rgba(0, 55, 100, 0.14);
      color: var(--navy);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .check-item.is-secondary {
      opacity: 0.92;
    }
    .check-item.is-priority input {
      accent-color: var(--navy);
    }
    .check-item input {
      margin-top: 2px;
      transform: scale(1.08);
    }
    .optional-toggle-wrap {
      display: flex;
      justify-content: flex-start;
      margin-top: 10px;
    }
    .optional-toggle-btn {
      appearance: none;
      display: inline-flex;
      align-items: center;
      min-height: 38px;
      padding: 9px 14px;
      border-radius: 999px;
      border: 1px solid rgba(15, 82, 127, 0.16);
      background: rgba(255, 255, 255, 0.96);
      color: var(--navy);
      font-size: 13px;
      line-height: 1.3;
      font-weight: 800;
      cursor: pointer;
      transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
    }
    .optional-toggle-btn:hover {
      border-color: rgba(15, 82, 127, 0.3);
      box-shadow: 0 12px 22px rgba(4, 36, 60, 0.08);
      transform: translateY(-1px);
    }
    .optional-toggle-btn[hidden] {
      display: none;
    }
    .result-banner {
      display: grid;
      gap: 6px;
      margin: 0 0 14px;
      padding: 16px;
      border-radius: 18px;
      border: 1px solid rgba(15, 82, 127, 0.12);
      background: linear-gradient(180deg, rgba(235, 244, 251, 0.96) 0%, rgba(248, 251, 254, 0.98) 100%);
      color: var(--navy-deep);
    }
    .result-banner.ok {
      border-color: rgba(17, 117, 71, 0.18);
      background: linear-gradient(180deg, rgba(234, 248, 240, 0.98) 0%, rgba(247, 252, 249, 0.98) 100%);
    }
    .result-banner.warn {
      border-color: rgba(139, 83, 22, 0.18);
      background: linear-gradient(180deg, rgba(252, 244, 235, 0.98) 0%, rgba(255, 250, 245, 0.98) 100%);
    }
    .result-banner.info {
      border-color: rgba(35, 95, 141, 0.18);
    }
    .result-banner strong {
      font-size: 18px;
      line-height: 1.34;
      letter-spacing: -0.02em;
    }
    .result-banner span {
      font-size: 14px;
      line-height: 1.48;
      color: var(--smna-sub);
      font-weight: 700;
    }
    .result-meta-grid {
      display: grid;
      gap: 12px;
      grid-template-columns: 1fr;
      margin-bottom: 12px;
    }
    .result-meta-card,
    .status-card {
      padding: 15px 14px;
      border-radius: 18px;
      border: 1px solid rgba(182, 200, 215, 0.8);
      background: rgba(255, 255, 255, 0.9);
    }
    .metric-label {
      margin: 0 0 6px;
      color: var(--muted);
      font-size: 14px;
      font-weight: 800;
      line-height: 1.45;
      letter-spacing: -0.01em;
    }
    .metric-value {
      margin: 0;
      font-size: clamp(28px, 4.2vw, 42px);
      line-height: 1.16;
      letter-spacing: -0.03em;
      font-weight: 900;
      color: var(--navy-deep);
      word-break: keep-all;
    }
    .result-date {
      font-size: clamp(24px, 3.6vw, 34px);
    }
    .status-grid {
      display: grid;
      gap: 10px;
      grid-template-columns: 1fr;
      margin-bottom: 12px;
    }
    .status {
      margin: 0;
      font-size: clamp(20px, 3vw, 28px);
      font-weight: 900;
      line-height: 1.25;
      color: var(--smna-primary);
      word-break: keep-all;
    }
    .status.ok { color: var(--ok); }
    .status.warn { color: var(--warn); }
    .meta-box {
      margin: 0;
      padding: 12px 13px;
      border-radius: 14px;
      border: 1px solid rgba(182, 200, 215, 0.82);
      background: rgba(247, 250, 253, 0.98);
      color: var(--smna-primary);
      font-size: 15px;
      line-height: 1.48;
      font-weight: 700;
    }
    .law-box {
      margin: 0 0 10px;
      padding: 12px 13px;
      border-radius: 16px;
      border: 1px solid rgba(183, 150, 114, 0.34);
      background: linear-gradient(180deg, rgba(247, 242, 236, 0.98) 0%, rgba(252, 249, 245, 0.98) 100%);
      color: var(--smna-warning);
      font-size: 14px;
      line-height: 1.56;
      font-weight: 700;
    }
    .law-box a {
      color: var(--info);
    }
    .case-surface-card {
      margin-top: 10px;
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid rgba(15, 82, 127, 0.14);
      background: rgba(255, 255, 255, 0.82);
    }
    .case-surface-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 6px;
    }
    .result-actions-wrap {
      margin: 0 0 12px;
      padding: 14px;
      border-radius: 18px;
      border: 1px dashed rgba(15, 82, 127, 0.24);
      background: rgba(247, 251, 254, 0.92);
    }
    .result-actions-note {
      margin: 0;
      color: var(--smna-sub);
      font-size: 14px;
      line-height: 1.46;
      font-weight: 700;
    }
    .result-brief-wrap {
      display: grid;
      gap: 8px;
      margin-top: 12px;
      padding: 12px;
      border-radius: 16px;
      border: 1px solid rgba(15, 82, 127, 0.12);
      background: rgba(255, 255, 255, 0.86);
    }
    .result-brief-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
    }
    .result-brief-label {
      margin: 0;
      color: var(--navy-deep);
      font-size: 13px;
      line-height: 1.3;
      font-weight: 900;
      letter-spacing: -0.01em;
    }
    #resultBrief {
      width: 100%;
      min-height: 64px;
      resize: vertical;
      border-radius: 12px;
      border: 1px solid rgba(15, 82, 127, 0.14);
      background: rgba(247, 251, 254, 0.98);
      color: var(--smna-primary);
      font-size: 13px;
      line-height: 1.5;
      padding: 10px 11px;
    }
    .result-brief-meta {
      margin: 0;
      color: var(--smna-sub);
      font-size: 12px;
      line-height: 1.5;
      font-weight: 700;
    }
    .actions {
      display: none;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 0;
    }
    .result-actions-wrap.ready .actions {
      display: flex;
    }
    .result-actions-wrap.ready .result-actions-note {
      display: block;
    }
    .mobile-quick-bar {
      position: fixed;
      left: 14px;
      right: 14px;
      bottom: 14px;
      z-index: 48;
      display: none;
      gap: 10px;
      padding: 14px;
      border-radius: 22px;
      border: 1px solid rgba(15, 82, 127, 0.14);
      background: rgba(255, 255, 255, 0.94);
      box-shadow: 0 20px 44px rgba(4, 36, 60, 0.18);
      backdrop-filter: blur(16px);
    }
    .mobile-quick-bar.is-ready {
      display: grid;
    }
    .mobile-quick-copy {
      display: grid;
      gap: 4px;
    }
    .mobile-quick-title {
      margin: 0;
      font-size: 15px;
      font-weight: 900;
      line-height: 1.34;
      color: var(--navy-deep);
      letter-spacing: -0.02em;
    }
    .mobile-quick-meta {
      margin: 0;
      font-size: 13px;
      line-height: 1.46;
      color: var(--smna-sub);
      font-weight: 700;
    }
    .mobile-quick-actions {
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .mobile-quick-btn {
      appearance: none;
      border: 1px solid rgba(15, 82, 127, 0.18);
      background: rgba(255, 255, 255, 0.96);
      color: var(--navy);
      min-height: 42px;
      padding: 10px 12px;
      border-radius: 999px;
      font-size: 14px;
      font-weight: 800;
      line-height: 1.2;
      cursor: pointer;
      transition: all 0.16s ease;
    }
    .mobile-quick-btn.is-primary {
      border-color: rgba(0, 55, 100, 0.88);
      background: linear-gradient(145deg, var(--navy) 0%, var(--navy-soft) 100%);
      color: #fff;
      box-shadow: 0 12px 24px rgba(0, 55, 100, 0.18);
    }
    .mobile-quick-btn:disabled {
      cursor: not-allowed;
      opacity: 0.46;
      box-shadow: none;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      padding: 9px 14px;
      border-radius: 999px;
      text-decoration: none;
      font-size: 14px;
      font-weight: 800;
      line-height: 1.2;
      border: 1px solid rgba(15, 82, 127, 0.18);
      color: var(--navy);
      background: #ffffff;
      transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
    }
    .btn:hover {
      transform: translateY(-1px);
      border-color: rgba(15, 82, 127, 0.34);
      box-shadow: 0 12px 22px rgba(4, 36, 60, 0.08);
    }
    .btn.main {
      border-color: rgba(0, 55, 100, 0.88);
      background: linear-gradient(145deg, var(--navy) 0%, var(--navy-soft) 100%);
      color: #fff;
    }
    .tip {
      margin-top: 8px;
      padding: 13px 14px;
      border-radius: 16px;
      border: 1px solid rgba(183, 150, 114, 0.24);
      background: linear-gradient(180deg, rgba(243, 236, 228, 0.92) 0%, rgba(249, 245, 240, 0.98) 100%);
      color: var(--smna-warning);
      font-size: 14px;
      line-height: 1.5;
      font-weight: 700;
    }
    @media (min-width: 920px) {
      .grid {
        grid-template-columns: minmax(0, 1.12fr) minmax(360px, 0.88fr);
      }
      .field-grid.two {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .field-grid.three {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
      .result-meta-grid,
      .status-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .check-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .result-card {
        position: sticky;
        top: 18px;
      }
    }
    @media (max-width: 1279px) {
      .result-card {
        position: static;
      }
    }
    @media (max-width: 919px) {
      body.has-mobile-quick-bar {
        padding-bottom: 124px;
      }
      .container {
        padding-inline: 14px;
      }
      .hero-stat {
        min-height: 92px;
      }
      .smart-profile-grid {
        grid-template-columns: 1fr;
      }
      .wizard-steps {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .wizard-rail-head {
        flex-direction: column;
      }
      .wizard-mobile-sticky {
        display: grid;
        position: sticky;
        top: 10px;
        z-index: 26;
      }
    }
    @media (min-width: 920px) {
      .mobile-quick-bar {
        display: none !important;
      }
    }
  </style>
</head>
<body>
  <main class="container">
    <section class="hero">
      <h1>AI 인허가 사전검토 진단기</h1>
      <p>업종별 인허가 등록 전, 자본금·기술인력·장비 요건을 법령 근거로 사전 점검합니다.</p>
      <div class="meta">
        업종 DB: __INDUSTRY_TOTAL__개 · 대분류: __MAJOR_TOTAL__개 · 등록기준 연동: __WITH_RULE_TOTAL__개
      </div>
      <div class="meta">
        핵심 업종군: __FOCUS_TARGET_TOTAL__개 · 실업종 __REAL_FOCUS_TARGET_TOTAL__개 · 등록기준 업종군 __RULES_ONLY_FOCUS_TARGET_TOTAL__개
      </div>
      <div class="meta">
        규칙 버전: __RULE_VERSION__ · 기준일: __RULE_EFFECTIVE_DATE__
      </div>
    </section>

    <div class="grid">
      <section class="card" aria-labelledby="input-title">
        <h2 id="input-title">사전검토 입력</h2>
        <div class="field">
          <label for="focusModeSelect">조회 모드</label>
          <select id="focusModeSelect" class="control">
            <option value="focus_only">핵심 업종만 보기</option>
            <option value="all">전체 업종 보기</option>
            <option value="inferred_only">추론 후보 점검</option>
          </select>
          <p id="focusHint" class="assist"></p>
        </div>
        <div class="field">
          <label for="focusQuickSelect">핵심 업종 빠른 선택</label>
          <select id="focusQuickSelect" class="control"></select>
          <p id="focusQuickHint" class="assist"></p>
        </div>
        <div class="field">
                <label for="industrySearchInput">업종명 우선 검색</label>
                <input id="industrySearchInput" class="control" type="search" placeholder="예: 건축, 전기공사, 경비, 소방" />
        </div>
        <div class="field">
          <label for="categorySelect">대분류 카테고리</label>
          <select id="categorySelect" class="control"></select>
        </div>
        <div class="field">
          <label for="industrySelect">세부 인허가 업종</label>
          <select id="industrySelect" class="control"></select>
          <p id="industryHint" class="assist"></p>
          <p id="industryAutoReason" class="assist auto-selection-reason" role="button" tabindex="0" aria-live="polite"></p>
        </div>
        <div class="field">
          <label for="capitalInput">현재 보유 자본금(억)</label>
          <input id="capitalInput" class="control" type="number" inputmode="decimal" min="0" step="0.01" placeholder="예: 1.5" aria-required="true" />
          <p id="crossValidation" class="assist" aria-live="polite"></p>
        </div>
        <div class="field">
          <label for="technicianInput">현재 기술인력 수(명)</label>
          <input id="technicianInput" class="control" type="number" inputmode="numeric" min="0" step="1" placeholder="예: 2" aria-required="true" />
        </div>
        <div class="field">
          <label for="equipmentInput">현재 보유 장비 수(식)</label>
          <input id="equipmentInput" class="control" type="number" inputmode="numeric" min="0" step="1" placeholder="예: 1" />
        </div>
        <div class="field">
          <label>선택 준비 상태</label>
          <div class="meta-box">
            <label><input id="officeSecuredInput" type="checkbox" /> 사무실/영업소 확보</label><br>
            <label><input id="facilitySecuredInput" type="checkbox" /> 시설·장비·보관공간 확보</label><br>
            <label><input id="qualificationSecuredInput" type="checkbox" /> 자격·교육·경력 확보</label><br>
            <label><input id="insuranceSecuredInput" type="checkbox" /> 보험·보증 가입 확인</label><br>
            <label><input id="safetySecuredInput" type="checkbox" /> 안전·환경 요건 확인</label><br>
            <label><input id="documentReadyInput" type="checkbox" /> 필수 제출서류 준비</label>
          </div>
        </div>
        <p class="guide">자본금 단위는 억입니다. 예: 1억 5천만 원 = 1.5</p>
      </section>

      <section class="card" aria-labelledby="result-title">
        <h2 id="result-title">진단 결과</h2>
        <p class="metric-label">법정 최소 자본금</p>
        <p id="requiredCapital" class="metric-value">-</p>
        <p class="metric-label">핵심 세부 요건</p>
        <p id="requirementsMeta" class="meta-box">-</p>

        <p class="metric-label">자본금 갭 진단</p>
        <p id="capitalGapStatus" class="status" aria-live="polite">-</p>
        <p class="metric-label">기술인력 갭 진단</p>
        <p id="technicianGapStatus" class="status" aria-live="polite">-</p>
        <p class="metric-label">장비 갭 진단</p>
        <p id="equipmentGapStatus" class="status" aria-live="polite">-</p>

        <p class="metric-label">오늘 보완 시 예상 진단 가능일</p>
        <p id="diagnosisDate" class="metric-value">-</p>
        <p id="fallbackGuide" class="meta-box" style="display:none"></p>
        <div id="legalBasis" class="law-box" style="display:none"></div>
        <div id="focusProfileBox" class="law-box" style="display:none"></div>
        <div id="qualityFlagsBox" class="law-box" style="display:none"></div>
        <div id="proofClaimBox" class="law-box" style="display:none"></div>
        <div id="reviewPresetBox" class="law-box" style="display:none"></div>
        <div id="caseStoryBox" class="law-box" style="display:none"></div>
        <div id="operatorDemoBox" class="law-box" style="display:none"></div>
        <div id="runtimeReasoningCardBox" class="law-box" style="display:none"></div>
        <p id="coverageGuide" class="meta-box" style="display:none"></p>
        <div id="typedCriteriaBox" class="law-box" style="display:none"></div>
        <div id="evidenceChecklistBox" class="law-box" style="display:none"></div>
        <div id="nextActionsBox" class="law-box" style="display:none"></div>

        <div class="actions">
          <a class="btn main" href="__NOTICE_URL__" target="_blank" rel="noopener noreferrer">전문가 상담 연결</a>
          <a class="btn" href="tel:__CONTACT_PHONE_DIGITS__">대표전화 __CONTACT_PHONE__</a>
        </div>
        <p class="tip">법령/관할 해석이 필요한 항목은 결과 화면의 법령 근거를 기반으로 상담 단계에서 최종 확정됩니다.</p>
      </section>
    </div>
  </main>

<script nowprocket>
    const permitDataUrl = "__PERMIT_DATA_URL__";
    const permitDataEncoding = "__PERMIT_DATA_ENCODING__";
    const inlineBootstrap = __PERMIT_BOOTSTRAP_JSON__;
    const inlineBootstrapCompressed = "__PERMIT_BOOTSTRAP_GZIP_BASE64__";

    const decodeBase64ToBytes = (text) => {
      const source = String(text || "");
      if (!source) return new Uint8Array();
      const binary = window.atob(source);
      const out = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i += 1) {
        out[i] = binary.charCodeAt(i);
      }
      return out;
    };

    const gunzipText = async (bytes) => {
      if (!bytes || !bytes.length) {
        return "{}";
      }
      if (typeof DecompressionStream === "undefined") {
        throw new Error("permit_data_gzip_unsupported");
      }
      const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
      return await new Response(stream).text();
    };

    const parseBootstrapText = (text) => {
      try {
        return JSON.parse(String(text || "{}"));
      } catch (_error) {
        throw new Error("permit_data_parse_failed");
      }
    };

    const extractHtmlPayload = (htmlText) => {
      const src = String(htmlText || "");
      const match = src.match(/<script[^>]*id=["']smna-permit-payload["'][^>]*>([\\s\\S]*?)<\\/script>/i);
      if (!match) {
        throw new Error("permit_data_html_payload_missing");
      }
      return String(match[1] || "").trim();
    };

    const extractRenderedPayloadFromJson = async (res) => {
      const payload = await res.json();
      const rendered = payload && payload.content && typeof payload.content.rendered === "string"
        ? payload.content.rendered
        : "";
      return extractHtmlPayload(rendered);
    };

    const loadBootstrapData = async () => {
      if (permitDataUrl) {
        const res = await fetch(permitDataUrl, { credentials: "omit", cache: "no-store" });
        if (!res.ok) {
          throw new Error(`permit_data_fetch_failed:${res.status}`);
        }
        if (permitDataEncoding === "gzip-base64-rest-rendered") {
          return parseBootstrapText(await gunzipText(decodeBase64ToBytes(await extractRenderedPayloadFromJson(res))));
        }
        if (permitDataEncoding === "gzip-base64-html") {
          const htmlText = await res.text();
          return parseBootstrapText(await gunzipText(decodeBase64ToBytes(extractHtmlPayload(htmlText))));
        }
        if (permitDataEncoding === "gzip") {
          const zipped = new Uint8Array(await res.arrayBuffer());
          return parseBootstrapText(await gunzipText(zipped));
        }
        return await res.json();
      }
      if (inlineBootstrapCompressed) {
        return parseBootstrapText(await gunzipText(decodeBase64ToBytes(inlineBootstrapCompressed)));
      }
      return inlineBootstrap || {};
    };

    (async () => {
      const bootstrap = await loadBootstrapData();
      const permitCatalog = bootstrap.permitCatalog || { major_categories: [], industries: [], summary: {} };
      const ruleLookup = bootstrap.ruleLookup || {};
      const ruleCatalogMeta = bootstrap.ruleCatalogMeta || {};
      const permitWizardStepsMeta = [
        {
          id: "permitWizardStep1",
          shortLabel: "STEP 1",
          title: "업종 검색 시작",
          meta: "조회 모드 · 빠른 선택 · 업종명 검색",
          note: "쉬운 검색 정보부터 입력합니다.",
          optional: false,
        },
        {
          id: "permitWizardStep2",
          shortLabel: "STEP 2",
          title: "업종 확정",
          meta: "대분류 · 세부 업종",
          note: "검색 결과를 확정합니다.",
          optional: false,
        },
        {
          id: "permitWizardStep3",
          shortLabel: "STEP 3",
          title: "현재 보유 현황",
          meta: "자본금 · 기술자 · 장비",
          note: "핵심 등록요건부터 먼저 넣습니다.",
          optional: false,
        },
        {
          id: "permitWizardStep4",
          shortLabel: "STEP 4",
          title: "선택 준비 상태",
          meta: "체크 항목 · 서류 준비도",
          note: "결과 보정에 쓰이는 선택 정보입니다.",
          optional: true,
        },
      ];

    const applyExperienceLayout = () => {
      const summary = permitCatalog.summary || {};
      const toCountText = (value) => Math.max(0, Number(value || 0)).toLocaleString("ko-KR");
      const safeText = (value) => String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
      const ruleVersion = String((ruleCatalogMeta && ruleCatalogMeta.version) || "최신");
      const effectiveDate = String(
        (ruleCatalogMeta && ruleCatalogMeta.effective_date)
          || ((ruleCatalogMeta && ruleCatalogMeta.source && ruleCatalogMeta.source.fetched_at) || "확인 중")
      );
      const hero = document.querySelector(".hero");
      if (hero && !hero.classList.contains("is-enhanced")) {
        hero.classList.add("is-enhanced");
        const heroMain = document.createElement("div");
        heroMain.className = "hero-main";
        heroMain.innerHTML = `
          <p class="hero-kicker">AI Permit Precheck</p>
          <h1>AI 인허가 사전검토 진단기</h1>
          <p>업종을 고르면 등록기준, 법령 근거, 부족 항목, 다음 확인 포인트까지 한 화면에서 정리합니다.</p>
          <div class="priority-badges">
            <span class="priority-badge">업종 선택</span>
            <span class="priority-badge">현재 자본금 입력</span>
            <span class="priority-badge">기술자/장비 확인</span>
            <span class="priority-badge">법령 기준 즉시 비교</span>
          </div>`;
        const heroStats = document.createElement("div");
        heroStats.className = "hero-stats";
        heroStats.innerHTML = `
          <div class="hero-stat">
            <span class="hero-stat-label">업종 DB</span>
            <strong>${Core.toInt(summary.industry_total || 0).toLocaleString("ko-KR")}개</strong>
            <span>대분류 ${Core.toInt(summary.major_category_total || 0).toLocaleString("ko-KR")}개를 한 번에 탐색합니다.</span>
          </div>
          <div class="hero-stat">
            <span class="hero-stat-label">등록기준 연동</span>
            <strong>${Core.toInt(summary.with_registration_rule_total || 0).toLocaleString("ko-KR")}개</strong>
            <span>법령 구조화 기준으로 즉시 비교 가능한 업종입니다.</span>
          </div>
          <div class="hero-stat">
            <span class="hero-stat-label">핵심 업종</span>
            <strong>${Core.toInt(summary.focus_target_total || 0).toLocaleString("ko-KR")}개</strong>
            <span>실업종 ${Core.toInt(summary.real_focus_target_total || 0).toLocaleString("ko-KR")}개, 규칙 우선 ${Core.toInt(summary.rules_only_focus_target_total || 0).toLocaleString("ko-KR")}개입니다.</span>
          </div>
          <div class="hero-stat">
            <span class="hero-stat-label">규칙 버전</span>
            <strong>${esc(ruleVersion)}</strong>
            <span>기준일 ${esc(effectiveDate)}</span>
          </div>`;
        hero.insertBefore(heroMain, hero.firstChild);
        hero.appendChild(heroStats);
      }

      const grid = document.querySelector(".grid");
      const cards = grid ? Array.from(grid.children).filter((node) => node.classList && node.classList.contains("card")) : [];
      const inputCard = cards[0] || null;
      const resultCard = cards[1] || null;
      const findField = (id) => {
        const node = document.getElementById(id);
        return node ? (node.closest(".field") || node) : null;
      };
      const ensureCardHeader = (card, toplineText, leadText, extraClass) => {
        if (!card) return null;
        if (extraClass) card.classList.add(extraClass);
        const heading = card.querySelector("h2");
        if (!heading) return null;
        let topline = card.querySelector(".card-topline");
        if (!topline) {
          topline = document.createElement("div");
          topline.className = "card-topline";
          heading.parentNode.insertBefore(topline, heading);
        }
        topline.textContent = toplineText;
        let lead = heading.nextElementSibling;
        if (!(lead && lead.classList && lead.classList.contains("section-lead"))) {
          lead = document.createElement("p");
          lead.className = "section-lead";
          heading.insertAdjacentElement("afterend", lead);
        }
        lead.textContent = leadText;
        return heading;
      };
      const createPermitWizardNav = (stepIndex, noteText) => {
        const nav = document.createElement("div");
        nav.className = "wizard-nav";
        nav.innerHTML = ''
          + `<p class="wizard-nav-copy">${safeText(noteText || "")}</p>`
          + '<div class="wizard-nav-actions">'
          + `<button type="button" class="wizard-nav-btn" data-permit-wizard-prev="${stepIndex}">이전</button>`
          + `<button type="button" class="wizard-nav-btn is-primary" data-permit-wizard-next="${stepIndex}">다음</button>`
          + '</div>';
        return nav;
      };
      const createPermitWizardChip = (step, stepIndex) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = `wizard-step-chip${step.optional ? " is-optional" : ""}`;
        chip.id = `permitWizardChip${stepIndex + 1}`;
        chip.setAttribute("data-permit-wizard-track", String(stepIndex));
        chip.innerHTML = ''
          + `<span class="wizard-step-chip-label">${safeText(step.shortLabel || "")}${step.optional ? ' · 선택' : ''}</span>`
          + `<span class="wizard-step-chip-title">${safeText(step.title || "")}</span>`
          + `<span class="wizard-step-chip-meta">${safeText(step.meta || "")}</span>`;
        return chip;
      };

      if (inputCard && !document.getElementById("smartIndustryProfile")) {
        ensureCardHeader(
          inputCard,
          "필수 입력 4단계",
          "상단 필수 정보만 넣어도 현재 등록기준 충족 여부와 부족 항목이 바로 보이도록 정리했습니다.",
          "input-card",
        );
        const heading = inputCard.querySelector("h2");
        const focusModeField = findField("focusModeSelect");
        const focusQuickField = findField("focusQuickSelect");
        const searchField = findField("industrySearchInput");
        const categoryField = findField("categorySelect");
        const industryField = findField("industrySelect");
        const capitalField = findField("capitalInput");
        const technicianField = findField("technicianInput");
        const equipmentField = findField("equipmentInput");
        const extraField = findField("officeSecuredInput");
        const guideNode = inputCard.querySelector(".guide");
        const wizardShell = document.createElement("div");
        wizardShell.id = "permitInputWizard";
        wizardShell.className = "wizard-shell";

        const wizardRail = document.createElement("div");
        wizardRail.id = "permitWizardRail";
        wizardRail.className = "wizard-rail";
        wizardRail.innerHTML = ''
          + '<div class="wizard-rail-head">'
          + '<div>'
          + '<p class="wizard-rail-kicker">Sequential Input</p>'
          + '<h3 id="permitWizardStepTitle" class="wizard-rail-title">STEP 1 · 업종 검색 시작</h3>'
          + '<p id="permitWizardStepNote" class="wizard-rail-note">쉬운 검색 정보부터 입력하고, 선택 정보는 마지막 단계에서 반영합니다.</p>'
          + '</div>'
          + '<div class="tip">한 단계에 2~3개 정보만 넣도록 쪼갰습니다. 마지막 단계는 <strong>선택</strong>입니다.</div>'
          + '</div>';
        const wizardProgress = document.createElement("div");
        wizardProgress.id = "permitWizardProgress";
        wizardProgress.className = "wizard-progress";
      wizardProgress.innerHTML = ''
        + '<div class="wizard-progress-copy">'
        + '<div id="permitWizardProgressLabel" class="wizard-progress-label">현재 1/4 단계</div>'
        + '<div id="permitWizardProgressBar" class="wizard-progress-track" role="progressbar" aria-valuemin="1" aria-valuemax="4" aria-valuenow="1" aria-describedby="permitWizardProgressMeta">'
        + '<span id="permitWizardProgressFill" class="wizard-progress-fill"></span>'
          + '</div>'
          + '<div id="permitWizardProgressMeta" class="wizard-progress-meta">필수 0/3 완료 · 업종 검색부터 시작합니다.</div>'
          + '<button type="button" id="permitWizardNextAction" class="wizard-progress-action" data-permit-next-action><span class="wizard-progress-action-label">지금 할 일</span><span id="permitWizardNextActionText" class="wizard-progress-action-text">업종명 검색이나 빠른 선택으로 시작하세요.</span></button>'
        + '</div>'
        + '<strong id="permitWizardProgressCount" class="wizard-progress-count">1/4</strong>';
      wizardRail.appendChild(wizardProgress);
      const wizardMobileSticky = document.createElement("button");
      wizardMobileSticky.type = "button";
      wizardMobileSticky.id = "permitWizardMobileSticky";
      wizardMobileSticky.className = "wizard-mobile-sticky";
      wizardMobileSticky.setAttribute("data-permit-next-action", "mobile");
      wizardMobileSticky.innerHTML = ''
        + '<div class="wizard-mobile-sticky-copy">'
        + '<div id="permitWizardMobileStickyLabel" class="wizard-mobile-sticky-label">현재 1/4 단계</div>'
        + '<div id="permitWizardMobileStickyAction" class="wizard-mobile-sticky-action">업종명 검색이나 빠른 선택으로 시작하세요.</div>'
        + '<div id="permitWizardMobileStickyCompact" class="wizard-mobile-sticky-compact">업종 검색부터 시작</div>'
        + '<div id="permitWizardMobileStickyMeta" class="wizard-mobile-sticky-meta">필수 0/3 완료 · 업종 검색부터 시작합니다.</div>'
        + '</div>'
        + '<span id="permitWizardMobileStickyCount" class="wizard-mobile-sticky-count">1/4</span>';
      wizardRail.appendChild(wizardMobileSticky);
      const wizardSummary = document.createElement("div");
        wizardSummary.id = "permitWizardSummary";
        wizardSummary.className = "wizard-summary";
        wizardSummary.innerHTML = '<span class="wizard-summary-chip is-empty">검색을 시작하면 현재 선택 상태와 필수 입력 진행률을 여기에 요약합니다.</span>';
        wizardRail.appendChild(wizardSummary);
        const wizardBlocker = document.createElement("div");
        wizardBlocker.id = "permitWizardBlocker";
        wizardBlocker.className = "wizard-blocker";
        wizardBlocker.textContent = "다음 단계로 가려면 업종명 검색이나 빠른선택을 먼저 시작해 주세요.";
        wizardRail.appendChild(wizardBlocker);
        const wizardSteps = document.createElement("div");
        wizardSteps.id = "permitWizardSteps";
        wizardSteps.className = "wizard-steps";
        permitWizardStepsMeta.forEach((step, stepIndex) => {
          wizardSteps.appendChild(createPermitWizardChip(step, stepIndex));
        });
        wizardRail.appendChild(wizardSteps);
        wizardShell.appendChild(wizardRail);

        const lookupBlock = document.createElement("section");
        lookupBlock.id = "permitWizardStep1";
        lookupBlock.className = "section-block priority wizard-step-card";
        lookupBlock.setAttribute("data-step-index", "0");
        lookupBlock.innerHTML = '<p class="section-kicker">STEP 1</p><h3 class="section-title">업종 검색 시작</h3><p class="assist">조회 모드, 빠른 선택, 업종명 검색처럼 쉬운 정보부터 넣습니다.</p>';
        const modePills = document.createElement("div");
        modePills.id = "focusModePills";
        modePills.className = "mode-pills";
        modePills.setAttribute("role", "group");
        modePills.setAttribute("aria-label", "조회 모드 바로가기");
        modePills.innerHTML = ''
          + '<button type="button" class="mode-pill" data-focus-mode="focus_only">핵심 업종만</button>'
          + '<button type="button" class="mode-pill" data-focus-mode="all">전체 업종</button>'
          + '<button type="button" class="mode-pill" data-focus-mode="inferred_only">추론 후보</button>';
        lookupBlock.appendChild(modePills);
        if (focusModeField) lookupBlock.appendChild(focusModeField);
        const quickGrid = document.createElement("div");
        quickGrid.className = "field-grid two";
        if (focusQuickField) quickGrid.appendChild(focusQuickField);
        if (searchField) quickGrid.appendChild(searchField);
        if (quickGrid.children.length) lookupBlock.appendChild(quickGrid);
        lookupBlock.appendChild(createPermitWizardNav(0, "검색어를 넣거나 빠른 선택을 누른 뒤 다음 단계에서 업종을 확정합니다."));

        const categoryBlock = document.createElement("section");
        categoryBlock.id = "permitWizardStep2";
        categoryBlock.className = "section-block priority wizard-step-card";
        categoryBlock.setAttribute("data-step-index", "1");
        categoryBlock.innerHTML = '<p class="section-kicker">STEP 2</p><h3 class="section-title">업종 확정</h3><p class="assist">대분류와 세부 업종을 확정하면 법정 최소 기준과 부족 항목이 바로 요약됩니다.</p>';
        const selectGrid = document.createElement("div");
        selectGrid.className = "field-grid two";
        if (categoryField) selectGrid.appendChild(categoryField);
        if (industryField) selectGrid.appendChild(industryField);
        if (selectGrid.children.length) categoryBlock.appendChild(selectGrid);
        const smartProfile = document.createElement("div");
        smartProfile.id = "smartIndustryProfile";
        smartProfile.className = "smart-profile is-empty";
        smartProfile.textContent = "업종을 선택하면 법정 최소 기준, 기준 출처, 보강이 필요한 준비 항목을 자동 요약합니다.";
        categoryBlock.appendChild(smartProfile);
        categoryBlock.appendChild(createPermitWizardNav(1, "업종이 확정되면 다음 단계에서 필수 보유 현황부터 입력하면 됩니다."));

        const holdingsBlock = document.createElement("section");
        holdingsBlock.id = "permitWizardStep3";
        holdingsBlock.className = "section-block priority wizard-step-card";
        holdingsBlock.setAttribute("data-step-index", "2");
        holdingsBlock.innerHTML = '<p class="section-kicker">STEP 3</p><h3 class="section-title">현재 보유 현황 입력</h3><p class="assist">현재 보유값만 입력하세요. 법정 기준은 우측 결과 패널과 업종 요약 카드에 자동으로 비교합니다.</p>';
        const inputGrid = document.createElement("div");
        inputGrid.className = "field-grid three";
        if (capitalField) inputGrid.appendChild(capitalField);
        if (technicianField) inputGrid.appendChild(technicianField);
        if (equipmentField) inputGrid.appendChild(equipmentField);
        if (inputGrid.children.length) holdingsBlock.appendChild(inputGrid);
        const presetActions = document.createElement("div");
        presetActions.className = "preset-actions";
        presetActions.innerHTML = ''
          + '<div class="preset-action-row">'
          + '<button type="button" id="fillRequirementPreset" class="preset-action is-primary">기준값 채우기</button>'
          + '<button type="button" id="resetHoldingsPreset" class="preset-action">입력 초기화</button>'
          + '</div>'
          + '<p id="presetActionHint" class="preset-hint">업종을 선택하면 법정 최소 기준을 현재 보유 현황에 바로 채울 수 있습니다.</p>';
        holdingsBlock.appendChild(presetActions);
        const holdingsPriorityHint = document.createElement("div");
        holdingsPriorityHint.id = "holdingsPriorityHint";
        holdingsPriorityHint.className = "wizard-priority-hint";
        holdingsPriorityHint.textContent = "업종을 먼저 확정하면 자본금, 기술자, 장비 중 무엇부터 확인해야 하는지 바로 안내합니다.";
        holdingsBlock.appendChild(holdingsPriorityHint);
        if (guideNode) holdingsBlock.appendChild(guideNode);
        holdingsBlock.appendChild(createPermitWizardNav(2, "핵심 등록요건부터 먼저 넣고, 마지막 단계에서 선택 항목을 추가 반영할 수 있습니다."));

        const optionalBlock = document.createElement("section");
        optionalBlock.id = "permitWizardStep4";
        optionalBlock.className = "section-block wizard-step-card optional-step";
        optionalBlock.setAttribute("data-step-index", "3");
        optionalBlock.innerHTML = '<p class="section-kicker">STEP 4 · 선택</p><h3 class="section-title">추가 준비 상태 <span class="step-choice-tag">선택</span></h3><p class="assist">결과 보정과 서류 준비도를 더 자세히 보려면 선택적으로 체크하세요. 입력하지 않아도 기본 진단은 가능합니다.</p>';
        const optionalPriorityHint = document.createElement("div");
        optionalPriorityHint.id = "optionalPriorityHint";
        optionalPriorityHint.className = "wizard-priority-hint optional-priority-hint";
        optionalPriorityHint.textContent = "업종을 고르면 마지막 단계에서 먼저 볼 선택 항목을 위로 정렬해 드립니다.";
        const optionalGrid = document.createElement("div");
        optionalGrid.id = "advancedInputs";
        optionalGrid.className = "check-grid";
        if (extraField) {
          const sourceBox = extraField.querySelector(".meta-box");
          const labels = sourceBox ? Array.from(sourceBox.querySelectorAll("label")) : [];
          labels.forEach((label) => {
            label.className = "check-item";
            const input = label.querySelector("input");
            if (input && input.id) label.dataset.checklistId = input.id;
            optionalGrid.appendChild(label);
          });
          extraField.remove();
        }
        optionalBlock.appendChild(optionalPriorityHint);
        optionalBlock.appendChild(optionalGrid);
        const optionalToggleWrap = document.createElement("div");
        optionalToggleWrap.className = "optional-toggle-wrap";
        optionalToggleWrap.innerHTML = '<button type="button" id="optionalChecklistToggle" class="optional-toggle-btn" hidden>추가 준비 항목 더 보기</button>';
        optionalBlock.appendChild(optionalToggleWrap);
        optionalBlock.appendChild(createPermitWizardNav(3, "선택 단계까지 확인했으면 결과 카드에서 부족 항목, 법령 근거, 다음 조치를 검토하세요."));

        wizardShell.appendChild(lookupBlock);
        wizardShell.appendChild(categoryBlock);
        wizardShell.appendChild(holdingsBlock);
        wizardShell.appendChild(optionalBlock);

        const anchor = heading ? heading.nextElementSibling : null;
        if (anchor) {
          inputCard.insertBefore(wizardShell, anchor.nextElementSibling || null);
        } else {
          inputCard.appendChild(wizardShell);
        }
      } else if (inputCard) {
        inputCard.classList.add("input-card");
      }

      if (resultCard && !document.getElementById("resultBanner")) {
        ensureCardHeader(
          resultCard,
          "자동 요약",
          "업종을 선택하면 최소 기준, 부족 항목, 후속 확인 순서를 자동으로 정리합니다.",
          "result-card",
        );
        const heading = resultCard.querySelector("h2");
        const requiredCapital = document.getElementById("requiredCapital");
        const requirementsMeta = document.getElementById("requirementsMeta");
        const capitalGapStatus = document.getElementById("capitalGapStatus");
        const technicianGapStatus = document.getElementById("technicianGapStatus");
        const equipmentGapStatus = document.getElementById("equipmentGapStatus");
        const diagnosisDate = document.getElementById("diagnosisDate");
        const crossValidationNode = document.getElementById("crossValidation");
        const fallbackGuide = document.getElementById("fallbackGuide");
        const actions = resultCard.querySelector(".actions");

        const resultBanner = document.createElement("div");
        resultBanner.id = "resultBanner";
        resultBanner.className = "result-banner info";
        resultBanner.innerHTML = '<strong id="resultBannerTitle">업종을 선택하면 자동 진단이 시작됩니다.</strong><span id="resultBannerMeta">필수 등록요건과 법령 근거, 준비 상태를 한 번에 비교합니다.</span>';

        const metaGrid = document.createElement("div");
        metaGrid.className = "result-meta-grid";
        const createMetricCard = (labelNode, valueNode) => {
          const card = document.createElement("div");
          card.className = "result-meta-card";
          if (labelNode) card.appendChild(labelNode);
          if (valueNode) card.appendChild(valueNode);
          return card;
        };
        const requiredLabel = requiredCapital ? requiredCapital.previousElementSibling : null;
        const requirementsLabel = requirementsMeta ? requirementsMeta.previousElementSibling : null;
        metaGrid.appendChild(createMetricCard(requiredLabel, requiredCapital));
        metaGrid.appendChild(createMetricCard(requirementsLabel, requirementsMeta));

        const statusGrid = document.createElement("div");
        statusGrid.className = "status-grid";
        const createStatusCard = (labelNode, valueNode, extraNode = null) => {
          const card = document.createElement("div");
          card.className = "status-card";
          if (labelNode) card.appendChild(labelNode);
          if (valueNode) card.appendChild(valueNode);
          if (extraNode) card.appendChild(extraNode);
          return card;
        };
        statusGrid.appendChild(createStatusCard(capitalGapStatus ? capitalGapStatus.previousElementSibling : null, capitalGapStatus));
        statusGrid.appendChild(createStatusCard(technicianGapStatus ? technicianGapStatus.previousElementSibling : null, technicianGapStatus));
        statusGrid.appendChild(createStatusCard(equipmentGapStatus ? equipmentGapStatus.previousElementSibling : null, equipmentGapStatus));
        if (diagnosisDate) diagnosisDate.classList.add("result-date");
        statusGrid.appendChild(createStatusCard(diagnosisDate ? diagnosisDate.previousElementSibling : null, diagnosisDate, crossValidationNode));

        const actionWrap = document.createElement("div");
        actionWrap.id = "resultActionWrap";
        actionWrap.className = "result-actions-wrap";
        const actionNote = document.createElement("p");
        actionNote.id = "resultActionNote";
        actionNote.className = "result-actions-note";
        actionNote.textContent = "업종을 선택하면 상담과 후속 안내 동선이 열립니다.";
        actionWrap.appendChild(actionNote);
        const resultBriefWrap = document.createElement("div");
        resultBriefWrap.id = "resultBriefWrap";
        resultBriefWrap.className = "result-brief-wrap";
        resultBriefWrap.innerHTML = ''
          + '<div class="result-brief-head">'
          + '<p class="result-brief-label">상담 전달용 한 줄 브리프</p>'
          + '<button type="button" class="btn" id="btnCopyResultBrief" disabled>한 줄 브리프 복사</button>'
          + '</div>'
          + '<textarea id="resultBrief" readonly placeholder="업종을 선택하면 대표가 바로 전달할 한 줄 요약을 자동 생성합니다."></textarea>'
          + '<p id="resultBriefMeta" class="result-brief-meta">핵심 기준과 보완 항목만 한 줄로 정리해 상담 연결 속도를 높입니다.</p>';
        actionWrap.appendChild(resultBriefWrap);
        if (actions) {
          actions.id = "resultActionButtons";
          actionWrap.appendChild(actions);
        }

        const headingAnchor = heading ? heading.nextElementSibling : null;
        if (headingAnchor) {
          resultCard.insertBefore(resultBanner, headingAnchor.nextElementSibling || null);
        } else {
          resultCard.appendChild(resultBanner);
        }
        resultCard.appendChild(metaGrid);
        resultCard.appendChild(statusGrid);
        resultCard.appendChild(actionWrap);
        if (fallbackGuide) resultCard.appendChild(fallbackGuide);
      } else if (resultCard) {
        resultCard.classList.add("result-card");
      }
      if (!document.getElementById("mobileQuickBar")) {
        const mobileQuickBar = document.createElement("div");
        mobileQuickBar.id = "mobileQuickBar";
        mobileQuickBar.className = "mobile-quick-bar";
        mobileQuickBar.innerHTML = ''
          + '<div class="mobile-quick-copy">'
          + '<p id="mobileQuickTitle" class="mobile-quick-title">업종을 선택하면 핵심 결과를 아래에 요약합니다.</p>'
          + '<p id="mobileQuickMeta" class="mobile-quick-meta">모바일에서는 결과 카드가 아래에 있어, 바로가기 버튼으로 빠르게 이동할 수 있습니다.</p>'
          + '</div>'
          + '<div class="mobile-quick-actions">'
          + '<button type="button" id="mobileQuickPresetButton" class="mobile-quick-btn">기준값 채우기</button>'
          + '<button type="button" id="mobileQuickResultButton" class="mobile-quick-btn is-primary">결과 보기</button>'
          + '</div>';
        document.body.appendChild(mobileQuickBar);
      }
    };

    const ui = {
      permitInputWizard: document.getElementById("permitInputWizard"),
      permitWizardRail: document.getElementById("permitWizardRail"),
      permitWizardStepTitle: document.getElementById("permitWizardStepTitle"),
      permitWizardStepNote: document.getElementById("permitWizardStepNote"),
      permitWizardProgressLabel: document.getElementById("permitWizardProgressLabel"),
      permitWizardProgressMeta: document.getElementById("permitWizardProgressMeta"),
      permitWizardNextActionText: document.getElementById("permitWizardNextActionText"),
      permitWizardProgressBar: document.getElementById("permitWizardProgressBar"),
      permitWizardProgressFill: document.getElementById("permitWizardProgressFill"),
      permitWizardProgressCount: document.getElementById("permitWizardProgressCount"),
      permitWizardMobileStickyLabel: document.getElementById("permitWizardMobileStickyLabel"),
      permitWizardMobileStickyAction: document.getElementById("permitWizardMobileStickyAction"),
      permitWizardMobileStickyCompact: document.getElementById("permitWizardMobileStickyCompact"),
      permitWizardMobileStickyMeta: document.getElementById("permitWizardMobileStickyMeta"),
      permitWizardMobileStickyCount: document.getElementById("permitWizardMobileStickyCount"),
      permitWizardSummary: document.getElementById("permitWizardSummary"),
      permitWizardBlocker: document.getElementById("permitWizardBlocker"),
      permitWizardStep1: document.getElementById("permitWizardStep1"),
      permitWizardStep2: document.getElementById("permitWizardStep2"),
      permitWizardStep3: document.getElementById("permitWizardStep3"),
      permitWizardStep4: document.getElementById("permitWizardStep4"),
      focusModeSelect: document.getElementById("focusModeSelect"),
      focusHint: document.getElementById("focusHint"),
      focusModePills: document.getElementById("focusModePills"),
      focusQuickSelect: document.getElementById("focusQuickSelect"),
      focusQuickHint: document.getElementById("focusQuickHint"),
      industrySearchInput: document.getElementById("industrySearchInput"),
      categorySelect: document.getElementById("categorySelect"),
      industrySelect: document.getElementById("industrySelect"),
      industryHint: document.getElementById("industryHint"),
      industryAutoReason: document.getElementById("industryAutoReason"),
      smartIndustryProfile: document.getElementById("smartIndustryProfile"),
      capitalInput: document.getElementById("capitalInput"),
      technicianInput: document.getElementById("technicianInput"),
      equipmentInput: document.getElementById("equipmentInput"),
      fillRequirementPreset: document.getElementById("fillRequirementPreset"),
      resetHoldingsPreset: document.getElementById("resetHoldingsPreset"),
      presetActionHint: document.getElementById("presetActionHint"),
      holdingsPriorityHint: document.getElementById("holdingsPriorityHint"),
      mobileQuickBar: document.getElementById("mobileQuickBar"),
      mobileQuickTitle: document.getElementById("mobileQuickTitle"),
      mobileQuickMeta: document.getElementById("mobileQuickMeta"),
      mobileQuickPresetButton: document.getElementById("mobileQuickPresetButton"),
      mobileQuickResultButton: document.getElementById("mobileQuickResultButton"),
      officeSecuredInput: document.getElementById("officeSecuredInput"),
      facilitySecuredInput: document.getElementById("facilitySecuredInput"),
      qualificationSecuredInput: document.getElementById("qualificationSecuredInput"),
      insuranceSecuredInput: document.getElementById("insuranceSecuredInput"),
      safetySecuredInput: document.getElementById("safetySecuredInput"),
      documentReadyInput: document.getElementById("documentReadyInput"),
      advancedInputs: document.getElementById("advancedInputs"),
      optionalPriorityHint: document.getElementById("optionalPriorityHint"),
      optionalChecklistToggle: document.getElementById("optionalChecklistToggle"),
      crossValidation: document.getElementById("crossValidation"),
      requiredCapital: document.getElementById("requiredCapital"),
      requirementsMeta: document.getElementById("requirementsMeta"),
      capitalGapStatus: document.getElementById("capitalGapStatus"),
      technicianGapStatus: document.getElementById("technicianGapStatus"),
      equipmentGapStatus: document.getElementById("equipmentGapStatus"),
      diagnosisDate: document.getElementById("diagnosisDate"),
      resultBanner: document.getElementById("resultBanner"),
      resultBannerTitle: document.getElementById("resultBannerTitle"),
      resultBannerMeta: document.getElementById("resultBannerMeta"),
      resultActionWrap: document.getElementById("resultActionWrap"),
      resultActionButtons: document.getElementById("resultActionButtons"),
      resultActionNote: document.getElementById("resultActionNote"),
      resultBrief: document.getElementById("resultBrief"),
      resultBriefMeta: document.getElementById("resultBriefMeta"),
      btnCopyResultBrief: document.getElementById("btnCopyResultBrief"),
      fallbackGuide: document.getElementById("fallbackGuide"),
      legalBasis: document.getElementById("legalBasis"),
      focusProfileBox: document.getElementById("focusProfileBox"),
      qualityFlagsBox: document.getElementById("qualityFlagsBox"),
      proofClaimBox: document.getElementById("proofClaimBox"),
      reviewPresetBox: document.getElementById("reviewPresetBox"),
      caseStoryBox: document.getElementById("caseStoryBox"),
      operatorDemoBox: document.getElementById("operatorDemoBox"),
      runtimeReasoningCardBox: document.getElementById("runtimeReasoningCardBox"),
      coverageGuide: document.getElementById("coverageGuide"),
      typedCriteriaBox: document.getElementById("typedCriteriaBox"),
      evidenceChecklistBox: document.getElementById("evidenceChecklistBox"),
      nextActionsBox: document.getElementById("nextActionsBox"),
      };

      const _debounce = (fn, ms) => {
        let tid;
        const d = (...a) => { clearTimeout(tid); tid = setTimeout(() => fn(...a), ms); };
        d.cancel = () => clearTimeout(tid);
        d.flush = (...a) => { clearTimeout(tid); fn(...a); };
        return d;
      };
      const Core = (() => {
      const toNum = (value) => {
        const n = Number(value || 0);
        if (!Number.isFinite(n)) return 0;
        return Math.max(0, n);
      };
      const toInt = (value) => Math.max(0, Math.floor(toNum(value)));
      const formatEok = (value) => {
        const rounded = Math.round(toNum(value) * 100) / 100;
        return `${rounded.toLocaleString("ko-KR")}억`;
      };
      const toDateLabel = (dateObj) => {
        const y = dateObj.getFullYear();
        const m = String(dateObj.getMonth() + 1).padStart(2, "0");
        const d = String(dateObj.getDate()).padStart(2, "0");
        return `${y}-${m}-${d}`;
      };
      const computeGap = (required, current) => {
        const req = toNum(required);
        const cur = toNum(current);
        const gap = Math.max(0, req - cur);
        return {
          required: req,
          current: cur,
          gap,
          isSatisfied: gap <= 0,
        };
      };
      const computeIntGap = (required, current) => {
        const req = toInt(required);
        const cur = toInt(current);
        const gap = Math.max(0, req - cur);
        return {
          required: req,
          current: cur,
          gap,
          isSatisfied: gap <= 0,
        };
      };
      const predictDiagnosisDate = (depositDays) => {
        const days = Math.max(0, toInt(depositDays));
        const base = new Date();
        const target = new Date(base);
        target.setDate(base.getDate() + days);
        return {
          days,
          dateLabel: toDateLabel(target),
        };
      };
      const detectSuspiciousCapitalInput = (rawInput, inputEok, requiredEok) => {
        const raw = String(rawInput || "").trim().replace(/,/g, "");
        if (!raw) return false;
        const value = toNum(inputEok);
        const required = toNum(requiredEok);
        const overThreeX = required > 0 && value > required * 3;
        const decimalPatternOdd = !/^\\d+(\\.\\d{1,2})?$/.test(raw);
        const likelyUnitMistake = /^\\d{2,}$/.test(raw) && value >= 10;
        return overThreeX || decimalPatternOdd || likelyUnitMistake;
      };
      return {
        toNum,
        toInt,
        formatEok,
        computeGap,
        computeIntGap,
        predictDiagnosisDate,
        detectSuspiciousCapitalInput,
      };
    })();

    const esc = (value) =>
      String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");

    const copyText = async (text) => {
      const value = String(text || "").trim();
      if (!value) return false;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
          await navigator.clipboard.writeText(value);
          return true;
        } catch (_error) {}
      }
      try {
        const area = document.createElement("textarea");
        area.value = value;
        area.setAttribute("readonly", "readonly");
        area.style.position = "fixed";
        area.style.top = "-9999px";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.focus();
        area.select();
        const copied = document.execCommand("copy");
        document.body.removeChild(area);
        return !!copied;
      } catch (_error) {
        return false;
      }
    };

    applyExperienceLayout();
    ui.permitInputWizard = document.getElementById("permitInputWizard");
    ui.permitWizardRail = document.getElementById("permitWizardRail");
    ui.permitWizardStepTitle = document.getElementById("permitWizardStepTitle");
    ui.permitWizardStepNote = document.getElementById("permitWizardStepNote");
    ui.permitWizardProgressLabel = document.getElementById("permitWizardProgressLabel");
    ui.permitWizardProgressMeta = document.getElementById("permitWizardProgressMeta");
    ui.permitWizardNextActionText = document.getElementById("permitWizardNextActionText");
    ui.permitWizardProgressBar = document.getElementById("permitWizardProgressBar");
    ui.permitWizardProgressFill = document.getElementById("permitWizardProgressFill");
    ui.permitWizardProgressCount = document.getElementById("permitWizardProgressCount");
    ui.permitWizardMobileStickyLabel = document.getElementById("permitWizardMobileStickyLabel");
    ui.permitWizardMobileStickyAction = document.getElementById("permitWizardMobileStickyAction");
    ui.permitWizardMobileStickyCompact = document.getElementById("permitWizardMobileStickyCompact");
    ui.permitWizardMobileStickyMeta = document.getElementById("permitWizardMobileStickyMeta");
    ui.permitWizardMobileStickyCount = document.getElementById("permitWizardMobileStickyCount");
    ui.permitWizardSummary = document.getElementById("permitWizardSummary");
    ui.permitWizardBlocker = document.getElementById("permitWizardBlocker");
    ui.permitWizardStep1 = document.getElementById("permitWizardStep1");
    ui.permitWizardStep2 = document.getElementById("permitWizardStep2");
    ui.permitWizardStep3 = document.getElementById("permitWizardStep3");
    ui.permitWizardStep4 = document.getElementById("permitWizardStep4");
    ui.focusModePills = document.getElementById("focusModePills");
    ui.smartIndustryProfile = document.getElementById("smartIndustryProfile");
    ui.resultBanner = document.getElementById("resultBanner");
    ui.resultBannerTitle = document.getElementById("resultBannerTitle");
    ui.resultBannerMeta = document.getElementById("resultBannerMeta");
    ui.resultActionWrap = document.getElementById("resultActionWrap");
    ui.resultActionButtons = document.getElementById("resultActionButtons");
    ui.resultActionNote = document.getElementById("resultActionNote");
    ui.resultBrief = document.getElementById("resultBrief");
    ui.resultBriefMeta = document.getElementById("resultBriefMeta");
    ui.btnCopyResultBrief = document.getElementById("btnCopyResultBrief");
    ui.fillRequirementPreset = document.getElementById("fillRequirementPreset");
    ui.resetHoldingsPreset = document.getElementById("resetHoldingsPreset");
    ui.presetActionHint = document.getElementById("presetActionHint");
    ui.holdingsPriorityHint = document.getElementById("holdingsPriorityHint");
    ui.industryAutoReason = document.getElementById("industryAutoReason");
    ui.mobileQuickBar = document.getElementById("mobileQuickBar");
    ui.mobileQuickTitle = document.getElementById("mobileQuickTitle");
    ui.mobileQuickMeta = document.getElementById("mobileQuickMeta");
    ui.mobileQuickPresetButton = document.getElementById("mobileQuickPresetButton");
    ui.mobileQuickResultButton = document.getElementById("mobileQuickResultButton");
    ui.advancedInputs = document.getElementById("advancedInputs");
    ui.optionalPriorityHint = document.getElementById("optionalPriorityHint");
    ui.optionalChecklistToggle = document.getElementById("optionalChecklistToggle");

    const makeOption = (value, label) => {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = label;
      return opt;
    };

    const FOCUS_CATEGORY_CODE = "SEL-FOCUS";
    const INFERRED_CATEGORY_CODE = "SEL-INFERRED";
    const allIndustryRows = Array.isArray(permitCatalog.industries) ? permitCatalog.industries : [];
    const platformCatalog = permitCatalog.platform_catalog && typeof permitCatalog.platform_catalog === "object"
      ? permitCatalog.platform_catalog
      : { major_categories: [], industries: [], summary: {} };
    const masterCatalog = permitCatalog.master_catalog && typeof permitCatalog.master_catalog === "object"
      ? permitCatalog.master_catalog
      : { major_categories: [], industries: [], summary: {} };
    const displayCatalog = Array.isArray(masterCatalog.industries) && masterCatalog.industries.length
      ? masterCatalog
      : (Array.isArray(platformCatalog.industries) && platformCatalog.industries.length
        ? platformCatalog
      : {
          major_categories: Array.isArray(permitCatalog.major_categories) ? permitCatalog.major_categories : [],
          industries: Array.isArray(permitCatalog.industries) ? permitCatalog.industries : [],
          summary: permitCatalog.summary && typeof permitCatalog.summary === "object" ? permitCatalog.summary : {},
        });
    const displayIndustryRows = Array.isArray(displayCatalog.industries) ? displayCatalog.industries : [];
    const displayMajorCategories = Array.isArray(displayCatalog.major_categories) ? displayCatalog.major_categories : [];
    const displayMajorCategoriesByCode = (() => {
      const map = Object.create(null);
      displayMajorCategories.forEach((row) => {
        const key = String(row.major_code || "");
        if (!key) return;
        map[key] = row;
      });
      return map;
    })();
    const selectorCatalog = permitCatalog.selector_catalog && typeof permitCatalog.selector_catalog === "object"
      ? permitCatalog.selector_catalog
      : { major_categories: [], industries: [], summary: {} };
    const selectorCatalogRows = Array.isArray(selectorCatalog.industries) ? selectorCatalog.industries : [];
    const focusSelectorEntries = selectorCatalogRows.length
      ? selectorCatalogRows.filter((row) => String(row.selector_kind || "") === "focus")
      : (Array.isArray(permitCatalog.focus_selector_entries) ? permitCatalog.focus_selector_entries : []);
    const inferredSelectorEntries = selectorCatalogRows.length
      ? selectorCatalogRows.filter((row) => String(row.selector_kind || "") === "inferred")
      : (Array.isArray(permitCatalog.inferred_selector_entries) ? permitCatalog.inferred_selector_entries : []);
    const selectorEntries = selectorCatalogRows.length
      ? selectorCatalogRows
      : (Array.isArray(permitCatalog.selector_entries) ? permitCatalog.selector_entries : [...focusSelectorEntries, ...inferredSelectorEntries]);
    const selectorEntriesByCode = (() => {
      const map = Object.create(null);
      selectorEntries.forEach((row) => {
        const key = String(row.service_code || row.selector_code || "");
        if (!key) return;
        map[key] = row;
      });
      return map;
    })();
    const allIndustryRowsByCode = (() => {
      const map = Object.create(null);
      allIndustryRows.forEach((row) => {
        const key = String(row.service_code || "");
        if (!key) return;
        map[key] = row;
      });
      return map;
    })();
    const displayRowsByCode = (() => {
      const map = Object.create(null);
      displayIndustryRows.forEach((row) => {
        const key = String(row.service_code || "");
        if (!key) return;
        map[key] = row;
      });
      return map;
    })();

    const qualityFlagLabels = {
      law_only: "법령만 확보",
      stale_candidate_source: "후보 재현 불일치",
      sparse_criteria: "기준 문장 부족",
      generic_basis_title: "근거 제목 일반적",
      article_name_unmatched: "업종명 직접 불일치",
    };

    const proofDomainLabels = {
      industry_selector: "업종 선택",
      capital_eok: "자본금",
      technicians_count: "기술인력",
      other_requirement_checklist: "기타 요건 체크리스트",
      equipment_inventory: "장비 현황",
      deposit_hold_days: "예치기간",
      safety_environment: "안전·환경",
      facility_equipment: "시설·장비",
    };

    const otherRequirementLabels = {
      equipment: "장비",
      deposit: "예치",
      office: "사무실",
      guarantee: "보증",
      insurance: "보험",
      facility_equipment: "시설·장비",
      safety_environment: "안전·환경",
      document: "서류",
      operations: "운영체계",
    };

    const reviewReasonLabels = {
      capital_and_technician_shortfall: "자본금·기술인력 동시 부족",
      capital_shortfall_only: "자본금 부족",
      technician_shortfall_only: "기술인력 부족",
      other_requirement_documents_missing: "서류 보완 검토",
    };

    const promptBindingFocusLabels = {
      manual_review_gate: "수동 검토 게이트",
      capital_and_technician_gap_first: "자본금·기술인력 동시 부족 우선",
      capital_gap_first: "자본금 부족 우선",
      technician_gap_first: "기술인력 부족 우선",
      review_reason_first: "검토 사유 우선",
      baseline_reference: "기준값 참조",
    };

    const reviewChecklistPresetMap = {
      office: "officeSecuredInput",
      facility_equipment: "facilitySecuredInput",
      equipment: "facilitySecuredInput",
      guarantee: "insuranceSecuredInput",
      insurance: "insuranceSecuredInput",
      safety_environment: "safetySecuredInput",
      document: "documentReadyInput",
    };

    const getRegistrationProfile = (row) => {
      if (!row || typeof row !== "object") return {};
      return row.registration_requirement_profile && typeof row.registration_requirement_profile === "object"
        ? row.registration_requirement_profile
        : {};
    };

    const getReviewCasePresets = (row) => (
      Array.isArray(row && row.review_case_presets) ? row.review_case_presets : []
    );

    const getCaseStorySurface = (row) => (
      row && typeof row.case_story_surface === "object" ? row.case_story_surface : null
    );

    const getOperatorDemoSurface = (row) => (
      row && typeof row.operator_demo_surface === "object" ? row.operator_demo_surface : null
    );

    const getReviewReasonLabel = (reason) => reviewReasonLabels[String(reason || "").trim()] || String(reason || "").trim();
    const getPromptBindingFocusLabel = (focus) => (
      promptBindingFocusLabels[String(focus || "").trim()] || String(focus || "").trim()
    );

    const normalizeSearchKey = (value) => String(value || "")
      .toLowerCase()
      .replace(/[^0-9a-z가-힣]+/g, "");
    const getFocusMode = () => String((ui.focusModeSelect && ui.focusModeSelect.value) || "all");
    const focusModeLabels = {
      focus_only: "집중 업종",
      all: "전체 업종",
      inferred_only: "추론 후보",
    };
    const getIndustrySearchTerm = () => String((ui.industrySearchInput && ui.industrySearchInput.value) || "").trim().toLowerCase();
    const getSyntheticCategoryCode = (mode) => (mode === "inferred_only" ? INFERRED_CATEGORY_CODE : FOCUS_CATEGORY_CODE);
    const getSyntheticCategoryLabel = (mode) => (mode === "inferred_only" ? "추론 점검군" : "핵심 업종군");

    const getAliasSearchTokens = (row) => {
      const aliases = Array.isArray(row && row.platform_selector_aliases) ? row.platform_selector_aliases : [];
      return aliases
        .flatMap((item) => {
          if (item && typeof item === "object") {
            return [
              String(item.service_name || ""),
              String(item.selector_category_name || ""),
            ];
          }
          return [String(item || "")];
        })
        .map((item) => item.trim())
        .filter(Boolean);
    };

    const getRowSearchTokens = (row) => {
      const aliases = getAliasSearchTokens(row);
      return [
        String((row && row.service_name) || ""),
        String((row && row.major_name) || ""),
        String((row && row.group_name) || ""),
        String((row && row.law_title) || ""),
        String((row && row.legal_basis_title) || ""),
        ...aliases,
      ]
        .map((item) => item.trim())
        .filter(Boolean);
    };

    const getRowPrimarySearchTokens = (row) => {
      const aliases = getAliasSearchTokens(row);
      return [
        String((row && row.service_name) || ""),
        ...aliases,
      ]
        .map((item) => item.trim())
        .filter(Boolean);
    };

    const getRowSearchFieldEntries = (row) => {
      const entries = [
        { type: "service_name", weight: 600, value: String((row && row.service_name) || "") },
        ...getAliasSearchTokens(row).map((value) => ({ type: "alias", weight: 440, value })),
        { type: "major_name", weight: 180, value: String((row && row.major_name) || "") },
        { type: "group_name", weight: 160, value: String((row && row.group_name) || "") },
        { type: "law_title", weight: 120, value: String((row && row.law_title) || "") },
        { type: "legal_basis_title", weight: 90, value: String((row && row.legal_basis_title) || "") },
      ];
      const seen = new Set();
      return entries.filter((entry) => {
        const rawValue = String((entry && entry.value) || "").trim();
        const normalizedValue = normalizeSearchKey(rawValue);
        if (!rawValue || !normalizedValue) return false;
        const dedupeKey = normalizedValue;
        if (seen.has(dedupeKey)) return false;
        seen.add(dedupeKey);
        return true;
      });
    };

    const getSearchFieldTypeLabel = (fieldType) => {
      const key = String(fieldType || "").trim();
      if (key === "service_name") return "업종명";
      if (key === "alias") return "별칭";
      if (key === "major_name") return "대분류";
      if (key === "group_name") return "그룹명";
      if (key === "law_title") return "법령명";
      if (key === "legal_basis_title") return "근거명";
      return "검색 항목";
    };

    const getSearchMatchMeta = (row, searchTerm) => {
      const rawTerm = String(searchTerm || "").trim().toLowerCase();
      const normalizedTerm = normalizeSearchKey(rawTerm);
      if (!rawTerm && !normalizedTerm) {
        return {
          matched: true,
          score: 0,
          exact: false,
          prefix: false,
          fieldType: "",
          fieldIndex: 999,
        };
      }
      let best = null;
      getRowSearchFieldEntries(row).forEach((entry, index) => {
        const rawValue = String((entry && entry.value) || "").trim().toLowerCase();
        const normalizedValue = normalizeSearchKey(rawValue);
        if (!rawValue && !normalizedValue) return;
        let matched = false;
        let exact = false;
        let prefix = false;
        if (rawTerm && rawValue.includes(rawTerm)) {
          matched = true;
          exact = rawValue === rawTerm;
          prefix = rawValue.startsWith(rawTerm);
        }
        if (!matched && normalizedTerm && normalizedValue.includes(normalizedTerm)) {
          matched = true;
          exact = normalizedValue === normalizedTerm;
          prefix = normalizedValue.startsWith(normalizedTerm);
        }
        if (!matched) return;
        const lengthPenaltyBase = normalizedTerm
          ? Math.abs(normalizedValue.length - normalizedTerm.length)
          : Math.abs(rawValue.length - rawTerm.length);
        const score = Number(entry.weight || 0)
          + (exact ? 320 : (prefix ? 200 : 80))
          - Math.min(lengthPenaltyBase, 36);
        const candidate = {
          matched: true,
          score,
          exact,
          prefix,
          fieldType: String(entry.type || ""),
          fieldIndex: index,
        };
        if (
          !best
          || candidate.score > best.score
          || (candidate.score === best.score && candidate.fieldIndex < best.fieldIndex)
        ) {
          best = candidate;
        }
      });
      return best || {
        matched: false,
        score: -1,
        exact: false,
        prefix: false,
        fieldType: "",
        fieldIndex: 999,
      };
    };

    const filterAndSortRowsBySearch = (rows, searchTerm) => {
      const rawTerm = String(searchTerm || "").trim();
      const normalizedTerm = normalizeSearchKey(rawTerm);
      if (!rawTerm && !normalizedTerm) return [...rows];
      return rows
        .map((row) => ({
          row,
          meta: getSearchMatchMeta(row, searchTerm),
        }))
        .filter((item) => !!(item.meta && item.meta.matched))
        .sort((left, right) => {
          const leftScore = Number((left.meta && left.meta.score) || 0);
          const rightScore = Number((right.meta && right.meta.score) || 0);
          if (rightScore !== leftScore) return rightScore - leftScore;
          const leftFieldIndex = Number((left.meta && left.meta.fieldIndex) || 999);
          const rightFieldIndex = Number((right.meta && right.meta.fieldIndex) || 999);
          if (leftFieldIndex !== rightFieldIndex) return leftFieldIndex - rightFieldIndex;
          return String((left.row && left.row.service_name) || "").localeCompare(String((right.row && right.row.service_name) || ""), "ko");
        })
        .map((item) => item.row);
    };

    const matchesFocusMode = (row, mode) => {
      const profile = getRegistrationProfile(row);
      if (mode === "focus_only") return !!profile.focus_target;
      if (mode === "inferred_only") return !!profile.inferred_focus_candidate;
      return true;
    };

    const matchesSearchTerm = (row, searchTerm) => !!getSearchMatchMeta(row, searchTerm).matched;

    const getFilteredIndustries = () => {
      const mode = getFocusMode();
      const searchTerm = getIndustrySearchTerm();
      return filterAndSortRowsBySearch(
        displayIndustryRows.filter((row) => matchesFocusMode(row, mode)),
        searchTerm,
      );
    };

    const getSyntheticCategoryRows = (mode) => {
      if (mode !== "inferred_only") return [];
      return filterAndSortRowsBySearch(inferredSelectorEntries, getIndustrySearchTerm());
    };

    const getFocusQuickSelectRows = (mode) => {
      const sourceRows = mode === "inferred_only" ? inferredSelectorEntries : focusSelectorEntries;
      return filterAndSortRowsBySearch(sourceRows, getIndustrySearchTerm());
    };

    const buildIndustriesByCategory = (rows) => {
      const map = Object.create(null);
      const preserveSearchOrder = !!getIndustrySearchTerm();
      rows.forEach((row) => {
        const key = String(row.major_code || "");
        if (!key) return;
        if (!map[key]) map[key] = [];
        map[key].push(row);
      });
      if (!preserveSearchOrder) {
        Object.keys(map).forEach((key) => {
          map[key].sort((a, b) => String(a.service_name || "").localeCompare(String(b.service_name || ""), "ko"));
        });
      }
      return map;
    };

    const getVisibleCategoryRows = (filteredRows, visibleCounts) => {
      const searchTerm = getIndustrySearchTerm();
      if (!searchTerm) {
        return displayMajorCategories
          .map((row) => {
            const code = String(row.major_code || "");
            const count = Number(visibleCounts[code] || 0);
            if (!code || count <= 0) return null;
            return {
              major_code: code,
              major_name: String(row.major_name || ""),
              industry_count: count,
            };
          })
          .filter(Boolean);
      }
      const seen = new Set();
      return filteredRows
        .map((row) => {
          const code = String((row && row.major_code) || "");
          if (!code || seen.has(code) || Number(visibleCounts[code] || 0) <= 0) return null;
          seen.add(code);
          const meta = displayMajorCategoriesByCode[code] || row || {};
          return {
            major_code: code,
            major_name: String(meta.major_name || row.major_name || ""),
            industry_count: Number(visibleCounts[code] || 0),
          };
        })
        .filter(Boolean);
    };

    const buildFocusHint = (mode, filteredRows) => {
      const summary = permitCatalog.summary || {};
      const focusTotal = Number(summary.focus_target_total || 0);
      const realFocusTotal = Number(summary.real_focus_target_total || 0);
      const rulesFocusTotal = Number(summary.rules_only_focus_target_total || 0);
      const focusWithOtherTotal = Number(summary.focus_target_with_other_total || 0);
      const inferredTotal = Number(summary.inferred_focus_target_total || 0);
      const searchGuide = "업종명 우선, 별칭/법령명 보조 검색입니다.";
      if (mode === "focus_only") {
        return `핵심 업종 ${focusTotal}개를 우선 노출합니다. 실업종 ${realFocusTotal}개, 등록기준 업종군 ${rulesFocusTotal}개이며, 이 중 기타 요소까지 구조화된 업종은 ${focusWithOtherTotal}개입니다. ${searchGuide}`;
      }
      if (mode === "inferred_only") {
        return `추론 후보 ${inferredTotal}개만 노출합니다. 오탐 가능성이 있어 별도 검증이 필요합니다. ${searchGuide}`;
      }
      return `전체 플랫폼 카탈로그 ${filteredRows.length}개 중 핵심 업종 ${focusTotal}개, 기타 요소까지 구조화된 업종 ${focusWithOtherTotal}개, 추론 후보 ${inferredTotal}개입니다. ${searchGuide}`;
    };

    const renderFocusQuickSelect = () => {
      if (!ui.focusQuickSelect) return;
      const mode = getFocusMode();
      const sourceRows = getFocusQuickSelectRows(mode);
      ui.focusQuickSelect.innerHTML = "";
      ui.focusQuickSelect.appendChild(makeOption("", mode === "inferred_only" ? "추론 후보 빠른 선택" : "핵심 업종 빠른 선택"));
      sourceRows.forEach((row) => {
        const code = String(row.selector_code || row.service_code || "");
        const name = String(row.service_name || "");
        if (!code || !name) return;
        const originLabel = row.is_rules_only ? "등록기준군" : "실업종";
        ui.focusQuickSelect.appendChild(makeOption(code, `${name} (${originLabel})`));
      });
      if (ui.focusQuickHint) {
        ui.focusQuickHint.textContent = sourceRows.length
          ? `빠른 선택 ${sourceRows.length}개를 제공합니다. 검색창과 같이 사용하면 바로 해당 업종으로 이동합니다.`
          : "현재 조회 모드에 해당하는 빠른 선택 업종이 없습니다.";
      }
    };

    const renderCategories = () => {
      const mode = getFocusMode();
      const previousValue = String(ui.categorySelect.value || "");
      const filteredRows = getFilteredIndustries();
      const industriesByCategory = buildIndustriesByCategory(filteredRows);
      const syntheticRows = getSyntheticCategoryRows(mode);
      const syntheticCode = getSyntheticCategoryCode(mode);
      const syntheticLabel = getSyntheticCategoryLabel(mode);
      const visibleCounts = Object.keys(industriesByCategory).reduce((acc, key) => {
        acc[key] = industriesByCategory[key].length;
        return acc;
      }, Object.create(null));
      ui.categorySelect.innerHTML = "";
      ui.categorySelect.appendChild(makeOption("", "카테고리 선택"));
      const visibleCodes = [];
      if (syntheticRows.length) {
        visibleCodes.push(syntheticCode);
        ui.categorySelect.appendChild(makeOption(syntheticCode, `${syntheticLabel} (${syntheticRows.length}개)`));
      }
      if (mode !== "inferred_only") {
        getVisibleCategoryRows(filteredRows, visibleCounts).forEach((row) => {
          const code = String(row.major_code || "");
          const name = String(row.major_name || "");
          const count = Number(row.industry_count || visibleCounts[code] || 0);
          if (!code || !name || count <= 0) return;
          visibleCodes.push(code);
          ui.categorySelect.appendChild(makeOption(code, `${name} (${count}개)`));
        });
      }
      if (visibleCodes.includes(previousValue)) {
        ui.categorySelect.value = previousValue;
      } else if (visibleCodes.length === 1 || mode === "inferred_only" || !!getIndustrySearchTerm()) {
        ui.categorySelect.value = visibleCodes[0] || "";
      }
      if (ui.focusHint) {
        ui.focusHint.textContent = buildFocusHint(mode, filteredRows);
      }
      renderFocusQuickSelect();
    };

    const renderIndustries = () => {
      const mode = getFocusMode();
      const filteredRows = getFilteredIndustries();
      const industriesByCategory = buildIndustriesByCategory(filteredRows);
      const syntheticCode = getSyntheticCategoryCode(mode);
      const syntheticRows = getSyntheticCategoryRows(mode);
      const categoryCode = ui.categorySelect.value;
      const previousValue = String(ui.industrySelect.value || "");
      ui.industrySelect.innerHTML = "";
      ui.industrySelect.appendChild(makeOption("", "세부 업종 선택"));
      const rowsForCategory = categoryCode === syntheticCode
        ? syntheticRows
        : (industriesByCategory[categoryCode] || []);
      if (!categoryCode || !rowsForCategory.length) {
        ui.industryHint.textContent = filteredRows.length
          ? "선택한 조회 모드에 해당하는 카테고리를 먼저 선택하세요."
          : "현재 조회 모드에 해당하는 업종이 없습니다.";
        return;
      }
      const visibleCodes = [];
      rowsForCategory.forEach((row) => {
        const code = String(row.selector_code || row.service_code || "");
        const name = String(row.service_name || "");
        const hasRule = !!row.has_rule;
        const hasCandidateCriteria = Number(row.candidate_criteria_count || 0) > 0;
        const hasCandidateLaw = Array.isArray(row.auto_law_candidates) && row.auto_law_candidates.length > 0;
        const profile = getRegistrationProfile(row);
        if (!code || !name) return;
        let statusLabel = "기준확정 필요";
        if (hasRule) statusLabel = "법령기준";
        else if (hasCandidateCriteria) statusLabel = "법령추출";
        else if (hasCandidateLaw) statusLabel = "법령후보";
        const focusLabel = profile.focus_target
          ? "핵심"
          : profile.inferred_focus_candidate
            ? "추론"
            : statusLabel;
        const originLabel = row.is_rules_only ? "등록기준군" : "실업종";
        visibleCodes.push(code);
        ui.industrySelect.appendChild(makeOption(code, `${name} (${focusLabel} · ${originLabel})`));
      });
      if (visibleCodes.includes(previousValue)) {
        ui.industrySelect.value = previousValue;
      }
      const coveragePct = Number((permitCatalog.summary && permitCatalog.summary.coverage_pct) || 0);
      const candidateCriteriaTotal = Number((permitCatalog.summary && permitCatalog.summary.candidate_criteria_total) || 0);
      if (mode === "focus_only") {
        ui.industryHint.textContent = "핵심 업종만 노출합니다. 현재 기준은 자본금·기술인력 필수이며, 기타 요소 포함 여부는 별도 배지로 구분합니다.";
      } else if (mode === "inferred_only") {
        ui.industryHint.textContent = "추론 후보는 오탐 가능성이 있어 법령 원문과 품질 플래그를 함께 확인해야 합니다.";
      } else if (categoryCode === syntheticCode) {
        ui.industryHint.textContent = "핵심 업종군은 자본금·기술인력·기타 요소가 함께 필요한 고신뢰 등록기준 업종 중심으로 모았습니다.";
      } else if (coveragePct >= 95) {
        ui.industryHint.textContent = "업종을 선택하면 자본금·기술인력·장비 기준이 즉시 표시됩니다.";
      } else {
        ui.industryHint.textContent = `실업종 기준 법령 연동 ${coveragePct.toFixed(2)}%, 자동 추출 ${candidateCriteriaTotal}건입니다. 미연동 업종은 계속 수집 중입니다.`;
      }
    };

    const getSelectedIndustry = () => {
      const code = String(ui.industrySelect.value || "");
      if (!code) return null;
      const directDisplayRow = displayRowsByCode[code] || null;
      const selectorEntry = selectorEntriesByCode[code] || null;
      const canonicalCode = String(
        (directDisplayRow && directDisplayRow.canonical_service_code)
          || (selectorEntry && (selectorEntry.canonical_service_code || selectorEntry.service_code))
          || code
      );
      const displayRow = directDisplayRow || displayRowsByCode[canonicalCode] || null;
      const canonicalRow = allIndustryRowsByCode[canonicalCode] || null;
      if (!displayRow) {
        if (canonicalRow) {
          return {
            ...canonicalRow,
            selected_display_service_code: code,
            canonical_service_code: canonicalCode,
            platform_selector_aliases: Array.isArray(canonicalRow.platform_selector_aliases)
              ? canonicalRow.platform_selector_aliases
              : (Array.isArray(selectorEntry && selectorEntry.platform_selector_aliases)
                ? selectorEntry.platform_selector_aliases
                : []),
            platform_has_focus_alias: !!(canonicalRow.platform_has_focus_alias || (selectorEntry && selectorEntry.platform_has_focus_alias)),
            platform_has_inferred_alias: !!(canonicalRow.platform_has_inferred_alias || (selectorEntry && selectorEntry.platform_has_inferred_alias)),
            is_platform_row: !!(canonicalRow.is_platform_row || (selectorEntry && selectorEntry.is_platform_row)),
          };
        }
        if (selectorEntry) {
          return {
            ...selectorEntry,
            selected_display_service_code: code,
            canonical_service_code: canonicalCode,
          };
        }
        return null;
      }
      if (!canonicalRow) return displayRow;
      return {
        ...displayRow,
        ...canonicalRow,
        selected_display_service_code: code,
        canonical_service_code: canonicalCode,
        platform_row_origin: String(displayRow.platform_row_origin || canonicalRow.platform_row_origin || ""),
        platform_selector_aliases: Array.isArray(displayRow.platform_selector_aliases)
          ? displayRow.platform_selector_aliases
          : (Array.isArray(canonicalRow.platform_selector_aliases) ? canonicalRow.platform_selector_aliases : []),
        platform_has_focus_alias: !!(displayRow.platform_has_focus_alias || canonicalRow.platform_has_focus_alias),
        platform_has_inferred_alias: !!(displayRow.platform_has_inferred_alias || canonicalRow.platform_has_inferred_alias),
        is_platform_row: !!(displayRow.is_platform_row || canonicalRow.is_platform_row),
      };
    };

    const ensureSyntheticIndustryOptions = () => {
      if (!ui.categorySelect || !ui.industrySelect) return;
      const mode = getFocusMode();
      const syntheticCode = getSyntheticCategoryCode(mode);
      if (String(ui.categorySelect.value || "") !== syntheticCode) return;
      if ((ui.industrySelect.options || []).length > 1) return;
      const syntheticRows = getSyntheticCategoryRows(mode);
      syntheticRows.forEach((row) => {
        const code = String(row.service_code || row.selector_code || "");
        const name = String(row.service_name || "");
        if (!code || !name) return;
        ui.industrySelect.appendChild(
          makeOption(code, `${name} (${row.is_rules_only ? "등록기준군" : "실업종"})`)
        );
      });
    };

    const syncFocusQuickSelectSelection = () => {
      if (!ui.focusQuickSelect) return;
      const selected = getSelectedIndustry();
      if (!selected) {
        ui.focusQuickSelect.value = "";
        return;
      }
      const selectedOption = ui.industrySelect && ui.industrySelect.options && ui.industrySelect.selectedIndex >= 0
        ? ui.industrySelect.options[ui.industrySelect.selectedIndex]
        : null;
      const selectedLabel = String((selectedOption && selectedOption.textContent) || "")
        .split(" (", 1)[0]
        .trim();
      const candidateKeys = [
        String(selected.selected_display_service_code || ""),
        String(selected.service_code || ""),
        String(selected.canonical_service_code || ""),
      ].filter(Boolean);
      let matchedValue = candidateKeys.find((key) =>
        [...ui.focusQuickSelect.options].some((option) => String(option.value || "") === key)
      ) || "";
      if (!matchedValue && selectedLabel) {
        const matchedOption = [...ui.focusQuickSelect.options].find((option) =>
          String(option.textContent || "").split(" (", 1)[0].trim() === selectedLabel
        );
        matchedValue = matchedOption ? String(matchedOption.value || "") : "";
      }
      ui.focusQuickSelect.value = matchedValue;
    };

    const applyIndustrySelection = (selectionCode) => {
      const targetCode = String(selectionCode || "");
      if (!targetCode) return false;
      permitSearchStarted = true;
      const selectorEntry = selectorEntriesByCode[targetCode] || null;
      const directDisplayTarget = displayRowsByCode[targetCode] || null;
      const canonicalCode = String(
        (directDisplayTarget && directDisplayTarget.canonical_service_code)
          || (selectorEntry && (selectorEntry.canonical_service_code || selectorEntry.service_code))
          || targetCode
      );
      const displayTarget = directDisplayTarget || displayRowsByCode[canonicalCode] || null;
      const target = allIndustryRowsByCode[canonicalCode] || displayTarget || null;
      if (!target && !selectorEntry) return false;
      if (ui.categorySelect) {
        const mode = getFocusMode();
        const syntheticCode = getSyntheticCategoryCode(mode);
        const useSyntheticCategory = (!!selectorEntry && !displayTarget) || (mode === "inferred_only" && !!selectorEntry);
        ui.categorySelect.value = useSyntheticCategory
          ? String((selectorEntry && selectorEntry.selector_category_code) || syntheticCode)
          : String((displayTarget && displayTarget.major_code) || ((target && target.major_code) || ""));
      }
      renderIndustries();
      ensureSyntheticIndustryOptions();
      if (ui.industrySelect) {
        const useSyntheticSelection = (!!selectorEntry && !displayTarget) || (getFocusMode() === "inferred_only" && !!selectorEntry);
        const selectedValue = String(
          useSyntheticSelection
            ? targetCode
            : ((displayTarget && displayTarget.service_code) || canonicalCode)
        );
        if (![...ui.industrySelect.options].some((option) => option.value === selectedValue) && selectorEntry) {
          ui.industrySelect.appendChild(
            makeOption(
              selectedValue,
              `${String(selectorEntry.service_name || "선택 업종")} (${selectorEntry.is_rules_only ? "등록기준군" : "실업종"})`,
            )
          );
        }
        ui.industrySelect.value = selectedValue;
      }
      syncFocusQuickSelectSelection();
      return true;
    };

    const getSelectedRule = (selected) => {
      if (!selected || typeof selected !== "object") return null;
      const candidateKeys = [
        String(selected.service_code || ""),
        String(selected.canonical_service_code || ""),
        String(selected.selected_display_service_code || ""),
      ].filter(Boolean);
      for (const key of candidateKeys) {
        if (ruleLookup[key]) return ruleLookup[key];
      }
      return null;
    };

    let permitWizardStepIndex = 0;
    let permitSearchStarted = false;
    let permitAutoSelectionReasonText = "";
    let permitAutoSelectionReasonKind = "";
    let permitAutoSelectionReasonMeta = null;
    let optionalChecklistExpanded = false;
    let optionalChecklistPlanKey = "";
    const setPermitAutoSelectionReasonState = (text, kind, meta) => {
      permitAutoSelectionReasonText = String(text || "").trim();
      permitAutoSelectionReasonKind = String(kind || "").trim();
      permitAutoSelectionReasonMeta = meta && typeof meta === "object"
        ? {
            query: String(meta.query || "").trim(),
            fieldLabel: String(meta.fieldLabel || "").trim(),
            detailText: String(meta.detailText || "").trim(),
          }
        : null;
    };
    const clearPermitAutoSelectionReasonState = () => {
      permitAutoSelectionReasonText = "";
      permitAutoSelectionReasonKind = "";
      permitAutoSelectionReasonMeta = null;
    };
    const getIndustryAutoReasonTone = (kind) => {
      const normalized = String(kind || "").trim();
      if (!normalized) return "guide";
      if (["정확 일치", "접두 일치", "관련도 최고"].includes(normalized)) return "match";
      if (["검색 1건", "선택 1건", "자동 선택"].includes(normalized)) return "search";
      if (["빠른 선택", "직접 확정"].includes(normalized)) return "direct";
      return "guide";
    };
    const getIndustryAutoReasonIcon = (kind, tone = "") => {
      const normalizedTone = String(tone || "").trim();
      if (normalizedTone === "match") return "=";
      if (normalizedTone === "search") return "~";
      if (normalizedTone === "direct") return ">";
      if (normalizedTone === "guide") return "i";
      const normalized = String(kind || "").trim();
      if (!normalized) return "i";
      if (["?? ??", "?? ??", "??? ??"].includes(normalized)) return "=";
      if (["?? 1?", "?? 1?", "?? ??"].includes(normalized)) return "~";
      if (["?? ??", "?? ??"].includes(normalized)) return ">";
      return "i";
    };
    const getPermitCoreFieldPlan = () => {
      const selected = getSelectedIndustry();
      const rule = getSelectedRule(selected);
      const req = rule && rule.requirements ? rule.requirements : {};
      const profile = getRegistrationProfile(selected);
      const structuredCapital = rule
        ? Core.toNum(req.capital_eok || 0)
        : (profile.capital_required ? Core.toNum(profile.capital_eok || 0) : 0);
      const structuredTechnicians = rule
        ? Core.toInt(req.technicians || 0)
        : (profile.technical_personnel_required ? Core.toInt(profile.technicians_required || 0) : 0);
      const structuredEquipment = rule
        ? Core.toInt(req.equipment_count || 0)
        : (profile.other_required ? Core.toInt(profile.equipment_count_required || 0) : 0);
      const hasStructuredCore = structuredCapital > 0 || structuredTechnicians > 0 || structuredEquipment > 0;
      const fields = [
        {
          key: "capital",
          label: "자본금",
          input: ui.capitalInput,
          requiredValue: structuredCapital > 0 ? structuredCapital : null,
          priority: 0,
        },
        {
          key: "technicians",
          label: "기술자",
          input: ui.technicianInput,
          requiredValue: structuredTechnicians > 0 ? structuredTechnicians : null,
          priority: 1,
        },
        {
          key: "equipment",
          label: "장비",
          input: ui.equipmentInput,
          requiredValue: structuredEquipment > 0 ? structuredEquipment : null,
          priority: 2,
        },
      ].map((field) => {
        const rawValue = String((field.input && field.input.value) || "").trim();
        const required = hasStructuredCore ? field.requiredValue !== null : false;
        return {
          ...field,
          rawValue,
          filled: !!rawValue,
          required,
        };
      });
      const requiredFields = fields.filter((field) => field.required);
      const missingRequiredFields = requiredFields.filter((field) => !field.filled);
      return {
        hasStructuredCore,
        fields,
        requiredFields,
        missingRequiredFields,
        requiredFieldCount: requiredFields.length,
        filledRequiredCount: requiredFields.filter((field) => field.filled).length,
      };
    };
    const getPermitWizardState = () => {
      const selectedIndustry = !!getSelectedIndustry();
      const searchTouched = permitSearchStarted
        || !!String((ui.industrySearchInput && ui.industrySearchInput.value) || "").trim()
        || selectedIndustry;
      const corePlan = getPermitCoreFieldPlan();
      const filledCoreCount = corePlan.filledRequiredCount;
      const optionalCheckedCount = [
        ui.officeSecuredInput,
        ui.facilitySecuredInput,
        ui.qualificationSecuredInput,
        ui.insuranceSecuredInput,
        ui.safetySecuredInput,
        ui.documentReadyInput,
      ].filter((node) => !!(node && node.checked)).length;
      return {
        selectedIndustry,
        searchTouched,
        hasStructuredCore: corePlan.hasStructuredCore,
        filledCoreCount,
        requiredCoreCount: corePlan.requiredFieldCount,
        requiredCoreLabels: corePlan.requiredFields.map((field) => field.label),
        missingCoreLabels: corePlan.missingRequiredFields.map((field) => field.label),
        optionalCheckedCount,
        completed: [
          searchTouched || selectedIndustry,
          selectedIndustry,
          selectedIndustry && (
            !corePlan.hasStructuredCore
            || filledCoreCount >= corePlan.requiredFieldCount
          ),
          optionalCheckedCount > 0,
        ],
      };
    };
    const getPermitCoreGuide = () => {
      const state = getPermitWizardState();
      const fallbackLabels = ["자본금", "기술자", "장비"];
      if (!state.hasStructuredCore) {
        return {
          count: 0,
          labels: [],
          labelText: "정량 기준",
          countText: "0개",
          isStructured: false,
        };
      }
      const labels = state.requiredCoreLabels.length ? state.requiredCoreLabels : fallbackLabels.slice(0, state.requiredCoreCount || fallbackLabels.length);
      const count = state.requiredCoreCount || labels.length || fallbackLabels.length;
      return {
        count,
        labels,
        labelText: labels.join(", "),
        countText: `${count}개`,
        isStructured: true,
      };
    };
    const syncIndustryAutoReason = () => {
      if (!ui.industryAutoReason) return;
      const selected = getSelectedIndustry();
      const selectedValue = String((ui.industrySelect && ui.industrySelect.value) || "").trim();
      const searchText = String((ui.industrySearchInput && ui.industrySearchInput.value) || "").trim();
      let reasonText = "";
      let reasonKind = "";
      let reasonMeta = null;
      if (selected || selectedValue) {
        reasonText = permitAutoSelectionReasonText
          || (searchText
            ? "검색 결과에서 가장 가까운 업종으로 자동 선택했습니다."
            : "직접 확정한 업종입니다. 이제 법정 기준과 부족 항목을 바로 비교합니다.");
        reasonKind = permitAutoSelectionReasonKind || (searchText ? "자동 선택" : "직접 확정");
        reasonMeta = permitAutoSelectionReasonMeta
          || (searchText
            ? { query: searchText, detailText: "기준으로 가장 가까운 업종을 자동 선택했습니다." }
            : null);
      } else if (searchText) {
        reasonText = "후보가 여러 개면 직접 업종을 확정해 주세요.";
        reasonKind = "후보 확인";
        reasonMeta = { query: searchText, detailText: "기준 후보가 여러 개라 직접 업종을 확정해 주세요." };
      } else {
        reasonText = "업종명이 정확할수록 자동선택이 빨라집니다.";
        reasonKind = "검색 팁";
      }
      ui.industryAutoReason.dataset.reasonKind = reasonKind;
      const reasonTone = getIndustryAutoReasonTone(reasonKind);
      ui.industryAutoReason.dataset.reasonTone = reasonTone;
      ui.industryAutoReason.dataset.reasonIcon = getIndustryAutoReasonIcon(reasonKind, reasonTone);
      ui.industryAutoReason.dataset.actionable = searchText ? "1" : "0";
      ui.industryAutoReason.setAttribute("aria-label", searchText ? `${reasonText} 눌러서 검색어를 수정할 수 있습니다.` : reasonText);
      ui.industryAutoReason.innerHTML = "";
      if (reasonMeta && reasonMeta.query) {
        const body = document.createElement("span");
        body.className = "auto-selection-reason-body";
        const prefix = document.createElement("span");
        prefix.className = "auto-selection-reason-copy";
        prefix.textContent = "검색어";
        body.appendChild(prefix);
        const token = document.createElement("strong");
        token.className = "auto-selection-token";
        token.textContent = reasonMeta.query;
        body.appendChild(token);
        if (reasonMeta.fieldLabel) {
          const field = document.createElement("span");
          field.className = "auto-selection-field";
          field.textContent = reasonMeta.fieldLabel;
          body.appendChild(field);
        }
        const detail = document.createElement("span");
        detail.className = "auto-selection-reason-copy";
        detail.textContent = reasonMeta.detailText || "기준으로 자동 선택했습니다.";
        body.appendChild(detail);
        ui.industryAutoReason.appendChild(body);
      } else {
        ui.industryAutoReason.textContent = reasonText;
      }
      ui.industryAutoReason.hidden = !reasonText;
    };
    const syncPermitWizardProgress = () => {
      if (
        !ui.permitWizardProgressLabel
        && !ui.permitWizardProgressMeta
        && !ui.permitWizardNextActionText
        && !ui.permitWizardProgressFill
        && !ui.permitWizardProgressCount
        && !ui.permitWizardProgressBar
        && !ui.permitWizardMobileStickyLabel
        && !ui.permitWizardMobileStickyAction
        && !ui.permitWizardMobileStickyCompact
        && !ui.permitWizardMobileStickyMeta
        && !ui.permitWizardMobileStickyCount
      ) return;
      const state = getPermitWizardState();
      const totalSteps = permitWizardStepsMeta.length;
      const currentIndex = Math.max(0, Math.min(totalSteps - 1, Number(permitWizardStepIndex) || 0));
      const requiredTotal = permitWizardStepsMeta.filter((step) => !step.optional).length;
      const requiredDone = permitWizardStepsMeta.reduce((count, step, stepIndex) => {
        if (step.optional) return count;
        return count + (state.completed[stepIndex] ? 1 : 0);
      }, 0);
      const progressPct = Math.round(((currentIndex + 1) / Math.max(1, totalSteps)) * 100);
      const labelText = `현재 ${currentIndex + 1}/${totalSteps} 단계`;
      const nextActionText = getPermitWizardNextActionCopy();
      let metaText = "";
      if (!state.searchTouched && !state.selectedIndustry) {
        metaText = `필수 ${requiredDone}/${requiredTotal} 완료 · 업종 검색부터 시작합니다.`;
      } else if (!state.selectedIndustry) {
        metaText = `필수 ${requiredDone}/${requiredTotal} 완료 · 업종 확정이 남았습니다.`;
      } else if (!state.hasStructuredCore) {
        metaText = `필수 ${requiredDone}/${requiredTotal} 완료 · 이 업종은 보유 현황 대신 법령·서류 확인이 중심입니다.`;
      } else if (state.filledCoreCount < state.requiredCoreCount) {
        metaText = `필수 ${requiredDone}/${requiredTotal} 완료 · 현재 보유 ${state.filledCoreCount}/${state.requiredCoreCount} 입력`;
      } else if (state.optionalCheckedCount > 0) {
        metaText = `필수 입력 완료 · 선택 ${state.optionalCheckedCount}건이 결과에 반영되고 있습니다.`;
      } else {
        metaText = "필수 입력 완료 · 마지막 선택 단계에서 준비 상태만 확인하면 됩니다.";
      }
      if (ui.permitWizardProgressLabel) ui.permitWizardProgressLabel.textContent = `현재 ${currentIndex + 1}/${totalSteps} 단계`;
      if (ui.permitWizardProgressMeta) ui.permitWizardProgressMeta.textContent = metaText;
      if (ui.permitWizardNextActionText) ui.permitWizardNextActionText.textContent = getPermitWizardNextActionCopy();
      if (ui.permitWizardProgressFill) ui.permitWizardProgressFill.style.width = `${progressPct}%`;
      if (ui.permitWizardProgressCount) ui.permitWizardProgressCount.textContent = `${currentIndex + 1}/${totalSteps}`;
      if (ui.permitWizardProgressLabel) ui.permitWizardProgressLabel.textContent = labelText;
      if (ui.permitWizardNextActionText) ui.permitWizardNextActionText.textContent = nextActionText;
      if (ui.permitWizardMobileStickyLabel) ui.permitWizardMobileStickyLabel.textContent = labelText;
      if (ui.permitWizardMobileStickyAction) ui.permitWizardMobileStickyAction.textContent = nextActionText;
      if (ui.permitWizardMobileStickyCompact) ui.permitWizardMobileStickyCompact.textContent = getPermitWizardMobileCompactCopy();
      if (ui.permitWizardMobileStickyMeta) ui.permitWizardMobileStickyMeta.textContent = metaText;
      if (ui.permitWizardMobileStickyCount) ui.permitWizardMobileStickyCount.textContent = `${currentIndex + 1}/${totalSteps}`;
      const stickyShellNode = document.getElementById("permitWizardMobileSticky");
      if (stickyShellNode) {
        stickyShellNode.setAttribute(
          "aria-label",
          `${labelText}. ${nextActionText}. ${getPermitWizardMobileCompactCopy()}. ${metaText}`
        );
      }
      if (ui.permitWizardProgressBar) {
        ui.permitWizardProgressBar.setAttribute("aria-valuenow", String(currentIndex + 1));
        ui.permitWizardProgressBar.setAttribute("aria-valuetext", `현재 ${currentIndex + 1}단계 / 총 ${totalSteps}단계`);
      }
    };
    const getPermitWizardMobileCompactCopy = () => {
      const state = getPermitWizardState();
      const coreGuide = getPermitCoreGuide();
      if (!state.searchTouched && !state.selectedIndustry) {
        return "업종 검색부터 시작";
      }
      if (!state.selectedIndustry) {
        return "후보에서 업종 확정";
      }
      if (!state.hasStructuredCore) {
        return "법령·서류 중심 확인";
      }
      if (state.filledCoreCount < state.requiredCoreCount) {
        const compactLabels = (coreGuide.labels || []).slice(0, Math.max(1, Math.min(2, state.requiredCoreCount || 1)));
        return compactLabels.length ? `${compactLabels.join("·")} 순서 입력` : "핵심 요건부터 입력";
      }
      if (state.optionalCheckedCount > 0) {
        return "브리프 복사 후 전달";
      }
      return "선택 준비만 체크하면 완료";
    };
    const getPermitWizardNextActionCopy = () => {
      const state = getPermitWizardState();
      if (!state.searchTouched && !state.selectedIndustry) {
        return "업종명 검색이나 빠른 선택으로 시작하세요.";
      }
      if (!state.selectedIndustry) {
        return "자동 선택 결과에서 업종을 확정하세요.";
      }
      if (!state.hasStructuredCore) {
        return "법령 근거와 준비 서류부터 확인하세요.";
      }
      if (state.filledCoreCount < state.requiredCoreCount) {
        const missing = state.missingCoreLabels.filter(Boolean);
        if (missing.length === 1) {
          return `${missing[0]}부터 입력하세요.`;
        }
        if (missing.length > 1) {
          return `${missing.join(", ")}를 순서대로 입력하세요.`;
        }
        return "현재 보유 필수 입력을 마무리하세요.";
      }
      if (state.optionalCheckedCount > 0) {
        return "전달 브리프를 복사해 바로 전달하세요.";
      }
      return "선택 준비 항목은 필요한 것만 체크하세요.";
    };
    const resolvePermitActionTargetNode = (target) => {
      if (!target) return null;
      return typeof target === "string"
        ? (document.querySelector(target) || document.getElementById(target))
        : target;
    };
    let permitGuidedFocusTimer = 0;
    let permitGuidedFocusNode = null;
    const clearPermitGuidedFocus = () => {
      if (permitGuidedFocusTimer) {
        window.clearTimeout(permitGuidedFocusTimer);
        permitGuidedFocusTimer = 0;
      }
      if (permitGuidedFocusNode) {
        permitGuidedFocusNode.classList.remove("guided-focus-target");
        delete permitGuidedFocusNode.dataset.guidedFocus;
        delete permitGuidedFocusNode.dataset.guidedFocusCopy;
        delete permitGuidedFocusNode.dataset.guidedFocusLevel;
        permitGuidedFocusNode = null;
      }
    };
    const resolvePermitGuidedFocusNode = (node) => {
      if (!node) return null;
      return node.closest(".field, .check-item, .result-banner, .result-card, .wizard-progress-card, .optional-toggle-wrap, .btn-row") || node;
    };
    const getPermitGuidedFocusCopy = (target, node, source = "") => {
      const key = typeof target === "string"
        ? target
        : String((node && (node.id || node.name || "")) || "").trim();
      if (source === "mobile") {
        if (key === "industrySearchInput") return "지금은 업종명만 다시 검색하면 됩니다.";
        if (key === "industrySelect") return "지금은 업종 하나만 확정하면 됩니다.";
        if (["capitalInput", "technicianInput", "equipmentInput"].includes(key)) return "지금 이 필수값만 채우면 됩니다.";
        if (key === "legalBasis") return "지금은 법령 근거만 먼저 확인하면 됩니다.";
        if (key === "btnCopyResultBrief") return "지금은 브리프만 복사하면 전달됩니다.";
        if (key === "optionalChecklistToggle") return "지금은 우선 항목만 체크하면 됩니다.";
      }
      if (key === "industrySearchInput") return "업종명만 다시 검색하면 후보가 바로 다시 정렬됩니다.";
      if (key === "industrySelect") return "여기서 원하는 업종만 확정하면 다음 단계로 넘어갑니다.";
      if (key === "capitalInput") return "자본금부터 입력하면 부족 금액이 바로 보입니다.";
      if (key === "technicianInput") return "기술자 수만 넣어도 충족 여부가 바로 바뀝니다.";
      if (key === "equipmentInput") return "장비 수를 넣으면 마지막 코어 비교가 끝납니다.";
      if (key === "legalBasis") return "정량 기준이 없을 때는 여기서 법령 근거를 먼저 확인합니다.";
      if (key === "btnCopyResultBrief") return "복사 후 카카오톡이나 문자로 바로 전달하면 됩니다.";
      if (key === "optionalChecklistToggle") return "우선 항목만 먼저 보고 나머지는 필요할 때 펼치면 됩니다.";
      if (node && node.matches && node.matches('#advancedInputs .check-item input')) return "준비된 항목이면 체크만 해도 전달 준비도가 올라갑니다.";
      return "여기만 확인하면 다음 행동이 이어집니다.";
    };
    const showPermitGuidedFocus = (node, helperCopy = "", options = {}) => {
      const highlightNode = resolvePermitGuidedFocusNode(node);
      if (!highlightNode) return;
      clearPermitGuidedFocus();
      highlightNode.classList.add("guided-focus-target");
      highlightNode.dataset.guidedFocus = "1";
      if (helperCopy) highlightNode.dataset.guidedFocusCopy = helperCopy;
      if (options && options.level) highlightNode.dataset.guidedFocusLevel = String(options.level);
      permitGuidedFocusNode = highlightNode;
      permitGuidedFocusTimer = window.setTimeout(() => {
        clearPermitGuidedFocus();
      }, 1400);
    };
    const focusPermitActionTarget = (target, options = {}) => {
      const node = resolvePermitActionTargetNode(target);
      if (!node) return false;
      if ("disabled" in node && node.disabled) return false;
      if (node.hidden) return false;
      if (node.closest("[hidden]")) return false;
      const style = window.getComputedStyle(node);
      if (!style || style.display === "none" || style.visibility === "hidden") return false;
      if (typeof node.scrollIntoView === "function") {
        node.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      if (typeof node.focus === "function") {
        try { node.focus({ preventScroll: true }); } catch (_error) { node.focus(); }
      }
      const source = options && options.source ? String(options.source) : "";
      showPermitGuidedFocus(node, getPermitGuidedFocusCopy(target, node, source), {
        level: source === "mobile" ? "sticky" : "",
      });
      return document.activeElement === node || (!!document.activeElement && node.contains(document.activeElement));
    };
    const getPermitWizardNextActionTarget = () => {
      const state = getPermitWizardState();
      if (!state.searchTouched && !state.selectedIndustry) {
        return { stepIndex: 0, target: "industrySearchInput" };
      }
      if (!state.selectedIndustry) {
        return { stepIndex: 0, target: "industrySelect" };
      }
      if (!state.hasStructuredCore) {
        return { stepIndex: 3, target: "legalBasis" };
      }
      if (state.filledCoreCount < state.requiredCoreCount) {
        const missing = state.missingCoreLabels.filter(Boolean);
        if (missing.includes("자본금")) return { stepIndex: 2, target: "capitalInput" };
        if (missing.includes("기술자")) return { stepIndex: 2, target: "technicianInput" };
        if (missing.includes("장비")) return { stepIndex: 2, target: "equipmentInput" };
        return { stepIndex: 2, target: "capitalInput" };
      }
      if (state.optionalCheckedCount > 0) {
        return { stepIndex: 3, target: "btnCopyResultBrief" };
      }
      const firstPriorityToggle = document.querySelector('#advancedInputs .check-item.is-priority input:not(:checked)');
      return { stepIndex: 3, target: firstPriorityToggle || "optionalChecklistToggle" };
    };
    const runPermitWizardNextAction = (source = "") => {
      const action = getPermitWizardNextActionTarget();
      if (!action) return;
      if (Number.isFinite(Number(action.stepIndex))) {
        setPermitWizardStep(Number(action.stepIndex), false);
      }
      window.setTimeout(() => {
        if (action.target === "btnCopyResultBrief") {
          const resultTarget = document.getElementById("resultBanner")
            || document.getElementById("result-title")
            || document.querySelector(".result-card");
          if (resultTarget && typeof resultTarget.scrollIntoView === "function") {
            resultTarget.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        }
        focusPermitActionTarget(action.target, { source });
      }, 80);
    };
    const findPermitWizardResumeStep = () => {
      const state = getPermitWizardState();
      if (!state.searchTouched && !state.selectedIndustry) return 0;
      if (!state.selectedIndustry) return 1;
      if (state.filledCoreCount < state.requiredCoreCount) return 2;
      return 3;
    };
    const syncPermitWizardSummary = () => {
      if (!ui.permitWizardSummary) return;
      const state = getPermitWizardState();
      const selected = getSelectedIndustry();
      const items = [];
      items.push(`조회 ${focusModeLabels[getFocusMode()] || "전체 업종"}`);
      items.push(selected ? `업종 ${String(selected.service_name || "").trim()}` : (state.searchTouched ? "업종 선택 대기" : "검색부터 시작"));
      if (!state.hasStructuredCore && selected) {
        items.push("현재 보유 구조화 기준 없음");
      } else {
        items.push(state.filledCoreCount > 0 ? `현재 보유 ${state.filledCoreCount}/3 입력` : "현재 보유 미입력");
      }
      if (state.optionalCheckedCount > 0) {
        items.push(`선택 ${state.optionalCheckedCount}건 반영`);
      } else {
        items.push("선택 정보는 마지막 단계");
      }
      if (state.hasStructuredCore && state.filledCoreCount > 0) {
        items[2] = `현재 보유 ${state.filledCoreCount}/${state.requiredCoreCount} 입력`;
      }
      ui.permitWizardSummary.innerHTML = items
        .map((item, itemIndex) => `<span class="wizard-summary-chip${!selected && itemIndex === 1 ? " is-empty" : ""}">${esc(item)}</span>`)
        .join("");
    };
    const formatPermitCoreRequirement = (field) => {
      if (!field) return "";
      if (field.requiredValue === null || field.requiredValue === undefined) return field.label;
      if (field.key === "capital") return `${field.label} ${Core.formatEok(field.requiredValue)}`;
      if (field.key === "technicians") return `${field.label} ${Core.toInt(field.requiredValue).toLocaleString("ko-KR")}명`;
      if (field.key === "equipment") return `${field.label} ${Core.toInt(field.requiredValue).toLocaleString("ko-KR")}식`;
      return field.label;
    };
    const buildPermitCorePriorityCopy = () => {
      const selected = getSelectedIndustry();
      const corePlan = getPermitCoreFieldPlan();
      const orderedCore = corePlan.requiredFields.length ? corePlan.requiredFields : corePlan.fields;
      const missingCore = orderedCore.filter((field) => !field.filled);
      return {
        selected,
        orderedCore,
        missingCore,
        missingLabels: missingCore.map((field) => field.label),
        priorityText: orderedCore.map((field) => formatPermitCoreRequirement(field)).filter(Boolean).join(", "),
      };
    };
    const syncPermitWizardBlocker = () => {
      if (!ui.permitWizardBlocker) return;
      const state = getPermitWizardState();
      if (!state.searchTouched && !state.selectedIndustry) {
        ui.permitWizardBlocker.classList.remove("is-ready");
        ui.permitWizardBlocker.textContent = "다음 단계로 가려면 업종명 검색이나 빠른선택을 먼저 시작해 주세요.";
        return;
      }
      if (!state.selectedIndustry) {
        ui.permitWizardBlocker.classList.remove("is-ready");
        ui.permitWizardBlocker.textContent = "다음 단계로 가려면 업종을 확정해 주세요.";
        return;
      }
      if (state.filledCoreCount < state.requiredCoreCount) {
        const missing = [];
        const priorityCopy = buildPermitCorePriorityCopy();
        if (!String((ui.capitalInput && ui.capitalInput.value) || "").trim()) missing.push("자본금");
        if (!String((ui.technicianInput && ui.technicianInput.value) || "").trim()) missing.push("기술자");
        if (!String((ui.equipmentInput && ui.equipmentInput.value) || "").trim()) missing.push("장비");
        if (priorityCopy.missingLabels.length) {
          missing.splice(0, missing.length, ...priorityCopy.missingLabels);
        }
        ui.permitWizardBlocker.classList.remove("is-ready");
        ui.permitWizardBlocker.textContent = `다음 단계로 가려면 ${missing.join(", ")} 입력이 필요합니다.`;
        return;
      }
      ui.permitWizardBlocker.classList.add("is-ready");
      ui.permitWizardBlocker.textContent = "필수 입력은 끝났습니다. 마지막 선택 단계는 서류·현장 준비 상태를 보정할 때만 체크하면 됩니다.";
    };
    const syncHoldingsPriorityHint = () => {
      if (!ui.holdingsPriorityHint) return;
      const selected = getSelectedIndustry();
      if (!selected) {
        ui.holdingsPriorityHint.textContent = "업종을 먼저 확정하면 자본금, 기술자, 장비 중 무엇부터 확인해야 하는지 바로 안내합니다.";
        return;
      }
      const rule = getSelectedRule(selected);
      const profile = getRegistrationProfile(selected);
      const capitalText = rule
        ? Core.formatEok((rule.requirements && rule.requirements.capital_eok) || 0)
        : (profile.capital_required ? Core.formatEok(profile.capital_eok || 0) : "확인");
      const technicianText = rule
        ? `${Core.toInt((rule.requirements && rule.requirements.technicians) || 0)}명`
        : (profile.technical_personnel_required ? `${Core.toInt(profile.technicians_required || 0)}명` : "확인");
      const equipmentRequired = rule
        ? Core.toInt((rule.requirements && rule.requirements.equipment_count) || 0)
        : (profile.other_required ? Core.toInt(profile.equipment_count_required || 0) : 0);
      const equipmentText = equipmentRequired > 0 ? `장비 ${equipmentRequired}식` : "장비 확인";
      ui.holdingsPriorityHint.textContent = `${String(selected.service_name || "선택 업종")}은 자본금 ${capitalText}, 기술자 ${technicianText}, ${equipmentText}을 먼저 맞추면 바로 비교가 됩니다. 숫자 3칸만 채우고 마지막 선택 단계로 넘어가세요.`;
    };
    const formatPermitCoreRequirementSafe = (field) => {
      if (!field) return "";
      if (field.requiredValue === null || field.requiredValue === undefined) return field.label;
      if (field.key === "capital") return `${field.label} ${Core.formatEok(field.requiredValue)}`;
      if (field.key === "technicians") return `${field.label} ${Core.toInt(field.requiredValue).toLocaleString("ko-KR")}명`;
      if (field.key === "equipment") return `${field.label} ${Core.toInt(field.requiredValue).toLocaleString("ko-KR")}식`;
      return field.label;
    };
    const buildPermitCorePriorityCopySafe = () => {
      const selected = getSelectedIndustry();
      const corePlan = getPermitCoreFieldPlan();
      if (!corePlan.hasStructuredCore) {
        return {
          selected,
          orderedCore: [],
          missingCore: [],
          missingLabels: [],
          priorityText: "",
        };
      }
      const orderedCore = corePlan.requiredFields.length ? corePlan.requiredFields : corePlan.fields;
      const missingCore = orderedCore.filter((field) => !field.filled);
      return {
        selected,
        orderedCore,
        missingCore,
        missingLabels: missingCore.map((field) => field.label),
        priorityText: orderedCore.map((field) => formatPermitCoreRequirementSafe(field)).filter(Boolean).join(", "),
      };
    };
    const syncPermitWizardBlockerSafe = () => {
      if (!ui.permitWizardBlocker) return;
      const state = getPermitWizardState();
      if (!state.searchTouched && !state.selectedIndustry) {
        ui.permitWizardBlocker.classList.remove("is-ready");
        ui.permitWizardBlocker.textContent = "다음 단계로 가려면 업종명 검색이나 빠른 선택부터 시작해 주세요.";
        return;
      }
      if (!state.selectedIndustry) {
        ui.permitWizardBlocker.classList.remove("is-ready");
        ui.permitWizardBlocker.textContent = "다음 단계로 가려면 업종을 확정해 주세요.";
        return;
      }
      if (!state.hasStructuredCore) {
        ui.permitWizardBlocker.classList.add("is-ready");
        ui.permitWizardBlocker.textContent = "이 업종은 정량 기준이 아직 구조화되지 않아 보유 현황 입력 없이도 결과를 볼 수 있습니다. 마지막 선택 단계의 서류·현장 체크와 법령 근거를 먼저 확인해 주세요.";
        return;
      }
      if (state.filledCoreCount < state.requiredCoreCount) {
        const priorityCopy = buildPermitCorePriorityCopySafe();
        const missing = priorityCopy.missingLabels.length ? priorityCopy.missingLabels : state.missingCoreLabels;
        ui.permitWizardBlocker.classList.remove("is-ready");
        ui.permitWizardBlocker.textContent = missing.length
          ? `다음 단계로 가려면 ${missing.join(", ")} 입력이 필요합니다. ${priorityCopy.priorityText ? `${priorityCopy.priorityText} 순으로 보시면 됩니다.` : ""}`.trim()
          : "다음 단계로 가려면 현재 보유 현황 입력이 더 필요합니다.";
        return;
      }
      ui.permitWizardBlocker.classList.add("is-ready");
      ui.permitWizardBlocker.textContent = "필수 입력은 끝났습니다. 마지막 선택 단계에서 서류·현장 준비 상태를 필요한 만큼 체크하면 됩니다.";
    };
    const syncHoldingsPriorityHintSafe = () => {
      if (!ui.holdingsPriorityHint) return;
      const selected = getSelectedIndustry();
      if (!selected) {
        ui.holdingsPriorityHint.textContent = "업종을 먼저 확정하면 자본금, 기술자, 장비 중 무엇부터 확인해야 하는지 바로 안내합니다.";
        return;
      }
      const priorityCopy = buildPermitCorePriorityCopySafe();
      const industryName = String(selected.service_name || "선택 업종");
      if (!getPermitWizardState().hasStructuredCore) {
        ui.holdingsPriorityHint.textContent = `${industryName}은 자본금·기술자·장비의 정량 기준이 아직 구조화되지 않았습니다. 결과 배너의 법령 근거, 준비 서류, 다음 단계 안내를 먼저 확인해 주세요.`;
        return;
      }
      if (priorityCopy.missingCore.length) {
        ui.holdingsPriorityHint.textContent = `${industryName}은 ${priorityCopy.priorityText || "자본금, 기술자, 장비"} 순으로 보면 빠릅니다. 지금은 ${priorityCopy.missingLabels.join(", ")}부터 입력해 주세요.`;
        return;
      }
      ui.holdingsPriorityHint.textContent = `${industryName} 필수 코어 입력이 끝났습니다. 마지막 선택 단계에서 사무실, 보험, 서류 준비 상태만 체크하면 됩니다.`;
    };
    const syncPermitWizardNavCopies = () => {
      const coreGuide = getPermitCoreGuide();
      const step2Copy = document.querySelector("#permitWizardStep2 .wizard-nav-copy");
      if (step2Copy) {
        step2Copy.textContent = coreGuide.isStructured
          ? `업종이 확정되면 다음 단계에서 ${coreGuide.labelText} 중 필수 ${coreGuide.countText}만 입력하면 됩니다.`
          : "업종이 확정되면 다음 단계에서 법령 근거와 준비 서류 위주로 확인합니다.";
      }
      const step3Copy = document.querySelector("#permitWizardStep3 .wizard-nav-copy");
      if (step3Copy) {
        step3Copy.textContent = coreGuide.isStructured
          ? `${coreGuide.labelText} 중 필수 ${coreGuide.countText}부터 먼저 넣고, 마지막 단계에서 선택 항목을 추가 반영할 수 있습니다.`
          : "이 업종은 정량 기준이 아직 구조화되지 않아 현재 보유 현황 입력 없이도 결과를 확인할 수 있습니다.";
      }
    };
    const focusPermitWizardStep = (stepIndex) => {
      const meta = permitWizardStepsMeta[stepIndex];
      const node = meta ? document.getElementById(meta.id) : null;
      if (!node) return;
      const focusTarget = node.querySelector("input, select, button:not([disabled])");
      if (typeof node.scrollIntoView === "function") {
        node.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      if (focusTarget && typeof focusTarget.focus === "function") {
        try { focusTarget.focus({ preventScroll: true }); } catch (_error) { focusTarget.focus(); }
      }
    };
    const setPermitWizardStep = (nextIndex, options = {}) => {
      const maxIndex = Math.max(0, permitWizardStepsMeta.length - 1);
      permitWizardStepIndex = Math.max(0, Math.min(maxIndex, Number(nextIndex) || 0));
      syncPermitWizard();
      if (options && options.focus) {
        focusPermitWizardStep(permitWizardStepIndex);
      }
    };
    const syncPermitWizard = () => {
      if (!ui.permitInputWizard) return;
      const state = getPermitWizardState();
      const coreGuide = getPermitCoreGuide();
      if (!state.selectedIndustry && permitWizardStepIndex > 1) {
        permitWizardStepIndex = 1;
      }
      syncPermitWizardProgress();
      syncPermitWizardSummary();
      syncPermitWizardBlockerSafe();
      syncHoldingsPriorityHintSafe();
      syncPermitWizardNavCopies();
      const currentMeta = permitWizardStepsMeta[permitWizardStepIndex] || permitWizardStepsMeta[0];
      if (ui.permitWizardStepTitle) {
        ui.permitWizardStepTitle.textContent = `${currentMeta.shortLabel} · ${currentMeta.title}${currentMeta.optional ? " (선택)" : ""}`;
      }
      if (ui.permitWizardStepNote) {
        let dynamicNote = currentMeta.note;
        if (currentMeta.optional) {
          dynamicNote = getOptionalChecklistPlan(getSelectedIndustry(), getSelectedRule(getSelectedIndustry())).hint;
        } else if (currentMeta.id === "permitWizardStep2") {
          dynamicNote = !coreGuide.isStructured
            ? "정량 기준이 없는 업종은 법령 근거와 준비 서류 위주로 먼저 확인합니다."
            : state.selectedIndustry
            ? `업종이 확정되면 ${coreGuide.labelText} 중 필수 ${coreGuide.countText}만 확인하면 됩니다.`
            : "검색 결과를 확정합니다.";
        } else if (currentMeta.id === "permitWizardStep3") {
          dynamicNote = coreGuide.isStructured
            ? `${coreGuide.labelText} 중 필수 ${coreGuide.countText}부터 입력하면 결과가 바로 갱신됩니다.`
            : "이 업종은 핵심 등록요건이 아직 구조화되지 않아 보유 현황 입력 없이 결과를 확인할 수 있습니다.";
        }
        ui.permitWizardStepNote.textContent = dynamicNote;
      }
      permitWizardStepsMeta.forEach((step, stepIndex) => {
        const stepNode = document.getElementById(step.id);
        const isActive = stepIndex === permitWizardStepIndex;
        if (stepNode) {
          stepNode.classList.toggle("is-active", isActive);
          stepNode.hidden = !isActive;
        }
        document.querySelectorAll(`[data-permit-wizard-track="${stepIndex}"]`).forEach((chip) => {
          chip.classList.toggle("is-active", isActive);
          chip.classList.toggle("is-complete", !!state.completed[stepIndex]);
          chip.classList.toggle("is-optional", !!step.optional);
          chip.setAttribute("aria-current", isActive ? "step" : "false");
        });
        document.querySelectorAll(`[data-permit-wizard-prev="${stepIndex}"]`).forEach((button) => {
          button.disabled = stepIndex === 0;
        });
        document.querySelectorAll(`[data-permit-wizard-next="${stepIndex}"]`).forEach((button) => {
          let nextLabel = "다음";
          let disabled = false;
          if (stepIndex === 0) nextLabel = "업종 확정으로";
          else if (stepIndex === 1) {
            nextLabel = "보유 현황 입력";
            disabled = !state.selectedIndustry;
          } else if (stepIndex === 2) nextLabel = "선택 정보 보기";
          else nextLabel = "결과 보기";
          button.textContent = nextLabel;
          button.disabled = disabled;
        });
      });
    };

    const syncFocusModePills = () => {
      const mode = getFocusMode();
      const buttons = Array.from(document.querySelectorAll("[data-focus-mode]"));
      buttons.forEach((button) => {
        const active = String(button.getAttribute("data-focus-mode") || "") === mode;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
      });
    };

    const getSearchDrivenIndustryCandidates = () => {
      const searchTerm = getIndustrySearchTerm();
      const normalizedTerm = normalizeSearchKey(searchTerm);
      if (!searchTerm && !normalizedTerm) return [];
      const mode = getFocusMode();
      const buckets = [
        ...getFilteredIndustries(),
        ...getSyntheticCategoryRows(mode),
        ...getFocusQuickSelectRows(mode),
      ];
      const seen = new Set();
      const rows = [];
      buckets.forEach((row) => {
        const code = String(row.selector_code || row.service_code || "");
        if (!code || seen.has(code)) return;
        seen.add(code);
        const matchMeta = getSearchMatchMeta(row, searchTerm);
        const tokens = getRowPrimarySearchTokens(row);
        const normalizedTokens = tokens.map((token) => normalizeSearchKey(token)).filter(Boolean);
        rows.push({
          code,
          exact: !!matchMeta.exact || normalizedTokens.some((token) => token === normalizedTerm),
          prefix: !!matchMeta.prefix || normalizedTokens.some((token) => token.startsWith(normalizedTerm)),
          score: Number(matchMeta.score || 0),
          fieldType: String(matchMeta.fieldType || ""),
        });
      });
      rows.sort((left, right) => Number(right.score || 0) - Number(left.score || 0));
      return rows;
    };

    const tryAutoSelectIndustry = () => {
      const visibleCodes = [...ui.industrySelect.options]
        .map((option) => String(option.value || "").trim())
        .filter(Boolean);
      const currentValue = String(ui.industrySelect.value || "").trim();
      const searchTerm = String((ui.industrySearchInput && ui.industrySearchInput.value) || "").trim();
      const renderAutoSelection = () => {
        renderResult();
        syncExperienceLayer();
      };
      let targetCode = "";
      let reasonText = "";
      let reasonKind = "";
      let reasonMeta = null;
      const candidates = getSearchDrivenIndustryCandidates();
      const exactMatches = candidates.filter((row) => row.exact);
      const prefixMatches = candidates.filter((row) => row.prefix);
      const bestScore = candidates.length ? Number(candidates[0].score || 0) : 0;
      const bestScoreMatches = candidates.filter((row) => Number(row.score || 0) === bestScore);
      if (exactMatches.length === 1) {
        targetCode = exactMatches[0].code;
        reasonText = `검색어 '${searchTerm}'이 ${getSearchFieldTypeLabel(exactMatches[0].fieldType)}과 정확히 일치해 자동 선택했습니다.`;
        reasonKind = "정확 일치";
        reasonMeta = {
          query: searchTerm,
          fieldLabel: getSearchFieldTypeLabel(exactMatches[0].fieldType),
          detailText: "과 정확히 일치해 자동 선택했습니다.",
        };
      } else if (prefixMatches.length === 1) {
        targetCode = prefixMatches[0].code;
        reasonText = `검색어 '${searchTerm}'이 ${getSearchFieldTypeLabel(prefixMatches[0].fieldType)} 시작과 일치해 자동 선택했습니다.`;
        reasonKind = "접두 일치";
        reasonMeta = {
          query: searchTerm,
          fieldLabel: getSearchFieldTypeLabel(prefixMatches[0].fieldType),
          detailText: "시작과 일치해 자동 선택했습니다.",
        };
      } else if (bestScoreMatches.length === 1 && bestScore >= 520) {
        targetCode = bestScoreMatches[0].code;
        reasonText = `검색어 '${searchTerm}'과 ${getSearchFieldTypeLabel(bestScoreMatches[0].fieldType)} 관련도가 가장 높아 자동 선택했습니다.`;
        reasonKind = "관련도 최고";
        reasonMeta = {
          query: searchTerm,
          fieldLabel: getSearchFieldTypeLabel(bestScoreMatches[0].fieldType),
          detailText: "기준 관련도가 가장 높아 자동 선택했습니다.",
        };
      } else if (candidates.length === 1) {
        targetCode = candidates[0].code;
        reasonText = `검색어 '${searchTerm}' 기준 후보가 1건만 남아 자동 선택했습니다.`;
        reasonKind = "검색 1건";
        reasonMeta = {
          query: searchTerm,
          detailText: "기준 후보가 1건만 남아 자동 선택했습니다.",
        };
      } else if (visibleCodes.length === 1) {
        targetCode = visibleCodes[0];
        reasonText = searchTerm
          ? `검색어 '${searchTerm}' 기준 현재 필터에서 선택 가능한 업종이 1건이라 자동 선택했습니다.`
          : "현재 필터에서 선택 가능한 업종이 1건이라 자동 선택했습니다.";
        reasonKind = "선택 1건";
        reasonMeta = searchTerm
          ? {
              query: searchTerm,
              detailText: "기준 현재 필터에서 선택 가능한 업종이 1건이라 자동 선택했습니다.",
            }
          : null;
      }
      if (!targetCode) return false;
      if (currentValue === targetCode) {
        setPermitAutoSelectionReasonState(reasonText, reasonKind, reasonMeta);
        renderAutoSelection();
        return true;
      }
      if (applyIndustrySelection(targetCode)) {
        setPermitAutoSelectionReasonState(reasonText, reasonKind, reasonMeta);
        renderAutoSelection();
        return true;
      }
      if (visibleCodes.includes(targetCode)) {
        ui.industrySelect.value = targetCode;
        setPermitAutoSelectionReasonState(reasonText, reasonKind, reasonMeta);
        syncFocusQuickSelectSelection();
        renderAutoSelection();
        return true;
      }
      return false;
    };

    const applyReviewCasePreset = (preset) => {
      if (!preset || typeof preset !== "object") return false;
      const inputPayload = preset.input_payload && typeof preset.input_payload === "object"
        ? preset.input_payload
        : {};
      const selectorCode = String(inputPayload.industry_selector || preset.service_code || "").trim();
      if (selectorCode) {
        applyIndustrySelection(selectorCode);
      }
      if (ui.capitalInput && Object.prototype.hasOwnProperty.call(inputPayload, "capital_eok")) {
        ui.capitalInput.value = String(Core.toNum(inputPayload.capital_eok || 0));
      }
      if (ui.technicianInput && Object.prototype.hasOwnProperty.call(inputPayload, "technicians_count")) {
        ui.technicianInput.value = String(Core.toInt(inputPayload.technicians_count || 0));
      }
      if (ui.equipmentInput && !String(ui.equipmentInput.value || "").trim()) {
        ui.equipmentInput.value = "0";
      }
      const checklist = inputPayload.other_requirement_checklist && typeof inputPayload.other_requirement_checklist === "object"
        ? inputPayload.other_requirement_checklist
        : {};
      OPTIONAL_CHECKLIST_IDS.forEach((id) => {
        if (ui[id]) ui[id].checked = false;
      });
      Object.entries(checklist).forEach(([key, value]) => {
        const inputId = reviewChecklistPresetMap[String(key || "").trim()];
        if (inputId && ui[inputId]) ui[inputId].checked = !!value;
      });
      renderResult();
      syncExperienceLayer();
      return true;
    };

    const getRequirementPresetSnapshot = () => {
      const selected = getSelectedIndustry();
      if (!selected) {
        return {
          ready: false,
          industryName: "",
          values: { capital: null, technicians: null, equipment: null },
        };
      }
      const rule = getSelectedRule(selected);
      const req = rule && rule.requirements ? rule.requirements : {};
      const profile = getRegistrationProfile(selected);
      const capital = rule
        ? Core.toNum(req.capital_eok || 0)
        : (profile.capital_required ? Core.toNum(profile.capital_eok || 0) : null);
      const technicians = rule
        ? Core.toInt(req.technicians || 0)
        : (profile.technical_personnel_required ? Core.toInt(profile.technicians_required || 0) : null);
      const equipment = rule
        ? Core.toInt(req.equipment_count || 0)
        : (profile.other_required ? Core.toInt(profile.equipment_count_required || 0) : null);
      const values = {
        capital: Number.isFinite(Number(capital)) && Number(capital) > 0 ? Number(capital) : null,
        technicians: Number.isFinite(Number(technicians)) && Number(technicians) > 0 ? Number(technicians) : null,
        equipment: Number.isFinite(Number(equipment)) && Number(equipment) > 0 ? Number(equipment) : null,
      };
      return {
        ready: Object.values(values).some((value) => value !== null),
        industryName: String(selected.service_name || ""),
        values,
      };
    };

    const syncPresetActions = () => {
      const snapshot = getRequirementPresetSnapshot();
      const state = getPermitWizardState();
      const selected = getSelectedIndustry();
      const rule = getSelectedRule(selected);
      const visibleInputs = getVisibleHoldingsInputs(selected, rule);
      const hasInputs = visibleInputs
        .some((node) => !!String((node && node.value) || "").trim());
      if (ui.fillRequirementPreset) {
        ui.fillRequirementPreset.disabled = !snapshot.ready;
        ui.fillRequirementPreset.textContent = getFillPresetActionLabel(state);
      }
      if (ui.resetHoldingsPreset) ui.resetHoldingsPreset.disabled = !hasInputs;
      if (!ui.presetActionHint) return;
      if (!snapshot.industryName) {
        ui.presetActionHint.textContent = "업종을 선택하면 법정 최소 기준을 현재 보유 현황에 바로 채울 수 있습니다.";
        return;
      }
      if (snapshot.ready) {
        ui.presetActionHint.textContent = `${snapshot.industryName} 기준값을 한 번에 채워 빠르게 충족 여부를 시뮬레이션할 수 있습니다.`;
        return;
      }
      if (!state.hasStructuredCore) {
        ui.presetActionHint.textContent = `${snapshot.industryName}은 구조화된 정량 기준이 없어 기준값 채우기를 사용할 수 없습니다. 법령 근거와 준비 서류를 먼저 확인해 주세요.`;
        return;
      }
      ui.presetActionHint.textContent = `${snapshot.industryName}은 구조화된 최소 기준이 없어 현재 보유 현황을 직접 입력해 비교합니다.`;
    };

    const syncMobileQuickBar = () => {
      if (!ui.mobileQuickBar || !ui.mobileQuickTitle || !ui.mobileQuickMeta) return;
      const selected = getSelectedIndustry();
      const ready = !!selected;
      ui.mobileQuickBar.classList.toggle("is-ready", ready);
      document.body.classList.toggle("has-mobile-quick-bar", ready);
      if (!ready) {
        ui.mobileQuickTitle.textContent = "업종을 선택하면 핵심 결과를 아래에 요약합니다.";
        ui.mobileQuickMeta.textContent = "모바일에서는 결과 카드가 아래에 있어, 바로가기 버튼으로 빠르게 이동할 수 있습니다.";
        if (ui.mobileQuickPresetButton) {
          ui.mobileQuickPresetButton.textContent = "기준값 채우기";
          ui.mobileQuickPresetButton.disabled = true;
          ui.mobileQuickPresetButton.dataset.mode = "fill";
        }
        if (ui.mobileQuickResultButton) ui.mobileQuickResultButton.disabled = true;
        return;
      }
      const bannerTitle = String((ui.resultBannerTitle && ui.resultBannerTitle.textContent) || "").trim();
      const bannerMeta = String((ui.resultBannerMeta && ui.resultBannerMeta.textContent) || "").trim();
      const snapshot = getRequirementPresetSnapshot();
      const state = getPermitWizardState();
      const rule = getSelectedRule(selected);
      const visibleInputs = getVisibleHoldingsInputs(selected, rule);
      const hasInputs = visibleInputs
        .some((node) => !!String((node && node.value) || "").trim());
      const allCoreOk = getVisibleCoreStatusNodes(selected, rule)
        .every((node) => !!(node && node.classList.contains("ok")));
      ui.mobileQuickTitle.textContent = String(selected.service_name || "선택 업종");
      ui.mobileQuickMeta.textContent = allCoreOk
        ? (bannerTitle || bannerMeta || "결과 카드에서 부족 항목과 법령 근거를 확인하세요.")
        : (bannerMeta || bannerTitle || "결과 카드에서 부족 항목과 법령 근거를 확인하세요.");
      if (ui.mobileQuickPresetButton) {
        const useReset = allCoreOk && hasInputs;
        ui.mobileQuickPresetButton.dataset.mode = useReset ? "reset" : "fill";
        ui.mobileQuickPresetButton.textContent = useReset
          ? "입력 초기화"
          : (snapshot.ready ? getFillPresetActionLabel(state) : (state.hasStructuredCore ? getFillPresetActionLabel(state) : "법령 확인형"));
        ui.mobileQuickPresetButton.disabled = useReset ? !hasInputs : !snapshot.ready;
      }
      if (ui.mobileQuickResultButton) ui.mobileQuickResultButton.disabled = false;
    };

    const renderSmartIndustryProfile = () => {
      if (!ui.smartIndustryProfile) return;
      const selected = getSelectedIndustry();
      if (!selected) {
        ui.smartIndustryProfile.className = "smart-profile is-empty";
        ui.smartIndustryProfile.textContent = "업종을 선택하면 법정 최소 기준, 기준 출처, 보강이 필요한 준비 항목을 자동 요약합니다.";
        if (ui.capitalInput && !String(ui.capitalInput.value || "").trim()) ui.capitalInput.placeholder = "예: 1.5";
        if (ui.technicianInput && !String(ui.technicianInput.value || "").trim()) ui.technicianInput.placeholder = "예: 2";
        if (ui.equipmentInput && !String(ui.equipmentInput.value || "").trim()) ui.equipmentInput.placeholder = "예: 1";
        return;
      }

      const rule = getSelectedRule(selected);
      const req = rule && rule.requirements ? rule.requirements : {};
      const profile = getRegistrationProfile(selected);
      const capitalValue = rule
        ? Core.formatEok(req.capital_eok || 0)
        : (profile.capital_required ? Core.formatEok(profile.capital_eok || 0) : "법령 확인");
      const technicianValue = rule
        ? `${Core.toInt(req.technicians)}명`
        : (profile.technical_personnel_required ? `${Core.toInt(profile.technicians_required || 0)}명` : "법령 확인");
      const equipmentValue = rule
        ? `${Core.toInt(req.equipment_count)}대`
        : (profile.other_required ? "별도 장비요건 확인" : "장비 없음/확인");
      const depositValue = rule
        ? `${Core.toInt(req.deposit_days)}일`
        : "법령 확인";
      const sourceLabel = rule
        ? "법령 구조화"
        : (Number(selected.candidate_criteria_count || 0) > 0
          ? "법령 자동 추출"
          : ((Array.isArray(selected.auto_law_candidates) && selected.auto_law_candidates.length) ? "법령 후보" : "확인 필요"));
      const corePlan = getPermitCoreFieldPlan();
      const capitalSeedValue = rule
        ? Number(req.capital_eok || 0)
        : (profile.capital_required ? Number(profile.capital_eok || 0) : 0);
      const technicianSeedValue = rule
        ? Number(req.technicians || 0)
        : (profile.technical_personnel_required ? Number(profile.technicians_required || 0) : 0);
      const equipmentSeedValue = rule
        ? Number(req.equipment_count || 0)
        : (profile.other_required ? Number(profile.equipment_count_required || 0) : 0);
      const depositSeedValue = rule ? Number(req.deposit_days || 0) : 0;
      const chips = [];
      if (profile.focus_target) chips.push("핵심 업종");
      else if (profile.inferred_focus_candidate) chips.push("추론 후보");
      if (selected.is_rules_only) chips.push("법령 우선 검토");
      if (selected.is_platform_row) chips.push("실제 노출 업종");
      if (corePlan.hasStructuredCore && corePlan.requiredFieldCount > 0) {
        chips.push(`필수 ${corePlan.requiredFieldCount}개만 확인`);
      } else {
        chips.push("법령 확인형");
      }
      if (Array.isArray(selected.platform_selector_aliases) && selected.platform_selector_aliases.length) {
        chips.push(`검색어 ${selected.platform_selector_aliases.length}개 지원`);
      }
      const smartProfileItems = [
        {
          label: "기준 자본금",
          value: capitalValue,
          visible: capitalSeedValue > 0,
        },
        {
          label: "기준 기술자",
          value: technicianValue,
          visible: technicianSeedValue > 0,
        },
        {
          label: "장비/설비",
          value: equipmentValue,
          visible: equipmentSeedValue > 0,
        },
        {
          label: "예치/보완 일정",
          value: depositValue,
          visible: depositSeedValue > 0,
        },
      ].filter((item) => !!item.visible);
      if (!smartProfileItems.length) {
        smartProfileItems.push({
          label: "법령 기준",
          value: "결과 카드에서 확인",
          visible: true,
        });
      }

      ui.smartIndustryProfile.className = "smart-profile";
      ui.smartIndustryProfile.innerHTML = `
        <div class="smart-profile-head">
          <strong>${esc(selected.service_name || "선택 업종")}</strong>
          <span class="smart-profile-tag">${esc(sourceLabel)}</span>
        </div>
        <div class="smart-profile-grid">
          ${smartProfileItems.map((item) => `
          <div class="smart-profile-item">
            <span class="smart-profile-label">${esc(item.label)}</span>
            <span class="smart-profile-value">${esc(item.value)}</span>
          </div>`).join("")}
        </div>
        <div class="smart-chip-row">${chips.map((item) => `<span class="smart-chip">${esc(item)}</span>`).join("")}</div>`;

      if (ui.capitalInput && !String(ui.capitalInput.value || "").trim()) {
        ui.capitalInput.placeholder = capitalSeedValue > 0
          ? `예: ${String(Math.round(capitalSeedValue * 100) / 100)}`
          : "해당 시 입력";
      }
      if (ui.technicianInput && !String(ui.technicianInput.value || "").trim()) {
        ui.technicianInput.placeholder = technicianSeedValue > 0
          ? `예: ${String(Core.toInt(technicianSeedValue))}`
          : "해당 시 입력";
      }
      if (ui.equipmentInput && !String(ui.equipmentInput.value || "").trim()) {
        ui.equipmentInput.placeholder = equipmentSeedValue > 0
          ? `예: ${String(Core.toInt(equipmentSeedValue))}`
          : "해당 시 입력";
      }
    };

    const summarizeStatusNode = (node, label) => {
      const statusCard = node ? node.closest(".status-card") : null;
      if (statusCard && statusCard.hidden) return "";
      const text = String((node && node.textContent) || "").trim();
      if (!text || text === "-") return "";
      return `${label} ${text}`;
    };

    const getStructuredCoreVisibility = (selected = null, rule = null) => {
      if (!selected) {
        return {
          capital: true,
          technicians: true,
          equipment: true,
          deposit: true,
        };
      }
      const profile = getRegistrationProfile(selected);
      const req = rule && rule.requirements ? rule.requirements : {};
      if (!rule) {
        return {
          capital: !!profile.capital_required,
          technicians: !!profile.technical_personnel_required,
          equipment: !!profile.other_required,
          deposit: Number(profile.deposit_days_required || 0) > 0,
        };
      }
      return {
        capital: Number(req.capital_eok || 0) > 0,
        technicians: Number(req.technicians || 0) > 0,
        equipment: Number(req.equipment_count || 0) > 0,
        deposit: Number(req.deposit_days || 0) > 0,
      };
    };

    const getVisibleCoreStatusNodes = (selected = null, rule = null) => {
      const visibility = getStructuredCoreVisibility(selected, rule);
      return [
        visibility.capital ? ui.capitalGapStatus : null,
        visibility.technicians ? ui.technicianGapStatus : null,
        visibility.equipment ? ui.equipmentGapStatus : null,
      ].filter(Boolean);
    };

    const setStatusCardVisibility = (node, visible) => {
      const statusCard = node ? node.closest(".status-card") : null;
      if (!statusCard) return;
      statusCard.hidden = !visible;
    };

    const syncCoreStatusCardVisibility = (selected = null, rule = null) => {
      const visibility = getStructuredCoreVisibility(selected, rule);
      setStatusCardVisibility(ui.capitalGapStatus, visibility.capital);
      setStatusCardVisibility(ui.technicianGapStatus, visibility.technicians);
      setStatusCardVisibility(ui.equipmentGapStatus, visibility.equipment);
    };

    const buildRequirementsMetaSummary = (selected = null, rule = null) => {
      if (!selected || !rule) return "-";
      const req = rule && rule.requirements ? rule.requirements : {};
      const visibility = getStructuredCoreVisibility(selected, rule);
      const parts = [];
      if (visibility.technicians) parts.push(`기술인력 ${Core.toInt(req.technicians || 0)}명`);
      if (visibility.equipment) parts.push(`장비 ${Core.toInt(req.equipment_count || 0)}식`);
      if (visibility.deposit) parts.push(`예치 ${Core.toInt(req.deposit_days || 0)}일`);
      return parts.length ? parts.join(" / ") : "결과 카드에서 확인";
    };

    const getVisibleHoldingsInputs = (selected = null, rule = null) => {
      const visibility = getStructuredCoreVisibility(selected, rule);
      return [
        visibility.capital ? ui.capitalInput : null,
        visibility.technicians ? ui.technicianInput : null,
        visibility.equipment ? ui.equipmentInput : null,
      ].filter(Boolean);
    };

    const getFillPresetActionLabel = (state = null) => {
      const currentState = state || getPermitWizardState();
      if (!currentState.hasStructuredCore || Number(currentState.requiredCoreCount || 0) <= 0) {
        return "기준값 채우기";
      }
      return `필수 ${currentState.requiredCoreCount}개 채우기`;
    };

    const syncHoldingsInputVisibility = (selected = null, rule = null) => {
      const visibility = getStructuredCoreVisibility(selected, rule);
      [
        { input: ui.capitalInput, visible: visibility.capital },
        { input: ui.technicianInput, visible: visibility.technicians },
        { input: ui.equipmentInput, visible: visibility.equipment },
      ].forEach(({ input, visible }) => {
        if (!input) return;
        const field = input.closest(".field");
        if (field) field.hidden = !visible;
        input.disabled = !visible;
        if (!visible) {
          input.value = "";
          input.placeholder = "해당 없음";
        }
      });
    };

    const OPTIONAL_CHECKLIST_IDS = [
      "officeSecuredInput",
      "facilitySecuredInput",
      "qualificationSecuredInput",
      "insuranceSecuredInput",
      "safetySecuredInput",
      "documentReadyInput",
    ];

    const OPTIONAL_CHECKLIST_LABELS = {
      officeSecuredInput: "사무실",
      facilitySecuredInput: "시설·장비",
      qualificationSecuredInput: "자격·경력",
      insuranceSecuredInput: "보험·보증",
      safetySecuredInput: "안전·환경",
      documentReadyInput: "제출서류",
    };

    const getOptionalChecklistPlan = (selected = null, rule = null) => {
      const pushUnique = (target, value) => {
        if (!value || target.includes(value)) return;
        target.push(value);
      };
      const orderedIds = [];
      if (!selected) {
        OPTIONAL_CHECKLIST_IDS.forEach((id) => pushUnique(orderedIds, id));
        return {
          orderedIds,
          primaryIds: orderedIds.slice(0, 3),
          hint: "업종을 고르면 마지막 단계에서 먼저 볼 선택 항목을 위로 정렬해 드립니다.",
        };
      }

      const industryName = String(selected.service_name || "선택 업종");
      const visibility = getStructuredCoreVisibility(selected, rule);
      const normalizedName = industryName.replace(/\\s+/g, "");
      const isSafetyHeavy = /(전기|가스|소방|위험물|시설시공)/.test(normalizedName);
      const isSecurityHeavy = /(경비|보안|호송)/.test(normalizedName);
      const hasStructuredCore = getPermitWizardState().hasStructuredCore;

      if (!hasStructuredCore) {
        [
          "documentReadyInput",
          "qualificationSecuredInput",
          "officeSecuredInput",
        ].forEach((id) => pushUnique(orderedIds, id));
      } else {
        if (isSafetyHeavy) pushUnique(orderedIds, "safetySecuredInput");
        if (isSecurityHeavy) pushUnique(orderedIds, "insuranceSecuredInput");
        if (visibility.equipment) pushUnique(orderedIds, "facilitySecuredInput");
        if (visibility.technicians) pushUnique(orderedIds, "qualificationSecuredInput");
        if (visibility.capital) pushUnique(orderedIds, "officeSecuredInput");
        pushUnique(orderedIds, "documentReadyInput");
        if (!isSecurityHeavy) pushUnique(orderedIds, "insuranceSecuredInput");
        if (!isSafetyHeavy) pushUnique(orderedIds, "safetySecuredInput");
      }

      OPTIONAL_CHECKLIST_IDS.forEach((id) => pushUnique(orderedIds, id));
      const primaryIds = orderedIds.slice(0, 3);
      const primaryLabels = primaryIds
        .map((id) => OPTIONAL_CHECKLIST_LABELS[id] || "")
        .filter(Boolean);
      const hint = !hasStructuredCore
        ? `${industryName}은 마지막 단계에서 ${primaryLabels.join(", ")}부터 확인하면 서류 전달 준비가 빠릅니다.`
        : `${industryName}은 마지막 단계에서 ${primaryLabels.join(", ")}부터 체크하면 전달 준비가 빠릅니다.`;
      return {
        orderedIds,
        primaryIds,
        hint,
      };
    };

    const syncOptionalChecklistLayout = () => {
      const optionalGrid = ui.advancedInputs;
      if (!optionalGrid) return;
      const selected = getSelectedIndustry();
      const rule = getSelectedRule(selected);
      const plan = getOptionalChecklistPlan(selected, rule);
      const planKey = selected
        ? `${String(selected.service_code || selected.selected_display_service_code || selected.service_name || "")}:${plan.orderedIds.join(",")}`
        : `blank:${plan.orderedIds.join(",")}`;
      if (planKey !== optionalChecklistPlanKey) {
        optionalChecklistPlanKey = planKey;
        optionalChecklistExpanded = false;
      }
      const labelsById = new Map(
        Array.from(optionalGrid.querySelectorAll(".check-item"))
          .map((label) => {
            const input = label.querySelector("input");
            return [String((input && input.id) || label.dataset.checklistId || ""), label];
          })
          .filter(([id]) => !!id)
      );
      plan.orderedIds.forEach((id, index) => {
        const label = labelsById.get(id);
        if (!label) return;
        label.dataset.priorityRank = String(index + 1);
        const priorityIndex = plan.primaryIds.indexOf(id);
        const isPriority = priorityIndex >= 0;
        label.classList.toggle("is-priority", isPriority);
        label.classList.toggle("is-secondary", !isPriority);
        if (isPriority) {
          label.dataset.priorityBadge = `우선 ${priorityIndex + 1}`;
        } else {
          label.removeAttribute("data-priority-badge");
        }
        optionalGrid.appendChild(label);
      });
      const secondaryCount = Math.max(0, plan.orderedIds.length - plan.primaryIds.length);
      optionalGrid.classList.toggle("is-collapsed", secondaryCount > 0 && !optionalChecklistExpanded);
      if (ui.optionalPriorityHint) {
        ui.optionalPriorityHint.textContent = plan.hint;
      }
      if (ui.optionalChecklistToggle) {
        ui.optionalChecklistToggle.hidden = secondaryCount <= 0;
        ui.optionalChecklistToggle.textContent = optionalChecklistExpanded
          ? "우선 항목만 보기"
          : `추가 준비 항목 ${secondaryCount}개 더 보기`;
        ui.optionalChecklistToggle.setAttribute("aria-expanded", optionalChecklistExpanded ? "true" : "false");
      }
    };
    const clearOptionalChecklistSelections = () => {
      optionalChecklistExpanded = false;
      OPTIONAL_CHECKLIST_IDS.forEach((id) => {
        if (ui[id]) ui[id].checked = false;
      });
    };
    const buildPermitOptionalReadiness = (selected, rule) => {
      const optionalPlan = getOptionalChecklistPlan(selected, rule);
      const labels = optionalPlan.orderedIds
        .filter((id) => !!(ui[id] && ui[id].checked))
        .map((id) => OPTIONAL_CHECKLIST_LABELS[id] || "")
        .filter(Boolean);
      return {
        count: labels.length,
        labels,
        summary: labels.length > 0
          ? `선택 준비 ${labels.slice(0, 2).join(", ")}${labels.length > 2 ? ` 외 ${labels.length - 2}건` : ""}`
          : "",
      };
    };
    const getPermitDeliveryGuidance = (selected, rule, optionalReadiness, allCoreOk, fallbackText = "", hasWarn = false) => {
      if (!selected) {
        return {
          actionNote: "업종을 선택하면 상담과 후속 안내 동선이 열립니다.",
          briefMeta: "업종을 선택하면 대표가 바로 전달할 한 줄 요약을 자동 생성합니다.",
          copyLabel: "한 줄 브리프 복사",
        };
      }
      if (!rule && fallbackText) {
        return {
          actionNote: "법령 근거와 준비 서류 중심으로 먼저 공유하면 상담 범위를 빠르게 좁힐 수 있습니다.",
          briefMeta: "법령 확인형 요약입니다. 담당자에게 바로 전달할 수 있습니다.",
          copyLabel: "법령 요약 복사",
        };
      }
      if (allCoreOk) {
        if (optionalReadiness.count > 0) {
          return {
            actionNote: "핵심 기준과 선택 준비 체크까지 반영됐습니다. 지금 상태로 상담 전달을 시작해도 됩니다.",
            briefMeta: "전달 준비까지 반영된 브리프입니다. 카카오톡, 문자, 내부 메신저에 바로 전달할 수 있습니다.",
            copyLabel: "전달 브리프 복사",
          };
        }
        return {
          actionNote: "핵심 기준은 충족 상태입니다. 선택 준비를 더 체크하면 전달 문구를 더 구체화할 수 있습니다.",
          briefMeta: "충족 상태 요약입니다. 선택 준비를 더 체크하면 전달 문구가 더 구체화됩니다.",
          copyLabel: "충족 브리프 복사",
        };
      }
      if (hasWarn) {
        if (optionalReadiness.count > 0) {
          return {
            actionNote: "보완 항목과 선택 준비 상태를 함께 전달하면 상담 우선순위를 더 빨리 잡을 수 있습니다.",
            briefMeta: "보완 포인트와 선택 준비 체크를 함께 정리한 브리프입니다.",
            copyLabel: "보완 브리프 복사",
          };
        }
        return {
          actionNote: "부족한 항목부터 전달해 보완 상담을 시작하는 편이 빠릅니다.",
          briefMeta: "부족 항목 중심 브리프입니다. 보완 상담용으로 바로 전달할 수 있습니다.",
          copyLabel: "보완 브리프 복사",
        };
      }
      return {
        actionNote: "법령 및 준비 서류 확인 포인트를 먼저 공유하면 후속 상담이 빨라집니다.",
        briefMeta: "확인 필요 항목 중심 요약입니다. 전달 전 검토 메모로도 사용할 수 있습니다.",
        copyLabel: "검토 브리프 복사",
      };
    };

    const buildPermitResultBrief = () => {
      const selected = getSelectedIndustry();
      if (!selected) return "";
      const rule = getSelectedRule(selected);
      const bannerTitle = String((ui.resultBannerTitle && ui.resultBannerTitle.textContent) || "").trim();
      const bannerMeta = String((ui.resultBannerMeta && ui.resultBannerMeta.textContent) || "").trim();
      const capitalSummary = summarizeStatusNode(ui.capitalGapStatus, "자본금");
      const technicianSummary = summarizeStatusNode(ui.technicianGapStatus, "기술자");
      const equipmentSummary = summarizeStatusNode(ui.equipmentGapStatus, "장비");
      const coreSummary = [capitalSummary, technicianSummary, equipmentSummary].filter(Boolean).join(", ");
      const optionalReadiness = buildPermitOptionalReadiness(selected, rule);
      return [
        "인허가 사전검토",
        String(selected.service_name || "업종").trim(),
        bannerTitle || "상태 확인",
        coreSummary || bannerMeta || "핵심 기준 확인 중",
        optionalReadiness.summary,
      ].filter(Boolean).join(" | ");
    };

    const syncPermitResultBrief = () => {
      const brief = buildPermitResultBrief();
      const selected = getSelectedIndustry();
      const rule = getSelectedRule(selected);
      const fallbackText = String((ui.fallbackGuide && ui.fallbackGuide.textContent) || "").trim();
      const optionalReadiness = buildPermitOptionalReadiness(selected, rule);
      const visibleCoreNodes = getVisibleCoreStatusNodes(selected, rule);
      const allCoreOk = !!selected && visibleCoreNodes.length > 0
        && visibleCoreNodes.every((node) => !!(node && node.classList.contains("ok")));
      const hasWarn = [ui.capitalGapStatus, ui.technicianGapStatus, ui.equipmentGapStatus]
        .some((node) => !!(node && node.classList.contains("warn")));
      const guidance = getPermitDeliveryGuidance(selected, rule, optionalReadiness, allCoreOk, fallbackText, hasWarn);
      if (ui.resultBrief) {
        ui.resultBrief.value = brief;
      }
      if (ui.resultBriefMeta) {
        ui.resultBriefMeta.textContent = brief
          ? "복사해서 카카오톡, 문자, 내부 메신저로 바로 전달할 수 있습니다."
          : "업종을 선택하면 대표가 바로 전달할 한 줄 요약을 자동 생성합니다.";
        ui.resultBriefMeta.textContent = guidance.briefMeta;
      }
      if (ui.btnCopyResultBrief) {
        ui.btnCopyResultBrief.disabled = !brief;
        ui.btnCopyResultBrief.textContent = guidance.copyLabel;
      }
    };

    const syncResultChrome = () => {
      if (!ui.resultBanner || !ui.resultBannerTitle || !ui.resultBannerMeta) return;
      const selected = getSelectedIndustry();
      const ready = !!selected;
      if (ui.resultActionWrap) ui.resultActionWrap.classList.toggle("ready", ready);
      if (ui.resultActionNote) {
        ui.resultActionNote.textContent = ready
          ? "법령 근거와 보완 포인트를 확인한 뒤 바로 상담으로 이어갈 수 있습니다."
          : "업종을 선택하면 상담과 후속 안내 동선이 열립니다.";
      }

      if (!selected) {
        ui.resultBanner.className = "result-banner info";
        ui.resultBannerTitle.textContent = "업종을 선택하면 자동 진단이 시작됩니다.";
        ui.resultBannerMeta.textContent = "필수 등록요건과 법령 근거, 준비 상태를 한 번에 비교합니다.";
        return;
      }

      const rule = getSelectedRule(selected);
      const fallbackText = String((ui.fallbackGuide && ui.fallbackGuide.textContent) || "").trim();
      const coverageText = String((ui.coverageGuide && ui.coverageGuide.textContent) || "").trim();
      const statusSummaries = [
        summarizeStatusNode(ui.capitalGapStatus, "자본금"),
        summarizeStatusNode(ui.technicianGapStatus, "기술자"),
        summarizeStatusNode(ui.equipmentGapStatus, "장비"),
      ].filter(Boolean);
      const optionalReadiness = buildPermitOptionalReadiness(selected, rule);
      const visibleCoreNodes = getVisibleCoreStatusNodes(selected, rule);
      const allCoreOk = visibleCoreNodes.length > 0
        && visibleCoreNodes.every((node) => !!(node && node.classList.contains("ok")));
      const hasWarn = [ui.capitalGapStatus, ui.technicianGapStatus, ui.equipmentGapStatus]
        .some((node) => !!(node && node.classList.contains("warn")));
      const guidance = getPermitDeliveryGuidance(selected, rule, optionalReadiness, allCoreOk, fallbackText, hasWarn);
      if (ui.resultActionNote) {
        ui.resultActionNote.textContent = guidance.actionNote;
      }

      if (!rule && fallbackText) {
        ui.resultBanner.className = "result-banner info";
        ui.resultBannerTitle.textContent = "법령 근거 확인이 우선입니다.";
        ui.resultBannerMeta.textContent = fallbackText;
        return;
      }

      if (allCoreOk && !fallbackText) {
        ui.resultBanner.className = "result-banner ok";
        ui.resultBannerTitle.textContent = optionalReadiness.count > 0
          ? "등록기준 충족 가능성이 높고 전달 준비도 진행 중입니다."
          : "등록기준 충족 가능성이 높습니다.";
        ui.resultBannerMeta.textContent = optionalReadiness.summary
          ? `${selected.service_name || "선택 업종"} 기준으로 핵심 등록요건이 충족됩니다. ${optionalReadiness.summary} 확인까지 반영되어 바로 상담 전달 준비를 이어갈 수 있습니다.`
          : `${selected.service_name || "선택 업종"} 기준으로 핵심 등록요건이 충족됩니다. 추가 서류와 법령 해석만 확인하면 됩니다.`;
        return;
      }

      if (hasWarn) {
        ui.resultBanner.className = "result-banner warn";
        ui.resultBannerTitle.textContent = "보완이 필요한 항목이 있습니다.";
        ui.resultBannerMeta.textContent = optionalReadiness.summary
          ? `${statusSummaries.join(" / ") || "핵심 등록요건 중 부족한 항목을 먼저 보완해야 합니다."} / ${optionalReadiness.summary}`
          : (statusSummaries.join(" / ") || "핵심 등록요건 중 부족한 항목을 먼저 보완해야 합니다.");
        return;
      }

      ui.resultBanner.className = "result-banner info";
      ui.resultBannerTitle.textContent = "법령 및 서류 확인이 더 필요합니다.";
      ui.resultBannerMeta.textContent = fallbackText || coverageText || "업종별 추가 요건과 제출자료를 함께 검토하세요.";
    };

    const syncExperienceLayer = () => {
      syncFocusModePills();
      syncFocusQuickSelectSelection();
      syncIndustryAutoReason();
      renderSmartIndustryProfile();
      const selected = getSelectedIndustry();
      const rule = getSelectedRule(selected);
      syncHoldingsInputVisibility(selected, rule);
      syncOptionalChecklistLayout();
      syncPresetActions();
      syncResultChrome();
      syncPermitResultBrief();
      syncMobileQuickBar();
      syncPermitWizard();
    };

    const clearResult = () => {
      ui.requiredCapital.textContent = "-";
      ui.requirementsMeta.textContent = "-";
      ui.capitalGapStatus.textContent = "-";
      ui.capitalGapStatus.className = "status";
      ui.technicianGapStatus.textContent = "-";
      ui.technicianGapStatus.className = "status";
      ui.equipmentGapStatus.textContent = "-";
      ui.equipmentGapStatus.className = "status";
      ui.diagnosisDate.textContent = "-";
      ui.crossValidation.textContent = "";
      ui.fallbackGuide.style.display = "none";
      ui.fallbackGuide.textContent = "";
      ui.legalBasis.style.display = "none";
      ui.legalBasis.innerHTML = "";
      ui.focusProfileBox.style.display = "none";
      ui.focusProfileBox.innerHTML = "";
      ui.qualityFlagsBox.style.display = "none";
      ui.qualityFlagsBox.innerHTML = "";
      ui.proofClaimBox.style.display = "none";
      ui.proofClaimBox.innerHTML = "";
      ui.reviewPresetBox.style.display = "none";
      ui.reviewPresetBox.innerHTML = "";
      ui.caseStoryBox.style.display = "none";
      ui.caseStoryBox.innerHTML = "";
      ui.operatorDemoBox.style.display = "none";
      ui.operatorDemoBox.innerHTML = "";
      ui.runtimeReasoningCardBox.style.display = "none";
      ui.runtimeReasoningCardBox.innerHTML = "";
      ui.coverageGuide.style.display = "none";
      ui.coverageGuide.textContent = "";
      ui.typedCriteriaBox.style.display = "none";
      ui.typedCriteriaBox.innerHTML = "";
      ui.evidenceChecklistBox.style.display = "none";
      ui.evidenceChecklistBox.innerHTML = "";
      ui.nextActionsBox.style.display = "none";
      ui.nextActionsBox.innerHTML = "";
      syncCoreStatusCardVisibility(null, null);
      syncExperienceLayer();
    };

    const renderGapStatus = (node, gap, formatter, okText, needText) => {
      if (gap.isSatisfied) {
        node.textContent = okText;
        node.className = "status ok";
      } else {
        node.textContent = `${formatter(gap.gap)} ${needText}`;
        node.className = "status warn";
      }
    };

    const renderBasisRows = (rows, title = "법령 근거") => {
      if (!rows.length) {
        ui.legalBasis.style.display = "none";
        ui.legalBasis.innerHTML = "";
        return;
      }
      const parts = rows.map((item) => {
        const lawTitle = esc(item.law_title || "");
        const article = esc(item.article || "");
        const url = esc(item.url || "");
        if (!url) {
          return `${lawTitle} ${article}`.trim();
        }
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${lawTitle} ${article}</a>`;
      });
      ui.legalBasis.innerHTML = `<strong>${esc(title)}</strong><br>${parts.join("<br>")}`;
      ui.legalBasis.style.display = "block";
    };

    const renderRuleBasis = (rule) => {
      const rows = Array.isArray(rule.legal_basis) ? rule.legal_basis : [];
      renderBasisRows(rows, "법령 근거");
    };

    const renderFocusProfile = (industry) => {
      const profile = getRegistrationProfile(industry);
      if (!profile || !Object.keys(profile).length) {
        ui.focusProfileBox.style.display = "none";
        ui.focusProfileBox.innerHTML = "";
        return;
      }
      const badges = [];
      if (profile.focus_target_with_other) badges.push("자본금+기술인력+기타 필수");
      else if (profile.focus_target) badges.push("자본금+기술인력 필수");
      else if (profile.inferred_focus_candidate) badges.push("핵심 후보(재검증)");
      else badges.push("부분 구조화");
      badges.push(industry && industry.is_rules_only ? "등록기준 업종군" : "실업종");
      badges.push(profile.profile_source === "structured_requirements" ? "구조화 기준" : "본문 추론");

      const details = [];
      if (profile.capital_required) details.push(`자본금 ${Core.formatEok(profile.capital_eok || 0)}`);
      if (profile.technical_personnel_required) {
        details.push(`기술인력 ${Core.toInt(profile.technicians_required || 0)}명`);
      }
      if (profile.other_required) {
        const labels = Array.isArray(profile.other_components)
          ? profile.other_components.map((item) => otherRequirementLabels[item] || item)
          : [];
        if (labels.length) details.push(`기타 ${labels.join(", ")}`);
      }
      ui.focusProfileBox.innerHTML = `<strong>핵심 요건 프로필</strong><br>${badges
        .map((item) => `[${esc(item)}]`)
        .join(" ")}${details.length ? `<br>${details.map((item) => `- ${esc(item)}`).join("<br>")}` : ""}`;
      ui.focusProfileBox.style.display = "block";
    };

    const renderQualityFlags = (industry) => {
      const flags = Array.isArray(industry && industry.quality_flags) ? industry.quality_flags : [];
      if (!flags.length) {
        ui.qualityFlagsBox.style.display = "none";
        ui.qualityFlagsBox.innerHTML = "";
        return;
      }
      ui.qualityFlagsBox.innerHTML = `<strong>품질 경고</strong><br>${flags
        .map((item) => `- ${esc(qualityFlagLabels[item] || item)}`)
        .join("<br>")}`;
      ui.qualityFlagsBox.style.display = "block";
    };

    const renderProofClaim = (industry) => {
      const proof = industry && typeof industry.raw_source_proof === "object" ? industry.raw_source_proof : null;
      const claim = industry && typeof industry.claim_packet_summary === "object" ? industry.claim_packet_summary : null;
      if (!proof && !claim) {
        ui.proofClaimBox.style.display = "none";
        ui.proofClaimBox.innerHTML = "";
        return;
      }

      const lines = ["<strong>법령군 증빙</strong>"];
      if (claim) {
        const badges = [];
        if (claim.claim_id) badges.push(`claim ${esc(claim.claim_id)}`);
        if (claim.family_key) badges.push(esc(claim.family_key));
        if (claim.proof_coverage_ratio) badges.push(`proof ${esc(claim.proof_coverage_ratio)}`);
        if (badges.length) {
          lines.push(badges.map((item) => `[${item}]`).join(" "));
        }
        if (claim.claim_statement) {
          lines.push(esc(claim.claim_statement));
        }
        const requiredDomains = Array.isArray(claim.required_input_domains) ? claim.required_input_domains : [];
        const optionalDomains = Array.isArray(claim.optional_input_domains) ? claim.optional_input_domains : [];
        if (requiredDomains.length) {
          lines.push(`- 필수 입력: ${requiredDomains.map((item) => esc(proofDomainLabels[item] || item)).join(", ")}`);
        }
        if (optionalDomains.length) {
          lines.push(`- 기타 입력: ${optionalDomains.map((item) => esc(proofDomainLabels[item] || item)).join(", ")}`);
        }
        if (Number(claim.checksum_sample_total || 0) > 0) {
          lines.push(`- checksum sample ${Number(claim.checksum_sample_total || 0)}건`);
        }
        const checksumSamples = Array.isArray(claim.checksum_samples) ? claim.checksum_samples.slice(0, 3) : [];
        if (checksumSamples.length) {
          lines.push(`- sample: ${checksumSamples.map((item) => esc(item)).join(", ")}`);
        }
      }
      const snapshotNote = (proof && proof.official_snapshot_note)
        || (claim && claim.official_snapshot_note)
        || "";
      if (snapshotNote) {
        lines.push(`- snapshot: ${esc(snapshotNote)}`);
      }
      const proofUrls = proof && Array.isArray(proof.source_urls) && proof.source_urls.length
        ? proof.source_urls.slice(0, 1)
        : (claim && Array.isArray(claim.source_url_samples) ? claim.source_url_samples.slice(0, 1) : []);
      if (proofUrls.length) {
        const url = esc(proofUrls[0]);
        lines.push(`- source: <a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`);
      }
      ui.proofClaimBox.innerHTML = lines.join("<br>");
      ui.proofClaimBox.style.display = "block";
    };

    const renderReviewCasePresets = (industry) => {
      if (!ui.reviewPresetBox) return;
      const presets = getReviewCasePresets(industry);
      if (!presets.length) {
        ui.reviewPresetBox.style.display = "none";
        ui.reviewPresetBox.innerHTML = "";
        return;
      }
      const cards = presets.map((preset) => {
        const expected = preset.expected_outcome && typeof preset.expected_outcome === "object"
          ? preset.expected_outcome
          : {};
        const badges = [];
        if (expected.overall_status) badges.push(`예상 ${esc(expected.overall_status)}`);
        if (expected.review_reason) badges.push(esc(getReviewReasonLabel(expected.review_reason)));
        if (expected.manual_review_expected) badges.push("수동 검토");
        if (expected.proof_coverage_ratio) badges.push(`proof ${esc(expected.proof_coverage_ratio)}`);
        const serviceMeta = preset.service_name && industry && preset.service_name !== industry.service_name
          ? `<div class="assist">대표 업종: ${esc(preset.service_name)}</div>`
          : "";
        return ''
          + '<div class="case-surface-card">'
          + `<div class="case-surface-head"><strong>${esc(preset.preset_label || preset.case_kind || "검토 프리셋")}</strong>`
          + `<button type="button" class="preset-action" data-review-preset-id="${esc(preset.preset_id || "")}">이 시나리오 채우기</button></div>`
          + (badges.length ? `<div class="assist">${badges.map((item) => `[${item}]`).join(" ")}</div>` : "")
          + serviceMeta
          + (preset.operator_note ? `<div class="assist">${esc(preset.operator_note)}</div>` : "")
          + '</div>';
      });
      ui.reviewPresetBox.innerHTML = `<strong>검토 시나리오 프리셋</strong><br>${cards.join("")}`;
      ui.reviewPresetBox.style.display = "block";
      ui.reviewPresetBox.querySelectorAll("[data-review-preset-id]").forEach((button) => {
        button.addEventListener("click", () => {
          const presetId = String(button.getAttribute("data-review-preset-id") || "");
          const target = presets.find((item) => String(item.preset_id || "") === presetId);
          if (target) applyReviewCasePreset(target);
        });
      });
    };

    const renderCaseStorySurface = (industry) => {
      if (!ui.caseStoryBox) return;
      const story = getCaseStorySurface(industry);
      if (!story) {
        ui.caseStoryBox.style.display = "none";
        ui.caseStoryBox.innerHTML = "";
        return;
      }
      const reasons = Array.isArray(story.review_reasons)
        ? story.review_reasons.map((item) => getReviewReasonLabel(item)).filter(Boolean)
        : [];
      const storyPoints = Array.isArray(story.operator_story_points)
        ? story.operator_story_points.filter(Boolean)
        : [];
      const representativeCases = Array.isArray(story.representative_cases)
        ? story.representative_cases
        : [];
      const meta = [];
      if (story.claim_id) meta.push(`claim ${esc(story.claim_id)}`);
      if (Number(story.preset_total || 0) > 0) meta.push(`preset ${Number(story.preset_total || 0)}건`);
      if (Number(story.manual_review_preset_total || 0) > 0) meta.push(`수동 검토 ${Number(story.manual_review_preset_total || 0)}건`);
      if (reasons.length) meta.push(`사유 ${reasons.join(", ")}`);
      const caseLines = representativeCases.slice(0, 3).map((item) => {
        const parts = [esc(item.service_name || item.service_code || "")];
        if (item.case_kind) parts.push(esc(item.case_kind));
        if (item.review_reason) parts.push(esc(getReviewReasonLabel(item.review_reason)));
        if (item.manual_review_expected) parts.push("수동 검토");
        return `- ${parts.filter(Boolean).join(" / ")}`;
      });
      ui.caseStoryBox.innerHTML = ''
        + '<strong>케이스 스토리 요약</strong><br>'
        + (meta.length ? `${meta.map((item) => `[${item}]`).join(" ")}<br>` : "")
        + (storyPoints.length ? `${storyPoints.map((item) => `- ${esc(item)}`).join("<br>")}<br>` : "")
        + (caseLines.length ? `<span class="assist">대표 케이스</span><br>${caseLines.join("<br>")}` : "");
      ui.caseStoryBox.style.display = "block";
    };

    const getRuntimeCriticalPromptLens = () => (
      permitCatalog.summary && typeof permitCatalog.summary.runtime_critical_prompt_lens === "object"
        ? permitCatalog.summary.runtime_critical_prompt_lens
        : {}
    );

    const renderOperatorDemoSurface = (industry) => {
      if (!ui.operatorDemoBox) return;
      const demo = getOperatorDemoSurface(industry);
      if (!demo) {
        ui.operatorDemoBox.style.display = "none";
        ui.operatorDemoBox.innerHTML = "";
        return;
      }
      const meta = [];
      if (demo.claim_id) meta.push(`claim ${esc(demo.claim_id)}`);
      if (demo.family_key) meta.push(esc(demo.family_key));
      if (demo.proof_coverage_ratio) meta.push(`proof ${esc(demo.proof_coverage_ratio)}`);
      if (Number(demo.demo_case_total || 0) > 0) meta.push(`demo ${Number(demo.demo_case_total || 0)}건`);
      if (Number(demo.manual_review_demo_total || 0) > 0) meta.push(`수동 검토 ${Number(demo.manual_review_demo_total || 0)}건`);
      const reviewReasons = Array.isArray(demo.review_reasons)
        ? demo.review_reasons.map((item) => getReviewReasonLabel(item)).filter(Boolean)
        : [];
      if (reviewReasons.length) meta.push(`사유 ${reviewReasons.join(", ")}`);
      const storyPoints = Array.isArray(demo.operator_story_points)
        ? demo.operator_story_points.filter(Boolean)
        : [];
      const criticalPromptLines = Array.isArray((permitCatalog.summary && permitCatalog.summary.runtime_critical_prompt_excerpt) || [])
        ? permitCatalog.summary.runtime_critical_prompt_excerpt.filter(Boolean)
        : [];
      const criticalPromptLens = getRuntimeCriticalPromptLens();
      const binding = demo.prompt_case_binding && typeof demo.prompt_case_binding === "object"
        ? demo.prompt_case_binding
        : null;
      const bindingPresetId = String((binding && binding.preset_id) || "").trim();
      const bindingParts = [];
      if (binding) {
        if (binding.service_name || binding.service_code) {
          bindingParts.push(esc(binding.service_name || binding.service_code || ""));
        }
        if (binding.expected_status) bindingParts.push(`expected ${esc(binding.expected_status)}`);
        if (binding.review_reason) bindingParts.push(esc(getReviewReasonLabel(binding.review_reason)));
        if (binding.binding_focus) bindingParts.push(`lens ${esc(getPromptBindingFocusLabel(binding.binding_focus))}`);
        if (binding.manual_review_expected) bindingParts.push("수동 검토");
      }
      const bindingQuestion = String((binding && binding.binding_question) || "").trim();
      const caseLines = Array.isArray(demo.demo_cases)
        ? demo.demo_cases.slice(0, 3).map((item) => {
            const parts = [esc(item.service_name || item.service_code || "")];
            if (item.case_kind) parts.push(esc(item.case_kind));
            if (item.expected_status) parts.push(esc(item.expected_status));
            if (item.review_reason) parts.push(esc(getReviewReasonLabel(item.review_reason)));
            if (item.manual_review_expected) parts.push("수동 검토");
            return `- ${parts.filter(Boolean).join(" / ")}`;
          })
        : [];
      const lensLines = [];
      if (criticalPromptLens && typeof criticalPromptLens === "object" && criticalPromptLens.lens_ready) {
        if (criticalPromptLens.bottleneck_statement) lensLines.push(`- bottleneck: ${esc(criticalPromptLens.bottleneck_statement)}`);
        if (criticalPromptLens.inspect_first) lensLines.push(`- inspect first: ${esc(criticalPromptLens.inspect_first)}`);
        if (criticalPromptLens.next_action) lensLines.push(`- next action: ${esc(criticalPromptLens.next_action)}`);
        if (criticalPromptLens.falsification_test) lensLines.push(`- falsification: ${esc(criticalPromptLens.falsification_test)}`);
      }
      const packetPath = String((permitCatalog.summary && permitCatalog.summary.runtime_operator_demo_packet_path) || "").trim();
      ui.operatorDemoBox.innerHTML = ''
        + '<strong>운영 데모 패킷</strong><br>'
        + (meta.length ? `${meta.map((item) => `[${item}]`).join(" ")}<br>` : "")
        + (storyPoints.length ? `${storyPoints.map((item) => `- ${esc(item)}`).join("<br>")}<br>` : "")
        + (bindingParts.length || bindingQuestion || bindingPresetId
            ? `<span class="assist">판단 바로가기</span><br>`
              + (bindingParts.length ? `- ${bindingParts.join(" / ")}<br>` : "")
              + (bindingQuestion ? `- 질문: ${esc(bindingQuestion)}<br>` : "")
              + (bindingPresetId
                  ? `<button type="button" class="preset-action" data-prompt-preset-id="${esc(bindingPresetId)}">대표 시나리오 채우기</button><br>`
                  : "")
            : "")
        + (caseLines.length ? `<span class="assist">대표 데모 케이스</span><br>${caseLines.join("<br>")}<br>` : "")
        + (lensLines.length ? `<span class="assist">critical thinking lens</span><br>${lensLines.join("<br>")}<br>` : "")
        + (criticalPromptLines.length
            ? `<span class="assist">?먰뙋 ?꾨줈?꾪듃</span><br>${criticalPromptLines.map((item) => `- ${esc(item)}`).join("<br>")}<br>`
            : "")
        + (packetPath ? `<span class="assist">packet: ${esc(packetPath)}</span>` : "");
      if (bindingPresetId) {
        const button = ui.operatorDemoBox.querySelector("[data-prompt-preset-id]");
        if (button) {
          button.addEventListener("click", () => {
            const presets = getReviewCasePresets(industry);
            const target = presets.find((item) => String(item.preset_id || "") === bindingPresetId);
            if (target) applyReviewCasePreset(target);
          });
        }
      }
      ui.operatorDemoBox.style.display = "block";
    };

    const getRuntimeReasoningLadderMap = () => (
      permitCatalog.summary && typeof permitCatalog.summary.runtime_reasoning_ladder_map === "object"
        ? permitCatalog.summary.runtime_reasoning_ladder_map
        : {}
    );

    const deriveRuntimeReasonKey = (typedEval, capitalGap, technicianGap) => {
      if (!typedEval || typeof typedEval !== "object") return "";
      const capitalShort = !!(capitalGap && !capitalGap.isSatisfied);
      const technicianShort = !!(technicianGap && !technicianGap.isSatisfied);
      if (typedEval.manualReviewRequired) return "other_requirement_documents_missing";
      if (capitalShort && technicianShort) return "capital_and_technician_shortfall";
      if (capitalShort && !technicianShort) return "capital_shortfall_only";
      if (technicianShort && !capitalShort) return "technician_shortfall_only";
      return "";
    };

    const getRuntimeReasoningPreset = (industry, reasonKey) => {
      const demo = getOperatorDemoSurface(industry);
      const presets = getReviewCasePresets(industry);
      if (reasonKey === "other_requirement_documents_missing"
          && demo
          && demo.prompt_case_binding
          && typeof demo.prompt_case_binding === "object") {
        return demo.prompt_case_binding;
      }
      const preset = presets.find((item) => {
        const expected = item && typeof item.expected_outcome === "object" ? item.expected_outcome : {};
        return String(expected.review_reason || "").trim() === reasonKey;
      });
      if (preset) {
        const expected = preset && typeof preset.expected_outcome === "object" ? preset.expected_outcome : {};
        return {
          preset_id: String(preset.preset_id || "").trim(),
          service_code: String(preset.service_code || "").trim(),
          service_name: String(preset.service_name || "").trim(),
          expected_status: String(expected.overall_status || "").trim(),
          review_reason: String(expected.review_reason || "").trim(),
          manual_review_expected: !!expected.manual_review_expected,
          binding_focus: reasonKey === "capital_and_technician_shortfall"
            ? "capital_and_technician_gap_first"
            : (reasonKey === "capital_shortfall_only"
              ? "capital_gap_first"
              : (reasonKey === "technician_shortfall_only" ? "technician_gap_first" : "review_reason_first")),
        };
      }
      return null;
    };

    const renderRuntimeReasoningCard = (industry, typedEval, context = {}) => {
      if (!ui.runtimeReasoningCardBox) return;
      if (!industry || !typedEval || typeof typedEval !== "object") {
        ui.runtimeReasoningCardBox.style.display = "none";
        ui.runtimeReasoningCardBox.innerHTML = "";
        return;
      }
      const ladderMap = getRuntimeReasoningLadderMap();
      const criticalPromptLens = getRuntimeCriticalPromptLens();
      const reasonKey = deriveRuntimeReasonKey(typedEval, context.capitalGap, context.technicianGap);
      const ladder = reasonKey && typeof ladderMap[reasonKey] === "object" ? ladderMap[reasonKey] : null;
      const preset = getRuntimeReasoningPreset(industry, reasonKey);
      const badges = [];
      if (typedEval.overall_status) badges.push(`status ${esc(typedEval.overall_status)}`);
      if (reasonKey) badges.push(esc(getReviewReasonLabel(reasonKey)));
      if (typedEval.manualReviewRequired) badges.push("수동 검토");
      if (preset && preset.binding_focus) badges.push(`lens ${esc(getPromptBindingFocusLabel(preset.binding_focus))}`);
      const inspectFirst = String((ladder && ladder.inspect_first) || "").trim()
        || (context.capitalGap && !context.capitalGap.isSatisfied && context.technicianGap && !context.technicianGap.isSatisfied
          ? "자본금과 기술인력 증빙을 함께 먼저 확인해 주세요."
          : "")
        || (context.capitalGap && !context.capitalGap.isSatisfied
          ? "자본금 증빙과 입력값을 먼저 확인해 주세요."
          : (context.technicianGap && !context.technicianGap.isSatisfied
            ? "기술인력 자격과 인원 증빙을 먼저 확인해 주세요."
            : "누락된 서류와 자동 검토 보류 사유를 먼저 확인해 주세요."));
      const nextAction = String((ladder && ladder.next_action) || "").trim()
        || (Array.isArray(typedEval.next_actions) && typedEval.next_actions.length
          ? String(typedEval.next_actions[0] || "").trim()
          : "다음 액션을 위해 증빙과 입력값을 먼저 정리해 주세요.");
      const evidenceFirst = Array.isArray(ladder && ladder.evidence_first)
        ? ladder.evidence_first.map((item) => esc(proofDomainLabels[item] || item)).filter(Boolean)
        : [];
      const bindingQuestion = String((preset && preset.binding_question) || "").trim()
        || (Array.isArray(ladder && ladder.binding_questions) ? String((ladder.binding_questions[0] || "")).trim() : "");
      const _cardSections = [];
      _cardSections.push(`<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;"><strong style="font-size:15px;">실시간 판단 카드</strong>${badges.map((item) => `<span style="background:var(--smna-badge-info-bg,#E3F2FD);color:var(--smna-primary,#003764);padding:2px 8px;border-radius:4px;font-size:11px;font-weight:500;">${item}</span>`).join("")}</div>`);
      _cardSections.push(`<div style="margin:6px 0;padding:8px 12px;background:var(--smna-badge-warning-bg,#FFF8E1);border-radius:6px;border-left:3px solid #FFB800;font-size:13px;"><strong>우선 확인:</strong> ${esc(inspectFirst)}</div>`);
      if (evidenceFirst.length) {
        _cardSections.push(`<div style="margin:4px 0;font-size:13px;color:var(--smna-sub);"><strong>증빙 우선:</strong> ${evidenceFirst.join(", ")}</div>`);
      }
      _cardSections.push(`<div style="margin:4px 0;font-size:13px;"><strong>다음 단계:</strong> ${esc(nextAction)}</div>`);
      if (criticalPromptLens && criticalPromptLens.lens_ready && criticalPromptLens.falsification_test) {
        _cardSections.push(`<div style="margin:4px 0;font-size:12px;color:var(--smna-sub);"><strong>검증 렌즈:</strong> ${esc(criticalPromptLens.falsification_test)}</div>`);
      }
      if (bindingQuestion) {
        _cardSections.push(`<div style="margin:4px 0;font-size:13px;color:var(--smna-primary,#003764);"><strong>확인 질문:</strong> ${esc(bindingQuestion)}</div>`);
      }
      if (preset && preset.preset_id) {
        _cardSections.push(
          `<button type="button" class="preset-action" data-runtime-preset-id="${esc(preset.preset_id)}" style="margin-top:8px;padding:8px 16px;border:none;border-radius:6px;background:var(--smna-primary,#003764);color:#fff;font-size:13px;cursor:pointer;">대표 보완 프리셋 적용</button>`
        );
      }
      ui.runtimeReasoningCardBox.innerHTML = _cardSections.join("");
      ui.runtimeReasoningCardBox.style.display = "block";
      const button = ui.runtimeReasoningCardBox.querySelector("[data-runtime-preset-id]");
      if (button && preset && preset.preset_id) {
        button.addEventListener("click", () => {
          const presets = getReviewCasePresets(industry);
          const target = presets.find((item) => String(item.preset_id || "") === String(preset.preset_id || "").trim());
          if (target) applyReviewCasePreset(target);
        });
      }
    };

    const renderCandidateFallback = (industry) => {
      const criteriaRows = Array.isArray(industry.candidate_criteria_lines) ? industry.candidate_criteria_lines : [];
      const additionalRows = Array.isArray(industry.candidate_additional_criteria_lines)
        ? industry.candidate_additional_criteria_lines
        : [];
      const autoCandidates = Array.isArray(industry.auto_law_candidates) ? industry.auto_law_candidates : [];
      const basisRows = Array.isArray(industry.candidate_legal_basis) && industry.candidate_legal_basis.length
        ? industry.candidate_legal_basis
        : autoCandidates.map((item) => ({
            law_title: String(item.law_title || ""),
            article: "",
            url: String(item.law_url || ""),
          }));

      ui.requiredCapital.textContent = criteriaRows.length ? "법령 추출본 확인" : "법령 후보 확인";
      ui.requirementsMeta.textContent = criteriaRows.length
        ? `자동 추출 기준 ${criteriaRows.length}건`
        : `법령 후보 ${autoCandidates.length}건`;
      ui.capitalGapStatus.textContent = criteriaRows.length ? "수치 기준 구조화 중" : "법령 후보 검토 필요";
      ui.capitalGapStatus.className = "status warn";
      ui.technicianGapStatus.textContent = criteriaRows.length ? "추출 문장 확인" : "추출 대기";
      ui.technicianGapStatus.className = "status warn";
      ui.equipmentGapStatus.textContent = additionalRows.length ? "추가 기준 추출됨" : "법령 본문 확인 필요";
      ui.equipmentGapStatus.className = "status warn";
      ui.diagnosisDate.textContent = "-";
      ui.crossValidation.textContent = "";

      ui.fallbackGuide.style.display = "block";
      ui.fallbackGuide.textContent = criteriaRows.length
        ? `${industry.service_name}: 자동 수집한 법령 기준 문장을 우선 표시합니다. 정량 비교는 구조화가 끝나는 대로 반영합니다.`
        : `${industry.service_name}: 법령 후보는 확보됐지만 등록기준 문장 추출은 아직 미완료입니다.`;

      renderBasisRows(basisRows, criteriaRows.length ? "자동 수집 법령 근거" : "법령 후보");

      if (criteriaRows.length) {
        ui.coverageGuide.textContent = "자동 추출 기준 문장을 표시합니다. 법령 해석이 필요한 항목은 원문 링크로 함께 확인하세요.";
        ui.coverageGuide.style.display = "block";
        ui.typedCriteriaBox.innerHTML = `<strong>자동 추출 등록기준</strong><br>${criteriaRows
          .map((row) => `- ${esc(row.text || "")}`)
          .join("<br>")}`;
        ui.typedCriteriaBox.style.display = "block";
      }

      if (additionalRows.length) {
        ui.evidenceChecklistBox.innerHTML = `<strong>추가 확인 항목</strong><br>${additionalRows
          .map((row) => `- ${esc(row.text || "")}`)
          .join("<br>")}`;
        ui.evidenceChecklistBox.style.display = "block";
      }

      if (autoCandidates.length) {
        ui.nextActionsBox.innerHTML = `<strong>후속 처리</strong><br>${autoCandidates
          .slice(0, 3)
          .map((row) => `- ${esc(row.law_title || "")}`)
          .join("<br>")}`;
        ui.nextActionsBox.style.display = "block";
      }
    };

    const buildAdditionalInputs = () => ({
      office_secured: !!(ui.officeSecuredInput && ui.officeSecuredInput.checked),
      facility_secured: !!(ui.facilitySecuredInput && ui.facilitySecuredInput.checked),
      qualification_secured: !!(ui.qualificationSecuredInput && ui.qualificationSecuredInput.checked),
      insurance_secured: !!(ui.insuranceSecuredInput && ui.insuranceSecuredInput.checked),
      safety_secured: !!(ui.safetySecuredInput && ui.safetySecuredInput.checked),
      document_ready: !!(ui.documentReadyInput && ui.documentReadyInput.checked),
    });

    const evaluateTypedCriteriaLocal = (rule, inputs) => {
      const typed = Array.isArray(rule && rule.typed_criteria) ? rule.typed_criteria : [];
      const pending = Array.isArray(rule && rule.pending_criteria_lines) ? rule.pending_criteria_lines : [];
      const mappingMeta = rule && rule.mapping_meta ? rule.mapping_meta : {};
      const coerce = (value, type) => {
        const vt = String(type || "number").toLowerCase();
        if (vt === "boolean" || vt === "bool") return !!value;
        if (vt === "integer" || vt === "int") return Core.toInt(value);
        if (vt === "string" || vt === "text") return String(value || "").trim();
        return Number.isFinite(Number(value)) ? Number(value) : null;
      };
      const criterionResults = [];
      const evidenceChecklist = [];
      let blockingFailureCount = 0;
      let unknownBlockingCount = 0;
      typed.forEach((criterion) => {
        const inputKey = String((criterion && criterion.input_key) || "");
        if (!inputKey) return;
        const currentRaw = Object.prototype.hasOwnProperty.call(inputs, inputKey) ? inputs[inputKey] : null;
        const currentValue = coerce(currentRaw, criterion.value_type);
        const requiredValue = coerce(criterion.required_value, criterion.value_type);
        const operator = String(criterion.operator || ">=");
        let status = "missing_input";
        let ok = null;
        let gap = null;
        if (!(currentValue === null || currentValue === undefined || (String(criterion.value_type || '').toLowerCase() === 'number' && !Number.isFinite(Number(currentValue))))) {
          if (operator === "==") {
            ok = currentValue === requiredValue;
          } else if (operator === ">=") {
            ok = Number(currentValue) >= Number(requiredValue);
            gap = Math.max(0, Number(requiredValue) - Number(currentValue));
          } else {
            ok = currentValue === requiredValue;
          }
          status = ok ? "pass" : "fail";
        }
        const blocking = !!criterion.blocking;
        if (blocking && status === "fail") blockingFailureCount += 1;
        if (blocking && status === "missing_input") unknownBlockingCount += 1;
        const row = {
          criterion_id: String(criterion.criterion_id || ""),
          label: String(criterion.label || criterion.criterion_id || ""),
          category: String(criterion.category || ""),
          status,
          ok,
          gap,
          blocking,
          evidence_types: Array.isArray(criterion.evidence_types) ? criterion.evidence_types : [],
          note: String(criterion.note || ""),
        };
        criterionResults.push(row);
        if (status === "fail" || status === "missing_input") {
          const reason = status === "fail" ? "보완 필요" : "입력 확인 필요";
          const evidenceTypes = row.evidence_types.length ? row.evidence_types : ["증빙 자료 확인"];
          evidenceTypes.forEach((label, idx) => {
            evidenceChecklist.push({
              doc_id: `${row.criterion_id}::${idx + 1}`,
              label: String(label || ""),
              criterion_id: row.criterion_id,
              reason,
            });
          });
        }
      });
      const mappingConfidence = Number(mappingMeta.mapping_confidence || 0) || null;
      const coverageStatus = String(mappingMeta.coverage_status || (pending.length ? "partial" : "full"));
      let manualReviewRequired = !!mappingMeta.manual_review_required || pending.length > 0;
      if (mappingConfidence !== null && mappingConfidence < 0.75) manualReviewRequired = true;
      let overallStatus = "pass";
      if (blockingFailureCount > 0) overallStatus = "shortfall";
      else if (unknownBlockingCount > 0 || manualReviewRequired || coverageStatus !== "full") overallStatus = "manual_review";
      const nextActions = [];
      const ctaMode = blockingFailureCount > 0 ? "shortfall" : (manualReviewRequired ? "manual_review" : "pass");
      if (ctaMode === "shortfall") {
        nextActions.push("부족한 요건부터 먼저 보완해 주세요.");
        if (unknownBlockingCount > 0) nextActions.push("입력하지 않은 필수 항목을 확인해 주세요.");
        nextActions.push("보완 완료 후 다시 진단하면 등록 가능 여부를 확인할 수 있습니다.");
      } else if (ctaMode === "manual_review") {
        if (unknownBlockingCount > 0) nextActions.push("일부 항목의 입력값이 누락되어 정확한 판단이 어렵습니다.");
        if (pending.length > 0) nextActions.push("자동 구조화가 완료되지 않은 기준이 있어 법령 원문 대조가 필요합니다.");
        if (mappingConfidence !== null && mappingConfidence < 0.75) nextActions.push("매핑 신뢰도가 낮아 전문 행정사의 확인을 권장합니다.");
        nextActions.push("정밀 검토가 필요한 경우 전문 상담을 이용해 주세요.");
      }
      return {
        typed_criteria_total: typed.length,
        pending_criteria_count: pending.length,
        criterion_results: criterionResults,
        evidence_checklist: evidenceChecklist,
        blocking_failure_count: blockingFailureCount,
        unknown_blocking_count: unknownBlockingCount,
        manual_review_required: manualReviewRequired,
        coverage_status: coverageStatus,
        mapping_confidence: mappingConfidence,
        overall_status: overallStatus,
        next_actions: nextActions,
        pending_lines: pending,
      };
    };

    const renderStructuredReview = (typedEval) => {
      const coverageText = [];
      if (typedEval.coverage_status) coverageText.push(`구조화 상태: ${esc(typedEval.coverage_status)}`);
      if (Number.isFinite(Number(typedEval.mapping_confidence))) coverageText.push(`신뢰도: ${Number(typedEval.mapping_confidence).toFixed(2)}`);
      if (Number(typedEval.pending_criteria_count || 0) > 0) coverageText.push(`미구조화 ${Number(typedEval.pending_criteria_count)}건`);
      if (coverageText.length) {
        ui.coverageGuide.textContent = coverageText.join(" / ");
        ui.coverageGuide.style.display = "block";
      }

      const criteriaRows = Array.isArray(typedEval.criterion_results) ? typedEval.criterion_results : [];
      if (criteriaRows.length) {
        const _bs = {
          pass: "background:var(--smna-badge-success-bg,#E6F9F1);color:#0F9460;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;",
          fail: "background:var(--smna-badge-error-bg,#FFEBEE);color:#D32F2F;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;",
          missing_input: "background:var(--smna-badge-warning-bg,#FFF8E1);color:#F57C00;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;",
        };
        ui.typedCriteriaBox.innerHTML = `<strong style="display:block;margin-bottom:8px;">자동 점검 결과 <span style="font-weight:400;color:var(--smna-sub);font-size:13px;">(${criteriaRows.length}개 항목)</span></strong>${criteriaRows.map((row) => {
          const badgeText = row.status === "pass" ? "충족" : (row.status === "fail" ? "부족" : "입력 필요");
          const st = _bs[row.status] || _bs.missing_input;
          const note = row.note ? `<span style="color:var(--smna-sub);font-size:12px;margin-left:4px;">${esc(row.note)}</span>` : "";
          return `<div style="margin:4px 0;display:flex;align-items:center;gap:8px;flex-wrap:wrap;"><span style="${st}">${esc(badgeText)}</span><span>${esc(row.label || row.criterion_id)}</span>${note}</div>`;
        }).join("")}`;
        ui.typedCriteriaBox.style.display = "block";
      }

      const evidenceRows = Array.isArray(typedEval.evidence_checklist) ? typedEval.evidence_checklist : [];
      if (evidenceRows.length) {
        const isShortfall = typedEval.overall_status === "shortfall";
        const evidenceTitle = isShortfall ? "보완 필요 서류" : "확인 권장 서류";
        const evidenceDesc = isShortfall
          ? "아래 서류를 준비하시면 등록 요건을 충족할 수 있습니다."
          : "아래 항목은 전문가 확인 시 필요할 수 있는 서류입니다.";
        const _evBorder = isShortfall ? "border-left:3px solid #D32F2F;" : "border-left:3px solid var(--smna-accent-strong,#0078D4);";
        ui.evidenceChecklistBox.innerHTML = `<div style="${_evBorder}padding:12px;border-radius:8px;background:${isShortfall ? "var(--smna-badge-error-bg,#FFEBEE)" : "var(--smna-badge-info-bg,#E3F2FD)"};"><strong style="display:block;margin-bottom:6px;">${evidenceTitle}</strong><small style="color:var(--smna-sub);display:block;margin-bottom:8px;">${evidenceDesc}</small>${evidenceRows.map((row) => {
          const _evStyle = row.reason === "보완 필요" ? "color:#D32F2F;font-weight:600;" : "color:var(--smna-sub);";
          return `<div style="margin:4px 0;display:flex;align-items:flex-start;gap:6px;"><span style="flex-shrink:0;width:18px;text-align:center;">${row.reason === "보완 필요" ? "⚠️" : "📋"}</span><span>${esc(row.label)} <span style="${_evStyle}font-size:12px;">(${esc(row.reason || "확인 필요")})</span></span></div>`;
        }).join("")}</div>`;
        ui.evidenceChecklistBox.style.display = "block";
      }

      const nextRows = Array.isArray(typedEval.next_actions) ? typedEval.next_actions : [];
      if (nextRows.length) {
        const isManualReview = typedEval.overall_status === "manual_review";
        const ctaTitle = isManualReview ? "전문가 검토 안내" : "다음 단계";
        const ctaStyle = isManualReview ? "background:#FFF8E1;border-left:3px solid #FFB800;padding:12px;border-radius:8px;" : "";
        ui.nextActionsBox.innerHTML = `<div style="${ctaStyle}"><strong>${ctaTitle}</strong><br>${nextRows.map((row) => `- ${esc(row)}`).join("<br>")}</div>`;
        ui.nextActionsBox.style.display = "block";
      }
    };

    const renderResult = () => {
      const selected = getSelectedIndustry();
      const rule = getSelectedRule(selected);
      syncHoldingsInputVisibility(selected, rule);
      if (!selected) {
        clearResult();
        return;
      }

      const industryName = String(selected.service_name || "");
      renderFocusProfile(selected);
      renderQualityFlags(selected);
      renderProofClaim(selected);
      renderReviewCasePresets(selected);
      renderCaseStorySurface(selected);
      renderOperatorDemoSurface(selected);
      ui.runtimeReasoningCardBox.style.display = "none";
      ui.runtimeReasoningCardBox.innerHTML = "";

      const rawCapitalInput = String(ui.capitalInput.value || "").trim();
      const currentCapital = Core.toNum(rawCapitalInput);
      const currentTechnicians = Core.toInt(ui.technicianInput.value || 0);
      const currentEquipment = Core.toInt(ui.equipmentInput.value || 0);

      if (!rule) {
        syncCoreStatusCardVisibility(selected, rule);
        const hasCandidateCriteria = Number(selected.candidate_criteria_count || 0) > 0;
        const hasCandidateLaw = Array.isArray(selected.auto_law_candidates) && selected.auto_law_candidates.length > 0;
        if (hasCandidateCriteria || hasCandidateLaw) {
          renderCandidateFallback(selected);
          return;
        }
        ui.requiredCapital.textContent = "확인 필요";
        ui.requirementsMeta.textContent = "이 업종은 아직 정량 기준이 구조화되지 않아 법령 근거 중심으로 안내합니다.";
        ui.capitalGapStatus.textContent = "자본금 기준 확인 필요";
        ui.capitalGapStatus.className = "status warn";
        ui.technicianGapStatus.textContent = "기술인력 기준 확인 필요";
        ui.technicianGapStatus.className = "status warn";
        ui.equipmentGapStatus.textContent = "장비 기준 확인 필요";
        ui.equipmentGapStatus.className = "status warn";
        ui.diagnosisDate.textContent = "-";
        ui.crossValidation.textContent = "";
        ui.fallbackGuide.style.display = "block";
        ui.fallbackGuide.textContent = `${industryName}: 현재는 법령 후보(실업종/등록기준/특례)를 우선 안내합니다.`;
        ui.legalBasis.style.display = "none";
        ui.legalBasis.innerHTML = "";
        return;
      }

      const req = rule.requirements || {};
      syncCoreStatusCardVisibility(selected, rule);
      const capitalGap = Core.computeGap(req.capital_eok, currentCapital);
      const technicianGap = Core.computeIntGap(req.technicians, currentTechnicians);
      const equipmentGap = Core.computeIntGap(req.equipment_count, currentEquipment);
      const diagnosis = Core.predictDiagnosisDate(req.deposit_days);
      const typedEval = evaluateTypedCriteriaLocal(rule, {
        capital_eok: currentCapital,
        current_capital_eok: currentCapital,
        technicians_count: currentTechnicians,
        technicians: currentTechnicians,
        current_technicians: currentTechnicians,
        equipment_count: currentEquipment,
        current_equipment_count: currentEquipment,
        deposit_days: Core.toInt(req.deposit_days || 0),
        raw_capital_input: rawCapitalInput,
        ...buildAdditionalInputs(),
      });

      ui.requiredCapital.textContent = Core.formatEok(req.capital_eok || 0);
      ui.requirementsMeta.textContent = buildRequirementsMetaSummary(selected, rule);

      renderGapStatus(ui.capitalGapStatus, capitalGap, Core.formatEok, "기준 충족", "추가 확보 필요");
      renderGapStatus(
        ui.technicianGapStatus,
        technicianGap,
        (v) => `${Core.toInt(v).toLocaleString("ko-KR")}명`,
        "기준 충족",
        "추가 확보 필요",
      );
      renderGapStatus(
        ui.equipmentGapStatus,
        equipmentGap,
        (v) => `${Core.toInt(v).toLocaleString("ko-KR")}식`,
        "기준 충족",
        "추가 확보 필요",
      );
      if (!getStructuredCoreVisibility(selected, rule).equipment) {
        ui.equipmentGapStatus.textContent = "-";
        ui.equipmentGapStatus.className = "status";
      }

      ui.diagnosisDate.textContent = `${diagnosis.dateLabel} (D+${diagnosis.days})`;

      const suspicious = Core.detectSuspiciousCapitalInput(rawCapitalInput, currentCapital, req.capital_eok || 0);
      if (suspicious) {
        ui.crossValidation.textContent =
          `입력 자본금 ${Core.formatEok(currentCapital)}은 단위가 크게 들어간 값처럼 보입니다. 억 단위인지 확인해 주세요.`;
      } else {
        ui.crossValidation.textContent = "";
      }

      ui.fallbackGuide.style.display = "none";
      ui.fallbackGuide.textContent = "";
      if (typedEval.manualReviewRequired) {
        ui.fallbackGuide.style.display = "block";
        ui.fallbackGuide.textContent = `${industryName}: 자동 구조화가 덜 된 항목이 있어 법령 원문을 함께 확인해 주세요.`;
      }
      renderRuleBasis(rule);
      renderRuntimeReasoningCard(selected, typedEval, { capitalGap, technicianGap });
      renderStructuredReview(typedEval);
    };

    const init = () => {
      const defaultMode = String((permitCatalog.summary && permitCatalog.summary.focus_default_mode) || "all");
      if (ui.focusModeSelect) ui.focusModeSelect.value = defaultMode;
      syncFocusModePills();
      renderCategories();
      renderIndustries();
      ensureSyntheticIndustryOptions();
      clearResult();
      const rerenderSelection = () => {
        renderCategories();
        renderIndustries();
        ensureSyntheticIndustryOptions();
        clearResult();
        syncExperienceLayer();
        setPermitWizardStep(findPermitWizardResumeStep());
      };
      const renderWithExperience = () => {
        renderResult();
        syncExperienceLayer();
      };
      const advancePermitWizardAfterIndustrySelection = () => {
        const resumeStep = findPermitWizardResumeStep();
        if (getSelectedIndustry() && permitWizardStepIndex < resumeStep) {
          setPermitWizardStep(resumeStep);
        }
      };
      if (ui.permitInputWizard) {
        ui.permitInputWizard.addEventListener("click", (event) => {
          const target = event.target;
          const nextActionButton = target && target.closest ? target.closest("[data-permit-next-action]") : null;
          if (nextActionButton) {
            runPermitWizardNextAction(String(nextActionButton.getAttribute("data-permit-next-action") || ""));
            return;
          }
          const prevButton = target && target.closest ? target.closest("[data-permit-wizard-prev]") : null;
          if (prevButton) {
            setPermitWizardStep(Number(prevButton.getAttribute("data-permit-wizard-prev") || 0) - 1, { focus: true });
            return;
          }
          const nextButton = target && target.closest ? target.closest("[data-permit-wizard-next]") : null;
          if (nextButton) {
            const currentIndex = Number(nextButton.getAttribute("data-permit-wizard-next") || 0);
            if (currentIndex >= permitWizardStepsMeta.length - 1) {
              const resultTarget = document.getElementById("resultBanner")
                || document.getElementById("result-title")
                || document.querySelector(".result-card");
              if (resultTarget && typeof resultTarget.scrollIntoView === "function") {
                resultTarget.scrollIntoView({ behavior: "smooth", block: "start" });
              }
              return;
            }
            setPermitWizardStep(currentIndex + 1, { focus: true });
            return;
          }
          const trackButton = target && target.closest ? target.closest("[data-permit-wizard-track]") : null;
          if (trackButton) {
            setPermitWizardStep(Number(trackButton.getAttribute("data-permit-wizard-track") || 0), { focus: true });
          }
        });
      }
      if (ui.focusModePills) {
        Array.from(ui.focusModePills.querySelectorAll("[data-focus-mode]")).forEach((button) => {
          button.addEventListener("click", () => {
            const mode = String(button.getAttribute("data-focus-mode") || "all");
            if (ui.focusModeSelect) ui.focusModeSelect.value = mode;
            rerenderSelection();
          });
        });
      }
      if (ui.focusModeSelect) {
        ui.focusModeSelect.addEventListener("change", () => {
          rerenderSelection();
        });
      }
      if (ui.focusQuickSelect) {
        ui.focusQuickSelect.addEventListener("change", () => {
          permitSearchStarted = true;
          const targetCode = String(ui.focusQuickSelect.value || "");
          if (!targetCode) {
            clearPermitAutoSelectionReasonState();
            clearResult();
            syncExperienceLayer();
            return;
          }
          setPermitAutoSelectionReasonState("빠른 선택으로 바로 확정한 업종입니다.", "빠른 선택");
          if (applyIndustrySelection(targetCode)) {
            renderWithExperience();
            advancePermitWizardAfterIndustrySelection();
          }
        });
      }
      if (ui.fillRequirementPreset) {
        ui.fillRequirementPreset.addEventListener("click", () => {
          const snapshot = getRequirementPresetSnapshot();
          if (!snapshot.ready) return;
          if (ui.capitalInput && snapshot.values.capital !== null) {
            ui.capitalInput.value = String(Math.round(snapshot.values.capital * 100) / 100);
          }
          if (ui.technicianInput && snapshot.values.technicians !== null) {
            ui.technicianInput.value = String(Core.toInt(snapshot.values.technicians));
          }
          if (ui.equipmentInput && snapshot.values.equipment !== null) {
            ui.equipmentInput.value = String(Core.toInt(snapshot.values.equipment));
          }
          renderWithExperience();
          setPermitWizardStep(findPermitWizardResumeStep(), { focus: true });
        });
      }
      if (ui.resetHoldingsPreset) {
        ui.resetHoldingsPreset.addEventListener("click", () => {
          [ui.capitalInput, ui.technicianInput, ui.equipmentInput].forEach((node) => {
            if (node) node.value = "";
          });
          clearOptionalChecklistSelections();
          renderWithExperience();
          setPermitWizardStep(findPermitWizardResumeStep(), { focus: true });
        });
      }
      if (ui.mobileQuickPresetButton) {
        ui.mobileQuickPresetButton.addEventListener("click", () => {
          const mode = String(ui.mobileQuickPresetButton.dataset.mode || "fill");
          if (mode === "reset") {
            if (ui.resetHoldingsPreset && !ui.resetHoldingsPreset.disabled) ui.resetHoldingsPreset.click();
            return;
          }
          if (ui.fillRequirementPreset && !ui.fillRequirementPreset.disabled) ui.fillRequirementPreset.click();
        });
      }
      if (ui.optionalChecklistToggle) {
        ui.optionalChecklistToggle.addEventListener("click", () => {
          optionalChecklistExpanded = !optionalChecklistExpanded;
          syncOptionalChecklistLayout();
        });
      }
      if (ui.mobileQuickResultButton) {
        ui.mobileQuickResultButton.addEventListener("click", () => {
          const target = document.getElementById("resultBanner")
            || document.getElementById("result-title")
            || document.querySelector(".result-card");
          if (target && typeof target.scrollIntoView === "function") {
            target.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        });
      }
      if (ui.btnCopyResultBrief) {
        ui.btnCopyResultBrief.addEventListener("click", async () => {
          const ok = await copyText(ui.resultBrief ? ui.resultBrief.value : "");
          alert(ok ? "한 줄 브리프를 복사했습니다." : "한 줄 브리프 복사에 실패했습니다.");
        });
      }
      if (ui.industryAutoReason) {
        const focusPermitSearchRefine = () => {
          setPermitWizardStep(0, false);
          window.setTimeout(() => {
            focusPermitActionTarget("industrySearchInput");
          }, 32);
        };
        ui.industryAutoReason.addEventListener("click", () => {
          focusPermitSearchRefine();
        });
        ui.industryAutoReason.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          focusPermitSearchRefine();
        });
      }
      if (ui.industrySearchInput) {
        ui.industrySearchInput.addEventListener("input", () => {
          permitSearchStarted = !!String(ui.industrySearchInput.value || "").trim();
          clearPermitAutoSelectionReasonState();
          rerenderSelection();
          tryAutoSelectIndustry();
          advancePermitWizardAfterIndustrySelection();
        });
      }
      ui.categorySelect.addEventListener("change", () => {
        clearPermitAutoSelectionReasonState();
        renderIndustries();
        ensureSyntheticIndustryOptions();
        clearResult();
        tryAutoSelectIndustry();
        syncExperienceLayer();
        advancePermitWizardAfterIndustrySelection();
      });
      ui.industrySelect.addEventListener("change", () => {
        setPermitAutoSelectionReasonState("직접 확정한 업종입니다. 이제 법정 기준과 부족 항목을 바로 비교합니다.", "직접 확정");
        renderWithExperience();
        advancePermitWizardAfterIndustrySelection();
      });
      const _debouncedRender = _debounce(renderWithExperience, 250);
      ui.capitalInput.addEventListener("input", _debouncedRender);
      ui.technicianInput.addEventListener("input", _debouncedRender);
      ui.equipmentInput.addEventListener("input", _debouncedRender);
      [
        ui.officeSecuredInput,
        ui.facilitySecuredInput,
        ui.qualificationSecuredInput,
        ui.insuranceSecuredInput,
        ui.safetySecuredInput,
        ui.documentReadyInput,
      ].forEach((node) => {
        if (node) node.addEventListener("change", renderWithExperience);
      });
      setPermitWizardStep(findPermitWizardResumeStep());
      syncExperienceLayer();
    };

      init();
    })().catch((error) => {
      const fallbackNode = document.getElementById("fallbackGuide");
      if (fallbackNode) {
        fallbackNode.style.display = "block";
        fallbackNode.textContent = "인허가 데이터 로딩 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.";
      }
      if (window.console) {
        try { console.error("[permit-precheck] bootstrap failed", error); } catch (_e) {}
      }
    });
  </script>
</body>
</html>
"""

    meta_source = dict(rule_catalog_meta.get("source") or {})
    version = str(rule_catalog_meta.get("version", "") or "미지정")
    effective_date = str(rule_catalog_meta.get("effective_date", "") or "미지정")
    if not effective_date and meta_source.get("fetched_at"):
        effective_date = str(meta_source.get("fetched_at"))

    rendered_html = (
        html_template.replace("__TITLE__", escape(str(title or "")))
        .replace("__NOTICE_URL__", escape(resolved_notice_url))
        .replace("__CONTACT_PHONE__", escape(resolved_phone))
        .replace("__CONTACT_PHONE_DIGITS__", escape(resolved_phone_digits))
        .replace("__INDUSTRY_TOTAL__", str(_coerce_non_negative_int(summary.get("industry_total", 0))))
        .replace("__MAJOR_TOTAL__", str(_coerce_non_negative_int(summary.get("major_category_total", 0))))
        .replace("__WITH_RULE_TOTAL__", str(_coerce_non_negative_int(summary.get("with_registration_rule_total", 0))))
        .replace("__FOCUS_TARGET_TOTAL__", str(_coerce_non_negative_int(summary.get("focus_target_total", 0))))
        .replace(
            "__REAL_FOCUS_TARGET_TOTAL__",
            str(_coerce_non_negative_int(summary.get("real_focus_target_total", 0))),
        )
        .replace(
            "__RULES_ONLY_FOCUS_TARGET_TOTAL__",
            str(_coerce_non_negative_int(summary.get("rules_only_focus_target_total", 0))),
        )
        .replace("__RULE_VERSION__", escape(version))
        .replace("__RULE_EFFECTIVE_DATE__", escape(effective_date))
        .replace("__PERMIT_DATA_URL__", escape(resolved_data_url))
        .replace("__PERMIT_DATA_ENCODING__", escape(resolved_data_encoding))
        .replace(
            "__PERMIT_BOOTSTRAP_JSON__",
            _safe_json(inline_bootstrap_json),
        )
        .replace("__PERMIT_BOOTSTRAP_GZIP_BASE64__", inline_bootstrap_gzip_base64)
    )
    rendered_html = _repair_generated_permit_html(rendered_html)
    rendered_html = _wrap_wordpress_safe_scripts(rendered_html)
    if fragment:
        return _build_wordpress_fragment(rendered_html)
    return rendered_html


def _replace_first_block(text: str, pattern: str, replacement: str) -> str:
    updated, _ = re.subn(pattern, replacement, text, count=1, flags=re.S)
    return updated


def _repair_generated_permit_html(html: str) -> str:
    repaired = str(html or "")

    repaired = _replace_first_block(
        repaired,
        r'(<div class="field">\s*<label for="equipmentInput">.*?</div>\s*)(<div class="field">\s*<label>.*?</div>\s*</div>)',
        r'''\1<div class="field">
          <label>기타 준비 상태</label>
          <div class="meta-box">
            <label><input id="officeSecuredInput" type="checkbox" /> 사무실/영업소 확보</label><br>
            <label><input id="facilitySecuredInput" type="checkbox" /> 시설·장비·보관공간 확보</label><br>
            <label><input id="qualificationSecuredInput" type="checkbox" /> 자격·교육·경력 확보</label><br>
            <label><input id="insuranceSecuredInput" type="checkbox" /> 보험·보증 가입 확인</label><br>
            <label><input id="safetySecuredInput" type="checkbox" /> 안전·환경 요건 확인</label><br>
            <label><input id="documentReadyInput" type="checkbox" /> 필수 제출서류 준비</label>
          </div>
        </div>''',
    )
    repaired = _replace_first_block(
        repaired,
        r'<p class="tip">.*?최종 확정됩니다\.</p>',
        '<p class="tip">법령/관할 해석이 필요한 항목은 결과 화면의 법령 근거를 바탕으로 상담 단계에서 최종 확정됩니다.</p>',
    )
    repaired = _replace_first_block(
        repaired,
        r'const renderBasisRows = \(rows, title = .*?\n    };\n',
        '''const renderBasisRows = (rows, title = "법령 근거") => {
      if (!rows.length) {
        ui.legalBasis.style.display = "none";
        ui.legalBasis.innerHTML = "";
        return;
      }
      const parts = rows.map((item) => {
        const lawTitle = esc(item.law_title || "");
        const article = esc(item.article || "");
        const url = esc(item.url || "");
        if (!url) {
          return `${lawTitle} ${article}`.trim();
        }
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${lawTitle} ${article}</a>`;
      });
      ui.legalBasis.innerHTML = `<strong>${esc(title)}</strong><br>${parts.join("<br>")}`;
      ui.legalBasis.style.display = "block";
    };
''',
    )
    repaired = _replace_first_block(
        repaired,
        r'const renderRuleBasis = \(rule\) => \{.*?\n    };\n',
        '''const renderRuleBasis = (rule) => {
      const rows = Array.isArray(rule.legal_basis) ? rule.legal_basis : [];
      renderBasisRows(rows, "법령 근거");
    };
''',
    )
    repaired = _replace_first_block(
        repaired,
        r'const renderFocusProfile = \(industry\) => \{.*?\n    };\n',
        '''const renderFocusProfile = (industry) => {
      const profile = getRegistrationProfile(industry);
      if (!profile || !Object.keys(profile).length) {
        ui.focusProfileBox.style.display = "none";
        ui.focusProfileBox.innerHTML = "";
        return;
      }
      const badges = [];
      if (profile.focus_target_with_other) badges.push("자본금+기술인력+기타 필수");
      else if (profile.focus_target) badges.push("자본금+기술인력 필수");
      else if (profile.inferred_focus_candidate) badges.push("핵심 후보(재검증)");
      else badges.push("부분 구조화");
      badges.push(industry && industry.is_rules_only ? "등록기준 업종군" : "실업종");
      badges.push(profile.profile_source === "structured_requirements" ? "구조화 기준" : "본문 추론");

      const details = [];
      if (profile.capital_required) details.push(`자본금 ${Core.formatEok(profile.capital_eok || 0)}`);
      if (profile.technical_personnel_required) {
        details.push(`기술인력 ${Core.toInt(profile.technicians_required || 0)}명`);
      }
      if (profile.other_required) {
        const labels = Array.isArray(profile.other_components)
          ? profile.other_components.map((item) => otherRequirementLabels[item] || item)
          : [];
        if (labels.length) details.push(`기타 ${labels.join(", ")}`);
      }
      ui.focusProfileBox.innerHTML = `<strong>핵심 요건 프로필</strong><br>${badges
        .map((item) => `[${esc(item)}]`)
        .join(" ")}${details.length ? `<br>${details.map((item) => `- ${esc(item)}`).join("<br>")}` : ""}`;
      ui.focusProfileBox.style.display = "block";
    };
''',
    )
    repaired = _replace_first_block(
        repaired,
        r'const renderQualityFlags = \(industry\) => \{.*?\n    };\n',
        '''const renderQualityFlags = (industry) => {
      const flags = Array.isArray(industry && industry.quality_flags) ? industry.quality_flags : [];
      if (!flags.length) {
        ui.qualityFlagsBox.style.display = "none";
        ui.qualityFlagsBox.innerHTML = "";
        return;
      }
      ui.qualityFlagsBox.innerHTML = `<strong>품질 경고</strong><br>${flags
        .map((item) => `- ${esc(qualityFlagLabels[item] || item)}`)
        .join("<br>")}`;
      ui.qualityFlagsBox.style.display = "block";
    };
''',
    )
    repaired = _replace_first_block(
        repaired,
        r'const renderProofClaim = \(industry\) => \{.*?\n    };\n',
        '''const renderProofClaim = (industry) => {
      const proof = industry && typeof industry.raw_source_proof === "object" ? industry.raw_source_proof : null;
      const claim = industry && typeof industry.claim_packet_summary === "object" ? industry.claim_packet_summary : null;
      if (!proof && !claim) {
        ui.proofClaimBox.style.display = "none";
        ui.proofClaimBox.innerHTML = "";
        return;
      }

      const lines = ["<strong>법령군 증빙</strong>"];
      if (claim) {
        const badges = [];
        if (claim.claim_id) badges.push(`claim ${esc(claim.claim_id)}`);
        if (claim.family_key) badges.push(esc(claim.family_key));
        if (claim.proof_coverage_ratio) badges.push(`proof ${esc(claim.proof_coverage_ratio)}`);
        if (badges.length) {
          lines.push(badges.map((item) => `[${item}]`).join(" "));
        }
        if (claim.claim_statement) {
          lines.push(esc(claim.claim_statement));
        }
        const requiredDomains = Array.isArray(claim.required_input_domains) ? claim.required_input_domains : [];
        const optionalDomains = Array.isArray(claim.optional_input_domains) ? claim.optional_input_domains : [];
        if (requiredDomains.length) {
          lines.push(`- 필수 입력: ${requiredDomains.map((item) => esc(proofDomainLabels[item] || item)).join(", ")}`);
        }
        if (optionalDomains.length) {
          lines.push(`- 기타 입력: ${optionalDomains.map((item) => esc(proofDomainLabels[item] || item)).join(", ")}`);
        }
        if (Number(claim.checksum_sample_total || 0) > 0) {
          lines.push(`- checksum sample ${Number(claim.checksum_sample_total || 0)}건`);
        }
        const checksumSamples = Array.isArray(claim.checksum_samples) ? claim.checksum_samples.slice(0, 3) : [];
        if (checksumSamples.length) {
          lines.push(`- sample: ${checksumSamples.map((item) => esc(item)).join(", ")}`);
        }
      }
      if (proof && proof.official_snapshot_note) {
        lines.push(`- snapshot: ${esc(proof.official_snapshot_note)}`);
      }
      const proofUrls = proof && Array.isArray(proof.source_urls) ? proof.source_urls.slice(0, 1) : [];
      if (proofUrls.length) {
        const url = esc(proofUrls[0]);
        lines.push(`- source: <a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`);
      }
      ui.proofClaimBox.innerHTML = lines.join("<br>");
      ui.proofClaimBox.style.display = "block";
    };
''',
    )
    repaired = _replace_first_block(
        repaired,
        r'const renderCandidateFallback = \(industry\) => \{.*?\n    };\n',
        '''const renderCandidateFallback = (industry) => {
      const criteriaRows = Array.isArray(industry.candidate_criteria_lines) ? industry.candidate_criteria_lines : [];
      const additionalRows = Array.isArray(industry.candidate_additional_criteria_lines)
        ? industry.candidate_additional_criteria_lines
        : [];
      const autoCandidates = Array.isArray(industry.auto_law_candidates) ? industry.auto_law_candidates : [];
      const basisRows = Array.isArray(industry.candidate_legal_basis) && industry.candidate_legal_basis.length
        ? industry.candidate_legal_basis
        : autoCandidates.map((item) => ({
            law_title: String(item.law_title || ""),
            article: "",
            url: String(item.law_url || ""),
          }));

      ui.requiredCapital.textContent = criteriaRows.length ? "법령 추출본 확인" : "법령 후보 확인";
      ui.requirementsMeta.textContent = criteriaRows.length
        ? `자동 추출 기준 ${criteriaRows.length}건`
        : `법령 후보 ${autoCandidates.length}건`;
      ui.capitalGapStatus.textContent = criteriaRows.length ? "수치 기준 구조화 중" : "법령 후보 검토 필요";
      ui.capitalGapStatus.className = "status warn";
      ui.technicianGapStatus.textContent = criteriaRows.length ? "추출 문장 확인" : "추출 대기";
      ui.technicianGapStatus.className = "status warn";
      ui.equipmentGapStatus.textContent = additionalRows.length ? "추가 기준 추출됨" : "법령 본문 확인 필요";
      ui.equipmentGapStatus.className = "status warn";
      ui.diagnosisDate.textContent = "-";
      ui.crossValidation.textContent = "";

      ui.fallbackGuide.style.display = "block";
      ui.fallbackGuide.textContent = criteriaRows.length
        ? `${industry.service_name}: 자동 수집한 법령 기준 문장을 우선 표시합니다. 정량 비교는 구조화가 끝나는 대로 반영합니다.`
        : `${industry.service_name}: 법령 후보는 확보됐지만 등록기준 문장 추출은 아직 미완료입니다.`;

      renderBasisRows(basisRows, criteriaRows.length ? "자동 수집 법령 근거" : "법령 후보");

      if (criteriaRows.length) {
        ui.coverageGuide.textContent = "자동 추출 기준 문장을 표시합니다. 법령 해석이 필요한 항목은 원문 링크로 함께 확인하세요.";
        ui.coverageGuide.style.display = "block";
        ui.typedCriteriaBox.innerHTML = `<strong>자동 추출 등록기준</strong><br>${criteriaRows
          .map((row) => `- ${esc(row.text || "")}`)
          .join("<br>")}`;
        ui.typedCriteriaBox.style.display = "block";
      }

      if (additionalRows.length) {
        ui.evidenceChecklistBox.innerHTML = `<strong>추가 확인 항목</strong><br>${additionalRows
          .map((row) => `- ${esc(row.text || "")}`)
          .join("<br>")}`;
        ui.evidenceChecklistBox.style.display = "block";
      }

      if (autoCandidates.length) {
        ui.nextActionsBox.innerHTML = `<strong>후속 처리</strong><br>${autoCandidates
          .slice(0, 3)
          .map((row) => `- ${esc(row.law_title || "")}`)
          .join("<br>")}`;
        ui.nextActionsBox.style.display = "block";
      }
    };
''',
    )
    repaired = _replace_first_block(
        repaired,
        r'const evaluateTypedCriteriaLocal = \(rule, inputs\) => \{.*?\n    };\n',
        '''const evaluateTypedCriteriaLocal = (rule, inputs) => {
      const typed = Array.isArray(rule && rule.typed_criteria) ? rule.typed_criteria : [];
      const pending = Array.isArray(rule && rule.pending_criteria_lines) ? rule.pending_criteria_lines : [];
      const mappingMeta = rule && rule.mapping_meta ? rule.mapping_meta : {};
      const coerce = (value, type) => {
        const vt = String(type || "number").toLowerCase();
        if (vt === "boolean" || vt === "bool") return !!value;
        if (vt === "integer" || vt === "int") return Core.toInt(value);
        if (vt === "string" || vt === "text") return String(value || "").trim();
        return Number.isFinite(Number(value)) ? Number(value) : null;
      };
      const criterionResults = [];
      const evidenceChecklist = [];
      let blockingFailureCount = 0;
      let unknownBlockingCount = 0;
      typed.forEach((criterion) => {
        const inputKey = String((criterion && criterion.input_key) || "");
        if (!inputKey) return;
        const currentRaw = Object.prototype.hasOwnProperty.call(inputs, inputKey) ? inputs[inputKey] : null;
        const currentValue = coerce(currentRaw, criterion.value_type);
        const requiredValue = coerce(criterion.required_value, criterion.value_type);
        const operator = String(criterion.operator || ">=");
        let status = "missing_input";
        let ok = null;
        let gap = null;
        if (!(currentValue === null || currentValue === undefined || (String(criterion.value_type || '').toLowerCase() === 'number' && !Number.isFinite(Number(currentValue))))) {
          if (operator === "==") {
            ok = currentValue === requiredValue;
          } else if (operator === ">=") {
            ok = Number(currentValue) >= Number(requiredValue);
            gap = Math.max(0, Number(requiredValue) - Number(currentValue));
          } else {
            ok = currentValue === requiredValue;
          }
          status = ok ? "pass" : "fail";
        }
        const blocking = !!criterion.blocking;
        if (blocking && status === "fail") blockingFailureCount += 1;
        if (blocking && status === "missing_input") unknownBlockingCount += 1;
        const row = {
          criterion_id: String(criterion.criterion_id || ""),
          label: String(criterion.label || criterion.criterion_id || ""),
          category: String(criterion.category || ""),
          status,
          ok,
          gap,
          blocking,
          evidence_types: Array.isArray(criterion.evidence_types) ? criterion.evidence_types : [],
          note: String(criterion.note || ""),
        };
        criterionResults.push(row);
        if (status === "fail" || status === "missing_input") {
          const reason = status === "fail" ? "보완 필요" : "입력 확인 필요";
          const evidenceTypes = row.evidence_types.length ? row.evidence_types : ["증빙 자료 확인"];
          evidenceTypes.forEach((label, idx) => {
            evidenceChecklist.push({
              doc_id: `${row.criterion_id}::${idx + 1}`,
              label: String(label || ""),
              criterion_id: row.criterion_id,
              reason,
            });
          });
        }
      });
      const mappingConfidence = Number(mappingMeta.mapping_confidence || 0) || null;
      const coverageStatus = String(mappingMeta.coverage_status || (pending.length ? "partial" : "full"));
      let manualReviewRequired = !!mappingMeta.manual_review_required || pending.length > 0;
      if (mappingConfidence !== null && mappingConfidence < 0.75) manualReviewRequired = true;
      let overallStatus = "pass";
      if (blockingFailureCount > 0) overallStatus = "shortfall";
      else if (unknownBlockingCount > 0 || manualReviewRequired || coverageStatus !== "full") overallStatus = "manual_review";
      const nextActions = [];
      const ctaMode = blockingFailureCount > 0 ? "shortfall" : (manualReviewRequired ? "manual_review" : "pass");
      if (ctaMode === "shortfall") {
        nextActions.push("부족한 요건부터 먼저 보완해 주세요.");
        if (unknownBlockingCount > 0) nextActions.push("입력하지 않은 필수 항목을 확인해 주세요.");
        nextActions.push("보완 완료 후 다시 진단하면 등록 가능 여부를 확인할 수 있습니다.");
      } else if (ctaMode === "manual_review") {
        if (unknownBlockingCount > 0) nextActions.push("일부 항목의 입력값이 누락되어 정확한 판단이 어렵습니다.");
        if (pending.length > 0) nextActions.push("자동 구조화가 완료되지 않은 기준이 있어 법령 원문 대조가 필요합니다.");
        if (mappingConfidence !== null && mappingConfidence < 0.75) nextActions.push("매핑 신뢰도가 낮아 전문 행정사의 확인을 권장합니다.");
        nextActions.push("정밀 검토가 필요한 경우 전문 상담을 이용해 주세요.");
      }
      return {
        typed_criteria_total: typed.length,
        pending_criteria_count: pending.length,
        criterion_results: criterionResults,
        evidence_checklist: evidenceChecklist,
        blocking_failure_count: blockingFailureCount,
        unknown_blocking_count: unknownBlockingCount,
        manual_review_required: manualReviewRequired,
        coverage_status: coverageStatus,
        mapping_confidence: mappingConfidence,
        overall_status: overallStatus,
        next_actions: nextActions,
        pending_lines: pending,
      };
    };
''',
    )
    repaired = _replace_first_block(
        repaired,
        r'const renderStructuredReview = \(typedEval\) => \{.*?\n    };\n',
        '''const renderStructuredReview = (typedEval) => {
      const coverageText = [];
      if (typedEval.coverage_status) coverageText.push(`구조화 상태: ${esc(typedEval.coverage_status)}`);
      if (Number.isFinite(Number(typedEval.mapping_confidence))) coverageText.push(`신뢰도: ${Number(typedEval.mapping_confidence).toFixed(2)}`);
      if (Number(typedEval.pending_criteria_count || 0) > 0) coverageText.push(`미구조화 ${Number(typedEval.pending_criteria_count)}건`);
      if (coverageText.length) {
        ui.coverageGuide.textContent = coverageText.join(" / ");
        ui.coverageGuide.style.display = "block";
      }

      const criteriaRows = Array.isArray(typedEval.criterion_results) ? typedEval.criterion_results : [];
      if (criteriaRows.length) {
        const _bs = {
          pass: "background:var(--smna-badge-success-bg,#E6F9F1);color:#0F9460;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;",
          fail: "background:var(--smna-badge-error-bg,#FFEBEE);color:#D32F2F;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;",
          missing_input: "background:var(--smna-badge-warning-bg,#FFF8E1);color:#F57C00;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;",
        };
        ui.typedCriteriaBox.innerHTML = `<strong style="display:block;margin-bottom:8px;">자동 점검 결과 <span style="font-weight:400;color:var(--smna-sub);font-size:13px;">(${criteriaRows.length}개 항목)</span></strong>${criteriaRows.map((row) => {
          const badgeText = row.status === "pass" ? "충족" : (row.status === "fail" ? "부족" : "입력 필요");
          const st = _bs[row.status] || _bs.missing_input;
          const note = row.note ? `<span style="color:var(--smna-sub);font-size:12px;margin-left:4px;">${esc(row.note)}</span>` : "";
          return `<div style="margin:4px 0;display:flex;align-items:center;gap:8px;flex-wrap:wrap;"><span style="${st}">${esc(badgeText)}</span><span>${esc(row.label || row.criterion_id)}</span>${note}</div>`;
        }).join("")}`;
        ui.typedCriteriaBox.style.display = "block";
      }

      const evidenceRows = Array.isArray(typedEval.evidence_checklist) ? typedEval.evidence_checklist : [];
      if (evidenceRows.length) {
        const isShortfall = typedEval.overall_status === "shortfall";
        const evidenceTitle = isShortfall ? "보완 필요 서류" : "확인 권장 서류";
        const evidenceDesc = isShortfall
          ? "아래 서류를 준비하시면 등록 요건을 충족할 수 있습니다."
          : "아래 항목은 전문가 확인 시 필요할 수 있는 서류입니다.";
        const _evBorder = isShortfall ? "border-left:3px solid #D32F2F;" : "border-left:3px solid var(--smna-accent-strong,#0078D4);";
        ui.evidenceChecklistBox.innerHTML = `<div style="${_evBorder}padding:12px;border-radius:8px;background:${isShortfall ? "var(--smna-badge-error-bg,#FFEBEE)" : "var(--smna-badge-info-bg,#E3F2FD)"};"><strong style="display:block;margin-bottom:6px;">${evidenceTitle}</strong><small style="color:var(--smna-sub);display:block;margin-bottom:8px;">${evidenceDesc}</small>${evidenceRows.map((row) => {
          const _evStyle = row.reason === "보완 필요" ? "color:#D32F2F;font-weight:600;" : "color:var(--smna-sub);";
          return `<div style="margin:4px 0;display:flex;align-items:flex-start;gap:6px;"><span style="flex-shrink:0;width:18px;text-align:center;">${row.reason === "보완 필요" ? "⚠️" : "📋"}</span><span>${esc(row.label)} <span style="${_evStyle}font-size:12px;">(${esc(row.reason || "확인 필요")})</span></span></div>`;
        }).join("")}</div>`;
        ui.evidenceChecklistBox.style.display = "block";
      }

      const nextRows = Array.isArray(typedEval.next_actions) ? typedEval.next_actions : [];
      if (nextRows.length) {
        const isManualReview = typedEval.overall_status === "manual_review";
        const ctaTitle = isManualReview ? "전문가 검토 안내" : "다음 단계";
        const ctaStyle = isManualReview ? "background:#FFF8E1;border-left:3px solid #FFB800;padding:12px;border-radius:8px;" : "";
        ui.nextActionsBox.innerHTML = `<div style="${ctaStyle}"><strong>${ctaTitle}</strong><br>${nextRows.map((row) => `- ${esc(row)}`).join("<br>")}</div>`;
        ui.nextActionsBox.style.display = "block";
      }
    };
''',
    )
    repaired = _replace_first_block(
        repaired,
        r'const renderResult = \(\) => \{.*?\n    };\n',
        '''const renderResult = () => {
      const selected = getSelectedIndustry();
      const rule = getSelectedRule(selected);
      syncHoldingsInputVisibility(selected, rule);
      if (!selected) {
        clearResult();
        return;
      }

      const industryName = String(selected.service_name || "");
      renderFocusProfile(selected);
      renderQualityFlags(selected);
      renderProofClaim(selected);
      renderReviewCasePresets(selected);
      renderCaseStorySurface(selected);
      renderOperatorDemoSurface(selected);

      const rawCapitalInput = String(ui.capitalInput.value || "").trim();
      const currentCapital = Core.toNum(rawCapitalInput);
      const currentTechnicians = Core.toInt(ui.technicianInput.value || 0);
      const currentEquipment = Core.toInt(ui.equipmentInput.value || 0);

      if (!rule) {
        syncCoreStatusCardVisibility(selected, rule);
        const hasCandidateCriteria = Number(selected.candidate_criteria_count || 0) > 0;
        const hasCandidateLaw = Array.isArray(selected.auto_law_candidates) && selected.auto_law_candidates.length > 0;
        if (hasCandidateCriteria || hasCandidateLaw) {
          renderCandidateFallback(selected);
          return;
        }
        ui.requiredCapital.textContent = "확인 필요";
        ui.requirementsMeta.textContent = "이 업종은 아직 정량 기준이 구조화되지 않아 법령 근거 중심으로 안내합니다.";
        ui.capitalGapStatus.textContent = "자본금 기준 확인 필요";
        ui.capitalGapStatus.className = "status warn";
        ui.technicianGapStatus.textContent = "기술인력 기준 확인 필요";
        ui.technicianGapStatus.className = "status warn";
        ui.equipmentGapStatus.textContent = "장비 기준 확인 필요";
        ui.equipmentGapStatus.className = "status warn";
        ui.diagnosisDate.textContent = "-";
        ui.crossValidation.textContent = "";
        ui.fallbackGuide.style.display = "block";
        ui.fallbackGuide.textContent = `${industryName}: 현재는 법령 후보(실업종/등록기준/특례)를 우선 안내합니다.`;
        ui.legalBasis.style.display = "none";
        ui.legalBasis.innerHTML = "";
        return;
      }

      const req = rule.requirements || {};
      syncCoreStatusCardVisibility(selected, rule);
      const capitalGap = Core.computeGap(req.capital_eok, currentCapital);
      const technicianGap = Core.computeIntGap(req.technicians, currentTechnicians);
      const equipmentGap = Core.computeIntGap(req.equipment_count, currentEquipment);
      const diagnosis = Core.predictDiagnosisDate(req.deposit_days);
      const typedEval = evaluateTypedCriteriaLocal(rule, {
        capital_eok: currentCapital,
        current_capital_eok: currentCapital,
        technicians_count: currentTechnicians,
        technicians: currentTechnicians,
        current_technicians: currentTechnicians,
        equipment_count: currentEquipment,
        current_equipment_count: currentEquipment,
        deposit_days: Core.toInt(req.deposit_days || 0),
        raw_capital_input: rawCapitalInput,
        ...buildAdditionalInputs(),
      });

      ui.requiredCapital.textContent = Core.formatEok(req.capital_eok || 0);
      ui.requirementsMeta.textContent = buildRequirementsMetaSummary(selected, rule);

      renderGapStatus(ui.capitalGapStatus, capitalGap, Core.formatEok, "기준 충족", "추가 확보 필요");
      renderGapStatus(
        ui.technicianGapStatus,
        technicianGap,
        (v) => `${Core.toInt(v).toLocaleString("ko-KR")}명`,
        "기준 충족",
        "추가 확보 필요",
      );
      renderGapStatus(
        ui.equipmentGapStatus,
        equipmentGap,
        (v) => `${Core.toInt(v).toLocaleString("ko-KR")}식`,
        "기준 충족",
        "추가 확보 필요",
      );
      if (!getStructuredCoreVisibility(selected, rule).equipment) {
        ui.equipmentGapStatus.textContent = "-";
        ui.equipmentGapStatus.className = "status";
      }

      ui.diagnosisDate.textContent = `${diagnosis.dateLabel} (D+${diagnosis.days})`;

      const suspicious = Core.detectSuspiciousCapitalInput(rawCapitalInput, currentCapital, req.capital_eok || 0);
      if (suspicious) {
        ui.crossValidation.textContent =
          `입력 자본금 ${Core.formatEok(currentCapital)}은 단위가 크게 들어간 값처럼 보입니다. 억 단위인지 확인해 주세요.`;
      } else {
        ui.crossValidation.textContent = "";
      }

      ui.fallbackGuide.style.display = "none";
      ui.fallbackGuide.textContent = "";
      if (typedEval.manualReviewRequired) {
        ui.fallbackGuide.style.display = "block";
        ui.fallbackGuide.textContent = `${industryName}: 자동 구조화가 덜 된 항목이 있어 법령 원문을 함께 확인해 주세요.`;
      }
      renderRuleBasis(rule);
      renderStructuredReview(typedEval);
    };
''',
    )
    repaired = re.sub(
        r'(const criteriaRows = Array\.isArray\(typedEval\.criterion_results\) \? typedEval\.criterion_results : \[\];\s*if \(criteriaRows\.length\) \{\s*ui\.typedCriteriaBox\.innerHTML = `<strong>)(.*?)(</strong><br>\$\{criteriaRows\.map\(\(row\) => \{)',
        r'\1자동 점검 결과\3',
        repaired,
        count=1,
        flags=re.S,
    )
    repaired = re.sub(
        r'(const evidenceRows = Array\.isArray\(typedEval\.evidence_checklist\) \? typedEval\.evidence_checklist : \[\];\s*if \(evidenceRows\.length\) \{\s*ui\.evidenceChecklistBox\.innerHTML = `<strong>)(.*?)(</strong><br>\$\{evidenceRows\.map\(\(row\) => `- )',
        r'\1준비 서류\3',
        repaired,
        count=1,
        flags=re.S,
    )
    repaired = re.sub(
        r'(const nextRows = Array\.isArray\(typedEval\.next_actions\) \? typedEval\.next_actions : \[\];\s*if \(nextRows\.length\) \{\s*ui\.nextActionsBox\.innerHTML = `<strong>)(.*?)(</strong><br>\$\{nextRows\.map\(\(row\) => `- )',
        r'\1다음 단계\3',
        repaired,
        count=1,
        flags=re.S,
    )
    if "자동 점검 결과" not in repaired:
        repaired = repaired.replace(
            'const renderResult = () => {',
            '''const renderStructuredReview = (typedEval) => {
      const coverageText = [];
      if (typedEval.coverage_status) coverageText.push(`구조화 상태: ${esc(typedEval.coverage_status)}`);
      if (Number.isFinite(Number(typedEval.mapping_confidence))) coverageText.push(`신뢰도: ${Number(typedEval.mapping_confidence).toFixed(2)}`);
      if (Number(typedEval.pending_criteria_count || 0) > 0) coverageText.push(`미구조화 ${Number(typedEval.pending_criteria_count)}건`);
      if (coverageText.length) {
        ui.coverageGuide.textContent = coverageText.join(" / ");
        ui.coverageGuide.style.display = "block";
      }

      const criteriaRows = Array.isArray(typedEval.criterion_results) ? typedEval.criterion_results : [];
      if (criteriaRows.length) {
        const _bs = {
          pass: "background:var(--smna-badge-success-bg,#E6F9F1);color:#0F9460;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;",
          fail: "background:var(--smna-badge-error-bg,#FFEBEE);color:#D32F2F;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;",
          missing_input: "background:var(--smna-badge-warning-bg,#FFF8E1);color:#F57C00;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;",
        };
        ui.typedCriteriaBox.innerHTML = `<strong style="display:block;margin-bottom:8px;">자동 점검 결과 <span style="font-weight:400;color:var(--smna-sub);font-size:13px;">(${criteriaRows.length}개 항목)</span></strong>${criteriaRows.map((row) => {
          const badgeText = row.status === "pass" ? "충족" : (row.status === "fail" ? "부족" : "입력 필요");
          const st = _bs[row.status] || _bs.missing_input;
          const note = row.note ? `<span style="color:var(--smna-sub);font-size:12px;margin-left:4px;">${esc(row.note)}</span>` : "";
          return `<div style="margin:4px 0;display:flex;align-items:center;gap:8px;flex-wrap:wrap;"><span style="${st}">${esc(badgeText)}</span><span>${esc(row.label || row.criterion_id)}</span>${note}</div>`;
        }).join("")}`;
        ui.typedCriteriaBox.style.display = "block";
      }

      const evidenceRows = Array.isArray(typedEval.evidence_checklist) ? typedEval.evidence_checklist : [];
      if (evidenceRows.length) {
        const isShortfall = typedEval.overall_status === "shortfall";
        const evidenceTitle = isShortfall ? "보완 필요 서류" : "확인 권장 서류";
        const evidenceDesc = isShortfall
          ? "아래 서류를 준비하시면 등록 요건을 충족할 수 있습니다."
          : "아래 항목은 전문가 확인 시 필요할 수 있는 서류입니다.";
        const _evBorder = isShortfall ? "border-left:3px solid #D32F2F;" : "border-left:3px solid var(--smna-accent-strong,#0078D4);";
        ui.evidenceChecklistBox.innerHTML = `<div style="${_evBorder}padding:12px;border-radius:8px;background:${isShortfall ? "var(--smna-badge-error-bg,#FFEBEE)" : "var(--smna-badge-info-bg,#E3F2FD)"};"><strong style="display:block;margin-bottom:6px;">${evidenceTitle}</strong><small style="color:var(--smna-sub);display:block;margin-bottom:8px;">${evidenceDesc}</small>${evidenceRows.map((row) => {
          const _evStyle = row.reason === "보완 필요" ? "color:#D32F2F;font-weight:600;" : "color:var(--smna-sub);";
          return `<div style="margin:4px 0;display:flex;align-items:flex-start;gap:6px;"><span style="flex-shrink:0;width:18px;text-align:center;">${row.reason === "보완 필요" ? "⚠️" : "📋"}</span><span>${esc(row.label)} <span style="${_evStyle}font-size:12px;">(${esc(row.reason || "확인 필요")})</span></span></div>`;
        }).join("")}</div>`;
        ui.evidenceChecklistBox.style.display = "block";
      }

      const nextRows = Array.isArray(typedEval.next_actions) ? typedEval.next_actions : [];
      if (nextRows.length) {
        const isManualReview = typedEval.overall_status === "manual_review";
        const ctaTitle = isManualReview ? "전문가 검토 안내" : "다음 단계";
        const ctaStyle = isManualReview ? "background:#FFF8E1;border-left:3px solid #FFB800;padding:12px;border-radius:8px;" : "";
        ui.nextActionsBox.innerHTML = `<div style="${ctaStyle}"><strong>${ctaTitle}</strong><br>${nextRows.map((row) => `- ${esc(row)}`).join("<br>")}</div>`;
        ui.nextActionsBox.style.display = "block";
      }
    };

    const renderResult = () => {''',
            1,
        )
    repaired = repaired.replace("'''const renderCandidateFallback", "const renderCandidateFallback")
    repaired = repaired.replace("'''const evaluateTypedCriteriaLocal", "const evaluateTypedCriteriaLocal")
    repaired = repaired.replace("'''const renderStructuredReview", "const renderStructuredReview")
    return repaired


def _scope_embed_css(style_body: str, wrapper_selector: str) -> str:
    def repl(match: re.Match[str]) -> str:
        indent = match.group("indent")
        raw_selector = match.group("selector")
        selectors = []
        for piece in raw_selector.split(","):
            selector = piece.strip()
            if not selector:
                continue
            if selector in {":root", "body"}:
                selectors.append(wrapper_selector)
            elif selector == "*":
                selectors.extend([wrapper_selector, f"{wrapper_selector} *"])
            else:
                selectors.append(f"{wrapper_selector} {selector}")
        deduped = []
        for item in selectors:
            if item not in deduped:
                deduped.append(item)
        return f'{indent}{", ".join(deduped)} {{'

    return re.sub(
        r'(?m)^(?P<indent>\s*)(?P<selector>(?!@)[^\n{}]+?)\s*\{',
        repl,
        style_body,
    )


def _wrap_wordpress_safe_scripts(html: str) -> str:
    pattern = re.compile(r"<script(?P<attrs>[^>]*)\snowprocket(?:=\"\")?[^>]*>(?P<body>.*?)</script>", flags=re.S)

    def repl(match: re.Match[str]) -> str:
        body = str(match.group("body") or "").strip()
        if not body:
            return str(match.group(0) or "")
        encoded = base64.b64encode(body.encode("utf-8")).decode("ascii")
        return (
            "<script nowprocket>"
            "(()=>{"
            f'const encoded="{encoded}";'
            "const bytes=Uint8Array.from(atob(encoded),(ch)=>ch.charCodeAt(0));"
            'const source=new TextDecoder("utf-8").decode(bytes);'
            "(new Function(source))();"
            "})();"
            "</script>"
        )

    return pattern.sub(repl, html)


def _build_wordpress_fragment(full_html: str) -> str:
    wrapper_selector = "#smna-permit-precheck"
    style_blocks = re.findall(r"<style>\s*(.*?)\s*</style>", full_html, flags=re.S)
    scoped_style = "\n\n".join(_scope_embed_css(block, wrapper_selector) for block in style_blocks if block.strip())
    scoped_style = scoped_style.replace(f"{wrapper_selector} @media", "@media")
    body_match = re.search(r"<body>\s*(.*?)\s*</body>", full_html, flags=re.S)
    body_inner = body_match.group(1).strip() if body_match else full_html
    body_inner = body_inner.replace("실��종", "실업종")
    return f"""<section id="smna-permit-precheck" class="smna-permit-embed">
  <style>
{scoped_style}
    {wrapper_selector} {{
      overflow: hidden;
    }}
  </style>
  {body_inner}
  <script nowprocket>
    (() => {{
      const titleNode = document.querySelector(".entry-title, .page-title");
      if (titleNode) titleNode.style.display = "none";
    }})();
  </script>
</section>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI permit pre-check calculator HTML")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG_PATH), help="Path to collected permit industry JSON")
    parser.add_argument("--rules", default=str(DEFAULT_RULES_PATH), help="Path to objective legal rules JSON")
    parser.add_argument("--output", default="output/ai_permit_precheck.html", help="Output HTML file path")
    parser.add_argument("--data-output", default="", help="Optional output path for client bootstrap JSON")
    parser.add_argument("--data-url", default="", help="Optional public JSON URL to fetch bootstrap data from")
    parser.add_argument("--data-encoding", default="", help="Optional external bootstrap encoding (e.g. gzip)")
    parser.add_argument("--fragment", action="store_true", help="Emit WordPress-friendly fragment output")
    parser.add_argument("--title", default="", help="HTML title")
    parser.add_argument("--channel-id", default="")
    # Backward-compatible no-op args so legacy deploy commands do not fail.
    parser.add_argument("--contact-phone", default="")
    parser.add_argument("--openchat-url", default="")
    parser.add_argument("--notice-url", default="")
    parser.add_argument("--consult-endpoint", default="")
    parser.add_argument("--usage-endpoint", default="")
    args = parser.parse_args()

    catalog = _load_catalog(Path(args.catalog).expanduser().resolve())
    rules = _load_rule_catalog(Path(args.rules).expanduser().resolve())
    bootstrap_payload = build_bootstrap_payload(catalog, rules)
    branding = resolve_channel_branding(
        channel_id=str(args.channel_id or "").strip(),
        overrides={
            "contact_phone": str(args.contact_phone or "").strip(),
            "notice_url": str(args.notice_url or "").strip(),
        },
    )
    default_title = f"AI 인허가 사전검토 진단기 | {str(branding.get('brand_name') or 'Partner').strip()}"

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if str(args.data_output or "").strip():
        data_output = Path(args.data_output).expanduser().resolve()
        data_output.parent.mkdir(parents=True, exist_ok=True)
        data_output.write_text(json.dumps(bootstrap_payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"[saved-data] {data_output}")
    output.write_text(
        build_html(
            title=str(args.title or default_title),
            catalog=catalog,
            rule_catalog=rules,
            channel_id=str(args.channel_id or ""),
            contact_phone=str(args.contact_phone or ""),
            notice_url=str(args.notice_url or ""),
            bootstrap_payload=bootstrap_payload,
            data_url=str(args.data_url or ""),
            data_encoding=str(args.data_encoding or ""),
            fragment=bool(args.fragment),
        ),
        encoding="utf-8",
    )
    print(f"[saved] {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
