import json
import tempfile
import unittest
from pathlib import Path

from scripts.extract_astra_design_reference import build_astra_design_reference


class ExtractAstraDesignReferenceTests(unittest.TestCase):
    def test_extracts_reference_and_next_strategy(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            theme_json = base / "theme.json"
            style_css = base / "style.css"
            front_css = base / "globals.css"
            theme_json.write_text(
                json.dumps(
                    {
                        "settings": {
                            "color": {"palette": [{"slug": "ast-global-color-0", "name": "Theme Color 1", "color": "var(--ast-global-color-0)"}]},
                            "typography": {"fontSizes": [{"slug": "large", "name": "Large", "size": "36px"}]},
                            "layout": {"contentSize": "1200px", "wideSize": "1440px", "fullSize": "none"},
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            style_css.write_text("Theme Name: Astra\nVersion: 4.12.3\n", encoding="utf-8")
            front_css.write_text(":root { --bg: #fff; --brand: #000; }\n.page-shell{ width:min(1200px,100%); }\n", encoding="utf-8")

            out = build_astra_design_reference(
                theme_json_path=theme_json,
                style_css_path=style_css,
                front_css_path=front_css,
            )

            self.assertEqual(out["astra"]["theme_name"], "Astra")
            self.assertEqual(out["astra"]["theme_version"], "4.12.3")
            self.assertEqual(out["decision"]["strategy"], "reference_only_for_next_front")
            self.assertTrue(out["kr_front"]["content_width_style_present"])
            self.assertTrue(out["suggested_actions"])


if __name__ == "__main__":
    unittest.main()
