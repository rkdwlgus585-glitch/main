import argparse
import json
import re
from datetime import date, timedelta
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_CATALOG_PATH = ROOT / "config" / "kr_permit_industries_localdata.json"
DEFAULT_RULES_PATH = ROOT / "config" / "permit_registration_rules_law.json"
RULES_ONLY_CATEGORY_CODE = "RG"
RULES_ONLY_CATEGORY_NAME = "등록기준 업종군"
OBJECTIVE_SOURCE_HOSTS = (
    "law.go.kr",
    "localdata.go.kr",
    "gov.kr",
)


def _safe_json(data) -> str:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return text.replace("</", "<\\/")


def _blank_catalog() -> dict:
    return {
        "summary": {"industry_total": 0, "major_category_total": 0},
        "major_categories": [],
        "industries": [],
    }


def _blank_rule_catalog() -> dict:
    return {
        "version": "",
        "effective_date": "",
        "source": {},
        "rule_groups": [],
    }


def _load_catalog(path: Path) -> dict:
    if not path.exists():
        return _blank_catalog()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank_catalog()
    if not isinstance(loaded, dict):
        return _blank_catalog()
    base = _blank_catalog()
    base.update(loaded)
    if not isinstance(base.get("major_categories"), list):
        base["major_categories"] = []
    if not isinstance(base.get("industries"), list):
        base["industries"] = []
    if not isinstance(base.get("summary"), dict):
        base["summary"] = {"industry_total": 0, "major_category_total": 0}
    return base


def _load_rule_catalog(path: Path) -> dict:
    if not path.exists():
        return _blank_rule_catalog()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blank_rule_catalog()
    if not isinstance(loaded, dict):
        return _blank_rule_catalog()
    base = _blank_rule_catalog()
    base.update(loaded)
    groups = loaded.get("rule_groups")
    if not isinstance(groups, list):
        groups = loaded.get("rules")
    if not isinstance(groups, list):
        groups = []
    base["rule_groups"] = groups
    return base


def _normalize_key(value) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", str(value or "").strip().lower())


def _is_objective_source_url(url: str) -> bool:
    src = str(url or "").strip().lower()
    if not src.startswith("http"):
        return False
    return any(host in src for host in OBJECTIVE_SOURCE_HOSTS)


def _coerce_non_negative_float(value) -> float:
    try:
        out = float(value)
    except Exception:
        return 0.0
    if out != out or out < 0:
        return 0.0
    return out


def _coerce_non_negative_int(value) -> int:
    try:
        out = int(float(value))
    except Exception:
        return 0
    if out < 0:
        return 0
    return out


def _expand_rule_groups(rule_catalog: dict) -> list:
    rows = []
    groups = list(rule_catalog.get("rule_groups") or [])
    for group in groups:
        if not isinstance(group, dict):
            continue
        rule_id = str(group.get("rule_id", "") or "").strip()
        if not rule_id:
            continue

        legal_basis = []
        for item in list(group.get("legal_basis") or []):
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "") or "").strip()
            if not _is_objective_source_url(url):
                continue
            legal_basis.append(
                {
                    "law_title": str(item.get("law_title", "") or "").strip(),
                    "article": str(item.get("article", "") or "").strip(),
                    "url": url,
                }
            )
        if not legal_basis:
            continue

        req_src = dict(group.get("requirements") or {})
        requirements = {
            "capital_eok": _coerce_non_negative_float(req_src.get("capital_eok", 0)),
            "technicians": _coerce_non_negative_int(req_src.get("technicians", 0)),
            "equipment_count": _coerce_non_negative_int(req_src.get("equipment_count", 0)),
            "deposit_days": _coerce_non_negative_int(req_src.get("deposit_days", 0)),
        }

        names = []
        single = str(group.get("industry_name", "") or "").strip()
        if single:
            names.append(single)
        for name in list(group.get("industry_names") or []):
            txt = str(name or "").strip()
            if txt:
                names.append(txt)
        dedup_names = []
        seen = set()
        for name in names:
            key = _normalize_key(name)
            if not key or key in seen:
                continue
            seen.add(key)
            dedup_names.append(name)
        if not dedup_names:
            continue

        aliases = [str(x or "").strip() for x in list(group.get("aliases") or []) if str(x or "").strip()]
        service_codes = [str(x or "").strip() for x in list(group.get("service_codes") or []) if str(x or "").strip()]
        include_in_selector = bool(group.get("include_in_selector", True))

        for idx, name in enumerate(dedup_names):
            rows.append(
                {
                    "rule_id": f"{rule_id}-{idx + 1}" if len(dedup_names) > 1 else rule_id,
                    "group_rule_id": rule_id,
                    "industry_name": name,
                    "aliases": list(aliases),
                    "service_codes": list(service_codes),
                    "requirements": dict(requirements),
                    "legal_basis": list(legal_basis),
                    "include_in_selector": include_in_selector,
                }
            )
    return rows


