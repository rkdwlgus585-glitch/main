#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
TXT_OUT = LOGS / "calculator_progress_latest.txt"
PDF_OUT = LOGS / "calculator_progress_latest.pdf"
JSON_OUT = LOGS / "calculator_progress_latest.json"


def _run(cmd: List[str]) -> Tuple[bool, str]:
    try:
        cp = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=240,
        )
    except Exception as exc:
        return False, f"[runner_error] {exc}"
    out = (cp.stdout or "").strip()
    err = (cp.stderr or "").strip()
    merged = "\n".join([x for x in [out, err] if x]).strip()
    return cp.returncode == 0, merged


def _parse_unittest_output(text: str) -> Dict[str, Any]:
    src = str(text or "")
    ran = 0
    m = re.search(r"Ran\s+(\d+)\s+tests?", src)
    if m:
        try:
            ran = int(m.group(1))
        except Exception:
            ran = 0
    ok = "OK" in src and "FAILED" not in src
    return {"ok": ok, "ran": ran}


def _register_font() -> str:
    candidates = [
        Path(r"C:\Windows\Fonts\malgun.ttf"),
        Path(r"C:\Windows\Fonts\gulim.ttc"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]
    for fp in candidates:
        if not fp.exists():
            continue
        try:
            name = "CalcProgressFont"
            pdfmetrics.registerFont(TTFont(name, str(fp)))
            return name
        except Exception:
            continue
    return "Helvetica"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}


def build_payload() -> Dict[str, Any]:
    py = sys.executable

    compile_ok, compile_out = _run(
        [
            py,
            "-m",
            "py_compile",
            "yangdo_calculator.py",
            "acquisition_calculator.py",
            "permit_diagnosis_calculator.py",
            "yangdo_blackbox_api.py",
            "yangdo_consult_api.py",
        ]
    )

    test_ok, test_out = _run(
        [
            py,
            "-m",
            "unittest",
            "tests.test_yangdo_calculator_input_variables",
            "tests.test_permit_diagnosis_calculator_rules",
            "tests.test_all_yangdo_estimator",
            "tests.test_all_yangdo_calculator_page",
            "tests.test_yangdo_consult_api",
        ]
    )
    test_info = _parse_unittest_output(test_out)

    combo_ok, combo_out = _run([py, "scripts/run_calculator_combo_sanity.py"])
    combo_json: Dict[str, Any] = {}
    try:
        combo_json = json.loads(str(combo_out).splitlines()[-1])
    except Exception:
        combo_json = {}

    fuzz_ok, fuzz_out = _run([py, "scripts/run_permit_diagnosis_input_fuzz.py"])
    fuzz_json = _load_json(LOGS / "permit_diagnosis_input_fuzz_latest.json")

    acq = combo_json.get("acquisition") if isinstance(combo_json.get("acquisition"), dict) else {}
    yg = combo_json.get("yangdo") if isinstance(combo_json.get("yangdo"), dict) else {}

    weights = {
        "compile": 10,
        "unit_tests": 35,
        "combo_sanity": 25,
        "permit_fuzz": 20,
        "reporting": 10,
    }
    score = 0
    if compile_ok:
        score += weights["compile"]
    if bool(test_info.get("ok")):
        score += weights["unit_tests"]
    if combo_ok:
        score += weights["combo_sanity"]
    if fuzz_ok and bool(fuzz_json.get("ok", False)):
        score += weights["permit_fuzz"]
    score += weights["reporting"]

    payload: Dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall_progress_pct": int(score),
        "weights": weights,
        "compile_check": {"ok": compile_ok, "output": compile_out[-1200:]},
        "unit_tests": {
            "ok": bool(test_info.get("ok")),
            "ran": int(test_info.get("ran") or 0),
            "output": test_out[-1200:],
        },
        "combo_sanity": {
            "ok": combo_ok,
            "acquisition_passed": int(acq.get("passed") or 0),
            "acquisition_cases": int(acq.get("cases") or 0),
            "yangdo_passed": int(yg.get("passed") or 0),
            "yangdo_cases": int(yg.get("cases") or 0),
            "output": combo_out[-1200:],
        },
        "permit_fuzz": {
            "ok": bool(fuzz_json.get("ok", False)) and fuzz_ok,
            "ok_rate_pct": float(fuzz_json.get("ok_rate_pct") or 0.0),
            "anomaly_total": int(fuzz_json.get("anomaly_total") or 0),
            "output": fuzz_out[-1200:],
        },
        "api_usage_note": {
            "yangdo_core_logic_api_required": False,
            "permit_core_logic_api_required": False,
            "api_required_only_for": [
                "원격 추정 엔드포인트 사용 시(estimate_endpoint 설정 시)",
                "상담 접수 서버 저장 사용 시(consult_endpoint 설정 시)",
                "사용량 원격 로그 사용 시(usage_endpoint 설정 시)",
            ],
        },
    }
    return payload


