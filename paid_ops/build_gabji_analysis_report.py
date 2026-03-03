import argparse
import importlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _desktop_output_dir():
    user_profile = os.environ.get("USERPROFILE", "").strip()
    home = os.path.expanduser("~")
    candidates = []
    if user_profile:
        candidates.append(os.path.join(user_profile, "Desktop"))
    candidates.append(os.path.join(home, "Desktop"))
    for path in candidates:
        if path and os.path.isdir(path):
            return path
    return user_profile or home or os.getcwd()


def _default_output_path(registration_no=""):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{registration_no}" if str(registration_no or "").strip() else ""
    return os.path.join(_desktop_output_dir(), f"maemul_analysis_report{suffix}_{stamp}.pdf")


def _resolve_backend_module(module_name=""):
    name = str(module_name or "gabji").strip() or "gabji"
    module = importlib.import_module(name)
    missing = []
    if not hasattr(module, "ListingSheetLookup"):
        missing.append("ListingSheetLookup")
    if not hasattr(module, "GabjiGenerator"):
        missing.append("GabjiGenerator")
    return module, name, missing


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]


def _digits(value):
    return re.sub(r"\D+", "", str(value or ""))


def _to_float_number(value):
    src = str(value or "").strip().replace(",", "")
    if not src or src in {"-", "--", "none", "None"}:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", src)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _fmt_eok(value):
    num = _to_float_number(value)
    if num is None:
        return "-"
    if abs(num - round(num)) < 1e-9:
        return f"{int(round(num))}억"
    return f"{num:.1f}억"


def _pick_first(dct, keys, default=""):
    src = dct if isinstance(dct, dict) else {}
    for key in keys:
        if key in src and str(src.get(key, "")).strip():
            return src.get(key)
    return default


def _get_rows(data):
    src = data if isinstance(data, dict) else {}
    value = _pick_first(
        src,
        [
            "업종정보",
            "?낆쥌?뺣낫",
            "industry_rows",
            "rows",
        ],
        [],
    )
    return value if isinstance(value, list) else []


def _get_notes(data):
    src = data if isinstance(data, dict) else {}
    notes = _as_list(_pick_first(src, ["비고", "鍮꾧퀬", "notes"], []))
    admin = _as_list(_pick_first(src, ["행정사항", "?됱젙?ы빆", "admin_notes"], []))
    merged = []
    seen = set()
    for line in notes + admin:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(line)
    return merged


def _sales_for_year(sales_dict, year):
    src = sales_dict if isinstance(sales_dict, dict) else {}
    wanted = str(year)
    for key, value in src.items():
        if _digits(key)[:4] == wanted:
            return value
    return None


def _calc_year_sum(sales_dict, year_keys):
    total = 0.0
    found = False
    for year in year_keys:
        v = _to_float_number(_sales_for_year(sales_dict, year))
        if v is None:
            continue
        total += v
        found = True
    return round(total, 1) if found else None


def _sum_field_value(row, keys):
    src = row if isinstance(row, dict) else {}
    return _to_float_number(_pick_first(src, keys, None))


def _validate_sales_sums(rows, tolerance=0.11):
    issues = []
    for idx, row in enumerate(rows or [], start=1):
        src = row if isinstance(row, dict) else {}
        sales = _pick_first(src, ["매출", "留ㅼ텧", "sales"], {})
        name = str(_pick_first(src, ["업종", "?낆쥌", "industry"], f"row{idx}")).strip() or f"row{idx}"
        raw3 = _sum_field_value(src, ["3년합계", "3?꾪빀怨?", "sum3"])
        raw5 = _sum_field_value(src, ["5년합계", "5?꾪빀怨?", "sum5"])
        calc3 = _calc_year_sum(sales, ["2023", "2024", "2025"])
        calc5 = _calc_year_sum(sales, ["2021", "2022", "2023", "2024", "2025"])

        if raw3 is not None and calc3 is not None and abs(raw3 - calc3) > tolerance:
            issues.append({"row": idx, "name": name, "type": "sum3_mismatch", "raw": raw3, "calc": calc3})
        if raw5 is not None and calc5 is not None and abs(raw5 - calc5) > tolerance:
            issues.append({"row": idx, "name": name, "type": "sum5_mismatch", "raw": raw5, "calc": calc5})
    return issues


