from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, asdict


@dataclass
class PlanAssumption:
    name: str
    yangdo_runs_month: int
    permit_runs_month: int
    yangdo_tokens_per_ai_run: int
    permit_tokens_per_ai_run: int
    ai_usage_ratio: float
    fixed_ops_usd: float
    support_usd: float
    target_margin: float


@dataclass
class PricingResult:
    name: str
    monthly_tokens: int
    monthly_input_tokens: int
    monthly_output_tokens: int
    api_cost_usd: float
    fixed_cost_usd: float
    total_cost_usd: float
    recommended_price_usd: float
    included_tokens: int
    overage_price_per_1k_tokens_usd: float


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _compute_plan(
    plan: PlanAssumption,
    input_rate_per_1m: float,
    output_rate_per_1m: float,
    input_token_ratio: float,
) -> PricingResult:
    token_ratio_in = _clamp01(input_token_ratio)
    token_ratio_out = 1.0 - token_ratio_in
    ai_ratio = _clamp01(plan.ai_usage_ratio)

    monthly_tokens = int(
        (plan.yangdo_runs_month * plan.yangdo_tokens_per_ai_run
         + plan.permit_runs_month * plan.permit_tokens_per_ai_run)
        * ai_ratio
    )
    monthly_input_tokens = int(monthly_tokens * token_ratio_in)
    monthly_output_tokens = max(0, monthly_tokens - monthly_input_tokens)

    api_cost = (
        (monthly_input_tokens / 1_000_000.0) * max(0.0, input_rate_per_1m)
        + (monthly_output_tokens / 1_000_000.0) * max(0.0, output_rate_per_1m)
    )
    fixed_cost = max(0.0, plan.fixed_ops_usd) + max(0.0, plan.support_usd)
    total_cost = api_cost + fixed_cost

    margin = max(0.0, min(0.95, plan.target_margin))
    recommended_price = total_cost / max(0.05, (1.0 - margin))

    included_tokens = int(math.ceil(monthly_tokens * 1.15 / 10_000.0) * 10_000)

    blended_token_cost_per_1k = (
        (token_ratio_in * input_rate_per_1m + token_ratio_out * output_rate_per_1m) / 1000.0
    )
    overage_price_per_1k = blended_token_cost_per_1k / max(0.05, (1.0 - margin))
    if monthly_tokens <= 0:
        included_tokens = 0
        overage_price_per_1k = 0.0

    return PricingResult(
        name=plan.name,
        monthly_tokens=monthly_tokens,
        monthly_input_tokens=monthly_input_tokens,
        monthly_output_tokens=monthly_output_tokens,
        api_cost_usd=round(api_cost, 4),
        fixed_cost_usd=round(fixed_cost, 4),
        total_cost_usd=round(total_cost, 4),
        recommended_price_usd=round(recommended_price, 2),
        included_tokens=included_tokens,
        overage_price_per_1k_tokens_usd=round(overage_price_per_1k, 4),
    )


def build_default_plans() -> tuple[PlanAssumption, PlanAssumption, PlanAssumption]:
    # seoulmna.co.kr ?? ??: ?? ?? ??(?? API ?? 0)
    internal = PlanAssumption(
        name="seoul-internal",
        yangdo_runs_month=6000,
        permit_runs_month=2800,
        yangdo_tokens_per_ai_run=0,
        permit_tokens_per_ai_run=0,
        ai_usage_ratio=0.0,
        fixed_ops_usd=45.0,
        support_usd=35.0,
        target_margin=0.0,
    )

    # ??? ???: ?? ??? ?? ??, ??? AI ?? ??? ?? ??
    standard = PlanAssumption(
        name="partner-standard",
        yangdo_runs_month=1400,
        permit_runs_month=800,
        yangdo_tokens_per_ai_run=0,
        permit_tokens_per_ai_run=900,
        ai_usage_ratio=0.35,
        fixed_ops_usd=40.0,
        support_usd=30.0,
        target_margin=0.55,
    )

    # ??? PRO: ?? ??/????/?????? ?? ??? ??
    pro = PlanAssumption(
        name="partner-pro",
        yangdo_runs_month=3200,
        permit_runs_month=1600,
        yangdo_tokens_per_ai_run=1200,
        permit_tokens_per_ai_run=2400,
        ai_usage_ratio=0.65,
        fixed_ops_usd=70.0,
        support_usd=90.0,
        target_margin=0.60,
    )

    return internal, standard, pro


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate token cost and recommended pricing for Yangdo/Permit plans")
    parser.add_argument("--input-rate-per-1m", type=float, default=0.40, help="USD per 1M input tokens")
    parser.add_argument("--output-rate-per-1m", type=float, default=1.60, help="USD per 1M output tokens")
    parser.add_argument("--input-token-ratio", type=float, default=0.70, help="Input token ratio (0~1)")
    parser.add_argument("--json", action="store_true", help="Output json only")
    args = parser.parse_args()

    internal, standard, pro = build_default_plans()
    results = [
        _compute_plan(internal, args.input_rate_per_1m, args.output_rate_per_1m, args.input_token_ratio),
        _compute_plan(standard, args.input_rate_per_1m, args.output_rate_per_1m, args.input_token_ratio),
        _compute_plan(pro, args.input_rate_per_1m, args.output_rate_per_1m, args.input_token_ratio),
    ]

    payload = {
        "assumptions": {
            "input_rate_per_1m": args.input_rate_per_1m,
            "output_rate_per_1m": args.output_rate_per_1m,
            "input_token_ratio": args.input_token_ratio,
            "output_token_ratio": round(1.0 - args.input_token_ratio, 4),
        },
        "plans": [asdict(r) for r in results],
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("=== Token Pricing Simulation ===")
    print(json.dumps(payload["assumptions"], ensure_ascii=False))
    for row in results:
        print(
            f"[{row.name}] tokens={row.monthly_tokens:,} "
            f"api=${row.api_cost_usd:.4f} total=${row.total_cost_usd:.2f} "
            f"price_floor=${row.recommended_price_usd:.2f} included_tokens={row.included_tokens:,} "
            f"overage_per_1k=${row.overage_price_per_1k_tokens_usd:.4f}"
        )
    print("\n-- JSON --")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
