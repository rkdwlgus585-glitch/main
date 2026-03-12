"""AI 양도가 산정 엔진 (AI Construction License Transfer Pricing Engine).

건설업 면허 양도·양수 거래에서 적정 양도가격을 산정하는 핵심 알고리즘을 구현한다.

Algorithm overview
------------------
1. **입력 수집** — 업종, 연차별 시공실적, 보유 기술자 수, 자본금, 사무실 여부 등
2. **시장 데이터 클러스터링** — ``core_engine.yangdo_listing_recommender`` 가 제공하는
   동종 업종 매물 데이터를 기반으로 유사 매물 클러스터 구성
3. **기저 양도가 산정** — 시공실적·자본금·기술인력 가중 종합 점수에서 업종별
   scale multiplier(전기/정보통신 1.5×, 소방 1.0×) 적용
4. **신뢰도 산출** — 데이터 밀도, 분산, 직접 매칭률을 종합한 0-100 점수.
   ``singleCorePublicationCap()`` 로 업종별 상한 적용
5. **특수 업종 정산** — ``SPECIAL_BALANCE_AUTO_POLICIES`` 에 정의된 전기/정보통신/소방
   자동 정산 비율(minAutoBalanceShare, reorgOverrides)을 적용하여 최종 양도가 범위 산출
6. **결과 HTML 생성** — Python f-string 으로 클라이언트 JavaScript 포함 HTML 페이지를
   직접 렌더링. ``{`` / ``}}`` 이스케이프 패턴 사용

Core functions
--------------
- ``build_page_html()`` → 전체 양도가 산정 결과 HTML 페이지
- ``build_training_dataset()`` → 매물 학습 데이터셋 구성
- ``build_meta()`` → API 응답용 메타데이터 생성

See also
--------
- ``yangdo_blackbox_api.py`` — HTTP API 서버 (이 모듈을 호출)
- ``core_engine/yangdo_listing_recommender.py`` — 매물 추천/클러스터링
- ``core_engine/yangdo_duplicate_cluster.py`` — 중복 매물 탐지
"""

from __future__ import annotations

import os
import re
from html import escape
from typing import Any

from core_engine.api_response import now_iso, safe_json_for_script
from core_engine.channel_branding import resolve_channel_branding
from core_engine.host_utils import sanitize_endpoint as _sanitize_endpoint

# ── Module-level constants (single source of truth) ──────────────────
DEFAULT_LISTING_BASE_URL: str = "https://seoulmna.co.kr"
DEFAULT_CONTACT_PHONE: str = "1668-3548"
DEFAULT_CONTACT_PHONE_DIGITS: str = "16683548"

def _round4(value: Any) -> float | None:
    """Round *value* to 4 decimal places; return ``None`` on non-numeric input."""
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except (ValueError, TypeError):
        return None
def listing_detail_url(site_url: Any, seoul_no: Any = 0, now_uid: Any = "") -> str:
    """Build a canonical listing detail URL from *site_url* + *seoul_no* or *now_uid*."""
    base = str(site_url or "").rstrip("/")
    if not base:
        base = DEFAULT_LISTING_BASE_URL
    try:
        no = int(seoul_no or 0)
    except (ValueError, TypeError):
        no = 0
    if no > 0:
        return f"{base}/mna/{no}"
    uid_txt = str(now_uid or "").strip()
    if uid_txt.isdigit():
        return f"{base}/mna/{uid_txt}"
    return f"{base}/mna"
def _normalize_price_text(raw: Any) -> str:
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
    src = re.sub(r"<br\s*/?>", "\n", src, flags=re.IGNORECASE)
    return src
def _price_token_to_eok(token: Any) -> float | None:
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
def _extract_price_values_eok(raw: Any) -> list[float]:
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
def _derive_display_range_eok(current_price_text: Any, claim_price_text: Any, current_price_eok: Any, claim_price_eok: Any) -> tuple[float | None, float | None]:
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
def build_training_dataset(records: Any, site_url: str = "") -> list[dict[str, Any]]:
    """Transform raw listing records into normalised training rows for the AI engine.

    Extracts price ranges, financial ratios, license tokens, and listing URLs.
    Records with non-positive prices are filtered out.
    """
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
        except (ValueError, TypeError):
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


def _compact_train_row(row: Any) -> list:
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
def calc_quantile(values: Any, q: float) -> float | None:
    nums = []
    for raw in list(values or []):
        try:
            nums.append(float(raw))
        except (ValueError, TypeError):
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
def mean_or_none(values: Any) -> float | None:
    nums = _finite_numbers(values)
    if not nums:
        return None
    return _round4(sum(nums) / float(len(nums)))
def build_meta(all_records: Any, train_dataset: Any) -> dict[str, Any]:
    """Compute aggregate statistics (quantiles, counts, top licenses) for the AI engine UI."""
    prices = [row.get("price_eok") for row in list(train_dataset or [])]
    specialty_vals = [row.get("specialty") for row in list(train_dataset or [])]
    sales3_vals = [row.get("sales3_eok") for row in list(train_dataset or [])]
    debt_vals = [row.get("debt_ratio") for row in list(train_dataset or [])]
    liq_vals = [row.get("liq_ratio") for row in list(train_dataset or [])]
    capital_vals = [row.get("capital_eok") for row in list(train_dataset or [])]
    surplus_vals = [row.get("surplus_eok") for row in list(train_dataset or [])]
    balance_vals = [row.get("balance_eok") for row in list(train_dataset or [])]
    top_licenses: dict[str, int] = {}
    for rec in list(all_records or []):
        for token in rec.get("license_tokens", set()) or set():
            top_licenses[token] = top_licenses.get(token, 0) + 1
    top_items = sorted(top_licenses.items(), key=lambda x: (-x[1], x[0]))[:12]
    all_count = len(list(all_records or []))
    train_count = len(list(train_dataset or []))
    return {
        "generated_at": now_iso(),
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


def _normalize_license_key_py(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"(\(주\)|주식회사)", "", text)
    text = re.sub(r"(업종|면허)$", "", text)
    text = re.sub(r"(공사업|건설업|공사|사업)$", "", text)
    return text


def _finite_numbers(values: Any) -> list[float]:
    out = []
    for raw in list(values or []):
        try:
            num = float(raw)
        except (ValueError, TypeError):
            continue
        if num != num:
            continue
        out.append(num)
    return out


def _median_or_none(values: Any) -> float | None:
    nums = _finite_numbers(values)
    if not nums:
        return None
    return _round4(calc_quantile(nums, 0.5))


def _fallback_capital_eok(key: Any) -> float:
    token = _normalize_license_key_py(key)
    if not token:
        return 1.5
    if "토목건축" in token or "산업환경설비" in token:
        return 8.5
    if "토목" in token or "건축" in token or "조경" in token:
        return 5.0
    if "전기" in token or "정보통신" in token:
        return 1.5
    if "소방" in token:
        return 1.0
    return 1.5


def _fallback_surplus_eok(capital_eok: Any) -> float:
    try:
        capital = float(capital_eok)
    except (ValueError, TypeError):
        capital = 0.0
    if capital <= 0:
        return 0.2
    return _round4(min(1.2, max(0.15, capital * 0.08))) or 0.0


def _fallback_min_balance_eok(key: Any, median_balance_eok: Any = None) -> float:
    token = _normalize_license_key_py(key)
    if token:
        if "토목건축" in token or "산업환경설비" in token:
            return 0.9
        if "토목" in token or "건축" in token or "조경" in token:
            return 0.52
        if "전기" in token:
            return 0.24
        if "정보통신" in token or "통신" in token:
            return 0.2
        if "소방" in token:
            return 0.16
        return 0.2
    if isinstance(median_balance_eok, (int, float)) and float(median_balance_eok) > 0:
        return _round4(max(0.16, min(0.6, float(median_balance_eok) * 0.45))) or 0.0
    return 0.2


def _build_license_ui_profiles(train_dataset: Any, license_canonical_by_key: Any = None, generic_license_keys: Any = None) -> dict[str, Any]:
    canonical_map = {}
    for raw_key, raw_label in dict(license_canonical_by_key or {}).items():
        key = _normalize_license_key_py(raw_key)
        label = str(raw_label or "").strip()
        if key and label:
            canonical_map[key] = label
    generic_keys = {_normalize_license_key_py(v) for v in list(generic_license_keys or [])}
    buckets: dict[str, dict[str, Any]] = {}
    for row in list(train_dataset or []):
        tokens = list(row.get("tokens") or [])
        if not tokens:
            continue
        seen = set()
        for raw_token in tokens:
            key = _normalize_license_key_py(raw_token)
            if not key or key in seen or key in generic_keys or len(key) < 2:
                continue
            seen.add(key)
            bucket = buckets.setdefault(
                key,
                {
                    "token": key,
                    "display_name": canonical_map.get(key) or str(raw_token or key).strip() or key,
                    "count": 0,
                    "specialty": [],
                    "sales3": [],
                    "sales5": [],
                    "capital": [],
                    "surplus": [],
                    "balance": [],
                },
            )
            bucket["count"] += 1
            for field_name, bucket_name in (
                ("specialty", "specialty"),
                ("sales3_eok", "sales3"),
                ("sales5_eok", "sales5"),
                ("capital_eok", "capital"),
                ("surplus_eok", "surplus"),
                ("balance_eok", "balance"),
            ):
                val = row.get(field_name)
                if isinstance(val, (int, float)) and float(val) == float(val):
                    bucket[bucket_name].append(float(val))
    profiles = {}
    quick_tokens = []
    for key, bucket in buckets.items():
        median_balance = _median_or_none(bucket["balance"])
        capital_eok = _median_or_none(bucket["capital"])
        if capital_eok is None:
            capital_eok = _fallback_capital_eok(key)
        surplus_eok = _median_or_none(bucket["surplus"])
        if surplus_eok is None:
            surplus_eok = _fallback_surplus_eok(capital_eok)
        profile = {
            "token": key,
            "display_name": bucket["display_name"],
            "sample_count": int(bucket["count"] or 0),
            "prefill_capital_eok": _round4(capital_eok),
            "prefill_surplus_eok": _round4(surplus_eok),
            "default_balance_eok": _round4(_fallback_min_balance_eok(key, median_balance)),
            "median_balance_eok": median_balance,
            "typical_specialty_eok": _median_or_none(bucket["specialty"]),
            "typical_sales3_eok": _median_or_none(bucket["sales3"]),
            "typical_sales5_eok": _median_or_none(bucket["sales5"]),
        }
        profiles[key] = profile
        quick_tokens.append(
            {
                "token": key,
                "display_name": bucket["display_name"],
                "sample_count": int(bucket["count"] or 0),
            }
        )
    quick_tokens.sort(key=lambda item: (-int(item.get("sample_count") or 0), str(item.get("display_name") or "")))
    return {
        "profiles": profiles,
        "quick_tokens": quick_tokens[:18],
    }


def _collapse_script_whitespace(html_text: Any) -> str:
    """Minify inline <script> blocks by trimming per-line whitespace.

    Previous implementation wrapped JS in ``(0,eval)(code)`` which required
    CSP ``unsafe-eval`` and risked ASI (Automatic Semicolon Insertion) bugs.
    This version preserves line breaks to maintain JS semantics and avoids
    dynamic code evaluation entirely.
    """
    src = str(html_text or "")
    if not src:
        return src

    env_flag = os.environ.get("SMNA_DISABLE_SCRIPT_COLLAPSE", "")
    if str(env_flag).strip().lower() in {"1", "true", "yes", "on"}:
        return src

    def _trim_script(match: re.Match) -> str:
        open_tag = match.group(1) or ""
        body = match.group(2) or ""
        close_tag = match.group(3) or ""
        # Skip external scripts (with src=)
        if "src=" in open_tag.lower():
            return f"{open_tag}{body}{close_tag}"
        # Trim leading/trailing whitespace per line; keep line breaks for ASI safety
        trimmed = "\n".join(line.strip() for line in body.splitlines() if line.strip())
        return f"{open_tag}\n{trimmed}\n{close_tag}"

    return re.sub(r"(<script[^>]*>)([\s\S]*?)(</script>)", _trim_script, src, flags=re.IGNORECASE)


def build_page_html(
    train_dataset: Any,
    meta: Any,
    site_url: str = "",
    channel_id: str = "",
    license_canonical_by_key: Any = None,
    generic_license_keys: Any = None,
    view_mode: str = "customer",
    consult_endpoint: str = "",
    usage_endpoint: str = "",
    estimate_endpoint: str = "",
    api_key: str = "",
    contact_phone: str = DEFAULT_CONTACT_PHONE,
    openchat_url: str = "",
    enable_consult_widget: bool = False,
    enable_usage_log: bool = False,
    enable_hot_match: bool = False,
) -> str:
    """Build a complete self-contained HTML page for the AI 양도가 산정 calculator.

    Embeds the training dataset, statistical metadata, and a JS engine that
    performs real-time valuation.  Channel branding and feature toggles
    (consult widget, usage logging, hot-match) are configurable.

    Returns a UTF-8 HTML string ready to be written to disk or served.
    """
    branding = resolve_channel_branding(
        channel_id=str(channel_id or "").strip(),
        overrides={
            "site_url": site_url,
            "contact_phone": contact_phone,
            "openchat_url": openchat_url,
        },
    )
    site_url = str(branding.get("site_url") or site_url or "").strip()
    contact_phone = str(branding.get("contact_phone") or contact_phone or DEFAULT_CONTACT_PHONE).strip()
    openchat_url = str(branding.get("openchat_url") or openchat_url or "").strip()
    brand_name = str(branding.get("brand_name") or "서울건설정보").strip()
    brand_label = str(branding.get("brand_label") or brand_name).strip()
    brand_notice_url = str(branding.get("notice_url") or "").strip()
    consult_email = str(branding.get("contact_email") or "").strip()
    source_tag_prefix = str(branding.get("source_tag_prefix") or "channel").strip()
    contact_phone_digits = str(branding.get("contact_phone_digits") or "").strip()
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
    license_ui_profiles = _build_license_ui_profiles(
        train_dataset,
        license_canonical_by_key=license_canonical_by_key,
        generic_license_keys=generic_license_keys,
    )
    license_profiles_json = safe_json_for_script(license_ui_profiles)
    mode_json = safe_json_for_script(mode)
    consult_endpoint_json = safe_json_for_script(consult_endpoint_text)
    usage_endpoint_json = safe_json_for_script(usage_endpoint_text)
    estimate_endpoint_json = safe_json_for_script(estimate_endpoint_text)
    api_key_json = safe_json_for_script(str(api_key or "").strip())
    contact_phone_json = safe_json_for_script(contact_phone or DEFAULT_CONTACT_PHONE)
    openchat_url_json = safe_json_for_script(openchat_url_text)
    brand_name_json = safe_json_for_script(brand_name)
    consult_email_json = safe_json_for_script(consult_email)
    source_tag_prefix_json = safe_json_for_script(source_tag_prefix)
    enable_consult_widget_json = safe_json_for_script(bool(enable_consult_widget))
    enable_usage_log_json = safe_json_for_script(bool(enable_usage_log))
    enable_hot_match_json = safe_json_for_script(bool(enable_hot_match))
    title = "AI 양도가 산정 계산기" if mode == "customer" else "AI 양도가 산정 계산기 (내부 검수)"
    meta_mid_label = "중앙 기준가(억)" if mode == "customer" else "중앙 양도가(억)"
    subtitle_text = (
        "건설업 전 면허 대상 양도양수·분할합병 거래 범위를 먼저 계산하고, 즉시 1:1 상담으로 연결합니다."
        if mode == "customer" and enable_consult_widget
        else (
            "건설업 전 면허 대상 양도양수·분할합병 거래 범위를 먼저 계산합니다."
            if mode == "customer"
            else f"내부 검수 모드: {brand_name} 매물번호 + now UID 대조 데이터로 정밀 산정합니다."
        )
    )
    top_cta_text = (
        "건설업 전 면허의 예상 양도가 범위를 1분 안에 계산하고, 결과 기반 상담까지 바로 진행하세요."
        if enable_consult_widget
        else "건설업 전 면허의 예상 양도가 범위를 1분 안에 계산하고, 결과 요약을 바로 검토하세요."
    )
    top_cta_button_text = "대표 행정사 1:1 직접 상담" if enable_consult_widget else "결과를 오픈채팅으로 공유"
    hot_match_section_html = (
        """          <div class="lead-capture" id="hot-match-cta">
            <div class="msg" id="hot-match-msg">현재 보유하신 면허와 매칭률이 90% 이상인 대기 매수자가 3명 있습니다. 상세 리포트를 카카오톡으로 받으시겠습니까?</div>
            <div class="actions">
              <button type="button" class="btn-accent" id="btn-hot-match">상세 리포트 카카오톡으로 받기</button>
              <button type="button" class="btn-neutral" id="btn-hot-match-copy">연락처 입력 후 요약 복사</button>
            </div>
            <div class="help">성함/연락처를 입력하면 상담 문의 시트에 자동 저장되어 빠르게 회신받을 수 있습니다.</div>
          </div>
"""
        if enable_hot_match
        else ""
    )
    consult_section_html = (
        """          <div class="consult-wrap">
            <details class="consult-panel">
              <summary>전문가 상담 요청 열기</summary>
              <div class="consult-panel-body">
                <div class="consult-title">전문가 상담 요청</div>
                <div class="consult-sub">산정 결과를 첨부해 바로 상담 요청할 수 있습니다.<br>대표 상담 / <strong id="contact-phone-display" style="font-weight:600">{escape(contact_phone)}</strong></div>
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
                  <strong>개인정보 수집·이용 안내 (행정사사무소하랑 · {escape(brand_name)})</strong><br>
                  상담 요청 시 입력한 성함·연락처·이메일·상담메모는 상담 회신 및 계약 진행 안내 목적에 한해 사용되며, 관련 법령에 따라 안전하게 보관·관리됩니다.
                </div>
                <label class="consent-check"><input id="consult-consent" type="checkbox" /> 개인정보 수집·이용 안내를 확인했으며 상담 목적 활용에 동의합니다.</label>
                <div class="small" style="margin-top:6px">수신: <strong id="consult-target-email">{escape(consult_email or "-")}</strong></div>
              </div>
            </details>
          </div>
"""
        if enable_consult_widget
        else ""
    )
    html = f"""<section id="seoulmna-yangdo-calculator" class="smna-wrap" role="region" aria-labelledby="yangdo-main-title">
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
      --smna-primary-strong: #002244;
      --smna-primary-soft: #0A4D8C;
      --smna-neutral: #F8FAFB;
      --smna-accent: #00A3FF;
      --smna-accent-strong: #0080CC;
      --smna-bg: linear-gradient(180deg, #F8FAFB 0%, #FFFFFF 100%);
      --smna-bg-soft: #F8FAFB;
      --smna-line: rgba(0, 55, 100, 0.10);
      --smna-accent-soft: rgba(0, 163, 255, 0.08);
      --smna-accent-border: rgba(0, 163, 255, 0.22);
      --smna-text: #1A1A2E;
      --smna-sub: #4B5563;
      --smna-warning: #FFB800;
      --smna-warning-text: #946200;
      --smna-success: #00C48C;
      --smna-success-text: #008756;
      --smna-error: #FF4757;
      --smna-border: #E5E7EB;
      --smna-header-text: #f8fbff;
      --smna-header-sub: #d8edf6;
      --smna-teal: #0f9fb0;
      --smna-teal-light: #36bad0;
      --smna-teal-dark: #0f5f75;
      --smna-badge-success-bg: #E6F9F1;
      --smna-badge-warning-bg: #FFF8E1;
      --smna-badge-error-bg: #FFEBEE;
      --smna-badge-info-bg: #E3F2FD;
      --smna-disabled-bg: #f0f4f9;
      font-family: "Pretendard", "Noto Sans KR", "Malgun Gothic", Arial, sans-serif;
      color: var(--smna-text);
      font-size: 19px;
      line-height: 1.68;
      margin: 0 auto;
      max-width: 1140px;
      background: var(--smna-bg);
      border: 1px solid var(--smna-line);
      border-radius: 28px;
      overflow: hidden;
      box-shadow: 0 28px 80px rgba(7, 30, 52, 0.12);
    }}
    #seoulmna-yangdo-calculator .smna-header {{
      position: relative;
      overflow: hidden;
      background:
        radial-gradient(circle at 12% 18%, rgba(90, 194, 214, 0.28), transparent 30%),
        radial-gradient(circle at 88% 22%, rgba(138, 201, 255, 0.18), transparent 28%),
        linear-gradient(136deg, #02243b 0%, #003764 46%, #0f5a8e 100%);
      color: #f8fbff;
      padding: 30px 30px 22px;
      border-bottom: 1px solid rgba(255,255,255,.16);
    }}
    #seoulmna-yangdo-calculator .smna-header::before {{
      content: "";
      position: absolute;
      inset: auto -10% -42% 52%;
      height: 240px;
      background: linear-gradient(135deg, rgba(255,255,255,0.16), rgba(255,255,255,0));
      transform: rotate(-12deg);
      pointer-events: none;
    }}
    #seoulmna-yangdo-calculator .smna-header::after {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0));
      pointer-events: none;
    }}
    #seoulmna-yangdo-calculator .smna-brand-row {{
      position: relative;
      z-index: 1;
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
      padding: 5px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,.12);
      border: 1px solid rgba(181, 229, 239, .42);
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
      font-size: 14px;
      letter-spacing: .015em;
      font-weight: 800;
      color: #d9eef7;
    }}
    #seoulmna-yangdo-calculator .smna-mode {{
      font-size: 13px;
      color: #eef8fc;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid rgba(188, 232, 241, .36);
      background: rgba(0,0,0,.12);
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator h2 {{
      position: relative;
      z-index: 1;
      margin: 0;
      font-size: 42px;
      font-weight: 900;
      letter-spacing: -0.02em;
      line-height: 1.18;
      color: var(--smna-header-text) !important;
      text-shadow: 0 8px 24px rgba(0,0,0,.18);
    }}
    #seoulmna-yangdo-calculator .smna-subtitle {{
      position: relative;
      z-index: 1;
      margin-top: 10px;
      max-width: 760px;
      font-size: 20px;
      line-height: 1.6;
      font-weight: 700;
      color: var(--smna-header-sub);
    }}
    #seoulmna-yangdo-calculator .smna-ratio {{
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: 7fr 2fr 1fr;
      margin-top: 18px;
      height: 9px;
      border-radius: 999px;
      overflow: hidden;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.16);
    }}
    #seoulmna-yangdo-calculator .smna-ratio > div:nth-child(1) {{ background: #8dd8e3; }}
    #seoulmna-yangdo-calculator .smna-ratio > div:nth-child(2) {{ background: #dce8f1; }}
    #seoulmna-yangdo-calculator .smna-ratio > div:nth-child(3) {{ background: var(--smna-teal); }}
    #seoulmna-yangdo-calculator .smna-body {{
      padding: 24px;
      background: var(--smna-bg);
    }}
    #seoulmna-yangdo-calculator .smna-meta {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 18px;
    }}
    #seoulmna-yangdo-calculator .smna-meta .item {{
      background: rgba(255,255,255,0.92);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 16px;
      padding: 12px 14px;
      box-shadow: 0 16px 34px rgba(7, 30, 52, 0.07);
    }}
    #seoulmna-yangdo-calculator .smna-meta .label {{
      display: block;
      font-size: 12px;
      color: var(--smna-sub);
      margin-bottom: 4px;
      letter-spacing: .02em;
      text-transform: uppercase;
    }}
    #seoulmna-yangdo-calculator .smna-meta .value {{
      font-size: 24px;
      font-weight: 800;
      color: var(--smna-primary);
      line-height: 1.2;
    }}
    #seoulmna-yangdo-calculator .impact {{
      background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(242,249,251,0.98));
      border: 1px solid rgba(15, 159, 176, 0.16);
      border-radius: 18px;
      padding: 14px 16px;
      margin-bottom: 12px;
      font-size: 17px;
      color: var(--smna-primary);
      font-weight: 700;
      box-shadow: 0 16px 32px rgba(6, 32, 57, 0.06);
    }}
    #seoulmna-yangdo-calculator .impact.cta-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator .impact .cta-text {{
      max-width: 720px;
      font-size: 23px;
      color: var(--smna-primary-strong);
      font-weight: 900;
      line-height: 1.45;
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
      transition: transform .18s ease, box-shadow .18s ease, background .18s ease;
      box-shadow: 0 12px 24px rgba(6, 29, 52, 0.12);
    }}
    #seoulmna-yangdo-calculator .cta-button.call {{
      background: rgba(255,255,255,0.96);
      color: var(--smna-primary);
      border: 1px solid rgba(0, 55, 100, 0.12);
    }}
    #seoulmna-yangdo-calculator .cta-button.chat {{
      background: linear-gradient(135deg, var(--smna-accent), var(--smna-teal-light));
      color: #fff;
      border: 1px solid rgba(4, 96, 108, 0.28);
    }}
    #seoulmna-yangdo-calculator .smna-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.12fr) minmax(340px, 0.88fr);
      gap: 16px;
      align-items: start;
    }}
    #seoulmna-yangdo-calculator .smna-grid .panel + .panel {{
      margin-top: 0;
    }}
    #seoulmna-yangdo-calculator .panel {{
      background: rgba(255,255,255,0.94);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(0, 55, 100, 0.09);
      border-radius: 22px;
      overflow: hidden;
      box-shadow: 0 20px 48px rgba(8, 28, 49, 0.08);
    }}
    #seoulmna-yangdo-calculator .panel h3 {{
      margin: 0;
      padding: 16px 18px;
      font-size: 28px;
      font-weight: 900;
      color: #fff;
      background: linear-gradient(135deg, var(--smna-primary-strong), var(--smna-primary));
      line-height: 1.22;
    }}
    #seoulmna-yangdo-calculator .panel.result h3 {{
      background: linear-gradient(135deg, var(--smna-primary-strong), var(--smna-accent));
    }}
    #seoulmna-yangdo-calculator .panel.result {{
      position: sticky;
      top: 18px;
    }}
    #seoulmna-yangdo-calculator .panel .panel-body {{
      padding: 18px;
      overflow: hidden;
    }}
    #seoulmna-yangdo-calculator .avg-guide {{
      font-size: 16px;
      color: var(--smna-primary-soft);
      background: rgba(235, 245, 250, 0.9);
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 14px;
      padding: 11px 12px;
      margin-bottom: 12px;
      line-height: 1.55;
    }}
    #seoulmna-yangdo-calculator .input-row {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 2px;
      overflow: visible;
    }}
    #seoulmna-yangdo-calculator .field {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-width: 0;
    }}
    #seoulmna-yangdo-calculator .field.wide {{
      grid-column: 1 / -1;
    }}
    #seoulmna-yangdo-calculator .field.strong {{
      border: 1px solid rgba(15, 159, 176, 0.18);
      background: linear-gradient(180deg, rgba(15, 159, 176, 0.05), rgba(255,255,255,0.9));
      border-radius: 16px;
      padding: 12px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.82);
    }}
    #seoulmna-yangdo-calculator label {{
      font-size: 15px;
      color: var(--smna-sub);
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator .field.strong label {{
      color: var(--smna-primary);
      font-weight: 800;
    }}
    #seoulmna-yangdo-calculator input, #seoulmna-yangdo-calculator textarea, #seoulmna-yangdo-calculator select {{
      width: 100%;
      border: 1px solid rgba(0, 55, 100, 0.14);
      border-radius: 14px;
      padding: 13px 15px;
      font-size: 17px;
      color: var(--smna-text);
      background: rgba(255,255,255,0.96);
      outline: none;
      line-height: 1.45;
      transition: border-color .16s ease, box-shadow .16s ease, background .16s ease;
    }}
    #seoulmna-yangdo-calculator input:focus, #seoulmna-yangdo-calculator textarea:focus, #seoulmna-yangdo-calculator select:focus {{
      border-color: rgba(15, 159, 176, 0.46);
      box-shadow: 0 0 0 4px rgba(15, 159, 176, 0.12);
      background: #fff;
    }}
    #seoulmna-yangdo-calculator button:focus-visible,
    #seoulmna-yangdo-calculator .license-chip:focus-visible,
    #seoulmna-yangdo-calculator .reorg-choice-btn:focus-visible,
    #seoulmna-yangdo-calculator .cta-button:focus-visible {{
      outline: 3px solid var(--smna-accent-strong);
      outline-offset: 2px;
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
    #seoulmna-yangdo-calculator .required-pill {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 3px 9px;
      margin-left: 6px;
      border-radius: 999px;
      background: rgba(0, 55, 100, 0.08);
      color: var(--smna-primary);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: .04em;
      vertical-align: middle;
    }}
    #seoulmna-yangdo-calculator .field-sub {{
      margin-top: 2px;
      font-size: 13px;
      line-height: 1.55;
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .license-chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 2px;
    }}
    #seoulmna-yangdo-calculator .license-chip {{
      border: 1px solid rgba(0, 55, 100, 0.1);
      background: rgba(255,255,255,0.92);
      color: var(--smna-primary);
      border-radius: 999px;
      padding: 7px 11px;
      font-size: 13px;
      font-weight: 800;
      line-height: 1;
      cursor: pointer;
    }}
    #seoulmna-yangdo-calculator .scale-mode-switch {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    #seoulmna-yangdo-calculator .scale-mode-btn {{
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 5px;
      border: 1px solid rgba(0, 55, 100, 0.1);
      border-radius: 18px;
      padding: 14px 15px;
      background: rgba(255,255,255,0.94);
      color: var(--smna-primary);
      box-shadow: none;
    }}
    #seoulmna-yangdo-calculator .scale-mode-btn .eyebrow {{
      font-size: 11px;
      font-weight: 900;
      letter-spacing: .08em;
      color: var(--smna-sub);
      text-transform: uppercase;
    }}
    #seoulmna-yangdo-calculator .scale-mode-btn .title {{
      font-size: 18px;
      font-weight: 900;
      line-height: 1.2;
    }}
    #seoulmna-yangdo-calculator .scale-mode-btn .desc {{
      font-size: 13px;
      line-height: 1.5;
      color: var(--smna-sub);
      text-align: left;
    }}
    #seoulmna-yangdo-calculator .scale-mode-btn.active {{
      background: linear-gradient(135deg, rgba(0, 55, 100, 0.96), rgba(15, 90, 142, 0.96));
      border-color: rgba(0, 55, 100, 0.35);
      color: #fff;
      box-shadow: 0 18px 34px rgba(0, 55, 100, 0.24);
    }}
    #seoulmna-yangdo-calculator .scale-mode-btn.active .eyebrow,
    #seoulmna-yangdo-calculator .scale-mode-btn.active .desc {{
      color: rgba(236, 247, 250, 0.9);
    }}
    #seoulmna-yangdo-calculator .scale-mode-btn:disabled {{
      opacity: .55;
      cursor: not-allowed;
      box-shadow: none;
    }}
    #seoulmna-yangdo-calculator .reorg-choice-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 10px;
    }}
    #seoulmna-yangdo-calculator .reorg-choice-btn {{
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 5px;
      min-height: 92px;
      padding: 14px 15px;
      border: 1px solid rgba(0, 55, 100, 0.12);
      border-radius: 18px;
      background: rgba(255,255,255,0.96);
      color: var(--smna-primary);
      text-align: left;
      cursor: pointer;
      transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease, background 0.16s ease;
    }}
    #seoulmna-yangdo-calculator .reorg-choice-btn:hover {{
      border-color: rgba(0, 55, 100, 0.26);
      box-shadow: 0 16px 28px rgba(8, 28, 49, 0.10);
      transform: translateY(-1px);
    }}
    #seoulmna-yangdo-calculator .reorg-choice-btn .eyebrow {{
      font-size: 11px;
      font-weight: 900;
      letter-spacing: .08em;
      color: var(--smna-sub);
      text-transform: uppercase;
    }}
    #seoulmna-yangdo-calculator .reorg-choice-btn .title {{
      font-size: 18px;
      font-weight: 900;
      line-height: 1.2;
    }}
    #seoulmna-yangdo-calculator .reorg-choice-btn .desc {{
      font-size: 13px;
      line-height: 1.5;
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .reorg-choice-btn.is-active {{
      background: linear-gradient(135deg, rgba(0, 55, 100, 0.96), rgba(15, 90, 142, 0.96));
      border-color: rgba(0, 55, 100, 0.35);
      color: #fff;
      box-shadow: 0 18px 34px rgba(0, 55, 100, 0.24);
    }}
    #seoulmna-yangdo-calculator .reorg-choice-btn.is-active .eyebrow,
    #seoulmna-yangdo-calculator .reorg-choice-btn.is-active .desc {{
      color: rgba(236, 247, 250, 0.9);
    }}
    #seoulmna-yangdo-calculator .reorg-choice-btn.is-required {{
      border-color: rgba(169, 92, 24, 0.34);
      box-shadow: 0 16px 28px rgba(125, 74, 29, 0.12);
      background: linear-gradient(180deg, rgba(252, 245, 237, 0.99), rgba(255,255,255,0.99));
    }}
    #seoulmna-yangdo-calculator .reorg-compare-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 10px;
    }}
    #seoulmna-yangdo-calculator .reorg-compare-card {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-height: 116px;
      padding: 14px 15px;
      border: 1px solid rgba(0, 55, 100, 0.10);
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(250, 252, 253, 0.98), rgba(240, 247, 250, 0.96));
      color: var(--smna-primary);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.92);
      transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
    }}
    #seoulmna-yangdo-calculator .reorg-compare-card .eyebrow {{
      font-size: 11px;
      font-weight: 900;
      letter-spacing: .08em;
      color: var(--smna-sub);
      text-transform: uppercase;
    }}
    #seoulmna-yangdo-calculator .reorg-compare-card .title {{
      font-size: 16px;
      font-weight: 900;
      line-height: 1.25;
    }}
    #seoulmna-yangdo-calculator .reorg-compare-card .desc {{
      font-size: 13px;
      line-height: 1.5;
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .reorg-compare-card .meta {{
      margin-top: auto;
      font-size: 12px;
      font-weight: 800;
      color: var(--smna-warning-text);
    }}
    #seoulmna-yangdo-calculator .reorg-compare-card.is-active {{
      border-color: rgba(0, 55, 100, 0.26);
      box-shadow: 0 18px 34px rgba(0, 55, 100, 0.12);
      transform: translateY(-1px);
    }}
    #seoulmna-yangdo-calculator .reorg-compare-card.is-required {{
      border-color: rgba(169, 92, 24, 0.30);
      background: linear-gradient(180deg, rgba(252, 245, 237, 0.99), rgba(255,255,255,0.99));
    }}
    #seoulmna-yangdo-calculator .scale-search-panel.is-hidden {{
      display: none;
    }}
    #seoulmna-yangdo-calculator .smart-panel {{
      border: 1px solid rgba(0, 55, 100, 0.09);
      border-radius: 18px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.98), rgba(240,247,250,0.96));
      padding: 16px;
      margin-bottom: 12px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
    }}
    #seoulmna-yangdo-calculator .smart-panel-head {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
      margin-bottom: 12px;
    }}
    #seoulmna-yangdo-calculator .smart-panel-title {{
      font-size: 15px;
      font-weight: 900;
      color: var(--smna-primary);
      margin: 0;
    }}
    #seoulmna-yangdo-calculator .smart-panel-note {{
      margin: 4px 0 0;
      font-size: 13px;
      line-height: 1.5;
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .smart-panel .btn-mini {{
      padding: 9px 11px;
      font-size: 13px;
      font-weight: 800;
      border-radius: 999px;
      box-shadow: none;
    }}
    #seoulmna-yangdo-calculator .smart-metrics {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    #seoulmna-yangdo-calculator .smart-metric {{
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 16px;
      background: rgba(255,255,255,0.92);
      padding: 12px;
    }}
    #seoulmna-yangdo-calculator .smart-metric.highlight {{
      background: linear-gradient(135deg, rgba(0, 55, 100, 0.05), rgba(15, 159, 176, 0.09));
      border-color: rgba(15, 159, 176, 0.18);
    }}
    #seoulmna-yangdo-calculator .smart-metric .k {{
      display: block;
      font-size: 12px;
      font-weight: 800;
      color: var(--smna-sub);
      margin-bottom: 6px;
    }}
    #seoulmna-yangdo-calculator .smart-metric .v {{
      display: block;
      font-size: 22px;
      line-height: 1.2;
      font-weight: 900;
      color: var(--smna-primary);
    }}
    #seoulmna-yangdo-calculator .smart-metric .sub {{
      display: block;
      margin-top: 4px;
      font-size: 12px;
      line-height: 1.45;
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .checks {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 8px;
      padding-top: 4px;
    }}
    #seoulmna-yangdo-calculator .checks label {{
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--smna-primary);
      font-size: 16px;
      border: 1px solid rgba(15, 159, 176, 0.14);
      background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(241,248,250,0.94));
      border-radius: 14px;
      padding: 10px 12px;
      white-space: normal;
      line-height: 1.4;
      min-height: 50px;
      min-width: 0;
      font-weight: 800;
    }}
    #seoulmna-yangdo-calculator .checks input[type="checkbox"] {{
      width: 18px;
      height: 18px;
      margin: 0;
      flex: 0 0 auto;
      accent-color: var(--smna-primary);
    }}
    #seoulmna-yangdo-calculator .advanced-panel {{
      margin-top: 12px;
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 18px;
      background: rgba(247, 250, 252, 0.9);
      overflow: hidden;
    }}
    #seoulmna-yangdo-calculator .advanced-panel > summary {{
      list-style: none;
      cursor: pointer;
      padding: 14px 16px;
      font-size: 15px;
      font-weight: 900;
      color: var(--smna-primary);
      background: rgba(0, 55, 100, 0.04);
    }}
    #seoulmna-yangdo-calculator .advanced-panel > summary::-webkit-details-marker {{
      display: none;
    }}
    #seoulmna-yangdo-calculator .advanced-panel[open] > summary {{
      border-bottom: 1px solid rgba(0, 55, 100, 0.08);
    }}
    #seoulmna-yangdo-calculator .advanced-panel-body {{
      padding: 14px;
    }}
    #seoulmna-yangdo-calculator .btn-row {{
      margin-top: 12px;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator button {{
      border: 0;
      border-radius: 14px;
      padding: 12px 15px;
      font-size: 20px;
      font-weight: 800;
      cursor: pointer;
      transition: transform .18s ease, box-shadow .18s ease, opacity .18s ease;
    }}
    #seoulmna-yangdo-calculator button:hover, #seoulmna-yangdo-calculator .cta-button:hover {{ transform: translateY(-1px); }}
    #seoulmna-yangdo-calculator .btn-primary {{
      background: linear-gradient(135deg, var(--smna-primary-strong), var(--smna-primary));
      color: #fff;
      box-shadow: 0 16px 30px rgba(0, 55, 100, 0.18);
    }}
    #seoulmna-yangdo-calculator .btn-neutral {{
      background: rgba(255,255,255,0.98);
      color: var(--smna-text);
      border: 1px solid rgba(0, 55, 100, 0.1);
    }}
    #seoulmna-yangdo-calculator .btn-accent {{
      background: linear-gradient(135deg, var(--smna-accent-strong), var(--smna-accent));
      color: #fff;
      box-shadow: 0 16px 30px rgba(8, 120, 137, 0.2);
    }}
    #seoulmna-yangdo-calculator .result-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin-bottom: 8px;
    }}
    #seoulmna-yangdo-calculator .result-card {{
      background: #fff;
      border: 1px solid var(--smna-border);
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
      border: 1px solid var(--smna-border);
      border-radius: 10px;
      padding: 9px 11px;
      background: var(--smna-neutral);
      color: var(--smna-primary);
      font-size: 15px;
      line-height: 1.5;
      word-break: keep-all;
    }}
    #seoulmna-yangdo-calculator .yoy-compare strong {{
      font-weight: 800;
      color: var(--smna-primary);
    }}
    #seoulmna-yangdo-calculator .yoy-compare.up strong {{ color: var(--smna-primary-soft); }}
    #seoulmna-yangdo-calculator .yoy-compare.down strong {{ color: var(--smna-warning-text); }}
    #seoulmna-yangdo-calculator .risk-note {{
      background: var(--smna-accent-soft);
      border: 1px solid var(--smna-accent-border);
      border-radius: 16px;
      padding: 12px 13px;
      font-size: 17px;
      color: var(--smna-primary-soft);
      margin-top: 8px;
      line-height: 1.55;
    }}
    #seoulmna-yangdo-calculator .result-reason-chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }}
    #seoulmna-yangdo-calculator .result-reason-chip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 11px;
      border-radius: 999px;
      border: 1px solid var(--smna-border);
      background: var(--smna-neutral);
      color: var(--smna-primary);
      font-size: 13px;
      font-weight: 800;
      line-height: 1.35;
    }}
    #seoulmna-yangdo-calculator .result-reason-chip.publication {{
      background: var(--smna-neutral);
      color: var(--smna-primary);
    }}
    #seoulmna-yangdo-calculator .result-reason-chip.settlement {{
      background: #f6fbf4;
      color: var(--smna-success-text);
      border-color: #d5e8d5;
    }}
    #seoulmna-yangdo-calculator .settlement-panel {{
      margin-top: 10px;
      border: 1px solid var(--smna-border);
      border-radius: 12px;
      padding: 10px 11px;
      background: linear-gradient(180deg, #fbfdff 0%, #f1f6fb 100%);
    }}
    #seoulmna-yangdo-calculator .settlement-panel .title {{
      font-size: 16px;
      font-weight: 800;
      color: var(--smna-primary);
    }}
    #seoulmna-yangdo-calculator .settlement-panel .sub {{
      margin-top: 4px;
      font-size: 14px;
      color: var(--smna-sub);
      line-height: 1.5;
    }}
    #seoulmna-yangdo-calculator .settlement-grid {{
      margin-top: 8px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
    }}
    #seoulmna-yangdo-calculator .settlement-item {{
      border: 1px solid var(--smna-border);
      border-radius: 10px;
      background: #fff;
      padding: 8px 10px;
    }}
    #seoulmna-yangdo-calculator .settlement-item .k {{
      display: block;
      font-size: 13px;
      color: var(--smna-sub);
      margin-bottom: 2px;
    }}
    #seoulmna-yangdo-calculator .settlement-item .v {{
      display: block;
      font-size: 20px;
      font-weight: 800;
      color: var(--smna-primary);
    }}
    #seoulmna-yangdo-calculator .settlement-notes {{
      margin: 8px 0 0;
      padding-left: 18px;
      color: var(--smna-sub);
      font-size: 14px;
      line-height: 1.5;
    }}
    #seoulmna-yangdo-calculator .settlement-scenarios {{
      margin-top: 10px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
    }}
    #seoulmna-yangdo-calculator .settlement-scenario {{
      border: 1px solid var(--smna-border);
      border-radius: 11px;
      background: #fff;
      padding: 10px 11px;
      box-shadow: 0 4px 12px rgba(16, 57, 88, 0.04);
    }}
    #seoulmna-yangdo-calculator .settlement-scenario.is-selected {{
      border-color: var(--smna-accent-strong);
      box-shadow: 0 0 0 2px rgba(15, 159, 176, 0.12);
    }}
    #seoulmna-yangdo-calculator .settlement-scenario .head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }}
    #seoulmna-yangdo-calculator .settlement-scenario .name {{
      font-size: 14px;
      font-weight: 800;
      color: var(--smna-primary);
    }}
    #seoulmna-yangdo-calculator .settlement-scenario .badge {{
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      font-weight: 700;
      background: #e7f8f7;
      color: var(--smna-accent-strong);
      white-space: nowrap;
    }}
    #seoulmna-yangdo-calculator .settlement-scenario .metric {{
      margin-top: 8px;
      display: grid;
      gap: 4px;
    }}
    #seoulmna-yangdo-calculator .settlement-scenario .metric .k {{
      font-size: 12px;
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .settlement-scenario .metric .v {{
      font-size: 18px;
      font-weight: 800;
      color: var(--smna-primary);
    }}
    #seoulmna-yangdo-calculator .settlement-scenario .sub {{
      margin-top: 6px;
      font-size: 12px;
      color: var(--smna-sub);
      line-height: 1.45;
    }}
    #seoulmna-yangdo-calculator .field.required-field {{
      border: 1px solid rgba(15, 159, 176, 0.24);
      border-radius: 18px;
      padding: 12px;
      background: linear-gradient(180deg, rgba(15, 159, 176, 0.06), rgba(255,255,255,0.94));
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
    }}
    #seoulmna-yangdo-calculator .field-note {{
      margin-top: 6px;
      font-size: 14px;
      line-height: 1.45;
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .draft-restore-note {{
      display: none;
      margin: 0 0 10px 0;
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid rgba(15, 159, 176, 0.18);
      background: linear-gradient(180deg, rgba(15, 159, 176, 0.08), rgba(255,255,255,0.96));
      color: var(--smna-primary-soft);
      font-size: 14px;
      line-height: 1.5;
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator .draft-restore-note.is-visible {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator .draft-restore-note-text {{
      flex: 1 1 280px;
      min-width: 0;
    }}
    #seoulmna-yangdo-calculator .draft-restore-actions {{
      display: inline-flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator .draft-restore-action {{
      appearance: none;
      border: 1px solid rgba(12, 84, 106, 0.16);
      background: rgba(255,255,255,0.96);
      color: var(--smna-accent-strong);
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 13px;
      font-weight: 800;
      line-height: 1;
      cursor: pointer;
      white-space: nowrap;
      box-shadow: 0 10px 22px rgba(14, 76, 94, 0.08);
    }}
    #seoulmna-yangdo-calculator .draft-restore-action:hover {{
      background: #ffffff;
      border-color: rgba(12, 84, 106, 0.24);
    }}
    #seoulmna-yangdo-calculator .draft-restore-action.is-primary {{
      background: linear-gradient(135deg, var(--smna-teal), #1b6aa8);
      color: #ffffff;
      border-color: transparent;
      box-shadow: 0 14px 28px rgba(16, 116, 156, 0.2);
    }}
    #seoulmna-yangdo-calculator .draft-restore-action.is-primary:hover {{
      background: linear-gradient(135deg, #13aabc, #155d95);
      border-color: transparent;
    }}
    #seoulmna-yangdo-calculator .small {{
      font-size: 14px;
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .consult-wrap {{
      margin-top: 12px;
      border: 1px solid rgba(0, 55, 100, 0.08);
      background: linear-gradient(180deg, rgba(248,252,255,0.98) 0%, rgba(238,244,250,0.98) 100%);
      border-radius: 18px;
      padding: 12px;
    }}
    #seoulmna-yangdo-calculator .consult-title {{
      font-size: 20px;
      font-weight: 800;
      color: var(--smna-primary-strong);
      margin-bottom: 4px;
    }}
    #seoulmna-yangdo-calculator .consult-sub {{
      font-size: 17px;
      color: var(--smna-sub, #4B5563);
      margin-bottom: 8px;
      text-align: center;
      line-height: 1.6;
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
      border: 1px solid rgba(0, 55, 100, 0.1);
      background: #ffffff;
      border-radius: 14px;
      padding: 12px;
    }}
    #seoulmna-yangdo-calculator details.consult-panel > summary {{
      cursor: pointer;
      font-size: 22px;
      font-weight: 800;
      color: var(--smna-primary);
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
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 14px;
      background: #ffffff;
      padding: 10px;
    }}
    #seoulmna-yangdo-calculator details.consult-details > summary {{
      cursor: pointer;
      font-size: 14px;
      color: var(--smna-primary);
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
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 14px;
      overflow: hidden;
    }}
    #seoulmna-yangdo-calculator .neighbor-panel {{
      margin-top: 8px;
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 14px;
      background: var(--smna-neutral);
      overflow: hidden;
    }}
    #seoulmna-yangdo-calculator .neighbor-panel summary {{
      list-style: none;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 3px;
      padding: 11px 12px;
      color: var(--smna-primary);
      font-size: 14px;
      font-weight: 800;
      background: linear-gradient(180deg, rgba(243,249,253,0.98), rgba(255,255,255,0.98));
    }}
    #seoulmna-yangdo-calculator .neighbor-panel summary::-webkit-details-marker {{ display: none; }}
    #seoulmna-yangdo-calculator .neighbor-panel summary .sub {{
      font-size: 12px;
      font-weight: 700;
      color: var(--smna-sub);
      line-height: 1.45;
    }}
    #seoulmna-yangdo-calculator .neighbor-panel[open] summary {{
      border-bottom: 1px solid rgba(0, 55, 100, 0.08);
    }}
    #seoulmna-yangdo-calculator thead th {{
      background: var(--smna-neutral);
      color: var(--smna-text);
      font-size: 13px;
      text-align: left;
      padding: 8px;
      border-bottom: 1px solid rgba(0, 55, 100, 0.08);
    }}
    #seoulmna-yangdo-calculator tbody td {{
      padding: 8px;
      border-bottom: 1px solid rgba(0, 55, 100, 0.06);
      color: var(--smna-text);
      word-break: break-word;
      white-space: normal;
    }}
    #seoulmna-yangdo-calculator tbody tr:last-child td {{ border-bottom: 0; }}
    #seoulmna-yangdo-calculator a {{ color: var(--smna-primary); text-decoration: none; }}
    #seoulmna-yangdo-calculator .foot {{
      margin-top: 10px;
      font-size: 13px;
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .trust-signal {{
      margin-top: 14px;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid rgba(0, 55, 100, 0.07);
      background: linear-gradient(135deg, rgba(244,248,252,0.96) 0%, rgba(255,255,255,0.98) 100%);
    }}
    #seoulmna-yangdo-calculator .trust-signal-items {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    #seoulmna-yangdo-calculator .trust-signal-chip {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(0, 55, 100, 0.06);
      font-size: 12px;
      font-weight: 700;
      color: var(--smna-body);
      white-space: nowrap;
    }}
    #seoulmna-yangdo-calculator .trust-signal-chip .ts-label {{
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .trust-signal-chip .ts-value {{
      color: var(--smna-primary);
      font-weight: 900;
    }}
    #seoulmna-yangdo-calculator .trust-signal-meta {{
      margin-top: 6px;
      font-size: 11px;
      font-weight: 700;
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .action-steps {{
      margin-top: 10px;
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 16px;
      background: var(--smna-neutral);
      padding: 13px 14px;
    }}
    #seoulmna-yangdo-calculator .action-steps.compact-followup {{
      margin-top: 6px;
      padding: 10px 11px;
    }}
    #seoulmna-yangdo-calculator .action-steps .title {{
      color: var(--smna-primary-strong);
      font-weight: 800;
      font-size: 17px;
      margin-bottom: 6px;
    }}
    #seoulmna-yangdo-calculator .action-steps ol {{
      margin: 0;
      padding-left: 18px;
      color: var(--smna-primary-strong);
      font-size: 15px;
    }}
    #seoulmna-yangdo-calculator .action-steps li {{ margin: 4px 0; }}
    #seoulmna-yangdo-calculator .recommend-panel {{
      margin-top: 10px;
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 16px;
      background: var(--smna-neutral);
      padding: 13px 14px;
    }}
    #seoulmna-yangdo-calculator .recommend-panel.priority-single {{
      margin-top: 6px;
      border-color: rgba(15, 159, 176, 0.18);
      box-shadow: 0 16px 34px rgba(15, 159, 176, 0.10);
      padding: 11px 12px;
    }}
    #seoulmna-yangdo-calculator .recommend-panel.priority-single .sub {{
      margin-bottom: 6px;
    }}
    #seoulmna-yangdo-calculator .recommend-panel .title {{
      color: var(--smna-primary-strong);
      font-weight: 800;
      font-size: 17px;
      margin-bottom: 4px;
    }}
    #seoulmna-yangdo-calculator .recommend-panel .sub {{
      color: var(--smna-sub);
      font-size: 14px;
      line-height: 1.45;
      margin-bottom: 8px;
    }}
    #seoulmna-yangdo-calculator .recommend-panel .guide {{
      display: none;
      margin-bottom: 8px;
      padding: 10px 11px;
      border-radius: 12px;
      border: 1px solid rgba(15, 159, 176, 0.18);
      background: rgba(15, 159, 176, 0.08);
      color: var(--smna-primary-soft);
      font-size: 14px;
      font-weight: 800;
      line-height: 1.5;
    }}
    #seoulmna-yangdo-calculator .recommend-panel .followup {{
      display: none;
      margin-top: 7px;
      padding: 9px 10px;
      border-radius: 12px;
      border: 1px dashed rgba(0, 55, 100, 0.14);
      background: rgba(0, 55, 100, 0.04);
      color: var(--smna-primary);
      font-size: 13px;
      font-weight: 700;
      line-height: 1.45;
    }}
    #seoulmna-yangdo-calculator .recommend-panel .followup-text {{
      margin: 0;
    }}
    #seoulmna-yangdo-calculator .recommend-panel .followup-note {{
      display: none;
      margin-top: 6px;
      color: var(--smna-sub);
      font-size: 12px;
      font-weight: 700;
      line-height: 1.5;
    }}
    #seoulmna-yangdo-calculator .recommend-panel .followup-actions {{
      display: none;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }}
    #seoulmna-yangdo-calculator .recommend-panel .followup-action {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 34px;
      padding: 0 12px;
      border-radius: 999px;
      border: 1px solid rgba(15, 159, 176, 0.22);
      background: #ffffff;
      color: var(--smna-primary-soft);
      font-size: 13px;
      font-weight: 800;
      cursor: pointer;
      transition: background 0.18s ease, color 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    }}
    #seoulmna-yangdo-calculator .recommend-panel .followup-action[data-rank="1"] {{
      background: var(--smna-primary);
      border-color: var(--smna-primary);
      color: #ffffff;
      box-shadow: 0 12px 28px rgba(0, 55, 100, 0.18);
    }}
    #seoulmna-yangdo-calculator .recommend-panel .followup-action:hover {{
      background: rgba(15, 159, 176, 0.08);
    }}
    #seoulmna-yangdo-calculator .recommend-panel .followup-action[data-rank="1"]:hover {{
      background: var(--smna-primary-soft);
    }}
    #seoulmna-yangdo-calculator .recommend-focus-target {{
      border-color: rgba(0, 55, 100, 0.42) !important;
      box-shadow: 0 0 0 4px rgba(15, 159, 176, 0.16);
      animation: recommend-focus-pulse 0.95s ease;
    }}
    @keyframes recommend-focus-pulse {{
      0% {{ box-shadow: 0 0 0 0 rgba(15, 159, 176, 0.28); }}
      100% {{ box-shadow: 0 0 0 8px rgba(15, 159, 176, 0); }}
    }}
    #seoulmna-yangdo-calculator .recommended-listings {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    #seoulmna-yangdo-calculator .recommend-card {{
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 16px;
      background: #ffffff;
      padding: 12px 13px;
      box-shadow: 0 12px 28px rgba(8, 28, 49, 0.05);
    }}
    #seoulmna-yangdo-calculator .recommend-card .top {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: flex-start;
    }}
    #seoulmna-yangdo-calculator .recommend-card .name {{
      font-size: 18px;
      font-weight: 800;
      color: var(--smna-primary);
      line-height: 1.35;
    }}
    #seoulmna-yangdo-calculator .recommend-card .badge {{
      flex: 0 0 auto;
      border-radius: 999px;
      background: rgba(15, 159, 176, 0.08);
      color: var(--smna-accent-strong);
      font-size: 12px;
      font-weight: 800;
      padding: 4px 8px;
    }}
    #seoulmna-yangdo-calculator .recommend-panel.priority-single .recommend-card {{
      padding: 11px 12px;
    }}
    #seoulmna-yangdo-calculator .recommend-card .price {{
      margin-top: 6px;
      font-size: 16px;
      font-weight: 800;
      color: var(--smna-primary-strong);
    }}
    #seoulmna-yangdo-calculator .recommend-card .reason-chips {{
      margin-top: 6px;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    #seoulmna-yangdo-calculator .recommend-card .reason-chip {{
      border-radius: 999px;
      background: rgba(0, 55, 100, 0.06);
      color: var(--smna-primary-soft);
      font-size: 12px;
      font-weight: 800;
      line-height: 1;
      padding: 5px 8px;
      border: 1px solid rgba(0, 55, 100, 0.08);
    }}
    #seoulmna-yangdo-calculator .recommend-card .reason-chip.primary {{
      background: rgba(15, 159, 176, 0.12);
      color: var(--smna-accent-strong);
      border-color: rgba(15, 159, 176, 0.18);
      box-shadow: 0 8px 16px rgba(15, 159, 176, 0.12);
    }}
    #seoulmna-yangdo-calculator .recommend-card .why {{
      margin-top: 6px;
      font-size: 14px;
      line-height: 1.5;
      color: var(--smna-sub);
      word-break: keep-all;
    }}
    #seoulmna-yangdo-calculator .recommend-card .order-note {{
      margin-top: 5px;
      font-size: 12px;
      line-height: 1.45;
      color: var(--smna-sub);
      word-break: keep-all;
    }}
    #seoulmna-yangdo-calculator .recommend-card .owner-note {{
      margin-top: 5px;
      font-size: 12px;
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .recommend-card .actions {{
      margin-top: 8px;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator .recommend-card .actions a {{
      font-size: 14px;
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator .input-guide {{
      font-size: 16px;
      font-weight: 800;
      color: var(--smna-primary);
      margin: 0 0 10px 0;
      line-height: 1.5;
      background: linear-gradient(180deg, rgba(235,245,250,0.92), rgba(255,255,255,0.96));
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 16px;
      padding: 12px 13px;
    }}
    #seoulmna-yangdo-calculator .wizard-shell {{
      display: grid;
      gap: 14px;
    }}
    #seoulmna-yangdo-calculator .wizard-rail {{
      display: grid;
      gap: 10px;
      margin-bottom: 6px;
    }}
    #seoulmna-yangdo-calculator .wizard-rail-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 15px;
      border-radius: 18px;
      border: 1px solid rgba(0, 55, 100, 0.08);
      background: linear-gradient(180deg, rgba(243,249,253,0.98), rgba(255,255,255,0.98));
    }}
    #seoulmna-yangdo-calculator .wizard-rail-kicker {{
      margin: 0 0 4px 0;
      color: var(--smna-primary-soft);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    #seoulmna-yangdo-calculator .wizard-rail-title {{
      margin: 0;
      color: var(--smna-primary);
      font-size: 20px;
      font-weight: 900;
      line-height: 1.32;
      letter-spacing: -0.02em;
    }}
    #seoulmna-yangdo-calculator .wizard-rail-note {{
      margin: 6px 0 0;
      color: var(--smna-sub);
      font-size: 13px;
      line-height: 1.48;
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator .wizard-summary {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 0 2px 2px;
    }}
    #seoulmna-yangdo-calculator .wizard-summary-chip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 34px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(0, 55, 100, 0.10);
      background: rgba(255,255,255,0.96);
      color: var(--smna-primary);
      font-size: 12px;
      font-weight: 800;
      line-height: 1.35;
      box-shadow: 0 10px 20px rgba(8, 28, 49, 0.05);
    }}
    #seoulmna-yangdo-calculator .wizard-summary-chip.is-empty {{
      color: var(--smna-sub);
      border-style: dashed;
      box-shadow: none;
    }}
    #seoulmna-yangdo-calculator .wizard-blocker {{
      padding: 11px 13px;
      border-radius: 16px;
      border: 1px solid rgba(183, 150, 114, 0.26);
      background: linear-gradient(180deg, rgba(250, 245, 238, 0.98), rgba(255,255,255,0.98));
      color: var(--smna-warning-text);
      font-size: 13px;
      font-weight: 800;
      line-height: 1.48;
    }}
    #seoulmna-yangdo-calculator .wizard-blocker.is-ready {{
      border-color: rgba(15, 159, 176, 0.22);
      background: linear-gradient(180deg, rgba(232, 247, 248, 0.98), rgba(255,255,255,0.98));
      color: var(--smna-accent-strong);
    }}
    #seoulmna-yangdo-calculator .wizard-priority-hint {{
      margin-top: 12px;
      padding: 12px 13px;
      border-radius: 16px;
      border: 1px solid rgba(0, 55, 100, 0.08);
      background: linear-gradient(180deg, rgba(245, 249, 252, 0.98), rgba(255,255,255,0.98));
      color: var(--smna-primary);
      font-size: 13px;
      line-height: 1.5;
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator .wizard-progress {{
      display: flex;
      align-items: flex-start;
      gap: 12px;
      margin-top: 14px;
      padding: 14px 15px;
      border-radius: 18px;
      border: 1px solid rgba(0, 55, 100, 0.08);
      background: linear-gradient(180deg, rgba(244, 248, 252, 0.98), rgba(255,255,255,0.99));
      box-shadow: 0 12px 24px rgba(8, 28, 49, 0.06);
    }}
    #seoulmna-yangdo-calculator .wizard-progress-copy {{
      flex: 1 1 220px;
      min-width: 0;
    }}
    #seoulmna-yangdo-calculator .wizard-progress-label {{
      color: var(--smna-primary);
      font-size: 13px;
      font-weight: 900;
      line-height: 1.4;
    }}
    #seoulmna-yangdo-calculator .wizard-progress-track {{
      position: relative;
      width: 100%;
      height: 8px;
      margin: 9px 0 8px;
      border-radius: 999px;
      background: rgba(0, 55, 100, 0.10);
      overflow: hidden;
    }}
    #seoulmna-yangdo-calculator .wizard-progress-fill {{
      display: block;
      height: 100%;
      width: 0%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--smna-teal-dark) 0%, var(--smna-primary) 100%);
      transition: width 0.22s ease;
    }}
    #seoulmna-yangdo-calculator .wizard-progress-meta {{
      color: var(--smna-sub);
      font-size: 12px;
      line-height: 1.5;
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator .wizard-progress-action {{
      appearance: none;
      display: inline-flex;
      align-items: center;
      justify-content: flex-start;
      flex-wrap: wrap;
      gap: 7px;
      width: 100%;
      margin-top: 10px;
      padding: 8px 11px;
      border-radius: 14px;
      background: rgba(0, 55, 100, 0.06);
      border: 1px solid rgba(0, 55, 100, 0.08);
      cursor: pointer;
      text-align: left;
    }}
    #seoulmna-yangdo-calculator .wizard-progress-action-label {{
      color: var(--smna-primary);
      font-size: 11px;
      line-height: 1.3;
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
      #seoulmna-yangdo-calculator .wizard-progress-action-text {{
        color: var(--smna-primary);
        font-size: 12px;
        line-height: 1.5;
        font-weight: 800;
      }}
      #seoulmna-yangdo-calculator .wizard-progress-support {{
        margin-top: 8px;
        color: var(--smna-sub);
        font-size: 12px;
        line-height: 1.56;
        font-weight: 700;
      }}
      #seoulmna-yangdo-calculator .wizard-progress-support[data-actionable="1"] {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        padding: 8px 10px;
        border-radius: 14px;
        cursor: pointer;
        transition: background 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
      }}
      #seoulmna-yangdo-calculator .wizard-progress-support[data-actionable="1"]::after {{
        content: "눌러서 바로 이동";
        display: inline-flex;
        align-items: center;
        min-height: 22px;
        padding: 0 8px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.94);
        border: 1px solid rgba(0, 55, 100, 0.12);
        color: var(--smna-sub);
        font-size: 11px;
        line-height: 1;
        font-weight: 900;
        letter-spacing: 0.02em;
      }}
      #seoulmna-yangdo-calculator .wizard-progress-support[data-actionable="1"]:hover,
      #seoulmna-yangdo-calculator .wizard-progress-support[data-actionable="1"]:focus-visible {{
        outline: none;
        transform: translateY(-1px);
        background: rgba(0, 55, 100, 0.04);
        box-shadow: 0 0 0 3px rgba(0, 55, 100, 0.08);
      }}
      #seoulmna-yangdo-calculator .value-preview {{
        display: none;
        margin-top: 10px;
        padding: 10px 12px;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(0, 55, 100, 0.04) 0%, rgba(15, 95, 117, 0.06) 100%);
        border: 1px solid rgba(0, 55, 100, 0.09);
      }}
      #seoulmna-yangdo-calculator .value-preview.is-visible {{
        display: block;
        animation: smnaFadeIn 0.24s ease;
      }}
      #seoulmna-yangdo-calculator .value-preview-label {{
        font-size: 11px;
        font-weight: 900;
        color: var(--smna-sub);
        letter-spacing: 0.03em;
        margin-bottom: 5px;
      }}
      #seoulmna-yangdo-calculator .value-preview-range {{
        display: flex;
        align-items: center;
        gap: 8px;
      }}
      #seoulmna-yangdo-calculator .value-preview-bar {{
        flex: 1;
        height: 6px;
        border-radius: 999px;
        background: rgba(0, 55, 100, 0.10);
        position: relative;
        overflow: hidden;
      }}
      #seoulmna-yangdo-calculator .value-preview-fill {{
        position: absolute;
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, var(--smna-primary), var(--smna-teal-dark));
        transition: left 0.3s ease, width 0.3s ease;
      }}
      #seoulmna-yangdo-calculator .value-preview-text {{
        font-size: 14px;
        font-weight: 900;
        color: var(--smna-primary);
        white-space: nowrap;
      }}
      #seoulmna-yangdo-calculator .value-preview-count {{
        font-size: 11px;
        font-weight: 700;
        color: var(--smna-sub);
        margin-top: 4px;
      }}
      #seoulmna-yangdo-calculator .guided-focus-target {{
        position: relative;
        box-shadow: 0 0 0 3px rgba(0, 55, 100, 0.16), 0 18px 34px rgba(0, 55, 100, 0.14);
        border-color: var(--smna-accent-strong) !important;
        animation: yangdoGuidedFocusPulse 0.9s ease-out 1;
      }}
      #seoulmna-yangdo-calculator .guided-focus-target[data-guided-focus-copy]::after {{
        content: attr(data-guided-focus-copy);
        position: absolute;
        top: 10px;
        right: 10px;
        max-width: min(240px, calc(100% - 20px));
        padding: 7px 10px;
        border-radius: 999px;
        background: rgba(0, 55, 100, 0.92);
        color: var(--smna-header-text);
        font-size: 11px;
        line-height: 1.35;
        font-weight: 900;
        letter-spacing: -0.01em;
        box-shadow: 0 12px 22px rgba(0, 55, 100, 0.18);
        z-index: 3;
        pointer-events: none;
        white-space: normal;
      }}
      #seoulmna-yangdo-calculator .guided-focus-target[data-guided-focus-level="sticky"] {{
        box-shadow: 0 0 0 4px rgba(0, 55, 100, 0.20), 0 24px 44px rgba(0, 55, 100, 0.20);
      }}
      #seoulmna-yangdo-calculator .guided-focus-target[data-guided-focus-level="sticky"][data-guided-focus-copy]::after {{
        top: -12px;
        right: auto;
        left: 12px;
        max-width: min(280px, calc(100% - 24px));
        padding: 9px 12px;
        background: linear-gradient(135deg, rgba(0, 55, 100, 0.96), rgba(16, 106, 165, 0.94));
        font-size: 12px;
        box-shadow: 0 16px 28px rgba(0, 55, 100, 0.24);
      }}
      @keyframes yangdoGuidedFocusPulse {{
        0% {{
          box-shadow: 0 0 0 0 rgba(31, 106, 165, 0.30), 0 10px 20px rgba(0, 55, 100, 0.10);
        }}
        100% {{
          box-shadow: 0 0 0 3px rgba(0, 55, 100, 0.16), 0 18px 34px rgba(0, 55, 100, 0.14);
        }}
      }}
    #seoulmna-yangdo-calculator .wizard-progress-count {{
      flex: 0 0 auto;
      min-width: 58px;
      padding: 8px 10px;
      border-radius: 14px;
      background: rgba(0, 55, 100, 0.08);
      color: var(--smna-primary);
      font-size: 15px;
      font-weight: 900;
      letter-spacing: -0.01em;
      text-align: center;
    }}
    #seoulmna-yangdo-calculator .wizard-mobile-sticky {{
      display: none;
      appearance: none;
      width: 100%;
      padding: 11px 13px;
      border-radius: 18px;
      border: 1px solid rgba(0, 55, 100, 0.14);
      background: rgba(255, 255, 255, 0.94);
      backdrop-filter: blur(14px);
      text-align: left;
      box-shadow: 0 12px 24px rgba(8, 28, 49, 0.10);
      cursor: pointer;
    }}
    #seoulmna-yangdo-calculator .wizard-mobile-sticky-copy {{
      min-width: 0;
    }}
    #seoulmna-yangdo-calculator .wizard-mobile-sticky-label {{
      color: var(--smna-primary);
      font-size: 11px;
      line-height: 1.3;
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    #seoulmna-yangdo-calculator .wizard-mobile-sticky-action {{
      margin-top: 3px;
      color: var(--smna-primary);
      font-size: 14px;
      line-height: 1.45;
      font-weight: 900;
      letter-spacing: -0.02em;
      word-break: keep-all;
    }}
    #seoulmna-yangdo-calculator .wizard-mobile-sticky-compact {{
      margin-top: 4px;
      color: var(--smna-sub);
      font-size: 12px;
      line-height: 1.42;
      font-weight: 800;
      word-break: keep-all;
    }}
    #seoulmna-yangdo-calculator .wizard-mobile-sticky-meta {{
      display: none;
      color: var(--smna-sub);
      font-size: 12px;
      line-height: 1.45;
      font-weight: 700;
      word-break: keep-all;
    }}
    #seoulmna-yangdo-calculator .wizard-mobile-sticky-reason {{
      display: none;
      color: var(--smna-primary);
      font-size: 12px;
      line-height: 1.5;
      font-weight: 700;
      word-break: keep-all;
    }}
    #seoulmna-yangdo-calculator .wizard-mobile-sticky-count {{
      margin-top: 8px;
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 5px 10px;
      border-radius: 999px;
      background: rgba(0, 55, 100, 0.08);
      color: var(--smna-primary);
      font-size: 12px;
      font-weight: 900;
      letter-spacing: -0.01em;
    }}
    #seoulmna-yangdo-calculator .wizard-steps {{
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }}
    #seoulmna-yangdo-calculator .wizard-step-chip {{
      appearance: none;
      border: 1px solid rgba(0, 55, 100, 0.08);
      background: rgba(255,255,255,0.98);
      border-radius: 18px;
      padding: 12px 10px;
      text-align: left;
      cursor: pointer;
      transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
    }}
    #seoulmna-yangdo-calculator .wizard-step-chip:hover {{
      border-color: rgba(0, 55, 100, 0.24);
      box-shadow: 0 12px 24px rgba(8, 28, 49, 0.08);
      transform: translateY(-1px);
    }}
    #seoulmna-yangdo-calculator .wizard-step-chip.is-active {{
      border-color: rgba(0, 55, 100, 0.34);
      background: linear-gradient(180deg, rgba(0,55,100,0.08), rgba(255,255,255,1));
      box-shadow: 0 16px 28px rgba(8, 28, 49, 0.10);
    }}
    #seoulmna-yangdo-calculator .wizard-step-chip.is-complete {{
      border-color: rgba(15, 159, 176, 0.28);
      background: linear-gradient(180deg, rgba(15,159,176,0.10), rgba(255,255,255,1));
    }}
    #seoulmna-yangdo-calculator .wizard-step-chip.is-optional {{
      border-style: dashed;
    }}
    #seoulmna-yangdo-calculator .wizard-step-chip.is-alert {{
      border-color: rgba(169, 92, 24, 0.34);
      background: linear-gradient(180deg, rgba(250, 242, 233, 0.98), rgba(255,255,255,1));
      box-shadow: 0 16px 28px rgba(125, 74, 29, 0.12);
    }}
    #seoulmna-yangdo-calculator .wizard-step-chip-label {{
      display: block;
      margin-bottom: 5px;
      color: var(--smna-primary-soft);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    #seoulmna-yangdo-calculator .wizard-step-chip-title {{
      display: block;
      color: var(--smna-primary);
      font-size: 14px;
      font-weight: 900;
      line-height: 1.35;
    }}
    #seoulmna-yangdo-calculator .wizard-step-chip-meta {{
      display: block;
      margin-top: 4px;
      color: var(--smna-sub);
      font-size: 12px;
      line-height: 1.42;
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator .wizard-step-card {{
      display: none;
      margin-bottom: 0;
    }}
    #seoulmna-yangdo-calculator .wizard-step-card.is-active {{
      display: block;
    }}
    #seoulmna-yangdo-calculator .wizard-step-card.optional-step {{
      border: 1px dashed rgba(183, 150, 114, 0.38);
      background: linear-gradient(180deg, rgba(249,245,239,0.98), rgba(255,255,255,0.98));
      border-radius: 18px;
      padding: 16px;
    }}
    #seoulmna-yangdo-calculator .wizard-step-card.is-alert {{
      border-color: rgba(169, 92, 24, 0.44);
      background: linear-gradient(180deg, rgba(252, 245, 237, 0.99), rgba(255,255,255,0.99));
      box-shadow: 0 18px 30px rgba(125, 74, 29, 0.12);
    }}
    #seoulmna-yangdo-calculator .step-choice-tag {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      margin-left: 8px;
      padding: 4px 9px;
      border-radius: 999px;
      background: rgba(183, 150, 114, 0.14);
      color: var(--smna-warning-text);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      vertical-align: middle;
    }}
    #seoulmna-yangdo-calculator .wizard-nav {{
      margin-top: 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator .wizard-nav-copy {{
      flex: 1 1 180px;
      color: var(--smna-sub);
      font-size: 13px;
      line-height: 1.48;
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator .wizard-nav-actions {{
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      flex: 0 0 auto;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator .wizard-nav-btn {{
      appearance: none;
      border: 1px solid rgba(0, 55, 100, 0.12);
      background: rgba(255,255,255,0.98);
      color: var(--smna-primary-strong);
      min-height: 42px;
      padding: 10px 14px;
      border-radius: 999px;
      font-size: 14px;
      font-weight: 800;
      cursor: pointer;
      transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
    }}
    #seoulmna-yangdo-calculator .wizard-nav-btn:hover {{
      border-color: rgba(0, 55, 100, 0.24);
      box-shadow: 0 12px 24px rgba(8, 28, 49, 0.08);
      transform: translateY(-1px);
    }}
    #seoulmna-yangdo-calculator .wizard-nav-btn.is-primary {{
      border-color: rgba(0, 55, 100, 0.88);
      background: linear-gradient(145deg, rgba(0,55,100,1), rgba(15,90,142,0.96));
      color: #fff;
    }}
    #seoulmna-yangdo-calculator .wizard-nav-btn:disabled {{
      opacity: 0.46;
      cursor: not-allowed;
      box-shadow: none;
      transform: none;
    }}
    #seoulmna-yangdo-calculator .info-boxes {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }}
    #seoulmna-yangdo-calculator .info-box {{
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 16px;
      background: rgba(255,255,255,0.92);
      padding: 13px 14px;
      box-shadow: 0 12px 26px rgba(8, 28, 49, 0.05);
    }}
    #seoulmna-yangdo-calculator .info-box.emphasis {{
      background: linear-gradient(135deg, rgba(0, 55, 100, 0.96), rgba(15, 90, 142, 0.94));
      border-color: rgba(0, 55, 100, 0.28);
    }}
    #seoulmna-yangdo-calculator .info-box.emphasis .k,
    #seoulmna-yangdo-calculator .info-box.emphasis .v {{
      color: var(--smna-neutral);
    }}
    #seoulmna-yangdo-calculator .info-box .k {{
      font-size: 14px;
      font-weight: 800;
      color: var(--smna-primary);
      margin-bottom: 5px;
    }}
    #seoulmna-yangdo-calculator .info-box .v {{
      font-size: 16px;
      line-height: 1.45;
      color: var(--smna-primary-strong);
      word-break: keep-all;
    }}
    #seoulmna-yangdo-calculator .lead-capture {{
      margin-top: 10px;
      border: 1px solid rgba(15, 159, 176, 0.18);
      border-radius: 16px;
      background: linear-gradient(180deg, rgba(255,255,255,0.97), rgba(240,248,250,0.96));
      padding: 13px 14px;
      display: none;
    }}
    #seoulmna-yangdo-calculator .lead-capture .msg {{
      font-size: 16px;
      font-weight: 700;
      line-height: 1.45;
      color: var(--smna-primary);
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
      color: var(--smna-sub);
    }}
    #seoulmna-yangdo-calculator .result-share-wrap {{
      margin-top: 10px;
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 16px;
      background: linear-gradient(180deg, rgba(250,252,255,0.98), rgba(242,247,251,0.96));
      padding: 12px 13px;
    }}
    #seoulmna-yangdo-calculator .recommend-panel.priority-single + .action-steps.compact-followup + .result-share-wrap {{
      margin-top: 8px;
      padding: 11px 12px;
    }}
    #seoulmna-yangdo-calculator .result-share-note {{
      font-size: 14px;
      line-height: 1.5;
      color: var(--smna-sub);
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator .result-brief-wrap {{
      display: grid;
      gap: 8px;
      margin-top: 10px;
      padding: 11px 12px;
      border-radius: 14px;
      border: 1px solid rgba(0, 55, 100, 0.08);
      background: rgba(255, 255, 255, 0.86);
    }}
    #seoulmna-yangdo-calculator .result-brief-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
    }}
    #seoulmna-yangdo-calculator .result-brief-label {{
      font-size: 13px;
      font-weight: 900;
      letter-spacing: -0.01em;
      color: var(--smna-primary);
    }}
    #seoulmna-yangdo-calculator #result-brief {{
      width: 100%;
      min-height: 64px;
      resize: vertical;
      border-radius: 12px;
      border: 1px solid rgba(0, 55, 100, 0.12);
      background: var(--smna-neutral);
      color: var(--smna-primary);
      font-size: 13px;
      line-height: 1.5;
      padding: 10px 11px;
    }}
    #seoulmna-yangdo-calculator .result-brief-meta {{
      font-size: 12px;
      line-height: 1.5;
      color: var(--smna-sub);
      font-weight: 700;
    }}
    #seoulmna-yangdo-calculator .result-share-actions {{
      display: none;
    }}
    #seoulmna-yangdo-calculator .result-share-wrap.ready .result-share-actions {{
      display: flex;
    }}
    #seoulmna-yangdo-calculator .compliance-note {{
      margin-top: 10px;
      padding: 10px 11px;
      border: 1px solid rgba(0, 55, 100, 0.08);
      border-radius: 14px;
      background: var(--smna-neutral);
      color: var(--smna-primary);
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
      color: var(--smna-primary-strong);
    }}
    #seoulmna-yangdo-calculator .consent-check input {{
      width: 18px;
      height: 18px;
      margin-top: 2px;
      flex: 0 0 auto;
    }}
    @media (max-width: 1280px) {{
      #seoulmna-yangdo-calculator .smna-grid {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .panel.result {{ position: static; top: auto; }}
    }}
    @media (max-width: 980px) {{
      #seoulmna-yangdo-calculator .smna-meta {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      #seoulmna-yangdo-calculator .smna-grid {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .input-row {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .field.wide {{ grid-column: auto; }}
      #seoulmna-yangdo-calculator .result-grid {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .info-boxes {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .smart-metrics {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .scale-mode-switch {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .recommended-listings {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .consult-grid {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .checks {{ grid-template-columns: 1fr; }}
      #seoulmna-yangdo-calculator .wizard-steps {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      #seoulmna-yangdo-calculator .wizard-rail-head {{ flex-direction: column; }}
      #seoulmna-yangdo-calculator .wizard-mobile-sticky {{
        display: grid;
        position: sticky;
        top: 10px;
        z-index: 26;
      }}
      #seoulmna-yangdo-calculator h2 {{ font-size: 33px; }}
      #seoulmna-yangdo-calculator .impact .cta-text {{ font-size: 17px; }}
      #seoulmna-yangdo-calculator .cta-button {{ font-size: 18px; }}
      #seoulmna-yangdo-calculator .panel h3 {{ font-size: 26px; }}
    }}
    @media (max-width: 640px) {{
      #seoulmna-yangdo-calculator .panel .panel-body {{ padding: 15px; }}
      #seoulmna-yangdo-calculator .btn-row {{ position: sticky; bottom: 0; z-index: 40; background: linear-gradient(to top, rgba(255,255,255,0.98) 70%, transparent); padding: 12px 0 4px; margin-left: -15px; margin-right: -15px; padding-left: 15px; padding-right: 15px; }}
      #seoulmna-yangdo-calculator .result-grid {{ gap: 8px; margin-bottom: 6px; }}
      #seoulmna-yangdo-calculator .yoy-compare {{ margin-top: 6px; padding: 8px 10px; }}
      #seoulmna-yangdo-calculator .risk-note {{ margin-top: 6px; padding: 10px 11px; font-size: 15px; }}
      #seoulmna-yangdo-calculator .settlement-panel {{ margin-top: 8px; padding: 9px 10px; }}
      #seoulmna-yangdo-calculator .settlement-grid {{ margin-top: 7px; gap: 7px; }}
      #seoulmna-yangdo-calculator .settlement-scenarios {{ margin-top: 8px; gap: 7px; }}
      #seoulmna-yangdo-calculator .action-steps {{ margin-top: 8px; padding: 11px 12px; }}
      #seoulmna-yangdo-calculator .action-steps .title {{ margin-bottom: 5px; }}
      #seoulmna-yangdo-calculator .recommend-panel {{ margin-top: 8px; padding: 11px 12px; }}
      #seoulmna-yangdo-calculator .recommend-panel .guide {{ margin-bottom: 6px; padding: 9px 10px; font-size: 13px; }}
      #seoulmna-yangdo-calculator .recommend-panel .sub {{ margin-bottom: 6px; }}
      #seoulmna-yangdo-calculator .recommended-listings {{ gap: 8px; }}
      #seoulmna-yangdo-calculator .recommend-card {{ padding: 11px 12px; }}
      #seoulmna-yangdo-calculator .recommend-card .reason-chip.primary {{ padding: 6px 10px; font-size: 13px; }}
      #seoulmna-yangdo-calculator .neighbor-panel summary {{ padding: 10px 11px; }}
      #seoulmna-yangdo-calculator .neighbor-panel summary .sub {{ font-size: 11px; }}
    }}

    /* ── Design System Components (#003764) ── */
    #seoulmna-yangdo-calculator .badge-success {{ background: var(--smna-badge-success-bg); color: var(--smna-success, #00C48C); padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; display: inline-block; }}
    #seoulmna-yangdo-calculator .badge-warning {{ background: var(--smna-badge-warning-bg); color: var(--smna-warning, #FFB800); padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; display: inline-block; }}
    #seoulmna-yangdo-calculator .badge-error {{ background: var(--smna-badge-error-bg); color: var(--smna-error, #FF4757); padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; display: inline-block; }}
    #seoulmna-yangdo-calculator .badge-info {{ background: var(--smna-badge-info-bg); color: var(--smna-primary, #003764); padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; display: inline-block; }}
    #seoulmna-yangdo-calculator .sector-chip {{ padding: 6px 14px; border-radius: 20px; background: var(--smna-neutral); color: var(--smna-sub, #4B5563); font-size: 14px; cursor: pointer; transition: all 0.2s ease; border: none; }}
    #seoulmna-yangdo-calculator .sector-chip:hover {{ background: var(--smna-border); }}
    #seoulmna-yangdo-calculator .sector-chip.active {{ background: var(--smna-primary, #003764); color: #FFFFFF; }}
    #seoulmna-yangdo-calculator .bottom-cta-wrap {{ position: sticky; bottom: 0; left: 0; right: 0; padding: 16px 20px; background: linear-gradient(to top, #fff 80%, transparent); z-index: 50; }}
    #seoulmna-yangdo-calculator .btn-primary {{ width: 100%; height: 52px; background: var(--smna-primary, #003764); color: white; border-radius: 12px; font-size: 17px; font-weight: 600; border: none; cursor: pointer; transition: background 0.2s; }}
    #seoulmna-yangdo-calculator .btn-primary:hover {{ background: var(--smna-primary-strong, #002244); }}
    #seoulmna-yangdo-calculator .alert-banner {{ background: var(--smna-neutral, #F8FAFB); border-left: 3px solid var(--smna-accent, #00A3FF); padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 8px 0; font-size: 14px; }}
    #seoulmna-yangdo-calculator .step-indicator {{ height: 4px; background: var(--smna-border); border-radius: 2px; overflow: hidden; }}
    #seoulmna-yangdo-calculator .step-indicator-fill {{ height: 100%; background: var(--smna-accent, #00A3FF); border-radius: 2px; transition: width 0.3s ease; }}
  </style>

  <div class="smna-header">
    <div class="smna-brand-row">
      <div class="smna-brand" style="color:var(--smna-header-text);font-weight:800;">{escape(brand_label)}</div>
      <div class="smna-mode">{'실시간 고객 화면' if mode == "customer" else '내부 검수 화면(비공개)'}</div>
    </div>
    <div class="smna-badge">전국 최초</div>
    <h2 id="yangdo-main-title" style="color:var(--smna-header-text) !important;">{escape(title)}</h2>
    <div class="smna-subtitle" style="color:var(--smna-header-sub);">{escape(subtitle_text)}</div>
    <div class="smna-ratio"><div></div><div></div><div></div></div>
  </div>

  <div class="smna-body">
    <div class="smna-meta">
      <div class="item"><span class="label">전체 매물</span><strong class="value" id="meta-all">-</strong></div>
      <div class="item"><span class="label">가격 확인 매물</span><strong class="value" id="meta-train">-</strong></div>
      <div class="item"><span class="label">{escape(meta_mid_label)}</span><strong class="value" id="meta-mid">-</strong></div>
      <div class="item"><span class="label">데이터 갱신시각</span><strong class="value" id="meta-updated" style="font-size:17px">-</strong></div>
    </div>
    <div class="impact cta-row">
      <span class="cta-text">{escape(top_cta_text)}</span>
      <span class="cta-actions">
        <button type="button" class="cta-button chat" id="btn-openchat-top">{escape(top_cta_button_text)}</button>
        <a id="btn-call-top" class="cta-button call" href="tel:{escape(contact_phone_digits or DEFAULT_CONTACT_PHONE_DIGITS)}">{escape(contact_phone)}</a>
      </span>
    </div>
    <div class="impact">AI가 유사 매물 + 핵심 입력값을 종합 계산해 예상 양도가 범위를 제시합니다. 업종을 넣으면 통상 매물 기준값을 먼저 채워 대표님 입력 부담을 줄입니다.</div>
    <div class="info-boxes">
      <div class="info-box emphasis">
        <div class="k">상단 필수 입력</div>
        <div class="v">면허/업종, 검색 기준(시평 또는 실적), 자본금, 필수 기준 충족 여부만 먼저 입력하면 바로 계산됩니다. 일반 업종만 공제조합 잔액을 가격에 반영합니다.</div>
      </div>
      <div class="info-box">
        <div class="k">자동 입력</div>
        <div class="v">업종을 입력하면 통상 매물 기준의 자본금·이익잉여금을 먼저 제안합니다. 일반 업종은 공제조합 잔액도 가격용으로 제안하고, 전기·정보통신·소방은 별도 정산 참고값으로만 안내합니다.</div>
      </div>
      <div class="info-box">
        <div class="k">데이터 상태</div>
        <div class="v" id="data-quality-box">전체 매물 중 가격이 숫자로 확인된 매물만 계산 기준으로 사용합니다.</div>
      </div>
      <div class="info-box">
        <div class="k">검색 편의성</div>
        <div class="v">ENCAR처럼 한 축만 먼저 잡도록 시평 검색 또는 실적 검색 중 하나를 선택합니다. 동시에 두 축을 강하게 넣어 값이 튀는 문제를 줄였습니다.</div>
      </div>
    </div>

    <div class="smna-grid">
      <div class="panel">
        <h3>1단계: 핵심 거래 정보 입력</h3>
        <div class="panel-body">
          <div class="input-guide">대표님이 가장 많이 묻는 순서대로 재배치했습니다. 먼저 업종을 고르면 통상 매물 기준값이 채워지고, 검색 기준은 시평 또는 실적 중 한 축만 선택해 빠르게 계산합니다.</div>
          <div class="draft-restore-note" id="draft-restore-note">
            <span class="draft-restore-note-text" id="draft-restore-note-text"></span>
            <span class="draft-restore-actions" id="draft-restore-actions">
              <button type="button" class="draft-restore-action is-primary" id="draft-restore-estimate-action">바로 계산</button>
              <button type="button" class="draft-restore-action" id="draft-restore-action">새로 시작</button>
            </span>
          </div>
          <div class="avg-guide" id="avg-guide">평균 지표를 불러오는 중...</div>
          <div class="input-row">
            <div class="field wide required-field">
              <label for="in-license">면허/업종 <span class="required-pill" aria-hidden="true">필수</span></label>
              <input id="in-license" type="text" maxlength="120" list="license-suggestions" placeholder="예: 토목, 상하, 철콘, 실내건축" aria-required="true" />
              <datalist id="license-suggestions"></datalist>
              <div class="field-sub">인기 면허를 바로 선택하거나 직접 입력하세요. 복수 면허는 쉼표로 구분합니다.</div>
              <div class="license-chip-row" id="license-quick-chips"></div>
            </div>
            <div class="field wide">
              <div class="smart-panel" id="smart-profile-card">
                <div class="smart-panel-head">
                  <div>
                    <div class="smart-panel-title">업종 기준 자동 제안</div>
                    <p class="smart-panel-note" id="smart-profile-note">업종을 입력하면 거래되는 통상 매물 기준값을 바로 채웁니다.</p>
                  </div>
                  <button type="button" class="btn-neutral btn-mini" id="btn-apply-license-profile">기준값 다시 적용</button>
                </div>
                <div class="smart-metrics">
                  <div class="smart-metric">
                    <span class="k">통상 자본금</span>
                    <strong class="v" id="smart-capital">-</strong>
                    <span class="sub">고급 입력에 자동 반영</span>
                  </div>
                  <div class="smart-metric">
                    <span class="k">통상 이익잉여금</span>
                    <strong class="v" id="smart-surplus">-</strong>
                    <span class="sub">고급 입력에 자동 반영</span>
                  </div>
                  <div class="smart-metric highlight">
                    <span class="k" id="smart-balance-label">미입력 시 공제조합 잔액</span>
                    <strong class="v" id="smart-balance">-</strong>
                    <span class="sub" id="smart-balance-sub">최대 융자 60% 이후 남는 통상 최저 잔액 기준</span>
                  </div>
                  <div class="smart-metric">
                    <span class="k">대표 참고 스케일</span>
                    <strong class="v" id="smart-scale">-</strong>
                    <span class="sub" id="smart-profile-token">업종 입력 후 표시</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="field wide">
              <label>검색 기준 <span class="required-pill">필수</span></label>
              <input id="in-scale-search-mode" type="hidden" value="specialty" />
              <div class="scale-mode-switch" id="scale-mode-switch">
                <button type="button" class="scale-mode-btn active" data-scale-mode="specialty">
                  <span class="eyebrow">Primary Search</span>
                  <span class="title">시평으로 찾기</span>
                  <span class="desc">시평 한 값만 빠르게 넣고 유사 매물을 좁힙니다.</span>
                </button>
                <button type="button" class="scale-mode-btn" data-scale-mode="sales">
                  <span class="eyebrow">Primary Search</span>
                  <span class="title">실적으로 찾기</span>
                  <span class="desc">연도별, 3년, 5년 중 한 방식으로만 실적을 넣습니다.</span>
                </button>
              </div>
              <div class="field-sub" id="scale-mode-switch-note">동시에 두 축을 강하게 넣어 값이 튀는 문제를 줄이기 위해 한 번에 한 축만 주 검색 기준으로 씁니다.</div>
            </div>
            <div class="field wide scale-search-panel" id="specialty-search-panel">
              <label for="in-specialty">시평(억) <span class="required-pill">시평 검색</span></label>
              <input id="in-specialty" type="number" step="0.1" placeholder="예: 32" />
              <div class="field-sub" id="specialty-search-note">시평 기준으로 먼저 찾고 싶을 때 씁니다.</div>
            </div>
            <div class="field wide scale-search-panel is-hidden" id="sales-search-panel">
              <div class="input-row" style="margin-bottom:0">
                <div class="field wide">
                  <label for="in-sales-input-mode">실적 입력 방식 <span class="required-pill">실적 검색</span></label>
                  <select id="in-sales-input-mode">
                    <option value="yearly">연도별 입력 (2023~2025)</option>
                    <option value="sales3">최근 3년 실적 합계(억)</option>
                    <option value="sales5">최근 5년 실적 합계(억)</option>
                  </select>
                </div>
                <div class="field" id="sales-yearly-group"><label for="in-y23">2023 매출(억)</label><input id="in-y23" type="number" step="0.1" /></div>
                <div class="field" id="sales-yearly-group-2"><label for="in-y24">2024 매출(억)</label><input id="in-y24" type="number" step="0.1" /></div>
                <div class="field" id="sales-yearly-group-3"><label for="in-y25">2025 매출(억)</label><input id="in-y25" type="number" step="0.1" /></div>
                <div class="field" id="sales-total-group"><label for="in-sales3-total">최근 3년 실적 합계(억)</label><input id="in-sales3-total" type="number" step="0.1" /></div>
                <div class="field" id="sales-total-group-2"><label for="in-sales5-total">최근 5년 실적 합계(억)</label><input id="in-sales5-total" type="number" step="0.1" /></div>
              </div>
              <div class="field-sub" id="sales-search-note">선택한 방식 한 개만 채우면 됩니다. 다른 실적 칸은 참조용으로만 유지됩니다.</div>
            </div>
            <div class="field strong required-field">
              <label for="in-balance"><span id="balance-label-text">공제조합 잔액(억)</span> <span class="required-pill" id="balance-impact-pill">일반 업종 가격 반영</span></label>
              <input id="in-balance" type="number" step="0.01" placeholder="미입력 시 업종 기준 자동 적용" />
              <div class="field-note" id="balance-auto-note">미입력 시 업종 기준 통상 최저 잔액을 자동 반영합니다.</div>
            </div>
            <div class="field wide">
              <label>가격 영향 체크 <span class="required-pill">필수</span></label>
              <div class="checks">
                <label><input id="ok-capital" type="checkbox" checked /> 자본금 기준 충족</label>
                <label><input id="ok-engineer" type="checkbox" checked /> 기술자 기준 충족</label>
                <label><input id="ok-office" type="checkbox" checked /> 사무실 기준 충족</label>
              </div>
              <div class="field-sub">세 항목 중 미충족이 있으면 최종 가격을 보수적으로 낮춰 계산합니다.</div>
            </div>
            <details class="advanced-panel field wide" id="advanced-inputs">
              <summary>고급 입력 열기: 가격 보정용 보조 항목</summary>
              <div class="advanced-panel-body">
                <div class="input-row" style="margin-bottom:0">
                  <div class="field wide" id="reorg-mode-wrap">
                    <label for="in-reorg-mode">양도 구조</label>
                    <select id="in-reorg-mode">
                      <option value="">선택 안함</option>
                      <option value="포괄">포괄</option>
                      <option value="분할/합병">분할/합병</option>
                    </select>
                    <div class="reorg-choice-grid" id="reorg-choice-grid">
                      <button type="button" class="reorg-choice-btn" data-reorg-choice="포괄">
                        <span class="eyebrow">기본 구조</span>
                        <span class="title">포괄</span>
                        <span class="desc">시평과 재무 보정까지 함께 반영하는 일반 구조입니다.</span>
                      </button>
                      <button type="button" class="reorg-choice-btn" data-reorg-choice="분할/합병">
                        <span class="eyebrow">구조 필수</span>
                        <span class="title">분할/합병</span>
                        <span class="desc">전기·정보통신·소방은 실적과 자본금 중심으로 다시 계산합니다.</span>
                      </button>
                    </div>
                    <div class="reorg-compare-grid" id="reorg-compare-grid">
                      <div class="reorg-compare-card" data-reorg-compare="포괄">
                        <span class="eyebrow">포괄 기준</span>
                        <span class="title">시평·재무 보정 포함</span>
                        <span class="desc">시평, 외부신용, 부채/유동비율, 이익잉여금까지 함께 반영하는 일반 구조입니다.</span>
                        <span class="meta">일반 업종 기본 구조</span>
                      </div>
                      <div class="reorg-compare-card" data-reorg-compare="분할/합병">
                        <span class="eyebrow">분할/합병 기준</span>
                        <span class="title">실적·자본금 중심</span>
                        <span class="desc">전기·정보통신·소방은 시평과 재무 보정을 빼고 다시 계산합니다.</span>
                        <span class="meta">특수 업종 구조 필수</span>
                      </div>
                    </div>
                    <div id="reorg-compare-note" class="field-note">업종을 고르면 구조별 계산 차이를 바로 비교합니다.</div>
                    <div class="field-sub">전기/정보통신/소방에서 <strong>분할/합병</strong>을 선택하면 시평·외부신용·부채/유동비율·이익잉여금은 가격 반영에서 제외합니다.</div>
                    <div id="reorg-mode-note" class="field-note" style="display:none"></div>
                  </div>
                  <div class="field wide" id="balance-usage-wrap">
                    <label for="in-balance-usage-mode">공제조합 정산 방식</label>
                    <select id="in-balance-usage-mode">
                      <option value="auto">기본값(시장 관행 기준)</option>
                      <option value="loan_withdrawal">양도자가 조합 융자 인출 후 현금 차감</option>
                      <option value="credit_transfer">양수자가 공제잔액을 인수해 1:1 차감</option>
                      <option value="none">공제조합 잔액 별도 정산 없음</option>
                    </select>
                    <div class="field-note" id="balance-usage-note">일반 업종은 공제조합 잔액 반영 구조를 고르고, 전기·정보통신·소방은 정산 시나리오 비교용으로 사용합니다.</div>
                  </div>
                  <div class="field strong"><label for="in-capital">자본금(억, 고급)</label><input id="in-capital" type="number" step="0.1" /></div>
                  <div class="field strong"><label for="in-surplus">이익잉여금(억, 고급)</label><input id="in-surplus" type="number" step="0.1" /></div>
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
                </div>
              </div>
            </details>
          </div>
          <div class="btn-row">
            <button type="button" class="btn-primary" id="btn-estimate">AI 예상 양도가 계산</button>
            <button type="button" class="btn-neutral" id="btn-reset">입력 초기화</button>
          </div>
          <div class="small" style="margin-top:8px">
            데이터 기준: {escape(brand_name)} 매물 DB 대조 · 유사도 기반 정밀 계산. 일반 업종의 공제조합 잔액만 미입력 시 업종 기준 통상 최저 잔액으로 자동 보정하고, 전기·정보통신·소방은 별도 정산 참고값으로만 봅니다.
          </div>
        </div>
      </div>

      <div class="panel result" id="estimate-result-panel">
        <h3>2단계: AI 산정 결과 확인</h3>
        <div class="panel-body">
          <div class="result-grid">
            <div class="result-card"><span class="k">예상 총 거래가</span><strong class="v" id="out-center">-</strong></div>
            <div class="result-card"><span class="k">총 거래가 범위</span><strong class="v" id="out-range">-</strong></div>
              <div class="result-card"><span class="k">예상 현금 정산액</span><strong class="v" id="out-cash-due">-</strong></div>
            <div class="result-card"><span class="k" id="out-balance-label">공제 활용분</span><strong class="v" id="out-realizable-balance">-</strong></div>
            <div class="result-card"><span class="k">예측 신뢰도</span><strong class="v" id="out-confidence">-</strong></div>
            <div class="result-card"><span class="k">비슷한 사례 수</span><strong class="v" id="out-neighbors">-</strong></div>
            <div class="result-card"><span class="k">사례 근거 수준</span><strong class="v" id="out-source-tier">-</strong></div>
          </div>
          <div class="yoy-compare" id="out-yoy-compare">동일 조건 전년 대비 비교는 계산 후 표시됩니다.</div>
          <div id="result-reason-chips" class="result-reason-chips" style="display:none"></div>
          <div id="risk-note" class="risk-note" aria-live="polite" aria-atomic="true">AI 산정 전: 면허/업종, 검색 기준(시평 또는 실적), 자본금, 필수 기준 충족 여부를 먼저 확인해 주세요.</div>
          <div id="settlement-panel" class="settlement-panel" style="display:none">
            <div class="title">정산 안내</div>
                <div class="sub" id="settlement-summary">총 거래가와 공제 활용분을 분리해 현금 정산액을 해석합니다.</div>
            <div class="settlement-grid">
              <div class="settlement-item"><span class="k">총 거래가</span><strong class="v" id="out-settlement-total">-</strong></div>
              <div class="settlement-item"><span class="k" id="out-settlement-balance-label">공제 활용분</span><strong class="v" id="out-settlement-balance">-</strong></div>
                  <div class="settlement-item"><span class="k">예상 현금 정산액</span><strong class="v" id="out-settlement-cash">-</strong></div>
            </div>
            <ul id="settlement-notes" class="settlement-notes"></ul>
            <div id="settlement-scenarios" class="settlement-scenarios" style="display:none"></div>
          </div>
{hot_match_section_html}
          <div class="result-share-wrap" id="result-share-wrap">
            <div class="result-share-note" id="result-share-note">AI 계산 후 결과 전달 버튼이 열립니다. 먼저 핵심 입력을 완료하고 계산을 실행해 주세요.</div>
            <div class="result-brief-wrap" id="result-brief-wrap">
              <div class="result-brief-head">
                <div class="result-brief-label">상담 전달용 한 줄 브리프</div>
                <button type="button" class="btn-neutral" id="btn-copy-brief" disabled>한 줄 브리프 복사</button>
              </div>
              <textarea id="result-brief" readonly placeholder="AI 계산 후 대표가 카카오톡이나 내부 메신저로 바로 전달할 한 줄 요약을 자동 생성합니다."></textarea>
              <div class="result-brief-meta" id="result-brief-meta">핵심 수치와 정산 포인트만 한 줄로 정리해 전달 속도를 높입니다.</div>
            </div>
            <div class="btn-row result-share-actions" id="result-share-actions" style="margin-top:10px">
              <button type="button" class="btn-accent" id="btn-openchat-result">결과를 오픈채팅으로 전달</button>
              <button type="button" class="btn-neutral" id="btn-copy-result">결과 요약 복사</button>
              <button type="button" class="btn-neutral" id="btn-email-result">결과를 이메일로 전달</button>
            </div>
          </div>
          <div class="action-steps" id="result-action-steps">
            <div class="title" id="recommend-actions-title">지금 하면 좋은 순서 3단계</div>
            <ol id="recommend-actions">
              <li>면허/업종을 먼저 선택해 통상 매물 기준값을 자동으로 불러옵니다.</li>
              <li>시평 검색 또는 실적 검색 중 한 축만 선택해 핵심 규모 값을 입력합니다.</li>
              <li>결과 요약을 복사하거나 메일로 전달해 내부 검토에 활용합니다.</li>
            </ol>
          </div>
          <div class="recommend-panel" id="recommend-panel">
            <div class="title">추천 매물</div>
            <div class="sub">가격 사례표와 별도로, 입력한 업종·선택한 검색축·규모에 가까운 매물을 먼저 골랐습니다.</div>
            <div class="guide" id="recommend-panel-guide">표본이 적을 때는 아래 비슷한 사례 2~3건의 핵심 조건부터 먼저 보세요.</div>
            <div id="recommended-listings" class="recommended-listings"><div class="small">계산 후 입력한 업종·검색축·규모에 가까운 추천 매물이 표시됩니다.</div></div>
            <div class="followup" id="recommend-panel-followup">
              <div class="followup-text" id="recommend-panel-followup-text">최근 3년 실적을 1~2건만 더 보강하면 현재 범위를 더 줄이는 데 도움이 됩니다.</div>
              <div class="followup-note" id="recommend-panel-followup-note">1순위는 최근 3년 실적, 2순위는 자본금입니다. 두 값만 보강해도 다음 계산에서 범위를 더 빨리 줄일 수 있습니다.</div>
              <div class="followup-actions" id="recommend-panel-followup-actions">
                <button type="button" class="followup-action" id="recommend-panel-followup-action" style="display:none">1순위 · 최근 3년 실적 보강</button>
                <button type="button" class="followup-action" id="recommend-panel-followup-secondary-action" style="display:none">2순위 · 자본금 보강</button>
              </div>
            </div>
          </div>
{consult_section_html}
          <details class="neighbor-panel" id="neighbor-panel" open>
            <summary>
              <span id="neighbor-panel-label">비슷한 사례 표 자세히 보기</span>
              <span class="sub" id="neighbor-panel-summary">추천 매물 아래에서 실제 사례표를 열어 확인하세요.</span>
            </summary>
            <table>
              <thead id="neighbor-head"></thead>
              <tbody id="neighbor-body"><tr><td colspan="5" class="small">아직 산정 결과가 없습니다.</td></tr></tbody>
            </table>
          </details>
          <div class="foot">주의: 본 산정치는 참고용입니다. 법정/계약 효력은 없으며 최종 거래가는 실사 결과, 채무 조건, 협의사항으로 달라질 수 있습니다.</div>
          <div class="trust-signal" id="trust-signal" aria-label="최근 시장 현황">
            <div class="trust-signal-items" id="trust-signal-items"></div>
            <div class="trust-signal-meta" id="trust-signal-meta"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script nowprocket data-nowprocket>
    // nowprocket
    /* ── global error boundary ─────────────────────────────────── */
    window.addEventListener("error", function(event) {{
      var node = document.getElementById("seoulmna-yangdo-calculator");
      var fb = node && node.querySelector(".yangdo-error-banner");
      if (!fb) {{
        fb = document.createElement("div");
        fb.className = "yangdo-error-banner";
        fb.style.cssText = "padding:12px 16px;background:#FFF3CD;border:1px solid #FFD54F;border-radius:8px;margin:12px 0;font-size:14px;color:#664D03;";
        fb.textContent = "양도가 산정 도구에서 예기치 않은 오류가 발생했습니다. 페이지를 새로고침해 주세요.";
        if (node) node.prepend(fb);
      }}
      if (window.console) {{
        try {{ console.error("[yangdo] unhandled error:", event.error || event.message); }} catch (_e) {{}}
      }}
    }});
    window.addEventListener("unhandledrejection", function(event) {{
      if (window.console) {{
        try {{ console.error("[yangdo] unhandled rejection:", event.reason); }} catch (_e) {{}}
      }}
    }});
    /* ── /global error boundary ────────────────────────────────── */
    // DOMContentLoaded
    (function() {{
      const datasetRaw = {dataset_json};
      const meta = {meta_json};
      const viewMode = {mode_json};
      const canonicalByKey = {canonical_map_json};
      const genericKeys = new Set({generic_keys_json});
      const licenseProfileBundle = {license_profiles_json};
      const consultEndpointRaw = {consult_endpoint_json};
      const usageEndpointRaw = {usage_endpoint_json};
      const estimateEndpointRaw = {estimate_endpoint_json};
      const apiKeyRaw = {api_key_json};
      const brandName = {brand_name_json};
      const consultPhone = {contact_phone_json};
      const consultOpenchatUrl = {openchat_url_json};
      const consultEmailDefault = {consult_email_json};
      const sourceTagPrefix = {source_tag_prefix_json};
      const enableConsultWidget = !!{enable_consult_widget_json};
      const enableUsageLog = !!{enable_usage_log_json};
      const enableHotMatch = !!{enable_hot_match_json};
      const YANGDO_SERVICE_TRACK = "transfer_price_estimation";
      const YANGDO_BUSINESS_DOMAIN = "yangdo_transfer";
      const YANGDO_PAGE_MODE = "yangdo_calculator";
      const YANGDO_SOURCE_TAG = `${{sourceTagPrefix || "channel"}}_yangdo_ai`;
      const isLoopbackEndpoint = (src) => /^(?:https?:\\/\\/)?(?:localhost|127\\.0\\.0\\.1|::1)(?::\\d+)?(?:\\/|$)/i.test(String(src || "").trim());
      const consultEndpoint = (() => {{
        if (!enableConsultWidget) return "";
        const src = String(consultEndpointRaw || "").trim();
        if (!src || isLoopbackEndpoint(src)) return "";
        return src;
      }})();
      const usageEndpoint = (() => {{
        if (!enableUsageLog) return "";
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
      const apiKey = String(apiKeyRaw || "").trim();
      const buildApiHeaders = (baseHeaders) => {{
        const out = Object.assign({{}}, baseHeaders || {{}});
        if (apiKey) out["X-API-Key"] = apiKey;
        return out;
      }};
      const siteMna = "{site_url.rstrip("/") if site_url else ""}/mna";
      const consultEmail = consultEmailDefault || "";
      const consultSubjectPrefix = viewMode === "owner" ? `[내부검수] ${{brandName}} AI 산정 상담 요청` : `[고객] ${{brandName}} AI 산정 상담 요청`;
      let lastEstimate = null;
      let isEstimating = false;
      let lastEstimateClickAt = 0;
      let pendingResultPanelScroll = false;
      let recommendAutoLoop = null;
      let recommendAutoLoopTimer = 0;
      let isSubmittingConsult = false;
      let neighborPanelDisclosureManual = false;
      let neighborPanelDisclosureSyncing = false;
      let recommendedListingCount = 0;
      const draftStorageKey = `smna_yangdo_draft_${{viewMode || "customer"}}`;
      const urlParams = new URLSearchParams(String(location.search || ""));
      const embedFromCo = (urlParams.get("from") || "").toLowerCase() === "co";
      const forceHideElements = (selector) => {{
        document.querySelectorAll(selector).forEach((el) => {{
          if (!el) return;
          el.style.setProperty("display", "none", "important");
          el.style.setProperty("visibility", "hidden", "important");
          el.style.setProperty("height", "0", "important");
          el.style.setProperty("min-height", "0", "important");
          el.style.setProperty("margin", "0", "important");
          el.style.setProperty("padding", "0", "important");
        }});
      }};
      const hideStandalonePageTitle = () => {{
        try {{ forceHideElements(".entry-header, .entry-title, .wp-block-post-title"); }} catch (_e) {{}}
      }};
      const hideEmbedChrome = () => {{
        try {{
          forceHideElements([
            "#masthead", "header", ".site-header",
            ".site-main-header-wrap", ".ast-main-header-wrap",
            ".main-header-bar-wrap", ".ast-mobile-header-wrap",
            ".main-header-bar", ".ast-primary-header-bar",
            ".site-logo-img", ".site-branding", ".ast-site-identity",
            ".ast-builder-layout-element", ".custom-logo-link", ".custom-logo",
            ".entry-header", ".entry-title", ".wp-block-post-title",
            ".ast-breadcrumbs", "#colophon", ".site-below-footer-wrap",
          ].join(","));
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
      try {{
        hideStandalonePageTitle();
        const titleObserver = new MutationObserver(() => hideStandalonePageTitle());
        titleObserver.observe(document.documentElement || document.body, {{ childList: true, subtree: true }});
      }} catch (_e) {{}}
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
      const _debounce = (fn, ms) => {{
        let tid;
        const d = (...a) => {{ clearTimeout(tid); tid = setTimeout(() => fn(...a), ms); }};
        d.cancel = () => clearTimeout(tid);
        d.flush = (...a) => {{ clearTimeout(tid); fn(...a); }};
        return d;
      }};
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
      const licenseProfiles = (() => {{
        const src = (licenseProfileBundle && licenseProfileBundle.profiles) ? licenseProfileBundle.profiles : {{}};
        const out = {{}};
        Object.keys(src).forEach((rawKey) => {{
          const key = normalizeLicenseKey(rawKey);
          if (!key) return;
          out[key] = Object.assign({{}}, src[rawKey], {{ token: key }});
        }});
        return out;
      }})();
      const quickLicenseProfiles = Array.isArray(licenseProfileBundle && licenseProfileBundle.quick_tokens)
        ? licenseProfileBundle.quick_tokens
        : [];
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
      const formatInputNumber = (value, digits = 1) => {{
        const numValue = Number(value);
        if (!Number.isFinite(numValue)) return "";
        const fixed = numValue.toFixed(digits);
        return fixed.replace(/\\.0+$/, "").replace(/(\\.\\d*[1-9])0+$/, "$1");
      }};
      const getScaleSearchMode = () => compact(($("in-scale-search-mode") || {{}}).value) || "specialty";
      const setScaleSearchMode = (mode) => {{
        const normalized = mode === "sales" ? "sales" : "specialty";
        const node = $("in-scale-search-mode");
        if (node) node.value = normalized;
        document.querySelectorAll("#seoulmna-yangdo-calculator .scale-mode-btn").forEach((btn) => {{
          if (!btn) return;
          btn.classList.toggle("active", compact(btn.getAttribute("data-scale-mode")) === normalized);
        }});
      }};
      const yangdoWizardStepsMeta = [
        {{
          id: "yangdoWizardStep1",
          shortLabel: "STEP 1",
          title: "면허/업종 입력",
          meta: "면허 · 자동 제안",
          note: "가장 쉬운 업종 정보부터 입력합니다.",
          optional: false,
        }},
        {{
          id: "yangdoWizardStep2",
          shortLabel: "STEP 2",
          title: "검색 기준 입력",
          meta: "시평 또는 실적",
          note: "시평과 실적 중 한 축만 선택해 유사 매물을 좁힙니다.",
          optional: false,
        }},
        {{
          id: "yangdoWizardStep3",
          shortLabel: "STEP 3",
          title: "핵심 가격 영향 입력",
          meta: "자본금 · 공제잔액 · 기준 충족",
          note: "가격에 직접 영향을 주는 필수 정보만 먼저 넣습니다.",
          optional: false,
        }},
        {{
          id: "yangdoWizardStep4",
          shortLabel: "STEP 4",
          title: "구조·정산 정보",
          meta: "양도 구조 · 정산 방식 · 면허년도",
          note: "일부 업종만 필요한 구조 정보를 마지막 단계에서 반영합니다.",
          optional: true,
        }},
        {{
          id: "yangdoWizardStep5",
          shortLabel: "STEP 5",
          title: "재무·회사 선택 정보",
          meta: "이익잉여금 · 재무상태 · 회사 리스크",
          note: "선택 입력입니다. 비워도 기본 계산은 가능합니다.",
          optional: true,
        }},
      ];
      let yangdoWizardStepIndex = 0;
      const createYangdoWizardNav = (stepIndex, noteText) => {{
        const wrap = document.createElement("div");
        wrap.className = "wizard-nav";
        wrap.innerHTML = ''
          + `<p class="wizard-nav-copy">${{escapeHtml(noteText || "")}}</p>`
          + '<div class="wizard-nav-actions">'
          + `<button type="button" class="wizard-nav-btn" data-yangdo-wizard-prev="${{stepIndex}}">이전</button>`
          + `<button type="button" class="wizard-nav-btn is-primary" data-yangdo-wizard-next="${{stepIndex}}">다음</button>`
          + '</div>';
        return wrap;
      }};
      const createYangdoWizardChip = (step, stepIndex) => {{
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = `wizard-step-chip${{step.optional ? " is-optional" : ""}}`;
        chip.id = `yangdoWizardChip${{stepIndex + 1}}`;
        chip.setAttribute("data-yangdo-wizard-track", String(stepIndex));
        chip.innerHTML = ''
          + `<span class="wizard-step-chip-label">${{escapeHtml(step.shortLabel || "")}}${{step.optional ? " · 선택" : ""}}</span>`
          + `<span class="wizard-step-chip-title">${{escapeHtml(step.title || "")}}</span>`
          + `<span class="wizard-step-chip-meta">${{escapeHtml(step.meta || "")}}</span>`;
        return chip;
      }};
      const getFieldWrap = (id) => {{
        const node = $(id);
        return node ? (node.closest(".field") || node) : null;
      }};
      const applyYangdoWizardLayout = () => {{
        const panel = document.querySelector("#seoulmna-yangdo-calculator .smna-grid > .panel");
        if (!panel || $("yangdo-input-wizard")) return;
        const panelBody = panel.querySelector(".panel-body");
        if (!panelBody) return;
        const inputGuide = panelBody.querySelector(".input-guide");
        const avgGuide = $("avg-guide");
        const primaryRow = panelBody.querySelector(".input-row");
        const estimateActions = panelBody.querySelector(".btn-row");
        const tailNote = estimateActions ? estimateActions.nextElementSibling : null;
        const licenseField = getFieldWrap("in-license");
        const smartProfileField = $("smart-profile-card") ? $("smart-profile-card").closest(".field") : null;
        const scaleField = $("scale-mode-switch") ? $("scale-mode-switch").closest(".field") : null;
        const specialtyField = getFieldWrap("in-specialty");
        const salesField = $("sales-search-panel");
        const balanceField = getFieldWrap("in-balance");
        const checksField = $("ok-capital") ? $("ok-capital").closest(".field") : null;
        const capitalField = getFieldWrap("in-capital");
        const reorgField = getFieldWrap("in-reorg-mode");
        const balanceUsageField = getFieldWrap("in-balance-usage-mode");
        const licenseYearField = getFieldWrap("in-license-year");
        const surplusField = getFieldWrap("in-surplus");
        const debtField = getFieldWrap("in-debt-level");
        const liqField = getFieldWrap("in-liq-level");
        const companyTypeField = getFieldWrap("in-company-type");
        const creditField = getFieldWrap("in-credit-level");
        const adminField = getFieldWrap("in-admin-history");
        const advancedDetails = $("advanced-inputs");
        const wizardShell = document.createElement("div");
        wizardShell.id = "yangdo-input-wizard";
        wizardShell.className = "wizard-shell";
        const wizardRail = document.createElement("div");
        wizardRail.id = "yangdoWizardRail";
        wizardRail.className = "wizard-rail";
        wizardRail.innerHTML = ''
          + '<div class="wizard-rail-head">'
          + '<div>'
          + '<p class="wizard-rail-kicker">Sequential Deal Intake</p>'
          + '<h4 id="yangdoWizardStepTitle" class="wizard-rail-title">STEP 1 · 면허/업종 입력</h4>'
          + '<p id="yangdoWizardStepNote" class="wizard-rail-note">쉬운 정보부터 넣고, 선택 정보는 마지막 단계에서 결과에 반영합니다.</p>'
          + '</div>'
          + '<div class="info-box" style="margin:0; padding:12px 13px;">'
          + '<div class="k">입력 원칙</div>'
          + '<div class="v">한 단계에 2~3개 핵심 정보만 입력하고, 마지막 단계는 <strong>선택</strong> 정보로 분리했습니다.</div>'
          + '</div>'
          + '</div>';
        const wizardProgress = document.createElement("div");
        wizardProgress.id = "yangdoWizardProgress";
        wizardProgress.className = "wizard-progress";
        wizardProgress.innerHTML = ''
          + '<div class="wizard-progress-copy">'
          + '<div id="yangdoWizardProgressLabel" class="wizard-progress-label">현재 1/5 단계</div>'
          + '<div id="yangdoWizardProgressBar" class="wizard-progress-track" role="progressbar" aria-valuemin="1" aria-valuemax="5" aria-valuenow="1" aria-describedby="yangdoWizardProgressMeta">'
          + '<span id="yangdoWizardProgressFill" class="wizard-progress-fill"></span>'
          + '</div>'
          + '<div id="yangdoWizardProgressMeta" class="wizard-progress-meta">필수 0/3 완료 · 업종부터 입력하면 자동 제안이 시작됩니다.</div>'
          + '<button type="button" id="yangdoWizardNextAction" class="wizard-progress-action" data-yangdo-next-action><span class="wizard-progress-action-label">지금 할 일</span><span id="yangdoWizardNextActionText" class="wizard-progress-action-text">면허/업종부터 선택하세요.</span></button>'
          + '<div id="yangdoWizardActionReason" class="wizard-progress-support" role="button" tabindex="0" data-yangdo-action-reason data-actionable="1">업종이 정해져야 통상 자본금과 공제조합 기준을 자동 제안할 수 있습니다.</div>'
          + '<div id="yangdoValuePreview" class="value-preview" aria-live="polite" aria-atomic="true">'
          + '<div class="value-preview-label">현재 입력 기준 예상 양도가 범위</div>'
          + '<div class="value-preview-range">'
          + '<div class="value-preview-bar"><div id="yangdoValuePreviewFill" class="value-preview-fill" style="left:0%;width:100%"></div></div>'
          + '<span id="yangdoValuePreviewText" class="value-preview-text">—</span>'
          + '</div>'
          + '<div id="yangdoValuePreviewCount" class="value-preview-count"></div>'
          + '</div>'
          + '</div>'
          + '<strong id="yangdoWizardProgressCount" class="wizard-progress-count">1/5</strong>';
        wizardRail.appendChild(wizardProgress);
        const wizardMobileSticky = document.createElement("button");
        wizardMobileSticky.type = "button";
        wizardMobileSticky.id = "yangdoWizardMobileSticky";
        wizardMobileSticky.className = "wizard-mobile-sticky";
        wizardMobileSticky.setAttribute("data-yangdo-next-action", "mobile");
        wizardMobileSticky.innerHTML = ''
          + '<div class="wizard-mobile-sticky-copy">'
          + '<div id="yangdoWizardMobileStickyLabel" class="wizard-mobile-sticky-label">현재 1/5 단계</div>'
          + '<div id="yangdoWizardMobileStickyAction" class="wizard-mobile-sticky-action">면허/업종부터 선택하세요.</div>'
          + '<div id="yangdoWizardMobileStickyCompact" class="wizard-mobile-sticky-compact">업종 선택 후 자동 기준 시작</div>'
          + '<div id="yangdoWizardMobileStickyMeta" class="wizard-mobile-sticky-meta">필수 0/3 완료 · 업종부터 입력하면 자동 제안이 시작됩니다.</div>'
          + '<div id="yangdoWizardMobileStickyReason" class="wizard-mobile-sticky-reason">업종이 정해져야 통상 자본금과 공제조합 기준을 자동 제안할 수 있습니다.</div>'
          + '</div>'
          + '<span id="yangdoWizardMobileStickyCount" class="wizard-mobile-sticky-count">1/5</span>';
        wizardRail.appendChild(wizardMobileSticky);
        const wizardSummary = document.createElement("div");
        wizardSummary.id = "yangdoWizardSummary";
        wizardSummary.className = "wizard-summary";
        wizardSummary.innerHTML = '<span class="wizard-summary-chip is-empty">업종부터 입력하면 현재 계산 축과 필수 진행 상태를 여기에 요약합니다.</span>';
        wizardRail.appendChild(wizardSummary);
        const wizardBlocker = document.createElement("div");
        wizardBlocker.id = "yangdoWizardBlocker";
        wizardBlocker.className = "wizard-blocker";
        wizardBlocker.textContent = "다음 단계로 가려면 먼저 업종을 입력해 주세요.";
        wizardRail.appendChild(wizardBlocker);
        const wizardSteps = document.createElement("div");
        wizardSteps.id = "yangdoWizardSteps";
        wizardSteps.className = "wizard-steps";
        yangdoWizardStepsMeta.forEach((step, stepIndex) => {{
          wizardSteps.appendChild(createYangdoWizardChip(step, stepIndex));
        }});
        wizardRail.appendChild(wizardSteps);
        wizardShell.appendChild(wizardRail);

        const buildStep = (stepId, titleText, assistText, optional = false, kickerText = "") => {{
          const step = document.createElement("section");
          step.id = stepId;
          step.className = `wizard-step-card${{optional ? " optional-step" : ""}}`;
          step.setAttribute("data-step-index", String(yangdoWizardStepsMeta.findIndex((item) => item.id === stepId)));
          step.innerHTML = `<p class="section-kicker">${{escapeHtml(kickerText || "")}}</p><h4 class="section-title">${{escapeHtml(titleText || "")}}${{optional ? ' <span class="step-choice-tag">선택</span>' : ''}}</h4><p class="field-sub" style="margin-top:6px">${{escapeHtml(assistText || "")}}</p>`;
          return step;
        }};

        const step1 = buildStep("yangdoWizardStep1", "면허/업종 입력", "업종을 고르면 통상 매물 기준값이 자동 제안됩니다.", false, "STEP 1");
        if (licenseField) step1.appendChild(licenseField);
        if (smartProfileField) step1.appendChild(smartProfileField);
        step1.appendChild(createYangdoWizardNav(0, "대표가 가장 먼저 아는 업종 정보부터 입력합니다."));

        const step2 = buildStep("yangdoWizardStep2", "검색 기준 입력", "시평 또는 실적 중 한 축만 선택해 핵심 규모를 빠르게 잡습니다.", false, "STEP 2");
        if (scaleField) step2.appendChild(scaleField);
        if (specialtyField) step2.appendChild(specialtyField);
        if (salesField) step2.appendChild(salesField);
        step2.appendChild(createYangdoWizardNav(1, "검색 기준이 정해지면 필수 가격 영향 정보만 입력하면 됩니다."));

        const step3 = buildStep("yangdoWizardStep3", "핵심 가격 영향 입력", "가격에 직접 영향을 주는 필수 정보만 먼저 받습니다.", false, "STEP 3");
        const criticalGrid = document.createElement("div");
        criticalGrid.className = "input-row";
        if (capitalField) criticalGrid.appendChild(capitalField);
        if (balanceField) criticalGrid.appendChild(balanceField);
        if (checksField) criticalGrid.appendChild(checksField);
        step3.appendChild(criticalGrid);
        const criticalHint = document.createElement("div");
        criticalHint.id = "yangdoCriticalHint";
        criticalHint.className = "wizard-priority-hint";
        criticalHint.textContent = "가격을 안정적으로 보려면 자본금, 공제조합 잔액, 필수 기준 충족 여부부터 먼저 확인해 주세요.";
        step3.appendChild(criticalHint);
        step3.appendChild(createYangdoWizardNav(2, "필수 입력이 끝나면 구조·정산 같은 선택 정보를 마지막에 반영합니다."));

        const step4 = buildStep("yangdoWizardStep4", "구조·정산 정보", "해당 업종에서만 필요한 구조 정보를 마지막 단계에 따로 넣습니다.", true, "STEP 4 · 선택");
        const optionalGrid1 = document.createElement("div");
        optionalGrid1.className = "input-row";
        if (reorgField) optionalGrid1.appendChild(reorgField);
        if (balanceUsageField) optionalGrid1.appendChild(balanceUsageField);
        if (licenseYearField) optionalGrid1.appendChild(licenseYearField);
        step4.appendChild(optionalGrid1);
        const structureHint = document.createElement("div");
        structureHint.id = "yangdoStructureHint";
        structureHint.className = "wizard-priority-hint";
        structureHint.textContent = "양도 구조, 공제조합 정산 방식, 면허년도 순서로 보면 마지막 정산 가정을 빠르게 정리할 수 있습니다.";
        step4.appendChild(structureHint);
        step4.appendChild(createYangdoWizardNav(3, "전기·정보통신·소방 등 일부 업종은 양도 구조 선택이 사실상 필수일 수 있습니다."));

        const step5 = buildStep("yangdoWizardStep5", "재무·회사 선택 정보", "이익잉여금, 재무 상태, 회사 리스크는 선택 입력으로 결과를 미세 보정합니다.", true, "STEP 5 · 선택");
        const optionalGrid2 = document.createElement("div");
        optionalGrid2.className = "input-row";
        if (surplusField) optionalGrid2.appendChild(surplusField);
        const financeGroup = document.createElement("div");
        financeGroup.className = "field wide";
        financeGroup.id = "yangdo-optional-finance-group";
        financeGroup.innerHTML = '<label>재무 상태 <span class="step-choice-tag">선택</span></label><div class="input-row" style="margin-bottom:0"></div><div class="field-sub">평균 대비 재무 상태만 선택하면 됩니다.</div>';
        const financeGrid = financeGroup.querySelector(".input-row");
        if (debtField && financeGrid) financeGrid.appendChild(debtField);
        if (liqField && financeGrid) financeGrid.appendChild(liqField);
        optionalGrid2.appendChild(financeGroup);
        const companyRiskGroup = document.createElement("div");
        companyRiskGroup.className = "field wide";
        companyRiskGroup.id = "yangdo-optional-company-group";
        companyRiskGroup.innerHTML = '<label>회사 리스크 <span class="step-choice-tag">선택</span></label><div class="input-row" style="margin-bottom:0"></div><div class="field-sub">회사형태, 외부신용, 행정처분 이력을 선택하면 보정에 반영합니다.</div>';
        const companyGrid = companyRiskGroup.querySelector(".input-row");
        if (companyTypeField && companyGrid) companyGrid.appendChild(companyTypeField);
        if (creditField && companyGrid) companyGrid.appendChild(creditField);
        if (adminField && companyGrid) companyGrid.appendChild(adminField);
        optionalGrid2.appendChild(companyRiskGroup);
        step5.appendChild(optionalGrid2);
        const companyHint = document.createElement("div");
        companyHint.id = "yangdoCompanyHint";
        companyHint.className = "wizard-priority-hint";
        companyHint.textContent = "재무 상태와 회사 리스크는 마지막 미세 보정용입니다. 필요한 항목만 선택해도 됩니다.";
        step5.appendChild(companyHint);
      step5.appendChild(createYangdoWizardNav(4, "선택 정보를 검토했으면 바로 계산 결과와 다음 순서를 확인합니다."));

        wizardShell.appendChild(step1);
        wizardShell.appendChild(step2);
        wizardShell.appendChild(step3);
        wizardShell.appendChild(step4);
        wizardShell.appendChild(step5);

        if (inputGuide) panelBody.appendChild(inputGuide);
        if (avgGuide) panelBody.appendChild(avgGuide);
        panelBody.appendChild(wizardShell);
        if (estimateActions) panelBody.appendChild(estimateActions);
        if (tailNote) panelBody.appendChild(tailNote);
        if (advancedDetails) advancedDetails.remove();
        if (primaryRow) primaryRow.remove();
      }};
      const resolveLicenseProfile = (licenseRaw) => {{
        const consider = (rawKey, currentBest) => {{
          const key = normalizeLicenseKey(rawKey);
          if (!key || !licenseProfiles[key]) return currentBest;
          const profile = licenseProfiles[key];
          if (!currentBest) return profile;
          return Number(profile.sample_count || 0) > Number(currentBest.sample_count || 0) ? profile : currentBest;
        }};
        let best = null;
        const tokens = Array.from(licenseTokenSet(licenseRaw));
        tokens.forEach((token) => {{
          best = consider(token, best);
        }});
        const rawKey = normalizeLicenseKey(licenseRaw);
        if (!best && rawKey) best = consider(rawKey, best);
        if (!best && rawKey) {{
          const fuzzy = findClosestKnownToken(rawKey);
          if (fuzzy) best = consider(fuzzy, best);
        }}
        return best;
      }};
      const renderLicenseSuggestions = () => {{
        const list = $("license-suggestions");
        if (!list) return;
        const items = [];
        quickLicenseProfiles.forEach((item) => {{
          const label = compact(item && (item.display_name || item.token));
          if (!label) return;
          items.push(label);
        }});
        knownTokens.slice(0, 60).forEach((token) => {{
          const label = compact((licenseProfiles[token] && licenseProfiles[token].display_name) || canonicalByKey[token] || token);
          if (!label) return;
          items.push(label);
        }});
        const seen = new Set();
        list.innerHTML = items.filter((label) => {{
          const key = normalizeLicenseKey(label);
          if (!key || seen.has(key)) return false;
          seen.add(key);
          return true;
        }}).slice(0, 80).map((label) => `<option value="${{escapeHtml(label)}}"></option>`).join("");
      }};
      const renderLicenseQuickChips = () => {{
        const wrap = $("license-quick-chips");
        if (!wrap) return;
        const items = quickLicenseProfiles.slice(0, 8);
        if (!items.length) {{
          wrap.innerHTML = "";
          return;
        }}
        wrap.innerHTML = items.map((item) => {{
          const label = compact(item && (item.display_name || item.token));
          const count = Number(item && item.sample_count) || 0;
          return `<button type="button" class="license-chip" data-license-chip="${{escapeHtml(label)}}">${{escapeHtml(label)}}${{count > 0 ? ` · ${{count}}건` : ""}}</button>`;
        }}).join("");
        wrap.querySelectorAll("[data-license-chip]").forEach((btn) => {{
          btn.addEventListener("click", () => {{
            const node = $("in-license");
            if (!node) return;
            node.value = compact(btn.getAttribute("data-license-chip"));
            delete node.dataset.manual;
            syncLicenseAutoProfile(true);
            syncReorgModeRequirement();
            syncConsultSummary();
            persistDraft();
          }});
        }});
      }};
      const setFieldAutoValue = (id, value, force = false) => {{
        const node = $(id);
        const numValue = Number(value);
        if (!node || !Number.isFinite(numValue)) return false;
        if (!force && compact(node.value) && node.dataset.autofill !== "1") return false;
        const digits = id === "in-balance" ? 2 : 1;
        node.dataset.applyingAuto = "1";
        node.value = formatInputNumber(numValue, digits);
        node.dataset.autofill = "1";
        delete node.dataset.manual;
        delete node.dataset.applyingAuto;
        return true;
      }};
      const syncLicenseAutoProfile = (force = false) => {{
        const profile = resolveLicenseProfile(($("in-license") || {{}}).value);
        const specialBalance = isSeparateBalanceGroupToken(($("in-license") || {{}}).value);
        const capitalNode = $("smart-capital");
        const surplusNode = $("smart-surplus");
        const balanceNode = $("smart-balance");
        const balanceLabelNode = $("smart-balance-label");
        const balanceSubNode = $("smart-balance-sub");
        const scaleNode = $("smart-scale");
        const noteNode = $("smart-profile-note");
        const tokenNode = $("smart-profile-token");
        const balanceHint = $("balance-auto-note");
        if (!profile) {{
          if (capitalNode) capitalNode.textContent = "-";
          if (surplusNode) surplusNode.textContent = "-";
          if (balanceNode) balanceNode.textContent = "-";
          if (balanceLabelNode) balanceLabelNode.textContent = specialBalance ? "별도 공제조합 잔액(참고)" : "미입력 시 공제조합 잔액";
          if (balanceSubNode) balanceSubNode.textContent = specialBalance ? "가격 영향 0 · 필요하면 참고용 입력" : "최대 융자 60% 이후 남는 통상 최저 잔액 기준";
          if (scaleNode) scaleNode.textContent = "-";
          if (tokenNode) tokenNode.textContent = "업종 입력 후 표시";
          if (noteNode) noteNode.textContent = specialBalance
            ? "전기·정보통신·소방은 공제조합 잔액을 양도가와 별도로 봅니다. 가격 계산에는 반영하지 않습니다."
            : "업종을 입력하면 거래되는 통상 매물 기준값을 바로 채웁니다.";
          if (balanceHint) balanceHint.textContent = specialBalance
            ? "전기·정보통신·소방은 공제조합 잔액이 양도가와 별도이며 가격 계산에는 반영하지 않습니다. 필요하면 참고용으로만 입력하세요."
            : "미입력 시 업종 기준 통상 최저 잔액을 자동 반영합니다.";
          syncYangdoWizard();
          return;
        }}
        const scaleMode = getScaleSearchMode();
        const scaleValue = scaleMode === "sales"
          ? (Number.isFinite(num(profile.typical_sales3_eok)) ? `3년 ${{fmtEok(num(profile.typical_sales3_eok))}}` : (Number.isFinite(num(profile.typical_sales5_eok)) ? `5년 ${{fmtEok(num(profile.typical_sales5_eok))}}` : "-"))
          : (Number.isFinite(num(profile.typical_specialty_eok)) ? fmtEok(num(profile.typical_specialty_eok)) : "-");
        if (capitalNode) capitalNode.textContent = fmtEok(num(profile.prefill_capital_eok));
        if (surplusNode) surplusNode.textContent = fmtEok(num(profile.prefill_surplus_eok));
        if (balanceNode) balanceNode.textContent = fmtEok(num(profile.default_balance_eok));
        if (balanceLabelNode) balanceLabelNode.textContent = specialBalance ? "대표 참고 공제조합 잔액" : "미입력 시 공제조합 잔액";
        if (balanceSubNode) balanceSubNode.textContent = specialBalance ? "별도 정산 참고값 · 가격 영향 0" : "최대 융자 60% 이후 남는 통상 최저 잔액 기준";
        if (scaleNode) scaleNode.textContent = scaleValue;
        if (tokenNode) tokenNode.textContent = `${{compact(profile.display_name || profile.token)}} · 표본 ${{Number(profile.sample_count || 0).toLocaleString("ko-KR")}}건`;
        if (noteNode) {{
          noteNode.textContent = specialBalance
            ? `${{compact(profile.display_name || profile.token)}} 업종은 공제조합 잔액이 양도가와 별도이며 가격 계산에는 반영하지 않습니다. 필요하면 참고용으로만 입력하세요.`
            : `${{compact(profile.display_name || profile.token)}} 통상 매물 기준입니다. 공제조합 잔액을 비우면 ${{fmtEok(num(profile.default_balance_eok))}}를 자동 적용합니다.`;
        }}
        if (balanceHint) {{
          const hasManualBalance = Number.isFinite(num(($("in-balance") || {{}}).value));
          balanceHint.textContent = specialBalance
            ? `${{compact(profile.display_name || profile.token)}} 업종은 공제조합 잔액이 양도가와 별도입니다. 입력해도 가격에는 반영하지 않고 참고용으로만 표시합니다.`
            : (
              hasManualBalance
                ? "직접 입력한 공제조합 잔액을 가격 계산에 반영합니다."
                : `${{compact(profile.display_name || profile.token)}} 기준 통상 최저 잔액 ${{fmtEok(num(profile.default_balance_eok))}}를 자동 적용합니다.`
            );
        }}
        setFieldAutoValue("in-capital", profile.prefill_capital_eok, force);
        setFieldAutoValue("in-surplus", profile.prefill_surplus_eok, force);
        if (specialBalance) {{
          const balanceInput = $("in-balance");
          if (balanceInput && balanceInput.dataset.autofill === "1" && !compact(balanceInput.dataset.manual)) {{
            balanceInput.value = "";
            delete balanceInput.dataset.autofill;
          }}
        }} else if (!Number.isFinite(num(($("in-balance") || {{}}).value))) {{
          setFieldAutoValue("in-balance", profile.default_balance_eok, force);
        }}
        syncYangdoWizard();
      }};
      const syncScaleSearchModeUi = () => {{
        const mode = getScaleSearchMode();
        const specialtyPanel = $("specialty-search-panel");
        const salesPanel = $("sales-search-panel");
        const specialtyInput = $("in-specialty");
        if (specialtyPanel) specialtyPanel.classList.toggle("is-hidden", mode !== "specialty");
        if (salesPanel) salesPanel.classList.toggle("is-hidden", mode !== "sales");
        if (specialtyInput) specialtyInput.disabled = mode !== "specialty";
        syncSalesInputModeUi();
        syncLicenseAutoProfile(false);
        syncYangdoWizard();
      }};
      const isSeparateBalanceGroupToken = (raw) => !!specialBalanceSectorName(raw);
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
      const normalizeReorgMode = (raw) => {{
        const txt = compact(raw).toLowerCase().replace(/\\s+/g, "");
        if (!txt) return "";
        if (txt === "분할포괄" || txt === "분할/포괄") return "분할/합병";
        const hasSplit = (txt.indexOf("분할") >= 0) || (txt.indexOf("split") >= 0);
        const hasMerge = (txt.indexOf("합병") >= 0) || (txt.indexOf("merge") >= 0);
        const hasSplitGroup = hasSplit || hasMerge;
        const hasComprehensive = (txt.indexOf("포괄") >= 0) || (txt.indexOf("흡수") >= 0) || (txt.indexOf("comprehensive") >= 0);
        if (hasSplitGroup && hasComprehensive) return "";
        if (hasSplitGroup) return "분할/합병";
        if (hasComprehensive) return "포괄";
        return compact(raw);
      }};
      const normalizeBalanceUsageMode = (raw) => {{
        const txt = compact(raw).toLowerCase().replace(/\\s+/g, "");
        if (!txt) return "";
        if (["auto", "기본", "기본값", "default"].indexOf(txt) >= 0) return "auto";
        if (txt.indexOf("융자") >= 0 || txt.indexOf("대출") >= 0 || txt.indexOf("loan") >= 0 || txt.indexOf("withdraw") >= 0) return "loan_withdrawal";
        if (txt.indexOf("잔액승계") >= 0 || txt.indexOf("잔액인수") >= 0 || txt.indexOf("credit") >= 0 || txt.indexOf("offset") >= 0 || txt.indexOf("1:1") >= 0 || txt.indexOf("차감") >= 0) return "credit_transfer";
        if (["none", "없음", "미반영", "별도정산없음"].indexOf(txt) >= 0) return "none";
        return "";
      }};
      const SPECIAL_BALANCE_LOAN_UTILIZATION = 0.60;
      const SPECIAL_SETTLEMENT_SCENARIO_INPUT_MODES = ["auto", "credit_transfer", "none"];
      const SPECIAL_BALANCE_AUTO_POLICIES = {{
        "전기": {{
          sector: "전기",
          autoMode: "loan_withdrawal",
          loanUtilization: SPECIAL_BALANCE_LOAN_UTILIZATION,
          minAutoBalanceShare: 0.10,
          minAutoBalanceEok: 0.05,
          summary: "전기: 총가·공제 정산 분리",
          reorgOverrides: {{
            "분할/합병": {{
              minAutoBalanceShare: 0.105,
              minAutoBalanceEok: 0.05,
            }},
          }},
        }},
        "정보통신": {{
          sector: "정보통신",
          autoMode: "loan_withdrawal",
          loanUtilization: SPECIAL_BALANCE_LOAN_UTILIZATION,
          minAutoBalanceShare: 0.0625,
          minAutoBalanceEok: 0.025,
          summary: "정보통신: 총가·공제 정산 분리",
          reorgOverrides: {{
            "분할/합병": {{
              minAutoBalanceShare: 0.065,
              minAutoBalanceEok: 0.025,
            }},
          }},
        }},
        "소방": {{
          sector: "소방",
          autoMode: "loan_withdrawal",
          loanUtilization: SPECIAL_BALANCE_LOAN_UTILIZATION,
          minAutoBalanceShare: 0.17,
          minAutoBalanceEok: 0.09,
          summary: "소방: 총가·공제 정산 분리",
          reorgOverrides: {{
            "분할/합병": {{
              minAutoBalanceShare: 0.1758,
              minAutoBalanceEok: 0.09,
            }},
          }},
        }},
      }};
      const specialBalanceSectorName = (raw) => {{
        const key = normalizeLicenseKey(raw);
        if (!key) return "";
        if (key.indexOf("정보통신") >= 0 || key.indexOf("통신") >= 0) return "정보통신";
        if (key.indexOf("소방") >= 0) return "소방";
        if (key.indexOf("전기") >= 0) return "전기";
        return "";
      }};
      const getSpecialBalanceAutoPolicy = (licenseRaw, reorgModeRaw) => {{
        const sector = specialBalanceSectorName(licenseRaw);
        const mode = normalizeReorgMode(reorgModeRaw);
        const base = Object.assign({{}}, SPECIAL_BALANCE_AUTO_POLICIES[sector] || {{}});
        const overrides = (base.reorgOverrides && typeof base.reorgOverrides === "object")
          ? base.reorgOverrides[mode]
          : null;
        if (overrides && typeof overrides === "object") {{
          Object.assign(base, overrides);
        }}
        const autoMode = compact(base.autoMode || "loan_withdrawal");
        const loanUtilization = Number.isFinite(Number(base.loanUtilization)) ? Number(base.loanUtilization) : SPECIAL_BALANCE_LOAN_UTILIZATION;
        let minAutoBalanceShare = Number.isFinite(Number(base.minAutoBalanceShare)) ? Number(base.minAutoBalanceShare) : 0.05;
        let minAutoBalanceEok = Number.isFinite(Number(base.minAutoBalanceEok)) ? Number(base.minAutoBalanceEok) : 0.0;
        let summary = compact(base.summary || "");
        if (sector && mode === "분할/합병") {{
          summary = `${{sector}} 분할/합병: 총가·공제 정산 분리`;
        }} else if (sector) {{
          summary = `${{sector}}: 총가·공제 정산 분리`;
        }}
        return {{
          sector,
          reorgMode: mode,
          autoMode,
          loanUtilization,
          minAutoBalanceShare,
          minAutoBalanceEok,
          summary,
        }};
      }};
      const resolveSpecialAutoMode = (policy, totalTransferValue, rawBalanceInput) => {{
        const sector = compact(policy && policy.sector);
        const baseMode = compact((policy && policy.autoMode) || "loan_withdrawal");
        const total = Math.max(0.05, num(totalTransferValue) || 0);
        const rawBalance = Math.max(0, num(rawBalanceInput) || 0);
        const share = total > 0 ? (rawBalance / total) : 0;
        const minShare = Math.max(0, num(policy && policy.minAutoBalanceShare) || 0.05);
        const minBalance = Math.max(0, num(policy && policy.minAutoBalanceEok) || 0.0);
        const reason = compact(policy && policy.summary) || "총가와 공제 정산을 분리합니다.";
        if (rawBalance <= 0) {{
          return {{
            mode: "none",
            reason: "잔액 입력 없음 -> auto=별도 정산 없음",
            balanceShare: share,
          }};
        }}
        if (rawBalance <= minBalance || share <= minShare) {{
          return {{
            mode: "none",
            reason: "잔액 비중 작음 -> auto=별도 정산 없음",
            balanceShare: share,
          }};
        }}
        return {{
          mode: baseMode,
          reason: sector ? `잔액 비중 충분 -> auto=${{settlementScenarioLabel(baseMode)}}` : reason,
          balanceShare: share,
        }};
      }};
      const resolveBalanceUsageMode = (requestedMode, sellerWithdrawsGuaranteeLoan, buyerTakesBalanceAsCredit, balanceExcluded, licenseRaw = "", reorgModeRaw = "") => {{
        const normalized = normalizeBalanceUsageMode(requestedMode);
        if (normalized && normalized !== "auto") return normalized;
        if (buyerTakesBalanceAsCredit) return "credit_transfer";
        if (sellerWithdrawsGuaranteeLoan) return "loan_withdrawal";
        if (balanceExcluded) {{
          const policy = getSpecialBalanceAutoPolicy(licenseRaw, reorgModeRaw);
          return compact(policy.autoMode || "loan_withdrawal");
        }}
        return "embedded_balance";
      }};
      const balanceUsageModeLabel = (modeRaw) => {{
        const raw = compact(modeRaw);
        const requested = normalizeBalanceUsageMode(raw);
        if (!requested && raw === "embedded_balance") return "총 거래가에 반영된 잔액 기여분 분리";
        if (!requested || requested === "auto") return "기본값(시장 관행 기준)";
        const mode = resolveBalanceUsageMode(requested, false, false, false, "", "");
        if (mode === "loan_withdrawal") return "양도자 조합 융자 인출 후 현금 차감";
        if (mode === "credit_transfer") return "양수자 공제잔액 인수 1:1 차감";
        if (mode === "embedded_balance") return "총 거래가에 반영된 잔액 기여분 분리";
        if (mode === "none") return "공제조합 잔액 별도 정산 없음";
        return "기본값(시장 관행 기준)";
      }};
      const settlementScenarioLabel = (modeRaw) => {{
        const mode = normalizeBalanceUsageMode(modeRaw);
        if (mode === "credit_transfer") return "1:1 차감";
        if (mode === "none") return "별도 정산 없음";
        if (mode === "loan_withdrawal") return "융자 인출 후 현금 차감";
        return "기본값(시장 관행 기준)";
      }};
      const scaleSearchModeLabel = (modeRaw) => {{
        return compact(modeRaw) === "sales" ? "실적 검색" : "시평 검색";
      }};
      const isSplitOptionalPricingProfile = (target, reorgModeRaw) => {{
        if (normalizeReorgMode(reorgModeRaw) !== "분할/합병") return false;
        return isSeparateBalanceGroupTarget(target);
      }};
      const requiresReorgSelectionByLicense = (licenseRaw) => {{
        const raw = compact(licenseRaw);
        if (!raw) return false;
        const tokens = licenseTokenSet(raw);
        return isSeparateBalanceGroupTarget({{
          license_raw: raw,
          raw_license_key: normalizeLicenseKey(raw),
          tokens,
        }});
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
        if (t.count < 2 || c.count < 2 || t.sum <= 0 || c.sum <= 0) return 0.2;
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
        if (wSum <= 0.2) return 0.2;
        const norm = diff / wSum;
        return clamp(1 - Math.min(1, norm / 0.9), 0, 1);
      }};
      const listingNumberBand = (raw) => {{
        const value = Number(raw || 0);
        if (!Number.isFinite(value)) return 0;
        if (value >= 7000) return 3;
        if (value >= 6000) return 2;
        if (value >= 5000) return 1;
        return 0;
      }};
      const displaySalesFitScore = (target, rec) => {{
        const sales3Score = relativeCloseness(num(target && target.sales3_eok), num(rec && rec.sales3_eok));
        const sales5Score = relativeCloseness(num(target && target.sales5_eok), num(rec && rec.sales5_eok));
        const yearlyScore = Number(yearlyShapeSimilarity(target || {{}}, rec || {{}})) || 0;
        const scores = [sales3Score, sales5Score, yearlyScore * 0.75];
        const usable = scores.filter((x) => Number.isFinite(Number(x)));
        if (!usable.length) return 0;
        return clamp(Math.max.apply(null, usable), 0, 1);
      }};
      const prioritizeDisplayNeighborRows = (rows, target) => {{
        const src = Array.isArray(rows) ? rows.slice() : [];
        const targetHasSales = Number.isFinite(num(target && target.sales3_eok)) || Number.isFinite(num(target && target.sales5_eok));
        return src.sort((left, right) => {{
          const leftSim = Number(left && left[0]) || 0;
          const rightSim = Number(right && right[0]) || 0;
          const leftRec = left && left[1] ? left[1] : {{}};
          const rightRec = right && right[1] ? right[1] : {{}};
          const leftFit = displaySalesFitScore(target, leftRec);
          const rightFit = displaySalesFitScore(target, rightRec);
          const leftHasSales = Number.isFinite(num(leftRec.sales3_eok)) || Number.isFinite(num(leftRec.sales5_eok));
          const rightHasSales = Number.isFinite(num(rightRec.sales3_eok)) || Number.isFinite(num(rightRec.sales5_eok));
          const leftComparable = (leftFit >= 0.62 || ((!targetHasSales || !leftHasSales) && leftSim >= 94)) ? 1 : 0;
          const rightComparable = (rightFit >= 0.62 || ((!targetHasSales || !rightHasSales) && rightSim >= 94)) ? 1 : 0;
          if (leftComparable !== rightComparable) return rightComparable - leftComparable;
          const leftBand = listingNumberBand(leftRec.seoul_no || leftRec.number);
          const rightBand = listingNumberBand(rightRec.seoul_no || rightRec.number);
          if (leftBand !== rightBand) return rightBand - leftBand;
          if (leftSim !== rightSim) return rightSim - leftSim;
          if (leftFit !== rightFit) return rightFit - leftFit;
          return (Number(rightRec.seoul_no || rightRec.number) || 0) - (Number(leftRec.seoul_no || leftRec.number) || 0);
        }});
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
      const plainQuantile = (values, q) => {{
        const nums = (Array.isArray(values) ? values : [])
          .map((value) => Number(value))
          .filter((value) => Number.isFinite(value));
        if (!nums.length) return null;
        nums.sort((a, b) => a - b);
        if (nums.length === 1) return nums[0];
        const qv = clamp(Number(q), 0, 1);
        const idx = qv * (nums.length - 1);
        const lo = Math.floor(idx);
        const hi = Math.min(nums.length - 1, lo + 1);
        const frac = idx - lo;
        return nums[lo] + ((nums[hi] - nums[lo]) * frac);
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

      const classifyPriceEvidence = (neighborCount, confidenceScore, hotMatchCount = 0, providedTier = "", providedLabel = "", providedSample = null) => {{
        const normalizedTier = compact(providedTier).toUpperCase();
        const labels = {{
          A: "비교 자료 충분",
          B: "비교 자료 보통",
          C: "표본 적음",
        }};
        if (normalizedTier && labels[normalizedTier]) {{
          const sample = Number.isFinite(Number(providedSample))
            ? Number(providedSample)
            : (Number.isFinite(Number(neighborCount)) ? Number(neighborCount) : 0);
          return {{
            tier: normalizedTier,
            label: compact(providedLabel) || labels[normalizedTier],
            sampleCount: Math.max(0, sample),
          }};
        }}
        const n = Number.isFinite(Number(neighborCount)) ? Number(neighborCount) : 0;
        const conf = Number.isFinite(Number(confidenceScore)) ? Number(confidenceScore) : 0;
        const hot = Number.isFinite(Number(hotMatchCount)) ? Number(hotMatchCount) : 0;
        let tier = "C";
        if (n >= 12 && conf >= 75 && hot >= 2) tier = "A";
        else if (n >= 6 && conf >= 60) tier = "B";
        return {{
          tier: tier,
          label: labels[tier],
          sampleCount: Math.max(0, n),
        }};
      }};

      const singleCorePublicationCap = (target, center) => {{
        if (!(target && target.single_core_mode)) return null;
        let singleCoreMid = num(target.single_core_median_eok);
        const singleCorePlainMid = num(target.single_core_plain_median_eok);
        const supportCount = Math.max(0, Number(target.single_core_support_count || 0));
        if (supportCount <= 2 && Number.isFinite(singleCorePlainMid) && singleCorePlainMid > 0) {{
          if (!Number.isFinite(singleCoreMid) || singleCoreMid <= 0) singleCoreMid = singleCorePlainMid;
          else singleCoreMid = Math.max(singleCoreMid, singleCorePlainMid);
        }}
        if (!Number.isFinite(singleCoreMid) || singleCoreMid <= 0) return null;
        if (!Number.isFinite(Number(center)) || Number(center) <= 0) return null;
        const centerRatio = Number(center) / Math.max(singleCoreMid, 0.1);
        const dispersionRatio = num(target.single_core_dispersion_ratio);
        const specialty = num(target.specialty);
        const sales3Eok = num(target.sales3_eok);
        const licenseText = compact(target.license_text, 80);
        const specialtyMissing = !target.split_optional_pricing && !Number.isFinite(num(target.specialty));
        const salesMissing = !Number.isFinite(num(target.sales3_eok));
        const scaleMissing = specialtyMissing || salesMissing;
        if (
          licenseText === "전기"
          && supportCount >= 8
          && Number.isFinite(sales3Eok)
          && sales3Eok <= 0.5
          && Number.isFinite(dispersionRatio)
          && dispersionRatio >= 2.0
        ) {{
          return {{
            confidenceCap: 66,
            reason: "전기 단일면허의 저실적 고분산 구간은 점추정 오차가 커 기준가는 비공개하고 범위만 공개합니다.",
          }};
        }}
        if (
          licenseText === "정보통신"
          && supportCount >= 5
          && Number.isFinite(sales3Eok)
          && sales3Eok <= 0.3
          && Number.isFinite(dispersionRatio)
          && dispersionRatio >= 1.8
        ) {{
          return {{
            confidenceCap: 66,
            reason: "정보통신 단일면허의 저실적 고분산 구간은 점추정 오차가 커 기준가는 비공개하고 범위만 공개합니다.",
          }};
        }}
        if (
          licenseText === "소방"
          && supportCount >= 4
          && Number.isFinite(sales3Eok)
          && sales3Eok <= 0.3
          && Number.isFinite(dispersionRatio)
          && dispersionRatio >= 1.5
        ) {{
          return {{
            confidenceCap: 66,
            reason: "소방 단일면허의 저실적 고분산 구간은 점추정 오차가 커 기준가는 비공개하고 범위만 공개합니다.",
          }};
        }}
        if (
          (licenseText === "전기" || licenseText === "정보통신" || licenseText === "소방")
          && supportCount <= 2
          && scaleMissing
        ) {{
          return {{
            confidenceCap: 50,
          reason: `${{licenseText}} 단일면허의 동일 업종 표본이 얇고 핵심 입력이 부족해 기준가 공개를 자세히 확인 후 안내로 낮춥니다.`,
          }};
        }}
        if (
          licenseText === "실내"
          && supportCount === 3
          && Number.isFinite(specialty)
          && specialty <= 6.5
          && centerRatio < 0.95
        ) {{
          return {{
            confidenceCap: 66,
            reason: "실내 단일면허의 저시평 thin-support 구간은 점추정보다 범위 공개가 안전합니다.",
          }};
        }}
        if (
          licenseText === "건축"
          && supportCount <= 2
          && Number.isFinite(specialty)
          && Number.isFinite(sales3Eok)
          && specialty >= 20
          && specialty <= 40
          && sales3Eok >= 10
          && sales3Eok <= 40
          && centerRatio < 0.90
        ) {{
          return {{
            confidenceCap: 66,
            reason: "건축 단일면허의 sparse mid-band 구간은 기준가 편차가 커 범위만 공개합니다.",
          }};
        }}
        if (
          licenseText === "건축"
          && supportCount <= 2
          && Number.isFinite(specialty)
          && Number.isFinite(sales3Eok)
          && specialty >= 90
          && sales3Eok >= 70
          && Number.isFinite(dispersionRatio)
          && dispersionRatio >= 4.0
        ) {{
          return {{
            confidenceCap: 66,
            reason: "건축 단일면허의 sparse high-band 구간은 동일 업종 분산이 커 범위만 공개합니다.",
          }};
        }}
        if (scaleMissing && supportCount <= 2) {{
          return {{
            confidenceCap: 50,
            reason: "동일 업종 실거래 표본이 1~2건이고 핵심 시평/실적 입력이 부족해 기준가 공개를 자세히 확인 후 안내로 낮춥니다.",
          }};
        }}
        if (supportCount <= 2 && centerRatio < 0.75) {{
          return {{
            confidenceCap: 66,
            reason: "동일 업종 실거래 표본이 얇고 기준가가 동일 업종 중앙값보다 낮아 기준가는 비공개하고 범위만 공개합니다.",
          }};
        }}
        if (centerRatio < 0.50) {{
          return {{
            confidenceCap: 66,
            reason: "동일 업종 실거래 중앙값 대비 기준가가 과도하게 낮아 점추정보다 범위 공개가 안전합니다.",
          }};
        }}
        if (centerRatio > 2.0) {{
          return {{
            confidenceCap: 66,
            reason: "동일 업종 실거래 중앙값 대비 기준가가 과도하게 높아 점추정보다 범위 공개가 안전합니다.",
          }};
        }}
        if (scaleMissing && Number.isFinite(dispersionRatio) && dispersionRatio > 1.80) {{
          return {{
            confidenceCap: 66,
            reason: "동일 업종 실거래 분산이 크고 핵심 시평/실적 입력이 부족해 기준가는 비공개하고 범위만 공개합니다.",
          }};
        }}
        return null;
      }};
      const trimmedMedian = (values, lowerQ = 0.20, upperQ = 0.80) => {{
        const nums = (Array.isArray(values) ? values : []).map((value) => Number(value)).filter((value) => Number.isFinite(value)).sort((a, b) => a - b);
        if (!nums.length) return null;
        const lo = plainQuantile(nums, lowerQ);
        const hi = plainQuantile(nums, upperQ);
        const trimmed = nums.filter((value) => value >= lo && value <= hi);
        return plainQuantile(trimmed.length ? trimmed : nums, 0.50);
      }};

      const sectorSignalValue = (source) => {{
        const sales3 = num(source && source.sales3_eok);
        const specialty = num(source && source.specialty);
        if (Number.isFinite(sales3) && Number.isFinite(specialty)) return (sales3 * 0.65) + (specialty * 0.35);
        if (Number.isFinite(sales3)) return sales3;
        if (Number.isFinite(specialty)) return specialty;
        return null;
      }};

      const applyFireSingleLicenseGuardedPrior = (target, center, low, high, riskNotes) => {{
        const targetTokens = target && target.tokens instanceof Set ? Array.from(target.tokens) : [];
        if (targetTokens.length !== 1) return {{ applied: false, center, low, high, mode: "" }};
        if (compact(target && target.license_text) !== "소방") return {{ applied: false, center, low, high, mode: "" }};
        const targetSignal = sectorSignalValue(target);
        if (!Number.isFinite(targetSignal) || targetSignal <= 0) return {{ applied: false, center, low, high, mode: "" }};
        const sectorRows = dataset.filter((row) => {{
          const rowTokens = Array.isArray(row && row.tokens) ? row.tokens.map((token) => compact(token)).filter((token) => !!token) : [];
          return rowTokens.length === 1 && rowTokens[0] === "소방" && Number.isFinite(num(row && row.price_eok)) && num(row && row.price_eok) > 0;
        }});
        const prices = sectorRows.map((row) => num(row && row.price_eok)).filter((value) => Number.isFinite(value) && value > 0);
        if (prices.length < 8) return {{ applied: false, center, low, high, mode: "" }};
        const ratios = sectorRows.map((row) => {{
          const price = num(row && row.price_eok);
          const signal = sectorSignalValue(row);
          if (!Number.isFinite(price) || price <= 0 || !Number.isFinite(signal) || signal <= 0) return null;
          return price / signal;
        }}).filter((value) => Number.isFinite(value) && value > 0);
        if (ratios.length < 6) return {{ applied: false, center, low, high, mode: "" }};
        const priorEstimate = targetSignal * trimmedMedian(ratios, 0.20, 0.80);
        const q25 = plainQuantile(prices, 0.25);
        const q60 = plainQuantile(prices, 0.60);
        if (!Number.isFinite(priorEstimate) || !Number.isFinite(q25) || !Number.isFinite(q60)) return {{ applied: false, center, low, high, mode: "" }};
        const candidate = Number(center) + (0.55 * Math.max(0, priorEstimate - Number(center)));
        const floorValue = Math.max(Number(center), q25 * 0.90);
        const capValue = Math.min(q60 * 1.02, Number(center) * 1.60);
        const adjustedCenter = Math.max(floorValue, Math.min(candidate, capValue));
        if (!(adjustedCenter > Number(center) + 0.0005)) return {{ applied: false, center, low, high, mode: "" }};
        const lowGap = Math.max(0, Number(center) - Number(low));
        const highGap = Math.max(0, Number(high) - Number(center));
        const adjustedLow = Math.max(0.05, adjustedCenter - lowGap);
        const adjustedHigh = Math.max(adjustedLow, adjustedCenter + highGap);
        if (Array.isArray(riskNotes) && riskNotes.indexOf("소방 단일면허는 same-sector bounded prior를 제한 반영해 none-mode 과소평가를 줄였습니다.") < 0) {{
          riskNotes.push("소방 단일면허는 same-sector bounded prior를 제한 반영해 none-mode 과소평가를 줄였습니다.");
        }}
        return {{
          applied: true,
          mode: "fire_single_license_guarded_prior",
          center: adjustedCenter,
          low: adjustedLow,
          high: adjustedHigh,
        }};
      }};

      const renderYoyCompare = (out) => {{
        const node = $("out-yoy-compare");
        if (!node) return;
        node.classList.remove("up", "down");
        const pubMode = compact(out && (out.publicationMode || out.publication_mode || out.publicMode || ""));
        const publicCenter = num(out && (out.publicCenter ?? out.public_center_eok ?? out.center));
        if (pubMode && pubMode !== "full") {{
          node.textContent = "전년 대비 비교는 기준가 공개 시 표시됩니다.";
          return;
        }}
        const yoy = out && out.yoy ? out.yoy : null;
        const prevCenter = yoy ? Number(yoy.previous_center) : NaN;
        const changePct = yoy ? Number(yoy.change_pct) : NaN;
        const prevYear = yoy ? Number(yoy.previous_year || 0) : 0;
        const currYear = yoy ? Number(yoy.current_year || 0) : 0;
        const basis = yoy ? compact(yoy.basis || "") : "";
        if (!Number.isFinite(prevCenter) || prevCenter <= 0 || !Number.isFinite(changePct) || !Number.isFinite(publicCenter)) {{
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
        node.innerHTML = `${{escapeHtml(leftYear)}} 동조건 추정가 <strong>${{fmtEok(prevCenter)}}</strong> 대비 ${{escapeHtml(rightYear)}} 추정가 <strong>${{fmtEok(publicCenter)}}</strong> (전년 대비 <strong>${{escapeHtml(signedPct)}} ${{escapeHtml(direction)}}</strong>)${{basisText}}`;
      }};

      const applyPublicationPolicy = (rawOut) => {{
        const out = Object.assign({{}}, rawOut || {{}});
        const riskNotes = Array.isArray(out.riskNotes) ? out.riskNotes.slice() : [];
        const target = out && out.target ? out.target : null;
        const missingCritical = target && Array.isArray(target.missing_critical) ? target.missing_critical.length : 0;
        const providedSignals = target ? Number(target.provided_signals || 0) : 0;
        const hasLicenseInput = !!(target && target.has_license_input);
        const confidenceScore = num(out.confidenceScore ?? out.confidence_score ?? out.confidence_percent);
        const effectiveClusterCount = Number.isFinite(num(out.effective_cluster_count))
          ? Number(num(out.effective_cluster_count))
          : (Number.isFinite(num(out.neighbor_count)) ? Number(num(out.neighbor_count)) : 0);
        const rawNeighborCount = Number.isFinite(num(out.raw_neighbor_count))
          ? Number(num(out.raw_neighbor_count))
          : effectiveClusterCount;
        let mode = compact(out.publicationMode || out.publication_mode || out.publicMode || "");
        let label = compact(out.publicationLabel || out.publication_label || "");
        let reason = compact(out.publicationReason || out.publication_reason || "");
        const singleCoreSupport = Math.max(0, Number(num(target && target.single_core_support_count) || 0));
        const verySparseSupport = effectiveClusterCount <= 2 || (!!(target && target.single_core_mode) && singleCoreSupport <= 2);
        if (!mode) {{
          if (!hasLicenseInput) {{
            mode = "consult_only";
            label = "상담 후 안내";
            reason = "면허 정보를 먼저 확인한 뒤 가격을 안내해 드립니다.";
          }} else if (
            verySparseSupport
            && (
              (Number.isFinite(confidenceScore) && confidenceScore < 56)
              || missingCritical >= 2
              || providedSignals <= 2
            )
          ) {{
            mode = "consult_only";
            label = "상담 후 안내";
            reason = "비슷한 사례가 매우 적어 업종과 실적을 먼저 확인한 뒤 가격을 안내해 드립니다.";
          }} else if (
            (Number.isFinite(confidenceScore) && confidenceScore < 68)
            || effectiveClusterCount < 5
            || missingCritical >= 2
            || providedSignals <= 2
          ) {{
            mode = "range_only";
            label = "범위 먼저 안내";
            reason = "비슷한 사례는 있지만 편차가 있어 기준가는 숨기고 범위부터 보여드립니다.";
          }} else {{
            mode = "full";
            label = "기준가+범위";
          }}
        }} else {{
          if (mode === "consult_only" && !label) label = "상담 후 안내";
          if (mode === "consult_only" && !reason) reason = "비슷한 사례가 매우 적어 업종과 실적을 먼저 확인한 뒤 가격을 안내해 드립니다.";
          if (mode === "range_only" && !label) label = "범위 먼저 안내";
          if (mode === "range_only" && !reason) reason = "비슷한 사례는 있지만 편차가 있어 기준가는 숨기고 범위부터 보여드립니다.";
        }}
        const publicCenterRaw = num(out.publicCenter ?? out.public_center_eok ?? out.center);
        const publicLowRaw = num(out.publicLow ?? out.public_low_eok ?? out.low);
        const publicHighRaw = num(out.publicHigh ?? out.public_high_eok ?? out.high);
        let publicCenterOut = Number.isFinite(publicCenterRaw) ? publicCenterRaw : null;
        let publicLowOut = Number.isFinite(publicLowRaw) ? publicLowRaw : null;
        let publicHighOut = Number.isFinite(publicHighRaw) ? publicHighRaw : null;
        if (mode === "consult_only") {{
          publicCenterOut = null;
          publicLowOut = null;
          publicHighOut = null;
        }} else if (mode === "range_only") {{
          publicCenterOut = null;
        }}
        if (reason && riskNotes.indexOf(reason) < 0) riskNotes.unshift(reason);
        out.publicationMode = mode || "full";
        out.publicationLabel = label || "기준가+범위";
        out.publicationReason = reason;
        out.publicCenter = publicCenterOut;
        out.publicLow = publicLowOut;
        out.publicHigh = publicHighOut;
        out.rawNeighborCount = rawNeighborCount;
        out.effectiveClusterCount = effectiveClusterCount;
        out.riskNotes = riskNotes;
        return out;
      }};
      const buildSettlementOutput = (rawOut) => {{
        const out = Object.assign({{}}, rawOut || {{}});
        const target = out && out.target ? out.target : null;
        const licenseRaw = compact((target && (target.license_raw || target.license_text || target.raw_license_key)) || out.license_text || "");
        const reorgModeRaw = compact((target && target.reorg_mode) || out.reorg_mode || "");
        const balanceExcluded = !!(target && target.balance_excluded);
        const balanceInput = Math.max(0, num((target && (target.input_balance_eok ?? target.balance_eok)) ?? out.raw_balance_input_eok) || 0);
        const requestedMode = compact((target && (target.balance_usage_mode_requested || target.balance_usage_mode)) || out.balance_usage_mode_requested || out.balance_usage_mode || "");
        const sellerWithdraws = !!((target && target.seller_withdraws_guarantee_loan) || out.seller_withdraws_guarantee_loan);
        const buyerTakesCredit = !!((target && target.buyer_takes_balance_as_credit) || out.buyer_takes_balance_as_credit);
        const requestedModeNormalized = normalizeBalanceUsageMode(requestedMode);
        let mode = resolveBalanceUsageMode(requestedMode, sellerWithdraws, buyerTakesCredit, balanceExcluded, licenseRaw, reorgModeRaw);
        const policy = balanceExcluded
          ? getSpecialBalanceAutoPolicy(licenseRaw, reorgModeRaw)
          : {{
              sector: "",
              reorgMode: normalizeReorgMode(reorgModeRaw),
              autoMode: "embedded_balance",
              loanUtilization: SPECIAL_BALANCE_LOAN_UTILIZATION,
              summary: "",
            }};
        const publicationMode = compact(out.publicationMode || out.publication_mode || "");
        const internalTotal = num(out.internalEstimateEok ?? out.internal_estimate_eok ?? out.center);
        const totalLow = num(out.low);
        const totalHigh = num(out.high);
        const publicTotal = publicationMode === "full" ? num(out.publicCenter ?? out.public_center_eok) : null;
        const publicLow = publicationMode === "consult_only" ? null : num(out.publicLow ?? out.public_low_eok);
        const publicHigh = publicationMode === "consult_only" ? null : num(out.publicHigh ?? out.public_high_eok);
        const buildSingleSettlementView = (resolvedModeRaw) => {{
          let resolvedMode = normalizeBalanceUsageMode(resolvedModeRaw) || compact(resolvedModeRaw) || (balanceExcluded ? "none" : "embedded_balance");
          if (balanceInput <= 0) resolvedMode = balanceExcluded ? "none" : resolvedMode;
          const loanUtilization = Number.isFinite(Number(policy && policy.loanUtilization))
            ? Number(policy.loanUtilization)
            : SPECIAL_BALANCE_LOAN_UTILIZATION;
          const embeddedRate = Math.max(0, Math.min(1.0, num(out.balancePassThrough ?? out.balance_pass_through) || 0));
          let rate = 0;
          const notes = [];
          if (resolvedMode === "credit_transfer") {{
            rate = balanceInput > 0 ? 1.0 : 0.0;
            notes.push("1:1 차감 기준");
          }} else if (resolvedMode === "loan_withdrawal") {{
            rate = balanceInput > 0 ? loanUtilization : 0.0;
            notes.push("융자 인출 후 현금 차감");
          }} else if (resolvedMode === "none") {{
            rate = 0.0;
            notes.push("별도 정산 없음");
          }} else {{
            resolvedMode = "embedded_balance";
            rate = balanceInput > 0 ? embeddedRate : 0.0;
            notes.push("총가 반영 잔액 분리");
          }}
          const totalForCalc = Number.isFinite(internalTotal) ? Math.max(0.05, internalTotal) : null;
          const realizableBalance = Number.isFinite(totalForCalc) ? Math.min(totalForCalc, balanceInput * rate) : null;
          const estimatedCashDue = (Number.isFinite(totalForCalc) && Number.isFinite(realizableBalance))
            ? Math.max(0, totalForCalc - realizableBalance)
            : null;
          const estimatedCashLow = (Number.isFinite(totalLow) && Number.isFinite(realizableBalance))
            ? Math.max(0, totalLow - realizableBalance)
            : null;
          const estimatedCashHigh = (Number.isFinite(totalHigh) && Number.isFinite(realizableBalance))
            ? Math.max(Number.isFinite(estimatedCashLow) ? estimatedCashLow : 0, totalHigh - realizableBalance)
            : null;
          const publicCashDue = (Number.isFinite(publicTotal) && Number.isFinite(realizableBalance))
            ? Math.max(0, publicTotal - realizableBalance)
            : null;
          const publicCashLow = (Number.isFinite(publicLow) && Number.isFinite(realizableBalance))
            ? Math.max(0, publicLow - realizableBalance)
            : null;
          const publicCashHigh = (Number.isFinite(publicHigh) && Number.isFinite(realizableBalance))
            ? Math.max(Number.isFinite(publicCashLow) ? publicCashLow : 0, publicHigh - realizableBalance)
            : null;
          return {{
            mode: resolvedMode,
            mode_label: balanceUsageModeLabel(resolvedMode),
            realizable_balance_rate: rate,
            realizable_balance_eok: Number.isFinite(realizableBalance) ? realizableBalance : null,
            total_transfer_value_eok: Number.isFinite(totalForCalc) ? totalForCalc : null,
            total_transfer_low_eok: Number.isFinite(totalLow) ? totalLow : null,
            total_transfer_high_eok: Number.isFinite(totalHigh) ? totalHigh : null,
            estimated_cash_due_eok: Number.isFinite(estimatedCashDue) ? estimatedCashDue : null,
            estimated_cash_due_low_eok: Number.isFinite(estimatedCashLow) ? estimatedCashLow : null,
            estimated_cash_due_high_eok: Number.isFinite(estimatedCashHigh) ? estimatedCashHigh : null,
            public_estimated_cash_due_eok: Number.isFinite(publicCashDue) ? publicCashDue : null,
            public_estimated_cash_due_low_eok: Number.isFinite(publicCashLow) ? publicCashLow : null,
            public_estimated_cash_due_high_eok: Number.isFinite(publicCashHigh) ? publicCashHigh : null,
            notes,
          }};
        }};
        let autoDecision = balanceExcluded
          ? resolveSpecialAutoMode(policy, internalTotal, balanceInput)
          : {{
              mode,
              reason: compact(policy.summary),
              balanceShare: Math.max(0, balanceInput) / Math.max(0.05, Number.isFinite(internalTotal) ? internalTotal : 0.05),
            }};
        if (balanceExcluded && (!requestedModeNormalized || requestedModeNormalized === "auto")) {{
          mode = compact(autoDecision.mode) || mode;
        }}
        const primary = buildSingleSettlementView(mode);
        out.balance_usage_mode_requested = requestedModeNormalized;
        out.balance_usage_mode = primary.mode;
        out.raw_balance_input_eok = balanceInput;
        out.balance_reference_eok = balanceInput;
        out.realizable_balance_rate = primary.realizable_balance_rate;
        out.realizable_balance_eok = primary.realizable_balance_eok;
        out.total_transfer_value_eok = primary.total_transfer_value_eok;
        out.total_transfer_low_eok = primary.total_transfer_low_eok;
        out.total_transfer_high_eok = primary.total_transfer_high_eok;
        out.estimated_cash_due_eok = primary.estimated_cash_due_eok;
        out.estimated_cash_due_low_eok = primary.estimated_cash_due_low_eok;
        out.estimated_cash_due_high_eok = primary.estimated_cash_due_high_eok;
        out.public_estimated_cash_due_eok = primary.public_estimated_cash_due_eok;
        out.public_estimated_cash_due_low_eok = primary.public_estimated_cash_due_low_eok;
        out.public_estimated_cash_due_high_eok = primary.public_estimated_cash_due_high_eok;
        out.settlement_policy = {{
          sector: compact(policy.sector),
          reorg_mode: compact(policy.reorgMode),
          auto_mode: compact(policy.autoMode),
          auto_mode_label: balanceUsageModeLabel(policy.autoMode),
          resolved_auto_mode: compact(autoDecision.mode),
          resolved_auto_mode_label: balanceUsageModeLabel(autoDecision.mode),
          auto_decision_reason: compact(autoDecision.reason),
          balance_share_of_total: Number.isFinite(Number(autoDecision.balanceShare)) ? Number(autoDecision.balanceShare) : null,
          loan_utilization: Number.isFinite(Number(policy.loanUtilization)) ? Number(policy.loanUtilization) : SPECIAL_BALANCE_LOAN_UTILIZATION,
          min_auto_balance_share: Number.isFinite(Number(policy.minAutoBalanceShare)) ? Number(policy.minAutoBalanceShare) : null,
          min_auto_balance_eok: Number.isFinite(Number(policy.minAutoBalanceEok)) ? Number(policy.minAutoBalanceEok) : null,
          summary: compact(policy.summary),
        }};
        out.settlement_scenarios = [];
        if (balanceExcluded && balanceInput > 0) {{
          const scenarioModes = SPECIAL_SETTLEMENT_SCENARIO_INPUT_MODES.slice();
          out.settlement_scenarios = scenarioModes.map((inputMode, idx) => {{
            const resolvedMode = inputMode === "auto"
              ? (compact(autoDecision.mode) || mode)
              : resolveBalanceUsageMode(inputMode, false, false, true, licenseRaw, reorgModeRaw);
            const row = buildSingleSettlementView(resolvedMode);
            const selected = (inputMode === "auto")
              ? ((!requestedModeNormalized || requestedModeNormalized === "auto") && compact(row.mode) === compact(autoDecision.mode || mode))
              : (requestedModeNormalized && requestedModeNormalized !== "auto" && compact(row.mode) === compact(mode));
            return {{
              scenario_index: idx,
              input_mode: inputMode,
              label: inputMode === "auto" ? "기본값(시장 관행 기준)" : balanceUsageModeLabel(inputMode),
              resolved_mode: row.mode,
              resolved_mode_label: row.mode_label,
              is_recommended: inputMode === "auto",
              is_selected: selected,
              realizable_balance_rate: row.realizable_balance_rate,
              realizable_balance_eok: row.realizable_balance_eok,
              estimated_cash_due_eok: row.estimated_cash_due_eok,
              estimated_cash_due_low_eok: row.estimated_cash_due_low_eok,
              estimated_cash_due_high_eok: row.estimated_cash_due_high_eok,
              public_estimated_cash_due_eok: row.public_estimated_cash_due_eok,
              public_estimated_cash_due_low_eok: row.public_estimated_cash_due_low_eok,
              public_estimated_cash_due_high_eok: row.public_estimated_cash_due_high_eok,
              notes: Array.isArray(row.notes) ? row.notes.slice() : [],
            }};
          }});
        }}
        out.settlement_breakdown = {{
          model: primary.mode,
          model_label: primary.mode_label,
          balance_excluded_from_total: balanceExcluded,
          split_optional_pricing: !!(target && target.split_optional_pricing),
          raw_balance_input_eok: balanceInput,
          realizable_balance_rate: primary.realizable_balance_rate,
          realizable_balance_eok: primary.realizable_balance_eok,
          buyer_cash_due_eok: primary.estimated_cash_due_eok,
          buyer_cash_due_low_eok: primary.estimated_cash_due_low_eok,
          buyer_cash_due_high_eok: primary.estimated_cash_due_high_eok,
          notes: Array.isArray(primary.notes) ? primary.notes.slice() : [],
          policy: Object.assign({{}}, out.settlement_policy || {{}}),
        }};
        return out;
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
        const requiresReorgMode = requiresReorgSelectionByLicense(licenseRaw);
        const requestedScaleSearchMode = getScaleSearchMode();
        const resolvedProfile = resolveLicenseProfile(licenseRaw);
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
        const reorgMode = normalizeReorgMode($("in-reorg-mode").value);
        const balanceExcluded = isSeparateBalanceGroupTarget({{
          license_raw: licenseRaw,
          raw_license_key: normalizeLicenseKey(licenseRaw),
          tokens,
        }});
        const requestedBalanceUsageMode = normalizeBalanceUsageMode($("in-balance-usage-mode").value);
        const balanceUsageMode = resolveBalanceUsageMode(
          requestedBalanceUsageMode,
          requestedBalanceUsageMode === "loan_withdrawal",
          requestedBalanceUsageMode === "credit_transfer",
          balanceExcluded,
          licenseRaw,
          reorgMode,
        );
        const splitOptionalPricing = isSplitOptionalPricingProfile({{
          license_raw: licenseRaw,
          raw_license_key: normalizeLicenseKey(licenseRaw),
          tokens,
        }}, reorgMode);
        const effectiveScaleSearchMode = (splitOptionalPricing && requestedScaleSearchMode === "specialty") ? "sales" : requestedScaleSearchMode;
        if (splitOptionalPricing && requestedScaleSearchMode === "specialty") {{
          scaleNotes.push("분할/합병에서는 시평보다 실적과 자본금 기준을 우선 적용합니다.");
        }}
        const licenseYear = num($("in-license-year").value);
        const balanceRaw = num($("in-balance").value);
        const capitalRaw = num($("in-capital").value);
        const surplusRaw = num($("in-surplus").value);
        const autoBalanceSeed = (!splitOptionalPricing && !balanceExcluded && !Number.isFinite(balanceRaw) && resolvedProfile)
          ? num(resolvedProfile.default_balance_eok)
          : null;
        const autoCapitalSeed = (!Number.isFinite(capitalRaw) && resolvedProfile)
          ? num(resolvedProfile.prefill_capital_eok)
          : null;
        const autoSurplusSeed = (!splitOptionalPricing && !Number.isFinite(surplusRaw) && resolvedProfile)
          ? num(resolvedProfile.prefill_surplus_eok)
          : null;
        const balanceSource = Number.isFinite(balanceRaw) ? balanceRaw : autoBalanceSeed;
        const capitalSource = Number.isFinite(capitalRaw) ? capitalRaw : autoCapitalSeed;
        const surplusSource = Number.isFinite(surplusRaw) ? surplusRaw : autoSurplusSeed;
        const autoAppliedFields = [];
        if (!balanceExcluded && !Number.isFinite(balanceRaw) && Number.isFinite(autoBalanceSeed)) {{
          autoAppliedFields.push("공제조합 잔액");
          scaleNotes.push(`${{compact((resolvedProfile && (resolvedProfile.display_name || resolvedProfile.token)) || "업종")}} 기준 통상 최저 공제조합 잔액 ${{fmtEok(autoBalanceSeed)}}를 자동 적용했습니다.`);
        }}
        if (!Number.isFinite(capitalRaw) && Number.isFinite(autoCapitalSeed)) autoAppliedFields.push("자본금");
        if (!splitOptionalPricing && !Number.isFinite(surplusRaw) && Number.isFinite(autoSurplusSeed)) autoAppliedFields.push("이익잉여금");
        const inputBalance = bounded(autoScaleByReference(balanceSource, num(meta.avg_balance_eok), num(meta.p90_balance_eok), "공제조합 잔액", scaleNotes, true), 0, 500);
        const balance = balanceExcluded ? null : inputBalance;
        const capital = bounded(autoScaleByReference(capitalSource, num(meta.avg_capital_eok), num(meta.p90_capital_eok), "자본금", scaleNotes), 0, 500);
        const surplus = splitOptionalPricing
          ? null
          : bounded(autoScaleByReference(surplusSource, num(meta.avg_surplus_eok), num(meta.p90_surplus_eok), "이익잉여금", scaleNotes), -300, 300);
        const companyType = compact($("in-company-type").value);
        const creditLevel = splitOptionalPricing ? "" : compact($("in-credit-level").value);
        const adminHistory = compact($("in-admin-history").value);
        const debtLevel = splitOptionalPricing ? "auto" : $("in-debt-level").value;
        const liqLevel = splitOptionalPricing ? "auto" : $("in-liq-level").value;
        const avgDebt = num(meta.avg_debt_ratio);
        const avgLiq = num(meta.avg_liq_ratio);
        let debtRatio = null;
        let liqRatio = null;
        if (!splitOptionalPricing && Number.isFinite(avgDebt)) {{
          if (debtLevel === "below") debtRatio = avgDebt * 0.82;
          else if (debtLevel === "above") debtRatio = avgDebt * 1.25;
        }}
        if (!splitOptionalPricing && Number.isFinite(avgLiq)) {{
          if (liqLevel === "above") liqRatio = avgLiq * 1.20;
          else if (liqLevel === "below") liqRatio = avgLiq * 0.78;
        }}
        let specialtyUse = null;
        let sales3Use = null;
        let sales5Use = null;
        if (!splitOptionalPricing && effectiveScaleSearchMode === "specialty") {{
          specialtyUse = specialty;
          y23Use = null;
          y24Use = null;
          y25Use = null;
        }} else {{
          specialtyUse = null;
          sales3Use = sales3;
          sales5Use = sales5;
        }}
        if (splitOptionalPricing) {{
          scaleNotes.push("전기/정보통신/소방의 분할/합병은 실적과 자본금 중심으로 계산합니다.");
        }}
        const numericSignals = [specialtyUse, y23Use, y24Use, y25Use, sales3Use, sales5Use, inputBalance, capital, surplus, licenseYear].filter((x) => Number.isFinite(x)).length;
        const categorySignals = [companyType, creditLevel, adminHistory].filter((x) => !!x).length;
        const missingCritical = [];
        if (!balanceExcluded && !Number.isFinite(balance)) missingCritical.push("공제조합 잔액");
        if (!licenseRaw) missingCritical.push("면허/업종");
        if (effectiveScaleSearchMode === "specialty") {{
          if (!splitOptionalPricing && !Number.isFinite(specialtyUse)) missingCritical.push("시평");
        }} else if (salesInputMode === "yearly") {{
          if (!Number.isFinite(y23Use) && !Number.isFinite(y24Use) && !Number.isFinite(y25Use)) missingCritical.push("실적");
        }} else if (salesInputMode === "sales3") {{
          if (!Number.isFinite(sales3Use)) missingCritical.push("실적");
        }} else if (salesInputMode === "sales5") {{
          if (!Number.isFinite(sales5Use)) missingCritical.push("실적");
        }}
        const missingGuide = [];
        if (!licenseRaw) missingGuide.push("면허/업종");
        if (requiresReorgMode && !reorgMode) missingGuide.push("포괄 또는 분할/합병");
        if (effectiveScaleSearchMode === "specialty") {{
          if (!splitOptionalPricing && !Number.isFinite(specialtyUse)) missingGuide.push("시평");
        }} else if (salesInputMode === "yearly") {{
          if (!Number.isFinite(y23Use) && !Number.isFinite(y24Use) && !Number.isFinite(y25Use)) missingGuide.push("연도별 매출(2023~2025)");
        }} else if (salesInputMode === "sales3") {{
          if (!Number.isFinite(sales3Use)) missingGuide.push("최근 3년 실적 합계");
        }} else if (salesInputMode === "sales5") {{
          if (!Number.isFinite(sales5Use)) missingGuide.push("최근 5년 실적 합계");
        }}
        return {{
          license_raw: licenseRaw,
          raw_license_key: normalizeLicenseKey(licenseRaw),
          has_license_input: !!licenseRaw,
          tokens,
          requires_reorg_mode: requiresReorgMode,
          reorg_mode: reorgMode,
          license_year: licenseYear,
          requested_scale_search_mode: requestedScaleSearchMode,
          scale_search_mode: effectiveScaleSearchMode,
          specialty: specialtyUse,
          y23: y23Use,
          y24: y24Use,
          y25: y25Use,
          sales_input_mode: salesInputMode,
          sales3_eok: sales3Use,
          sales5_eok: sales5Use,
          balance_eok: balance,
          input_balance_eok: inputBalance,
          balance_excluded: balanceExcluded,
          balance_usage_mode_requested: requestedBalanceUsageMode,
          balance_usage_mode: balanceUsageMode,
          seller_withdraws_guarantee_loan: balanceUsageMode === "loan_withdrawal",
          buyer_takes_balance_as_credit: balanceUsageMode === "credit_transfer",
          split_optional_pricing: splitOptionalPricing,
          capital_eok: capital,
          surplus_eok: surplus,
          auto_profile_label: resolvedProfile ? compact(resolvedProfile.display_name || resolvedProfile.token) : "",
          auto_applied_fields: autoAppliedFields,
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
        const hasCoreScaleInput = ["specialty", "sales3_eok", "sales5_eok", "capital_eok"].some((field) => {{
          const vv = num(target ? target[field] : null);
          return Number.isFinite(vv) && vv > 0;
        }});
        const balanceSimilarityWeight = hasCoreScaleInput ? 1.0 : 4.0;
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
        if (!balanceExcluded) score += sBalance * balanceSimilarityWeight;
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

      const featureScaleMismatch = (target, cand, balanceExcluded) => {{
        const checks = [];
        ["specialty", "sales3_eok"].forEach((field) => {{
          const targetValue = num(target && target[field]);
          if (!Number.isFinite(targetValue) || targetValue <= 0) return;
          const candValue = num(cand && cand[field]);
          if (!Number.isFinite(candValue) || candValue <= 0) {{
            checks.push({{ field, ratio: null, lo: 0.40, hi: 2.50 }});
            return;
          }}
          const ratio = positiveRatio(targetValue, candValue);
          if (!Number.isFinite(ratio)) {{
            checks.push({{ field, ratio: null, lo: 0.40, hi: 2.50 }});
            return;
          }}
          checks.push({{ field, ratio, lo: 0.40, hi: 2.50 }});
        }});
        const pushRatio = (field, lo, hi) => {{
          const ratio = positiveRatio(target && target[field], cand && cand[field]);
          if (!Number.isFinite(ratio)) return;
          checks.push({{ field, ratio, lo, hi }});
        }};
        pushRatio("capital_eok", 0.55, 1.90);
        if (!balanceExcluded) pushRatio("balance_eok", 0.25, 4.00);
        let mismatchCount = 0;
        checks.forEach((item) => {{
          if (!Number.isFinite(item.ratio)) {{
            if (item.field === "specialty" || item.field === "sales3_eok") mismatchCount += 1;
            return;
          }}
          if (item.ratio < item.lo || item.ratio > item.hi) mismatchCount += 1;
        }});
        return {{ signalCount: checks.length, mismatchCount }};
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

      const buildStableAnchorTarget = (target) => {{
        const anchorTarget = Object.assign({{}}, target || {{}});
        [
          "specialty",
          "sales3_eok",
          "sales5_eok",
          "license_year",
          "debt_ratio",
          "liq_ratio",
          "capital_eok",
          "balance_eok",
          "surplus_eok",
        ].forEach((field) => {{
          anchorTarget[field] = null;
        }});
        anchorTarget.provided_signals = compact(anchorTarget.license_text).length ? 3 : 0;
        anchorTarget.missing_critical = [];
        anchorTarget.missing_guide = [];
        return anchorTarget;
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
          return {{ slope: NaN, reliability: 0.0, samples: rows.length }};
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
        if (!Number.isFinite(slope)) return {{ slope: NaN, reliability: 0.0, samples: rows.length }};
        slope = clamp(slope, 0.92, 1.08);
        const minB = Math.min(...rows.map((x) => x.b));
        const maxB = Math.max(...rows.map((x) => x.b));
        const span = Math.max(0, maxB - minB);
        const reliability = clamp(((rows.length / 12) * 0.7) + (Math.min(1, span / 2.5) * 0.3), 0.25, 0.92);
        return {{ slope, reliability, samples: rows.length }};
      }};

      const BALANCE_BASE_CORE_BETA = 0.785;
      const balanceBaseTargetCenter = (coreCenter, balanceInput, effectiveBalanceRate) => {{
        return Math.max(0.05, (Number(coreCenter) * BALANCE_BASE_CORE_BETA) + (Number(balanceInput) * Number(effectiveBalanceRate)));
      }};

      const buildFeatureAnchor = (target, neighbors, balanceSlope = 0, balanceExcluded = false) => {{
        const components = [];
        const compWeights = [];
        let maxSamples = 0;
        const notes = [];
        const build = (targetValue, field, weight, label, ratioLo = 0.004, ratioHi = 9.0) => {{
          if (!Number.isFinite(targetValue) || targetValue <= 0) return;
          const ratios = [];
          const ratioWeights = [];
          neighbors.slice(0, 20).forEach(([sim, rec]) => {{
            const price = num(rec.price_eok);
            const base = num(rec[field]);
            if (!Number.isFinite(price) || !Number.isFinite(base) || base <= 0) return;
            let corePrice = price;
            if (!balanceExcluded && Number.isFinite(balanceSlope) && balanceSlope > 0) {{
              const recBalance = num(rec.balance_eok);
              if (Number.isFinite(recBalance) && recBalance >= 0) {{
                corePrice = price - (recBalance * balanceSlope);
              }}
            }}
            if (!Number.isFinite(corePrice) || corePrice <= 0.03) return;
            const ratio = corePrice / base;
            if (!Number.isFinite(ratio) || ratio < ratioLo || ratio > ratioHi) return;
            ratios.push(ratio);
            ratioWeights.push(Math.max(0.2, (Number(sim) || 0) / 45));
          }});
          if (ratios.length < 3) return;
          if (ratios.length >= 4) {{
            const trimLo = weightedQuantile(ratios, ratioWeights, 0.15);
            const trimHi = weightedQuantile(ratios, ratioWeights, 0.85);
            if (Number.isFinite(trimLo) && Number.isFinite(trimHi) && trimHi > trimLo) {{
              const trimmedRatios = [];
              const trimmedWeights = [];
              ratios.forEach((ratio, idx) => {{
                if (ratio < trimLo || ratio > trimHi) return;
                trimmedRatios.push(ratio);
                trimmedWeights.push(ratioWeights[idx]);
              }});
              if (trimmedRatios.length >= 3) {{
                ratios.length = 0;
                ratioWeights.length = 0;
                trimmedRatios.forEach((ratio) => ratios.push(ratio));
                trimmedWeights.forEach((weightValue) => ratioWeights.push(weightValue));
              }}
            }}
          }}
          maxSamples = Math.max(maxSamples, ratios.length);
          const ratioMid = weightedQuantile(ratios, ratioWeights, 0.5);
          if (!Number.isFinite(ratioMid) || ratioMid <= 0) return;
          components.push(targetValue * ratioMid);
          compWeights.push(weight);
          notes.push(`${{label}} 앵커 반영`);
        }};
        build(num(target.specialty), "specialty", 0.52, "시평");
        build(num(target.sales3_eok), "sales3_eok", 0.30, "3개년 실적");
        build(num(target.capital_eok), "capital_eok", 0.12, "자본금", 0.02, 15.0);
        if (!target.balance_excluded && !(Number.isFinite(balanceSlope) && balanceSlope > 0)) build(num(target.balance_eok), "balance_eok", 0.02, "공제조합 잔액", 0.02, 40.0);
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
        if (ratio >= 0.78 && ratio <= 1.42) {{
          const mildGap = Math.abs(ratio - 1);
          if (mildGap < 0.03) return {{ center, low, high }};
          const mildPull = Math.min(0.16, 0.04 + (mildGap * 0.28)) * reliability;
          let mildCenter = (center * (1 - mildPull)) + (anchor * mildPull);
          if (!Number.isFinite(mildCenter) || mildCenter <= 0) return {{ center, low, high }};
          if (mildCenter > center) {{
            const upCap = center * (1.14 + (reliability * 0.12));
            if (mildCenter > upCap) {{
              mildCenter = upCap;
              riskNotes.push("입력 스케일 상향 보정 한도 적용");
            }}
          }}
          const mildScale = mildCenter / Math.max(center, 0.05);
          return {{
            center: mildCenter,
            low: Math.max(0.05, low * mildScale),
            high: Math.max(Math.max(0.05, low * mildScale), high * mildScale),
          }};
        }}
        const pull = Math.max(0.24, Math.min(0.72, (Math.abs(ratio - 1) * 0.52) + 0.08)) * (0.55 + (reliability * 0.45));
        let adjustedCenter = (center * (1 - pull)) + (anchor * pull);
        if (!Number.isFinite(adjustedCenter) || adjustedCenter <= 0) return {{ center, low, high }};
        if (adjustedCenter > center) {{
          const upCap = center * (1.14 + (reliability * 0.12));
          if (adjustedCenter > upCap) {{
            adjustedCenter = upCap;
            riskNotes.push("입력 스케일 상향 보정 한도 적용");
          }}
        }}
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
          riskNotes.push(`유사군 일관성 보정: 비슷한 사례 상위 분위 대비 과대 추정을 ${{
            Math.round(Math.max(0, ((center / Math.max(ref, 0.05)) - 1) * 100))
          }}% 구간에서 안정화했습니다.`);
        }}
        return {{ center: nextCenter, low: nextLow, high: nextHigh }};
      }};

      const applySparseCoreGuard = (center, low, high, prices, sims, effectiveClusterCount, target, riskNotes) => {{
        if (!Number.isFinite(center) || center <= 0) return {{ center, low, high }};
        const safePrices = (Array.isArray(prices) ? prices : []).map((v) => Number(v)).filter((v) => Number.isFinite(v) && v > 0);
        if (safePrices.length < 3) return {{ center, low, high }};
        const safeSims = (Array.isArray(sims) ? sims : []).map((v) => Number(v)).filter((v) => Number.isFinite(v) && v > 0);
        const weights = safeSims.length === safePrices.length ? safeSims : safePrices.map(() => 1);
        const support = Math.max(1, Math.min(Number(effectiveClusterCount) || safePrices.length, safePrices.length));
        if (support >= 5) return {{ center, low, high }};
        const p20 = weightedQuantile(safePrices, weights, 0.20);
        const p35 = weightedQuantile(safePrices, weights, 0.35);
        const p50 = weightedQuantile(safePrices, weights, 0.50);
        if (!Number.isFinite(p35) || p35 <= 0) return {{ center, low, high }};
        const excess = (center / Math.max(p35, 0.05)) - 1;
        if (excess <= 0.05) return {{ center, low, high }};
        let basePull = support === 4 ? 0.12 : (support === 3 ? 0.18 : 0.28);
        if (target && target.single_core_mode) basePull += 0.05;
        if (Number(target && target.provided_signals) <= 4) basePull += 0.04;
        const pull = Math.max(basePull, Math.min(0.48, Math.max(0, excess * 0.36)));
        const nextCenter = (center * (1 - pull)) + (p35 * pull);
        if (!Number.isFinite(nextCenter) || nextCenter >= center) return {{ center, low, high }};
        const scale = nextCenter / Math.max(center, 0.05);
        let nextLow = Math.max(0.05, low * scale);
        if (Number.isFinite(p20) && support <= 3) {{
          nextLow = Math.max(0.05, Math.min(nextLow, p20));
        }}
        const highRef = Number.isFinite(p50) && p50 > 0 ? p50 : p35;
        const highCap = highRef * (support <= 2 ? 1.78 : (support === 3 ? 1.92 : 2.05));
        const nextHigh = Math.max(nextLow, Math.min(high * scale, highCap));
        if (Array.isArray(riskNotes)) {{
          riskNotes.push("희소 유사군 보수화: 근거가 얇은 구간은 기준가를 하단 쪽으로 안정화했습니다.");
        }}
        return {{ center: nextCenter, low: nextLow, high: nextHigh }};
      }};

      const valueRatio = (left, right) => {{
        const lv = num(left);
        const rv = num(right);
        if (!Number.isFinite(lv) || !Number.isFinite(rv) || lv <= 0 || rv <= 0) return null;
        return Math.max(lv, rv) / Math.max(0.05, Math.min(lv, rv));
      }};

      const rangePair = (rec) => {{
        const low = num(rec && rec.display_low_eok);
        const high = num(rec && rec.display_high_eok);
        if (!Number.isFinite(low) && !Number.isFinite(high)) {{
          const center = num(rec && (rec.price_eok ?? rec.current_price_eok));
          return [center, center];
        }}
        let lo = Number.isFinite(low) ? low : high;
        let hi = Number.isFinite(high) ? high : low;
        if (Number.isFinite(lo) && Number.isFinite(hi) && hi < lo) {{
          const tmp = lo;
          lo = hi;
          hi = tmp;
        }}
        return [lo, hi];
      }};

      const priceOverlapScore = (left, right) => {{
        const [l1, h1] = rangePair(left);
        const [l2, h2] = rangePair(right);
        if (![l1, h1, l2, h2].every((x) => Number.isFinite(x))) return 0;
        const overlapLow = Math.max(l1, l2);
        const overlapHigh = Math.min(h1, h2);
        if (overlapHigh >= overlapLow) {{
          const overlap = overlapHigh - overlapLow;
          const union = Math.max(h1, h2) - Math.min(l1, l2);
          if (union <= 0) return 1;
          return clamp(overlap / union, 0, 1);
        }}
        return relativeCloseness((l1 + h1) / 2, (l2 + h2) / 2);
      }};

      const textKey = (value) => compact(value).toLowerCase();
      const sameTextScore = (left, right) => {{
        const a = textKey(left);
        const b = textKey(right);
        if (!a || !b) return 0;
        return a === b ? 1 : 0;
      }};

      const locationMatchScore = (left, right) => {{
        const a = textKey(left && left.location);
        const b = textKey(right && right.location);
        if (!a || !b) return 0;
        if (a === b) return 1;
        const a1 = a.split(/\\s+/)[0];
        const b1 = b.split(/\\s+/)[0];
        return a1 && b1 && a1 === b1 ? 0.65 : 0;
      }};

      const extremeMismatchCount = (left, right) => {{
        let count = 0;
        ["specialty", "sales3_eok", "capital_eok"].forEach((key) => {{
          const ratio = valueRatio(left && left[key], right && right[key]);
          if (Number.isFinite(ratio) && ratio > 4) count += 1;
        }});
        return count;
      }};

      const duplicateAffinity = (left, right) => {{
        const leftTokens = new Set(Array.isArray(left && left.tokens) ? left.tokens : []);
        const rightTokens = new Set(Array.isArray(right && right.tokens) ? right.tokens : []);
        const inter = [...leftTokens].filter((x) => rightTokens.has(x));
        if (!inter.length) return {{ score: 0, secondaryHits: 0 }};
        if (extremeMismatchCount(left, right) >= 2) return {{ score: 0, secondaryHits: 0 }};
        const specialtyClose = relativeCloseness(left && left.specialty, right && right.specialty);
        const sales3Close = relativeCloseness(left && left.sales3_eok, right && right.sales3_eok);
        const capitalClose = relativeCloseness(left && left.capital_eok, right && right.capital_eok);
        const yearClose = relativeCloseness(left && left.license_year, right && right.license_year);
        const sharesClose = relativeCloseness(left && left.shares, right && right.shares);
        const priceOverlap = priceOverlapScore(left, right);
        const companyMatch = sameTextScore(left && left.company_type, right && right.company_type);
        const locationMatch = locationMatchScore(left, right);
        const associationMatch = sameTextScore(left && left.association, right && right.association);
        const score = (
          (jaccard(leftTokens, rightTokens) * 0.24) +
          (tokenContainment(leftTokens, rightTokens) * 0.14) +
          (specialtyClose * 0.14) +
          (sales3Close * 0.14) +
          (capitalClose * 0.10) +
          (yearClose * 0.06) +
          (sharesClose * 0.05) +
          (priceOverlap * 0.06) +
          (companyMatch * 0.04) +
          (locationMatch * 0.02) +
          (associationMatch * 0.01)
        );
        const secondaryHits = [
          priceOverlap >= 0.35,
          companyMatch >= 1,
          locationMatch >= 0.65,
          associationMatch >= 1,
          sharesClose >= 0.85,
        ].filter(Boolean).length;
        return {{ score, secondaryHits }};
      }};

      const isSameDuplicateCluster = (left, right) => {{
        const affinity = duplicateAffinity(left, right);
        if (affinity.score >= 0.82) return true;
        if (affinity.score >= 0.72 && affinity.secondaryHits >= 2) return true;
        return false;
      }};

      const completenessScore = (rec) => {{
        let score = 0;
        ["specialty", "sales3_eok", "capital_eok", "license_year", "display_low_eok", "display_high_eok", "claim_price_eok"].forEach((key) => {{
          if (Number.isFinite(num(rec && rec[key]))) score += 1;
        }});
        ["company_type", "location", "association"].forEach((key) => {{
          if (textKey(rec && rec[key])) score += 1;
        }});
        return score;
      }};

      const collapseDuplicateNeighborRows = (neighbors) => {{
        const rows = Array.isArray(neighbors)
          ? neighbors
              .filter((row) => Array.isArray(row) && row[1] && typeof row[1] === "object")
              .map((row) => [Number(row[0]) || 0, row[1]])
          : [];
        const rawCount = rows.length;
        if (rawCount <= 1) {{
          return {{
            collapsed_neighbors: rows,
            raw_neighbor_count: rawCount,
            effective_cluster_count: rawCount,
            duplicate_cluster_adjusted: false,
          }};
        }}
        const parent = rows.map((_, idx) => idx);
        const find = (idx) => {{
          let cursor = idx;
          while (parent[cursor] !== cursor) {{
            parent[cursor] = parent[parent[cursor]];
            cursor = parent[cursor];
          }}
          return cursor;
        }};
        const union = (a, b) => {{
          const ra = find(a);
          const rb = find(b);
          if (ra !== rb) parent[rb] = ra;
        }};
        for (let i = 0; i < rows.length; i += 1) {{
          for (let j = i + 1; j < rows.length; j += 1) {{
            if (isSameDuplicateCluster(rows[i][1], rows[j][1])) union(i, j);
          }}
        }}
        const grouped = new Map();
        rows.forEach((row, idx) => {{
          const root = find(idx);
          if (!grouped.has(root)) grouped.set(root, []);
          grouped.get(root).push(row);
        }});
        const collapsed = [];
        grouped.forEach((clusterRows) => {{
          const ranked = clusterRows.slice().sort((a, b) => {{
            const completenessDiff = completenessScore(b[1]) - completenessScore(a[1]);
            if (completenessDiff !== 0) return completenessDiff;
            const simDiff = (Number(b[0]) || 0) - (Number(a[0]) || 0);
            if (simDiff !== 0) return simDiff;
            return (Number(b[1] && b[1].row) || 0) - (Number(a[1] && a[1].row) || 0);
          }});
          const rep = Object.assign({{}}, ranked[0][1] || {{}});
          rep.cluster_size = clusterRows.length;
          rep.cluster_member_uids = clusterRows
            .map((x) => compact(x && x[1] ? x[1].uid : ""))
            .filter(Boolean)
            .slice(0, 12);
          collapsed.push([Number(ranked[0][0]) || 0, rep]);
        }});
        collapsed.sort((a, b) => (Number(b[0]) || 0) - (Number(a[0]) || 0));
        return {{
          collapsed_neighbors: collapsed,
          raw_neighbor_count: rawCount,
          effective_cluster_count: collapsed.length,
          duplicate_cluster_adjusted: collapsed.length !== rawCount,
        }};
      }};

      const buildRecommendationReasons = (target, rec, metrics) => {{
        const reasons = [];
        const tokenMatch = Number(metrics && metrics.tokenMatch) || 0;
        const sameCore = Number(metrics && metrics.sameCore) || 0;
        const salesFit = Number(metrics && metrics.salesFit) || 0;
        const priceFit = Number(metrics && metrics.priceFit) || 0;
        const specialtyFit = Number(metrics && metrics.specialtyFit) || 0;
        const capitalFit = Number(metrics && metrics.capitalFit) || 0;
        const balanceFit = Number(metrics && metrics.balanceFit) || 0;
        const yearlyFit = Number(metrics && metrics.yearlyFit) || 0;
        const companyMatch = Number(metrics && metrics.companyMatch) || 0;
        if (tokenMatch >= 0.999) reasons.push("면허 구성이 같습니다");
        else if (sameCore >= 0.999) reasons.push("같은 핵심 업종입니다");
        if (salesFit >= 0.72) reasons.push("최근 실적 규모가 비슷합니다");
        else if (yearlyFit >= 0.70) reasons.push("최근 3년 실적 흐름이 비슷합니다");
        if (priceFit >= 0.62) reasons.push("현재 입력 조건과 비교 우선도가 높습니다");
        if (specialtyFit >= 0.78 && Number.isFinite(num(target && target.specialty))) reasons.push("시평 규모가 비슷합니다");
        if (capitalFit >= 0.78 && Number.isFinite(num(target && target.capital_eok))) reasons.push("자본금 규모가 비슷합니다");
        if (!(target && target.balance_excluded) && balanceFit >= 0.72 && Number.isFinite(num(target && target.balance_eok))) reasons.push("공제조합 잔액 규모가 비슷합니다");
        if (companyMatch >= 0.999) reasons.push("회사 형태가 같습니다");
        if (!reasons.length) reasons.push("입력한 면허와 현재 조건이 가까운 매물입니다");
        return reasons.filter((item, idx, arr) => item && arr.indexOf(item) === idx).slice(0, 3);
      }};

      const buildRecommendedListings = (target, rows, center, low, high, limit = 4) => {{
        const sourceRows = Array.isArray(rows) ? rows.filter((row) => Array.isArray(row) && row[1]) : [];
        if (!sourceRows.length) return [];
        const estimateRef = {{
          display_low_eok: Number.isFinite(num(low)) ? num(low) : null,
          display_high_eok: Number.isFinite(num(high)) ? num(high) : null,
          price_eok: Number.isFinite(num(center)) ? num(center) : null,
        }};
        const targetTokens = target && target.tokens instanceof Set ? target.tokens : new Set();
        const targetCompany = normalizeCompanyType(target && target.company_type);
        const targetHasSales = ["sales3_eok", "sales5_eok"].some((field) => (num(target && target[field]) || 0) > 0);
        const ranked = [];
        const seen = new Set();
        sourceRows.forEach(([simRaw, rec]) => {{
          const recObj = rec && typeof rec === "object" ? rec : null;
          if (!recObj) return;
          const marker = `${{Number(recObj.seoul_no || recObj.number || 0)}}:${{compact(recObj.now_uid || recObj.uid || "")}}:${{Number(recObj.row || 0)}}`;
          if (seen.has(marker)) return;
          seen.add(marker);
          const sim = Number(simRaw) || 0;
          const candTokens = Array.isArray(recObj.tokens) && recObj.tokens.length
            ? new Set(recObj.tokens)
            : licenseTokenSet(recObj.license_text || "");
          const tokenMatch = (targetTokens.size && candTokens.size) ? tokenContainment(targetTokens, candTokens) : 0;
          const sameCore = (singleTokenTargetCore(targetTokens) && isSingleTokenSameCore(targetTokens, candTokens, recObj.license_text || "")) ? 1 : 0;
          const recHasSales = ["sales3_eok", "sales5_eok"].some((field) => (num(recObj && recObj[field]) || 0) > 0);
          const salesFit = displaySalesFitScore(target, recObj);
          const specialtyFit = relativeCloseness(num(target && target.specialty), num(recObj.specialty));
          const capitalFit = relativeCloseness(num(target && target.capital_eok), num(recObj.capital_eok));
          const balanceFit = (target && target.balance_excluded) ? 0 : relativeCloseness(num(target && target.balance_eok), num(recObj.balance_eok));
          const yearly = yearlyShapeSimilarity(target || {{}}, recObj || {{}});
          const yearlyFit = clamp((Number(yearly) || 0) * 0.86, 0, 1);
          let priceFit = priceOverlapScore(estimateRef, recObj);
          const estimateRange = rangePair(estimateRef);
          const recRange = rangePair(recObj);
          if (
            estimateRange.every((value) => Number.isFinite(value))
            && recRange.every((value) => Number.isFinite(value))
            && Math.min(estimateRange[1], recRange[1]) < Math.max(estimateRange[0], recRange[0])
          ) {{
            priceFit *= 0.35;
          }}
          const companyMatch = (targetCompany && targetCompany === normalizeCompanyType(recObj.company_type)) ? 1 : 0;
          const mismatch = featureScaleMismatch(target || {{}}, recObj || {{}}, !!(target && target.balance_excluded));
          let score = 0;
          score += (sim / 100) * 0.30;
          score += Math.max(salesFit, tokenMatch, sameCore) * 0.24;
          score += priceFit * 0.18;
          score += specialtyFit * 0.10;
          score += capitalFit * 0.07;
          score += balanceFit * 0.04;
          score += yearlyFit * 0.05;
          score += companyMatch * 0.02;
          if (targetTokens.size && tokenMatch >= 0.999) score += 0.03;
          if (sameCore >= 0.999) score += 0.02;
          if (Number(mismatch && mismatch.signalCount) >= 2 && Number(mismatch && mismatch.mismatchCount) >= Number(mismatch && mismatch.signalCount)) score -= 0.18;
          else if (Number(mismatch && mismatch.signalCount) >= 2 && Number(mismatch && mismatch.mismatchCount) >= 2) score -= 0.08;
          if (targetHasSales && recHasSales) {{
            if (salesFit < 0.50) score -= 0.18;
            else if (salesFit < 0.62) score -= 0.12;
          }}
          if (priceFit < 0.16 && salesFit < 0.48 && sim < 88) score -= 0.10;
          score = clamp(score, 0, 1);
          const bucket = ((salesFit >= 0.72 && priceFit >= 0.20) || salesFit >= 0.82 || (score >= 0.78 && salesFit >= 0.62))
            ? 2
            : (((salesFit >= 0.58 && priceFit >= 0.12) || salesFit >= 0.68 || (score >= 0.64 && salesFit >= 0.50)) ? 1 : 0);
          if (bucket <= 0 && score < 0.54) return;
          const reasons = buildRecommendationReasons(target, recObj, {{
            tokenMatch,
            sameCore,
            salesFit,
            priceFit,
            specialtyFit,
            capitalFit,
            balanceFit,
            yearlyFit,
            companyMatch,
          }});
          const label = score >= 0.78 ? "우선 검토" : (score >= 0.64 ? "조건 유사" : "보조 검토");
          ranked.push({{
            bucket,
            band: listingNumberBand(recObj.seoul_no || recObj.number),
            score,
            sim,
            no: Number(recObj.seoul_no || recObj.number || 0),
            row: {{
              seoul_no: Number(recObj.seoul_no || recObj.number || 0),
              now_uid: String(recObj.now_uid || recObj.uid || ""),
              license_text: String(recObj.license_text || ""),
              price_eok: Number.isFinite(num(recObj.price_eok)) ? num(recObj.price_eok) : num(recObj.current_price_eok),
              display_low_eok: Number.isFinite(num(recObj.display_low_eok)) ? num(recObj.display_low_eok) : num(recObj.price_eok),
              display_high_eok: Number.isFinite(num(recObj.display_high_eok)) ? num(recObj.display_high_eok) : num(recObj.price_eok),
              recommendation_score: Math.round(score * 1000) / 10,
              recommendation_label: label,
              similarity: Math.round(sim * 10) / 10,
              reasons,
              url: String(recObj.url || siteMna),
            }},
          }});
        }});
        ranked.sort((left, right) => {{
          if (left.bucket !== right.bucket) return right.bucket - left.bucket;
          const scoreGap = Math.abs((left.score || 0) - (right.score || 0));
          if (scoreGap > 0.015 && left.score !== right.score) return right.score - left.score;
          if (left.band !== right.band) return right.band - left.band;
          if (left.sim !== right.sim) return right.sim - left.sim;
          if (left.score !== right.score) return right.score - left.score;
          return right.no - left.no;
        }});
        if (ranked.length) return ranked.slice(0, Math.max(1, limit || 0)).map((entry) => entry.row);
        return prioritizeDisplayNeighborRows(sourceRows, target).slice(0, Math.max(1, Math.min(limit || 0, 3))).map(([sim, rec]) => ({{
          seoul_no: Number(rec.seoul_no || rec.number || 0),
          now_uid: String(rec.now_uid || rec.uid || ""),
          license_text: String(rec.license_text || ""),
          price_eok: Number.isFinite(num(rec.price_eok)) ? num(rec.price_eok) : num(rec.current_price_eok),
          display_low_eok: Number.isFinite(num(rec.display_low_eok)) ? num(rec.display_low_eok) : num(rec.price_eok),
          display_high_eok: Number.isFinite(num(rec.display_high_eok)) ? num(rec.display_high_eok) : num(rec.price_eok),
          recommendation_score: Math.round((Number(sim) || 0) * 10) / 10,
          recommendation_label: "조건 유사",
          similarity: Math.round((Number(sim) || 0) * 10) / 10,
          reasons: ["입력한 면허와 현재 조건이 가까운 매물입니다"],
          url: String(rec.url || siteMna),
        }}));
      }};

      const normalizeRecommendationRows = (rawRows, target, center, low, high, fallbackRows = []) => {{
        const mapped = Array.isArray(rawRows) ? rawRows.map((row) => {{
          const reasons = Array.isArray(row && row.reasons)
            ? row.reasons.map((item) => compact(item)).filter((item) => !!item)
            : [];
          return {{
            seoul_no: Number(row && (row.seoul_no ?? row.no) || 0),
            now_uid: String(row && (row.now_uid || row.uid) || ""),
            license_text: String(row && (row.license_text || row.license) || ""),
            price_eok: Number.isFinite(num(row && (row.price_eok ?? row.center_eok))) ? num(row && (row.price_eok ?? row.center_eok)) : null,
            display_low_eok: Number.isFinite(num(row && (row.display_low_eok ?? row.low_eok ?? row.range_low))) ? num(row && (row.display_low_eok ?? row.low_eok ?? row.range_low)) : null,
            display_high_eok: Number.isFinite(num(row && (row.display_high_eok ?? row.high_eok ?? row.range_high))) ? num(row && (row.display_high_eok ?? row.high_eok ?? row.range_high)) : null,
            recommendation_score: Number.isFinite(num(row && (row.recommendation_score ?? row.score))) ? num(row && (row.recommendation_score ?? row.score)) : null,
            recommendation_label: compact(row && row.recommendation_label) || "조건 유사",
            similarity: Number.isFinite(num(row && (row.similarity ?? row.sim))) ? num(row && (row.similarity ?? row.sim)) : null,
            reasons: reasons.length ? reasons.slice(0, 3) : ["입력한 면허와 현재 조건이 가까운 매물입니다"],
            url: String(row && row.url || siteMna),
          }};
        }}).filter((row) => row && (row.seoul_no > 0 || row.url)) : [];
        if (mapped.length) return mapped.slice(0, 4);
        return buildRecommendedListings(target, fallbackRows, center, low, high, 4);
      }};

      const estimateLocal = (target) => {{
        const balanceExcluded = !!(target && target.balance_excluded);
        const candidates = selectCandidates(target);
        const topK = 12;
        let scored = [];
        let minSimilarity = target.tokens.size ? 26 : 14;
        if (target.tokens.size >= 2) minSimilarity = 32;
        if (target.tokens.size && candidates.length <= 16) minSimilarity = Math.max(20, minSimilarity - 4);
        if (target.provided_signals <= 2) minSimilarity = minSimilarity + 6;
        if (target.tokens.size && !target.missing_critical.length) minSimilarity += 3;
        const strictSameCore = !!singleTokenTargetCore(target.tokens);
        const targetCoreSet = coreTokens(target.tokens);
        const targetCoreCount = targetCoreSet.size;
        const scorePool = (modelTarget, pool, strictOnly, threshold) => {{
          const modelTokens = modelTarget && modelTarget.tokens ? modelTarget.tokens : new Set();
          const modelCoreSet = coreTokens(modelTokens);
          const modelCoreCount = modelCoreSet.size;
          const rows = [];
          for (const cand of pool) {{
            const p = Number(cand.price_eok);
            if (!Number.isFinite(p) || p <= 0) continue;
            const candTokens = new Set(Array.isArray(cand.tokens) ? cand.tokens : []);
            const candCore = new Set([...coreTokens(candTokens), ...coreTokensFromText(cand.license_text || "")]);
            if (modelCoreCount >= 2) {{
              const hasCoreOverlap = [...modelCoreSet].some((x) => candCore.has(x));
              if (!hasCoreOverlap) continue;
            }}
            if (strictOnly && !isSingleTokenSameCore(modelTokens, candTokens, cand.license_text)) continue;
            if (isSingleTokenCrossCombo(modelTokens, candTokens, cand.license_text)) continue;
            if (isSingleTokenProfileOutlier(modelTarget, cand)) continue;
            const sim = neighborScore(modelTarget, cand);
            if (sim < threshold) continue;
            rows.push([sim, cand]);
          }}
          return rows;
        }};
        scored = scorePool(target, candidates, strictSameCore, minSimilarity);
        if (strictSameCore && !scored.length) {{
          scored = scorePool(target, candidates, true, Math.max(12, minSimilarity - 8));
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
        const publicationSeedRows = scored.slice(0, Math.max(12, topK));
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
            const candCore = new Set([...coreTokens(candTokens), ...coreTokensFromText(candLicenseText)]);
            const interCoreCount = [...targetCoreSet].filter((x) => candCore.has(x)).length;
            const coreContain = interCoreCount / Math.max(1, Math.min(targetCoreSet.size, candCore.size || targetCoreSet.size));
            return interCoreCount >= Math.min(2, targetCoreSet.size) || Math.max(tokenContainment(target.tokens, candTokens), coreContain) >= 0.60;
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
        const singleCoreReferencePool = statNeighbors.slice();

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
        const featureFiltered = neighbors.filter((row) => {{
          const rec = row && row[1] ? row[1] : null;
          const sim = Number(row && row[0]);
          const diag = featureScaleMismatch(target, rec || {{}}, balanceExcluded);
          const hardScaleMismatch = diag.signalCount >= 2 && diag.mismatchCount >= diag.signalCount;
          if (hardScaleMismatch) return false;
          const mismatchSimCap = targetCoreCount >= 2 ? 94 : 96;
          if (diag.signalCount >= 2 && diag.mismatchCount >= 2 && sim < mismatchSimCap) return false;
          return true;
        }});
        const featureNeighborFloor = targetCoreCount === 1 ? 4 : (targetCoreCount >= 2 ? 3 : 6);
        if (featureFiltered.length >= Math.max(featureNeighborFloor, Math.min(8, topK))) neighbors = featureFiltered;
        const collectSingleCoreRows = (rows) => rows.filter((row) => {{
          const rec = row && row[1] ? row[1] : null;
          const candTokens = new Set(Array.isArray(rec && rec.tokens) ? rec.tokens : []);
          if (isSingleTokenCrossCombo(target.tokens, candTokens, rec && rec.license_text ? rec.license_text : "")) return false;
          if (!isSingleTokenSameCore(target.tokens, candTokens, rec && rec.license_text ? rec.license_text : "")) return false;
          const yearly = yearlyShapeSimilarity(target, rec);
          const tYearSeries = yearlySeries(target);
          const cYearSeries = yearlySeries(rec);
          const hasYearlyBasis = tYearSeries.count >= 2 && cYearSeries.count >= 2 && tYearSeries.sum > 0 && cYearSeries.sum > 0;
          if (hasYearlyBasis && yearly < 0.44) return false;
          return true;
        }});
        let singleCoreReferenceRows = [];
        if (strictSameCore) {{
          singleCoreReferenceRows = collectSingleCoreRows(publicationSeedRows);
          if (!singleCoreReferenceRows.length) {{
            singleCoreReferenceRows = collectSingleCoreRows(neighbors);
          }}
          if (!singleCoreReferenceRows.length && singleCoreReferencePool.length) {{
            singleCoreReferenceRows = collectSingleCoreRows(singleCoreReferencePool);
          }}
        }}
        const clusterMeta = collapseDuplicateNeighborRows(neighbors);
        const rawNeighborCount = Number(clusterMeta.raw_neighbor_count || neighbors.length);
        const effectiveClusterCount = Number(clusterMeta.effective_cluster_count || neighbors.length);
        if (Array.isArray(clusterMeta.collapsed_neighbors) && clusterMeta.collapsed_neighbors.length) {{
          neighbors = clusterMeta.collapsed_neighbors.slice();
        }}
        const exactCorePrices = [];
        const exactCoreWeights = [];
        let exactCoreSupportCount = 0;
        if (targetCoreSet.size >= 2) {{
          neighbors.forEach((row) => {{
            const sim = Number(row && row[0]);
            const rec = row && row[1] ? row[1] : null;
            const candTokens = new Set(Array.isArray(rec && rec.tokens) ? rec.tokens : []);
            const candCore = new Set([...coreTokens(candTokens), ...coreTokensFromText(rec && rec.license_text ? rec.license_text : "")]);
            if (candCore.size !== targetCoreSet.size) return;
            if (![...targetCoreSet].every((token) => candCore.has(token))) return;
            const price = num(rec ? rec.price_eok : null);
            if (!Number.isFinite(price) || price <= 0) return;
            exactCoreSupportCount += 1;
            exactCorePrices.push(price);
            exactCoreWeights.push(Math.max(0.2, (Number.isFinite(sim) ? sim : 0) / 45));
          }});
        }}
        let singleCoreSupportCount = 0;
        let singleCoreMedianEok = null;
        let singleCorePlainMedianEok = null;
        let singleCoreDispersionRatio = null;
        if (strictSameCore && singleCoreReferenceRows.length) {{
          const singleCoreCluster = collapseDuplicateNeighborRows(singleCoreReferenceRows);
          const singleCoreRows = Array.isArray(singleCoreCluster.collapsed_neighbors) && singleCoreCluster.collapsed_neighbors.length
            ? singleCoreCluster.collapsed_neighbors.slice()
            : singleCoreReferenceRows.slice();
          const singleCorePrices = [];
          const singleCoreWeights = [];
          singleCoreRows.forEach((row) => {{
            const sim = Number(row && row[0]);
            const rec = row && row[1] ? row[1] : null;
            const price = num(rec ? rec.price_eok : null);
            if (!Number.isFinite(price) || price <= 0) return;
            singleCoreSupportCount += 1;
            singleCorePrices.push(price);
            singleCoreWeights.push(Math.max(0.2, (Number.isFinite(sim) ? sim : 0) / 45));
          }});
          if (singleCorePrices.length) {{
            singleCorePlainMedianEok = plainQuantile(singleCorePrices, 0.50);
            singleCoreMedianEok = weightedQuantile(singleCorePrices, singleCoreWeights, 0.50);
            const singleCoreP90 = weightedQuantile(singleCorePrices, singleCoreWeights, 0.90);
            if (Number.isFinite(singleCoreMedianEok) && Number.isFinite(singleCoreP90) && singleCoreMedianEok > 0) {{
              singleCoreDispersionRatio = singleCoreP90 / Math.max(singleCoreMedianEok, 0.1);
            }}
          }}
        }}
        target.single_core_mode = !!strictSameCore;
        target.single_core_support_count = singleCoreSupportCount;
        target.single_core_plain_median_eok = Number.isFinite(singleCorePlainMedianEok) ? singleCorePlainMedianEok : null;
        target.single_core_median_eok = Number.isFinite(singleCoreMedianEok) ? singleCoreMedianEok : null;
        target.single_core_dispersion_ratio = Number.isFinite(singleCoreDispersionRatio) ? singleCoreDispersionRatio : null;
        let anchorRows = neighbors.slice();
        const anchorTarget = buildStableAnchorTarget(target);
        const anchorThreshold = target.tokens.size ? (targetCoreCount >= 2 ? 22 : 18) : 10;
        let anchorScored = scorePool(anchorTarget, candidates, strictSameCore, anchorThreshold);
        if (!anchorScored.length) {{
          const anchorPool = (target.tokens.size && candidates.length) ? candidates : dataset;
          anchorScored = scorePool(anchorTarget, anchorPool, strictSameCore, Math.max(10, anchorThreshold - 6));
        }}
        if (anchorScored.length) {{
          anchorScored.sort((a, b) => b[0] - a[0]);
          anchorRows = anchorScored.slice(0, Math.max(24, topK * 4));
          const anchorCluster = collapseDuplicateNeighborRows(anchorRows);
          if (Array.isArray(anchorCluster.collapsed_neighbors) && anchorCluster.collapsed_neighbors.length >= 6) {{
            anchorRows = anchorCluster.collapsed_neighbors.slice();
          }}
        }}
        if (anchorRows.length < 6) anchorRows = neighbors.slice();
        const balanceRows = (!balanceExcluded && anchorRows.length) ? anchorRows : neighbors;
        let balanceSlope = 0;
        let neighborBalanceMean = null;
        let neighborBalanceMedian = null;
        let neighborBalanceP25 = null;
        let neighborBalanceP75 = null;
        if (!balanceExcluded && balanceRows.length) {{
          const balanceInfo = inferBalancePassThrough(balanceRows);
          balanceSlope = Number(balanceInfo && balanceInfo.slope);
          const balanceMeanPairs = balanceRows
            .map((row) => {{
              const sim = Number(row && row[0]);
              const rec = row && row[1] ? row[1] : null;
              const b = num(rec ? rec.balance_eok : null);
              if (!Number.isFinite(b) || b < 0) return null;
              return [b, Math.max(0.2, Number.isFinite(sim) ? sim : 1)];
            }})
            .filter((x) => !!x);
          if (balanceMeanPairs.length) {{
            const neighborBalanceValues = balanceMeanPairs.map((x) => Number(x[0])).filter((x) => Number.isFinite(x));
            const neighborBalanceWeights = balanceMeanPairs.map((x) => Number(x[1])).filter((x) => Number.isFinite(x) && x > 0);
            if (neighborBalanceValues.length && neighborBalanceWeights.length === neighborBalanceValues.length) {{
              neighborBalanceMean = weightedMean(neighborBalanceValues, neighborBalanceWeights);
              neighborBalanceMedian = weightedQuantile(neighborBalanceValues, neighborBalanceWeights, 0.50);
              if (neighborBalanceValues.length >= 3) {{
                neighborBalanceP25 = weightedQuantile(neighborBalanceValues, neighborBalanceWeights, 0.25);
                neighborBalanceP75 = weightedQuantile(neighborBalanceValues, neighborBalanceWeights, 0.75);
              }}
            }}
          }}
        }}
        const displayNeighbors = prioritizeDisplayNeighborRows(neighbors, target).slice(0, 12);
        const hotMatchCount = Math.max(
          displayNeighbors.filter((row) => Number(row[0]) >= 90).length,
          neighbors.filter((row) => Number(row[0]) >= 90).length,
        );
        const prices = neighbors.map((x) => Number(x[1].price_eok));
        const sims = neighbors.map((x) => Number(x[0]));
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
        if (useBaseModel) {{
          riskNotes.push("유사 매물가를 영업권(core)과 공제조합 잔액으로 분해해 산정했습니다.");
        }}
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
        if (clusterMeta.duplicate_cluster_adjusted && rawNeighborCount > effectiveClusterCount) {{
          riskNotes.push(`공유 네트워크 중복 매물을 군집화해 근거 ${{rawNeighborCount}}건을 실효 ${{effectiveClusterCount}}건으로 보정했습니다.`);
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
        if (!balanceExcluded && !useBaseModel) {{
          applyRelative("공제조합 잔액", target.balance_eok, num(meta.avg_balance_eok), 0.06, 0.08);
        }} else if (balanceExcluded) {{
          riskNotes.push("전기/정보통신/소방 업종은 공제조합 잔액 별도 정산 관행을 반영해 가격 반영에서 제외했습니다.");
        }}
        if (!balanceExcluded && !useBaseModel) {{
          applyNeighborPercentile("공제조합 잔액", num(target.balance_eok), "balance_eok", 1, 0.04, 0.06, 5);
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
        const neighborWeightedMedian = (rows, field) => {{
          const values = [];
          const weights = [];
          (Array.isArray(rows) ? rows : []).forEach((row) => {{
            const sim = Number(row && row[0]);
            const rec = row && row[1] ? row[1] : null;
            const rv = num(rec ? rec[field] : null);
            if (!Number.isFinite(rv)) return;
            values.push(rv);
            weights.push(Math.max(0.2, (Number.isFinite(sim) ? sim : 0) / 45));
          }});
          if (values.length < 3) return null;
          return weightedQuantile(values, weights, 0.5);
        }};
        const peerSpecialtyMedian = neighborWeightedMedian(anchorRows, "specialty");
        const peerSalesMedian = neighborWeightedMedian(anchorRows, "sales3_eok");
        const anchorInfo = buildFeatureAnchor(target, anchorRows, balanceSlope, balanceExcluded);
        const anchored = applyAnchorGuard(center, low, high, anchorInfo, riskNotes);
        center = anchored.center;
        low = anchored.low;
        high = anchored.high;
        if (anchorInfo && Array.isArray(anchorInfo.notes)) {{
          anchorInfo.notes.forEach((note) => {{
            if (note && riskNotes.indexOf(note) < 0) riskNotes.push(note);
          }});
        }}
        const prePostCenter = center;
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
          const med = Number.isFinite(peerSpecialtyMedian) ? peerSpecialtyMedian : num(meta.median_specialty);
          if (!Number.isFinite(sp) || !Number.isFinite(med) || med <= 0) return 0;
          const ratio = sp / Math.max(med, 0.1);
          if (!Number.isFinite(ratio) || ratio <= 0) return 0;
          const adj = clamp(Math.log(ratio) * 0.060, -0.08, 0.10);
          if (Math.abs(adj) >= 0.008) {{
            riskNotes.push(`시평 레벨 반영: ${{adj >= 0 ? "+" : ""}}${{(adj * 100).toFixed(1)}}%`);
          }}
          return adj;
        }})();
        postFactor += specialtyLevelAdj;
        const salesLevelAdj = (() => {{
          const sales = num(target.sales3_eok);
          const med = Number.isFinite(peerSalesMedian) ? peerSalesMedian : num(meta.median_sales3_eok);
          if (!Number.isFinite(sales) || !Number.isFinite(med) || med <= 0) return 0;
          const ratio = sales / Math.max(med, 0.1);
          if (!Number.isFinite(ratio) || ratio <= 0) return 0;
          const adj = clamp(Math.log(ratio) * 0.085, -0.10, 0.12);
          if (Math.abs(adj) >= 0.008) {{
            riskNotes.push(`실적 레벨 반영: ${{adj >= 0 ? "+" : ""}}${{(adj * 100).toFixed(1)}}%`);
          }}
          return adj;
        }})();
        postFactor += salesLevelAdj;
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
        const specialtyPeerRatio = positiveRatio(target.specialty, peerSpecialtyMedian);
        const salesPeerRatio = positiveRatio(target.sales3_eok, peerSalesMedian);
        let scaleGuardCap = null;
        if (Number.isFinite(specialtyPeerRatio) && Number.isFinite(salesPeerRatio)) {{
          if (specialtyPeerRatio < 0.80 && salesPeerRatio < 0.80) scaleGuardCap = 1.02;
          else if (specialtyPeerRatio < 0.95 && salesPeerRatio < 0.95) scaleGuardCap = 1.06;
        }}
        if (Number.isFinite(scaleGuardCap)) {{
          const cappedCenter = prePostCenter * scaleGuardCap;
          if (center > cappedCenter) {{
            const scale = cappedCenter / Math.max(center, 0.05);
            center = cappedCenter;
            low = Math.max(0.05, low * scale);
            high = Math.max(low, high * scale);
            riskNotes.push("시평·실적 동시 하락 구간 상향 보정 한도 적용");
          }}
        }}
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
        if (!target.split_optional_pricing && (!target.credit_level || !target.admin_history)) {{
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
        const sparseCoreGuarded = applySparseCoreGuard(center, low, high, priceAxis, weightAxis, effectiveClusterCount, target, riskNotes);
        center = sparseCoreGuarded.center;
        low = sparseCoreGuarded.low;
        high = sparseCoreGuarded.high;
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
        const coreCenterBeforeBalance = center;
        let effectiveBalanceRate = null;
        let balanceAddition = 0;
        let balanceModelMode = "none";
        let rawBalanceAddition = 0;
        let targetCenterWithBalance = coreCenterBeforeBalance;
        const balanceInput = num(target.balance_eok);
        if (!balanceExcluded && Number.isFinite(balanceInput) && balanceInput >= 0 && Number.isFinite(balanceSlope)) {{
          const slopeSafe = clamp(balanceSlope, 0.92, 1.08);
          const meanBalance = Number.isFinite(neighborBalanceMean) ? Number(neighborBalanceMean) : 0;
          const medianBalance = Number.isFinite(neighborBalanceMedian) ? Number(neighborBalanceMedian) : meanBalance;
          const balanceIqr = (Number.isFinite(neighborBalanceP25) && Number.isFinite(neighborBalanceP75))
            ? Math.max(0.08, Number(neighborBalanceP75) - Number(neighborBalanceP25))
            : 0.35;
          const balanceDelta = useBaseModel ? balanceInput : (balanceInput - meanBalance);
          const absDelta = Math.abs(balanceDelta);
          const extremeBalanceInput = Number.isFinite(medianBalance) && medianBalance > 0.05 && balanceInput > (medianBalance * 10);
          let damp = 1.0;
          const applyIqrDamp = !(useBaseModel && balanceInput <= 300 && !extremeBalanceInput);
          if (applyIqrDamp && absDelta > balanceIqr * 8.0) damp *= 0.92;
          if (applyIqrDamp && absDelta > balanceIqr * 16.0) damp *= 0.80;
          if (applyIqrDamp && absDelta > balanceIqr * 28.0) damp *= 0.68;
          if (extremeBalanceInput) {{
            damp *= 0.48;
            riskNotes.push("공제조합 잔액이 유사군 대비 과도해 보수적으로 반영했습니다.");
          }}
          if (Number.isFinite(balanceInput) && balanceInput > 300) {{
            damp *= 0.45;
            riskNotes.push("공제조합 잔액 단위 오입력 가능성을 감안해 영향도를 제한했습니다.");
          }}
          effectiveBalanceRate = slopeSafe * damp;
          if (Number.isFinite(balanceInput) && balanceInput <= 300) {{
            effectiveBalanceRate = Math.max(0.92, effectiveBalanceRate);
          }}
          if (useBaseModel) {{
            balanceAddition = balanceInput * effectiveBalanceRate;
            balanceModelMode = "direct_balance_base";
          }} else {{
            targetCenterWithBalance = balanceBaseTargetCenter(coreCenterBeforeBalance, balanceInput, effectiveBalanceRate);
            balanceAddition = targetCenterWithBalance - coreCenterBeforeBalance;
            rawBalanceAddition = balanceAddition;
            balanceModelMode = "balance_base_core_beta";
          }}
          const p90Price = weightedQuantile(priceAxis, weightAxis, 0.90);
          const balanceCap = Number.isFinite(p90Price)
            ? Math.max(1.35, Math.min(p90Price * 1.35, center * 1.28))
            : Math.max(1.35, center * 1.18);
          balanceAddition = clamp(balanceAddition, -Math.max(balanceCap, Math.abs(balanceAddition) * 1.05), Math.max(balanceCap, Math.abs(balanceAddition) * 1.05));
          if (Number.isFinite(balanceAddition) && Math.abs(balanceAddition) > 0.001) {{
            if (balanceModelMode === "balance_base_core_beta") {{
              center = coreCenterBeforeBalance + balanceAddition;
              const targetLowWithBalance = (low * BALANCE_BASE_CORE_BETA) + (Math.max(0, balanceInput) * effectiveBalanceRate * 0.90);
              const targetHighWithBalance = (high * BALANCE_BASE_CORE_BETA) + (Math.max(0, balanceInput) * effectiveBalanceRate * 1.02);
              let scale = 1.0;
              if (Math.abs(rawBalanceAddition) > 1e-6) {{
                scale = balanceAddition / rawBalanceAddition;
              }}
              low = Math.max(0.05, low + ((targetLowWithBalance - low) * scale));
              high = Math.max(low, high + ((targetHighWithBalance - high) * scale));
              riskNotes.push("공제조합 잔액 기준축에 core 가치를 보수 가중해 최종 합산했습니다.");
            }} else {{
              center += balanceAddition;
              low = Math.max(0.05, low + (balanceAddition * 0.90));
              high = Math.max(low, high + (balanceAddition * 1.02));
              riskNotes.push("공제조합 잔액 입력값을 최종 합산 단계에서 반영했습니다.");
            }}
          }}
        }}
        if (neighbors.length <= 2) {{
          const extra = Math.max(center * 0.18, (high - low) * 0.45);
          low = Math.max(0.05, low - (extra * 0.45));
          high = Math.max(low, high + extra);
        riskNotes.push("비슷한 사례 수가 적어 오차 범위를 보수적으로 넓혔습니다.");
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
        if (targetCoreSet.size >= 2) {{
          if (exactCoreSupportCount <= 2 && avgSim < 80) {{
            confidenceScore -= (exactCoreSupportCount <= 1 ? 12 : 10);
            riskNotes.push("동일 복합면허 근거가 희소해 기준가 공개를 보수적으로 판단합니다.");
          }} else if (exactCorePrices.length >= 2) {{
            const exactMid = weightedQuantile(exactCorePrices, exactCoreWeights, 0.50);
            const exactP90 = weightedQuantile(exactCorePrices, exactCoreWeights, 0.90);
            if (Number.isFinite(exactMid) && Number.isFinite(exactP90) && exactMid > 0) {{
              const exactSpreadRatio = exactP90 / Math.max(exactMid, 0.1);
              if (exactSpreadRatio > 1.55 && avgSim < 82) {{
                const penalty = Math.min(16, 6 + ((exactSpreadRatio - 1.55) * 14));
                confidenceScore -= penalty;
                riskNotes.push("동일 복합면허 실거래 분산이 커 기준가 공개를 보수적으로 낮춥니다.");
              }}
            }}
            const exactMidUnweighted = exactCorePrices.length ? calc_quantile(exactCorePrices, 0.50) : null;
            if (Number.isFinite(exactMidUnweighted) && exactMidUnweighted > 0 && exactCoreSupportCount >= 4) {{
              const exactMaxRatio = Math.max(...exactCorePrices) / Math.max(exactMidUnweighted, 0.1);
              if (exactMaxRatio > 1.85 && avgSim < 82) {{
                const penalty = Math.min(14, 5 + ((exactMaxRatio - 1.85) * 20));
                confidenceScore -= penalty;
                riskNotes.push("동일 복합면허 내 고가 outlier가 커 기준가 공개를 한 단계 보수화합니다.");
              }}
            }}
          }}
        }}
        const missingCritical = target.missing_critical.length;
        confidenceScore -= (missingCritical * 7);
        if (!target.has_license_input) confidenceScore -= 10;
        if (target.provided_signals <= 2) confidenceScore -= 8;
        confidenceScore -= (Math.abs(factor - 1.0) * 24);
        confidenceScore -= (Math.abs(postFactor - 1.0) * 18);
        const singleCorePolicy = singleCorePublicationCap(target, center);
        if (singleCorePolicy && Number.isFinite(Number(singleCorePolicy.confidenceCap))) {{
          confidenceScore = Math.min(confidenceScore, Number(singleCorePolicy.confidenceCap));
        }}
        if (singleCorePolicy && compact(singleCorePolicy.reason) && riskNotes.indexOf(compact(singleCorePolicy.reason)) < 0) {{
          riskNotes.push(compact(singleCorePolicy.reason));
        }}
        if (
          targetCoreSet.size >= 2 &&
          useBaseModel &&
          effectiveClusterCount <= 6 &&
          Number.isFinite(specialtyPeerRatio) &&
          Number.isFinite(salesPeerRatio) &&
          specialtyPeerRatio >= 2.2 &&
          salesPeerRatio >= 2.2
        ) {{
          confidenceScore = Math.min(confidenceScore, 66);
          if (riskNotes.indexOf("희소 복합면허 고스케일 입력으로 기준가 공개를 범위형으로 제한합니다.") < 0) {{
            riskNotes.push("희소 복합면허 고스케일 입력으로 기준가 공개를 범위형으로 제한합니다.");
          }}
        }}
        const anchorValue = num(anchorInfo && anchorInfo.anchor);
        if (
          useBaseModel &&
          effectiveClusterCount <= 8 &&
          avgTokenMatch >= 0.70 &&
          Number.isFinite(anchorValue) &&
          anchorValue > 0 &&
          Number.isFinite(coreCenterBeforeBalance) &&
          coreCenterBeforeBalance > 0 &&
          riskNotes.indexOf("입력 스케일 상향 보정 한도 적용") >= 0
        ) {{
          const anchorGapRatio = anchorValue / Math.max(coreCenterBeforeBalance, 0.05);
          if (anchorGapRatio >= 1.80) {{
            confidenceScore = Math.min(confidenceScore, 66);
            if (riskNotes.indexOf("입력 스케일과 유사군 기준가 괴리가 커 기준가 공개를 범위형으로 제한합니다.") < 0) {{
              riskNotes.push("입력 스케일과 유사군 기준가 괴리가 커 기준가 공개를 범위형으로 제한합니다.");
            }}
          }}
        }}
        if (
          targetCoreSet.size >= 2 &&
          useBaseModel &&
          effectiveClusterCount <= 5 &&
          Number.isFinite(num(target.sales3_eok)) &&
          num(target.sales3_eok) > 0 &&
          Number.isFinite(num(target.sales5_eok)) &&
          (num(target.sales5_eok) / Math.max(num(target.sales3_eok), 0.05)) >= 12.0
        ) {{
          confidenceScore = Math.min(confidenceScore, 66);
          if (riskNotes.indexOf("복합면허 저실적·장기실적 편중 구간은 점추정 대신 범위 공개로 제한합니다.") < 0) {{
            riskNotes.push("복합면허 저실적·장기실적 편중 구간은 점추정 대신 범위 공개로 제한합니다.");
          }}
        }}
        confidenceScore = Math.max(0, Math.min(100, confidenceScore));
        const confidence = `${{Math.round(confidenceScore)}}%`;
        let corePricingMode = "";
        if (balanceExcluded) {{
          const fireGuarded = applyFireSingleLicenseGuardedPrior(target, center, low, high, riskNotes);
          if (fireGuarded && fireGuarded.applied) {{
            center = fireGuarded.center;
            low = fireGuarded.low;
            high = fireGuarded.high;
            corePricingMode = compact(fireGuarded.mode);
          }}
        }}
        if (!riskNotes.length) riskNotes.push("강한 영향 항목 입력이 없어 기본 유사 매물 기준으로 계산했습니다.");
        const yoy = buildYoyInsight(target, center, neighbors);
        const evidence = classifyPriceEvidence(neighbors.length, confidenceScore, hotMatchCount);
        const recommendedListings = buildRecommendedListings(target, neighbors, center, low, high, 4);
        return {{
          center,
          low,
          high,
          internalEstimateEok: Number.isFinite(center) ? center : null,
          coreEstimateEok: Number.isFinite(coreCenterBeforeBalance) ? coreCenterBeforeBalance : null,
          baseModelApplied: !!useBaseModel,
          confidence,
          confidenceScore,
          corePricingMode,
          balanceModelMode,
          balancePassThrough: Number.isFinite(effectiveBalanceRate) ? effectiveBalanceRate : (Number.isFinite(balanceSlope) ? balanceSlope : null),
          balanceAdditionEok: Number.isFinite(balanceAddition) ? balanceAddition : null,
          avgSim,
          neighbor_count: neighbors.length,
          raw_neighbor_count: rawNeighborCount,
          effective_cluster_count: effectiveClusterCount,
          display_neighbor_count: displayNeighbors.length,
          duplicate_cluster_adjusted: !!clusterMeta.duplicate_cluster_adjusted,
          neighbors: displayNeighbors,
          recommendedListings,
          hotMatchCount,
          riskNotes,
          yoy,
          priceSourceTier: evidence.tier,
          priceSourceLabel: evidence.label,
          priceSampleCount: evidence.sampleCount,
          priceRangeKind: "AI_ESTIMATED_RANGE",
          priceDisclaimer: "참고용 가격입니다. 실제 거래가는 실사와 협의 조건에 따라 달라질 수 있습니다.",
          target,
        }};
      }};

      const estimateRemote = async (target) => {{
        if (!estimateEndpoint) {{
          return {{ error: "AI 서버 엔드포인트가 설정되지 않았습니다.", target }};
        }}
        const payload = {{
          mode: viewMode,
          license_text: sanitizePlain(target.license_raw || "", 120),
          license_year: target.license_year,
          specialty: target.specialty,
          y23: target.y23,
          y24: target.y24,
          y25: target.y25,
          sales_input_mode: sanitizePlain(target.sales_input_mode || "yearly", 20),
          reorg_mode: sanitizePlain(target.reorg_mode || "", 20),
          sales3_eok: target.sales3_eok,
          sales5_eok: target.sales5_eok,
          balance_eok: target.balance_eok,
          balance_usage_mode: sanitizePlain(target.balance_usage_mode_requested || target.balance_usage_mode || "", 40),
          seller_withdraws_guarantee_loan: !!target.seller_withdraws_guarantee_loan,
          buyer_takes_balance_as_credit: !!target.buyer_takes_balance_as_credit,
          capital_eok: target.capital_eok,
          surplus_eok: target.surplus_eok,
          debt_ratio: target.debt_ratio,
          liq_ratio: target.liq_ratio,
          company_type: sanitizePlain(target.company_type || "", 40),
          credit_level: sanitizePlain(target.credit_level || "", 40),
          admin_history: sanitizePlain(target.admin_history || "", 40),
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
            headers: buildApiHeaders({{ "Content-Type": "application/json" }}),
            body: JSON.stringify(payload),
          }}, 8500);
          if (!res.ok) {{
            throw new Error(`HTTP ${{res.status}}`);
          }}
          const data = await res.json();
          const publicationModeRaw = compact(data.publication_mode || "");
          const publicationLabelRaw = compact(data.publication_label || "");
          const publicationReasonRaw = compact(data.publication_reason || "");
          const publicCenterRaw = num(data.public_center_eok ?? data.estimate_center_eok ?? data.center_eok ?? data.center);
          const publicLowRaw = num(data.public_low_eok ?? data.estimate_low_eok ?? data.low_eok ?? data.low);
          const publicHighRaw = num(data.public_high_eok ?? data.estimate_high_eok ?? data.high_eok ?? data.high);
          let center = publicCenterRaw;
          let low = publicLowRaw;
          let high = publicHighRaw;
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
          const displayNeighbors = prioritizeDisplayNeighborRows(neighbors, target);
          const recommendedListings = normalizeRecommendationRows(data.recommended_listings, target, center, low, high, neighbors);
          const confRaw = num(data.confidence_score ?? data.confidence_percent ?? data.confidence_value);
          const confidenceScore = Number.isFinite(confRaw) ? confRaw : null;
          const confidence = Number.isFinite(confidenceScore)
            ? `${{Math.round(confidenceScore)}}%`
            : (compact(data.confidence || data.confidence_label || "") || "-");
          const riskNotes = Array.isArray(data.risk_notes) && data.risk_notes.length
            ? data.risk_notes.map((x) => compact(x)).filter((x) => !!x)
            : ["AI 서버 결과를 기준으로 산정했습니다."];
          const avgSim = num(data.avg_similarity ?? data.avg_sim) || 0;
          if (publicationModeRaw) {{
            const hotMatchCount = Number(data.hot_match_count || neighbors.filter((x) => Number(x[0]) >= 90).length || 0);
            const yoy = (() => {{
              const prevCenter = num(data.previous_estimate_eok ?? data.yoy_previous_eok ?? data.prev_center_eok);
              const changePctRaw = num(data.yoy_change_pct ?? data.yoy_percent ?? data.prev_change_pct);
              if (Number.isFinite(prevCenter) && prevCenter > 0 && Number.isFinite(publicCenterRaw)) {{
                const currYear = Number(data.current_year || new Date().getFullYear());
                const prevYear = Number(data.previous_year || (currYear > 0 ? currYear - 1 : 0));
                const pct = Number.isFinite(changePctRaw) ? changePctRaw : (((publicCenterRaw / prevCenter) - 1) * 100);
                return {{
                  current_year: currYear,
                  previous_year: prevYear,
                  previous_center: prevCenter,
                  change_pct: pct,
                  basis: compact(data.yoy_basis || "AI 서버 전년 비교"),
                }};
              }}
              return null;
            }})();
            const evidence = classifyPriceEvidence(
              Number(data.effective_cluster_count ?? data.neighbor_count ?? neighbors.length),
              Number.isFinite(confidenceScore) ? confidenceScore : avgSim,
              hotMatchCount,
              compact(data.price_source_tier || ""),
              compact(data.price_source_label || ""),
              num(data.price_sample_count),
            );
            const priceDisclaimer = compact(data.price_disclaimer || "")
              || "참고용 가격입니다. 실제 거래가는 실사와 협의 조건에 따라 달라질 수 있습니다.";
            return applyPublicationPolicy({{
              center: publicCenterRaw,
              low: publicLowRaw,
              high: publicHighRaw,
              internalEstimateEok: num(data.internal_estimate_eok ?? data.internalEstimateEok ?? publicCenterRaw),
              coreEstimateEok: num(data.core_estimate_eok ?? data.coreEstimateEok),
              confidence: confidence,
              confidenceScore: Number.isFinite(confidenceScore) ? confidenceScore : avgSim,
              avgSim,
              balanceModelMode: compact(data.balance_model_mode || ""),
              balancePassThrough: num(data.balance_pass_through ?? data.balancePassThrough),
              balanceAdditionEok: num(data.balance_adjustment_eok ?? data.balanceAdditionEok),
              neighbors: displayNeighbors,
              neighbor_count: Number(data.effective_cluster_count ?? data.neighbor_count ?? neighbors.length),
              raw_neighbor_count: Number(data.raw_neighbor_count ?? data.neighbor_count ?? neighbors.length),
              effective_cluster_count: Number(data.effective_cluster_count ?? data.neighbor_count ?? neighbors.length),
              hotMatchCount,
              riskNotes,
              yoy,
              priceSourceTier: evidence.tier,
              priceSourceLabel: evidence.label,
              priceSampleCount: evidence.sampleCount,
              priceRangeKind: compact(data.price_range_kind || "AI_ESTIMATED_RANGE"),
              priceDisclaimer: priceDisclaimer,
              publication_mode: publicationModeRaw,
              publication_label: publicationLabelRaw,
              publication_reason: publicationReasonRaw,
              public_center_eok: publicCenterRaw,
              public_low_eok: publicLowRaw,
              public_high_eok: publicHighRaw,
              balance_usage_mode_requested: compact(data.balance_usage_mode_requested || target.balance_usage_mode_requested || ""),
              balance_usage_mode: compact(data.balance_usage_mode || target.balance_usage_mode || ""),
              realizable_balance_eok: num(data.realizable_balance_eok),
              estimated_cash_due_eok: num(data.estimated_cash_due_eok),
              estimated_cash_due_low_eok: num(data.estimated_cash_due_low_eok),
              estimated_cash_due_high_eok: num(data.estimated_cash_due_high_eok),
              public_estimated_cash_due_eok: num(data.public_estimated_cash_due_eok),
              public_estimated_cash_due_low_eok: num(data.public_estimated_cash_due_low_eok),
              public_estimated_cash_due_high_eok: num(data.public_estimated_cash_due_high_eok),
              settlement_policy: data.settlement_policy || null,
              settlement_scenarios: Array.isArray(data.settlement_scenarios) ? data.settlement_scenarios : [],
              settlement_breakdown: data.settlement_breakdown || null,
              recommendedListings,
              target,
            }});
          }}
          if (!Number.isFinite(center) || !Number.isFinite(low) || !Number.isFinite(high)) {{
            return {{ error: "AI 서버 응답 형식이 올바르지 않습니다.", target }};
          }}
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
              if (ratios.length >= 4) {{
                const tLo = weightedQuantile(ratios, ratioW, 0.15);
                const tHi = weightedQuantile(ratios, ratioW, 0.85);
                if (Number.isFinite(tLo) && Number.isFinite(tHi) && tHi > tLo) {{
                  const tR = []; const tW = [];
                  ratios.forEach((r, i) => {{ if (r >= tLo && r <= tHi) {{ tR.push(r); tW.push(ratioW[i]); }} }});
                  if (tR.length >= 3) {{ ratios.length = 0; ratioW.length = 0; tR.forEach(r => ratios.push(r)); tW.forEach(w => ratioW.push(w)); }}
                }}
              }}
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
        riskNotes.push("비슷한 사례 수가 적어 오차 범위를 보수적으로 넓혔습니다.");
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
          const evidence = classifyPriceEvidence(
            neighbors.length,
            finalConfidenceScore,
            hotMatchCount,
            compact(data.price_source_tier || ""),
            compact(data.price_source_label || ""),
            num(data.price_sample_count),
          );
          const priceDisclaimer = compact(data.price_disclaimer || "")
            || "참고용 가격입니다. 실제 거래가는 실사와 협의 조건에 따라 달라질 수 있습니다.";
          const priceRangeKind = compact(data.price_range_kind || "AI_ESTIMATED_RANGE");
          const prioritizedNeighbors = prioritizeDisplayNeighborRows(neighbors, target);
          return {{
            center,
            low,
            high,
            internalEstimateEok: num(data.internal_estimate_eok ?? data.internalEstimateEok ?? center),
            coreEstimateEok: num(data.core_estimate_eok ?? data.coreEstimateEok),
            confidence: finalConfidence || confidence,
            confidenceScore: finalConfidenceScore,
            avgSim,
            balanceModelMode: compact(data.balance_model_mode || ""),
            balancePassThrough: num(data.balance_pass_through ?? data.balancePassThrough),
            balanceAdditionEok: num(data.balance_adjustment_eok ?? data.balanceAdditionEok),
            neighbors: prioritizedNeighbors,
            recommendedListings,
            hotMatchCount,
            riskNotes,
            yoy,
            priceSourceTier: evidence.tier,
            priceSourceLabel: evidence.label,
            priceSampleCount: evidence.sampleCount,
            priceRangeKind: priceRangeKind,
            priceDisclaimer: priceDisclaimer,
            balance_usage_mode_requested: compact(data.balance_usage_mode_requested || target.balance_usage_mode_requested || ""),
            balance_usage_mode: compact(data.balance_usage_mode || target.balance_usage_mode || ""),
            realizable_balance_eok: num(data.realizable_balance_eok),
            estimated_cash_due_eok: num(data.estimated_cash_due_eok),
            estimated_cash_due_low_eok: num(data.estimated_cash_due_low_eok),
            estimated_cash_due_high_eok: num(data.estimated_cash_due_high_eok),
            public_estimated_cash_due_eok: num(data.public_estimated_cash_due_eok),
            public_estimated_cash_due_low_eok: num(data.public_estimated_cash_due_low_eok),
            public_estimated_cash_due_high_eok: num(data.public_estimated_cash_due_high_eok),
            settlement_policy: data.settlement_policy || null,
            settlement_scenarios: Array.isArray(data.settlement_scenarios) ? data.settlement_scenarios : [],
            settlement_breakdown: data.settlement_breakdown || null,
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
        const splitOptionalNote = target.split_optional_pricing
          ? "전기/정보통신/소방의 분할/합병은 실적과 자본금 중심으로 계산했습니다."
          : "";
        if (!target.has_any_signal) {{
          return {{ error: "입력된 정보가 없습니다. 면허/업종 또는 숫자 항목 1개 이상 입력해 주세요.", target }};
        }}
        if (target.requires_reorg_mode && !target.reorg_mode) {{
          return {{ error: "전기/정보통신/소방이 포함된 경우 포괄 또는 분할/합병을 먼저 선택해 주세요.", target }};
        }}
        if (estimateEndpoint) {{
          const remoteOut = await estimateRemote(target);
          if (!remoteOut.error) {{
            if (splitOptionalNote) {{
              remoteOut.riskNotes = [splitOptionalNote].concat(Array.isArray(remoteOut.riskNotes) ? remoteOut.riskNotes : []);
            }}
            return buildSettlementOutput(applyPublicationPolicy(remoteOut));
          }}
          if (!dataset.length) return remoteOut;
          const localOut = estimateLocal(target);
          if (!localOut.error) {{
            localOut.riskNotes = [
              "AI 서버 응답 지연으로 로컬 산정 엔진으로 전환했습니다.",
            ].concat(Array.isArray(localOut.riskNotes) ? localOut.riskNotes : []);
            if (splitOptionalNote) {{
              localOut.riskNotes.unshift(splitOptionalNote);
            }}
          }}
          return buildSettlementOutput(applyPublicationPolicy(localOut));
        }}
        if (!dataset.length) {{
          return {{ error: "산정 데이터가 준비되지 않았습니다. 잠시 후 다시 시도해 주세요.", target }};
        }}
        const localOut = estimateLocal(target);
        if (!localOut.error && splitOptionalNote) {{
          localOut.riskNotes = [splitOptionalNote].concat(Array.isArray(localOut.riskNotes) ? localOut.riskNotes : []);
        }}
        return buildSettlementOutput(applyPublicationPolicy(localOut));
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
        const val = (id) => {{
          const node = $(id);
          return node ? node.value : "";
        }};
        const txt = (id) => {{
          const node = $(id);
          return node ? node.textContent : "";
        }};
        const name = sanitizePlain(val("consult-name"), 40);
        const phone = sanitizePhone(val("consult-phone"));
        const email = sanitizeEmail(val("consult-email"));
        const note = sanitizePlain(val("consult-note"), 500);
        const license = sanitizePlain(val("in-license"), 120);
        const center = compact(txt("out-center"));
        const range = compact(txt("out-range"));
        const confidence = compact(txt("out-confidence"));
        const neighbors = compact(txt("out-neighbors"));
        const sourceTier = compact(txt("out-source-tier"));
        const cashDue = compact(txt("out-cash-due"));
        const balanceRealized = compact(txt("out-realizable-balance"));
        const yoyText = compact(txt("out-yoy-compare"));
        const risk = compact(txt("risk-note"));
        const requestedScaleMode = getScaleSearchMode();
        const effectiveScaleMode = compact((lastEstimate && lastEstimate.target && (lastEstimate.target.scale_search_mode || lastEstimate.target.requested_scale_search_mode)) || requestedScaleMode) || "specialty";
        const scaleModeLabelText = scaleSearchModeLabel(effectiveScaleMode);
        const salesMode = compact(val("in-sales-input-mode")) || "yearly";
        const specialtyValue = compact(val("in-specialty"));
        const salesLine = (() => {{
          if (effectiveScaleMode !== "sales") return "미사용";
          if (salesMode === "sales3") return `최근 3년 실적 합계 ${{compact(val("in-sales3-total")) || "-"}}억`;
          if (salesMode === "sales5") return `최근 5년 실적 합계 ${{compact(val("in-sales5-total")) || "-"}}억`;
          return `2023 ${{compact(val("in-y23")) || "-"}}억 · 2024 ${{compact(val("in-y24")) || "-"}}억 · 2025 ${{compact(val("in-y25")) || "-"}}억`;
        }})();
        const specialBalance = !!((lastEstimate && lastEstimate.target && lastEstimate.target.balance_excluded) || isSeparateBalanceGroupToken(license));
        const autoApplied = [];
        if (compact(val("in-balance")) && (($("in-balance") || {{}}).dataset.autofill === "1")) autoApplied.push(`공제잔액 자동입력 ${{compact(val("in-balance"))}}억`);
        if (compact(val("in-capital")) && (($("in-capital") || {{}}).dataset.autofill === "1")) autoApplied.push(`자본금 자동입력 ${{compact(val("in-capital"))}}억`);
        if (compact(val("in-surplus")) && (($("in-surplus") || {{}}).dataset.autofill === "1")) autoApplied.push(`이익잉여금 자동입력 ${{compact(val("in-surplus"))}}억`);
        const optionalAdjustments = [];
        if (compact(val("in-balance-usage-mode")) && compact(val("in-balance-usage-mode")) !== "auto") optionalAdjustments.push("정산 방식 반영");
        if (compact(val("in-license-year"))) optionalAdjustments.push(`면허년도 ${{compact(val("in-license-year"))}}`);
        const companyAdjustmentCount = [
          "in-surplus",
          "in-debt-level",
          "in-liq-level",
          "in-company-type",
          "in-credit-level",
          "in-admin-history",
        ].filter((id) => {{
          const node = $(id);
          const value = compact(node ? node.value : "");
          if (!value || value === "auto") return false;
          if (node && node.dataset && node.dataset.autofill === "1" && node.dataset.manual !== "1") return false;
          return true;
        }}).length;
        if (companyAdjustmentCount > 0) optionalAdjustments.push(`회사 보정 ${{companyAdjustmentCount}}건`);
        const briefParts = [
          "양도양수",
          license || "업종 확인",
          effectiveScaleMode === "specialty" ? `시평 ${{specialtyValue || "-"}}억` : salesLine,
          center && center !== "-" ? `예상 총 거래가 ${{center}}` : "",
          range && range !== "-" ? `범위 ${{range}}` : "",
          cashDue && cashDue !== "-" ? `현금 정산 ${{cashDue}}` : "",
          confidence && confidence !== "-" ? `신뢰 ${{confidence}}` : "",
          neighbors && neighbors !== "-" ? `근거 ${{neighbors}}` : "",
          specialBalance
            ? (balanceRealized && balanceRealized !== "-" ? `별도 공제잔액 ${{balanceRealized}}` : "")
            : (balanceRealized && balanceRealized !== "-" ? `공제 활용 ${{balanceRealized}}` : ""),
          compact(val("in-reorg-mode")) ? `구조 ${{compact(val("in-reorg-mode"))}}` : "",
          optionalAdjustments.length ? `선택 ${{optionalAdjustments.join(", ")}}` : "",
        ].filter(Boolean);
        const brief = briefParts.join(" | ");
        const lines = [
          brandName + " AI 산정 상담 요청",
          "",
          "[서비스 트랙] 양도양수 양도가 산정(인허가 신규등록 사전검토와 별도 운영)",
          `[고객] ${{name || "-"}} / ${{phone || "-"}} / ${{email || "-"}}`,
          `[면허] ${{license || "-"}}`,
          `[검색기준] ${{scaleModeLabelText}}`,
          `[양도 구조] ${{compact(val("in-reorg-mode")) || "-"}}`,
          `[공제조합 정산] ${{specialBalance ? `${{settlementScenarioLabel(val("in-balance-usage-mode")) || "-"}} · 양도가 영향 0` : (balanceUsageModeLabel(val("in-balance-usage-mode")) || "-")}}`,
          `[산정] 기준가 ${{center || "-"}} · 범위 ${{range || "-"}} · 신뢰지수 ${{confidence || "-"}} · 근거 ${{neighbors || "-"}} · 사례 근거 ${{sourceTier || "-"}}`,
          `[정산] 예상 현금 정산액 ${{cashDue || "-"}} · ${{specialBalance ? `별도 공제잔액 ${{balanceRealized || "-"}} (양도가 영향 0)` : `공제 활용분 ${{balanceRealized || "-"}}`}}`,
          `[전년 비교] ${{yoyText || "-"}}`,
          `[핵심 입력] 시평 ${{effectiveScaleMode === "specialty" ? `${{specialtyValue || "-"}}억` : "미사용"}} · 실적 ${{salesLine}}`,
          `[재무 입력] ${{specialBalance ? "별도 공제잔액" : "공제잔액"}} ${{compact(val("in-balance")) || "-"}}억${{specialBalance ? " (양도가 영향 0)" : ""}} · 자본금 ${{compact(val("in-capital")) || "-"}}억 · 이익잉여금 ${{compact(val("in-surplus")) || "-"}}억`,
          `[자동 입력] ${{autoApplied.length ? autoApplied.join(" · ") : "-"}}`,
          `[추가 입력] 회사형태 ${{compact(val("in-company-type")) || "-"}} · 외부신용등급 ${{compact(val("in-credit-level")) || "-"}} · 행정처분이력 ${{compact(val("in-admin-history")) || "-"}}`,
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
          brief: brief,
          name: name,
          phone: phone,
          email: email,
          note: note,
          license: license,
          result_center: center,
          result_range: range,
          result_confidence: confidence,
          result_neighbors: neighbors,
          result_source_tier: sourceTier,
          result_cash_due: cashDue,
          result_realizable_balance: balanceRealized,
          result_yoy: yoyText,
          service_track: YANGDO_SERVICE_TRACK,
          business_domain: YANGDO_BUSINESS_DOMAIN,
          page_mode: YANGDO_PAGE_MODE,
          source_tag: YANGDO_SOURCE_TAG,
          scale_search_mode: effectiveScaleMode,
          reorg_mode: sanitizePlain(val("in-reorg-mode"), 20),
          balance_usage_mode: sanitizePlain(val("in-balance-usage-mode"), 40),
          company_type: sanitizePlain(val("in-company-type"), 40),
          credit_level: sanitizePlain(val("in-credit-level"), 40),
          admin_history: sanitizePlain(val("in-admin-history"), 40),
        }};
      }};

      const syncConsultSummary = () => {{
        const payload = buildConsultPayload();
        const summary = $("consult-summary");
        if (summary) summary.value = payload.body;
        const resultBrief = $("result-brief");
        const resultBriefMeta = $("result-brief-meta");
        const resultBriefCopy = $("btn-copy-brief");
        if (!lastEstimate) {{
          if (resultBrief) resultBrief.value = "";
          if (resultBriefMeta) resultBriefMeta.textContent = "AI 계산 후 대표가 카카오톡이나 내부 메신저로 바로 전달할 한 줄 요약을 자동 생성합니다.";
          if (resultBriefCopy) resultBriefCopy.disabled = true;
          return;
        }}
        if (resultBrief) resultBrief.value = payload.brief || "";
        if (resultBriefMeta) resultBriefMeta.textContent = "복사해서 오픈채팅, 문자, 내부 메신저에 바로 전달할 수 있습니다.";
        if (resultBriefCopy) resultBriefCopy.disabled = !compact(payload.brief);
      }};

      const copyText = async (text) => {{
        const value = String(text || "").trim();
        if (!value) return false;
        if (navigator.clipboard && navigator.clipboard.writeText) {{
          try {{
            await navigator.clipboard.writeText(value);
            return true;
          }} catch (_e) {{}}
        }}
        try {{
          const area = document.createElement("textarea");
          area.value = value;
          area.setAttribute("readonly", "readonly");
          area.style.position = "fixed";
          area.style.top = "-9999px";
          area.style.opacity = "0";
          document.body.appendChild(area);
          area.focus();
          area.select();
          const copied = document.execCommand("copy");
          document.body.removeChild(area);
          return !!copied;
        }} catch (_e) {{
          return false;
        }}
      }};

      const openOpenchatWithSummary = async (payload = null) => {{
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
        const copied = await copyText(text);
        if (copied) alert("요약을 복사했습니다. 오픈채팅창에 붙여넣어 주세요.");
        openChat();
      }};

      const sendUsageLog = (target, out, status = "ok", errorText = "") => {{
        if (!enableUsageLog) return;
        if (!usageEndpoint) return;
        const payload = {{
          source: YANGDO_SOURCE_TAG,
          page_mode: YANGDO_PAGE_MODE,
          source_mode: viewMode,
          service_track: YANGDO_SERVICE_TRACK,
          business_domain: YANGDO_BUSINESS_DOMAIN,
          status: compact(status || "ok"),
          error_text: compact(errorText || ""),
          license_text: compact($("in-license").value),
          input_scale_search_mode: compact(($("in-scale-search-mode") || {{}}).value),
          input_specialty: compact($("in-specialty").value),
          input_sales_mode: compact(($("in-sales-input-mode") || {{}}).value),
          input_reorg_mode: compact(($("in-reorg-mode") || {{}}).value),
          input_balance_usage_mode: compact(($("in-balance-usage-mode") || {{}}).value),
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
          target_scale_search_mode: target ? compact(target.scale_search_mode || target.requested_scale_search_mode || "") : "",
          ok_capital: !!$("ok-capital").checked,
          ok_engineer: !!$("ok-engineer").checked,
          ok_office: !!$("ok-office").checked,
          output_center: out && Number.isFinite(out.center) ? fmtEok(out.center) : "-",
          output_range: out && Number.isFinite(out.low) && Number.isFinite(out.high) ? buildDisplayRange(out.low, out.high).text : "-",
          output_cash_due: out && Number.isFinite(out.public_estimated_cash_due_eok) ? fmtEok(out.public_estimated_cash_due_eok) : "-",
          output_balance_realized: out && Number.isFinite(out.realizable_balance_eok) ? fmtEok(out.realizable_balance_eok) : "-",
          output_confidence: out ? `${{out.confidence || "-"}}` : "-",
          output_neighbors: out && out.neighbors ? `${{out.neighbors.length}}건` : "-",
          output_source_tier: out ? compact(out.priceSourceLabel || out.priceSourceTier || "") : "",
          output_yoy: compact($("out-yoy-compare").textContent),
          missing_critical: target && target.missing_critical ? target.missing_critical.join(",") : "",
          page_url: window.location.href,
          requested_at: new Date().toISOString(),
        }};
        requestWithTimeout(usageEndpoint, {{
          method: "POST",
          headers: buildApiHeaders({{ "Content-Type": "application/json" }}),
          body: JSON.stringify(payload),
        }}, 5000).catch(() => {{}});
      }};

      const sendHotMatchLead = async () => {{
        if (!enableHotMatch) return;
        if (!lastEstimate) return;
        const payload = buildConsultPayload();
        sendUsageLog(lastEstimate.target || null, lastEstimate, "hot_match_click", "");
        if (!consultEndpoint) return;
        if (!payload.name || (!payload.phone && !payload.email)) return;
        try {{
          await requestWithTimeout(consultEndpoint, {{
            method: "POST",
            headers: buildApiHeaders({{ "Content-Type": "application/json" }}),
            body: JSON.stringify({{
              source: `${{sourceTagPrefix || "channel"}}_hot_match`,
              page_mode: YANGDO_PAGE_MODE,
              source_mode: viewMode,
              service_track: YANGDO_SERVICE_TRACK,
              business_domain: YANGDO_BUSINESS_DOMAIN,
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
          head.innerHTML = `<tr><th>${{escapeHtml(brandName || "파트너")}} 매물번호</th><th>now UID</th><th>업종</th><th>기준가(억)</th><th>오차 범위(억)</th><th>유사도</th><th>링크</th></tr>`;
          return 7;
        }}
        head.innerHTML = "<tr><th>매물번호</th><th>업종</th><th>오차 범위(억)</th><th>유사도</th><th>링크</th></tr>";
        return 5;
      }};
      const syncNeighborPanelDisclosure = (force) => {{
        const panel = $("neighbor-panel");
        if (!panel) return;
        if (!force && neighborPanelDisclosureManual) return;
        const shouldOpen = recommendedListingCount <= 1
          ? false
          : (typeof window.matchMedia === "function"
            ? !window.matchMedia("(max-width: 640px)").matches
            : ((window.innerWidth || 0) > 640));
        if (panel.open === shouldOpen) return;
        neighborPanelDisclosureSyncing = true;
        panel.open = shouldOpen;
        window.setTimeout(() => {{
          neighborPanelDisclosureSyncing = false;
        }}, 0);
      }};
      const updateNeighborPanelSummary = (rows) => {{
        const label = $("neighbor-panel-label");
        const summary = $("neighbor-panel-summary");
        const count = Array.isArray(rows) ? rows.length : 0;
        if (label) label.textContent = count > 0 ? `비슷한 사례 표 ${{count}}건 자세히 보기` : "비슷한 사례 표 자세히 보기";
        if (summary) summary.textContent = count === 0
          ? "추천 매물이 아직 없어 사례표를 접어두었습니다. 입력을 조금 보강한 뒤 다시 계산해 보세요."
          : (count === 1
            ? "추천 매물 1건이 먼저 보이도록 사례표는 접어두었습니다."
            : "추천 매물 아래에서 실제 사례표를 펼쳐 차이를 확인하세요.");
      }};

      const syncResultPriorityLayout = (rows) => {{
        const panelBody = document.querySelector("#estimate-result-panel .panel-body");
        const shareWrap = $("result-share-wrap");
        const actionSteps = $("result-action-steps");
        const recommendPanel = $("recommend-panel");
        if (!panelBody || !shareWrap || !actionSteps || !recommendPanel) return;
        const priorityRecommendation = Array.isArray(rows) && rows.length <= 1;
        recommendPanel.classList.toggle("priority-single", priorityRecommendation);
        actionSteps.classList.toggle("compact-followup", priorityRecommendation);
        if (priorityRecommendation) {{
          panelBody.insertBefore(recommendPanel, shareWrap);
          panelBody.insertBefore(actionSteps, shareWrap);
          return;
        }}
        panelBody.insertBefore(shareWrap, actionSteps);
        panelBody.insertBefore(actionSteps, recommendPanel);
      }};

      const renderRecommendPanelGuide = (out) => {{
        const node = $("recommend-panel-guide");
        if (!node) return;
        const safeOut = out && typeof out === "object" ? out : null;
        const guideTarget = safeOut && safeOut.target ? safeOut.target : null;
        const splitOptionalPricing = !!(guideTarget && guideTarget.split_optional_pricing);
        const balanceExcluded = !!(guideTarget && guideTarget.balance_excluded);
        const scaleMode = compact(guideTarget && (guideTarget.scale_search_mode || guideTarget.requested_scale_search_mode));
        const pubMode = compact(safeOut && safeOut.publicationMode);
        const sourceTier = compact(safeOut && (safeOut.priceSourceTier || safeOut.priceSourceLabel));
        const rawCount = safeOut && safeOut.neighbor_count;
        const count = Number.isFinite(Number(rawCount))
          ? Number(rawCount)
          : (Array.isArray(safeOut && safeOut.neighbors) ? safeOut.neighbors.length : 0);
        let text = "";
        if (count === 0) {{
          if (splitOptionalPricing) {{
            text = "추천 후보가 아직 없어 최근 3년 실적과 자본금을 먼저 보강해 주세요.";
          }} else if (scaleMode === "sales") {{
            text = balanceExcluded
              ? "추천 후보가 아직 없어 자본금을 더 정확히 넣어 주세요."
              : "추천 후보가 아직 없어 공제조합 잔액을 더 정확히 넣어 주세요.";
          }} else {{
            text = "추천 후보가 아직 없어 시평을 더 구체적으로 넣어 주세요.";
          }}
        }} else if (pubMode === "consult_only" || sourceTier.indexOf("표본 적음") >= 0 || (count > 0 && count <= 3)) {{
          text = splitOptionalPricing
            ? "표본이 적을 때는 아래 비슷한 사례의 최근 3년 실적과 자본금부터 먼저 보세요."
            : "표본이 적을 때는 아래 비슷한 사례 2~3건의 핵심 조건부터 먼저 보세요.";
        }} else if (pubMode === "range_only") {{
          text = splitOptionalPricing
            ? "범위가 넓을 때는 아래 추천 매물의 최근 3년 실적과 자본금 공통 조건부터 먼저 보세요."
            : "범위가 넓을 때는 아래 추천 매물의 공통 조건을 먼저 보세요.";
        }}
        node.textContent = text;
        node.style.display = text ? "block" : "none";
      }};
      const clearRecommendAutoLoopTimer = () => {{
        if (!recommendAutoLoopTimer) return;
        window.clearTimeout(recommendAutoLoopTimer);
        recommendAutoLoopTimer = 0;
      }};
      const clearRecommendAutoLoop = () => {{
        clearRecommendAutoLoopTimer();
        recommendAutoLoop = null;
      }};
      const recommendAutoLoopFieldId = (actionKind) => {{
        if (actionKind === "specialty") return "in-specialty";
        if (actionKind === "balance") return "in-balance";
        if (actionKind === "capital") return "in-capital";
        return "in-sales3-total";
      }};
      const armRecommendAutoLoop = (actionKind) => {{
        const fieldId = recommendAutoLoopFieldId(actionKind);
        const field = $(fieldId);
        if (!field) return;
        recommendAutoLoop = {{
          actionKind,
          fieldId,
          baseline: compact(field.value),
        }};
      }};
      const scheduleRecommendAutoLoopEstimate = () => {{
        if (!recommendAutoLoop || isEstimating) return;
        clearRecommendAutoLoopTimer();
        recommendAutoLoopTimer = window.setTimeout(() => {{
          if (!recommendAutoLoop || isEstimating) return;
          const state = recommendAutoLoop;
          const field = $(state.fieldId);
          const currentValue = compact(field && field.value);
          if (!currentValue || currentValue === state.baseline) return;
          clearRecommendAutoLoop();
          pendingResultPanelScroll = true;
          const estimateButton = $("btn-estimate");
          if (estimateButton && !estimateButton.disabled) estimateButton.click();
        }}, 900);
      }};
      const maybeRunRecommendAutoLoop = (fieldId) => {{
        if (!recommendAutoLoop || recommendAutoLoop.fieldId !== fieldId) return;
        const field = $(fieldId);
        const currentValue = compact(field && field.value);
        if (!currentValue || currentValue === recommendAutoLoop.baseline) {{
          clearRecommendAutoLoopTimer();
          return;
        }}
        const noteNode = $("recommend-panel-followup-note");
        if (noteNode) {{
          noteNode.textContent = "값이 바뀌면 다시 계산이 자동으로 이어집니다.";
          noteNode.style.display = "block";
        }}
        scheduleRecommendAutoLoopEstimate();
      }};
      const focusRecommendSales3Refinement = () => {{
        const salesModeNode = $("in-sales-input-mode");
        const sales3Input = $("in-sales3-total");
        if (!salesModeNode || !sales3Input) return;
        focusRecommendInputField(1, "yangdoWizardStep2", sales3Input, () => {{
          setScaleSearchMode("sales");
          syncScaleSearchModeUi();
          salesModeNode.dataset.splitManualMode = "1";
          salesModeNode.value = "sales3";
          syncSalesInputModeUi();
        }});
      }};
      const focusRecommendSpecialtyRefinement = () => {{
        const specialtyInput = $("in-specialty");
        if (!specialtyInput) return;
        focusRecommendInputField(1, "yangdoWizardStep2", specialtyInput, () => {{
          setScaleSearchMode("specialty");
          syncScaleSearchModeUi();
        }});
      }};
      const focusRecommendBalanceRefinement = () => {{
        const balanceInput = $("in-balance");
        if (!balanceInput) return;
        focusRecommendInputField(2, "yangdoWizardStep3", balanceInput);
      }};
      const focusRecommendCapitalRefinement = () => {{
        const capitalInput = $("in-capital");
        if (!capitalInput) return;
        focusRecommendInputField(2, "yangdoWizardStep3", capitalInput);
      }};
      const flashRecommendFocusTarget = (inputNode) => {{
        if (!inputNode || !inputNode.classList) return;
        inputNode.classList.remove("recommend-focus-target");
        void inputNode.offsetWidth;
        inputNode.classList.add("recommend-focus-target");
        window.setTimeout(() => {{
          inputNode.classList.remove("recommend-focus-target");
        }}, 1400);
      }};
      const focusRecommendInputField = (stepIndex, stepId, inputNode, beforeFocus = null) => {{
        if (!inputNode) return;
        setYangdoWizardStep(stepIndex, false);
        if (typeof beforeFocus === "function") beforeFocus();
        syncYangdoWizard();
        window.setTimeout(() => {{
          const step = $(stepId);
          if (step && typeof step.scrollIntoView === "function") {{
            step.scrollIntoView({{ behavior: "smooth", block: "start" }});
          }}
          flashRecommendFocusTarget(inputNode);
          if (typeof inputNode.focus === "function") inputNode.focus();
          if (typeof inputNode.select === "function") inputNode.select();
        }}, 80);
      }};
      const buildRecommendPanelFollowupPlan = (out, rowsOrCount) => {{
        const safeOut = out && typeof out === "object" ? out : null;
        const guideTarget = safeOut && safeOut.target ? safeOut.target : null;
        const splitOptionalPricing = !!(guideTarget && guideTarget.split_optional_pricing);
        const balanceExcluded = !!(guideTarget && guideTarget.balance_excluded);
        const scaleMode = compact(guideTarget && (guideTarget.scale_search_mode || guideTarget.requested_scale_search_mode));
        const pubMode = compact(safeOut && safeOut.publicationMode);
        const sourceTier = compact(safeOut && (safeOut.priceSourceTier || safeOut.priceSourceLabel));
        const count = Array.isArray(rowsOrCount) ? rowsOrCount.length : Math.max(0, Number(rowsOrCount) || 0);
        const noRecommendation = count === 0;
        const lowSample = pubMode === "consult_only" || sourceTier.indexOf("표본 적음") >= 0;
        const licenseText = compact(guideTarget && guideTarget.license_text);
        const sectorName = specialBalanceSectorName(licenseText);
        const reorgMode = compact(guideTarget && guideTarget.reorg_mode);
        const isSplitMerge = reorgMode === "분할/합병";
        const actions = [];
        let text = "";
        let note = "";
        const pushAction = (kind, label, reason) => {{
          const cleanKind = compact(kind);
          const cleanLabel = compact(label);
          if (!cleanKind || !cleanLabel || actions.some((item) => item.kind === cleanKind)) return;
          actions.push({{
            kind: cleanKind,
            label: cleanLabel,
            shortLabel: cleanLabel.replace(/^\\d순위\\s*·\\s*/, ""),
            reason: compact(reason),
          }});
        }};
        if (splitOptionalPricing && (lowSample || count <= 1)) {{
          if (noRecommendation && isSplitMerge && sectorName) {{
            const sectorTip = sectorName === "전기"
              ? "전기공사업 분할/합병은 최근 3년 실적과 자본금이 핵심입니다. 두 값을 정확히 입력하면 추천 후보를 다시 찾을 수 있습니다."
              : sectorName === "정보통신"
              ? "정보통신공사업 분할/합병은 최근 3년 실적과 자본금 중심으로 산정합니다. 실적을 먼저 보강해 주세요."
              : "소방시설공사업 분할/합병은 실적과 자본금 중심이며, 잔액 비중 기준이 타 업종보다 높습니다. 실적을 먼저 보강해 주세요.";
            text = sectorTip;
          }} else {{
            text = noRecommendation
              ? "아직 바로 비교할 추천 매물이 없습니다. 최근 3년 실적과 자본금을 더 보강하면 추천 후보를 다시 찾는 데 도움이 됩니다."
              : "최근 3년 실적을 1~2건만 더 보강하면 현재 범위를 더 줄이는 데 도움이 됩니다.";
          }}
          note = noRecommendation
            ? "1순위는 최근 3년 실적, 2순위는 자본금입니다. 두 값만 다시 맞춰도 다음 계산에서 추천 후보가 다시 잡힐 가능성이 큽니다."
            : "1순위는 최근 3년 실적입니다. 범위가 남으면 자본금을 같이 보강해 다음 계산 폭을 더 줄이세요.";
          pushAction("sales3", "1순위 · 최근 3년 실적 보강", "추천 후보를 다시 만드는 핵심 입력입니다.");
          pushAction("capital", "2순위 · 자본금 보강", "실적 보강 후 가격 범위를 한 번 더 줄이는 보조 입력입니다.");
        }} else if (!splitOptionalPricing && (lowSample || noRecommendation) && count <= 2) {{
          if (balanceExcluded) {{
            text = scaleMode === "sales"
              ? (noRecommendation
                ? "아직 바로 비교할 추천 매물이 없습니다. 자본금을 더 정확히 넣으면 추천 후보를 다시 찾는 데 도움이 됩니다."
                : "자본금을 더 정확히 넣으면 현재 범위를 더 빨리 좁힐 수 있습니다.")
              : (noRecommendation
                ? "아직 바로 비교할 추천 매물이 없습니다. 시평을 더 정확히 넣으면 추천 후보를 다시 찾는 데 도움이 됩니다."
                : "시평을 더 정확히 넣으면 현재 범위를 더 빨리 좁힐 수 있습니다.");
            if (scaleMode === "sales") {{
              note = "1순위는 자본금, 2순위는 최근 3년 실적입니다. 두 값을 같이 맞추면 추천 후보를 더 빨리 다시 만들 수 있습니다.";
              pushAction("capital", "1순위 · 자본금 보강", "실적 검색에서 범위를 다시 만드는 핵심 보강값입니다.");
              pushAction("sales3", "2순위 · 최근 3년 실적 보강", "자본금 보강 후 범위를 더 정밀하게 줄이는 보조 입력입니다.");
            }} else {{
              note = "1순위는 시평, 2순위는 자본금입니다. 시평을 먼저 맞춘 뒤 자본금으로 후보 범위를 더 조여 보세요.";
              pushAction("specialty", "1순위 · 시평 보강", "추천 후보를 다시 잡는 핵심 입력입니다.");
              pushAction("capital", "2순위 · 자본금 보강", "시평 보강 후 후보 범위를 더 안정적으로 줄이는 보조 입력입니다.");
            }}
          }} else {{
            text = scaleMode === "sales"
              ? (noRecommendation
                ? "아직 바로 비교할 추천 매물이 없습니다. 공제조합 잔액을 더 정확히 넣으면 추천 후보를 다시 찾는 데 도움이 됩니다."
                : "공제조합 잔액을 더 정확히 넣으면 현재 범위를 더 빨리 좁힐 수 있습니다.")
              : (noRecommendation
                ? "아직 바로 비교할 추천 매물이 없습니다. 시평을 더 정확히 넣으면 추천 후보를 다시 찾는 데 도움이 됩니다."
                : "시평을 더 정확히 넣으면 현재 범위를 더 빨리 좁힐 수 있습니다.");
            if (scaleMode === "sales") {{
              note = "1순위는 공제조합 잔액, 2순위는 자본금입니다. 잔액부터 맞추고 자본금으로 범위를 더 조이면 다음 계산이 빨라집니다.";
              pushAction("balance", "1순위 · 공제조합 잔액 보강", "실적 검색에서 추천 후보를 다시 잡는 핵심 보강값입니다.");
              pushAction("capital", "2순위 · 자본금 보강", "공제조합 잔액 보강 후 후보 범위를 한 번 더 줄이는 보조 입력입니다.");
            }} else {{
              note = "1순위는 시평, 2순위는 공제조합 잔액입니다. 시평으로 먼저 축을 맞추고 공제조합 잔액으로 세부 범위를 줄이세요.";
              pushAction("specialty", "1순위 · 시평 보강", "추천 후보를 다시 잡는 핵심 입력입니다.");
              pushAction("balance", "2순위 · 공제조합 잔액 보강", "시평 보강 후 후보 범위를 더 안정적으로 줄이는 보조 입력입니다.");
            }}
          }}
        }}
        if (noRecommendation && actions.length > 0) {{
          pushAction("market", "시장 전체 매물 확인", "직접 비교할 매물 목록을 시장에서 확인합니다.");
        }}
        return {{ text, note, actions, noRecommendation, lowSample, count }};
      }};
      const renderRecommendPanelFollowup = (out, rows) => {{
        const node = $("recommend-panel-followup");
        const textNode = $("recommend-panel-followup-text");
        const noteNode = $("recommend-panel-followup-note");
        const actionsNode = $("recommend-panel-followup-actions");
        const actionNode = $("recommend-panel-followup-action");
        const secondaryActionNode = $("recommend-panel-followup-secondary-action");
        if (!node || !textNode || !noteNode || !actionsNode || !actionNode || !secondaryActionNode) return;
        const plan = buildRecommendPanelFollowupPlan(out, rows);
        const primaryAction = plan.actions[0] || null;
        const secondaryAction = plan.actions[1] || null;
        const autoLoopNote = primaryAction
          ? `${{plan.note ? `${{plan.note}} ` : ""}}보강 버튼을 누른 뒤 값을 바꾸면 다시 계산이 자동으로 이어집니다.`
          : (plan.note || "");
        textNode.textContent = plan.text || "";
        noteNode.textContent = autoLoopNote;
        noteNode.style.display = autoLoopNote ? "block" : "none";
        node.style.display = plan.text ? "block" : "none";
        actionNode.textContent = primaryAction ? primaryAction.label : "";
        actionNode.style.display = primaryAction ? "inline-flex" : "none";
        actionNode.dataset.focusAction = primaryAction ? primaryAction.kind : "";
        actionNode.dataset.rank = primaryAction ? "1" : "";
        actionNode.title = primaryAction && primaryAction.reason ? primaryAction.reason : "";
        secondaryActionNode.textContent = secondaryAction ? secondaryAction.label : "";
        secondaryActionNode.style.display = secondaryAction ? "inline-flex" : "none";
        secondaryActionNode.dataset.focusAction = secondaryAction ? secondaryAction.kind : "";
        secondaryActionNode.dataset.rank = secondaryAction ? "2" : "";
        secondaryActionNode.title = secondaryAction && secondaryAction.reason ? secondaryAction.reason : "";
        const tertiaryAction = plan.actions[2] || null;
        let tertiaryNode = $("recommend-panel-followup-tertiary-action");
        if (tertiaryAction && !tertiaryNode && actionsNode) {{
          tertiaryNode = document.createElement("button");
          tertiaryNode.type = "button";
          tertiaryNode.id = "recommend-panel-followup-tertiary-action";
          tertiaryNode.className = "followup-action tertiary";
          tertiaryNode.addEventListener("click", () => {{ runRecommendFollowupAction(tertiaryNode); }});
          actionsNode.appendChild(tertiaryNode);
        }}
        if (tertiaryNode) {{
          tertiaryNode.textContent = tertiaryAction ? tertiaryAction.label : "";
          tertiaryNode.style.display = tertiaryAction ? "inline-flex" : "none";
          tertiaryNode.dataset.focusAction = tertiaryAction ? tertiaryAction.kind : "";
          tertiaryNode.dataset.rank = tertiaryAction ? "3" : "";
          tertiaryNode.title = tertiaryAction && tertiaryAction.reason ? tertiaryAction.reason : "";
        }}
        actionsNode.style.display = primaryAction || secondaryAction || tertiaryAction ? "flex" : "none";
        if (!primaryAction && !secondaryAction) clearRecommendAutoLoop();
      }};
      const renderRecommendedListings = (rows, out = null) => {{
        const wrap = $("recommended-listings");
        if (!wrap) return;
        recommendedListingCount = Array.isArray(rows) ? rows.length : 0;
        syncResultPriorityLayout(rows);
        renderRecommendPanelGuide(out);
        renderRecommendPanelFollowup(out, rows);
        if (!Array.isArray(rows) || !rows.length) {{
          const emptyTarget = out && out.target ? out.target : null;
          const emptySplitOptionalPricing = !!(emptyTarget && emptyTarget.split_optional_pricing);
          const emptyBalanceExcluded = !!(emptyTarget && emptyTarget.balance_excluded);
          const emptyScaleMode = compact(emptyTarget && (emptyTarget.scale_search_mode || emptyTarget.requested_scale_search_mode));
          const emptyPlan = buildRecommendPanelFollowupPlan(out, 0);
          const emptyPrimaryAction = emptyPlan.actions[0] || null;
          const emptyPrimaryLabel = emptyPrimaryAction ? emptyPrimaryAction.shortLabel : "1순위 보강";
          const emptyMessage = emptySplitOptionalPricing
            ? "최근 3년 실적과 자본금을 보강한 뒤 다시 계산해 보세요."
            : (emptyScaleMode === "sales"
              ? (emptyBalanceExcluded
                ? "자본금을 보강한 뒤 다시 계산해 보세요."
                : "공제조합 잔액을 보강한 뒤 다시 계산해 보세요.")
              : "시평을 조금 더 구체적으로 넣고 다시 계산해 보세요.");
          wrap.innerHTML = `<div class="small"><strong>추천 후보가 아직 없습니다.</strong> ${{emptyMessage}} 아래 ${{emptyPrimaryLabel}}부터 누르면 해당 입력칸으로 바로 이동합니다.</div>`;
          syncNeighborPanelDisclosure(false);
          return;
        }}
        const currentTarget = out && out.target ? out.target : null;
        const splitOptionalPricing = !!(currentTarget && currentTarget.split_optional_pricing);
        const specialSector = splitOptionalPricing ? specialBalanceSectorName(currentTarget && currentTarget.license_text) : "";
        const chipPriority = splitOptionalPricing
          ? {{
            "3년 실적 우선": 0,
            "실적 유사": 1,
            "자본금 유사": 2,
            "업종 일치": 3,
            "조건 적합": 4,
            "시평 유사": 5,
            "번호대 우선": 6,
          }}
          : {{
            "업종 일치": 1,
            "실적 유사": 2,
            "조건 적합": 3,
            "시평 유사": 4,
            "자본금 유사": 5,
            "번호대 우선": 6,
        }};
        const humanizeRecommendationBadge = (label, precisionTier) => {{
          const src = compact(label);
          const tier = compact(precisionTier);
          if (tier === "high" || src.indexOf("우선") >= 0) return "먼저 볼 후보";
          if (tier === "assist" || src.indexOf("보조") >= 0) return "참고 후보";
          if (tier === "medium" || src.indexOf("유사") >= 0 || src.indexOf("조건") >= 0) return "같이 볼 후보";
          return "같이 볼 후보";
        }};
        const primaryChipLabel = (label) => {{
          if (label === "3년 실적 우선") return "1순위 · 3년 실적 기준";
          if (splitOptionalPricing && label === "실적 유사") return "1순위 · 비슷한 3년 실적";
          if (splitOptionalPricing && label === "자본금 유사") return "1순위 · 비슷한 자본금";
          if (splitOptionalPricing && label === "업종 일치") return "1순위 · 같은 업종";
          if (label === "업종 일치") return "1순위 · 같은 업종";
          if (label === "실적 유사") return "1순위 · 비슷한 실적";
          if (label === "조건 적합") return "1순위 · 현재 조건 적합";
          if (label === "시평 유사") return "1순위 · 비슷한 시평";
          if (label === "자본금 유사") return "1순위 · 비슷한 자본금";
          if (label === "번호대 우선") return "1순위 · 우선 검토 번호대";
          return `1순위 · ${{label}}`;
        }};
        const buildRecommendationOrderNote = (chips) => {{
          const primary = Array.isArray(chips) && chips.length ? compact(chips[0]) : "";
          if (splitOptionalPricing) {{
            const prefix = specialSector ? `${{specialSector}} 분할/합병은` : "분할/합병은";
            if (primary === "조건 적합") return `${{prefix}} 번호대보다 최근 3년 실적·자본금과 현재 입력 조건을 먼저 반영했습니다.`;
            if (primary === "업종 일치") return `${{prefix}} 번호대보다 업종과 최근 3년 실적을 먼저 반영했습니다.`;
            return `${{prefix}} 번호대보다 최근 3년 실적과 자본금을 먼저 반영했습니다.`;
          }}
          if (primary === "번호대 우선") return "비슷한 후보끼리는 7천·6천·5천 번호대를 먼저 보여드립니다.";
          if (primary === "실적 유사") return "번호대보다 최근 실적이 더 비슷한 매물을 먼저 보여드립니다.";
          if (primary === "조건 적합") return "번호대보다 현재 입력 조건에 더 가까운 매물을 먼저 보여드립니다.";
          if (primary === "업종 일치") return "번호대보다 같은 업종 여부를 먼저 반영했습니다.";
          return "번호대보다 업종·실적·조건 적합도를 먼저 반영했습니다.";
        }};
        const humanizeReasonText = (text) => {{
          const src = compact(text);
          if (!src) return "";
          if (src.indexOf("면허 구성") >= 0 || (src.indexOf("면허") >= 0 && src.indexOf("같") >= 0) || (src.indexOf("업종") >= 0 && src.indexOf("같") >= 0)) return "업종이 같습니다.";
          if (src.indexOf("실적") >= 0 && (src.indexOf("비슷") >= 0 || src.indexOf("가깝") >= 0)) return "실적 규모가 비슷합니다.";
          if ((src.indexOf("가격") >= 0 || src.indexOf("범위") >= 0) && (src.indexOf("비슷") >= 0 || src.indexOf("가깝") >= 0)) return "현재 조건 적합도가 높습니다.";
          if (src.indexOf("자본금") >= 0 && (src.indexOf("비슷") >= 0 || src.indexOf("가깝") >= 0)) return "자본금이 비슷합니다.";
          if (src.indexOf("번호대") >= 0 || src.indexOf("7천") >= 0 || src.indexOf("7000") >= 0) return "우선 검토할 번호대 매물입니다.";
          return src;
        }};
        const buildReasonChips = (row) => {{
          const chips = [];
          const pushChip = (text) => {{
            const label = compact(text);
            if (!label || chips.includes(label) || chips.length >= 3) return;
            chips.push(label);
          }};
          if (splitOptionalPricing) pushChip("3년 실적 우선");
          const scanText = (text) => {{
            const src = compact(text);
            if (!src) return;
            if (src.indexOf("업종") >= 0 || src.indexOf("면허") >= 0) pushChip("업종 일치");
            if (src.indexOf("실적") >= 0) pushChip("실적 유사");
            if (src.indexOf("시평") >= 0) pushChip("시평 유사");
            if (src.indexOf("가격") >= 0 || src.indexOf("범위") >= 0) pushChip("조건 적합");
            if (src.indexOf("자본금") >= 0) pushChip("자본금 유사");
            if (src.indexOf("7천") >= 0 || src.indexOf("7000") >= 0 || src.indexOf("번호대") >= 0) pushChip("번호대 우선");
          }};
          const focus = compact(row && row.recommendation_focus);
          const fitSummary = compact(row && row.fit_summary);
          const reasons = Array.isArray(row && row.reasons) ? row.reasons.map((item) => compact(item)).filter((item) => !!item) : [];
          [focus, fitSummary, ...reasons].forEach(scanText);
          if (!chips.length) {{
            reasons.slice(0, 3).forEach((item) => {{
              const shortened = compact(String(item || "").replace(/[.]/g, ""));
              if (shortened) pushChip(shortened.length > 14 ? `${{shortened.slice(0, 14)}}…` : shortened);
            }});
          }}
          return chips.sort((a, b) => {{
            const pa = Number.isFinite(Number(chipPriority[a])) ? Number(chipPriority[a]) : 99;
            const pb = Number.isFinite(Number(chipPriority[b])) ? Number(chipPriority[b]) : 99;
            return pa - pb;
          }}).slice(0, 3);
        }};
        wrap.innerHTML = rows.slice(0, 4).map((row) => {{
          const seoulNo = Number(row && row.seoul_no || 0);
          const licenseText = escapeHtml(compact(row && row.license_text) || "-");
          const badge = escapeHtml(humanizeRecommendationBadge(row && row.recommendation_label, row && row.precision_tier));
          const focusRaw = compact(row && row.recommendation_focus);
          const fitSummaryRaw = compact(row && row.fit_summary);
          const reasonFirst = Array.isArray(row && row.reasons) ? compact(row.reasons[0]) : "";
          const why = escapeHtml(humanizeReasonText(fitSummaryRaw || reasonFirst || focusRaw || "입력한 면허와 현재 조건이 가까운 매물입니다."));
          const reasonChips = buildReasonChips(row);
          const orderNote = escapeHtml(buildRecommendationOrderNote(reasonChips));
          const url = safeUrl(row && row.url, siteMna);
          const precision = compact(row && row.precision_tier);
          const ownerNote = viewMode === "owner"
            ? `<div class="owner-note">추천점수 ${{escapeHtml(String(Math.round((Number(row && row.recommendation_score) || 0) * 10) / 10))}} · 유사도 ${{escapeHtml(String(Math.round((Number(row && row.similarity) || 0) * 10) / 10))}} · 정밀도 ${{escapeHtml(precision || "-")}}</div>`
            : "";
          return `<div class="recommend-card">
            <div class="top">
              <div class="name">매물 ${{seoulNo > 0 ? seoulNo : "-"}} · ${{licenseText}}</div>
              <div class="badge">${{badge}}</div>
            </div>
            <div class="why">${{why}}</div>
            <div class="order-note">${{orderNote}}</div>
            ${{reasonChips.length ? `<div class="reason-chips">${{reasonChips.map((item, idx) => `<span class="reason-chip${{idx === 0 ? " primary" : ""}}">${{escapeHtml(idx === 0 ? primaryChipLabel(item) : item)}}</span>`).join("")}}</div>` : ""}}
            ${{ownerNote}}
            <div class="actions"><a href="${{url}}" target="_blank" rel="noopener">상세 보기</a></div>
          </div>`;
        }}).join("");
      }};

      const renderNeighbors = (rows) => {{
        const body = $("neighbor-body");
        const colCount = renderNeighborHead();
        updateNeighborPanelSummary(rows);
        if (!rows || !rows.length) {{
          body.innerHTML = `<tr><td colspan="${{colCount}}" class='small'>비슷한 사례가 없습니다.</td></tr>`;
          syncNeighborPanelDisclosure(false);
          return;
        }}
        body.innerHTML = rows.slice(0, 10).map(([sim, rec]) => {{
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
        syncNeighborPanelDisclosure(false);
      }};

      const renderActionSteps = (out, targetOverride = null) => {{
        const list = $("recommend-actions");
        const title = $("recommend-actions-title");
        if (!list) return;
        const t = targetOverride || (out && out.target ? out.target : null);
        const compactRecommendation = recommendedListingCount <= 1;
        const zeroRecommendation = recommendedListingCount === 0;
        const followupPlan = buildRecommendPanelFollowupPlan(out, recommendedListingCount);
        const primaryFollowupAction = followupPlan.actions[0] || null;
        const items = [];
        const pushStep = (text) => {{
          const msg = compact(text);
          if (!msg || items.includes(msg)) return;
          items.push(msg);
        }};
        const scaleModeLabelText = scaleSearchModeLabel(t && (t.scale_search_mode || t.requested_scale_search_mode));
        if (!t) {{
          if (title) title.textContent = "지금 하면 좋은 순서 3단계";
          pushStep("면허/업종을 먼저 선택해 통상 매물 기준값을 자동으로 불러옵니다.");
          pushStep("시평 검색 또는 실적 검색 중 한 축만 선택해 핵심 규모 값을 입력합니다.");
          pushStep("결과 요약을 복사하거나 메일로 전달해 내부 검토에 활용합니다.");
          list.innerHTML = items.map((x) => `<li>${{x}}</li>`).join("");
          return;
        }}
        if (title) title.textContent = compactRecommendation
          ? (zeroRecommendation ? "비슷한 사례 찾기 2단계" : "지금 하면 좋은 순서 2단계")
          : "지금 하면 좋은 순서 3단계";
        if (compactRecommendation) {{
          if (zeroRecommendation) {{
            pushStep(primaryFollowupAction
              ? `${{primaryFollowupAction.shortLabel}}부터 눌러 추천 후보를 먼저 만들어 보세요.`
              : "보강 버튼을 눌러 가장 영향이 큰 입력칸으로 바로 돌아가 보세요.");
            if (t.split_optional_pricing) {{
              pushStep("최근 3년 실적과 자본금을 보강한 뒤 다시 계산하면 추천 후보를 다시 찾는 데 도움이 됩니다.");
            }} else if (t.balance_excluded) {{
              pushStep(`${{scaleModeLabelText}} 값과 자본금을 더 정확히 넣어 추천 후보를 먼저 만들어 보세요.`);
            }} else {{
              pushStep(`${{scaleModeLabelText}} 값과 공제조합 잔액을 더 정확히 넣어 추천 후보를 먼저 만들어 보세요.`);
            }}
          }} else if (t.split_optional_pricing) {{
            pushStep("추천 매물 1건의 최근 3년 실적과 자본금을 먼저 비교해 보세요.");
            pushStep("최근 3년 실적을 1~2건만 더 보강해 다시 계산하면 범위를 더 빨리 좁힐 수 있습니다.");
          }} else if (t.balance_excluded) {{
            pushStep("추천 매물 1건의 업종과 핵심 조건을 먼저 비교해 보세요.");
            pushStep(`${{scaleModeLabelText}} 값과 자본금을 더 정확히 넣어 다시 계산하면 범위를 더 빨리 좁힐 수 있습니다.`);
          }} else {{
            pushStep("추천 매물 1건의 업종과 핵심 조건을 먼저 비교해 보세요.");
            pushStep(`${{scaleModeLabelText}} 값과 공제조합 잔액을 더 정확히 넣어 다시 계산하면 범위를 더 빨리 좁힐 수 있습니다.`);
          }}
          list.innerHTML = items.slice(0, 2).map((x) => `<li>${{x}}</li>`).join("");
          return;
        }}
        if (t.requires_reorg_mode && !t.reorg_mode) {{
          pushStep("전기/정보통신/소방은 포괄 또는 분할/합병을 먼저 선택해야 정확히 계산됩니다.");
        }} else if (t.missing_critical && t.missing_critical.length) {{
          pushStep(`현재 선택한 ${{scaleModeLabelText}} 기준에서 핵심 항목(${{t.missing_critical.join(" · ")}})을 추가 입력해 오차를 먼저 줄이세요.`);
        }} else {{
          if (t.split_optional_pricing) pushStep("전기/정보통신/소방의 분할/합병은 실적과 자본금 중심으로 계산합니다. 최근 3년·5년·연도별 중 한 방식만 입력하세요.");
          else if (t.balance_excluded) pushStep("전기·정보통신·소방은 공제조합 잔액이 양도가와 별도이며 가격에는 반영하지 않습니다.");
          else pushStep(`${{scaleModeLabelText}} 값과 공제조합 잔액이 정확할수록 결과 범위가 더 좁아집니다.`);
        }}
        if (t.split_optional_pricing) {{
          pushStep("시평·이익잉여금·외부신용·부채/유동비율은 가격에 넣지 않으니 비교용으로만 확인하세요.");
        }} else if (t.balance_excluded) {{
          pushStep("공제조합 잔액은 참고용으로만 입력하세요. 양도가와 별도 정산이며 가격 계산에는 반영하지 않습니다.");
        }}
        if (out && Number.isFinite(out.confidenceScore)) {{
          if (out.confidenceScore >= 70) {{
            pushStep(t.split_optional_pricing
              ? "아래 추천 매물에서 실적이 가까운 순서대로 검토 우선순위를 먼저 정리해 보세요."
              : "아래 추천 매물부터 확인해 검토 우선순위를 1차로 정리해 보세요.");
          }} else {{
            pushStep(t.split_optional_pricing
              ? "자료 편차가 있으면 최근 실적과 자본금을 더 정확히 넣고 다시 계산해 보세요."
              : (t.balance_excluded
                ? `자료 편차가 있어 범위가 넓습니다. ${{scaleModeLabelText}} 값과 자본금 입력을 보강해 다시 계산해 보세요.`
                : `자료 편차가 있어 범위가 넓습니다. ${{scaleModeLabelText}} 값과 공제조합 잔액을 보강해 다시 계산해 보세요.`));
          }}
        }} else {{
          pushStep(t.split_optional_pricing
            ? "최근 실적과 자본금 입력을 보강하면 범위를 더 좁힐 수 있습니다."
            : (t.balance_excluded
              ? `${{scaleModeLabelText}} 값과 자본금 입력을 보강하면 범위를 더 좁힐 수 있습니다.`
              : `${{scaleModeLabelText}} 값과 공제조합 잔액을 보강하면 범위를 더 좁힐 수 있습니다.`));
        }}
        if (enableConsultWidget || enableHotMatch) {{
          pushStep("상담 접수 또는 리포트 요청으로 현재 계산 결과를 전달해 후속 검토를 진행합니다.");
        }} else {{
          pushStep("결과 요약 복사/메일 전달 버튼으로 현재 계산 결과를 내부 검토 흐름에 공유합니다.");
        }}
        list.innerHTML = items.slice(0, 3).map((x) => `<li>${{x}}</li>`).join("");
      }};

      const buildPublicResultMessage = (out) => {{
        if (!out) return "AI 산정 결과가 준비되지 않았습니다.";
        const safeOut = out && typeof out === "object" ? out : null;
        const lines = [];
        const pushLine = (text) => {{
          const msg = compact(text);
          if (!msg || lines.includes(msg) || lines.length >= 3) return;
          lines.push(msg);
        }};
        const neighborCount = Number.isFinite(Number(safeOut && safeOut.neighbor_count))
          ? Number(safeOut.neighbor_count)
          : (safeOut && safeOut.neighbors ? safeOut.neighbors.length : 0);
        const rawNeighborCount = Number.isFinite(Number(safeOut && safeOut.rawNeighborCount))
          ? Number(safeOut.rawNeighborCount)
          : neighborCount;
        pushLine(rawNeighborCount > neighborCount
          ? `비슷한 매물 ${{neighborCount}}건 기준입니다. 중복 매물은 하나로 묶었습니다.`
          : `비슷한 매물 ${{neighborCount}}건 기준입니다.`);
        const publicationLabel = compact(safeOut && safeOut.publicationLabel);
        const target = safeOut && safeOut.target ? safeOut.target : null;
        const buildConsultOnlyHint = () => {{
          const scaleMode = compact(target && target.scale_search_mode);
          const reorgMode = compact(target && target.reorg_mode);
          if (target && target.split_optional_pricing) {{
            return "비슷한 매물이 아직 적습니다. 양도 구조와 최근 3년 실적을 알려주시면 더 정확해집니다.";
          }}
          if (target && target.balance_excluded) {{
            if (!reorgMode) return "비슷한 매물이 아직 적습니다. 포괄인지 분할/합병인지와 최근 3년 실적을 알려주시면 더 정확해집니다.";
            return scaleMode === "sales"
              ? "비슷한 매물이 아직 적습니다. 최근 3년 실적과 자본금을 더 정확히 넣어주시면 더 정확해집니다."
              : "비슷한 매물이 아직 적습니다. 시평과 자본금을 더 정확히 넣어주시면 더 정확해집니다.";
          }}
          return scaleMode === "sales"
            ? "비슷한 매물이 아직 적습니다. 최근 3년 실적과 공제잔액을 더 정확히 넣어주시면 더 정확해집니다."
            : "비슷한 매물이 아직 적습니다. 시평과 공제잔액을 더 정확히 넣어주시면 더 정확해집니다.";
        }};
        if (target && target.split_optional_pricing) {{
          pushLine("분할/합병은 실적과 자본금 중심으로 계산했습니다.");
        }} else if (target && target.balance_excluded) {{
          pushLine("전기·정보통신·소방은 공제잔액을 가격에 넣지 않았습니다.");
        }} else if (Number.isFinite(out.balanceAdditionEok) && Math.abs(out.balanceAdditionEok) > 0.01) {{
          pushLine("공제잔액까지 반영했습니다.");
        }}
        if (compact(out && out.publicationMode) === "consult_only") {{
          pushLine(buildConsultOnlyHint());
        }} else if (compact(out && out.publicationMode) === "range_only") {{
          pushLine("편차가 커 점추정 대신 범위만 공개합니다.");
        }} else if (Number.isFinite(out.confidenceScore) && out.confidenceScore < 70) {{
          pushLine(target && target.split_optional_pricing
            ? "실적과 자본금을 더 정확히 넣으면 범위를 더 좁힐 수 있습니다."
            : (target && target.balance_excluded
              ? "검색축 값과 자본금을 더 정확히 넣으면 범위를 더 좁힐 수 있습니다."
              : "검색축 값과 공제잔액을 더 정확히 넣으면 범위를 더 좁힐 수 있습니다."));
        }} else {{
          pushLine(Array.isArray(out && out.recommendedListings) && out.recommendedListings.length
            ? "아래 추천 매물부터 보면서 검토 우선순위를 정리해 보세요."
            : "현재 값은 협상 출발선으로 보시면 됩니다.");
        }}
        return lines.map((x) => `• ${{escapeHtml(x)}}`).join("<br>");
      }};
      const summarizePublicationChip = (out) => {{
        const mode = compact(out && (out.publicationMode || out.publication_mode || ""));
        const reason = compact(out && (out.publicationReason || out.publication_reason || ""));
        if (mode === "consult_only") {{
          if (reason.indexOf("면허") >= 0) return "면허부터 확인";
          return "자세히 확인 후 안내";
        }}
        if (mode === "range_only") {{
          if (reason.indexOf("편차") >= 0 || reason.indexOf("분산") >= 0) return "편차가 커 범위만 안내";
          return "범위 먼저 안내";
        }}
        return "기준가 바로 보기";
      }};
      const summarizeSettlementChip = (out) => {{
        const target = out && out.target ? out.target : null;
        const balanceExcluded = !!(target && target.balance_excluded);
        const mode = compact(out && out.balance_usage_mode);
        if (balanceExcluded) {{
          if (mode === "credit_transfer") return "정산 · 공제 1:1 차감";
          if (mode === "loan_withdrawal") return "정산 · 융자 인출 차감";
          return "정산 · 공제잔액 별도";
        }}
        if (mode === "none") return "정산 · 공제 별도 정산";
        if (mode === "credit_transfer") return "정산 · 공제 1:1 차감";
        if (mode === "loan_withdrawal") return "정산 · 융자 인출 차감";
        return "정산 · 총가에 공제 반영";
      }};
      const renderResultReasonChips = (out) => {{
        const node = $("result-reason-chips");
        if (!node) return;
        if (!out || (out && out.error)) {{
          node.style.display = "none";
          node.innerHTML = "";
          return;
        }}
        const chips = [
          {{ cls: "publication", text: summarizePublicationChip(out) }},
          {{ cls: "settlement", text: summarizeSettlementChip(out) }},
        ].filter((row) => compact(row && row.text));
        if (!chips.length) {{
          node.style.display = "none";
          node.innerHTML = "";
          return;
        }}
        node.innerHTML = chips
          .map((row) => `<span class="result-reason-chip ${{escapeHtml(row.cls)}}">${{escapeHtml(row.text)}}</span>`)
          .join("");
        node.style.display = "flex";
      }};
      const renderSettlementPanel = (out) => {{
        const panel = $("settlement-panel");
        const summary = $("settlement-summary");
        const notesNode = $("settlement-notes");
        const scenariosNode = $("settlement-scenarios");
        if (!panel || !summary || !notesNode || !scenariosNode) return;
        if (!out) {{
          panel.style.display = "none";
          scenariosNode.style.display = "none";
          scenariosNode.innerHTML = "";
          return;
        }}
        const target = out && out.target ? out.target : null;
        const balanceExcluded = !!(target && target.balance_excluded);
        const total = num(out.publicCenter ?? out.public_total_transfer_value_eok);
        const cashDue = num(out.public_estimated_cash_due_eok);
        const totalRangeVisible = Number.isFinite(num(out.publicLow)) && Number.isFinite(num(out.publicHigh));
        const cashRangeVisible = Number.isFinite(num(out.public_estimated_cash_due_low_eok)) && Number.isFinite(num(out.public_estimated_cash_due_high_eok));
        const realizableBalance = num(out.realizable_balance_eok);
        const rawBalanceInput = num((target && (target.input_balance_eok ?? target.balance_eok)) ?? out.raw_balance_input_eok ?? out.balance_reference_eok);
        const breakdown = out && out.settlement_breakdown ? out.settlement_breakdown : null;
        const mode = compact(out && out.balance_usage_mode);
        const requestedMode = compact(out && out.balance_usage_mode_requested);
        const modeLabel = balanceExcluded ? "별도 공제잔액 참고" : balanceUsageModeLabel(mode);
        const displayedBalance = balanceExcluded
          ? (Number.isFinite(rawBalanceInput) ? rawBalanceInput : realizableBalance)
          : realizableBalance;
        $("out-settlement-total").textContent = Number.isFinite(total) ? fmtEok(total) : (totalRangeVisible ? "범위 먼저 보기" : "먼저 확인 필요");
        $("out-settlement-balance").textContent = Number.isFinite(displayedBalance)
          ? fmtEok(displayedBalance)
          : "-";
        $("out-settlement-cash").textContent = Number.isFinite(cashDue) ? fmtEok(cashDue) : (cashRangeVisible ? "범위 먼저 보기" : "먼저 확인 필요");
        const equation = (
          balanceExcluded && Number.isFinite(total) && Number.isFinite(displayedBalance) && Number.isFinite(cashDue)
        )
          ? `총 거래가 ${{fmtEok(total)}} · 별도 공제잔액 ${{fmtEok(displayedBalance)}} 참고 · 현금 정산액 ${{fmtEok(cashDue)}}`
          : (
            Number.isFinite(total) && Number.isFinite(realizableBalance) && Number.isFinite(cashDue)
          )
          ? `총 거래가 ${{fmtEok(total)}} - 공제 ${{fmtEok(realizableBalance)}} = 현금 정산액 ${{fmtEok(cashDue)}}`
          : (balanceExcluded
            ? "별도 공제잔액 참고값과 현금 정산액을 함께 확인합니다."
            : "총 거래가와 공제 활용분을 분리해 현금 정산액을 해석합니다.");
        summary.textContent = `${{modeLabel}} · ${{equation}}`;
        const noteItems = [];
        const policy = out && out.settlement_policy ? out.settlement_policy : null;
        if (policy && compact(policy.summary)) noteItems.push(compact(policy.summary));
        const showAutoDecision = balanceExcluded && (!requestedMode || requestedMode === "auto");
        if (showAutoDecision && policy && compact(policy.auto_decision_reason) && compact(policy.auto_decision_reason) !== compact(policy.summary)) {{
          noteItems.push(compact(policy.auto_decision_reason));
        }}
        if (showAutoDecision && policy) {{
          const thresholdBits = [];
          const minBalance = num(policy.min_auto_balance_eok);
          const minShare = num(policy.min_auto_balance_share);
          if (Number.isFinite(minBalance) && minBalance > 0) thresholdBits.push(`잔액 ${{fmtEok(minBalance)}} 이상`);
          if (Number.isFinite(minShare) && minShare > 0) thresholdBits.push(`총 거래가 대비 ${{(minShare * 100).toFixed(2)}}% 초과`);
          if (thresholdBits.length) {{
            noteItems.push(`auto 기준: ${{thresholdBits.join(" / ")}}`);
          }}
        }}
        if (breakdown && Array.isArray(breakdown.notes)) {{
          breakdown.notes.forEach((item) => {{
            const txt = compact(item);
            if (txt) noteItems.push(txt);
          }});
        }}
        if (!balanceExcluded && Number.isFinite(out.public_estimated_cash_due_low_eok) && Number.isFinite(out.public_estimated_cash_due_high_eok)) {{
          noteItems.push(`현금 범위 ${{buildDisplayRange(out.public_estimated_cash_due_low_eok, out.public_estimated_cash_due_high_eok).text}}`);
        }}
        const dedupedNoteItems = [];
        const seenNoteItems = new Set();
        noteItems.forEach((item) => {{
          const txt = compact(item);
          if (!txt || seenNoteItems.has(txt)) return;
          seenNoteItems.add(txt);
          dedupedNoteItems.push(txt);
        }});
        const displayNoteItems = dedupedNoteItems.slice(0, 3);
        notesNode.innerHTML = dedupedNoteItems.length
          ? displayNoteItems.map((item) => `<li>${{escapeHtml(item)}}</li>`).join("")
          : `<li>${{escapeHtml(balanceExcluded ? "공제 정산 기준으로 현금액을 봅니다." : "총가와 공제 활용분을 나눠 봅니다.")}}</li>`;
        const scenarios = Array.isArray(out && out.settlement_scenarios) ? out.settlement_scenarios : [];
        if (scenarios.length >= 2) {{
          scenariosNode.innerHTML = scenarios.map((row) => {{
            const label = compact(row && row.label) || balanceUsageModeLabel(row && row.input_mode);
            const badge = row && row.is_selected
              ? "현재 적용"
              : ((row && row.is_recommended) ? "기본값" : "");
            const cashText = Number.isFinite(num(row && (row.public_estimated_cash_due_eok ?? row.estimated_cash_due_eok)))
              ? fmtEok(num(row && (row.public_estimated_cash_due_eok ?? row.estimated_cash_due_eok)))
              : "먼저 확인 필요";
            const balanceText = Number.isFinite(num(row && row.realizable_balance_eok))
              ? fmtEok(num(row && row.realizable_balance_eok))
              : "-";
            const rangeText = (Number.isFinite(num(row && row.public_estimated_cash_due_low_eok)) && Number.isFinite(num(row && row.public_estimated_cash_due_high_eok)))
              ? buildDisplayRange(num(row.public_estimated_cash_due_low_eok), num(row.public_estimated_cash_due_high_eok)).text
              : "";
            const subText = compact((row && row.resolved_mode_label) || "");
            return `<div class="settlement-scenario${{row && row.is_selected ? " is-selected" : ""}}">
              <div class="head">
                <span class="name">${{escapeHtml(label)}}</span>
                ${{badge ? `<span class="badge">${{escapeHtml(badge)}}</span>` : ""}}
              </div>
              <div class="metric"><span class="k">예상 현금 정산액</span><span class="v">${{escapeHtml(cashText)}}</span></div>
              <div class="metric"><span class="k">공제 활용분</span><span class="v">${{escapeHtml(balanceText)}}</span></div>
              ${{rangeText ? `<div class="sub">현금 정산 범위 ${{escapeHtml(rangeText)}}</div>` : ""}}
              ${{subText ? `<div class="sub">${{escapeHtml(subText)}}</div>` : ""}}
            </div>`;
          }}).join("");
          scenariosNode.style.display = "grid";
        }} else {{
          scenariosNode.style.display = "none";
          scenariosNode.innerHTML = "";
        }}
        panel.style.display = "block";
      }};

      const updateHotMatchCta = (out) => {{
        const wrap = $("hot-match-cta");
        const msg = $("hot-match-msg");
        if (!wrap || !msg || !out) return;
        if (!enableHotMatch) {{
          wrap.style.display = "none";
          return;
        }}
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
      const syncResultShareActions = (hasResult) => {{
        const wrap = $("result-share-wrap");
        const note = $("result-share-note");
        if (!wrap || !note) return;
        const ready = !!hasResult;
        wrap.classList.toggle("ready", ready);
        note.textContent = ready
          ? "계산 결과를 복사하거나 오픈채팅으로 바로 전달할 수 있습니다."
          : "AI 계산 후 결과 전달 버튼이 열립니다. 먼저 핵심 입력을 완료하고 계산을 실행해 주세요.";
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
          const total = Number(meta.all_record_count || 0);
          const train = Number(meta.train_count || 0);
          const excluded = Math.max(0, total - train);
          let msg = `전체 ${{total.toLocaleString()}}건 중 가격이 숫자로 확인된 ${{train.toLocaleString()}}건만 계산 기준으로 사용합니다.`;
          if (excluded > 0) msg += ` 협의·비공개·오입력 ${{excluded.toLocaleString()}}건은 제외됩니다.`;
          msg += ` 갱신시각 ${{String(meta.generated_at || "-")}}`;
          qualityBox.textContent = msg;
        }}
      }};

      const syncSalesInputModeUi = () => {{
        const modeNode = $("in-sales-input-mode");
        const mode = compact(modeNode ? modeNode.value : "") || "yearly";
        const scaleMode = getScaleSearchMode();
        const disable = (id, disabled) => {{
          const node = $(id);
          if (!node) return;
          node.disabled = !!disabled;
          node.style.background = disabled ? "var(--smna-disabled-bg)" : "";
          node.style.opacity = disabled ? "0.78" : "";
        }};
        const toggleGroup = (id, visible) => {{
          const node = $(id);
          if (!node) return;
          node.style.display = visible ? "" : "none";
        }};
        const salesModeDisabled = scaleMode !== "sales";
        if (salesModeDisabled) {{
          ["in-y23", "in-y24", "in-y25", "in-sales3-total", "in-sales5-total", "in-sales-input-mode"].forEach((id) => disable(id, true));
          ["sales-yearly-group", "sales-yearly-group-2", "sales-yearly-group-3", "sales-total-group", "sales-total-group-2"].forEach((id) => toggleGroup(id, true));
          return;
        }}
        disable("in-sales-input-mode", false);
        if (mode === "yearly") {{
          disable("in-y23", false);
          disable("in-y24", false);
          disable("in-y25", false);
          disable("in-sales3-total", true);
          disable("in-sales5-total", true);
          toggleGroup("sales-yearly-group", true);
          toggleGroup("sales-yearly-group-2", true);
          toggleGroup("sales-yearly-group-3", true);
          toggleGroup("sales-total-group", false);
          toggleGroup("sales-total-group-2", false);
        }} else if (mode === "sales3") {{
          disable("in-y23", true);
          disable("in-y24", true);
          disable("in-y25", true);
          disable("in-sales3-total", false);
          disable("in-sales5-total", true);
          toggleGroup("sales-yearly-group", false);
          toggleGroup("sales-yearly-group-2", false);
          toggleGroup("sales-yearly-group-3", false);
          toggleGroup("sales-total-group", true);
          toggleGroup("sales-total-group-2", false);
        }} else {{
          disable("in-y23", true);
          disable("in-y24", true);
          disable("in-y25", true);
          disable("in-sales3-total", true);
          disable("in-sales5-total", false);
          toggleGroup("sales-yearly-group", false);
          toggleGroup("sales-yearly-group-2", false);
          toggleGroup("sales-yearly-group-3", false);
          toggleGroup("sales-total-group", false);
          toggleGroup("sales-total-group-2", true);
        }}
      }};
      const syncSeparateBalanceUi = () => {{
        const licenseRaw = compact((($("in-license") || {{}}).value));
        const specialBalance = isSeparateBalanceGroupToken(licenseRaw);
        const labelNode = $("balance-label-text");
        const pillNode = $("balance-impact-pill");
        const balanceInputNode = $("in-balance");
        const usageNode = $("in-balance-usage-mode");
        const usageNote = $("balance-usage-note");
        const resultLabel = $("out-balance-label");
        const settlementLabel = $("out-settlement-balance-label");
        if (labelNode) labelNode.textContent = specialBalance ? "공제조합 잔액(억, 별도 참고)" : "공제조합 잔액(억)";
        if (pillNode) pillNode.textContent = specialBalance ? "별도 정산 · 가격 영향 0" : "일반 업종 가격 반영";
        if (balanceInputNode) balanceInputNode.placeholder = specialBalance ? "참고용 입력(가격 영향 0)" : "미입력 시 업종 기준 자동 적용";
        if (usageNode) {{
          if (!usageNode.dataset.defaultOptions) {{
            usageNode.dataset.defaultOptions = usageNode.innerHTML;
          }}
          const previousUsageValue = compact(usageNode.value);
          usageNode.innerHTML = usageNode.dataset.defaultOptions || usageNode.innerHTML;
          usageNode.disabled = false;
          if (
            previousUsageValue
            && Array.from(usageNode.options || []).some((opt) => compact(opt && opt.value) === previousUsageValue)
          ) {{
            usageNode.value = previousUsageValue;
          }}
          if (!usageNode.value) usageNode.value = "auto";
          delete usageNode.dataset.specialLocked;
        }}
        if (usageNote) usageNote.textContent = specialBalance
          ? "전기·정보통신·소방은 공제조합 잔액을 양도가에 넣지 않고, 아래 정산 시나리오로 현금 정산액만 비교합니다."
          : "일반 업종은 공제조합 잔액을 총 거래가에 반영하거나 별도 정산 구조로 해석할 수 있습니다.";
        if (resultLabel) resultLabel.textContent = specialBalance ? "별도 공제잔액 참고값" : "공제 활용분";
        if (settlementLabel) settlementLabel.textContent = specialBalance ? "별도 공제잔액" : "공제 활용분";
      }};
      const focusSplitSales3InputIfReady = () => {{
        const salesModeNode = $("in-sales-input-mode");
        const sales3Input = $("in-sales3-total");
        if (!salesModeNode || !sales3Input) return;
        if (salesModeNode.dataset.splitAutoSelected !== "1" || salesModeNode.dataset.splitAutoFocusDone === "1") return;
        if (sales3Input.disabled || compact(sales3Input.value)) return;
        const active = document.activeElement;
        const activeId = compact(active && active.id);
        const activeTag = String((active && active.tagName) || "").toLowerCase();
        const typingNow = activeTag === "textarea"
          || (activeTag === "input" && activeId !== "in-sales3-total")
          || (activeTag === "select" && activeId !== "in-reorg-mode" && activeId !== "in-sales-input-mode");
        if (typingNow) return;
        salesModeNode.dataset.splitAutoFocusDone = "1";
        window.setTimeout(() => {{
          if (salesModeNode.dataset.splitAutoSelected !== "1") return;
          if (sales3Input.disabled || compact(sales3Input.value)) return;
          const currentActive = document.activeElement;
          const currentId = compact(currentActive && currentActive.id);
          const currentTag = String((currentActive && currentActive.tagName) || "").toLowerCase();
          const typingLater = currentTag === "textarea"
            || (currentTag === "input" && currentId !== "in-sales3-total")
            || (currentTag === "select" && currentId !== "in-reorg-mode" && currentId !== "in-sales-input-mode");
          if (typingLater) {{
            delete salesModeNode.dataset.splitAutoFocusDone;
            return;
          }}
          if (typeof sales3Input.focus === "function") sales3Input.focus();
          if (typeof sales3Input.select === "function") sales3Input.select();
        }}, 0);
      }};
      const syncSplitOptionalPricingUi = () => {{
        const licenseRaw = compact((($("in-license") || {{}}).value));
        const reorgMode = compact((($("in-reorg-mode") || {{}}).value));
        const splitOptionalPricing = isSplitOptionalPricingProfile({{
          license_raw: licenseRaw,
          raw_license_key: normalizeLicenseKey(licenseRaw),
          tokens: licenseTokenSet(licenseRaw),
        }}, reorgMode);
        const scaleModeNode = $("in-scale-search-mode");
        const salesModeNode = $("in-sales-input-mode");
        const specialtyBtn = document.querySelector('#seoulmna-yangdo-calculator .scale-mode-btn[data-scale-mode="specialty"]');
        const specialtyInput = $("in-specialty");
        const specialtyNote = $("specialty-search-note");
        const scaleSwitchNote = $("scale-mode-switch-note");
        const salesSearchNote = $("sales-search-note");
        const toggleDisabledField = (id, disabled) => {{
          const node = $(id);
          if (!node) return;
          if (node.dataset.defaultPlaceholder === undefined) {{
            node.dataset.defaultPlaceholder = node.getAttribute("placeholder") || "";
          }}
          node.disabled = !!disabled;
          node.style.background = disabled ? "var(--smna-disabled-bg)" : "";
          node.style.opacity = disabled ? "0.78" : "";
          if (disabled) {{
            node.dataset.splitLocked = "1";
          }} else {{
            delete node.dataset.splitLocked;
          }}
        }};
        if (splitOptionalPricing) {{
          if (scaleModeNode && scaleModeNode.dataset.splitForced !== "1") {{
            scaleModeNode.dataset.splitForced = "1";
            scaleModeNode.dataset.previousScaleMode = getScaleSearchMode();
          }}
          let autoSales3Applied = false;
          if (salesModeNode) {{
            const currentSalesMode = compact(salesModeNode.value) || "yearly";
            if (salesModeNode.dataset.splitPrepared !== "1") {{
              salesModeNode.dataset.splitPrepared = "1";
              salesModeNode.dataset.previousMode = currentSalesMode;
            }}
            if (salesModeNode.dataset.splitManualMode !== "1" && (currentSalesMode === "" || currentSalesMode === "yearly")) {{
              salesModeNode.dataset.autoApplying = "1";
              salesModeNode.value = "sales3";
              delete salesModeNode.dataset.autoApplying;
              salesModeNode.dataset.splitAutoSelected = "1";
              autoSales3Applied = true;
            }}
          }}
          setScaleSearchMode("sales");
          syncScaleSearchModeUi();
          if (specialtyBtn) specialtyBtn.disabled = true;
          toggleDisabledField("in-specialty", true);
          toggleDisabledField("in-surplus", true);
          toggleDisabledField("in-debt-level", true);
          toggleDisabledField("in-liq-level", true);
          toggleDisabledField("in-credit-level", true);
          if (specialtyInput) specialtyInput.setAttribute("placeholder", "분할/합병에서는 실적 기준 사용");
          if (specialtyNote) specialtyNote.textContent = "전기·정보통신·소방의 분할/합병은 시평을 쓰지 않고 실적 기준으로 계산합니다.";
          if (scaleSwitchNote) scaleSwitchNote.textContent = "전기·정보통신·소방의 분할/합병은 실적 검색으로 자동 전환됩니다.";
          if (salesSearchNote) salesSearchNote.textContent = autoSales3Applied
            ? "분할/합병은 최근 3년 실적 합계를 먼저 추천해 자동 선택했습니다. 한 칸만 입력하면 됩니다."
            : "분할/합병은 최근 3년 실적 합계를 가장 빠른 기본값으로 권장합니다. 필요하면 연도별이나 5년 합계로 바꿀 수 있습니다.";
          if (autoSales3Applied) focusSplitSales3InputIfReady();
        }} else {{
          if (specialtyBtn) specialtyBtn.disabled = false;
          toggleDisabledField("in-specialty", false);
          toggleDisabledField("in-surplus", false);
          toggleDisabledField("in-debt-level", false);
          toggleDisabledField("in-liq-level", false);
          toggleDisabledField("in-credit-level", false);
          if (specialtyInput) specialtyInput.setAttribute("placeholder", specialtyInput.dataset.defaultPlaceholder || "예: 32");
          if (specialtyNote) specialtyNote.textContent = "시평 기준으로 먼저 찾고 싶을 때 씁니다.";
          if (scaleSwitchNote) scaleSwitchNote.textContent = "동시에 두 축을 강하게 넣어 값이 튀는 문제를 줄이기 위해 한 번에 한 축만 주 검색 기준으로 씁니다.";
          if (salesSearchNote) salesSearchNote.textContent = "선택한 방식 한 개만 채우면 됩니다. 다른 실적 칸은 참조용으로만 유지됩니다.";
          if (salesModeNode && salesModeNode.dataset.splitPrepared === "1") {{
            if (salesModeNode.dataset.splitAutoSelected === "1") {{
              salesModeNode.dataset.autoApplying = "1";
              salesModeNode.value = compact(salesModeNode.dataset.previousMode) || "yearly";
              delete salesModeNode.dataset.autoApplying;
            }}
            delete salesModeNode.dataset.splitPrepared;
            delete salesModeNode.dataset.previousMode;
            delete salesModeNode.dataset.splitAutoSelected;
            delete salesModeNode.dataset.splitAutoFocusDone;
            delete salesModeNode.dataset.splitManualMode;
          }}
          if (scaleModeNode && scaleModeNode.dataset.splitForced === "1") {{
            const previousMode = compact(scaleModeNode.dataset.previousScaleMode) || "specialty";
            setScaleSearchMode(previousMode);
            syncScaleSearchModeUi();
            delete scaleModeNode.dataset.splitForced;
            delete scaleModeNode.dataset.previousScaleMode;
          }}
        }}
      }};
      const syncReorgQuickChoices = () => {{
        const licenseRaw = compact((($("in-license") || {{}}).value));
        const reorgMode = compact((($("in-reorg-mode") || {{}}).value));
        const needs = requiresReorgSelectionByLicense(licenseRaw);
        document.querySelectorAll("[data-reorg-choice]").forEach((button) => {{
          const value = compact(button.getAttribute("data-reorg-choice"));
          const isActive = !!value && value === reorgMode;
          button.classList.toggle("is-active", isActive);
          button.classList.toggle("is-required", !!needs && !reorgMode);
          button.setAttribute("aria-pressed", isActive ? "true" : "false");
        }});
      }};
      const syncReorgCompareGuide = () => {{
        const licenseRaw = compact((($("in-license") || {{}}).value));
        const reorgMode = compact((($("in-reorg-mode") || {{}}).value));
        const needs = requiresReorgSelectionByLicense(licenseRaw);
        const sectorName = specialBalanceSectorName(licenseRaw) || "";
        const compareNote = $("reorg-compare-note");
        const compareCopy = {{
          "포괄": {{
            eyebrow: "포괄 기준",
            title: "시평·재무 보정 포함",
            desc: "시평, 외부신용, 부채/유동비율, 이익잉여금까지 함께 반영하는 일반 구조입니다.",
            meta: needs ? `${{sectorName || "특수 업종"}}도 포괄 구조와 비교해 판단합니다.` : "일반 업종 기본 구조",
          }},
          "분할/합병": {{
            eyebrow: needs ? "구조 필수" : "분할/합병 기준",
            title: "실적·자본금 중심",
            desc: needs
              ? `${{sectorName || "특수"}} 계열은 시평과 재무 보정을 빼고 실적·자본금 중심으로 다시 계산합니다.`
              : "구조에 따라 실적과 자본금 중심 비교가 필요한 경우에 사용합니다.",
            meta: needs
              ? "시평·외부신용·부채/유동비율·이익잉여금 제외"
              : "특수 업종이나 재편 거래 비교용",
          }},
        }};
        document.querySelectorAll("[data-reorg-compare]").forEach((card) => {{
          const key = compact(card.getAttribute("data-reorg-compare"));
          const copy = compareCopy[key];
          if (!copy) return;
          const eyebrow = card.querySelector(".eyebrow");
          const title = card.querySelector(".title");
          const desc = card.querySelector(".desc");
          const meta = card.querySelector(".meta");
          if (eyebrow) eyebrow.textContent = copy.eyebrow;
          if (title) title.textContent = copy.title;
          if (desc) desc.textContent = copy.desc;
          if (meta) meta.textContent = copy.meta;
          card.classList.toggle("is-active", !!key && key === reorgMode);
          card.classList.toggle("is-required", !!needs && !reorgMode);
        }});
        if (!compareNote) return;
        if (!licenseRaw) {{
          compareNote.textContent = "업종을 고르면 구조별 계산 차이를 바로 비교합니다.";
          return;
        }}
        if (!needs) {{
          compareNote.textContent = "일반 업종은 포괄 구조가 기본값이지만, 재편 거래면 분할/합병 기준도 같이 비교해볼 수 있습니다.";
          return;
        }}
        if (!reorgMode) {{
          compareNote.textContent = `${{sectorName || "전기·정보통신·소방"}} 계열은 구조 선택에 따라 계산 축이 크게 달라집니다. 포괄과 분할/합병 중 하나를 먼저 선택하세요.`;
          return;
        }}
        compareNote.textContent = reorgMode === "분할/합병"
          ? `${{sectorName || "특수"}} 계열은 분할/합병 선택 시 실적·자본금 중심으로 계산하고, 공제조합 잔액은 별도 정산 비교로 봅니다.`
          : `${{sectorName || "특수"}} 계열도 포괄 구조를 선택하면 시평과 재무 보정을 함께 보되, 공제조합 잔액은 가격과 별도로 정산합니다.`;
      }};
      const syncReorgModeRequirement = () => {{
        syncSeparateBalanceUi();
        syncSplitOptionalPricingUi();
        const wrap = $("reorg-mode-wrap");
        const note = $("reorg-mode-note");
        const advanced = $("advanced-inputs");
        const licenseNode = $("in-license");
        const reorgNode = $("in-reorg-mode");
        const licenseRaw = compact(licenseNode ? licenseNode.value : "");
        const reorgMode = compact(reorgNode ? reorgNode.value : "");
        const needs = requiresReorgSelectionByLicense(licenseRaw);
        syncDraftRestoreNote();
        syncReorgQuickChoices();
        syncReorgCompareGuide();
        if (wrap) wrap.classList.toggle("required-field", !!needs && !reorgMode);
        if (needs && advanced) advanced.open = true;
        if (!note) return;
        if (!needs) {{
          note.style.display = "none";
          note.textContent = "";
          return;
        }}
        note.style.display = "block";
        if (!reorgMode) {{
          note.textContent = "전기/정보통신/소방이 포함되어 포괄 또는 분할/합병 선택이 필요합니다.";
          return;
        }}
        if (reorgMode === "분할/합병") {{
          const sectorName = specialBalanceSectorName(licenseRaw) || "";
          const SECTOR_SPLIT_NOTES = {{
            "전기": " 전기공사업은 실적과 자본금 중심으로 산정하며, 공제조합 잔액은 별도 정산으로 비교합니다.",
            "정보통신": " 정보통신공사업은 실적과 자본금 중심으로 산정하며, 공제조합 잔액 비중이 작은 경우 정산을 생략합니다.",
            "소방": " 소방시설공사업은 실적과 자본금 중심으로 산정하며, 잔액 비중 기준이 타 업종보다 높습니다.",
          }};
          const splitDetail = "분할/합병 선택 시 시평·외부신용·부채/유동비율·이익잉여금은 가격 반영에서 제외됩니다." + (SECTOR_SPLIT_NOTES[sectorName] || "");
          note.textContent = splitDetail;
          return;
        }}
        note.textContent = "전기·정보통신·소방은 공제조합 잔액이 양도가와 별도이며 가격 계산에는 반영하지 않습니다.";
        syncYangdoWizard();
      }};
      let draftRestored = false;
      function salesModeLabel(mode) {{
        if (mode === "sales3") return "최근 3년 실적 합계";
        if (mode === "sales5") return "최근 5년 실적 합계";
        return "연도별 입력";
      }}
      function appendKoreanParticle(text, batchimParticle, nonBatchimParticle) {{
        const value = compact(text);
        if (!value) return "";
        const lastChar = value.charCodeAt(value.length - 1);
        if (lastChar < 0xac00 || lastChar > 0xd7a3) return `${{value}}${{batchimParticle}}`;
        const hasBatchim = ((lastChar - 0xac00) % 28) !== 0;
        return `${{value}}${{hasBatchim ? batchimParticle : nonBatchimParticle}}`;
      }}
      function isYangdoEstimateReady(state) {{
        const current = state || getYangdoWizardState();
        return !!(current && current.hasLicense && current.scaleReady && current.criticalReady && (!current.needsReorg || !!current.reorgValue));
      }}
      function syncDraftRestoreNote() {{
        const note = $("draft-restore-note");
        const noteText = $("draft-restore-note-text");
        const noteAction = $("draft-restore-action");
        const noteEstimateAction = $("draft-restore-estimate-action");
        if (!note || !noteText || !noteAction || !noteEstimateAction) return;
        if (!draftRestored) {{
          note.style.display = "none";
          note.classList.remove("is-visible");
          noteText.textContent = "";
          noteEstimateAction.style.display = "none";
          return;
        }}
        const licenseRaw = compact((($("in-license") || {{}}).value));
        const reorgMode = compact((($("in-reorg-mode") || {{}}).value));
        const salesMode = compact((($("in-sales-input-mode") || {{}}).value)) || "yearly";
        const resumeStepIndex = findYangdoWizardResumeStep();
        const resumeMeta = yangdoWizardStepsMeta[resumeStepIndex] || yangdoWizardStepsMeta[0];
        const resumeLabel = `${{resumeMeta.shortLabel}} · ${{resumeMeta.title}}${{resumeMeta.optional ? " (선택)" : ""}}`;
        const estimateReady = isYangdoEstimateReady();
        const splitOptionalPricing = isSplitOptionalPricingProfile({{
          license_raw: licenseRaw,
          raw_license_key: normalizeLicenseKey(licenseRaw),
          tokens: licenseTokenSet(licenseRaw),
        }}, reorgMode);
        let msg = estimateReady
          ? `이전 입력값을 불러왔습니다. 지금 상태로 바로 계산할 수 있고, 필요하면 ${{resumeLabel}}부터 계속 수정할 수 있습니다. 바로 계산하거나 새로 시작을 누르세요.`
          : `이전 입력값을 불러왔습니다. ${{resumeLabel}}부터 이어서 계산할 수 있습니다. 필요하면 바로 새로 시작을 누르세요.`;
        if (splitOptionalPricing) {{
          msg = salesMode === "sales3"
            ? (estimateReady
              ? `이전 입력값을 불러왔습니다. 분할/합병에서는 최근 3년 실적 합계를 기본으로 추천하며 지금 상태로 바로 계산할 수 있습니다. 필요하면 ${{resumeLabel}}에서 수정하거나 바로 계산을 누르세요.`
              : `이전 입력값을 불러왔습니다. ${{resumeLabel}}부터 이어가며, 분할/합병에서는 최근 3년 실적 합계를 기본으로 추천합니다. 필요하면 바로 새로 시작을 누르세요.`)
            : (estimateReady
              ? `이전 입력값을 불러와 실적 입력 방식을 ${{appendKoreanParticle(salesModeLabel(salesMode), "으로", "로")}} 유지했고 지금 상태로 바로 계산할 수 있습니다. 분할/합병 기본 추천은 최근 3년 실적 합계입니다. 필요하면 ${{resumeLabel}}에서 수정하거나 바로 계산을 누르세요.`
              : `이전 입력값을 불러와 ${{resumeLabel}}부터 이어갑니다. 실적 입력 방식은 ${{appendKoreanParticle(salesModeLabel(salesMode), "으로", "로")}} 유지했고, 분할/합병 기본 추천은 최근 3년 실적 합계입니다. 필요하면 바로 새로 시작을 누르세요.`);
        }}
        noteText.textContent = msg;
        noteEstimateAction.style.display = estimateReady ? "inline-flex" : "none";
        note.style.display = "flex";
        note.classList.add("is-visible");
      }}
      const getYangdoWizardState = () => {{
        const licenseValue = compact(($("in-license") || {{}}).value);
        const scaleMode = getScaleSearchMode();
        const salesMode = compact(($("in-sales-input-mode") || {{}}).value) || "yearly";
        const specialtyReady = Number.isFinite(num(($("in-specialty") || {{}}).value));
        const yearlyReady = ["in-y23", "in-y24", "in-y25"].some((id) => Number.isFinite(num(($(id) || {{}}).value)));
        const sales3Ready = Number.isFinite(num(($("in-sales3-total") || {{}}).value));
        const sales5Ready = Number.isFinite(num(($("in-sales5-total") || {{}}).value));
        const scaleReady = scaleMode === "sales"
          ? (salesMode === "yearly" ? yearlyReady : (salesMode === "sales3" ? sales3Ready : sales5Ready))
          : specialtyReady;
        const capitalReady = Number.isFinite(num(($("in-capital") || {{}}).value));
        const balanceReady = Number.isFinite(num(($("in-balance") || {{}}).value));
        const hasProfile = !!resolveLicenseProfile(licenseValue);
        const checksReady = ["ok-capital", "ok-engineer", "ok-office"].every((id) => {{
          const node = $(id);
          return !!node && !!node.checked;
        }});
        const needsReorg = requiresReorgSelectionByLicense(licenseValue);
        const reorgValue = normalizeReorgMode(($("in-reorg-mode") || {{}}).value);
        const balanceUsageValue = normalizeBalanceUsageMode(($("in-balance-usage-mode") || {{}}).value);
        const licenseYearValue = compact(($("in-license-year") || {{}}).value);
        const structureInfoReady = !!reorgValue || (!!balanceUsageValue && balanceUsageValue !== "auto") || !!licenseYearValue;
        const companyInfoCount = [
          $("in-surplus"),
          $("in-debt-level"),
          $("in-liq-level"),
          $("in-company-type"),
          $("in-credit-level"),
          $("in-admin-history"),
        ].filter((node) => {{
          const value = compact(node ? node.value : "");
          if (!value || value === "auto") return false;
          if (node && node.dataset && node.dataset.autofill === "1" && node.dataset.manual !== "1") return false;
          return true;
        }}).length;
        const companyInfoReady = companyInfoCount > 0;
        const criticalReadyCount = [capitalReady, (balanceReady || hasProfile), checksReady].filter(Boolean).length;
        const optionalCount = (reorgValue ? 1 : 0)
          + ((balanceUsageValue && balanceUsageValue !== "auto") ? 1 : 0)
          + (licenseYearValue ? 1 : 0)
          + companyInfoCount;
        return {{
          hasLicense: !!licenseValue,
          scaleReady,
          criticalReady: criticalReadyCount >= 3,
          structureInfoReady,
          companyInfoReady,
          criticalReadyCount,
          optionalCount,
          needsReorg,
          reorgValue,
          completed: [
            !!licenseValue,
            scaleReady,
            criticalReadyCount >= 3,
            structureInfoReady || (!needsReorg && !reorgValue),
            companyInfoReady,
          ],
        }};
      }};
      const focusYangdoWizardStep = (stepIndex) => {{
        const meta = yangdoWizardStepsMeta[stepIndex];
        const node = meta ? $(meta.id) : null;
        if (!node) return;
        if (typeof node.scrollIntoView === "function") {{
          node.scrollIntoView({{ behavior: "smooth", block: "start" }});
        }}
        const focusTarget = node.querySelector("input, select, button:not([disabled])");
        if (focusTarget && typeof focusTarget.focus === "function") {{
          try {{ focusTarget.focus({{ preventScroll: true }}); }} catch (_e) {{ focusTarget.focus(); }}
        }}
      }};
      const scrollResultPanelIntoView = () => {{
        const panel = $("estimate-result-panel") || document.querySelector("#seoulmna-yangdo-calculator .panel.result");
        if (!panel || typeof panel.scrollIntoView !== "function") return;
        const prefersReducedMotion = typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        panel.scrollIntoView({{ behavior: prefersReducedMotion ? "auto" : "smooth", block: "start" }});
      }};
      const flushPendingResultPanelScroll = () => {{
        if (!pendingResultPanelScroll) return;
        pendingResultPanelScroll = false;
        const isMobileLike = typeof window.matchMedia === "function"
          ? window.matchMedia("(max-width: 980px)").matches
          : ((window.innerWidth || 0) <= 980);
        if (!isMobileLike) return;
        window.setTimeout(scrollResultPanelIntoView, 120);
      }};
      const buildYangdoWizardSearchSummary = () => {{
        const scaleMode = getScaleSearchMode();
        if (scaleMode === "sales") {{
          const salesMode = compact(($("in-sales-input-mode") || {{}}).value) || "yearly";
          if (salesMode === "sales3") {{
            const total = num(($("in-sales3-total") || {{}}).value);
            return Number.isFinite(total) ? `실적 3년 ${{fmtEok(total)}}` : "실적 3년 입력 전";
          }}
          if (salesMode === "sales5") {{
            const total = num(($("in-sales5-total") || {{}}).value);
            return Number.isFinite(total) ? `실적 5년 ${{fmtEok(total)}}` : "실적 5년 입력 전";
          }}
          const totals = ["in-y23", "in-y24", "in-y25"]
            .map((id) => num(($(id) || {{}}).value))
            .filter((value) => Number.isFinite(value));
          if (!totals.length) return "실적 연도별 입력 전";
          const sum = totals.reduce((acc, value) => acc + value, 0);
          return `실적 연도별 ${{fmtEok(sum)}}`;
        }}
        const specialtyValue = num(($("in-specialty") || {{}}).value);
        return Number.isFinite(specialtyValue)
          ? `시평 ${{formatInputNumber(specialtyValue, 1)}}`
          : "시평 입력 전";
      }};
      const syncYangdoWizardProgress = () => {{
        const labelNode = $("yangdoWizardProgressLabel");
        const metaNode = $("yangdoWizardProgressMeta");
        const fillNode = $("yangdoWizardProgressFill");
        const countNode = $("yangdoWizardProgressCount");
        const barNode = $("yangdoWizardProgressBar");
        const actionNode = $("yangdoWizardNextActionText");
        const actionReasonNode = $("yangdoWizardActionReason");
        const stickyShellNode = $("yangdoWizardMobileSticky");
        const stickyLabelNode = $("yangdoWizardMobileStickyLabel");
        const stickyActionNode = $("yangdoWizardMobileStickyAction");
        const stickyCompactNode = $("yangdoWizardMobileStickyCompact");
        const stickyMetaNode = $("yangdoWizardMobileStickyMeta");
        const stickyReasonNode = $("yangdoWizardMobileStickyReason");
        const stickyCountNode = $("yangdoWizardMobileStickyCount");
        if (!labelNode && !metaNode && !fillNode && !countNode && !barNode && !actionNode && !stickyShellNode && !stickyLabelNode && !stickyActionNode && !stickyCompactNode && !stickyMetaNode && !stickyReasonNode && !stickyCountNode) return;
        const state = getYangdoWizardState();
        const totalSteps = yangdoWizardStepsMeta.length;
        const currentIndex = Math.max(0, Math.min(totalSteps - 1, Number(yangdoWizardStepIndex) || 0));
        const requiredIndices = yangdoWizardStepsMeta
          .map((step, stepIndex) => step.optional ? -1 : stepIndex)
          .filter((stepIndex) => stepIndex >= 0);
        const optionalIndices = yangdoWizardStepsMeta
          .map((step, stepIndex) => step.optional ? stepIndex : -1)
          .filter((stepIndex) => stepIndex >= 0);
        const requiredDone = requiredIndices.filter((stepIndex) => !!state.completed[stepIndex]).length;
        const optionalDone = optionalIndices.filter((stepIndex) => !!state.completed[stepIndex]).length;
        const requiredTotal = requiredIndices.length;
        const optionalTotal = optionalIndices.length;
        const progressPct = Math.round(((currentIndex + 1) / Math.max(1, totalSteps)) * 100);
        let metaText = "";
        if (!state.hasLicense) {{
          metaText = `필수 ${{requiredDone}}/${{requiredTotal}} 완료 · 업종부터 입력하면 자동 제안이 시작됩니다.`;
        }} else if (!state.scaleReady) {{
          metaText = `필수 ${{requiredDone}}/${{requiredTotal}} 완료 · 검색 기준 1단계가 남았습니다.`;
        }} else if (!state.criticalReady) {{
          metaText = `필수 ${{requiredDone}}/${{requiredTotal}} 완료 · 가격 영향 필수 입력을 마치면 결과가 더 안정됩니다.`;
        }} else if (state.needsReorg && !state.reorgValue) {{
          metaText = `필수 ${{requiredDone}}/${{requiredTotal}} 완료 · 이 업종은 구조 선택이 먼저 필요합니다.`;
        }} else if (optionalTotal > 0 && optionalDone > 0) {{
          metaText = `필수 입력 완료 · 선택 ${{optionalDone}}/${{optionalTotal}}단계가 결과에 반영되고 있습니다.`;
        }} else if (optionalTotal > 0) {{
          metaText = `필수 입력 완료 · 남은 ${{optionalTotal}}단계는 선택 보정입니다.`;
        }} else {{
          metaText = `필수 ${{requiredDone}}/${{requiredTotal}} 완료`;
        }}
        if (labelNode) labelNode.textContent = `현재 ${{currentIndex + 1}}/${{totalSteps}} 단계`;
        if (metaNode) metaNode.textContent = metaText;
        if (actionNode) actionNode.textContent = getYangdoWizardNextActionCopy();
        if (actionReasonNode) {{
          actionReasonNode.textContent = getYangdoWizardActionReasonCopy();
          actionReasonNode.dataset.actionable = "1";
          actionReasonNode.setAttribute("aria-label", `${{getYangdoWizardActionReasonCopy()}} 눌러서 바로 이동합니다.`);
        }}
        if (fillNode) fillNode.style.width = `${{progressPct}}%`;
        if (countNode) countNode.textContent = `${{currentIndex + 1}}/${{totalSteps}}`;
        if (stickyLabelNode) stickyLabelNode.textContent = `현재 ${{currentIndex + 1}}/${{totalSteps}} 단계`;
        if (stickyActionNode) stickyActionNode.textContent = getYangdoWizardNextActionCopy();
        if (stickyCompactNode) stickyCompactNode.textContent = getYangdoWizardMobileCompactCopy();
        if (stickyMetaNode) stickyMetaNode.textContent = metaText;
        if (stickyReasonNode) stickyReasonNode.textContent = getYangdoWizardActionReasonCopy();
        if (stickyCountNode) stickyCountNode.textContent = `${{currentIndex + 1}}/${{totalSteps}}`;
        if (stickyShellNode) {{
          stickyShellNode.setAttribute(
            "aria-label",
            `현재 ${{currentIndex + 1}}/${{totalSteps}} 단계. ${{getYangdoWizardNextActionCopy()}}. ${{getYangdoWizardMobileCompactCopy()}}. ${{metaText}}`
          );
        }}
        if (barNode) {{
          barNode.setAttribute("aria-valuenow", String(currentIndex + 1));
          barNode.setAttribute("aria-valuetext", `현재 ${{currentIndex + 1}}단계 / 총 ${{totalSteps}}단계`);
        }}
      }};
      const syncValuePreview = () => {{
        const shell = $("yangdoValuePreview");
        if (!shell) return;
        const fillNode = $("yangdoValuePreviewFill");
        const textNode = $("yangdoValuePreviewText");
        const countNode = $("yangdoValuePreviewCount");
        const state = getYangdoWizardState();
        if (!state.hasLicense || !dataset.length) {{
          shell.classList.remove("is-visible");
          return;
        }}
        const licenseValue = compact(($("in-license") || {{}}).value);
        const licTokens = licenseValue
          ? Object.keys(canonicalByKey).filter((key) => licenseValue.indexOf(key) >= 0 || (canonicalByKey[key] || "").indexOf(licenseValue) >= 0)
          : [];
        const licSet = new Set(licTokens.length ? licTokens : [licenseValue]);
        let filtered = dataset.filter((row) => {{
          const rowTokens = Array.isArray(row.tokens) ? row.tokens : [];
          return rowTokens.some((t) => licSet.has(compact(t)));
        }});
        if (!filtered.length) {{
          filtered = dataset.filter((row) => {{
            const lt = compact(row.license_text || "");
            return lt.indexOf(licenseValue) >= 0 || licenseValue.indexOf(lt) >= 0;
          }});
        }}
        if (!filtered.length) {{
          shell.classList.remove("is-visible");
          return;
        }}
        if (state.scaleReady) {{
          const scaleMode = getScaleSearchMode();
          if (scaleMode === "specialty") {{
            const sv = num(($("in-specialty") || {{}}).value);
            if (Number.isFinite(sv) && sv > 0) {{
              const margin = sv * 0.4;
              const sub = filtered.filter((r) => {{
                const rs = num(r.specialty);
                return Number.isFinite(rs) && rs > 0 && Math.abs(rs - sv) <= margin;
              }});
              if (sub.length >= 3) filtered = sub;
            }}
          }} else {{
            const s3 = num(($("in-sales3-total") || {{}}).value);
            if (Number.isFinite(s3) && s3 > 0) {{
              const margin = s3 * 0.5;
              const sub = filtered.filter((r) => {{
                const rs = num(r.sales3_eok);
                return Number.isFinite(rs) && rs > 0 && Math.abs(rs - s3) <= margin;
              }});
              if (sub.length >= 3) filtered = sub;
            }}
          }}
        }}
        if (state.criticalReady) {{
          const capVal = num(($("in-capital") || {{}}).value);
          if (Number.isFinite(capVal) && capVal > 0) {{
            const margin = capVal * 0.5;
            const sub = filtered.filter((r) => {{
              const rc = num(r.capital_eok);
              return Number.isFinite(rc) && rc > 0 && Math.abs(rc - capVal) <= margin;
            }});
            if (sub.length >= 3) filtered = sub;
          }}
        }}
        const prices = filtered
          .map((r) => num(r.price_eok))
          .filter((v) => Number.isFinite(v) && v > 0)
          .sort((a, b) => a - b);
        if (!prices.length) {{
          shell.classList.remove("is-visible");
          return;
        }}
        const q10Idx = Math.max(0, Math.floor(prices.length * 0.1));
        const q90Idx = Math.min(prices.length - 1, Math.floor(prices.length * 0.9));
        const low = prices[q10Idx];
        const high = prices[q90Idx];
        const globalMin = prices[0];
        const globalMax = prices[prices.length - 1];
        const range = Math.max(0.01, globalMax - globalMin);
        const barLeft = Math.round(((low - globalMin) / range) * 100);
        const barWidth = Math.max(4, Math.round(((high - low) / range) * 100));
        const fmtP = (v) => {{
          if (v >= 1) return v.toFixed(1) + "억";
          return Math.round(v * 10000).toLocaleString() + "만";
        }};
        shell.classList.add("is-visible");
        if (fillNode) {{
          fillNode.style.left = barLeft + "%";
          fillNode.style.width = barWidth + "%";
        }}
        if (textNode) textNode.textContent = `${{fmtP(low)}} ~ ${{fmtP(high)}}`;
        if (countNode) countNode.textContent = `유사 매물 ${{prices.length}}건 기준 · 입력이 늘수록 범위가 좁아집니다`;
      }};
      const getYangdoWizardNextActionCopy = () => {{
        const state = getYangdoWizardState();
        const licenseValue = compact(($("in-license") || {{}}).value);
        if (!state.hasLicense) {{
          return "면허/업종부터 선택하세요.";
        }}
        if (!state.scaleReady) {{
          return "시평 또는 실적 중 한 축을 먼저 입력하세요.";
        }}
        if (!state.criticalReady) {{
          const missing = [];
          if (!Number.isFinite(num(($("in-capital") || {{}}).value))) missing.push("자본금");
          if (!(Number.isFinite(num(($("in-balance") || {{}}).value)) || !!resolveLicenseProfile(licenseValue))) missing.push("공제조합 잔액");
          const pendingChecks = [];
          ["ok-capital", "ok-engineer", "ok-office"].forEach((id) => {{
            const checkbox = $(id);
            if (!checkbox || checkbox.checked) return;
            if (id === "ok-capital") pendingChecks.push("자본금 충족");
            if (id === "ok-engineer") pendingChecks.push("기술자 충족");
            if (id === "ok-office") pendingChecks.push("사무실 충족");
          }});
          if (missing.length) {{
            return missing.length === 1
              ? `${{missing[0]}}부터 입력하세요.`
              : `${{missing.join(", ")}}를 순서대로 입력하세요.`;
          }}
          if (pendingChecks.length) {{
            return pendingChecks.length === 1
              ? `${{pendingChecks[0]}} 체크를 마치세요.`
              : `${{pendingChecks.join(", ")}} 체크를 마치세요.`;
          }}
          return "핵심 가격 영향 입력을 먼저 마치세요.";
        }}
        if (state.needsReorg && !state.reorgValue) {{
          return "포괄 또는 분할/합병 중 구조를 선택하세요.";
        }}
        if (state.optionalCount > 0) {{
          return "결과를 확인하고 전달용 브리프를 복사하세요.";
        }}
        return "선택 정보는 필요한 것만 더하고 바로 결과를 확인하세요.";
      }};
      const getYangdoWizardActionReasonCopy = () => {{
        const state = getYangdoWizardState();
        const licenseValue = compact(($("in-license") || {{}}).value);
        if (!state.hasLicense) {{
          return "업종이 정해져야 통상 자본금과 공제조합 기준을 자동 제안할 수 있습니다.";
        }}
        if (!state.scaleReady) {{
          return "시평과 실적을 함께 받으면 값이 튈 수 있어 먼저 한 축만 입력합니다.";
        }}
        if (!state.criticalReady) {{
          return "자본금과 공제조합 잔액이 맞아야 추천 후보 범위와 결과 신뢰도가 빨리 안정됩니다.";
        }}
        if (state.needsReorg && !state.reorgValue) {{
          return `${{licenseValue || "이 업종"}}은 구조에 따라 계산 축이 달라져 여기서 포괄과 분할/합병을 먼저 나눕니다.`;
        }}
        if (state.optionalCount > 0) {{
          return "선택 정보는 가격보다 전달 정밀도를 높이는 마지막 보정 단계입니다.";
        }}
        return "필수 입력은 끝났고, 필요하면 선택 정보만 더한 뒤 바로 결과를 확인하면 됩니다.";
      }};
      const getYangdoWizardMobileCompactCopy = () => {{
        const state = getYangdoWizardState();
        if (!state.hasLicense) {{
          return "업종 선택 후 자동 기준 시작";
        }}
        if (!state.scaleReady) {{
          return "시평/실적 한 축만 먼저";
        }}
        if (!state.criticalReady) {{
          return "자본금·잔액·필수 체크 순서";
        }}
        if (state.needsReorg && !state.reorgValue) {{
          return "구조 선택 먼저";
        }}
        if (state.optionalCount > 0) {{
          return "선택 정보는 마지막 보정";
        }}
        return "결과 브리프 바로 전달";
      }};
      const resolveYangdoActionTargetNode = (target) => {{
        if (!target) return null;
        return typeof target === "string"
          ? (document.querySelector(target) || $(target))
          : target;
      }};
      let yangdoGuidedFocusTimer = 0;
      let yangdoGuidedFocusNode = null;
      const clearYangdoGuidedFocus = () => {{
        if (yangdoGuidedFocusTimer) {{
          window.clearTimeout(yangdoGuidedFocusTimer);
          yangdoGuidedFocusTimer = 0;
        }}
        if (yangdoGuidedFocusNode) {{
          yangdoGuidedFocusNode.classList.remove("guided-focus-target");
          delete yangdoGuidedFocusNode.dataset.guidedFocus;
          delete yangdoGuidedFocusNode.dataset.guidedFocusCopy;
          delete yangdoGuidedFocusNode.dataset.guidedFocusLevel;
          yangdoGuidedFocusNode = null;
        }}
      }};
      const resolveYangdoGuidedFocusNode = (node) => {{
        if (!node) return null;
        return node.closest(".field, .reorg-choice-btn, .reorg-compare-card, .result-share-wrap, .wizard-progress-card, .panel, .btn-row") || node;
      }};
      const getYangdoGuidedFocusCopy = (target, node, source = "") => {{
        const key = typeof target === "string"
          ? target
          : String((node && (node.id || node.getAttribute && node.getAttribute("data-reorg-choice"))) || "").trim();
        if (source === "mobile") {{
          if (key === "in-license") return "지금은 업종만 고르면 됩니다.";
          if (["in-specialty", "in-y23", "in-sales3-total", "in-sales5-total"].includes(key)) return "지금은 검색 기준 한 축만 정하면 됩니다.";
          if (["in-capital", "in-balance"].includes(key)) return "지금 이 값만 채우면 바로 다음으로 넘어갑니다.";
          if (["ok-capital", "ok-engineer", "ok-office"].includes(key)) return "지금은 확인 체크만 끝내면 됩니다.";
          if (key.indexOf("[data-reorg-choice=") === 0 || key === "포괄" || key === "분할/합병") return "지금은 구조 하나만 선택하면 됩니다.";
          if (key === "btn-copy-brief") return "지금은 브리프만 복사하면 전달 준비가 끝납니다.";
        }}
        if (key === "in-license") return "업종만 고르면 자동 기준이 바로 시작됩니다.";
        if (["in-specialty", "in-y23", "in-sales3-total", "in-sales5-total"].includes(key)) return "이 값 하나만 넣으면 다음 판단이 쉬워집니다.";
        if (key === "in-capital") return "자본금부터 넣으면 추천 범위가 빨리 안정됩니다.";
        if (key === "in-balance") return "공제조합 잔액만 맞추면 후보 비교가 쉬워집니다.";
        if (["ok-capital", "ok-engineer", "ok-office"].includes(key)) return "확인됐다면 체크만 해도 다음 단계로 넘어갑니다.";
        if (key.indexOf("[data-reorg-choice=") === 0 || key === "포괄" || key === "분할/합병") return "구조 하나만 선택하면 계산 축이 정리됩니다.";
        if (key === "btn-estimate") return "여기서 바로 AI 계산을 실행합니다.";
        if (key === "btn-copy-brief") return "복사 후 바로 상담 전달에 쓰면 됩니다.";
        if (key === "in-balance-usage-mode") return "정산 방식을 고르면 전달 문구가 더 정확해집니다.";
        return "여기만 확인하면 다음 행동이 이어집니다.";
      }};
      const showYangdoGuidedFocus = (node, helperCopy = "", options = {{}}) => {{
        const highlightNode = resolveYangdoGuidedFocusNode(node);
        if (!highlightNode) return;
        clearYangdoGuidedFocus();
        highlightNode.classList.add("guided-focus-target");
        highlightNode.dataset.guidedFocus = "1";
        if (helperCopy) highlightNode.dataset.guidedFocusCopy = helperCopy;
        if (options && options.level) highlightNode.dataset.guidedFocusLevel = String(options.level);
        yangdoGuidedFocusNode = highlightNode;
        yangdoGuidedFocusTimer = window.setTimeout(() => {{
          clearYangdoGuidedFocus();
        }}, 1400);
      }};
      const isYangdoActionTargetFocusable = (node) => {{
        if (!node) return false;
        if ("disabled" in node && node.disabled) return false;
        if (node.hidden) return false;
        if (node.closest("[hidden]")) return false;
        const style = window.getComputedStyle(node);
        if (!style || style.display === "none" || style.visibility === "hidden") return false;
        return node.getClientRects().length > 0;
      }};
      const focusYangdoActionTarget = (target, options = {{}}) => {{
        const node = resolveYangdoActionTargetNode(target);
        if (!isYangdoActionTargetFocusable(node)) return false;
        if (typeof node.scrollIntoView === "function") {{
          node.scrollIntoView({{ behavior: "smooth", block: "center" }});
        }}
        if (typeof node.focus === "function") {{
          try {{ node.focus({{ preventScroll: true }}); }} catch (_error) {{ node.focus(); }}
        }}
        const source = options && options.source ? String(options.source) : "";
        showYangdoGuidedFocus(node, getYangdoGuidedFocusCopy(target, node, source), {{
          level: source === "mobile" ? "sticky" : "",
        }});
        return document.activeElement === node || (!!document.activeElement && node.contains(document.activeElement));
      }};
      const getYangdoWizardNextActionTarget = () => {{
        const state = getYangdoWizardState();
        const scaleMode = getScaleSearchMode();
        const salesMode = compact(($("in-sales-input-mode") || {{}}).value) || "yearly";
        if (!state.hasLicense) {{
          return {{ stepIndex: 0, target: "in-license" }};
        }}
        if (!state.scaleReady) {{
          if (scaleMode === "sales") {{
            if (salesMode === "sales3") return {{ stepIndex: 1, target: "in-sales3-total" }};
            if (salesMode === "sales5") return {{ stepIndex: 1, target: "in-sales5-total" }};
            return {{ stepIndex: 1, target: "in-y23" }};
          }}
          return {{ stepIndex: 1, target: "in-specialty" }};
        }}
        if (!state.criticalReady) {{
          if (!Number.isFinite(num(($("in-capital") || {{}}).value))) return {{ stepIndex: 2, target: "in-capital" }};
          if (!(Number.isFinite(num(($("in-balance") || {{}}).value)) || !!resolveLicenseProfile(compact(($("in-license") || {{}}).value)))) {{
            return {{ stepIndex: 2, target: "in-balance" }};
          }}
          if (!($("ok-capital") || {{}}).checked) return {{ stepIndex: 2, target: "ok-capital" }};
          if (!($("ok-engineer") || {{}}).checked) return {{ stepIndex: 2, target: "ok-engineer" }};
          if (!($("ok-office") || {{}}).checked) return {{ stepIndex: 2, target: "ok-office" }};
          return {{ stepIndex: 2, target: "in-capital" }};
        }}
        if (state.needsReorg && !state.reorgValue) {{
          return {{ stepIndex: 3, target: '[data-reorg-choice="포괄"]' }};
        }}
        if (isYangdoEstimateReady(state)) {{
          if (lastEstimate && $("btn-copy-brief") && !$("btn-copy-brief").disabled) {{
            return {{ stepIndex: 4, target: "btn-copy-brief" }};
          }}
          return {{ stepIndex: 2, target: "btn-estimate" }};
        }}
        return {{ stepIndex: findYangdoWizardResumeStep(), target: "in-balance-usage-mode" }};
      }};
      const runYangdoWizardNextAction = (source = "") => {{
        const action = getYangdoWizardNextActionTarget();
        if (!action) return;
        if (Number.isFinite(Number(action.stepIndex))) {{
          setYangdoWizardStep(Number(action.stepIndex), false);
        }}
        let attemptsLeft = 6;
        const tryFocusAction = () => {{
          const latestAction = Number(action.stepIndex) === 1 ? (getYangdoWizardNextActionTarget() || action) : action;
          if (latestAction.target === "btn-copy-brief" && lastEstimate) {{
            const resultPanel = $("estimate-result-panel") || document.querySelector("#seoulmna-yangdo-calculator .panel.result");
            if (resultPanel && typeof resultPanel.scrollIntoView === "function") {{
              resultPanel.scrollIntoView({{ behavior: "smooth", block: "start" }});
            }}
          }}
          if (focusYangdoActionTarget(latestAction.target, {{ source }})) return;
          attemptsLeft -= 1;
          if (attemptsLeft <= 0) return;
          window.setTimeout(tryFocusAction, 48);
        }};
        window.setTimeout(tryFocusAction, 0);
      }};
      const syncYangdoWizardSummary = () => {{
        const node = $("yangdoWizardSummary");
        if (!node) return;
        const state = getYangdoWizardState();
        const licenseValue = compact(($("in-license") || {{}}).value);
        const items = [];
        let criticalSummary = `필수 ${{state.criticalReadyCount}}/3 입력`;
        if (!state.hasLicense) {{
          criticalSummary = "핵심 입력 준비 전";
        }} else if (!state.scaleReady) {{
          criticalSummary = "검색 기준 먼저 입력";
        }} else if (state.criticalReady) {{
          criticalSummary = "필수 가격 영향 완료";
        }}
        items.push(licenseValue ? `업종 ${{licenseValue}}` : "업종부터 시작");
        items.push(buildYangdoWizardSearchSummary());
        items.push(criticalSummary);
        if (state.optionalCount > 0) {{
          items.push(`선택 ${{state.optionalCount}}건 반영`);
        }} else if (state.needsReorg && !state.reorgValue) {{
          items.push("구조 선택 필요");
        }} else {{
          items.push("선택 정보는 마지막 단계");
        }}
        node.innerHTML = items
          .map((item, itemIndex) => `<span class="wizard-summary-chip${{!licenseValue && itemIndex === 0 ? " is-empty" : ""}}">${{escapeHtml(item)}}</span>`)
          .join("");
      }};
      const syncYangdoPriorityHint = () => {{
        const node = $("yangdoCriticalHint");
        if (!node) return;
        const licenseValue = compact(($("in-license") || {{}}).value);
        const scaleMode = getScaleSearchMode();
        const needsReorg = requiresReorgSelectionByLicense(licenseValue);
        if (!licenseValue) {{
          node.textContent = "업종을 먼저 입력하면 통상 매물 기준값을 불러와 어떤 숫자부터 봐야 할지 자동으로 안내합니다.";
          return;
        }}
        if (needsReorg && scaleMode === "sales") {{
          node.textContent = "전기·정보통신·소방 계열은 실적과 자본금이 먼저 안정돼야 값이 덜 튑니다. 공제조합 잔액은 별도 참고로 보고 구조 선택은 다음 단계에서 반영합니다.";
          return;
        }}
        if (scaleMode === "sales") {{
          node.textContent = "실적 축에서는 자본금과 필수 기준 충족이 먼저 맞아야 비교 매물 범위가 안정됩니다. 공제조합 잔액은 최소 기준만 먼저 확인하면 됩니다.";
          return;
        }}
        node.textContent = "시평 축에서는 자본금, 공제조합 잔액, 필수 기준 충족 3가지를 먼저 맞추면 결과 범위가 가장 안정적으로 잡힙니다.";
      }};
      const getYangdoOptionalGuide = () => {{
        const licenseValue = compact(($("in-license") || {{}}).value);
        const scaleMode = getScaleSearchMode();
        const needsReorg = requiresReorgSelectionByLicense(licenseValue);
        const specialBalance = isSeparateBalanceGroupToken(licenseValue);
        if (!licenseValue) {{
          return {{
            structureHint: "업종을 먼저 고르면 마지막 단계에서 어떤 선택 정보부터 보면 되는지 자동으로 안내합니다.",
            companyHint: "필수 입력이 끝난 뒤에는 재무 상태와 회사 리스크를 필요한 만큼만 보정용으로 넣으면 됩니다.",
          }};
        }}
        if (needsReorg) {{
          return {{
            structureHint: "전기·정보통신·소방 계열은 양도 구조를 가장 먼저 정하고, 그 다음 공제조합 정산 방식과 면허년도를 확인하면 전달용 정산 가정이 빠르게 정리됩니다.",
            companyHint: "이 계열은 구조 선택 영향이 커서 재무 상태와 회사 리스크는 마지막 미세 보정용으로만 넣어도 충분합니다.",
          }};
        }}
        if (scaleMode === "sales") {{
          return {{
            structureHint: `${{licenseValue}}은 실적 축을 먼저 잡은 상태라 공제조합 정산 방식${{specialBalance ? " 참고 여부" : ""}}와 면허년도만 정리해도 상담 전달 가정이 거의 정리됩니다.`,
            companyHint: "실적 축에서는 이익잉여금보다 회사 리스크 정보가 있으면 후속 상담 우선순위를 더 빨리 잡을 수 있습니다.",
          }};
        }}
        return {{
          structureHint: `${{licenseValue}}은 시평 축 기준으로 공제조합 정산 방식${{specialBalance ? " 참고 여부" : ""}}와 면허년도 정도만 넣으면 마지막 전달 문구가 정리됩니다.`,
          companyHint: "시평 축에서는 이익잉여금과 회사 리스크를 필요한 만큼만 선택해 미세 보정하면 됩니다.",
        }};
      }};
      const syncYangdoOptionalHints = () => {{
        const plan = getYangdoOptionalGuide();
        const structureNode = $("yangdoStructureHint");
        const companyNode = $("yangdoCompanyHint");
        if (structureNode) structureNode.textContent = plan.structureHint;
        if (companyNode) companyNode.textContent = plan.companyHint;
      }};
      const syncYangdoWizardBlocker = () => {{
        const node = $("yangdoWizardBlocker");
        if (!node) return;
        const state = getYangdoWizardState();
        const missing = [];
        if (!state.hasLicense) {{
          node.classList.remove("is-ready");
          node.textContent = "다음 단계로 가려면 먼저 업종을 입력해 주세요.";
          return;
        }}
        if (!state.scaleReady) {{
          node.classList.remove("is-ready");
          node.textContent = "다음 단계로 가려면 시평 또는 실적 중 한 축을 입력해 주세요.";
          return;
        }}
        if (!state.criticalReady) {{
          if (!Number.isFinite(num(($("in-capital") || {{}}).value))) missing.push("자본금");
          if (!(Number.isFinite(num(($("in-balance") || {{}}).value)) || !!resolveLicenseProfile(compact(($("in-license") || {{}}).value)))) missing.push("공제조합 잔액");
          ["ok-capital", "ok-engineer", "ok-office"].forEach((id) => {{
            const checkbox = $(id);
            if (!checkbox || checkbox.checked) return;
            if (id === "ok-capital") missing.push("자본금 충족 체크");
            if (id === "ok-engineer") missing.push("기술자 충족 체크");
            if (id === "ok-office") missing.push("사무실 충족 체크");
          }});
          node.classList.remove("is-ready");
          node.textContent = `다음 단계로 가려면 ${{missing.join(", ")}}를 확인해 주세요.`;
          return;
        }}
        if (state.needsReorg && !state.reorgValue) {{
          node.classList.remove("is-ready");
          node.textContent = "전기·정보통신·소방 계열은 다음 단계에서 포괄 또는 분할/합병을 선택해야 계산할 수 있습니다.";
          return;
        }}
        node.classList.add("is-ready");
        node.textContent = "필수 입력은 끝났습니다. 선택 정보는 필요할 때만 보정용으로 넣고 바로 AI 계산 결과를 보셔도 됩니다.";
      }};
      const findYangdoWizardResumeStep = () => {{
        const state = getYangdoWizardState();
        if (!state.hasLicense) return 0;
        if (!state.scaleReady) return 1;
        if (!state.criticalReady) return 2;
        if (state.needsReorg && !state.reorgValue) return 3;
        if (isYangdoEstimateReady(state)) return 2;
        if (state.companyInfoReady) return 4;
        if (state.structureInfoReady) return 4;
        return 3;
      }};
      const syncYangdoWizard = () => {{
        const shell = $("yangdo-input-wizard");
        if (!shell) return;
        const state = getYangdoWizardState();
        const step4NeedsAttention = !!state.needsReorg && !state.reorgValue;
        const maxIndex = Math.max(0, yangdoWizardStepsMeta.length - 1);
        yangdoWizardStepIndex = Math.max(0, Math.min(maxIndex, Number(yangdoWizardStepIndex) || 0));
        const currentMeta = yangdoWizardStepsMeta[yangdoWizardStepIndex] || yangdoWizardStepsMeta[0];
        const titleNode = $("yangdoWizardStepTitle");
        const noteNode = $("yangdoWizardStepNote");
        if (titleNode) titleNode.textContent = `${{currentMeta.shortLabel}} · ${{currentMeta.title}}${{currentMeta.optional ? " (선택)" : ""}}`;
        if (noteNode) {{
          if (currentMeta.id === "yangdoWizardStep4" && state.needsReorg && !state.reorgValue) {{
            noteNode.textContent = "전기·정보통신·소방 계열은 이 단계에서 양도 구조 선택이 필요합니다.";
          }} else if (currentMeta.optional) {{
            noteNode.textContent = "마지막 단계는 선택 정보입니다. 비워도 기본 계산은 가능하지만 일부 업종은 구조 선택이 필요할 수 있습니다.";
          }} else {{
            noteNode.textContent = currentMeta.note;
          }}
        }}
        syncYangdoWizardProgress();
        syncYangdoWizardSummary();
        syncYangdoWizardBlocker();
        syncYangdoPriorityHint();
        syncYangdoOptionalHints();
        syncValuePreview();
        yangdoWizardStepsMeta.forEach((step, stepIndex) => {{
          const stepNode = $(step.id);
          const isActive = stepIndex === yangdoWizardStepIndex;
          const isAlert = step.id === "yangdoWizardStep4" && step4NeedsAttention;
          if (stepNode) {{
            stepNode.classList.toggle("is-active", isActive);
            stepNode.classList.toggle("is-alert", isAlert);
            stepNode.hidden = !isActive;
          }}
          document.querySelectorAll(`[data-yangdo-wizard-track="${{stepIndex}}"]`).forEach((chip) => {{
            chip.classList.toggle("is-active", isActive);
            chip.classList.toggle("is-complete", !!state.completed[stepIndex]);
            chip.classList.toggle("is-optional", !!step.optional);
            chip.classList.toggle("is-alert", isAlert);
            chip.setAttribute("aria-current", isActive ? "step" : "false");
          }});
          document.querySelectorAll(`[data-yangdo-wizard-prev="${{stepIndex}}"]`).forEach((button) => {{
            button.disabled = stepIndex === 0;
          }});
          document.querySelectorAll(`[data-yangdo-wizard-next="${{stepIndex}}"]`).forEach((button) => {{
            let nextLabel = "다음";
            let disabled = false;
            if (stepIndex === 0) {{
              nextLabel = "검색 기준으로";
              disabled = !state.hasLicense;
            }} else if (stepIndex === 1) {{
              nextLabel = "핵심 가격 영향 입력";
              disabled = !state.scaleReady;
            }} else if (stepIndex === 2) {{
              nextLabel = step4NeedsAttention ? "구조·정산 정보(필수)" : "구조·정산 정보";
              disabled = !state.criticalReady;
            }} else if (stepIndex === 3) {{
              nextLabel = step4NeedsAttention ? "양도 구조 먼저 선택" : "재무·회사 정보";
              disabled = step4NeedsAttention;
            }} else {{
              nextLabel = "AI 계산 결과 보기";
            }}
            button.textContent = nextLabel;
            button.disabled = disabled;
          }});
        }});
      }};
      const setYangdoWizardStep = (nextIndex, focusStep = false) => {{
        const maxIndex = Math.max(0, yangdoWizardStepsMeta.length - 1);
        yangdoWizardStepIndex = Math.max(0, Math.min(maxIndex, Number(nextIndex) || 0));
        syncYangdoWizard();
        if (focusStep) focusYangdoWizardStep(yangdoWizardStepIndex);
      }};

      const draftFieldIds = [
        "in-license", "in-scale-search-mode", "in-reorg-mode", "in-balance-usage-mode", "in-license-year", "in-specialty", "in-sales-input-mode", "in-y23", "in-y24", "in-y25", "in-sales3-total", "in-sales5-total",
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
        clearRecommendAutoLoop();
        $("in-license").value = "";
        setScaleSearchMode("specialty");
        $("in-reorg-mode").value = "";
        $("in-balance-usage-mode").value = "auto";
        $("in-license-year").value = "";
        $("in-specialty").value = "";
        $("in-sales-input-mode").value = "yearly";
        delete $("in-sales-input-mode").dataset.splitPrepared;
        delete $("in-sales-input-mode").dataset.previousMode;
        delete $("in-sales-input-mode").dataset.splitAutoSelected;
        delete $("in-sales-input-mode").dataset.splitAutoFocusDone;
        delete $("in-sales-input-mode").dataset.splitManualMode;
        delete $("in-sales-input-mode").dataset.autoApplying;
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
        $("out-cash-due").textContent = "-";
        $("out-realizable-balance").textContent = "-";
        $("out-confidence").textContent = "-";
        $("out-neighbors").textContent = "-";
        $("out-source-tier").textContent = "-";
        renderYoyCompare(null);
        renderResultReasonChips(null);
        $("risk-note").textContent = "AI 산정 전: 면허/업종, 검색 기준(시평 또는 실적), 자본금, 필수 기준 충족 여부를 먼저 확인해 주세요.";
        const settlementPanel = $("settlement-panel");
        if (settlementPanel) settlementPanel.style.display = "none";
        const hotCta = $("hot-match-cta");
        if (hotCta) hotCta.style.display = "none";
        const advanced = $("advanced-inputs");
        if (advanced) advanced.open = false;
        ["in-balance", "in-capital", "in-surplus"].forEach((id) => {{
          const node = $(id);
          if (!node) return;
          delete node.dataset.manual;
          delete node.dataset.autofill;
        }});
        lastEstimate = null;
        renderRecommendedListings([], null);
        neighborPanelDisclosureManual = false;
        renderNeighbors([]);
        renderActionSteps(null);
        syncResultShareActions(false);
        pendingResultPanelScroll = false;
        draftRestored = false;
        syncScaleSearchModeUi();
        syncSalesInputModeUi();
        syncReorgModeRequirement();
        syncLicenseAutoProfile(false);
        syncConsultSummary();
        setYangdoWizardStep(0);
        clearDraft();
      }};

      // Apply meta counters before optional contact widgets to avoid late-stage rendering gaps.
      applyYangdoWizardLayout();
      setMeta();
      renderLicenseSuggestions();
      renderLicenseQuickChips();
      if (!enableConsultWidget) {{
        document.querySelectorAll("#seoulmna-yangdo-calculator .consult-wrap").forEach((el) => {{
          if (!el) return;
          el.style.display = "none";
        }});
      }}
      if (!enableHotMatch) {{
        const hotCta = $("hot-match-cta");
        if (hotCta) hotCta.style.display = "none";
      }}
      const on = (id, eventName, handler) => {{
        const node = $(id);
        if (!node) return false;
        node.addEventListener(eventName, handler);
        return true;
      }};
      const neighborPanel = $("neighbor-panel");
      if (neighborPanel) {{
        neighborPanel.addEventListener("toggle", () => {{
          if (neighborPanelDisclosureSyncing) return;
          neighborPanelDisclosureManual = true;
        }});
      }}
      window.addEventListener("resize", () => syncNeighborPanelDisclosure(false));
      const wizardShell = $("yangdo-input-wizard");
      if (wizardShell) {{
        wizardShell.addEventListener("click", (event) => {{
          const target = event.target;
          const actionButton = target && target.closest ? target.closest("[data-yangdo-next-action]") : null;
          if (actionButton) {{
            runYangdoWizardNextAction(String(actionButton.getAttribute("data-yangdo-next-action") || ""));
            return;
          }}
          const actionReason = target && target.closest ? target.closest("[data-yangdo-action-reason]") : null;
          if (actionReason) {{
            runYangdoWizardNextAction("reason");
            return;
          }}
          const prevButton = target && target.closest ? target.closest("[data-yangdo-wizard-prev]") : null;
          if (prevButton) {{
            setYangdoWizardStep(Number(prevButton.getAttribute("data-yangdo-wizard-prev") || 0) - 1, true);
            return;
          }}
          const nextButton = target && target.closest ? target.closest("[data-yangdo-wizard-next]") : null;
          if (nextButton) {{
            const currentIndex = Number(nextButton.getAttribute("data-yangdo-wizard-next") || 0);
            if (currentIndex >= yangdoWizardStepsMeta.length - 1) {{
              const estimateButton = $("btn-estimate");
              if (estimateButton && !estimateButton.disabled) estimateButton.click();
              return;
            }}
            setYangdoWizardStep(currentIndex + 1, true);
            return;
          }}
          const trackButton = target && target.closest ? target.closest("[data-yangdo-wizard-track]") : null;
          if (trackButton) {{
            setYangdoWizardStep(Number(trackButton.getAttribute("data-yangdo-wizard-track") || 0), true);
          }}
        }});
        wizardShell.addEventListener("keydown", (event) => {{
          const target = event.target;
          const actionReason = target && target.closest ? target.closest("[data-yangdo-action-reason]") : null;
          if (!actionReason) return;
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          runYangdoWizardNextAction("reason");
        }});
      }}
      const ensureConsultConsent = () => {{
        const node = $("consult-consent");
        if (!node) return true;
        if (node.checked) return true;
        alert("개인정보 수집·이용 안내 동의 후 상담 요청을 진행해 주세요.");
        return false;
      }};
      let _skeletonTimer = null;
      let _skeletonActive = false;
      const _skeletonSteps = [
        "재무 비율 분석 중...",
        "행정처분 이력 확인 중...",
        "시장 평균 비교 중...",
        "유사 사례 매칭 중...",
        "최종 가격 산정 중...",
      ];
      const startSkeletonProgress = () => {{
        let idx = 0;
        _skeletonActive = true;
        const note = $("risk-note");
        if (!note) return;
        note.style.transition = "opacity 0.18s ease";
        const show = () => {{
          if (!_skeletonActive) return;
          if (idx >= _skeletonSteps.length) idx = _skeletonSteps.length - 1;
          note.style.opacity = "0.6";
          setTimeout(() => {{
            if (!_skeletonActive) return;
            note.textContent = _skeletonSteps[idx];
            note.style.opacity = "1";
            idx++;
          }}, 120);
        }};
        show();
        _skeletonTimer = setInterval(show, 380);
      }};
      const stopSkeletonProgress = () => {{
        _skeletonActive = false;
        if (_skeletonTimer) {{ clearInterval(_skeletonTimer); _skeletonTimer = null; }}
        const note = $("risk-note");
        if (note) note.style.transition = "";
      }};
      const setEstimateBusy = (busy) => {{
        const btn = $("btn-estimate");
        if (!btn) return;
        isEstimating = !!busy;
        btn.disabled = !!busy;
        btn.style.opacity = busy ? "0.72" : "";
        btn.style.cursor = busy ? "wait" : "";
        btn.textContent = busy ? "AI 계산 중..." : "AI 예상 양도가 계산";
        if (busy) {{ startSkeletonProgress(); }} else {{ stopSkeletonProgress(); }}
      }};

      on("btn-estimate", "click", async () => {{
        if (isEstimating) return;
        const nowTs = Date.now();
        if ((nowTs - lastEstimateClickAt) < 700) return;
        lastEstimateClickAt = nowTs;
        clearRecommendAutoLoop();
        setEstimateBusy(true);
        try {{
          setMeta();
          const out = await estimate();
          if (out.error) {{
            $("out-center").textContent = "-";
            $("out-range").textContent = "-";
            $("out-cash-due").textContent = "-";
            $("out-realizable-balance").textContent = "-";
            $("out-confidence").textContent = "-";
            $("out-neighbors").textContent = "-";
            $("out-source-tier").textContent = "-";
            renderYoyCompare(null);
            renderResultReasonChips(null);
            $("risk-note").textContent = out.error;
            renderSettlementPanel(null);
            const hotCta = $("hot-match-cta");
            if (hotCta) hotCta.style.display = "none";
            if (out.error.indexOf("입력된 정보가 없습니다") >= 0) {{
              alert(out.error);
            }}
            lastEstimate = null;
            renderRecommendedListings([], null);
            renderNeighbors([]);
            renderActionSteps(out, out.target || null);
            syncResultShareActions(false);
            sendUsageLog(out.target || null, null, "error", out.error || "");
            syncConsultSummary();
            pendingResultPanelScroll = false;
            return;
          }}
          lastEstimate = out;
          const publicCenter = num(out.publicCenter);
          const publicLow = num(out.publicLow);
          const publicHigh = num(out.publicHigh);
          const publicRangeVisible = Number.isFinite(publicLow) && Number.isFinite(publicHigh);
          $("out-center").textContent = Number.isFinite(publicCenter) ? fmtEok(publicCenter) : (publicRangeVisible ? "범위 먼저 보기" : "먼저 확인 필요");
          $("out-range").textContent = (Number.isFinite(publicLow) && Number.isFinite(publicHigh))
            ? buildDisplayRange(publicLow, publicHigh).text
            : "사례 더 필요";
          const publicCashDue = num(out.public_estimated_cash_due_eok ?? out.estimated_cash_due_eok);
          const publicCashLow = num(out.public_estimated_cash_due_low_eok);
          const publicCashHigh = num(out.public_estimated_cash_due_high_eok);
          const publicCashRangeVisible = Number.isFinite(publicCashLow) && Number.isFinite(publicCashHigh);
          $("out-cash-due").textContent = Number.isFinite(publicCashDue) ? fmtEok(publicCashDue) : (publicCashRangeVisible ? "범위 먼저 보기" : "먼저 확인 필요");
          const displayBalance = (out && out.target && out.target.balance_excluded)
            ? num((out.target.input_balance_eok ?? out.target.balance_eok) ?? out.raw_balance_input_eok ?? out.balance_reference_eok)
            : num(out.realizable_balance_eok);
          $("out-realizable-balance").textContent = Number.isFinite(displayBalance)
            ? fmtEok(displayBalance)
            : "-";
          $("out-confidence").textContent = out.confidence;
          const neighborCountText = Number.isFinite(Number(out.neighbor_count))
            ? Number(out.neighbor_count)
            : ((out.neighbors && out.neighbors.length) ? out.neighbors.length : 0);
          $("out-neighbors").textContent = `${{neighborCountText}}건`;
          $("out-source-tier").textContent = compact(out.priceSourceLabel || out.priceSourceTier || "-");
          renderYoyCompare(out);
          renderResultReasonChips(out);
          $("risk-note").innerHTML = buildPublicResultMessage(out);
          renderSettlementPanel(out);
          renderRecommendedListings(out.recommendedListings, out);
          renderNeighbors(out.neighbors);
          updateHotMatchCta(out);
          renderActionSteps(out);
          syncResultShareActions(true);
          sendUsageLog(out.target || null, out, "ok", "");
          syncConsultSummary();
          persistDraft();
          flushPendingResultPanelScroll();
        }} catch (e) {{
          const msg = (e && e.message) ? String(e.message) : "unknown_error";
          $("out-center").textContent = "-";
          $("out-range").textContent = "-";
          $("out-cash-due").textContent = "-";
          $("out-realizable-balance").textContent = "-";
          $("out-confidence").textContent = "-";
          $("out-neighbors").textContent = "-";
          $("out-source-tier").textContent = "-";
          renderYoyCompare(null);
          renderResultReasonChips(null);
          $("risk-note").textContent = "계산 중 예외가 발생했습니다. 잠시 후 다시 시도해 주세요.";
          renderSettlementPanel(null);
          renderRecommendedListings([], null);
          renderNeighbors([]);
          renderActionSteps(null);
          syncResultShareActions(false);
          sendUsageLog(null, null, "error", msg);
          pendingResultPanelScroll = false;
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
      on("btn-openchat-consult", "click", async () => {{
        if (!lastEstimate) {{
          alert("먼저 예상 양도가 계산을 완료하면 결과 요약을 함께 보낼 수 있습니다.");
        }}
        if (!ensureConsultConsent()) return;
        const payload = buildConsultPayload();
        openOpenchatWithSummary(payload);
      }});
      on("btn-openchat-result", "click", async () => {{
        if (!lastEstimate) {{
          alert("먼저 예상 양도가 계산을 완료해 주세요.");
          return;
        }}
        openOpenchatWithSummary(buildConsultPayload());
      }});
      on("btn-copy-result", "click", async () => {{
        if (!lastEstimate) {{
          alert("먼저 예상 양도가 계산을 완료해 주세요.");
          return;
        }}
        const ok = await copyText(buildConsultPayload().body);
        alert(ok ? "결과 요약이 복사되었습니다." : "결과 요약 복사에 실패했습니다.");
      }});
      on("btn-copy-brief", "click", async () => {{
        if (!lastEstimate) {{
          alert("먼저 예상 양도가 계산을 완료해 주세요.");
          return;
        }}
        const ok = await copyText(buildConsultPayload().brief);
        alert(ok ? "한 줄 브리프가 복사되었습니다." : "한 줄 브리프 복사에 실패했습니다.");
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
      on("btn-hot-match", "click", async () => {{
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
        const ok = await copyText(payload.body);
        alert(ok ? "상세 리포트 요약이 복사되었습니다. 상담 요청 양식에 연락처를 입력한 뒤 전송해 주세요." : "요약 복사에 실패했습니다. 상담 요청 영역에서 다시 시도해 주세요.");
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
            headers: buildApiHeaders({{ "Content-Type": "application/json" }}),
            body: JSON.stringify({{
              source: YANGDO_SOURCE_TAG,
              page_mode: YANGDO_PAGE_MODE,
              source_mode: viewMode,
              service_track: YANGDO_SERVICE_TRACK,
              business_domain: YANGDO_BUSINESS_DOMAIN,
              subject: payload.subject,
              summary_text: payload.body,
              customer_name: payload.name,
              customer_phone: payload.phone,
              customer_email: payload.email,
              customer_note: payload.note,
              license_text: payload.license,
              input_reorg_mode: payload.reorg_mode,
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
        const ok = await copyText(payload.body);
        alert(ok ? "상담 요약이 복사되었습니다." : "상담 요약 복사에 실패했습니다.");
      }});
      const _debouncedSyncConsult = _debounce(syncConsultSummary, 300);
      ["consult-name", "consult-phone", "consult-email", "consult-note", "in-reorg-mode", "in-balance-usage-mode", "in-company-type", "in-credit-level", "in-admin-history", "in-scale-search-mode", "in-specialty", "in-sales-input-mode", "in-sales3-total", "in-sales5-total", "in-y23", "in-y24", "in-y25", "in-balance", "in-capital", "in-surplus"].forEach((id) => {{
        const el = $(id);
        if (!el) return;
        el.addEventListener("input", _debouncedSyncConsult);
        el.addEventListener("change", syncConsultSummary);
      }});
      on("in-license", "input", () => {{
        syncLicenseAutoProfile(false);
        syncReorgModeRequirement();
        syncConsultSummary();
      }});
      on("in-license", "change", () => {{
        syncLicenseAutoProfile(false);
        syncReorgModeRequirement();
        syncConsultSummary();
      }});
      on("in-reorg-mode", "change", syncReorgModeRequirement);
      document.querySelectorAll("[data-reorg-choice]").forEach((button) => {{
        button.addEventListener("click", () => {{
          const reorgNode = $("in-reorg-mode");
          const value = compact(button.getAttribute("data-reorg-choice"));
          if (!reorgNode || !value) return;
          reorgNode.value = value;
          reorgNode.dispatchEvent(new Event("change", {{ bubbles: true }}));
        }});
      }});
      on("in-balance-usage-mode", "change", syncConsultSummary);
      on("in-sales-input-mode", "change", () => {{
        const modeNode = $("in-sales-input-mode");
        if (modeNode && modeNode.dataset.autoApplying !== "1") {{
          modeNode.dataset.splitManualMode = "1";
          delete modeNode.dataset.splitAutoSelected;
        }}
        syncSalesInputModeUi();
        syncReorgModeRequirement();
        syncConsultSummary();
      }});
      document.querySelectorAll("#seoulmna-yangdo-calculator .scale-mode-btn").forEach((btn) => {{
        if (!btn) return;
        btn.addEventListener("click", () => {{
          const mode = compact(btn.getAttribute("data-scale-mode")) === "sales" ? "sales" : "specialty";
          setScaleSearchMode(mode);
          syncScaleSearchModeUi();
          syncConsultSummary();
          persistDraft();
        }});
      }});
      on("btn-apply-license-profile", "click", () => {{
        syncLicenseAutoProfile(true);
        syncConsultSummary();
        persistDraft();
      }});
      ["in-balance", "in-capital", "in-surplus"].forEach((id) => {{
        const node = $(id);
        if (!node) return;
        const markManual = () => {{
          if (node.dataset.applyingAuto === "1") return;
          if (compact(node.value)) {{
            node.dataset.manual = "1";
            delete node.dataset.autofill;
          }} else {{
            delete node.dataset.manual;
            delete node.dataset.autofill;
          }}
          syncLicenseAutoProfile(false);
          syncConsultSummary();
        }};
        node.addEventListener("input", markManual);
        node.addEventListener("change", markManual);
      }});
      const _debouncedPersistDraft = _debounce(persistDraft, 800);
      draftFieldIds.forEach((id) => {{
        const el = $(id);
        if (!el) return;
        el.addEventListener("input", _debouncedPersistDraft);
        el.addEventListener("change", persistDraft);
      }});
      ["in-specialty", "in-sales3-total", "in-balance", "in-capital"].forEach((id) => {{
        const el = $(id);
        if (!el) return;
        const handle = () => maybeRunRecommendAutoLoop(id);
        const debouncedHandle = _debounce(handle, 500);
        el.addEventListener("input", debouncedHandle);
        el.addEventListener("change", handle);
      }});
      draftToggleIds.forEach((id) => {{
        const el = $(id);
        if (!el) return;
        el.addEventListener("change", persistDraft);
      }});
      const _debouncedWizardSync = _debounce(syncYangdoWizard, 250);
      [
        "in-license", "in-specialty", "in-sales-input-mode", "in-y23", "in-y24", "in-y25",
        "in-sales3-total", "in-sales5-total", "in-balance", "in-capital", "in-reorg-mode",
        "in-balance-usage-mode", "in-license-year", "in-surplus", "in-debt-level", "in-liq-level",
        "in-company-type", "in-credit-level", "in-admin-history", "ok-capital", "ok-engineer", "ok-office",
      ].forEach((id) => {{
        const el = $(id);
        if (!el) return;
        el.addEventListener("input", _debouncedWizardSync);
        el.addEventListener("change", syncYangdoWizard);
      }});
      on("btn-reset", "click", resetForm);
      on("draft-restore-action", "click", resetForm);
      const runRecommendFollowupAction = (actionNode) => {{
        const actionKind = compact(actionNode && actionNode.dataset.focusAction);
        if (actionKind === "market") {{
          const listingsSection = document.querySelector(".result-panel .neighbor-panel, .neighbor-panel, #neighbor-panel");
          if (listingsSection && typeof listingsSection.scrollIntoView === "function") {{
            listingsSection.scrollIntoView({{ behavior: "smooth", block: "start" }});
          }} else {{
            const resultPanel = $("result-panel");
            if (resultPanel && typeof resultPanel.scrollIntoView === "function") {{
              resultPanel.scrollIntoView({{ behavior: "smooth", block: "start" }});
            }}
          }}
          return;
        }}
        if (actionKind === "specialty") {{
          focusRecommendSpecialtyRefinement();
        }} else if (actionKind === "balance") {{
          focusRecommendBalanceRefinement();
        }} else if (actionKind === "capital") {{
          focusRecommendCapitalRefinement();
        }} else {{
          focusRecommendSales3Refinement();
        }}
        window.setTimeout(() => {{
          armRecommendAutoLoop(actionKind || "sales3");
        }}, 120);
        persistDraft();
      }};
      on("recommend-panel-followup-action", "click", () => {{
        runRecommendFollowupAction($("recommend-panel-followup-action"));
      }});
      on("recommend-panel-followup-secondary-action", "click", () => {{
        runRecommendFollowupAction($("recommend-panel-followup-secondary-action"));
      }});
      on("draft-restore-estimate-action", "click", () => {{
        pendingResultPanelScroll = true;
        const estimateButton = $("btn-estimate");
        if (estimateButton && !estimateButton.disabled) estimateButton.click();
      }});
      const topChat = $("btn-openchat-top");
      const topCall = $("btn-call-top");
      if (topChat) {{
        topChat.addEventListener("click", () => openOpenchatWithSummary(buildConsultPayload()));
      }}
      if (topCall) {{
        const displayPhone = consultPhone || "1668-3548";
        const digits = displayPhone.replace(/[^0-9]/g, "");
        topCall.textContent = displayPhone;
        if (digits) {{
          topCall.href = `tel:${{digits}}`;
        }}
      }}
      const targetEmailNode = $("consult-target-email");
      if (targetEmailNode) targetEmailNode.textContent = consultEmail;
      const phoneNode = $("contact-phone-display");
      if (phoneNode) phoneNode.textContent = consultPhone || "1668-3548";
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
      window.__yangdoQaHooks = {{
        renderRecommendedListings,
        renderActionSteps,
        runRecommendFollowupAction,
        focusRecommendSales3Refinement,
        focusRecommendSpecialtyRefinement,
        focusRecommendBalanceRefinement,
        focusRecommendCapitalRefinement,
      }};
      renderNeighborHead();
      syncNeighborPanelDisclosure(true);
      draftRestored = restoreDraft();
      setScaleSearchMode(compact(($("in-scale-search-mode") || {{}}).value) || "specialty");
      syncScaleSearchModeUi();
      syncReorgModeRequirement();
      renderRecommendedListings([]);
      renderActionSteps(null);
      renderYoyCompare(null);
      syncResultShareActions(false);
      syncConsultSummary();
      syncYangdoWizard();
      setYangdoWizardStep(draftRestored ? findYangdoWizardResumeStep() : 0, draftRestored);
      (() => {{
        const container = $("trust-signal-items");
        const metaNode = $("trust-signal-meta");
        if (!container || !dataset.length) return;
        const byToken = {{}};
        dataset.forEach((row) => {{
          const tokens = Array.isArray(row.tokens) ? row.tokens : [];
          const price = num(row.price_eok);
          if (!Number.isFinite(price) || price <= 0) return;
          const key = tokens.length === 1 ? compact(tokens[0]) : compact(row.license_text || "");
          if (!key) return;
          if (!byToken[key]) byToken[key] = [];
          byToken[key].push(price);
        }});
        const entries = Object.entries(byToken)
          .filter(([, prices]) => prices.length >= 2)
          .sort((a, b) => b[1].length - a[1].length)
          .slice(0, 6);
        if (!entries.length) return;
        const fmtP = (v) => v >= 1 ? v.toFixed(1) + "억" : Math.round(v * 10000).toLocaleString() + "만";
        entries.forEach(([label, prices]) => {{
          prices.sort((a, b) => a - b);
          const mid = prices[Math.floor(prices.length / 2)];
          const chip = document.createElement("span");
          chip.className = "trust-signal-chip";
          chip.innerHTML = `<span class="ts-label">${{escapeHtml(label)}}</span><span class="ts-value">${{fmtP(mid)}}</span>`;
          container.appendChild(chip);
        }});
        if (metaNode) {{
          metaNode.textContent = `${{dataset.length}}건 매물 기준 · 업종별 중앙 시세`;
        }}
      }})();
    }})();
  </script>
  <script>
    /* Widget ↔ Platform PostMessage child-side (iframe → parent) */
    (function() {{
      if (window.self === window.top) return;
      var root = document.getElementById("seoulmna-yangdo-calculator");
      try {{ window.parent.postMessage({{ type: "widget-ready" }}, "*"); }} catch (_e) {{}}
      if (typeof ResizeObserver !== "undefined" && root) {{
        var lastH = 0;
        new ResizeObserver(function(entries) {{
          var h = Math.ceil(entries[0].contentRect.height);
          if (Math.abs(h - lastH) > 20) {{
            lastH = h;
            try {{ window.parent.postMessage({{ type: "widget-resize", height: h }}, "*"); }} catch (_e) {{}}
          }}
        }}).observe(root);
      }}
    }})();
  </script>
</section>"""
    return _collapse_script_whitespace(html)


