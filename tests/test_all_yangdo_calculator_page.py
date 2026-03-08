import importlib
import unittest


allmod = importlib.import_module("all")


def _make_row(
    number="",
    uid="",
    license_name="",
    license_year="",
    specialty="",
    y23="",
    y24="",
    y25="",
    price="",
    claim="",
    debt="",
    liq="",
    capital="",
    surplus="",
):
    row = [""] * 41
    row[0] = str(number)
    row[2] = str(license_name)
    row[3] = str(license_year)
    row[4] = str(specialty)
    row[8] = str(y23)
    row[9] = str(y24)
    row[12] = str(y25)
    row[18] = str(price)
    row[19] = str(capital)
    row[21] = str(debt)
    row[23] = str(liq)
    row[30] = str(surplus)
    row[33] = str(claim)
    row[34] = str(uid)
    return row


class AllYangdoCalculatorPageTest(unittest.TestCase):
    def test_training_dataset_excludes_rows_without_numeric_price(self):
        header = [""] * 41
        rows = [
            _make_row(number=1, uid=10001, license_name="토목", license_year=2010, specialty=22, y23=4, y24=5, y25=6, price="2.1억"),
            _make_row(number=2, uid=10002, license_name="토목", license_year=2011, specialty=24, y23=5, y24=6, y25=7, price="협의"),
        ]
        records = allmod._build_estimate_records([header, *rows])
        train = allmod._build_yangdo_calculator_training_dataset(records)
        self.assertEqual(len(train), 1)
        self.assertEqual(train[0]["now_uid"], "10001")
        self.assertEqual(train[0]["seoul_no"], 1)
        self.assertGreater(train[0]["price_eok"], 0)

    def test_training_dataset_uses_seoul_number_link_and_claim_range(self):
        header = [""] * 41
        rows = [
            _make_row(
                number=7545,
                uid=11840,
                license_name="토목",
                license_year=2014,
                specialty=40,
                y23=1,
                y24=2,
                y25=3,
                price="2.6억",
                claim="2.1억~2.6억 / 2.6억",
            )
        ]
        records = allmod._build_estimate_records([header, *rows])
        train = allmod._build_yangdo_calculator_training_dataset(records)
        self.assertEqual(len(train), 1)
        row = train[0]
        self.assertTrue(str(row.get("url", "")).endswith("/mna/7545"))
        self.assertAlmostEqual(float(row.get("display_low_eok") or 0), 2.1, places=3)
        self.assertAlmostEqual(float(row.get("display_high_eok") or 0), 2.6, places=3)

    def test_calculator_page_html_contains_core_blocks(self):
        header = [""] * 41
        rows = [
            _make_row(number=11, uid=20001, license_name="건축", license_year=2015, specialty=30, y23=11, y24=12, y25=13, price="2.8억"),
            _make_row(number=12, uid=20002, license_name="건축", license_year=2016, specialty=32, y23=12, y24=13, y25=14, price="3.0억"),
        ]
        records = allmod._build_estimate_records([header, *rows])
        train = allmod._build_yangdo_calculator_training_dataset(records)
        meta = allmod._build_yangdo_calculator_meta(records, train)
        html_customer = allmod._build_yangdo_calculator_page_html(train, meta, view_mode="customer")
        html_owner = allmod._build_yangdo_calculator_page_html(train, meta, view_mode="owner")

        self.assertIn('id="btn-estimate"', html_customer)
        self.assertNotIn("atob('", html_customer)
        self.assertNotIn("[smna-calc] script decode failed", html_customer)
        self.assertIn("AI 양도가 산정 계산기", html_customer)
        self.assertNotIn("입금가", html_customer)
        self.assertNotIn("중앙 양도가(억)", html_customer)
        self.assertIn("중앙 기준가(억)", html_customer)
        self.assertIn("AI 양도가 산정 계산기 (내부 검수)", html_owner)
        self.assertIn('id="btn-email-result"', html_customer)
        expect_consult_widget = bool(getattr(allmod, "YANGDO_ENABLE_CONSULT_WIDGET", False))
        self.assertEqual('id="btn-mail-consult"' in html_customer, expect_consult_widget)
        self.assertEqual('id="btn-submit-consult"' in html_customer, expect_consult_widget)
        self.assertEqual('id="consult-summary"' in html_customer, expect_consult_widget)
        self.assertIn('id="out-yoy-compare"', html_customer)
        self.assertIn('id="in-scale-search-mode"', html_customer)
        self.assertIn('id="smart-profile-card"', html_customer)
        self.assertIn('id="license-quick-chips"', html_customer)
        self.assertIn("yangdo-input-wizard", html_customer)
        self.assertIn("yangdoWizardRail", html_customer)
        self.assertIn("yangdoWizardProgress", html_customer)
        self.assertIn("yangdoWizardProgressLabel", html_customer)
        self.assertIn("yangdoWizardProgressFill", html_customer)
        self.assertIn("yangdoWizardMobileSticky", html_customer)
        self.assertIn("yangdoWizardMobileStickyAction", html_customer)
        self.assertIn("yangdoWizardMobileStickyCompact", html_customer)
        self.assertIn("yangdoWizardMobileStickyReason", html_customer)
        self.assertIn("yangdoWizardActionReason", html_customer)
        self.assertIn("data-yangdo-action-reason", html_customer)
        self.assertIn("yangdoWizardNextAction", html_customer)
        self.assertIn("yangdoWizardNextActionText", html_customer)
        self.assertIn("data-yangdo-next-action", html_customer)
        self.assertIn("guided-focus-target", html_customer)
        self.assertIn("yangdoWizardSummary", html_customer)
        self.assertIn("yangdoWizardBlocker", html_customer)
        self.assertIn("yangdoWizardStep1", html_customer)
        self.assertIn("yangdoWizardStep5", html_customer)
        self.assertIn("applyYangdoWizardLayout", html_customer)
        self.assertIn("setYangdoWizardStep", html_customer)
        self.assertIn("findYangdoWizardResumeStep", html_customer)
        self.assertIn("syncYangdoWizardProgress", html_customer)
        self.assertIn("getYangdoWizardActionReasonCopy", html_customer)
        self.assertIn("getYangdoWizardNextActionCopy", html_customer)
        self.assertIn("getYangdoGuidedFocusCopy", html_customer)
        self.assertIn("data-guided-focus-copy", html_customer)
        self.assertIn("data-guided-focus-level", html_customer)
        self.assertIn("wizard-progress-support[data-actionable=\"1\"]", html_customer)
        self.assertIn("showYangdoGuidedFocus", html_customer)
        self.assertIn("syncYangdoWizardSummary", html_customer)
        self.assertIn("syncYangdoWizardBlocker", html_customer)
        self.assertIn("getYangdoOptionalGuide", html_customer)
        self.assertIn("syncYangdoOptionalHints", html_customer)
        self.assertIn(".wizard-step-chip.is-alert", html_customer)
        self.assertIn(".wizard-step-card.is-alert", html_customer)
        self.assertIn('data-reorg-choice="포괄"', html_customer)
        self.assertIn('data-reorg-choice="분할/합병"', html_customer)
        self.assertIn('id="reorg-compare-grid"', html_customer)
        self.assertIn('id="reorg-compare-note"', html_customer)
        self.assertIn('data-reorg-compare="포괄"', html_customer)
        self.assertIn('data-reorg-compare="분할/합병"', html_customer)
        self.assertIn("syncReorgCompareGuide", html_customer)
        self.assertIn("yangdoCriticalHint", html_customer)
        self.assertIn("yangdoStructureHint", html_customer)
        self.assertIn("yangdoCompanyHint", html_customer)
        self.assertIn("재무·회사 선택 정보", html_customer)
        self.assertIn("마지막 단계는 <strong>선택</strong> 정보로 분리했습니다.", html_customer)
        self.assertIn('id="advanced-inputs"', html_customer)
        self.assertIn('id="result-share-wrap"', html_customer)
        self.assertIn('id="result-share-actions"', html_customer)
        self.assertIn('id="result-brief"', html_customer)
        self.assertIn('id="btn-copy-brief"', html_customer)
        self.assertIn('id="in-reorg-mode"', html_customer)
        self.assertIn('id="reorg-mode-note"', html_customer)
        self.assertIn('id="in-sales-input-mode"', html_customer)
        self.assertIn('id="in-sales3-total"', html_customer)
        self.assertIn('id="in-sales5-total"', html_customer)
        self.assertIn('id="draft-restore-note"', html_customer)
        self.assertIn('id="draft-restore-note-text"', html_customer)
        self.assertIn('id="draft-restore-estimate-action"', html_customer)
        self.assertIn('id="draft-restore-action"', html_customer)
        self.assertIn('id="estimate-result-panel"', html_customer)
        self.assertIn("시평으로 찾기", html_customer)
        self.assertIn("실적으로 찾기", html_customer)
        self.assertIn('option value="분할/합병"', html_customer)
        self.assertNotIn('option value="분할포괄"', html_customer)
        self.assertIn("가격 확인 매물", html_customer)
        self.assertIn("사례 근거 수준", html_customer)
        self.assertIn("추천 매물", html_customer)
        self.assertIn('id="recommended-listings"', html_customer)
        self.assertIn('id="recommend-panel-guide"', html_customer)
        self.assertIn('id="recommend-panel"', html_customer)
        self.assertIn('id="result-action-steps"', html_customer)
        self.assertIn('id="neighbor-panel"', html_customer)
        self.assertIn('id="neighbor-panel-summary"', html_customer)
        self.assertIn("전기/정보통신/소방에서 <strong>분할/합병</strong>을 선택하면", html_customer)
        self.assertIn("전기/정보통신/소방이 포함된 경우 포괄 또는 분할/합병을 먼저 선택해 주세요.", html_customer)
        self.assertIn("전체 매물 중 가격이 숫자로 확인된 매물만 계산 기준으로 사용합니다.", html_customer)
        self.assertIn("공제조합 잔액(억, 별도 참고)", html_customer)
        self.assertIn("별도 정산 · 가격 영향 0", html_customer)
        self.assertIn("별도 공제잔액 참고", html_customer)
        self.assertIn("별도 정산 참고값 · 가격 영향 0", html_customer)
        self.assertIn("참고용 입력(가격 영향 0)", html_customer)
        self.assertIn("전기·정보통신·소방의 분할/합병은 시평을 쓰지 않고 실적 기준으로 계산합니다.", html_customer)
        self.assertIn("전기·정보통신·소방의 분할/합병은 실적 검색으로 자동 전환됩니다.", html_customer)
        self.assertIn("전기/정보통신/소방의 분할/합병은 실적과 자본금 중심으로 계산합니다. 최근 3년·5년·연도별 중 한 방식만 입력하세요.", html_customer)
        self.assertIn("분할/합병은 최근 3년 실적 합계를 먼저 추천해 자동 선택했습니다. 한 칸만 입력하면 됩니다.", html_customer)
        self.assertIn("분할/합병은 최근 3년 실적 합계를 가장 빠른 기본값으로 권장합니다. 필요하면 연도별이나 5년 합계로 바꿀 수 있습니다.", html_customer)
        self.assertIn("이전 입력값을 불러왔습니다. ${resumeLabel}부터 이어서 계산할 수 있습니다. 필요하면 바로 새로 시작을 누르세요.", html_customer)
        self.assertIn("지금 상태로 바로 계산할 수 있고, 필요하면 ${resumeLabel}부터 계속 수정할 수 있습니다. 바로 계산하거나 새로 시작을 누르세요.", html_customer)
        self.assertIn("바로 계산", html_customer)
        self.assertIn("isYangdoEstimateReady", html_customer)
        self.assertIn("scrollResultPanelIntoView", html_customer)
        self.assertIn("flushPendingResultPanelScroll", html_customer)
        self.assertIn("appendKoreanParticle", html_customer)
        self.assertIn("시평·이익잉여금·외부신용·부채/유동비율은 가격에 넣지 않으니 비교용으로만 확인하세요.", html_customer)
        self.assertIn("아래 추천 매물에서 실적이 가까운 순서대로 검토 우선순위를 먼저 정리해 보세요.", html_customer)
        self.assertIn("전기·정보통신·소방은 공제조합 잔액이 양도가와 별도이며 가격 계산에는 반영하지 않습니다. 필요하면 참고용으로만 입력하세요.", html_customer)
        self.assertIn("비슷한 사례 수", html_customer)
        self.assertIn("비슷한 사례 표 자세히 보기", html_customer)
        self.assertIn("지금 하면 좋은 순서 3단계", html_customer)
        self.assertIn("범위 먼저 보기", html_customer)
        self.assertIn("먼저 확인 필요", html_customer)
        self.assertIn("사례 더 필요", html_customer)
        self.assertIn("기준가 바로 보기", html_customer)
        self.assertNotIn("근거 매물 수", html_customer)
        self.assertNotIn("근거 표 상세 비교", html_customer)
        self.assertNotIn("추천 액션 3단계", html_customer)
        self.assertNotIn("범위 우선 안내", html_customer)
        self.assertIn("비슷한 매물 ${neighborCount}건 기준입니다.", html_customer)
        self.assertIn("분할/합병은 실적과 자본금 중심으로 계산했습니다.", html_customer)
        self.assertIn("편차가 커 점추정 대신 범위만 공개합니다.", html_customer)
        self.assertIn("비슷한 매물이 아직 적습니다. 포괄인지 분할/합병인지와 최근 3년 실적을 알려주시면 더 정확해집니다.", html_customer)
        self.assertIn("비슷한 매물이 아직 적습니다. 최근 3년 실적과 공제잔액을 더 정확히 넣어주시면 더 정확해집니다.", html_customer)
        self.assertIn("reason-chips", html_customer)
        self.assertIn("reason-chip", html_customer)
        self.assertIn("reason-chip.primary", html_customer)
        self.assertIn("1순위 · 같은 업종", html_customer)
        self.assertIn("1순위 · 비슷한 실적", html_customer)
        self.assertIn("1순위 · 현재 조건 적합", html_customer)
        self.assertIn("buildRecommendationOrderNote", html_customer)
        self.assertIn("번호대보다 최근 실적이 더 비슷한 매물을 먼저 보여드립니다.", html_customer)
        self.assertIn("번호대보다 현재 입력 조건에 더 가까운 매물을 먼저 보여드립니다.", html_customer)
        self.assertIn("비슷한 후보끼리는 7천·6천·5천 번호대를 먼저 보여드립니다.", html_customer)
        self.assertIn("번호대보다 최근 3년 실적과 자본금을 먼저 반영했습니다.", html_customer)
        self.assertIn("번호대보다 업종과 최근 3년 실적을 먼저 반영했습니다.", html_customer)
        self.assertIn("번호대보다 최근 3년 실적·자본금과 현재 입력 조건을 먼저 반영했습니다.", html_customer)
        self.assertIn("현재 조건 적합도가 높습니다.", html_customer)
        self.assertIn("입력한 면허와 현재 조건이 가까운 매물입니다.", html_customer)
        self.assertIn("표본이 적을 때는 아래 비슷한 사례의 최근 3년 실적과 자본금부터 먼저 보세요.", html_customer)
        self.assertIn("범위가 넓을 때는 아래 추천 매물의 최근 3년 실적과 자본금 공통 조건부터 먼저 보세요.", html_customer)
        self.assertIn("1순위 · 3년 실적 기준", html_customer)
        self.assertIn("recommend-actions-title", html_customer)
        self.assertIn("추천 매물 1건이 먼저 보이도록 사례표는 접어두었습니다.", html_customer)
        self.assertIn("추천 매물이 아직 없어 사례표를 접어두었습니다. 입력을 조금 보강한 뒤 다시 계산해 보세요.", html_customer)
        self.assertIn("recommend-panel-followup", html_customer)
        self.assertIn("recommend-panel-followup-note", html_customer)
        self.assertIn("recommend-panel-followup-action", html_customer)
        self.assertIn("recommend-panel-followup-secondary-action", html_customer)
        self.assertIn("보강 버튼을 누른 뒤 값을 바꾸면 다시 계산이 자동으로 이어집니다.", html_customer)
        self.assertIn("recommendAutoLoopFieldId", html_customer)
        self.assertIn("scheduleRecommendAutoLoopEstimate", html_customer)
        self.assertIn("maybeRunRecommendAutoLoop", html_customer)
        self.assertIn("최근 3년 실적을 1~2건만 더 보강하면 현재 범위를 더 줄이는 데 도움이 됩니다.", html_customer)
        self.assertIn("아직 바로 비교할 추천 매물이 없습니다. 최근 3년 실적과 자본금을 더 보강하면 추천 후보를 다시 찾는 데 도움이 됩니다.", html_customer)
        self.assertIn("아직 바로 비교할 추천 매물이 없습니다. 공제조합 잔액을 더 정확히 넣으면 추천 후보를 다시 찾는 데 도움이 됩니다.", html_customer)
        self.assertIn("아직 바로 비교할 추천 매물이 없습니다. 시평을 더 정확히 넣으면 추천 후보를 다시 찾는 데 도움이 됩니다.", html_customer)
        self.assertIn("아직 바로 비교할 추천 매물이 없습니다. 자본금을 더 정확히 넣으면 추천 후보를 다시 찾는 데 도움이 됩니다.", html_customer)
        self.assertIn("공제조합 잔액을 더 정확히 넣으면 현재 범위를 더 빨리 좁힐 수 있습니다.", html_customer)
        self.assertIn("시평을 더 정확히 넣으면 현재 범위를 더 빨리 좁힐 수 있습니다.", html_customer)
        self.assertIn("자본금을 더 정확히 넣으면 현재 범위를 더 빨리 좁힐 수 있습니다.", html_customer)
        self.assertIn("1순위 · 최근 3년 실적 보강", html_customer)
        self.assertIn("1순위 · 공제조합 잔액 보강", html_customer)
        self.assertIn("1순위 · 시평 보강", html_customer)
        self.assertIn("1순위 · 자본금 보강", html_customer)
        self.assertIn("2순위 · 자본금 보강", html_customer)
        self.assertIn("2순위 · 공제조합 잔액 보강", html_customer)
        self.assertIn("2순위 · 최근 3년 실적 보강", html_customer)
        self.assertIn("1순위는 최근 3년 실적, 2순위는 자본금입니다.", html_customer)
        self.assertIn("1순위는 공제조합 잔액, 2순위는 자본금입니다.", html_customer)
        self.assertIn("1순위는 시평, 2순위는 공제조합 잔액입니다.", html_customer)
        self.assertIn("추천 후보가 아직 없어 최근 3년 실적과 자본금을 먼저 보강해 주세요.", html_customer)
        self.assertIn("추천 후보가 아직 없어 공제조합 잔액을 더 정확히 넣어 주세요.", html_customer)
        self.assertIn("추천 후보가 아직 없어 자본금을 더 정확히 넣어 주세요.", html_customer)
        self.assertIn("추천 후보가 아직 없어 시평을 더 구체적으로 넣어 주세요.", html_customer)
        self.assertIn("${emptyPrimaryLabel}부터 누르면 해당 입력칸으로 바로 이동합니다.", html_customer)
        self.assertIn("최근 3년 실적과 자본금을 보강한 뒤 다시 계산해 보세요.", html_customer)
        self.assertIn("공제조합 잔액을 보강한 뒤 다시 계산해 보세요.", html_customer)
        self.assertIn("자본금을 보강한 뒤 다시 계산해 보세요.", html_customer)
        self.assertIn("시평을 조금 더 구체적으로 넣고 다시 계산해 보세요.", html_customer)
        self.assertIn("비슷한 사례 찾기 2단계", html_customer)
        self.assertIn("${primaryFollowupAction.shortLabel}부터 눌러 추천 후보를 먼저 만들어 보세요.", html_customer)
        self.assertIn("${emptyPrimaryLabel}부터 누르면 해당 입력칸으로 바로 이동합니다.", html_customer)
        self.assertIn("추천 매물 1건의 최근 3년 실적과 자본금을 먼저 비교해 보세요.", html_customer)
        self.assertIn("추천 매물 1건의 업종과 핵심 조건을 먼저 비교해 보세요.", html_customer)
        self.assertIn("보강 버튼을 눌러 가장 영향이 큰 입력칸으로 바로 돌아가 보세요.", html_customer)
        self.assertIn("최근 3년 실적과 자본금을 보강한 뒤 다시 계산하면 추천 후보를 다시 찾는 데 도움이 됩니다.", html_customer)
        self.assertIn("${scaleModeLabelText} 값과 공제조합 잔액을 더 정확히 넣어 추천 후보를 먼저 만들어 보세요.", html_customer)
        self.assertIn("${scaleModeLabelText} 값과 자본금을 더 정확히 넣어 추천 후보를 먼저 만들어 보세요.", html_customer)
        self.assertIn("다시 계산하면 범위를 더 빨리 좁힐 수 있습니다.", html_customer)
        self.assertIn("1순위 · 비슷한 3년 실적", html_customer)
        self.assertIn("표본이 적을 때는 아래 비슷한 사례 2~3건의 핵심 조건부터 먼저 보세요.", html_customer)
        self.assertIn("범위가 넓을 때는 아래 추천 매물의 공통 조건을 먼저 보세요.", html_customer)
        self.assertIn("renderRecommendPanelGuide", html_customer)
        self.assertIn("renderRecommendPanelFollowup", html_customer)
        self.assertIn("focusRecommendSales3Refinement", html_customer)
        self.assertIn("focusRecommendSpecialtyRefinement", html_customer)
        self.assertIn("focusRecommendBalanceRefinement", html_customer)
        self.assertIn("focusRecommendCapitalRefinement", html_customer)
        self.assertIn("focusRecommendInputField", html_customer)
        self.assertIn("flashRecommendFocusTarget", html_customer)
        self.assertIn("recommend-focus-target", html_customer)
        self.assertIn("__yangdoQaHooks", html_customer)
        self.assertNotIn('<div class="price">', html_customer)
        self.assertNotIn("추천 매물 1건의 업종과 가격대를 먼저 비교해 보세요.", html_customer)
        self.assertNotIn("희망 가격대를 먼저 정리해 보세요.", html_customer)
        self.assertNotIn("시평을 먼저 맞춘 뒤 자본금으로 가격대를 더 조여 보세요.", html_customer)
        self.assertIn("humanizeRecommendationBadge", html_customer)
        self.assertIn("먼저 볼 후보", html_customer)
        self.assertIn("같이 볼 후보", html_customer)
        self.assertIn("참고 후보", html_customer)
        self.assertIn("syncResultPriorityLayout", html_customer)
        self.assertIn("@media (max-width: 640px)", html_customer)
        self.assertIn("syncNeighborPanelDisclosure", html_customer)
        self.assertIn("updateNeighborPanelSummary", html_customer)
        self.assertIn("업종이 같습니다.", html_customer)
        self.assertIn("실적 규모가 비슷합니다.", html_customer)
        self.assertIn("동일 조건 전년 대비 비교는 계산 후 표시됩니다.", html_customer)
        self.assertIn("입력한 업종·선택한 검색축·규모에 가까운 매물을 먼저 골랐습니다.", html_customer)
        self.assertIn("면허/업종, 검색 기준(시평 또는 실적), 자본금, 필수 기준 충족 여부를 먼저 확인해 주세요.", html_customer)
        self.assertIn("양도 구조를 가장 먼저 정하고, 그 다음 공제조합 정산 방식과 면허년도를 확인하면 전달용 정산 가정이 빠르게 정리됩니다.", html_customer)
        self.assertIn("재무 상태와 회사 리스크는 마지막 미세 보정용입니다. 필요한 항목만 선택해도 됩니다.", html_customer)
        self.assertIn("구조·정산 정보(필수)", html_customer)
        self.assertIn("양도 구조 먼저 선택", html_customer)
        self.assertIn("syncReorgQuickChoices", html_customer)
        self.assertIn("renderYoyCompare", html_customer)
        self.assertIn("service_track: YANGDO_SERVICE_TRACK", html_customer)
        self.assertIn("양도양수 양도가 산정(인허가 신규등록 사전검토와 별도 운영)", html_customer)
        self.assertIn("사례 근거", html_customer)
        self.assertNotIn("고객용 화면은 내부 UID를 숨기고", html_customer)

    def test_compact_yangdo_training_dataset_applies_limit(self):
        train = []
        for i in range(1, 11):
            train.append(
                {
                    "seoul_no": 1000 + i,
                    "now_uid": str(2000 + i),
                    "tokens": ["토목"] if i % 2 else ["건축"],
                    "price_eok": float(i),
                }
            )
        compact = allmod._compact_yangdo_training_dataset(train, max_rows=4)
        self.assertEqual(len(compact), 4)
        self.assertEqual(len({row["seoul_no"] for row in compact}), 4)
        same = allmod._compact_yangdo_training_dataset(train, max_rows=0)
        self.assertEqual(len(same), len(train))


if __name__ == "__main__":
    unittest.main()
