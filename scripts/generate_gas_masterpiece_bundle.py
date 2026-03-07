import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]


def _py_cmd(args: List[str]) -> List[str]:
    if shutil.which("py"):
        return ["py", "-3", *args]
    return [sys.executable, *args]


def _run(cmd: List[str], env_override: Dict[str, str] | None = None, timeout_sec: int = 420) -> Dict[str, Any]:
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    if env_override:
        env.update({k: str(v) for k, v in env_override.items()})
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
        env=env,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": int(proc.returncode),
        "command": cmd,
        "stdout_tail": "\n".join((proc.stdout or "").splitlines()[-80:]),
        "stderr_tail": "\n".join((proc.stderr or "").splitlines()[-80:]),
    }


def _find_js_assignment(source: str, var_name: str, opener: str, closer: str) -> str:
    pattern = (
        rf"(?:const|let|var)\s+{re.escape(var_name)}\s*=\s*"
        rf"({re.escape(opener)}[\s\S]*?{re.escape(closer)});"
    )
    m = re.search(pattern, source, flags=re.S)
    return m.group(1) if m else ""


def _json_load_maybe_escaped(payload: str) -> Any:
    tried: List[str] = [payload]
    # admin/filter-safe inline script can escape quotes: [{\"k\":\"v\"}]
    if '\\"' in payload:
        tried.append(payload.replace('\\"', '"'))
    for cand in tried:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    return None


