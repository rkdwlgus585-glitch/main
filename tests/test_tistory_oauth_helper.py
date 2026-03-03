import importlib.util
import pathlib
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "tistory_ops" / "oauth_helper.py"
SPEC = importlib.util.spec_from_file_location("tistory_oauth_helper", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class TistoryOauthHelperTest(unittest.TestCase):
    def test_build_authorize_url_contains_required_params(self):
        url = MOD.build_authorize_url("app-id", "https://example.com/callback", state="abc123")
        self.assertIn("client_id=app-id", url)
        self.assertIn("redirect_uri=https%3A%2F%2Fexample.com%2Fcallback", url)
        self.assertIn("response_type=code", url)
        self.assertIn("state=abc123", url)


if __name__ == "__main__":
    unittest.main()

