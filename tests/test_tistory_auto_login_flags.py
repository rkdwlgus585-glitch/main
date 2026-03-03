import importlib.util
import pathlib
import types
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "tistory_ops" / "publish_browser.py"
SPEC = importlib.util.spec_from_file_location("tistory_publish_browser_auto_login", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class TistoryAutoLoginFlagsTest(unittest.TestCase):
    def test_to_bool_variants(self):
        self.assertTrue(MOD._to_bool("1"))
        self.assertTrue(MOD._to_bool("yes"))
        self.assertFalse(MOD._to_bool("0"))
        self.assertFalse(MOD._to_bool("no"))
        self.assertTrue(MOD._to_bool("", default=True))

    def test_wait_for_login_uses_auto_login_when_enabled(self):
        pub = MOD.TistoryBrowserPublisher(blog_domain="seoulmna.tistory.com")
        pub.driver = types.SimpleNamespace(current_url="https://www.tistory.com")
        pub.try_auto_login = lambda **kwargs: True
        pub.wait_for_login(
            interactive=False,
            login_wait_sec=10,
            auto_login=True,
            login_id="id",
            login_password="pw",
            login_url="https://www.tistory.com/auth/login",
        )

    def test_wait_for_login_without_auto_or_interactive_raises(self):
        pub = MOD.TistoryBrowserPublisher(blog_domain="seoulmna.tistory.com")
        pub.driver = types.SimpleNamespace(current_url="https://www.tistory.com")
        with self.assertRaises(RuntimeError):
            pub.wait_for_login(interactive=False, auto_login=False)


if __name__ == "__main__":
    unittest.main()
