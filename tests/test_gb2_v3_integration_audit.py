import importlib.util
import pathlib
import sys
import types
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "paid_ops" / "audit_gb2_v3_integration.py"
SPEC = importlib.util.spec_from_file_location("audit_gb2_v3_integration", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class Gb2V3IntegrationAuditTest(unittest.TestCase):
    def setUp(self):
        self.temp_modules = []

    def tearDown(self):
        for name in self.temp_modules:
            sys.modules.pop(name, None)

    def _register_module(self, name, module):
        sys.modules[name] = module
        self.temp_modules.append(name)

    def test_inspect_backend_ready(self):
        mod = types.ModuleType("tmp_backend_ready")

        class ListingSheetLookup:
            def load_listing(self, registration_no):
                return {"registration_no": registration_no}

        class GabjiGenerator:
            def analyze_image(self, image_path):
                return {"image": image_path}

        mod.ListingSheetLookup = ListingSheetLookup
        mod.GabjiGenerator = GabjiGenerator
        mod.extract_final_yangdo_price = lambda raw: raw
        self._register_module("tmp_backend_ready", mod)

        row = MOD.inspect_backend("tmp_backend_ready")
        self.assertTrue(row["import_ok"])
        self.assertTrue(row["ready_for_registration"])
        self.assertTrue(row["ready_for_image"])
        self.assertTrue(row["ready_for_report_pipeline"])

    def test_inspect_backend_missing_symbols(self):
        mod = types.ModuleType("tmp_backend_missing")

        class ListingSheetLookup:
            pass

        mod.ListingSheetLookup = ListingSheetLookup
        self._register_module("tmp_backend_missing", mod)

        row = MOD.inspect_backend("tmp_backend_missing")
        self.assertTrue(row["import_ok"])
        self.assertFalse(row["ready_for_report_pipeline"])
        self.assertFalse(row["symbols"]["ListingSheetLookup.load_listing"])
        self.assertFalse(row["symbols"]["GabjiGenerator"])

    def test_choose_recommended_backend_prefers_gb2_v3(self):
        rows = [
            {"module": "gabji", "ready_for_report_pipeline": True},
            {"module": "gb2_v3", "ready_for_report_pipeline": True},
        ]
        pick = MOD.choose_recommended_backend(rows)
        self.assertEqual(pick, "gb2_v3")


if __name__ == "__main__":
    unittest.main()
