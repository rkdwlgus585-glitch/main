#!/usr/bin/env python3
"""
CSS Design System Migration Script
Replaces hardcoded hex colors with var(--smna-*) CSS custom properties.
Based on Codex CSS audit (logs/css_design_system_audit.md).
"""

import re
import sys
from pathlib import Path

# Audit data: (line_number, hex_value, css_variable)
# Only "replaceable" entries from the audit
YANGDO_REPLACEMENTS = [
    (850, "#1d415f", "--smna-primary"),
    (937, "#0f4b77", "--smna-primary-soft"),
    (983, "#0f172a", "--smna-text"),
    (1021, "#566e84", "--smna-sub"),
    (1054, "#20425f", "--smna-primary"),
    (1061, "#607489", "--smna-sub"),
    (1072, "#5a6d80", "--smna-sub"),
    (1106, "#20425f", "--smna-primary"),
    (1120, "#607489", "--smna-sub"),
    (1131, "#5a6d80", "--smna-sub"),
    (1163, "#1e405d", "--smna-primary"),
    (1171, "#607489", "--smna-sub"),
    (1182, "#50677d", "--smna-sub"),
    (1188, "#6a4a1d", "--smna-warning"),
    (1228, "#577086", "--smna-sub"),
    (1256, "#607489", "--smna-sub"),
    (1271, "#62758a", "--smna-sub"),
    (1283, "#194869", "--smna-primary"),
    (1350, "#102132", "--smna-text"),
    (1366, "#d2dce8", "--smna-border"),
    (1384, "#d8e3ef", "--smna-border"),
    (1387, "#eef4fb", "--smna-neutral"),
    (1388, "#173e64", "--smna-primary"),
    (1395, "#0f3356", "--smna-primary"),
    (1397, "#0e4f7d", "--smna-primary-soft"),
    (1405, "#0f4b77", "--smna-primary-soft"),
    (1421, "#d8e3ef", "--smna-border"),
    (1422, "#f7fbff", "--smna-neutral"),
    (1423, "#17405f", "--smna-primary"),
    (1429, "#f3f8ff", "--smna-neutral"),
    (1430, "#15476d", "--smna-primary"),
    (1434, "#23513d", "--smna-success"),
    (1439, "#d8e3ef", "--smna-border"),
    (1447, "#183b5b", "--smna-primary"),
    (1452, "#4b6478", "--smna-sub"),
    (1462, "#d6e1eb", "--smna-border"),
    (1470, "#587086", "--smna-sub"),
    (1477, "#163a59", "--smna-primary"),
    (1482, "#50687d", "--smna-sub"),
    (1493, "#d6e2ec", "--smna-border"),
    (1500, "#0f9fb0", "--smna-accent-strong"),
    (1512, "#183b5b", "--smna-primary"),
    (1520, "#0a7b89", "--smna-accent-strong"),
    (1530, "#587086", "--smna-sub"),
    (1535, "#163a59", "--smna-primary"),
    (1540, "#5d7488", "--smna-sub"),
    (1554, "#4c7389", "--smna-sub"),
    (1563, "#18536a", "--smna-primary-soft"),
    (1590, "#0f5f75", "--smna-accent-strong"),
    (1628, "#0f3052", "--smna-primary-strong"),
    (1657, "#163b5f", "--smna-primary"),
    (1693, "#284a6b", "--smna-primary"),
    (1713, "#f8fbff", "--smna-neutral"),
    (1723, "#123a5a", "--smna-primary"),
    (1732, "#5d7287", "--smna-sub"),
    (1739, "#ecf4f8", "--smna-neutral"),
    (1740, "#0f172a", "--smna-text"),
    (1749, "#1e293b", "--smna-text"),
    (1758, "#64748b", "--smna-sub"),
    (1764, "#f4f8fb", "--smna-neutral"),
    (1772, "#0f3052", "--smna-primary-strong"),
    (1780, "#1f344a", "--smna-primary-strong"),
    (1788, "#f8fbff", "--smna-neutral"),
    (1801, "#0f3052", "--smna-primary-strong"),
    (1807, "#486076", "--smna-sub"),
    (1819, "#0f4b77", "--smna-primary-soft"),
    (1831, "#31526d", "--smna-primary"),
    (1842, "#5d748a", "--smna-sub"),
    (1862, "#0f4b77", "--smna-primary-soft"),
    (1869, "#003764", "--smna-primary"),
    (1870, "#003764", "--smna-primary"),
    (1878, "#0f4b77", "--smna-primary-soft"),
    (1910, "#153a5c", "--smna-primary"),
    (1917, "#155f6d", "--smna-accent-strong"),
    (1929, "#0f3052", "--smna-primary-strong"),
    (1940, "#1a496d", "--smna-primary-soft"),
    (1949, "#0f5f6c", "--smna-accent-strong"),
    (1957, "#425a70", "--smna-sub"),
    (1964, "#5d7284", "--smna-sub"),
    (1970, "#708396", "--smna-sub"),
    (1985, "#153e60", "--smna-primary"),
    (2014, "#0f527f", "--smna-primary-soft"),
    (2022, "#123453", "--smna-primary"),
    (2030, "#536d82", "--smna-sub"),
    (2050, "#17405d", "--smna-primary"),
    (2057, "#5a7186", "--smna-sub"),
    (2066, "#7b4b1d", "--smna-warning"),
    (2074, "#0f5f75", "--smna-accent-strong"),
    (2082, "#264761", "--smna-primary"),
    (2103, "#173652", "--smna-primary"),
    (2126, "#5a7186", "--smna-sub"),
    (2148, "#003764", "--smna-primary"),
    (2156, "#173652", "--smna-primary"),
    (2163, "#4f6679", "--smna-sub"),
    (2187, "#46627a", "--smna-sub"),
    (2203, "#1f6aa5", "--smna-accent-strong"),
    (2252, "#003764", "--smna-primary"),
    (2275, "#003764", "--smna-primary"),
    (2284, "#173652", "--smna-primary"),
    (2293, "#4c6782", "--smna-sub"),
    (2301, "#5a7186", "--smna-sub"),
    (2309, "#36516c", "--smna-primary"),
    (2323, "#003764", "--smna-primary"),
    (2368, "#0f527f", "--smna-primary-soft"),
    (2376, "#173652", "--smna-primary"),
    (2384, "#5a7186", "--smna-sub"),
    (2415, "#7b562d", "--smna-warning"),
    (2432, "#536d82", "--smna-sub"),
    (2448, "#0f3052", "--smna-primary-strong"),
    (2492, "#f2f9fc", "--smna-neutral"),
    (2497, "#1a436a", "--smna-primary"),
    (2503, "#1d334a", "--smna-primary-strong"),
    (2518, "#153b61", "--smna-primary"),
    (2530, "#4f647c", "--smna-sub"),
    (2546, "#43637c", "--smna-sub"),
    (2569, "#123b60", "--smna-primary"),
    (2577, "#f8fbfe", "--smna-neutral"),
    (2578, "#173a57", "--smna-primary"),
    (2586, "#56748c", "--smna-sub"),
    (2600, "#f4f8fc", "--smna-neutral"),
    (2601, "#2b445e", "--smna-primary"),
    (2612, "#1d3550", "--smna-primary-strong"),
    (2674, "#F3F4F6", "--smna-neutral"),
    (2675, "#E5E7EB", "--smna-border"),
    (2681, "#E5E7EB", "--smna-border"),
]