def _recommend_report_image_count(rows, note_lines):
    row_count = len(rows or [])
    note_count = len([x for x in (note_lines or []) if str(x).strip()])
    if row_count >= 2 or note_count >= 8:
        return 2
    if row_count >= 1 and note_count >= 3:
        return 1
    return 0


def _normalize_price_text(data, override_price=None):
    if override_price:
        return str(override_price).strip()
    src = data if isinstance(data, dict) else {}
    return str(_pick_first(src, ["양도가", "?묐룄媛", "price"], "")).strip()


def build_report_payload(data, recipient="", sender="", override_price=None, enforce_sum_validation=True):
    src = data if isinstance(data, dict) else {}
    rows = _get_rows(src)
    note_lines = _get_notes(src)
    sum_issues = _validate_sales_sums(rows)
    if enforce_sum_validation and sum_issues:
        first = sum_issues[0]
        raise ValueError(
            f"sales sum mismatch: row={first.get('row')} type={first.get('type')} raw={first.get('raw')} calc={first.get('calc')}"
        )

    registration_no = str(
        _pick_first(src, ["등록번호", "?깅줉踰덊샇", "registration_no", "registration"], "")
    ).strip()
    price_text = _normalize_price_text(src, override_price=override_price)
    capital = _pick_first(src, ["자본금", "?먮낯湲?", "capital"], "")
    location = _pick_first(src, ["소재지", "?뚯옱吏", "location"], "")
    founded = _pick_first(src, ["법인설립년", "踰뺤씤?ㅻ┰??", "founded"], "")
    company_type = _pick_first(src, ["회사형태", "?뚯궗?뺥깭", "company_type"], "")
    shares = _pick_first(src, ["공제조합출자좌수", "怨듭젣議고빀異쒖옄醫뚯닔", "shares"], "")
    balance = _pick_first(src, ["공제조합잔액", "怨듭젣議고빀?붿븸", "balance"], "")

    summary_lines = []
    if company_type:
        summary_lines.append(f"Company type: {company_type}")
    if capital:
        summary_lines.append(f"Capital: {capital}")
    if location:
        summary_lines.append(f"Location: {location}")
    if founded:
        summary_lines.append(f"Founded: {founded}")
    if shares:
        summary_lines.append(f"Mutual shares: {shares}")
    if balance:
        summary_lines.append(f"Mutual balance: {balance}")

    risks = []
    for issue in sum_issues:
        risks.append(
            {
                "title": f"Sales sum mismatch ({issue.get('name')})",
                "status": f"Raw {issue.get('raw')} vs calc {issue.get('calc')}",
                "plan": "Review source sheet year columns and lock validated totals.",
            }
        )

    if not risks:
        risks.append(
            {
                "title": "Data consistency",
                "status": "No sum mismatch detected",
                "plan": "Continue with standard due diligence checks.",
            }
        )

    image_count = _recommend_report_image_count(rows, note_lines)
    opinion = "Proceed with conditional review." if sum_issues else "Proceed. Core checks are within expected bounds."

    payload = {
        "generated_at": datetime.now().isoformat(),
        "registration_no": registration_no,
        "recipient": str(recipient or "").strip(),
        "sender": str(sender or "").strip(),
        "price": price_text,
        "summary": summary_lines,
        "notes": note_lines,
        "rows": rows,
        "risks": risks,
        "opinion": opinion,
        "quality_checks": {
            "sum_validation_ok": len(sum_issues) == 0,
            "sum_issues": sum_issues,
        },
        "image_plan": {
            "recommended_count": image_count,
            "reason": "rows/notes complexity",
        },
    }
    return payload


