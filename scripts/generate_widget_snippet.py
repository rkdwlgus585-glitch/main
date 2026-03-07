#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core_engine.channel_branding import resolve_channel_branding
from scripts.plan_channel_embed import DEFAULT_CHANNELS, DEFAULT_ENV, DEFAULT_REGISTRY, plan_embed
from scripts.validate_tenant_onboarding import _load_json

WIDGET_DEFAULTS = {
    "yangdo": {
        "title": "\u0041\u0049 \uc591\ub3c4\uac00 \uc0b0\uc815 \uacc4\uc0b0\uae30",
        "subtitle": "\uac74\uc124\uc5c5 \uba74\ud5c8 \uc591\ub3c4 \uac00\uaca9 \ubc94\uc704\ub97c \ube60\ub974\uac8c \ud655\uc778",
        "cta_label": "\uc591\ub3c4\uac00 \uacc4\uc0b0\uae30 \uc5f4\uae30",
        "min_height": 1280,
    },
    "permit": {
        "title": "\u0041\u0049 \uc778\ud5c8\uac00 \uc0ac\uc804\uac80\ud1a0",
        "subtitle": "\ub4f1\ub85d\uae30\uc900 \ucda9\uc871 \uc5ec\ubd80\uc640 \uc900\ube44 \ud56d\ubaa9\uc744 \ube60\ub974\uac8c \uc810\uac80",
        "cta_label": "\uc0ac\uc804\uac80\ud1a0 \uc2dc\uc791",
        "min_height": 1420,
    },
}


def _channel_row_by_id(channels_path: str, channel_id: str) -> dict:
    rows = _load_json(Path(str(channels_path or DEFAULT_CHANNELS)).resolve()).get("channels") or []
    wanted = str(channel_id or "").strip().lower()
    for row in rows:
        if isinstance(row, dict) and str(row.get("channel_id") or "").strip().lower() == wanted:
            return dict(row)
    return {}


def _preferred_host_from_channel(row: dict) -> str:
    explicit = str(row.get("canonical_public_host") or "").strip()
    if explicit:
        return explicit.split(":", 1)[0].lower()
    branding = row.get("branding") if isinstance(row.get("branding"), dict) else {}
    site_url = str(branding.get("site_url") or "").strip()
    if site_url:
        try:
            parsed = urlparse(site_url)
        except Exception:
            parsed = None
        candidate = str(parsed.netloc if parsed else "").strip().lower()
        if candidate:
            return candidate.split(":", 1)[0]
    hosts = row.get("channel_hosts") if isinstance(row.get("channel_hosts"), list) else []
    return str(hosts[0] or "").strip() if hosts else ""


def _resolve_host(*, host: str, channel_id: str, channels_path: str) -> str:
    host = str(host or "").strip()
    if host:
        return host
    row = _channel_row_by_id(channels_path, channel_id)
    return _preferred_host_from_channel(row)


def build_launcher_snippet(
    *,
    widget_url: str,
    brand_name: str,
    brand_label: str,
    title: str,
    subtitle: str,
    cta_label: str,
    host_element_id: str = "smna-widget-host",
) -> str:
    return f"""<!-- Widget Launcher START -->
<div id=\"{host_element_id}\"></div>
<script>
(function() {{
  var widgetUrl = {widget_url!r};
  var host = document.getElementById({host_element_id!r});
  if (!host) return;
  host.innerHTML = '' +
    '<div style="position:fixed;right:18px;bottom:18px;z-index:9999;max-width:300px;box-shadow:0 12px 30px rgba(0,0,0,.22);border-radius:16px;overflow:hidden;font-family:Pretendard,\\'Noto Sans KR\\',Arial,sans-serif;background:#fff">' +
    '  <div style="background:linear-gradient(120deg,#0f2742 0%,#17507d 68%,#c89a4b 100%);padding:14px 16px;color:#fff">' +
    '    <div style="font-size:11px;opacity:.92;margin-bottom:4px">{brand_label}</div>' +
    '    <div style="font-size:20px;font-weight:900;line-height:1.25">{title}</div>' +
    '    <div style="font-size:13px;line-height:1.45;margin-top:6px;opacity:.95">{subtitle}</div>' +
    '  </div>' +
    '  <div style="padding:10px 12px;background:#fff;color:#1d1d1f;font-size:12px">{brand_name}</div>' +
    '  <a href="' + widgetUrl + '" target="_blank" rel="noopener noreferrer" style="display:block;text-align:center;padding:13px 14px;font-size:17px;font-weight:900;text-decoration:none;background:#fee500;color:#191919">{cta_label}</a>' +
    '</div>';
}})();
</script>
<!-- Widget Launcher END -->
"""


