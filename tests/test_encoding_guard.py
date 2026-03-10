import re
import unittest
from pathlib import Path

_MNAKR = Path(__file__).resolve().parents[1].parent / "ALL" / "mnakr.py"


class EncodingGuardTest(unittest.TestCase):
    def test_no_mojibake_in_runtime_critical_lines(self):
        src = _MNAKR.read_text(encoding="utf-8")
        hints = (
            "logger.",
            "messagebox",
            "raise ValueError(",
            "subtitle=",
            "showwarning(",
            "showerror(",
            "showinfo(",
            "root.title(",
            "status_label =",
        )
        bad_cjk = re.compile(r"[一-鿿]")

        failures = []
        for i, line in enumerate(src.splitlines(), 1):
            if not any(h in line for h in hints):
                continue
            if "\\?{" in line:
                continue
            if "??" in line or bad_cjk.search(line):
                failures.append((i, line.strip()))

        self.assertFalse(
            failures,
            "Mojibake detected in runtime-critical lines: "
            + "; ".join([f"{i}:{txt}" for i, txt in failures[:10]]),
        )

    def test_columnist_prompt_contains_clear_contract(self):
        src = _MNAKR.read_text(encoding="utf-8")
        self.assertIn("Target keyword", src)
        self.assertIn("Return valid JSON only", src)


if __name__ == "__main__":
    unittest.main()