PERMIT_REPLACEMENTS = [
    (2401, "#003764", "--smna-primary"),
    (2402, "#022640", "--smna-primary-strong"),
    (2403, "#0f527f", "--smna-primary-soft"),
    (2404, "#d9e8f4", "--smna-neutral"),
    (2406, "#b79672", "--smna-warning"),
    (2408, "#eef3f8", "--smna-neutral"),
    (2409, "#e4edf5", "--smna-neutral"),
    (2412, "#162736", "--smna-text"),
    (2413, "#5b7286", "--smna-sub"),
    (2414, "#d5e1eb", "--smna-border"),
    (2415, "#b6c8d7", "--smna-border"),
    (2416, "#117547", "--smna-success"),
    (2417, "#8b5316", "--smna-warning"),
    (2418, "#235f8d", "--smna-primary-soft"),
    (2626, "#7b562d", "--smna-warning"),
    (2705, "#7b4b1d", "--smna-warning"),
    (2713, "#0e5d39", "--smna-success"),
    (2765, "#577086", "--smna-sub"),
    (2803, "#2e7db0", "--smna-accent-strong"),
    (2890, "#4d687f", "--smna-sub"),
    (2898, "#577086", "--smna-sub"),
    (2968, "#577086", "--smna-sub"),
    (2993, "#536d82", "--smna-sub"),
    (3066, "#8ba9c1", "--smna-border"),
    (3070, "#5e90b4", "--smna-accent-strong"),
    (3076, "#4c6780", "--smna-sub"),
    (3114, "#003764", "--smna-primary"),
    (3130, "#0f6a4b", "--smna-success"),
    (3135, "#003764", "--smna-primary"),
    (3140, "#1d587f", "--smna-primary-soft"),
    (3145, "#5c6f83", "--smna-sub"),
    (3156, "#4e6982", "--smna-sub"),
    (3169, "#47637d", "--smna-sub"),
    (3188, "#003764", "--smna-primary"),
    (3193, "#1c587f", "--smna-primary-soft"),
    (3198, "#627787", "--smna-sub"),
    (3311, "#284c68", "--smna-primary"),
    (3357, "#4c6780", "--smna-sub"),
    (3404, "#27465f", "--smna-primary"),
    (3499, "#446278", "--smna-sub"),
    (3546, "#274f71", "--smna-primary"),
    (3557, "#38576f", "--smna-primary"),
    (3568, "#4f4538", "--smna-warning"),
    (3600, "#577084", "--smna-sub"),
    (3636, "#153954", "--smna-primary"),
    (3643, "#5b7385", "--smna-sub"),
    (3694, "#4b667d", "--smna-sub"),
    (3759, "#5c4a37", "--smna-warning"),
]


