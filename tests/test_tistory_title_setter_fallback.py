import importlib.util
import pathlib
import types
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1].parent / "ALL" / "tistory_ops" / "publish_browser.py"
SPEC = importlib.util.spec_from_file_location("tistory_publish_browser_title", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class _FakeEl:
    def __init__(self, interactable: bool = True):
        self._interactable = interactable
        self.keys = []
        self.cleared = False
        self.clicked = False

    def is_displayed(self):
        return self._interactable

    def is_enabled(self):
        return self._interactable

    def click(self):
        self.clicked = True
        if not self._interactable:
            raise RuntimeError("not interactable")

    def clear(self):
        self.cleared = True
        if not self._interactable:
            raise RuntimeError("not interactable")

    def send_keys(self, *args):
        if not self._interactable:
            raise RuntimeError("not interactable")
        self.keys.extend(args)


class _FakeDriver:
    def __init__(self, el: _FakeEl):
        self.el = el
        self.scripts = []

    def find_elements(self, by, query):
        if "title" in str(query) or "제목" in str(query):
            return [self.el]
        return []

    def execute_script(self, script, *args):
        self.scripts.append(script)
        # JS value assignment fallback should return true.
        if "const el = arguments[0]" in script:
            return True
        return True


class TistoryTitleSetterFallbackTest(unittest.TestCase):
    def test_set_title_uses_js_fallback_when_not_interactable(self):
        pub = MOD.TistoryBrowserPublisher(blog_domain="seoulmna.tistory.com")
        fake_el = _FakeEl(interactable=False)
        pub.driver = _FakeDriver(fake_el)
        pub.set_title("테스트 제목")
        self.assertTrue(any("const el = arguments[0]" in s for s in pub.driver.scripts))


if __name__ == "__main__":
    unittest.main()
