import importlib.util
import pathlib
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "tistory_ops" / "publish_browser.py"
SPEC = importlib.util.spec_from_file_location("tistory_publish_browser_policy", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class TistoryPublishStatePolicyTest(unittest.TestCase):
    def test_content_digest_changes_when_payload_changes(self):
        digest_a = MOD._content_digest("제목", "<p>본문A</p>", "http://example.com/a")
        digest_b = MOD._content_digest("제목", "<p>본문B</p>", "http://example.com/a")
        self.assertNotEqual(digest_a, digest_b)

    def test_duplicate_decision_uses_digest(self):
        digest_old = MOD._content_digest("t", "a", "u")
        digest_new = MOD._content_digest("t", "b", "u")
        sig_old = MOD._content_signature("A BODY")
        sig_new = MOD._content_signature("B BODY")
        state = {
            "published": {
                "7540": {
                    "content_digest": digest_old,
                    "content_signature": sig_old,
                    "published_at": "2026-02-25T01:00:00+00:00",
                },
                "7541": {
                    "content_digest": "x",
                    "content_signature": sig_new,
                    "published_at": "2026-02-25T02:00:00+00:00",
                }
            }
        }

        action_same, _ = MOD._duplicate_decision(
            state, "7540", digest_old, content_signature=sig_old, republish_changed=True
        )
        action_changed_allow, _ = MOD._duplicate_decision(
            state, "7540", digest_new, content_signature=sig_old, republish_changed=True
        )
        action_changed_block, _ = MOD._duplicate_decision(
            state, "7540", digest_new, content_signature=sig_old, republish_changed=False
        )
        action_signature_dup, _ = MOD._duplicate_decision(
            state, "7542", MOD._content_digest("x", "y", "z"), content_signature=sig_new, republish_changed=True
        )

        self.assertEqual(action_same, "skip_duplicate")
        self.assertEqual(action_changed_allow, "allow_changed")
        self.assertEqual(action_changed_block, "skip_changed")
        self.assertEqual(action_signature_dup, "skip_duplicate_signature")

    def test_validate_blog_domain_requires_host_only(self):
        allowed = ["seoulmna.tistory.com"]
        normalized = MOD._validate_blog_domain("SeoulMNA.Tistory.com", override_domains=allowed)
        self.assertEqual(normalized, "seoulmna.tistory.com")

        with self.assertRaises(ValueError):
            MOD._validate_blog_domain("seoulmna.tistory.com/manage/newpost", override_domains=allowed)


if __name__ == "__main__":
    unittest.main()
