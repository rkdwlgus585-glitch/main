import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_attorney_handoff import build_attorney_handoff, main


class GenerateAttorneyHandoffTests(unittest.TestCase):
    def test_build_handoff_has_single_packet_and_three_tracks(self):
        data = build_attorney_handoff()
        self.assertEqual(data["packet_id"], "attorney_handoff_latest")
        self.assertEqual(len(data["tracks"]), 3)
        self.assertIn("변리사 전달 관련 내용은 이 attorney_handoff_latest만 기준으로 갱신", data["executive_summary"]["update_rule"])

    def test_track_a_contains_claim_outline_and_evidence(self):
        data = build_attorney_handoff()
        track_a = next(track for track in data["tracks"] if track["track_id"] == "A")
        self.assertIn("양도가 산정 방법", track_a["claim_draft_outline"]["independent"])
        self.assertIn("양도가 산정 방법", track_a["claim_sentence_draft"]["independent"])
        self.assertGreaterEqual(len(track_a["claim_sentence_draft"]["dependents"]), 3)
        self.assertTrue(any("요약 추천 필드" in item or "추천 요약 필드" in item for item in track_a["claim_sentence_draft"]["dependents"]))
        self.assertTrue(any("추천 정밀도 QA 매트릭스" == ev.get("label") for ev in track_a["evidence"]))
        self.assertTrue(len(track_a["evidence"]) > 0)

    def test_cli_writes_files(self):
        with tempfile.TemporaryDirectory() as td:
            json_path = Path(td) / "attorney.json"
            md_path = Path(td) / "attorney.md"
            from unittest.mock import patch
            import io
            stdout = io.StringIO()
            argv = [
                "generate_attorney_handoff.py",
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
            self.assertEqual(payload["packet_id"], "attorney_handoff_latest")
            self.assertIn("Attorney Handoff", md_path.read_text(encoding="utf-8"))
            self.assertIn("Claim sentence draft", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
