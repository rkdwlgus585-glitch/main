import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_permit_service_copy_packet import build_permit_service_copy_packet


class GeneratePermitServiceCopyPacketTests(unittest.TestCase):
    def test_build_packet_returns_ready_service_copy(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia_path = base / "ia.json"
            ux_path = base / "ux.json"
            rental_path = base / "rental.json"

            ia_path.write_text(
                json.dumps(
                    {
                        "topology": {"platform_host": "seoulmna.kr"},
                        "pages": [
                            {"page_id": "permit", "slug": "/permit", "primary_cta": '[seoulmna_calc_gate type="permit"]'},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            ux_path.write_text(
                json.dumps({"summary": {"ux_ok": True, "service_pages_ok": True, "market_bridge_ok": True}}, ensure_ascii=False),
                encoding="utf-8",
            )
            rental_path.write_text(
                json.dumps({"summary": {"permit_selector_entry_total": 51, "permit_platform_industry_total": 51}}, ensure_ascii=False),
                encoding="utf-8",
            )

            payload = build_permit_service_copy_packet(ia_path=ia_path, ux_path=ux_path, rental_path=rental_path)

            summary = payload.get("summary") or {}
            self.assertTrue(summary.get("packet_ready"))
            self.assertEqual(summary.get("service_slug"), "/permit")
            self.assertTrue(summary.get("checklist_story_ready"))
            self.assertTrue(summary.get("manual_review_story_ready"))
            self.assertTrue(summary.get("document_story_ready"))

            hero = payload.get("hero") or {}
            self.assertIn("등록기준", hero.get("title", ""))
            self.assertIn('[seoulmna_calc_gate type="permit"]', hero.get("gate_shortcode", ""))

            ctas = payload.get("cta_ladder") or {}
            self.assertEqual((ctas.get("secondary_consult") or {}).get("target"), "/consult?intent=permit")
            self.assertEqual((ctas.get("supporting_knowledge") or {}).get("target"), "/knowledge")


if __name__ == "__main__":
    unittest.main()
