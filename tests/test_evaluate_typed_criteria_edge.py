"""Edge-case tests for evaluate_typed_criteria.

Covers: empty input, unknown operators, missing input keys, blocking logic,
mapping_confidence thresholds, pending_criteria_lines, deposit_days
calculation, and overall_status decision branches.
"""

from __future__ import annotations

from datetime import date

import pytest

from core_engine.permit_criteria_schema import evaluate_typed_criteria


# ── helper ────────────────────────────────────────────────────────

def _rule(
    typed_criteria: list | None = None,
    mapping_meta: dict | None = None,
    pending_criteria_lines: list | None = None,
    document_templates: list | None = None,
) -> dict:
    """Build a minimal rule dict."""
    return {
        "typed_criteria": typed_criteria or [],
        "mapping_meta": mapping_meta or {},
        "pending_criteria_lines": pending_criteria_lines or [],
        "document_templates": document_templates or [],
    }


def _criterion(
    criterion_id: str = "c1",
    category: str = "capital",
    input_key: str = "capital_eok",
    operator: str = ">=",
    required_value: float = 1.0,
    value_type: str = "number",
    blocking: bool = True,
    **extra: object,
) -> dict:
    return {
        "criterion_id": criterion_id,
        "category": category,
        "input_key": input_key,
        "operator": operator,
        "required_value": required_value,
        "value_type": value_type,
        "blocking": blocking,
        **extra,
    }


# ── empty / null inputs ──────────────────────────────────────────

class TestEmptyInputs:

    def test_empty_typed_criteria_returns_pass(self) -> None:
        result = evaluate_typed_criteria(_rule(), {})
        assert result["overall_status"] == "pass"
        assert result["typed_criteria_total"] == 0
        assert result["blocking_failure_count"] == 0

    def test_none_typed_criteria(self) -> None:
        result = evaluate_typed_criteria(_rule(typed_criteria=None), {})
        assert result["overall_status"] == "pass"
        assert result["typed_criteria_total"] == 0

    def test_empty_inputs_with_criteria(self) -> None:
        """All criteria should be missing_input when inputs is empty."""
        rule = _rule(typed_criteria=[_criterion()])
        result = evaluate_typed_criteria(rule, {})
        assert result["criterion_results"][0]["status"] == "missing_input"

    def test_none_rule_fields(self) -> None:
        """Rule with all None fields should not crash."""
        rule = {
            "typed_criteria": None,
            "mapping_meta": None,
            "pending_criteria_lines": None,
            "document_templates": None,
        }
        result = evaluate_typed_criteria(rule, {})
        assert isinstance(result, dict)
        assert result["overall_status"] == "pass"


# ── operator edge cases ──────────────────────────────────────────

class TestOperators:

    def test_gte_pass(self) -> None:
        rule = _rule(typed_criteria=[_criterion(operator=">=", required_value=1.0)])
        result = evaluate_typed_criteria(rule, {"capital_eok": 1.5})
        assert result["criterion_results"][0]["ok"] is True

    def test_gte_exact_boundary(self) -> None:
        rule = _rule(typed_criteria=[_criterion(operator=">=", required_value=1.0)])
        result = evaluate_typed_criteria(rule, {"capital_eok": 1.0})
        assert result["criterion_results"][0]["ok"] is True

    def test_gte_fail(self) -> None:
        rule = _rule(typed_criteria=[_criterion(operator=">=", required_value=1.5)])
        result = evaluate_typed_criteria(rule, {"capital_eok": 1.0})
        assert result["criterion_results"][0]["ok"] is False

    def test_boolean_true_pass(self) -> None:
        rule = _rule(typed_criteria=[
            _criterion(
                input_key="has_office",
                operator="==",
                required_value=True,
                value_type="boolean",
            ),
        ])
        result = evaluate_typed_criteria(rule, {"has_office": True})
        assert result["criterion_results"][0]["ok"] is True

    def test_boolean_false_fail(self) -> None:
        rule = _rule(typed_criteria=[
            _criterion(
                input_key="has_office",
                operator="==",
                required_value=True,
                value_type="boolean",
            ),
        ])
        result = evaluate_typed_criteria(rule, {"has_office": False})
        assert result["criterion_results"][0]["ok"] is False


# ── blocking / non-blocking ──────────────────────────────────────

class TestBlockingLogic:

    def test_blocking_failure_sets_shortfall(self) -> None:
        rule = _rule(typed_criteria=[
            _criterion(blocking=True, required_value=5.0),
        ])
        result = evaluate_typed_criteria(rule, {"capital_eok": 1.0})
        assert result["overall_status"] == "shortfall"
        assert result["blocking_failure_count"] == 1

    def test_nonblocking_failure_does_not_block(self) -> None:
        rule = _rule(typed_criteria=[
            _criterion(blocking=False, required_value=5.0),
        ])
        result = evaluate_typed_criteria(rule, {"capital_eok": 1.0})
        assert result["overall_status"] == "pass"
        assert result["blocking_failure_count"] == 0

    def test_mixed_blocking_nonblocking(self) -> None:
        rule = _rule(typed_criteria=[
            _criterion(criterion_id="c1", blocking=True, required_value=1.0),
            _criterion(criterion_id="c2", blocking=False, required_value=100.0),
        ])
        result = evaluate_typed_criteria(rule, {"capital_eok": 2.0})
        assert result["overall_status"] == "pass"  # c1 passes, c2 fails non-blocking
        assert result["blocking_failure_count"] == 0

    def test_missing_blocking_input_causes_manual_review(self) -> None:
        rule = _rule(typed_criteria=[
            _criterion(input_key="nonexistent_key", blocking=True),
        ])
        result = evaluate_typed_criteria(rule, {})
        assert result["overall_status"] in {"manual_review", "shortfall"}
        assert result["unknown_blocking_count"] >= 1 or result["blocking_failure_count"] >= 1


