import importlib.util
import pathlib
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "tistory_ops" / "listing_template.py"
SPEC = importlib.util.spec_from_file_location("tistory_listing_template", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class TistoryListingTemplateTest(unittest.TestCase):
    def test_build_listing_content_contains_sections_and_values(self):
        data = {
            "등록번호": "7540",
            "상태": "가능",
            "양도가": "0.5억",
            "법인설립일": "2022",
            "자본금": "1억",
            "회사형태": "주식회사",
            "공제조합출자좌수": "40좌",
            "대출후 남은잔액": "2100만",
            "협회가입": "가입",
            "소재지": "지방",
            "업종정보": [
                {
                    "업종": "상하",
                    "면허년도": "0",
                    "시공능력": "10",
                    "매출": {
                        "2022": "1.3",
                        "2023": "0.8",
                        "2024": "0.8",
                    },
                    "3년합계": "2.9",
                    "5년합계": "2.9",
                }
            ],
            "비고": ["전문소방", "현금+자체결산", "부채:51% 유동:243%"],
        }
        imgs = MOD.build_auto_image_urls(data, max_images=2)
        html = MOD.build_listing_content(data, source_url="http://www.nowmna.com/yangdo_view1.php?uid=7540&page_no=1", image_urls=imgs)
        self.assertIn("회사개요", html)
        self.assertIn("최근년도 매출실적", html)
        self.assertIn("재무지표", html)
        self.assertIn("주요 체크사항", html)
        self.assertIn("7540", html)
        self.assertNotIn("0.5억", html)
        self.assertIn("상하수도설비공사업", html)
        self.assertIn("부채비율", html)
        self.assertIn("https://seoulmna.co.kr/mna/7540", html)
        self.assertIn("https://www.law.go.kr", html)
        self.assertIn("https://www.kiscon.net", html)
        self.assertIn("매물 상세 정보 확인하기", html)
        self.assertIn("관련 제도 안내", html)
        self.assertNotIn("내부 링크:", html)
        self.assertNotIn("외부 기준 확인:", html)
        self.assertNotIn("출처:", html)
        self.assertGreaterEqual(html.count("<img"), 2)

    def test_evaluate_seo_quality_high_score(self):
        data = {
            "등록번호": "7540",
            "양도가": "0.5억",
            "업종정보": [{"업종": "소방", "면허년도": "2020", "시공능력": "10", "매출": {"2023": "0.8", "2024": "0.9", "2025": "1.1"}}],
            "비고": ["부채:51% 유동:243%", "행정처분 이력 없음"],
        }
        title = MOD.build_listing_title(data)
        body = MOD.build_listing_content(data, image_urls=MOD.build_auto_image_urls(data, max_images=2))
        report = MOD.evaluate_seo_quality(title, body, "7540")
        self.assertGreaterEqual(report["score"], 90)
        self.assertTrue(report["ok"])

    def test_evaluate_legal_and_cx_quality_high_score(self):
        data = {
            "등록번호": "7540",
            "상태": "가능",
            "업종정보": [{"업종": "상하", "면허년도": "2020", "시공능력": "10", "매출": {"2023": "0.8", "2024": "0.9", "2025": "1.1"}}],
            "비고": ["부채:51% 유동:243%", "행정처분 이력 없음"],
        }
        title = MOD.build_listing_title(data)
        body = MOD.build_listing_content(data, image_urls=MOD.build_auto_image_urls(data, max_images=2))
        legal = MOD.evaluate_legal_quality(title, body, "7540")
        cx = MOD.evaluate_cx_quality(title, body, "7540")
        self.assertTrue(legal["ok"])
        self.assertTrue(cx["ok"])


if __name__ == "__main__":
    unittest.main()
