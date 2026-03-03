import importlib
import unittest


allmod = importlib.import_module("all")


class AllAdminMemoFormatTest(unittest.TestCase):
    def test_build_mna_admin_memo_keeps_gap_notation(self):
        item = {
            "uid": "11840",
            "license": "civil",
            "sheet_claim_price": "11840 civil\n2.1억~2.6억 / 2.6억",
            "source_url": "http://www.nowmna.com/yangdo_view1.php?uid=11840&page_no=1",
        }
        memo = allmod._build_mna_admin_memo(item)
        self.assertEqual(
            memo,
            "11840 civil<br>2.1억~2.6억 / 2.6억<br><br>http://www.nowmna.com/yangdo_view1.php?uid=11840&page_no=1",
        )

    def test_build_mna_admin_memo_preserves_section_breaks(self):
        item = {
            "uid": "11835",
            "license": "civil",
            "sheet_claim_price": "11835 civil\n1.9억~2.3억\n\n11835 civil(nego)\n1.8억~2.2억",
            "source_url": "http://www.nowmna.com/yangdo_view1.php?uid=11835&page_no=1",
        }
        memo = allmod._build_mna_admin_memo(item)
        self.assertEqual(
            memo,
            "11835 civil<br>1.9억~2.3억<br><br>11835 civil(nego)<br>1.8억~2.2억<br><br>http://www.nowmna.com/yangdo_view1.php?uid=11835&page_no=1",
        )

    def test_extract_uid_from_admin_memo_supports_numeric_header(self):
        memo = "11840 civil<br>2.1억~2.6억 / 2.6억<br><br>http://www.nowmna.com/yangdo_view1.php?uid=11840&page_no=1"
        self.assertEqual(allmod._extract_uid_from_admin_memo(memo), "11840")

    def test_validate_admin_memo_format(self):
        memo = "11840 civil<br>2.1억~2.6억 / 2.6억<br><br>http://www.nowmna.com/yangdo_view1.php?uid=11840&page_no=1"
        ok, diag = allmod._validate_admin_memo_format(memo, require_br=True)
        self.assertTrue(ok)
        self.assertEqual(diag.get("uid"), "11840")
        self.assertEqual(diag.get("errors"), [])


if __name__ == "__main__":
    unittest.main()

