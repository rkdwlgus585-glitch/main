import argparse
import importlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def inspect_backend(module_name):
    name = str(module_name or "").strip()
    result = {
        "module": name,
        "import_ok": False,
        "module_file": "",
        "symbols": {
            "ListingSheetLookup": False,
            "GabjiGenerator": False,
            "ListingSheetLookup.load_listing": False,
            "GabjiGenerator.analyze_image": False,
            "extract_final_yangdo_price": False,
        },
        "ready_for_registration": False,
        "ready_for_image": False,
        "ready_for_report_pipeline": False,
        "errors": [],
    }
    if not name:
        result["errors"].append("empty_module_name")
        return result

    try:
        mod = importlib.import_module(name)
    except Exception as exc:
        result["errors"].append(f"import_failed:{type(exc).__name__}:{exc}")
        return result

    result["import_ok"] = True
    result["module_file"] = str(getattr(mod, "__file__", "") or "")

    listing_cls = getattr(mod, "ListingSheetLookup", None)
    generator_cls = getattr(mod, "GabjiGenerator", None)
    result["symbols"]["ListingSheetLookup"] = listing_cls is not None
    result["symbols"]["GabjiGenerator"] = generator_cls is not None
    result["symbols"]["extract_final_yangdo_price"] = hasattr(mod, "extract_final_yangdo_price")

    if listing_cls is not None and hasattr(listing_cls, "load_listing"):
        result["symbols"]["ListingSheetLookup.load_listing"] = True
    if generator_cls is not None and hasattr(generator_cls, "analyze_image"):
        result["symbols"]["GabjiGenerator.analyze_image"] = True

    result["ready_for_registration"] = (
        result["symbols"]["ListingSheetLookup"]
        and result["symbols"]["ListingSheetLookup.load_listing"]
    )
    result["ready_for_image"] = (
        result["symbols"]["GabjiGenerator"]
        and result["symbols"]["GabjiGenerator.analyze_image"]
    )
    result["ready_for_report_pipeline"] = (
        result["ready_for_registration"] and result["symbols"]["GabjiGenerator"]
    )
    return result


def choose_recommended_backend(results):
    for preferred in ("gb2_v3", "gabji"):
        for row in results:
            if row.get("module") == preferred and row.get("ready_for_report_pipeline"):
                return preferred
    for row in results:
        if row.get("ready_for_report_pipeline"):
            return row.get("module", "")
    return ""


def main():
    parser = argparse.ArgumentParser(description="gb2_v3/gabji 백엔드 연동 가능성 진단")
    parser.add_argument(
        "--modules",
        default="gb2_v3,gabji",
        help="점검할 모듈 목록(콤마 구분), 기본: gb2_v3,gabji",
    )
    parser.add_argument("--out", default="", help="진단 JSON 저장 경로(미입력 시 콘솔만 출력)")
    args = parser.parse_args()

    modules = [x.strip() for x in str(args.modules).split(",") if x.strip()]
    rows = [inspect_backend(name) for name in modules]
    recommended = choose_recommended_backend(rows)
    payload = {
        "workspace": str(ROOT),
        "requested_modules": modules,
        "results": rows,
        "recommended_backend": recommended,
        "cli_hint": f"--gabji-backend {recommended}" if recommended else "",
        "ready": bool(recommended),
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + os.linesep, encoding="utf-8")
        print(f"[saved] {out_path}")
    return 0 if payload["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
