import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "apply_co_global_banner_admin.py"


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location("apply_co_global_banner_admin", str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


class ApplyCoGlobalBannerAdminReviewTest(unittest.TestCase):
    def test_review_blocks_internal_explanation_copy(self):
        mod = _load_module(SCRIPT_PATH)
        snippet = "<div>빈 게시판처럼 보이던 첫 화면 대신, 최근 프리미엄 매물을 먼저 보여주고 상세 매물 확인으로 바로 이어지도록 구성했습니다.</div>"
        issues = mod._review_snippet_copy(snippet)
        self.assertIn("internal_problem_statement", issues)
        self.assertIn("before_after_ui_explanation", issues)
        self.assertIn("implementation_explanation", issues)

    def test_review_allows_customer_facing_copy(self):
        mod = _load_module(SCRIPT_PATH)
        snippet = "<div>최근 등록된 프리미엄 매물을 한눈에 비교하고, 관심 매물은 상세 페이지에서 실적·실인수·신용·결산 상태까지 바로 확인할 수 있습니다.</div>"
        issues = mod._review_snippet_copy(snippet)
        self.assertEqual([], issues)


if __name__ == "__main__":
    unittest.main()
