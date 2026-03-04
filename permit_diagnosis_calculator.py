import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_CATALOG_PATH = ROOT / "config" / "kr_permit_industries_localdata.json"


def _safe_json(data) -> str:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return text.replace("</", "<\\/")


def _load_catalog(path: Path) -> dict:
    if not path.exists():
        return {
            "summary": {"industry_total": 0, "major_category_total": 0},
            "major_categories": [],
            "industries": [],
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "summary": {"industry_total": 0, "major_category_total": 0},
            "major_categories": [],
            "industries": [],
        }


def _known_rules() -> dict:
    # NOTE:
    # - 업종별 요건은 법령/시점/관할에 따라 달라질 수 있어, 안전하게 "확정 가능한 범위"만 유지한다.
    # - 미정 업종은 UI에서 "상담 확정" 흐름으로 안내한다.
    return {
        "국내여행업": {"minCapitalEok": 0.3, "requiredTechnicians": 0, "depositDays": 15},
        "국외여행업": {"minCapitalEok": 0.6, "requiredTechnicians": 0, "depositDays": 15},
        "종합여행업": {"minCapitalEok": 1.2, "requiredTechnicians": 1, "depositDays": 20},
        "시설경비업": {"minCapitalEok": 1.0, "requiredTechnicians": 0, "depositDays": 30},
        "호송경비업": {"minCapitalEok": 2.0, "requiredTechnicians": 1, "depositDays": 30},
        "신변보호업": {"minCapitalEok": 1.0, "requiredTechnicians": 0, "depositDays": 30},
        "기계경비업": {"minCapitalEok": 1.0, "requiredTechnicians": 0, "depositDays": 30},
    }


