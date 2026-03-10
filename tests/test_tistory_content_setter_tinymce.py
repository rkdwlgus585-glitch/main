import importlib.util
import pathlib
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1].parent / "ALL" / "tistory_ops" / "publish_browser.py"
SPEC = importlib.util.spec_from_file_location("tistory_publish_browser_content", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class _FakeDriverTinymce:
    def __init__(self):
        self.scripts = []

    def execute_script(self, script, *_args):
        self.scripts.append(script)
        if "var out={tinymce:false, iframe:false, prose:false, textarea:false}" in script:
            return {"tinymce": True, "iframe": True, "prose": False, "textarea": True}
        # tinymce branch succeeds first
        if "setContent(html,{format:'raw'})" in script and "tinymce.get('editor-tistory')" in script:
            return {"tinymce": True, "iframe": True, "textarea": True, "any": True}
        if "__codex_editor_text_len__" in script:
            return {"__codex_editor_text_len__": 240, "__codex_editor_has_probe__": True}
        return False


class TistoryContentSetterTinymceTest(unittest.TestCase):
    def test_set_content_uses_tinymce_path(self):
        pub = MOD.TistoryBrowserPublisher(blog_domain="seoulmna.tistory.com")
        pub.driver = _FakeDriverTinymce()
        pub.resolve_draft_alert = lambda: False
        pub.set_content_html("<p>본문</p>")
        self.assertTrue(any("setContent(html,{format:'raw'})" in s for s in pub.driver.scripts))


if __name__ == "__main__":
    unittest.main()
