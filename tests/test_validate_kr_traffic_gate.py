import tempfile
import unittest
from pathlib import Path

from scripts.validate_kr_traffic_gate import build_static_audit


class ValidateKrTrafficGateTests(unittest.TestCase):
    def test_build_static_audit_detects_gate_and_noindex(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "components").mkdir(parents=True)
            (base / "app" / "yangdo").mkdir(parents=True)
            (base / "app" / "permit").mkdir(parents=True)
            (base / "app" / "widget" / "yangdo").mkdir(parents=True)
            (base / "app" / "widget" / "permit").mkdir(parents=True)
            (base / "components" / "widget-frame.tsx").write_text(
                '"use client";\nimport { useState } from "react";\nconst a = !isExpanded; <div className="widget-gate" data-traffic-gate="closed"></div><button data-traffic-gate-launch="true"></button><iframe />',
                encoding="utf-8",
            )
            (base / "app" / "yangdo" / "page.tsx").write_text('gateNote={"x"} launchLabel={"y"}', encoding="utf-8")
            (base / "app" / "permit" / "page.tsx").write_text('gateNote={"x"} launchLabel={"y"}', encoding="utf-8")
            (base / "app" / "widget" / "yangdo" / "page.tsx").write_text("robots: { index: false, follow: false }", encoding="utf-8")
            (base / "app" / "widget" / "permit" / "page.tsx").write_text("robots: { index: false, follow: false }", encoding="utf-8")

            out = build_static_audit(base)
            self.assertTrue(out["widget_frame_gate_ready"])
            self.assertTrue(out["public_pages_use_gate_copy"])
            self.assertTrue(out["widget_pages_noindex_ready"])


if __name__ == "__main__":
    unittest.main()

