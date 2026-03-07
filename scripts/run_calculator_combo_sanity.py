from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import acquisition_calculator
import yangdo_calculator


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def run_acquisition_combo_tests(cases: int = 120, seed: int = 42) -> Dict[str, Any]:
    rng = random.Random(seed)
    titles = [
        "AI 건설업 신규등록 비용 산정 계산기",
        "인허가(신규등록) 계산기 테스트",
        "Acq Calc QA",
        "",
    ]
    phones = ["010-9926-8661", "02-123-4567", "01012345678", ""]
    urls = [
        "",
        "https://example.com/chat",
        "https://seoulmna.co.kr/openchat",
        "javascript:alert(1)",
        "http://localhost:9000/internal",
    ]

    ok = 0
    for _ in range(cases):
        html = acquisition_calculator.build_page_html(
            title=rng.choice(titles),
            contact_phone=rng.choice(phones),
            openchat_url=rng.choice(urls),
            consult_endpoint=rng.choice(urls),
            usage_endpoint=rng.choice(urls),
        )
        _assert('id="acq-btn-calc"' in html, "acq calc button missing")
        _assert('id="acq-btn-copy"' in html, "acq copy button missing")
        _assert("const copyText = async" in html, "acq copy helper missing")
        _assert('id="acq-license-type"' in html, "acq license select missing")
        ok += 1
    return {"cases": cases, "passed": ok, "seed": seed}


def _sample_row(rng: random.Random, idx: int) -> Dict[str, Any]:
    price = round(rng.uniform(0.5, 20.0), 4)
    claim = round(price * rng.uniform(0.85, 1.25), 4)
    return {
        "uid": f"u{idx}",
        "number": idx + 1,
        "license_text": rng.choice(["실내건축공사업", "철근콘크리트공사업", "건축공사업"]),
        "license_tokens": {"건축", "공사업"},
        "license_year": rng.randint(1997, 2025),
        "specialty": round(rng.uniform(1, 180), 2),
        "years": {
            "y20": round(rng.uniform(0, 60), 2),
            "y21": round(rng.uniform(0, 60), 2),
            "y22": round(rng.uniform(0, 60), 2),
            "y23": round(rng.uniform(0, 60), 2),
            "y24": round(rng.uniform(0, 60), 2),
            "y25": round(rng.uniform(0, 60), 2),
        },
        "sales3_eok": round(rng.uniform(2, 200), 2),
        "sales5_eok": round(rng.uniform(3, 300), 2),
        "capital_eok": round(rng.uniform(0.5, 20), 2),
        "surplus_eok": round(rng.uniform(0, 12), 2),
        "debt_ratio": round(rng.uniform(0, 500), 2),
        "liq_ratio": round(rng.uniform(0, 2000), 2),
        "company_type": rng.choice(["주식회사", "유한회사", "개인"]),
        "location": rng.choice(["서울", "경기", "부산"]),
        "association": "",
        "shares": rng.randint(30, 350),
        "balance_eok": round(rng.uniform(0, 30), 2),
        "current_price_eok": price,
        "claim_price_eok": claim,
        "current_price_text": f"{price:.2f}억",
        "claim_price_text": f"{claim:.2f}억",
    }


def run_yangdo_combo_tests(cases: int = 120, seed: int = 7) -> Dict[str, Any]:
    rng = random.Random(seed)
    urls = ["", "https://example.com/c", "javascript:bad", "http://127.0.0.1:9011/x"]
    modes = ["customer", "owner", "invalid"]

    ok = 0
    for i in range(cases):
        rows = [_sample_row(rng, i * 10 + j) for j in range(rng.randint(5, 15))]
        dataset = yangdo_calculator.build_training_dataset(rows, site_url="https://seoulmna.co.kr")
        enable_consult_widget = bool(rng.randint(0, 1))
        enable_hot_match = bool(rng.randint(0, 1))
        html = yangdo_calculator.build_page_html(
            dataset,
            {"generated": True, "idx": i},
            view_mode=rng.choice(modes),
            consult_endpoint=rng.choice(urls),
            usage_endpoint=rng.choice(urls),
            estimate_endpoint=rng.choice(urls),
            openchat_url=rng.choice(urls),
            enable_consult_widget=enable_consult_widget,
            enable_hot_match=enable_hot_match,
        )
        _assert('id="btn-estimate"' in html, "yangdo estimate button missing")
        _assert('id="btn-copy-result"' in html, "yangdo copy result button missing")
        _assert("const copyText = async" in html, "yangdo copy helper missing")
        _assert("const topK = 12;" in html, "yangdo local estimator topK default missing")
        _assert(('id="btn-copy-consult"' in html) == enable_consult_widget, "yangdo consult widget toggle mismatch")
        _assert(('id="hot-match-cta"' in html) == enable_hot_match, "yangdo hot-match toggle mismatch")
        ok += 1
    return {"cases": cases, "passed": ok, "seed": seed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run combo sanity checks for acquisition/yangdo calculators")
    parser.add_argument("--acq-cases", type=int, default=120)
    parser.add_argument("--yangdo-cases", type=int, default=120)
    parser.add_argument("--acq-seed", type=int, default=42)
    parser.add_argument("--yangdo-seed", type=int, default=7)
    args = parser.parse_args()

    acq = run_acquisition_combo_tests(cases=max(1, args.acq_cases), seed=args.acq_seed)
    yg = run_yangdo_combo_tests(cases=max(1, args.yangdo_cases), seed=args.yangdo_seed)
    print(json.dumps({"acquisition": acq, "yangdo": yg}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