def apply_replacements(file_path: str, replacements: list, dry_run: bool = False):
    """Replace hex colors with CSS variable references."""
    path = Path(file_path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    total = len(lines)
    applied = 0
    skipped = 0

    for line_num, hex_val, css_var in replacements:
        idx = line_num - 1
        if idx < 0 or idx >= total:
            print(f"  SKIP line {line_num}: out of range")
            skipped += 1
            continue

        line = lines[idx]
        hex_lower = hex_val.lower()
        line_lower = line.lower()

        if hex_lower not in line_lower:
            # Line numbers might have shifted; search nearby (+/- 5 lines)
            found = False
            for offset in range(-5, 6):
                check_idx = idx + offset
                if 0 <= check_idx < total and hex_lower in lines[check_idx].lower():
                    idx = check_idx
                    line = lines[idx]
                    found = True
                    if offset != 0:
                        print(f"  SHIFTED line {line_num} -> {check_idx + 1}: {hex_val}")
                    break
            if not found:
                print(f"  SKIP line {line_num}: '{hex_val}' not found nearby")
                skipped += 1
                continue

        # Replace hex with var(--token) - case insensitive
        pattern = re.compile(re.escape(hex_val), re.IGNORECASE)
        new_line = pattern.sub(f"var({css_var})", line, count=1)

        if new_line != line:
            lines[idx] = new_line
            applied += 1
        else:
            skipped += 1

    if not dry_run:
        path.write_text("".join(lines), encoding="utf-8")

    print(f"\n  Applied: {applied}, Skipped: {skipped}, Total: {len(replacements)}")
    return applied, skipped


def main():
    dry_run = "--dry-run" in sys.argv

    base = Path(__file__).resolve().parent.parent
    target = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].startswith("-") else "all"

    total_applied = 0
    total_skipped = 0

    if target in ("all", "yangdo"):
        yangdo_path = base / "yangdo_calculator.py"
        if yangdo_path.exists():
            print(f"{'DRY RUN - ' if dry_run else ''}Migrating yangdo_calculator.py CSS tokens...")
            a, s = apply_replacements(str(yangdo_path), YANGDO_REPLACEMENTS, dry_run)
            total_applied += a
            total_skipped += s

    if target in ("all", "permit"):
        permit_path = base / "permit_diagnosis_calculator.py"
        if permit_path.exists():
            print(f"\n{'DRY RUN - ' if dry_run else ''}Migrating permit_diagnosis_calculator.py CSS tokens...")
            a, s = apply_replacements(str(permit_path), PERMIT_REPLACEMENTS, dry_run)
            total_applied += a
            total_skipped += s

    print(f"\n=== TOTAL: Applied {total_applied}, Skipped {total_skipped} ===")
    if total_skipped > 0:
        print(f"  WARNING: {total_skipped} replacements skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