def _build_rule_index(rule_catalog: dict) -> dict:
    rules = _expand_rule_groups(rule_catalog)
    by_service_code = {}
    by_key = {}
    for rule in rules:
        for code in list(rule.get("service_codes") or []):
            by_service_code[str(code)] = rule
        keys = [_normalize_key(rule.get("industry_name", ""))]
        keys.extend(_normalize_key(alias) for alias in list(rule.get("aliases") or []))
        for key in keys:
            if not key:
                continue
            if key not in by_key:
                by_key[key] = rule
    return {
        "rules": rules,
        "by_service_code": by_service_code,
        "by_key": by_key,
    }


def _resolve_rule_for_industry(industry: dict, rule_index: dict):
    service_code = str(industry.get("service_code", "") or "").strip()
    if service_code and service_code in rule_index.get("by_service_code", {}):
        return rule_index["by_service_code"][service_code]
    service_name = str(industry.get("service_name", "") or "").strip()
    if service_name:
        key = _normalize_key(service_name)
        hit = rule_index.get("by_key", {}).get(key)
        if hit:
            return hit
    return None


def evaluate_registration_diagnosis(
    rule: dict,
    current_capital_eok,
    current_technicians,
    current_equipment_count,
    raw_capital_input="",
    base_date: date | None = None,
) -> dict:
    req = dict(rule.get("requirements") or {})

    required_capital = _coerce_non_negative_float(req.get("capital_eok", 0))
    required_technicians = _coerce_non_negative_int(req.get("technicians", 0))
    required_equipment = _coerce_non_negative_int(req.get("equipment_count", 0))
    deposit_days = _coerce_non_negative_int(req.get("deposit_days", 0))

    current_capital = _coerce_non_negative_float(current_capital_eok)
    current_tech = _coerce_non_negative_int(current_technicians)
    current_equipment = _coerce_non_negative_int(current_equipment_count)

    capital_gap = max(0.0, required_capital - current_capital)
    technician_gap = max(0, required_technicians - current_tech)
    equipment_gap = max(0, required_equipment - current_equipment)

    baseline = base_date or date.today()
    expected_date = baseline + timedelta(days=deposit_days)
    date_label = expected_date.strftime("%Y-%m-%d")

    raw_capital = str(raw_capital_input or "").strip().replace(",", "")
    suspicious = False
    if raw_capital:
        over_three_x = required_capital > 0 and current_capital > required_capital * 3
        decimal_pattern_odd = re.match(r"^\d+(\.\d{1,2})?$", raw_capital) is None
        likely_unit_mistake = re.match(r"^\d{2,}$", raw_capital) is not None and current_capital >= 10
        suspicious = bool(over_three_x or decimal_pattern_odd or likely_unit_mistake)

    capital_ok = capital_gap <= 0
    technicians_ok = technician_gap <= 0
    equipment_ok = equipment_gap <= 0
    overall_ok = bool(capital_ok and technicians_ok and equipment_ok)

    return {
        "capital": {
            "required": required_capital,
            "current": current_capital,
            "gap": round(capital_gap, 4),
            "ok": capital_ok,
        },
        "technicians": {
            "required": required_technicians,
            "current": current_tech,
            "gap": technician_gap,
            "ok": technicians_ok,
        },
        "equipment": {
            "required": required_equipment,
            "current": current_equipment,
            "gap": equipment_gap,
            "ok": equipment_ok,
        },
        "deposit_days": deposit_days,
        "expected_diagnosis_date": date_label,
        "capital_input_suspicious": suspicious,
        "overall_ok": overall_ok,
    }


