import unittest

from internal_linker import InternalLinker, extract_faqs_from_content


class InternalLinkerTest(unittest.TestCase):
    def test_extract_faqs_from_content_matches_rendered_format(self):
        html = (
            '<div style="background:#f8fafc;">'
            '<span style="x">Q</span><span style="y">Question?</span><br>'
            '<span style="x">A</span>Answer.'
            "</div>"
        )
        faqs = extract_faqs_from_content(html)
        self.assertEqual(len(faqs), 1)
        self.assertEqual(faqs[0]["question"], "Question?")
        self.assertEqual(faqs[0]["answer"], "Answer.")

    def test_extract_faqs_from_content_matches_korean_labels(self):
        html = (
            '<div style="background:#f8fafc;">'
            '<span style="x">질문</span><span style="y">기간은 얼마나 걸리나요?</span><br>'
            '<span style="x">답변</span>사전진단 후 일정표를 안내합니다.'
            "</div>"
        )
        faqs = extract_faqs_from_content(html)
        self.assertEqual(len(faqs), 1)
        self.assertEqual(faqs[0]["question"], "기간은 얼마나 걸리나요?")
        self.assertEqual(faqs[0]["answer"], "사전진단 후 일정표를 안내합니다.")

    def test_inject_links_inserts_before_conclusion_and_escapes(self):
        linker = InternalLinker("https://example.com")
        html = (
            '<div style="margin-bottom:56px;"><h2>Body1</h2><div>Text1</div></div>'
            '<div style="margin-bottom:56px;"><h2>Body2</h2><div>Text2</div></div>'
            '<div style="margin-bottom:56px;"><h2>Body3</h2><div>Text3</div></div>'
            '<div style="background:#003764;padding:44px 48px;margin:56px 0;">Conclusion</div>'
        )
        related = [{"title": '키스콘(kiscon) <가이드>', "link": "https://example.com/?q=1&v=2", "relevance": 99}]

        out = linker.inject_links(html, related, position="after_body2")

        self.assertIn("키스콘 &lt;가이드&gt;", out)
        self.assertNotIn("kiscon", out.lower())
        self.assertIn("q=1&amp;v=2", out)
        self.assertLess(out.find("키스콘 &lt;가이드&gt;"), out.find("background:#003764;padding:44px 48px;margin:56px 0;"))

    def test_inject_links_skips_english_only_titles(self):
        linker = InternalLinker("https://example.com")
        html = '<div style="background:#003764;padding:44px 48px;margin:56px 0;">Conclusion</div>'
        related = [{"title": "Company Overview", "link": "https://example.com/a", "relevance": 91}]
        out = linker.inject_links(html, related)
        self.assertEqual(out, html)

    def test_inject_links_skips_when_marker_exists(self):
        linker = InternalLinker("https://example.com")
        html = '<div data-internal-links="1"><p>already injected</p></div>'
        related = [{"title": "T1", "link": "https://example.com/a", "relevance": 11}]
        out = linker.inject_links(html, related)
        self.assertEqual(out, html)

    def test_find_related_posts_penalizes_overused_links(self):
        linker = InternalLinker("https://example.com")
        linker.cached_posts = [
            {"title": "construction new license process", "link": "https://example.com/a", "slug": "a", "excerpt": ""},
            {"title": "construction new license docs", "link": "https://example.com/b", "slug": "b", "excerpt": ""},
        ]
        linker.memory = {"by_keyword": {}, "by_link": {"https://example.com/a": 12, "https://example.com/b": 0}}

        rows = linker.find_related_posts("construction new license", content_text="", max_results=2)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["link"], "https://example.com/b")

    def test_inject_links_filters_unsafe_or_external_urls(self):
        linker = InternalLinker("https://seoulmna.kr/wp-json/wp/v2")
        html = '<div style="background:#003764;padding:44px 48px;margin:56px 0;">Conclusion</div>'
        related = [
            {"title": "bad_js", "link": "javascript:alert(1)", "relevance": 99},
            {"title": "bad_ext", "link": "https://evil.example/post", "relevance": 98},
            {"title": "정상 링크", "link": "https://seoulmna.kr/ok-post", "relevance": 97},
        ]

        out = linker.inject_links(html, related)

        self.assertIn("https://seoulmna.kr/ok-post", out)
        self.assertNotIn("javascript:alert", out)
        self.assertNotIn("evil.example", out)


if __name__ == "__main__":
    unittest.main()
