#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / 'logs'
DEFAULT_BALANCE_CV_INPUT = LOG_DIR / 'yangdo_balance_base_cv_latest.json'
DEFAULT_SECTOR_AUDIT_INPUT = LOG_DIR / 'yangdo_sector_price_audit_latest.json'
DEFAULT_JSON_OUTPUT = LOG_DIR / 'yangdo_none_mode_sector_experiment_latest.json'
DEFAULT_MD_OUTPUT = LOG_DIR / 'yangdo_none_mode_sector_experiment_latest.md'

for candidate in (ROOT, Path(__file__).resolve().parent):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import yangdo_blackbox_api

SECTOR_ELECTRIC = '\uC804\uAE30'
SECTOR_INFOCOMM = '\uC815\uBCF4\uD1B5\uC2E0'
SECTOR_FIRE = '\uC18C\uBC29'
TOKEN_TELECOM = '\uD1B5\uC2E0'

FOCUS_SECTORS = [SECTOR_ELECTRIC, SECTOR_INFOCOMM, SECTOR_FIRE]
SECTOR_MAX_OVER_INCREASE = {
    SECTOR_ELECTRIC: 2,
    SECTOR_INFOCOMM: 1,
    SECTOR_FIRE: 1,
}
BLEND_GRID = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55]
CAP_Q_GRID = [0.55, 0.60, 0.65, 0.70, 0.75]
CAP_MULT_GRID = [0.98, 1.00, 1.02, 1.05]
CURRENT_CAP_MULT = 1.60
Q25_FLOOR_MULT = 0.90


@dataclass(frozen=True)
class EvalRow:
    sector: str
    uid: str
    number: int
    actual_price_eok: float
    current_pred_eok: float
    signal_eok: Optional[float]
    prior_estimate_eok: float
    q25_price_eok: float
    q55_price_eok: float
    q60_price_eok: float
    q65_price_eok: float
    q70_price_eok: float
    q75_price_eok: float


def _now_str() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == '':
            return None
        return float(value)
    except Exception:
        return None


def _round4(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), 4)


def _quantile(values: Iterable[float], q: float) -> float:
    seq = sorted(float(v) for v in values)
    if not seq:
        return 0.0
    if len(seq) == 1:
        return seq[0]
    idx = (len(seq) - 1) * q
    lo = int(idx)
    hi = min(len(seq) - 1, lo + 1)
    frac = idx - lo
    return seq[lo] * (1.0 - frac) + seq[hi] * frac


def _trimmed_median(values: Iterable[float], lower_q: float = 0.20, upper_q: float = 0.80) -> float:
    seq = sorted(float(v) for v in values)
    if not seq:
        return 0.0
    lo = _quantile(seq, lower_q)
    hi = _quantile(seq, upper_q)
    trimmed = [value for value in seq if lo <= value <= hi]
    return float(statistics.median(trimmed or seq))


def _signal_from_record(record: Dict[str, Any]) -> Optional[float]:
    sales3 = _safe_float(record.get('sales3_eok'))
    sigpyeong = _safe_float(record.get('sigpyeong_eok'))
    if sales3 is not None and sigpyeong is not None:
        return 0.65 * sales3 + 0.35 * sigpyeong
    if sales3 is not None:
        return sales3
    if sigpyeong is not None:
        return sigpyeong
    return None


def _sector_from_tokens(tokens: Iterable[Any]) -> Optional[str]:
    token_set = {str(token or '').strip() for token in tokens or [] if str(token or '').strip()}
    if len(token_set) != 1:
        return None
    if SECTOR_ELECTRIC in token_set:
        return SECTOR_ELECTRIC
    if SECTOR_INFOCOMM in token_set or TOKEN_TELECOM in token_set:
        return SECTOR_INFOCOMM
    if SECTOR_FIRE in token_set:
        return SECTOR_FIRE
    return None


def _focus_sectors_from_audit(sector_audit: Dict[str, Any]) -> List[str]:
    for action in sector_audit.get('next_actions') or []:
        if str(action.get('id') or '') == 'none_mode_sector_calibration':
            sectors = [str(value or '').strip() for value in action.get('focus_sectors') or [] if str(value or '').strip()]
            if sectors:
                return sectors
    return list(FOCUS_SECTORS)


