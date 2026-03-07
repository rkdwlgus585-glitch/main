import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_permit_batch_law_autocollect


class PermitBatchLawAutoCollectTests(unittest.TestCase):
    def test_collect_candidates_batch_captures_success_and_error(self):
        def fake_collector(
            service_name,
            *,
            service_code="",
            synonyms=None,
            max_candidates=3,
            group_name="",
            group_description="",
            major_name="",
        ):
            if service_code == "B":
                raise RuntimeError("lookup failed")
            return [{"law_title": f"{service_name}법", "score": 7}]

        results = run_permit_batch_law_autocollect._collect_candidates_batch(
            [
                {"service_code": "A", "service_name": "에이업"},
                {"service_code": "B", "service_name": "비업"},
            ],
            synonyms={},
            max_candidates=2,
            workers=3,
            collector=fake_collector,
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["service_code"], "A")
        self.assertEqual(results[0]["candidates"][0]["law_title"], "에이업법")
        self.assertEqual(results[0]["error"], "")
        self.assertEqual(results[1]["service_code"], "B")
        self.assertEqual(results[1]["candidates"], [])
        self.assertEqual(results[1]["error"], "lookup failed")

    def test_build_query_variants_adds_keyword_law_hints(self):
        tourism = run_permit_batch_law_autocollect._build_query_variants(
            "\uad00\uad11\uc219\ubc15\uc5c5"
        )
        livestock = run_permit_batch_law_autocollect._build_query_variants(
            "\uac00\ucd95\uc0ac\uc721\uc5c5"
        )

        self.assertIn("\uad00\uad11\uc9c4\ud765\ubc95", tourism)
        self.assertIn("\ucd95\uc0b0\ubc95", livestock)
        self.assertIn("\uad00\uad11\uc219\ubc15", tourism)
        self.assertIn("\uac00\ucd95\uc0ac\uc721", livestock)

    def test_build_query_variants_uses_context_hints_and_filters_low_signal_suffixes(self):
        variants = run_permit_batch_law_autocollect._build_query_variants(
            "유료직업소개소",
            service_code="11_50_02_P",
            synonyms={"11_50_02_P": ["직업안정법", "직업안정법 시행규칙"]},
            group_name="직업소개",
            group_description="직업을 소개하는 업종",
            major_name="기타",
        )

        self.assertIn("직업안정법", variants)
        self.assertNotIn("유료", variants)

    def test_build_query_variants_ignores_misleading_group_context(self):
        variants = run_permit_batch_law_autocollect._build_query_variants(
            "숙박업",
            group_name="게임",
            group_description="PC방, 오락실 인형뽑기 등 게임관련 업소 정보",
            major_name="문화",
        )

        self.assertIn("공중위생관리법", variants)
        self.assertNotIn("게임산업진흥에 관한 법률", variants)

    def test_build_query_variants_uses_service_code_hints_for_international_meeting(self):
        variants = run_permit_batch_law_autocollect._build_query_variants(
            "국제회의기획업",
            service_code="03_08_01_P",
            synonyms=run_permit_batch_law_autocollect.DEFAULT_SYNONYMS,
            group_name="게임",
            group_description="PC방, 오락실 인형뽑기 등 게임관련 업소 정보",
            major_name="문화",
        )

        self.assertIn("관광진흥법", variants)
        self.assertIn("관광진흥법 시행령", variants)

    def test_build_query_variants_uses_service_code_hints_for_culture_arts_corporation(self):
        variants = run_permit_batch_law_autocollect._build_query_variants(
            "문화예술법인",
            service_code="03_08_03_P",
            synonyms=run_permit_batch_law_autocollect.DEFAULT_SYNONYMS,
            group_name="게임",
            group_description="PC방, 오락실 인형뽑기 등 게임관련 업소 정보",
            major_name="문화",
        )

        self.assertIn("문화체육관광부 및 국가유산청 소관 비영리법인의 설립 및 감독에 관한 규칙", variants)
        self.assertNotIn("게임", variants)

    def test_build_query_variants_uses_service_code_hints_for_stale_large_store_case(self):
        variants = run_permit_batch_law_autocollect._build_query_variants(
            "대규모점포",
            service_code="08_25_01_P",
            synonyms=run_permit_batch_law_autocollect.DEFAULT_SYNONYMS,
            group_name="미용",
            group_description="헤어, 메이크업, 네일아트 등 미용 업소 정보",
            major_name="생활",
        )

        self.assertIn("유통산업발전법", variants)
        self.assertIn("유통산업발전법 시행규칙", variants)
        self.assertNotIn("미용", variants)

    def test_score_title_normalizes_spacing_for_exact_matches(self):
        score = run_permit_batch_law_autocollect._score_title(
            "환경관리대행기관",
            "환경관리 대행기관의 지정 등에 관한 규칙",
            query_used="환경관리대행기관",
        )

        self.assertGreaterEqual(score, 8)

    def test_collect_candidates_for_service_keeps_direct_law_title_hints(self):
        with patch.object(run_permit_batch_law_autocollect, "_autocom_titles", return_value=[]):
            candidates = run_permit_batch_law_autocollect._collect_candidates_for_service(
                "의료유사업",
                service_code="01_01_10_P",
                synonyms={
                    "01_01_10_P": [
                        "의료유사업자에 관한 규칙",
                        "의료법",
                        "의료법 시행규칙",
                    ]
                },
                max_candidates=5,
                group_name="의료기관",
                group_description="병원, 의원, 산후조리업, 약국 등 의료에 관련된 의료기관 또는 업소정보",
                major_name="건강",
            )

        titles = [item["law_title"] for item in candidates]
        self.assertIn("의료유사업자에 관한 규칙", titles)
        self.assertIn("의료법", titles)
        self.assertIn("의료법 시행규칙", titles)

    def test_main_writes_worker_count_and_updates_mapping_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            criteria_path = root / "criteria.json"
            payload = {
                "industries": [
                    {
                        "service_code": "A001",
                        "service_name": "에이업",
                        "mapping_status": "queued_law_mapping",
                        "collection_status": "pending_law_mapping",
                    },
                    {
                        "service_code": "B001",
                        "service_name": "비업",
                        "mapping_status": "queued_law_mapping",
                        "collection_status": "pending_law_mapping",
                    },
                ],
                "mapping_pipeline": {
                    "batches": [
                        {
                            "batch_id": "M01-B01",
                            "service_codes": ["A001", "B001"],
                        }
                    ]
                },
            }
            criteria_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            mocked_results = [
                {
                    "service_code": "A001",
                    "service_name": "에이업",
                    "candidates": [{"law_title": "에이업법", "score": 9}],
                    "error": "",
                },
                {
                    "service_code": "B001",
                    "service_name": "비업",
                    "candidates": [],
                    "error": "",
                },
            ]

            argv = [
                "run_permit_batch_law_autocollect.py",
                "--criteria",
                str(criteria_path),
                "--workers",
                "5",
                "--top-batches",
                "1",
            ]
            with patch("sys.argv", argv):
                with patch.object(run_permit_batch_law_autocollect, "_load_synonyms", return_value={}):
                    with patch.object(
                        run_permit_batch_law_autocollect,
                        "_collect_candidates_batch",
                        return_value=mocked_results,
                    ):
                        code = run_permit_batch_law_autocollect.main()

            self.assertEqual(code, 0)
            updated = json.loads(criteria_path.read_text(encoding="utf-8"))
            by_code = {row["service_code"]: row for row in updated["industries"]}
            self.assertEqual(by_code["A001"]["mapping_status"], "candidate_collected")
            self.assertEqual(by_code["A001"]["collection_status"], "candidate_collected")
            self.assertEqual(by_code["B001"]["mapping_status"], "queued_law_mapping_no_hit")

            meta = updated["mapping_pipeline"]["last_auto_collection"]
            self.assertEqual(meta["worker_count"], 5)
            self.assertEqual(meta["service_target_total"], 2)
            self.assertEqual(meta["service_processed_total"], 2)
            self.assertEqual(meta["success_total"], 1)
            self.assertEqual(meta["no_hit_total"], 1)


if __name__ == "__main__":
    unittest.main()
