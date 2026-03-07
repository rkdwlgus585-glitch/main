import importlib
import unittest


allmod = importlib.import_module("all")


class AllListingValidationTest(unittest.TestCase):
    def test_validate_item_for_sheet_detects_blank_claim_price(self) -> None:
        ok, issues = allmod._validate_item_for_sheet(
            {"uid": "7760", "license": "civil", "claim_price": "", "price": "consult"}
        )

        self.assertFalse(ok)
        self.assertIn("claim_price_missing", issues)

    def test_validate_item_for_sheet_allows_existing_claim_price_on_update(self) -> None:
        ok, issues = allmod._validate_item_for_sheet(
            {"uid": "7760", "license": "", "claim_price": "", "price": "consult"},
            existing_claim_price="2.1-2.4",
        )

        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_derive_sheet_status_marks_invalid_item_complete(self) -> None:
        status = allmod._derive_sheet_status_for_new_item(
            {"uid": "7752", "claim_price": "", "price": "consult"},
            ["claim_price_missing"],
        )

        self.assertEqual(status, "완료")

    def test_skip_site_publish_for_invalid_item(self) -> None:
        should_skip = allmod._should_skip_site_publish_for_item(
            {"uid": "7752"},
            "완료",
            ["claim_price_missing"],
        )

        self.assertTrue(should_skip)

    def test_resolve_sheet_row_no_prefers_site_wr_id(self) -> None:
        resolved = allmod._resolve_sheet_row_no(
            old_no="7752",
            row_no_override="7753",
            fallback_no=7754,
            allocate_if_missing=False,
        )

        self.assertEqual(resolved, 7753)

    def test_resolve_sheet_row_no_keeps_existing_number_for_complete_row(self) -> None:
        resolved = allmod._resolve_sheet_row_no(
            old_no="7752",
            row_no_override="",
            fallback_no=7753,
            allocate_if_missing=False,
        )

        self.assertEqual(resolved, 7752)

    def test_resolve_sheet_row_no_does_not_allocate_for_blank_override(self) -> None:
        resolved = allmod._resolve_sheet_row_no(
            old_no="",
            row_no_override="",
            fallback_no=7753,
            allocate_if_missing=False,
        )

        self.assertEqual(resolved, "")

    def test_resolve_sheet_row_no_clears_existing_number_when_requested(self) -> None:
        resolved = allmod._resolve_sheet_row_no(
            old_no="7752",
            row_no_override="__CLEAR__",
            fallback_no=7753,
            allocate_if_missing=False,
        )

        self.assertEqual(resolved, "")

    def test_resolve_publish_listing_result_discovers_canonical_wr_id(self) -> None:
        class DummyPublisher:
            site_url = "https://seoulmna.co.kr"
            board_slug = "mna"

        original = allmod._discover_site_wr_map_from_board
        try:
            allmod._discover_site_wr_map_from_board = lambda publisher, target_uids, max_pages=0: (
                {"11862": 7752},
                {"scanned_pages": 2, "scanned_wr_ids": 15},
            )
            out = allmod._resolve_publish_listing_result(
                DummyPublisher(),
                {"uid": "11862"},
                {"url": "https://seoulmna.co.kr/bbs/write.php?bo_table=mna", "subject": "협의"},
                max_pages=10,
            )
        finally:
            allmod._discover_site_wr_map_from_board = original

        self.assertEqual(out.get("wr_id"), 7752)
        self.assertEqual(out.get("url"), "https://seoulmna.co.kr/mna/7752")

    def test_reconcile_sheet_sync_marks_row_number_only_alignment_change(self) -> None:
        runtime = {
            "uid_to_row": {"11862": 2},
            "all_values": [["번호", "상태"], ["7753", "가능"]],
            "last_row": 2,
            "last_no": 7753,
        }

        out = allmod._reconcile_sheet_sync(
            worksheet=None,
            runtime=runtime,
            uid="11862",
            status_label="가능",
            item=None,
            dry_run=True,
            row_no_override="7752",
        )

        self.assertEqual(out.get("action"), "status_only")
        self.assertEqual(out.get("alignment_change"), "row_no_only")
        self.assertTrue(out.get("row_no_changed"))
        self.assertFalse(out.get("status_changed"))

    def test_reconcile_sheet_sync_marks_row_number_and_status_alignment_change(self) -> None:
        runtime = {
            "uid_to_row": {"11862": 2},
            "all_values": [["번호", "상태"], ["7753", "가능"]],
            "last_row": 2,
            "last_no": 7753,
        }

        out = allmod._reconcile_sheet_sync(
            worksheet=None,
            runtime=runtime,
            uid="11862",
            status_label="완료",
            item=None,
            dry_run=True,
            row_no_override="7752",
        )

        self.assertEqual(out.get("action"), "status_only")
        self.assertEqual(out.get("alignment_change"), "row_no_and_status")
        self.assertTrue(out.get("row_no_changed"))
        self.assertTrue(out.get("status_changed"))

    def test_build_mna_subject_prefers_claim_price_over_consult_price(self) -> None:
        subject = allmod._build_mna_subject(
            {"price": "협의", "claim_price": "11866 소방\n0.2억~0.3억"}
        )

        self.assertEqual(subject, "0.2억~0.3억")

    def test_format_admin_price_repairs_broken_eok_marker(self) -> None:
        text = allmod._format_admin_price_for_memo("0.6?~0.7?")

        self.assertEqual(text, "0.6억~0.7억")

    def test_build_mna_subject_repairs_broken_eok_marker(self) -> None:
        subject = allmod._build_mna_subject(
            {"price": "협의", "claim_price": "11866 소방\n0.2?~0.3?"}
        )

        self.assertEqual(subject, "0.2억~0.3억")


if __name__ == "__main__":
    unittest.main()
