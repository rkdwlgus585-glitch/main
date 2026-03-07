import argparse
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = ROOT / ".env"
DEFAULT_BACKUP_DIR = ROOT / "snapshots"

KEY_FIELDS = (
    "YANGDO_WIDGET_API_KEY",
    "YANGDO_CONSULT_API_KEY",
    "YANGDO_BLACKBOX_API_KEY",
    "YANGDO_BLACKBOX_ADMIN_API_KEY",
)


def _read_env_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _parse_env_map(lines: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw in lines:
        line = str(raw or "").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _upsert_env(lines: List[str], updates: Dict[str, str]) -> List[str]:
    pending = dict(updates)
    out: List[str] = []
    for raw in lines:
        if "=" not in raw:
            out.append(raw)
            continue
        k = raw.split("=", 1)[0].strip()
        if k in pending:
            out.append(f"{k}={pending.pop(k)}")
        else:
            out.append(raw)
    if pending:
        if out and out[-1].strip():
            out.append("")
        out.append("# === Auto-added by security_key_manager.py ===")
        for k in sorted(pending.keys()):
            out.append(f"{k}={pending[k]}")
    return out


def _first_key(raw: str) -> str:
    for piece in str(raw or "").split(","):
        token = piece.strip()
        if token:
            if ":" in token:
                token = token.split(":", 1)[1].strip()
            if token:
                return token
    return ""


def _build_key_ring(new_key: str, old_raw: str, keep_old: bool) -> str:
    old = _first_key(old_raw)
    if keep_old and old and old != new_key:
        return f"{new_key},{old}"
    return new_key


def _new_key() -> str:
    return secrets.token_urlsafe(36)


def _mask(value: str) -> str:
    token = _first_key(value)
    if not token:
        return ""
    if len(token) <= 8:
        return "*" * len(token)
    return token[:4] + "*" * (len(token) - 8) + token[-4:]


def _backup_env(env_path: Path, backup_dir: Path) -> str:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = backup_dir / f"{env_path.stem}_security_backup_{stamp}{env_path.suffix or '.env'}"
    if env_path.exists():
        out.write_text(env_path.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        out.write_text("", encoding="utf-8")
    return str(out)


def cmd_bootstrap(env_path: Path, force: bool) -> Dict[str, object]:
    lines = _read_env_lines(env_path)
    env = _parse_env_map(lines)

    existing_widget = _first_key(env.get("YANGDO_WIDGET_API_KEY", ""))
    existing_public = _first_key(env.get("YANGDO_CONSULT_API_KEY", "")) or _first_key(env.get("YANGDO_BLACKBOX_API_KEY", ""))
    existing_admin = _first_key(env.get("YANGDO_BLACKBOX_ADMIN_API_KEY", ""))

    widget_key = _new_key() if force or (not existing_widget and not existing_public) else (existing_widget or existing_public)
    admin_key = _new_key() if force or not existing_admin else existing_admin

    updates = {
        "YANGDO_WIDGET_API_KEY": widget_key,
        "YANGDO_CONSULT_API_KEY": widget_key,
        "YANGDO_BLACKBOX_API_KEY": widget_key,
        "YANGDO_BLACKBOX_ADMIN_API_KEY": admin_key,
        "YANGDO_CONSULT_MAX_BODY_BYTES": env.get("YANGDO_CONSULT_MAX_BODY_BYTES", "131072") or "131072",
        "YANGDO_CONSULT_RATE_LIMIT_PER_MIN": env.get("YANGDO_CONSULT_RATE_LIMIT_PER_MIN", "120") or "120",
        "YANGDO_CONSULT_TRUST_X_FORWARDED_FOR": env.get("YANGDO_CONSULT_TRUST_X_FORWARDED_FOR", "false") or "false",
        "YANGDO_CONSULT_SECURITY_LOG_FILE": env.get("YANGDO_CONSULT_SECURITY_LOG_FILE", "logs/security_consult_events.jsonl") or "logs/security_consult_events.jsonl",
        "YANGDO_BLACKBOX_MAX_BODY_BYTES": env.get("YANGDO_BLACKBOX_MAX_BODY_BYTES", "65536") or "65536",
        "YANGDO_BLACKBOX_RATE_LIMIT_PER_MIN": env.get("YANGDO_BLACKBOX_RATE_LIMIT_PER_MIN", "90") or "90",
        "YANGDO_BLACKBOX_TRUST_X_FORWARDED_FOR": env.get("YANGDO_BLACKBOX_TRUST_X_FORWARDED_FOR", "false") or "false",
        "YANGDO_BLACKBOX_SECURITY_LOG_FILE": env.get("YANGDO_BLACKBOX_SECURITY_LOG_FILE", "logs/security_blackbox_events.jsonl") or "logs/security_blackbox_events.jsonl",
        "YANGDO_CONSULT_ALLOW_ORIGINS": env.get(
            "YANGDO_CONSULT_ALLOW_ORIGINS",
            "https://seoulmna.kr,https://www.seoulmna.kr,https://seoulmna.co.kr,https://www.seoulmna.co.kr",
        )
        or "https://seoulmna.kr,https://www.seoulmna.kr,https://seoulmna.co.kr,https://www.seoulmna.co.kr",
        "YANGDO_BLACKBOX_ALLOW_ORIGINS": env.get(
            "YANGDO_BLACKBOX_ALLOW_ORIGINS",
            "https://seoulmna.kr,https://www.seoulmna.kr,https://seoulmna.co.kr,https://www.seoulmna.co.kr",
        )
        or "https://seoulmna.kr,https://www.seoulmna.kr,https://seoulmna.co.kr,https://www.seoulmna.co.kr",
    }
    merged = _upsert_env(lines, updates)
    env_path.write_text("\n".join(merged).rstrip() + "\n", encoding="utf-8")
    return {
        "action": "bootstrap",
        "updated": True,
        "masked": {k: _mask(updates[k]) for k in KEY_FIELDS},
    }


def cmd_rotate(env_path: Path, keep_old: bool) -> Dict[str, object]:
    lines = _read_env_lines(env_path)
    env = _parse_env_map(lines)
    new_widget = _new_key()
    new_admin = _new_key()

    updates = {
        "YANGDO_WIDGET_API_KEY": new_widget,
        "YANGDO_CONSULT_API_KEY": _build_key_ring(new_widget, env.get("YANGDO_CONSULT_API_KEY", ""), keep_old=keep_old),
        "YANGDO_BLACKBOX_API_KEY": _build_key_ring(new_widget, env.get("YANGDO_BLACKBOX_API_KEY", ""), keep_old=keep_old),
        "YANGDO_BLACKBOX_ADMIN_API_KEY": _build_key_ring(new_admin, env.get("YANGDO_BLACKBOX_ADMIN_API_KEY", ""), keep_old=keep_old),
    }
    merged = _upsert_env(lines, updates)
    env_path.write_text("\n".join(merged).rstrip() + "\n", encoding="utf-8")
    return {
        "action": "rotate",
        "updated": True,
        "keep_old": bool(keep_old),
        "masked": {k: _mask(updates[k]) for k in KEY_FIELDS},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap and rotate security API keys in .env")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV))
    parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR))
    parser.add_argument("--mode", choices=["bootstrap", "rotate"], default="bootstrap")
    parser.add_argument("--force", action="store_true", help="Regenerate keys even when already present (bootstrap mode).")
    parser.add_argument("--keep-old", action="store_true", help="Keep previous first key as fallback in key ring (rotate mode).")
    args = parser.parse_args()

    env_path = Path(str(args.env_file)).resolve()
    backup_dir = Path(str(args.backup_dir)).resolve()
    backup_path = _backup_env(env_path, backup_dir)

    if args.mode == "bootstrap":
        result = cmd_bootstrap(env_path, force=bool(args.force))
    else:
        result = cmd_rotate(env_path, keep_old=bool(args.keep_old))

    result["env_file"] = str(env_path)
    result["backup_file"] = backup_path
    result["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