def _prepare_eval_rows(balance_cv: Dict[str, Any], focus_sectors: List[str]) -> Dict[str, List[EvalRow]]:
    estimator = yangdo_blackbox_api.YangdoBlackboxEstimator()
    estimator.refresh()
    records, _token_index, _meta = estimator._snapshot()
    record_map = {(str(record.get('uid') or ''), int(record.get('number') or 0)): record for record in records}

    sector_raw_rows: Dict[str, List[Dict[str, Any]]] = {sector: [] for sector in focus_sectors}
    for row in balance_cv.get('record_rows') or []:
        if str(row.get('balance_model_mode') or '') != 'none':
            continue
        if int(row.get('combo_size') or 0) != 1:
            continue
        record = record_map.get((str(row.get('uid') or ''), int(row.get('number') or 0)))
        if not record:
            continue
        sector = _sector_from_tokens(record.get('license_tokens') or [])
        if sector not in focus_sectors:
            continue
        actual = _safe_float(row.get('actual_price_eok'))
        current_pred = _safe_float(row.get('engine_internal_pred_eok'))
        if actual is None or actual <= 0 or current_pred is None or current_pred <= 0:
            continue
        sector_raw_rows[sector].append(
            {
                'sector': sector,
                'uid': str(row.get('uid') or ''),
                'number': int(row.get('number') or 0),
                'actual_price_eok': actual,
                'current_pred_eok': current_pred,
                'signal_eok': _signal_from_record(record),
            }
        )

    prepared: Dict[str, List[EvalRow]] = {sector: [] for sector in focus_sectors}
    for sector, rows in sector_raw_rows.items():
        for item in rows:
            peers = [peer for peer in rows if not (peer['uid'] == item['uid'] and peer['number'] == item['number'])]
            price_peers = [float(peer['actual_price_eok']) for peer in peers if float(peer['actual_price_eok']) > 0]
            if len(price_peers) < 3:
                continue
            ratio_peers = []
            for peer in peers:
                signal = peer.get('signal_eok')
                actual = float(peer['actual_price_eok'])
                if signal is not None and signal > 0 and actual > 0:
                    ratio_peers.append(actual / signal)
            target_signal = item.get('signal_eok')
            if ratio_peers and target_signal is not None and target_signal > 0:
                prior_estimate = target_signal * _trimmed_median(ratio_peers)
            else:
                prior_estimate = float(statistics.median(price_peers))
            prepared[sector].append(
                EvalRow(
                    sector=sector,
                    uid=item['uid'],
                    number=item['number'],
                    actual_price_eok=float(item['actual_price_eok']),
                    current_pred_eok=float(item['current_pred_eok']),
                    signal_eok=item['signal_eok'],
                    prior_estimate_eok=float(prior_estimate),
                    q25_price_eok=_quantile(price_peers, 0.25),
                    q55_price_eok=_quantile(price_peers, 0.55),
                    q60_price_eok=_quantile(price_peers, 0.60),
                    q65_price_eok=_quantile(price_peers, 0.65),
                    q70_price_eok=_quantile(price_peers, 0.70),
                    q75_price_eok=_quantile(price_peers, 0.75),
                )
            )
    return prepared


def _candidate_prediction(row: EvalRow, *, blend: float, cap_quantile: float, cap_mult: float) -> float:
    quantile_value = {
        0.55: row.q55_price_eok,
        0.60: row.q60_price_eok,
        0.65: row.q65_price_eok,
        0.70: row.q70_price_eok,
        0.75: row.q75_price_eok,
    }.get(round(cap_quantile, 2), row.q65_price_eok)
    uplift = max(0.0, row.prior_estimate_eok - row.current_pred_eok)
    predicted = row.current_pred_eok + (blend * uplift)
    floor_value = max(row.current_pred_eok, row.q25_price_eok * Q25_FLOOR_MULT)
    cap_value = min(quantile_value * cap_mult, row.current_pred_eok * CURRENT_CAP_MULT)
    return max(floor_value, min(predicted, cap_value))


def _metrics_from_predictions(rows: List[EvalRow], params: Optional[Tuple[float, float, float]] = None) -> Dict[str, Any]:
    abs_pcts: List[float] = []
    signed_pcts: List[float] = []
    over_150 = 0
    under_67 = 0
    predictions: List[Dict[str, Any]] = []
    for row in rows:
        predicted = row.current_pred_eok if params is None else _candidate_prediction(row, blend=params[0], cap_quantile=params[1], cap_mult=params[2])
        ratio = predicted / row.actual_price_eok
        abs_pct = abs(ratio - 1.0) * 100.0
        signed_pct = (ratio - 1.0) * 100.0
        abs_pcts.append(abs_pct)
        signed_pcts.append(signed_pct)
        over_150 += int(ratio > 1.5)
        under_67 += int(ratio < 0.67)
        predictions.append(
            {
                'uid': row.uid,
                'number': row.number,
                'actual_price_eok': _round4(row.actual_price_eok),
                'current_pred_eok': _round4(row.current_pred_eok),
                'prior_estimate_eok': _round4(row.prior_estimate_eok),
                'candidate_pred_eok': _round4(predicted),
                'signal_eok': _round4(row.signal_eok),
                'ratio_vs_actual': _round4(ratio),
            }
        )
    count = len(rows)
    return {
        'count': count,
        'median_abs_pct': _round4(statistics.median(abs_pcts)) if abs_pcts else 0.0,
        'median_signed_pct': _round4(statistics.median(signed_pcts)) if signed_pcts else 0.0,
        'pred_lt_actual_0_67x': under_67,
        'pred_gt_actual_1_5x': over_150,
        'under_67_share': _round4((under_67 / count) if count else 0.0),
        'over_150_share': _round4((over_150 / count) if count else 0.0),
        'predictions': predictions,
    }


