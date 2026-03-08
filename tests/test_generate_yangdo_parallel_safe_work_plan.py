from __future__ import annotations

import unittest

from scripts.generate_yangdo_parallel_safe_work_plan import build_report


class GenerateYangdoParallelSafeWorkPlanTests(unittest.TestCase):
    def test_classifies_core_files_as_blocked(self) -> None:
        payload = build_report(
            git_status_lines=[
                " M yangdo_blackbox_api.py",
                " M scripts/publish_private_ai_admin_pages.py",
                "?? scripts/generate_yangdo_exact_combo_recovery_audit.py",
            ],
            sector_audit={
                "sectors": [
                    {"sector": "전기", "status": "underpricing_hotspot", "price_metrics": {"under_67_share": 0.8}, "observed_record_count": 10},
                    {"sector": "토목", "status": "sparse_support_hotspot", "price_metrics": {"under_67_share": 0.2}, "observed_record_count": 8},
                ]
            },
            brainstorm={
                "current_execution_lane": {"id": "balance_model_none_replacement"},
                "parallel_brainstorm_lane": {"id": "exact_combo_support_recovery"},
            },
        )
        summary = payload["summary"]
        self.assertEqual(summary["blocked_to_edit_now"], 2)
        self.assertEqual(summary["safe_to_edit_now"], 1)
        self.assertEqual(summary["parallel_lane"], "exact_combo_support_recovery")
        blocked_paths = [row["path"] for row in payload["safe_workzones"]["blocked_runtime_files"]]
        self.assertIn("yangdo_blackbox_api.py", blocked_paths)


if __name__ == "__main__":
    unittest.main()
