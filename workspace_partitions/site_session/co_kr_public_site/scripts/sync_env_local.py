#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / ".env.local"
DEFAULT_EXAMPLE = PROJECT_ROOT / ".env.example"


def find_workspace_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / ".env").exists() and (candidate / "tenant_config" / "channel_profiles.json").exists():
            return candidate
    return start


WORKSPACE_ROOT = find_workspace_root(PROJECT_ROOT)
ROOT_ENV_PATH = WORKSPACE_ROOT / ".env"
CHANNELS_PATH = WORKSPACE_ROOT / "tenant_config" / "channel_profiles.json"


def read_env_file(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    if not path.exists():
        return payload

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = str(raw_line or "").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip().lstrip("\ufeff")] = value.strip()
    return payload


def load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def normalize_host(value: str) -> str:
    text = str(value or "").strip().rstrip("/")
    if not text:
        return ""
    if "://" not in text:
        return f"https://{text}"
    return text


def coalesce(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def is_placeholder_value(*, key: str, value: str, example_value: str, mode: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    if text == str(example_value or "").strip():
        return True
    lowered = text.lower()
    if key == "NEXT_PUBLIC_CONTACT_EMAIL" and lowered.endswith("@example.com"):
        return True
    if key == "NEXT_PUBLIC_KAKAO_URL" and "your-room-id" in lowered:
        return True
    if key == "NEXT_PUBLIC_SITE_HOST" and mode == "production" and "example.com" in lowered:
        return True
    return False


def find_channel(payload: dict[str, Any], channel_id: str) -> dict[str, Any]:
    wanted = str(channel_id or "").strip().lower()
    for item in payload.get("channels") or []:
        if isinstance(item, dict) and str(item.get("channel_id") or "").strip().lower() == wanted:
            return item
    return {}


def build_env_map(
    *,
    channel: dict[str, Any],
    example_env: dict[str, str],
    root_env: dict[str, str],
    existing_env: dict[str, str],
    mode: str,
    explicit_site_host: str,
) -> dict[str, str]:
    branding = channel.get("branding") if isinstance(channel.get("branding"), dict) else {}

    preview_host = normalize_host(
        coalesce(
            explicit_site_host if mode == "preview" else "",
            example_env.get("NEXT_PUBLIC_SITE_HOST"),
            "https://seoulmna-public.example.com",
        )
    )
    production_host = normalize_host(
        coalesce(
            explicit_site_host if mode == "production" else "",
            root_env.get("MAIN_SITE"),
            branding.get("site_url"),
            channel.get("canonical_public_host"),
        )
    )

    site_host = production_host if mode == "production" and production_host else preview_host
    platform_host = normalize_host(
        coalesce(
            channel.get("platform_front_host"),
            root_env.get("GUIDE_LINK"),
            example_env.get("NEXT_PUBLIC_PLATFORM_HOST"),
            "https://seoulmna.kr",
        )
    )

    resolved = {
        "NEXT_PUBLIC_SITE_HOST": site_host,
        "NEXT_PUBLIC_PLATFORM_HOST": platform_host,
        "NEXT_PUBLIC_COMPANY_NAME": coalesce(
            root_env.get("BRAND_NAME"),
            branding.get("brand_name"),
            example_env.get("NEXT_PUBLIC_COMPANY_NAME"),
        ),
        "NEXT_PUBLIC_REPRESENTATIVE_NAME": coalesce(
            root_env.get("CONSULTANT_NAME"),
            example_env.get("NEXT_PUBLIC_REPRESENTATIVE_NAME"),
        ),
        "NEXT_PUBLIC_BUSINESS_NUMBER": coalesce(
            root_env.get("BUSINESS_NUMBER"),
            example_env.get("NEXT_PUBLIC_BUSINESS_NUMBER"),
        ),
        "NEXT_PUBLIC_MAIL_ORDER_NUMBER": coalesce(
            root_env.get("MAIL_ORDER_NUMBER"),
            example_env.get("NEXT_PUBLIC_MAIL_ORDER_NUMBER"),
        ),
        "NEXT_PUBLIC_CONTACT_PHONE": coalesce(
            branding.get("contact_phone"),
            root_env.get("CONTACT_PHONE"),
            example_env.get("NEXT_PUBLIC_CONTACT_PHONE"),
        ),
        "NEXT_PUBLIC_CONTACT_MOBILE": coalesce(
            root_env.get("PHONE"),
            example_env.get("NEXT_PUBLIC_CONTACT_MOBILE"),
        ),
        "NEXT_PUBLIC_CONTACT_EMAIL": coalesce(
            branding.get("contact_email"),
            root_env.get("CONTACT_EMAIL"),
            example_env.get("NEXT_PUBLIC_CONTACT_EMAIL"),
        ),
        "NEXT_PUBLIC_KAKAO_URL": coalesce(
            root_env.get("KAKAO_OPENCHAT_URL"),
            branding.get("openchat_url"),
            example_env.get("NEXT_PUBLIC_KAKAO_URL"),
        ),
        "NEXT_PUBLIC_COMPANY_ADDRESS": coalesce(
            root_env.get("COMPANY_ADDRESS"),
            example_env.get("NEXT_PUBLIC_COMPANY_ADDRESS"),
        ),
        "NEXT_PUBLIC_OFFICE_HOURS": coalesce(
            root_env.get("OFFICE_HOURS"),
            example_env.get("NEXT_PUBLIC_OFFICE_HOURS"),
        ),
        "NEXT_PUBLIC_GA_MEASUREMENT_ID": coalesce(
            existing_env.get("NEXT_PUBLIC_GA_MEASUREMENT_ID"),
            root_env.get("GA_MEASUREMENT_ID"),
            example_env.get("NEXT_PUBLIC_GA_MEASUREMENT_ID"),
        ),
        "CONSULT_WEBHOOK_URL": coalesce(
            existing_env.get("CONSULT_WEBHOOK_URL"),
            root_env.get("CONSULT_WEBHOOK_URL"),
            example_env.get("CONSULT_WEBHOOK_URL"),
        ),
    }

    merged = dict(resolved)
    for key, value in existing_env.items():
        if not is_placeholder_value(
            key=key,
            value=str(value or ""),
            example_value=example_env.get(key, ""),
            mode=mode,
        ):
            merged[key] = value
    return merged


def render_env(env_map: dict[str, str]) -> str:
    ordered_keys = [
        "NEXT_PUBLIC_SITE_HOST",
        "NEXT_PUBLIC_PLATFORM_HOST",
        "NEXT_PUBLIC_COMPANY_NAME",
        "NEXT_PUBLIC_REPRESENTATIVE_NAME",
        "NEXT_PUBLIC_BUSINESS_NUMBER",
        "NEXT_PUBLIC_MAIL_ORDER_NUMBER",
        "NEXT_PUBLIC_CONTACT_PHONE",
        "NEXT_PUBLIC_CONTACT_MOBILE",
        "NEXT_PUBLIC_CONTACT_EMAIL",
        "NEXT_PUBLIC_KAKAO_URL",
        "NEXT_PUBLIC_COMPANY_ADDRESS",
        "NEXT_PUBLIC_OFFICE_HOURS",
        "NEXT_PUBLIC_GA_MEASUREMENT_ID",
        "CONSULT_WEBHOOK_URL",
    ]
    lines = [f"{key}={env_map.get(key, '')}" for key in ordered_keys]
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync co_kr_public_site .env.local from workspace config.")
    parser.add_argument("--channel-id", default="seoul_widget_internal")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--mode", choices=["preview", "production"], default="preview")
    parser.add_argument("--site-host", default="")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(str(args.output)).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    example_env = read_env_file(DEFAULT_EXAMPLE)
    root_env = read_env_file(ROOT_ENV_PATH)
    existing_env = read_env_file(output_path)
    channels = load_json(CHANNELS_PATH)
    channel = find_channel(channels if isinstance(channels, dict) else {}, str(args.channel_id))
    if not channel:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "channel_not_found",
                    "channelId": str(args.channel_id),
                    "channelsPath": str(CHANNELS_PATH),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    env_map = build_env_map(
        channel=channel,
        example_env=example_env,
        root_env=root_env,
        existing_env=existing_env,
        mode=str(args.mode),
        explicit_site_host=str(args.site_host),
    )
    content = render_env(env_map)
    if not args.dry_run:
        output_path.write_text(content, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "mode": str(args.mode),
                "channelId": str(args.channel_id),
                "output": str(output_path),
                "workspaceRoot": str(WORKSPACE_ROOT),
                "rootEnvPath": str(ROOT_ENV_PATH),
                "preservedKeys": sorted(
                    [
                        key
                        for key, value in existing_env.items()
                        if not is_placeholder_value(
                            key=key,
                            value=str(value or ""),
                            example_value=example_env.get(key, ""),
                            mode=str(args.mode),
                        )
                    ]
                ),
                "env": env_map,
                "dryRun": bool(args.dry_run),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