def build_iframe_snippet(*, widget_url: str, min_height: int) -> str:
    return (
        f'<iframe src="{widget_url}" title="SMNA calculator widget" '
        f'style="width:100%;min-height:{int(min_height)}px;border:0" '
        'sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox" '
        'allow="clipboard-write" '
        'loading="lazy" referrerpolicy="strict-origin-when-cross-origin"></iframe>'
    )


def build_widget_payload(
    *,
    host: str = "",
    origin: str = "",
    channel_id: str = "",
    tenant_id: str = "",
    widget: str = "yangdo",
    mode: str = "iframe",
    registry_path: str = "",
    channels_path: str = "",
    env_path: str = "",
    title: str = "",
    subtitle: str = "",
    cta_label: str = "",
) -> dict:
    widget = str(widget or "yangdo").strip().lower()
    mode = str(mode or "iframe").strip().lower()
    channels_path = str(channels_path or DEFAULT_CHANNELS)
    host = _resolve_host(host=host, channel_id=channel_id, channels_path=channels_path)
    plan = plan_embed(
        host=host,
        origin=origin,
        tenant_id=tenant_id,
        widget=widget,
        registry_path=registry_path or str(DEFAULT_REGISTRY),
        channels_path=channels_path,
        env_path=env_path or str(DEFAULT_ENV),
    )
    defaults = dict(WIDGET_DEFAULTS.get(widget) or WIDGET_DEFAULTS["yangdo"])
    resolved_channel_id = str(plan.get("channel_id") or channel_id or "").strip().lower()
    branding = resolve_channel_branding(channel_id=resolved_channel_id, config_path=channels_path)
    widget_url = str(plan.get("widget_url") or "").strip()
    resolved_title = str(title or defaults["title"]).strip()
    resolved_subtitle = str(subtitle or defaults["subtitle"]).strip()
    resolved_cta = str(cta_label or defaults["cta_label"]).strip()
    snippet = ""
    if bool(plan.get("ok")) and widget_url:
        if mode == "launcher":
            snippet = build_launcher_snippet(
                widget_url=widget_url,
                brand_name=str(branding.get("brand_name") or ""),
                brand_label=str(branding.get("brand_label") or ""),
                title=resolved_title,
                subtitle=resolved_subtitle,
                cta_label=resolved_cta,
            )
        else:
            snippet = build_iframe_snippet(widget_url=widget_url, min_height=int(defaults.get("min_height", 1200)))
    return {
        "ok": bool(plan.get("ok")) and bool(snippet),
        "widget": widget,
        "mode": mode,
        "title": resolved_title,
        "subtitle": resolved_subtitle,
        "cta_label": resolved_cta,
        "channel_id": resolved_channel_id,
        "tenant_id": str(plan.get("tenant_id") or "").strip(),
        "widget_url": widget_url,
        "brand_name": str(branding.get("brand_name") or ""),
        "brand_label": str(branding.get("brand_label") or ""),
        "note": str(plan.get("note") or "").strip(),
        "activation_blockers": list(plan.get("activation_blockers") or []),
        "snippet": snippet,
        "plan": plan,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate widget snippet for yangdo/permit channels")
    parser.add_argument("--host", default="", help="Channel host (e.g. seoulmna.kr)")
    parser.add_argument("--origin", default="", help="Optional origin URL")
    parser.add_argument("--channel-id", default="", help="Channel id override")
    parser.add_argument("--tenant-id", default="", help="Explicit tenant id override")
    parser.add_argument("--widget", default="yangdo", choices=["yangdo", "permit"])
    parser.add_argument("--mode", default="iframe", choices=["iframe", "launcher"])
    parser.add_argument("--title", default="")
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--cta-label", default="")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--channels", default=str(DEFAULT_CHANNELS))
    parser.add_argument("--env-file", default=str(DEFAULT_ENV))
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    payload = build_widget_payload(
        host=args.host,
        origin=args.origin,
        channel_id=args.channel_id,
        tenant_id=args.tenant_id,
        widget=args.widget,
        mode=args.mode,
        registry_path=args.registry,
        channels_path=args.channels,
        env_path=args.env_file,
        title=args.title,
        subtitle=args.subtitle,
        cta_label=args.cta_label,
    )
    if args.output:
        out = Path(str(args.output)).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(str(payload.get("snippet") or ""), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": payload["ok"],
                "widget": payload["widget"],
                "mode": payload["mode"],
                "channel_id": payload["channel_id"],
                "tenant_id": payload["tenant_id"],
                "widget_url": payload["widget_url"],
                "activation_blockers": payload["activation_blockers"],
                "note": payload["note"],
                "output": str(Path(args.output).resolve()) if args.output else "",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not payload["ok"]:
        return 1
    if not args.output:
        print(payload["snippet"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
