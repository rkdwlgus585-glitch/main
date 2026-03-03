import importlib.util
import pathlib
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "paid_ops" / "build_gabji_analysis_report.py"
SPEC = importlib.util.spec_from_file_location("build_gabji_analysis_report", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class GabjiReportSumValidationTest(unittest.TestCase):
    def _sample_data(self, bad_sum=False):
        row = {
            "업종": "건축",
            "면허년도": "2020",
            "시공능력평가액": "20",
            "매출": {
                "2020년": "-",
                "2021년": "10.5",
                "2022년": "23.3",
                "2023년": "12.2",
                "2024년": "15",
                "2025년": "13",
            },
            "3년합계": "40.2억",
            "5년합계": "74억" if not bad_sum else "70억",
        }
        return {
            "업종정보": [row],
            "비고": ["행정처분이력 없음"],
            "행정사항": ["행정처분이력 없음"],
            "양도가": "2.7억",
            "등록번호": "7737",
            "자본금": "3.5억",
            "소재지": "지방",
            "법인설립일": "2020년",
            "회사형태": "주식회사",
            "공제조합출자좌수": "94좌",
            "공제조합잔액": "6500만원",
        }

    def test_build_report_payload_raises_on_sum_mismatch(self):
        with self.assertRaises(ValueError):
            MOD.build_report_payload(self._sample_data(bad_sum=True), enforce_sum_validation=True)

    def test_build_report_payload_allows_sum_mismatch_when_disabled(self):
        payload = MOD.build_report_payload(self._sample_data(bad_sum=True), enforce_sum_validation=False)
        qc = payload.get("quality_checks", {})
        self.assertFalse(qc.get("sum_validation_ok", True))
        self.assertTrue(len(qc.get("sum_issues", [])) >= 1)


if __name__ == "__main__":
    unittest.main()
