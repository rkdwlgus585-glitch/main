import importlib
import unittest


allmod = importlib.import_module("all")


def _make_row(
    number="",
    uid="",
    license_name="",
    license_year="",
    specialty="",
    y20="",
    y21="",
    y22="",
    y23="",
    y24="",
    y25="",
    location="",
    association="",
    debt="",
    liq="",
    price="",
    claim="",
):
    row = [""] * 41
    row[0] = str(number)
    row[2] = str(license_name)
    row[3] = str(license_year)
    row[4] = str(specialty)
    row[5] = str(y20)
    row[6] = str(y21)
    row[7] = str(y22)
    row[8] = str(y23)
    row[9] = str(y24)
    row[12] = str(y25)
    row[16] = str(location)
    row[18] = str(price)
    row[20] = str(association)
    row[21] = str(debt)
    row[23] = str(liq)
    row[33] = str(claim)
    row[34] = str(uid)
    return row


class AllYangdoEstimatorTest(unittest.TestCase):
    def test_price_to_eok_float_parses_range_and_man(self):
        self.assertAlmostEqual(allmod._price_to_eok_float("1.9억~2.3억 / 2.3억"), 2.3, places=4)
        self.assertAlmostEqual(allmod._price_to_eok_float("6,500만원"), 0.65, places=4)
        self.assertIsNone(allmod._price_to_eok_float("협의"))

    def test_build_yangdo_estimate_rows_returns_estimate_for_missing_price(self):
        header = [""] * 41
        rows = [
            _make_row(number=1001, uid=9001, license_name="토목", license_year=2013, specialty=20, y23=6, y24=7, y25=8, location="지방", association="가입", debt=55, liq=220, price="1.9억"),
            _make_row(number=1002, uid=9002, license_name="토목", license_year=2014, specialty=22, y23=7, y24=8, y25=9, location="지방", association="가입", debt=60, liq=200, price="2.1억"),
            _make_row(number=1003, uid=9003, license_name="토목", license_year=2012, specialty=18, y23=5, y24=6, y25=7, location="지방", association="가입", debt=50, liq=240, price="1.8억"),
            _make_row(number=1004, uid=9004, license_name="토목", license_year=2013, specialty=21, y23=6.5, y24=7.5, y25=8.5, location="지방", association="가입", debt=58, liq=210, price="협의", claim="1.9억~2.2억"),
        ]

        estimates, meta = allmod._build_yangdo_estimate_rows(
            [header, *rows],
            uid_filter="9004",
            only_missing=True,
            top_k=5,
            min_score=15.0,
        )
        self.assertEqual(meta["train_count"], 3)
        self.assertEqual(len(estimates), 1)

        row = estimates[0]
        self.assertEqual(row["uid"], "9004")
        self.assertGreaterEqual(row["neighbor_count"], 2)
        self.assertGreater(row["estimate_center_eok"], 1.7)
        self.assertLess(row["estimate_center_eok"], 2.3)
        self.assertLessEqual(row["estimate_low_eok"], row["estimate_center_eok"])
        self.assertGreaterEqual(row["estimate_high_eok"], row["estimate_center_eok"])

    def test_estimate_only_missing_filter_excludes_numeric_price_rows(self):
        header = [""] * 41
        rows = [
            _make_row(number=2001, uid=9101, license_name="건축", specialty=30, y23=11, y24=13, y25=15, price="2.4억"),
            _make_row(number=2002, uid=9102, license_name="건축", specialty=32, y23=12, y24=14, y25=16, price="2.6억"),
            _make_row(number=2003, uid=9103, license_name="건축", specialty=31, y23=11.5, y24=13.5, y25=15.5, price="협의"),
        ]

        estimates_missing, _ = allmod._build_yangdo_estimate_rows(
            [header, *rows],
            only_missing=True,
            top_k=4,
            min_score=15.0,
        )
        self.assertEqual(len(estimates_missing), 1)
        self.assertEqual(estimates_missing[0]["uid"], "9103")

        estimates_all, _ = allmod._build_yangdo_estimate_rows(
            [header, *rows],
            only_missing=False,
            top_k=4,
            min_score=15.0,
        )
        self.assertGreaterEqual(len(estimates_all), 2)


if __name__ == "__main__":
    unittest.main()