def _candidate_score(metrics: Dict[str, Any], baseline: Dict[str, Any], sector: str) -> float:
    max_allowed_over = int(baseline.get('pred_gt_actual_1_5x') or 0) + SECTOR_MAX_OVER_INCREASE.get(sector, 1)
    under_share = float(metrics.get('under_67_share') or 0.0)
    over_excess = max(0, int(metrics.get('pred_gt_actual_1_5x') or 0) - max_allowed_over)
    abs_drift = max(0.0, float(metrics.get('median_abs_pct') or 0.0) - float(baseline.get('median_abs_pct') or 0.0))
    return under_share + (0.05 * over_excess) + (0.001 * abs_drift)


def _search_sector(rows: List[EvalRow], sector: str) -> Dict[str, Any]:
    baseline = _metrics_from_predictions(rows, None)
    best: Optional[Dict[str, Any]] = None
    conservative: Optional[Dict[str, Any]] = None
    max_allowed_over = int(baseline.get('pred_gt_actual_1_5x') or 0) + SECTOR_MAX_OVER_INCREASE.get(sector, 1)
    for blend in BLEND_GRID:
        for cap_quantile in CAP_Q_GRID:
            for cap_mult in CAP_MULT_GRID:
                metrics = _metrics_from_predictions(rows, (blend, cap_quantile, cap_mult))
                candidate = {
                    'blend': blend,
                    'cap_quantile': cap_quantile,
                    'cap_mult': cap_mult,
                    'metrics': {k: v for k, v in metrics.items() if k != 'predictions'},
                    'score': _round4(_candidate_score(metrics, baseline, sector)),
                }
                if best is None or float(candidate['score']) < float(best['score']):
                    best = candidate
                if int(metrics.get('pred_gt_actual_1_5x') or 0) <= max_allowed_over:
                    if conservative is None:
                        conservative = candidate
                    else:
                        conservative_key = (
                            float(conservative['metrics']['under_67_share']),
                            float(conservative['metrics']['median_abs_pct']),
                        )
                        candidate_key = (
                            float(candidate['metrics']['under_67_share']),
                            float(candidate['metrics']['median_abs_pct']),
                        )
                        if candidate_key < conservative_key:
                            conservative = candidate
    assert best is not None
    best_metrics_full = _metrics_from_predictions(rows, (best['blend'], best['cap_quantile'], best['cap_mult']))
    best['sample_predictions'] = sorted(best_metrics_full['predictions'], key=lambda item: abs(float(item['ratio_vs_actual'] or 0.0) - 1.0), reverse=True)[:8]
    conservative_full = None
    if conservative is not None:
        conservative_metrics_full = _metrics_from_predictions(rows, (conservative['blend'], conservative['cap_quantile'], conservative['cap_mult']))
        conservative_full = dict(conservative)
        conservative_full['sample_predictions'] = sorted(
            conservative_metrics_full['predictions'],
            key=lambda item: abs(float(item['ratio_vs_actual'] or 0.0) - 1.0),
            reverse=True,
        )[:8]
    return {
        'sector': sector,
        'baseline': {k: v for k, v in baseline.items() if k != 'predictions'},
        'best_candidate': best,
        'conservative_candidate': conservative_full,
        'max_allowed_over_150_count': max_allowed_over,
        'signal_coverage_share': _round4(sum(1 for row in rows if row.signal_eok is not None and row.signal_eok > 0) / len(rows)) if rows else 0.0,
        'record_count': len(rows),
    }


