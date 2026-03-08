from __future__ import annotations

import argparse
import base64
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MASTER_INPUT = ROOT / "logs" / "permit_master_catalog_latest.json"
DEFAULT_PROVENANCE_INPUT = ROOT / "logs" / "permit_provenance_audit_latest.json"
DEFAULT_FOCUS_INPUT = ROOT / "logs" / "permit_focus_priority_latest.json"
DEFAULT_BACKLOG_INPUT = ROOT / "logs" / "permit_source_upgrade_backlog_latest.json"
DEFAULT_PATENT_INPUT = ROOT / "logs" / "permit_patent_evidence_bundle_latest.json"
DEFAULT_GOLDSET_INPUT = ROOT / "logs" / "permit_family_case_goldset_latest.json"
DEFAULT_RUNTIME_ASSERTIONS_INPUT = ROOT / "logs" / "permit_runtime_case_assertions_latest.json"
DEFAULT_WIDGET_INPUT = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_API_CONTRACT_INPUT = ROOT / "logs" / "api_contract_spec_latest.json"
DEFAULT_CASE_RELEASE_GUARD_INPUT = ROOT / "logs" / "permit_case_release_guard_latest.json"
DEFAULT_REVIEW_CASE_PRESETS_INPUT = ROOT / "logs" / "permit_review_case_presets_latest.json"
DEFAULT_CASE_STORY_SURFACE_INPUT = ROOT / "logs" / "permit_case_story_surface_latest.json"
DEFAULT_PRESET_STORY_GUARD_INPUT = ROOT / "logs" / "permit_preset_story_release_guard_latest.json"
DEFAULT_OPERATOR_DEMO_PACKET_INPUT = ROOT / "logs" / "permit_operator_demo_packet_latest.json"
DEFAULT_RELEASE_BUNDLE_INPUT = ROOT / "logs" / "permit_release_bundle_latest.json"
DEFAULT_UI_INPUT = ROOT / "output" / "ai_permit_precheck.html"
DEFAULT_PROMPT_DOC_INPUT = ROOT / "docs" / "permit_critical_thinking_prompt.md"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_next_action_brainstorm_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_next_action_brainstorm_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit brainstorm input must be a JSON object")
    return payload


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except Exception:
        return 0


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _has_encoding_noise(value: Any) -> bool:
    text = _safe_str(value)
    return bool(text) and "\ufffd" in text


def _expand_runtime_html_text(html: str) -> str:
    text = str(html or "")
    sources = [text]
    for encoded in re.findall(r'const encoded="([^"]+)";', text):
        try:
            decoded = base64.b64decode(str(encoded or "").strip()).decode("utf-8")
        except Exception:
            continue
        if decoded:
            sources.append(decoded)
    return "\n".join(sources)


def _runtime_proof_surface_ready(html: str) -> bool:
    text = _expand_runtime_html_text(html)
    required_markers = (
        'id="proofClaimBox"',
        "const renderProofClaim = (industry) => {",
        "claim_packet_summary",
    )
    return all(marker in text for marker in required_markers)


def _count_encoding_noise(rows: List[Dict[str, Any]]) -> int:
    noisy = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        fields = (
            row.get("service_name"),
            row.get("major_name"),
            row.get("group_name"),
            row.get("law_title"),
            row.get("legal_basis_title"),
        )
        if any(_has_encoding_noise(value) for value in fields):
            noisy += 1
    return noisy


def _runtime_proof_surface_ready(html: str) -> bool:
    text = _expand_runtime_html_text(html)
    required_markers = (
        'id="proofClaimBox"',
        "const renderProofClaim = (industry) => {",
        "claim_packet_summary",
    )
    return all(marker in text for marker in required_markers)


def _runtime_review_preset_surface_ready(html: str) -> bool:
    text = _expand_runtime_html_text(html)
    required_markers = (
        'id="reviewPresetBox"',
        "const renderReviewCasePresets = (industry) => {",
        "data-review-preset-id",
        "const applyReviewCasePreset = (preset) => {",
    )
    return all(marker in text for marker in required_markers)


def _runtime_operator_demo_surface_ready(html: str) -> bool:
    text = _expand_runtime_html_text(html)
    required_markers = (
        'id="operatorDemoBox"',
        "const renderOperatorDemoSurface = (industry) => {",
        "const getOperatorDemoSurface = (row) => (",
        "operator_demo_surface",
    )
    return all(marker in text for marker in required_markers)


def _doc_excerpt(prompt_doc: str, limit: int = 8) -> str:
    lines = [line.rstrip() for line in str(prompt_doc or "").splitlines() if line.strip()]
    return "\n".join(lines[:limit])


def _build_execution_prompt(
    *,
    primary_title: str,
    focus_seed_total: int,
    focus_family_registry_total: int,
    candidate_pack_total: int,
    claim_packet_complete_family_total: int,
    runtime_failed_case_total: int,
) -> str:
    return "\\n".join(
        [
            "You are the improvement owner for the SeoulMNA permit precheck platform.",
            f"The current execution lane is '{primary_title}'.",
            (
                "Current critical counts: "
                f"focus-seed {focus_seed_total}, "
                f"family registry {focus_family_registry_total}, "
                f"candidate pack {candidate_pack_total}, "
                f"claim packet complete family {claim_packet_complete_family_total}, "
                f"runtime failed case {runtime_failed_case_total}"
            ),
            "Pick one bottleneck at a time and prove that it changes real user flow or operator cost.",
            "Do not polish wording only. Tie together legal basis, checklist exposure, manual review branching, and runtime proof.",
            "Output format must stay: bottleneck, evidence, fix, verification, next priority.",
        ]
    )


def _build_parallel_brainstorm_prompt(primary_title: str, parallel_title: str) -> str:
    return "\\n".join(
        [
            f"The active execution lane is '{primary_title}', and the parallel brainstorm lane is '{parallel_title}'.",
            "Brainstorming is not idea collection. It is a filter for the next batch candidate set.",
            "Only keep a candidate if all questions below are answered with evidence.",
            "1. Does it reduce real user input time or operator decision time?",
            "2. Does it lower legal, checklist, manual-review, or partner-contract risk at the same time?",
            "3. Can the current test assets verify it immediately?",
            "4. Does it produce evidence strong enough to change the next batch priority?",
            "Keep only the passed candidates. Hold the rest.",
        ]
    )


def _build_first_principles_prompt(primary_title: str) -> str:
    return "\\n".join(
        [
            f"Do not treat '{primary_title}' as a routine task. Break it back down to first principles.",
            "Separate fact, inference, and presentation layer.",
            "If legal basis, checklist, manual review, or publication contract is missing, treat it as an assumption.",
            "Only keep fixes that improve at least two of input burden, result explainability, and consult conversion with the smallest possible change.",
        ]
    )


def _founder_mode_questions() -> List[str]:
    return [
        "Does this change reduce both user input time and operator decision time?",
        "Does it strengthen at least two of legal basis, checklist quality, manual review branching, and partner contract safety?",
        "Is it hitting the single most expensive bottleneck in this batch?",
        "Can it be verified immediately with the current runtime and test assets?",
    ]


