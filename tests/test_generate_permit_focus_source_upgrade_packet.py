import unittest

from scripts import generate_permit_focus_source_upgrade_packet


class GeneratePermitFocusSourceUpgradePacketTests(unittest.TestCase):
    def test_build_packet_targets_top_pending_family_and_materializes_registry_rows(self):
        focus_seed_catalog = {
            "industries": [
                {
                    "service_code": "FOCUS::construction-general-geonchuk",
                    "service_name": "건축공사업(종합)",
                    "major_code": "31",
                    "major_name": "건설",
                    "group_name": "건설업 등록기준",
                    "law_title": "건설산업기본법 시행령",
                    "legal_basis_title": "별표 2",
                    "seed_rule_service_code": "RULE::construction-general-geonchuk",
                    "seed_rule_id": "construction-general-geonchuk",
                },
                {
                    "service_code": "FOCUS::construction-general-tomok",
                    "service_name": "토목공사업(종합)",
                    "major_code": "31",
                    "major_name": "건설",
                    "group_name": "건설업 등록기준",
                    "law_title": "건설산업기본법 시행령",
                    "legal_basis_title": "별표 2",
                    "seed_rule_service_code": "RULE::construction-general-tomok",
                    "seed_rule_id": "construction-general-tomok",
                },
                {
                    "service_code": "FOCUS::electrical-construction",
                    "service_name": "전기공사업",
                    "major_code": "32",
                    "major_name": "전기·정보통신",
                    "group_name": "전기공사업 등록기준",
                    "law_title": "전기공사업법 시행령",
                    "legal_basis_title": "별표 1",
                    "seed_rule_service_code": "RULE::electrical-construction",
                    "seed_rule_id": "electrical-construction",
                },
            ]
        }
        focus_family_registry = {
            "industries": [
                {
                    "service_code": "FOCUS::electrical-construction",
                    "service_name": "전기공사업",
                    "catalog_source_kind": "focus_family_registry",
                    "law_title": "전기공사업법 시행령",
                }
            ]
        }

        packet = generate_permit_focus_source_upgrade_packet.build_packet(
            focus_seed_catalog=focus_seed_catalog,
            focus_family_registry=focus_family_registry,
        )

        self.assertEqual(packet["summary"]["focus_seed_row_total"], 3)
        self.assertEqual(packet["summary"]["focus_family_registry_row_total"], 1)
        self.assertEqual(packet["summary"]["pending_focus_seed_row_total"], 2)
        self.assertEqual(packet["summary"]["target_family_row_total"], 2)
        self.assertEqual(packet["summary"]["remaining_pending_after_apply_total"], 0)
        self.assertEqual(packet["target_family"]["family_key"], "건설산업기본법 시행령")
        self.assertEqual(len(packet["execution_packet"]["registry_rows"]), 2)
        self.assertEqual(
            packet["execution_packet"]["registry_rows"][0]["catalog_source_kind"],
            "focus_family_registry",
        )
        self.assertEqual(
            packet["execution_packet"]["registry_rows"][0]["source_upgrade_status"],
            "materialized_from_focus_seed",
        )

        markdown = generate_permit_focus_source_upgrade_packet.render_markdown(packet)
        self.assertIn("Permit Focus Source Upgrade Packet", markdown)
        self.assertIn("건설산업기본법 시행령", markdown)
        self.assertIn("focus_family_registry_row_total", markdown)


if __name__ == "__main__":
    unittest.main()
