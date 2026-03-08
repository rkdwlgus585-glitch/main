#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_SPLIT_EXPERIMENT = LOG_DIR / "yangdo_exact_pool_split_experiment_latest.json"
DEFAULT_UNLOCK_EXPERIMENT = LOG_DIR / "yangdo_same_combo_unlock_experiment_latest.json"
DEFAULT_SECTOR_AUDIT = LOG_DIR / "yangdo_sector_price_audit_latest.json"
DEFAULT_JSON = LOG_DIR / "yangdo_alias_catalog_audit_latest.json"
DEFAULT_MD = LOG_DIR / "yangdo_alias_catalog_audit_latest.md"

for candidate in (ROOT, Path(__file__).resolve().parent):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import yangdo_blackbox_api


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _find_sector_row(rows: Iterable[Dict[str, Any]], sector: str) -> Dict[str, Any]:
    for row in rows:
        if str(row.get("sector") or "") == sector:
            return row
    return {}


def _target_sectors(split_experiment: Dict[str, Any], unlock_experiment: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for row in split_experiment.get("sector_candidates") or []:
        if str(row.get("decision") or "") == "alias_or_catalog_first":
            sector = str(row.get("sector") or "").strip()
            if sector and sector not in out:
                out.append(sector)
    for row in unlock_experiment.get("sector_results") or []:
        if str(row.get("decision") or "") == "alias_or_catalog_first":
            sector = str(row.get("sector") or "").strip()
            if sector and sector not in out:
                out.append(sector)
    return out


def _token_set(record: Dict[str, Any]) -> Set[str]:
    return {str(token or "").strip() for token in list(record.get("license_tokens") or []) if str(token or "").strip()}


def _token_inventory(records: Iterable[Dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for record in records:
        if not record.get("current_price_eok"):
            continue
        for token in _token_set(record):
            counter[token] += 1
    return counter


def _related_tokens(inventory: Counter[str], aliases: Set[str]) -> List[Dict[str, Any]]:
    roots = {alias[:2] for alias in aliases if len(alias) >= 2}
    rows: List[Dict[str, Any]] = []
    for token, count in inventory.items():
        if token in aliases:
            continue
        if any(root and root in token for root in roots):
            rows.append({"token": token, "count": int(count)})
    rows.sort(key=lambda item: (-int(item["count"]), str(item["token"])))
    return rows[:8]


def _bundle_combos(records: Iterable[Dict[str, Any]], aliases: Set[str]) -> List[Dict[str, Any]]:
    combos: Counter[str] = Counter()
    for record in records:
        tokens = _token_set(record)
        if not (tokens & aliases):
            continue
        combo_key = " + ".join(sorted(tokens))
        combos[combo_key] += 1
    return [{"combo": combo, "count": count} for combo, count in combos.most_common(8)]


def _decision(*, alias_present: bool, exact_single_count: int, partial_count: int, related_token_count: int) -> str:
    if not alias_present and related_token_count > 0:
        return "canonical_alias_candidate"
    if alias_present and exact_single_count == 0 and partial_count > 0:
        return "bundle_only_market_structure"
    if not alias_present and related_token_count == 0:
        return "taxonomy_gap"
    if alias_present and exact_single_count > 0:
        return "not_alias_problem"
    return "monitor"


def _proposed_action(decision: str) -> str:
    mapping = {
        "canonical_alias_candidate": "관련 토큰을 canonical sector alias로 묶는 매핑 실험을 먼저 수행한다.",
        "bundle_only_market_structure": "alias 수정 대신 단일 exact 부재를 market structure로 분리하고, 번들 전용 설명/정책으로 다룬다.",
        "taxonomy_gap": "데이터 유입 또는 카탈로그 자체가 비어 있는지 먼저 점검한다.",
        "not_alias_problem": "alias 문제는 아니므로 가격/cohort 실험으로 다시 되돌린다.",
        "monitor": "추가 조치 없이 drift만 감시한다.",
    }
    return mapping.get(decision, "monitor")


def build_report(*, split_experiment: Dict[str, Any], unlock_experiment: Dict[str, Any], sector_audit: Dict[str, Any]) -> Dict[str, Any]:
    estimator = yangdo_blackbox_api.YangdoBlackboxEstimator()
    estimator.refresh()
    records, _token_index, _meta = estimator._snapshot()
    inventory = _token_inventory(records)
    sector_rows = [row for row in sector_audit.get("sectors") or [] if isinstance(row, dict)]

    out_rows: List[Dict[str, Any]] = []
    for sector in _target_sectors(split_experiment, unlock_experiment):
        sector_row = _find_sector_row(sector_rows, sector)
        aliases = {sector}
        for item in sector_row.get("aliases") or []:
            text = str(item or "").strip()
            if text:
                aliases.add(text)
        alias_present = any(alias in inventory for alias in aliases)
        exact_single_count = 0
        partial_count = 0
        for record in records:
            tokens = _token_set(record)
            if not (tokens & aliases):
                continue
            if len(tokens) == 1:
                exact_single_count += 1
            elif len(tokens) > 1:
                partial_count += 1
        related = _related_tokens(inventory, aliases)
        decision = _decision(
            alias_present=alias_present,
            exact_single_count=exact_single_count,
            partial_count=partial_count,
            related_token_count=len(related),
        )
        out_rows.append(
            {
                "sector": sector,
                "aliases": sorted(aliases),
                "alias_present_in_inventory": alias_present,
                "exact_single_count": exact_single_count,
                "partial_combo_count": partial_count,
                "related_tokens": related,
                "top_bundle_combos": _bundle_combos(records, aliases),
                "decision": decision,
                "proposed_action": _proposed_action(decision),
            }
        )

    return {
        "generated_at": _now_str(),
        "packet_id": "yangdo_alias_catalog_audit_latest",
        "summary": {
            "target_sector_count": len(out_rows),
            "decisions": {str(row.get("sector") or ""): str(row.get("decision") or "") for row in out_rows},
        },
        "sector_results": out_rows,
        "next_actions": [
            "canonical_alias_candidate는 alias merge packet으로 분리한다.",
            "bundle_only_market_structure는 엔진 패치보다 번들 전용 설명과 정책으로 다룬다.",
            "taxonomy_gap는 데이터 유입/카탈로그 점검으로 보낸다.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# Yangdo Alias Catalog Audit",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        "",
        "## Sector Results",
    ]
    for row in payload.get("sector_results") or []:
        lines.append(
            "- {sector}: decision={decision}, alias_present={alias_present}, exact_single={exact_single}, partial={partial}".format(
                sector=row.get("sector"),
                decision=row.get("decision"),
                alias_present=row.get("alias_present_in_inventory"),
                exact_single=row.get("exact_single_count"),
                partial=row.get("partial_combo_count"),
            )
        )
    lines.extend(["", "## Next Actions"])
    for item in payload.get("next_actions") or []:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate alias/catalog audit for sectors flagged as alias-first.")
    parser.add_argument("--split-experiment", type=Path, default=DEFAULT_SPLIT_EXPERIMENT)
    parser.add_argument("--unlock-experiment", type=Path, default=DEFAULT_UNLOCK_EXPERIMENT)
    parser.add_argument("--sector-audit", type=Path, default=DEFAULT_SECTOR_AUDIT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_report(
        split_experiment=_load_json(args.split_experiment),
        unlock_experiment=_load_json(args.unlock_experiment),
        sector_audit=_load_json(args.sector_audit),
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
