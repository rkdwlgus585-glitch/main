#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_JSON = LOG_DIR / "ai_platform_first_principles_review_latest.json"
DEFAULT_MD = LOG_DIR / "ai_platform_first_principles_review_latest.md"
DEFAULT_DASHBOARD = LOG_DIR / "ai_admin_dashboard_latest.json"
DEFAULT_REGRESSION = LOG_DIR / "yangdo_operational_regression_latest.json"
DEFAULT_BRAINSTORM = LOG_DIR / "ai_platform_next_brainstorm_latest.md"
DEFAULT_GATE_REVIEW = LOG_DIR / "partner_gate_placement_latest.json"
DEFAULT_FALLBACK_SMOKE = LOG_DIR / "wp_surface_lab_fallback_smoke_latest.json"
DEFAULT_PUBLIC_SUMMARY = LOG_DIR / "public_calculator_publish_summary_latest.json"


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            data = json.loads(path.read_text(encoding=encoding))
            return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


def _lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _brainstorm_candidates(lines: List[str]) -> List[str]:
    items: List[str] = []
    in_candidates = False
    for raw in lines:
        text = str(raw or "").rstrip()
        if text.startswith("## Next Candidates"):
            in_candidates = True
            continue
        if in_candidates and text.startswith("## "):
            break
        if in_candidates and text[:2] in {"1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."}:
            items.append(text)
    return items


def _one_line(dashboard: Dict[str, Any]) -> str:
    return str(((dashboard.get("one_line_summary") or {}).get("text")) or "").strip()


def _decision_pack(current_bottleneck: str) -> Dict[str, str]:
    if current_bottleneck == "public-only publish summary missing":
        return {
            "do_now": "Add a compact public-only publish summary that shows public verify status, one-line health, and customer/permit verdicts on one screen.",
            "hold": "Do not add more public deploy branches or extra public checks until the summary exists.",
            "falsification_test": "Run the public post-publish verifier and confirm the summary alone is enough to decide whether customer and permit are both healthy.",
        }
    if current_bottleneck == "fallback smoke visibility policy unresolved":
        return {
            "do_now": "Decide whether fallback smoke stays ops-only or deserves a separate lab-health dashboard.",
            "hold": "Do not surface fallback smoke in the main operator dashboard until that policy is explicit.",
            "falsification_test": "Ask whether any operator used fallback smoke in the last release loop. If not, keep it out of the main dashboard.",
        }
    if current_bottleneck == "summary/checklist drift policy unresolved":
        return {
            "do_now": "Define when public summary and first-principles checklist must be regenerated together so operators never read stale guidance.",
            "hold": "Do not add more summary surfaces until checklist drift is explicitly controlled.",
            "falsification_test": "Change the first-principles checklist and verify that operator-facing summary stays stale unless the chosen sync policy runs.",
        }
    return {
        "do_now": f"Attack the current bottleneck first: {current_bottleneck}.",
        "hold": "Do not add new feature branches until the primary release bottleneck is reduced.",
        "falsification_test": "Define one smoke or regression check that proves the chosen fix is wrong.",
    }


def _fallback_visibility_policy(fallback_smoke: Dict[str, Any]) -> Dict[str, Any]:
    timing = fallback_smoke.get("timing") if isinstance(fallback_smoke.get("timing"), dict) else {}
    total_sec = float(timing.get("total_duration_sec") or 0.0)
    return {
        "visibility": "ops_only",
        "decision": "keep_out_of_main_operator_dashboard",
        "reason": (
            "Fallback smoke validates the WordPress lab/bootstrap path, not the main customer-facing release path. "
            "It is useful for ops and migration diagnostics, but too expensive and too indirect for the main release surface."
        ),
        "total_duration_sec": total_sec,
        "falsification_test": (
            "If any operator needs fallback smoke to approve a normal release, or if production depends on the fallback path, "
            "promote it into a separate lab-health dashboard instead of the main operator hub."
        ),
    }


