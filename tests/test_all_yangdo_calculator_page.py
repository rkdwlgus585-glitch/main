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
        self.assertIn('id="btn-mail-consult"', html_customer)
        self.assertIn('id="btn-submit-consult"', html_customer)
        self.assertIn('id="consult-summary"', html_customer)
        self.assertIn('id="out-yoy-compare"', html_customer)
        self.assertIn('id="in-sales-input-mode"', html_customer)
        self.assertIn('id="in-sales3-total"', html_customer)
        self.assertIn('id="in-sales5-total"', html_customer)
        self.assertIn("공제조합 잔액 단위가 의심되어 자동 보정 후 계산했습니다.", html_customer)
        self.assertIn("동일 조건 전년 대비 비교는 계산 후 표시됩니다.", html_customer)
        self.assertIn("renderYoyCompare", html_customer)
        self.assertIn("메일로 문의", html_customer)
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