def _apply_item_text_overrides(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    templates: Dict[str, Dict[str, str]] = {
        "focus_seed_source_upgrade": {
            "title": "focus-seed source proof hardening",
            "current_gap": "Seed source proof is not yet locked across public contract, runtime surface, and partner-safe outputs.",
            "why_now": "If source proof is unstable, checklist quality, partner safety, and patent evidence all weaken together.",
            "proposed_next_step": "Lock source proof for the main focus families and add drift checks around the publication surface.",
            "success_metric": "The focus-seed source lane stays green and drift-free.",
        },
        "patent_evidence_bundle": {
            "title": "patent evidence bundle reinforcement",
            "current_gap": "The feature works, but the evidence bundle is not yet as compressed and claim-mapped as it can be.",
            "why_now": "At filing time, claim-to-evidence linkage matters more than implementation volume.",
            "proposed_next_step": "Re-bundle logs, QA, contract artifacts, and UI proof per claim axis.",
            "success_metric": "The attorney handoff has no evidence gaps.",
        },
        "focus_family_registry_hardening": {
            "title": "focus family registry hardening",
            "current_gap": "The focus family registry exists, but the runtime, widget, and handoff surfaces are not yet fully anchored to the same contract.",
            "why_now": "Registry instability directly weakens public checklist quality and manual-review branching.",
            "proposed_next_step": "Treat the focus family registry as a single shared contract across runtime, widget, and handoff.",
            "success_metric": "Registry drift remains at zero.",
        },
        "patent_evidence_bundle_lock": {
            "title": "patent evidence bundle lock",
            "current_gap": "The evidence bundle exists, but release reproducibility is not yet fully enforced.",
            "why_now": "Before filing, reproducibility matters as much as coverage.",
            "proposed_next_step": "Anchor the patent evidence bundle to release artifacts and repeatable generation steps.",
            "success_metric": "The same evidence can be regenerated after release without manual reconstruction.",
        },
        "platform_contract_proof_surface": {
            "title": "platform contract proof surface",
            "current_gap": "The platform, runtime, and service surfaces still need stronger proof that they speak the same publication contract.",
            "why_now": "Contract drift breaks both partner sales and user trust.",
            "proposed_next_step": "Lock the same proof surface across runtime, widget, operator, and handoff artifacts.",
            "success_metric": "The public contract audit stays green.",
        },
        "family_case_goldset": {
            "title": "family case goldset expansion",
            "current_gap": "Representative family cases exist, but exception families are still under-covered.",
            "why_now": "Missing exception families weakens both checklist detail and manual-review confidence.",
            "proposed_next_step": "Add representative and edge families to the goldset.",
            "success_metric": "Goldset family coverage expands measurably.",
        },
        "runtime_proof_disclosure": {
            "title": "runtime proof disclosure",
            "current_gap": "The proof surface exists, but the public-safe disclosure contract can still be tightened.",
            "why_now": "Weak proof disclosure reduces answer explainability at the exact point of user trust formation.",
            "proposed_next_step": "Re-check proof disclosure across summary, detailed, and internal layers.",
            "success_metric": "The runtime proof surface matches the publication contract.",
        },
        "runtime_proof_regression_lock": {
            "title": "runtime proof regression lock",
            "current_gap": "Proof surface regressions are still too easy to introduce with small UI changes.",
            "why_now": "A minor wording or rendering change can break the disclosure contract.",
            "proposed_next_step": "Bind proof-surface rules into tests and release guards.",
            "success_metric": "No proof-surface regressions escape the guardrail.",
        },
        "family_case_runtime_assertions": {
            "title": "family case runtime assertions",
            "current_gap": "Runtime assertions cover core families, but edge and exception families need more depth.",
            "why_now": "Weak edge assertions directly erode manual-review trust.",
            "proposed_next_step": "Extend runtime assertions to more exception and boundary families.",
            "success_metric": "Runtime assertion coverage expands across edge families.",
        },
        "widget_case_parity": {
            "title": "widget/API case parity",
            "current_gap": "Widget and API parity still needs continuous enforcement at the case level.",
            "why_now": "Rental products fail fast when widget and API outputs drift apart.",
            "proposed_next_step": "Tie widget/API parity cases directly into release guards.",
            "success_metric": "The widget/API parity audit remains green.",
        },
        "case_release_guard": {
            "title": "case release guard hardening",
            "current_gap": "The release guard exists, but case-centric gating can still be tighter.",
            "why_now": "The last safe stop before release is the case guard.",
            "proposed_next_step": "Attach more focus-family and edge-case checks directly to the release guard.",
            "success_metric": "Release guard failures remain at zero.",
        },
        "family_case_edge_expansion": {
            "title": "family edge expansion",
            "current_gap": "Boundary and exception family cases are still thinner than the representative set.",
            "why_now": "Weak edge coverage drives unnecessary manual review volume.",
            "proposed_next_step": "Expand edge cases around the focus families.",
            "success_metric": "Edge family coverage increases.",
        },
        "case_release_observability": {
            "title": "case release observability",
            "current_gap": "It is still too hard to read which case surface degraded after a release.",
            "why_now": "Weak observability delays regression detection.",
            "proposed_next_step": "Expose case-release observability more directly in the operations packet.",
            "success_metric": "Case regressions can be spotted immediately after release.",
        },
        "review_case_input_presets": {
            "title": "review case input presets",
            "current_gap": "Input presets exist, but they are not yet fully aligned with service explanation and manual-review flow.",
            "why_now": "Weak presets hurt operator reproducibility and partner demos.",
            "proposed_next_step": "Align review presets with service-copy lanes.",
            "success_metric": "The review preset surface matches the service-copy ladder.",
        },
        "case_story_surface": {
            "title": "case story surface",
            "current_gap": "Case stories exist, but they can explain the move into detailed lanes more clearly.",
            "why_now": "Weak story surfaces weaken upgrade conversion into detailed checklist lanes.",
            "proposed_next_step": "Align case stories across service pages and operator demos.",
            "success_metric": "Case story surfaces and CTA structure read as one flow.",
        },
        "runtime_review_preset_surface": {
            "title": "runtime review preset surface",
            "current_gap": "The runtime preset surface exists, but service-copy and release alignment can be stronger.",
            "why_now": "When runtime and service explanation drift, user expectation drifts with them.",
            "proposed_next_step": "Align the runtime preset surface with service copy and operator demo surfaces.",
            "success_metric": "The runtime preset surface alignment stays green.",
        },
        "story_contract_surface": {
            "title": "story contract surface",
            "current_gap": "Story, contract, and evidence surfaces still need stronger alignment around the same lane ladder.",
            "why_now": "Story/contract drift separates product reality from sales language.",
            "proposed_next_step": "Re-bind story and contract surfaces across widget, API, and handoff artifacts.",
            "success_metric": "The story contract surface audit stays green.",
        },
        "preset_story_release_guard": {
            "title": "preset-story release guard",
            "current_gap": "Preset and story surfaces are still not protected as a single release contract strongly enough.",
            "why_now": "Preset/story consistency directly affects user understanding and operator reproducibility.",
            "proposed_next_step": "Promote preset-story guardrails into a release-bundle requirement.",
            "success_metric": "The preset-story release guard remains green.",
        },
        "operator_demo_packet": {
            "title": "operator demo packet",
            "current_gap": "The operator demo exists, but it still needs stronger linkage to release and contract audits.",
            "why_now": "Weak internal demos reduce QA quality and partner onboarding confidence.",
            "proposed_next_step": "Lock the operator demo packet into release and contract audit chains.",
            "success_metric": "The operator demo packet remains ready.",
        },
        "operator_demo_surface": {
            "title": "operator demo surface",
            "current_gap": "The operator demo surface exists, but it can explain stage differences more clearly.",
            "why_now": "Demo surfaces reduce operator decision cost directly.",
            "proposed_next_step": "Add clearer lane comparisons and next-step language to the operator demo surface.",
            "success_metric": "Operator demo surface readiness remains stable.",
        },
        "partner_demo_surface": {
            "title": "partner demo surface",
            "current_gap": "The partner demo exists, but product-tier differentiation can still be clearer.",
            "why_now": "Blurry partner lanes weaken pricing and upgrade logic.",
            "proposed_next_step": "Reflect lane-specific publication scope more clearly in the partner demo surface.",
            "success_metric": "The partner demo surface matches the rental catalog.",
        },
        "critical_prompt_surface_lock": {
            "title": "critical prompt surface lock",
            "current_gap": "Critical thinking prompts exist, but operators still need a shorter reusable block inside the working surfaces.",
            "why_now": "As iterations increase, prompt accessibility becomes a bottleneck.",
            "proposed_next_step": "Lock the current bottleneck prompt block directly into operator and release surfaces.",
            "success_metric": "Critical prompt blocks are embedded in the operating artifacts.",
        },
        "demo_surface_observability": {
            "title": "demo surface observability",
            "current_gap": "There is still no compact view that shows operator and partner demo readiness together.",
            "why_now": "As surface count grows, observability gaps become regression risk.",
            "proposed_next_step": "Expose a compact demo-surface observability summary in the operations packet.",
            "success_metric": "Demo-surface readiness is visible in one place.",
        },
        "materialize_absorbed_registry": {
            "title": "absorbed registry materialization",
            "current_gap": "Absorbed rows still make family-level management less explicit in runtime and operations.",
            "why_now": "Absorbed rows are hidden quality debt that later turns into drift.",
            "proposed_next_step": "Materialize the top absorbed families into explicit registry rows.",
            "success_metric": "master_absorbed_row_total decreases.",
        },
        "candidate_pack_rule_upgrade": {
            "title": "candidate-pack rule upgrade",
            "current_gap": "Candidate packs still exist that have not been elevated into stable rule packs.",
            "why_now": "Even a small number of upgraded candidate packs can improve perceived quality sharply.",
            "proposed_next_step": "Convert the top candidate-pack families into article/rule packs.",
            "success_metric": "candidate_pack_total decreases.",
        },
        "inferred_row_reverification": {
            "title": "inferred row reverification",
            "current_gap": "Inferred overlay rows still carry higher operating and partner-risk than verified rows.",
            "why_now": "A small number of inferred rows can still undermine trust in the visible catalog.",
            "proposed_next_step": "Reverify each inferred row against law title, article, and registration-criteria sentences.",
            "success_metric": "Inferred rows move into an explicitly verified state.",
        },
        "real_focus_catalog_gap": {
            "title": "real focus catalog expansion",
            "current_gap": "The real focus catalog is still narrower than the perceived product scope.",
            "why_now": "A narrow catalog makes the product feel smaller than it is.",
            "proposed_next_step": "Expand the real focus catalog across construction, electric, information-communication, and fire domains.",
            "success_metric": "real_focus_target_total increases.",
        },
        "encoding_noise_repair": {
            "title": "encoding noise repair",
            "current_gap": "Some output rows still have a risk of broken text.",
            "why_now": "Broken legal names or service labels damage both product trust and partner/patent documentation.",
            "proposed_next_step": "Apply UTF-8 validation and clean-text overrides across the publication layer.",
            "success_metric": "encoding noise row total stays at zero.",
        },
    }

    normalized: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cloned = dict(item)
        override = templates.get(str(cloned.get("id") or ""))
        if override:
            cloned.update(override)
        normalized.append(cloned)
    return normalized


def _story_contract_surface_ready(
    *,
    widget_summary: Dict[str, Any],
    api_contract_master_summary: Dict[str, Any],
    release_bundle_summary: Dict[str, Any],
) -> bool:
    widget_family_total = _safe_int(widget_summary.get("permit_case_story_family_total"))
    api_family_total = _safe_int(api_contract_master_summary.get("case_story_surface_family_total"))
    release_family_total = _safe_int(release_bundle_summary.get("case_story_family_total"))
    review_reason_total = _safe_int(release_bundle_summary.get("case_story_review_reason_total"))
    return (
        widget_family_total > 0
        and api_family_total > 0
        and release_family_total > 0
        and review_reason_total > 0
    )


def build_brainstorm(
    *,
    master_catalog: Dict[str, Any],
    provenance_audit: Dict[str, Any],
    focus_report: Dict[str, Any],
    source_upgrade_backlog: Dict[str, Any],
    permit_patent_evidence_bundle: Dict[str, Any] | None = None,
    permit_family_case_goldset: Dict[str, Any] | None = None,
    permit_runtime_case_assertions: Dict[str, Any] | None = None,
    widget_rental_catalog: Dict[str, Any] | None = None,
    api_contract_spec: Dict[str, Any] | None = None,
    permit_case_release_guard: Dict[str, Any] | None = None,
    permit_review_case_presets: Dict[str, Any] | None = None,
    permit_case_story_surface: Dict[str, Any] | None = None,
    permit_preset_story_release_guard: Dict[str, Any] | None = None,
    permit_operator_demo_packet: Dict[str, Any] | None = None,
    permit_release_bundle: Dict[str, Any] | None = None,
    runtime_html: str | None = None,
    prompt_doc: str = "",
) -> Dict[str, Any]:
    master_summary = dict(master_catalog.get("summary") or {})
    provenance_summary = dict(provenance_audit.get("summary") or {})
    focus_summary = dict(focus_report.get("summary") or {})
    backlog_summary = dict(source_upgrade_backlog.get("summary") or {})
    patent_summary = (
        dict((permit_patent_evidence_bundle or {}).get("summary") or {})
        if isinstance(permit_patent_evidence_bundle, dict)
        else {}
    )
    goldset_summary = (
        dict((permit_family_case_goldset or {}).get("summary") or {})
        if isinstance(permit_family_case_goldset, dict)
        else {}
    )
    runtime_assertions_summary = (
        dict((permit_runtime_case_assertions or {}).get("summary") or {})
        if isinstance(permit_runtime_case_assertions, dict)
        else {}
    )
    widget_summary = (
        dict((widget_rental_catalog or {}).get("summary") or {})
        if isinstance(widget_rental_catalog, dict)
        else {}
    )
    case_release_guard_summary = (
        dict((permit_case_release_guard or {}).get("summary") or {})
        if isinstance(permit_case_release_guard, dict)
        else {}
    )
    review_case_presets_summary = (
        dict((permit_review_case_presets or {}).get("summary") or {})
        if isinstance(permit_review_case_presets, dict)
        else {}
    )
    case_story_surface_summary = (
        dict((permit_case_story_surface or {}).get("summary") or {})
        if isinstance(permit_case_story_surface, dict)
        else {}
    )
    preset_story_guard_summary = (
        dict((permit_preset_story_release_guard or {}).get("summary") or {})
        if isinstance(permit_preset_story_release_guard, dict)
        else {}
    )
    operator_demo_summary = (
        dict((permit_operator_demo_packet or {}).get("summary") or {})
        if isinstance(permit_operator_demo_packet, dict)
        else {}
    )
    release_bundle_summary = (
        dict((permit_release_bundle or {}).get("summary") or {})
        if isinstance(permit_release_bundle, dict)
        else {}
    )
    api_contract_master_summary = {}
    if isinstance(api_contract_spec, dict):
        services = api_contract_spec.get("services") if isinstance(api_contract_spec.get("services"), dict) else {}
        permit_service = services.get("permit") if isinstance(services.get("permit"), dict) else {}
        response_contract = (
            permit_service.get("response_contract") if isinstance(permit_service.get("response_contract"), dict) else {}
        )
        catalog_contracts = (
            response_contract.get("catalog_contracts")
            if isinstance(response_contract.get("catalog_contracts"), dict)
            else {}
        )
        master_contract = catalog_contracts.get("master_catalog") if isinstance(catalog_contracts.get("master_catalog"), dict) else {}
        api_contract_master_summary = (
            master_contract.get("current_summary") if isinstance(master_contract.get("current_summary"), dict) else {}
        )
    master_rows = [row for row in list(master_catalog.get("industries") or []) if isinstance(row, dict)]
    focus_seed_groups = list(
        ((source_upgrade_backlog.get("upgrade_tracks") or {}).get("focus_seed_source_groups") or [])
    )
    absorbed_groups = list(
        ((source_upgrade_backlog.get("upgrade_tracks") or {}).get("absorbed_source_groups") or [])
    )
    candidate_pack_groups = list(
        ((source_upgrade_backlog.get("upgrade_tracks") or {}).get("candidate_pack_stabilization_groups") or [])
    )

    focus_seed_total = _safe_int(provenance_summary.get("focus_seed_row_total"))
    focus_family_registry_total = _safe_int(provenance_summary.get("focus_family_registry_row_total"))
    focus_family_registry_missing_raw_source_proof_total = _safe_int(
        provenance_summary.get("focus_family_registry_missing_raw_source_proof_total")
    )
    absorbed_total = _safe_int(master_summary.get("master_absorbed_row_total"))
    candidate_pack_total = _safe_int(provenance_summary.get("candidate_pack_total"))
    inferred_total = _safe_int(provenance_summary.get("master_inferred_overlay_total"))
    real_focus_target_total = _safe_int(
        focus_summary.get("real_focus_target_total", focus_summary.get("real_high_confidence_focus_total"))
    )
    focus_registry_total = _safe_int(master_summary.get("master_focus_registry_row_total"))
    patent_family_total = _safe_int(patent_summary.get("focus_source_family_total"))
    claim_packet_family_total = _safe_int(patent_summary.get("claim_packet_family_total"))
    claim_packet_complete_family_total = _safe_int(patent_summary.get("claim_packet_complete_family_total"))
    checksum_sample_family_total = _safe_int(patent_summary.get("checksum_sample_family_total"))
    family_case_goldset_family_total = _safe_int(goldset_summary.get("goldset_complete_family_total"))
    edge_case_total = _safe_int(goldset_summary.get("edge_case_total"))
    edge_case_family_total = _safe_int(goldset_summary.get("edge_case_family_total"))
    manual_review_case_total = _safe_int(goldset_summary.get("manual_review_case_total"))
    runtime_asserted_family_total = _safe_int(runtime_assertions_summary.get("asserted_family_total"))
    runtime_failed_case_total = _safe_int(runtime_assertions_summary.get("failed_case_total"))
    runtime_assertions_ready = bool(runtime_assertions_summary.get("runtime_assertions_ready", False))
    runtime_proof_surface_ready = _runtime_proof_surface_ready(runtime_html)
    widget_claim_packet_family_total = _safe_int(widget_summary.get("permit_claim_packet_family_total"))
    widget_checksum_sample_family_total = _safe_int(widget_summary.get("permit_checksum_sample_family_total"))
    widget_case_parity_family_total = _safe_int(widget_summary.get("permit_widget_case_parity_family_total"))
    api_case_parity_family_total = _safe_int(api_contract_master_summary.get("family_case_goldset_family_total"))
    case_release_guard_family_total = _safe_int(case_release_guard_summary.get("family_total"))
    case_release_guard_failed_total = (
        _safe_int(case_release_guard_summary.get("runtime_failed_case_total"))
        + _safe_int(case_release_guard_summary.get("runtime_missing_case_total"))
        + _safe_int(case_release_guard_summary.get("widget_missing_case_total"))
        + _safe_int(case_release_guard_summary.get("api_missing_case_total"))
        + _safe_int(case_release_guard_summary.get("runtime_extra_case_total"))
        + _safe_int(case_release_guard_summary.get("widget_extra_case_total"))
        + _safe_int(case_release_guard_summary.get("api_extra_case_total"))
    )
    case_release_guard_ready = bool(case_release_guard_summary.get("release_guard_ready", False))
    case_release_guard_preview_ready = bool(release_bundle_summary.get("case_release_guard_preview_ready", False)) or bool(
        case_release_guard_summary
    )
    review_case_preset_total = _safe_int(review_case_presets_summary.get("preset_total"))
    review_case_preset_family_total = _safe_int(review_case_presets_summary.get("preset_family_total"))
    review_case_preset_ready = bool(review_case_presets_summary.get("preset_ready", False))
    case_story_family_total = _safe_int(case_story_surface_summary.get("story_family_total"))
    case_story_review_reason_total = _safe_int(case_story_surface_summary.get("review_reason_total"))
    case_story_surface_ready = bool(case_story_surface_summary.get("story_ready", False))
    runtime_review_preset_surface_ready = _runtime_review_preset_surface_ready(runtime_html)
    story_contract_surface_ready = _story_contract_surface_ready(
        widget_summary=widget_summary,
        api_contract_master_summary=api_contract_master_summary,
        release_bundle_summary=release_bundle_summary,
    )
    preset_story_guard_ready = bool(preset_story_guard_summary.get("preset_story_guard_ready", False))
    operator_demo_packet_ready = bool(operator_demo_summary.get("operator_demo_ready", False))
    operator_demo_family_total = _safe_int(operator_demo_summary.get("family_total"))
    operator_demo_case_total = _safe_int(operator_demo_summary.get("demo_case_total"))
    runtime_operator_demo_surface_ready = _runtime_operator_demo_surface_ready(runtime_html)
    operator_demo_release_surface_ready = bool(
        release_bundle_summary.get("operator_demo_release_surface_ready", False)
    )
    widget_partner_demo_surface_ready = bool(widget_summary.get("permit_partner_demo_surface_ready", False))
    api_partner_demo_surface_ready = bool(api_contract_master_summary.get("partner_demo_surface_ready", False))
    partner_demo_surface_ready = widget_partner_demo_surface_ready and api_partner_demo_surface_ready
    story_contract_surface_ready = story_contract_surface_ready or any(
        (
            preset_story_guard_ready,
            operator_demo_packet_ready,
            runtime_operator_demo_surface_ready,
            operator_demo_release_surface_ready,
            widget_partner_demo_surface_ready,
            api_partner_demo_surface_ready,
        )
    )
    contract_surface_already_materialized = any(
        (
            runtime_review_preset_surface_ready,
            story_contract_surface_ready,
            preset_story_guard_ready,
            operator_demo_packet_ready,
            runtime_operator_demo_surface_ready,
            operator_demo_release_surface_ready,
            widget_partner_demo_surface_ready,
            api_partner_demo_surface_ready,
        )
    )
    encoding_noise_total = _count_encoding_noise(master_rows)
    prompt_doc_ready = bool(str(prompt_doc or "").strip())
    prompt_doc_excerpt = _doc_excerpt(prompt_doc)

    brainstorm_items: List[Dict[str, Any]] = []
    if focus_seed_total:
        top_group = _safe_str(focus_seed_groups[0].get("group_key")) if focus_seed_groups else "top focus-seed family"
        brainstorm_items.append(
            {
                "id": "focus_seed_source_upgrade",
                "priority": "P1",
                "track": "execution",
                "title": f"Focus-seed {focus_seed_total}건 official source upgrade",
                "current_gap": f"중간 원천 focus-seed row {focus_seed_total}건이 아직 official raw source로 고정되지 않음",
                "why_now": "제품 coverage는 확보됐지만, 특허·임대형 계약 기준으로는 중간 seed 의존을 줄여야 함",
                "proposed_next_step": f"`{top_group}`부터 official source snapshot 또는 raw master seed로 치환",
                "success_metric": f"focus_seed_row_total {focus_seed_total} -> 0",
                "parallelizable_with": ["candidate_pack_rule_upgrade", "encoding_noise_repair"],
            }
        )
        brainstorm_items.append(
            {
                "id": "patent_evidence_bundle",
                "priority": "P2",
                "track": "research",
                "title": "특허 근거 패킷 병렬 정리",
                "current_gap": f"focus-seed 법령군 {max(1, len(focus_seed_groups))}개가 제품에는 반영됐지만 특허 claim/evidence packet으로는 아직 분리되지 않음",
                "why_now": "official source upgrade와 병렬로 진행해도 충돌이 없고, 이후 플랫폼/임대형 설명자료의 정합성을 높일 수 있음",
                "proposed_next_step": "법령군별로 법령 근거, 입력 변수, 계산 결과, UI 노출 문구를 묶은 특허 증빙 패킷을 생성",
                "success_metric": f"focus_seed_group_total {max(1, len(focus_seed_groups))} families documented",
                "parallelizable_with": ["focus_seed_source_upgrade"],
            }
        )
    elif focus_family_registry_total and focus_family_registry_missing_raw_source_proof_total:
        brainstorm_items.append(
            {
                "id": "focus_family_registry_hardening",
                "priority": "P1",
                "track": "execution",
                "title": f"Curated family registry {focus_family_registry_total}건 raw-source hardening",
                "current_gap": (
                    f"focus-family-registry row {focus_family_registry_total}건 중 "
                    f"{focus_family_registry_missing_raw_source_proof_total}건이 raw-source proof 없이 남아 있음"
                ),
                "why_now": "focus-seed 잔량은 정리됐고, 이제 남은 핵심 리스크는 curated registry의 증빙 밀도와 원천화 수준임",
                "proposed_next_step": "법령군별로 official snapshot note, raw source checksum, 증빙 캡처 메타를 family registry row에 추가",
                "success_metric": (
                    f"focus_family_registry_missing_raw_source_proof_total "
                    f"{focus_family_registry_missing_raw_source_proof_total} -> 0"
                ),
                "parallelizable_with": ["patent_evidence_bundle"],
            }
        )
        brainstorm_items.append(
            {
                "id": "patent_evidence_bundle",
                "priority": "P2",
                "track": "research",
                "title": "특허 근거 패킷 병렬 정리",
                "current_gap": "family registry가 제품에는 반영됐지만 특허 claim/evidence packet과 raw-source proof packet이 완전히 결합되지는 않음",
                "why_now": "registry hardening과 병렬로 정리하면 플랫폼/임대형/특허 설명자료 정합성을 바로 끌어올릴 수 있음",
                "proposed_next_step": "법령군별 claim, 입력 변수, 계산 로직, UI 노출, source proof를 하나의 증빙 packet으로 통합",
                "success_metric": "all curated family registry groups documented with claim+source proof",
                "parallelizable_with": ["focus_family_registry_hardening"],
            }
        )
    elif focus_family_registry_total and claim_packet_complete_family_total < max(1, patent_family_total):
        brainstorm_items.append(
            {
                "id": "patent_evidence_bundle_lock",
                "priority": "P1",
                "track": "execution",
                "title": "특허 증빙 패킷 고도화",
                "current_gap": (
                    f"curated family registry {focus_family_registry_total}건은 raw-source proof까지 채워졌지만 "
                    "claim/evidence 설명 패킷이 아직 제품 계약·특허 서술 기준으로 완전히 고정되지는 않음"
                ),
                "why_now": "raw-source hardening이 끝난 뒤에는 특허 및 외부 설명자료 정밀화가 다음 병목이 됨",
                "proposed_next_step": "법령군별 claim, 입력 변수, 계산 로직, UI 노출, checksum proof를 하나의 특허 증빙 패킷으로 통합",
                "success_metric": (
                    f"claim_packet_complete_family_total {claim_packet_complete_family_total}"
                    f" -> {max(1, patent_family_total)}"
                ),
                "parallelizable_with": ["platform_contract_proof_surface"],
            }
        )
        brainstorm_items.append(
            {
                "id": "platform_contract_proof_surface",
                "priority": "P2",
                "track": "product",
                "title": "플랫폼 계약에 provenance 노출",
                "current_gap": "widget/API/master 계약은 준비됐지만 raw-source proof 요약이 외부 계약 필드로는 충분히 드러나지 않음",
                "why_now": "특허·임대형·운영 QA가 같은 source proof를 보도록 맞춰야 이후 설명 불일치가 줄어듦",
                "proposed_next_step": "master/widget/api summary에 raw-source proof coverage와 family checksum 요약을 추가",
                "success_metric": "external contracts expose proof coverage + checksum summary",
                "parallelizable_with": ["patent_evidence_bundle_lock"],
            }
        )
    elif checksum_sample_family_total and (
        widget_claim_packet_family_total < claim_packet_complete_family_total
        or widget_checksum_sample_family_total < checksum_sample_family_total
    ) and not contract_surface_already_materialized:
        brainstorm_items.append(
            {
                "id": "platform_contract_proof_surface",
                "priority": "P1",
                "track": "execution",
                "title": "플랫폼 계약에 claim/proof surface 고정",
                "current_gap": (
                    f"특허 증빙 family {claim_packet_complete_family_total}건은 claim packet이 완성됐지만 "
                    f"외부 계약면에는 checksum sample family {widget_checksum_sample_family_total}/{checksum_sample_family_total}만 노출됨"
                ),
                "why_now": "patent bundle 정합성이 확보된 뒤에는 widget/API/master 계약에 같은 checksum sample과 claim packet 지표를 바로 노출해야 함",
                "proposed_next_step": "widget/API/master summary와 proof examples에 family checksum sample 및 claim packet coverage를 동기화",
                "success_metric": (
                    f"widget checksum surface {widget_checksum_sample_family_total}/{checksum_sample_family_total}"
                    f" and claim packet surface {widget_claim_packet_family_total}/{claim_packet_complete_family_total}"
                ),
                "parallelizable_with": ["family_case_goldset"],
            }
        )
        brainstorm_items.append(
            {
                "id": "family_case_goldset",
                "priority": "P2",
                "track": "research",
                "title": "법령군별 검증 사례 gold-set 구축",
                "current_gap": "구조화된 claim packet은 생겼지만 family별 대표 입력/예상결과 사례 세트는 아직 없음",
                "why_now": "계약면과 특허 서술이 정리된 뒤에는 계산 검증 표본이 있어야 QA와 특허 근거가 같이 버틸 수 있음",
                "proposed_next_step": "6개 법령군별 최소/경계/실패 사례 입력과 예상 결과를 gold-set JSON으로 고정",
                "success_metric": f"family case gold-set documented for {max(1, claim_packet_complete_family_total)} families",
                "parallelizable_with": ["platform_contract_proof_surface"],
            }
        )
    elif focus_family_registry_total and not runtime_proof_surface_ready:
        brainstorm_items.append(
            {
                "id": "runtime_proof_disclosure",
                "priority": "P1",
                "track": "execution",
                "title": "런타임 proof/claim 노출 정렬",
                "current_gap": (
                    f"family claim packet {claim_packet_family_total}건과 checksum sample {checksum_sample_family_total}건은 준비됐지만 "
                    "실제 런타임/운영 화면에서는 proof badge와 claim summary가 바로 보이지 않음"
                ),
                "why_now": "특허 번들과 외부 계약면이 정리된 뒤에는 QA와 운영자가 같은 근거를 제품 화면에서 바로 확인할 수 있어야 함",
                "proposed_next_step": "permit runtime bootstrap과 UI에 family claim id, checksum sample, official snapshot note를 노출",
                "success_metric": "runtime proof badge and claim summary visible across focus rows",
                "parallelizable_with": ["family_case_goldset"],
            }
        )
        brainstorm_items.append(
            {
                "id": "family_case_goldset",
                "priority": "P2",
                "track": "research",
                "title": "법령군별 검증 사례 gold-set 구축",
                "current_gap": "family proof와 claim packet은 갖췄지만 대표 성공/실패/경계 사례 세트는 아직 별도 자산이 아님",
                "why_now": "UI proof disclosure와 병렬로 gold-set을 고정해 두면 이후 계산 regression과 특허 설명을 한 번에 검증할 수 있음",
                "proposed_next_step": "6개 법령군별 최소/경계/실패 사례 입력과 예상 결과를 gold-set JSON으로 생성",
                "success_metric": f"family case gold-set documented for {max(1, claim_packet_complete_family_total)} families",
                "parallelizable_with": ["runtime_proof_disclosure"],
            }
        )
    elif focus_family_registry_total and family_case_goldset_family_total < max(1, claim_packet_complete_family_total):
        brainstorm_items.append(
            {
                "id": "family_case_goldset",
                "priority": "P1",
                "track": "execution",
                "title": "family case gold-set generation",
                "current_gap": (
                    f"runtime proof surface is ready, but family gold-set coverage remains "
                    f"{family_case_goldset_family_total}/{max(1, claim_packet_complete_family_total)}"
                ),
                "why_now": "Without family minimum/boundary/shortfall cases, the proof surface is visible but not regression-ready.",
                "proposed_next_step": "Generate gold-set JSON/MD for all claim-packet families with minimum, boundary, and shortfall cases.",
                "success_metric": (
                    f"family_case_goldset_family_total {family_case_goldset_family_total} -> "
                    f"{max(1, claim_packet_complete_family_total)}"
                ),
                "parallelizable_with": ["runtime_proof_regression_lock"],
            }
        )
        brainstorm_items.append(
            {
                "id": "runtime_proof_regression_lock",
                "priority": "P2",
                "track": "research",
                "title": "runtime proof regression markers",
                "current_gap": "Proof/claim UI is present, but proof marker stability is not yet locked as a regression contract.",
                "why_now": "The gold-set can be generated in parallel while the runtime disclosure markers are stabilized for future UI QA.",
                "proposed_next_step": "Lock proofClaimBox, claim id, checksum sample, and snapshot note markers in the generated runtime HTML.",
                "success_metric": "runtime proof disclosure markers remain stable across generated HTML",
                "parallelizable_with": ["family_case_goldset"],
            }
        )
    elif focus_family_registry_total:
        widget_case_parity_ready = (
            widget_case_parity_family_total >= max(1, family_case_goldset_family_total)
            and api_case_parity_family_total >= max(1, family_case_goldset_family_total)
        )
        widget_case_parity_ready = widget_case_parity_ready or any(
            (
                case_release_guard_ready,
                case_release_guard_preview_ready,
                review_case_preset_ready,
                case_story_surface_ready,
                runtime_review_preset_surface_ready,
                story_contract_surface_ready,
                preset_story_guard_ready,
                operator_demo_packet_ready,
                runtime_operator_demo_surface_ready,
                operator_demo_release_surface_ready,
                widget_partner_demo_surface_ready,
                api_partner_demo_surface_ready,
            )
        )
        if not runtime_assertions_ready:
            brainstorm_items.append(
                {
                    "id": "family_case_runtime_assertions",
                    "priority": "P1",
                    "track": "execution",
                    "title": "gold-set driven runtime assertions",
                    "current_gap": "Runtime proof disclosure and family gold-set are both ready, but the runtime regression suite does not consume them yet.",
                    "why_now": "The next reliability step is to turn the visible proof surface and family cases into executable regression guarantees.",
                    "proposed_next_step": "Use the family gold-set to add success, boundary, and shortfall runtime assertions for each law family.",
                    "success_metric": f"runtime regression covers {family_case_goldset_family_total} families",
                    "parallelizable_with": ["widget_case_parity"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "widget_case_parity",
                    "priority": "P2",
                    "track": "research",
                    "title": "widget/API case parity",
                    "current_gap": "Widget/API contracts expose proof surfaces, but they do not yet surface representative family case samples.",
                    "why_now": "Keeping runtime, widget, and API case references aligned reduces partner QA drift and patent explanation mismatch.",
                    "proposed_next_step": "Expose family case sample ids and expected statuses in widget/API contract artifacts.",
                    "success_metric": "widget/api contracts expose family case references for all families",
                    "parallelizable_with": ["family_case_runtime_assertions"],
                }
            )
        elif not widget_case_parity_ready:
            brainstorm_items.append(
                {
                    "id": "widget_case_parity",
                    "priority": "P1",
                    "track": "execution",
                    "title": "widget/API case parity",
                    "current_gap": (
                        f"runtime assertions cover {runtime_asserted_family_total}/{max(1, family_case_goldset_family_total)} families, "
                        f"but widget/api case parity remains {widget_case_parity_family_total}/{max(1, family_case_goldset_family_total)}"
                    ),
                    "why_now": "Runtime assertions are in place, so the next mismatch risk is external contract drift across widget and API artifacts.",
                    "proposed_next_step": "Expose family case sample ids and expected statuses in widget/API contract artifacts.",
                    "success_metric": "widget/api contracts expose family case references for all families",
                    "parallelizable_with": ["case_release_guard"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "case_release_guard",
                    "priority": "P2",
                    "track": "research",
                    "title": "runtime/widget/api case parity guard",
                    "current_gap": "Release bundle does not yet fail when runtime assertions and external case surfaces drift.",
                    "why_now": "Once parity surfaces exist, the next leverage point is a single guardrail that blocks inconsistent release artifacts.",
                    "proposed_next_step": "Compare runtime assertions, widget case samples, and API case samples in one release-level parity audit.",
                    "success_metric": "release guard tracks all family case surfaces",
                    "parallelizable_with": ["widget_case_parity"],
                }
            )
        elif not case_release_guard_ready:
            brainstorm_items.append(
                {
                    "id": "case_release_guard",
                    "priority": "P1",
                    "track": "execution",
                    "title": "runtime/widget/api case parity guard",
                    "current_gap": (
                        f"runtime assertions and external parity are ready, but there is no release-level guard over "
                        f"{family_case_goldset_family_total} family case surfaces."
                    ),
                    "why_now": "At this stage the highest-risk failure mode is silent drift between runtime, widget, API, and patent evidence artifacts.",
                    "proposed_next_step": "Add a release-level parity audit that compares runtime assertions with widget/API case surfaces and blocks drift.",
                    "success_metric": f"case parity guard passes for {family_case_goldset_family_total} families",
                    "parallelizable_with": ["family_case_edge_expansion"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "family_case_edge_expansion",
                    "priority": "P2",
                    "track": "research",
                    "title": "family case edge expansion",
                    "current_gap": "The gold-set is locked at minimum/boundary/shortfall cases and does not yet cover operator-review edge patterns.",
                    "why_now": "With the core parity chain stabilized, the next quality gain comes from adding ambiguous and manual-review edge cases.",
                    "proposed_next_step": "Expand family gold-set coverage with ambiguous, document-missing, and operator-review edge cases per law family.",
                    "success_metric": "gold-set expands beyond pass/boundary/shortfall into operator-review cases",
                    "parallelizable_with": ["case_release_guard"],
                }
            )
        elif edge_case_family_total < max(1, family_case_goldset_family_total):
            brainstorm_items.append(
                {
                    "id": "family_case_edge_expansion",
                    "priority": "P1",
                    "track": "execution",
                    "title": "family case edge expansion",
                    "current_gap": (
                        f"release guard covers {case_release_guard_family_total}/{max(1, family_case_goldset_family_total)} families, "
                        "but the gold-set still stops at minimum/boundary/shortfall scenarios."
                    ),
                    "why_now": "The core release parity chain is locked, so the next gain comes from operator-review and ambiguous edge cases.",
                    "proposed_next_step": "Add ambiguous, document-missing, and manual-review cases per law family and carry them through runtime/widget/api surfaces.",
                    "success_metric": "edge-case gold-set expands across all focus families",
                    "parallelizable_with": ["case_release_observability"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "case_release_observability",
                    "priority": "P2",
                    "track": "research",
                    "title": "case release observability",
                    "current_gap": "Release guard is passing, but the guard status is not yet summarized as a first-class release artifact for operators.",
                    "why_now": "Once parity is enforced, the next operational improvement is to surface drift health directly in release and partner QA views.",
                    "proposed_next_step": "Expose release-guard pass/fail counts and missing-case previews in the release summary and partner QA notes.",
                    "success_metric": "release summary exposes case-guard health without opening raw JSON",
                    "parallelizable_with": ["family_case_edge_expansion"],
                }
            )
        elif not case_release_guard_preview_ready:
            brainstorm_items.append(
                {
                    "id": "case_release_observability",
                    "priority": "P1",
                    "track": "execution",
                    "title": "case release observability",
                    "current_gap": (
                        f"edge-case gold-set covers {edge_case_family_total}/{max(1, family_case_goldset_family_total)} families, "
                        "but release summary and partner QA notes do not surface guard health yet."
                    ),
                    "why_now": "Once guard parity and edge cases exist, operators need a visible summary instead of opening raw JSON artifacts.",
                    "proposed_next_step": "Expose release-guard pass/fail counts and missing-case previews in release summary and partner QA notes.",
                    "success_metric": "release summary surfaces case guard health and preview samples",
                    "parallelizable_with": ["review_case_input_presets"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "review_case_input_presets",
                    "priority": "P2",
                    "track": "research",
                    "title": "review-case input presets",
                    "current_gap": "Edge cases exist in the gold-set, but operators still have to enter them manually during QA or demos.",
                    "why_now": "Preset payloads make manual review scenarios reproducible across runtime checks, partner demos, and patent evidence.",
                    "proposed_next_step": "Generate reusable preset payloads for manual-review, document-missing, capital-only, and technician-only scenarios.",
                    "success_metric": "preset payloads exist for all focus law families",
                    "parallelizable_with": ["case_release_observability"],
                }
            )
        elif not review_case_preset_ready:
            brainstorm_items.append(
                {
                    "id": "review_case_input_presets",
                    "priority": "P1",
                    "track": "execution",
                    "title": "review-case input presets",
                    "current_gap": (
                        f"release guard and edge cases are locked across {edge_case_family_total}/{max(1, family_case_goldset_family_total)} families, "
                        "but there are no reusable operator-review presets."
                    ),
                    "why_now": "The next leverage point is faster operator QA, demos, and patent evidence reproduction with canned inputs.",
                    "proposed_next_step": "Generate preset payloads for manual-review, document-missing, capital-only, and technician-only scenarios.",
                    "success_metric": "review-case presets cover all focus families",
                    "parallelizable_with": ["case_story_surface"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "case_story_surface",
                    "priority": "P2",
                    "track": "research",
                    "title": "case story surface",
                    "current_gap": "Edge-case reasons exist in the gold-set, but the operator-facing story is not yet summarized in one surface.",
                    "why_now": "Once presets exist, the next quality improvement is a concise reason map for partner QA and patent reviewers.",
                    "proposed_next_step": "Surface review reasons and representative edge cases as a compact operator/patent story sheet.",
                    "success_metric": "operator story sheet covers all edge-case types and law families",
                    "parallelizable_with": ["review_case_input_presets"],
                }
            )
        elif not case_story_surface_ready:
            brainstorm_items.append(
                {
                    "id": "case_story_surface",
                    "priority": "P1",
                    "track": "execution",
                    "title": "case story surface",
                    "current_gap": (
                        f"review-case presets cover {review_case_preset_family_total}/{max(1, family_case_goldset_family_total)} families, "
                        "but the operator-facing story is not yet summarized in one surface."
                    ),
                    "why_now": "Preset payloads exist, so the next quality gain is a compact reason map for partner QA and patent reviewers.",
                    "proposed_next_step": "Surface review reasons and representative edge cases as a compact operator/patent story sheet.",
                    "success_metric": "operator story sheet covers all edge-case types and law families",
                    "parallelizable_with": ["runtime_review_preset_surface"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "runtime_review_preset_surface",
                    "priority": "P2",
                    "track": "research",
                    "title": "runtime review preset surface",
                    "current_gap": "Preset payloads exist as logs, but the runtime does not yet surface them as reusable QA/demo actions.",
                    "why_now": "Binding presets into the runtime makes operator QA and patent demonstrations reproducible with one click.",
                    "proposed_next_step": "Expose generated review-case presets in runtime quick-fill surfaces for operator-review scenarios.",
                    "success_metric": "runtime can load preset payloads for all focus families",
                    "parallelizable_with": ["case_story_surface"],
                }
            )
        elif not runtime_review_preset_surface_ready:
            brainstorm_items.append(
                {
                    "id": "runtime_review_preset_surface",
                    "priority": "P1",
                    "track": "execution",
                    "title": "runtime review preset surface",
                    "current_gap": (
                        f"review-case presets cover {review_case_preset_family_total}/{max(1, family_case_goldset_family_total)} families and "
                        f"story surface covers {case_story_family_total}/{max(1, family_case_goldset_family_total)} families, "
                        "but the runtime does not yet expose them as reusable QA/demo actions."
                    ),
                    "why_now": "The knowledge artifacts are ready, so the next step is operational leverage inside the actual runtime.",
                    "proposed_next_step": "Expose generated review-case presets as runtime quick-fill actions for operator-review scenarios.",
                    "success_metric": "runtime review presets are available across all focus families",
                    "parallelizable_with": ["story_contract_surface"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "story_contract_surface",
                    "priority": "P2",
                    "track": "research",
                    "title": "story contract surface",
                    "current_gap": "Case story surface exists as an internal artifact, but partner/widget/API contracts do not summarize the review-story layer.",
                    "why_now": "Surfacing story coverage in external contracts reduces mismatch between operator QA, partner QA, and patent explanations.",
                    "proposed_next_step": "Expose case story coverage and representative review reasons in release, widget, and API summaries.",
                    "success_metric": "story coverage appears across release/widget/API contract surfaces",
                    "parallelizable_with": ["runtime_review_preset_surface"],
                }
            )
        elif not story_contract_surface_ready:
            brainstorm_items.append(
                {
                    "id": "story_contract_surface",
                    "priority": "P1",
                    "track": "execution",
                    "title": "story contract surface",
                    "current_gap": (
                        "Runtime review presets are visible, but release/widget/API summaries still do not surface "
                        "case story coverage and representative review reasons together."
                    ),
                    "why_now": "External QA and patent reviewers still need to open internal artifacts to understand why a review scenario exists.",
                    "proposed_next_step": "Expose case story coverage, representative review reasons, and manual-review family counts in release, widget, and API summaries.",
                    "success_metric": "story coverage appears across release/widget/API contract surfaces",
                    "parallelizable_with": ["preset_story_release_guard"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "preset_story_release_guard",
                    "priority": "P2",
                    "track": "research",
                    "title": "preset/story release guard",
                    "current_gap": "Runtime preset actions and story artifacts exist, but no guard checks that both surfaces stay aligned in generated releases.",
                    "why_now": "Once the surfaces are visible, the next failure mode is silent drift between runtime buttons and contract summaries.",
                    "proposed_next_step": "Add a release-level guard that checks runtime preset markers and story contract coverage in one place.",
                    "success_metric": "release guard verifies both preset and story surfaces",
                    "parallelizable_with": ["story_contract_surface"],
                }
            )
        elif not preset_story_guard_ready:
            brainstorm_items.append(
                {
                    "id": "preset_story_release_guard",
                    "priority": "P1",
                    "track": "execution",
                    "title": "preset/story release guard",
                    "current_gap": (
                        "Runtime preset surface and story contract surface are both ready, "
                        "but release validation does not yet assert their marker/sample parity."
                    ),
                    "why_now": "The next reliability gap is preserving these new QA/demo surfaces across bundle generation.",
                    "proposed_next_step": "Add a release-level guard for runtime review preset markers and story contract coverage parity.",
                    "success_metric": "release guard blocks preset/story surface drift",
                    "parallelizable_with": ["operator_demo_packet"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "operator_demo_packet",
                    "priority": "P2",
                    "track": "research",
                    "title": "operator demo packet",
                    "current_gap": "Preset buttons and story summaries exist, but there is no compact operator/demo packet linking them into one walkthrough.",
                    "why_now": "A single operator packet improves partner QA, internal demos, and patent narrative reuse.",
                    "proposed_next_step": "Generate a compact demo packet that maps one-click presets to expected review stories and proof coverage.",
                    "success_metric": "operator demo packet covers all focus families",
                    "parallelizable_with": ["preset_story_release_guard"],
                }
            )
        elif not operator_demo_packet_ready:
            brainstorm_items.append(
                {
                    "id": "operator_demo_packet",
                    "priority": "P1",
                    "track": "execution",
                    "title": "operator demo packet",
                    "current_gap": (
                        "Preset/story surfaces are guarded, but operators still do not have a single compact walkthrough "
                        "that maps one-click presets to expected review stories and proof coverage."
                    ),
                    "why_now": "Once drift is blocked, the next leverage point is speeding internal demos, partner QA, and patent explanation reuse.",
                    "proposed_next_step": "Generate a compact operator demo packet grouped by law family with preset ids, expected statuses, and proof coverage.",
                    "success_metric": "operator demo packet covers all focus families",
                    "parallelizable_with": ["operator_demo_surface"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "operator_demo_surface",
                    "priority": "P2",
                    "track": "research",
                    "title": "operator demo surface",
                    "current_gap": "There is still no operator-facing runtime or release surface that points to the walkthrough packet.",
                    "why_now": "If the packet exists only as a log artifact, operators and reviewers still need manual handoff.",
                    "proposed_next_step": "Design a minimal runtime/release surface that links preset buttons, review stories, and the operator walkthrough packet.",
                    "success_metric": "operators can reach the demo packet from runtime or release summary",
                    "parallelizable_with": ["operator_demo_packet"],
                }
            )
        elif not runtime_operator_demo_surface_ready or not operator_demo_release_surface_ready:
            brainstorm_items.append(
                {
                    "id": "operator_demo_surface",
                    "priority": "P1",
                    "track": "execution",
                    "title": "operator demo surface",
                    "current_gap": "The walkthrough packet exists, but runtime and release surfaces still do not expose it as a first-class operator aid.",
                    "why_now": "The next friction point is discovery: QA and demos still depend on opening raw logs.",
                    "proposed_next_step": "Expose the operator demo packet path and summary on runtime/release surfaces.",
                    "success_metric": "operators can launch the packet directly from release or runtime",
                    "parallelizable_with": ["partner_demo_surface"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "partner_demo_surface",
                    "priority": "P2",
                    "track": "research",
                    "title": "partner demo surface",
                    "current_gap": "Partner-facing widget/API materials still do not reference the compact walkthrough packet.",
                    "why_now": "Adding a partner-safe demo surface makes rental onboarding and proof-based sales demos faster.",
                    "proposed_next_step": "Define a partner-safe summary that references the operator packet without leaking internal-only detail.",
                    "success_metric": "partner packet can point to a safe walkthrough summary",
                    "parallelizable_with": ["operator_demo_surface"],
                }
            )
        elif not partner_demo_surface_ready:
            brainstorm_items.append(
                {
                    "id": "partner_demo_surface",
                    "priority": "P1",
                    "track": "execution",
                    "title": "partner demo surface",
                    "current_gap": "Runtime/release operator demo surface is ready, but widget/API materials still do not expose a partner-safe demo summary.",
                    "why_now": "Sales demos and rental onboarding still require opening internal operator artifacts instead of partner-safe contract surfaces.",
                    "proposed_next_step": "Expose partner-safe demo samples on widget/API contract surfaces with family, proof, status, and review-reason coverage only.",
                    "success_metric": "widget and API both expose partner-safe demo samples for every focus family",
                    "parallelizable_with": ["critical_prompt_surface_lock"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "critical_prompt_surface_lock",
                    "priority": "P2",
                    "track": "research",
                    "title": "critical prompt surface lock",
                    "current_gap": "The critical-thinking prompt doc exists, but operator/release surfaces still do not compress it into an immediately usable decision lens.",
                    "why_now": "Once demo surfaces are visible, the next drift risk is prioritization quality rather than missing evidence.",
                    "proposed_next_step": "Design a compact first-principles/founder-mode summary that can sit on operator demo and release surfaces without bloating them.",
                    "success_metric": "operators can see bottleneck, founder questions, and anti-patterns without opening raw markdown",
                    "parallelizable_with": ["partner_demo_surface"],
                }
            )
        else:
            brainstorm_items.append(
                {
                    "id": "critical_prompt_surface_lock",
                    "priority": "P1",
                    "track": "execution",
                    "title": "critical prompt surface lock",
                    "current_gap": "Evidence and demo surfaces are green, but the operator still has to open raw prompt docs to apply first-principles prioritization consistently.",
                    "why_now": "The bottleneck is shifting from missing proof to weak prioritization discipline across repeated iterations.",
                    "proposed_next_step": "Surface a compact first-principles/founder-mode prompt block on release/operator surfaces using the current bottleneck and next-lane evidence.",
                    "success_metric": "release and operator surfaces expose a reusable critical-thinking lens tied to the active lane",
                    "parallelizable_with": ["demo_surface_observability"],
                }
            )
            brainstorm_items.append(
                {
                    "id": "demo_surface_observability",
                    "priority": "P2",
                    "track": "research",
                    "title": "demo surface observability",
                    "current_gap": "Runtime, release, widget, and API now each carry demo surfaces, but there is no single compact health view for demo-surface parity.",
                    "why_now": "As surfaces multiply, regressions will move from missing content to mismatched surface coverage.",
                    "proposed_next_step": "Define a compact observability report for operator demo and partner demo parity across runtime/release/widget/API.",
                    "success_metric": "one summary shows operator and partner demo surface readiness across all focus families",
                    "parallelizable_with": ["critical_prompt_surface_lock"],
                }
            )
    if absorbed_total:
        top_group = _safe_str(absorbed_groups[0].get("group_key")) if absorbed_groups else "top absorbed family"
        brainstorm_items.append(
            {
                "id": "materialize_absorbed_registry",
                "priority": "P1",
                "track": "execution",
                "title": "Absorbed 50건 raw registry materialization",
                "current_gap": f"runtime에서만 흡수된 row {absorbed_total}건이 남아 있음",
                "why_now": "현재 제품에서는 보이지만 원천 스냅샷으로 굳어 있지 않아 재생성 의존성이 큼",
                "proposed_next_step": f"`{top_group}`부터 raw/master seed 파일을 만들어 흡수 row를 원천화",
                "success_metric": "master_absorbed_row_total 50 -> 0",
                "parallelizable_with": ["candidate_pack_rule_upgrade", "encoding_noise_repair"],
            }
        )
    if candidate_pack_total:
        top_group = _safe_str(candidate_pack_groups[0].get("group_key")) if candidate_pack_groups else "top candidate-pack family"
        brainstorm_items.append(
            {
                "id": "candidate_pack_rule_upgrade",
                "priority": "P1",
                "track": "execution",
                "title": "Candidate-pack 3건 structured mapping 고정",
                "current_gap": f"법령 후보 기반 row {candidate_pack_total}건이 아직 구조화되지 않음",
                "why_now": "핵심 스코프가 53건으로 줄었기 때문에 3건만 해결해도 제품 신뢰도가 크게 올라감",
                "proposed_next_step": f"`{top_group}`부터 article/rule pack으로 승격하는 수동 매핑 seed 추가",
                "success_metric": "candidate_pack_total 3 -> 0",
                "parallelizable_with": ["materialize_absorbed_registry", "inferred_row_reverification"],
            }
        )
    if inferred_total:
        brainstorm_items.append(
            {
                "id": "inferred_row_reverification",
                "priority": "P1",
                "track": "research",
                "title": "Inferred 3건 재검증",
                "current_gap": f"추론 alias row {inferred_total}건이 partner 기본값으로 쓰이기엔 위험함",
                "why_now": "남은 실업종 3건이 모두 inferred/candidate-pack 계열이라 오탐 리스크가 집중됨",
                "proposed_next_step": "각 row의 법령명, 조문명, 등록기준 문장을 대조하는 gold-set 검증 추가",
                "success_metric": "master_inferred_overlay_total 3 -> 0 또는 명시적 verified flag 3/3",
                "parallelizable_with": ["candidate_pack_rule_upgrade", "encoding_noise_repair"],
            }
        )
    if focus_registry_total and real_focus_target_total < max(3, focus_registry_total // 5):
        brainstorm_items.append(
            {
                "id": "real_focus_catalog_gap",
                "priority": "P2",
                "track": "product",
                "title": "실업종 핵심 row 부재 해소",
                "current_gap": f"실업종 핵심 row가 {real_focus_target_total}건뿐이라 전부 focus registry/rule 계층에 의존",
                "why_now": "플랫폼/임대형 계약은 안정화됐지만 사용자 체감상 아직 real catalog 중심 제품처럼 보이기 어려움",
                "proposed_next_step": "건설·전기·소방 계열을 raw 업종 카탈로그로 승격하거나 별도 public focus registry를 정의",
                "success_metric": "real_focus_target_total -> 10+",
                "parallelizable_with": ["materialize_absorbed_registry"],
            }
        )
    if encoding_noise_total:
        brainstorm_items.append(
            {
                "id": "encoding_noise_repair",
                "priority": "P2",
                "track": "quality",
                "title": "문자 인코딩 오염 정리",
                "current_gap": f"출력 row {encoding_noise_total}건에서 깨진 문자열이 관찰됨",
                "why_now": "법령명/업종명이 깨지면 특허 근거와 partner 임대 자료의 신뢰도를 즉시 훼손함",
                "proposed_next_step": "master/focus 출력 전 텍스트 필드에 인코딩 이상 탐지와 교정 큐를 추가",
                "success_metric": "encoding_noise_row_total -> 0",
                "parallelizable_with": ["materialize_absorbed_registry", "candidate_pack_rule_upgrade"],
            }
        )

    primary_execution = next(
        (item for item in brainstorm_items if item.get("track") == "execution"),
        {},
    )
    if not primary_execution and brainstorm_items:
        primary_execution = dict(brainstorm_items[0])
    primary_parallel = next(
        (
            item
            for item in brainstorm_items
            if item.get("id") != primary_execution.get("id")
            and item.get("track") in {"research", "quality", "product"}
        ),
        {},
    )
    if not primary_parallel:
        primary_parallel = next(
            (
                item
                for item in brainstorm_items
                if item.get("id") != primary_execution.get("id")
            ),
            {},
        )

    brainstorm_items = _apply_item_text_overrides(brainstorm_items)
    primary_execution = next(
        (item for item in brainstorm_items if item.get("id") == primary_execution.get("id")),
        primary_execution,
    )
    primary_parallel = next(
        (item for item in brainstorm_items if item.get("id") == primary_parallel.get("id")),
        primary_parallel,
    )

    execution_prompt = _build_execution_prompt(
        primary_title=str(primary_execution.get("title") or ""),
        focus_seed_total=focus_seed_total,
        focus_family_registry_total=focus_family_registry_total,
        candidate_pack_total=candidate_pack_total,
        claim_packet_complete_family_total=claim_packet_complete_family_total,
        runtime_failed_case_total=runtime_failed_case_total,
    )
    brainstorm_prompt = _build_parallel_brainstorm_prompt(
        str(primary_execution.get("title") or ""),
        str(primary_parallel.get("title") or ""),
    )
    first_principles_prompt = _build_first_principles_prompt(
        str(primary_execution.get("title") or "")
    )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "master_industry_total": _safe_int(master_summary.get("master_industry_total")),
            "focus_family_registry_row_total": _safe_int(
                provenance_summary.get("focus_family_registry_row_total")
            ),
            "focus_seed_row_total": focus_seed_total,
            "master_absorbed_row_total": absorbed_total,
            "candidate_pack_total": candidate_pack_total,
            "inferred_reverification_total": inferred_total,
            "real_focus_target_total": real_focus_target_total,
            "real_high_confidence_focus_total": real_focus_target_total,
            "encoding_noise_row_total": encoding_noise_total,
            "focus_seed_group_total": _safe_int(backlog_summary.get("focus_seed_group_total")),
            "absorbed_group_total": _safe_int(backlog_summary.get("absorbed_group_total")),
            "claim_packet_family_total": claim_packet_family_total,
            "claim_packet_complete_family_total": claim_packet_complete_family_total,
            "checksum_sample_family_total": checksum_sample_family_total,
            "runtime_proof_surface_ready": runtime_proof_surface_ready,
            "family_case_goldset_family_total": family_case_goldset_family_total,
            "edge_case_total": edge_case_total,
            "edge_case_family_total": edge_case_family_total,
            "manual_review_case_total": manual_review_case_total,
            "runtime_asserted_family_total": runtime_asserted_family_total,
            "runtime_failed_case_total": runtime_failed_case_total,
            "widget_claim_packet_family_total": widget_claim_packet_family_total,
            "widget_checksum_sample_family_total": widget_checksum_sample_family_total,
            "widget_case_parity_family_total": widget_case_parity_family_total,
            "api_case_parity_family_total": api_case_parity_family_total,
            "case_release_guard_family_total": case_release_guard_family_total,
            "case_release_guard_failed_total": case_release_guard_failed_total,
            "case_release_guard_ready": case_release_guard_ready,
            "case_release_guard_preview_ready": case_release_guard_preview_ready,
            "review_case_preset_total": review_case_preset_total,
            "review_case_preset_family_total": review_case_preset_family_total,
            "review_case_preset_ready": review_case_preset_ready,
            "case_story_family_total": case_story_family_total,
            "case_story_review_reason_total": case_story_review_reason_total,
            "case_story_surface_ready": case_story_surface_ready,
            "runtime_review_preset_surface_ready": runtime_review_preset_surface_ready,
            "story_contract_surface_ready": story_contract_surface_ready,
            "preset_story_guard_ready": preset_story_guard_ready,
            "operator_demo_packet_ready": operator_demo_packet_ready,
            "operator_demo_family_total": operator_demo_family_total,
            "operator_demo_case_total": operator_demo_case_total,
            "runtime_operator_demo_surface_ready": runtime_operator_demo_surface_ready,
            "operator_demo_release_surface_ready": operator_demo_release_surface_ready,
            "widget_partner_demo_surface_ready": widget_partner_demo_surface_ready,
            "api_partner_demo_surface_ready": api_partner_demo_surface_ready,
            "partner_demo_surface_ready": partner_demo_surface_ready,
            "prompt_doc_ready": prompt_doc_ready,
        },
        "current_execution_lane": primary_execution,
        "parallel_brainstorm_lane": primary_parallel,
        "execution_prompt": execution_prompt,
        "brainstorm_prompt": brainstorm_prompt,
        "first_principles_prompt": first_principles_prompt,
        "critical_prompts": {
            "execution_prompt": execution_prompt,
            "brainstorm_prompt": brainstorm_prompt,
            "first_principles_prompt": first_principles_prompt,
            "founder_mode_questions": _founder_mode_questions(),
            "prompt_doc_ready": prompt_doc_ready,
            "prompt_doc_excerpt": prompt_doc_excerpt,
        },
        "brainstorm_items": brainstorm_items,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    prompts = dict(report.get("critical_prompts") or {})
    lines = [
        "# Permit Next Action Brainstorm",
        "",
        "## Summary",
        f"- master_industry_total: `{summary.get('master_industry_total', 0)}`",
        f"- focus_family_registry_row_total: `{summary.get('focus_family_registry_row_total', 0)}`",
        f"- focus_seed_row_total: `{summary.get('focus_seed_row_total', 0)}`",
        f"- master_absorbed_row_total: `{summary.get('master_absorbed_row_total', 0)}`",
        f"- candidate_pack_total: `{summary.get('candidate_pack_total', 0)}`",
        f"- inferred_reverification_total: `{summary.get('inferred_reverification_total', 0)}`",
        f"- real_focus_target_total: `{summary.get('real_focus_target_total', summary.get('real_high_confidence_focus_total', 0))}`",
        f"- encoding_noise_row_total: `{summary.get('encoding_noise_row_total', 0)}`",
        f"- focus_seed_group_total: `{summary.get('focus_seed_group_total', 0)}`",
        f"- absorbed_group_total: `{summary.get('absorbed_group_total', 0)}`",
        f"- claim_packet_family_total: `{summary.get('claim_packet_family_total', 0)}`",
        f"- claim_packet_complete_family_total: `{summary.get('claim_packet_complete_family_total', 0)}`",
        f"- checksum_sample_family_total: `{summary.get('checksum_sample_family_total', 0)}`",
        f"- runtime_proof_surface_ready: `{summary.get('runtime_proof_surface_ready', False)}`",
        f"- family_case_goldset_family_total: `{summary.get('family_case_goldset_family_total', 0)}`",
        f"- edge_case_total: `{summary.get('edge_case_total', 0)}`",
        f"- edge_case_family_total: `{summary.get('edge_case_family_total', 0)}`",
        f"- manual_review_case_total: `{summary.get('manual_review_case_total', 0)}`",
        f"- runtime_asserted_family_total: `{summary.get('runtime_asserted_family_total', 0)}`",
        f"- runtime_failed_case_total: `{summary.get('runtime_failed_case_total', 0)}`",
        f"- widget_claim_packet_family_total: `{summary.get('widget_claim_packet_family_total', 0)}`",
        f"- widget_checksum_sample_family_total: `{summary.get('widget_checksum_sample_family_total', 0)}`",
        f"- widget_case_parity_family_total: `{summary.get('widget_case_parity_family_total', 0)}`",
        f"- api_case_parity_family_total: `{summary.get('api_case_parity_family_total', 0)}`",
        f"- case_release_guard_family_total: `{summary.get('case_release_guard_family_total', 0)}`",
        f"- case_release_guard_failed_total: `{summary.get('case_release_guard_failed_total', 0)}`",
        f"- case_release_guard_ready: `{summary.get('case_release_guard_ready', False)}`",
        f"- case_release_guard_preview_ready: `{summary.get('case_release_guard_preview_ready', False)}`",
        f"- review_case_preset_total: `{summary.get('review_case_preset_total', 0)}`",
        f"- review_case_preset_family_total: `{summary.get('review_case_preset_family_total', 0)}`",
        f"- review_case_preset_ready: `{summary.get('review_case_preset_ready', False)}`",
        f"- case_story_family_total: `{summary.get('case_story_family_total', 0)}`",
        f"- case_story_review_reason_total: `{summary.get('case_story_review_reason_total', 0)}`",
        f"- case_story_surface_ready: `{summary.get('case_story_surface_ready', False)}`",
        f"- runtime_review_preset_surface_ready: `{summary.get('runtime_review_preset_surface_ready', False)}`",
        f"- story_contract_surface_ready: `{summary.get('story_contract_surface_ready', False)}`",
        f"- preset_story_guard_ready: `{summary.get('preset_story_guard_ready', False)}`",
        f"- operator_demo_packet_ready: `{summary.get('operator_demo_packet_ready', False)}`",
        f"- operator_demo_family_total: `{summary.get('operator_demo_family_total', 0)}`",
        f"- operator_demo_case_total: `{summary.get('operator_demo_case_total', 0)}`",
        f"- runtime_operator_demo_surface_ready: `{summary.get('runtime_operator_demo_surface_ready', False)}`",
        f"- operator_demo_release_surface_ready: `{summary.get('operator_demo_release_surface_ready', False)}`",
        f"- widget_partner_demo_surface_ready: `{summary.get('widget_partner_demo_surface_ready', False)}`",
        f"- api_partner_demo_surface_ready: `{summary.get('api_partner_demo_surface_ready', False)}`",
        f"- partner_demo_surface_ready: `{summary.get('partner_demo_surface_ready', False)}`",
        f"- prompt_doc_ready: `{summary.get('prompt_doc_ready', False)}`",
        "",
        "## Active Execution Lane",
    ]
    execution_lane = dict(report.get("current_execution_lane") or {})
    if execution_lane:
        lines.extend(
            [
                f"- id: `{execution_lane.get('id', '')}`",
                f"- title: {execution_lane.get('title', '')}",
                f"- current_gap: {execution_lane.get('current_gap', '')}",
                f"- proposed_next_step: {execution_lane.get('proposed_next_step', '')}",
                f"- success_metric: {execution_lane.get('success_metric', '')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Parallel Brainstorm Lane"])
    brainstorm_lane = dict(report.get("parallel_brainstorm_lane") or {})
    if brainstorm_lane:
        lines.extend(
            [
                f"- id: `{brainstorm_lane.get('id', '')}`",
                f"- title: {brainstorm_lane.get('title', '')}",
                f"- current_gap: {brainstorm_lane.get('current_gap', '')}",
                f"- proposed_next_step: {brainstorm_lane.get('proposed_next_step', '')}",
                f"- success_metric: {brainstorm_lane.get('success_metric', '')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Critical Prompt",
            "```text",
            str(prompts.get("execution_prompt") or "").strip(),
            "```",
            "",
            "## Parallel Brainstorm Prompt",
            "```text",
            str(prompts.get("brainstorm_prompt") or "").strip(),
            "```",
            "",
            "## First-Principles Prompt",
            "```text",
            str(prompts.get("first_principles_prompt") or "").strip(),
            "```",
            "",
            "## Founder Mode Questions",
        ]
    )
    for question in list(prompts.get("founder_mode_questions") or []):
        lines.append(f"- {question}")
    prompt_doc_excerpt = str(prompts.get("prompt_doc_excerpt") or "").strip()
    if prompt_doc_excerpt:
        lines.extend(
            [
                "",
                "## Prompt Doc Excerpt",
                "```text",
                prompt_doc_excerpt,
                "```",
            ]
        )
    lines.extend(["", "## Brainstorm Items"])
    for item in list(report.get("brainstorm_items") or []):
        if not isinstance(item, dict):
            continue
        lines.append(
            f"- `{item.get('id', '')}` [{item.get('priority', '')}] {item.get('title', '')}"
            f" / next {item.get('proposed_next_step', '')}"
            f" / metric {item.get('success_metric', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the next action brainstorm for the permit focus scope.")
    parser.add_argument("--master-input", default=str(DEFAULT_MASTER_INPUT))
    parser.add_argument("--provenance-input", default=str(DEFAULT_PROVENANCE_INPUT))
    parser.add_argument("--focus-input", default=str(DEFAULT_FOCUS_INPUT))
    parser.add_argument("--backlog-input", default=str(DEFAULT_BACKLOG_INPUT))
    parser.add_argument("--patent-input", default=str(DEFAULT_PATENT_INPUT))
    parser.add_argument("--goldset-input", default=str(DEFAULT_GOLDSET_INPUT))
    parser.add_argument("--runtime-assertions-input", default=str(DEFAULT_RUNTIME_ASSERTIONS_INPUT))
    parser.add_argument("--widget-input", default=str(DEFAULT_WIDGET_INPUT))
    parser.add_argument("--api-contract-input", default=str(DEFAULT_API_CONTRACT_INPUT))
    parser.add_argument("--case-release-guard-input", default=str(DEFAULT_CASE_RELEASE_GUARD_INPUT))
    parser.add_argument("--review-case-presets-input", default=str(DEFAULT_REVIEW_CASE_PRESETS_INPUT))
    parser.add_argument("--case-story-surface-input", default=str(DEFAULT_CASE_STORY_SURFACE_INPUT))
    parser.add_argument("--preset-story-guard-input", default=str(DEFAULT_PRESET_STORY_GUARD_INPUT))
    parser.add_argument("--operator-demo-packet-input", default=str(DEFAULT_OPERATOR_DEMO_PACKET_INPUT))
    parser.add_argument("--release-bundle-input", default=str(DEFAULT_RELEASE_BUNDLE_INPUT))
    parser.add_argument("--ui-input", default=str(DEFAULT_UI_INPUT))
    parser.add_argument("--prompt-doc-input", default=str(DEFAULT_PROMPT_DOC_INPUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    master_input = Path(args.master_input).expanduser().resolve()
    provenance_input = Path(args.provenance_input).expanduser().resolve()
    focus_input = Path(args.focus_input).expanduser().resolve()
    backlog_input = Path(args.backlog_input).expanduser().resolve()
    patent_input = Path(args.patent_input).expanduser().resolve()
    goldset_input = Path(args.goldset_input).expanduser().resolve()
    runtime_assertions_input = Path(args.runtime_assertions_input).expanduser().resolve()
    widget_input = Path(args.widget_input).expanduser().resolve()
    api_contract_input = Path(args.api_contract_input).expanduser().resolve()
    case_release_guard_input = Path(args.case_release_guard_input).expanduser().resolve()
    review_case_presets_input = Path(args.review_case_presets_input).expanduser().resolve()
    case_story_surface_input = Path(args.case_story_surface_input).expanduser().resolve()
    preset_story_guard_input = Path(args.preset_story_guard_input).expanduser().resolve()
    operator_demo_packet_input = Path(args.operator_demo_packet_input).expanduser().resolve()
    release_bundle_input = Path(args.release_bundle_input).expanduser().resolve()
    ui_input = Path(args.ui_input).expanduser().resolve()
    prompt_doc_input = Path(args.prompt_doc_input).expanduser().resolve()

    report = build_brainstorm(
        master_catalog=_load_json(master_input),
        provenance_audit=_load_json(provenance_input),
        focus_report=_load_json(focus_input),
        source_upgrade_backlog=_load_json(backlog_input),
        permit_patent_evidence_bundle=_load_json(patent_input) if patent_input.exists() else {},
        permit_family_case_goldset=_load_json(goldset_input) if goldset_input.exists() else {},
        permit_runtime_case_assertions=_load_json(runtime_assertions_input) if runtime_assertions_input.exists() else {},
        widget_rental_catalog=_load_json(widget_input) if widget_input.exists() else {},
        api_contract_spec=_load_json(api_contract_input) if api_contract_input.exists() else {},
        permit_case_release_guard=_load_json(case_release_guard_input) if case_release_guard_input.exists() else {},
        permit_review_case_presets=_load_json(review_case_presets_input) if review_case_presets_input.exists() else {},
        permit_case_story_surface=_load_json(case_story_surface_input) if case_story_surface_input.exists() else {},
        permit_preset_story_release_guard=_load_json(preset_story_guard_input) if preset_story_guard_input.exists() else {},
        permit_operator_demo_packet=_load_json(operator_demo_packet_input) if operator_demo_packet_input.exists() else {},
        permit_release_bundle=_load_json(release_bundle_input) if release_bundle_input.exists() else {},
        runtime_html=_load_text(ui_input),
        prompt_doc=_load_text(prompt_doc_input),
    )

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
