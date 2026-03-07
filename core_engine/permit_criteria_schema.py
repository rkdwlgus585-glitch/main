from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        out = float(value)
    except Exception:
        return None
    if out != out:
        return None
    return out


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(float(value))
    except Exception:
        return None


def _to_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    txt = str(value).strip().lower()
    if txt in {"1", "true", "yes", "on", "y"}:
        return True
    if txt in {"0", "false", "no", "off", "n"}:
        return False
    return None


def _safe_list(values: Any) -> List[Any]:
    if isinstance(values, list):
        return list(values)
    if values is None:
        return []
    return [values]


def _resolve_input(inputs: Dict[str, Any], key: str) -> Any:
    if not key:
        return None
    if key in inputs:
        return inputs.get(key)
    aliases = {
        "capital_eok": ["capital_eok", "current_capital_eok"],
        "technicians": ["technicians", "technicians_count", "current_technicians"],
        "technicians_count": ["technicians_count", "technicians", "current_technicians"],
        "equipment_count": ["equipment_count", "current_equipment_count"],
        "deposit_days": ["deposit_days", "current_deposit_days"],
        "office_secured": ["office_secured", "current_office_secured"],
        "facility_secured": ["facility_secured", "current_facility_secured"],
        "guarantee_secured": ["guarantee_secured", "current_guarantee_secured"],
        "insurance_secured": ["insurance_secured", "current_insurance_secured"],
        "qualification_secured": ["qualification_secured", "current_qualification_secured"],
        "document_ready": ["document_ready", "current_document_ready"],
        "safety_secured": ["safety_secured", "current_safety_secured"],
        "qualification_count": ["qualification_count", "current_qualification_count"],
    }
    for alias in aliases.get(key, []):
        if alias in inputs:
            return inputs.get(alias)
    return None


