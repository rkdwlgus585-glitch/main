import tempfile
import unittest
from pathlib import Path

from scripts.generate_external_masterplan_alignment import build_alignment


class GenerateExternalMasterplanAlignmentTests(unittest.TestCase):
    def test_build_alignment_detects_missing_directives(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            source = base / "external.txt"
            masterplan = base / "MASTERPLAN.md"
            source.write_text(
                "\n".join(
                    [
                        "AI 양도가 산정 시스템",
                        "AI 인허가 사전검토 시스템",
                        "seoulmna.kr 플랫폼 형식으로 전면 개편",
                        "특허를 위한 고도화, 정교화",
                        "관계 법령 등(특례 등), 등록기준, 사례 등 데이터 수집",
                    ]
                ),
                encoding="utf-8",
            )
            masterplan.write_text(
                "\n".join(
                    [
                        "AI 양도가 산정",
                        "permit",
                        "seoulmna.kr 플랫폼 전면 개편",
                        "특허",
                    ]
                ),
                encoding="utf-8",
            )

            payload = build_alignment(source, masterplan)

            self.assertTrue(payload["summary"]["packet_ready"])
            self.assertFalse(payload["summary"]["alignment_ok"])
            self.assertIn("permit_law_exception_case_collection", payload["summary"]["missing_keys"])


if __name__ == "__main__":
    unittest.main()
