#!/usr/bin/env python3
"""Enrich permit_registration_criteria_expanded.json with auto-generated typed_criteria.

For industries that lack typed_criteria but have `other_components` in their
registration_requirement_profile, this script generates typed_criteria entries
based on a deterministic mapping from other_components → criterion templates.

Usage:
    python scripts/enrich_permit_typed_criteria.py [--dry-run]

The script is idempotent: running it multiple times will not duplicate criteria.
Auto-generated criteria have criterion_id ending with `.auto` for easy tracking.
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "config" / "permit_registration_criteria_expanded.json"

# ── Mapping: other_component → typed_criteria template ─────────────────────
# These mirror _PENDING_CRITERIA_TEMPLATES in permit_diagnosis_calculator.py
# but are keyed by `other_components` values (not pending_criteria_lines categories).
COMPONENT_TO_CRITERIA = {
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
    "facility_equipment": {
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
    "equipment": {
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
    "safety_environment": {
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
    "guarantee": {
        "criterion_id": "guarantee.secured.auto",
        "category": "guarantee",
        "label": "보증금·이행보증 확인",
        "input_key": "guarantee_secured",
        "value_type": "boolean",
        "operator": "==",
        "required_value": True,
        "blocking": False,
        "evidence_types": ["보증보험 증권", "이행보증서", "보증금 납부 영수증"],
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
    "deposit": {
        # deposit alone doesn't warrant a separate UI checkbox;
        # covered by facility_secured (장비·설비에 포함)
        "criterion_id": "facility.secured.auto",
        "category": "facility",
        "label": "시설·장비·보관공간 확인",
        "input_key": "facility_secured",
        "value_type": "boolean",
        "operator": "==",
        "required_value": True,
        "blocking": False,
        "evidence_types": ["시설 보유 증빙", "보증금 납부 증빙"],
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


def generate_typed_criteria(other_components: list, legal_basis_title: str = "") -> list:
    """Generate typed_criteria from other_components, deduplicating by criterion_id."""
    criteria_by_id = {}
    for comp in other_components:
        template = COMPONENT_TO_CRITERIA.get(comp)
        if not template:
            continue
        cid = template["criterion_id"]
        if cid in criteria_by_id:
            # Merge evidence_types
            existing = criteria_by_id[cid]
            existing_ev = set(existing.get("evidence_types", []))
            for ev in template.get("evidence_types", []):
                if ev not in existing_ev:
                    existing["evidence_types"].append(ev)
                    existing_ev.add(ev)
            continue
        row = dict(template)
        if legal_basis_title:
            row["basis_refs"] = [legal_basis_title]
        row["note"] = f"other_components 기반 자동 생성 ({comp})"
        criteria_by_id[cid] = row
    return list(criteria_by_id.values())


def main():
    parser = argparse.ArgumentParser(description="Enrich permit data with typed_criteria")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing")
    args = parser.parse_args()

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    industries = data["industries"]
    enriched_count = 0
    skipped_already = 0
    skipped_no_components = 0

    for ind in industries:
        # Skip if already has typed_criteria
        existing_tc = ind.get("typed_criteria", [])
        if existing_tc:
            skipped_already += 1
            continue

        profile = ind.get("registration_requirement_profile", {})
        other_components = profile.get("other_components", [])

        # Get legal basis title for basis_refs
        legal_basis_title = str(ind.get("legal_basis_title", "") or "").strip()

        if not other_components:
            # Fallback: industries with no other_components get a minimal
            # document_ready criterion so they still appear in the typed evaluation
            generated = [
                {
                    "criterion_id": "document.ready.auto",
                    "category": "document",
                    "label": "필수 신고·등록·서류 준비",
                    "input_key": "document_ready",
                    "value_type": "boolean",
                    "operator": "==",
                    "required_value": True,
                    "blocking": False,
                    "evidence_types": ["신고증", "등록증", "신청서"],
                    "basis_refs": [legal_basis_title] if legal_basis_title else [],
                    "note": "기본 서류 제출 요건 (other_components 미지정)",
                }
            ]
            ind["typed_criteria"] = generated
            enriched_count += 1
            continue

        generated = generate_typed_criteria(other_components, legal_basis_title)
        if generated:
            ind["typed_criteria"] = generated
            enriched_count += 1

    total = len(industries)
    with_tc_after = sum(1 for ind in industries if ind.get("typed_criteria"))

    print(f"=== Permit typed_criteria Enrichment ===")
    print(f"Total industries: {total}")
    print(f"Already had typed_criteria: {skipped_already}")
    print(f"No other_components: {skipped_no_components}")
    print(f"Enriched: {enriched_count}")
    print(f"Coverage: {skipped_already}/{total} → {with_tc_after}/{total} ({with_tc_after/total*100:.1f}%)")

    if args.dry_run:
        print("\n[DRY RUN] No file written.")
        return

    # Update metadata
    data["enrichment_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    data["enrichment_stats"] = {
        "total": total,
        "pre_existing": skipped_already,
        "auto_generated": enriched_count,
        "no_components": skipped_no_components,
        "coverage_pct": round(with_tc_after / total * 100, 1),
    }

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Written to {DATA_PATH}")
    print(f"  File size: {DATA_PATH.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