def _decode_eval_code_block(html: str) -> str:
    m = re.search(r'var\s+code\s*=\s*"(.*?)";\s*code=code\.replace', html, flags=re.S)
    if not m:
        return ""
    escaped = m.group(1)
    try:
        return bytes(escaped, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return bytes(escaped, "utf-8").decode("unicode_escape", errors="replace")


def _extract_dataset_from_source(source: str) -> List[Dict[str, Any]]:
    payload = _find_js_assignment(source, "dataset", "[", "]")
    if not payload:
        payload = _find_js_assignment(source, "datasetRaw", "[", "]")
    if not payload:
        payload = _find_js_assignment(source, "SMNA_DATASET", "[", "]")
    if not payload:
        return []
    raw = _json_load_maybe_escaped(payload)
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for row in raw:
        if isinstance(row, dict):
            out.append(row)
            continue
        if isinstance(row, list):
            out.append(
                {
                    "now_uid": str(row[0] if len(row) > 0 else ""),
                    "seoul_no": row[1] if len(row) > 1 else 0,
                    "license_text": str(row[2] if len(row) > 2 else ""),
                    "tokens": row[3] if len(row) > 3 and isinstance(row[3], list) else [],
                    "license_year": row[4] if len(row) > 4 else None,
                    "specialty": row[5] if len(row) > 5 else None,
                    "y23": row[6] if len(row) > 6 else None,
                    "y24": row[7] if len(row) > 7 else None,
                    "y25": row[8] if len(row) > 8 else None,
                    "sales3_eok": row[9] if len(row) > 9 else None,
                    "sales5_eok": row[10] if len(row) > 10 else None,
                    "capital_eok": row[11] if len(row) > 11 else None,
                    "surplus_eok": row[12] if len(row) > 12 else None,
                    "debt_ratio": row[13] if len(row) > 13 else None,
                    "liq_ratio": row[14] if len(row) > 14 else None,
                    "company_type": str(row[15] if len(row) > 15 else ""),
                    "balance_eok": row[16] if len(row) > 16 else None,
                    "price_eok": row[17] if len(row) > 17 else None,
                    "display_low_eok": row[18] if len(row) > 18 else None,
                    "display_high_eok": row[19] if len(row) > 19 else None,
                    "url": str(row[20] if len(row) > 20 else ""),
                }
            )
    return out


def _extract_meta_from_source(source: str) -> Dict[str, Any]:
    payload = _find_js_assignment(source, "meta", "{", "}")
    if not payload:
        payload = _find_js_assignment(source, "SMNA_META", "{", "}")
    if not payload:
        return {}
    raw = _json_load_maybe_escaped(payload)
    return raw if isinstance(raw, dict) else {}


def _extract_dataset_from_html(html: str) -> List[Dict[str, Any]]:
    direct = _extract_dataset_from_source(html)
    if direct:
        return direct
    decoded = _decode_eval_code_block(html)
    if decoded:
        return _extract_dataset_from_source(decoded)
    return []


def _extract_meta_from_html(html: str) -> Dict[str, Any]:
    direct = _extract_meta_from_source(html)
    if direct:
        return direct
    decoded = _decode_eval_code_block(html)
    if decoded:
        return _extract_meta_from_source(decoded)
    return {}


def _safe_json(data: Any) -> str:
    txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return txt.replace("</", "<\\/")


def _code_gs(dataset: List[Dict[str, Any]], meta: Dict[str, Any]) -> str:
    dataset_json = _safe_json(dataset)
    meta_json = _safe_json(meta)
    return rf"""
const SMNA_DATASET = {dataset_json};
const SMNA_META = {meta_json};
const SHEET_USAGE_TAB = 'ai_calc_usage';
const SHEET_CONSULT_TAB = 'ai_calc_consult';

function doGet(e) {{
  const p = (e && e.parameter) ? e.parameter : {{}};
  const modeRaw = String(p.mode || 'customer').toLowerCase();
  const mode = (modeRaw === 'acquisition' || modeRaw === 'newreg' || modeRaw === 'permit_precheck')
    ? 'permit_precheck'
    : 'customer';
  const execUrl = getExecUrl_(e);
  if (String(p.api || '') === '1') {{
    return jsonOut_({{ ok: true, mode, generated_at: new Date().toISOString(), train_count: SMNA_DATASET.length, meta: SMNA_META }});
  }}
  const fileName = (mode === 'permit_precheck') ? 'acquisition' : 'customer';
  return renderPage_(fileName, execUrl, mode);
}}

function doPost(e) {{
  const payload = parseJson_((e && e.postData) ? e.postData.contents : '');
  if (!payload) return jsonOut_({{ ok: false, error: 'invalid_json' }});

  if (payload.action === 'estimate' || hasEstimateSignal_(payload)) {{
    return jsonOut_(estimate_(payload));
  }}
  if (payload.action === 'consult' || hasConsultSignal_(payload)) {{
    const row = buildConsultRow_(payload);
    appendToSheet_(SHEET_CONSULT_TAB, row);
    return jsonOut_({{ ok: true, stored: true, type: 'consult' }});
  }}
  if (payload.action === 'usage' || hasUsageSignal_(payload)) {{
    const row = buildUsageRow_(payload);
    appendToSheet_(SHEET_USAGE_TAB, row);
    return jsonOut_({{ ok: true, stored: true, type: 'usage' }});
  }}
  return jsonOut_({{ ok: false, error: 'unsupported_payload' }});
}}

function renderPage_(fileName, execUrl, mode) {{
  let html = HtmlService.createHtmlOutputFromFile(fileName).getContent();
  html = html.replace(/__GAS_EXEC_URL__/g, String(execUrl || ''));
  const pageTitle = (String(mode || '').toLowerCase() === 'permit_precheck')
    ? 'AI 인허가 사전검토 진단기(신규등록 전용)'
    : 'AI 양도가 산정 계산기';
  return HtmlService
    .createHtmlOutput(html)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .setTitle(pageTitle);
}}

function getExecUrl_(e) {{
  try {{
    if (e && e.parameter && e.parameter.exec_url) return String(e.parameter.exec_url || '');
    if (e && e.parameter && e.parameter.api_url) return String(e.parameter.api_url || '');
  }} catch (_e) {{}}
  return ''; // 배포 후 최초 1회는 생성 URL을 고객 HTML에 치환해도 됩니다.
}}

function parseJson_(raw) {{
  try {{
    const text = String(raw || '').trim();
    if (!text) return null;
    return JSON.parse(text);
  }} catch (_e) {{
    return null;
  }}
}}

function jsonOut_(data) {{
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}}

function hasEstimateSignal_(p) {{
  const keys = ['license_text','license','y23','y24','y25','balance_eok','capital_eok','surplus_eok','specialty','license_year'];
  return keys.some((k) => p[k] !== undefined && p[k] !== null && String(p[k]).trim() !== '');
}}

function hasConsultSignal_(p) {{
  const name = String(p.customer_name || p.name || '').trim();
  const phone = String(p.customer_phone || p.phone || '').trim();
  const email = String(p.customer_email || p.email || '').trim();
  return !!(name || phone || email);
}}

function hasUsageSignal_(p) {{
  return String(p.event_type || p.source || '').trim().length > 0;
}}

function toNum_(v) {{
  if (v === null || v === undefined) return null;
  const n = Number(String(v).replace(/,/g, '').trim());
  return Number.isFinite(n) ? n : null;
}}

function compact_(v) {{
  return String(v || '').replace(/\\s+/g, ' ').trim();
}}

function normToken_(v) {{
  return compact_(v)
    .replace(/[()\[\]]/g, '')
    .replace(/주식회사/g, '')
    .replace(/공사업|건설업|업종|면허|사업/g, '')
    .trim();
}}

function tokenize_(licenseText) {{
  const src = String(licenseText || '').replace(/<br\\s*\\/?\\>/gi, '\\n');
  const parts = src.split(/[\\n\\/,|·&\\s]+/g).map(normToken_).filter(Boolean);
  return Array.from(new Set(parts));
}}

function intersectCount_(a, b) {{
  if (!a.length || !b.length) return 0;
  const setA = new Set(a);
  let c = 0;
  for (const x of b) if (setA.has(x)) c += 1;
  return c;
}}

function jaccard_(a, b) {{
  if (!a.length || !b.length) return 0;
  const inter = intersectCount_(a, b);
  const union = new Set([].concat(a, b)).size;
  return union > 0 ? (inter / union) : 0;
}}

function relClose_(x, y) {{
  if (!Number.isFinite(x) || !Number.isFinite(y)) return 0.35;
  const d = Math.max(Math.abs(x), Math.abs(y), 1);
  const r = Math.abs(x - y) / d;
  return Math.max(0, 1 - Math.min(1, r));
}}

function positiveRatio_(num, den) {{
  if (!Number.isFinite(num) || !Number.isFinite(den) || den <= 0) return NaN;
  const v = num / den;
  return Number.isFinite(v) && v > 0 ? v : NaN;
}}

function weightedQuantile_(values, weights, q) {{
  const arr = [];
  for (let i = 0; i < values.length; i += 1) {{
    const v = Number(values[i]);
    const w = Number(weights[i]);
    if (!Number.isFinite(v) || !Number.isFinite(w) || w <= 0) continue;
    arr.push([v, w]);
  }}
  if (!arr.length) return null;
  arr.sort((a, b) => a[0] - b[0]);
  const total = arr.reduce((s, x) => s + x[1], 0);
  if (total <= 0) return null;
  const target = Math.max(0, Math.min(1, Number(q))) * total;
  let run = 0;
  for (const [v, w] of arr) {{
    run += w;
    if (run >= target) return v;
  }}
  return arr[arr.length - 1][0];
}}

function avg_(rows, key) {{
  const vals = rows.map((r) => Number(r[key])).filter((x) => Number.isFinite(x));
  if (!vals.length) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}}

function estimate_(payload) {{
  const licenseText = compact_(payload.license_text || payload.license || '');
  const tokens = tokenize_(licenseText);
  const y21 = toNum_(payload.y21), y22 = toNum_(payload.y22), y23 = toNum_(payload.y23), y24 = toNum_(payload.y24), y25 = toNum_(payload.y25);
  const sales3 = [y23, y24, y25].filter(Number.isFinite).reduce((a, b) => a + b, 0) || null;
  const sales5 = [y21, y22, y23, y24, y25].filter(Number.isFinite).reduce((a, b) => a + b, 0) || sales3;
  const focusSales = ((sales3 || 0) >= (sales5 || 0)) ? (sales3 || sales5 || 0) : (sales5 || sales3 || 0);

  const target = {{
    tokens,
    license_year: toNum_(payload.license_year),
    specialty: toNum_(payload.specialty),
    balance_eok: toNum_(payload.balance_eok || payload.balance),
    claim_price_eok: toNum_(payload.claim_price_eok || payload.claim_eok || payload.claim_price),
    capital_eok: toNum_(payload.capital_eok || payload.capital),
    surplus_eok: toNum_(payload.surplus_eok || payload.surplus),
    focus_sales: focusSales,
    ok_capital: !!payload.ok_capital,
    ok_engineer: !!payload.ok_engineer,
    ok_office: !!payload.ok_office,
    credit_level: compact_(payload.credit_level || ''),
    admin_history: compact_(payload.admin_history || ''),
    provided_signals: Number(payload.provided_signals || 0),
    missing_critical: Array.isArray(payload.missing_critical) ? payload.missing_critical : [],
  }};
  const CORE_LICENSE_TOKENS = new Set([
    "전기", "정보통신", "소방", "기계설비", "가스",
    "토건", "토목", "건축", "조경", "실내",
    "토공", "포장", "철콘", "상하", "석공", "비계", "석면", "습식", "도장",
    "조경식재", "조경시설", "산림토목", "도시정비", "보링", "수중", "금속",
  ]);
  const CORE_LICENSE_TOKENS_SORTED = Array.from(CORE_LICENSE_TOKENS).sort((a, b) => b.length - a.length);
  const CORE_TEXT_ALIAS_MAP = {{
    "실내건축": "실내",
    "철근콘크리트": "철콘",
    "상하수도설비": "상하",
    "토목건축": "토건",
    "정보통신공사업": "정보통신",
    "통신공사업": "정보통신",
    "통신": "정보통신",
    "기계설비공사업": "기계설비",
    "기계가스설비공사업": "기계설비",
    "기계가스": "기계설비",
    "기계": "기계설비",
    "금속구조물창호온실": "금속",
    "비계구조물해체": "비계",
    "석면해체제거": "석면",
    "습식방수석공": "습식",
    "소방시설": "소방",
    "전기공사업": "전기",
    "소방공사업": "소방",
  }};
  const coreTokensFromText_ = (raw) => {{
    const key = normToken_(raw || "");
    const out = new Set();
    if (!key) return out;
    if (CORE_TEXT_ALIAS_MAP[key]) {{
      out.add(CORE_TEXT_ALIAS_MAP[key]);
      return out;
    }}
    for (const token of CORE_LICENSE_TOKENS_SORTED) {{
      if (token && key.indexOf(token) >= 0) out.add(token);
    }}
    return out;
  }};
  const coreTokens_ = (arr) => {{
    const set = new Set(Array.isArray(arr) ? arr : []);
    const out = new Set();
    set.forEach((t) => {{
      const s = String(t || "");
      if (!s) return;
      if (CORE_LICENSE_TOKENS.has(s)) out.add(s);
      coreTokensFromText_(s).forEach((v) => out.add(v));
    }});
    return out;
  }};
  const isSingleTokenCrossCombo_ = (targetArr, candArr, candLicenseText) => {{
    const c = new Set(Array.isArray(candArr) ? candArr : []);
    const tv = singleTokenTargetCore_(targetArr);
    const cc = new Set([...coreTokens_(Array.from(c)), ...coreTokensFromText_(candLicenseText || "")]);
    if (!tv || (!c.has(tv) && !cc.has(tv))) return false;
    if (cc.size <= 1) return false;
    for (const tok of cc) {{
      if (tok !== tv) return true;
    }}
    return false;
  }};
  const singleTokenTargetCore_ = (targetArr) => {{
    const t = new Set(Array.isArray(targetArr) ? targetArr : []);
    const core = new Set([...coreTokens_(Array.from(t))]);
    if (core.size === 1) return Array.from(core)[0];
    if (t.size === 1) return Array.from(t)[0] || '';
    return '';
  }};
  const isSingleTokenSameCore_ = (targetArr, candArr, candLicenseText) => {{
    const target = singleTokenTargetCore_(targetArr);
    if (!target) return false;
    const c = new Set(Array.isArray(candArr) ? candArr : []);
    const candCore = new Set([...coreTokens_(Array.from(c)), ...coreTokensFromText_(candLicenseText || '')]);
    if (candCore.size >= 2) return false;
    if (candCore.size === 1) return candCore.has(target);
    if (c.size === 1) {{
      const tok = Array.from(c)[0] || '';
      return !!tok && (tok.indexOf(target) >= 0 || target.indexOf(tok) >= 0);
    }}
    return false;
  }};
  const isSingleTokenProfileOutlier_ = (targetObj, rowObj) => {{
    if (!targetObj || !Array.isArray(targetObj.tokens) || !singleTokenTargetCore_(targetObj.tokens) || !rowObj) return false;
    const specRatio = positiveRatio_(targetObj.specialty, Number(rowObj.specialty));
    const salesRatio = positiveRatio_(targetObj.focus_sales, Number(rowObj.sales3_eok));
    if (Number.isFinite(specRatio) && (specRatio < 0.30 || specRatio > 3.30)) return true;
    if (Number.isFinite(salesRatio) && (salesRatio < 0.30 || salesRatio > 3.30)) return true;
    return false;
  }};

  const rows = Array.isArray(SMNA_DATASET) ? SMNA_DATASET : [];
  if (!rows.length) {{
    return {{ ok: false, error: 'dataset_unavailable' }};
  }}

  let scored = [];
  const minSimilarity = target.tokens.length >= 2 ? 26 : (target.tokens.length ? 20 : 10);
  const strictSameCore = !!singleTokenTargetCore_(target.tokens);
  const targetCoreSet = coreTokens_(target.tokens);
  const targetCoreCount = targetCoreSet.size;
  const scoreRows_ = (pool, strictOnly, threshold) => {{
    const out = [];
    for (const row of pool) {{
      const price = Number(row.price_eok);
      if (!Number.isFinite(price) || price <= 0) continue;
      const candTokens = Array.isArray(row.tokens) ? row.tokens.map(normToken_).filter(Boolean) : tokenize_(row.license_text || '');
      const candCore = new Set([...coreTokens_(candTokens), ...coreTokensFromText_(row.license_text || '')]);
      if (targetCoreCount >= 2) {{
        const hasCoreOverlap = Array.from(targetCoreSet).some((x) => candCore.has(x));
        if (!hasCoreOverlap) continue;
      }}
      if (strictOnly && !isSingleTokenSameCore_(target.tokens, candTokens, row.license_text || '')) continue;
      if (isSingleTokenCrossCombo_(target.tokens, candTokens, row.license_text || '')) continue;
      if (isSingleTokenProfileOutlier_(target, row)) continue;
      const inter = intersectCount_(target.tokens, candTokens);
      const tokenPrecision = candTokens.length ? (inter / candTokens.length) : 0;
      let sim = 0;
      sim += jaccard_(target.tokens, candTokens) * 52;
      sim += Math.min(16, inter * 4.5);
      sim += relClose_(target.specialty, Number(row.specialty)) * 6;
      sim += relClose_(target.focus_sales, Math.max(Number(row.sales3_eok) || 0, Number(row.sales5_eok) || 0)) * 8;
      sim += relClose_(target.license_year, Number(row.license_year)) * 2;
      sim += relClose_(target.balance_eok, Number(row.balance_eok)) * 10;
      sim += relClose_(target.capital_eok, Number(row.capital_eok)) * 9;
      sim += relClose_(target.surplus_eok, Number(row.surplus_eok)) * 8;
      if (target.tokens.length && candTokens.length && inter === 0) sim *= 0.58;
      if (strictSameCore && candTokens.length >= 2 && inter > 0) {{
        sim *= 0.62;
        if (tokenPrecision < 0.60) sim *= 0.72;
        const specRatio = (Number.isFinite(target.specialty) && Number(row.specialty)) ? (target.specialty / Number(row.specialty)) : NaN;
        const salesRatio = (Number.isFinite(target.focus_sales) && Number(row.sales3_eok)) ? (target.focus_sales / Number(row.sales3_eok)) : NaN;
        if (
          (Number.isFinite(specRatio) && (specRatio < 0.35 || specRatio > 2.85)) ||
          (Number.isFinite(salesRatio) && (salesRatio < 0.35 || salesRatio > 2.85))
        ) {{
          sim *= 0.72;
        }}
      }}
      sim = Math.max(0, Math.min(100, sim));
      if (sim < threshold) continue;
      out.push([sim, row, tokenPrecision, candTokens.length]);
    }}
    return out;
  }};
  scored = scoreRows_(rows, strictSameCore, minSimilarity);
  if (strictSameCore && !scored.length) scored = scoreRows_(rows, true, Math.max(12, minSimilarity - 8));

  if (!scored.length) {{
    return {{ ok: false, error: 'neighbors_not_found' }};
  }}

  scored.sort((a, b) => b[0] - a[0]);
  const minStats = Math.max(10, Number(payload.top_k || 12));
  const tokenCount = targetCoreCount > 0 ? targetCoreCount : target.tokens.length;
  const simWindow = tokenCount >= 2 ? 18 : (strictSameCore ? 14 : 10);
  const bestSim = Number(scored[0][0]);
  const statsFloor = Math.max(minSimilarity, bestSim - simWindow);
  let statsScored = scored.filter((x) => Number(x[0]) >= statsFloor);
  if (strictSameCore) {{
    const strict = statsScored.filter((x) => {{
      const row = x && x[1] ? x[1] : {{}};
      const candTokens = Array.isArray(row.tokens) ? row.tokens : [];
      if (!isSingleTokenSameCore_(target.tokens, candTokens, row.license_text || '')) return false;
      if (isSingleTokenCrossCombo_(target.tokens, candTokens, row.license_text || '')) return false;
      if (isSingleTokenProfileOutlier_(target, row)) return false;
      return Number(x[3] || 0) <= 1 || Number(x[2] || 0) >= 0.60;
    }});
    if (strict.length >= Math.max(10, minStats)) statsScored = strict;
  }}
  if (statsScored.length < minStats) {{
    statsScored = scored.slice(0, Math.max(minStats, 48));
  }}
  const scoredDisplay = scored.slice(0, 12);

  const prices = statsScored.map((x) => Number(x[1].price_eok));
  const weights = statsScored.map((x) => Math.max(0.1, Number(x[0])));
  let center = weightedQuantile_(prices, weights, 0.5);
  let low = weightedQuantile_(prices, weights, 0.25);
  let high = weightedQuantile_(prices, weights, 0.75);
  let p10 = weightedQuantile_(prices, weights, 0.10);
  let p90 = weightedQuantile_(prices, weights, 0.90);
  let p95 = weightedQuantile_(prices, weights, 0.95);
  if (!Number.isFinite(center)) center = prices.reduce((a, b) => a + b, 0) / prices.length;
  if (!Number.isFinite(low)) low = Math.min(...prices);
  if (!Number.isFinite(high)) high = Math.max(...prices);
  if (!Number.isFinite(p10)) p10 = Math.min(...prices);
  if (!Number.isFinite(p90)) p90 = Math.max(...prices);
  if (!Number.isFinite(p95)) p95 = Math.max(...prices);
  const avgSim = statsScored.reduce((s, x) => s + Number(x[0]), 0) / statsScored.length;

  const claim = Number(target.claim_price_eok);
  if (Number.isFinite(claim) && claim > 0) {{
    const baseCenter = Number(center);
    const gapRatio = Math.abs(claim - baseCenter) / Math.max(baseCenter, 0.1);
    let claimWeight = Math.min(0.35, 0.18 + Math.max(0, gapRatio - 0.15) * 0.20);
    const p90Safe = Math.max(Number(p90), 0.1);
    const p10Safe = Math.max(Number(p10), 0.1);
    if (claim > (p90Safe * 1.25) && avgSim >= 52) {{
      let uplift = Math.min(0.40, Math.max(0, ((claim / p90Safe) - 1.25) * 0.28));
      if (statsScored.length <= 6) uplift *= 1.15;
      if (target.tokens.length >= 2) uplift *= 1.10;
      claimWeight = Math.min(0.72, claimWeight + uplift);
    }} else if (claim < (p10Safe * 0.80) && avgSim >= 52) {{
      const down = Math.min(0.20, Math.max(0, (0.80 - (claim / p10Safe)) * 0.18));
      claimWeight = Math.max(0.10, claimWeight - down);
    }}
    center = (baseCenter * (1 - claimWeight)) + (claim * claimWeight);
    low = Math.min(low, center);
    high = Math.max(high, center);
    if (claim >= 20 && avgSim >= 55) {{
      const highGap = (claim / Math.max(center, 0.1)) - 1;
      if (highGap > 0.22) {{
        const sparsePull = Math.min(0.34, Math.max(0.10, ((highGap - 0.22) * 0.28) + 0.10));
        center = (center * (1 - sparsePull)) + (claim * sparsePull);
        low = Math.min(low, center);
        high = Math.max(high, center);
      }}
    }}
    if (claim > high * 1.18) {{
      const extra = Math.min(claim - high, Math.max(center * 0.45, (high - low) * 0.80));
      let extraW = 0.55;
      if (claim >= 20 && avgSim >= 55) extraW = 0.86;
      high = high + Math.max(0, extra * extraW);
    }}
    if (claim >= 20 && avgSim >= 55 && claim > Math.max(p90 * 1.20, center * 1.18)) {{
      high = Math.max(high, claim);
    }}
  }}

  const upperCap = Math.max(Number(p95) * 1.35, Number(p90) * 1.45, Number(high) * 1.15, 0.15);
  const claimAllowsHigh = Number.isFinite(claim) && claim > (upperCap * 1.05);
  if (center > upperCap && !claimAllowsHigh) {{
    const ratio = (center / Math.max(upperCap, 0.1)) - 1;
    const pull = Math.min(0.65, Math.max(0.18, ratio * 0.55 + 0.18));
    const nextCenter = (center * (1 - pull)) + (upperCap * pull);
    const scale = nextCenter / Math.max(center, 0.1);
    center = nextCenter;
    low = Math.max(0.05, low * scale);
    high = Math.max(low, high * scale);
  }}

  const avgBalance = avg_(rows, 'balance_eok');
  const avgCapital = avg_(rows, 'capital_eok');
  const avgSurplus = avg_(rows, 'surplus_eok');

  const notes = [];
  let factor = 1;

  function applyRel(label, value, avg, weight, cap) {{
    if (!Number.isFinite(value) || !Number.isFinite(avg) || avg <= 0) return;
    const rel = (value - avg) / Math.max(avg, 0.1);
    let adj = rel * weight;
    adj = Math.max(-cap, Math.min(cap, adj));
    if (Math.abs(adj) >= 0.01) notes.push(`${{label}} 반영: ${{adj >= 0 ? '+' : ''}}${{(adj * 100).toFixed(1)}}%`);
    factor += adj;
  }}

  function applySalesTrendAdj() {{
    const y23v = Number.isFinite(y23) ? y23 : NaN;
    const y24v = Number.isFinite(y24) ? y24 : NaN;
    const y25v = Number.isFinite(y25) ? y25 : NaN;
    if (!Number.isFinite(y23v) && !Number.isFinite(y24v) && !Number.isFinite(y25v)) return 0;

    let targetTrend = 0;
    let tw = 0;
    if (Number.isFinite(y25v) && Number.isFinite(y24v) && Math.abs(y24v) > 0.1) {{
      targetTrend += ((y25v - y24v) / Math.max(Math.abs(y24v), 0.1)) * 0.64;
      tw += 0.64;
    }}
    if (Number.isFinite(y25v) && Number.isFinite(y23v) && Math.abs(y23v) > 0.1) {{
      targetTrend += ((y25v - y23v) / Math.max(Math.abs(y23v), 0.1)) * 0.36;
      tw += 0.36;
    }}
    if (tw <= 0) return 0;
    targetTrend = Math.max(-1.2, Math.min(1.2, targetTrend / tw));

    const trendVals = [];
    const trendWts = [];
    for (const [sim, row] of statsScored) {{
      const n23 = Number(row.y23);
      const n25 = Number(row.y25);
      if (!Number.isFinite(n23) || !Number.isFinite(n25) || Math.abs(n23) <= 0.1) continue;
      const tr = (n25 - n23) / Math.max(Math.abs(n23), 0.1);
      if (!Number.isFinite(tr)) continue;
      trendVals.push(Math.max(-1.6, Math.min(1.6, tr)));
      trendWts.push(Math.max(0.2, Number(sim) / 40));
    }}

    let statAdj = 0;
    if (trendVals.length >= 4) {{
      const q50 = weightedQuantile_(trendVals, trendWts, 0.5);
      const q25 = weightedQuantile_(trendVals, trendWts, 0.25);
      const q75 = weightedQuantile_(trendVals, trendWts, 0.75);
      const spread = Math.max(0.12, Math.abs((q75 || 0) - (q25 || 0)));
      const z = (targetTrend - (Number.isFinite(q50) ? q50 : 0)) / spread;
      statAdj = Math.max(-0.08, Math.min(0.10, z * 0.028));
    }} else {{
      statAdj = Math.max(-0.05, Math.min(0.06, targetTrend * 0.05));
    }}

    let recencyAdj = 0;
    if (Number.isFinite(y23v) && Number.isFinite(y24v) && Number.isFinite(y25v)) {{
      const late = (y25v - y24v) / Math.max(Math.abs(y24v), 0.1);
      const early = (y24v - y23v) / Math.max(Math.abs(y23v), 0.1);
      recencyAdj = Math.max(-0.03, Math.min(0.04, (late * 0.70 + early * 0.30) * 0.03));
    }}
    const adj = Math.max(-0.10, Math.min(0.12, statAdj + recencyAdj));
    if (Math.abs(adj) >= 0.008) notes.push(`실적 추이 통계 반영(2023↔2025): ${{adj >= 0 ? '+' : ''}}${{(adj * 100).toFixed(1)}}%`);
    return adj;
  }}

  applyRel('공제조합 잔액', target.balance_eok, avgBalance, 0.20, 0.22);
  applyRel('자본금', target.capital_eok, avgCapital, 0.16, 0.18);
  // 이익잉여금은 양수자 관리 리스크로 감산 반영
  applyRel('이익잉여금', target.surplus_eok, avgSurplus, -0.18, 0.22);
  factor += applySalesTrendAdj();

  if (!target.ok_capital) {{ factor -= 0.12; notes.push('자본금 기준 미충족: 보수 하향'); }}
  if (!target.ok_engineer) {{ factor -= 0.16; notes.push('기술자 기준 미충족: 리스크 증가'); }}
  if (!target.ok_office) {{ factor -= 0.10; notes.push('사무실 기준 미충족: 리스크 증가'); }}

  const credit = String(target.credit_level || '').toLowerCase();
  if (credit === 'high') {{ factor += 0.04; notes.push('외부신용등급 우수: 가산 반영'); }}
  if (credit === 'low') {{ factor -= 0.05; notes.push('외부신용등급 주의: 감산 반영'); }}

  if (String(target.admin_history || '').toLowerCase() === 'has') {{
    factor -= 0.10;
    notes.push('행정처분 이력 있음: 리스크 반영');
  }}

  factor = Math.max(0.62, Math.min(1.42, factor));
  center *= factor;
  low *= factor;
  high *= factor;
  if (high < low) {{ const t = low; low = high; high = t; }}

  const coverage = Math.min(1, statsScored.length / 8);
  const dispersion = Math.max(0, (high - low) / Math.max(center, 0.1));
  let confidence = (avgSim * 0.60) + (coverage * 24) + Math.max(0, 20 - dispersion * 42);
  confidence -= (target.missing_critical.length * 7);
  confidence = Math.max(0, Math.min(100, confidence));

  const neighbors = scoredDisplay.map((x) => {{
    const sim = Math.round(Number(x[0]) * 10) / 10;
    const row = x[1] || {{}};
    const lo = Number(row.display_low_eok || row.price_eok || 0);
    const hi = Number(row.display_high_eok || row.price_eok || 0);
    return {{
      similarity: sim,
      seoul_no: Number(row.seoul_no || 0),
      now_uid: String(row.now_uid || ''),
      license_text: String(row.license_text || ''),
      price_eok: Number(row.price_eok || 0),
      display_low_eok: Number.isFinite(lo) ? lo : null,
      display_high_eok: Number.isFinite(hi) ? hi : null,
      y23: Number(row.y23 || 0),
      y24: Number(row.y24 || 0),
      y25: Number(row.y25 || 0),
      sales3_eok: Number(row.sales3_eok || 0),
      sales5_eok: Number(row.sales5_eok || 0),
      url: String(row.url || 'https://seoulmna.co.kr/mna')
    }};
  }});

  if (!notes.length) notes.push('유사 매물 기반 기본 산정 결과입니다.');

  return {{
    ok: true,
    generated_at: new Date().toISOString(),
    estimate_center_eok: Math.round(center * 10000) / 10000,
    estimate_low_eok: Math.round(low * 10000) / 10000,
    estimate_high_eok: Math.round(high * 10000) / 10000,
    confidence_score: Math.round(confidence * 10) / 10,
    confidence_percent: Math.round(confidence),
    confidence: `${{Math.round(confidence)}}%`,
    avg_similarity: Math.round(avgSim * 10) / 10,
    neighbor_count: statsScored.length,
    display_neighbor_count: neighbors.length,
    hot_match_count: neighbors.filter((n) => Number(n.similarity) >= 90).length,
    risk_notes: notes,
    neighbors,
  }};
}}

function buildConsultRow_(p) {{
  return [
    new Date(),
    compact_(p.source || 'gas_calc'),
    compact_(p.page_mode || ''),
    compact_(p.lead_type || ''),
    compact_(p.customer_name || p.name || ''),
    compact_(p.customer_phone || p.phone || ''),
    compact_(p.customer_email || p.email || ''),
    compact_(p.license_text || p.license || ''),
    compact_(p.estimated_range || p.result_range || ''),
    compact_(p.estimated_center || p.result_center || ''),
    compact_(p.estimated_confidence || p.result_confidence || ''),
    compact_(p.summary_text || p.body || ''),
    compact_(p.page_url || ''),
    compact_(p.requested_at || ''),
  ];
}}

function buildUsageRow_(p) {{
  return [
    new Date(),
    compact_(p.source || 'gas_calc'),
    compact_(p.page_mode || ''),
    compact_(p.event_type || ''),
    compact_(p.input_license || ''),
    compact_(p.output_range || ''),
    compact_(p.output_confidence || ''),
    compact_(p.output_neighbors || ''),
    compact_(p.page_url || ''),
    compact_(p.requested_at || ''),
  ];
}}

function appendToSheet_(tabName, row) {{
  try {{
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName(tabName) || ss.insertSheet(tabName);
    sh.appendRow(row);
    return true;
  }} catch (_e) {{
    return false;
  }}
}}
""".strip() + "\n"


def _appsscript_json() -> str:
    payload = {
        "timeZone": "Asia/Seoul",
        "dependencies": {},
        "exceptionLogging": "STACKDRIVER",
        "runtimeVersion": "V8",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _read_env(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip().lstrip("\ufeff")
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate GAS masterpiece bundle for B-plan")
    parser.add_argument("--out-dir", default="output/gas_masterpiece")
    parser.add_argument("--max-train-rows", type=int, default=260)
    parser.add_argument("--report", default="logs/gas_masterpiece_bundle_latest.json")
    args = parser.parse_args()

    out_dir = (ROOT / args.out_dir).resolve()
    src_dir = out_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    env = _read_env(ROOT / ".env")
    contact_phone = str(
        env.get("CALCULATOR_CONTACT_PHONE", "") or env.get("PHONE", "") or env.get("MY_PHONE", "") or "010-9926-8661"
    ).strip()
    if "1668" in contact_phone:
        contact_phone = "010-9926-8661"

    placeholder = "__GAS_EXEC_URL__"
    build_env_placeholder = {
        "YANGDO_ESTIMATE_ENDPOINT": placeholder,
        "YANGDO_CONSULT_ENDPOINT": placeholder,
        "YANGDO_USAGE_ENDPOINT": placeholder,
        "CALCULATOR_CONTACT_PHONE": contact_phone,
    }
    build_env_dataset = {
        "YANGDO_ESTIMATE_ENDPOINT": "",
        "YANGDO_CONSULT_ENDPOINT": "",
        "YANGDO_USAGE_ENDPOINT": "",
        "CALCULATOR_CONTACT_PHONE": contact_phone,
    }

    customer_data_src = src_dir / "customer_dataset_source.html"
    customer_src = src_dir / "customer_source.html"
    acquisition_src = src_dir / "acquisition_source.html"

    steps: List[Dict[str, Any]] = []
    steps.append(
        _run(
            _py_cmd(
                [
                    "all.py",
                    "--build-yangdo-page",
                    "--yangdo-page-mode",
                    "customer",
                    "--yangdo-page-max-train-rows",
                    str(max(1, int(args.max_train_rows))),
                    "--yangdo-page-output",
                    str(customer_data_src),
                ]
            ),
            env_override=build_env_dataset,
            timeout_sec=480,
        )
    )
    steps.append(
        _run(
            _py_cmd(
                [
                    "all.py",
                    "--build-yangdo-page",
                    "--yangdo-page-mode",
                    "customer",
                    "--yangdo-page-max-train-rows",
                    str(max(1, int(args.max_train_rows))),
                    "--yangdo-page-output",
                    str(customer_src),
                ]
            ),
            env_override=build_env_placeholder,
            timeout_sec=480,
        )
    )
    steps.append(
        _run(
            _py_cmd(
                [
                    "scripts/collect_kr_permit_industries.py",
                    "--output",
                    str((ROOT / "config" / "kr_permit_industries_localdata.json").resolve()),
                    "--strict",
                ]
            ),
            timeout_sec=240,
        )
    )
    steps.append(
        _run(
            _py_cmd(
                [
                    "permit_diagnosis_calculator.py",
                    "--catalog",
                    str((ROOT / "config" / "kr_permit_industries_localdata.json").resolve()),
                    "--output",
                    str(acquisition_src),
                    "--title",
                    "AI 인허가 사전검토 진단기(신규등록 전용)",
                ]
            ),
            timeout_sec=240,
        )
    )

    ok = all(bool(x.get("ok")) for x in steps)
    error = ""
    dataset: List[Dict[str, Any]] = []
    meta: Dict[str, Any] = {}

    if ok and customer_data_src.exists() and customer_src.exists() and acquisition_src.exists():
        customer_data_html = _read_text(customer_data_src)
        customer_html = _read_text(customer_src)
        acquisition_html = _read_text(acquisition_src)
        dataset = _extract_dataset_from_html(customer_data_html)
        meta = _extract_meta_from_html(customer_data_html)
        if not dataset:
            ok = False
            error = "dataset extraction failed from customer dataset html"
        else:
            (out_dir / "Code.gs").write_text(_code_gs(dataset, meta), encoding="utf-8")
            (out_dir / "appsscript.json").write_text(_appsscript_json(), encoding="utf-8")
            (out_dir / "customer.html").write_text(customer_html, encoding="utf-8")
            (out_dir / "acquisition.html").write_text(acquisition_html, encoding="utf-8")
            (out_dir / "dataset_snapshot.json").write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
            (out_dir / "meta_snapshot.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

            guide = [
                "# GAS 마스터피스 배포 가이드",
                "",
                f"생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"학습 데이터 건수: {len(dataset)}",
                "",
                "## 1) Apps Script 프로젝트 생성",
                "- script.google.com > 새 프로젝트",
                "- `Code.gs`, `customer.html`, `acquisition.html`, `appsscript.json` 파일 내용을 각각 붙여넣기",
                "",
                "## 2) 웹앱 배포",
                "- 배포 > 새 배포 > 유형: 웹 앱",
                "- 실행 사용자: 본인 / 접근: 모든 사용자",
                "- 배포 후 `/exec` URL 확보",
                "",
                "## 3) URL 치환",
                "- 본 번들은 `__GAS_EXEC_URL__` 플레이스홀더를 사용합니다.",
                "- 웹앱 실행 URL이 확정되면 코드 변경 없이 동작합니다(서버 렌더링 시 자동 치환).",
                "",
                "## 4) 상담/사용로그 시트",
                "- 기본은 스크립트의 Active Spreadsheet에 `ai_calc_usage`, `ai_calc_consult` 탭으로 append",
                "- 스프레드시트를 미리 열어두면 자동 생성됩니다.",
                "",
                "## 5) B안 연동",
                "- co.kr 전역 배너 스니펫의 frame URL을 아래처럼 지정:",
                "  - 고객:   <exec>?mode=customer",
                "  - 신규등록 비용: <exec>?mode=acquisition",
                "",
                "## 참고",
                "- 이익잉여금은 양수자 리스크로 감산 반영",
                "- 3년/5년 실적 우위 로직 포함",
                "",
            ]
            (out_dir / "README.md").write_text("\n".join(guide), encoding="utf-8")
    elif not error:
        error = "build step failed"

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": ok,
        "out_dir": str(out_dir),
        "dataset_rows": len(dataset),
        "meta": meta,
        "steps": steps,
        "error": error,
    }
    report_path = (ROOT / args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[saved] {report_path}")
    print(f"[ok] {ok}")
    if error:
        print(f"[error] {error}")
    print(f"[bundle] {out_dir}")
    print(f"[dataset_rows] {len(dataset)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


