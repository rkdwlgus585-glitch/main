import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "prepare_co_global_banner_snippet.py"


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location("prepare_co_global_banner_snippet", str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


class CoGlobalBannerSnippetTest(unittest.TestCase):
    def test_banner_snippet_contains_marker_and_target(self):
        mod = _load_module(SCRIPT_PATH)
        target = "https://seoulmna.kr/yangdo-ai-customer/"
        snippet = mod.build_banner_snippet(target)
        self.assertIn("SEOULMNA GLOBAL BANNER START", snippet)
        self.assertIn("SEOULMNA GLOBAL BANNER END", snippet)
        self.assertIn(target, snippet)
        self.assertIn("smna-global-banner", snippet)
        self.assertIn("applyBannerTextBalance", snippet)
        self.assertIn("class=\"sub-chat\"", snippet)
        self.assertIn("class=\"sub-phone\"", snippet)
        self.assertIn("align-center", snippet)
        self.assertIn("전체 매물 페이지", snippet)
        self.assertIn("#header,body.smna-co-calc-bridge-mode #hd", snippet)


if __name__ == "__main__":
    unittest.main()
