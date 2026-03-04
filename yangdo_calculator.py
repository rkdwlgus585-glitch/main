import json
import os
import re
from datetime import datetime
from html import escape
def _round4(value):
    if value is None:
        return None
    return round(float(value), 4)
def safe_json_for_script(data):
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (
        text.replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _sanitize_endpoint(url):
    src = str(url or "").strip()
    if not src:
        return ""
    lowered = src.lower()
    if lowered.startswith("javascript:"):
        return ""
    if "localhost" in lowered or "127.0.0.1" in lowered or "::1" in lowered:
        return ""
    return src
def listing_detail_url(site_url, seoul_no=0, now_uid=""):
    base = str(site_url or "").rstrip("/")
    if not base:
        base = "https://seoulmna.co.kr"
    try:
        no = int(seoul_no or 0)
    except Exception:
        no = 0
    if no > 0:
        return f"{base}/mna/{no}"
    uid_txt = str(now_uid or "").strip()
    if uid_txt.isdigit():
        return f"{base}/mna/{uid_txt}"
    return f"{base}/mna"
def _normalize_price_text(raw):
    src = str(raw or "")
    if not src:
        return ""
    src = (
        src.replace("\uFF0D", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u223C", "~")
        .replace("\u301C", "~")
        .replace("\uFF0F", "/")
    )
    src = re.sub(r"(?<=\d)\s*\uC5D0", "\uC5B5", src)
    src = re.sub(r"<br\s*/?>", "\n", src, flags=re.I)
    return src
def _price_token_to_eok(token):
    src = str(token or "").strip().replace(",", "")
    if not src:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*\uC5B5(?:\s*(\d+(?:\.\d+)?)\s*\uB9CC)?", src)
    if m:
        eok = float(m.group(1))
        man = float(m.group(2) or 0.0)
        val = eok + (man / 10000.0)
        return _round4(val) if val > 0 else None
    m = re.search(r"(\d+(?:\.\d+)?)\s*\uB9CC", src)
    if m:
        val = float(m.group(1)) / 10000.0
        return _round4(val) if val > 0 else None
    m = re.search(r"\d+(?:\.\d+)?", src)
    if m and "\uC5B5" in src:
        val = float(m.group(0))
        return _round4(val) if val > 0 else None
    return None
def _extract_price_values_eok(raw):
    src = _normalize_price_text(raw)
    if not src:
        return []
    out = []
    for m in re.finditer(r"\d+(?:\.\d+)?\s*\uC5B5(?:\s*\d+(?:\.\d+)?\s*\uB9CC)?|\d+(?:\.\d+)?\s*\uB9CC", src):
        val = _price_token_to_eok(m.group(0))
        if isinstance(val, (int, float)) and float(val) > 0:
            out.append(float(val))
    seen = set()
    uniq = []
    for v in out:
        key = f"{v:.4f}"
        if key in seen:
            continue
        seen.add(key)
        uniq.append(v)
    return uniq
def _derive_display_range_eok(current_price_text, claim_price_text, current_price_eok, claim_price_eok):
    claim_txt = _normalize_price_text(claim_price_text)
    current_txt = _normalize_price_text(current_price_text)
    claim_vals = _extract_price_values_eok(claim_txt)
    current_vals = _extract_price_values_eok(current_txt)
    values = []
    if claim_vals:
        values.extend(claim_vals)
    if current_vals:
        values.extend(current_vals)
    if len(values) < 2:
        if isinstance(current_price_eok, (int, float)) and float(current_price_eok) > 0:
            values.append(float(current_price_eok))
        if isinstance(claim_price_eok, (int, float)) and float(claim_price_eok) > 0:
            values.append(float(claim_price_eok))
    vals = [float(v) for v in values if isinstance(v, (int, float)) and float(v) > 0]
    if not vals:
        return None, None
    return _round4(min(vals)), _round4(max(vals))
def build_training_dataset(records, site_url=""):
    rows = []
    for rec in list(records or []):
        price = rec.get("current_price_eok")
        claim = rec.get("claim_price_eok")
        if not isinstance(price, (int, float)) or float(price) <= 0:
            continue
        display_low, display_high = _derive_display_range_eok(
            rec.get("current_price_text", ""),
            rec.get("claim_price_text", ""),
            price,
            claim,
        )
        if not isinstance(display_low, (int, float)) or float(display_low) <= 0:
            display_low = float(price)
        if not isinstance(display_high, (int, float)) or float(display_high) <= 0:
            display_high = float(price)
        if float(display_high) < float(display_low):
            display_low, display_high = display_high, display_low
        try:
            seoul_no = int(rec.get("number", 0) or 0)
        except Exception:
            seoul_no = 0
        rows.append(
            {
                "now_uid": str(rec.get("uid", "")).strip(),
                "seoul_no": seoul_no,
                "license_text": str(rec.get("license_text", "") or ""),
                "tokens": sorted(list(rec.get("license_tokens", set()) or set())),
                "license_year": rec.get("license_year"),
                "specialty": rec.get("specialty"),
                "y20": rec.get("years", {}).get("y20"),
                "y21": rec.get("years", {}).get("y21"),
                "y22": rec.get("years", {}).get("y22"),
                "y23": rec.get("years", {}).get("y23"),
                "y24": rec.get("years", {}).get("y24"),
                "y25": rec.get("years", {}).get("y25"),
                "sales3_eok": rec.get("sales3_eok"),
                "sales5_eok": rec.get("sales5_eok"),
                "capital_eok": rec.get("capital_eok"),
                "surplus_eok": rec.get("surplus_eok"),
                "debt_ratio": rec.get("debt_ratio"),
                "liq_ratio": rec.get("liq_ratio"),
                "company_type": str(rec.get("company_type", "") or ""),
                "location": str(rec.get("location", "") or ""),
                "association": str(rec.get("association", "") or ""),
                "shares": rec.get("shares"),
                "balance_eok": rec.get("balance_eok"),
                "price_eok": float(price),
                "claim_eok": float(claim) if isinstance(claim, (int, float)) and float(claim) > 0 else None,
                "display_low_eok": float(display_low),
                "display_high_eok": float(display_high),
                "url": listing_detail_url(site_url, seoul_no=seoul_no, now_uid=rec.get("uid", "")),
            }
        )
    return rows


def _compact_train_row(row):
    src = dict(row or {})
    return [
        str(src.get("now_uid", "") or ""),  # 0
        int(src.get("seoul_no", 0) or 0),  # 1
        str(src.get("license_text", "") or ""),  # 2
        list(src.get("tokens", []) or []),  # 3
        src.get("license_year"),  # 4
        src.get("specialty"),  # 5
        src.get("y23"),  # 6
        src.get("y24"),  # 7
        src.get("y25"),  # 8
        src.get("sales3_eok"),  # 9
        src.get("sales5_eok"),  # 10
        src.get("capital_eok"),  # 11
        src.get("surplus_eok"),  # 12
        src.get("debt_ratio"),  # 13
        src.get("liq_ratio"),  # 14
        str(src.get("company_type", "") or ""),  # 15
        src.get("balance_eok"),  # 16
        src.get("price_eok"),  # 17
        src.get("display_low_eok"),  # 18
        src.get("display_high_eok"),  # 19
        str(src.get("url", "") or ""),  # 20
    ]
def calc_quantile(values, q):
    nums = []
    for raw in list(values or []):
        try:
            nums.append(float(raw))
        except Exception:
            continue
    if not nums:
        return None
    nums.sort()
    qv = max(0.0, min(1.0, float(q)))
    if len(nums) == 1:
        return nums[0]
    idx = qv * (len(nums) - 1)
    lo = int(idx)
    hi = min(len(nums) - 1, lo + 1)
    frac = idx - lo
    return nums[lo] + (nums[hi] - nums[lo]) * frac
def mean_or_none(values):
    nums = []
    for raw in list(values or []):
        try:
            n = float(raw)
        except Exception:
            continue
        if n != n:
            continue
        nums.append(n)
    if not nums:
        return None
    return _round4(sum(nums) / float(len(nums)))
def build_meta(all_records, train_dataset):
    prices = [row.get("price_eok") for row in list(train_dataset or [])]
    specialty_vals = [row.get("specialty") for row in list(train_dataset or [])]
    sales3_vals = [row.get("sales3_eok") for row in list(train_dataset or [])]
    debt_vals = [row.get("debt_ratio") for row in list(train_dataset or [])]
    liq_vals = [row.get("liq_ratio") for row in list(train_dataset or [])]
    capital_vals = [row.get("capital_eok") for row in list(train_dataset or [])]
    surplus_vals = [row.get("surplus_eok") for row in list(train_dataset or [])]
    balance_vals = [row.get("balance_eok") for row in list(train_dataset or [])]
    top_licenses = {}
    for rec in list(all_records or []):
        for token in rec.get("license_tokens", set()) or set():
            top_licenses[token] = top_licenses.get(token, 0) + 1
    top_items = sorted(top_licenses.items(), key=lambda x: (-x[1], x[0]))[:12]
    all_count = len(list(all_records or []))
    train_count = len(list(train_dataset or []))
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "all_record_count": all_count,
        "train_count": train_count,
        "priced_ratio": _round4((train_count / max(1, all_count)) * 100.0),
        "median_price_eok": _round4(calc_quantile(prices, 0.5)),
        "p25_price_eok": _round4(calc_quantile(prices, 0.25)),
        "p75_price_eok": _round4(calc_quantile(prices, 0.75)),
        "avg_debt_ratio": mean_or_none(debt_vals),
        "avg_liq_ratio": mean_or_none(liq_vals),
        "avg_capital_eok": mean_or_none(capital_vals),
        "p90_capital_eok": _round4(calc_quantile(capital_vals, 0.9)),
        "avg_surplus_eok": mean_or_none(surplus_vals),
        "p90_surplus_eok": _round4(calc_quantile(surplus_vals, 0.9)),
        "avg_balance_eok": mean_or_none(balance_vals),
        "p90_balance_eok": _round4(calc_quantile(balance_vals, 0.9)),
        "median_specialty": _round4(calc_quantile(specialty_vals, 0.5)),
        "p90_specialty": _round4(calc_quantile(specialty_vals, 0.9)),
        "median_sales3_eok": _round4(calc_quantile(sales3_vals, 0.5)),
        "p90_sales3_eok": _round4(calc_quantile(sales3_vals, 0.9)),
        "top_license_tokens": [{"token": k, "count": v} for k, v in top_items],
    }


def _collapse_script_whitespace(html_text):
    src = str(html_text or "")
    if not src:
        return src
    if str(os.environ.get("SMNA_DISABLE_SCRIPT_COLLAPSE", "")).strip().lower() in {"1", "true", "yes", "on"}:
        return src
    def _pack_script(match):
        open_tag = str(match.group(1) or "")
        body = str(match.group(2) or "")
        close_tag = str(match.group(3) or "")
        if "src=" in open_tag.lower():
            return f"{open_tag}{body}{close_tag}"
        compact_body = "\n".join(line.strip() for line in body.splitlines() if line.strip())
        payload = compact_body.replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        payload_json = json.dumps(payload, ensure_ascii=False)
        loader = (
            "(function(){"
            "try{"
            f"var code={payload_json};"
            "code=code.replace(/\\\\u0026/g,String.fromCharCode(38));"
            "(0,eval)(code);"
            "}catch(e){"
            "if(window.console){try{console.error('[smna-calc] script load failed',e);}catch(_e){}}"
            "}"
            "})();"
        )
        return f"{open_tag}{loader}{close_tag}"

    return re.sub(r"(<script[^>]*>)([\s\S]*?)(</script>)", _pack_script, src, flags=re.IGNORECASE)


def build_page_html(
    train_dataset,
    meta,
    site_url="",
    license_canonical_by_key=None,
    generic_license_keys=None,
    view_mode="customer",
    consult_endpoint="",
    usage_endpoint="",
    estimate_endpoint="",
    contact_phone="010-9926-8661",
    openchat_url="",
):
    mode = str(view_mode or "customer").strip().lower()
    if mode not in {"customer", "owner"}:
        mode = "customer"
    estimate_endpoint_text = _sanitize_endpoint(estimate_endpoint)
    consult_endpoint_text = _sanitize_endpoint(consult_endpoint)
    usage_endpoint_text = _sanitize_endpoint(usage_endpoint)
    openchat_url_text = _sanitize_endpoint(openchat_url)
    dataset_payload = [] if estimate_endpoint_text else [_compact_train_row(row) for row in list(train_dataset or [])]
    dataset_json = safe_json_for_script(dataset_payload)
    meta_json = safe_json_for_script(meta)
    canonical_map_json = safe_json_for_script(dict(license_canonical_by_key or {}))
    generic_keys_json = safe_json_for_script(sorted(list(generic_license_keys or [])))
    mode_json = safe_json_for_script(mode)
    consult_endpoint_json = safe_json_for_script(consult_endpoint_text)
    usage_endpoint_json = safe_json_for_script(usage_endpoint_text)
    estimate_endpoint_json = safe_json_for_script(estimate_endpoint_text)
    contact_phone_json = safe_json_for_script(str(contact_phone or "").strip() or "010-9926-8661")
    openchat_url_json = safe_json_for_script(openchat_url_text)
    title = "AI 양도가 산정 계산기" if mode == "customer" else "AI 양도가 산정 계산기 (내부 검수)"
    meta_mid_label = "중앙 기준가(억)" if mode == "customer" else "중앙 양도가(억)"
    html = f"""<section id="seoulmna-yangdo-calculator" class="smna-wrap">
  <style>
    #seoulmna-yangdo-calculator, #seoulmna-yangdo-calculator * {{ box-sizing: border-box; }}
    html.smna-embed-co #masthead .custom-logo-link img,
    html.smna-embed-co header .custom-logo-link img {{
      width: auto !important;
      max-width: 84px !important;
      max-height: 48px !important;
      height: auto !important;
      display: block !important;
      transform: none !important;
      margin: 0 auto !important;
      object-fit: contain !important;
      position: relative !important;
      top: 0 !important;
      bottom: auto !important;
      object-position: center center !important;
      vertical-align: middle !important;
    }}
    html.smna-embed-co #masthead .custom-logo-link,
    html.smna-embed-co header .custom-logo-link {{
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      height: 56px !important;
      min-height: 56px !important;
      overflow: visible !important;
      line-height: 1 !important;
    }}
    html.smna-embed-co #masthead .site-logo-img,
    html.smna-embed-co #masthead .site-logo-img .custom-logo-link {{
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      line-height: 1 !important;
      overflow: visible !important;
      min-height: 56px !important;
    }}
    html.smna-embed-co #masthead .ast-primary-header-bar {{
      min-height: 92px !important;
      padding-top: 10px !important;
      padding-bottom: 10px !important;
      overflow: visible !important;
      display: flex !important;
      align-items: center !important;
    }}
    html.smna-embed-co #masthead .main-header-bar-navigation,
    html.smna-embed-co #masthead .ast-builder-menu-1,
    html.smna-embed-co #masthead .ast-builder-menu-1 .menu-link {{
      display: flex !important;
      align-items: center !important;
    }}
    html.smna-embed-co #masthead .ast-builder-menu-1 .menu-link,
    html.smna-embed-co #masthead .main-header-menu > li > a {{
      line-height: 1.3 !important;
      padding-top: 13px !important;
      padding-bottom: 13px !important;
    }}
    html.smna-embed-co #masthead,
    html.smna-embed-co .site-header,
    html.smna-embed-co .main-header-bar,
    html.smna-embed-co .ast-primary-header-bar,
    html.smna-embed-co .site-logo-img,
    html.smna-embed-co .site-branding,
    html.smna-embed-co .ast-site-identity,
    html.smna-embed-co .ast-builder-layout-element,
    html.smna-embed-co .custom-logo-link,
    html.smna-embed-co .custom-logo,
    html.smna-embed-co .custom-logo-link img,
    html.smna-embed-co .entry-header,
    html.smna-embed-co .entry-title,
    html.smna-embed-co .ast-breadcrumbs,
    html.smna-embed-co #colophon,
    html.smna-embed-co .site-below-footer-wrap {{
      display: none !important;
    }}
    html.smna-embed-co #content,
    html.smna-embed-co .site-content,
    html.smna-embed-co .ast-container,
    html.smna-embed-co #primary,
    html.smna-embed-co article {{
      margin: 0 !important;
      padding: 0 !important;
      max-width: 100% !important;
      width: 100% !important;
    }}
    #seoulmna-yangdo-calculator {{
      --smna-primary: #003764;
      --smna-neutral: #e8eef5;
      --smna-accent: #b87333;
      --smna-bg: #f4f7fb;
      --smna-accent-soft: #fff6ec;
      --smna-accent-border: #e6c5a4;
      --smna-text: #0f172a;
      --smna-sub: #475569;
      font-family: "Pretendard", "Noto Sans KR", "Malgun Gothic", Arial, sans-serif;
      color: var(--smna-text);
      font-size: 19px;
      line-height: 1.68;
      margin: 0 auto;
      max-width: 1080px;
      background: var(--smna-bg);
      border: 1px solid #d5e0ea;
      border-radius: 20px;
      overflow: hidden;
    }}
    #seoulmna-yangdo-calculator .smna-header {{
      background: linear-gradient(128deg, #003764 0%, #014477 74%, #0d4f84 100%);
      color: #f8fbff;
      padding: 26px 28px 18px;
      border-bottom: 1px solid rgba(255,255,255,.16);
    }}
    #seoulmna-yangdo-calculator .smna-brand-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 8px;
    }}
    #seoulmna-yangdo-calculator .smna-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,.14);
      border: 1px solid rgba(255,255,255,.36);
      color: #f4fbff;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: .02em;
      margin-bottom: 8px;
    }}
    #seoulmna-yangdo-calculator .smna-brand {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 15px;
      letter-spacing: .015em;
      font-weight: 800;
      color: #e4f0fa;
    }}
    #seoulmna-yangdo-calculator .smna-mode {{
      font-size: 13px;
      color: #f4f8fc;
      padding: 4px 9px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,.38);
      background: rgba(255,255,255,.12);
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator h2 {{
      margin: 0;
      font-size: 42px;
      font-weight: 800;
      letter-spacing: -0.02em;
      line-height: 1.25;
      color: #f8fbff !important;
      text-shadow: 0 2px 10px rgba(0,0,0,.22);
    }}
    #seoulmna-yangdo-calculator .smna-subtitle {{
      margin-top: 10px;
      font-size: 22px;
      line-height: 1.55;
      font-weight: 700;
      color: #d7e8f6;
    }}
    #seoulmna-yangdo-calculator .smna-ratio {{
      display: grid;
      grid-template-columns: 7fr 2fr 1fr;
      margin-top: 14px;
      height: 8px;
      border-radius: 999px;
      overflow: hidden;
    }}
    #seoulmna-yangdo-calculator .smna-ratio > div:nth-child(1) {{ background: #003764; }}
    #seoulmna-yangdo-calculator .smna-ratio > div:nth-child(2) {{ background: #d7e2ef; }}
    #seoulmna-yangdo-calculator .smna-ratio > div:nth-child(3) {{ background: #b87333; }}
    #seoulmna-yangdo-calculator .smna-body {{
      padding: 20px;
      background: var(--smna-bg);
    }}
    #seoulmna-yangdo-calculator .smna-meta {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }}
    #seoulmna-yangdo-calculator .smna-meta .item {{
      background: #ffffff;
      border: 1px solid #d9e3ed;
      border-radius: 12px;
      padding: 10px 12px;
    }}
    #seoulmna-yangdo-calculator .smna-meta .label {{
      display: block;
      font-size: 13px;
      color: var(--smna-sub);
      margin-bottom: 2px;
    }}
    #seoulmna-yangdo-calculator .smna-meta .value {{
      font-size: 24px;
      font-weight: 700;
      color: var(--smna-primary);
      line-height: 1.2;
    }}
    #seoulmna-yangdo-calculator .impact {{
      background: var(--smna-accent-soft);
      border: 1px solid var(--smna-accent-border);
      border-radius: 12px;
      padding: 10px 12px;
      margin-bottom: 12px;
      font-size: 17px;
      color: #7a4818;
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator .impact.cta-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator .impact .cta-text {{
      font-size: 22px;
      color: #6a3f17;
      font-weight: 800;
      line-height: 1.5;
    }}
    #seoulmna-yangdo-calculator .impact .cta-actions {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator .cta-button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 0;
      border-radius: 11px;
      text-decoration: none;
      padding: 14px 16px;
      font-size: 20px;
      font-weight: 800;
      white-space: nowrap;
      cursor: pointer;
      transition: .18s ease;
    }}
    #seoulmna-yangdo-calculator .cta-button.call {{ background: var(--smna-neutral); color: #003764; }}
    #seoulmna-yangdo-calculator .cta-button.chat {{ background: #b87333; color: #fff; border: 1px solid #a5652d; }}
    #seoulmna-yangdo-calculator .smna-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 14px;
      align-items: start;
    }}
    #seoulmna-yangdo-calculator .smna-grid .panel + .panel {{
      margin-top: 0;
    }}
    #seoulmna-yangdo-calculator .panel {{
      background: #ffffff;
      border: 1px solid #d8e3ee;
      border-radius: 14px;
      overflow: hidden;
    }}
    #seoulmna-yangdo-calculator .panel h3 {{
      margin: 0;
      padding: 11px 14px;
      font-size: 30px;
      font-weight: 800;
      color: #fff;
      background: var(--smna-primary);
      line-height: 1.28;
    }}
    #seoulmna-yangdo-calculator .panel.result h3 {{ background: var(--smna-accent); }}
    #seoulmna-yangdo-calculator .panel .panel-body {{ padding: 14px; overflow: hidden; }}
    #seoulmna-yangdo-calculator .avg-guide {{
      font-size: 16px;
      color: #0b4a79;
      background: #eef6ff;
      border: 1px solid #cfe4fa;
      border-radius: 10px;
      padding: 8px 10px;
      margin-bottom: 10px;
    }}
    #seoulmna-yangdo-calculator .input-row {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 2px;
      overflow: visible;
    }}
    #seoulmna-yangdo-calculator .field {{
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }}
    #seoulmna-yangdo-calculator .field.wide {{
      grid-column: 1 / -1;
    }}
    #seoulmna-yangdo-calculator .field.strong {{
      border: 1px solid #e6c7a8;
      background: #fff8f0;
      border-radius: 10px;
      padding: 8px;
    }}
    #seoulmna-yangdo-calculator label {{
      font-size: 16px;
      color: var(--smna-sub);
      font-weight: 600;
    }}
    #seoulmna-yangdo-calculator .field.strong label {{
      color: #7b4b1b;
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator input, #seoulmna-yangdo-calculator textarea, #seoulmna-yangdo-calculator select {{
      width: 100%;
      border: 1px solid #cdd9e5;
      border-radius: 10px;
      padding: 12px 14px;
      font-size: 17px;
      color: #0f172a;
      background: #fff;
      outline: none;
      line-height: 1.45;
      transition: border-color .16s ease, box-shadow .16s ease;
    }}
    #seoulmna-yangdo-calculator input:focus, #seoulmna-yangdo-calculator textarea:focus, #seoulmna-yangdo-calculator select:focus {{
      border-color: #4b7ca4;
      box-shadow: 0 0 0 3px rgba(0,55,100,.12);
    }}
    #seoulmna-yangdo-calculator select {{
      min-height: 52px;
      padding-top: 12px;
      padding-bottom: 12px;
      line-height: 1.45;
      appearance: auto;
      white-space: normal;
    }}
    #seoulmna-yangdo-calculator textarea {{ min-height: 84px; resize: vertical; }}
    #seoulmna-yangdo-calculator .checks {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 8px;
      padding-top: 8px;
    }}
    #seoulmna-yangdo-calculator .checks label {{
      display: flex;
      align-items: center;
      gap: 8px;
      color: #7b4b1b;
      font-size: 17px;
      border: 1px solid #e6c7a8;
      background: #fff8f0;
      border-radius: 8px;
      padding: 7px 10px;
      white-space: normal;
      line-height: 1.35;
      min-height: 44px;
      min-width: 0;
    }}
    #seoulmna-yangdo-calculator .checks input[type="checkbox"] {{
      width: 18px;
      height: 18px;
      margin: 0;
      flex: 0 0 auto;
    }}
    #seoulmna-yangdo-calculator .btn-row {{
      margin-top: 12px;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator button {{
      border: 0;
      border-radius: 10px;
      padding: 12px 15px;
      font-size: 20px;
      font-weight: 700;
      cursor: pointer;
      transition: .18s ease;
    }}
    #seoulmna-yangdo-calculator button:hover, #seoulmna-yangdo-calculator .cta-button:hover {{ transform: translateY(-1px); }}
    #seoulmna-yangdo-calculator .btn-primary {{ background: var(--smna-primary); color: #fff; }}
    #seoulmna-yangdo-calculator .btn-neutral {{ background: var(--smna-neutral); color: #0f172a; }}
    #seoulmna-yangdo-calculator .btn-accent {{ background: var(--smna-accent); color: #fff; }}
    #seoulmna-yangdo-calculator .result-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 8px;
    }}
    #seoulmna-yangdo-calculator .result-card {{
      background: #fff;
      border: 1px solid #d2dce8;
      border-radius: 11px;
      padding: 10px 12px;
    }}
    #seoulmna-yangdo-calculator .result-card .k {{
      display: block;
      color: var(--smna-sub);
      font-size: 15px;
      margin-bottom: 2px;
    }}
    #seoulmna-yangdo-calculator .result-card .v {{
      font-size: 33px;
      line-height: 1.25;
      font-weight: 800;
      color: var(--smna-primary);
    }}
    #seoulmna-yangdo-calculator .yoy-compare {{
      margin-top: 8px;
      border: 1px solid #d8e3ef;
      border-radius: 10px;
      padding: 9px 11px;
      background: #eef4fb;
      color: #173e64;
      font-size: 15px;
      line-height: 1.5;
      word-break: keep-all;
    }}
    #seoulmna-yangdo-calculator .yoy-compare strong {{
      font-weight: 800;
      color: #0f3356;
    }}
    #seoulmna-yangdo-calculator .yoy-compare.up strong {{ color: #0e4f7d; }}
    #seoulmna-yangdo-calculator .yoy-compare.down strong {{ color: #8a4a18; }}
    #seoulmna-yangdo-calculator .risk-note {{
      background: var(--smna-accent-soft);
      border: 1px solid var(--smna-accent-border);
      border-radius: 10px;
      padding: 10px 11px;
      font-size: 17px;
      color: #7d4a17;
      margin-top: 8px;
    }}
    #seoulmna-yangdo-calculator .small {{
      font-size: 14px;
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .consult-wrap {{
      margin-top: 12px;
      border: 1px solid #d8e3ee;
      background: linear-gradient(180deg, #f8fbff 0%, #eef4fa 100%);
      border-radius: 12px;
      padding: 10px;
    }}
    #seoulmna-yangdo-calculator .consult-title {{
      font-size: 20px;
      font-weight: 800;
      color: #0f3052;
      margin-bottom: 4px;
    }}
    #seoulmna-yangdo-calculator .consult-sub {{
      font-size: 17px;
      color: #4a5d72;
      margin-bottom: 8px;
    }}
    #seoulmna-yangdo-calculator .consult-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 8px;
    }}
    #seoulmna-yangdo-calculator .consult-grid .field.wide {{
      grid-column: 1 / -1;
    }}
    #seoulmna-yangdo-calculator details.consult-panel {{
      border: 1px solid #cdd9e6;
      background: #ffffff;
      border-radius: 10px;
      padding: 10px;
    }}
    #seoulmna-yangdo-calculator details.consult-panel > summary {{
      cursor: pointer;
      font-size: 22px;
      font-weight: 800;
      color: #163b5f;
      list-style: none;
      outline: none;
      margin: 0;
    }}
    #seoulmna-yangdo-calculator details.consult-panel > summary::marker {{
      display: none;
    }}
    #seoulmna-yangdo-calculator details.consult-panel > summary::-webkit-details-marker {{
      display: none;
    }}
    #seoulmna-yangdo-calculator .consult-panel-body {{
      margin-top: 8px;
    }}
    #seoulmna-yangdo-calculator .consult-actions {{
      display: flex;
      gap: 8px;
      margin-top: 8px;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator #consult-summary {{
      min-height: 96px;
      font-size: 14px;
      line-height: 1.45;
      background: #fff;
    }}
    #seoulmna-yangdo-calculator details.consult-details {{
      margin-top: 8px;
      border: 1px solid #d6e0ec;
      border-radius: 10px;
      background: #ffffff;
      padding: 8px;
    }}
    #seoulmna-yangdo-calculator details.consult-details > summary {{
      cursor: pointer;
      font-size: 14px;
      color: #284a6b;
      font-weight: 700;
      list-style: none;
      outline: none;
    }}
    #seoulmna-yangdo-calculator table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      font-size: 14px;
      margin-top: 8px;
      background: #fff;
      border: 1px solid #d5deea;
      border-radius: 10px;
      overflow: hidden;
    }}
    #seoulmna-yangdo-calculator thead th {{
      background: #ecf2f8;
      color: #0f172a;
      font-size: 13px;
      text-align: left;
      padding: 8px;
      border-bottom: 1px solid #d5deea;
    }}
    #seoulmna-yangdo-calculator tbody td {{
      padding: 8px;
      border-bottom: 1px solid #ecf1f6;
      color: #1e293b;
      word-break: break-word;
      white-space: normal;
    }}
    #seoulmna-yangdo-calculator tbody tr:last-child td {{ border-bottom: 0; }}
    #seoulmna-yangdo-calculator a {{ color: var(--smna-primary); text-decoration: none; }}
    #seoulmna-yangdo-calculator .foot {{
      margin-top: 10px;
      font-size: 13px;
      color: #64748b;
    }}
    #seoulmna-yangdo-calculator .action-steps {{
      margin-top: 10px;
      border: 1px solid #d7e0ec;
      border-radius: 11px;
      background: #f3f7fb;
      padding: 11px 12px;
    }}
    #seoulmna-yangdo-calculator .action-steps .title {{
      color: #0f3052;
      font-weight: 800;
      font-size: 17px;
      margin-bottom: 6px;
    }}
    #seoulmna-yangdo-calculator .action-steps ol {{
      margin: 0;
      padding-left: 18px;
      color: #1f344a;
      font-size: 15px;
    }}
    #seoulmna-yangdo-calculator .action-steps li {{ margin: 4px 0; }}
    #seoulmna-yangdo-calculator .input-guide {{
      font-size: 16px;
      font-weight: 800;
      color: #183b5d;
      margin: 0 0 10px 0;
      line-height: 1.5;
      background: #edf4fb;
      border: 1px solid #cee0f0;
      border-radius: 10px;
      padding: 8px 10px;
    }}
    #seoulmna-yangdo-calculator .info-boxes {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }}
    #seoulmna-yangdo-calculator .info-box {{
      border: 1px solid #d6e2ee;
      border-radius: 11px;
      background: #f6f9fd;
      padding: 10px 11px;
    }}
    #seoulmna-yangdo-calculator .info-box .k {{
      font-size: 14px;
      font-weight: 800;
      color: #1a436a;
      margin-bottom: 5px;
    }}
    #seoulmna-yangdo-calculator .info-box .v {{
      font-size: 16px;
      line-height: 1.45;
      color: #1d334a;
      word-break: keep-all;
    }}
    #seoulmna-yangdo-calculator .lead-capture {{
      margin-top: 10px;
      border: 1px solid #d8e1eb;
      border-radius: 11px;
      background: #f6f9fd;
      padding: 10px 11px;
      display: none;
    }}
    #seoulmna-yangdo-calculator .lead-capture .msg {{
      font-size: 16px;
      font-weight: 700;
      line-height: 1.45;
      color: #153b61;
      margin-bottom: 8px;
      word-break: keep-all;
    }}
    #seoulmna-yangdo-calculator .lead-capture .actions {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator .lead-capture .help {{
      margin-top: 6px;
      font-size: 13px;
      color: #4f647c;
    }}
    #seoulmna-yangdo-calculator .compliance-note {{
      margin-top: 10px;
      padding: 10px 11px;
      border: 1px solid #d7e0ec;
      border-radius: 10px;
      background: #f4f8fc;
      color: #2b445e;
      font-size: 14px;
      line-height: 1.55;
    }}
    #seoulmna-yangdo-calculator .consent-check {{
      display: flex;
      align-items: flex-start;
      gap: 8px;
      margin-top: 8px;
      font-size: 14px;
      font-weight: 700;
      color: #1d3550;
    }}
    #seoulmna-yangdo-calculator .consent-check input {{
      width: 18px;
      height: 18px;
      margin-top: 2px;
      flex: 0 0 auto;
    }}
    @media (max-width: 1280px) {{
      #seoulmna-yangdo-calculator .smna-grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 980px) {{
      #seoulmna-yangdo-calculator .smna-meta {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      #seoulmna-yangdo-calculator .smna-grid {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .input-row {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .field.wide {{ grid-column: auto; }}
      #seoulmna-yangdo-calculator .result-grid {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .info-boxes {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .consult-grid {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .checks {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator h2 {{ font-size: 33px; }}
      #seoulmna-yangdo-calculator .impact .cta-text {{ font-size: 17px; }}
      #seoulmna-yangdo-calculator .cta-button {{ font-size: 18px; }}
      #seoulmna-yangdo-calculator .panel h3 {{ font-size: 26px; }}
    }}
  </style>

  <div class="smna-header">
    <div class="smna-brand-row">
      <div class="smna-brand" style="color:#e8f3ff;font-weight:800;">서울건설정보 · SEOUL CONSTRUCTION INFO</div>
      <div class="smna-mode">{'실시간 고객 화면' if mode == "customer" else '내부 검수 화면(비공개)'}</div>
    </div>
    <div class="smna-badge">전국 최초</div>
    <h2 style="color:#f8fbff !important;">{escape(title)}</h2>
    <div class="smna-subtitle" style="color:#eaf4ff;">{"건설업 전 면허 대상 양도양수·분할합병 거래 범위를 먼저 계산하고, 즉시 1:1 상담으로 연결합니다." if mode == "customer" else "내부 검수 모드: 서울건설정보 매물번호 + now UID 대조 데이터로 정밀 산정합니다."}</div>
    <div class="smna-ratio"><div></div><div></div><div></div></div>
  </div>

  <div class="smna-body">
    <div class="smna-meta">
      <div class="item"><span class="label">전체 매물</span><strong class="value" id="meta-all">-</strong></div>
      <div class="item"><span class="label">가격학습 건수</span><strong class="value" id="meta-train">-</strong></div>
      <div class="item"><span class="label">{escape(meta_mid_label)}</span><strong class="value" id="meta-mid">-</strong></div>
      <div class="item"><span class="label">데이터 갱신시각</span><strong class="value" id="meta-updated" style="font-size:17px">-</strong></div>
    </div>
    <div class="impact cta-row">
      <span class="cta-text">건설업 전 면허의 예상 양도가 범위를 1분 안에 계산하고, 결과 기반 상담까지 바로 진행하세요.</span>
      <span class="cta-actions">
        <button type="button" class="cta-button chat" id="btn-openchat-top">대표 행정사 1:1 직접 상담</button>
        <a id="btn-call-top" class="cta-button call" href="tel:01099268661">010-9926-8661</a>
      </span>
    </div>
    <div class="impact">AI가 유사 매물 + 핵심 입력값을 종합 계산해 예상 양도가 범위를 제시합니다.</div>
    <div class="info-boxes">
      <div class="info-box">
        <div class="k">가격 영향 큰 항목</div>
        <div class="v">공제조합 잔액, 자본금, 기술자/사무실 충족, 이익잉여금은 결과에 크게 반영됩니다.</div>
      </div>
      <div class="info-box">
        <div class="k">데이터 상태</div>
        <div class="v" id="data-quality-box">가격학습 건수와 갱신시각은 상단 메타에서 확인할 수 있습니다.</div>
      </div>
      <div class="info-box">
        <div class="k">추천 입력 순서</div>
        <div class="v">면허/업종 → 공제조합 잔액 → 실적 입력모드(연도별/3년/5년) → 시평 순으로 입력하면 오차 범위가 줄어듭니다.</div>
      </div>
    </div>

    <div class="smna-grid">
      <div class="panel">
        <h3>1단계: 거래 정보 입력</h3>
        <div class="panel-body">
          <div class="input-guide">입력하세요: 해당 면허, 실적(연도별/3년/5년 선택), 시평, 공제조합 잔액 등 핵심 정보를 채울수록 결과 오차 범위가 줄어듭니다.</div>
          <div class="avg-guide" id="avg-guide">평균 지표를 불러오는 중...</div>
          <div class="input-row">
            <div class="field wide">
              <label for="in-license">면허/업종 (권장)</label>
              <textarea id="in-license" maxlength="120" placeholder="예: 토목, 상하, 철콘, 실내건축 (축약 입력 가능)"></textarea>
            </div>
            <div class="field"><label for="in-specialty">시평(억)</label><input id="in-specialty" type="number" step="0.1" /></div>
            <div class="field wide">
              <label for="in-sales-input-mode">실적 입력 방식</label>
              <select id="in-sales-input-mode">
                <option value="yearly">연도별 입력 (2023~2025)</option>
                <option value="sales3">최근 3년 실적 합계(억)</option>
                <option value="sales5">최근 5년 실적 합계(억)</option>
              </select>
            </div>
            <div class="field"><label for="in-y23">2023 매출(억)</label><input id="in-y23" type="number" step="0.1" /></div>
            <div class="field"><label for="in-y24">2024 매출(억)</label><input id="in-y24" type="number" step="0.1" /></div>
            <div class="field"><label for="in-y25">2025 매출(억)</label><input id="in-y25" type="number" step="0.1" /></div>
            <div class="field"><label for="in-sales3-total">최근 3년 실적 합계(억)</label><input id="in-sales3-total" type="number" step="0.1" /></div>
            <div class="field"><label for="in-sales5-total">최근 5년 실적 합계(억)</label><input id="in-sales5-total" type="number" step="0.1" /></div>
            <div class="field strong"><label for="in-balance">공제조합 잔액(억)</label><input id="in-balance" type="number" step="0.01" /></div>
            <div class="field wide"><label>입력 예시</label><div class="avg-guide">공제조합 잔액은 기본 ‘억’ 단위 입력입니다. 예: 6,000만원 → <strong>0.6</strong>, 1억 2,000만원 → <strong>1.2</strong>, 9,500만원 → <strong>0.95</strong>. 단위 착오가 의심되면 AI가 보정합니다.</div></div>
            <div class="field strong"><label for="in-capital">자본금(억, 선택)</label><input id="in-capital" type="number" step="0.1" /></div>
            <div class="field strong"><label for="in-surplus">이익잉여금(억)</label><input id="in-surplus" type="number" step="0.1" /></div>
            <div class="field"><label for="in-license-year">면허년도(선택)</label><input id="in-license-year" type="number" min="1900" max="2099" /></div>
            <div class="field wide">
              <label for="in-debt-level">부채비율 (평균 대비)</label>
              <select id="in-debt-level">
                <option value="auto">선택 안함</option>
                <option value="below">평균 이하(양호)</option>
                <option value="above">평균 이상(주의)</option>
              </select>
            </div>
            <div class="field wide">
              <label for="in-liq-level">유동비율 (평균 대비)</label>
              <select id="in-liq-level">
                <option value="auto">선택 안함</option>
                <option value="above">평균 이상(양호)</option>
                <option value="below">평균 이하(주의)</option>
              </select>
            </div>
            <div class="field">
              <label for="in-company-type">회사형태</label>
              <select id="in-company-type">
                <option value="">선택 안함</option>
                <option value="주식회사">주식회사</option>
                <option value="유한회사">유한회사</option>
                <option value="개인">개인사업자</option>
                <option value="기타">기타</option>
              </select>
            </div>
            <div class="field">
              <label for="in-credit-level">외부신용등급</label>
              <select id="in-credit-level">
                <option value="">선택 안함</option>
                <option value="high">우수 (A 등급대)</option>
                <option value="mid">보통 (B 등급대)</option>
                <option value="low">확인 필요 (C등급/연체 이력)</option>
              </select>
            </div>
            <div class="field wide">
              <label for="in-admin-history">행정처분 이력</label>
              <select id="in-admin-history">
                <option value="">선택 안함</option>
                <option value="none">없음</option>
                <option value="has">있음</option>
              </select>
            </div>
            <div class="field wide">
              <label>필수 기준 체크</label>
              <div class="checks">
                <label><input id="ok-capital" type="checkbox" checked /> 자본금 충족</label>
                <label><input id="ok-engineer" type="checkbox" checked /> 기술자 충족</label>
                <label><input id="ok-office" type="checkbox" checked /> 사무실 충족</label>
              </div>
            </div>
          </div>
          <div class="btn-row">
            <button type="button" class="btn-primary" id="btn-estimate">AI 예상 양도가 계산</button>
            <button type="button" class="btn-neutral" id="btn-reset">입력 초기화</button>
          </div>
          <div class="small" style="margin-top:8px">
            데이터 기준: 서울건설정보 매물 DB 전체 대조 · 유사도 기반 정밀 계산.
          </div>
        </div>
      </div>

      <div class="panel result">
        <h3>2단계: AI 산정 결과 확인</h3>
        <div class="panel-body">
          <div class="result-grid">
            <div class="result-card"><span class="k">예상 기준가</span><strong class="v" id="out-center">-</strong></div>
            <div class="result-card"><span class="k">예상 오차 범위</span><strong class="v" id="out-range">-</strong></div>
            <div class="result-card"><span class="k">예측 신뢰도</span><strong class="v" id="out-confidence">-</strong></div>
            <div class="result-card"><span class="k">근거 매물 수</span><strong class="v" id="out-neighbors">-</strong></div>
          </div>
          <div class="yoy-compare" id="out-yoy-compare">동일 조건 전년 대비 비교는 계산 후 표시됩니다.</div>
          <div id="risk-note" class="risk-note">AI 산정 전: 면허·시평·실적 입력방식(연도별/3년/5년)·공제조합 잔액을 입력하면 결과 정확도가 올라갑니다.</div>
          <div class="lead-capture" id="hot-match-cta">
            <div class="msg" id="hot-match-msg">현재 보유하신 면허와 매칭률이 90% 이상인 대기 매수자가 3명 있습니다. 상세 리포트를 카카오톡으로 받으시겠습니까?</div>
            <div class="actions">
              <button type="button" class="btn-accent" id="btn-hot-match">상세 리포트 카카오톡으로 받기</button>
              <button type="button" class="btn-neutral" id="btn-hot-match-copy">연락처 입력 후 요약 복사</button>
            </div>
            <div class="help">성함/연락처를 입력하면 상담 문의 시트에 자동 저장되어 빠르게 회신받을 수 있습니다.</div>
          </div>
          <div class="btn-row" style="margin-top:10px">
            <button type="button" class="btn-accent" id="btn-openchat-result">결과를 오픈채팅으로 전달</button>
            <button type="button" class="btn-neutral" id="btn-email-result">결과를 이메일로 전달</button>
          </div>
          <div class="action-steps">
            <div class="title">추천 액션 3단계</div>
            <ol id="recommend-actions">
              <li>면허/업종 + 공제조합 잔액을 먼저 입력해 오차 범위를 줄입니다.</li>
              <li>AI 계산 결과의 신뢰지수(%)와 근거 매물 수를 확인합니다.</li>
              <li>상담 접수하기로 현재 결과를 즉시 전달합니다.</li>
            </ol>
          </div>
          <div class="consult-wrap">
            <details class="consult-panel">
              <summary>전문가 상담 요청 열기</summary>
              <div class="consult-panel-body">
                <div class="consult-title">전문가 상담 요청</div>
                <div class="consult-sub">산정 결과를 첨부해 바로 상담 요청할 수 있습니다. 대표 행정사 상담 / <strong id="contact-phone-display">010-9926-8661</strong></div>
                <div class="consult-grid">
                  <div class="field"><label for="consult-name">성함</label><input id="consult-name" type="text" maxlength="40" placeholder="홍길동" /></div>
                  <div class="field"><label for="consult-phone">연락처</label><input id="consult-phone" type="text" maxlength="20" placeholder="010-1234-5678" /></div>
                  <div class="field wide"><label for="consult-email">이메일</label><input id="consult-email" type="email" maxlength="120" placeholder="name@example.com" /></div>
                </div>
                <div class="field wide"><label for="consult-note">상담 메모(선택)</label><textarea id="consult-note" maxlength="500" placeholder="추가 요청 사항"></textarea></div>
                <details class="consult-details">
                  <summary>전송 요약 확인</summary>
                  <div class="field wide" style="margin-top:8px"><label for="consult-summary">전송 요약(자동 생성)</label><textarea id="consult-summary" readonly></textarea></div>
                </details>
                <div class="consult-actions">
                  <button type="button" class="btn-primary" id="btn-submit-consult">상담 요청 보내기</button>
                  <button type="button" class="btn-accent" id="btn-mail-consult">메일로 문의</button>
                  <button type="button" class="btn-accent" id="btn-openchat-consult">오픈채팅 문의</button>
                  <button type="button" class="btn-neutral" id="btn-copy-consult">요약 복사</button>
                </div>
                <div class="compliance-note">
                  <strong>개인정보 수집·이용 안내 (행정사사무소하랑 · 서울건설정보)</strong><br>
                  상담 요청 시 입력한 성함·연락처·이메일·상담메모는 상담 회신 및 계약 진행 안내 목적에 한해 사용되며, 관련 법령에 따라 안전하게 보관·관리됩니다.
                </div>
                <label class="consent-check"><input id="consult-consent" type="checkbox" /> 개인정보 수집·이용 안내를 확인했으며 상담 목적 활용에 동의합니다.</label>
                <div class="small" style="margin-top:6px">수신: <strong id="consult-target-email">seoulmna@gmail.com</strong></div>
              </div>
            </details>
          </div>
          <table>
            <thead id="neighbor-head"></thead>
            <tbody id="neighbor-body"><tr><td colspan="5" class="small">아직 산정 결과가 없습니다.</td></tr></tbody>
          </table>
          <div class="foot">주의: 본 산정치는 참고용입니다. 법정/계약 효력은 없으며 최종 거래가는 실사 결과, 채무 조건, 협의사항으로 달라질 수 있습니다.</div>
        </div>
      </div>
    </div>
  </div>

  <script nowprocket data-nowprocket>
    // nowprocket
    // DOMContentLoaded
    (function() {{
      const datasetRaw = {dataset_json};
      const meta = {meta_json};
      const viewMode = {mode_json};
      const canonicalByKey = {canonical_map_json};
      const genericKeys = new Set({generic_keys_json});
      const consultEndpointRaw = {consult_endpoint_json};
      const usageEndpointRaw = {usage_endpoint_json};
      const estimateEndpointRaw = {estimate_endpoint_json};
      const consultPhone = {contact_phone_json};
      const consultOpenchatUrl = {openchat_url_json};
      const isLoopbackEndpoint = (src) => /^(?:https?:\\/\\/)?(?:localhost|127\\.0\\.0\\.1|::1)(?::\\d+)?(?:\\/|$)/i.test(String(src || "").trim());
      const consultEndpoint = (() => {{
        const src = String(consultEndpointRaw || "").trim();
        if (!src || isLoopbackEndpoint(src)) return "";
        return src;
      }})();
      const usageEndpoint = (() => {{
        const src = String(usageEndpointRaw || "").trim();
        if (src && !isLoopbackEndpoint(src)) return src;
        if (!consultEndpoint) return "";
        return consultEndpoint.replace(/\\/consult\\/?$/i, "/usage");
      }})();
      const estimateEndpoint = (() => {{
        const src = String(estimateEndpointRaw || "").trim();
        if (!src || isLoopbackEndpoint(src)) return "";
        return src;
      }})();
      const siteMna = "{site_url.rstrip("/") if site_url else ""}/mna";
      const consultEmail = "seoulmna@gmail.com";
      const consultSubjectPrefix = viewMode === "owner" ? "[내부검수] 서울건설정보 AI 산정 상담 요청" : "[고객] 서울건설정보 AI 산정 상담 요청";
      let lastEstimate = null;
      let isEstimating = false;
      let lastEstimateClickAt = 0;
      let isSubmittingConsult = false;
      const draftStorageKey = `smna_yangdo_draft_${{viewMode || "customer"}}`;
      const urlParams = new URLSearchParams(String(location.search || ""));
      const embedFromCo = (urlParams.get("from") || "").toLowerCase() === "co";
      const hideEmbedChrome = () => {{
        try {{
          const hideSelectors = [
            "#masthead",
            "header",
            ".site-header",
            ".site-main-header-wrap",
            ".ast-main-header-wrap",
            ".main-header-bar-wrap",
            ".ast-mobile-header-wrap",
            ".main-header-bar",
            ".ast-primary-header-bar",
            ".site-logo-img",
            ".site-branding",
            ".ast-site-identity",
            ".ast-builder-layout-element",
            ".custom-logo-link",
            ".custom-logo",
            ".entry-header",
            ".entry-title",
            ".wp-block-post-title",
            ".ast-breadcrumbs",
            "#colophon",
            ".site-below-footer-wrap",
          ];
          document.querySelectorAll(hideSelectors.join(",")).forEach((el) => {{
            if (!el) return;
            el.style.setProperty("display", "none", "important");
            el.style.setProperty("visibility", "hidden", "important");
            el.style.setProperty("height", "0", "important");
            el.style.setProperty("min-height", "0", "important");
            el.style.setProperty("margin", "0", "important");
            el.style.setProperty("padding", "0", "important");
          }});
        }} catch (_e) {{}}
      }};
      if (embedFromCo) {{
        try {{
          document.documentElement.classList.add("smna-embed-co");
          document.body && document.body.classList.add("smna-embed-co");
          hideEmbedChrome();
          const mo = new MutationObserver(() => hideEmbedChrome());
          mo.observe(document.documentElement || document.body, {{ childList: true, subtree: true }});
        }} catch (_e) {{}}
      }}
      const requestWithTimeout = async (url, options = {{}}, timeoutMs = 9000) => {{
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort("timeout"), timeoutMs);
        try {{
          const merged = Object.assign({{}}, options || {{}}, {{ signal: controller.signal }});
          return await fetch(url, merged);
        }} finally {{
          clearTimeout(timer);
        }}
      }};
      const decodeDatasetRow = (row) => {{
        if (!row) return null;
        if (!Array.isArray(row)) return row;
        return {{
          now_uid: String(row[0] || ""),
          seoul_no: Number(row[1] || 0),
          license_text: String(row[2] || ""),
          tokens: Array.isArray(row[3]) ? row[3] : [],
          license_year: row[4],
          specialty: row[5],
          y23: row[6],
          y24: row[7],
          y25: row[8],
          sales3_eok: row[9],
          sales5_eok: row[10],
          capital_eok: row[11],
          surplus_eok: row[12],
          debt_ratio: row[13],
          liq_ratio: row[14],
          company_type: String(row[15] || ""),
          balance_eok: row[16],
          price_eok: row[17],
          display_low_eok: row[18],
          display_high_eok: row[19],
          url: String(row[20] || ""),
        }};
      }};
      const dataset = Array.isArray(datasetRaw)
        ? datasetRaw.map(decodeDatasetRow).filter((x) => !!x)
        : [];

      const $ = (id) => document.getElementById(id);
      const num = (v) => {{
        if (v === null || v === undefined) return null;
        const txt = String(v).replace(/,/g, "").trim();
        if (!txt) return null;
        const m = txt.match(/-?\\d+(?:\\.\\d+)?/);
        if (!m) return null;
        const n = Number(m[0]);
        return Number.isFinite(n) ? n : null;
      }};
      const fmtEok = (v) => {{
        if (v === null || v === undefined || !Number.isFinite(v)) return "-";
        return (Math.round(v * 100) / 100).toFixed(2).replace(/\\.00$/, "").replace(/(\\.\\d)0$/, "$1") + "억";
      }};
      const displayRangeStep = (highValue) => {{
        const h = Number(highValue) || 0;
        if (h >= 20) return 1.0;
        if (h >= 10) return 0.5;
        if (h >= 3) return 0.2;
        return 0.1;
      }};
      const buildDisplayRange = (lowValue, highValue) => {{
        const lowNum = Number(lowValue);
        const highNum = Number(highValue);
        if (!Number.isFinite(lowNum) || !Number.isFinite(highNum)) {{
          return {{ low: null, high: null, text: "-" }};
        }}
        const safeLow = Math.max(0.05, lowNum);
        const safeHigh = Math.max(safeLow, highNum);
        const lowered = Math.max(0.05, safeLow - displayRangeStep(safeHigh));
        return {{
          low: lowered,
          high: safeHigh,
          text: `${{fmtEok(lowered)}}~${{fmtEok(safeHigh)}}`,
        }};
      }};
      const compact = (v) => String(v || "").replace(/\\s+/g, " ").trim();
      const bounded = (v, minV, maxV) => {{
        if (!Number.isFinite(v)) return v;
        return Math.max(minV, Math.min(maxV, Number(v)));
      }};
      const escapeHtml = (v) => String(v === null || v === undefined ? "" : v)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
      const safeUrl = (value, fallback) => {{
        const fb = compact(fallback || siteMna || "https://seoulmna.co.kr/mna");
        const src = compact(value);
        if (!src) return fb;
        try {{
          const parsed = new URL(src, window.location.href);
          const proto = String(parsed.protocol || "").toLowerCase();
          if (proto !== "http:" && proto !== "https:") return fb;
          return parsed.href;
        }} catch (_e) {{
          return fb;
        }}
      }};
      const normalizeLicenseKey = (raw) => {{
        let t = compact(raw).replace(/\\s+/g, "");
        t = t.replace(/\\(주\\)|주식회사/g, "");
        t = t.replace(/(업종|면허)$/g, "");
        t = t.replace(/(공사업|건설업|공사|사업)$/g, "");
        return t;
      }};
      const aliasMap = {{
        "상하": "상하수도설비",
        "상하수도": "상하수도설비",
        "의장": "실내건축",
        "실내": "실내건축",
        "통신": "정보통신",
        "기계": "기계설비",
        "토목건축": "토건",
        "토목건축공사업": "토건",
        "철콘": "철근콘크리트",
        "미장방수": "미장방수조적",
        "단종토목": "토목",
        "토건": "토목건축",
        "금속": "금속구조물창호온실",
        "비계": "비계구조물해체",
        "석면": "석면해체제거",
        "습식": "습식방수석공",
      }};
      const knownTokenSet = (() => {{
        const out = new Set();
        Object.keys(canonicalByKey || {{}}).forEach((k) => {{
          const n = normalizeLicenseKey(k);
          if (n) out.add(n);
        }});
        Object.values(canonicalByKey || {{}}).forEach((v) => {{
          const n = normalizeLicenseKey(v);
          if (n) out.add(n);
        }});
        Object.values(aliasMap).forEach((v) => {{
          const n = normalizeLicenseKey(v);
          if (n) out.add(n);
        }});
        dataset.forEach((row) => {{
          const tokens = Array.isArray(row.tokens) ? row.tokens : [];
          tokens.forEach((t) => {{
            const n = normalizeLicenseKey(t);
            if (n) out.add(n);
          }});
        }});
        return out;
      }})();
      const knownTokens = Array.from(knownTokenSet);
      const charBigrams = (s) => {{
        const src = normalizeLicenseKey(s);
        const out = new Set();
        if (!src) return out;
        if (src.length < 2) {{
          out.add(src);
          return out;
        }}
        for (let i = 0; i < src.length - 1; i += 1) {{
          out.add(src.slice(i, i + 2));
        }}
        return out;
      }};
      const bigramJaccard = (a, b) => {{
        const aa = charBigrams(a);
        const bb = charBigrams(b);
        if (!aa.size || !bb.size) return 0;
        let inter = 0;
        aa.forEach((x) => {{ if (bb.has(x)) inter += 1; }});
        const union = aa.size + bb.size - inter;
        return union > 0 ? inter / union : 0;
      }};
      const findClosestKnownToken = (rawKey) => {{
        const key = normalizeLicenseKey(rawKey);
        if (!key || key.length < 2) return "";
        let best = "";
        let bestScore = 0;
        for (let i = 0; i < knownTokens.length; i += 1) {{
          const cand = knownTokens[i];
          if (!cand) continue;
          let score = 0;
          if (cand === key) {{
            score = 1;
          }} else if (cand.indexOf(key) >= 0 || key.indexOf(cand) >= 0) {{
            score = 0.88 - (Math.abs(cand.length - key.length) * 0.02);
          }} else {{
            score = bigramJaccard(key, cand);
          }}
          if (score > bestScore) {{
            bestScore = score;
            best = cand;
          }}
        }}
        return bestScore >= 0.44 ? best : "";
      }};
      const canonicalizeToken = (raw) => {{
        let key = normalizeLicenseKey(raw);
        if (!key) return "";
        if (aliasMap[key]) {{
          key = normalizeLicenseKey(aliasMap[key]);
        }}
        let mapped = canonicalByKey[key] || raw;
        if (mapped === raw) {{
          const fuzzy = findClosestKnownToken(key);
          if (fuzzy) mapped = canonicalByKey[fuzzy] || fuzzy;
        }}
        const out = normalizeLicenseKey(mapped || key);
        if (!out || genericKeys.has(out) || out.length < 2) return "";
        return out;
      }};
      const licenseTokenSet = (raw) => {{
        const out = new Set();
        const txt = String(raw || "").replace(/<br\\s*\\/?>/gi, "\\n");
        txt.split(/\\n/).forEach((line) => {{
          String(line || "").split(/[\\/,|·ㆍ+&\\s]+/).forEach((piece) => {{
            const can = canonicalizeToken(piece);
            if (can) out.add(can);
          }});
        }});
        return out;
      }};
      const isSeparateBalanceGroupToken = (raw) => {{
        const t = normalizeLicenseKey(raw);
        if (!t) return false;
        return (
          t.indexOf("전기") >= 0
          || t.indexOf("정보통신") >= 0
          || t.indexOf("통신") >= 0
          || t.indexOf("소방") >= 0
        );
      }};
      const isSeparateBalanceGroupTarget = (target) => {{
        const tokens = (target && target.tokens instanceof Set) ? target.tokens : new Set();
        if (tokens.size) {{
          for (const token of tokens) {{
            if (isSeparateBalanceGroupToken(token)) return true;
          }}
        }}
        const raw = target && (
          target.license_raw
          || target.raw_license_key
          || target.license_text
          || ""
        );
        return isSeparateBalanceGroupToken(raw);
      }};
      const jaccard = (a, b) => {{
        if (!a.size || !b.size) return 0;
        let inter = 0;
        a.forEach((x) => {{ if (b.has(x)) inter += 1; }});
        const union = a.size + b.size - inter;
        return union > 0 ? inter / union : 0;
      }};
      const relativeCloseness = (left, right) => {{
        const leftMissing = (left === null || left === undefined || !Number.isFinite(Number(left)));
        const rightMissing = (right === null || right === undefined || !Number.isFinite(Number(right)));
        if (leftMissing && rightMissing) return 0;
        if (leftMissing || rightMissing) return 0.08;
        const denom = Math.max(Math.abs(left), Math.abs(right), 1.0);
        const rel = Math.abs(left - right) / denom;
        return Math.max(0, 1 - Math.min(rel, 1));
      }};
      const yearlySeries = (obj) => {{
        const vals = [num(obj && obj.y23), num(obj && obj.y24), num(obj && obj.y25)]
          .map((v) => (Number.isFinite(v) ? Math.max(0, v) : null));
        let sum = 0;
        let count = 0;
        vals.forEach((v) => {{
          if (!Number.isFinite(v)) return;
          sum += v;
          count += 1;
        }});
        return {{ vals, sum, count }};
      }};
      const yearlyShapeSimilarity = (target, cand) => {{
        const t = yearlySeries(target);
        const c = yearlySeries(cand);
        if (t.count < 2 || c.count < 2 || t.sum <= 0 || c.sum <= 0) return 0.5;
        const w = [0.34, 0.33, 0.33];
        let wSum = 0;
        let diff = 0;
        for (let i = 0; i < 3; i += 1) {{
          const tv = t.vals[i];
          const cv = c.vals[i];
          if (!Number.isFinite(tv) || !Number.isFinite(cv)) continue;
          const tw = w[i];
          const tr = tv / Math.max(0.01, t.sum);
          const cr = cv / Math.max(0.01, c.sum);
          diff += Math.abs(tr - cr) * tw;
          wSum += tw;
        }}
        if (wSum <= 0.2) return 0.5;
        const norm = diff / wSum;
        return clamp(1 - Math.min(1, norm / 0.9), 0, 1);
      }};
      const positiveRatio = (left, right) => {{
        const l = num(left);
        const r = num(right);
        if (!Number.isFinite(l) || !Number.isFinite(r) || r <= 0) return null;
        const ratio = l / r;
        return Number.isFinite(ratio) && ratio > 0 ? ratio : null;
      }};
      const weightedQuantile = (values, weights, q) => {{
        const arr = [];
        for (let i = 0; i < values.length; i += 1) {{
          const v = Number(values[i]);
          const w = Number(weights[i]);
          if (!Number.isFinite(v) || !Number.isFinite(w) || w <= 0) continue;
          arr.push([v, w]);
        }}
        if (!arr.length) return null;
        arr.sort((x, y) => x[0] - y[0]);
        const total = arr.reduce((acc, cur) => acc + cur[1], 0);
        if (total <= 0) return null;
        const threshold = Math.max(0, Math.min(1, Number(q))) * total;
        let run = 0;
        for (const [val, wt] of arr) {{
          run += wt;
          if (run >= threshold) return val;
        }}
        return arr[arr.length - 1][0];
      }};
      const weightedMean = (values, weights) => {{
        let sumW = 0;
        let sumV = 0;
        for (let i = 0; i < values.length; i += 1) {{
          const v = Number(values[i]);
          const w = Number(weights[i]);
          if (!Number.isFinite(v) || !Number.isFinite(w) || w <= 0) continue;
          sumW += w;
          sumV += (v * w);
        }}
        if (sumW <= 0) return null;
        return sumV / sumW;
      }};

      const clamp = (v, minV, maxV) => {{
        if (!Number.isFinite(v)) return minV;
        return Math.max(minV, Math.min(maxV, v));
      }};

      const buildYoyInsight = (target, center, neighbors) => {{
        if (!Number.isFinite(center) || center <= 0) return null;
        const now = new Date();
        const currentYear = Number(now.getFullYear()) || 0;
        const previousYear = currentYear > 0 ? currentYear - 1 : 0;
        const trendVals = [];
        const trendWts = [];
        const basisParts = [];

        const pushTrend = (val, wt, basisText) => {{
          if (!Number.isFinite(val)) return;
          trendVals.push(clamp(Number(val), -0.85, 0.85));
          trendWts.push(Math.max(0.1, Number.isFinite(wt) ? Number(wt) : 1));
          if (basisText) basisParts.push(String(basisText));
        }};

        if (Number.isFinite(target.y24) && Number.isFinite(target.y25) && Math.abs(Number(target.y24)) > 0.1) {{
          const g = (Number(target.y25) - Number(target.y24)) / Math.max(Math.abs(Number(target.y24)), 0.1);
          const gAbs = Math.abs(g);
          if (gAbs >= 0.005) {{
            const targetWt = gAbs < 0.03 ? 1.0 : 2.4;
            pushTrend(g, targetWt, "입력 실적(2024→2025)");
          }}
        }} else if (Number.isFinite(target.y23) && Number.isFinite(target.y24) && Math.abs(Number(target.y23)) > 0.1) {{
          const g = (Number(target.y24) - Number(target.y23)) / Math.max(Math.abs(Number(target.y23)), 0.1);
          const gAbs = Math.abs(g);
          if (gAbs >= 0.005) {{
            const targetWt = gAbs < 0.03 ? 0.9 : 1.8;
            pushTrend(g, targetWt, "입력 실적(2023→2024)");
          }}
        }}

        const nearRows = Array.isArray(neighbors) ? neighbors.slice(0, 8) : [];
        nearRows.forEach(([sim, rec]) => {{
          const s23 = num(rec && rec.y23);
          const s24 = num(rec && rec.y24);
          const s25 = num(rec && rec.y25);
          if (Number.isFinite(s24) && Number.isFinite(s25) && Math.abs(s24) > 0.1) {{
            const g = (s25 - s24) / Math.max(Math.abs(s24), 0.1);
            const wt = Math.max(0.35, (Number(sim) || 0) / 42.0);
            pushTrend(g, wt, "업종·실적 유사군");
          }} else if (Number.isFinite(s23) && Number.isFinite(s24) && Math.abs(s23) > 0.1) {{
            const g = (s24 - s23) / Math.max(Math.abs(s23), 0.1);
            const wt = Math.max(0.30, (Number(sim) || 0) / 52.0);
            pushTrend(g, wt, "업종·실적 유사군");
          }}
        }});

        if (!trendVals.length) return null;
        const trendMid = weightedQuantile(trendVals, trendWts, 0.5);
        const trendAvg = weightedMean(trendVals, trendWts);
        const trend = Number.isFinite(trendMid) && Number.isFinite(trendAvg)
          ? ((trendMid * 0.6) + (trendAvg * 0.4))
          : (Number.isFinite(trendMid) ? trendMid : trendAvg);
        if (!Number.isFinite(trend)) return null;

        const elasticity = 0.28;
        let ratio = 1 + (clamp(Number(trend), -0.48, 0.48) * elasticity);
        ratio = clamp(ratio, 0.72, 1.28);
        const prevCenter = center / ratio;
        if (!Number.isFinite(prevCenter) || prevCenter <= 0) return null;
        const changePct = ((center / prevCenter) - 1) * 100;
        const basis = basisParts.length ? Array.from(new Set(basisParts)).join(" + ") : "업종·실적 유사군";
        return {{
          current_year: currentYear,
          previous_year: previousYear,
          previous_center: prevCenter,
          change_pct: changePct,
          basis: basis,
        }};
      }};

      const renderYoyCompare = (out) => {{
        const node = $("out-yoy-compare");
        if (!node) return;
        node.classList.remove("up", "down");
        const yoy = out && out.yoy ? out.yoy : null;
        const prevCenter = yoy ? Number(yoy.previous_center) : NaN;
        const changePct = yoy ? Number(yoy.change_pct) : NaN;
        const prevYear = yoy ? Number(yoy.previous_year || 0) : 0;
        const currYear = yoy ? Number(yoy.current_year || 0) : 0;
        const basis = yoy ? compact(yoy.basis || "") : "";
        if (!Number.isFinite(prevCenter) || prevCenter <= 0 || !Number.isFinite(changePct)) {{
          node.textContent = "동일 조건 전년 대비 비교는 계산 후 표시됩니다.";
          return;
        }}
        const direction = changePct >= 0 ? "상승" : "하락";
        const signedPct = `${{changePct >= 0 ? "+" : ""}}${{changePct.toFixed(1)}}%`;
        if (changePct >= 0) node.classList.add("up");
        else node.classList.add("down");
        const leftYear = prevYear > 0 ? `${{prevYear}}년` : "전년";
        const rightYear = currYear > 0 ? `${{currYear}}년` : "올해";
        const basisText = basis ? ` · 기준: ${{escapeHtml(basis)}}` : "";
        node.innerHTML = `${{escapeHtml(leftYear)}} 동조건 추정가 <strong>${{fmtEok(prevCenter)}}</strong> 대비 ${{escapeHtml(rightYear)}} 추정가 <strong>${{fmtEok(Number(out.center))}}</strong> (전년 대비 <strong>${{escapeHtml(signedPct)}} ${{escapeHtml(direction)}}</strong>)${{basisText}}`;
      }};

      const tokenIndex = (() => {{
        const idx = {{}};
        dataset.forEach((row, i) => {{
          const tokens = Array.isArray(row.tokens) ? row.tokens : [];
          tokens.forEach((token) => {{
            if (!idx[token]) idx[token] = [];
            idx[token].push(i);
          }});
        }});
        return idx;
      }})();

      const autoScaleByReference = (rawValue, p50, p90, label, notes, aggressiveUnits = false) => {{
        if (rawValue === null || rawValue === undefined || !Number.isFinite(rawValue) || rawValue <= 0) return rawValue;
        const ref = (Number.isFinite(p50) && p50 > 0) ? p50 : rawValue;
        if (!Number.isFinite(ref) || ref <= 0) return rawValue;
        const ratio = rawValue / ref;
        if (ratio >= 0.08 && ratio <= 300) return rawValue;
        const cand = [rawValue];
        if (ratio > 300 || (Number.isFinite(p90) && p90 > 0 && rawValue > p90 * 120)) cand.push(rawValue / 10);
        if (ratio > 3000 || (Number.isFinite(p90) && p90 > 0 && rawValue > p90 * 900)) cand.push(rawValue / 100);
        if (aggressiveUnits && (ratio > 800 || (Number.isFinite(p90) && p90 > 0 && rawValue > p90 * 2500))) cand.push(rawValue / 1000);
        if (aggressiveUnits && (ratio > 2000 || (Number.isFinite(p90) && p90 > 0 && rawValue > p90 * 7000))) cand.push(rawValue / 10000);
        let best = rawValue;
        let bestScore = -1e9;
        cand.forEach((c) => {{
          if (!Number.isFinite(c) || c <= 0) return;
          let score = -Math.abs(Math.log1p(c) - Math.log1p(ref));
          if (Number.isFinite(p90) && p90 > 0 && c > p90 * 18) score -= 0.9;
          if (Number.isFinite(p90) && p90 > 0 && c < p90 * 0.02) score -= 0.85;
          if (c < ref * 0.04) score -= 1.0;
          if (Math.abs(c - rawValue) > 1e-9) score -= 0.08;
          if (score > bestScore) {{
            bestScore = score;
            best = c;
          }}
        }});
        if (Math.abs(best - rawValue) > 1e-9) {{
          notes.push(`${{label}} 단위를 자동 보정했습니다 (${{rawValue}} → ${{(Math.round(best * 100) / 100)}})`);
        }}
        return best;
      }};

      const formInput = () => {{
        const scaleNotes = [];
        const licenseRaw = compact($("in-license").value);
        const specialtyRaw = num($("in-specialty").value);
        const y23Raw = num($("in-y23").value);
        const y24Raw = num($("in-y24").value);
        const y25Raw = num($("in-y25").value);
        const sales3Raw = num($("in-sales3-total").value);
        const sales5Raw = num($("in-sales5-total").value);
        const salesInputMode = compact(($("in-sales-input-mode") || {{}}).value) || "yearly";
        const specialty = bounded(
          autoScaleByReference(specialtyRaw, num(meta.median_specialty), num(meta.p90_specialty), "시평", scaleNotes),
          0,
          5000,
        );
        const salesRef = num(meta.median_sales3_eok);
        const salesP90 = num(meta.p90_sales3_eok);
        const y23 = bounded(autoScaleByReference(y23Raw, Number.isFinite(salesRef) ? salesRef / 3.0 : null, Number.isFinite(salesP90) ? salesP90 / 3.0 : null, "2023 매출", scaleNotes), 0, 5000);
        const y24 = bounded(autoScaleByReference(y24Raw, Number.isFinite(salesRef) ? salesRef / 3.0 : null, Number.isFinite(salesP90) ? salesP90 / 3.0 : null, "2024 매출", scaleNotes), 0, 5000);
        const y25 = bounded(autoScaleByReference(y25Raw, Number.isFinite(salesRef) ? salesRef / 3.0 : null, Number.isFinite(salesP90) ? salesP90 / 3.0 : null, "2025 매출", scaleNotes), 0, 5000);
        const sales3Input = bounded(autoScaleByReference(sales3Raw, salesRef, salesP90, "최근 3년 실적 합계", scaleNotes), 0, 12000);
        const sales5Input = bounded(autoScaleByReference(
          sales5Raw,
          Number.isFinite(salesRef) ? salesRef * 1.62 : null,
          Number.isFinite(salesP90) ? salesP90 * 1.62 : null,
          "최근 5년 실적 합계",
          scaleNotes,
        ), 0, 18000);
        const sales3FromYearlyVals = [y23, y24, y25].filter((x) => Number.isFinite(x));
        const sales3FromYearly = sales3FromYearlyVals.length ? sales3FromYearlyVals.reduce((a, b) => a + b, 0) : null;
        let sales3 = sales3FromYearly;
        let sales5 = Number.isFinite(sales5Input) ? sales5Input : null;
        let y23Use = y23;
        let y24Use = y24;
        let y25Use = y25;
        if (salesInputMode === "sales3") {{
          sales3 = Number.isFinite(sales3Input) ? sales3Input : null;
          y23Use = null;
          y24Use = null;
          y25Use = null;
          if (!Number.isFinite(sales5)) sales5 = Number.isFinite(sales3) ? (sales3 * 1.62) : null;
        }} else if (salesInputMode === "sales5") {{
          sales5 = Number.isFinite(sales5Input) ? sales5Input : null;
          sales3 = Number.isFinite(sales3Input) ? sales3Input : (Number.isFinite(sales5) ? (sales5 * 0.62) : null);
          y23Use = null;
          y24Use = null;
          y25Use = null;
        }} else {{
          if (!Number.isFinite(sales3) && Number.isFinite(sales3Input)) sales3 = sales3Input;
          if (!Number.isFinite(sales5) && Number.isFinite(sales3)) sales5 = sales3 * 1.62;
        }}
        const tokens = licenseTokenSet(licenseRaw);
        const balanceExcluded = isSeparateBalanceGroupTarget({{
          license_raw: licenseRaw,
          raw_license_key: normalizeLicenseKey(licenseRaw),
          tokens,
        }});
        const licenseYear = num($("in-license-year").value);
        const balanceRaw = num($("in-balance").value);
        const capitalRaw = num($("in-capital").value);
        const surplusRaw = num($("in-surplus").value);
        const balance = balanceExcluded
          ? null
          : bounded(autoScaleByReference(balanceRaw, num(meta.avg_balance_eok), num(meta.p90_balance_eok), "공제조합 잔액", scaleNotes, true), 0, 500);
        const capital = bounded(autoScaleByReference(capitalRaw, num(meta.avg_capital_eok), num(meta.p90_capital_eok), "자본금", scaleNotes), 0, 500);
        const surplus = bounded(autoScaleByReference(surplusRaw, num(meta.avg_surplus_eok), num(meta.p90_surplus_eok), "이익잉여금", scaleNotes), -300, 300);
        const companyType = compact($("in-company-type").value);
        const creditLevel = compact($("in-credit-level").value);
        const adminHistory = compact($("in-admin-history").value);
        const debtLevel = $("in-debt-level").value;
        const liqLevel = $("in-liq-level").value;
        const avgDebt = num(meta.avg_debt_ratio);
        const avgLiq = num(meta.avg_liq_ratio);
        let debtRatio = null;
        let liqRatio = null;
        if (Number.isFinite(avgDebt)) {{
          if (debtLevel === "below") debtRatio = avgDebt * 0.82;
          else if (debtLevel === "above") debtRatio = avgDebt * 1.25;
        }}
        if (Number.isFinite(avgLiq)) {{
          if (liqLevel === "above") liqRatio = avgLiq * 1.20;
          else if (liqLevel === "below") liqRatio = avgLiq * 0.78;
        }}
        const numericSignals = [specialty, y23Use, y24Use, y25Use, sales3, sales5, balance, capital, surplus, licenseYear].filter((x) => Number.isFinite(x)).length;
        const categorySignals = [companyType, creditLevel, adminHistory].filter((x) => !!x).length;
        const missingCritical = [];
        if (!balanceExcluded && !Number.isFinite(balance)) missingCritical.push("공제조합 잔액");
        if (!Number.isFinite(capital)) missingCritical.push("자본금");
        if (!Number.isFinite(surplus)) missingCritical.push("이익잉여금");
        const missingGuide = [];
        if (!licenseRaw) missingGuide.push("면허/업종");
        if (!Number.isFinite(specialty)) missingGuide.push("시평");
        if (salesInputMode === "yearly") {{
          if (!Number.isFinite(y23Use) && !Number.isFinite(y24Use) && !Number.isFinite(y25Use)) missingGuide.push("연도별 매출(2023~2025)");
        }} else if (salesInputMode === "sales3") {{
          if (!Number.isFinite(sales3)) missingGuide.push("최근 3년 실적 합계");
        }} else if (salesInputMode === "sales5") {{
          if (!Number.isFinite(sales5)) missingGuide.push("최근 5년 실적 합계");
        }}
        return {{
          license_raw: licenseRaw,
          raw_license_key: normalizeLicenseKey(licenseRaw),
          has_license_input: !!licenseRaw,
          tokens,
          license_year: licenseYear,
          specialty: specialty,
          y23: y23Use,
          y24: y24Use,
          y25: y25Use,
          sales_input_mode: salesInputMode,
          sales3_eok: sales3,
          sales5_eok: sales5,
          balance_eok: balance,
          balance_excluded: balanceExcluded,
          capital_eok: capital,
          surplus_eok: surplus,
          company_type: companyType,
          credit_level: creditLevel,
          admin_history: adminHistory,
          debt_ratio: debtRatio,
          liq_ratio: liqRatio,
          debt_level: debtLevel,
          liq_level: liqLevel,
          ok_capital: $("ok-capital").checked,
          ok_engineer: $("ok-engineer").checked,
          ok_office: $("ok-office").checked,
          scale_notes: scaleNotes,
          has_any_signal: !!licenseRaw || numericSignals > 0 || categorySignals > 0,
          provided_signals: numericSignals + (tokens.size ? 1 : 0) + categorySignals,
          missing_critical: missingCritical,
          missing_guide: missingGuide,
        }};
      }};
      const normalizeCompanyType = (raw) => {{
        const t = compact(raw).replace(/\\s+/g, "");
        if (!t) return "";
        if (t.indexOf("주식") >= 0) return "주식회사";
        if (t.indexOf("유한") >= 0) return "유한회사";
        if (t.indexOf("개인") >= 0) return "개인";
        return t;
      }};
      const tokenContainment = (a, b) => {{
        const sa = a instanceof Set ? a : new Set();
        const sb = b instanceof Set ? b : new Set();
        if (!sa.size || !sb.size) return 0;
        let inter = 0;
        sa.forEach((t) => {{ if (sb.has(t)) inter += 1; }});
        return inter / Math.max(1, Math.min(sa.size, sb.size));
      }};
      const CORE_LICENSE_TOKENS = new Set([
        "전기", "정보통신", "소방", "기계설비", "가스",
        "토건", "토목", "건축", "조경", "실내",
        "토공", "포장", "철콘", "상하", "석공", "비계", "석면", "습식", "도장",
        "조경식재", "조경시설", "산림토목", "도시정비", "보링", "수중", "금속",
      ]);
      const CORE_LICENSE_TOKENS_SORTED = [...CORE_LICENSE_TOKENS].sort((a, b) => b.length - a.length);
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
      const coreTokensFromText = (raw) => {{
        const key = normalizeLicenseKey(raw || "");
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
      const coreTokens = (tokens) => {{
        const src = tokens instanceof Set ? tokens : new Set();
        const out = new Set();
        src.forEach((t) => {{
          const token = String(t || "");
          if (!token) return;
          if (CORE_LICENSE_TOKENS.has(token)) out.add(token);
          coreTokensFromText(token).forEach((v) => out.add(v));
        }});
        return out;
      }};
      const isSingleTokenCrossCombo = (targetTokens, candTokens, candLicenseText) => {{
        const c = candTokens instanceof Set ? candTokens : new Set();
        const target = singleTokenTargetCore(targetTokens);
        if (!target) return false;
        const candCore = new Set([...coreTokens(c), ...coreTokensFromText(candLicenseText || "")]);
        if (!c.has(target) && !candCore.has(target)) return false;
        if (candCore.size <= 1) return false;
        for (const tok of candCore) {{
          if (tok !== target) return true;
        }}
        return false;
      }};
      const singleTokenTargetCore = (targetTokens) => {{
        const t = targetTokens instanceof Set ? targetTokens : new Set();
        const fromCore = new Set([...coreTokens(t)]);
        if (fromCore.size === 1) return [...fromCore][0];
        if (t.size === 1) return [...t][0];
        return "";
      }};
      const isSingleTokenSameCore = (targetTokens, candTokens, candLicenseText) => {{
        const target = singleTokenTargetCore(targetTokens);
        if (!target) return false;
        const c = candTokens instanceof Set ? candTokens : new Set();
        const candCore = new Set([...coreTokens(c), ...coreTokensFromText(candLicenseText || "")]);
        if (candCore.size >= 2) return false;
        if (candCore.size === 1) return candCore.has(target);
        if (c.size === 1) {{
          const arr = [...c];
          const tok = arr.length ? arr[0] : "";
          return !!tok && (tok.indexOf(target) >= 0 || target.indexOf(tok) >= 0);
        }}
        return false;
      }};
      const isSingleTokenProfileOutlier = (target, cand) => {{
        const t = target && target.tokens instanceof Set ? target.tokens : new Set();
        if (!singleTokenTargetCore(t)) return false;
        const sr = positiveRatio(target ? target.specialty : null, cand ? cand.specialty : null);
        const tr = positiveRatio(target ? target.sales3_eok : null, cand ? cand.sales3_eok : null);
        if (Number.isFinite(sr) && (sr < 0.30 || sr > 3.30)) return true;
        if (Number.isFinite(tr) && (tr < 0.30 || tr > 3.30)) return true;
        return false;
      }};

      const neighborScore = (target, cand) => {{
        const balanceExcluded = !!(target && target.balance_excluded);
        const candTokens = new Set(Array.isArray(cand.tokens) ? cand.tokens : []);
        const inter = [...target.tokens].filter((x) => candTokens.has(x));
        const tokenJac = jaccard(target.tokens, candTokens);
        const tokenContain = tokenContainment(target.tokens, candTokens);
        const tokenPrecision = candTokens.size ? (inter.length / Math.max(1, candTokens.size)) : 0;
        const singleCoreTarget = !!singleTokenTargetCore(target.tokens);
        const rawLicenseSimilarity = (!target.tokens.size && target.raw_license_key)
          ? bigramJaccard(target.raw_license_key, cand.license_text || "")
          : 0;
        const sSpecialty = relativeCloseness(target.specialty, cand.specialty);
        const sSales3 = relativeCloseness(target.sales3_eok, cand.sales3_eok);
        const sSales5 = relativeCloseness(target.sales5_eok, cand.sales5_eok);
        const sLicenseYear = relativeCloseness(target.license_year, cand.license_year);
        const sDebt = relativeCloseness(target.debt_ratio, cand.debt_ratio);
        const sLiq = relativeCloseness(target.liq_ratio, cand.liq_ratio);
        const sCapital = relativeCloseness(target.capital_eok, cand.capital_eok);
        const sBalance = relativeCloseness(target.balance_eok, cand.balance_eok);
        const sSurplus = relativeCloseness(target.surplus_eok, cand.surplus_eok);
        const sYearShape = yearlyShapeSimilarity(target, cand);
        const targetYearInfo = yearlySeries(target);
        const candYearInfo = yearlySeries(cand);
        let score = 0;
        score += tokenJac * 42;
        score += tokenContain * 24;
        score += tokenPrecision * 18;
        score += Math.min(14, 3.5 * inter.length);
        score += rawLicenseSimilarity * 26;
        score += sSpecialty * 8;
        score += sSales3 * 7;
        score += sSales5 * 5;
        score += sLicenseYear * 2;
        score += sDebt * 2.5;
        score += sLiq * 2.5;
        score += sCapital * 10;
        if (!balanceExcluded) score += sBalance * 12;
        score += sSurplus * 2.5;
        score += sYearShape * 9;
        if (sSpecialty >= 0.90 && sSales3 >= 0.90) score += 4.5;
        if (target.tokens.size && inter.length === target.tokens.size) score += 8;
        const targetComp = normalizeCompanyType(target.company_type);
        const candComp = normalizeCompanyType(cand.company_type);
        if (targetComp && candComp) {{
          score += (targetComp === candComp ? 3.5 : -1.2);
        }}
        const specialtyRatio = positiveRatio(target.specialty, cand.specialty);
        if (Number.isFinite(specialtyRatio)) {{
          if (specialtyRatio < 0.08 || specialtyRatio > 12.0) score *= 0.78;
          else if (specialtyRatio < 0.20 || specialtyRatio > 5.0) score *= 0.90;
        }}
        const salesRatio = positiveRatio(target.sales3_eok, cand.sales3_eok);
        if (Number.isFinite(salesRatio)) {{
          if (salesRatio < 0.08 || salesRatio > 12.0) score *= 0.78;
          else if (salesRatio < 0.20 || salesRatio > 5.0) score *= 0.90;
        }}
        if (targetYearInfo.count >= 2 && candYearInfo.count >= 2) {{
          if (sYearShape < 0.22) score *= 0.62;
          else if (sYearShape < 0.35) score *= 0.80;
        }}
        if (target.tokens.size && candTokens.size) {{
          if (!inter.length) score *= 0.08;
          else if (target.tokens.size >= 2 && inter.length <= 1) score *= 0.55;
          if (singleCoreTarget && tokenPrecision < 0.28) score *= 0.74;
          else if (target.tokens.size >= 2 && tokenPrecision < 0.36) score *= 0.80;
          if (singleCoreTarget && candTokens.size >= 2) {{
            // 단일 업종 검색에서 복합면허(예: 전기+소방) 과대매칭 억제
            const extraTokenCount = [...candTokens].filter((t) => !target.tokens.has(t)).length;
            if (extraTokenCount >= 1) {{
              score *= 0.62;
              if (tokenPrecision < 0.60) score *= 0.72;
              const specRatio2 = positiveRatio(target.specialty, cand.specialty);
              const salesRatio2 = positiveRatio(target.sales3_eok, cand.sales3_eok);
              if (
                (Number.isFinite(specRatio2) && (specRatio2 < 0.35 || specRatio2 > 2.85)) ||
                (Number.isFinite(salesRatio2) && (salesRatio2 < 0.35 || salesRatio2 > 2.85))
              ) {{
                score *= 0.72;
              }}
            }}
          }}
          if (isSingleTokenCrossCombo(target.tokens, candTokens, cand.license_text)) {{
            // 단일 업종 입력에서 타 핵심업종 포함 복합면허는 하드 감점
            score *= 0.10;
          }}
        }} else if (!target.tokens.size && target.raw_license_key) {{
          if (rawLicenseSimilarity < 0.28) score *= 0.55;
          else if (rawLicenseSimilarity < 0.42) score *= 0.78;
        }}
        return Math.max(0, Math.min(100, score));
      }};

      const selectCandidates = (target) => {{
        const tokens = target && target.tokens ? target.tokens : new Set();
        const picked = [];
        const seen = new Set();
        if (tokens && tokens.size) {{
          tokens.forEach((token) => {{
            const idxRows = tokenIndex[token] || [];
            idxRows.forEach((rowIdx) => {{
              if (!seen.has(rowIdx)) {{
                seen.add(rowIdx);
                picked.push(dataset[rowIdx]);
              }}
            }});
          }});
        }}
        if (tokens && tokens.size && picked.length > 0) {{
          return picked;
        }}
        const rawKey = target && target.raw_license_key ? String(target.raw_license_key) : "";
        if ((!tokens || !tokens.size) && rawKey && rawKey.length >= 2) {{
          const hinted = dataset.filter((row) => {{
            const rowText = normalizeLicenseKey(row.license_text || "");
            if (!rowText) return false;
            if (rowText.indexOf(rawKey) >= 0 || rawKey.indexOf(rowText) >= 0) return true;
            return bigramJaccard(rawKey, rowText) >= 0.55;
          }});
          if (hinted.length > 0) return hinted;
        }}
        if (picked.length < 80) return dataset.slice();
        return picked;
      }};

      const inferBalancePassThrough = (neighbors) => {{
        const rows = (Array.isArray(neighbors) ? neighbors : [])
          .map((row) => {{
            const sim = Number(row && row[0]);
            const rec = row && row[1] ? row[1] : null;
            const b = num(rec ? rec.balance_eok : null);
            const p = num(rec ? rec.price_eok : null);
            if (!Number.isFinite(b) || !Number.isFinite(p) || p <= 0 || b < 0) return null;
            return {{
              w: Math.max(0.25, (Number.isFinite(sim) ? sim : 0) / 45),
              b,
              p,
            }};
          }})
          .filter((x) => !!x);
        if (rows.length < 4) {{
          return {{ slope: 0.78, reliability: 0.28, samples: rows.length }};
        }}
        const wSum = rows.reduce((a, x) => a + x.w, 0) || 1;
        const meanB = rows.reduce((a, x) => a + (x.b * x.w), 0) / wSum;
        const meanP = rows.reduce((a, x) => a + (x.p * x.w), 0) / wSum;
        let cov = 0;
        let varB = 0;
        rows.forEach((x) => {{
          const db = x.b - meanB;
          cov += x.w * db * (x.p - meanP);
          varB += x.w * db * db;
        }});
        let slope = Number.isFinite(varB) && varB > 1e-7 ? (cov / varB) : NaN;
        if (!Number.isFinite(slope)) slope = 0.78;
        slope = clamp(slope, 0.35, 1.02);
        const minB = Math.min(...rows.map((x) => x.b));
        const maxB = Math.max(...rows.map((x) => x.b));
        const span = Math.max(0, maxB - minB);
        const reliability = clamp(((rows.length / 12) * 0.7) + (Math.min(1, span / 2.5) * 0.3), 0.25, 0.92);
        return {{ slope, reliability, samples: rows.length }};
      }};

      const buildFeatureAnchor = (target, neighbors) => {{
        const components = [];
        const compWeights = [];
        let maxSamples = 0;
        const notes = [];
        const build = (targetValue, field, weight, label, ratioLo = 0.004, ratioHi = 9.0) => {{
          if (!Number.isFinite(targetValue) || targetValue <= 0) return;
          const ratios = [];
          const ratioWeights = [];
          neighbors.slice(0, 10).forEach(([sim, rec]) => {{
            const price = num(rec.price_eok);
            const base = num(rec[field]);
            if (!Number.isFinite(price) || !Number.isFinite(base) || base <= 0) return;
            const ratio = price / base;
            if (!Number.isFinite(ratio) || ratio < ratioLo || ratio > ratioHi) return;
            ratios.push(ratio);
            ratioWeights.push(Math.max(0.2, (Number(sim) || 0) / 45));
          }});
          if (ratios.length < 3) return;
          maxSamples = Math.max(maxSamples, ratios.length);
          const ratioMid = weightedQuantile(ratios, ratioWeights, 0.5);
          if (!Number.isFinite(ratioMid) || ratioMid <= 0) return;
          components.push(targetValue * ratioMid);
          compWeights.push(weight);
          notes.push(`${{label}} 앵커 반영`);
        }};
        build(num(target.specialty), "specialty", 0.44, "시평");
        build(num(target.sales3_eok), "sales3_eok", 0.26, "3개년 실적");
        build(num(target.capital_eok), "capital_eok", 0.12, "자본금", 0.02, 15.0);
        if (!components.length) return {{ anchor: null, reliability: 0, notes }};
        const anchor = weightedMean(components, compWeights);
        if (!Number.isFinite(anchor) || anchor <= 0) return {{ anchor: null, reliability: 0, notes }};
        let reliability = Math.min(1, maxSamples / 8);
        if (target.provided_signals >= 6) reliability *= 1.0;
        else if (target.provided_signals >= 4) reliability *= 0.88;
        else reliability *= 0.68;
        return {{ anchor, reliability, notes }};
      }};

      const applyAnchorGuard = (center, low, high, anchorInfo, riskNotes) => {{
        const anchor = num(anchorInfo && anchorInfo.anchor);
        const reliability = clamp(num(anchorInfo && anchorInfo.reliability) || 0, 0, 1);
        if (!Number.isFinite(anchor) || anchor <= 0 || reliability <= 0) return {{ center, low, high }};
        const ratio = center / anchor;
        if (ratio >= 0.58 && ratio <= 1.72) return {{ center, low, high }};
        const pull = Math.max(0.18, Math.min(0.58, Math.abs(ratio - 1) * 0.35)) * reliability;
        const adjustedCenter = (center * (1 - pull)) + (anchor * pull);
        if (!Number.isFinite(adjustedCenter) || adjustedCenter <= 0) return {{ center, low, high }};
        const scale = adjustedCenter / Math.max(center, 0.05);
        let nextLow = Math.max(0.05, low * scale);
        let nextHigh = Math.max(nextLow, high * scale);
        const widen = Math.max(0.03, (nextHigh - nextLow) * 0.08);
        nextLow = Math.max(0.05, nextLow - widen);
        nextHigh = Math.max(nextLow, nextHigh + widen);
        riskNotes.push(`입력 스케일(시평/실적) 기반 보정 적용: ${{fmtEok(center)}} → ${{fmtEok(adjustedCenter)}}`);
        return {{ center: adjustedCenter, low: nextLow, high: nextHigh }};
      }};
      const stabilizeRangeByCoverage = (target, center, low, high, riskNotes) => {{
        if (!Number.isFinite(center) || center <= 0) return {{ center, low, high }};
        let nextLow = Math.max(0.05, Number(low) || 0.05);
        let nextHigh = Math.max(nextLow, Number(high) || nextLow);
        const strongCore = !!(target && target.tokens && target.tokens.size && (!target.missing_critical || !target.missing_critical.length) && Number(target.provided_signals || 0) >= 6);
        const mediumCore = !!(target && target.tokens && target.tokens.size && Number(target.provided_signals || 0) >= 4);
        if (strongCore && center >= 5) {{
          const lowFloor = center * 0.38;
          const highCeil = center * 2.05;
          if (nextLow < lowFloor) {{
            nextLow = lowFloor;
            if (Array.isArray(riskNotes) && riskNotes.indexOf("핵심항목 충족 조건으로 하단 오차 범위를 안정화했습니다.") < 0) {{
              riskNotes.push("핵심항목 충족 조건으로 하단 오차 범위를 안정화했습니다.");
            }}
          }}
          if (nextHigh > highCeil) nextHigh = Math.max(nextLow, highCeil);
        }} else if (mediumCore && center >= 3) {{
          nextLow = Math.max(nextLow, center * 0.22);
        }}
        return {{ center, low: nextLow, high: Math.max(nextLow, nextHigh) }};
      }};
      const applyUncertaintyDiscount = (center, low, high, avgSim, neighborCount, avgTokenMatch, riskNotes) => {{
        if (!Number.isFinite(center) || center <= 0) return {{ center, low, high, discount: 0 }};
        const sim = Number(avgSim) || 0;
        const n = Number(neighborCount) || 0;
        const token = Number.isFinite(avgTokenMatch) ? Number(avgTokenMatch) : 1;
        let discount = 0;
        if (sim < 55) discount += Math.min(0.18, (55 - sim) / 260);
        if (n < 4) discount += Math.min(0.12, (4 - n) * 0.03);
        if (token < 0.60) discount += Math.min(0.08, (0.60 - token) * 0.20);
        discount = clamp(discount, 0, 0.22);
        if (discount <= 0.01) return {{ center, low, high, discount: 0 }};
        const nextCenter = center * (1 - discount);
        const nextLow = Math.max(0.05, low * (1 - discount * 0.85));
        const nextHigh = Math.max(nextLow, high * (1 - discount * 0.65));
        if (Array.isArray(riskNotes)) {{
          riskNotes.push(`유사도 불확실성 보정: ${{Math.round(discount * 100)}}% 보수 조정`);
        }}
        return {{ center: nextCenter, low: nextLow, high: nextHigh, discount }};
      }};
      const applyUpperGuardBySimilarity = (center, low, high, prices, sims, avgTokenMatch, neighborCount, riskNotes) => {{
        if (!Number.isFinite(center) || center <= 0) return {{ center, low, high }};
        const safePrices = (Array.isArray(prices) ? prices : []).map((v) => Number(v)).filter((v) => Number.isFinite(v) && v > 0);
        if (!safePrices.length) return {{ center, low, high }};
        const safeSims = (Array.isArray(sims) ? sims : []).map((v) => Number(v)).filter((v) => Number.isFinite(v) && v > 0);
        const p80 = weightedQuantile(safePrices, safeSims.length === safePrices.length ? safeSims : safePrices.map(() => 1), 0.80);
        const p90 = weightedQuantile(safePrices, safeSims.length === safePrices.length ? safeSims : safePrices.map(() => 1), 0.90);
        const ref = Number.isFinite(p80) ? p80 : (Number.isFinite(p90) ? p90 : Math.max(...safePrices));
        if (!Number.isFinite(ref) || ref <= 0) return {{ center, low, high }};
        const token = Number.isFinite(avgTokenMatch) ? Number(avgTokenMatch) : 1;
        const n = Number(neighborCount) || safePrices.length;
        let capMultiplier = 1.18;
        if (token >= 0.80 && n >= 6) capMultiplier = 1.30;
        else if (token >= 0.70 && n >= 4) capMultiplier = 1.24;
        else if (token < 0.60 || n <= 3) capMultiplier = 1.10;
        const upperCap = ref * capMultiplier;
        if (!Number.isFinite(upperCap)) return {{ center, low, high }};
        let triggerRatio = 1.02;
        if (token >= 0.70 && n >= 6) triggerRatio = 1.12;
        else if (token >= 0.60 && n >= 4) triggerRatio = 1.08;
        if (center <= (upperCap * triggerRatio)) return {{ center, low, high }};
        const excess = (center / Math.max(upperCap, 0.05)) - 1;
        const pullGain = (token >= 0.70 && n >= 6) ? 0.42 : (n <= 3 ? 0.75 : 0.58);
        const pull = clamp(excess * pullGain, 0.16, 0.68);
        const nextCenter = (center * (1 - pull)) + (upperCap * pull);
        const scale = nextCenter / Math.max(center, 0.05);
        const nextLow = Math.max(0.05, low * scale);
        const nextHigh = Math.max(nextLow, Math.min(high * scale, upperCap * (1 + (n <= 3 ? 0.26 : 0.34))));
        if (Array.isArray(riskNotes)) {{
          riskNotes.push(`고가 이상치 억제: 상위 분위 대비 초과분 ${{
            Math.round(Math.max(0, excess) * 100)
          }}%를 점진 보정했습니다.`);
        }}
        return {{ center: nextCenter, low: nextLow, high: nextHigh }};
      }};
      const applyNeighborConsistencyGuard = (center, low, high, neighbors, avgTokenMatch, riskNotes, target = null) => {{
        if (!Number.isFinite(center) || center <= 0) return {{ center, low, high }};
        if (!Array.isArray(neighbors) || neighbors.length < 4) return {{ center, low, high }};
        const prices = [];
        const weights = [];
        neighbors.forEach(([sim, rec]) => {{
          const lowRange = num(rec && rec.display_low_eok);
          const highRange = num(rec && rec.display_high_eok);
          let p = num(rec && rec.price_eok);
          if ((!Number.isFinite(p) || p <= 0) && Number.isFinite(lowRange) && Number.isFinite(highRange) && highRange >= lowRange) {{
            p = (lowRange + highRange) / 2;
          }}
          if (!Number.isFinite(p) || p <= 0) return;
          prices.push(Number(p));
          weights.push(Math.max(0.2, (Number(sim) || 0) / 45));
        }});
        if (prices.length < 4) return {{ center, low, high }};
        const p50 = weightedQuantile(prices, weights, 0.50);
        const p75 = weightedQuantile(prices, weights, 0.75);
        const p90 = weightedQuantile(prices, weights, 0.90);
        const ref = Number.isFinite(p90) ? p90 : p75;
        if (!Number.isFinite(ref) || ref <= 0) return {{ center, low, high }};
        const token = Number.isFinite(avgTokenMatch) ? Number(avgTokenMatch) : 1;
        const n = neighbors.length;
        let capMult = 1.42;
        if (token >= 0.80 && n >= 8) capMult = 1.52;
        else if (token >= 0.70 && n >= 6) capMult = 1.46;
        else if (token < 0.60 || n <= 4) capMult = 1.34;
        let hardCap = ref * capMult;
        const hasBalanceUnitFix = !!(target && Array.isArray(target.scale_notes) && target.scale_notes.some((x) => String(x || "").indexOf("공제조합 잔액") >= 0));
        const balanceRaw = target ? num(target.balance_eok) : null;
        if (hasBalanceUnitFix) {{
          hardCap = Math.min(hardCap, ref * 1.36);
        }}
        if (Number.isFinite(balanceRaw) && balanceRaw > 50) {{
          hardCap = Math.min(hardCap, ref * 1.30);
        }}
        if (!Number.isFinite(hardCap) || hardCap <= 0 || center <= hardCap) return {{ center, low, high }};
        let nextCenter = center;
        if (center > hardCap * 2.2) {{
          nextCenter = hardCap * 1.02;
        }} else {{
          const excess = (center / Math.max(hardCap, 0.05)) - 1;
          const pull = clamp(excess * 0.82, 0.22, 0.84);
          nextCenter = (center * (1 - pull)) + (hardCap * pull);
        }}
        if (Number.isFinite(p50) && p50 > 0 && nextCenter > (p50 * 1.9)) {{
          nextCenter = (nextCenter * 0.55) + ((p50 * 1.9) * 0.45);
        }}
        const scale = nextCenter / Math.max(center, 0.05);
        const nextLow = Math.max(0.05, low * scale);
        const nextHigh = Math.max(nextLow, Math.min(high * scale, hardCap * (n <= 5 ? 1.18 : 1.24)));
        if (Array.isArray(riskNotes)) {{
          riskNotes.push(`유사군 일관성 보정: 근거 매물 상위 분위 대비 과대 추정을 ${{
            Math.round(Math.max(0, ((center / Math.max(ref, 0.05)) - 1) * 100))
          }}% 구간에서 안정화했습니다.`);
        }}
        return {{ center: nextCenter, low: nextLow, high: nextHigh }};
      }};

      const estimateLocal = (target) => {{
        const balanceExcluded = !!(target && target.balance_excluded);
        const candidates = selectCandidates(target);
        let scored = [];
        let minSimilarity = target.tokens.size ? 26 : 14;
        if (target.tokens.size >= 2) minSimilarity = 32;
        if (target.tokens.size && candidates.length <= 16) minSimilarity = Math.max(20, minSimilarity - 4);
        if (target.provided_signals <= 2) minSimilarity = minSimilarity + 6;
        if (target.tokens.size && !target.missing_critical.length) minSimilarity += 3;
        const strictSameCore = !!singleTokenTargetCore(target.tokens);
        const targetCoreSet = coreTokens(target.tokens);
        const targetCoreCount = targetCoreSet.size;
        const scorePool = (pool, strictOnly, threshold) => {{
          const rows = [];
          for (const cand of pool) {{
            const p = Number(cand.price_eok);
            if (!Number.isFinite(p) || p <= 0) continue;
            const candTokens = new Set(Array.isArray(cand.tokens) ? cand.tokens : []);
            const candCore = new Set([...coreTokens(candTokens), ...coreTokensFromText(cand.license_text || "")]);
            if (targetCoreCount >= 2) {{
              const hasCoreOverlap = [...targetCoreSet].some((x) => candCore.has(x));
              if (!hasCoreOverlap) continue;
            }}
            if (strictOnly && !isSingleTokenSameCore(target.tokens, candTokens, cand.license_text)) continue;
            if (isSingleTokenCrossCombo(target.tokens, candTokens, cand.license_text)) continue;
            if (isSingleTokenProfileOutlier(target, cand)) continue;
            const sim = neighborScore(target, cand);
            if (sim < threshold) continue;
            rows.push([sim, cand]);
          }}
          return rows;
        }};
        scored = scorePool(candidates, strictSameCore, minSimilarity);
        if (strictSameCore && !scored.length) {{
          scored = scorePool(candidates, true, Math.max(12, minSimilarity - 8));
        }}
        if (!scored.length) {{
          const coarse = [];
          const coarsePool = (target.tokens.size && candidates.length) ? candidates : dataset;
          for (const cand of coarsePool) {{
            const p = Number(cand.price_eok);
            if (!Number.isFinite(p) || p <= 0) continue;
            const candTokens = new Set(Array.isArray(cand.tokens) ? cand.tokens : []);
            const candCore = new Set([...coreTokens(candTokens), ...coreTokensFromText(cand.license_text || "")]);
            if (targetCoreCount >= 2) {{
              const hasCoreOverlap = [...targetCoreSet].some((x) => candCore.has(x));
              if (!hasCoreOverlap) continue;
            }}
            if (strictSameCore && !isSingleTokenSameCore(target.tokens, candTokens, cand.license_text)) continue;
            if (isSingleTokenCrossCombo(target.tokens, candTokens, cand.license_text)) continue;
            if (isSingleTokenProfileOutlier(target, cand)) continue;
            const sim = neighborScore(target, cand);
            coarse.push([Math.max(0.1, sim), cand]);
          }}
          coarse.sort((a, b) => b[0] - a[0]);
          scored = coarse.slice(0, target.tokens.size ? 14 : 18);
        }}
        scored.sort((a, b) => b[0] - a[0]);
        if (!scored.length) {{
          return {{ error: "유사 매물 근거가 부족합니다. 면허/시평/매출 입력을 보강해 주세요.", target }};
        }}
        if (target.tokens.size) {{
          const strictTokenScored = scored.filter((row) => {{
            const candTokens = new Set(Array.isArray(row && row[1] && row[1].tokens) ? row[1].tokens : []);
            const candLicenseText = row && row[1] ? row[1].license_text : "";
            const candRec = row && row[1] ? row[1] : null;
            const tYear = yearlySeries(target);
            const cYear = yearlySeries(candRec);
            const shapeSim = yearlyShapeSimilarity(target, candRec);
            if (strictSameCore && !isSingleTokenSameCore(target.tokens, candTokens, candLicenseText)) return false;
            if (isSingleTokenCrossCombo(target.tokens, candTokens, candLicenseText)) return false;
            if (isSingleTokenProfileOutlier(target, row && row[1] ? row[1] : null)) return false;
            if (tYear.count >= 2 && cYear.count >= 2 && shapeSim < 0.24) return false;
            const interCount = [...target.tokens].filter((x) => candTokens.has(x)).length;
            const precision = candTokens.size ? (interCount / Math.max(1, candTokens.size)) : 0;
            if (strictSameCore) {{
              return (candTokens.size <= 1) || (precision >= 0.60);
            }}
            return tokenContainment(target.tokens, candTokens) >= 0.52;
          }});
          if (strictTokenScored.length >= 6) {{
            scored = strictTokenScored;
          }}
        }}
        const simWindow = targetCoreCount >= 2 ? 18 : (strictSameCore ? 14 : 10);
        const bestSim = Number(scored[0] && scored[0][0]) || 0;
        const statFloor = Math.max(minSimilarity, bestSim - simWindow);
        let statNeighbors = scored.filter((row) => Number(row[0]) >= statFloor);
        const minStatSize = Math.max(10, 12);
        if (statNeighbors.length < minStatSize) {{
          statNeighbors = scored.slice(0, Math.max(minStatSize, 48));
        }}

        const seedNeighbors = statNeighbors.slice(0, 18);
        let neighbors = statNeighbors.slice();
        const seedPrices = seedNeighbors.map((x) => Number(x[1].price_eok));
        const seedSims = seedNeighbors.map((x) => Number(x[0]));
        const seedCenter = weightedQuantile(seedPrices, seedSims, 0.5);
        if (Number.isFinite(seedCenter) && seedCenter > 0 && seedNeighbors.length >= 8) {{
          const filtered = statNeighbors.filter((row) => {{
            const p = Number(row[1].price_eok);
            if (!Number.isFinite(p) || p <= 0) return false;
            const ratio = p / seedCenter;
            let lower = target.tokens.size ? 0.25 : 0.14;
            let upper = target.tokens.size ? 3.9 : 6.2;
            if (Number(row[0]) >= 88) {{
              lower = Math.min(lower, 0.19);
              upper = Math.max(upper, 4.6);
            }}
            return ratio >= lower && ratio <= upper;
          }});
          if (filtered.length >= 8) neighbors = filtered;
        }}
        const targetYearInfo = yearlySeries(target);
        if (targetYearInfo.count >= 2 && neighbors.length >= 8) {{
          const shapeFiltered = neighbors.filter((row) => {{
            const rec = row && row[1] ? row[1] : null;
            const candYearInfo = yearlySeries(rec);
            if (candYearInfo.count < 2) return true;
            const shape = yearlyShapeSimilarity(target, rec);
            if (shape >= 0.26) return true;
            return Number(row[0]) >= 94 && shape >= 0.18;
          }});
          if (shapeFiltered.length >= 8) neighbors = shapeFiltered;
          else if (shapeFiltered.length >= 6 && shapeFiltered.length >= Math.floor(neighbors.length * 0.55)) neighbors = shapeFiltered;
        }}
        const displayNeighbors = neighbors.slice(0, 12);
        const hotMatchCount = Math.max(
          displayNeighbors.filter((row) => Number(row[0]) >= 90).length,
          neighbors.filter((row) => Number(row[0]) >= 90).length,
        );
        const prices = neighbors.map((x) => Number(x[1].price_eok));
        const sims = neighbors.map((x) => Number(x[0]));
        const balanceInfo = balanceExcluded ? {{ slope: 0 }} : inferBalancePassThrough(neighbors);
        const balanceSlope = balanceExcluded ? 0 : Number(balanceInfo && balanceInfo.slope);
        const balanceMeanPairs = balanceExcluded ? [] : neighbors
          .map((row) => {{
            const sim = Number(row && row[0]);
            const rec = row && row[1] ? row[1] : null;
            const b = num(rec ? rec.balance_eok : null);
            if (!Number.isFinite(b) || b < 0) return null;
            return [b, Math.max(0.2, Number.isFinite(sim) ? sim : 1)];
          }})
          .filter((x) => !!x);
        const neighborBalanceMean = balanceMeanPairs.length
          ? weightedMean(balanceMeanPairs.map((x) => Number(x[0])), balanceMeanPairs.map((x) => Number(x[1])))
          : null;
        const neighborBalanceValues = balanceMeanPairs.map((x) => Number(x[0])).filter((x) => Number.isFinite(x));
        const neighborBalanceWeights = balanceMeanPairs.map((x) => Number(x[1])).filter((x) => Number.isFinite(x) && x > 0);
        const neighborBalanceP25 = (neighborBalanceValues.length >= 3 && neighborBalanceWeights.length === neighborBalanceValues.length)
          ? weightedQuantile(neighborBalanceValues, neighborBalanceWeights, 0.25)
          : null;
        const neighborBalanceP75 = (neighborBalanceValues.length >= 3 && neighborBalanceWeights.length === neighborBalanceValues.length)
          ? weightedQuantile(neighborBalanceValues, neighborBalanceWeights, 0.75)
          : null;
        const neighborBalanceMedian = (neighborBalanceValues.length >= 3 && neighborBalanceWeights.length === neighborBalanceValues.length)
          ? weightedQuantile(neighborBalanceValues, neighborBalanceWeights, 0.50)
          : null;
        const basePairs = balanceExcluded ? [] : neighbors
          .map((row) => {{
            const sim = Number(row && row[0]);
            const rec = row && row[1] ? row[1] : null;
            const p = num(rec ? rec.price_eok : null);
            const b = num(rec ? rec.balance_eok : null);
            if (!Number.isFinite(p) || p <= 0 || !Number.isFinite(b) || b < 0) return null;
            const base = p - (b * balanceSlope);
            if (!Number.isFinite(base) || base <= 0.03) return null;
            return [base, Number.isFinite(sim) ? sim : 1];
          }})
          .filter((x) => !!x);
        const useBaseModel = basePairs.length >= 3;
        const priceAxis = useBaseModel ? basePairs.map((x) => Number(x[0])) : prices;
        const weightAxis = useBaseModel ? basePairs.map((x) => Number(x[1])) : sims;
        const tokenMatchRatios = target.tokens.size
          ? neighbors.map((row) => {{
              const candTokens = new Set(Array.isArray(row[1].tokens) ? row[1].tokens : []);
              return tokenContainment(target.tokens, candTokens);
            }})
          : [];
        const avgTokenMatch = tokenMatchRatios.length
          ? (tokenMatchRatios.reduce((a, b) => a + b, 0) / tokenMatchRatios.length)
          : 1;
        let center = weightedQuantile(priceAxis, weightAxis, 0.5);
        let p25 = weightedQuantile(priceAxis, weightAxis, 0.25);
        let p75 = weightedQuantile(priceAxis, weightAxis, 0.75);
        if (center === null) {{
          return {{ error: "추정 계산에 실패했습니다.", target }};
        }}
        if (p25 === null) p25 = Math.min(...priceAxis);
        if (p75 === null) p75 = Math.max(...priceAxis);
        const absDev = priceAxis.map((x) => Math.abs(x - center));
        const mad = weightedQuantile(absDev, weightAxis, 0.5) || 0;
        const spread = Math.max((p75 - p25), mad * 1.8, center * 0.08, 0.08);
        let low = Math.max(0.05, center - spread * 0.55);
        let high = Math.max(low, center + spread * 0.55);

        const riskNotes = [].concat(target.scale_notes || []);
        if (!target.has_license_input) {{
          riskNotes.push("면허/업종 미입력: 전체 DB 유사도 기준으로 추정해 오차 범위가 넓어질 수 있습니다.");
        }} else if (!target.tokens.size) {{
          riskNotes.push("면허/업종이 일반 표현으로 입력되어 세부 면허명 기준 매칭이 제한될 수 있습니다.");
        }} else if (avgTokenMatch < 0.55) {{
          riskNotes.push("입력 면허와 완전 일치 매물 비중이 낮아 유사군 보정이 크게 반영되었습니다.");
        }}
        if (target.missing_critical.length) {{
          riskNotes.push(`핵심 항목 미입력: ${{target.missing_critical.join(" · ")}} (입력 시 정확도 향상)`);
        }}
        if (target.missing_guide.length) {{
          riskNotes.push(`추가 입력 권장: ${{target.missing_guide.join(" · ")}}`);
        }}
        let factor = 1.0;
        const applyRelative = (label, val, avg, weight, maxAdj) => {{
          if (!Number.isFinite(val) || !Number.isFinite(avg) || avg <= 0) return;
          const rel = (val - avg) / Math.max(avg, 0.1);
          const adj = Math.max(-maxAdj, Math.min(maxAdj, rel * weight));
          factor += adj;
          if (Math.abs(adj) >= 0.01) {{
            riskNotes.push(`${{label}} 반영: ${{adj >= 0 ? "+" : ""}}${{(adj * 100).toFixed(1)}}%`);
          }}
        }};
        const applyNeighborPercentile = (label, val, field, direction, weight, maxAdj, minSamples = 6) => {{
          if (!Number.isFinite(val)) return;
          const vals = neighbors
            .map((row) => num(row && row[1] ? row[1][field] : null))
            .filter((v) => Number.isFinite(v));
          if (vals.length < minSamples) return;
          vals.sort((a, b) => a - b);
          let le = 0;
          for (let i = 0; i < vals.length; i += 1) {{
            if (vals[i] <= val) le += 1;
          }}
          const pct = le / Math.max(1, vals.length);
          const centered = (pct - 0.5) * 2;
          const adjRaw = centered * weight * (direction >= 0 ? 1 : -1);
          const adj = clamp(adjRaw, -maxAdj, maxAdj);
          factor += adj;
          if (Math.abs(adj) >= 0.008) {{
            riskNotes.push(`${{label}} 유사군 분위 반영: ${{adj >= 0 ? "+" : ""}}${{(adj * 100).toFixed(1)}}%`);
          }}
        }};
        const applySalesTrend = () => {{
          const y23v = num(target.y23);
          const y24v = num(target.y24);
          const y25v = num(target.y25);
          if (!Number.isFinite(y23v) && !Number.isFinite(y24v) && !Number.isFinite(y25v)) return 0;
          let targetTrend = 0;
          let targetW = 0;
          if (Number.isFinite(y25v) && Number.isFinite(y24v) && Math.abs(y24v) > 0.1) {{
            targetTrend += ((y25v - y24v) / Math.max(Math.abs(y24v), 0.1)) * 0.64;
            targetW += 0.64;
          }}
          if (Number.isFinite(y25v) && Number.isFinite(y23v) && Math.abs(y23v) > 0.1) {{
            targetTrend += ((y25v - y23v) / Math.max(Math.abs(y23v), 0.1)) * 0.36;
            targetW += 0.36;
          }}
          if (targetW <= 0) return 0;
          targetTrend = clamp(targetTrend / targetW, -1.2, 1.2);

          const trendVals = [];
          const trendWts = [];
          neighbors.forEach(([sim, rec]) => {{
            const n23 = num(rec && rec.y23);
            const n25 = num(rec && rec.y25);
            if (!Number.isFinite(n23) || !Number.isFinite(n25) || Math.abs(n23) <= 0.1) return;
            const tr = (n25 - n23) / Math.max(Math.abs(n23), 0.1);
            if (!Number.isFinite(tr)) return;
            trendVals.push(clamp(tr, -1.6, 1.6));
            trendWts.push(Math.max(0.2, (Number(sim) || 0) / 40));
          }});

          let statAdj = 0;
          if (trendVals.length >= 4) {{
            const q50 = weightedQuantile(trendVals, trendWts, 0.50);
            const q25 = weightedQuantile(trendVals, trendWts, 0.25);
            const q75 = weightedQuantile(trendVals, trendWts, 0.75);
            const spread = Math.max(0.12, Math.abs((q75 || 0) - (q25 || 0)));
            const z = (targetTrend - (Number.isFinite(q50) ? q50 : 0)) / spread;
            statAdj = clamp(z * 0.028, -0.08, 0.10);
          }} else {{
            statAdj = clamp(targetTrend * 0.05, -0.05, 0.06);
          }}

          let recencyAdj = 0;
          if (Number.isFinite(y23v) && Number.isFinite(y24v) && Number.isFinite(y25v)) {{
            const late = (y25v - y24v) / Math.max(Math.abs(y24v), 0.1);
            const early = (y24v - y23v) / Math.max(Math.abs(y23v), 0.1);
            recencyAdj = clamp((late * 0.70 + early * 0.30) * 0.03, -0.03, 0.04);
          }}
          let horizonAdj = 0;
          if (Number.isFinite(y23v) && Number.isFinite(y25v) && Math.abs(y23v) > 0.1) {{
            const ratio = y25v / Math.max(Math.abs(y23v), 0.1);
            if (Number.isFinite(ratio) && ratio > 0) {{
              horizonAdj = clamp(Math.log(ratio) * 0.045, -0.06, 0.08);
            }}
          }}
          const adj = clamp(statAdj + recencyAdj + horizonAdj, -0.11, 0.14);
          if (Math.abs(adj) >= 0.008) {{
            riskNotes.push(`실적 추이 통계 반영(2023↔2025 가중): ${{adj >= 0 ? "+" : ""}}${{(adj * 100).toFixed(1)}}%`);
          }}
          return adj;
        }};
        if (!balanceExcluded) {{
          applyRelative("공제조합 잔액", target.balance_eok, num(meta.avg_balance_eok), 0.18, 0.22);
          applyNeighborPercentile("공제조합 잔액", num(target.balance_eok), "balance_eok", 1, 0.12, 0.16, 5);
        }} else {{
          riskNotes.push("전기/정보통신/소방 업종은 공제조합 잔액 별도 정산 관행을 반영해 가격 반영에서 제외했습니다.");
        }}
        applyRelative("자본금", target.capital_eok, num(meta.avg_capital_eok), 0.14, 0.18);
        applyRelative("이익잉여금", target.surplus_eok, num(meta.avg_surplus_eok), -0.14, 0.20);
        applyNeighborPercentile("자본금", num(target.capital_eok), "capital_eok", 1, 0.08, 0.10, 5);
        applyNeighborPercentile("이익잉여금", num(target.surplus_eok), "surplus_eok", -1, 0.10, 0.12, 5);
        applyNeighborPercentile("면허연도", num(target.license_year), "license_year", 1, 0.06, 0.08, 5);
        applyNeighborPercentile("시평", num(target.specialty), "specialty", 1, 0.04, 0.06, 6);
        applyNeighborPercentile("최근 3개년 매출", num(target.sales3_eok), "sales3_eok", 1, 0.05, 0.07, 6);
        applyNeighborPercentile("부채비율", num(target.debt_ratio), "debt_ratio", -1, 0.07, 0.09, 5);
        applyNeighborPercentile("유동비율", num(target.liq_ratio), "liq_ratio", 1, 0.07, 0.09, 5);
        factor = Math.max(0.70, Math.min(1.24, factor));
        center *= factor;
        low *= factor;
        high *= factor;
        const anchorInfo = buildFeatureAnchor(target, neighbors);
        const anchored = applyAnchorGuard(center, low, high, anchorInfo, riskNotes);
        center = anchored.center;
        low = anchored.low;
        high = anchored.high;
        if (anchorInfo && Array.isArray(anchorInfo.notes)) {{
          anchorInfo.notes.forEach((note) => {{
            if (note && riskNotes.indexOf(note) < 0) riskNotes.push(note);
          }});
        }}
        let postFactor = 1.0;
        if (!target.ok_capital) {{ postFactor -= 0.12; riskNotes.push("자본금 기준 미충족: 보수 하향"); }}
        if (!target.ok_engineer) {{ postFactor -= 0.16; riskNotes.push("기술자 기준 미충족: 리스크 증가"); }}
        if (!target.ok_office) {{ postFactor -= 0.10; riskNotes.push("사무실 기준 미충족: 리스크 증가"); }}
        if (target.ok_capital && target.ok_engineer && target.ok_office) postFactor += 0.03;
        if (target.debt_level === "above") {{ postFactor -= 0.06; riskNotes.push("부채비율 평균 이상: 보수 하향"); }}
        if (target.debt_level === "below") postFactor += 0.03;
        if (target.liq_level === "above") postFactor += 0.05;
        if (target.liq_level === "below") {{ postFactor -= 0.07; riskNotes.push("유동비율 평균 이하: 리스크 반영"); }}
        if (target.company_type === "개인") {{ postFactor -= 0.05; riskNotes.push("회사형태(개인사업자) 반영: 보수 하향"); }}
        else if (target.company_type === "주식회사") {{ postFactor += 0.01; }}
        else if (target.company_type === "유한회사") {{ postFactor -= 0.01; }}
        if (target.credit_level === "high") {{ postFactor += 0.05; riskNotes.push("외부신용등급 우수: 가산 반영"); }}
        else if (target.credit_level === "low") {{ postFactor -= 0.06; riskNotes.push("외부신용등급 주의: 감산 반영"); }}
        if (target.admin_history === "none") {{ postFactor += 0.03; }}
        else if (target.admin_history === "has") {{ postFactor -= 0.11; riskNotes.push("행정처분 이력 있음: 리스크 반영"); }}
        const postPercentileAdj = (label, val, field, direction, weight, maxAdj, minSamples = 6) => {{
          if (!Number.isFinite(val)) return 0;
          const vals = neighbors
            .map((row) => num(row && row[1] ? row[1][field] : null))
            .filter((v) => Number.isFinite(v));
          if (vals.length < minSamples) return 0;
          vals.sort((a, b) => a - b);
          let le = 0;
          for (let i = 0; i < vals.length; i += 1) {{
            if (vals[i] <= val) le += 1;
          }}
          const pct = le / Math.max(1, vals.length);
          const centered = (pct - 0.5) * 2;
          const adj = clamp(centered * weight * (direction >= 0 ? 1 : -1), -maxAdj, maxAdj);
          if (Math.abs(adj) >= 0.008) {{
            riskNotes.push(`${{label}} 세부 분위 보정: ${{adj >= 0 ? "+" : ""}}${{(adj * 100).toFixed(1)}}%`);
          }}
          return adj;
        }};
        postFactor += postPercentileAdj("시평", num(target.specialty), "specialty", 1, 0.05, 0.06, 6);
        postFactor += postPercentileAdj("최근 3개년 매출", num(target.sales3_eok), "sales3_eok", 1, 0.04, 0.05, 6);
        const specialtyLevelAdj = (() => {{
          const sp = num(target.specialty);
          const med = num(meta.median_specialty);
          if (!Number.isFinite(sp) || !Number.isFinite(med) || med <= 0) return 0;
          const ratio = sp / Math.max(med, 0.1);
          if (!Number.isFinite(ratio) || ratio <= 0) return 0;
          const adj = clamp(Math.log(ratio) * 0.045, -0.06, 0.08);
          if (Math.abs(adj) >= 0.008) {{
            riskNotes.push(`시평 레벨 반영: ${{adj >= 0 ? "+" : ""}}${{(adj * 100).toFixed(1)}}%`);
          }}
          return adj;
        }})();
        postFactor += specialtyLevelAdj;
        const licenseAgeAdj = (() => {{
          const y = num(target.license_year);
          if (!Number.isFinite(y) || y < 1950 || y > 2100) return 0;
          const age = Math.max(0, (new Date().getFullYear() - y));
          let adj = 0;
          if (age >= 12) adj += 0.03;
          else if (age >= 7) adj += 0.015;
          else if (age <= 2) adj -= 0.03;
          else if (age <= 4) adj -= 0.015;
          if (Math.abs(adj) >= 0.008) {{
            riskNotes.push(`면허 업력 반영: ${{adj >= 0 ? "+" : ""}}${{(adj * 100).toFixed(1)}}%`);
          }}
          return adj;
        }})();
        const surplusRiskAdj = (() => {{
          const surplus = num(target.surplus_eok);
          if (!Number.isFinite(surplus)) return 0;
          const capital = num(target.capital_eok);
          let adj = 0;
          if (Number.isFinite(capital) && capital > 0.05) {{
            const ratio = surplus / Math.max(0.05, capital);
            if (ratio >= 1.2) adj -= Math.min(0.08, (ratio - 1.2) * 0.04 + 0.02);
            else if (ratio >= 0.8) adj -= Math.min(0.05, (ratio - 0.8) * 0.05);
          }} else if (surplus >= 2.0) {{
            adj -= 0.03;
          }}
          if (Math.abs(adj) >= 0.008) {{
            riskNotes.push(`이익잉여금 리스크 반영: ${{adj >= 0 ? "+" : ""}}${{(adj * 100).toFixed(1)}}%`);
          }}
          return adj;
        }})();
        const surplusMonotonicAdj = (() => {{
          const surplus = num(target.surplus_eok);
          if (!Number.isFinite(surplus) || surplus <= 0) return 0;
          const capital = num(target.capital_eok);
          let adj = -Math.min(0.14, Math.log1p(Math.max(0, surplus)) * 0.055);
          if (Number.isFinite(capital) && capital > 0.05) {{
            const ratio = surplus / Math.max(0.05, capital);
            if (ratio >= 0.5) adj -= Math.min(0.06, (ratio - 0.5) * 0.04);
            if (ratio >= 1.2) adj -= Math.min(0.06, (ratio - 1.2) * 0.05);
          }}
          adj = clamp(adj, -0.22, 0);
          if (Math.abs(adj) >= 0.008) {{
            riskNotes.push(`이익잉여금 단조 감가 반영: ${{(adj * 100).toFixed(1)}}%`);
          }}
          return adj;
        }})();
        postFactor += applySalesTrend();
        postFactor += licenseAgeAdj;
        postFactor += surplusRiskAdj;
        postFactor += surplusMonotonicAdj;
        postFactor = Math.max(0.72, Math.min(1.24, postFactor));
        center *= postFactor;
        low *= postFactor;
        high *= postFactor;
        if (Math.abs(postFactor - 1) >= 0.01) {{
          riskNotes.push(`정성/리스크 종합 보정: ${{postFactor >= 1 ? "+" : ""}}${{((postFactor - 1) * 100).toFixed(1)}}%`);
        }}
        if (factor < 0.9) {{
          const extra = (high - low) * 0.08;
          low = Math.max(0.05, low - extra);
          high = high + extra;
        }}
        if (!target.has_license_input) {{
          const extra = (high - low) * 0.12;
          low = Math.max(0.05, low - extra);
          high = high + extra;
        }}
        if (avgTokenMatch < 0.55) {{
          const extra = (high - low) * 0.12;
          low = Math.max(0.05, low - extra);
          high = high + extra;
        }}
        if (target.missing_critical.length) {{
          const extra = (high - low) * (0.05 + (target.missing_critical.length * 0.04));
          low = Math.max(0.05, low - extra);
          high = high + extra;
        }}
        if (target.credit_level === "low" || target.admin_history === "has") {{
          const extra = (high - low) * 0.10;
          low = Math.max(0.05, low - extra);
          high = high + extra;
        }}
        if (!target.credit_level || !target.admin_history) {{
          riskNotes.push("외부신용등급/행정처분 이력을 입력하면 오차 범위를 더 줄일 수 있습니다.");
        }}
        const stabilized = stabilizeRangeByCoverage(target, center, low, high, riskNotes);
        center = stabilized.center;
        low = stabilized.low;
        high = stabilized.high;
        const avgSim = sims.reduce((a, b) => a + b, 0) / Math.max(1, sims.length);
        const discounted = applyUncertaintyDiscount(center, low, high, avgSim, neighbors.length, avgTokenMatch, riskNotes);
        center = discounted.center;
        low = discounted.low;
        high = discounted.high;
        const upperGuarded = applyUpperGuardBySimilarity(center, low, high, priceAxis, weightAxis, avgTokenMatch, neighbors.length, riskNotes);
        center = upperGuarded.center;
        low = upperGuarded.low;
        high = upperGuarded.high;
        const consistencyGuarded = applyNeighborConsistencyGuard(center, low, high, neighbors, avgTokenMatch, riskNotes, target);
        center = consistencyGuarded.center;
        low = consistencyGuarded.low;
        high = consistencyGuarded.high;
        const retainedPostNudge = clamp(1 + ((postFactor - 1) * 0.35), 0.92, 1.08);
        if (Math.abs(retainedPostNudge - 1) >= 0.005) {{
          center *= retainedPostNudge;
          low *= retainedPostNudge;
          high *= retainedPostNudge;
          riskNotes.push(`상한 보정 후 입력값 반영 유지: ${{retainedPostNudge >= 1 ? "+" : ""}}${{((retainedPostNudge - 1) * 100).toFixed(1)}}%`);
        }}
        let balanceAddition = 0;
        const balanceInput = num(target.balance_eok);
        if (!balanceExcluded && Number.isFinite(balanceInput) && balanceInput >= 0 && Number.isFinite(balanceSlope)) {{
          const slopeSafe = clamp(balanceSlope, 0.35, 1.02);
          const meanBalance = Number.isFinite(neighborBalanceMean) ? Number(neighborBalanceMean) : 0;
          const medianBalance = Number.isFinite(neighborBalanceMedian) ? Number(neighborBalanceMedian) : meanBalance;
          const balanceIqr = (Number.isFinite(neighborBalanceP25) && Number.isFinite(neighborBalanceP75))
            ? Math.max(0.08, Number(neighborBalanceP75) - Number(neighborBalanceP25))
            : 0.35;
          const balanceDelta = useBaseModel ? balanceInput : (balanceInput - meanBalance);
          const absDelta = Math.abs(balanceDelta);
          let damp = 1.0;
          if (absDelta > balanceIqr * 2.5) damp *= 0.72;
          if (absDelta > balanceIqr * 4.0) damp *= 0.56;
          if (absDelta > balanceIqr * 6.0) damp *= 0.42;
          if (Number.isFinite(medianBalance) && medianBalance > 0.05 && balanceInput > (medianBalance * 8)) {{
            damp *= 0.48;
            riskNotes.push("공제조합 잔액이 유사군 대비 과도해 보수적으로 반영했습니다.");
          }}
          if (Number.isFinite(balanceInput) && balanceInput > 200) {{
            damp *= 0.38;
            riskNotes.push("공제조합 잔액 단위 오입력 가능성을 감안해 영향도를 제한했습니다.");
          }}
          if (useBaseModel) {{
            balanceAddition = balanceInput * slopeSafe * damp;
          }} else {{
            balanceAddition = (balanceInput - meanBalance) * slopeSafe * damp;
          }}
          const p90Price = weightedQuantile(priceAxis, weightAxis, 0.90);
          const balanceCap = Number.isFinite(p90Price)
            ? Math.max(0.6, Math.min(p90Price * 0.78, center * 0.64))
            : Math.max(0.6, center * 0.60);
          balanceAddition = clamp(balanceAddition, -balanceCap, balanceCap);
          if (Number.isFinite(balanceAddition) && Math.abs(balanceAddition) > 0.001) {{
            center += balanceAddition;
            low = Math.max(0.05, low + (balanceAddition * 0.90));
            high = Math.max(low, high + (balanceAddition * 1.02));
            riskNotes.push("공제조합 잔액 입력값을 최종 합산 단계에서 반영했습니다.");
          }}
        }}
        if (neighbors.length <= 2) {{
          const extra = Math.max(center * 0.18, (high - low) * 0.45);
          low = Math.max(0.05, low - (extra * 0.45));
          high = Math.max(low, high + extra);
          riskNotes.push("근거 매물 수가 적어 오차 범위를 보수적으로 확장했습니다.");
        }}
        if (high < low) high = low;
        const coverage = Math.min(1, neighbors.length / 8);
        const dispersion = mad / Math.max(center, 0.1);
        let confidenceScore = (avgSim * 0.60) + (coverage * 24) + Math.max(0, 20 - dispersion * 60);
        if (avgSim >= 80) confidenceScore += 3;
        if (neighbors.length >= 8) confidenceScore += 4;
        if (avgTokenMatch >= 0.75) confidenceScore += 8;
        else if (avgTokenMatch >= 0.60) confidenceScore += 4;
        if (neighbors.length <= 2) confidenceScore -= 14;
        else if (neighbors.length <= 4) confidenceScore -= 6;
        const missingCritical = target.missing_critical.length;
        confidenceScore -= (missingCritical * 7);
        if (!target.has_license_input) confidenceScore -= 10;
        if (target.provided_signals <= 2) confidenceScore -= 8;
        confidenceScore -= (Math.abs(factor - 1.0) * 24);
        confidenceScore = Math.max(0, Math.min(100, confidenceScore));
        const confidence = `${{Math.round(confidenceScore)}}%`;
        if (!riskNotes.length) riskNotes.push("강한 영향 항목 입력이 없어 기본 유사 매물 기준으로 계산했습니다.");
        const yoy = buildYoyInsight(target, center, neighbors);
        return {{
          center,
          low,
          high,
          confidence,
          confidenceScore,
          balancePassThrough: Number.isFinite(balanceSlope) ? balanceSlope : null,
          balanceAdditionEok: Number.isFinite(balanceAddition) ? balanceAddition : null,
          avgSim,
          neighbor_count: neighbors.length,
          display_neighbor_count: displayNeighbors.length,
          neighbors: displayNeighbors,
          hotMatchCount,
          riskNotes,
          yoy,
          target,
        }};
      }};

      const estimateRemote = async (target) => {{
        if (!estimateEndpoint) {{
          return {{ error: "AI 서버 엔드포인트가 설정되지 않았습니다.", target }};
        }}
        const payload = {{
          mode: viewMode,
          license_text: target.license_raw || "",
          license_year: target.license_year,
          specialty: target.specialty,
          y23: target.y23,
          y24: target.y24,
          y25: target.y25,
          sales_input_mode: target.sales_input_mode || "yearly",
          sales3_eok: target.sales3_eok,
          sales5_eok: target.sales5_eok,
          balance_eok: target.balance_eok,
          capital_eok: target.capital_eok,
          surplus_eok: target.surplus_eok,
          debt_ratio: target.debt_ratio,
          liq_ratio: target.liq_ratio,
          company_type: target.company_type || "",
          credit_level: target.credit_level || "",
          admin_history: target.admin_history || "",
          ok_capital: !!target.ok_capital,
          ok_engineer: !!target.ok_engineer,
          ok_office: !!target.ok_office,
          missing_critical: Array.isArray(target.missing_critical) ? target.missing_critical : [],
          missing_guide: Array.isArray(target.missing_guide) ? target.missing_guide : [],
          provided_signals: Number(target.provided_signals || 0),
        }};
        try {{
          const res = await requestWithTimeout(estimateEndpoint, {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify(payload),
          }}, 8500);
          if (!res.ok) {{
            throw new Error(`HTTP ${{res.status}}`);
          }}
          const data = await res.json();
          let center = num(data.estimate_center_eok ?? data.center_eok ?? data.center);
          let low = num(data.estimate_low_eok ?? data.low_eok ?? data.low);
          let high = num(data.estimate_high_eok ?? data.high_eok ?? data.high);
          if (!Number.isFinite(center) || !Number.isFinite(low) || !Number.isFinite(high)) {{
            return {{ error: "AI 서버 응답 형식이 올바르지 않습니다.", target }};
          }}
          const strictSameCore = !!singleTokenTargetCore(target.tokens);
          const neighbors = Array.isArray(data.neighbors) ? data.neighbors.map((row) => {{
            const sim = Number(row.similarity ?? row.sim ?? 0);
            const rec = {{
              seoul_no: Number(row.seoul_no ?? row.no ?? 0),
              now_uid: String(row.now_uid || ""),
              license_text: String(row.license_text || row.license || ""),
              price_eok: Number(row.price_eok ?? row.center_eok ?? 0),
              display_low_eok: Number(row.display_low_eok ?? row.low_eok ?? row.range_low ?? 0),
              display_high_eok: Number(row.display_high_eok ?? row.high_eok ?? row.range_high ?? 0),
              y23: Number(row.y23 ?? row.sales_y23 ?? NaN),
              y24: Number(row.y24 ?? row.sales_y24 ?? NaN),
              y25: Number(row.y25 ?? row.sales_y25 ?? NaN),
              sales3_eok: Number(row.sales3_eok ?? row.sales3 ?? NaN),
              sales5_eok: Number(row.sales5_eok ?? row.sales5 ?? NaN),
              url: String(row.url || siteMna),
            }};
            return [Number.isFinite(sim) ? sim : 0, rec];
          }}).filter((row) => {{
            const rec = row && row[1] ? row[1] : null;
            const candTokens = licenseTokenSet((rec && rec.license_text) || "");
            if (strictSameCore && !isSingleTokenSameCore(target.tokens, candTokens, rec ? rec.license_text : "")) return false;
            if (isSingleTokenCrossCombo(target.tokens, candTokens, rec ? rec.license_text : "")) return false;
            if (isSingleTokenProfileOutlier(target, rec)) return false;
            return true;
          }}) : [];
          const confRaw = num(data.confidence_score ?? data.confidence_percent ?? data.confidence_value);
          const confidenceScore = Number.isFinite(confRaw) ? confRaw : null;
          const confidence = Number.isFinite(confidenceScore)
            ? `${{Math.round(confidenceScore)}}%`
            : (compact(data.confidence || data.confidence_label || "") || "-");
          const riskNotes = Array.isArray(data.risk_notes) && data.risk_notes.length
            ? data.risk_notes.map((x) => compact(x)).filter((x) => !!x)
            : ["AI 서버 결과를 기준으로 산정했습니다."];
          const avgSim = num(data.avg_similarity ?? data.avg_sim) || 0;
          const anchorFromNeighbors = (() => {{
            if (!Array.isArray(neighbors) || !neighbors.length) return null;
            const targetSpecialty = num(target.specialty);
            const targetSales3 = num(target.sales3_eok);
            const targetCapital = num(target.capital_eok);
            const components = [];
            const compW = [];
            const build = (targetValue, field, weight, lo, hi) => {{
              if (!Number.isFinite(targetValue) || targetValue <= 0) return;
              const ratios = [];
              const ratioW = [];
              neighbors.slice(0, 10).forEach(([sim, rec]) => {{
                const price = num(rec.price_eok);
                const base = num(rec[field]);
                if (!Number.isFinite(price) || !Number.isFinite(base) || base <= 0) return;
                const ratio = price / base;
                if (!Number.isFinite(ratio) || ratio < lo || ratio > hi) return;
                ratios.push(ratio);
                ratioW.push(Math.max(0.2, (Number(sim) || 0) / 45));
              }});
              if (ratios.length < 3) return;
              const q = weightedQuantile(ratios, ratioW, 0.5);
              if (!Number.isFinite(q) || q <= 0) return;
              components.push(targetValue * q);
              compW.push(weight);
            }};
            build(targetSpecialty, "specialty", 0.44, 0.004, 9.0);
            build(targetSales3, "sales3_eok", 0.26, 0.004, 9.0);
            build(targetCapital, "capital_eok", 0.12, 0.02, 15.0);
            if (!components.length) return null;
            const anchor = weightedMean(components, compW);
            if (!Number.isFinite(anchor) || anchor <= 0) return null;
            return anchor;
          }})();
          if (Number.isFinite(anchorFromNeighbors) && anchorFromNeighbors > 0) {{
            const ratio = center / anchorFromNeighbors;
            if (ratio < 0.58 || ratio > 1.72) {{
              const pull = Math.min(0.58, Math.max(0.18, Math.abs(ratio - 1) * 0.35));
              const adjustedCenter = (center * (1 - pull)) + (anchorFromNeighbors * pull);
              if (Number.isFinite(adjustedCenter) && adjustedCenter > 0) {{
                const scale = adjustedCenter / Math.max(center, 0.05);
                center = adjustedCenter;
                low = Math.max(0.05, low * scale);
                high = Math.max(low, high * scale);
                const widen = Math.max(0.03, (high - low) * 0.08);
                low = Math.max(0.05, low - widen);
                high = Math.max(low, high + widen);
                riskNotes.unshift(`유사군 스케일 보정 적용: ${{fmtEok(center)}} 기준으로 재조정`);
              }}
            }}
          }}
          const stabilizedRemote = stabilizeRangeByCoverage(target, center, low, high, riskNotes);
          center = stabilizedRemote.center;
          low = stabilizedRemote.low;
          high = stabilizedRemote.high;
          const remoteTokenMatchRatios = target.tokens.size
            ? neighbors.map((row) => {{
                const candidateTokens = licenseTokenSet((row && row[1] && row[1].license_text) || "");
                return tokenContainment(target.tokens, candidateTokens);
              }})
            : [];
          const avgRemoteTokenMatch = remoteTokenMatchRatios.length
            ? (remoteTokenMatchRatios.reduce((a, b) => a + b, 0) / remoteTokenMatchRatios.length)
            : 1;
          const discountedRemote = applyUncertaintyDiscount(center, low, high, avgSim, neighbors.length, avgRemoteTokenMatch, riskNotes);
          center = discountedRemote.center;
          low = discountedRemote.low;
          high = discountedRemote.high;
          const remotePrices = neighbors.map((x) => Number(x && x[1] && x[1].price_eok));
          const remoteSims = neighbors.map((x) => Number(x && x[0]));
          const upperGuardedRemote = applyUpperGuardBySimilarity(center, low, high, remotePrices, remoteSims, avgRemoteTokenMatch, neighbors.length, riskNotes);
          center = upperGuardedRemote.center;
          low = upperGuardedRemote.low;
          high = upperGuardedRemote.high;
          const consistencyGuardedRemote = applyNeighborConsistencyGuard(center, low, high, neighbors, avgRemoteTokenMatch, riskNotes, target);
          center = consistencyGuardedRemote.center;
          low = consistencyGuardedRemote.low;
          high = consistencyGuardedRemote.high;
          if (neighbors.length <= 2) {{
            const extra = Math.max(center * 0.18, (high - low) * 0.45);
            low = Math.max(0.05, low - (extra * 0.45));
            high = Math.max(low, high + extra);
            riskNotes.push("근거 매물 수가 적어 오차 범위를 보수적으로 확장했습니다.");
          }}
          const hotMatchCount = Number(data.hot_match_count || neighbors.filter((x) => Number(x[0]) >= 90).length || 0);
          const yoy = (() => {{
            const prevCenter = num(data.previous_estimate_eok ?? data.yoy_previous_eok ?? data.prev_center_eok);
            const changePctRaw = num(data.yoy_change_pct ?? data.yoy_percent ?? data.prev_change_pct);
            if (Number.isFinite(prevCenter) && prevCenter > 0) {{
              const currYear = Number(data.current_year || new Date().getFullYear());
              const prevYear = Number(data.previous_year || (currYear > 0 ? currYear - 1 : 0));
              const pct = Number.isFinite(changePctRaw) ? changePctRaw : (((center / prevCenter) - 1) * 100);
              return {{
                current_year: currYear,
                previous_year: prevYear,
                previous_center: prevCenter,
                change_pct: pct,
                basis: compact(data.yoy_basis || "AI 서버 전년 비교"),
              }};
            }}
            return buildYoyInsight(target, center, neighbors);
          }})();
          let finalConfidenceScore = Number.isFinite(confidenceScore) ? confidenceScore : avgSim;
          if (neighbors.length <= 2) finalConfidenceScore -= 14;
          else if (neighbors.length <= 4) finalConfidenceScore -= 6;
          if (Number.isFinite(discountedRemote.discount) && discountedRemote.discount > 0) {{
            finalConfidenceScore = Math.max(0, finalConfidenceScore - (discountedRemote.discount * 40));
          }}
          const finalConfidence = `${{Math.round(Math.max(0, Math.min(100, finalConfidenceScore)))}}%`;
          return {{
            center,
            low,
            high,
            confidence: finalConfidence || confidence,
            confidenceScore: finalConfidenceScore,
            avgSim,
            neighbors,
            hotMatchCount,
            riskNotes,
            yoy,
            target,
          }};
        }} catch (e) {{
          const msg = (e && e.name === "AbortError")
            ? "요청시간 초과"
            : (e && e.message ? e.message : "network_error");
          return {{ error: `AI 서버 연결 실패: ${{msg}}`, target }};
        }}
      }};

      const estimate = async () => {{
        const target = formInput();
        if (!target.has_any_signal) {{
          return {{ error: "입력된 정보가 없습니다. 면허/업종 또는 숫자 항목 1개 이상 입력해 주세요.", target }};
        }}
        if (estimateEndpoint) {{
          const remoteOut = await estimateRemote(target);
          if (!remoteOut.error) return remoteOut;
          if (!dataset.length) return remoteOut;
          const localOut = estimateLocal(target);
          if (!localOut.error) {{
            localOut.riskNotes = [
              "AI 서버 응답 지연으로 로컬 산정 엔진으로 전환했습니다.",
            ].concat(Array.isArray(localOut.riskNotes) ? localOut.riskNotes : []);
          }}
          return localOut;
        }}
        if (!dataset.length) {{
          return {{ error: "산정 데이터가 준비되지 않았습니다. 잠시 후 다시 시도해 주세요.", target }};
        }}
        return estimateLocal(target);
      }};

      const sanitizePlain = (v, maxLen = 120) => {{
        let s = compact(v).replace(/[\u0000-\u001f\u007f]/g, "");
        if (s.length > maxLen) s = s.slice(0, maxLen);
        return s;
      }};
      const sanitizePhone = (v) => {{
        const d = String(v || "").replace(/[^0-9]/g, "").slice(0, 11);
        if (!d) return "";
        if (d.length === 11) return `${{d.slice(0, 3)}}-${{d.slice(3, 7)}}-${{d.slice(7)}}`;
        if (d.length === 10) return `${{d.slice(0, 3)}}-${{d.slice(3, 6)}}-${{d.slice(6)}}`;
        return d;
      }};
      const sanitizeEmail = (v) => {{
        const e = sanitizePlain(v, 120).toLowerCase();
        if (!e) return "";
        return /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(e) ? e : "";
      }};

      const buildConsultPayload = () => {{
        const name = sanitizePlain($("consult-name").value, 40);
        const phone = sanitizePhone($("consult-phone").value);
        const email = sanitizeEmail($("consult-email").value);
        const note = sanitizePlain($("consult-note").value, 500);
        const license = sanitizePlain($("in-license").value, 120);
        const center = compact($("out-center").textContent);
        const range = compact($("out-range").textContent);
        const confidence = compact($("out-confidence").textContent);
        const neighbors = compact($("out-neighbors").textContent);
        const yoyText = compact($("out-yoy-compare").textContent);
        const risk = compact($("risk-note").textContent);
        const lines = [
          "서울건설정보 AI 산정 상담 요청",
          "",
          `[고객] ${{name || "-"}} / ${{phone || "-"}} / ${{email || "-"}}`,
          `[면허] ${{license || "-"}}`,
          `[산정] 기준가 ${{center || "-"}} · 범위 ${{range || "-"}} · 신뢰지수 ${{confidence || "-"}} · 근거 ${{neighbors || "-"}}`,
          `[전년 비교] ${{yoyText || "-"}}`,
          `[실적모드] ${{compact($("in-sales-input-mode").value) || "-"}}`,
          `[핵심 입력] 시평 ${{compact($("in-specialty").value) || "-"}}억 · 2023 ${{compact($("in-y23").value) || "-"}}억 · 2024 ${{compact($("in-y24").value) || "-"}}억 · 2025 ${{compact($("in-y25").value) || "-"}}억 · 3년합계 ${{compact($("in-sales3-total").value) || "-"}}억 · 5년합계 ${{compact($("in-sales5-total").value) || "-"}}억`,
          `[재무 입력] 공제잔액 ${{compact($("in-balance").value) || "-"}}억 · 자본금 ${{compact($("in-capital").value) || "-"}}억 · 이익잉여금 ${{compact($("in-surplus").value) || "-"}}억`,
          `[추가 입력] 회사형태 ${{compact($("in-company-type").value) || "-"}} · 외부신용등급 ${{compact($("in-credit-level").value) || "-"}} · 행정처분이력 ${{compact($("in-admin-history").value) || "-"}}`,
          `[메모] ${{note || "-"}}`,
          `[리스크 요약] ${{risk || "-"}}`,
          "",
          `페이지: ${{window.location.href}}`,
          `시각: ${{new Date().toLocaleString()}}`,
        ];
        const subjectBase = `${{consultSubjectPrefix}}${{license ? " | " + license : ""}}`;
        return {{
          subject: subjectBase.slice(0, 120),
          body: lines.join("\\n"),
          name: name,
          phone: phone,
          email: email,
          note: note,
          license: license,
          result_center: center,
          result_range: range,
          result_confidence: confidence,
          result_neighbors: neighbors,
          result_yoy: yoyText,
          company_type: compact($("in-company-type").value),
          credit_level: compact($("in-credit-level").value),
          admin_history: compact($("in-admin-history").value),
        }};
      }};

      const syncConsultSummary = () => {{
        const payload = buildConsultPayload();
        const summary = $("consult-summary");
        if (summary) summary.value = payload.body;
      }};

      const openOpenchatWithSummary = (payload = null) => {{
        if (!consultOpenchatUrl) {{
          alert("오픈채팅 URL이 아직 설정되지 않았습니다. 전화 또는 메일로 문의해 주세요.");
          return;
        }}
        const data = payload || buildConsultPayload();
        const text = data.body || "";
        const openChat = () => window.open(consultOpenchatUrl, "_blank", "noopener,noreferrer");
        if (!text) {{
          openChat();
          return;
        }}
        navigator.clipboard.writeText(text).then(() => {{
          alert("요약을 복사했습니다. 오픈채팅창에 붙여넣어 주세요.");
          openChat();
        }}).catch(() => {{
          openChat();
        }});
      }};

      const sendUsageLog = (target, out, status = "ok", errorText = "") => {{
        if (!usageEndpoint) return;
        const payload = {{
          source: "seoulmna_kr_yangdo_ai",
          page_mode: viewMode,
          status: compact(status || "ok"),
          error_text: compact(errorText || ""),
          license_text: compact($("in-license").value),
          input_specialty: compact($("in-specialty").value),
          input_sales_mode: compact(($("in-sales-input-mode") || {{}}).value),
          input_y23: compact($("in-y23").value),
          input_y24: compact($("in-y24").value),
          input_y25: compact($("in-y25").value),
          input_sales3_total: compact(($("in-sales3-total") || {{}}).value),
          input_sales5_total: compact(($("in-sales5-total") || {{}}).value),
          input_balance: compact($("in-balance").value),
          input_capital: compact($("in-capital").value),
          input_surplus: compact($("in-surplus").value),
          input_company_type: compact($("in-company-type").value),
          input_credit_level: compact($("in-credit-level").value),
          input_admin_history: compact($("in-admin-history").value),
          input_debt_level: compact($("in-debt-level").value),
          input_liq_level: compact($("in-liq-level").value),
          ok_capital: !!$("ok-capital").checked,
          ok_engineer: !!$("ok-engineer").checked,
          ok_office: !!$("ok-office").checked,
          output_center: out && Number.isFinite(out.center) ? fmtEok(out.center) : "-",
          output_range: out && Number.isFinite(out.low) && Number.isFinite(out.high) ? buildDisplayRange(out.low, out.high).text : "-",
          output_confidence: out ? `${{out.confidence || "-"}}` : "-",
          output_neighbors: out && out.neighbors ? `${{out.neighbors.length}}건` : "-",
          output_yoy: compact($("out-yoy-compare").textContent),
          missing_critical: target && target.missing_critical ? target.missing_critical.join(",") : "",
          page_url: window.location.href,
          requested_at: new Date().toISOString(),
        }};
        requestWithTimeout(usageEndpoint, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload),
        }}, 5000).catch(() => {{}});
      }};

      const sendHotMatchLead = async () => {{
        if (!lastEstimate) return;
        const payload = buildConsultPayload();
        sendUsageLog(lastEstimate.target || null, lastEstimate, "hot_match_click", "");
        if (!consultEndpoint) return;
        if (!payload.name || (!payload.phone && !payload.email)) return;
        try {{
          await requestWithTimeout(consultEndpoint, {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
              source: "seoulmna_kr_hot_match",
              page_mode: viewMode,
              lead_type: "hot_match",
              subject: `[고객] 90%+ 매칭 리포트 요청${{payload.license ? " | " + payload.license : ""}}`,
              summary_text: payload.body,
              customer_name: payload.name,
              customer_phone: payload.phone,
              customer_email: payload.email,
              customer_note: payload.note,
              license_text: payload.license,
              estimated_center: payload.result_center,
              estimated_range: payload.result_range,
              estimated_confidence: payload.result_confidence,
              estimated_neighbors: payload.result_neighbors,
              page_url: window.location.href,
              requested_at: new Date().toISOString(),
            }}),
          }}, 9000);
        }} catch (_e) {{}}
      }};

      const renderNeighborHead = () => {{
        const head = $("neighbor-head");
        if (viewMode === "owner") {{
          head.innerHTML = "<tr><th>서울건설정보 매물번호</th><th>now UID</th><th>업종</th><th>기준가(억)</th><th>오차 범위(억)</th><th>유사도</th><th>링크</th></tr>";
          return 7;
        }}
        head.innerHTML = "<tr><th>매물번호</th><th>업종</th><th>오차 범위(억)</th><th>유사도</th><th>링크</th></tr>";
        return 5;
      }};

      const renderNeighbors = (rows) => {{
        const body = $("neighbor-body");
        const colCount = renderNeighborHead();
        if (!rows || !rows.length) {{
          body.innerHTML = `<tr><td colspan="${{colCount}}" class='small'>근거 매물이 없습니다.</td></tr>`;
          return;
        }}
        body.innerHTML = rows.slice(0, 8).map(([sim, rec]) => {{
          const seoulNo = Number(rec.seoul_no || 0);
          const nowUid = (rec.now_uid || "").toString();
          const name = escapeHtml(compact(rec.license_text) || "-");
          const url = safeUrl(rec.url || siteMna, siteMna);
          const low = Number(rec.display_low_eok);
          const high = Number(rec.display_high_eok);
          const rangeText = `${{fmtEok(low)}}~${{fmtEok(high)}}`;
          const simText = escapeHtml((Math.round(sim * 10) / 10).toFixed(1));
          if (viewMode === "owner") {{
            return `<tr>
              <td>${{seoulNo > 0 ? seoulNo : "-"}}</td>
              <td>${{escapeHtml(nowUid || "-")}}</td>
              <td>${{name}}</td>
              <td>${{fmtEok(Number(rec.price_eok))}}</td>
              <td>${{rangeText}}</td>
              <td>${{simText}}</td>
              <td><a href="${{url}}" target="_blank" rel="noopener">상세</a></td>
            </tr>`;
          }}
          return `<tr>
            <td>${{seoulNo > 0 ? seoulNo : "-"}}</td>
            <td>${{name}}</td>
            <td>${{rangeText}}</td>
            <td>${{simText}}</td>
            <td><a href="${{url}}" target="_blank" rel="noopener">상세 보기</a></td>
          </tr>`;
        }}).join("");
      }};

      const renderActionSteps = (out, targetOverride = null) => {{
        const list = $("recommend-actions");
        if (!list) return;
        const t = targetOverride || (out && out.target ? out.target : null);
        const items = [];
        if (!t) {{
          items.push("면허/업종 + 공제조합 잔액을 먼저 입력해 오차 범위를 줄입니다.");
          items.push("실적 입력방식(연도별/3년/5년)을 선택한 뒤 AI 계산 결과의 신뢰지수(%)를 확인합니다.");
          items.push("상담 접수하기로 현재 결과를 즉시 전달합니다.");
          list.innerHTML = items.map((x) => `<li>${{x}}</li>`).join("");
          return;
        }}
        if (t.missing_critical && t.missing_critical.length) {{
          items.push(`핵심 항목(${{t.missing_critical.join(" · ")}})을 추가 입력해 오차를 먼저 줄이세요.`);
        }} else {{
          items.push("핵심 항목(공제조합 잔액·자본금·이익잉여금)이 충분하면 신뢰지수가 안정적으로 유지됩니다.");
        }}
        if (out && Number.isFinite(out.confidenceScore)) {{
          if (out.confidenceScore >= 70) {{
            items.push("근거 매물과 오차 범위를 비교한 뒤 거래 희망 범위를 좁혀 상담 준비를 진행하세요.");
          }} else {{
            items.push("입력 정보가 적어 예측 범위가 넓게 제시되었습니다. 면허/시평/매출을 보강해 다시 계산해 보세요.");
          }}
        }} else {{
          items.push("시평·매출 입력값을 보강하면 AI가 더 좁은 범위를 제시할 수 있습니다.");
        }}
        items.push("상담 접수하기를 눌러 현재 계산 결과를 전송하면 우선순위 리드로 자동 등록됩니다.");
        list.innerHTML = items.slice(0, 3).map((x) => `<li>${{x}}</li>`).join("");
      }};

      const buildPublicResultMessage = (out) => {{
        if (!out) return "AI 산정 결과가 준비되지 않았습니다.";
        const lines = [];
        const neighborCount = Number.isFinite(Number(out && out.neighbor_count))
          ? Number(out.neighbor_count)
          : (out && out.neighbors ? out.neighbors.length : 0);
        lines.push(`AI 산정 완료: 근거 매물 ${{neighborCount}}건 + 유사도 기반으로 결과를 계산했습니다.`);
        const target = out && out.target ? out.target : null;
        const scaleNotes = target && Array.isArray(target.scale_notes) ? target.scale_notes : [];
        const unitFix = scaleNotes.find((x) => String(x || "").indexOf("공제조합 잔액") >= 0);
        if (unitFix) {{
          lines.push("공제조합 잔액 단위가 의심되어 자동 보정 후 계산했습니다.");
        }}
        if (Number.isFinite(out.balanceAdditionEok) && Math.abs(out.balanceAdditionEok) > 0.01) {{
          lines.push("공제조합 잔액은 최종 합산 단계에서 반영되었습니다.");
        }}
        if (Number.isFinite(out.confidenceScore) && out.confidenceScore < 70) {{
          lines.push("신뢰도를 높이려면 면허·시평·최근 실적·공제조합 잔액을 보강해 다시 계산해 주세요.");
        }} else {{
          lines.push("결과를 1:1 상담으로 전송하면 실제 매수수요 기준으로 빠르게 검증할 수 있습니다.");
        }}
        return lines.map((x) => `• ${{escapeHtml(x)}}`).join("<br>");
      }};

      const updateHotMatchCta = (out) => {{
        const wrap = $("hot-match-cta");
        const msg = $("hot-match-msg");
        if (!wrap || !msg || !out) return;
        const count = Number(out.hotMatchCount || 0);
        if (count <= 0) {{
          wrap.style.display = "none";
          return;
        }}
        if (count >= 3) {{
          msg.textContent = "현재 보유하신 면허와 매칭률이 90% 이상인 대기 매수자가 3명 있습니다. 상세 리포트를 카카오톡으로 받으시겠습니까?";
        }} else {{
          msg.textContent = `현재 보유하신 면허와 매칭률이 90% 이상인 대기 매수자가 ${{count}}명 있습니다. 상세 리포트를 카카오톡으로 받으시겠습니까?`;
        }}
        wrap.style.display = "block";
      }};

      const setMeta = () => {{
        $("meta-all").textContent = (meta.all_record_count || 0).toLocaleString();
        $("meta-train").textContent = (meta.train_count || 0).toLocaleString();
        $("meta-mid").textContent = fmtEok(Number(meta.median_price_eok));
        $("meta-updated").textContent = String(meta.generated_at || "-");
        const avgDebt = num(meta.avg_debt_ratio);
        const avgLiq = num(meta.avg_liq_ratio);
        const parts = [];
        if (Number.isFinite(avgDebt)) parts.push(`평균 부채비율 ${{avgDebt.toFixed(1)}}%`);
        if (Number.isFinite(avgLiq)) parts.push(`평균 유동비율 ${{avgLiq.toFixed(1)}}%`);
        const avgText = parts.length ? parts.join(" · ") : "평균 지표가 부족해 일부 항목은 자동 계산에서 제외됩니다.";
        $("avg-guide").textContent = avgText;
        const qualityBox = $("data-quality-box");
        if (qualityBox) {{
          qualityBox.textContent = `가격학습 건수 ${{(meta.train_count || 0).toLocaleString()}}건 · 갱신시각 ${{String(meta.generated_at || "-")}}`;
        }}
      }};

      const syncSalesInputModeUi = () => {{
        const modeNode = $("in-sales-input-mode");
        const mode = compact(modeNode ? modeNode.value : "") || "yearly";
        const disable = (id, disabled) => {{
          const node = $(id);
          if (!node) return;
          node.disabled = !!disabled;
          node.style.background = disabled ? "#f0f4f9" : "";
          node.style.opacity = disabled ? "0.78" : "";
        }};
        if (mode === "yearly") {{
          disable("in-y23", false);
          disable("in-y24", false);
          disable("in-y25", false);
          disable("in-sales3-total", false);
          disable("in-sales5-total", false);
        }} else if (mode === "sales3") {{
          disable("in-y23", true);
          disable("in-y24", true);
          disable("in-y25", true);
          disable("in-sales3-total", false);
          disable("in-sales5-total", false);
        }} else {{
          disable("in-y23", true);
          disable("in-y24", true);
          disable("in-y25", true);
          disable("in-sales3-total", false);
          disable("in-sales5-total", false);
        }}
      }};

      const draftFieldIds = [
        "in-license", "in-license-year", "in-specialty", "in-sales-input-mode", "in-y23", "in-y24", "in-y25", "in-sales3-total", "in-sales5-total",
        "in-balance", "in-capital", "in-surplus", "in-company-type", "in-credit-level",
        "in-admin-history", "in-debt-level", "in-liq-level", "consult-name", "consult-phone",
        "consult-email", "consult-note",
      ];
      const draftToggleIds = ["ok-capital", "ok-engineer", "ok-office", "consult-consent"];
      const persistDraft = () => {{
        try {{
          const payload = {{
            saved_at: new Date().toISOString(),
            fields: {{}},
            toggles: {{}},
          }};
          draftFieldIds.forEach((id) => {{
            const node = $(id);
            if (!node) return;
            payload.fields[id] = String(node.value || "");
          }});
          draftToggleIds.forEach((id) => {{
            const node = $(id);
            if (!node) return;
            payload.toggles[id] = !!node.checked;
          }});
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
          Object.keys(fields).forEach((id) => {{
            const node = $(id);
            if (!node) return;
            const v = fields[id];
            if (v === null || v === undefined) return;
            node.value = String(v);
          }});
          Object.keys(toggles).forEach((id) => {{
            const node = $(id);
            if (!node) return;
            node.checked = !!toggles[id];
          }});
          return true;
        }} catch (_e) {{
          return false;
        }}
      }};
      const clearDraft = () => {{
        try {{ localStorage.removeItem(draftStorageKey); }} catch (_e) {{}}
      }};

      const resetForm = () => {{
        $("in-license").value = "";
        $("in-license-year").value = "";
        $("in-specialty").value = "";
        $("in-sales-input-mode").value = "yearly";
        $("in-y23").value = "";
        $("in-y24").value = "";
        $("in-y25").value = "";
        $("in-sales3-total").value = "";
        $("in-sales5-total").value = "";
        $("in-balance").value = "";
        $("in-capital").value = "";
        $("in-surplus").value = "";
        $("in-company-type").value = "";
        $("in-credit-level").value = "";
        $("in-admin-history").value = "";
        $("in-debt-level").value = "auto";
        $("in-liq-level").value = "auto";
        $("ok-capital").checked = true;
        $("ok-engineer").checked = true;
        $("ok-office").checked = true;
        $("out-center").textContent = "-";
        $("out-range").textContent = "-";
        $("out-confidence").textContent = "-";
        $("out-neighbors").textContent = "-";
        renderYoyCompare(null);
        $("risk-note").textContent = "AI 산정 전: 면허·시평·실적 입력방식(연도별/3년/5년)·공제조합 잔액을 입력하면 결과 정확도가 올라갑니다.";
        const hotCta = $("hot-match-cta");
        if (hotCta) hotCta.style.display = "none";
        lastEstimate = null;
        renderNeighbors([]);
        renderActionSteps(null);
        syncSalesInputModeUi();
        syncConsultSummary();
        clearDraft();
      }};

      // Apply meta counters before optional contact widgets to avoid late-stage rendering gaps.
      setMeta();
      const on = (id, eventName, handler) => {{
        const node = $(id);
        if (!node) return false;
        node.addEventListener(eventName, handler);
        return true;
      }};
      const ensureConsultConsent = () => {{
        const node = $("consult-consent");
        if (!node) return true;
        if (node.checked) return true;
        alert("개인정보 수집·이용 안내 동의 후 상담 요청을 진행해 주세요.");
        return false;
      }};
      const setEstimateBusy = (busy) => {{
        const btn = $("btn-estimate");
        if (!btn) return;
        isEstimating = !!busy;
        btn.disabled = !!busy;
        btn.style.opacity = busy ? "0.72" : "";
        btn.style.cursor = busy ? "wait" : "";
        btn.textContent = busy ? "AI 계산 중..." : "AI 예상 양도가 계산";
      }};

      on("btn-estimate", "click", async () => {{
        if (isEstimating) return;
        const nowTs = Date.now();
        if ((nowTs - lastEstimateClickAt) < 700) return;
        lastEstimateClickAt = nowTs;
        setEstimateBusy(true);
        try {{
          setMeta();
          const out = await estimate();
          if (out.error) {{
            $("out-center").textContent = "-";
            $("out-range").textContent = "-";
            $("out-confidence").textContent = "-";
            $("out-neighbors").textContent = "-";
            renderYoyCompare(null);
            $("risk-note").textContent = out.error;
            const hotCta = $("hot-match-cta");
            if (hotCta) hotCta.style.display = "none";
            if (out.error.indexOf("입력된 정보가 없습니다") >= 0) {{
              alert(out.error);
            }}
            lastEstimate = null;
            renderNeighbors([]);
            renderActionSteps(out, out.target || null);
            sendUsageLog(out.target || null, null, "error", out.error || "");
            syncConsultSummary();
            return;
          }}
          lastEstimate = out;
          $("out-center").textContent = fmtEok(out.center);
          $("out-range").textContent = buildDisplayRange(out.low, out.high).text;
          $("out-confidence").textContent = out.confidence;
          const neighborCountText = Number.isFinite(Number(out.neighbor_count))
            ? Number(out.neighbor_count)
            : ((out.neighbors && out.neighbors.length) ? out.neighbors.length : 0);
          $("out-neighbors").textContent = `${{neighborCountText}}건`;
          renderYoyCompare(out);
          $("risk-note").innerHTML = buildPublicResultMessage(out);
          renderNeighbors(out.neighbors);
          updateHotMatchCta(out);
          renderActionSteps(out);
          sendUsageLog(out.target || null, out, "ok", "");
          syncConsultSummary();
          persistDraft();
        }} catch (e) {{
          const msg = (e && e.message) ? String(e.message) : "unknown_error";
          $("out-center").textContent = "-";
          $("out-range").textContent = "-";
          $("out-confidence").textContent = "-";
          $("out-neighbors").textContent = "-";
          renderYoyCompare(null);
          $("risk-note").textContent = "계산 중 예외가 발생했습니다. 잠시 후 다시 시도해 주세요.";
          renderNeighbors([]);
          renderActionSteps(null);
          sendUsageLog(null, null, "error", msg);
          if (window.console) {{
            try {{ console.error("[smna-calc] estimate runtime error", e); }} catch (_e) {{}}
          }}
        }} finally {{
          setEstimateBusy(false);
        }}
      }});
      on("btn-mail-consult", "click", () => {{
        if (!lastEstimate) {{
          alert("먼저 예상 양도가 계산을 완료해 주세요.");
          return;
        }}
        if (!ensureConsultConsent()) return;
        const name = sanitizePlain($("consult-name").value, 40);
        const phone = sanitizePhone($("consult-phone").value);
        const email = sanitizeEmail($("consult-email").value);
        if (!name || (!phone && !email)) {{
          alert("성함과 연락처(또는 이메일)를 입력해 주세요.");
          return;
        }}
        const payload = buildConsultPayload();
        const href = `mailto:${{consultEmail}}?subject=${{encodeURIComponent(payload.subject)}}&body=${{encodeURIComponent(payload.body)}}`;
        window.location.href = href;
      }});
      on("btn-openchat-consult", "click", () => {{
        if (!lastEstimate) {{
          alert("먼저 예상 양도가 계산을 완료하면 결과 요약을 함께 보낼 수 있습니다.");
        }}
        if (!ensureConsultConsent()) return;
        const payload = buildConsultPayload();
        openOpenchatWithSummary(payload);
      }});
      on("btn-openchat-result", "click", () => {{
        if (!lastEstimate) {{
          alert("먼저 예상 양도가 계산을 완료해 주세요.");
          return;
        }}
        openOpenchatWithSummary(buildConsultPayload());
      }});
      on("btn-email-result", "click", () => {{
        if (!lastEstimate) {{
          alert("먼저 예상 양도가 계산을 완료해 주세요.");
          return;
        }}
        const payload = buildConsultPayload();
        const subject = `[결과전달] ${{payload.license || "건설면허"}} 예상 양도가`;
        const href = `mailto:${{consultEmail}}?subject=${{encodeURIComponent(subject)}}&body=${{encodeURIComponent(payload.body)}}`;
        window.location.href = href;
      }});
      on("btn-hot-match", "click", () => {{
        if (!lastEstimate) {{
          alert("먼저 AI 예상 양도가 계산을 진행해 주세요.");
          return;
        }}
        const consultPanel = document.querySelector("details.consult-panel");
        if (consultPanel) consultPanel.open = true;
        const note = $("consult-note");
        if (note) {{
          const existing = compact(note.value);
          const suffix = "90%+ 매칭 대기 매수자 상세 리포트 요청";
          note.value = existing ? `${{existing}} | ${{suffix}}` : suffix;
        }}
        sendHotMatchLead();
        syncConsultSummary();
        openOpenchatWithSummary(buildConsultPayload());
      }});
      on("btn-hot-match-copy", "click", async () => {{
        const consultPanel = document.querySelector("details.consult-panel");
        if (consultPanel) consultPanel.open = true;
        const payload = buildConsultPayload();
        sendHotMatchLead();
        try {{
          await navigator.clipboard.writeText(payload.body);
          alert("상세 리포트 요약이 복사되었습니다. 상담 요청 양식에 연락처를 입력한 뒤 전송해 주세요.");
        }} catch (_e) {{
          alert("요약 복사에 실패했습니다. 상담 요청 영역에서 다시 시도해 주세요.");
        }}
      }});
      on("btn-submit-consult", "click", async () => {{
        if (isSubmittingConsult) return;
        if (!lastEstimate) {{
          alert("먼저 예상 양도가 계산을 완료해 주세요.");
          return;
        }}
        if (!ensureConsultConsent()) return;
        const payload = buildConsultPayload();
        if (!payload.name || (!payload.phone && !payload.email)) {{
          alert("성함과 연락처(또는 이메일)를 입력해 주세요.");
          return;
        }}
        if (!consultEndpoint) {{
          openOpenchatWithSummary(payload);
          return;
        }}
        const submitBtn = $("btn-submit-consult");
        const submitBtnPrevText = submitBtn ? String(submitBtn.textContent || "") : "";
        isSubmittingConsult = true;
        if (submitBtn) {{
          submitBtn.disabled = true;
          submitBtn.style.opacity = "0.72";
          submitBtn.style.cursor = "wait";
          submitBtn.textContent = "상담 접수 전송 중...";
        }}
        try {{
          const res = await requestWithTimeout(consultEndpoint, {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
              source: "seoulmna_kr_yangdo_ai",
              page_mode: viewMode,
              subject: payload.subject,
              summary_text: payload.body,
              customer_name: payload.name,
              customer_phone: payload.phone,
              customer_email: payload.email,
              customer_note: payload.note,
              license_text: payload.license,
              input_company_type: payload.company_type,
              input_credit_level: payload.credit_level,
              input_admin_history: payload.admin_history,
              estimated_center: payload.result_center,
              estimated_range: payload.result_range,
              estimated_confidence: payload.result_confidence,
              estimated_neighbors: payload.result_neighbors,
              page_url: window.location.href,
              requested_at: new Date().toISOString(),
            }}),
          }}, 10000);
          if (!res.ok) {{
            throw new Error(`HTTP ${{res.status}}`);
          }}
          const data = await res.json().catch(() => ({{}}));
          const priority = compact(data.lead_priority || "");
          if (priority) {{
            alert(`상담 접수가 완료되었습니다. (${{priority}} 우선순위로 등록) 빠르게 연락드리겠습니다.`);
          }} else {{
            alert("상담 접수가 완료되었습니다. 빠르게 연락드리겠습니다.");
          }}
        }} catch (e) {{
          alert("상담 접수 중 오류가 발생했습니다. 오픈채팅으로 연결합니다.");
          openOpenchatWithSummary(payload);
        }} finally {{
          isSubmittingConsult = false;
          if (submitBtn) {{
            submitBtn.disabled = false;
            submitBtn.style.opacity = "";
            submitBtn.style.cursor = "";
            submitBtn.textContent = submitBtnPrevText || "상담 접수하기";
          }}
        }}
      }});
      on("btn-copy-consult", "click", async () => {{
        const payload = buildConsultPayload();
        try {{
          await navigator.clipboard.writeText(payload.body);
          alert("상담 요약이 복사되었습니다.");
        }} catch (_e) {{
          const summary = $("consult-summary");
          if (summary) {{
            summary.focus();
            summary.select();
            document.execCommand("copy");
          }}
          alert("상담 요약이 복사되었습니다.");
        }}
      }});
      ["consult-name", "consult-phone", "consult-email", "consult-note", "in-company-type", "in-credit-level", "in-admin-history", "in-sales-input-mode", "in-sales3-total", "in-sales5-total", "in-y23", "in-y24", "in-y25"].forEach((id) => {{
        const el = $(id);
        if (!el) return;
        el.addEventListener("input", syncConsultSummary);
        el.addEventListener("change", syncConsultSummary);
      }});
      on("in-sales-input-mode", "change", () => {{
        syncSalesInputModeUi();
        syncConsultSummary();
      }});
      draftFieldIds.forEach((id) => {{
        const el = $(id);
        if (!el) return;
        el.addEventListener("input", persistDraft);
        el.addEventListener("change", persistDraft);
      }});
      draftToggleIds.forEach((id) => {{
        const el = $(id);
        if (!el) return;
        el.addEventListener("change", persistDraft);
      }});
      on("btn-reset", "click", resetForm);
      const topChat = $("btn-openchat-top");
      const topCall = $("btn-call-top");
      if (topChat) {{
        topChat.addEventListener("click", () => openOpenchatWithSummary(buildConsultPayload()));
      }}
      if (topCall) {{
        const displayPhone = consultPhone || "010-9926-8661";
        const digits = displayPhone.replace(/[^0-9]/g, "");
        topCall.textContent = displayPhone;
        if (digits) {{
          topCall.href = `tel:${{digits}}`;
        }}
      }}
      const targetEmailNode = $("consult-target-email");
      if (targetEmailNode) targetEmailNode.textContent = consultEmail;
      const phoneNode = $("contact-phone-display");
      if (phoneNode) phoneNode.textContent = consultPhone || "010-9926-8661";
      if (!consultEndpoint) {{
        const submitBtn = $("btn-submit-consult");
        if (submitBtn) submitBtn.textContent = "오픈채팅으로 상담 요청";
      }}
      if (!consultOpenchatUrl) {{
        const openchatBtn = $("btn-openchat-consult");
        if (openchatBtn) {{
          openchatBtn.textContent = "오픈채팅 URL 미설정";
          openchatBtn.disabled = true;
          openchatBtn.style.opacity = "0.6";
          openchatBtn.style.cursor = "not-allowed";
        }}
        if (topChat) {{
          topChat.disabled = true;
          topChat.style.opacity = "0.6";
          topChat.style.cursor = "not-allowed";
        }}
        const resultChatBtn = $("btn-openchat-result");
        if (resultChatBtn) {{
          resultChatBtn.textContent = "오픈채팅 URL 미설정";
          resultChatBtn.disabled = true;
          resultChatBtn.style.opacity = "0.6";
          resultChatBtn.style.cursor = "not-allowed";
        }}
      }}
      renderNeighborHead();
      restoreDraft();
      syncSalesInputModeUi();
      renderActionSteps(null);
      renderYoyCompare(null);
      syncConsultSummary();
    }})();
  </script>
</section>"""
    return _collapse_script_whitespace(html)