def build_html(title: str, catalog: dict) -> str:
    major_categories = catalog.get("major_categories", [])
    industries = catalog.get("industries", [])
    summary = catalog.get("summary", {})
    rules = _known_rules()

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --navy: #003764;
      --beige: #ac9479;
      --bg: #f6f6f3;
      --ink: #172636;
      --muted: #5c6f82;
      --line: #d7dfe7;
      --card: #ffffff;
      --ok: #1f6a47;
      --warn: #7a4c12;
      --shadow: 0 12px 28px rgba(6, 39, 67, 0.08);
      --radius: 18px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Pretendard", "Noto Sans KR", sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.55;
    }}
    .container {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 20px 16px 48px;
    }}
    .hero {{
      background: linear-gradient(145deg, #062d4d 0%, var(--navy) 65%, #1a4b73 100%);
      color: #f3f9ff;
      border-radius: var(--radius);
      padding: 24px 20px;
      box-shadow: 0 18px 34px rgba(3, 34, 59, 0.24);
      margin-bottom: 16px;
    }}
    .hero h1 {{
      margin: 0 0 10px;
      font-size: clamp(24px, 3.8vw, 36px);
      line-height: 1.22;
      letter-spacing: -0.02em;
    }}
    .hero p {{
      margin: 0;
      color: #d9e8f4;
      font-size: clamp(15px, 2.5vw, 18px);
    }}
    .hero .meta {{
      margin-top: 10px;
      font-size: 13px;
      color: #c9dfef;
      font-weight: 700;
    }}
    .grid {{
      display: grid;
      gap: 14px;
      grid-template-columns: 1fr;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 18px 16px;
    }}
    .card h2 {{
      margin: 0 0 14px;
      font-size: 21px;
      color: var(--navy);
      letter-spacing: -0.01em;
      line-height: 1.28;
    }}
    .field {{
      margin-bottom: 16px;
    }}
    .field:last-child {{
      margin-bottom: 0;
    }}
    .field label {{
      display: block;
      margin-bottom: 8px;
      font-size: 15px;
      font-weight: 800;
      line-height: 1.35;
    }}
    .control {{
      width: 100%;
      min-height: 52px;
      border: 1px solid #bfccd9;
      border-radius: 12px;
      background: #fff;
      color: var(--ink);
      padding: 12px 14px;
      font-size: 18px;
      line-height: 1.3;
    }}
    .control:focus {{
      outline: 2px solid #7ea8cc;
      outline-offset: 1px;
    }}
    .assist {{
      margin-top: 8px;
      color: #4d6880;
      font-size: 14px;
      line-height: 1.42;
      font-weight: 700;
    }}
    .metric-label {{
      margin: 0 0 6px;
      color: var(--muted);
      font-size: 16px;
      font-weight: 700;
      line-height: 1.4;
    }}
    .metric-value {{
      margin: 0 0 12px;
      font-size: clamp(30px, 5vw, 44px);
      line-height: 1.16;
      letter-spacing: -0.02em;
      font-weight: 900;
      color: var(--navy);
      word-break: keep-all;
    }}
    .status {{
      margin: 0 0 12px;
      font-size: clamp(22px, 3.6vw, 30px);
      font-weight: 900;
      line-height: 1.22;
      color: #274f71;
      word-break: keep-all;
    }}
    .status.ok {{ color: var(--ok); }}
    .status.warn {{ color: var(--warn); }}
    .meta-box {{
      margin: 0 0 12px;
      padding: 11px 12px;
      border-radius: 12px;
      border: 1px solid #d4e0ec;
      background: #f7fafd;
      color: #37566f;
      font-size: 15px;
      line-height: 1.45;
      font-weight: 700;
    }}
    .tip {{
      margin-top: 10px;
      padding: 12px 13px;
      border-radius: 12px;
      border: 1px solid #e1d2c1;
      background: #f3ece4;
      color: #5d4a34;
      font-size: 14px;
      line-height: 1.45;
      font-weight: 700;
    }}
    .guide {{
      margin-top: 8px;
      color: #667381;
      font-size: 13px;
      line-height: 1.46;
      font-weight: 600;
    }}
    .actions {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 38px;
      padding: 7px 12px;
      border-radius: 999px;
      text-decoration: none;
      font-size: 14px;
      font-weight: 800;
      line-height: 1.2;
      border: 1px solid #b9cde0;
      color: #123f63;
      background: #fff;
    }}
    .btn.main {{
      border-color: #0f5c98;
      background: linear-gradient(145deg, #0f5f9e 0%, #1e78bd 100%);
      color: #fff;
    }}
    @media (min-width: 920px) {{
      .grid {{
        grid-template-columns: 1.04fr 0.96fr;
        align-items: start;
      }}
      .card {{
        padding: 20px 18px;
      }}
    }}
  </style>
</head>
<body>
  <main class="container">
    <section class="hero">
      <h1>AI 인허가 사전검토 진단기</h1>
      <p>업종별 인허가 등록 전, 자본금·기술인력·예치기간을 사전에 점검해 리스크를 줄입니다.</p>
      <div class="meta">업종 DB: {summary.get("industry_total", 0)}개 · 대분류: {summary.get("major_category_total", 0)}개 (LOCALDATA 기준)</div>
    </section>

    <div class="grid">
      <section class="card" aria-labelledby="input-title">
        <h2 id="input-title">사전검토 입력</h2>
        <div class="field">
          <label for="categorySelect">대분류 카테고리</label>
          <select id="categorySelect" class="control"></select>
        </div>
        <div class="field">
          <label for="industrySelect">세부 인허가 업종</label>
          <select id="industrySelect" class="control"></select>
          <p id="industryHint" class="assist"></p>
        </div>
        <div class="field">
          <label for="capitalInput">현재 보유 자본금(억)</label>
          <input id="capitalInput" class="control" type="number" inputmode="decimal" min="0" step="0.01" placeholder="예: 1.5" />
          <p id="crossValidation" class="assist" aria-live="polite"></p>
        </div>
        <p class="guide">입력 단위는 반드시 억입니다. 예: 1억 5천만 원 = 1.5</p>
      </section>

      <section class="card" aria-labelledby="result-title">
        <h2 id="result-title">진단 결과</h2>
        <p class="metric-label">법정 최소 자본금</p>
        <p id="requiredCapital" class="metric-value">-</p>
        <p class="metric-label">필수 기술자 수 / 필수 예치기간</p>
        <p id="requirementsMeta" class="meta-box">-</p>
        <p class="metric-label">자본금 갭 진단</p>
        <p id="capitalGapStatus" class="status">-</p>
        <p class="metric-label">오늘 증자 시 예상 진단 가능일</p>
        <p id="diagnosisDate" class="metric-value">-</p>
        <p id="fallbackGuide" class="meta-box" style="display:none"></p>
        <div class="actions">
          <a class="btn main" href="https://seoulmna.co.kr/notice" target="_blank" rel="noopener noreferrer">전문가 상담 연결</a>
          <a class="btn" href="tel:16683548">대표전화 1668-3548</a>
        </div>
        <p class="tip">타인 자본(차입금 등) 활용 비중은 재무 건전성 개선 지표로도 설계가 가능합니다.</p>
      </section>
    </div>
  </main>

  <script>
    const permitCatalog = { _safe_json({"major_categories": major_categories, "industries": industries}) };
    const knownRules = { _safe_json(rules) };

    const ui = {{
      categorySelect: document.getElementById("categorySelect"),
      industrySelect: document.getElementById("industrySelect"),
      industryHint: document.getElementById("industryHint"),
      capitalInput: document.getElementById("capitalInput"),
      crossValidation: document.getElementById("crossValidation"),
      requiredCapital: document.getElementById("requiredCapital"),
      requirementsMeta: document.getElementById("requirementsMeta"),
      capitalGapStatus: document.getElementById("capitalGapStatus"),
      diagnosisDate: document.getElementById("diagnosisDate"),
      fallbackGuide: document.getElementById("fallbackGuide"),
    }};

    const Core = (() => {{
      const toNum = (value) => {{
        const n = Number(value || 0);
        return Number.isFinite(n) ? n : 0;
      }};
      const formatEok = (value) => {{
        const rounded = Math.round(toNum(value) * 100) / 100;
        return `${{rounded.toLocaleString("ko-KR")}}억`;
      }};
      const toDateLabel = (dateObj) => {{
        const y = dateObj.getFullYear();
        const m = String(dateObj.getMonth() + 1).padStart(2, "0");
        const d = String(dateObj.getDate()).padStart(2, "0");
        return `${{y}}-${{m}}-${{d}}`;
      }};
      const computeGap = (requiredEok, currentEok) => {{
        const required = toNum(requiredEok);
        const current = toNum(currentEok);
        const gap = Math.max(0, required - current);
        return {{
          requiredEok: required,
          currentEok: current,
          gapEok: gap,
          isSatisfied: gap <= 0,
        }};
      }};
      const predictDiagnosisDate = (depositDays) => {{
        const days = Math.max(0, Number(depositDays || 0));
        const base = new Date();
        const target = new Date(base);
        target.setDate(base.getDate() + days);
        return {{
          days,
          dateLabel: toDateLabel(target),
        }};
      }};
      const detectSuspiciousInput = (rawInput, inputEok, requiredEok) => {{
        const raw = String(rawInput || "").trim().replace(/,/g, "");
        if (!raw) return false;
        const value = toNum(inputEok);
        const required = toNum(requiredEok);
        const overThreeX = required > 0 && value > required * 3;
        const decimalPatternOdd = !/^\\d+(\\.\\d{{1,2}})?$/.test(raw);
        const likelyUnitMistake = /^\\d{{2,}}$/.test(raw) && value >= 10;
        return overThreeX || decimalPatternOdd || likelyUnitMistake;
      }};
      return {{
        formatEok,
        computeGap,
        predictDiagnosisDate,
        detectSuspiciousInput,
      }};
    }})();

    const makeOption = (value, label) => {{
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = label;
      return opt;
    }};

    const industriesByCategory = (() => {{
      const map = Object.create(null);
      const rows = Array.isArray(permitCatalog.industries) ? permitCatalog.industries : [];
      rows.forEach((row) => {{
        const key = String(row.major_code || "");
        if (!key) return;
        if (!map[key]) map[key] = [];
        map[key].push(row);
      }});
      Object.keys(map).forEach((key) => {{
        map[key].sort((a, b) => String(a.service_name || "").localeCompare(String(b.service_name || ""), "ko"));
      }});
      return map;
    }})();

    const renderCategories = () => {{
      ui.categorySelect.innerHTML = "";
      ui.categorySelect.appendChild(makeOption("", "카테고리 선택"));
      const rows = Array.isArray(permitCatalog.major_categories) ? permitCatalog.major_categories : [];
      rows.forEach((row) => {{
        const code = String(row.major_code || "");
        const name = String(row.major_name || "");
        const count = Number(row.industry_count || 0);
        if (!code || !name) return;
        ui.categorySelect.appendChild(makeOption(code, `${{name}} (${{count}}개)`));
      }});
    }};

    const renderIndustries = () => {{
      const categoryCode = ui.categorySelect.value;
      ui.industrySelect.innerHTML = "";
      ui.industrySelect.appendChild(makeOption("", "세부 업종 선택"));
      if (!categoryCode || !industriesByCategory[categoryCode]) {{
        ui.industryHint.textContent = "";
        return;
      }}
      industriesByCategory[categoryCode].forEach((row) => {{
        const code = String(row.service_code || "");
        const name = String(row.service_name || "");
        if (!code || !name) return;
        ui.industrySelect.appendChild(makeOption(code, name));
      }});
      ui.industryHint.textContent = "업종을 선택하면 즉시 사전검토 상태가 표시됩니다.";
    }};

    const getSelectedIndustry = () => {{
      const code = String(ui.industrySelect.value || "");
      if (!code) return null;
      const rows = Array.isArray(permitCatalog.industries) ? permitCatalog.industries : [];
      return rows.find((row) => String(row.service_code || "") === code) || null;
    }};

    const clearResult = () => {{
      ui.requiredCapital.textContent = "-";
      ui.requirementsMeta.textContent = "-";
      ui.capitalGapStatus.textContent = "-";
      ui.capitalGapStatus.className = "status";
      ui.diagnosisDate.textContent = "-";
      ui.crossValidation.textContent = "";
      ui.fallbackGuide.style.display = "none";
      ui.fallbackGuide.textContent = "";
    }};

    const renderResult = () => {{
      const selected = getSelectedIndustry();
      if (!selected) {{
        clearResult();
        return;
      }}

      const industryName = String(selected.service_name || "");
      const rule = knownRules[industryName] || null;
      const rawInput = String(ui.capitalInput.value || "").trim();
      const currentCapital = Number(rawInput || 0);

      if (!rule) {{
        ui.requiredCapital.textContent = "상담 확정";
        ui.requirementsMeta.textContent = "이 업종은 인허가 DB에는 등록되어 있으나, 정량 요건(자본금/기술인력/예치기간) DB는 확장 작업 중입니다.";
        ui.capitalGapStatus.textContent = "업종별 법령 기준 사전검토 필요";
        ui.capitalGapStatus.className = "status warn";
        ui.diagnosisDate.textContent = "-";
        ui.crossValidation.textContent = "";
        ui.fallbackGuide.style.display = "block";
        ui.fallbackGuide.textContent = `${{industryName}}: 관할/법령/시점에 따라 기준이 달라질 수 있어 상담 과정에서 확정됩니다.`;
        return;
      }}

      const gap = Core.computeGap(rule.minCapitalEok, currentCapital);
      const diagnosis = Core.predictDiagnosisDate(rule.depositDays);
      ui.requiredCapital.textContent = Core.formatEok(rule.minCapitalEok);
      ui.requirementsMeta.textContent = `기술자 ${{rule.requiredTechnicians}}명 / 예치 ${{rule.depositDays}}일`;

      if (gap.isSatisfied) {{
        ui.capitalGapStatus.textContent = "자본금 요건 충족";
        ui.capitalGapStatus.className = "status ok";
      }} else {{
        ui.capitalGapStatus.textContent = `${{Core.formatEok(gap.gapEok)}} 추가 증자가 필요합니다`;
        ui.capitalGapStatus.className = "status";
      }}
      ui.diagnosisDate.textContent = `${{diagnosis.dateLabel}} (D+${{diagnosis.days}})`;

      const suspicious = Core.detectSuspiciousInput(rawInput, currentCapital, rule.minCapitalEok);
      if (suspicious) {{
        ui.crossValidation.textContent = `입력하신 금액이 ${{Core.formatEok(currentCapital)}}이 맞으십니까? 단위(억)를 다시 확인해 주세요.`;
      }} else {{
        ui.crossValidation.textContent = "";
      }}
      ui.fallbackGuide.style.display = "none";
      ui.fallbackGuide.textContent = "";
    }};

    const init = () => {{
      renderCategories();
      renderIndustries();
      clearResult();
      ui.categorySelect.addEventListener("change", () => {{
        renderIndustries();
        clearResult();
      }});
      ui.industrySelect.addEventListener("change", renderResult);
      ui.capitalInput.addEventListener("input", renderResult);
    }};

    init();
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI permit pre-check calculator HTML")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG_PATH), help="Path to collected permit industry JSON")
    parser.add_argument("--output", default="output/ai_permit_precheck.html", help="Output HTML file path")
    parser.add_argument("--title", default="AI 인허가 사전검토 진단기 | 서울건설정보", help="HTML title")
    # Backward-compatible no-op args so legacy deploy commands do not fail.
    parser.add_argument("--contact-phone", default="")
    parser.add_argument("--openchat-url", default="")
    parser.add_argument("--consult-endpoint", default="")
    parser.add_argument("--usage-endpoint", default="")
    args = parser.parse_args()

    catalog = _load_catalog(Path(args.catalog).expanduser().resolve())
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_html(title=str(args.title), catalog=catalog), encoding="utf-8")
    print(f"[saved] {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
