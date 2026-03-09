import argparse
import json
import pathlib
import re
from typing import Dict, List, Tuple


ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_SHIMS = sorted(ROOT.glob("*.bat"))
REAL_LAUNCHERS = sorted((ROOT / "launchers").glob("*.bat"))
OPS_RUNNERS = sorted((ROOT / "scripts").glob("*.cmd"))
IGNORE_PARTS = {
    ".git",
    ".venv",
    "archive",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "logs",
    "dist",
    "build",
    "desktop_related",
    "workspace_partitions",
    ".playwright-mcp",
}

CALL_RE = re.compile(r'^\s*call\s+"%~dp0launchers\\([^"]+\.bat)"(?:\s+(.*))?$', re.IGNORECASE)
GROUP_RE = re.compile(r"^\s*::\s*\[GROUP\]\s*([A-Za-z0-9_ -]+)\s*$", re.IGNORECASE)
PY_RE = re.compile(r"^\s*python\s+([^\s]+\.py)\b(.*)$", re.IGNORECASE)
PY_REF_RE = re.compile(r"([A-Za-z0-9_./\\-]+\.py)\b")
DELEGATE_BATCH_RE = re.compile(
    r"^\s*(?:call\s+)?(?:\"([^\"]+\.bat)\"|([^\"\s]+\.bat))(?:\s+.*)?$",
    re.IGNORECASE,
)


