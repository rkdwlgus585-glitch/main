import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "generate_gas_masterpiece_bundle.py"


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location("generate_gas_masterpiece_bundle", str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


class GasMasterpieceBundleExtractTest(unittest.TestCase):
    def test_extract_dataset_meta_from_plain_assignment(self):
        mod = _load_module(SCRIPT_PATH)
        html = """
        <script>
          const dataset = [{"now_uid":"1","seoul_no":100,"price_eok":1.2}];
          const meta = {"train_count": 1, "generated_at": "2026-03-02 01:49:00"};
        </script>
        """
        dataset = mod._extract_dataset_from_html(html)
        meta = mod._extract_meta_from_html(html)
        self.assertEqual(len(dataset), 1)
        self.assertEqual(dataset[0]["now_uid"], "1")
        self.assertEqual(meta.get("train_count"), 1)

    def test_extract_dataset_meta_from_eval_escaped_assignment(self):
        mod = _load_module(SCRIPT_PATH)
        html = (
            '<script>(function(){var code="'
            '(function(){'
            'const dataset = [{\\\\\\"now_uid\\\\\\":\\\\\\"2\\\\\\",\\\\\\"seoul_no\\\\\\":200,\\\\\\"price_eok\\\\\\":2.4}];'
            'const meta = {\\\\\\"train_count\\\\\\":2,\\\\\\"generated_at\\\\\\":\\\\\\"2026-03-02 01:50:00\\\\\\"};'
            '})();'
            '";code=code.replace(/\\\\u0026/g,String.fromCharCode(38));(0,eval)(code);}());</script>'
        )
        dataset = mod._extract_dataset_from_html(html)
        meta = mod._extract_meta_from_html(html)
        self.assertEqual(len(dataset), 1)
        self.assertEqual(dataset[0]["now_uid"], "2")
        self.assertEqual(dataset[0]["seoul_no"], 200)
        self.assertEqual(meta.get("train_count"), 2)


if __name__ == "__main__":
    unittest.main()