def _normalize_criterion(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    criterion_id = str(raw.get("criterion_id") or "").strip()
    input_key = str(raw.get("input_key") or "").strip()
    operator = str(raw.get("operator") or "").strip() or ">="
    if not criterion_id or not input_key:
        return None
    return {
        "criterion_id": criterion_id,
        "category": str(raw.get("category") or "").strip(),
        "label": str(raw.get("label") or criterion_id).strip(),
        "input_key": input_key,
        "value_type": str(raw.get("value_type") or "").strip() or "number",
        "operator": operator,
        "required_value": raw.get("required_value"),
        "unit": str(raw.get("unit") or "").strip(),
        "blocking": bool(raw.get("blocking", True)),
        "evidence_types": [str(x).strip() for x in _safe_list(raw.get("evidence_types")) if str(x).strip()],
        "basis_refs": [str(x).strip() for x in _safe_list(raw.get("basis_refs")) if str(x).strip()],
    }


def _coerce_value(value: Any, value_type: str) -> Any:
    vt = str(value_type or "").strip().lower()
    if vt in {"int", "integer"}:
        return _to_int(value)
    if vt in {"bool", "boolean"}:
        return _to_bool(value)
    if vt in {"string", "text"}:
        if value is None:
            return None
        return str(value).strip()
    if vt in {"list", "array"}:
        if value is None:
            return None
        if isinstance(value, list):
            return value
        return [value]
    return _to_float(value)


def _evaluate_operator(current_value: Any, required_value: Any, operator: str, value_type: str) -> Dict[str, Any]:
    current = _coerce_value(current_value, value_type)
    required = _coerce_value(required_value, value_type)
    op = str(operator or "").strip() or ">="
    status = "missing_input" if current is None else "pass"
    ok = None
    gap = None

    if current is None:
        return {
            "status": status,
            "ok": None,
            "current_value": None,
            "required_value": required,
            "gap": None,
        }

    if op == ">=":
        ok = current >= required
        status = "pass" if ok else "fail"
        if isinstance(current, (int, float)) and isinstance(required, (int, float)):
            gap = max(0, required - current)
    elif op == "<=":
        ok = current <= required
        status = "pass" if ok else "fail"
        if isinstance(current, (int, float)) and isinstance(required, (int, float)):
            gap = max(0, current - required)
    elif op == "==":
        ok = current == required
        status = "pass" if ok else "fail"
    elif op == "!=":
        ok = current != required
        status = "pass" if ok else "fail"
    elif op == "contains":
        current_set = set(_safe_list(current))
        req_set = set(_safe_list(required))
        ok = bool(req_set) and req_set.issubset(current_set)
        status = "pass" if ok else "fail"
    elif op == "in":
        ok = current in set(_safe_list(required))
        status = "pass" if ok else "fail"
    elif op == "truthy":
        ok = bool(current)
        status = "pass" if ok else "fail"
    else:
        ok = current == required
        status = "pass" if ok else "fail"

    return {
        "status": status,
        "ok": bool(ok),
        "current_value": current,
        "required_value": required,
        "gap": gap,
    }


def evaluate_typed_criteria(rule: Dict[str, Any], inputs: Dict[str, Any], *, base_date: Optional[date] = None) -> Dict[str, Any]:
    typed = []
    for item in _safe_list(rule.get("typed_criteria")):
        normalized = _normalize_criterion(item)
        if normalized is not None:
            typed.append(normalized)

    mapping_meta = dict(rule.get("mapping_meta") or {})
    pending_lines = [x for x in _safe_list(rule.get("pending_criteria_lines")) if isinstance(x, dict)]
    doc_templates = [x for x in _safe_list(rule.get("document_templates")) if isinstance(x, dict)]

    criterion_results: List[Dict[str, Any]] = []
    evidence_checklist: List[Dict[str, Any]] = []
    blocking_failure_count = 0
    unknown_blocking_count = 0

    doc_map = {}
    for doc in doc_templates:
        doc_id = str(doc.get("doc_id") or "").strip()
        if doc_id:
            doc_map[doc_id] = doc

    for criterion in typed:
        current_value = _resolve_input(inputs, criterion["input_key"])
        evaluated = _evaluate_operator(
            current_value=current_value,
            required_value=criterion.get("required_value"),
            operator=criterion.get("operator", ">="),
            value_type=criterion.get("value_type", "number"),
        )
        result = {
            "criterion_id": criterion["criterion_id"],
            "category": criterion.get("category", ""),
            "label": criterion.get("label", criterion["criterion_id"]),
            "input_key": criterion["input_key"],
            "status": evaluated["status"],
            "ok": evaluated["ok"],
            "gap": evaluated["gap"],
            "current_value": evaluated["current_value"],
            "required_value": evaluated["required_value"],
            "unit": criterion.get("unit", ""),
            "blocking": bool(criterion.get("blocking", True)),
            "basis_refs": list(criterion.get("basis_refs") or []),
            "evidence_types": list(criterion.get("evidence_types") or []),
        }
        criterion_results.append(result)

        if result["blocking"] and result["status"] == "fail":
            blocking_failure_count += 1
        elif result["blocking"] and result["status"] == "missing_input":
            unknown_blocking_count += 1

        if result["status"] in {"fail", "missing_input"}:
            reason = "기준 미충족" if result["status"] == "fail" else "입력 또는 구조화 미완료"
            evidence_types = list(result.get("evidence_types") or [])
            if not evidence_types:
                evidence_types = ["증빙서류 확인 필요"]
            for idx, label in enumerate(evidence_types, 1):
                evidence_checklist.append(
                    {
                        "doc_id": f"{result['criterion_id']}::{idx}",
                        "label": str(label),
                        "criterion_id": result["criterion_id"],
                        "required": True,
                        "reason": reason,
                        "basis_refs": list(result.get("basis_refs") or []),
                    }
                )

    pending_count = len(pending_lines)
    mapping_confidence = _to_float(mapping_meta.get("mapping_confidence"))
    coverage_status = str(mapping_meta.get("coverage_status") or "").strip() or ("pending" if pending_count else "full")
    manual_review_required = bool(mapping_meta.get("manual_review_required", False))
    if pending_count > 0:
        manual_review_required = True
    if mapping_confidence is not None and mapping_confidence < 0.75:
        manual_review_required = True

    overall_status = "pass"
    if blocking_failure_count > 0:
        overall_status = "shortfall"
    elif unknown_blocking_count > 0 or manual_review_required:
        overall_status = "manual_review"
    elif coverage_status not in {"full", "verified"}:
        overall_status = "manual_review"

    next_actions: List[str] = []
    if blocking_failure_count > 0:
        next_actions.append("부족 등록기준을 우선 충족해야 합니다.")
    if unknown_blocking_count > 0:
        next_actions.append("미입력 또는 구조화 미완료 기준을 상담으로 확인해야 합니다.")
    if pending_count > 0:
        next_actions.append("추가 등록기준 구조화가 완료될 때까지 전문가 검토가 필요합니다.")

    deposit_days = _to_int(inputs.get("deposit_days"))
    expected_date = ""
    if deposit_days is not None and deposit_days > 0:
        baseline = base_date or date.today()
        expected_date = (baseline + timedelta(days=int(deposit_days))).strftime("%Y-%m-%d")

    return {
        "typed_criteria_total": len(typed),
        "criterion_results": criterion_results,
        "evidence_checklist": evidence_checklist,
        "blocking_failure_count": blocking_failure_count,
        "unknown_blocking_count": unknown_blocking_count,
        "pending_criteria_count": pending_count,
        "manual_review_required": bool(manual_review_required),
        "coverage_status": coverage_status,
        "mapping_confidence": mapping_confidence,
        "overall_status": overall_status,
        "next_actions": next_actions,
        "expected_diagnosis_date": expected_date,
    }
