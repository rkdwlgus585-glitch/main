import unittest

from core_engine.permit_mapping_pipeline import apply_mapping_pipeline


class PermitMappingPipelineTests(unittest.TestCase):
    def test_apply_mapping_pipeline_assigns_batches(self):
        industries = [
            {"service_code": "02_A", "service_name": "A", "major_code": "02", "major_name": "Group2", "collection_status": "pending_law_mapping"},
            {"service_code": "02_B", "service_name": "B", "major_code": "02", "major_name": "Group2", "collection_status": "pending_law_mapping"},
            {"service_code": "02_C", "service_name": "C", "major_code": "02", "major_name": "Group2", "collection_status": "pending_law_mapping"},
            {"service_code": "03_A", "service_name": "A", "major_code": "03", "major_name": "Group3", "collection_status": "pending_law_mapping"},
            {"service_code": "03_B", "service_name": "B", "major_code": "03", "major_name": "Group3", "collection_status": "pending_law_mapping"},
            {"service_code": "03_C", "service_name": "C", "major_code": "03", "major_name": "Group3", "collection_status": "pending_law_mapping"},
            {"service_code": "03_D", "service_name": "D", "major_code": "03", "major_name": "Group3", "collection_status": "pending_law_mapping"},
            {"service_code": "01_M", "service_name": "M", "major_code": "01", "major_name": "Mapped", "collection_status": "criteria_extracted"},
        ]

        updated, meta = apply_mapping_pipeline(industries, batch_size=2)

        self.assertEqual(meta["pending_total"], 7)
        self.assertEqual(meta["mapped_total"], 1)
        self.assertEqual(meta["major_group_total"], 2)
        self.assertEqual(meta["batch_total"], 4)
        self.assertEqual(meta["batch_size"], 2)

        queued = [row for row in updated if row.get("mapping_status") == "queued_law_mapping"]
        self.assertEqual(len(queued), 7)
        self.assertTrue(all(str(row.get("mapping_batch_id") or "").startswith("M") for row in queued))

    def test_apply_mapping_pipeline_marks_mapped_rows(self):
        industries = [
            {"service_code": "01_A", "major_code": "01", "major_name": "M", "collection_status": "criteria_extracted"},
            {"service_code": "02_A", "major_code": "02", "major_name": "P", "collection_status": "pending_law_mapping"},
        ]

        updated, _meta = apply_mapping_pipeline(industries, batch_size=10)
        mapped = next(row for row in updated if row.get("service_code") == "01_A")
        pending = next(row for row in updated if row.get("service_code") == "02_A")

        self.assertEqual(mapped.get("mapping_status"), "mapped")
        self.assertEqual(mapped.get("mapping_batch_id"), "")
        self.assertEqual(mapped.get("mapping_batch_seq"), 0)
        self.assertEqual(pending.get("mapping_status"), "queued_law_mapping")
        self.assertTrue(str(pending.get("mapping_batch_id")).startswith("M02-"))


if __name__ == "__main__":
    unittest.main()
