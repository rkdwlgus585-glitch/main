#!/usr/bin/env python3
"""
One-shot refactoring script:  replace repetitive dict-extraction boilerplate
in permit_diagnosis_calculator.py with _get_str / _get_int helpers.

Patterns replaced:
  str(VAR.get("KEY", "") or "").strip()   →  _get_str(VAR, "KEY")
  str(VAR.get("KEY", "DEF") or "").strip()→  _get_str(VAR, "KEY", "DEF")  (if DEF != "")
  _coerce_non_negative_int(VAR.get("KEY", 0))  →  _get_int(VAR, "KEY")
  _coerce_non_negative_int(VAR.get("KEY", N))  →  _get_int(VAR, "KEY", N)  (if N != 0)

Dry-run by default; pass --apply to write changes.
"""
import re
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "permit_diagnosis_calculator.py"

# ── Pattern 1: str(VAR.get("KEY", DEFAULT) or "").strip() ──────────────
# Handles both single and double quotes for key; default "" or other string
PAT_GET_STR = re.compile(
    r'str\('
    r'(\w+)\.get\('           # group(1) = variable name
    r'(["\'])([^"\']+)\2'     # group(2)=quote, group(3)=key
    r',\s*'
    r'(["\'])([^"\']*)\4'     # group(4)=quote, group(5)=default value
    r'\)'                     # close .get(
    r'\s*or\s*["\']["\']'     # or ""
    r'\)\.strip\(\)'          # ).strip()
)

# ── Pattern 2: _coerce_non_negative_int(VAR.get("KEY", DEFAULT)) ──────
PAT_GET_INT = re.compile(
    r'_coerce_non_negative_int\('
    r'(\w+)\.get\('           # group(1) = variable name
    r'(["\'])([^"\']+)\2'     # group(2)=quote, group(3)=key
    r',\s*'
    r'([^)]*?)'              # group(4) = default value (could be 0, "", etc.)
    r'\)'                     # close .get(
    r'\)'                     # close _coerce_non_negative_int(
)


def replace_get_str(m):
    var = m.group(1)
    key = m.group(3)
    default = m.group(5)
    if default == "":
        return f'_get_str({var}, "{key}")'
    else:
        return f'_get_str({var}, "{key}", "{default}")'


def replace_get_int(m):
    var = m.group(1)
    key = m.group(3)
    raw_default = m.group(4).strip().strip('"').strip("'")
    # Determine numeric default
    try:
        default_val = int(float(raw_default)) if raw_default else 0
    except (ValueError, TypeError):
        default_val = 0
    if default_val == 0:
        return f'_get_int({var}, "{key}")'
    else:
        return f'_get_int({var}, "{key}", {default_val})'


def main():
    apply = "--apply" in sys.argv
    text = TARGET.read_text(encoding="utf-8")

    new_text, n_str = PAT_GET_STR.subn(replace_get_str, text)
    new_text, n_int = PAT_GET_INT.subn(replace_get_int, new_text)

    print(f"_get_str replacements: {n_str}")
    print(f"_get_int replacements: {n_int}")
    print(f"Total: {n_str + n_int}")

    if apply:
        TARGET.write_text(new_text, encoding="utf-8")
        print("✅ Changes written to", TARGET)
    else:
        print("(dry run — pass --apply to write changes)")
        # Show first 5 diffs for review
        import difflib
        orig = text.splitlines(keepends=True)
        new = new_text.splitlines(keepends=True)
        diff = list(difflib.unified_diff(orig, new, lineterm="", n=0))
        shown = 0
        for line in diff:
            if line.startswith("@@") or line.startswith("---") or line.startswith("+++"):
                continue
            if line.startswith("-") or line.startswith("+"):
                print(line.rstrip())
                shown += 1
                if shown >= 20:
                    print(f"... ({len(diff)} total diff lines)")
                    break


if __name__ == "__main__":
    main()
