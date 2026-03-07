import unittest
from unittest.mock import patch

from scripts import collect_permit_extended_criteria


class CollectPermitExtendedCriteriaTests(unittest.TestCase):
    def test_pick_relevant_byl_prefers_registration_basis_over_penalty_titles(self):
        entries = [
            {
                "byl_seq": "1",
                "title": "과징금의 부과기준(제22조의15 관련)",
                "byl_no": "0002",
                "byl_br_no": "03",
            },
            {
                "byl_seq": "2",
                "title": "환경전문공사업의 등록 세부기준(제30조제1항 관련)",
                "byl_no": "0004",
                "byl_br_no": "00",
            },
        ]

        picked = collect_permit_extended_criteria._pick_relevant_byl(
            entries,
            "환경전문공사업",
            [],
        )

        self.assertIsNotNone(picked)
        self.assertEqual(picked["byl_seq"], "2")
        self.assertTrue(
            collect_permit_extended_criteria._is_candidate_basis_title_acceptable(
                "환경전문공사업의 등록 세부기준(제30조제1항 관련)"
            )
        )
        self.assertTrue(
            collect_permit_extended_criteria._is_candidate_basis_title_acceptable(
                "공중위생영업의 종류별 시설 및 설비기준(제2조 관련)"
            )
        )
        self.assertTrue(
            collect_permit_extended_criteria._is_candidate_basis_title_acceptable(
                "수리업의 시설 및 품질관리체계의 기준(제35조제4항 관련)"
            )
        )
        self.assertFalse(
            collect_permit_extended_criteria._is_candidate_basis_title_acceptable(
                "행정처분기준(제42조 관련)"
            )
        )

    def test_pick_relevant_byl_prefers_industry_matched_facility_basis(self):
        entries = [
            {
                "byl_seq": "1",
                "title": "과징금의 산정기준(제11조제1항 관련)",
                "byl_no": "0001",
                "byl_br_no": "00",
            },
            {
                "byl_seq": "2",
                "title": "수리업의 시설 및 품질관리체계의 기준(제35조제4항 관련)",
                "byl_no": "0005",
                "byl_br_no": "00",
            },
        ]

        picked = collect_permit_extended_criteria._pick_relevant_byl(
            entries,
            "의료기기수리업",
            [],
        )

        self.assertIsNotNone(picked)
        self.assertEqual(picked["byl_seq"], "2")

    def test_pick_relevant_byl_prefers_semantic_business_suffix_match(self):
        entries = [
            {
                "byl_seq": "1",
                "title": "의료기기 유통품질 관리기준(제39조제4호 관련)",
                "byl_no": "0006",
                "byl_br_no": "00",
            },
            {
                "byl_seq": "2",
                "title": "수리업의 시설 및 품질관리체계의 기준(제35조제4항 관련)",
                "byl_no": "0005",
                "byl_br_no": "00",
            },
        ]

        picked = collect_permit_extended_criteria._pick_relevant_byl(
            entries,
            "의료기기수리업",
            ["의료기관", "건강"],
        )

        self.assertIsNotNone(picked)
        self.assertEqual(picked["byl_seq"], "2")

    def test_augment_candidate_laws_appends_subordinate_variants(self):
        augmented = collect_permit_extended_criteria._augment_candidate_laws(
            [
                {
                    "law_title": "사료관리법",
                    "law_url": "https://www.law.go.kr/법령/사료관리법",
                    "query_used": "사료",
                    "score": 8,
                }
            ]
        )

        titles = [item["law_title"] for item in augmented]
        self.assertEqual(titles[0], "사료관리법")
        self.assertIn("사료관리법 시행규칙", titles)
        self.assertIn("사료관리법 시행령", titles)

    def test_pick_relevant_article_prefers_registration_article(self):
        picked = collect_permit_extended_criteria._pick_relevant_article(
            [
                {"jo_no": "0005", "jo_br_no": "00", "title": "업무 범위"},
                {"jo_no": "0020", "jo_br_no": "00", "title": "안경업소의 시설기준"},
                {"jo_no": "0012", "jo_br_no": "00", "title": "안경업소의 개설등록 등"},
            ],
            "안경업",
            [],
        )

        self.assertIsNotNone(picked)
        self.assertEqual(picked["jo_no"], "0012")

    def test_pick_relevant_article_prefers_direct_industry_match_over_generic_registration(self):
        picked = collect_permit_extended_criteria._pick_relevant_article(
            [
                {"jo_no": "0020", "jo_br_no": "00", "title": "약국 개설등록"},
                {"jo_no": "0044", "jo_br_no": "02", "title": "안전상비의약품 판매자의 등록"},
                {"jo_no": "0076", "jo_br_no": "03", "title": "안전상비의약품 판매자의 등록취소"},
            ],
            "안전상비의약품 판매업소",
            [],
        )

        self.assertIsNotNone(picked)
        self.assertEqual(picked["jo_no"], "0044")

    def test_extract_article_body_text_uses_anchor_range(self):
        html = """
        <div>
          <a name="J20:0" id="J20:0"></a>
          <div class="pgroup">
            <p>제20조(약국 개설등록)</p>
            <p>약국을 개설하려는 자는 등록하여야 한다.</p>
          </div>
          <a name="J21:0" id="J21:0"></a>
          <div class="pgroup">
            <p>제21조(약국의 관리의무)</p>
          </div>
        </div>
        """

        text = collect_permit_extended_criteria._extract_article_body_text(html, "0020", "00")

        self.assertIn("제20조(약국 개설등록)", text)
        self.assertIn("약국을 개설하려는 자는 등록하여야 한다.", text)
        self.assertNotIn("제21조(약국의 관리의무)", text)

    def test_format_article_basis_title_includes_article_number(self):
        self.assertEqual(
            collect_permit_extended_criteria._format_article_basis_title("0044", "02", "안전상비의약품 판매자의 등록"),
            "제44조의2(안전상비의약품 판매자의 등록)",
        )
        self.assertEqual(
            collect_permit_extended_criteria._format_article_basis_title("0012", "00", "신고"),
            "제12조(신고)",
        )

    def test_dedupe_line_items_removes_overlap_between_summary_and_additional(self):
        summary, additional = collect_permit_extended_criteria._dedupe_line_items(
            [
                {"category": "document", "text": "신청서를 제출해야 한다."},
                {"category": "document", "text": "신청서를 제출해야 한다."},
            ],
            [
                {"category": "document", "text": "신청서를 제출해야 한다."},
                {"category": "facility_misc", "text": "시설을 갖추어야 한다."},
            ],
        )

        self.assertEqual(summary, [{"category": "document", "text": "신청서를 제출해야 한다."}])
        self.assertEqual(additional, [{"category": "facility_misc", "text": "시설을 갖추어야 한다."}])

    def test_needs_candidate_reextraction_retries_article_body_when_name_unmatched(self):
        self.assertTrue(
            collect_permit_extended_criteria._needs_candidate_reextraction(
                {
                    "has_rule": False,
                    "auto_law_candidates": [{"law_title": "Medical Act"}],
                    "candidate_criteria_status": "candidate_criteria_extracted",
                    "candidate_basis_title": "제12조(신고)",
                    "candidate_law_fetch_meta": {
                        "basis_type": "article_body",
                        "article_name_match_count": 0,
                    },
                }
            )
        )

    def test_needs_candidate_reextraction_skips_article_body_with_name_match(self):
        self.assertFalse(
            collect_permit_extended_criteria._needs_candidate_reextraction(
                {
                    "has_rule": False,
                    "auto_law_candidates": [{"law_title": "Medical Act"}],
                    "candidate_criteria_status": "candidate_criteria_extracted",
                    "candidate_criteria_count": 2,
                    "candidate_basis_title": "제12조(신고)",
                    "candidate_law_fetch_meta": {
                        "basis_type": "article_body",
                        "article_name_match_count": 1,
                        "article_selection_rules_version": collect_permit_extended_criteria.ARTICLE_SELECTION_RULES_VERSION,
                    },
                }
            )
        )

    def test_needs_candidate_reextraction_retries_when_article_selection_version_changes(self):
        self.assertTrue(
            collect_permit_extended_criteria._needs_candidate_reextraction(
                {
                    "has_rule": False,
                    "auto_law_candidates": [{"law_title": "Medical Act"}],
                    "candidate_criteria_status": "candidate_criteria_extracted",
                    "candidate_basis_title": "제12조(신고)",
                    "candidate_law_fetch_meta": {
                        "basis_type": "article_body",
                        "article_name_match_count": 1,
                        "article_selection_rules_version": 1,
                    },
                }
            )
        )

    def test_needs_candidate_reextraction_retries_sparse_candidate_result(self):
        self.assertTrue(
            collect_permit_extended_criteria._needs_candidate_reextraction(
                {
                    "has_rule": False,
                    "auto_law_candidates": [{"law_title": "방문판매 등에 관한 법률 시행령"}],
                    "candidate_criteria_status": "candidate_criteria_extracted",
                    "candidate_criteria_count": 1,
                    "candidate_basis_title": "최종소비자 판매비중 산정기준(제36조 관련)",
                    "candidate_law_fetch_meta": {
                        "basis_type": "candidate_pack",
                        "law_title": "방문판매 등에 관한 법률 시행령",
                    },
                }
            )
        )

    def test_needs_candidate_reextraction_retries_when_top_candidate_changes(self):
        self.assertTrue(
            collect_permit_extended_criteria._needs_candidate_reextraction(
                {
                    "has_rule": False,
                    "auto_law_candidates": [
                        {
                            "law_title": "관광진흥법",
                            "law_url": "https://www.law.go.kr/법령/관광진흥법",
                        },
                        {
                            "law_title": "관광진흥법 시행령",
                            "law_url": "https://www.law.go.kr/법령/관광진흥법시행령",
                        },
                    ],
                    "candidate_criteria_status": "candidate_criteria_extracted",
                    "candidate_basis_title": "시설기준(제15조의2제1항 관련)",
                    "candidate_law_fetch_meta": {
                        "law_title": "게임산업진흥에 관한 법률 시행령",
                        "law_url": "https://www.law.go.kr/법령/게임산업진흥에관한법률시행령",
                    },
                }
            )
        )

    def test_build_quality_flags_marks_stale_candidate_source(self):
        flags = collect_permit_extended_criteria._build_quality_flags(
            {
                "has_rule": False,
                "mapping_status": "queued_law_mapping_no_hit",
                "candidate_criteria_status": "candidate_criteria_extracted",
                "candidate_criteria_count": 2,
                "candidate_basis_title": "업종별시설기준(제36조 관련)",
            }
        )

        self.assertEqual(flags, ["stale_candidate_source"])

    def test_match_article_name_keys_uses_aliases_and_body_text(self):
        matched = collect_permit_extended_criteria._match_article_name_keys(
            "상조업",
            ["선불식 할부거래업자"],
            "제12조(선불식 할부거래업자의 등록절차 등)",
            "선불식 할부거래업자는 등록 후 영업할 수 있다.",
        )

        self.assertIn("선불식할부거래업자", matched)

    def test_build_candidate_aliases_adds_umbrella_registration_hints(self):
        tourism_aliases = collect_permit_extended_criteria._build_candidate_aliases(
            {
                "service_code": "03_08_01_P",
                "service_name": "국제회의기획업",
            },
            "국제회의기획업",
        )
        sports_aliases = collect_permit_extended_criteria._build_candidate_aliases(
            {
                "service_code": "10_31_01_P",
                "service_name": "골프연습장업",
            },
            "골프연습장업",
        )

        self.assertIn("관광사업", tourism_aliases)
        self.assertIn("체육시설업", sports_aliases)
        self.assertTrue(
            collect_permit_extended_criteria._needs_candidate_reextraction(
                {
                    "has_rule": False,
                    "auto_law_candidates": [{"law_title": "Medical Act"}],
                    "candidate_criteria_status": "candidate_criteria_extracted",
                    "candidate_basis_title": "신고",
                    "candidate_law_fetch_meta": {"basis_type": "article_body"},
                }
            )
        )

    def test_build_candidate_aliases_filters_irrelevant_group_context(self):
        aliases = collect_permit_extended_criteria._build_candidate_aliases(
            {
                "service_code": "03_07_02_P",
                "service_name": "관광사업자",
                "group_name": "게임",
                "major_name": "문화",
            },
            "관광사업자",
        )

        self.assertNotIn("게임", aliases)
        self.assertNotIn("문화", aliases)
        self.assertIn("관광사업", aliases)

    def test_build_candidate_name_keys_keeps_semantic_business_suffixes(self):
        keys = collect_permit_extended_criteria._build_candidate_name_keys("의료기기수리업", [])

        self.assertIn("수리업", keys)
        self.assertIn("의료기기", keys)
        self.assertGreater(
            collect_permit_extended_criteria._name_key_match_score("수리업"),
            collect_permit_extended_criteria._name_key_match_score("의료기기"),
        )

    def test_pick_relevant_article_avoids_generic_category_titles(self):
        picked = collect_permit_extended_criteria._pick_relevant_article(
            [
                {"jo_no": "0002", "jo_br_no": "00", "title": "의료기기의 날 행사 등"},
                {"jo_no": "0016", "jo_br_no": "00", "title": "수리업의 신고"},
            ],
            "의료기기수리업",
            [],
        )

        self.assertIsNotNone(picked)
        self.assertEqual(picked["jo_no"], "0016")

    def test_pick_relevant_article_prefers_registration_over_industry_type_article(self):
        picked = collect_permit_extended_criteria._pick_relevant_article(
            [
                {"jo_no": "0003", "jo_br_no": "00", "title": "관광사업의 종류"},
                {"jo_no": "0018", "jo_br_no": "00", "title": "등록 시의 신고ㆍ허가 의제 등"},
            ],
            "국제회의기획업",
            ["관광사업"],
        )

        self.assertIsNotNone(picked)
        self.assertEqual(picked["jo_no"], "0018")

    def test_pick_relevant_article_prefers_establishment_permit_over_dissolution_notice(self):
        picked = collect_permit_extended_criteria._pick_relevant_article(
            [
                {"jo_no": "0003", "jo_br_no": "00", "title": "설립허가의 신청"},
                {"jo_no": "0010", "jo_br_no": "00", "title": "해산신고"},
            ],
            "문화예술법인",
            ["비영리법인"],
        )

        self.assertIsNotNone(picked)
        self.assertEqual(picked["jo_no"], "0003")

    def test_pick_relevant_article_avoids_unrelated_association_establishment_article(self):
        picked = collect_permit_extended_criteria._pick_relevant_article(
            [
                {"jo_no": "0012", "jo_br_no": "00", "title": "중앙회의 설립 허가신청"},
                {"jo_no": "0034", "jo_br_no": "00", "title": "의료기관의 종류별 시설기준"},
            ],
            "병원",
            [],
        )

        self.assertIsNotNone(picked)
        self.assertEqual(picked["jo_no"], "0034")

    def test_pick_relevant_article_prefers_sales_report_article_over_do_not_call_system(self):
        picked = collect_permit_extended_criteria._pick_relevant_article(
            [
                {"jo_no": "0005", "jo_br_no": "00", "title": "방문판매업자등의 신고 등"},
                {"jo_no": "0042", "jo_br_no": "00", "title": "전화권유판매 수신거부의사 등록시스템 등"},
            ],
            "전화권유판매업",
            ["방문판매업자등", "방문판매업자"],
        )

        self.assertIsNotNone(picked)
        self.assertEqual(picked["jo_no"], "0005")

    def test_pick_relevant_byl_prefers_generic_umbrella_basis_over_unmatched_subtype(self):
        picked = collect_permit_extended_criteria._pick_relevant_byl(
            [
                {"byl_seq": "101", "title": "테마파크업의 시설 및 설비기준(제7조제1항 관련)", "byl_no": "0001", "byl_br_no": "02"},
                {"byl_seq": "201", "title": "관광사업의 등록기준(제5조 관련)", "byl_no": "0001", "byl_br_no": "00"},
            ],
            "관광사업자",
            ["관광사업"],
        )

        self.assertIsNotNone(picked)
        self.assertEqual(picked["byl_seq"], "201")

    def test_score_candidate_extraction_prefers_strong_registration_basis(self):
        weak = collect_permit_extended_criteria.CandidateExtraction(
            ok=True,
            service_code="A001",
            industry_name="의료기기수리업",
            data={
                "candidate_basis_title": "제10조의6(의료기기통합정보센터의 지정 및 업무 위탁)",
                "candidate_criteria_count": 2,
                "candidate_law_fetch_meta": {
                    "basis_type": "article_body",
                    "law_title": "의료기기법 시행령",
                    "article_name_match_count": 1,
                    "article_name_match_keys": ["의료기기"],
                },
            },
        )
        strong = collect_permit_extended_criteria.CandidateExtraction(
            ok=True,
            service_code="A001",
            industry_name="의료기기수리업",
            data={
                "candidate_basis_title": "제16조(수리업의 신고)",
                "candidate_criteria_count": 2,
                "candidate_law_fetch_meta": {
                    "basis_type": "article_body",
                    "law_title": "의료기기법",
                    "article_name_match_count": 1,
                    "article_name_match_keys": ["수리업"],
                },
            },
        )

        self.assertGreater(
            collect_permit_extended_criteria._score_candidate_extraction(strong),
            collect_permit_extended_criteria._score_candidate_extraction(weak),
        )

    def test_score_candidate_extraction_penalizes_unrelated_profession_basis(self):
        weak = collect_permit_extended_criteria.CandidateExtraction(
            ok=True,
            service_code="03_08_03_P",
            industry_name="문화예술법인",
            data={
                "service_code": "03_08_03_P",
                "candidate_basis_title": "문화예술교육사의 등급별 자격요건(제16조의2제1항 관련)",
                "candidate_criteria_count": 3,
                "candidate_law_fetch_meta": {
                    "basis_type": "candidate_pack",
                    "law_title": "문화예술교육 지원법 시행령",
                    "basis_name_match_count": 1,
                    "basis_name_match_keys": ["문화예술"],
                },
            },
        )
        strong = collect_permit_extended_criteria.CandidateExtraction(
            ok=True,
            service_code="03_08_03_P",
            industry_name="문화예술법인",
            data={
                "service_code": "03_08_03_P",
                "candidate_basis_title": "비영리법인의 설립허가 신청",
                "candidate_criteria_count": 2,
                "candidate_law_fetch_meta": {
                    "basis_type": "candidate_pack",
                    "law_title": "문화체육관광부 및 국가유산청 소관 비영리법인의 설립 및 감독에 관한 규칙",
                    "basis_name_match_count": 1,
                    "basis_name_match_keys": ["비영리법인"],
                },
            },
        )

        self.assertGreater(
            collect_permit_extended_criteria._score_candidate_extraction(strong),
            collect_permit_extended_criteria._score_candidate_extraction(weak),
        )

    @patch("scripts.collect_permit_extended_criteria._dedupe_line_items", side_effect=lambda a, b: (a, b))
    @patch("scripts.collect_permit_extended_criteria._extract_candidate_from_article_body")
    @patch("scripts.collect_permit_extended_criteria._parse_byl_entries", return_value=[])
    @patch("scripts.collect_permit_extended_criteria._powershell_fetch_text", return_value="[]")
    @patch("scripts.collect_permit_extended_criteria._build_byl_tree_url", return_value="https://example.com/tree")
    @patch("scripts.collect_permit_extended_criteria._is_law_service_busy", return_value=False)
    @patch("scripts.collect_permit_extended_criteria._resolve_law_landing_and_iframe")
    @patch("scripts.collect_permit_extended_criteria._augment_candidate_laws")
    def test_extract_candidate_criteria_prefers_stronger_later_article_fallback(
        self,
        mock_augment,
        mock_resolve,
        _mock_busy,
        _mock_tree_url,
        _mock_fetch_text,
        _mock_parse_entries,
        mock_extract_article_body,
        _mock_dedupe,
    ):
        row = {
            "service_code": "A001",
            "service_name": "의료기기수리업",
            "auto_law_candidates": [
                {"law_title": "의료기기법 시행령", "law_url": "https://example.com/1"},
                {"law_title": "의료기기법", "law_url": "https://example.com/2"},
            ],
        }
        mock_augment.return_value = list(row["auto_law_candidates"])
        mock_resolve.side_effect = [
            {"iframe_url": "https://example.com/iframe1", "iframe_html": "<html></html>"},
            {"iframe_url": "https://example.com/iframe2", "iframe_html": "<html></html>"},
        ]
        weak = collect_permit_extended_criteria.CandidateExtraction(
            ok=True,
            service_code="A001",
            industry_name="의료기기수리업",
            data={
                "service_code": "A001",
                "candidate_criteria_status": "candidate_criteria_extracted",
                "candidate_basis_title": "제10조의6(의료기기통합정보센터의 지정 및 업무 위탁)",
                "candidate_criteria_count": 1,
                "candidate_criteria_lines": [{"category": "document", "text": "위탁 관련"}],
                "candidate_additional_criteria_lines": [],
                "candidate_legal_basis": [{"law_title": "의료기기법 시행령", "article": "제10조의6(의료기기통합정보센터의 지정 및 업무 위탁)"}],
                "candidate_law_fetch_meta": {
                    "basis_type": "article_body",
                    "law_title": "의료기기법 시행령",
                    "article_name_match_count": 1,
                    "article_name_match_keys": ["의료기기"],
                },
            },
        )
        strong = collect_permit_extended_criteria.CandidateExtraction(
            ok=True,
            service_code="A001",
            industry_name="의료기기수리업",
            data={
                "service_code": "A001",
                "candidate_criteria_status": "candidate_criteria_extracted",
                "candidate_basis_title": "제16조(수리업의 신고)",
                "candidate_criteria_count": 2,
                "candidate_criteria_lines": [{"category": "document", "text": "수리업 신고"}],
                "candidate_additional_criteria_lines": [],
                "candidate_legal_basis": [{"law_title": "의료기기법", "article": "제16조(수리업의 신고)"}],
                "candidate_law_fetch_meta": {
                    "basis_type": "article_body",
                    "law_title": "의료기기법",
                    "article_name_match_count": 1,
                    "article_name_match_keys": ["수리업"],
                },
            },
        )
        mock_extract_article_body.side_effect = [weak, strong]

        extracted = collect_permit_extended_criteria._extract_candidate_criteria(row, timeout_sec=25)

        self.assertTrue(extracted.ok)
        self.assertEqual(extracted.data["candidate_basis_title"], "제16조(수리업의 신고)")

    @patch("scripts.collect_permit_extended_criteria._dedupe_line_items", side_effect=lambda a, b: (a, b))
    @patch("scripts.collect_permit_extended_criteria._extract_additional_criteria_lines", return_value=[])
    @patch("scripts.collect_permit_extended_criteria._extract_registration_summary_lines", return_value=[{"category": "document", "text": "등록기준"}])
    @patch("scripts.collect_permit_extended_criteria._extract_pdf_text", return_value="등록기준")
    @patch("scripts.collect_permit_extended_criteria._download_pdf_bytes", return_value=b"%PDF")
    @patch("scripts.collect_permit_extended_criteria._extract_pdf_fl_seq", return_value="123")
    @patch("scripts.collect_permit_extended_criteria._extract_candidate_from_article_body", return_value=None)
    @patch("scripts.collect_permit_extended_criteria._parse_byl_entries")
    @patch("scripts.collect_permit_extended_criteria._powershell_fetch_text", side_effect=["[]", "<html></html>", "[]", "<html></html>"])
    @patch("scripts.collect_permit_extended_criteria._build_byl_tree_url", return_value="https://example.com/tree")
    @patch("scripts.collect_permit_extended_criteria._is_law_service_busy", return_value=False)
    @patch("scripts.collect_permit_extended_criteria._resolve_law_landing_and_iframe")
    @patch("scripts.collect_permit_extended_criteria._augment_candidate_laws")
    def test_extract_candidate_criteria_prefers_stronger_later_bylaw_candidate(
        self,
        mock_augment,
        mock_resolve,
        _mock_busy,
        _mock_tree_url,
        _mock_fetch_text,
        mock_parse_entries,
        _mock_article_fallback,
        _mock_pdf_fl_seq,
        _mock_pdf_bytes,
        _mock_pdf_text,
        _mock_summary_lines,
        _mock_additional_lines,
        _mock_dedupe,
    ):
        row = {
            "service_code": "A001",
            "service_name": "국제회의기획업",
            "auto_law_candidates": [
                {"law_title": "관광진흥법 시행규칙", "law_url": "https://example.com/1", "query_used": "관광진흥법"},
                {"law_title": "관광진흥법 시행령", "law_url": "https://example.com/2", "query_used": "관광진흥법"},
            ],
        }
        mock_augment.return_value = list(row["auto_law_candidates"])
        mock_resolve.side_effect = [
            {"iframe_url": "https://example.com/iframe1", "iframe_html": "<html></html>", "landing_url": "https://example.com/1"},
            {"iframe_url": "https://example.com/iframe2", "iframe_html": "<html></html>", "landing_url": "https://example.com/2"},
        ]
        mock_parse_entries.side_effect = [
            [
                {"byl_seq": "101", "title": "테마파크업의 시설 및 설비기준(제7조제1항 관련)", "byl_no": "0001", "byl_br_no": "02"},
            ],
            [
                {"byl_seq": "201", "title": "관광사업의 등록기준(제5조 관련)", "byl_no": "0001", "byl_br_no": "00"},
            ],
        ]

        extracted = collect_permit_extended_criteria._extract_candidate_criteria(row, timeout_sec=25)

        self.assertTrue(extracted.ok)
        self.assertEqual(extracted.data["candidate_law_fetch_meta"]["law_title"], "관광진흥법 시행령")
        self.assertEqual(extracted.data["candidate_basis_title"], "관광사업의 등록기준(제5조 관련)")

    def test_build_quality_flags_marks_hidden_review_risks(self):
        flags = collect_permit_extended_criteria._build_quality_flags(
            {
                "has_rule": False,
                "auto_law_candidates": [{"law_title": "Medical Act"}],
                "candidate_criteria_status": "candidate_criteria_extracted",
                "candidate_criteria_count": 1,
                "candidate_basis_title": "신고",
                "candidate_law_fetch_meta": {
                    "basis_type": "article_body",
                    "article_name_match_count": 0,
                },
            }
        )

        self.assertEqual(
            flags,
            ["sparse_criteria", "generic_basis_title", "article_name_unmatched"],
        )

    def test_build_requirement_profile_marks_capital_technical_and_other_focus(self):
        profile = collect_permit_extended_criteria._build_requirement_profile(
            {
                "requirements": {
                    "capital_eok": 1.5,
                    "technicians": 3,
                    "equipment_count": 1,
                    "deposit_days": 30,
                },
                "criteria_summary": [
                    {"category": "office", "text": "사무실을 확보해야 한다."},
                    {"category": "document", "text": "신청서 및 첨부서류를 제출해야 한다."},
                ],
                "criteria_additional": [
                    {"category": "facility_misc", "text": "장비를 갖추어야 한다."},
                ],
            }
        )

        self.assertTrue(profile["capital_required"])
        self.assertEqual(profile["capital_eok"], 1.5)
        self.assertTrue(profile["technical_personnel_required"])
        self.assertEqual(profile["technicians_required"], 3)
        self.assertTrue(profile["other_required"])
        self.assertTrue(profile["focus_target"])
        self.assertTrue(profile["focus_target_with_other"])
        self.assertEqual(profile["focus_bucket"], "capital_technical_other")
        self.assertEqual(profile["profile_source"], "structured_requirements")
        self.assertFalse(profile["inferred_focus_candidate"])
        self.assertIn("equipment", profile["other_components"])
        self.assertIn("deposit", profile["other_components"])
        self.assertIn("office", profile["other_components"])

    def test_build_requirement_profile_marks_text_inference_as_low_confidence_focus(self):
        profile = collect_permit_extended_criteria._build_requirement_profile(
            {
                "criteria_summary": [
                    {"category": "core_requirement", "text": "기술인력 1명 이상"},
                    {"category": "core_requirement", "text": "납입자본금 5천만원 이상"},
                    {"category": "document", "text": "사업계획을 제출할 것"},
                ]
            }
        )

        self.assertEqual(profile["profile_source"], "text_inference")
        self.assertTrue(profile["inferred_focus_candidate"])
        self.assertFalse(profile["focus_target"])
        self.assertFalse(profile["focus_target_with_other"])
        self.assertEqual(profile["focus_bucket"], "inferred_capital_technical_other")

    def test_apply_manual_profile_override_excludes_false_positive_candidate(self):
        override_lookup = collect_permit_extended_criteria._build_profile_override_lookup(
            {
                "profile_overrides": [
                    {
                        "service_code": "08_26_04_P",
                        "action": "exclude_false_positive_candidate",
                        "reason": "오탐 제거",
                        "profile_patch": {
                            "capital_required": False,
                            "capital_eok": 0.0,
                            "technical_personnel_required": False,
                            "technicians_required": 0,
                            "other_required": False,
                            "other_components": [],
                            "equipment_count_required": 0,
                            "deposit_days_required": 0,
                            "profile_source": "manual_scope_override",
                            "inferred_focus_candidate": False,
                            "focus_target": False,
                            "focus_target_with_other": False,
                            "focus_bucket": "manual_excluded",
                            "capital_evidence": [],
                            "technical_personnel_evidence": [],
                            "other_evidence": [],
                        },
                    }
                ]
            }
        )

        patched = collect_permit_extended_criteria._apply_manual_profile_override(
            "08_26_04_P",
            {
                "capital_required": True,
                "technical_personnel_required": True,
                "other_required": True,
                "inferred_focus_candidate": True,
                "focus_target": False,
                "focus_target_with_other": False,
                "focus_bucket": "inferred_capital_technical_other",
                "profile_source": "text_inference",
            },
            override_lookup,
        )

        self.assertFalse(patched["capital_required"])
        self.assertFalse(patched["technical_personnel_required"])
        self.assertFalse(patched["inferred_focus_candidate"])
        self.assertEqual(patched["focus_bucket"], "manual_excluded")
        self.assertEqual(patched["profile_source"], "manual_scope_override")
        flags = collect_permit_extended_criteria._build_quality_flags(
            {"registration_requirement_profile": patched}
        )
        self.assertEqual(flags, ["manual_scope_override"])

    def test_extract_rule_pack_batch_collects_success_and_failure(self):
        def fake_extractor(rule, timeout_sec=50):
            rule_id = str(rule.get("rule_id") or "")
            if rule_id == "R2":
                return collect_permit_extended_criteria.RuleExtraction(
                    ok=False,
                    rule_id=rule_id,
                    industry_name=str(rule.get("industry_name") or ""),
                    data={},
                    error="pdf_text_empty",
                )
            return collect_permit_extended_criteria.RuleExtraction(
                ok=True,
                rule_id=rule_id,
                industry_name=str(rule.get("industry_name") or ""),
                data={"rule_id": rule_id, "additional_criteria_lines": [{"text": "기준"}]},
            )

        packs, errors = collect_permit_extended_criteria._extract_rule_pack_batch(
            [
                {"rule_id": "R1", "industry_name": "업종1"},
                {"rule_id": "R2", "industry_name": "업종2"},
            ],
            timeout_sec=30,
            workers=4,
            extractor=fake_extractor,
        )

        self.assertEqual(sorted(packs.keys()), ["R1"])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["rule_id"], "R2")
        self.assertEqual(errors[0]["error"], "pdf_text_empty")

    @patch("scripts.collect_permit_extended_criteria.apply_mapping_pipeline")
    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._prepare_ui_payload")
    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._load_rule_catalog")
    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._load_catalog")
    def test_build_expanded_catalog_includes_parallel_worker_summary(
        self,
        mock_load_catalog,
        mock_load_rule_catalog,
        mock_prepare_ui_payload,
        mock_apply_mapping_pipeline,
    ):
        mock_load_catalog.return_value = {}
        mock_load_rule_catalog.return_value = {}
        mock_prepare_ui_payload.return_value = {
            "industries": [
                {
                    "service_code": "A001",
                    "service_name": "에이업",
                    "major_code": "01",
                    "major_name": "그룹1",
                    "has_rule": True,
                },
                {
                    "service_code": "B001",
                    "service_name": "비업",
                    "major_code": "02",
                    "major_name": "그룹2",
                    "has_rule": True,
                },
            ],
            "rules_lookup": {
                "A001": {"rule_id": "R1", "industry_name": "에이업"},
                "B001": {"rule_id": "R2", "industry_name": "비업"},
            },
        }
        mock_apply_mapping_pipeline.side_effect = lambda industries, batch_size=12: (
            industries,
            {
                "pending_total": 1,
                "major_group_total": 1,
                "batch_total": 1,
                "batch_size": batch_size,
            },
        )

        def fake_extractor(rule, timeout_sec=50):
            rule_id = str(rule.get("rule_id") or "")
            if rule_id == "R2":
                return collect_permit_extended_criteria.RuleExtraction(
                    ok=False,
                    rule_id=rule_id,
                    industry_name=str(rule.get("industry_name") or ""),
                    data={},
                    error="iframe_not_found",
                )
            return collect_permit_extended_criteria.RuleExtraction(
                ok=True,
                rule_id=rule_id,
                industry_name=str(rule.get("industry_name") or ""),
                data={
                    "rule_id": rule_id,
                    "industry_name": str(rule.get("industry_name") or ""),
                    "additional_criteria_lines": [{"category": "document", "text": "추가서류"}],
                },
            )

        payload = collect_permit_extended_criteria.build_expanded_catalog(
            max_rules=0,
            timeout_sec=25,
            workers=6,
            extractor=fake_extractor,
            candidate_extractor=lambda row, timeout_sec=50: collect_permit_extended_criteria.CandidateExtraction(
                ok=False,
                service_code=str(row.get("service_code") or ""),
                industry_name=str(row.get("service_name") or ""),
                data={},
                error="candidate_missing",
            ),
        )

        self.assertEqual(payload["summary"]["worker_count"], 6)
        self.assertEqual(payload["summary"]["rule_pack_total"], 1)
        self.assertEqual(payload["summary"]["extraction_error_total"], 1)
        self.assertEqual(payload["summary"]["criteria_extracted_industry_total"], 1)
        self.assertEqual(payload["summary"]["pending_industry_total"], 1)
        self.assertEqual(len(payload["rule_criteria_packs"]), 1)
        self.assertEqual(payload["rule_criteria_packs"][0]["ref"], "rule::R1")
        self.assertEqual(payload["extraction_errors"][0]["rule_id"], "R2")

    @patch("scripts.collect_permit_extended_criteria.apply_mapping_pipeline")
    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._prepare_ui_payload")
    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._load_rule_catalog")
    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._load_catalog")
    def test_build_expanded_catalog_copies_rule_legal_basis_into_industry_rows(
        self,
        mock_load_catalog,
        mock_load_rule_catalog,
        mock_prepare_ui_payload,
        mock_apply_mapping_pipeline,
    ):
        mock_load_catalog.return_value = {}
        mock_load_rule_catalog.return_value = {}
        mock_prepare_ui_payload.return_value = {
            "industries": [
                {
                    "service_code": "A001",
                    "service_name": "국내여행업",
                    "major_code": "03",
                    "major_name": "문화",
                    "has_rule": True,
                }
            ],
            "rules_lookup": {
                "A001": {
                    "rule_id": "travel-domestic",
                    "industry_name": "국내여행업",
                    "requirements": {
                        "capital_eok": 0.3,
                        "technicians": 2,
                        "equipment_count": 1,
                        "deposit_days": 15,
                    },
                    "legal_basis": [
                        {
                            "law_title": "관광진흥법 시행령",
                            "article": "별표 1 여행업 등록기준",
                            "url": "https://www.law.go.kr/법령/관광진흥법시행령/별표1",
                        }
                    ],
                }
            },
        }
        mock_apply_mapping_pipeline.side_effect = lambda industries, batch_size=12: (
            industries,
            {
                "pending_total": 0,
                "major_group_total": 1,
                "batch_total": 1,
                "batch_size": batch_size,
            },
        )

        def fake_extractor(rule, timeout_sec=50):
            return collect_permit_extended_criteria.RuleExtraction(
                ok=True,
                rule_id=str(rule.get("rule_id") or ""),
                industry_name=str(rule.get("industry_name") or ""),
                data={
                    "rule_id": str(rule.get("rule_id") or ""),
                    "industry_name": str(rule.get("industry_name") or ""),
                    "requirements": {
                        "capital_eok": 0.3,
                        "technicians": 2,
                        "equipment_count": 1,
                        "deposit_days": 15,
                    },
                    "legal_basis": [
                        {
                            "law_title": "관광진흥법 시행령",
                            "article": "별표 1 여행업 등록기준",
                            "url": "https://www.law.go.kr/법령/관광진흥법시행령/별표1",
                        }
                    ],
                    "law_fetch_meta": {"selected_byl_title": "관광사업의 등록기준(제5조 관련)"},
                    "additional_criteria_lines": [{"category": "document", "text": "보증보험 서류"}],
                },
            )

        payload = collect_permit_extended_criteria.build_expanded_catalog(
            max_rules=0,
            timeout_sec=25,
            workers=2,
            extractor=fake_extractor,
            candidate_extractor=lambda row, timeout_sec=50: collect_permit_extended_criteria.CandidateExtraction(
                ok=False,
                service_code=str(row.get("service_code") or ""),
                industry_name=str(row.get("service_name") or ""),
                data={},
                error="candidate_missing",
            ),
        )

        row = payload["industries"][0]
        self.assertEqual(row["industry_name"], "국내여행업")
        self.assertEqual(row["legal_basis"][0]["law_title"], "관광진흥법 시행령")
        self.assertEqual(row["law_title"], "관광진흥법 시행령")
        self.assertEqual(row["legal_basis_title"], "별표 1 여행업 등록기준")
        self.assertEqual(row["criteria_source_type"], "rule_pack")
        self.assertEqual(row["status"], "criteria_extracted")
        self.assertTrue(row["registration_requirement_profile"]["capital_required"])
        self.assertTrue(row["registration_requirement_profile"]["technical_personnel_required"])
        self.assertTrue(row["registration_requirement_profile"]["focus_target_with_other"])
        self.assertEqual(row["law_fetch_meta"]["selected_byl_title"], "관광사업의 등록기준(제5조 관련)")
        self.assertEqual(row["additional_criteria_count"], 1)
        self.assertEqual(payload["requirement_focus_summary"]["capital_and_technical_total"], 1)
        self.assertEqual(payload["requirement_focus_summary"]["real_capital_and_technical_with_other_total"], 1)
        self.assertEqual(payload["requirement_focus_summary"]["inferred_capital_and_technical_total"], 0)

    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._prepare_ui_payload")
    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._load_rule_catalog")
    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._load_catalog")
    def test_build_expanded_catalog_preserves_previous_candidate_state(
        self,
        mock_load_catalog,
        mock_load_rule_catalog,
        mock_prepare_ui_payload,
    ):
        mock_load_catalog.return_value = {}
        mock_load_rule_catalog.return_value = {}
        mock_prepare_ui_payload.return_value = {
            "industries": [
                {
                    "service_code": "A001",
                    "service_name": "Alpha Clinic",
                    "major_code": "01",
                    "major_name": "Health",
                    "has_rule": False,
                },
                {
                    "service_code": "B001",
                    "service_name": "Beta Lab",
                    "major_code": "01",
                    "major_name": "Health",
                    "has_rule": False,
                },
            ],
            "rules_lookup": {},
        }
        previous_payload = {
            "mapping_pipeline": {
                "last_auto_collection": {
                    "run_at": "2026-03-06T20:00:18",
                    "success_total": 1,
                },
                "auto_collection_runs": [
                    {
                        "run_at": "2026-03-06T20:00:18",
                        "success_total": 1,
                    }
                ],
            },
            "industries": [
                {
                    "service_code": "A001",
                    "collection_status": "candidate_collected",
                    "mapping_status": "candidate_collected",
                    "auto_collection_at": "2026-03-06T20:00:18",
                    "auto_collection_error": "",
                    "auto_law_candidates": [{"law_title": "Medical Act", "score": 4}],
                },
                {
                    "service_code": "B001",
                    "collection_status": "pending_law_mapping",
                    "mapping_status": "queued_law_mapping_no_hit",
                    "auto_collection_at": "2026-03-06T20:00:18",
                    "auto_collection_error": "",
                    "auto_law_candidates": [],
                },
            ],
        }

        payload = collect_permit_extended_criteria.build_expanded_catalog(
            max_rules=0,
            timeout_sec=25,
            workers=2,
            candidate_extractor=lambda row, timeout_sec=50: collect_permit_extended_criteria.CandidateExtraction(
                ok=False,
                service_code=str(row.get("service_code") or ""),
                industry_name=str(row.get("service_name") or ""),
                data={},
                error="candidate_missing",
            ),
            previous_payload=previous_payload,
        )

        industries = {row["service_code"]: row for row in payload["industries"]}
        self.assertEqual(industries["A001"]["collection_status"], "candidate_collected")
        self.assertEqual(industries["A001"]["mapping_status"], "candidate_collected")
        self.assertEqual(industries["A001"]["auto_collection_at"], "2026-03-06T20:00:18")
        self.assertEqual(industries["A001"]["auto_law_candidates"][0]["law_title"], "Medical Act")
        self.assertEqual(industries["A001"]["mapping_batch_id"], "M01-B01")
        self.assertEqual(industries["A001"]["mapping_batch_seq"], 1)

        self.assertEqual(industries["B001"]["collection_status"], "pending_law_mapping")
        self.assertEqual(industries["B001"]["mapping_status"], "queued_law_mapping_no_hit")
        self.assertEqual(industries["B001"]["auto_collection_at"], "2026-03-06T20:00:18")
        self.assertEqual(industries["B001"]["auto_law_candidates"], [])
        self.assertEqual(industries["B001"]["mapping_batch_id"], "M01-B01")
        self.assertEqual(industries["B001"]["mapping_batch_seq"], 2)

        self.assertEqual(payload["summary"]["candidate_collected_industry_total"], 1)
        self.assertEqual(payload["summary"]["queued_law_mapping_no_hit_total"], 1)
        self.assertEqual(payload["summary"]["pending_industry_total"], 2)
        self.assertEqual(payload["mapping_pipeline"]["last_auto_collection"]["run_at"], "2026-03-06T20:00:18")
        self.assertEqual(len(payload["mapping_pipeline"]["auto_collection_runs"]), 1)

    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._prepare_ui_payload")
    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._load_rule_catalog")
    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._load_catalog")
    def test_build_expanded_catalog_collects_candidate_criteria(
        self,
        mock_load_catalog,
        mock_load_rule_catalog,
        mock_prepare_ui_payload,
    ):
        mock_load_catalog.return_value = {}
        mock_load_rule_catalog.return_value = {}
        mock_prepare_ui_payload.return_value = {
            "industries": [
                {
                    "service_code": "A001",
                    "service_name": "Alpha Clinic",
                    "major_code": "01",
                    "major_name": "Health",
                    "has_rule": False,
                    "auto_law_candidates": [{"law_title": "Medical Act", "law_url": "https://example.com"}],
                }
            ],
            "rules_lookup": {},
        }

        def fake_candidate_extractor(row, timeout_sec=50):
            return collect_permit_extended_criteria.CandidateExtraction(
                ok=True,
                service_code=str(row.get("service_code") or ""),
                industry_name=str(row.get("service_name") or ""),
                data={
                    "service_code": "A001",
                    "candidate_criteria_status": "candidate_criteria_extracted",
                    "candidate_basis_title": "별표 1",
                    "candidate_criteria_count": 2,
                    "candidate_criteria_lines": [
                        {"category": "core_requirement", "text": "자본금 1억원 이상"},
                        {"category": "facility_misc", "text": "사무실 확보 필요"},
                    ],
                    "candidate_additional_criteria_lines": [
                        {"category": "document", "text": "신청서 제출"}
                    ],
                    "candidate_legal_basis": [
                        {"law_title": "Medical Act", "article": "별표 1", "url": "https://example.com"}
                    ],
                },
            )

        payload = collect_permit_extended_criteria.build_expanded_catalog(
            max_rules=0,
            timeout_sec=25,
            workers=2,
            candidate_extractor=fake_candidate_extractor,
        )

        row = payload["industries"][0]
        self.assertEqual(row["candidate_criteria_status"], "candidate_criteria_extracted")
        self.assertEqual(row["candidate_basis_title"], "별표 1")
        self.assertEqual(row["candidate_criteria_count"], 3)
        self.assertEqual(row["candidate_criteria_lines"][0]["text"], "자본금 1억원 이상")
        self.assertEqual(row["law_title"], "Medical Act")
        self.assertEqual(row["legal_basis_title"], "별표 1")
        self.assertEqual(row["criteria_source_type"], "candidate_pack")
        self.assertEqual(row["status"], "candidate_criteria_extracted")
        self.assertEqual(row["criteria_summary"][0]["text"], "자본금 1억원 이상")
        self.assertEqual(row["criteria_additional"][0]["text"], "신청서 제출")
        self.assertEqual(row["legal_basis"][0]["law_title"], "Medical Act")
        self.assertEqual(payload["summary"]["candidate_criteria_extracted_total"], 1)
        self.assertEqual(payload["summary"]["candidate_extraction_error_total"], 0)
        self.assertEqual(payload["summary"]["real_industry_total"], 1)
        self.assertEqual(payload["summary"]["real_with_legal_basis_total"], 1)
        self.assertEqual(payload["summary"]["real_with_registration_criteria_total"], 1)
        self.assertEqual(payload["summary"]["real_blank_total"], 0)

    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._prepare_ui_payload")
    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._load_rule_catalog")
    @patch("scripts.collect_permit_extended_criteria.permit_diagnosis_calculator._load_catalog")
    def test_build_expanded_catalog_counts_additional_candidate_lines(
        self,
        mock_load_catalog,
        mock_load_rule_catalog,
        mock_prepare_ui_payload,
    ):
        mock_load_catalog.return_value = {}
        mock_load_rule_catalog.return_value = {}
        mock_prepare_ui_payload.return_value = {
            "industries": [
                {
                    "service_code": "A001",
                    "service_name": "Alpha Hall",
                    "major_code": "03",
                    "major_name": "Culture",
                    "has_rule": False,
                    "auto_law_candidates": [{"law_title": "Performance Act", "law_url": "https://example.com"}],
                }
            ],
            "rules_lookup": {},
        }

        def fake_candidate_extractor(row, timeout_sec=50):
            return collect_permit_extended_criteria.CandidateExtraction(
                ok=True,
                service_code=str(row.get("service_code") or ""),
                industry_name=str(row.get("service_name") or ""),
                data={
                    "service_code": "A001",
                    "candidate_criteria_status": "candidate_criteria_extracted",
                    "candidate_criteria_count": 0,
                    "candidate_criteria_lines": [],
                    "candidate_additional_criteria_lines": [
                        {"category": "operations", "text": "안전관리조직 설치"}
                    ],
                    "candidate_legal_basis": [
                        {"law_title": "Performance Act", "article": "안전관리조직의 설치기준", "url": "https://example.com"}
                    ],
                },
            )

        payload = collect_permit_extended_criteria.build_expanded_catalog(
            max_rules=0,
            timeout_sec=25,
            workers=2,
            candidate_extractor=fake_candidate_extractor,
        )

        row = payload["industries"][0]
        self.assertEqual(row["candidate_criteria_count"], 1)
        self.assertEqual(row["candidate_basis_title"], "안전관리조직의 설치기준")


if __name__ == "__main__":
    unittest.main()
