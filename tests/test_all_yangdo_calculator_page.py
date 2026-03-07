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
        self.assertIn("yangdoWizardSummary", html_customer)
        self.assertIn("yangdoWizardBlocker", html_customer)
        self.assertIn("yangdoWizardStep1", html_customer)
        self.assertIn("yangdoWizardStep5", html_customer)
        self.assertIn("applyYangdoWizardLayout", html_customer)
        self.assertIn("setYangdoWizardStep", html_customer)
        self.assertIn("findYangdoWizardResumeStep", html_customer)
        self.assertIn("syncYangdoWizardSummary", html_customer)
        self.assertIn("syncYangdoWizardBlocker", html_customer)
        self.assertIn("yangdoCriticalHint", html_customer)
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
        self.assertIn("비교 자료 수준", html_customer)
        self.assertIn("추천 매물", html_customer)
        self.assertIn('id="recommended-listings"', html_customer)
        self.assertIn('id="recommend-panel-guide"', html_customer)
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
        self.assertIn("아래 추천 매물에서 실적이 가까운 순서대로 희망 가격대를 먼저 정리해 보세요.", html_customer)
        self.assertIn("전기·정보통신·소방은 공제조합 잔액이 양도가와 별도이며 가격 계산에는 반영하지 않습니다. 필요하면 참고용으로만 입력하세요.", html_customer)
        self.assertIn("범위 우선 안내", html_customer)
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
        self.assertIn("1순위 · 가까운 가격대", html_customer)
        self.assertIn("표본이 적을 때는 아래 비슷한 사례 2~3건의 가격대부터 먼저 보세요.", html_customer)
        self.assertIn("범위가 넓을 때는 아래 추천 매물의 공통 가격대를 먼저 보세요.", html_customer)
        self.assertIn("renderRecommendPanelGuide", html_customer)
        self.assertIn("@media (max-width: 640px)", html_customer)
        self.assertIn("syncNeighborPanelDisclosure", html_customer)
        self.assertIn("updateNeighborPanelSummary", html_customer)
        self.assertIn("업종이 같습니다.", html_customer)
        self.assertIn("실적 규모가 비슷합니다.", html_customer)
        self.assertIn("동일 조건 전년 대비 비교는 계산 후 표시됩니다.", html_customer)
        self.assertIn("입력한 업종·선택한 검색축·규모에 가까운 매물을 먼저 골랐습니다.", html_customer)
        self.assertIn("면허/업종, 검색 기준(시평 또는 실적), 자본금, 필수 기준 충족 여부를 먼저 확인해 주세요.", html_customer)
        self.assertIn("renderYoyCompare", html_customer)
        self.assertIn("service_track: YANGDO_SERVICE_TRACK", html_customer)
        self.assertIn("양도양수 양도가 산정(인허가 신규등록 사전검토와 별도 운영)", html_customer)
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
