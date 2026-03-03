import importlib.util
import pathlib
import sys
import types
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "paid_ops" / "build_gabji_analysis_report.py"
SPEC = importlib.util.spec_from_file_location("build_gabji_analysis_report", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class BuildGabjiBackendAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp_modules = []

    def tearDown(self):
        for name in self.temp_modules:
            sys.modules.pop(name, None)

    def _register_module(self, name, module):
        sys.modules[name] = module
        self.temp_modules.append(name)

    def test_resolve_backend_module_ready(self):
        mod = types.ModuleType("tmp_build_backend_ready")

        class ListingSheetLookup:
            def load_listing(self, registration_no):
                return {"registration_no": registration_no}

        class GabjiGenerator:
            def analyze_image(self, image_path):
                return {"image": image_path}

        mod.ListingSheetLookup = ListingSheetLookup
        mod.GabjiGenerator = GabjiGenerator
        self._register_module("tmp_build_backend_ready", mod)

        backend, name, missing = MOD._resolve_backend_module("tmp_build_backend_ready")
        self.assertEqual(name, "tmp_build_backend_ready")
        self.assertEqual(missing, [])
        self.assertIs(backend, mod)

    def test_resolve_backend_module_missing_symbol(self):
        mod = types.ModuleType("tmp_build_backend_missing")
        mod.ListingSheetLookup = type("ListingSheetLookup", (), {})
        self._register_module("tmp_build_backend_missing", mod)

        _, _, missing = MOD._resolve_backend_module("tmp_build_backend_missing")
        self.assertIn("GabjiGenerator", missing)


if __name__ == "__main__":
    unittest.main()