def _search_global(rows_by_sector: Dict[str, List[EvalRow]]) -> Dict[str, Any]:
    baseline_under = 0
    baseline_over = 0
    baseline_count = 0
    for rows in rows_by_sector.values():
        baseline = _metrics_from_predictions(rows, None)
        baseline_under += int(baseline['pred_lt_actual_0_67x'])
        baseline_over += int(baseline['pred_gt_actual_1_5x'])
        baseline_count += int(baseline['count'])
    best: Optional[Dict[str, Any]] = None
    for blend in BLEND_GRID:
        for cap_quantile in CAP_Q_GRID:
            for cap_mult in CAP_MULT_GRID:
                total_under = 0
                total_over = 0
                total_count = 0
                sector_breakdown = {}
                for sector, rows in rows_by_sector.items():
                    metrics = _metrics_from_predictions(rows, (blend, cap_quantile, cap_mult))
                    sector_breakdown[sector] = {k: v for k, v in metrics.items() if k != 'predictions'}
                    total_under += int(metrics['pred_lt_actual_0_67x'])
                    total_over += int(metrics['pred_gt_actual_1_5x'])
                    total_count += int(metrics['count'])
                under_share = (total_under / total_count) if total_count else 0.0
                over_excess = max(0, total_over - (baseline_over + 4))
                score = under_share + (0.04 * over_excess)
                candidate = {
                    'blend': blend,
                    'cap_quantile': cap_quantile,
                    'cap_mult': cap_mult,
                    'combined_under_67_share': _round4(under_share),
                    'combined_pred_gt_actual_1_5x': total_over,
                    'score': _round4(score),
                    'sector_breakdown': sector_breakdown,
                }
                if best is None or float(candidate['score']) < float(best['score']):
                    best = candidate
    assert best is not None
    best['baseline_combined_under_67_share'] = _round4((baseline_under / baseline_count) if baseline_count else 0.0)
    best['baseline_combined_pred_gt_actual_1_5x'] = baseline_over
    return best


def _critical_takeaways(sector_results: List[Dict[str, Any]], global_candidate: Dict[str, Any]) -> List[str]:
    takeaways: List[str] = []
    baseline_under = sum(int(item['baseline']['pred_lt_actual_0_67x']) for item in sector_results)
    best_under = sum(int(item['best_candidate']['metrics']['pred_lt_actual_0_67x']) for item in sector_results)
    baseline_over = sum(int(item['baseline']['pred_gt_actual_1_5x']) for item in sector_results)
    best_over = sum(int(item['best_candidate']['metrics']['pred_gt_actual_1_5x']) for item in sector_results)
    takeaways.append(
        f"sector-specific bounded prior lowers under-0.67x from {baseline_under} to {best_under} while over-1.5x moves from {baseline_over} to {best_over}."
    )
    if int(global_candidate['combined_pred_gt_actual_1_5x']) > best_over:
        takeaways.append(
            'one global parameter set is weaker than sector-specific tuning; electric needs a tighter cap than infocomm or fire.'
        )
    for item in sector_results:
        sector = item['sector']
        baseline = item['baseline']
        best_candidate = item['best_candidate']
        takeaways.append(
            f"{sector}: under-0.67x {baseline['under_67_share']} -> {best_candidate['metrics']['under_67_share']}, over-1.5x {baseline['pred_gt_actual_1_5x']} -> {best_candidate['metrics']['pred_gt_actual_1_5x']}."
        )
        conservative_candidate = item.get('conservative_candidate')
        if conservative_candidate is None:
            takeaways.append(
                f"{sector}: no bounded-prior candidate stays within the strict overpricing budget ({item['max_allowed_over_150_count']}); this lane still needs a tighter cohort or publication lock."
            )
        else:
            takeaways.append(
                f"{sector}: conservative candidate stays within overpricing budget and lowers under-0.67x to {conservative_candidate['metrics']['under_67_share']}."
            )
    return takeaways