def render_report_pdf(payload, output_path):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except Exception as exc:
        raise RuntimeError("reportlab package is required. Install with `py -3 -m pip install reportlab`.") from exc

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    body_style = styles["BodyText"]
    heading_style = styles["Heading2"]

    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm)
    story = []
    story.append(Paragraph("Listing Analysis Report", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Registration: {payload.get('registration_no', '-')}", body_style))
    story.append(Paragraph(f"Price: {payload.get('price', '-')}", body_style))
    if payload.get("recipient"):
        story.append(Paragraph(f"Recipient: {payload.get('recipient')}", body_style))
    if payload.get("sender"):
        story.append(Paragraph(f"Sender: {payload.get('sender')}", body_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Summary", heading_style))
    for line in payload.get("summary", []):
        story.append(Paragraph(f"- {line}", body_style))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Key Notes", heading_style))
    for line in payload.get("notes", []):
        story.append(Paragraph(f"- {line}", body_style))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Risk Assessment", heading_style))
    for idx, item in enumerate(payload.get("risks", []), start=1):
        story.append(Paragraph(f"{idx}. {item.get('title', '')}", body_style))
        story.append(Paragraph(f"   status: {item.get('status', '')}", body_style))
        story.append(Paragraph(f"   plan: {item.get('plan', '')}", body_style))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Overall Opinion", heading_style))
    story.append(Paragraph(str(payload.get("opinion", "")), body_style))
    doc.build(story)
    return output_path


def _load_input_data(args, backend_module):
    if args.registration:
        lookup = backend_module.ListingSheetLookup()
        return lookup.load_listing(args.registration)
    if args.image:
        generator = backend_module.GabjiGenerator()
        return generator.analyze_image(args.image)
    if args.json_input:
        with open(args.json_input, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    raise ValueError("No input mode selected. Use --registration or --image or --json-input.")


def main():
    parser = argparse.ArgumentParser(description="Build listing analysis report PDF from gabji data")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--registration", help="Sheet registration number (e.g., 7737)")
    group.add_argument("--image", help="Gabji image path (requires Gemini access)")
    group.add_argument("--json-input", help="Gabji JSON input file path")
    parser.add_argument("--price", default="", help="Override price text")
    parser.add_argument("--recipient", default="", help="Recipient name")
    parser.add_argument("--sender", default="", help="Sender name")
    parser.add_argument("--output", default="", help="Output PDF path")
    parser.add_argument("--gabji-backend", default="", help="Gabji backend module (default: gabji, e.g., gb2_v3)")
    parser.add_argument("--print-payload", action="store_true", help="Print payload JSON")
    parser.add_argument("--print-backend-audit", action="store_true", help="Print backend compatibility JSON")
    parser.add_argument("--allow-sum-mismatch", action="store_true", help="Allow report generation with sum mismatch")
    args = parser.parse_args()

    backend_module, backend_name, backend_missing = _resolve_backend_module(args.gabji_backend)
    if args.print_backend_audit:
        print(
            json.dumps(
                {
                    "backend": backend_name,
                    "module_file": str(getattr(backend_module, "__file__", "")),
                    "missing_symbols": backend_missing,
                    "ready": len(backend_missing) == 0,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    if backend_missing:
        raise ValueError(f"Backend '{backend_name}' incompatible: missing symbols {', '.join(backend_missing)}")

    data = _load_input_data(args, backend_module)
    payload = build_report_payload(
        data=data,
        recipient=args.recipient,
        sender=args.sender,
        override_price=args.price.strip() or None,
        enforce_sum_validation=(not args.allow_sum_mismatch),
    )

    if args.print_payload:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    output_path = args.output.strip() or _default_output_path(payload.get("registration_no", ""))
    render_report_pdf(payload, output_path)
    print(f"[ok] report generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
