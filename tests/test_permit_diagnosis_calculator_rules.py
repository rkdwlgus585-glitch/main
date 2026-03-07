import unittest
from unittest.mock import patch

import permit_diagnosis_calculator


class PermitDiagnosisCalculatorRulesTest(unittest.TestCase):
    def test_merge_manual_rule_groups_synthesizes_rule_seed_for_real_service_code(self):
        merged = permit_diagnosis_calculator._merge_manual_rule_groups(
            permit_diagnosis_calculator._blank_rule_catalog(),
            {
                "manual_rule_groups": [
                    {
                        "rule_id": "wood-sawmill",
                        "industry_name": "제재업",
                        "service_codes": ["09_27_03_P"],
                        "requirements": {
                            "capital_eok": 0.3,
                            "technicians": 1,
                            "equipment_count": 0,
                            "deposit_days": 0,
                        },
                        "legal_basis": [
                            {
                                "law_title": "목재의 지속가능한 이용에 관한 법률 시행령",
                                "article": "목재생산업의 종류별 등록기준(제24조제1항 관련)",
                                "url": "https://www.law.go.kr/법령/목재의지속가능한이용에관한법률시행령",
                            }
                        ],
                        "pending_criteria_lines": [
                            {"category": "personnel_misc", "text": "기술인력 1명 이상"},
                            {"category": "office", "text": "자본금 3천만원 이상과 사무실"},
                        ],
                    }
                ]
            },
        )

        index = permit_diagnosis_calculator._build_rule_index(merged)
        rule = index["by_service_code"]["09_27_03_P"]
        self.assertEqual(rule["industry_name"], "제재업")
        self.assertEqual(rule["requirements"]["capital_eok"], 0.3)
        self.assertEqual(rule["requirements"]["technicians"], 1)
        self.assertTrue(rule["typed_criteria"])
        self.assertTrue(rule["document_templates"])
        self.assertEqual(rule["mapping_meta"]["coverage_status"], "partial")

    def test_rule_catalog_only_accepts_objective_legal_sources(self):
        rule_catalog = permit_diagnosis_calculator._load_rule_catalog(
            permit_diagnosis_calculator.DEFAULT_RULES_PATH
        )
        index = permit_diagnosis_calculator._build_rule_index(rule_catalog)
        self.assertGreaterEqual(len(index["rules"]), 20)
        for rule in index["rules"]:
            legal_basis = list(rule.get("legal_basis") or [])
            self.assertTrue(legal_basis)
            for basis in legal_basis:
                self.assertTrue(
                    permit_diagnosis_calculator._is_objective_source_url(str(basis.get("url", "") or ""))
                )

    def test_evaluate_registration_diagnosis_boundary_inputs(self):
        rule = {
            "industry_name": "테스트업",
            "requirements": {
                "capital_eok": 1.5,
                "technicians": 2,
                "equipment_count": 1,
                "deposit_days": 10,
            },
            "legal_basis": [{"law_title": "테스트법", "article": "별표 1", "url": "https://www.law.go.kr"}],
        }
        low = permit_diagnosis_calculator.evaluate_registration_diagnosis(
            rule=rule,
            current_capital_eok=-5,
            current_technicians=-2,
            current_equipment_count=-1,
            raw_capital_input="-5",
        )
        self.assertEqual(low["capital"]["current"], 0)
        self.assertEqual(low["technicians"]["current"], 0)
        self.assertEqual(low["equipment"]["current"], 0)
        self.assertFalse(low["overall_ok"])
        self.assertEqual(low["capital"]["gap"], 1.5)
        self.assertEqual(low["technicians"]["gap"], 2)
        self.assertEqual(low["equipment"]["gap"], 1)

        ok = permit_diagnosis_calculator.evaluate_registration_diagnosis(
            rule=rule,
            current_capital_eok=1.5,
            current_technicians=2,
            current_equipment_count=1,
            raw_capital_input="1.5",
        )
        self.assertTrue(ok["overall_ok"])
        self.assertEqual(ok["capital"]["gap"], 0)
        self.assertEqual(ok["technicians"]["gap"], 0)
        self.assertEqual(ok["equipment"]["gap"], 0)

        suspicious = permit_diagnosis_calculator.evaluate_registration_diagnosis(
            rule=rule,
            current_capital_eok=120,
            current_technicians=2,
            current_equipment_count=1,
            raw_capital_input="120",
        )
        self.assertTrue(suspicious["capital_input_suspicious"])

    def test_prepare_ui_payload_includes_rules_only_category(self):
        payload = permit_diagnosis_calculator._prepare_ui_payload(
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._load_rule_catalog(
                permit_diagnosis_calculator.DEFAULT_RULES_PATH
            ),
        )
        major_codes = {row.get("major_code") for row in payload.get("major_categories", [])}
        self.assertIn(permit_diagnosis_calculator.RULES_ONLY_CATEGORY_CODE, major_codes)
        summary = payload.get("summary", {})
        self.assertEqual(int(summary.get("industry_total", 0)), 0)
        self.assertEqual(int(summary.get("with_registration_rule_total", 0)), 0)
        self.assertGreater(int(summary.get("rules_only_industry_total", 0)), 0)
        self.assertGreater(int(summary.get("selector_industry_total", 0)), int(summary.get("industry_total", 0)))
        self.assertIn("coverage_pct", summary)
        self.assertIn("pending_rule_total", summary)
        self.assertIn(summary.get("public_claim_level"), {"phased", "full"})
        self.assertEqual(
            int(summary.get("industry_total", 0)),
            int(summary.get("with_registration_rule_total", 0)) + int(summary.get("pending_rule_total", 0)),
        )

    def test_build_html_contains_expanded_input_fields(self):
        html = permit_diagnosis_calculator.build_html(
            title="AI 인허가 사전검토 진단기(신규등록 전용)",
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._load_rule_catalog(
                permit_diagnosis_calculator.DEFAULT_RULES_PATH
            ),
        )
        self.assertIn('id="focusModeSelect"', html)
        self.assertIn('id="focusQuickSelect"', html)
        self.assertIn('id="industrySearchInput"', html)
        self.assertIn("permitInputWizard", html)
        self.assertIn("permitWizardRail", html)
        self.assertIn("permitWizardStepTitle", html)
        self.assertIn("permitWizardSummary", html)
        self.assertIn("permitWizardBlocker", html)
        self.assertIn("permitWizardStep1", html)
        self.assertIn("permitWizardStep4", html)
        self.assertIn("선택 준비 상태", html)
        self.assertIn("업종명 우선 검색", html)
        self.assertIn('id="categorySelect"', html)
        self.assertIn('id="industrySelect"', html)
        self.assertIn('id="capitalInput"', html)
        self.assertIn('id="technicianInput"', html)
        self.assertIn('id="equipmentInput"', html)
        self.assertIn('id="fillRequirementPreset"', html)
        self.assertIn('id="resetHoldingsPreset"', html)
        self.assertIn('id="presetActionHint"', html)
        self.assertIn("holdingsPriorityHint", html)
        self.assertIn("mobileQuickBar", html)
        self.assertIn("mobileQuickPresetButton", html)
        self.assertIn("mobileQuickResultButton", html)
        self.assertIn('id="legalBasis"', html)
        self.assertIn('id="focusProfileBox"', html)
        self.assertIn('id="qualityFlagsBox"', html)
        self.assertIn("focusModePills", html)
        self.assertIn("smartIndustryProfile", html)
        self.assertIn("resultBannerTitle", html)
        self.assertIn("resultActionWrap", html)
        self.assertIn("resultBriefWrap", html)
        self.assertIn('id="resultBrief"', html)
        self.assertIn('id="btnCopyResultBrief"', html)
        self.assertIn("advancedInputs", html)
        self.assertIn("tryAutoSelectIndustry", html)
        self.assertIn("findPermitWizardResumeStep", html)
        self.assertIn("syncPermitWizardSummary", html)
        self.assertIn("syncPermitWizardBlocker", html)
        self.assertIn("syncHoldingsPriorityHint", html)
        self.assertIn("syncPermitResultBrief", html)
        self.assertIn("normalizeSearchKey", html)
        self.assertIn("getSearchMatchMeta", html)
        self.assertIn("filterAndSortRowsBySearch", html)
        self.assertIn("getVisibleCategoryRows", html)
        self.assertIn("getPermitCoreGuide", html)
        self.assertIn("syncPermitWizardNavCopies", html)
        self.assertIn("현재 보유 구조화 기준 없음", html)
        self.assertIn("정량 기준이 없는 업종은 법령 근거와 준비 서류 위주로 먼저 확인합니다.", html)
        self.assertIn("법령 확인형", html)
        self.assertIn("필수 등록요건과 법령 근거, 준비 상태를 한 번에 비교합니다.", html)
        self.assertIn("const permitCatalog", html)
        self.assertIn("const ruleLookup", html)
        self.assertIn("focus_selector_entries", html)
        self.assertIn("selector_catalog", html)
        self.assertIn("platform_catalog", html)
        self.assertIn("master_catalog", html)
        self.assertIn("const masterCatalog = permitCatalog.master_catalog", html)
        self.assertIn("const displayCatalog", html)
        self.assertIn("selectorEntriesByCode", html)
        self.assertIn("displayRowsByCode", html)
        self.assertNotIn("현재 보유 현황 3가지만 입력하면 됩니다.", html)
        self.assertNotIn("핵심 3요건만 먼저 넣고", html)
        self.assertNotIn("필수 3요건과 법령 근거, 준비 상태를 한 번에 비교합니다.", html)
        self.assertNotIn("핵심 3요건이 충족됩니다.", html)
        self.assertNotIn("핵심 3요건 중 부족한 항목을 먼저 보완해야 합니다.", html)

    def test_build_html_keeps_permit_wizard_meta_in_shared_scope(self):
        html = permit_diagnosis_calculator.build_html(
            title="AI 인허가 사전검토 진단기(신규등록 전용)",
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._load_rule_catalog(
                permit_diagnosis_calculator.DEFAULT_RULES_PATH
            ),
        )
        wizard_meta_idx = html.index("const permitWizardStepsMeta = [")
        layout_idx = html.index("const applyExperienceLayout = () => {")
        sync_idx = html.index("const syncPermitWizard = () => {")
        self.assertLess(wizard_meta_idx, layout_idx)
        self.assertLess(wizard_meta_idx, sync_idx)

    @patch("permit_diagnosis_calculator._prepare_ui_payload")
    def test_build_bootstrap_payload_compacts_unused_industry_fields(self, mock_prepare_payload):
        mock_prepare_payload.return_value = {
            "summary": {"industry_total": 1, "major_category_total": 1, "with_registration_rule_total": 0},
            "major_categories": [{"major_code": "01", "major_name": "시설", "industry_count": 1}],
            "industries": [
                {
                    "service_code": "A001",
                    "service_name": "테스트업",
                    "major_code": "01",
                    "major_name": "시설",
                    "registration_requirement_profile": {
                        "capital_required": True,
                        "technical_personnel_required": True,
                        "focus_target": True,
                        "focus_target_with_other": False,
                        "inferred_focus_candidate": False,
                    },
                    "group_description": "unused",
                    "detail_url": "https://example.com/detail",
                    "auto_law_candidates": [
                        {"law_title": "건설산업기본법", "law_url": "https://www.law.go.kr", "unused": "x"}
                    ],
                    "candidate_criteria_count": 1,
                    "candidate_criteria_lines": [{"text": "자본금 1억원", "extra": "y"}],
                    "candidate_additional_criteria_lines": [{"text": "사무실 확보", "extra": "z"}],
                    "candidate_legal_basis": [
                        {
                            "law_title": "건설산업기본법",
                            "article": "별표 1",
                            "url": "https://www.law.go.kr",
                            "extra": "ignored",
                        }
                    ],
                    "raw_source_proof": {
                        "proof_status": "raw_source_hardened",
                        "official_snapshot_note": "law.go.kr curated snapshot",
                        "source_checksum": "proof-123",
                        "source_urls": ["https://www.law.go.kr"],
                        "source_url_total": 1,
                        "capture_meta": {
                            "captured_at": "2026-03-08 01:00:00",
                            "capture_kind": "law_go_kr_curated_family_registry",
                            "scope_policy": "capital_and_technical_only",
                            "family_key": "건설산업기본법 시행령",
                            "catalog_source_kind": "focus_family_registry",
                        },
                    },
                }
            ],
            "rules_lookup": {},
            "rule_catalog_meta": {"version": "v1", "effective_date": "2026-03-07", "source": {}},
        }
        bundle = permit_diagnosis_calculator.build_bootstrap_payload(
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._blank_rule_catalog(),
        )
        industry = bundle["permitCatalog"]["industries"][0]
        self.assertEqual(industry["service_name"], "테스트업")
        self.assertNotIn("detail_url", industry)
        self.assertNotIn("group_description", industry)
        self.assertEqual(industry["candidate_criteria_lines"][0], {"text": "자본금 1억원"})
        self.assertEqual(
            industry["auto_law_candidates"][0],
            {"law_title": "건설산업기본법", "article": "", "url": "https://www.law.go.kr"},
        )
        self.assertEqual(
            industry["candidate_legal_basis"][0],
            {"law_title": "건설산업기본법", "article": "별표 1", "url": "https://www.law.go.kr"},
        )
        self.assertEqual(industry["raw_source_proof"]["source_checksum"], "proof-123")
        self.assertEqual(industry["raw_source_proof"]["source_url_total"], 1)

    def test_build_html_supports_external_data_url(self):
        html = permit_diagnosis_calculator.build_html(
            title="AI 인허가 사전검토 진단기(신규등록 전용)",
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._blank_rule_catalog(),
            bootstrap_payload={
                "permitCatalog": {
                    "major_categories": [],
                    "industries": [{"service_code": "A001", "service_name": "테스트업", "major_code": "01"}],
                    "summary": {"industry_total": 1, "major_category_total": 1, "with_registration_rule_total": 0},
                },
                "ruleLookup": {},
                "ruleCatalogMeta": {"version": "v1", "effective_date": "2026-03-07", "source": {}},
            },
            data_url="https://example.com/permit-data.json",
            data_encoding="gzip",
        )
        self.assertIn('const permitDataUrl = "https://example.com/permit-data.json";', html)
        self.assertIn('const permitDataEncoding = "gzip";', html)
        self.assertIn("const inlineBootstrap = {};", html)
        self.assertNotIn('"service_name":"테스트업"', html)

    def test_build_html_supports_payload_page_encoding(self):
        html = permit_diagnosis_calculator.build_html(
            title="AI 인허가 사전검토 진단기(신규등록 전용)",
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._blank_rule_catalog(),
            bootstrap_payload={},
            data_url="https://example.com/permit-data-page",
            data_encoding="gzip-base64-html",
        )
        self.assertIn('const permitDataEncoding = "gzip-base64-html";', html)
        self.assertIn("const extractHtmlPayload = (htmlText) => {", html)

    def test_build_html_supports_payload_rest_rendered_encoding(self):
        html = permit_diagnosis_calculator.build_html(
            title="AI 인허가 사전검토 진단기(신규등록 전용)",
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._blank_rule_catalog(),
            bootstrap_payload={},
            data_url="https://seoulmna.kr/wp-json/wp/v2/pages/1810?_fields=content.rendered&context=view",
            data_encoding="gzip-base64-rest-rendered",
        )
        self.assertIn('const permitDataEncoding = "gzip-base64-rest-rendered";', html)
        self.assertIn("const extractRenderedPayloadFromJson = async (res) => {", html)

    def test_build_html_uses_compressed_inline_bootstrap(self):
        html = permit_diagnosis_calculator.build_html(
            title="AI 인허가 사전검토 진단기(신규등록 전용)",
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._blank_rule_catalog(),
            bootstrap_payload={
                "permitCatalog": {
                    "major_categories": [],
                    "industries": [{"service_code": "A001", "service_name": "테스트업", "major_code": "01"}],
                    "summary": {"industry_total": 1, "major_category_total": 1, "with_registration_rule_total": 0},
                },
                "ruleLookup": {},
                "ruleCatalogMeta": {"version": "v1", "effective_date": "2026-03-07", "source": {}},
            },
        )
        self.assertIn('const permitDataUrl = "";', html)
        self.assertIn('const permitDataEncoding = "";', html)
        self.assertIn('const inlineBootstrap = {};', html)
        self.assertIn("const inlineBootstrapCompressed = \"", html)
        self.assertNotIn('"service_name":"테스트업"', html)

    def test_build_html_repairs_visible_text_labels(self):
        html = permit_diagnosis_calculator.build_html(
            title="AI 인허가 사전검토 진단기(신규등록 전용)",
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._blank_rule_catalog(),
        )
        self.assertIn("기타 준비 상태", html)
        self.assertIn("사무실/영업소 확보", html)
        self.assertIn("법령 근거", html)
        self.assertIn("자동 점검 결과", html)
        self.assertIn("준비 서류", html)
        self.assertIn("다음 단계", html)
        self.assertNotIn("?? ???? ??", html)
        self.assertNotIn("실��종", html)

    def test_build_html_fragment_mode_emits_wordpress_embed_section(self):
        html = permit_diagnosis_calculator.build_html(
            title="AI 인허가 사전검토 진단기(신규등록 전용)",
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._blank_rule_catalog(),
            fragment=True,
        )
        self.assertTrue(html.startswith('<section id="smna-permit-precheck"'))
        self.assertNotIn("<!doctype html>", html.lower())
        self.assertIn('document.querySelector(".entry-title, .page-title")', html)
        self.assertIn("#smna-permit-precheck .container", html)

    @patch("permit_diagnosis_calculator._load_expanded_criteria_catalog")
    def test_prepare_ui_payload_merges_expanded_industry_metadata(self, mock_load_expanded):
        mock_load_expanded.return_value = {
            "industries": [
                {
                    "service_code": "A001",
                    "collection_status": "candidate_collected",
                    "status": "candidate_criteria_extracted",
                    "law_title": "의료법",
                    "legal_basis_title": "제10조(등록)",
                    "legal_basis": [{"law_title": "의료법", "article": "제10조(등록)", "url": "https://www.law.go.kr"}],
                    "criteria_summary": [{"text": "자본금 1억원 이상"}],
                    "criteria_additional": [{"text": "신청서 제출"}],
                    "criteria_source_type": "article_body",
                    "quality_flags": ["sparse_criteria"],
                    "registration_requirement_profile": {
                        "capital_required": True,
                        "technical_personnel_required": False,
                        "other_required": True,
                        "focus_target": False,
                        "focus_target_with_other": False,
                        "focus_bucket": "partial_core",
                    },
                    "auto_law_candidates": [{"law_title": "의료법", "law_url": "https://www.law.go.kr"}],
                    "candidate_criteria_count": 2,
                    "candidate_criteria_lines": [{"text": "자본금 1억원 이상"}],
                }
            ]
        }
        payload = permit_diagnosis_calculator._prepare_ui_payload(
            catalog={
                "summary": {},
                "major_categories": [{"major_code": "01", "major_name": "Health", "industry_count": 1}],
                "industries": [
                    {
                        "service_code": "A001",
                        "service_name": "테스트업",
                        "major_code": "01",
                        "major_name": "Health",
                        "group_code": "01",
                        "group_name": "테스트그룹",
                        "group_description": "그룹 설명",
                        "group_declared_total": 3,
                        "detail_url": "https://example.com",
                    }
                ],
            },
            rule_catalog=permit_diagnosis_calculator._blank_rule_catalog(),
        )
        row = payload["industries"][0]
        self.assertEqual(row["group_name"], "테스트그룹")
        self.assertEqual(row["group_description"], "그룹 설명")
        self.assertEqual(row["group_declared_total"], 3)
        self.assertEqual(row["collection_status"], "candidate_collected")
        self.assertEqual(row["status"], "candidate_criteria_extracted")
        self.assertEqual(row["law_title"], "의료법")
        self.assertEqual(row["legal_basis_title"], "제10조(등록)")
        self.assertEqual(row["criteria_summary"][0]["text"], "자본금 1억원 이상")
        self.assertEqual(row["criteria_additional"][0]["text"], "신청서 제출")
        self.assertEqual(row["criteria_source_type"], "article_body")
        self.assertEqual(row["quality_flags"], ["sparse_criteria"])
        self.assertTrue(row["registration_requirement_profile"]["capital_required"])
        self.assertEqual(row["candidate_criteria_count"], 2)
        self.assertEqual(row["candidate_criteria_lines"][0]["text"], "자본금 1억원 이상")
        self.assertEqual(payload["summary"]["candidate_law_total"], 1)
        self.assertEqual(payload["summary"]["candidate_criteria_total"], 1)
        self.assertIn("focus_target_total", payload["summary"])
        self.assertEqual(payload["summary"]["focus_default_mode"], "all")

    @patch("permit_diagnosis_calculator._load_expanded_criteria_catalog")
    def test_prepare_ui_payload_summarizes_focus_target_rows(self, mock_load_expanded):
        mock_load_expanded.return_value = {
            "industries": [
                {
                    "service_code": "A001",
                    "registration_requirement_profile": {
                        "capital_required": True,
                        "technical_personnel_required": True,
                        "other_required": True,
                        "focus_target": True,
                        "focus_target_with_other": True,
                        "inferred_focus_candidate": False,
                    },
                }
            ]
        }
        payload = permit_diagnosis_calculator._prepare_ui_payload(
            catalog={
                "summary": {},
                "major_categories": [{"major_code": "01", "major_name": "Health", "industry_count": 1}],
                "industries": [
                    {
                        "service_code": "A001",
                        "service_name": "테스트업",
                        "major_code": "01",
                        "major_name": "Health",
                    }
                ],
            },
            rule_catalog=permit_diagnosis_calculator._blank_rule_catalog(),
        )
        summary = payload["summary"]
        self.assertEqual(summary["focus_target_total"], 1)
        self.assertEqual(summary["focus_target_with_other_total"], 1)
        self.assertEqual(summary["real_focus_target_total"], 1)
        self.assertEqual(summary["real_focus_target_with_other_total"], 1)
        self.assertEqual(summary["rules_only_focus_target_total"], 0)
        self.assertEqual(summary["rules_only_focus_target_with_other_total"], 0)
        self.assertEqual(summary["inferred_focus_target_total"], 0)
        self.assertEqual(summary["focus_default_mode"], "focus_only")

    @patch("permit_diagnosis_calculator._load_expanded_criteria_catalog")
    def test_build_bootstrap_payload_includes_focus_entry_metadata(self, mock_load_expanded):
        mock_load_expanded.return_value = {
            "industries": [
                {
                    "service_code": "RULE::R1",
                    "collection_status": "criteria_extracted",
                    "law_title": "건설산업기본법 시행령",
                    "legal_basis_title": "별표 2 건설업 등록기준",
                    "quality_flags": [],
                    "registration_requirement_profile": {
                        "capital_required": True,
                        "technical_personnel_required": True,
                        "other_required": True,
                        "focus_target": True,
                        "focus_target_with_other": True,
                        "inferred_focus_candidate": False,
                        "capital_eok": 5.0,
                        "technicians_required": 5,
                        "other_components": ["equipment", "deposit"],
                        "profile_source": "structured_requirements",
                    },
                }
            ]
        }
        payload = permit_diagnosis_calculator.build_bootstrap_payload(
            catalog={
                "summary": {},
                "major_categories": [
                    {
                        "major_code": permit_diagnosis_calculator.RULES_ONLY_CATEGORY_CODE,
                        "major_name": permit_diagnosis_calculator.RULES_ONLY_CATEGORY_NAME,
                        "industry_count": 1,
                    }
                ],
                "industries": [],
            },
            rule_catalog={
                "version": "1",
                "effective_date": "2026-03-07",
                "source": {},
                "rule_groups": [
                    {
                        "rule_id": "R1",
                        "industry_name": "건축공사업(종합)",
                        "legal_basis": [
                            {
                                "law_title": "건설산업기본법 시행령",
                                "article": "별표 2 건설업 등록기준",
                                "url": "https://www.law.go.kr",
                            }
                        ],
                        "requirements": {"capital_eok": 5.0, "technicians": 5, "equipment_count": 1, "deposit_days": 30},
                    }
                ],
            },
        )
        permit_catalog = payload["permitCatalog"]
        self.assertEqual(len(permit_catalog["focus_entries"]), 1)
        focus_row = permit_catalog["focus_entries"][0]
        self.assertEqual(focus_row["service_code"], "RULE::R1")
        self.assertEqual(focus_row["law_title"], "건설산업기본법 시행령")
        self.assertEqual(focus_row["legal_basis_title"], "별표 2 건설업 등록기준")
        self.assertTrue(focus_row["registration_requirement_profile"]["focus_target_with_other"])
        self.assertEqual(permit_catalog["inferred_focus_entries"], [])
        self.assertEqual(permit_catalog["summary"]["focus_selector_entry_total"], 1)
        self.assertEqual(permit_catalog["summary"]["inferred_selector_entry_total"], 0)
        self.assertEqual(len(permit_catalog["focus_selector_entries"]), 1)
        self.assertEqual(len(permit_catalog["selector_entries"]), 1)
        selector_entry = permit_catalog["focus_selector_entries"][0]
        self.assertEqual(selector_entry["selector_kind"], "focus")
        self.assertEqual(selector_entry["selector_code"], "SEL::FOCUS::RULE::R1")
        self.assertEqual(selector_entry["canonical_service_code"], "RULE::R1")
        self.assertEqual(selector_entry["selector_category_code"], "SEL-FOCUS")
        self.assertEqual(selector_entry["selector_category_name"], "핵심 업종군")
        selector_catalog = permit_catalog["selector_catalog"]
        self.assertEqual(selector_catalog["summary"]["selector_category_total"], 1)
        self.assertEqual(selector_catalog["summary"]["selector_entry_total"], 1)
        self.assertEqual(selector_catalog["summary"]["selector_focus_total"], 1)
        self.assertEqual(selector_catalog["summary"]["selector_inferred_total"], 0)
        self.assertEqual(selector_catalog["summary"]["selector_real_entry_total"], 0)
        self.assertEqual(selector_catalog["summary"]["selector_rules_only_entry_total"], 1)
        self.assertEqual(selector_catalog["major_categories"][0]["major_code"], "SEL-FOCUS")
        selector_catalog_row = selector_catalog["industries"][0]
        self.assertEqual(selector_catalog_row["service_code"], "SEL::FOCUS::RULE::R1")
        self.assertEqual(selector_catalog_row["canonical_service_code"], "RULE::R1")
        self.assertEqual(selector_catalog_row["major_code"], "SEL-FOCUS")
        self.assertEqual(selector_catalog_row["major_name"], "핵심 업종군")
        self.assertTrue(selector_catalog_row["is_selector_row"])
        platform_catalog = permit_catalog["platform_catalog"]
        self.assertEqual(platform_catalog["summary"]["platform_industry_total"], 1)
        self.assertEqual(platform_catalog["summary"]["platform_real_row_total"], 0)
        self.assertEqual(platform_catalog["summary"]["platform_focus_registry_row_total"], 1)
        self.assertEqual(platform_catalog["summary"]["platform_promoted_selector_total"], 0)
        self.assertEqual(platform_catalog["summary"]["platform_absorbed_focus_total"], 0)
        self.assertEqual(platform_catalog["summary"]["platform_real_with_selector_alias_total"], 0)
        self.assertEqual(platform_catalog["summary"]["platform_focus_registry_with_alias_total"], 1)
        self.assertEqual(platform_catalog["summary"]["platform_focus_alias_total"], 1)
        self.assertEqual(platform_catalog["summary"]["platform_inferred_alias_total"], 0)
        platform_row = platform_catalog["industries"][0]
        self.assertEqual(platform_row["service_code"], "RULE::R1")
        self.assertEqual(platform_row["canonical_service_code"], "RULE::R1")
        self.assertEqual(platform_row["platform_row_origin"], "focus_registry_source")
        self.assertTrue(platform_row["platform_has_focus_alias"])
        self.assertFalse(platform_row["platform_has_inferred_alias"])
        self.assertEqual(len(platform_row["platform_selector_aliases"]), 1)
        self.assertEqual(platform_row["platform_selector_aliases"][0]["selector_code"], "SEL::FOCUS::RULE::R1")
        master_catalog = permit_catalog["master_catalog"]
        self.assertEqual(master_catalog["summary"]["master_industry_total"], 1)
        self.assertEqual(master_catalog["summary"]["master_real_row_total"], 0)
        self.assertEqual(master_catalog["summary"]["master_focus_registry_row_total"], 1)
        self.assertEqual(master_catalog["summary"]["master_promoted_row_total"], 0)
        self.assertEqual(master_catalog["summary"]["master_absorbed_row_total"], 0)
        self.assertEqual(master_catalog["summary"]["master_real_with_alias_total"], 0)
        self.assertEqual(master_catalog["summary"]["master_focus_row_total"], 1)
        self.assertEqual(master_catalog["summary"]["master_inferred_overlay_total"], 0)
        self.assertEqual(master_catalog["summary"]["master_canonicalized_promoted_total"], 0)
        self.assertEqual(master_catalog["feed_contract"]["primary_feed_name"], "master_catalog")
        self.assertEqual(master_catalog["feed_contract"]["overlay_feed_name"], "selector_catalog")
        self.assertEqual(
            master_catalog["feed_contract"]["focus_registry_row_key_policy"],
            "focus_registry_source rows use canonical_service_code as primary service_code",
        )
        self.assertEqual(
            master_catalog["feed_contract"]["absorbed_row_key_policy"],
            "focus_source_absorbed rows use canonical_service_code as primary service_code",
        )
        self.assertEqual(master_catalog["industries"][0]["service_code"], "RULE::R1")
        self.assertEqual(master_catalog["industries"][0]["canonical_service_code"], "RULE::R1")
        self.assertEqual(master_catalog["industries"][0]["master_row_origin"], "focus_registry_source")

    @patch("permit_diagnosis_calculator._load_expanded_criteria_catalog")
    def test_build_bootstrap_payload_merges_real_selector_alias_without_duplicate_platform_row(self, mock_load_expanded):
        mock_load_expanded.return_value = {
            "industries": [
                {
                    "service_code": "A001",
                    "law_title": "전자상거래법",
                    "legal_basis_title": "제12조(신고)",
                    "registration_requirement_profile": {
                        "capital_required": True,
                        "technical_personnel_required": True,
                        "focus_target": True,
                        "focus_target_with_other": False,
                        "inferred_focus_candidate": True,
                    },
                }
            ]
        }
        payload = permit_diagnosis_calculator.build_bootstrap_payload(
            catalog={
                "summary": {},
                "major_categories": [{"major_code": "09", "major_name": "유통", "industry_count": 1}],
                "industries": [
                    {
                        "service_code": "A001",
                        "service_name": "통신판매업",
                        "major_code": "09",
                        "major_name": "유통",
                    }
                ],
            },
            rule_catalog=permit_diagnosis_calculator._blank_rule_catalog(),
        )
        permit_catalog = payload["permitCatalog"]
        self.assertEqual(len(permit_catalog["focus_entries"]), 1)
        self.assertEqual(permit_catalog["focus_entries"][0]["service_code"], "A001")
        self.assertEqual(len(permit_catalog["selector_catalog"]["industries"]), 2)
        self.assertEqual(permit_catalog["selector_catalog"]["summary"]["selector_focus_total"], 1)
        self.assertEqual(permit_catalog["selector_catalog"]["summary"]["selector_inferred_total"], 1)
        self.assertEqual(permit_catalog["selector_catalog"]["summary"]["selector_real_entry_total"], 2)
        selector_codes = [row["service_code"] for row in permit_catalog["selector_catalog"]["industries"]]
        self.assertIn("SEL::FOCUS::A001", selector_codes)
        self.assertIn("SEL::INFERRED::A001", selector_codes)
        platform_catalog = permit_catalog["platform_catalog"]
        self.assertEqual(platform_catalog["summary"]["platform_industry_total"], 1)
        self.assertEqual(platform_catalog["summary"]["platform_real_row_total"], 1)
        self.assertEqual(platform_catalog["summary"]["platform_promoted_selector_total"], 0)
        self.assertEqual(platform_catalog["summary"]["platform_real_with_selector_alias_total"], 1)
        self.assertEqual(platform_catalog["summary"]["platform_focus_alias_total"], 1)
        self.assertEqual(platform_catalog["summary"]["platform_inferred_alias_total"], 1)
        platform_row = platform_catalog["industries"][0]
        self.assertEqual(platform_row["service_code"], "A001")
        self.assertEqual(platform_row["canonical_service_code"], "A001")
        self.assertEqual(platform_row["platform_row_origin"], "real_catalog")
        self.assertTrue(platform_row["platform_has_focus_alias"])
        self.assertTrue(platform_row["platform_has_inferred_alias"])
        self.assertEqual(len(platform_row["platform_selector_aliases"]), 2)
        alias_codes = sorted(alias["selector_code"] for alias in platform_row["platform_selector_aliases"])
        self.assertEqual(alias_codes, ["SEL::FOCUS::A001", "SEL::INFERRED::A001"])
        master_catalog = permit_catalog["master_catalog"]
        self.assertEqual(master_catalog["summary"]["master_industry_total"], 1)
        self.assertEqual(master_catalog["summary"]["master_real_row_total"], 1)
        self.assertEqual(master_catalog["summary"]["master_promoted_row_total"], 0)
        self.assertEqual(master_catalog["summary"]["master_real_with_alias_total"], 1)
        self.assertEqual(master_catalog["summary"]["master_focus_row_total"], 1)
        self.assertEqual(master_catalog["summary"]["master_inferred_overlay_total"], 1)
        self.assertEqual(master_catalog["summary"]["master_canonicalized_promoted_total"], 0)

    @patch("permit_diagnosis_calculator._prepare_ui_payload")
    def test_build_bootstrap_payload_filters_out_non_capital_technical_rows(self, mock_prepare_payload):
        mock_prepare_payload.return_value = {
            "summary": {"industry_total": 2, "major_category_total": 2, "with_registration_rule_total": 0},
            "major_categories": [
                {"major_code": "01", "major_name": "시설", "industry_count": 1},
                {"major_code": "02", "major_name": "기타", "industry_count": 1},
            ],
            "industries": [
                {
                    "service_code": "A001",
                    "service_name": "핵심업종",
                    "major_code": "01",
                    "major_name": "시설",
                    "registration_requirement_profile": {
                        "capital_required": True,
                        "technical_personnel_required": True,
                        "focus_target": True,
                        "focus_target_with_other": True,
                        "inferred_focus_candidate": False,
                    },
                },
                {
                    "service_code": "B001",
                    "service_name": "제외업종",
                    "major_code": "02",
                    "major_name": "기타",
                    "registration_requirement_profile": {
                        "capital_required": False,
                        "technical_personnel_required": False,
                        "focus_target": False,
                        "focus_target_with_other": False,
                        "inferred_focus_candidate": False,
                    },
                },
            ],
            "rules_lookup": {"A001": {"rule_id": "A001"}, "B001": {"rule_id": "B001"}},
            "rule_catalog_meta": {"version": "v1", "effective_date": "2026-03-07", "source": {}},
        }

        bundle = permit_diagnosis_calculator.build_bootstrap_payload(
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._blank_rule_catalog(),
        )

        permit_catalog = bundle["permitCatalog"]
        self.assertEqual([row["service_code"] for row in permit_catalog["industries"]], ["A001"])
        self.assertEqual([row["major_code"] for row in permit_catalog["major_categories"]], ["01"])
        self.assertEqual(permit_catalog["summary"]["scope_policy"], "capital_and_technical_only")
        self.assertEqual(permit_catalog["summary"]["industry_total"], 1)
        self.assertEqual(permit_catalog["summary"]["scope_real_industry_total"], 1)
        self.assertEqual(permit_catalog["summary"]["scope_rules_only_industry_total"], 0)
        self.assertEqual(sorted(bundle["ruleLookup"].keys()), ["A001"])

    @patch("permit_diagnosis_calculator._load_expanded_criteria_catalog")
    def test_build_bootstrap_payload_prefers_focus_seed_catalog_row_over_rules_only_duplicate(self, mock_load_expanded):
        mock_load_expanded.return_value = {"industries": []}
        payload = permit_diagnosis_calculator.build_bootstrap_payload(
            catalog={
                "summary": {"focus_seed_total": 1},
                "major_categories": [{"major_code": "31", "major_name": "건설", "industry_count": 1}],
                "industries": [
                    {
                        "service_code": "FOCUS::construction-general-geonchuk",
                        "service_name": "건축공사업(종합)",
                        "major_code": "31",
                        "major_name": "건설",
                        "group_code": "31-01",
                        "group_name": "건설업 등록기준",
                        "catalog_source_kind": "focus_seed_catalog",
                        "catalog_source_label": "permit_focus_seed_catalog",
                        "law_title": "건설산업기본법 시행령",
                        "legal_basis_title": "별표 2 건설업 등록기준",
                        "criteria_source_type": "rule_pack",
                        "has_rule": True,
                        "registration_requirement_profile": {
                            "capital_required": True,
                            "technical_personnel_required": True,
                            "other_required": False,
                            "focus_target": True,
                            "focus_target_with_other": False,
                            "inferred_focus_candidate": False,
                        },
                    }
                ],
            },
            rule_catalog={
                "version": "1",
                "effective_date": "2026-03-08",
                "source": {},
                "rule_groups": [
                    {
                        "rule_id": "construction-general-geonchuk",
                        "industry_name": "건축공사업(종합)",
                        "legal_basis": [
                            {
                                "law_title": "건설산업기본법 시행령",
                                "article": "별표 2 건설업 등록기준",
                                "url": "https://www.law.go.kr",
                            }
                        ],
                        "requirements": {
                            "capital_eok": 5.0,
                            "technicians": 5,
                            "equipment_count": 0,
                            "deposit_days": 0,
                        },
                    }
                ],
            },
        )

        permit_catalog = payload["permitCatalog"]
        self.assertEqual(permit_catalog["summary"]["focus_target_total"], 1)
        self.assertEqual(permit_catalog["summary"]["real_focus_target_total"], 1)
        self.assertEqual(permit_catalog["summary"]["rules_only_focus_target_total"], 0)
        self.assertEqual(permit_catalog["summary"]["scope_real_industry_total"], 1)
        self.assertEqual(permit_catalog["summary"]["scope_rules_only_industry_total"], 0)
        focus_row = permit_catalog["focus_entries"][0]
        self.assertEqual(focus_row["service_code"], "FOCUS::construction-general-geonchuk")
        self.assertEqual(focus_row["catalog_source_kind"], "focus_seed_catalog")
        self.assertFalse(focus_row["is_rules_only"])
        self.assertEqual(
            permit_catalog["focus_selector_entries"][0]["selector_code"],
            "SEL::FOCUS::construction-general-geonchuk",
        )

        platform_catalog = permit_catalog["platform_catalog"]
        self.assertEqual(platform_catalog["summary"]["platform_real_row_total"], 1)
        self.assertEqual(platform_catalog["summary"]["platform_focus_registry_row_total"], 0)
        platform_row = platform_catalog["industries"][0]
        self.assertEqual(platform_row["platform_row_origin"], "real_catalog")
        self.assertEqual(platform_row["catalog_source_kind"], "focus_seed_catalog")

        master_catalog = permit_catalog["master_catalog"]
        self.assertEqual(master_catalog["summary"]["master_real_row_total"], 1)
        self.assertEqual(master_catalog["summary"]["master_focus_registry_row_total"], 0)
        self.assertEqual(master_catalog["industries"][0]["master_row_origin"], "real_catalog")

    def test_merge_catalog_payloads_prefers_focus_family_registry_over_focus_seed(self):
        merged = permit_diagnosis_calculator._merge_catalog_payloads(
            {
                "summary": {},
                "major_categories": [],
                "industries": [],
            },
            (
                "focus_seed_catalog",
                {
                    "industries": [
                        {
                            "service_code": "FOCUS::construction-general-geonchuk",
                            "service_name": "건축공사업",
                            "major_code": "31",
                            "major_name": "건설",
                            "catalog_source_kind": "focus_seed_catalog",
                        }
                    ]
                },
            ),
            (
                "focus_family_registry",
                {
                    "industries": [
                        {
                            "service_code": "FOCUS::construction-general-geonchuk",
                            "service_name": "건축공사업(종합)",
                            "major_code": "31",
                            "major_name": "건설",
                            "catalog_source_kind": "focus_family_registry",
                        }
                    ]
                },
            ),
        )

        self.assertEqual(merged["summary"].get("focus_seed_total", 0), 0)
        self.assertEqual(merged["summary"]["focus_family_registry_total"], 1)
        self.assertEqual(len(merged["industries"]), 1)
        self.assertEqual(merged["industries"][0]["catalog_source_kind"], "focus_family_registry")
        self.assertEqual(merged["industries"][0]["service_name"], "건축공사업(종합)")


if __name__ == "__main__":
    unittest.main()

