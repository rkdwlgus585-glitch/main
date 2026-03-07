import unittest

from scripts import run_monthly_notice_archive_publish_pipeline as pipeline


class RunMonthlyNoticeArchivePublishPipelineTest(unittest.TestCase):
    def test_relax_pct_schedule(self) -> None:
        self.assertEqual(pipeline._relax_pct_for_attempt(1, 10, 0.05), 0.0)
        self.assertEqual(pipeline._relax_pct_for_attempt(10, 10, 0.05), 0.0)
        self.assertEqual(pipeline._relax_pct_for_attempt(11, 10, 0.05), 0.05)
        self.assertEqual(pipeline._relax_pct_for_attempt(20, 10, 0.05), 0.05)
        self.assertEqual(pipeline._relax_pct_for_attempt(21, 10, 0.05), 0.10)
        self.assertEqual(pipeline._relax_pct_for_attempt(205, 10, 0.05), 1.0)


if __name__ == "__main__":
    unittest.main()