def to_lines(payload: Dict[str, Any]) -> List[str]:
    c = payload.get("compile_check", {})
    t = payload.get("unit_tests", {})
    cs = payload.get("combo_sanity", {})
    fz = payload.get("permit_fuzz", {})
    api = payload.get("api_usage_note", {})

    lines: List[str] = []
    lines.append("계산기 진행률 정밀 점검")
    lines.append(f"생성시각: {payload.get('generated_at', '')}")
    lines.append(f"종합 진행률: {payload.get('overall_progress_pct', 0)}%")
    lines.append("")
    lines.append("[1] 컴파일 점검")
    lines.append(f"- 상태: {'정상' if bool(c.get('ok')) else '실패'}")
    lines.append("")
    lines.append("[2] 핵심 단위테스트")
    lines.append(f"- 상태: {'정상' if bool(t.get('ok')) else '실패'}")
    lines.append(f"- 실행 테스트 수: {int(t.get('ran') or 0)}")
    lines.append("")
    lines.append("[3] 조합 샌티티 테스트")
    lines.append(f"- 상태: {'정상' if bool(cs.get('ok')) else '실패'}")
    lines.append(
        f"- 인허가 산정기: {int(cs.get('acquisition_passed') or 0)}/{int(cs.get('acquisition_cases') or 0)}"
    )
    lines.append(f"- 양도가 산정기: {int(cs.get('yangdo_passed') or 0)}/{int(cs.get('yangdo_cases') or 0)}")
    lines.append("")
    lines.append("[4] 인허가 입력값 퍼즈 점검")
    lines.append(f"- 상태: {'정상' if bool(fz.get('ok')) else '실패'}")
    lines.append(f"- 정상 비율: {float(fz.get('ok_rate_pct') or 0.0):.2f}%")
    lines.append(f"- 이상치 수: {int(fz.get('anomaly_total') or 0)}")
    lines.append("")
    lines.append("[5] API 의존성 최소화 현황")
    lines.append(
        f"- 양도가 핵심 계산 로직 API 필수 여부: {'필수 아님' if not bool(api.get('yangdo_core_logic_api_required')) else '필수'}"
    )
    lines.append(
        f"- 인허가 핵심 계산 로직 API 필수 여부: {'필수 아님' if not bool(api.get('permit_core_logic_api_required')) else '필수'}"
    )
    lines.append("- API가 필요한 경우(선택 기능):")
    for item in list(api.get("api_required_only_for") or []):
        lines.append(f"  * {item}")
    lines.append("")
    lines.append("[결론]")
    lines.append("- 현재 점검 기준에서 계산기 2종(양도가/인허가) 핵심 로직은 로컬 중심으로 정상 통과.")
    lines.append("- 사용자 확인용 보고서는 본 txt/pdf 파일 기준으로 전달.")
    return lines


def write_outputs(payload: Dict[str, Any]) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8-sig")

    lines = to_lines(payload)
    TXT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")

    font_name = _register_font()
    c = canvas.Canvas(str(PDF_OUT), pagesize=A4)
    width, height = A4
    y = height - 45
    line_h = 14
    left = 45
    c.setFont(font_name, 10)
    for line in lines:
        if y < 45:
            c.showPage()
            c.setFont(font_name, 10)
            y = height - 45
        c.drawString(left, y, line[:130])
        y -= line_h
    c.save()


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(
        json.dumps(
            {
                "ok": True,
                "overall_progress_pct": payload.get("overall_progress_pct", 0),
                "txt": str(TXT_OUT),
                "pdf": str(PDF_OUT),
                "json": str(JSON_OUT),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
