import unittest
from unittest.mock import Mock, patch

from utils import Notifier, load_config, require_config, setup_logger


class UtilsConfigTest(unittest.TestCase):
    def test_require_config_raises_for_missing(self):
        cfg = {"A": "ok", "B": ""}
        with self.assertRaises(ValueError):
            require_config(cfg, ["A", "B"], context="test")

    def test_load_config_applies_aliases_and_bool(self):
        env = {
            "CONSULTANT_NAME": "Tester",
            "SCHEDULE_ENABLED": "true",
            "SCHEDULE_TIME": "10:30",
            "MAIN_SITE": "https://example.com",
        }
        with patch.dict("os.environ", env, clear=True), patch("utils._load_env_file", return_value={}):
            cfg = load_config()

        self.assertEqual(cfg["CONSULTANT"], "Tester")
        self.assertEqual(cfg["CONSULTANT_NAME"], "Tester")
        self.assertEqual(cfg["SITE_URL"], "https://example.com")
        self.assertTrue(cfg["SCHEDULE_ENABLED"])
        self.assertEqual(cfg["SCHEDULE_TIME"], "10:30")



    def test_notifier_retries_then_succeeds(self):
        notifier = Notifier(discord_url="https://discord.example/webhook")
        with patch("utils.requests.post") as mock_post:
            mock_post.side_effect = [Exception("net"), Mock(status_code=204)]
            ok = notifier.send("hello", title="t")

        self.assertTrue(ok)
        self.assertEqual(mock_post.call_count, 2)

    def test_setup_logger_does_not_duplicate_handlers(self):
        logger_name = "unit_logger_cfg"
        logger = setup_logger(name=logger_name, log_dir="logs")
        base_count = len(logger.handlers)
        logger2 = setup_logger(name=logger_name, log_dir="logs")
        self.assertEqual(len(logger2.handlers), base_count)

if __name__ == "__main__":
    unittest.main()


