import unittest

from scripts import build_monthly_notice_from_maemul as notice_build


class BuildMonthlyNoticeFromMaemulTest(unittest.TestCase):
    def _row(self, uid: int, businesses: list[str] | None = None) -> notice_build.ListingRow:
        return notice_build.ListingRow(
            uid=uid,
            status="가능",
            businesses=list(businesses or []),
            three_year="",
            five_year="",
            license_year="2023",
            capital_or_shares="",
            corp_and_transfer="협의",
            region="지방",
        )

    def test_resolve_transfer_display_marks_sheet_numeric_price_as_disclosed(self) -> None:
        item = self._row(1, ["토공"])

        resolved, disclosed = notice_build._resolve_transfer_display(
            item,
            {"sheet_price": "1.2억", "sheet_claim": "", "now_uid": ""},
            {},
        )

        self.assertEqual(resolved, "1.2억")
        self.assertTrue(disclosed)

    def test_resolve_transfer_display_marks_consult_only_as_not_disclosed(self) -> None:
        item = self._row(2, ["토공"])

        resolved, disclosed = notice_build._resolve_transfer_display(
            item,
            {"sheet_price": "협의", "sheet_claim": "", "now_uid": ""},
            {},
        )

        self.assertEqual(resolved, "")
        self.assertFalse(disclosed)

    def test_filter_notice_eligible_listings_requires_business_and_disclosed_price(self) -> None:
        good = self._row(1, ["토공"])
        good.transfer_display = "1.2억"
        good.transfer_disclosed = True

        no_business = self._row(2, [])
        no_business.transfer_display = "1.1억"
        no_business.transfer_disclosed = True

        no_price = self._row(3, ["전기"])
        no_price.transfer_display = "협의"
        no_price.transfer_disclosed = False

        kept, skipped = notice_build._filter_notice_eligible_listings([good, no_business, no_price])

        self.assertEqual([row.uid for row in kept], [1])
        self.assertEqual(skipped, 2)


if __name__ == "__main__":
    unittest.main()