def _prepare_ui_payload(catalog: dict, rule_catalog: dict) -> dict:
    rule_index = _build_rule_index(rule_catalog)
    major_categories = []
    for row in list(catalog.get("major_categories") or []):
        if not isinstance(row, dict):
            continue
        major_code = str(row.get("major_code", "") or "").strip()
        major_name = str(row.get("major_name", "") or "").strip()
        if not major_code or not major_name:
            continue
        major_categories.append(
            {
                "major_code": major_code,
                "major_name": major_name,
                "industry_count": _coerce_non_negative_int(row.get("industry_count", 0)),
            }
        )

    industries = []
    rules_lookup = {}
    seen_codes = set()
    seen_rule_names = set()
    for row in list(catalog.get("industries") or []):
        if not isinstance(row, dict):
            continue
        service_code = str(row.get("service_code", "") or "").strip()
        service_name = str(row.get("service_name", "") or "").strip()
        major_code = str(row.get("major_code", "") or "").strip()
        major_name = str(row.get("major_name", "") or "").strip()
        if not service_code or not service_name or not major_code:
            continue
        if service_code in seen_codes:
            continue
        seen_codes.add(service_code)
        industry = {
            "service_code": service_code,
            "service_name": service_name,
            "major_code": major_code,
            "major_name": major_name,
            "detail_url": str(row.get("detail_url", "") or "").strip(),
            "has_rule": False,
        }
        rule = _resolve_rule_for_industry(industry, rule_index)
        if rule:
            industry["has_rule"] = True
            rules_lookup[service_code] = rule
            seen_rule_names.add(_normalize_key(rule.get("industry_name", "")))
        industries.append(industry)

    rules_only_rows = []
    for rule in list(rule_index.get("rules") or []):
        if not bool(rule.get("include_in_selector", True)):
            continue
        key = _normalize_key(rule.get("industry_name", ""))
        if key and key in seen_rule_names:
            continue
        virtual_code = f"RULE::{rule.get('rule_id', '')}"
        if virtual_code in seen_codes:
            continue
        seen_codes.add(virtual_code)
        seen_rule_names.add(key)
        rules_only_rows.append(
            {
                "service_code": virtual_code,
                "service_name": str(rule.get("industry_name", "") or "").strip(),
                "major_code": RULES_ONLY_CATEGORY_CODE,
                "major_name": RULES_ONLY_CATEGORY_NAME,
                "detail_url": "",
                "has_rule": True,
            }
        )
        rules_lookup[virtual_code] = rule

    if rules_only_rows:
        major_categories.append(
            {
                "major_code": RULES_ONLY_CATEGORY_CODE,
                "major_name": RULES_ONLY_CATEGORY_NAME,
                "industry_count": len(rules_only_rows),
            }
        )
        industries.extend(rules_only_rows)

    major_categories.sort(key=lambda x: str(x.get("major_code", "")))
    industries.sort(key=lambda x: (str(x.get("major_code", "")), str(x.get("service_name", ""))))

    summary = dict(catalog.get("summary") or {})
    summary["industry_total"] = len(industries)
    summary["major_category_total"] = len(major_categories)
    summary["with_registration_rule_total"] = sum(1 for row in industries if bool(row.get("has_rule")))
    summary["rules_only_industry_total"] = len(rules_only_rows)
    summary["law_rule_total"] = len(list(rule_index.get("rules") or []))

    return {
        "summary": summary,
        "major_categories": major_categories,
        "industries": industries,
        "rules_lookup": rules_lookup,
        "rule_catalog_meta": {
            "version": str(rule_catalog.get("version", "") or ""),
            "effective_date": str(rule_catalog.get("effective_date", "") or ""),
            "source": dict(rule_catalog.get("source") or {}),
        },
    }


