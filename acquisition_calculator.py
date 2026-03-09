import argparse
import json
from datetime import datetime
from html import escape
from pathlib import Path
from core_engine.channel_branding import resolve_channel_branding


def _safe_json(data):
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (
        text.replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _sanitize_endpoint(url: str) -> str:
    src = str(url or "").strip()
    if not src:
        return ""
    lowered = src.lower()
    if lowered.startswith("javascript:"):
        return ""
    if "localhost" in lowered or "127.0.0.1" in lowered or "::1" in lowered:
        return ""
    return src


def _pack_inline_script(js_code: str) -> str:
    payload = str(js_code or "").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    payload_json = json.dumps(payload, ensure_ascii=False)
    return (
        "<script nowprocket data-nowprocket>(function(){"
        "try{var code="
        + payload_json
        + ";code=code.replace(/\\\\u0026/g,String.fromCharCode(38));(0,eval)(code);}"
        "catch(e){if(window.console){try{console.error('[smna-acq] script load failed',e);}catch(_e){}}}"
        "})();</script>"
    )


def _digits_only(text: str) -> str:
    return "".join(ch for ch in str(text or "") if ch.isdigit())


def build_page_html(
    title="AI 인허가 사전검토 진단기(신규등록 전용)",
    channel_id="",
    contact_phone="",
    openchat_url="",
    consult_endpoint="",
    usage_endpoint="",
    api_key="",
):
    branding = resolve_channel_branding(
        channel_id=str(channel_id or "").strip(),
        overrides={
            "contact_phone": contact_phone,
            "openchat_url": openchat_url,
        },
    )
    contact = str(branding.get("contact_phone") or contact_phone or "1668-3548").strip()
    contact_digits = _digits_only(contact) or "16683548"
    openchat = _sanitize_endpoint(str(branding.get("openchat_url") or openchat_url or ""))
    consult = _sanitize_endpoint(consult_endpoint)
    usage = _sanitize_endpoint(usage_endpoint)
    api_key_text = str(api_key or "").strip()
    brand_name = str(branding.get("brand_name") or "파트너").strip()
    brand_label = str(branding.get("brand_label") or brand_name).strip()
    contact_email = str(branding.get("contact_email") or "").strip()
    source_tag_prefix = str(branding.get("source_tag_prefix") or "channel").strip()

    profiles = {
        "토목건축공사업(종합)": {"category": "general", "capital_eok": 8.5, "guarantee_jwasu": 225, "guarantee_deposit_eok": 2.25, "engineers": 11, "monthly_manwon": 210},
        "토목공사업(종합)": {"category": "general", "capital_eok": 5.0, "guarantee_jwasu": 131, "guarantee_deposit_eok": 1.31, "engineers": 6, "monthly_manwon": 210},
        "건축공사업(종합)": {"category": "general", "capital_eok": 5.0, "guarantee_jwasu": 131, "guarantee_deposit_eok": 1.31, "engineers": 5, "monthly_manwon": 210},
        "산업·환경설비공사업(종합)": {"category": "general", "capital_eok": 8.5, "guarantee_jwasu": 225, "guarantee_deposit_eok": 2.25, "engineers": 12, "monthly_manwon": 210},
        "조경공사업(종합)": {"category": "general", "capital_eok": 5.0, "guarantee_jwasu": 131, "guarantee_deposit_eok": 1.31, "engineers": 6, "monthly_manwon": 210},

        "실내건축공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "토공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "철근콘크리트공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "상하수도설비공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "기계설비·가스공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "기계설비공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "가스시설시공업1종(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "지반조성·포장공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "보링·그라우팅공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "금속창호·지붕건축물조립공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "도장·습식·방수·석공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "구조물해체·비계공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "조경식재·시설물공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "철도·궤도공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "철강구조물공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "수중·준설공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "승강기·삭도공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "도장공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "습식·방수공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "석공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "조적공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "금속구조물공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "지붕판금·건축물조립공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "시설물유지관리업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "비계공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "구조물해체공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "조경식재공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "조경시설물설치공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "포장공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "지반조성공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "철도궤도공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "수중공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "준설공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "승강기설치공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},
        "삭도설치공사업(전문)": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 54, "guarantee_deposit_eok": 0.54, "engineers": 2, "monthly_manwon": 210},

        "전기공사업": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 200, "guarantee_deposit_eok": 0.6, "engineers": 3, "monthly_manwon": 210},
        "정보통신공사업": {"category": "special", "capital_eok": 1.5, "guarantee_jwasu": 100, "guarantee_deposit_eok": 0.5, "engineers": 3, "monthly_manwon": 210},
        "전문소방시설공사업": {"category": "special", "capital_eok": 1.0, "guarantee_jwasu": 40, "guarantee_deposit_eok": 0.4, "engineers": 3, "monthly_manwon": 210},
        "일반소방시설공사업(기계)": {"category": "special", "capital_eok": 1.0, "guarantee_jwasu": 40, "guarantee_deposit_eok": 0.4, "engineers": 2, "monthly_manwon": 210},
        "일반소방시설공사업(전기)": {"category": "special", "capital_eok": 1.0, "guarantee_jwasu": 40, "guarantee_deposit_eok": 0.4, "engineers": 2, "monthly_manwon": 210},
        "가스시설시공업2종": {"category": "special", "capital_eok": 1.0, "guarantee_jwasu": 35, "guarantee_deposit_eok": 0.35, "engineers": 1, "monthly_manwon": 210},
        "가스시설시공업3종": {"category": "special", "capital_eok": 1.0, "guarantee_jwasu": 35, "guarantee_deposit_eok": 0.35, "engineers": 1, "monthly_manwon": 210},
    }
    major_field_options = {
        "지반조성·포장공사업(전문)": ["지반조성공사", "포장공사"],
        "도장·습식·방수·석공사업(전문)": ["도장공사", "습식·방수공사", "석공사"],
        "구조물해체·비계공사업(전문)": ["구조물해체공사", "비계공사"],
        "조경식재·시설물공사업(전문)": ["조경식재공사", "조경시설물설치공사"],
        "금속창호·지붕건축물조립공사업(전문)": ["금속구조물·창호공사", "지붕판금·건축물조립공사"],
        "수중·준설공사업(전문)": ["수중공사", "준설공사"],
        "승강기·삭도공사업(전문)": ["승강기설치공사", "삭도설치공사"],
    }
    options = ['<option value="">업종 선택</option>'] + [f'<option value="{escape(name)}">{escape(name)}</option>' for name in profiles]
    options_html = "\n".join(options)

    js_code = f"""
(function() {{
  const profiles = {_safe_json(profiles)};
  const majorFieldMap = {_safe_json(major_field_options)};
  const contactPhone = {_safe_json(contact)};
  const contactDigits = {_safe_json(contact_digits)};
  const brandName = {_safe_json(brand_name)};
  const brandLabel = {_safe_json(brand_label)};
  const contactEmail = {_safe_json(contact_email)};
  const openchatUrl = {_safe_json(openchat)};
  const consultEndpoint = {_safe_json(consult)};
  const usageEndpoint = {_safe_json(usage)};
  const apiKey = {_safe_json(api_key_text)};
  const buildApiHeaders = (baseHeaders) => {{
    const out = Object.assign({{}}, baseHeaders || {{}});
    if (apiKey) out['X-API-Key'] = apiKey;
    return out;
  }};
  const PERMIT_SERVICE_TRACK = 'permit_precheck_new_registration';
  const PERMIT_BUSINESS_DOMAIN = 'permit_precheck';
  const PERMIT_PAGE_MODE = 'permit_precheck';
  const LEGACY_PAGE_MODE = 'acquisition';
  const PERMIT_SOURCE_TAG = { _safe_json(f"{source_tag_prefix}_permit_precheck_newreg") };
  const LEGACY_SOURCE_TAG = { _safe_json(f"{source_tag_prefix}_acquisition_newreg") };
  const consultSubject = '[고객] ' + brandName + ' 인허가 사전검토 상담 요청';
  const draftStorageKey = 'smna_acq_newreg_draft_v1';
  const viewModeStorageKey = 'smna_acq_view_mode_v1';
  const urlParams = new URLSearchParams(String(location.search || ''));
  const embedFromCo = (urlParams.get('from') || '').toLowerCase() === 'co';
  const hideEmbedChrome = () => {{
    try {{
      const hideSelectors = [
        '#masthead',
        'header',
        '.site-header',
        '.site-main-header-wrap',
        '.ast-main-header-wrap',
        '.main-header-bar-wrap',
        '.ast-mobile-header-wrap',
        '.main-header-bar',
        '.ast-primary-header-bar',
        '.site-logo-img',
        '.site-branding',
        '.ast-site-identity',
        '.ast-builder-layout-element',
        '.custom-logo-link',
        '.custom-logo',
        '.entry-header',
        '.entry-title',
        '.wp-block-post-title',
        '.ast-breadcrumbs',
        '#colophon',
        '.site-below-footer-wrap',
      ];
      document.querySelectorAll(hideSelectors.join(',')).forEach((el) => {{
        if (!el) return;
        el.style.setProperty('display', 'none', 'important');
        el.style.setProperty('visibility', 'hidden', 'important');
        el.style.setProperty('height', '0', 'important');
        el.style.setProperty('min-height', '0', 'important');
        el.style.setProperty('margin', '0', 'important');
        el.style.setProperty('padding', '0', 'important');
      }});
    }} catch (_e) {{}}
  }};
  if (embedFromCo) {{
    try {{
      document.documentElement.classList.add('smna-embed-co');
      document.body && document.body.classList.add('smna-embed-co');
      hideEmbedChrome();
      const mo = new MutationObserver(() => hideEmbedChrome());
      mo.observe(document.documentElement || document.body, {{ childList: true, subtree: true }});
    }} catch (_e) {{}}
  }}
  let isAcqCalculating = false;
  const requestWithTimeout = async (url, options = {{}}, timeoutMs = 9000) => {{
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort('timeout'), timeoutMs);
    try {{
      const merged = Object.assign({{}}, options || {{}}, {{ signal: controller.signal }});
      return await fetch(url, merged);
    }} finally {{
      clearTimeout(timer);
    }}
  }};

  const $ = (id) => document.getElementById(id);
  const compact = (v) => String(v || '').replace(/\\s+/g, ' ').trim();
  const normalizeProfileKey = (v) => compact(v).toLowerCase().replace(/[^0-9a-z가-힣]/g, '');
  const numFromValue = (v) => {{ const t = String(v || '').replace(/,/g, '').trim(); if (!t) return null; const n = Number(t); return Number.isFinite(n) ? n : null; }};
  const num = (id) => {{ const el = $(id); return el ? numFromValue(el.value) : null; }};
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const eokFromManwon = (v) => (Number(v) || 0) / 10000;
  const fmtEok = (v) => {{ const n = Number(v); if (!Number.isFinite(n)) return '-'; const t = (Math.round(n * 100) / 100).toFixed(2).replace(/\\.00$/, '').replace(/(\\.\\d)0$/, '$1'); return t + '억'; }};
  const fmtManwon = (v) => {{ const n = Number(v); if (!Number.isFinite(n)) return '-'; return (Math.round(n * 10) / 10).toLocaleString('ko-KR') + '만원'; }};
  const diagnosisLawLabel = (code) => {{
    const k = compact(code).toLowerCase();
    if (k === 'electric') return '전기';
    if (k === 'telecom') return '정보통신';
    if (k === 'fire') return '소방';
    return '건설';
  }};
  const profileEntries = Object.keys(profiles || {{}}).map((name) => ({{ name, data: profiles[name], norm: normalizeProfileKey(name) }}));
  const escHtml = (value) => String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
  let pendingMajorFieldSelections = null;
  let pendingExtraLicenseSelections = null;
  const fieldWrap = (id) => {{
    const el = $(id);
    if (!el) return null;
    return el.classList.contains('field') ? el : (el.closest('.field') || el);
  }};
  const setVisible = (id, visible) => {{
    const node = fieldWrap(id);
    if (!node) return;
    node.style.display = visible ? '' : 'none';
  }};
  const isSimpleMode = () => {{
    const root = $('smna-acq-calculator');
    return !!(root && root.classList.contains('smna-simple-mode'));
  }};
  const applyViewMode = (mode) => {{
    const simple = String(mode || 'simple') !== 'advanced';
    const root = $('smna-acq-calculator');
    if (root) root.classList.toggle('smna-simple-mode', simple);
    const advancedIds = [
      'acq-license-custom',
      'acq-region-override',
      'acq-major-field-wrap',
      'acq-auto-fill',
      'acq-admin-fee',
      'acq-legal-fee',
      'acq-ok-capital',
      'acq-ok-engineer',
      'acq-ok-office',
    ];
    advancedIds.forEach((id) => setVisible(id, !simple));
    const desc = $('acq-view-mode-desc');
    if (desc) {{
      desc.textContent = simple
        ? '초간편 모드: 필수 입력만 보입니다. 업종·법인상태·주소 입력 후 바로 계산하세요.'
        : '상세 모드: 특례/수동조정/검증용 항목까지 모두 확인할 수 있습니다.';
    }}
    const btnSimple = $('acq-mode-simple');
    const btnAdvanced = $('acq-mode-advanced');
    if (btnSimple) btnSimple.classList.toggle('active', simple);
    if (btnAdvanced) btnAdvanced.classList.toggle('active', !simple);
    try {{ localStorage.setItem(viewModeStorageKey, simple ? 'simple' : 'advanced'); }} catch (_e) {{}}
  }};
  const ensureViewModeBar = () => {{
    if ($('acq-view-mode-bar')) return;
    const panelBody = document.querySelector('#smna-acq-calculator .panel .panel-body');
    if (!panelBody) return;
    const bar = document.createElement('div');
    bar.id = 'acq-view-mode-bar';
    bar.className = 'view-mode-bar';
    bar.innerHTML =
      '<button type="button" id="acq-mode-simple" class="view-mode-btn">초간편 모드</button>'
      + '<button type="button" id="acq-mode-advanced" class="view-mode-btn">상세 모드</button>'
      + '<span id="acq-view-mode-desc" class="view-mode-desc"></span>';
    const guide = panelBody.querySelector('.guide');
    panelBody.insertBefore(bar, guide || panelBody.firstChild);
    const btnSimple = $('acq-mode-simple');
    const btnAdvanced = $('acq-mode-advanced');
    if (btnSimple) btnSimple.addEventListener('click', () => applyViewMode('simple'));
    if (btnAdvanced) btnAdvanced.addEventListener('click', () => applyViewMode('advanced'));
    let saved = 'simple';
    try {{
      const raw = localStorage.getItem(viewModeStorageKey);
      if (raw === 'advanced') saved = 'advanced';
    }} catch (_e) {{}}
    applyViewMode(saved);
  }};
  const profileAliasByNorm = {{
    "실내건축": "실내건축공사업(전문)",
    "실내건축공사": "실내건축공사업(전문)",
    "실내건축공사업": "실내건축공사업(전문)",
    "실내": "실내건축공사업(전문)",
    "토공": "토공사업(전문)",
    "토공사업": "토공사업(전문)",
    "토공공사업": "토공사업(전문)",
    "철콘": "철근콘크리트공사업(전문)",
    "철근콘크리트": "철근콘크리트공사업(전문)",
    "상하": "상하수도설비공사업(전문)",
    "상하수도": "상하수도설비공사업(전문)",
    "기계설비": "기계설비·가스공사업(전문)",
    "기계가스설비": "기계설비·가스공사업(전문)",
    "가스": "기계설비·가스공사업(전문)",
    "가스1종": "가스시설시공업1종(전문)",
    "전기": "전기공사업",
    "정보통신": "정보통신공사업",
    "소방": "전문소방시설공사업",
    "지반조성포장": "지반조성·포장공사업(전문)",
    "포장": "지반조성·포장공사업(전문)",
    "지반조성": "지반조성·포장공사업(전문)",
    "보링": "보링·그라우팅공사업(전문)",
    "그라우팅": "보링·그라우팅공사업(전문)",
    "금속창호": "금속창호·지붕건축물조립공사업(전문)",
    "지붕": "금속창호·지붕건축물조립공사업(전문)",
    "금속창호지붕건축물조립": "금속창호·지붕건축물조립공사업(전문)",
    "도장": "도장·습식·방수·석공사업(전문)",
    "습식": "도장·습식·방수·석공사업(전문)",
    "방수": "도장·습식·방수·석공사업(전문)",
    "석공": "도장·습식·방수·석공사업(전문)",
    "도장습식방수석공": "도장·습식·방수·석공사업(전문)",
    "비계": "구조물해체·비계공사업(전문)",
    "구조물해체": "구조물해체·비계공사업(전문)",
    "해체": "구조물해체·비계공사업(전문)",
    "조경식재": "조경식재·시설물공사업(전문)",
    "조경시설물": "조경식재·시설물공사업(전문)",
    "철도": "철도·궤도공사업(전문)",
    "궤도": "철도·궤도공사업(전문)",
    "철강구조물": "철강구조물공사업(전문)",
    "수중": "수중·준설공사업(전문)",
    "준설": "수중·준설공사업(전문)",
    "승강기": "승강기·삭도공사업(전문)",
    "삭도": "승강기·삭도공사업(전문)",
    "시설물": "시설물유지관리업(전문)",
    "금속구조물": "금속구조물공사업(전문)",
    "조적": "조적공사업(전문)",
    "비계공사업": "비계공사업(전문)",
    "구조물해체공사업": "구조물해체공사업(전문)",
    "조경식재공사업": "조경식재공사업(전문)",
    "조경시설물설치공사업": "조경시설물설치공사업(전문)",
    "포장공사업": "포장공사업(전문)",
    "지반조성공사업": "지반조성공사업(전문)",
    "철도궤도공사업": "철도궤도공사업(전문)",
    "수중공사업": "수중공사업(전문)",
    "준설공사업": "준설공사업(전문)",
    "승강기설치공사업": "승강기설치공사업(전문)",
    "삭도설치공사업": "삭도설치공사업(전문)",
    "일반소방기계": "일반소방시설공사업(기계)",
    "일반소방전기": "일반소방시설공사업(전기)",
    "가스2종": "가스시설시공업2종",
    "가스3종": "가스시설시공업3종",
    "토건": "토목건축공사업(종합)",
    "토목건축": "토목건축공사업(종합)",
    "건축": "건축공사업(종합)",
    "토목": "토목공사업(종합)",
  }};
  const majorFieldAliasByNorm = {{
    "지반조성포장": "지반조성·포장공사업(전문)",
    "도장습식방수석공": "도장·습식·방수·석공사업(전문)",
    "구조물해체비계": "구조물해체·비계공사업(전문)",
    "조경식재시설물": "조경식재·시설물공사업(전문)",
    "금속창호지붕건축물조립": "금속창호·지붕건축물조립공사업(전문)",
    "수중준설": "수중·준설공사업(전문)",
    "승강기삭도": "승강기·삭도공사업(전문)",
  }};
  const findProfileByName = (name) => {{
    const t = compact(name);
    if (!t) return null;
    return profileEntries.find((x) => x.name === t) || null;
  }};
  const findProfileByText = (raw) => {{
    const text = compact(raw);
    if (!text) return null;
    const norm = normalizeProfileKey(text);
    if (!norm) return null;
    const aliasName = profileAliasByNorm[norm];
    if (aliasName) {{
      const aliasHit = findProfileByName(aliasName);
      if (aliasHit) return aliasHit;
    }}
    const exact = profileEntries.find((x) => x.name === text || x.norm === norm);
    if (exact) return exact;
    const partial = profileEntries.filter((x) => x.norm.indexOf(norm) >= 0 || norm.indexOf(x.norm) >= 0);
    if (partial.length === 1) return partial[0];
    if (partial.length > 1) {{
      partial.sort((a, b) => b.norm.length - a.norm.length);
      return partial[0];
    }}
    return null;
  }};
  const getMajorFieldOptionsByProfileName = (profileName) => {{
    const direct = majorFieldMap[String(profileName || '')];
    if (Array.isArray(direct)) return direct.slice();
    const norm = normalizeProfileKey(profileName);
    const parentName = majorFieldAliasByNorm[norm];
    if (parentName && Array.isArray(majorFieldMap[parentName])) return majorFieldMap[parentName].slice();
    return [];
  }};
  const getSelectedMajorFields = (options = []) => {{
    const allow = new Set((Array.isArray(options) ? options : []).map((x) => compact(x)).filter(Boolean));
    if (!allow.size) return [];
    const selected = Array.from(document.querySelectorAll('input[name="acq-major-field"]:checked'))
      .map((el) => compact(el.value))
      .filter((v, idx, arr) => !!v && allow.has(v) && arr.indexOf(v) === idx);
    if (selected.length) return selected;
    const first = Array.from(allow)[0];
    return first ? [first] : [];
  }};
  const calcMajorFieldEngineerRule = (baseEngineers, selectedCount, majorEnabled) => {{
    const base = Math.max(0, Math.round(Number(baseEngineers) || 0));
    const count = Math.max(1, Math.round(Number(selectedCount) || 1));
    if (!majorEnabled || count <= 1) {{
      return {{
        required: base,
        without_exception: base,
        reduced_count: 0,
        selected_count: count,
      }};
    }}
    // 시행령 제16조 제5항 취지: 추가 주력분야마다 기술인력 1명은 이미 확보한 것으로 간주
    const withoutException = base * count;
    const reducedCount = Math.max(0, count - 1);
    const required = Math.max(base, withoutException - reducedCount);
    return {{
      required,
      without_exception: withoutException,
      reduced_count: Math.max(0, withoutException - required),
      selected_count: count,
    }};
  }};
  const syncMajorFieldBox = () => {{
    const wrap = $('acq-major-field-wrap');
    const list = $('acq-major-field-list');
    const hint = $('acq-major-field-hint');
    if (!wrap || !list || !hint) return;
    const found = resolveProfile();
    const options = getMajorFieldOptionsByProfileName(found.name);
    if (options.length < 2) {{
      wrap.style.display = 'none';
      list.innerHTML = '';
      hint.textContent = '';
      return;
    }}
    wrap.style.display = '';
    const previous = getSelectedMajorFields(options);
    let selected = [];
    if (Array.isArray(pendingMajorFieldSelections) && pendingMajorFieldSelections.length) {{
      selected = pendingMajorFieldSelections.map((x) => compact(x)).filter((v) => options.indexOf(v) >= 0);
      pendingMajorFieldSelections = null;
    }}
    if (!selected.length) selected = previous;
    if (!selected.length) selected = [options[0]];
    list.innerHTML = options.map((name) => {{
      const checked = selected.indexOf(name) >= 0 ? ' checked' : '';
      return '<label><input type="checkbox" name="acq-major-field" value="' + escHtml(name) + '"' + checked + ' /> ' + escHtml(name) + '</label>';
    }}).join('');
    const active = getSelectedMajorFields(options);
    if (!active.length) {{
      const first = list.querySelector('input[name="acq-major-field"]');
      if (first) first.checked = true;
    }}
    const baseEngineers = Number(found.data && found.data.engineers) || 0;
    const rule = calcMajorFieldEngineerRule(baseEngineers, getSelectedMajorFields(options).length, true);
    hint.textContent =
      '주력분야 복수 선택 시 기술자 특례(시행령 제16조 제5항 취지)를 반영합니다. 현재 선택 '
      + String(rule.selected_count)
      + '개 기준 기술자 '
      + String(rule.required)
      + '명(특례 미적용 '
      + String(rule.without_exception)
      + '명 대비 '
      + String(rule.reduced_count)
      + '명 경감).';
    Array.from(list.querySelectorAll('input[name="acq-major-field"]')).forEach((el) => {{
      el.addEventListener('change', () => {{
        const checked = list.querySelectorAll('input[name="acq-major-field"]:checked');
        if (!checked.length) el.checked = true;
        syncPresetBox();
        applyPreset(!!(($('acq-auto-fill') || {{}}).checked), true);
        syncDerivedFees();
        persistDraft();
      }});
    }});
    if (isSimpleMode()) wrap.style.display = 'none';
  }};
  const resolveMajorFieldMeta = (found, profileData) => {{
    const options = getMajorFieldOptionsByProfileName(found && found.name ? found.name : '');
    const majorEnabled = options.length >= 2;
    const selected = majorEnabled ? getSelectedMajorFields(options) : [];
    const count = majorEnabled ? Math.max(1, selected.length) : 1;
    const baseEngineers = Math.max(0, Math.round(Number(profileData && profileData.engineers) || 0));
    const rule = calcMajorFieldEngineerRule(baseEngineers, count, majorEnabled);
    return {{
      enabled: majorEnabled,
      options,
      selected: selected.length ? selected : (majorEnabled ? [options[0]] : []),
      base_engineers: baseEngineers,
      selected_count: rule.selected_count,
      required_engineers: rule.required,
      without_exception_engineers: rule.without_exception,
      reduced_engineers: rule.reduced_count,
    }};
  }};

  const resolveProfile = () => {{
    const selected = compact(($('acq-license-type') || {{}}).value);
    const selectedHit = findProfileByText(selected);
    if (selectedHit) return {{ name: selectedHit.name, data: selectedHit.data, matched: true }};
    const custom = compact(($('acq-license-custom') || {{}}).value);
    const customHit = findProfileByText(custom);
    if (customHit) return {{ name: customHit.name, data: customHit.data, matched: true }};
    if (selected) return {{ name: selected, data: null, matched: false }};
    if (custom) return {{ name: custom, data: null, matched: false }};
    const fallback = profileEntries.length ? profileEntries[0].name : '';
    return {{ name: fallback, data: fallback ? profiles[fallback] : null, matched: !!fallback }};
  }};
  const getExtraSelectedLicenseNames = () =>
    Array.from(document.querySelectorAll('input[name="acq-license-extra"]:checked'))
      .map((el) => compact(el.value))
      .filter((v, idx, arr) => !!v && arr.indexOf(v) === idx && !!profiles[v]);
  const buildLicenseBundle = () => {{
    const found = resolveProfile();
    const addUnique = (arr, name) => {{
      const t = compact(name);
      if (!t || !profiles[t]) return;
      if (arr.indexOf(t) >= 0) return;
      arr.push(t);
    }};
    const selected = [];
    if (found.data && profiles[found.name]) addUnique(selected, found.name);
    getExtraSelectedLicenseNames().forEach((n) => addUnique(selected, n));
    const entries = selected.map((name) => ({{ name, data: profiles[name] }}));
    return {{
      found,
      selected_names: selected,
      selected_count: selected.length,
      entries,
    }};
  }};

  const normalizeClassCode = (klass) => {{
    const raw = compact(klass).toLowerCase();
    if (!raw) return 'special';
    if (raw === 'general' || raw.indexOf('종') >= 0) return 'general';
    return 'special';
  }};
  const resolveClassCodeFromBundle = (bundle, fallback = 'special') => {{
    const entries = (bundle && Array.isArray(bundle.entries)) ? bundle.entries : [];
    if (entries.some((x) => normalizeClassCode(x && x.data ? x.data.category : '') === 'general')) return 'general';
    if (entries.length) return 'special';
    return normalizeClassCode(fallback);
  }};
  const inferLicenseLawGroup = (licenseName) => {{
    const norm = normalizeProfileKey(licenseName);
    if (norm.indexOf('전기공사업') >= 0) return 'electric';
    if (norm.indexOf('정보통신') >= 0) return 'telecom';
    if (norm.indexOf('소방') >= 0) return 'fire';
    return 'construction';
  }};
  const calcDiagnosisLawMeta = (licenseNames) => {{
    const names = Array.isArray(licenseNames) ? licenseNames : [];
    const groups = [];
    const push = (v) => {{ if (groups.indexOf(v) < 0) groups.push(v); }};
    names.forEach((name) => push(inferLicenseLawGroup(name)));
    if (!groups.length) push('construction');
    return {{
      groups,
      count: Math.max(1, groups.length),
    }};
  }};
  const calcCapitalSpecialCreditMeta = (entries) => {{
    const rows = (Array.isArray(entries) ? entries : [])
      .map((x) => {{
        const cap = Number(x && x.data ? x.data.capital_eok : 0) || 0;
        const cls = normalizeClassCode(x && x.data ? x.data.category : '');
        return {{ cap, cls }};
      }})
      .filter((x) => x.cap > 0);
    if (rows.length < 2) {{
      return {{
        base_credit: 0,
        general_special_credit: 0,
        total_credit: 0,
        has_mixed_general_special: false,
      }};
    }}
    const caps = rows.map((x) => x.cap).sort((a, b) => b - a);
    const largest = Number(caps[0] || 0);
    const second = Number(caps[1] || 0);
    // 시행령 제16조 제1항 취지(동시신청 준용): 1개 업종 한정, 1/2 한도 특례
    const baseCredit = Math.max(0, Math.min(largest * 0.5, second * 0.5));
    const hasGeneral = rows.some((x) => x.cls === 'general');
    const hasSpecial = rows.some((x) => x.cls === 'special');
    let gsCredit = 0;
    if (hasGeneral && hasSpecial) {{
      const maxGeneral = rows.filter((x) => x.cls === 'general').reduce((m, x) => Math.max(m, x.cap), 0);
      const maxSpecial = rows.filter((x) => x.cls === 'special').reduce((m, x) => Math.max(m, x.cap), 0);
      // 종합+전문 동시 등록 특례를 보수적으로 반영
      gsCredit = Math.max(0, Math.min(maxSpecial * 0.3, maxGeneral * 0.2));
    }}
    const sumCap = rows.reduce((a, x) => a + x.cap, 0);
    const floorCap = rows.reduce((m, x) => Math.max(m, x.cap), 0);
    const maxCredit = Math.max(0, sumCap - floorCap);
    const totalCredit = Math.min(maxCredit, baseCredit + gsCredit);
    return {{
      base_credit: Number(baseCredit || 0),
      general_special_credit: Number(gsCredit || 0),
      total_credit: Number(totalCredit || 0),
      has_mixed_general_special: !!(hasGeneral && hasSpecial),
    }};
  }};
  const inferTechFamilies = (licenseName) => {{
    const norm = normalizeProfileKey(licenseName);
    const out = [];
    const push = (k) => {{ if (out.indexOf(k) < 0) out.push(k); }};
    if (norm.indexOf('토목') >= 0 || norm.indexOf('토공') >= 0 || norm.indexOf('지반') >= 0 || norm.indexOf('포장') >= 0 || norm.indexOf('상하수도') >= 0 || norm.indexOf('준설') >= 0) push('civil');
    if (norm.indexOf('건축') >= 0 || norm.indexOf('실내') >= 0 || norm.indexOf('금속창호') >= 0 || norm.indexOf('지붕') >= 0 || norm.indexOf('조적') >= 0 || norm.indexOf('석공') >= 0 || norm.indexOf('습식') >= 0 || norm.indexOf('방수') >= 0 || norm.indexOf('도장') >= 0) push('building');
    if (norm.indexOf('조경') >= 0) push('landscape');
    if (norm.indexOf('기계') >= 0 || norm.indexOf('가스') >= 0 || norm.indexOf('승강기') >= 0 || norm.indexOf('삭도') >= 0) push('mechanical');
    if (norm.indexOf('전기') >= 0 || norm.indexOf('정보통신') >= 0 || norm.indexOf('소방') >= 0) push('electrical');
    if (norm.indexOf('철강') >= 0 || norm.indexOf('철근콘크리트') >= 0) push('structure');
    if (norm.indexOf('철도') >= 0 || norm.indexOf('궤도') >= 0) push('rail');
    if (!out.length) push('etc');
    return out;
  }};
  const calcInterLicenseTechCredit = (licenseNames, engineerNeeds, entries = []) => {{
    const names = Array.isArray(licenseNames) ? licenseNames : [];
    const needs = Array.isArray(engineerNeeds) ? engineerNeeds : [];
    const rows = Array.isArray(entries) ? entries : [];
    if (names.length < 2 || needs.length < 2) return {{ credit: 0, pair: '', base_credit: 0, general_special_credit: 0 }};
    let best = 0;
    let bestPair = '';
    for (let i = 0; i < names.length; i += 1) {{
      const famA = inferTechFamilies(names[i]);
      for (let j = i + 1; j < names.length; j += 1) {{
        const famB = inferTechFamilies(names[j]);
        const overlap = famA.some((k) => famB.indexOf(k) >= 0);
        if (!overlap) continue;
        const baseA = Math.max(0, Math.round(Number(needs[i]) || 0));
        const baseB = Math.max(0, Math.round(Number(needs[j]) || 0));
        const cand = Math.min(baseA, baseB) >= 5 ? 2 : 1;
        if (cand > best) {{
          best = cand;
          bestPair = names[i] + ' ↔ ' + names[j];
        }}
      }}
    }}
    const hasGeneral = rows.some((x) => normalizeClassCode(x && x.data ? x.data.category : '') === 'general');
    const hasSpecial = rows.some((x) => normalizeClassCode(x && x.data ? x.data.category : '') === 'special');
    let gsCredit = 0;
    if (hasGeneral && hasSpecial) {{
      gsCredit = 1;
      if (!bestPair) {{
        const gName = (rows.find((x) => normalizeClassCode(x && x.data ? x.data.category : '') === 'general') || {{}}).name || '종합';
        const sName = (rows.find((x) => normalizeClassCode(x && x.data ? x.data.category : '') === 'special') || {{}}).name || '전문';
        bestPair = String(gName) + ' ↔ ' + String(sName);
      }}
    }}
    const total = Math.max(best, gsCredit);
    // 시행령 제16조 제2항 취지: 1개 업종 한정 기술능력 인정
    return {{
      credit: Math.max(0, total),
      pair: bestPair,
      base_credit: Math.max(0, best),
      general_special_credit: Math.max(0, gsCredit),
    }};
  }};
  const syncExtraLicenseBox = () => {{
    const wrap = $('acq-license-extra-wrap');
    const list = $('acq-license-extra-list');
    const hint = $('acq-license-extra-hint');
    if (!wrap || !list || !hint) return;
    const found = resolveProfile();
    const selectedName = compact(found.name);
    const items = Object.keys(profiles || {{}})
      .filter((name) => name !== selectedName)
      .sort((a, b) => String(a).localeCompare(String(b), 'ko-KR'));
    if (!items.length) {{
      wrap.style.display = 'none';
      list.innerHTML = '';
      hint.textContent = '';
      return;
    }}
    wrap.style.display = '';
    let selected = [];
    if (Array.isArray(pendingExtraLicenseSelections) && pendingExtraLicenseSelections.length) {{
      selected = pendingExtraLicenseSelections
        .map((x) => compact(x))
        .filter((v) => items.indexOf(v) >= 0);
      pendingExtraLicenseSelections = null;
    }} else {{
      selected = getExtraSelectedLicenseNames()
        .filter((v) => items.indexOf(v) >= 0);
    }}
    list.innerHTML = items.map((name) => {{
      const checked = selected.indexOf(name) >= 0 ? ' checked' : '';
      return '<label><input type="checkbox" name="acq-license-extra" value="' + escHtml(name) + '"' + checked + ' /> ' + escHtml(name) + '</label>';
    }}).join('');
    const selectedCount = getExtraSelectedLicenseNames().length;
    hint.textContent = selectedCount > 0
      ? ('추가 업종 ' + String(selectedCount) + '개 선택: 업종 간 자본금/기술자 특례(시행령 제16조 제1·2항 취지)를 자동 반영합니다.')
      : '기본은 단일 업종 계산입니다. 복수 등록 시 추가 업종을 체크해 주세요.';
    Array.from(list.querySelectorAll('input[name="acq-license-extra"]')).forEach((el) => {{
      el.addEventListener('change', () => {{
        syncPresetBox();
        applyPreset(!!(($('acq-auto-fill') || {{}}).checked), true);
        syncDerivedFees();
        persistDraft();
      }});
    }});
  }};
  const classLabelByCode = (code) => (code === 'general' ? '종합' : '전문');
  const adminFeeByClass = (classCode) => (classCode === 'general' ? 500 : 300);
  const inferRegionStatus = (rawText) => {{
    const src = compact(rawText);
    const normalized = normalizeProfileKey(src);
    if (!normalized) {{
      return {{
        code: 'normal',
        certainty: 'unknown',
        label: '주소 미입력 · 일반지역 기준으로 임시 계산',
        reason: '법인 주소를 입력하면 중과세 여부를 자동 판정합니다.',
      }};
    }}
    const has = (keyword) => normalized.indexOf(normalizeProfileKey(keyword)) >= 0;
    const hasAny = (arr) => arr.some((k) => has(k));
    const sureNormalByProvince = [
      '부산', '대구', '광주광역시', '광주 북구', '광주 서구', '광주 동구', '광주 남구',
      '대전', '울산', '세종', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주',
    ];
    if (hasAny(sureNormalByProvince)) {{
      return {{
        code: 'normal',
        certainty: 'high',
        label: '일반지역(중과세 아님) 자동 판정',
        reason: '비수도권 주소로 판정되었습니다.',
      }};
    }}

    if (hasAny(['서울', '서울시', '서울특별시', '과밀억제권역', '중과세지역'])) {{
      return {{
        code: 'surcharge',
        certainty: 'high',
        label: '중과지역 자동 판정',
        reason: '서울/과밀억제권역 키워드가 확인되어 중과세가 반영됩니다.',
      }};
    }}

    if (hasAny(['비과밀', '비중과', '중과제외', '중과 제외', '자연보전권역', '성장관리권역'])) {{
      return {{
        code: 'normal',
        certainty: 'medium',
        label: '일반지역(중과세 아님) 자동 판정(예상)',
        reason: '비중과/제외 키워드가 확인되어 일반지역으로 계산했습니다.',
      }};
    }}

    if (has('시흥')) {{
      const specialNormalHints = ['반월', '정왕산단', '정왕공단'];
      if (hasAny(specialNormalHints)) {{
        return {{
          code: 'normal',
          certainty: 'medium',
          label: '일반지역(중과세 아님) 자동 판정',
          reason: '시흥 반월특수지역/산단 키워드가 확인되었습니다.',
        }};
      }}
      return {{
        code: 'surcharge',
        certainty: 'medium',
        label: '중과지역 자동 판정(예상)',
        reason: '시흥은 반월특수지역을 제외하면 중과 가능성이 높습니다.',
      }};
    }}

    if (has('남양주')) {{
      const surchargeDongs = ['호평', '평내', '금곡', '일패', '이패', '삼패', '가운', '수석', '지금', '도농'];
      const likelyNormalDongs = ['별내', '진접', '오남', '화도', '수동', '조안', '와부'];
      if (hasAny(surchargeDongs)) {{
        return {{
          code: 'surcharge',
          certainty: 'medium',
          label: '중과지역 자동 판정(예상)',
          reason: '남양주 중과 대상 동 키워드가 확인되었습니다.',
        }};
      }}
      if (hasAny(likelyNormalDongs)) {{
        return {{
          code: 'normal',
          certainty: 'medium',
          label: '일반지역 자동 판정(예상)',
          reason: '남양주 비중과 가능 지역 키워드가 확인되었습니다.',
        }};
      }}
      return {{
        code: 'normal',
        certainty: 'unknown',
        label: '확인 필요(남양주 일부만 중과) · 일반지역 임시 계산',
        reason: '남양주는 동/리별 판정 차이가 있으므로 상세 주소 확인이 필요합니다.',
      }};
    }}

    if (has('인천')) {{
      const normalHints = [
        '강화', '강화군', '옹진', '옹진군', '영종', '운서', '용유', '청라', '송도', '경제자유구역',
        'ifez', '검단', '남동국가산업단지', '남동산단',
      ];
      const surchargeHints = ['미추홀', '부평', '계양', '동구', '연수', '남동구'];
      if (hasAny(normalHints)) {{
        return {{
          code: 'normal',
          certainty: 'unknown',
          label: '확인 필요(인천 일부 제외지역) · 일반지역 임시 계산',
          reason: '인천 예외지역 키워드가 확인되어 일반지역 기준으로 임시 계산했습니다.',
        }};
      }}
      if (hasAny(surchargeHints)) {{
        return {{
          code: 'surcharge',
          certainty: 'medium',
          label: '중과지역 자동 판정(예상)',
          reason: '인천 도심권 키워드가 확인되어 중과 가능성이 높습니다.',
        }};
      }}
      return {{
        code: 'surcharge',
        certainty: 'unknown',
        label: '확인 필요(인천 지역별 차이) · 중과지역 임시 계산',
        reason: '인천은 구/동별 차이가 있어 자동판정 후 수동수정 옵션으로 최종 확인을 권장합니다.',
      }};
    }}

    const sureSurchargeCities = [
      '의정부', '구리', '하남', '고양', '수원', '성남', '안양', '부천', '광명', '과천', '의왕', '군포', '용인',
    ];
    if (hasAny(sureSurchargeCities)) {{
      return {{
        code: 'surcharge',
        certainty: 'high',
        label: '중과지역 자동 판정',
        reason: '수도권 과밀억제권역 도시 키워드가 확인되었습니다.',
      }};
    }}

    const likelyNormalMetroEdge = ['파주', '이천', '여주', '김포', '평택', '안성', '오산', '화성', '양주', '포천', '동두천', '가평', '양평', '연천', '안산'];
    if (hasAny(likelyNormalMetroEdge)) {{
      return {{
        code: 'normal',
        certainty: 'medium',
        label: '일반지역 자동 판정(예상)',
        reason: '수도권 외곽/비중과 가능 도시로 분류되어 일반지역 기준으로 계산했습니다.',
      }};
    }}

    if (hasAny(['경기', '경기도'])) {{
      return {{
        code: 'normal',
        certainty: 'unknown',
        label: '확인 필요(경기 일부만 중과) · 일반지역 임시 계산',
        reason: '경기도는 시/구/동별 중과 여부가 달라 상세 주소 기준 확인이 필요합니다.',
      }};
    }}

    return {{
      code: 'normal',
      certainty: 'unknown',
      label: '확인 필요 · 일반지역 임시 계산',
      reason: '주소 형식이 불명확합니다. 예: 서울 강남구 역삼동',
    }};
  }};
  const syncRegionInference = () => {{
    const text = $('acq-region-text');
    const override = $('acq-region-override');
    const hidden = $('acq-region');
    const out = $('acq-region-result');
    const help = $('acq-region-help');
    if (!text || !override || !hidden || !out || !help) return;
    const auto = inferRegionStatus(text.value);
    const overrideVal = compact(override.value) || 'auto';
    let finalCode = auto.code;
    let finalLabel = auto.label;
    if (overrideVal === 'normal') {{
      finalCode = 'normal';
      finalLabel = '수동 설정: 일반지역(중과세 아님)';
    }} else if (overrideVal === 'surcharge') {{
      finalCode = 'surcharge';
      finalLabel = '수동 설정: 중과지역';
    }} else if (auto.certainty === 'unknown') {{
      finalCode = 'normal';
    }}
    hidden.value = finalCode;
    out.value = finalLabel;
    help.textContent = auto.reason + (overrideVal === 'auto' ? '' : ' (수동 설정이 우선 적용됩니다.)');
  }};
  const calcDiagnosisFeeManwon = (assetWon, isEstablish) => {{
    // 시장 관행: 신설법인 약 50만원, 기존법인 약 70만원을 기준으로 자산규모에 따라 가감
    const assetEok = Math.max(0, Number(assetWon) || 0) / 100000000;
    const base = isEstablish ? 50 : 70;
    let adj = 0;
    if (assetEok > 5) adj = 10;
    if (assetEok > 10) adj = 20;
    if (assetEok > 30) adj = 30;
    if (assetEok > 60) adj = 40;
    return base + adj;
  }};
  const calcDetailedCostsManwon = (klass, region, corpState, capitalEok, guaranteeEok, engineerCount, selectedLicenseNames = []) => {{
    const classCode = normalizeClassCode(klass);
    const classType = classLabelByCode(classCode);
    const stateCode = compact(corpState) === 'existing' ? 'existing' : 'new';
    const regType = stateCode === 'existing' ? 'amend' : 'establish';
    const isEstablish = regType === 'establish';
    const capitalWon = Math.max(0, Number(capitalEok) || 0) * 100000000;
    const guaranteeWon = Math.max(0, Number(guaranteeEok) || 0) * 100000000;
    const isSurcharge = compact(region) === 'surcharge';
    // 실제 과밀억제권역 중과를 반영: 설립 등기는 기본세율의 3배, 변경 등기는 2배로 계산
    const taxSurchargeMultiplier = isSurcharge ? (isEstablish ? 3.0 : 2.0) : 1.0;

    const receptionFeeManwon = classCode === 'general' ? (isEstablish ? 7 : 6) : (isEstablish ? 5 : 4);
    const registrationTaxRate = isEstablish ? 0.004 : 0.002;
    const registrationTaxBaseManwon = (capitalWon * registrationTaxRate) / 10000;
    const registrationTaxManwon = registrationTaxBaseManwon * taxSurchargeMultiplier;
    const localTaxManwon = registrationTaxManwon * 0.2;
    const localTaxBaseManwon = registrationTaxBaseManwon * 0.2;
    const bondPurchaseManwon = (capitalWon * (classCode === 'general' ? 0.0012 : 0.0010)) / 10000;
    const bondInstantSaleLossManwon = bondPurchaseManwon * (isEstablish ? 0.07 : 0.05);
    const diagnosisBaseManwon = calcDiagnosisFeeManwon(capitalWon + guaranteeWon, isEstablish);
    const diagnosisLaw = calcDiagnosisLawMeta(selectedLicenseNames);
    const diagnosisFeeManwon = diagnosisBaseManwon * Number(diagnosisLaw.count || 1);
    const capitalEokSafe = Math.max(0, Number(capitalEok) || 0);
    const legalServiceBase = isEstablish ? 55 : 40;
    const legalServiceSlope = isEstablish ? 5.2 : 3.4;
    const legalServiceManwon = clamp(
      legalServiceBase + (capitalEokSafe * legalServiceSlope) + (isSurcharge ? (isEstablish ? 10 : 7) : 0),
      isEstablish ? 60 : 45,
      isEstablish ? 180 : 140,
    );
    const adminBaseManwon = adminFeeByClass(classCode);
    const extraLicenseCount = Math.max(0, (Array.isArray(selectedLicenseNames) ? selectedLicenseNames.length : 0) - 1);
    const adminExtraManwon = adminBaseManwon * 0.5 * extraLicenseCount;
    const adminFeeManwon = adminBaseManwon + adminExtraManwon;
    const capitalFundManwon = capitalWon / 10000;
    const guaranteeDepositManwon = guaranteeWon / 10000;
    const capitalRemainAfterGuaranteeManwon = Math.max(0, capitalFundManwon - guaranteeDepositManwon);
    const feesTaxesManwon =
      receptionFeeManwon +
      registrationTaxManwon +
      localTaxManwon +
      bondInstantSaleLossManwon;
    const professionalFeesManwon =
      legalServiceManwon +
      adminFeeManwon +
      diagnosisFeeManwon;
    const taxSurchargeDeltaManwon = Math.max(
      0,
      (registrationTaxManwon + localTaxManwon) - (registrationTaxBaseManwon + localTaxBaseManwon),
    );

    const legalTotalManwon =
      registrationTaxManwon +
      localTaxManwon +
      bondInstantSaleLossManwon +
      diagnosisFeeManwon +
      legalServiceManwon;

    const centerBaseCostManwon =
      feesTaxesManwon +
      professionalFeesManwon;
    const centerTotalRequiredManwon =
      centerBaseCostManwon +
      capitalFundManwon;

    return {{
      class_type: classType,
      class_code: classCode,
      corp_state: stateCode,
      corp_reg_type: regType,
      is_surcharge: isSurcharge,
      reception_fee_manwon: Math.round(receptionFeeManwon * 10) / 10,
      registration_tax_manwon: Math.round(registrationTaxManwon * 10) / 10,
      registration_tax_base_manwon: Math.round(registrationTaxBaseManwon * 10) / 10,
      local_tax_manwon: Math.round(localTaxManwon * 10) / 10,
      local_tax_base_manwon: Math.round(localTaxBaseManwon * 10) / 10,
      tax_surcharge_delta_manwon: Math.round(taxSurchargeDeltaManwon * 10) / 10,
      bond_purchase_manwon: Math.round(bondPurchaseManwon * 10) / 10,
      bond_instant_sale_loss_manwon: Math.round(bondInstantSaleLossManwon * 10) / 10,
      diagnosis_fee_base_manwon: Math.round(diagnosisBaseManwon * 10) / 10,
      diagnosis_fee_multiplier: Number(diagnosisLaw.count || 1),
      diagnosis_law_groups: (diagnosisLaw.groups || []).slice(),
      diagnosis_fee_manwon: Math.round(diagnosisFeeManwon * 10) / 10,
      legal_service_manwon: Math.round(legalServiceManwon * 10) / 10,
      legal_total_manwon: Math.round(legalTotalManwon * 10) / 10,
      admin_fee_base_manwon: Math.round(adminBaseManwon * 10) / 10,
      admin_fee_extra_manwon: Math.round(adminExtraManwon * 10) / 10,
      admin_fee_extra_license_count: Number(extraLicenseCount || 0),
      admin_fee_manwon: Math.round(adminFeeManwon * 10) / 10,
      capital_fund_manwon: Math.round(capitalFundManwon * 10) / 10,
      guarantee_deposit_manwon: Math.round(guaranteeDepositManwon * 10) / 10,
      capital_remain_after_guarantee_manwon: Math.round(capitalRemainAfterGuaranteeManwon * 10) / 10,
      fees_taxes_manwon: Math.round(feesTaxesManwon * 10) / 10,
      professional_fees_manwon: Math.round(professionalFeesManwon * 10) / 10,
      center_base_cost_manwon: Math.round(centerBaseCostManwon * 10) / 10,
      center_total_required_manwon: Math.round(centerTotalRequiredManwon * 10) / 10,
    }};
  }};

  const syncPresetBox = () => {{
    const box = $('acq-preset-box'); if (!box) return;
    const bundle = buildLicenseBundle();
    const found = bundle.found;
    const p = found.data || {{}};
    if (!found.data && !bundle.entries.length) {{
      const label = compact(found && found.name) || '직접 입력 업종';
      box.textContent = label + ' 기준값을 찾지 못했습니다. 업종 선택 목록에서 선택하거나 자본금/출자좌수/출자예치금/기술자 수를 직접 입력해 주세요.';
      return;
    }}
    const major = resolveMajorFieldMeta(found, p);
    const primaryEntry = (bundle.entries.find((x) => x.name === found.name) || bundle.entries[0] || null);
    const primaryData = primaryEntry && primaryEntry.data ? primaryEntry.data : p;
    const classCode = resolveClassCodeFromBundle(bundle, (primaryData && primaryData.category) || 'special');
    const caps = bundle.entries.map((x) => Number(x.data && x.data.capital_eok) || 0).filter((v) => v > 0);
    const sumCap = caps.reduce((a, b) => a + b, 0);
    const capMeta = calcCapitalSpecialCreditMeta(bundle.entries);
    const capCredit = Number(capMeta.total_credit || 0);
    const requiredCapital = bundle.entries.length ? Math.max((caps.length ? Math.max.apply(null, caps) : 0), sumCap - capCredit) : (Number(primaryData.capital_eok) || 0);
    const totalGuarantee = bundle.entries.length ? bundle.entries.reduce((a, x) => a + (Number(x.data && x.data.guarantee_deposit_eok) || 0), 0) : (Number(primaryData.guarantee_deposit_eok) || 0);
    const totalJwasu = bundle.entries.length ? bundle.entries.reduce((a, x) => a + (Number(x.data && x.data.guarantee_jwasu) || 0), 0) : (Number(primaryData.guarantee_jwasu) || 0);
    const engineNeeds = bundle.entries.length
      ? bundle.entries.map((x) => {{
        if (x.name === found.name && major.enabled) return Number(major.required_engineers || 0);
        return Number(x.data && x.data.engineers) || 0;
      }})
      : [Number(major.enabled ? major.required_engineers : (primaryData.engineers || 0)) || 0];
    const engineWithoutInter = engineNeeds.reduce((a, b) => a + (Number(b) || 0), 0);
    const interTech = calcInterLicenseTechCredit(bundle.selected_names, engineNeeds, bundle.entries);
    const requiredEngineers = Math.max(engineNeeds.length ? Math.max.apply(null, engineNeeds) : 0, engineWithoutInter - Number(interTech.credit || 0));
    let majorText = '';
    if (major.enabled) {{
      majorText =
        ' / 주력분야 <strong>' + escHtml(major.selected.join(', ')) + '</strong>'
        + ' / 특례 반영 기술자 <strong>' + Number(major.required_engineers || 0).toLocaleString('ko-KR') + '명</strong>'
        + ' <span style="color:#4b6480">(미적용 ' + Number(major.without_exception_engineers || 0).toLocaleString('ko-KR') + '명 대비 -' + Number(major.reduced_engineers || 0).toLocaleString('ko-KR') + '명)</span>';
    }}
    const licenseLabel = bundle.selected_names.length ? bundle.selected_names.join(', ') : (found.name || '');
    const capText = bundle.selected_names.length > 1
      ? (fmtEok(sumCap) + ' - 특례 ' + fmtEok(capCredit) + ' = ' + fmtEok(requiredCapital))
      : fmtEok(requiredCapital);
    const interText = (bundle.selected_names.length > 1 && Number(interTech.credit || 0) > 0)
      ? (' / 업종 간 기술자 특례 <strong>-' + Number(interTech.credit || 0).toLocaleString('ko-KR') + '명</strong> (' + escHtml(String(interTech.pair || '유사직종')) + ')')
      : '';
    const classMixText = (bundle.selected_names.length > 1 && capMeta.has_mixed_general_special && Number(capMeta.general_special_credit || 0) > 0)
      ? (' / 종합·전문간 자본금 특례 <strong>-' + fmtEok(capMeta.general_special_credit) + '</strong>')
      : '';
    box.innerHTML =
      '<strong>' + escHtml(licenseLabel) + '</strong> 기준'
      + ' · 자동분류 <strong>' + (classCode === 'general' ? '종합건설업' : '전문건설업') + '</strong>'
      + ' / 자본금 기준 <strong>' + capText + '</strong>'
      + ' (출자예치금 합계 <strong>' + fmtEok(totalGuarantee) + '</strong>, 출자좌수 합계 <strong>' + Number(totalJwasu || 0).toLocaleString('ko-KR') + '좌</strong>)'
      + ' / 기술자 기준 <strong>' + Number(requiredEngineers || 0).toLocaleString('ko-KR') + '명</strong>'
      + classMixText
      + interText
      + majorText;
  }};

  const ensureCorporateRegField = () => {{
    // Legacy hook kept for backward compatibility.
    const centerLabel = document.querySelector('#acq-out-center') ? document.querySelector('#acq-out-center').closest('.result-card') : null;
    const centerK = centerLabel ? centerLabel.querySelector('.k') : null;
    if (centerK) centerK.textContent = '예상 기준 필요자금';
  }};

  const syncDerivedFees = () => {{
    const bundle = buildLicenseBundle();
    const found = bundle.found; const p = found.data || {{}};
    const major = resolveMajorFieldMeta(found, p);
    const primary = (bundle.entries.find((x) => x.name === found.name) || bundle.entries[0] || {{ data: p }});
    const klass = resolveClassCodeFromBundle(bundle, compact(primary.data && primary.data.category || p.category || 'special'));
    syncRegionInference();
    const capital = num('acq-capital'); const region = compact(($('acq-region') || {{}}).value) || 'normal';
    const corpState = compact(($('acq-corp-state') || {{}}).value) || 'new';
    const caps = bundle.entries.map((x) => Number(x.data && x.data.capital_eok) || 0).filter((v) => v > 0);
    const sumCap = caps.reduce((a, b) => a + b, 0);
    const capMeta = calcCapitalSpecialCreditMeta(bundle.entries);
    const capCredit = Number(capMeta.total_credit || 0);
    const autoCapital = bundle.entries.length ? Math.max((caps.length ? Math.max.apply(null, caps) : 0), sumCap - capCredit) : Number(p.capital_eok || 0);
    const autoGuarantee = bundle.entries.length ? bundle.entries.reduce((a, x) => a + (Number(x.data && x.data.guarantee_deposit_eok) || 0), 0) : Number(p.guarantee_deposit_eok || 0);
    const perNeeds = bundle.entries.length
      ? bundle.entries.map((x) => (x.name === found.name && major.enabled) ? Number(major.required_engineers || 0) : (Number(x.data && x.data.engineers) || 0))
      : [Number(major.enabled ? major.required_engineers : Number(p.engineers || 0)) || 0];
    const inter = calcInterLicenseTechCredit(bundle.selected_names, perNeeds, bundle.entries);
    const autoEngineers = Math.max(perNeeds.length ? Math.max.apply(null, perNeeds) : 0, perNeeds.reduce((a, b) => a + (Number(b) || 0), 0) - Number(inter.credit || 0));
    const resolvedCapital = Number.isFinite(capital) ? capital : autoCapital;
    const resolvedGuarantee = num('acq-guarantee');
    const resolvedEngineers = num('acq-engineer-count');
    const detail = calcDetailedCostsManwon(
      klass,
      region,
      corpState,
      resolvedCapital,
      Number.isFinite(resolvedGuarantee) ? resolvedGuarantee : autoGuarantee,
      Number.isFinite(resolvedEngineers) ? resolvedEngineers : autoEngineers,
      bundle.selected_names,
    );
    $('acq-admin-fee').value = String(detail.admin_fee_manwon);
    $('acq-legal-fee').value = String(detail.legal_total_manwon);
  }};

  const applyPreset = (force = false, forceEngineer = false) => {{
    const auto = $('acq-auto-fill'); if (!auto || (!auto.checked && !force)) return;
    const bundle = buildLicenseBundle();
    const found = bundle.found; const p = found.data;
    if (!p && !bundle.entries.length) return;
    const major = resolveMajorFieldMeta(found, p || {{}});
    const caps = bundle.entries.map((x) => Number(x.data && x.data.capital_eok) || 0).filter((v) => v > 0);
    const sumCap = caps.reduce((a, b) => a + b, 0);
    const capMeta = calcCapitalSpecialCreditMeta(bundle.entries);
    const capCredit = Number(capMeta.total_credit || 0);
    const presetCapital = bundle.entries.length ? Math.max((caps.length ? Math.max.apply(null, caps) : 0), sumCap - capCredit) : Number((p || {{}}).capital_eok || 0);
    const presetJwasu = bundle.entries.length ? bundle.entries.reduce((a, x) => a + (Number(x.data && x.data.guarantee_jwasu) || 0), 0) : Number((p || {{}}).guarantee_jwasu || 0);
    const presetGuarantee = bundle.entries.length ? bundle.entries.reduce((a, x) => a + (Number(x.data && x.data.guarantee_deposit_eok) || 0), 0) : Number((p || {{}}).guarantee_deposit_eok || 0);
    const perNeeds = bundle.entries.length
      ? bundle.entries.map((x) => (x.name === found.name && major.enabled) ? Number(major.required_engineers || 0) : (Number(x.data && x.data.engineers) || 0))
      : [Number(major.enabled ? major.required_engineers : Number((p || {{}}).engineers || 0)) || 0];
    const inter = calcInterLicenseTechCredit(bundle.selected_names, perNeeds, bundle.entries);
    const presetEngineers = Math.max(perNeeds.length ? Math.max.apply(null, perNeeds) : 0, perNeeds.reduce((a, b) => a + (Number(b) || 0), 0) - Number(inter.credit || 0));
    if (force || !compact($('acq-capital').value)) $('acq-capital').value = String(presetCapital || '');
    if (force || !compact($('acq-guarantee-jwasu').value)) $('acq-guarantee-jwasu').value = String(presetJwasu || '');
    if (force || !compact($('acq-guarantee').value)) $('acq-guarantee').value = String(presetGuarantee || '');
    if (force || forceEngineer || !compact($('acq-engineer-count').value)) {{
      const targetEngineers = presetEngineers;
      $('acq-engineer-count').value = String(targetEngineers || '');
    }}
    syncDerivedFees();
  }};

  const calc = () => {{
    const bundle = buildLicenseBundle();
    const found = bundle.found; const p = found.data || {{}};
    const major = resolveMajorFieldMeta(found, p);
    const primary = (bundle.entries.find((x) => x.name === found.name) || bundle.entries[0] || {{ data: p }});
    const klass = resolveClassCodeFromBundle(bundle, compact(primary.data && primary.data.category || p.category || 'special'));
    syncRegionInference();
    const region = compact(($('acq-region') || {{}}).value) || 'normal';
    const corpState = compact(($('acq-corp-state') || {{}}).value) || 'new';
    const capital = num('acq-capital'); const jwasu = num('acq-guarantee-jwasu'); const guarantee = num('acq-guarantee');
    const engineers = num('acq-engineer-count');
    const caps = bundle.entries.map((x) => Number(x.data && x.data.capital_eok) || 0).filter((v) => v > 0);
    const sumCap = caps.reduce((a, b) => a + b, 0);
    const capMeta = calcCapitalSpecialCreditMeta(bundle.entries);
    const capCredit = Number(capMeta.total_credit || 0);
    const autoCapitalByRule = bundle.entries.length
      ? Math.max((caps.length ? Math.max.apply(null, caps) : 0), sumCap - capCredit)
      : Number(p.capital_eok || 0);
    const autoJwasu = bundle.entries.length
      ? bundle.entries.reduce((a, x) => a + (Number(x.data && x.data.guarantee_jwasu) || 0), 0)
      : Number(p.guarantee_jwasu || 0);
    const autoGuarantee = bundle.entries.length
      ? bundle.entries.reduce((a, x) => a + (Number(x.data && x.data.guarantee_deposit_eok) || 0), 0)
      : Number(p.guarantee_deposit_eok || 0);
    const perEngineers = bundle.entries.length
      ? bundle.entries.map((x) => (x.name === found.name && major.enabled) ? Number(major.required_engineers || 0) : (Number(x.data && x.data.engineers) || 0))
      : [Number(major.enabled ? major.required_engineers : Number(p.engineers || 0)) || 0];
    const engineerWithoutInterSpecial = perEngineers.reduce((a, b) => a + (Number(b) || 0), 0);
    const interTech = calcInterLicenseTechCredit(bundle.selected_names, perEngineers, bundle.entries);
    const autoEngineersByRule = Math.max(perEngineers.length ? Math.max.apply(null, perEngineers) : 0, engineerWithoutInterSpecial - Number(interTech.credit || 0));
    const resolvedCapital = Number.isFinite(capital) ? capital : autoCapitalByRule;
    const resolvedJwasu = Number.isFinite(jwasu) ? jwasu : autoJwasu;
    const resolvedGuarantee = Number.isFinite(guarantee) ? guarantee : autoGuarantee;
    const resolvedEngineers = Number.isFinite(engineers) ? engineers : autoEngineersByRule;
    const detail = calcDetailedCostsManwon(klass, region, corpState, resolvedCapital, resolvedGuarantee, resolvedEngineers, bundle.selected_names);

    let center = eokFromManwon(detail.center_total_required_manwon);
    const directCostEok = eokFromManwon(detail.center_base_cost_manwon);
    const okCapital = !!(($('acq-ok-capital') || {{}}).checked); const okEngineer = !!(($('acq-ok-engineer') || {{}}).checked); const okOffice = !!(($('acq-ok-office') || {{}}).checked);
    let adjust = 0; if (!okCapital) adjust += 0.04; if (!okEngineer) adjust += 0.06; if (!okOffice) adjust += 0.03; center *= (1 + adjust);
    const engineerGap = Math.max(0, Number(autoEngineersByRule || 0) - Number(resolvedEngineers || 0));
    if (engineerGap > 0) center *= (1 + clamp(engineerGap * 0.012, 0.0, 0.06));

    const required = [compact(($('acq-license-type') || {{}}).value) || compact(($('acq-license-custom') || {{}}).value), resolvedCapital > 0 ? 'y' : '', resolvedGuarantee > 0 ? 'y' : '', resolvedEngineers > 0 ? 'y' : '', compact(($('acq-region') || {{}}).value), corpState, compact(($('acq-region-text') || {{}}).value), (major.enabled ? (major.selected_count > 0 ? 'y' : '') : 'y')];
    const filled = required.filter((x) => !!x).length; const missing = required.length - filled; const unchecked = [okCapital, okEngineer, okOffice].filter((x) => !x).length;
    const band = clamp(0.10 + (missing * 0.02) + (unchecked * 0.03) + (engineerGap > 0 ? 0.02 : 0), 0.08, 0.24);
    const low = Math.max(0.1, center * (1 - band * 0.72)); const high = Math.max(low, center * (1 + band));
    const ready = center + 0.05;
    const confidence = Math.round(clamp(88 - (missing * 8) - (unchecked * 6) - (Math.abs(adjust) * 120) - (engineerGap * 3), 32, 97));

    const noteLines = [
      '총 필요자금은 자본금(공제조합 출자예치금 포함) + 필수 세금·수수료를 합산해 산정했습니다.',
      '법인 주소를 입력하면 중과세 여부를 자동 판정하고 등록면허세·지방세 중과분을 반영합니다.',
      '공제조합 출자예치금은 자본금 내부 배정 항목으로, 총 필요자금에 이중 합산되지 않습니다.',
      '아래 중간 정산표에서 접수수수료·등록면허세·채권 즉시매도 차액을 바로 확인하실 수 있습니다.',
      '권장 준비자금은 예비비 500만원을 추가한 금액입니다.',
    ];
    if (Number(detail.diagnosis_fee_multiplier || 1) > 1) {{
      noteLines.unshift(
        '기업진단기관 수수료는 법령군별(건설/전기/정보통신/소방)로 합산 적용했습니다. 현재 '
        + Number(detail.diagnosis_fee_multiplier || 1).toLocaleString('ko-KR')
        + '건 기준입니다.'
      );
    }} else {{
      noteLines.unshift('건설업 복수 업종은 기업진단기관 수수료를 1건 기준으로 적용했습니다.');
    }}
    if (bundle.selected_count > 1) {{
      noteLines.unshift(
        '행정사 수임료는 기본 업종 100% + 추가 면허당 50% 가산 규칙으로 계산했습니다(추가 '
        + Number(detail.admin_fee_extra_license_count || 0).toLocaleString('ko-KR')
        + '개).'
      );
    }}
    if (major.enabled) {{
      noteLines.unshift(
        '주력분야 ' + major.selected.join(', ') + ' 선택 기준으로 기술자 특례를 반영했습니다(시행령 제16조 제5항 취지: '
        + Number(major.without_exception_engineers || 0).toLocaleString('ko-KR') + '명 → '
        + Number(major.required_engineers || 0).toLocaleString('ko-KR') + '명).'
      );
    }}
    if (bundle.selected_count > 1) {{
      noteLines.unshift(
        '복수 업종 동시 등록 기준으로 자본금 특례를 반영했습니다(시행령 제16조 제1항 취지: 합산 '
        + fmtEok(sumCap)
        + ' - 특례 '
        + fmtEok(capCredit)
        + ' = '
        + fmtEok(autoCapitalByRule)
        + ').'
      );
      if (capMeta.has_mixed_general_special && Number(capMeta.general_special_credit || 0) > 0) {{
        noteLines.unshift(
          '종합·전문 업종 동시 등록 특례를 반영했습니다(자본금 추가 경감 '
          + fmtEok(capMeta.general_special_credit)
          + ').'
        );
      }}
      if (Number(interTech.credit || 0) > 0) {{
        noteLines.unshift(
          '업종 간 기술자 특례를 반영했습니다(시행령 제16조 제2항 취지: '
          + Number(engineerWithoutInterSpecial || 0).toLocaleString('ko-KR')
          + '명 → '
          + Number(autoEngineersByRule || 0).toLocaleString('ko-KR')
          + '명, '
          + (interTech.pair || '유사직종')
          + ').'
        );
        if (Number(interTech.general_special_credit || 0) > 0) {{
          noteLines.unshift('종합·전문간 기술자 특례를 추가 반영했습니다.');
        }}
      }} else {{
        noteLines.unshift('선택 업종 간 동일·유사 직종 기술자 중복 인정 요건이 불명확해 업종 간 기술자 특례는 보수적으로 미적용했습니다.');
      }}
    }}
    if (engineerGap > 0) {{
      noteLines.unshift(
        '입력 기술자 수가 기준 대비 '
        + Number(engineerGap).toLocaleString('ko-KR')
        + '명 부족해 신뢰도와 오차범위를 보수적으로 조정했습니다.'
      );
    }}

    return {{
      license: compact(($('acq-license-type') || {{}}).value) || compact(($('acq-license-custom') || {{}}).value) || found.name,
      selected_licenses: bundle.selected_names || (found.name ? [found.name] : []),
      selected_license_count: Number(bundle.selected_count || 0),
      class_code: klass,
      class_type: detail.class_type, corp_state: detail.corp_state, corp_reg_type: detail.corp_reg_type, region, region_input: compact(($('acq-region-text') || {{}}).value), region_result: compact(($('acq-region-result') || {{}}).value), capital_eok: resolvedCapital, guarantee_jwasu: resolvedJwasu, guarantee_eok: resolvedGuarantee, engineer_count: resolvedEngineers,
      capital_without_special_eok: Number(sumCap || 0),
      capital_special_credit_eok: Number(capCredit || 0),
      capital_special_base_credit_eok: Number(capMeta.base_credit || 0),
      capital_special_general_special_credit_eok: Number(capMeta.general_special_credit || 0),
      capital_required_by_rule_eok: Number(autoCapitalByRule || 0),
      guarantee_required_by_rule_eok: Number(autoGuarantee || 0),
      guarantee_jwasu_by_rule: Number(autoJwasu || 0),
      major_fields_selected: major.selected || [],
      major_field_count: Number(major.selected_count || 0),
      engineer_required_with_major_exception: Number(major.required_engineers || 0),
      engineer_without_major_exception: Number(major.without_exception_engineers || 0),
      engineer_exception_reduced: Number(major.reduced_engineers || 0),
      engineer_without_inter_special: Number(engineerWithoutInterSpecial || 0),
      engineer_inter_special_credit: Number(interTech.credit || 0),
      engineer_inter_special_base_credit: Number(interTech.base_credit || 0),
      engineer_inter_general_special_credit: Number(interTech.general_special_credit || 0),
      engineer_inter_special_pair: String(interTech.pair || ''),
      engineer_required_by_rule: Number(autoEngineersByRule || 0),
      engineer_gap_count: Number(engineerGap || 0),
      admin_fee_manwon: detail.admin_fee_manwon, legal_fee_manwon: detail.legal_total_manwon,
      reception_fee_manwon: detail.reception_fee_manwon, registration_tax_manwon: detail.registration_tax_manwon,
      local_tax_manwon: detail.local_tax_manwon, bond_purchase_manwon: detail.bond_purchase_manwon,
      bond_instant_sale_loss_manwon: detail.bond_instant_sale_loss_manwon, diagnosis_fee_manwon: detail.diagnosis_fee_manwon,
      diagnosis_fee_base_manwon: detail.diagnosis_fee_base_manwon,
      diagnosis_fee_multiplier: detail.diagnosis_fee_multiplier,
      diagnosis_law_groups: detail.diagnosis_law_groups || [],
      legal_service_manwon: detail.legal_service_manwon,
      admin_fee_base_manwon: detail.admin_fee_base_manwon,
      admin_fee_extra_manwon: detail.admin_fee_extra_manwon,
      admin_fee_extra_license_count: detail.admin_fee_extra_license_count,
      capital_fund_manwon: detail.capital_fund_manwon, guarantee_deposit_manwon: detail.guarantee_deposit_manwon,
      capital_remain_after_guarantee_manwon: detail.capital_remain_after_guarantee_manwon,
      fees_taxes_manwon: detail.fees_taxes_manwon,
      professional_fees_manwon: detail.professional_fees_manwon,
      tax_surcharge_delta_manwon: detail.tax_surcharge_delta_manwon,
      direct_cost_eok: directCostEok,
      center, low, high, ready, confidence,
      service_track: PERMIT_SERVICE_TRACK,
      business_domain: PERMIT_BUSINESS_DOMAIN,
      page_mode: PERMIT_PAGE_MODE,
      legacy_page_mode: LEGACY_PAGE_MODE,
      source_tag: PERMIT_SOURCE_TAG,
      legacy_source_tag: LEGACY_SOURCE_TAG,
      note_lines: noteLines,
    }};
  }};

  const buildSummary = (out) => [
    brandName + ' AI 인허가 사전검토 상담 요청','',
    '[업종] ' + (out.license || '-'),
    '[등록 업종(복수)] ' + ((out.selected_licenses || []).length ? out.selected_licenses.join(', ') : '-'),
    '[업종 분류] ' + (out.class_type || '-'),
    '[법인 상태] ' + (out.corp_state === 'existing' ? '기존법인' : '신설법인'),
    '[주소 입력] ' + (out.region_input || '-'),
    '[중과세 판정] ' + ((out.region_result || '').trim() || (out.region === 'surcharge' ? '중과지역' : '일반지역')),
    '[예상 기준 필요자금] ' + fmtEok(out.center),
    '[실지출 비용(준비자금 제외)] ' + fmtEok(out.direct_cost_eok),
    '[예상 범위] ' + fmtEok(out.low) + ' ~ ' + fmtEok(out.high),
    '[권장 준비자금(+500만원)] ' + fmtEok(out.ready),
    '[신뢰도] ' + String(out.confidence || '-') + '%',
    '[서비스 트랙] 인허가 사전검토(신규등록) 전용 · 양도양수 산정 계산기와 별도 운영',
    '[업종 간 자본금 특례] 합산 ' + fmtEok(out.capital_without_special_eok) + ' / 특례차감 ' + fmtEok(out.capital_special_credit_eok) + ' / 기준 ' + fmtEok(out.capital_required_by_rule_eok),
    '[주력분야 선택] ' + ((out.major_fields_selected || []).length ? out.major_fields_selected.join(', ') : '해당 없음'),
    '[기술자 기준(특례 반영)] ' + Number(out.engineer_required_by_rule || out.engineer_count || 0).toLocaleString('ko-KR') + '명 (주력분야 특례 경감 ' + Number(out.engineer_exception_reduced || 0).toLocaleString('ko-KR') + '명, 업종 간 특례 경감 ' + Number(out.engineer_inter_special_credit || 0).toLocaleString('ko-KR') + '명)',
    '[준비자금] 자본금 ' + fmtManwon(out.capital_fund_manwon) + ' (출자예치금 ' + fmtManwon(out.guarantee_deposit_manwon) + ' 포함)',
    '[세부비용] 접수수수료 ' + fmtManwon(out.reception_fee_manwon) + ' / 등록면허세 ' + fmtManwon(out.registration_tax_manwon) + ' / 지방세 ' + fmtManwon(out.local_tax_manwon),
    '[세부비용] 채권매입(즉매손) ' + fmtManwon(out.bond_instant_sale_loss_manwon) + ' / 기업진단 ' + fmtManwon(out.diagnosis_fee_manwon) + ' (기준 ' + fmtManwon(out.diagnosis_fee_base_manwon) + ' × ' + Number(out.diagnosis_fee_multiplier || 1).toLocaleString('ko-KR') + '건) / 법무사 수임료 ' + fmtManwon(out.legal_service_manwon) + ' / 행정사 수임료 ' + fmtManwon(out.admin_fee_manwon),
    '[행정사 수임료 구성] 기본 ' + fmtManwon(out.admin_fee_base_manwon) + ' + 추가면허 가산 ' + fmtManwon(out.admin_fee_extra_manwon) + ' (추가 ' + Number(out.admin_fee_extra_license_count || 0).toLocaleString('ko-KR') + '개)',
    '[기업진단 법령군] ' + ((out.diagnosis_law_groups || []).map((x) => diagnosisLawLabel(x)).join(', ') || '건설'),
    '[입력] 자본금 ' + fmtEok(out.capital_eok) + ' / 출자예치금 ' + fmtEok(out.guarantee_eok) + ' / 출자좌수 ' + Number(out.guarantee_jwasu || 0).toLocaleString('ko-KR') + '좌 / 기술자 ' + Number(out.engineer_count || 0).toLocaleString('ko-KR') + '명',
    '[행정사/법무세금] ' + fmtManwon(out.admin_fee_manwon) + ' / ' + fmtManwon(out.legal_fee_manwon),
    '페이지: ' + window.location.href,
    '시각: ' + new Date().toLocaleString(),
  ].join('\\n');

  const sendUsage = (out) => {{
    if (!usageEndpoint) return;
    requestWithTimeout(usageEndpoint, {{ method: 'POST', headers: buildApiHeaders({{ 'Content-Type': 'application/json' }}), body: JSON.stringify({{ source: PERMIT_SOURCE_TAG, legacy_source: LEGACY_SOURCE_TAG, business_domain: PERMIT_BUSINESS_DOMAIN, service_track: PERMIT_SERVICE_TRACK, page_mode: PERMIT_PAGE_MODE, legacy_page_mode: LEGACY_PAGE_MODE, status: 'ok', result_center: fmtEok(out.center), result_range: fmtEok(out.low) + '~' + fmtEok(out.high), result_confidence: String(out.confidence) + '%', detail: out }}) }}, 5000).catch(() => {{}});
  }};

  const submitConsult = (out) => {{
    if (!consultEndpoint) return Promise.resolve(false);
    return requestWithTimeout(consultEndpoint, {{ method: 'POST', headers: buildApiHeaders({{ 'Content-Type': 'application/json' }}), body: JSON.stringify({{ source: PERMIT_SOURCE_TAG, legacy_source: LEGACY_SOURCE_TAG, business_domain: PERMIT_BUSINESS_DOMAIN, service_track: PERMIT_SERVICE_TRACK, page_mode: PERMIT_PAGE_MODE, legacy_page_mode: LEGACY_PAGE_MODE, subject: consultSubject, body: buildSummary(out), result_center: fmtEok(out.center), result_range: fmtEok(out.low) + '~' + fmtEok(out.high), result_confidence: String(out.confidence) + '%', payload: out }}) }}, 10000)
      .then((res) => {{ if (!res.ok) throw new Error(String(res.status || 'consult_http_error')); return true; }})
      .catch(() => false);
  }};

  const ensureMidSettlementBox = () => {{
    let box = $('acq-mid-settlement');
    if (box) return box;
    const breakdown = $('acq-breakdown');
    if (!breakdown || !breakdown.parentNode) return null;
    box = document.createElement('div');
    box.id = 'acq-mid-settlement';
    box.className = 'mid-settlement';
    breakdown.parentNode.insertBefore(box, breakdown);
    return box;
  }};
  const renderMidSettlementPlaceholder = () => {{
    const box = ensureMidSettlementBox();
    if (!box) return;
    box.innerHTML = '<div class="mid-title">중간 정산표 (실지출/준비자금 분리)</div><div class="mid-placeholder">계산을 실행하면 접수 수수료·등록면허세·채권 즉시매도 손실·준비자금을 항목별로 바로 표시합니다.</div>';
  }};
  const renderMidSettlement = (out) => {{
    const box = ensureMidSettlementBox();
    if (!box) return;
    box.innerHTML = [
      '<div class="mid-title">중간 정산표 (실지출/준비자금 분리)</div>',
      '<div class="mid-table">',
      '<div class="mid-row"><span>자본금 기준(특례 반영)</span><strong>' + fmtEok(out.capital_required_by_rule_eok) + '</strong></div>',
      '<div class="mid-row"><span>자본금 특례(기본/종합·전문)</span><strong>-' + fmtEok(Number(out.capital_special_base_credit_eok || 0)) + ' / -' + fmtEok(Number(out.capital_special_general_special_credit_eok || 0)) + '</strong></div>',
      '<div class="mid-row"><span>공제조합 출자예치금(자본금 내 배정)</span><strong>' + fmtEok(out.guarantee_required_by_rule_eok) + '</strong></div>',
      '<div class="mid-row"><span>공제조합 출자좌수 기준</span><strong>' + Number(out.guarantee_jwasu_by_rule || 0).toLocaleString('ko-KR') + '좌</strong></div>',
      '<div class="mid-row"><span>접수 수수료 + 등록면허세 + 지방세 + 채권 즉시매도 손실</span><strong>' + fmtManwon(out.fees_taxes_manwon) + '</strong></div>',
      '<div class="mid-row"><span>기업진단 수임(법령군별)</span><strong>' + fmtManwon(out.diagnosis_fee_manwon) + ' (기준 ' + fmtManwon(out.diagnosis_fee_base_manwon) + ' × ' + Number(out.diagnosis_fee_multiplier || 1).toLocaleString('ko-KR') + '건)</strong></div>',
      '<div class="mid-row"><span>행정사 수임료(기본+50% 가산)</span><strong>' + fmtManwon(out.admin_fee_manwon) + ' (기본 ' + fmtManwon(out.admin_fee_base_manwon) + ' + 가산 ' + fmtManwon(out.admin_fee_extra_manwon) + ')</strong></div>',
      '<div class="mid-row"><span>법무사/기업진단/행정사 수임료 소계</span><strong>' + fmtManwon(out.professional_fees_manwon) + '</strong></div>',
      '<div class="mid-row"><span>실지출 비용(준비자금 제외)</span><strong>' + fmtEok(out.direct_cost_eok) + '</strong></div>',
      '<div class="mid-row total"><span>총 필요자금(기준)</span><strong>' + fmtEok(out.center) + '</strong></div>',
      '</div>',
    ].join('');
  }};
  const renderBreakdown = (out) => {{
    const box = $('acq-breakdown');
    if (!box) return;
    box.innerHTML = [
      '<div class="group">[기본 정보]</div>',
      '<div class="row"><span>법인 상태</span><strong>' + (out.corp_state === 'existing' ? '기존법인' : '신설법인') + '</strong></div>',
      '<div class="row"><span>중과세 판정</span><strong>' + (((out.region_result || '').trim()) || (out.region === 'surcharge' ? '중과지역' : '일반지역')) + '</strong></div>',
      '<div class="group">[복수 업종 등록/특례]</div>',
      '<div class="row"><span>선택 업종</span><strong>' + (((out.selected_licenses || []).length ? out.selected_licenses.join(', ') : (out.license || '단일 업종'))) + '</strong></div>',
      '<div class="row"><span>자본금 합산(특례 전)</span><strong>' + fmtEok(out.capital_without_special_eok) + '</strong></div>',
      '<div class="row"><span>기본 자본금 특례 차감</span><strong>' + fmtEok(out.capital_special_base_credit_eok) + '</strong></div>',
      '<div class="row"><span>종합·전문간 자본금 특례 차감</span><strong>' + fmtEok(out.capital_special_general_special_credit_eok) + '</strong></div>',
      '<div class="row"><span>업종 간 자본금 특례 차감</span><strong>' + fmtEok(out.capital_special_credit_eok) + '</strong></div>',
      '<div class="row"><span>자본금 기준(특례 반영)</span><strong>' + fmtEok(out.capital_required_by_rule_eok) + '</strong></div>',
      '<div class="row"><span>종합·전문간 기술자 특례 경감</span><strong>' + Number(out.engineer_inter_general_special_credit || 0).toLocaleString('ko-KR') + '명</strong></div>',
      '<div class="row"><span>업종 간 기술자 특례 경감</span><strong>' + Number(out.engineer_inter_special_credit || 0).toLocaleString('ko-KR') + '명</strong></div>',
      '<div class="row"><span>업종 간 특례 적용 페어</span><strong>' + (out.engineer_inter_special_pair || '해당 없음') + '</strong></div>',
      '<div class="group">[기술자 기준/특례]</div>',
      '<div class="row"><span>주력분야 선택</span><strong>' + (((out.major_fields_selected || []).length ? out.major_fields_selected.join(', ') : '해당 없음')) + '</strong></div>',
      '<div class="row"><span>기술자 기준(최종)</span><strong>' + Number(out.engineer_required_by_rule || out.engineer_count || 0).toLocaleString('ko-KR') + '명</strong></div>',
      '<div class="row"><span>특례 미적용 기준</span><strong>' + Number(out.engineer_without_inter_special || out.engineer_without_major_exception || 0).toLocaleString('ko-KR') + '명</strong></div>',
      '<div class="row"><span>주력분야 특례 경감</span><strong>' + Number(out.engineer_exception_reduced || 0).toLocaleString('ko-KR') + '명</strong></div>',
      '<div class="group">[준비자금]</div>',
      '<div class="row"><span>자본금(출자예치금 포함)</span><strong>' + fmtManwon(out.capital_fund_manwon) + '</strong></div>',
      '<div class="row"><span>공제조합 출자예치금(자본금 내 배정)</span><strong>' + fmtManwon(out.guarantee_deposit_manwon) + '</strong></div>',
      '<div class="row"><span>공제조합 출자좌수 기준</span><strong>' + Number(out.guarantee_jwasu_by_rule || 0).toLocaleString('ko-KR') + '좌</strong></div>',
      '<div class="row"><span>자본금 잔여 운영자금(예치 후)</span><strong>' + fmtManwon(out.capital_remain_after_guarantee_manwon) + '</strong></div>',
      '<div class="group">[세금/수수료]</div>',
      '<div class="row"><span>접수 수수료</span><strong>' + fmtManwon(out.reception_fee_manwon) + '</strong></div>',
      '<div class="row"><span>등록면허세</span><strong>' + fmtManwon(out.registration_tax_manwon) + '</strong></div>',
      '<div class="row"><span>지방세</span><strong>' + fmtManwon(out.local_tax_manwon) + '</strong></div>',
      '<div class="row"><span>중과세 추가 반영분(등록면허세+지방세)</span><strong>' + fmtManwon(out.tax_surcharge_delta_manwon) + '</strong></div>',
      '<div class="row"><span>채권매입(즉시매도 손실)</span><strong>' + fmtManwon(out.bond_instant_sale_loss_manwon) + '</strong></div>',
      '<div class="group">[전문가 수임료]</div>',
      '<div class="row"><span>법무사 수임료(평균)</span><strong>' + fmtManwon(out.legal_service_manwon) + '</strong></div>',
      '<div class="row"><span>기업진단기관 수수료</span><strong>' + fmtManwon(out.diagnosis_fee_manwon) + '</strong></div>',
      '<div class="row"><span>기업진단 기준 × 수임건수</span><strong>' + fmtManwon(out.diagnosis_fee_base_manwon) + ' × ' + Number(out.diagnosis_fee_multiplier || 1).toLocaleString('ko-KR') + '건</strong></div>',
      '<div class="row"><span>기업진단 법령군</span><strong>' + (((out.diagnosis_law_groups || []).length ? (out.diagnosis_law_groups || []).map((x) => diagnosisLawLabel(x)).join(', ') : '건설')) + '</strong></div>',
      '<div class="row"><span>행정사 수수료</span><strong>' + fmtManwon(out.admin_fee_manwon) + '</strong></div>',
      '<div class="row"><span>행정사 기본 + 추가면허 가산</span><strong>' + fmtManwon(out.admin_fee_base_manwon) + ' + ' + fmtManwon(out.admin_fee_extra_manwon) + '</strong></div>',
      '<div class="group">[그룹 합계]</div>',
      '<div class="row"><span>세금/수수료 합계</span><strong>' + fmtManwon(out.fees_taxes_manwon) + '</strong></div>',
      '<div class="row"><span>전문가 수임료 합계</span><strong>' + fmtManwon(out.professional_fees_manwon) + '</strong></div>',
      '<div class="row"><span>실지출 비용(준비자금 제외)</span><strong>' + fmtEok(out.direct_cost_eok) + '</strong></div>',
      '<div class="row"><span>총 필요자금(기준)</span><strong>' + fmtEok(out.center) + '</strong></div>',
    ].join('');
  }};
  const render = (out) => {{ $('acq-out-center').textContent = fmtEok(out.center); $('acq-out-range').textContent = fmtEok(out.low) + '~' + fmtEok(out.high); $('acq-out-ready').textContent = fmtEok(out.ready); $('acq-out-confidence').textContent = String(out.confidence) + '%'; $('acq-note').innerHTML = out.note_lines.map((line) => '• ' + line).join('<br>'); renderMidSettlement(out); renderBreakdown(out); }};
  const runCalc = () => {{ syncDerivedFees(); const out = calc(); render(out); sendUsage(out); return out; }};
  const copyText = async (text) => {{
    const value = String(text || '').trim();
    if (!value) return false;
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      try {{
        await navigator.clipboard.writeText(value);
        return true;
      }} catch (_e) {{}}
    }}
    try {{
      const area = document.createElement('textarea');
      area.value = value;
      area.setAttribute('readonly', 'readonly');
      area.style.position = 'fixed';
      area.style.top = '-9999px';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.focus();
      area.select();
      const copied = document.execCommand('copy');
      document.body.removeChild(area);
      return !!copied;
    }} catch (_e) {{
      return false;
    }}
  }};
  const copySummary = async (out) => copyText(buildSummary(out));
  const setCalcBusy = (busy) => {{
    const btn = $('acq-btn-calc');
    if (!btn) return;
    isAcqCalculating = !!busy;
    btn.disabled = !!busy;
    btn.style.opacity = busy ? '0.72' : '';
    btn.style.cursor = busy ? 'wait' : '';
    btn.textContent = busy ? 'AI 계산 중...' : 'AI 인허가 사전검토 실행';
  }};
  const draftFieldIds = ['acq-license-type','acq-license-custom','acq-corp-state','acq-region-text','acq-region-override','acq-capital','acq-guarantee-jwasu','acq-guarantee','acq-engineer-count'];
  const draftToggleIds = ['acq-auto-fill','acq-ok-capital','acq-ok-engineer','acq-ok-office'];
  const persistDraft = () => {{
    try {{
      const payload = {{ saved_at: new Date().toISOString(), fields: {{}}, toggles: {{}}, major_fields: [], extra_licenses: [] }};
      draftFieldIds.forEach((id) => {{ const el = $(id); if (!el) return; payload.fields[id] = String(el.value || ''); }});
      draftToggleIds.forEach((id) => {{ const el = $(id); if (!el) return; payload.toggles[id] = !!el.checked; }});
      payload.major_fields = getSelectedMajorFields();
      payload.extra_licenses = getExtraSelectedLicenseNames();
      localStorage.setItem(draftStorageKey, JSON.stringify(payload));
    }} catch (_e) {{}}
  }};
  const restoreDraft = () => {{
    try {{
      const raw = localStorage.getItem(draftStorageKey);
      if (!raw) return false;
      const parsed = JSON.parse(raw);
      const fields = parsed && parsed.fields ? parsed.fields : {{}};
      const toggles = parsed && parsed.toggles ? parsed.toggles : {{}};
      pendingMajorFieldSelections = Array.isArray(parsed && parsed.major_fields) ? parsed.major_fields : null;
      pendingExtraLicenseSelections = Array.isArray(parsed && parsed.extra_licenses) ? parsed.extra_licenses : null;
      Object.keys(fields).forEach((id) => {{ const el = $(id); if (!el) return; el.value = String(fields[id] || ''); }});
      Object.keys(toggles).forEach((id) => {{ const el = $(id); if (!el) return; el.checked = !!toggles[id]; }});
      return true;
    }} catch (_e) {{
      return false;
    }}
  }};
  const clearDraft = () => {{ try {{ localStorage.removeItem(draftStorageKey); }} catch (_e) {{}} }};

  const resetForm = () => {{
    ['acq-license-type','acq-license-custom','acq-capital','acq-guarantee-jwasu','acq-guarantee','acq-engineer-count'].forEach((id) => {{ const el = $(id); if (!el) return; if (el.tagName === 'SELECT') el.value = ''; else el.value = ''; }});
    $('acq-region').value = 'normal'; if ($('acq-corp-state')) $('acq-corp-state').value = 'new'; if ($('acq-region-text')) $('acq-region-text').value = ''; if ($('acq-region-override')) $('acq-region-override').value = 'auto'; if ($('acq-region-result')) $('acq-region-result').value = ''; if ($('acq-region-help')) $('acq-region-help').textContent = ''; $('acq-auto-fill').checked = true; $('acq-ok-capital').checked = true; $('acq-ok-engineer').checked = true; $('acq-ok-office').checked = true;
    pendingMajorFieldSelections = null;
    pendingExtraLicenseSelections = null;
    $('acq-out-center').textContent = '-'; $('acq-out-range').textContent = '-'; $('acq-out-ready').textContent = '-'; $('acq-out-confidence').textContent = '-'; $('acq-note').textContent = '정보를 입력하고 ‘AI 인허가 사전검토 실행’ 버튼을 눌러주세요.';
    renderMidSettlementPlaceholder();
    const breakdown = $('acq-breakdown'); if (breakdown) breakdown.innerHTML = '';
    syncRegionInference();
    syncExtraLicenseBox(); syncMajorFieldBox(); syncPresetBox(); applyPreset(true);
    try {{
      const mode = localStorage.getItem(viewModeStorageKey);
      applyViewMode(mode === 'advanced' ? 'advanced' : 'simple');
    }} catch (_e) {{
      applyViewMode('simple');
    }}
    clearDraft();
  }};

  ensureCorporateRegField();
  ensureViewModeBar();
  renderMidSettlementPlaceholder();
  ['acq-license-type','acq-license-custom','acq-corp-state','acq-region-text','acq-region-override','acq-capital','acq-guarantee-jwasu','acq-guarantee','acq-engineer-count'].forEach((id) => {{
    const el = $(id); if (!el) return;
    el.addEventListener('input', () => {{
      if (id === 'acq-region-text' || id === 'acq-region-override') syncRegionInference();
      if (id === 'acq-license-type' || id === 'acq-license-custom') {{ syncExtraLicenseBox(); syncMajorFieldBox(); }}
      syncPresetBox();
      syncDerivedFees();
      persistDraft();
    }});
    el.addEventListener('change', () => {{
      if (id === 'acq-region-text' || id === 'acq-region-override') syncRegionInference();
      if (id === 'acq-license-type' || id === 'acq-license-custom') {{ syncExtraLicenseBox(); syncMajorFieldBox(); }}
      syncPresetBox();
      syncDerivedFees();
      if (id === 'acq-license-type') applyPreset(true);
      else if (id === 'acq-license-custom') applyPreset(false, true);
      persistDraft();
    }});
  }});
  $('acq-auto-fill').addEventListener('change', () => {{ applyPreset(false, true); persistDraft(); }});
  ['acq-ok-capital','acq-ok-engineer','acq-ok-office'].forEach((id) => {{
    const el = $(id); if (!el) return;
    el.addEventListener('change', persistDraft);
  }});
  $('acq-btn-calc').addEventListener('click', async () => {{
    if (isAcqCalculating) return;
    setCalcBusy(true);
    try {{
      const out = runCalc();
      persistDraft();
      const ok = await submitConsult(out);
      if (!ok && consultEndpoint && window.console) console.warn('[smna-acq] consult endpoint unreachable');
    }} finally {{
      setCalcBusy(false);
    }}
  }});
  $('acq-btn-reset').addEventListener('click', resetForm);
  $('acq-btn-chat-top').addEventListener('click', async () => {{ const out = runCalc(); persistDraft(); await copySummary(out); if (openchatUrl) return window.open(openchatUrl, '_blank', 'noopener,noreferrer'); alert('오픈채팅 URL이 아직 설정되지 않았습니다. 전화 또는 이메일로 문의해 주세요.'); }});
  $('acq-btn-chat').addEventListener('click', async () => {{ const out = runCalc(); persistDraft(); await copySummary(out); if (openchatUrl) return window.open(openchatUrl, '_blank', 'noopener,noreferrer'); alert('오픈채팅 URL이 아직 설정되지 않았습니다. 전화 또는 이메일로 문의해 주세요.'); }});
  const copyBtn = $('acq-btn-copy');
  if (copyBtn) {{
    copyBtn.addEventListener('click', async () => {{ const out = runCalc(); persistDraft(); const ok = await copySummary(out); alert(ok ? '결과 요약이 복사되었습니다.' : '요약 복사에 실패했습니다. 이메일 전달 버튼을 이용해 주세요.'); }});
  }}
  $('acq-btn-mail').addEventListener('click', () => {{ const out = runCalc(); persistDraft(); const targetEmail = contactEmail || ''; window.location.href = 'mailto:' + encodeURIComponent(targetEmail) + '?subject=' + encodeURIComponent(consultSubject) + '&body=' + encodeURIComponent(buildSummary(out)); }});
  $('acq-btn-phone').setAttribute('href', 'tel:' + contactDigits); $('acq-btn-phone').textContent = contactPhone; $('acq-btn-phone-top').setAttribute('href', 'tel:' + contactDigits); $('acq-btn-phone-top').textContent = contactPhone; $('acq-contact-phone').textContent = contactPhone;
  ensureCorporateRegField();
  const restored = restoreDraft();
  syncRegionInference();
  syncExtraLicenseBox();
  syncMajorFieldBox();
  syncPresetBox();
  try {{
    const mode = localStorage.getItem(viewModeStorageKey);
    applyViewMode(mode === 'advanced' ? 'advanced' : 'simple');
  }} catch (_e) {{
    applyViewMode('simple');
  }}
  if (!restored) applyPreset(true);
  else applyPreset(false, true);
  syncDerivedFees();
}})();
"""

    html_template = """<section id="smna-acq-calculator" class="smna-wrap">
<style>
html.smna-embed-co #masthead .custom-logo-link img,html.smna-embed-co header .custom-logo-link img{width:auto!important;max-width:84px!important;max-height:48px!important;height:auto!important;display:block!important;transform:none!important;margin:0 auto!important;object-fit:contain!important;position:relative!important;top:0!important;bottom:auto!important;object-position:center center!important;vertical-align:middle!important}
html.smna-embed-co #masthead .custom-logo-link,html.smna-embed-co header .custom-logo-link{display:inline-flex!important;align-items:center!important;justify-content:center!important;height:56px!important;min-height:56px!important;overflow:visible!important;line-height:1!important}
html.smna-embed-co #masthead .site-logo-img,html.smna-embed-co #masthead .site-logo-img .custom-logo-link{display:inline-flex!important;align-items:center!important;justify-content:center!important;line-height:1!important;overflow:visible!important;min-height:56px!important}
html.smna-embed-co #masthead .ast-primary-header-bar{min-height:92px!important;padding-top:10px!important;padding-bottom:10px!important;overflow:visible!important;display:flex!important;align-items:center!important}
html.smna-embed-co #masthead .main-header-bar-navigation,html.smna-embed-co #masthead .ast-builder-menu-1,html.smna-embed-co #masthead .ast-builder-menu-1 .menu-link{display:flex!important;align-items:center!important}
html.smna-embed-co #masthead .ast-builder-menu-1 .menu-link,html.smna-embed-co #masthead .main-header-menu > li > a{line-height:1.3!important;padding-top:13px!important;padding-bottom:13px!important}
html.smna-embed-co #masthead,html.smna-embed-co .site-header,html.smna-embed-co .main-header-bar,html.smna-embed-co .ast-primary-header-bar,html.smna-embed-co .site-logo-img,html.smna-embed-co .site-branding,html.smna-embed-co .ast-site-identity,html.smna-embed-co .ast-builder-layout-element,html.smna-embed-co .custom-logo-link,html.smna-embed-co .custom-logo,html.smna-embed-co .custom-logo-link img,html.smna-embed-co .entry-header,html.smna-embed-co .entry-title,html.smna-embed-co .wp-block-post-title,html.smna-embed-co .ast-breadcrumbs,html.smna-embed-co #colophon,html.smna-embed-co .site-below-footer-wrap{display:none!important}
html.smna-embed-co #content,html.smna-embed-co .site-content,html.smna-embed-co .ast-container,html.smna-embed-co #primary,html.smna-embed-co article{margin:0!important;padding:0!important;max-width:100%!important;width:100%!important}
#smna-acq-calculator,#smna-acq-calculator *{box-sizing:border-box}
#smna-acq-calculator{
  --smna-primary:#003764;
  --smna-primary-soft:#0a4a7b;
  --smna-neutral:#e8eef5;
  --smna-bg:#f4f7fb;
  --smna-surface:#ffffff;
  --smna-accent:#b87333;
  --smna-accent-soft:#fff6ec;
  --smna-accent-border:#e6c5a4;
  --smna-text:#0f172a;
  --smna-sub:#475569;
  font-family:"Pretendard","Noto Sans KR","Malgun Gothic",Arial,sans-serif;
  color:var(--smna-text);
  font-size:19px;
  line-height:1.68;
  margin:0 auto;
  max-width:1080px;
  background:var(--smna-bg);
  border:1px solid #d5e0ea;
  border-radius:20px;
  overflow:hidden;
}
#smna-acq-calculator .smna-header{
  background:linear-gradient(128deg,#003764 0%,#014477 74%,#0d4f84 100%);
  color:#f8fbff;
  padding:26px 28px 18px;
  border-bottom:1px solid rgba(255,255,255,.16);
}
#smna-acq-calculator .smna-brand{font-size:15px;font-weight:800;color:#e4f0fa}
#smna-acq-calculator .smna-badge{display:inline-flex;padding:4px 10px;border-radius:999px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.38);font-size:12px;font-weight:800;margin:8px 0}
#smna-acq-calculator h2{margin:0;font-size:42px;font-weight:800;line-height:1.25;color:#f8fbff!important;letter-spacing:-.02em;text-shadow:0 2px 10px rgba(0,0,0,.2)}
#smna-acq-calculator .smna-subtitle{margin-top:10px;font-size:22px;line-height:1.55;font-weight:700;color:#deecf8}
#smna-acq-calculator .smna-ratio{display:grid;grid-template-columns:7fr 2fr 1fr;margin-top:14px;height:8px;border-radius:999px;overflow:hidden}
#smna-acq-calculator .smna-ratio>div:nth-child(1){background:#003764}
#smna-acq-calculator .smna-ratio>div:nth-child(2){background:#d7e2ef}
#smna-acq-calculator .smna-ratio>div:nth-child(3){background:#b87333}
#smna-acq-calculator .smna-body{padding:20px;background:var(--smna-bg)}
.impact{background:var(--smna-accent-soft);border:1px solid var(--smna-accent-border);border-radius:12px;padding:10px 12px;margin-bottom:12px;font-size:17px;color:#7a4818;font-weight:700}
.impact.cta-row{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.impact .cta-text{font-size:22px;color:#6a3f17;font-weight:800;line-height:1.5}
.view-mode-bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;background:#eef4fb;border:1px solid #d3dfeb;border-radius:10px;padding:8px 10px;margin-bottom:10px}
.view-mode-btn{border:1px solid #c9d7e6;background:#fff;color:#22486d;border-radius:999px;padding:8px 12px;font-size:15px;font-weight:800;line-height:1;cursor:pointer}
.view-mode-btn.active{background:#003764;border-color:#003764;color:#fff}
.view-mode-desc{font-size:14px;color:#406385;font-weight:700}
.cta-button{display:inline-flex;align-items:center;justify-content:center;border:0;border-radius:11px;text-decoration:none;padding:14px 16px;font-size:20px;font-weight:800;white-space:nowrap;cursor:pointer;transition:.18s ease}
.cta-button.call{background:var(--smna-neutral);color:var(--smna-primary)}
.cta-button.chat{background:#b87333;color:#fff}
.smna-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px;align-items:start}
.panel{background:var(--smna-surface);border:1px solid #d6e1ec;border-radius:14px;overflow:hidden}
.panel h3{margin:0;padding:11px 14px;font-size:30px;font-weight:800;color:#fff;background:#003764;line-height:1.28}
.panel.result h3{background:#b87333}
.panel .panel-body{padding:14px;overflow:hidden}
.guide{font-size:16px;color:#0f3f67;background:#edf4fb;border:1px solid #cee0f0;border-radius:10px;padding:8px 10px;margin-bottom:10px}
.preset-box{border:1px solid #d6e0eb;background:#f6f9fd;border-radius:10px;padding:9px 10px;margin-bottom:10px;color:#1f4568;font-size:15px;line-height:1.45}
.rows{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.field{display:flex;flex-direction:column;gap:4px;min-width:0}
.field.wide{grid-column:1/-1}
label{font-size:16px;color:var(--smna-sub);font-weight:600}
input,select{width:100%;border:1px solid #cdd9e5;border-radius:10px;padding:12px 14px;font-size:17px;color:#0f172a;background:#fff;line-height:1.35;min-height:50px;transition:border-color .16s ease, box-shadow .16s ease}
input:focus,select:focus{border-color:#4b7ca4;box-shadow:0 0 0 3px rgba(0,55,100,.12);outline:none}
.checks{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.checks label{border:1px solid #e6c7a8;background:#fff8f0;border-radius:9px;padding:8px 10px;display:flex;align-items:center;gap:8px;font-size:16px;color:#7b4b1b;min-height:42px}
.major-field-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.major-field-list label{border:1px solid #c8d9ea;background:#eef5fd;border-radius:9px;padding:8px 10px;display:flex;align-items:center;gap:8px;font-size:15px;color:#21476a;min-height:40px}
.major-field-list input[type=checkbox]{width:18px!important;height:18px!important;min-height:18px!important;margin:0!important;flex:0 0 18px;appearance:auto!important;accent-color:#003764}
.field#acq-license-extra-wrap .major-field-list{max-height:180px;overflow:auto;padding-right:4px}
.major-field-hint{margin-top:6px;font-size:13px;line-height:1.5;color:#3f5f7f}
.checks input[type=checkbox]{width:18px!important;height:18px!important;min-height:18px!important;margin:0!important;flex:0 0 18px;appearance:auto!important;accent-color:#003764}
.btn-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
button{border:0;border-radius:10px;padding:11px 14px;font-size:19px;font-weight:900;cursor:pointer;transition:.18s ease}
button:hover,.cta-button:hover{transform:translateY(-1px)}
.btn-primary{background:#003764;color:#fff}
.btn-neutral{background:var(--smna-neutral);color:#0f172a}
.btn-chat{background:#b87333;color:#fff}
.result-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-bottom:8px}
.result-card{border:1px solid #d2deea;background:#fff;border-radius:10px;padding:10px 11px}
.result-card .k{display:block;color:#4c6078;font-size:14px;margin-bottom:2px}
.result-card .v{color:#003764;font-size:31px;line-height:1.2;font-weight:900}
.mid-settlement{margin:8px 0 10px;border:1px solid #d6e2ef;background:#fafdff;border-radius:10px;padding:9px 10px}
.mid-settlement .mid-title{font-size:14px;font-weight:900;color:#325273;margin:0 0 7px}
.mid-settlement .mid-placeholder{font-size:13px;color:#4e6985;line-height:1.5}
.mid-settlement .mid-table{display:grid;grid-template-columns:minmax(0,1fr);gap:4px}
.mid-settlement .mid-row{display:flex;justify-content:space-between;gap:10px;font-size:14px;color:#244564;line-height:1.4;border-bottom:1px dashed #d7e3ef;padding:3px 0}
.mid-settlement .mid-row:last-child{border-bottom:0}
.mid-settlement .mid-row strong{color:#003764;font-weight:900}
.mid-settlement .mid-row.total{padding-top:6px}
.cost-breakdown{margin:8px 0;border:1px solid #d7e3ee;background:#f7fbff;border-radius:10px;padding:8px 10px}
.cost-breakdown .group{margin:6px 0 2px;padding-top:6px;border-top:1px dashed #d3deea;font-size:12px;font-weight:900;color:#4a6280;letter-spacing:.01em}
.cost-breakdown .group:first-child{margin-top:0;padding-top:0;border-top:0}
.cost-breakdown .row{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:2px 0;font-size:14px;color:#244564}
.cost-breakdown .row strong{color:#003764;font-weight:900}
.note{margin-top:10px;border:1px solid var(--smna-accent-border);background:var(--smna-accent-soft);color:#7d4a17;font-size:16px;font-weight:700;border-radius:10px;padding:9px 10px;line-height:1.45;min-height:132px}
.small{margin-top:8px;font-size:14px;color:#52667f;line-height:1.55}
.action-buttons{margin-top:10px;display:flex;flex-wrap:wrap;gap:8px}
.action-buttons a,.action-buttons button{border:0;border-radius:10px;padding:11px 14px;font-size:18px;font-weight:900;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;white-space:nowrap}
.action-buttons a,.action-buttons button{flex:1 1 170px}
#smna-acq-calculator.smna-simple-mode .cost-breakdown{display:none}
@media (max-width:1150px){.smna-grid{grid-template-columns:1fr}.rows{grid-template-columns:1fr}.checks{grid-template-columns:1fr}.result-grid{grid-template-columns:1fr}#smna-acq-calculator h2{font-size:33px}.impact .cta-text{font-size:17px}.cta-button{font-size:18px}.panel h3{font-size:26px}.action-buttons a,.action-buttons button{flex:1 1 calc(50% - 8px);font-size:16px;padding:10px 11px;white-space:normal}}
</style>
<div class="smna-header"><div class="smna-brand">__BRAND_LABEL__</div><div class="smna-badge">전국 최초</div><h2>__TITLE__</h2><div class="smna-subtitle">법령 연동 완료 업종 중심으로 등록기준(자본금·기술자·예치요건)을 사전 점검합니다. 미연동 업종은 전문가 확인 후 안내합니다. 양도양수 산정은 별도 계산기에서 진행합니다.</div><div class="smna-ratio"><div></div><div></div><div></div></div></div>
<div class="smna-body"><div class="impact cta-row"><span class="cta-text">법령 연동 업종 기준으로 1분 사전점검 후 상담을 진행하세요.</span><span class="cta-actions"><button type="button" class="cta-button chat" id="acq-btn-chat-top">대표 행정사 1:1 직접 상담</button><a id="acq-btn-phone-top" class="cta-button call" href="tel:__PHONE_DIGITS__">__PHONE__</a></span></div><div class="smna-grid"><div class="panel"><h3>1단계: 인허가 사전검토 정보 입력</h3><div class="panel-body"><div class="guide">① 업종 선택 → ② 법인 상태 선택 → ③ 법인 주소 입력 순서로 진행하면 자동으로 기준값과 중과세 여부를 판정합니다. 주력분야·복수 업종 특례도 자동 반영됩니다. 이 화면은 신규등록(인허가) 전용이며 양도양수는 별도 계산기에서 진행합니다.</div><div class="preset-box" id="acq-preset-box">업종을 선택하면 기준값이 표시됩니다.</div><div class="rows"><div class="field"><label for="acq-license-type">업종 선택</label><select id="acq-license-type">__OPTIONS__</select></div><div class="field"><label for="acq-license-custom">직접 입력 업종명(선택)</label><input id="acq-license-custom" type="text" maxlength="80" placeholder="예: 기타 전문공사업" /></div><div class="field"><label for="acq-corp-state">법인 상태</label><select id="acq-corp-state"><option value="new">신설법인</option><option value="existing">기존법인</option></select></div><div class="field"><label for="acq-region-text">법인 주소(시/구/동)</label><input id="acq-region-text" type="text" maxlength="80" placeholder="예: 서울 강남구 역삼동" /></div><div class="field"><label for="acq-region-result">중과세 자동판정</label><input id="acq-region-result" type="text" readonly placeholder="주소 입력 시 자동 판정" /></div><div class="field"><label for="acq-region-override">중과세 수동수정(필요시)</label><select id="acq-region-override"><option value="auto">자동판정 사용</option><option value="normal">수동: 일반지역</option><option value="surcharge">수동: 중과지역</option></select><input id="acq-region" type="hidden" value="normal" /><div class="major-field-hint" id="acq-region-help"></div></div><div class="field wide" id="acq-license-extra-wrap"><label>추가 등록 업종(복수 선택)</label><div class="major-field-list" id="acq-license-extra-list"></div><div class="major-field-hint" id="acq-license-extra-hint"></div></div><div class="field wide" id="acq-major-field-wrap" style="display:none"><label>주력분야 선택(복수 선택 가능)</label><div class="major-field-list" id="acq-major-field-list"></div><div class="major-field-hint" id="acq-major-field-hint"></div></div><div class="field wide"><label><input id="acq-auto-fill" type="checkbox" checked style="width:18px;height:18px;min-height:18px;vertical-align:middle;margin-right:6px;" /> 업종 선택 시 자동 기준 입력</label></div><div class="field"><label for="acq-capital">자본금(억)</label><input id="acq-capital" type="number" step="0.1" /></div><div class="field"><label for="acq-guarantee-jwasu">공제조합 출자좌수(좌)</label><input id="acq-guarantee-jwasu" type="number" step="1" /></div><div class="field"><label for="acq-guarantee">공제조합 출자예치금(억, 자본금 내 배정)</label><input id="acq-guarantee" type="number" step="0.01" /></div><div class="field"><label for="acq-engineer-count">기술자 수(명)</label><input id="acq-engineer-count" type="number" step="1" min="0" /></div><div class="field"><label for="acq-admin-fee">행정사 수임료(만원)</label><input id="acq-admin-fee" type="number" step="1" readonly /></div><div class="field"><label for="acq-legal-fee">세금·법무 자동합계(만원)</label><input id="acq-legal-fee" type="number" step="0.1" readonly /></div><div class="field wide"><label>필수 기준 체크</label><div class="checks"><label><input id="acq-ok-capital" type="checkbox" checked /> 자본금 기준 충족</label><label><input id="acq-ok-engineer" type="checkbox" checked /> 기술자 기준 충족</label><label><input id="acq-ok-office" type="checkbox" checked /> 사무실 기준 충족</label></div></div></div><div class="btn-row"><button type="button" class="btn-primary" id="acq-btn-calc">AI 인허가 사전검토 실행</button><button type="button" class="btn-neutral" id="acq-btn-reset">입력 초기화</button></div><div class="small">제외 항목: 준비기간 비용, 사무실 초기비, 협회/교육 비용 · 양도양수 가격 산정은 별도 계산기에서 제공합니다.</div></div></div><div class="panel result"><h3>2단계: AI 산정 결과 확인</h3><div class="panel-body"><div class="result-grid"><div class="result-card"><span class="k">예상 기준 필요자금</span><strong class="v" id="acq-out-center">-</strong></div><div class="result-card"><span class="k">예상 비용 범위</span><strong class="v" id="acq-out-range">-</strong></div><div class="result-card"><span class="k">권장 준비자금(+500만원)</span><strong class="v" id="acq-out-ready">-</strong></div><div class="result-card"><span class="k">계산 신뢰도</span><strong class="v" id="acq-out-confidence">-</strong></div></div><div class="cost-breakdown" id="acq-breakdown"></div><div class="note" id="acq-note">정보를 입력하고 ‘AI 인허가 사전검토 실행’ 버튼을 눌러주세요.</div><div class="action-buttons"><button type="button" class="btn-chat" id="acq-btn-chat">1:1 직접 상담</button><a class="btn-neutral" href="tel:__PHONE_DIGITS__" id="acq-btn-phone">__PHONE__</a><button type="button" class="btn-neutral" id="acq-btn-copy">결과 요약 복사</button><button type="button" class="btn-neutral" id="acq-btn-mail">결과를 이메일로 전달</button></div><div class="small">문의: <strong>__CONTACT_EMAIL__</strong> · 연락처: <strong id="acq-contact-phone">__PHONE__</strong></div></div></div></div></div>
__SCRIPT__
</section>"""

    return (
        html_template.replace("__TITLE__", escape(str(title or "AI 인허가 사전검토 진단기(신규등록 전용)")))
        .replace("__BRAND_LABEL__", escape(brand_label))
        .replace("__CONTACT_EMAIL__", escape(contact_email or "-"))
        .replace("__PHONE__", escape(contact))
        .replace("__PHONE_DIGITS__", escape(contact_digits))
        .replace("__OPTIONS__", options_html)
        .replace("__SCRIPT__", _pack_inline_script(js_code))
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build permit precheck (new-registration) calculator HTML")
    parser.add_argument("--output", default="output/ai_license_acquisition_calculator.html")
    parser.add_argument("--title", default="")
    parser.add_argument("--channel-id", default="")
    parser.add_argument("--contact-phone", default="")
    parser.add_argument("--openchat-url", default="")
    parser.add_argument("--consult-endpoint", default="")
    parser.add_argument("--usage-endpoint", default="")
    parser.add_argument("--api-key", default="")
    args = parser.parse_args()

    branding = resolve_channel_branding(
        channel_id=str(args.channel_id or "").strip(),
        overrides={
            "contact_phone": str(args.contact_phone or "").strip(),
            "openchat_url": str(args.openchat_url or "").strip(),
        },
    )
    default_title = f"AI 인허가 사전검토 진단기(신규등록 전용) | {str(branding.get('brand_name') or '파트너').strip()}"

    html = build_page_html(
        title=str(args.title or default_title),
        channel_id=str(args.channel_id or ""),
        contact_phone=str(args.contact_phone or ""),
        openchat_url=str(args.openchat_url or ""),
        consult_endpoint=str(args.consult_endpoint or ""),
        usage_endpoint=str(args.usage_endpoint or ""),
        api_key=str(args.api_key or ""),
    )
    out_path = Path(str(args.output)).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(
        json.dumps(
            {
                "saved": str(out_path),
                "bytes": len(html.encode("utf-8")),
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "title": str(args.title or default_title),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())