# ── mapping_confidence / coverage_status ─────────────────────────

class TestMappingConfidence:

    def test_low_confidence_forces_manual_review(self) -> None:
        rule = _rule(
            typed_criteria=[_criterion(required_value=1.0)],
            mapping_meta={"mapping_confidence": 0.5},
        )
        result = evaluate_typed_criteria(rule, {"capital_eok": 2.0})
        assert result["manual_review_required"] is True
        assert result["overall_status"] == "manual_review"

    def test_high_confidence_allows_pass(self) -> None:
        rule = _rule(
            typed_criteria=[_criterion(required_value=1.0)],
            mapping_meta={"mapping_confidence": 0.95, "coverage_status": "full"},
        )
        result = evaluate_typed_criteria(rule, {"capital_eok": 2.0})
        assert result["overall_status"] == "pass"

    def test_pending_criteria_forces_manual_review(self) -> None:
        rule = _rule(
            typed_criteria=[_criterion(required_value=1.0)],
            pending_criteria_lines=[{"raw": "추가 요건"}],
        )
        result = evaluate_typed_criteria(rule, {"capital_eok": 2.0})
        assert result["manual_review_required"] is True
        assert result["pending_criteria_count"] == 1

    def test_coverage_partial_forces_manual_review(self) -> None:
        rule = _rule(
            typed_criteria=[_criterion(required_value=1.0)],
            mapping_meta={"coverage_status": "partial", "mapping_confidence": 0.9},
        )
        result = evaluate_typed_criteria(rule, {"capital_eok": 2.0})
        assert result["overall_status"] == "manual_review"


# ── deposit_days / expected_date ─────────────────────────────────

class TestDepositDays:

    def test_deposit_days_positive(self) -> None:
        rule = _rule(typed_criteria=[_criterion(required_value=1.0)])
        result = evaluate_typed_criteria(
            rule,
            {"capital_eok": 2.0, "deposit_days": 30},
            base_date=date(2026, 1, 1),
        )
        assert result["expected_diagnosis_date"] == "2026-01-31"

    def test_deposit_days_zero(self) -> None:
        rule = _rule(typed_criteria=[_criterion(required_value=1.0)])
        result = evaluate_typed_criteria(
            rule,
            {"capital_eok": 2.0, "deposit_days": 0},
            base_date=date(2026, 1, 1),
        )
        assert result["expected_diagnosis_date"] == ""

    def test_deposit_days_missing(self) -> None:
        rule = _rule(typed_criteria=[_criterion(required_value=1.0)])
        result = evaluate_typed_criteria(rule, {"capital_eok": 2.0})
        assert result["expected_diagnosis_date"] == ""


# ── evidence_checklist / doc_id ──────────────────────────────────

class TestEvidenceChecklist:

    def test_failing_criterion_generates_evidence(self) -> None:
        rule = _rule(typed_criteria=[
            _criterion(required_value=5.0, evidence_types=["재무제표", "잔고증명"]),
        ])
        result = evaluate_typed_criteria(rule, {"capital_eok": 1.0})
        assert len(result["evidence_checklist"]) == 2
        assert result["evidence_checklist"][0]["label"] == "재무제표"
        assert result["evidence_checklist"][1]["label"] == "잔고증명"

    def test_passing_criterion_no_evidence(self) -> None:
        rule = _rule(typed_criteria=[_criterion(required_value=1.0)])
        result = evaluate_typed_criteria(rule, {"capital_eok": 5.0})
        assert len(result["evidence_checklist"]) == 0

    def test_missing_evidence_types_gets_default(self) -> None:
        rule = _rule(typed_criteria=[
            _criterion(required_value=5.0),
        ])
        result = evaluate_typed_criteria(rule, {"capital_eok": 1.0})
        assert len(result["evidence_checklist"]) >= 1
        assert "확인 필요" in result["evidence_checklist"][0]["label"]


# ── next_actions ─────────────────────────────────────────────────

class TestNextActions:

    def test_shortfall_next_action(self) -> None:
        rule = _rule(typed_criteria=[_criterion(required_value=5.0)])
        result = evaluate_typed_criteria(rule, {"capital_eok": 1.0})
        assert any("충족" in a for a in result["next_actions"])

    def test_pass_no_next_actions(self) -> None:
        rule = _rule(
            typed_criteria=[_criterion(required_value=1.0)],
            mapping_meta={"coverage_status": "full"},
        )
        result = evaluate_typed_criteria(rule, {"capital_eok": 5.0})
        assert len(result["next_actions"]) == 0

    def test_pending_has_expert_review_action(self) -> None:
        rule = _rule(
            typed_criteria=[_criterion(required_value=1.0)],
            pending_criteria_lines=[{"raw": "추가 요건"}],
        )
        result = evaluate_typed_criteria(rule, {"capital_eok": 5.0})
        assert any("전문가" in a for a in result["next_actions"])
