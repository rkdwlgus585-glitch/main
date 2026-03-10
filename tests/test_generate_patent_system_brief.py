import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_patent_system_brief import build_brief, main


class GeneratePatentSystemBriefTests(unittest.TestCase):
    def test_build_brief_has_three_tracks(self):
        data = build_brief()
        self.assertEqual(len(data["tracks"]), 3)
        ids = [track["track_id"] for track in data["tracks"]]
        self.assertEqual(ids, ["A", "B", "P"])

    def test_build_brief_contains_system_split_summary(self):
        data = build_brief()
        self.assertIn("yangdo", data["summary"]["independent_systems"])
        self.assertIn("permit", data["summary"]["independent_systems"])
        self.assertIn("activation_gate", data["summary"]["shared_platform"])
        track_a = next(track for track in data["tracks"] if track["track_id"] == "A")
        self.assertIn("yangdo API", track_a["system_boundary"]["in_scope"])
        self.assertIn("특정 사이트명/크롤링 방식", track_a["avoid_in_claims"])
        self.assertIn("independent", track_a["claim_draft_outline"])
        self.assertIn("attorney_handoff", data["summary"])

    def test_cli_outputs_files(self):
        with tempfile.TemporaryDirectory() as td:
            json_path = Path(td) / "brief.json"
            md_path = Path(td) / "brief.md"
            from unittest.mock import patch
            import io
            stdout = io.StringIO()
            argv = [
                "generate_patent_system_brief.py",
                "--json",
                str(json_path),
                "--md",
                str(md_path),
            ]
            with patch("sys.argv", argv):
                with patch("sys.stdout", stdout):
                    code = main()
            self.assertEqual(code, 0)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["tracks"]), 3)
            self.assertIn("Track A", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
