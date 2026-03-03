import unittest

import gabji


def _blank_row(size=45):
    return [""] * size


class GabjiLiveEnrichTest(unittest.TestCase):
    def _make_lookup(self, header=None, row=None):
        lookup = gabji.ListingSheetLookup()
        if header is None:
            header = _blank_row()
        if row is None:
            row = _blank_row()
        lookup._rows_cache = [header, row]
        lookup._header_index_cache = {}
        return lookup

    def test_resolve_source_uid_from_claim_text(self):
        header = _blank_row()
        row = _blank_row()
        header[33] = "청구 양도가"
        row[33] = "11574 산림토목<br>\n0.8억~0.9억<br>"
        lookup = self._make_lookup(header, row)

        self.assertEqual(lookup._resolve_source_uid(row, registration_no="7459"), "11574")

    def test_parse_live_listing_detail_extracts_core_fields(self):
        html = """
        <html><body>
        <table>
          <tr><td>상태</td><td>진행중 등록번호: 11574</td><td>회사형태</td><td>주식회사</td></tr>
          <tr><td>법인설립일</td><td>2025년</td><td>공제조합출자좌수</td><td>53좌/4500만</td></tr>
          <tr><td>자본금</td><td>3억</td><td>소재지</td><td>지방</td></tr>
          <tr><td>협회가입</td><td>&nbsp;</td><td>양도가</td><td>협의</td></tr>
          <tr><td>비고</td><td>산림토목 숲길조성<br>25.10월면허<br>외부신용등급B0<br>기술자5명 6개월승계 별도</td></tr>
        </table>
        <table>
          <tr>
            <td>업종</td><td>면허년도</td><td></td><td>2020년</td><td>2021년</td><td>2022년</td><td>2023년</td><td>2024년</td><td>3년합계</td><td>5년합계</td><td>2025년</td><td></td><td>시공능력 평가액</td>
          </tr>
          <tr>
            <td>산림토목</td><td>2025</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td>신규</td><td></td>
          </tr>
        </table>
        </body></html>
        """
        lookup = self._make_lookup()
        detail = lookup._parse_live_listing_detail(html)

        self.assertEqual(detail.get("원본등록번호"), "11574")
        self.assertEqual(detail.get("회사형태"), "주식회사")
        self.assertEqual(detail.get("자본금"), "3억")
        self.assertEqual(detail.get("소재지"), "지방")
        self.assertEqual(detail.get("법인설립일"), "2025년")
        self.assertEqual(detail.get("공제조합출자좌수"), "53좌")
        self.assertEqual(detail.get("공제조합잔액"), "4500만")
        self.assertEqual(detail.get("양도가"), "협의")
        self.assertIn("외부신용등급B0", detail.get("비고", []))
        self.assertEqual(detail.get("업종정보", [])[0].get("업종"), "산림토목")
        self.assertEqual(detail.get("업종정보", [])[0].get("매출", {}).get("2025년"), "신규")

    def test_merge_live_detail_keeps_base_numeric_price_when_live_is_consult(self):
        lookup = self._make_lookup()
        base = {
            "양도가": "0.9억",
            "비고": ["＊ 2025년 10월 면허"],
            "행정사항": ["＊ 2025년 10월 면허"],
        }
        live = {
            "양도가": "협의",
            "비고": ["산림토목 숲길조성", "25.10월면허", "외부신용등급B0", "기술자5명 6개월승계 별도"],
            "원본UID": "11574",
        }
        merged = lookup._merge_live_detail(base, live)

        self.assertEqual(merged.get("양도가"), "0.9억")
        self.assertEqual(merged.get("원본UID"), "11574")
        self.assertIn("산림토목 숲길조성", merged.get("비고", []))
        self.assertIn("기술자5명 6개월승계 별도", merged.get("비고", []))
        self.assertTrue(any("기술자" in line for line in merged.get("행정사항", [])))

    def test_merge_live_detail_overrides_when_live_has_numeric_price(self):
        lookup = self._make_lookup()
        base = {"양도가": "협의"}
        live = {"양도가": "1.2억"}
        merged = lookup._merge_live_detail(base, live)
        self.assertEqual(merged.get("양도가"), "1.2억")

    def test_merge_live_detail_keeps_all_licenses_from_base_and_live(self):
        lookup = self._make_lookup()
        base = {
            "업종정보": [
                {
                    "업종": "숲길조성",
                    "면허년도": "2025",
                    "시공능력평가액": "-",
                    "매출": {"2020년": "-", "2021년": "-", "2022년": "-", "2023년": "-", "2024년": "-", "2025년": "-"},
                    "3년합계": "-",
                    "5년합계": "-",
                }
            ]
        }
        live = {
            "업종정보": [
                {
                    "업종": "산림토목",
                    "면허년도": "2025",
                    "시공능력평가액": "-",
                    "매출": {"2020년": "-", "2021년": "-", "2022년": "-", "2023년": "-", "2024년": "-", "2025년": "신규"},
                    "3년합계": "-",
                    "5년합계": "-",
                }
            ]
        }
        merged = lookup._merge_live_detail(base, live)
        names = [x.get("업종") for x in merged.get("업종정보", [])]
        self.assertIn("숲길조성", names)
        self.assertIn("산림토목", names)
        self.assertEqual(len(names), 2)


if __name__ == "__main__":
    unittest.main()