def _next_actions(sector_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    for item in sector_results:
        selected = item.get('conservative_candidate') or item['best_candidate']
        actions.append(
            {
                'sector': item['sector'],
                'recommended_patch': {
                    'blend': selected['blend'],
                    'cap_quantile': selected['cap_quantile'],
                    'cap_mult': selected['cap_mult'],
                },
                'patch_readiness': 'candidate_only' if item.get('conservative_candidate') is None else 'ready_for_guarded_patch',
                'why': (
                    'same-sector bounded prior reduces none-mode underpricing without using a balance-base shortcut; '
                    'keep it sector-scoped until exact-combo recovery is solved.'
                ),
            }
        )
    actions.append(
        {
            'global_follow_up': 'apply this bounded prior only to none-mode single-license sectors first, then rerun exact-combo recovery for 토목/포장/상하수도/조경/토건/석공/석면/시설물 before widening publication.',
        }
    )
    return actions


def build_report(balance_cv: Dict[str, Any], sector_audit: Dict[str, Any]) -> Dict[str, Any]:
    focus_sectors = _focus_sectors_from_audit(sector_audit)
    rows_by_sector = _prepare_eval_rows(balance_cv, focus_sectors)
    sector_results = [_search_sector(rows_by_sector[sector], sector) for sector in focus_sectors if rows_by_sector.get(sector)]
    global_candidate = _search_global({item['sector']: rows_by_sector[item['sector']] for item in sector_results})
    return {
        'generated_at': _now_str(),
        'focus_sectors': focus_sectors,
        'sector_results': sector_results,
        'global_candidate': global_candidate,
        'critical_takeaways': _critical_takeaways(sector_results, global_candidate),
        'next_actions': _next_actions(sector_results),
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        '# Yangdo None-Mode Sector Experiment',
        '',
        f"- generated_at: {report['generated_at']}",
        f"- focus_sectors: {', '.join(report.get('focus_sectors') or [])}",
        '',
        '## Critical Takeaways',
    ]
    for item in report.get('critical_takeaways') or []:
        lines.append(f'- {item}')
    lines.extend(['', '## Sector Results'])
    for item in report.get('sector_results') or []:
        baseline = item['baseline']
        best_candidate = item['best_candidate']
        lines.append(f"### {item['sector']}")
        lines.append(f"- record_count: {item['record_count']}")
        lines.append(f"- signal_coverage_share: {item['signal_coverage_share']}")
        lines.append(f"- baseline_under_67_share: {baseline['under_67_share']}")
        lines.append(f"- baseline_over_150_count: {baseline['pred_gt_actual_1_5x']}")
        lines.append(
            f"- best_candidate: blend={best_candidate['blend']}, cap_q={best_candidate['cap_quantile']}, cap_mult={best_candidate['cap_mult']}"
        )
        lines.append(f"- candidate_under_67_share: {best_candidate['metrics']['under_67_share']}")
        lines.append(f"- candidate_over_150_count: {best_candidate['metrics']['pred_gt_actual_1_5x']}")
        lines.append(f"- candidate_median_abs_pct: {best_candidate['metrics']['median_abs_pct']}")
        lines.append(f"- max_allowed_over_150_count: {item['max_allowed_over_150_count']}")
        conservative_candidate = item.get('conservative_candidate')
        if conservative_candidate is None:
            lines.append('- conservative_candidate: none within strict overpricing budget')
        else:
            lines.append(
                f"- conservative_candidate: blend={conservative_candidate['blend']}, cap_q={conservative_candidate['cap_quantile']}, cap_mult={conservative_candidate['cap_mult']}"
            )
            lines.append(f"- conservative_under_67_share: {conservative_candidate['metrics']['under_67_share']}")
            lines.append(f"- conservative_over_150_count: {conservative_candidate['metrics']['pred_gt_actual_1_5x']}")
    lines.extend(['', '## Global Candidate'])
    global_candidate = report.get('global_candidate') or {}
    lines.append(
        f"- global_candidate: blend={global_candidate.get('blend')}, cap_q={global_candidate.get('cap_quantile')}, cap_mult={global_candidate.get('cap_mult')}"
    )
    lines.append(f"- baseline_combined_under_67_share: {global_candidate.get('baseline_combined_under_67_share')}")
    lines.append(f"- combined_under_67_share: {global_candidate.get('combined_under_67_share')}")
    lines.append(f"- baseline_combined_over_150_count: {global_candidate.get('baseline_combined_pred_gt_actual_1_5x')}")
    lines.append(f"- combined_over_150_count: {global_candidate.get('combined_pred_gt_actual_1_5x')}")
    lines.extend(['', '## Next Actions'])
    for item in report.get('next_actions') or []:
        lines.append(f'- {json.dumps(item, ensure_ascii=False)}')
    return '\n'.join(lines).strip() + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Evaluate bounded core prior candidates for none-mode sectors')
    parser.add_argument('--balance-cv-input', default=str(DEFAULT_BALANCE_CV_INPUT))
    parser.add_argument('--sector-audit-input', default=str(DEFAULT_SECTOR_AUDIT_INPUT))
    parser.add_argument('--json-output', default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument('--md-output', default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    balance_cv = _load_json(Path(args.balance_cv_input))
    sector_audit = _load_json(Path(args.sector_audit_input))
    report = build_report(balance_cv, sector_audit)

    json_output = Path(args.json_output)
    md_output = Path(args.md_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    md_output.write_text(render_markdown(report), encoding='utf-8')

    print(json.dumps({
        'ok': True,
        'generated_at': report['generated_at'],
        'json_output': str(json_output),
        'md_output': str(md_output),
        'focus_sectors': report['focus_sectors'],
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
