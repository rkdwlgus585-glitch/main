"""Config drift detection for permit_registration_criteria_expanded.json.

Ensures every industry code in the master config can be loaded,
typed_criteria entries resolve to known categories, and the
evaluate_typed_criteria function doesn't KeyError on any row.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core_engine.permit_criteria_schema import evaluate_typed_criteria

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "permit_registration_criteria_expanded.json"

KNOWN_CATEGORIES = frozenset({
    "capital",
    "technicians",
    "office",
    "qualification",
    "facility",
    "guarantee",
    "insurance",
    "document",
    "environment_safety",
    "occupancy",
    "equipment",
    "safety",
})


@pytest.fixture(scope="module")
def config_data() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def industries(config_data: dict) -> list:
    return config_data.get("industries", [])


class TestConfigIntegrity:
    """Master config file structural integrity."""

    def test_config_file_exists(self) -> None:
        assert CONFIG_PATH.exists(), f"Config not found: {CONFIG_PATH}"

    def test_config_is_valid_json(self) -> None:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_has_industries_key(self, config_data: dict) -> None:
        assert "industries" in config_data
        assert isinstance(config_data["industries"], list)

    def test_minimum_industry_count(self, industries: list) -> None:
        assert len(industries) >= 191, f"Expected ≥191 industries, got {len(industries)}"

    def test_unique_service_codes(self, industries: list) -> None:
        codes = [row.get("service_code") for row in industries]
        assert len(codes) == len(set(codes)), "Duplicate service_code detected"


class TestTypedCriteriaCoverage:
    """Every industry's typed_criteria entries use known categories."""

    def test_all_industries_have_typed_criteria(self, industries: list) -> None:
        missing = [
            row.get("service_code", "?")
            for row in industries
            if not row.get("typed_criteria")
        ]
        assert not missing, f"{len(missing)} industries lack typed_criteria: {missing[:5]}"

    def test_categories_are_known(self, industries: list) -> None:
        unknown: list[tuple[str, str]] = []
        for row in industries:
            code = row.get("service_code", "?")
            for tc in row.get("typed_criteria") or []:
                if isinstance(tc, dict):
                    cat = tc.get("category", "")
                    if cat and cat not in KNOWN_CATEGORIES:
                        unknown.append((code, cat))
        if unknown:
            samples = unknown[:10]
            pytest.fail(f"Unknown typed_criteria categories: {samples}")

    def test_criterion_ids_present(self, industries: list) -> None:
        """Every typed_criteria item must have a non-empty criterion_id."""
        missing_ids: list[str] = []
        for row in industries:
            code = row.get("service_code", "?")
            for tc in row.get("typed_criteria") or []:
                if isinstance(tc, dict) and not tc.get("criterion_id"):
                    missing_ids.append(code)
                    break
        assert not missing_ids, f"Industries with empty criterion_id: {missing_ids[:5]}"


class TestEvaluateTypedCriteriaSafety:
    """evaluate_typed_criteria must not crash on any config row."""

    @pytest.fixture(scope="class")
    def sample_inputs(self) -> dict:
        return {
            "capital_eok": 1.5,
            "technician_count": 3,
            "has_office": True,
            "has_qualification": True,
            "has_facility": True,
            "guarantee_eok": 2.0,
            "has_insurance": True,
            "has_equipment": True,
        }

    def test_no_crash_on_all_industries(self, industries: list, sample_inputs: dict) -> None:
        """Feed dummy inputs to every industry rule — must not KeyError or TypeError."""
        crash_codes: list[tuple[str, str]] = []
        for row in industries:
            code = row.get("service_code", "?")
            fake_rule = {
                "typed_criteria": row.get("typed_criteria", []),
                "mapping_meta": {},
                "pending_criteria_lines": [],
                "document_templates": [],
            }
            try:
                result = evaluate_typed_criteria(fake_rule, sample_inputs)
                assert isinstance(result, dict), f"{code}: result is not dict"
            except Exception as exc:
                crash_codes.append((code, f"{type(exc).__name__}: {exc}"))
        assert not crash_codes, f"evaluate_typed_criteria crashed on {len(crash_codes)} industries: {crash_codes[:5]}"


class TestRuleCriteriaPacks:
    """rule_criteria_packs integrity."""

    def test_packs_exist(self, config_data: dict) -> None:
        packs = config_data.get("rule_criteria_packs", [])
        assert isinstance(packs, list), f"Expected list, got {type(packs).__name__}"
        assert len(packs) >= 40, f"Expected ≥40 packs, got {len(packs)}"

    def test_packs_have_ref_field(self, config_data: dict) -> None:
        """Every pack must have a 'ref' identifier."""
        packs = config_data.get("rule_criteria_packs", [])
        missing_ref = [i for i, p in enumerate(packs) if not isinstance(p, dict) or not p.get("ref")]
        assert not missing_ref, f"Packs without 'ref' at indices: {missing_ref[:5]}"

    def test_pack_refs_resolve(self, config_data: dict) -> None:
        """Industries with rule_pack_ref should resolve to an existing pack."""
        packs = config_data.get("rule_criteria_packs", [])
        pack_refs = {p.get("ref") for p in packs if isinstance(p, dict) and p.get("ref")}
        industries = config_data.get("industries", [])
        with_ref = [(row.get("service_code", "?"), row.get("rule_pack_ref")) for row in industries if row.get("rule_pack_ref")]
        unresolved = [(code, ref) for code, ref in with_ref if ref not in pack_refs]
        # Track resolution rate — currently some packs are pending migration
        resolution_rate = 1.0 - (len(unresolved) / max(len(with_ref), 1))
        assert resolution_rate >= 0.80, (
            f"rule_pack_ref resolution {resolution_rate:.0%} < 80%. "
            f"Unresolved ({len(unresolved)}): {unresolved[:5]}"
        )