def build_review_payload() -> Dict[str, Any]:
    dashboard = _read_json(DEFAULT_DASHBOARD)
    regression = _read_json(DEFAULT_REGRESSION)
    gate_review = _read_json(DEFAULT_GATE_REVIEW)
    fallback_smoke = _read_json(DEFAULT_FALLBACK_SMOKE)
    public_summary = _read_json(DEFAULT_PUBLIC_SUMMARY)
    brainstorm_lines = _lines(DEFAULT_BRAINSTORM)
    next_candidates = _brainstorm_candidates(brainstorm_lines)

    one_line = _one_line(dashboard) or "CHECK | dashboard=missing"
    blocking = [str(x) for x in list(regression.get("blocking_issues") or [])]
    permit_integrity_ok = bool(((dashboard.get("permit_integrity") or {}).get("ok", True)))
    partner_api_ok = bool(((dashboard.get("partner_api_contract_smoke") or {}).get("ok")))
    browser_ok = bool(((dashboard.get("browser_smoke") or {}).get("ok")))
    secure_ok = bool(((dashboard.get("secure_stack") or {}).get("ok")))
    artifact_mode = str((((dashboard.get("permit_failure_artifacts") or {}).get("web_access_mode")) or "")).strip() or "local_only"
    gate_recommendation = str(gate_review.get("recommendation") or "").strip() or "unknown"
    gate_share_pct = ((gate_review.get("timing") or {}).get("partner_share_pct")) if isinstance(gate_review.get("timing"), dict) else None
    fallback_smoke_ok = bool(fallback_smoke.get("ok"))
    public_summary_ok = bool(public_summary.get("ok"))
    fallback_policy = _fallback_visibility_policy(fallback_smoke)
    checklist_promoted = isinstance(public_summary.get("release_checklist"), dict) and bool(public_summary.get("release_checklist"))

    current_bottleneck = "partner API smoke placement undecided"
    if gate_recommendation == "keep_in_publish_gate":
        current_bottleneck = "wp_surface_lab fallback smoke missing"
    elif gate_recommendation == "move_to_ops_loop":
        current_bottleneck = "publish gate cost too high"
    elif gate_recommendation == "keep_but_watch_cost":
        current_bottleneck = "partner API smoke cost watch required"

    if not partner_api_ok:
        current_bottleneck = "partner API contract mismatch"
    elif not browser_ok:
        current_bottleneck = "browser smoke unstable"
    elif not secure_ok:
        current_bottleneck = "secure stack drift"
    elif not permit_integrity_ok:
        current_bottleneck = "permit generated HTML integrity"
    elif blocking:
        current_bottleneck = f"regression blocking issue: {blocking[0]}"
    elif artifact_mode != "private_hub_embed":
        current_bottleneck = "failure artifacts still local-only"
    elif not public_summary_ok:
        current_bottleneck = "public-only publish summary missing"
    elif str(fallback_policy.get("visibility") or "") == "undecided":
        current_bottleneck = "fallback smoke visibility policy unresolved"
    elif not checklist_promoted:
        current_bottleneck = "release checklist promotion incomplete"
    else:
        current_bottleneck = "summary/checklist drift policy unresolved"

    prompt_block = """You are not a feature shipper. You are the system owner.
Goal: reduce operational branches, ambiguity, and unreproducible failures.
Think in first principles, not legacy respect.

Decision order:
1. If this feature is deleted, what actually breaks for user, operator, and partner?
2. If nothing breaks, why does it still exist: legacy, fear, duplication, or habit?
3. If it must stay, what is the smallest interface that preserves value?
4. How many manual branches remain for the operator? Remove every branch that reality does not force.
5. What single automated check must block release if this assumption is wrong?
6. Which output directly supports the decision: total value, balance usage, cash due, or confidence?
7. What is the biggest bottleneck right now: code complexity, data quality, deployment flow, explanation UX, artifact access, or release readability?
8. For every proposal, define one falsification test that can prove the idea wrong.

Rules:
- Market decision flow beats legacy implementation details.
- Never mix total transfer value, balance usage, and cash due.
- If public, private, and partner use different rules, treat it as a bug.
- Compress explanations into one chip or one sentence.
- Leave reproducible failure evidence, not only logs.
- Prefer delete, merge, and automate over feature addition.
- End with exactly three outputs: do now, hold, falsification test."""

    musk_questions = [
        "What should be deleted instead of improved?",
        "Which branch exists only because the system is not trusted yet?",
        "If one screen had to decide the release, what would it show?",
        "What value does the customer actually act on, and what is just diagnostic noise?",
        "Which check catches a failure before an operator has to think?",
    ]
    kill_list = [
        "operator-only local paths for critical failure evidence",
        "multi-step publish interpretation that needs log reading",
        "duplicate rule drift across public/private/partner",
        "long explanations without decision value",
    ]
    force_multiplier_bets = [
        "publish summary with one-screen release verdict",
        "first-principles packet embedded in each publish",
        "shared health contract across live, partner, and private surfaces",
        "artifact previews accessible inside the private hub",
    ]
    operator_loop = [
        "Read one-line health and pick one red or weakest yellow item.",
        "Classify it as data, UI, deployment, or observability within 10 minutes.",
        "Change one axis only.",
        "Close the loop with smoke, regression, and publish gate.",
        "Write the next bottleneck before leaving the loop.",
    ]
    release_checklist = _decision_pack(current_bottleneck)

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "packet_ready": True,
            "one_line_health": one_line,
            "blocking_issue_count": len(blocking),
            "current_bottleneck": current_bottleneck,
            "next_experiment_count": len(next_candidates[:5]),
            "critical_question_count": len(musk_questions),
            "gate_recommendation": gate_recommendation,
            "gate_partner_share_pct": gate_share_pct,
            "fallback_smoke_ok": fallback_smoke_ok,
            "fallback_policy_visibility": str(fallback_policy.get("visibility") or ""),
            "artifact_web_access_mode": artifact_mode,
            "public_summary_ok": public_summary_ok,
            "checklist_promoted": bool(checklist_promoted),
        },
        "current_state": {
            "one_line_health": one_line,
            "regression_blocking_issues": blocking,
            "current_bottleneck": current_bottleneck,
        },
        "gate_decision": gate_review,
        "fallback_smoke": fallback_smoke,
        "fallback_visibility_policy": fallback_policy,
        "public_publish_summary": public_summary,
        "first_principles_prompt": prompt_block,
        "musk_style_questions": musk_questions,
        "kill_list": kill_list,
        "force_multiplier_bets": force_multiplier_bets,
        "next_experiments": next_candidates[:5],
        "operator_loop": operator_loop,
        "release_checklist": release_checklist,
        "decision": {
            "primary_focus": current_bottleneck,
            "secondary_focus": "Stabilize release readability before adding more release surface area.",
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    state = payload.get("current_state") if isinstance(payload.get("current_state"), dict) else {}
    gate = payload.get("gate_decision") if isinstance(payload.get("gate_decision"), dict) else {}
    gate_timing = gate.get("timing") if isinstance(gate.get("timing"), dict) else {}
    fallback_smoke = payload.get("fallback_smoke") if isinstance(payload.get("fallback_smoke"), dict) else {}
    fallback_timing = fallback_smoke.get("timing") if isinstance(fallback_smoke.get("timing"), dict) else {}
    public_summary = payload.get("public_publish_summary") if isinstance(payload.get("public_publish_summary"), dict) else {}
    fallback_policy = payload.get("fallback_visibility_policy") if isinstance(payload.get("fallback_visibility_policy"), dict) else {}
    checklist = payload.get("release_checklist") if isinstance(payload.get("release_checklist"), dict) else {}
    lines = [
        "# AI Platform First-Principles Review",
        "",
        f"Updated: {payload.get('generated_at', '')} KST",
        "",
        "## Current State",
        f"- One-line health: `{state.get('one_line_health') or '(missing)'}`",
        f"- Regression blocking issues: `{', '.join(state.get('regression_blocking_issues') or []) or 'none'}`",
        f"- Current bottleneck: `{state.get('current_bottleneck') or '(missing)'}`",
        "",
        "## Gate Decision",
        f"- Recommendation: `{gate.get('recommendation') or '(missing)'}`",
        f"- Decision label: `{gate.get('decision_label') or '(missing)'}`",
        f"- Partner share: `{gate_timing.get('partner_share_pct')}`%",
        f"- Partner duration: `{gate_timing.get('partner_api_contract_smoke_sec')}` sec",
        "",
        "## Fallback Smoke",
        f"- Status: `{fallback_smoke.get('ok')}`",
        f"- Total duration: `{fallback_timing.get('total_duration_sec')}` sec",
        f"- Blocking issues: `{', '.join(fallback_smoke.get('blocking_issues') or []) or 'none'}`",
        f"- Artifact web access: `{summary.get('artifact_web_access_mode') or '(missing)'}`",
        f"- Visibility policy: `{fallback_policy.get('visibility') or '(missing)'}`",
        "",
        "## Public Summary",
        f"- Summary ready: `{summary.get('public_summary_ok')}`",
        f"- Verdict: `{(public_summary.get('one_line_verdict') or '(missing)')}`",
        "",
        "## Release Checklist",
        f"- Do now: {checklist.get('do_now') or '(missing)'}",
        f"- Hold: {checklist.get('hold') or '(missing)'}",
        f"- Falsification test: {checklist.get('falsification_test') or '(missing)'}",
        "",
        "## First-Principles Prompt",
        "```text",
        str(payload.get("first_principles_prompt") or "").rstrip(),
        "```",
        "",
        "## Musk-Style Questions",
    ]
    for item in payload.get("musk_style_questions") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Kill List"])
    for item in payload.get("kill_list") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Force-Multiplier Bets"])
    for item in payload.get("force_multiplier_bets") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Experiments"])
    for item in payload.get("next_experiments") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Operator Loop"])
    for idx, item in enumerate(payload.get("operator_loop") or [], start=1):
        lines.append(f"{idx}. {item}")
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    lines.extend([
        "",
        "## Decision",
        f"- primary_focus: {decision.get('primary_focus') or '(missing)'}",
        f"- secondary_focus: {decision.get('secondary_focus') or '(missing)'}",
        "",
        "## Summary",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- blocking_issue_count: {summary.get('blocking_issue_count')}",
        f"- next_experiment_count: {summary.get('next_experiment_count')}",
        f"- gate_recommendation: {summary.get('gate_recommendation')}",
    ])
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a first-principles review for the SeoulMNA AI platform.")
    parser.add_argument("--json", default=str(DEFAULT_JSON))
    parser.add_argument("--md", default=str(DEFAULT_MD))
    args = parser.parse_args()
    json_path = Path(str(args.json)).resolve()
    md_path = Path(str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_review_payload()
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_path), "md": str(md_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