def _safe_read(path: pathlib.Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _parse_root_shim(path: pathlib.Path) -> Dict[str, str]:
    text = _safe_read(path)
    target = ""
    args = ""
    group = ""
    for line in text.splitlines():
        gm = GROUP_RE.search(line.strip())
        if gm and not group:
            group = str(gm.group(1) or "").strip().upper().replace(" ", "_")
        m = CALL_RE.search(line.strip())
        if m:
            target = f"launchers/{m.group(1)}"
            args = (m.group(2) or "").strip()
            break
    return {
        "entry": path.name,
        "role": "ROOT_SHIM",
        "forwards_to": target,
        "args": args,
        "group": group,
    }


def _parse_launcher(path: pathlib.Path) -> Dict[str, str]:
    target, args, chain = _resolve_launcher_target(path)
    delegate_to = chain[1] if len(chain) > 1 else ""
    return {
        "entry": path.relative_to(ROOT).as_posix(),
        "role": "REAL_LAUNCHER",
        "python_target": target,
        "args": args,
        "delegate_to": delegate_to,
        "delegate_chain": chain,
    }


def _find_delegate_batches(lines: List[str]) -> List[str]:
    delegates: List[str] = []
    for line in lines:
        raw = line.strip()
        lower = raw.lower()
        if not raw or raw.startswith("::") or lower.startswith("rem "):
            continue
        m = DELEGATE_BATCH_RE.search(raw)
        if not m:
            continue
        token = (m.group(1) or m.group(2) or "").strip()
        if token:
            delegates.append(token.strip("\"'"))
    return delegates


def _resolve_delegate_path(current_batch: pathlib.Path, token: str) -> pathlib.Path | None:
    raw = str(token or "").strip().strip("\"'")
    if not raw:
        return None

    normalized = raw.replace("%~dp0", "").replace("%cd%", "")
    normalized = normalized.strip().strip("\"'")
    if not normalized:
        return None

    candidate = pathlib.Path(normalized)
    if not candidate.is_absolute():
        candidate = (current_batch.parent / candidate).resolve()

    if candidate.exists() and candidate.is_file():
        return candidate
    return None


def _resolve_launcher_target(path: pathlib.Path, visited: set[str] | None = None) -> Tuple[str, str, List[str]]:
    visited = visited or set()
    chain: List[str] = []
    current = path

    while True:
        key = str(current.resolve()).lower()
        if key in visited:
            break
        visited.add(key)
        try:
            chain.append(current.relative_to(ROOT).as_posix())
        except Exception:
            chain.append(str(current))

        text = _safe_read(current)
        lines = text.splitlines()
        for line in lines:
            m = PY_RE.search(line.strip())
            if m:
                target = m.group(1).replace("\\", "/")
                args = (m.group(2) or "").strip()
                return target, args, chain

        delegates = _find_delegate_batches(lines)
        next_path = None
        for token in delegates:
            cand = _resolve_delegate_path(current, token)
            if cand:
                next_path = cand
                break
        if not next_path:
            break
        current = next_path

    return "", "", chain


def _parse_cmd(path: pathlib.Path) -> Dict[str, object]:
    text = _safe_read(path)
    targets: List[str] = []
    seen = set()
    for line in text.splitlines():
        for m in PY_REF_RE.finditer(line.strip()):
            t = (m.group(1) or "").replace("\\", "/")
            key = t.lower()
            if t and key not in seen:
                targets.append(t)
                seen.add(key)
    return {
        "entry": path.relative_to(ROOT).as_posix(),
        "role": "OPS_RUNNER",
        "python_targets": targets,
    }


def _iter_entrypoint_files() -> List[pathlib.Path]:
    files: List[pathlib.Path] = []
    for pattern in ("*.bat", "*.cmd"):
        for path in ROOT.rglob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if any(part in IGNORE_PARTS for part in rel.parts):
                continue
            files.append(path)
    files.sort()
    return files


def _recognized_entrypoints() -> set[str]:
    out: set[str] = set()
    for path in ROOT_SHIMS:
        out.add(path.relative_to(ROOT).as_posix())
    for path in REAL_LAUNCHERS:
        out.add(path.relative_to(ROOT).as_posix())
    for path in OPS_RUNNERS:
        out.add(path.relative_to(ROOT).as_posix())
    return out


def build_map() -> Dict[str, object]:
    root_rows = [_parse_root_shim(p) for p in ROOT_SHIMS]
    launcher_rows = [_parse_launcher(p) for p in REAL_LAUNCHERS]
    ops_rows = [_parse_cmd(p) for p in OPS_RUNNERS]

    discovered = [p.relative_to(ROOT).as_posix() for p in _iter_entrypoint_files()]
    known = _recognized_entrypoints()
    unclassified = sorted([p for p in discovered if p not in known])

    return {
        "root_shims": root_rows,
        "real_launchers": launcher_rows,
        "ops_runners": ops_rows,
        "user_click_targets": [row["entry"] for row in root_rows],
        "internal_targets": [row["entry"] for row in launcher_rows] + [row["entry"] for row in ops_rows],
        "unclassified_entrypoints": unclassified,
        "summary": {
            "user_click_target_count": len(root_rows),
            "real_launcher_count": len(launcher_rows),
            "ops_runner_count": len(ops_rows),
            "discovered_entrypoint_count": len(discovered),
            "unclassified_count": len(unclassified),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Print launcher role map for Windows entrypoints.")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if unclassified .bat/.cmd entrypoints are detected.",
    )
    args = parser.parse_args()

    data = build_map()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("[ROLE_GUIDE]")
        print("- USER_CLICK_TARGET: root *.bat only")
        print("- INTERNAL_DO_NOT_CLICK: launchers/*.bat and scripts/*.cmd")

        print("\n[ROOT_SHIM]")
        for row in data["root_shims"]:
            group = row.get("group", "")
            group_text = f" [{group}]" if group else ""
            print(f"- {row['entry']}{group_text} -> {row.get('forwards_to', '')} {row.get('args', '')}".rstrip())

        print("\n[REAL_LAUNCHER]")
        for row in data["real_launchers"]:
            target = row.get("python_target", "")
            extra = row.get("args", "")
            chain = row.get("delegate_chain", [])
            via = " -> ".join(chain[1:]) if len(chain) > 1 else ""
            if target:
                suffix = f" [via {via}]" if via else ""
                print(f"- {row['entry']} -> {target} {extra}{suffix}".rstrip())
            elif via:
                print(f"- {row['entry']} -> {via}")
            else:
                print(f"- {row['entry']} ->")

        print("\n[OPS_RUNNER]")
        for row in data["ops_runners"]:
            joined = ", ".join(row.get("python_targets", []))
            print(f"- {row['entry']} -> {joined}")

        print("\n[UNCLASSIFIED_ENTRYPOINTS]")
        unclassified = data.get("unclassified_entrypoints", [])
        if unclassified:
            for entry in unclassified:
                print(f"- {entry}")
        else:
            print("- (none)")

        summary = data.get("summary", {})
        print(
            "\n[SUMMARY] user={user} launcher={launcher} ops={ops} discovered={discovered} unclassified={unclassified}".format(
                user=summary.get("user_click_target_count", 0),
                launcher=summary.get("real_launcher_count", 0),
                ops=summary.get("ops_runner_count", 0),
                discovered=summary.get("discovered_entrypoint_count", 0),
                unclassified=summary.get("unclassified_count", 0),
            )
        )

    if args.strict and data.get("unclassified_entrypoints"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