def build_html(title: str, catalog: dict, rule_catalog: dict) -> str:
    payload = _prepare_ui_payload(catalog, rule_catalog)
    summary = dict(payload.get("summary") or {})
    permit_catalog = {
        "major_categories": payload.get("major_categories", []),
        "industries": payload.get("industries", []),
        "summary": summary,
    }
    rules_lookup = payload.get("rules_lookup", {})
    rule_catalog_meta = payload.get("rule_catalog_meta", {})

    html_template = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>__TITLE__</title>
  <style>
    :root {
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
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Pretendard", "Noto Sans KR", sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.55;
    }
    .container {
      max-width: 1120px;
      margin: 0 auto;
      padding: 20px 16px 48px;
    }
    .hero {
      background: linear-gradient(145deg, #062d4d 0%, var(--navy) 65%, #1a4b73 100%);
      color: #f3f9ff;
      border-radius: var(--radius);
      padding: 24px 20px;
      box-shadow: 0 18px 34px rgba(3, 34, 59, 0.24);
      margin-bottom: 16px;
    }
    .hero h1 {
      margin: 0 0 10px;
      font-size: clamp(24px, 3.8vw, 36px);
      line-height: 1.22;
      letter-spacing: -0.02em;
    }
    .hero p {
      margin: 0;
      color: #d9e8f4;
      font-size: clamp(15px, 2.5vw, 18px);
    }
    .hero .meta {
      margin-top: 10px;
      font-size: 13px;
      color: #c9dfef;
      font-weight: 700;
    }
    .grid {
      display: grid;
      gap: 14px;
      grid-template-columns: 1fr;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 18px 16px;
    }
    .card h2 {
      margin: 0 0 14px;
      font-size: 21px;
      color: var(--navy);
      letter-spacing: -0.01em;
      line-height: 1.28;
    }
    .field {
      margin-bottom: 14px;
    }
    .field label {
      display: block;
      margin-bottom: 8px;
      font-size: 15px;
      font-weight: 800;
      line-height: 1.35;
    }
    .control {
      width: 100%;
      min-height: 52px;
      border: 1px solid #bfccd9;
      border-radius: 12px;
      background: #fff;
      color: var(--ink);
      padding: 12px 14px;
      font-size: 18px;
      line-height: 1.3;
    }
    .control:focus {
      outline: 2px solid #7ea8cc;
      outline-offset: 1px;
    }
    .assist {
      margin-top: 8px;
      color: #4d6880;
      font-size: 14px;
      line-height: 1.42;
      font-weight: 700;
    }
    .metric-label {
      margin: 0 0 6px;
      color: var(--muted);
      font-size: 16px;
      font-weight: 700;
      line-height: 1.4;
    }
    .metric-value {
      margin: 0 0 10px;
      font-size: clamp(30px, 5vw, 44px);
      line-height: 1.16;
      letter-spacing: -0.02em;
      font-weight: 900;
      color: var(--navy);
      word-break: keep-all;
    }
    .status {
      margin: 0 0 10px;
      font-size: clamp(20px, 3.2vw, 28px);
      font-weight: 900;
      line-height: 1.25;
      color: #274f71;
      word-break: keep-all;
    }
    .status.ok { color: var(--ok); }
    .status.warn { color: var(--warn); }
    .meta-box {
      margin: 0 0 10px;
      padding: 11px 12px;
      border-radius: 12px;
      border: 1px solid #d4e0ec;
      background: #f7fafd;
      color: #37566f;
      font-size: 15px;
      line-height: 1.45;
      font-weight: 700;
    }
    .law-box {
      margin: 0 0 10px;
      padding: 11px 12px;
      border-radius: 12px;
      border: 1px solid #e2d7ca;
      background: #f8f3ed;
      color: #504536;
      font-size: 14px;
      line-height: 1.5;
      font-weight: 700;
    }
    .law-box a { color: #1e4f79; }
    .tip {
      margin-top: 10px;
      padding: 12px 13px;
      border-radius: 12px;
      border: 1px solid #e1d2c1;
      background: #f3ece4;
      color: #5d4a34;
      font-size: 14px;
      line-height: 1.45;
      font-weight: 700;
    }
    .guide {
      margin-top: 8px;
      color: #667381;
      font-size: 13px;
      line-height: 1.46;
      font-weight: 600;
    }
    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }
    .btn {
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
    }
    .btn.main {
      border-color: #0f5c98;
      background: linear-gradient(145deg, #0f5f9e 0%, #1e78bd 100%);
      color: #fff;
    }
    @media (min-width: 920px) {
      .grid {
        grid-template-columns: 1.04fr 0.96fr;
        align-items: start;
      }
      .card {
        padding: 20px 18px;
      }
    }
  </style>
</head>
<body>
  <main class="container">
    <section class="hero">
      <h1>AI 인허가 사전검토 진단기</h1>
      <p>업종별 인허가 등록 전, 자본금·기술인력·장비 요건을 법령 근거로 사전 점검합니다.</p>
      <div class="meta">
        업종 DB: __INDUSTRY_TOTAL__개 · 대분류: __MAJOR_TOTAL__개 · 등록기준 연동: __WITH_RULE_TOTAL__개
      </div>
      <div class="meta">
        규칙 버전: __RULE_VERSION__ · 기준일: __RULE_EFFECTIVE_DATE__
      </div>
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
        <div class="field">
          <label for="technicianInput">현재 기술인력 수(명)</label>
          <input id="technicianInput" class="control" type="number" inputmode="numeric" min="0" step="1" placeholder="예: 2" />
        </div>
        <div class="field">
          <label for="equipmentInput">현재 보유 장비 수(식)</label>
          <input id="equipmentInput" class="control" type="number" inputmode="numeric" min="0" step="1" placeholder="예: 1" />
        </div>
        <p class="guide">자본금 단위는 억입니다. 예: 1억 5천만 원 = 1.5</p>
      </section>

      <section class="card" aria-labelledby="result-title">
        <h2 id="result-title">진단 결과</h2>
        <p class="metric-label">법정 최소 자본금</p>
        <p id="requiredCapital" class="metric-value">-</p>
        <p class="metric-label">필수 기술자 수 / 필수 장비 수 / 예치기간</p>
        <p id="requirementsMeta" class="meta-box">-</p>

        <p class="metric-label">자본금 갭 진단</p>
        <p id="capitalGapStatus" class="status">-</p>
        <p class="metric-label">기술인력 갭 진단</p>
        <p id="technicianGapStatus" class="status">-</p>
        <p class="metric-label">장비 갭 진단</p>
        <p id="equipmentGapStatus" class="status">-</p>

        <p class="metric-label">오늘 보완 시 예상 진단 가능일</p>
        <p id="diagnosisDate" class="metric-value">-</p>
        <p id="fallbackGuide" class="meta-box" style="display:none"></p>
        <div id="legalBasis" class="law-box" style="display:none"></div>

        <div class="actions">
          <a class="btn main" href="https://seoulmna.co.kr/notice" target="_blank" rel="noopener noreferrer">전문가 상담 연결</a>
          <a class="btn" href="tel:16683548">대표전화 1668-3548</a>
        </div>
        <p class="tip">법령/관할 해석이 필요한 항목은 결과 화면의 법령 근거를 기반으로 상담 단계에서 최종 확정됩니다.</p>
      </section>
    </div>
  </main>

  <script>
    const permitCatalog = __PERMIT_CATALOG_JSON__;
    const ruleLookup = __RULE_LOOKUP_JSON__;
    const ruleCatalogMeta = __RULE_CATALOG_META_JSON__;

    const ui = {
      categorySelect: document.getElementById("categorySelect"),
      industrySelect: document.getElementById("industrySelect"),
      industryHint: document.getElementById("industryHint"),
      capitalInput: document.getElementById("capitalInput"),
      technicianInput: document.getElementById("technicianInput"),
      equipmentInput: document.getElementById("equipmentInput"),
      crossValidation: document.getElementById("crossValidation"),
      requiredCapital: document.getElementById("requiredCapital"),
      requirementsMeta: document.getElementById("requirementsMeta"),
      capitalGapStatus: document.getElementById("capitalGapStatus"),
      technicianGapStatus: document.getElementById("technicianGapStatus"),
      equipmentGapStatus: document.getElementById("equipmentGapStatus"),
      diagnosisDate: document.getElementById("diagnosisDate"),
      fallbackGuide: document.getElementById("fallbackGuide"),
      legalBasis: document.getElementById("legalBasis"),
    };

    const Core = (() => {
      const toNum = (value) => {
        const n = Number(value || 0);
        if (!Number.isFinite(n)) return 0;
        return Math.max(0, n);
      };
      const toInt = (value) => Math.max(0, Math.floor(toNum(value)));
      const formatEok = (value) => {
        const rounded = Math.round(toNum(value) * 100) / 100;
        return `${rounded.toLocaleString("ko-KR")}억`;
      };
      const toDateLabel = (dateObj) => {
        const y = dateObj.getFullYear();
        const m = String(dateObj.getMonth() + 1).padStart(2, "0");
        const d = String(dateObj.getDate()).padStart(2, "0");
        return `${y}-${m}-${d}`;
      };
      const computeGap = (required, current) => {
        const req = toNum(required);
        const cur = toNum(current);
        const gap = Math.max(0, req - cur);
        return {
          required: req,
          current: cur,
          gap,
          isSatisfied: gap <= 0,
        };
      };
      const computeIntGap = (required, current) => {
        const req = toInt(required);
        const cur = toInt(current);
        const gap = Math.max(0, req - cur);
        return {
          required: req,
          current: cur,
          gap,
          isSatisfied: gap <= 0,
        };
      };
      const predictDiagnosisDate = (depositDays) => {
        const days = Math.max(0, toInt(depositDays));
        const base = new Date();
        const target = new Date(base);
        target.setDate(base.getDate() + days);
        return {
          days,
          dateLabel: toDateLabel(target),
        };
      };
      const detectSuspiciousCapitalInput = (rawInput, inputEok, requiredEok) => {
        const raw = String(rawInput || "").trim().replace(/,/g, "");
        if (!raw) return false;
        const value = toNum(inputEok);
        const required = toNum(requiredEok);
        const overThreeX = required > 0 && value > required * 3;
        const decimalPatternOdd = !/^\\d+(\\.\\d{1,2})?$/.test(raw);
        const likelyUnitMistake = /^\\d{2,}$/.test(raw) && value >= 10;
        return overThreeX || decimalPatternOdd || likelyUnitMistake;
      };
      return {
        toNum,
        toInt,
        formatEok,
        computeGap,
        computeIntGap,
        predictDiagnosisDate,
        detectSuspiciousCapitalInput,
      };
    })();

    const esc = (value) =>
      String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");

    const makeOption = (value, label) => {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = label;
      return opt;
    };

    const industriesByCategory = (() => {
      const map = Object.create(null);
      const rows = Array.isArray(permitCatalog.industries) ? permitCatalog.industries : [];
      rows.forEach((row) => {
        const key = String(row.major_code || "");
        if (!key) return;
        if (!map[key]) map[key] = [];
        map[key].push(row);
      });
      Object.keys(map).forEach((key) => {
        map[key].sort((a, b) => String(a.service_name || "").localeCompare(String(b.service_name || ""), "ko"));
      });
      return map;
    })();

    const renderCategories = () => {
      ui.categorySelect.innerHTML = "";
      ui.categorySelect.appendChild(makeOption("", "카테고리 선택"));
      const rows = Array.isArray(permitCatalog.major_categories) ? permitCatalog.major_categories : [];
      rows.forEach((row) => {
        const code = String(row.major_code || "");
        const name = String(row.major_name || "");
        const count = Number(row.industry_count || 0);
        if (!code || !name) return;
        ui.categorySelect.appendChild(makeOption(code, `${name} (${count}개)`));
      });
    };

    const renderIndustries = () => {
      const categoryCode = ui.categorySelect.value;
      ui.industrySelect.innerHTML = "";
      ui.industrySelect.appendChild(makeOption("", "세부 업종 선택"));
      if (!categoryCode || !industriesByCategory[categoryCode]) {
        ui.industryHint.textContent = "";
        return;
      }
      industriesByCategory[categoryCode].forEach((row) => {
        const code = String(row.service_code || "");
        const name = String(row.service_name || "");
        const hasRule = !!row.has_rule;
        if (!code || !name) return;
        ui.industrySelect.appendChild(makeOption(code, hasRule ? `${name} (법령기준)` : `${name} (기준확정 필요)`));
      });
      ui.industryHint.textContent = "업종을 선택하면 자본금·기술인력·장비 기준이 즉시 표시됩니다.";
    };

    const getSelectedIndustry = () => {
      const code = String(ui.industrySelect.value || "");
      if (!code) return null;
      const rows = Array.isArray(permitCatalog.industries) ? permitCatalog.industries : [];
      return rows.find((row) => String(row.service_code || "") === code) || null;
    };

    const clearResult = () => {
      ui.requiredCapital.textContent = "-";
      ui.requirementsMeta.textContent = "-";
      ui.capitalGapStatus.textContent = "-";
      ui.capitalGapStatus.className = "status";
      ui.technicianGapStatus.textContent = "-";
      ui.technicianGapStatus.className = "status";
      ui.equipmentGapStatus.textContent = "-";
      ui.equipmentGapStatus.className = "status";
      ui.diagnosisDate.textContent = "-";
      ui.crossValidation.textContent = "";
      ui.fallbackGuide.style.display = "none";
      ui.fallbackGuide.textContent = "";
      ui.legalBasis.style.display = "none";
      ui.legalBasis.innerHTML = "";
    };

    const renderGapStatus = (node, gap, formatter, okText, needText) => {
      if (gap.isSatisfied) {
        node.textContent = okText;
        node.className = "status ok";
      } else {
        node.textContent = `${formatter(gap.gap)} ${needText}`;
        node.className = "status warn";
      }
    };

    const renderRuleBasis = (rule) => {
      const rows = Array.isArray(rule.legal_basis) ? rule.legal_basis : [];
      if (!rows.length) {
        ui.legalBasis.style.display = "none";
        ui.legalBasis.innerHTML = "";
        return;
      }
      const parts = rows.map((item) => {
        const lawTitle = esc(item.law_title || "");
        const article = esc(item.article || "");
        const url = esc(item.url || "");
        if (!url) {
          return `${lawTitle} ${article}`.trim();
        }
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${lawTitle} ${article}</a>`;
      });
      ui.legalBasis.innerHTML = `<strong>법령 근거</strong><br>${parts.join("<br>")}`;
      ui.legalBasis.style.display = "block";
    };

    const renderResult = () => {
      const selected = getSelectedIndustry();
      if (!selected) {
        clearResult();
        return;
      }

      const industryName = String(selected.service_name || "");
      const serviceCode = String(selected.service_code || "");
      const rule = ruleLookup[serviceCode] || null;

      const rawCapitalInput = String(ui.capitalInput.value || "").trim();
      const currentCapital = Core.toNum(rawCapitalInput);
      const currentTechnicians = Core.toInt(ui.technicianInput.value || 0);
      const currentEquipment = Core.toInt(ui.equipmentInput.value || 0);

      if (!rule) {
        ui.requiredCapital.textContent = "상담 확정";
        ui.requirementsMeta.textContent = "이 업종은 현재 법령 근거 데이터셋의 정량 규칙 연동 대상이 아닙니다.";
        ui.capitalGapStatus.textContent = "법령 기준 매핑 필요";
        ui.capitalGapStatus.className = "status warn";
        ui.technicianGapStatus.textContent = "법령 기준 매핑 필요";
        ui.technicianGapStatus.className = "status warn";
        ui.equipmentGapStatus.textContent = "법령 기준 매핑 필요";
        ui.equipmentGapStatus.className = "status warn";
        ui.diagnosisDate.textContent = "-";
        ui.crossValidation.textContent = "";
        ui.fallbackGuide.style.display = "block";
        ui.fallbackGuide.textContent = `${industryName}: 업종 등록기준(자본금/기술인력/장비) 법령 매핑을 먼저 확정해야 합니다.`;
        ui.legalBasis.style.display = "none";
        ui.legalBasis.innerHTML = "";
        return;
      }

      const req = rule.requirements || {};
      const capitalGap = Core.computeGap(req.capital_eok, currentCapital);
      const technicianGap = Core.computeIntGap(req.technicians, currentTechnicians);
      const equipmentGap = Core.computeIntGap(req.equipment_count, currentEquipment);
      const diagnosis = Core.predictDiagnosisDate(req.deposit_days);

      ui.requiredCapital.textContent = Core.formatEok(req.capital_eok || 0);
      ui.requirementsMeta.textContent =
        `기술자 ${Core.toInt(req.technicians)}명 / 장비 ${Core.toInt(req.equipment_count)}식 / 예치 ${Core.toInt(req.deposit_days)}일`;

      renderGapStatus(ui.capitalGapStatus, capitalGap, Core.formatEok, "자본금 요건 충족", "추가 확보 필요");
      renderGapStatus(
        ui.technicianGapStatus,
        technicianGap,
        (v) => `${Core.toInt(v).toLocaleString("ko-KR")}명`,
        "기술인력 요건 충족",
        "추가 채용 필요",
      );
      renderGapStatus(
        ui.equipmentGapStatus,
        equipmentGap,
        (v) => `${Core.toInt(v).toLocaleString("ko-KR")}식`,
        "장비 요건 충족",
        "추가 확보 필요",
      );

      ui.diagnosisDate.textContent = `${diagnosis.dateLabel} (D+${diagnosis.days})`;

      const suspicious = Core.detectSuspiciousCapitalInput(rawCapitalInput, currentCapital, req.capital_eok || 0);
      if (suspicious) {
        ui.crossValidation.textContent =
          `입력 자본금이 ${Core.formatEok(currentCapital)}이 맞는지 확인해 주세요. 단위(억) 오입력 가능성이 있습니다.`;
      } else {
        ui.crossValidation.textContent = "";
      }

      ui.fallbackGuide.style.display = "none";
      ui.fallbackGuide.textContent = "";
      renderRuleBasis(rule);
    };

    const init = () => {
      renderCategories();
      renderIndustries();
      clearResult();
      ui.categorySelect.addEventListener("change", () => {
        renderIndustries();
        clearResult();
      });
      ui.industrySelect.addEventListener("change", renderResult);
      ui.capitalInput.addEventListener("input", renderResult);
      ui.technicianInput.addEventListener("input", renderResult);
      ui.equipmentInput.addEventListener("input", renderResult);
    };

    init();
  </script>
</body>
</html>
"""

    meta_source = dict(rule_catalog_meta.get("source") or {})
    version = str(rule_catalog_meta.get("version", "") or "미지정")
    effective_date = str(rule_catalog_meta.get("effective_date", "") or "미지정")
    if not effective_date and meta_source.get("fetched_at"):
        effective_date = str(meta_source.get("fetched_at"))

    return (
        html_template.replace("__TITLE__", escape(str(title or "")))
        .replace("__INDUSTRY_TOTAL__", str(_coerce_non_negative_int(summary.get("industry_total", 0))))
        .replace("__MAJOR_TOTAL__", str(_coerce_non_negative_int(summary.get("major_category_total", 0))))
        .replace("__WITH_RULE_TOTAL__", str(_coerce_non_negative_int(summary.get("with_registration_rule_total", 0))))
        .replace("__RULE_VERSION__", escape(version))
        .replace("__RULE_EFFECTIVE_DATE__", escape(effective_date))
        .replace("__PERMIT_CATALOG_JSON__", _safe_json(permit_catalog))
        .replace("__RULE_LOOKUP_JSON__", _safe_json(rules_lookup))
        .replace("__RULE_CATALOG_META_JSON__", _safe_json(rule_catalog_meta))
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI permit pre-check calculator HTML")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG_PATH), help="Path to collected permit industry JSON")
    parser.add_argument("--rules", default=str(DEFAULT_RULES_PATH), help="Path to objective legal rules JSON")
    parser.add_argument("--output", default="output/ai_permit_precheck.html", help="Output HTML file path")
    parser.add_argument("--title", default="AI 인허가 사전검토 진단기 | 서울건설정보", help="HTML title")
    # Backward-compatible no-op args so legacy deploy commands do not fail.
    parser.add_argument("--contact-phone", default="")
    parser.add_argument("--openchat-url", default="")
    parser.add_argument("--consult-endpoint", default="")
    parser.add_argument("--usage-endpoint", default="")
    args = parser.parse_args()

    catalog = _load_catalog(Path(args.catalog).expanduser().resolve())
    rules = _load_rule_catalog(Path(args.rules).expanduser().resolve())

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_html(title=str(args.title), catalog=catalog, rule_catalog=rules), encoding="utf-8")
    print(f"[saved] {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
