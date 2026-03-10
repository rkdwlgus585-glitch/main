import importlib.util
import pathlib
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1].parent / "ALL" / "tistory_ops" / "publish_browser.py"
SPEC = importlib.util.spec_from_file_location("tistory_publish_browser", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class TistoryPublishBrowserPackageTest(unittest.TestCase):
    def test_build_post_package(self):
        data = {
            "등록번호": "7540",
            "양도가": "0.5억",
            "업종정보": [{"업종": "소방", "면허년도": "0", "시공능력": "10", "매출": {"2022": "1.3"}}],
            "비고": ["전문소방"],
        }
        out = MOD.build_post_package(data)
        self.assertIn("title", out)
        self.assertIn("content", out)
        self.assertIn("source_url", out)
        self.assertIn("7540", out["title"])
        self.assertIn("회사개요", out["content"])
        self.assertIn("uid=7540", out["source_url"])


if __name__ == "__main__":
    unittest.main()

