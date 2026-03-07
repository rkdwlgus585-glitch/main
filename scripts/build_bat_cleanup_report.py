#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
ARCHIVE = ROOT / "archive" / "bat_unused_20260305"
TXT_OUT = LOGS / "bat_cleanup_summary_latest.txt"
PDF_OUT = LOGS / "bat_cleanup_summary_latest.pdf"


def _list_bat(path: Path) -> List[str]:
    if not path.exists() or not path.is_dir():
        return []
    return sorted([p.name for p in path.glob("*.bat") if p.is_file()])


def _register_font() -> str:
    candidates = [
        Path(r"C:\Windows\Fonts\malgun.ttf"),
        Path(r"C:\Windows\Fonts\맑은 고딕.ttf"),
        Path(r"C:\Windows\Fonts\gulim.ttc"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]
    for fp in candidates:
        if fp.exists():
            name = "BatReportFont"
            try:
                pdfmetrics.registerFont(TTFont(name, str(fp)))
                return name
            except Exception:
                continue
    return "Helvetica"


def _build_lines() -> List[str]:
    root_bats = _list_bat(ROOT)
    launcher_bats = _list_bat(ROOT / "launchers")
    archived = _list_bat(ARCHIVE)

    lines: List[str] = []
    lines.append("BAT 정리 요약")
    lines.append(f"생성시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("[핵심 안내]")
    lines.append("- 운영 상태는 운영요약열기.bat 또는 open_ops_snapshot.bat로 확인")
    lines.append("- 세부 자동화는 bat 대신 scripts/*.py, scripts/*.ps1 직접 실행 권장")
    lines.append("")
    lines.append(f"[현재 root BAT 수] {len(root_bats)}")
    for name in root_bats:
        lines.append(f"- {name}")
    lines.append("")
    lines.append(f"[현재 launchers BAT 수] {len(launcher_bats)}")
    for name in launcher_bats:
        lines.append(f"- {name}")
    lines.append("")
    lines.append(f"[archive/bat_unused_20260305 이동 파일 수] {len(archived)}")
    for name in archived:
        lines.append(f"- {name}")
    lines.append("")
    lines.append("[권장 사용자 진입점]")
    lines.append("- 운영요약열기.bat")
    lines.append("- 보안전체자동설정.bat")
    lines.append("- 작업물구획정리.bat")
    return lines


def _write_txt(lines: List[str]) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    TXT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def _write_pdf(lines: List[str]) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    font_name = _register_font()

    c = canvas.Canvas(str(PDF_OUT), pagesize=A4)
    width, height = A4
    left = 45
    y = height - 45
    line_h = 14

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
    lines = _build_lines()
    _write_txt(lines)
    _write_pdf(lines)
    print(
        f'{{"ok": true, "txt": "{TXT_OUT}", "pdf": "{PDF_OUT}", "archive": "{ARCHIVE}"}}'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
