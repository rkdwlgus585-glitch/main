import os
import unittest
from unittest.mock import patch

import gabji


class GabjiOutputPathTest(unittest.TestCase):
    def test_default_gabji_output_path_uses_desktop_dir(self):
        with patch.object(gabji, "_desktop_output_dir", return_value=r"C:\Users\tester\Desktop"):
            out = gabji._default_gabji_output_path("png")
        self.assertTrue(out.startswith(r"C:\Users\tester\Desktop"))
        self.assertTrue(out.endswith(".png"))
        self.assertIn("갑지_", os.path.basename(out))

    def test_desktop_output_dir_prefers_userprofile_desktop(self):
        user_profile = r"C:\Users\tester"

        def _isdir(path):
            return path == os.path.join(user_profile, "Desktop")

        with patch.dict(os.environ, {"USERPROFILE": user_profile}, clear=False):
            with patch("gabji.os.path.expanduser", return_value=r"C:\Home\tester"):
                with patch("gabji.os.path.isdir", side_effect=_isdir):
                    out = gabji._desktop_output_dir()

        self.assertEqual(out, os.path.join(user_profile, "Desktop"))

    def test_desktop_output_dir_falls_back_to_userprofile(self):
        user_profile = r"C:\Users\tester"
        with patch.dict(os.environ, {"USERPROFILE": user_profile}, clear=False):
            with patch("gabji.os.path.expanduser", return_value=r"C:\Home\tester"):
                with patch("gabji.os.path.isdir", return_value=False):
                    out = gabji._desktop_output_dir()
        self.assertEqual(out, user_profile)


if __name__ == "__main__":
    unittest.main()
