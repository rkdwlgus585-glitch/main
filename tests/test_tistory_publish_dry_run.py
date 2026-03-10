import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class TistoryPublishDryRunTest(unittest.TestCase):
    def test_publish_listing_dry_run_from_json(self):
        sample = {
            "등록번호": "7540",
            "양도가": "0.5억",
            "업종정보": [{"업종": "소방", "면허년도": "0", "시공능력": "10", "매출": {"2022": "1.3"}}],
            "비고": ["전문소방", "현금+자체결산"],
        }
        with tempfile.TemporaryDirectory() as td:
            td_path = pathlib.Path(td)
            src_path = td_path / "sample.json"
            out_html = td_path / "preview.html"
            src_path.write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT.parent / "ALL" / "tistory_ops" / "publish_listing.py"),
                    "--json-input",
                    str(src_path),
                    "--dry-run",
                    "--out-html",
                    str(out_html),
                    "--print-payload",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue(out_html.exists())
            body = out_html.read_text(encoding="utf-8")
            self.assertIn("회사개요", body)
            self.assertIn("7540", body)


if __name__ == "__main__":
    unittest.main()
