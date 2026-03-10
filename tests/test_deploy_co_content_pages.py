import json
import tempfile
import unittest
from pathlib import Path

from scripts.deploy_co_content_pages import _build_bridge_content_html, _load_widget_bundle_entry


class DeployCoContentPagesTests(unittest.TestCase):
    def test_load_widget_bundle_entry_reads_widget_paths(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "widgets": [
                            {
                                "widget": "permit",
                                "ok": True,
                                "widget_url": "https://calc.example.com/widgets/permit?tenant_id=x",
                                "iframe_path": "C:/tmp/permit.iframe.html",
                                "launcher_path": "C:/tmp/permit.launcher.html",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            row = _load_widget_bundle_entry(manifest, "permit")
            self.assertEqual(row["widget"], "permit")
            self.assertTrue(row["ok"])
            self.assertIn("/widgets/permit", row["widget_url"])

    def test_build_bridge_content_html_includes_bridge_marker_and_iframe(self):
        html = _build_bridge_content_html(
            marker="SMNA_BRIDGE_CUSTOMER SMNA_WIDGET_BRIDGE_CUSTOMER",
            title="AI 양도가 산정 계산기",
            description="설명",
            widget_url="https://calc.example.com/widgets/yangdo?tenant_id=x",
            iframe_html='<iframe src="https://calc.example.com/widgets/yangdo?tenant_id=x"></iframe>',
            open_label="계산기 바로 열기",
        )
        self.assertIn("smna-calc-bridge", html)
        self.assertIn("SMNA_WIDGET_BRIDGE_CUSTOMER", html)
        self.assertIn("https://calc.example.com/widgets/yangdo?tenant_id=x", html)


if __name__ == "__main__":
    unittest.main()
