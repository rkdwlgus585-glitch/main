import unittest
import json
import os
import re
import tempfile
from datetime import datetime
from unittest.mock import patch
from urllib.parse import unquote

import mnakr


class MnakrQualityTest(unittest.TestCase):
    def _long_text(self, keyword, min_len, repeats):
        seed = (f"{keyword} 진행 시 실무 체크포인트를 기준으로 준비해야 할 항목을 정리합니다. " * repeats).strip()
        while len(seed) < min_len:
            seed += " 서류 정합성, 일정 관리, 리스크 점검을 함께 검토합니다."
        return seed

    def test_safe_error_text_never_returns_none_literal(self):
        self.assertNotIn("None", mnakr._safe_error_text(None))
        self.assertIn("Exception", mnakr._safe_error_text(Exception(None)))

    def test_publication_qa_auditor_passes_on_strong_content(self):
        keyword = "건설업 면허 반납 절차"
        content = {
            "headline": f"{keyword} 2026 최신 가이드",
            "english_slug": "construction-license-surrender-process",
            "summary": (
                f"{keyword}를 준비하는 과정에서 필요한 서류, 점검 절차, 리스크 관리, 예상 일정과 비용 범위를 "
                "실무 기준으로 한 번에 정리한 종합 안내입니다. 실제 상담 전 반드시 확인해야 하는 핵심 체크리스트까지 포함합니다."
            ),
            "intro": (
                f"{keyword}의 핵심은 등록기준 적합성과 서류 정합성, 일정 리스크 선제 점검입니다. "
                "사전진단으로 반려 가능성을 줄일 수 있습니다."
                f"[PARA]{self._long_text(keyword, 420, 8)}"
            ),
            "body1_text": self._long_text(keyword, 850, 12),
            "body2_text": self._long_text(keyword, 850, 12)
            + " 사전진단이 없으면 기회비용과 리스크가 커질 수 있습니다."
            + "[PARA][EXTLINK]건설산업기본법|https://www.law.go.kr/법령/건설산업기본법[/EXTLINK]",
            "body3_text": self._long_text(keyword, 850, 12)
            + "[PARA][LIST]1단계: 진단|2단계: 서류점검|3단계: 접수[/LIST]"
            + "[PARA][EXTLINK]건설공제조합|https://www.cgbo.co.kr[/EXTLINK]",
            "conclusion": self._long_text(keyword, 340, 6)
            + "[PARA][FAQ]Q: 진행 기간은?|A: 사전진단 후 일정표를 안내합니다.[/FAQ]"
            + "[FAQ]Q: 준비서류는?|A: 체크리스트 기준으로 사전검토합니다.[/FAQ]",
        }
        html = (
            "background:#f8f9fb border-left:3px solid #003764 border:1px solid #e2e8f0 <ol href=\"#a\" "
            "Author Updated "
            "<h2 id='a'></h2><h2 id='b'></h2><h2 id='c'></h2> "
            "background:#001a33 tel: https://open.kakao.com/o/syWr1hIe "
            "margin-bottom:56px; margin-bottom:56px; margin-bottom:56px; "
            "<figure></figure> \"FAQPage\" \"@type\": \"Article\""
        )
        report = mnakr.PublicationQAAuditor().audit(keyword, content, rendered_html=html)

        self.assertTrue(report["pass_gate"])
        self.assertEqual(report["seo"]["score"], 100.0)
        self.assertEqual(report["legal"]["score"], 100.0)

    def test_format_text_repairs_extlink_without_url(self):
        wp = mnakr.WPEngine(verify_auth=False, allow_no_auth=True)
        src = "[EXTLINK]건설산업기본법 제20조(폐업신고 등)[/EXTLINK]"
        out = wp._format_text(src)
        self.assertIn("<a href=", out)
        self.assertNotIn("[EXTLINK]", out)
        self.assertNotIn("[/EXTLINK]", out)

    def test_format_text_handles_para_and_block_tokens_without_broken_p(self):
        wp = mnakr.WPEngine(verify_auth=False, allow_no_auth=True)
        src = (
            "[PARA]첫 문단입니다."
            "[PARA][POINT]핵심 안내[/POINT]"
            "[PARA][LIST]법인 <strong>3.5억</strong>|개인 &lt;strong&gt;7억&lt;/strong&gt;[/LIST]"
            "[PARA][FAQ]Q: 기간은?|A: 사전진단 후 일정표를 안내합니다.[/FAQ]"
        )
        out = wp._format_text(src)
        self.assertFalse(out.lstrip().startswith("</p>"))
        self.assertNotIn('<p style="margin-bottom:18px;line-height:1.85;color:#2d2d2d;"><div', out)
        self.assertNotIn("<p style=\"margin-bottom:18px;line-height:1.85;color:#2d2d2d;\"><ul", out)
        self.assertNotIn("&lt;strong", out)
        self.assertIn("핵심 포인트", out)

    def test_format_text_handles_korean_faq_labels(self):
        wp = mnakr.WPEngine(verify_auth=False, allow_no_auth=True)
        src = "[PARA][FAQ]질문: 진행 기간은?|답변: 사전진단 후 일정표를 안내합니다.[/FAQ]"
        out = wp._format_text(src)
        self.assertIn("질문", out)
        self.assertIn("답변", out)
        self.assertNotIn("[FAQ]", out)
        self.assertNotIn("[/FAQ]", out)

    def test_resolve_kakao_cta_media_uses_og_image_fallback(self):
        class FakeResp:
            status_code = 200
            text = '<html><head><meta property="og:image" content="https://cdn.example.com/kakao-cta.png"></head></html>'

        old_path = mnakr.CONFIG.get("KAKAO_CTA_IMAGE_PATH")
        old_url = mnakr.CONFIG.get("KAKAO_CTA_IMAGE_URL")
        old_openchat = mnakr.CONFIG.get("KAKAO_OPENCHAT_URL")
        try:
            mnakr.CONFIG["KAKAO_CTA_IMAGE_PATH"] = "missing_kakao_cta.png"
            mnakr.CONFIG["KAKAO_CTA_IMAGE_URL"] = ""
            mnakr.CONFIG["KAKAO_OPENCHAT_URL"] = "https://open.kakao.com/o/mock"

            wp = mnakr.WPEngine(verify_auth=False, allow_no_auth=True)
            with patch.object(wp, "_resolve_local_media_path", return_value=""), \
                 patch("mnakr.requests.get", return_value=FakeResp()):
                media = wp._resolve_kakao_cta_media()

            self.assertIsNotNone(media)
            self.assertEqual(media.get("source_url"), "https://cdn.example.com/kakao-cta.png")
            self.assertIsNone(media.get("id"))
        finally:
            mnakr.CONFIG["KAKAO_CTA_IMAGE_PATH"] = old_path
            mnakr.CONFIG["KAKAO_CTA_IMAGE_URL"] = old_url
            mnakr.CONFIG["KAKAO_OPENCHAT_URL"] = old_openchat

    def test_auto_fix_fact_errors_handles_integer_style_amount_variant(self):
        engine = mnakr.ColumnistEngine.__new__(mnakr.ColumnistEngine)
        content = {
            "summary": "",
            "intro": "건축공사업 법인 자본금은 5억원입니다.",
            "body1_text": "토목공사업 법인 자본금은 5억원입니다.",
            "body2_text": "",
            "body3_text": "",
            "conclusion": "",
        }
        errors = [
            {
                "type": "자본금_오류",
                "업종": "건축공사업",
                "발견값": "5.0억원",
                "정확값": "3.5억원",
            }
        ]
        engine._auto_fix_fact_errors(content, errors)
        self.assertIn("건축공사업 법인 자본금은 3.5억원", content["intro"])
        self.assertIn("토목공사업 법인 자본금은 5억원", content["body1_text"])

    def test_auto_fix_fact_errors_handles_korean_thousand_man_amount_variant(self):
        engine = mnakr.ColumnistEngine.__new__(mnakr.ColumnistEngine)
        content = {
            "summary": "",
            "intro": "토목공사업 법인 자본금은 8억 5천만원입니다.",
            "body1_text": "",
            "body2_text": "",
            "body3_text": "",
            "conclusion": "",
        }
        errors = [
            {
                "type": "자본금_오류",
                "업종": "토목공사업",
                "발견값": "8.5억원",
                "정확값": "5.0억원",
            }
        ]
        engine._auto_fix_fact_errors(content, errors)
        self.assertIn("토목공사업 법인 자본금은 5.0억원", content["intro"])
        self.assertNotIn("8억 5천만원", content["intro"])

    def test_auto_fix_fact_errors_does_not_cross_replace_other_industry_amount(self):
        engine = mnakr.ColumnistEngine.__new__(mnakr.ColumnistEngine)
        content = {
            "summary": "",
            "intro": "건축공사업 법인 자본금은 3.5억원이고 토목공사업 법인 자본금은 5.0억원입니다.",
            "body1_text": "",
            "body2_text": "",
            "body3_text": "",
            "conclusion": "",
        }
        errors = [
            {
                "type": "자본금_오류",
                "업종": "건축공사업",
                "발견값": "5.0억원",
                "정확값": "3.5억원",
            }
        ]
        engine._auto_fix_fact_errors(content, errors)
        self.assertIn("토목공사업 법인 자본금은 5.0억원", content["intro"])

    def test_validate_and_warn_does_not_match_across_section_boundaries(self):
        engine = mnakr.ColumnistEngine.__new__(mnakr.ColumnistEngine)
        content = {
            "summary": "",
            "intro": "토목공사업",
            "body1_text": "법인 자본금은 8.5억원입니다.",
            "body2_text": "",
            "body3_text": "",
            "conclusion": "",
        }
        errors = engine._validate_and_warn(content)
        self.assertEqual(errors, [])

    def test_compose_publish_slug_adds_korean_focus_hint(self):
        slug = mnakr._compose_publish_slug(
            "construction-license-strategy-2026",
            "건설업 면허 추가등록 전략",
        )
        self.assertIn("건설업-면허-추가등록-전략", unquote(slug))
        self.assertTrue(mnakr._is_valid_wp_slug(slug))

    def test_is_valid_wp_slug_accepts_hangul_tokens(self):
        self.assertTrue(
            mnakr._is_valid_wp_slug("construction-license-2026-건설업-면허-전략")
        )

    def test_summary_keyword_alignment_keeps_focus_keyword_in_summary(self):
        engine = mnakr.ColumnistEngine.__new__(mnakr.ColumnistEngine)
        keyword = "건설업 면허 추가등록 전략"
        content = {"summary": "2026년 기준 건설업 면허 추가등록을 위한 완벽 가이드입니다."}
        engine._ensure_summary_keyword_alignment(keyword, content)
        self.assertIn(keyword, content["summary"])
        self.assertLessEqual(len(content["summary"]), 160)
        self.assertNotIn("...", content["summary"])

    def test_build_seo_description_keeps_keyword_and_natural_ending(self):
        keyword = "건설업 면허 추가등록 전략"
        src = (
            "2026년 기준으로 자본금, 기술인력, 공제조합, 등록 서류를 빠르게 점검하고 "
            "실무에서 자주 누락되는 리스크 대응 절차를 한 번에 확인할 수 있도록 정리했습니다. "
            "상황별 체크리스트까지 제공합니다."
        )
        out = mnakr._build_seo_description(keyword, src, min_len=110, max_len=160)
        self.assertIn(keyword, out)
        self.assertGreaterEqual(len(out), 110)
        self.assertLessEqual(len(out), 160)
        self.assertNotIn("...", out)

    def test_build_seo_description_strips_trailing_ellipsis(self):
        keyword = "건설업 양도양수 절차"
        src = "건설업 양도양수 절차 핵심 포인트를 단계별로 정리했습니다..."
        out = mnakr._build_seo_description(keyword, src, min_len=110, max_len=160)
        self.assertIn(keyword, out)
        self.assertFalse(out.endswith("..."))

    def test_build_seo_description_closes_incomplete_tail_naturally(self):
        keyword = "건설업 양도양수 절차"
        src = (
            "2026년 최신 건설업 양도양수 절차를 완벽하게 안내합니다. 신규 등록보다 빠르게 실적을 승계하며 사업을 시작할 수 있는 "
            "양수도의 모든 과정을 단계별로 설명합니다. 기업 실사, 계약, 법정 등록기준 충족 등 성공적인 인수를 위한 핵심 포인트를 "
            "확인하세요. 건설업 양도양수 절차 핵심"
        )
        out = mnakr._build_seo_description(keyword, src, min_len=110, max_len=160)
        self.assertIn(keyword, out)
        self.assertRegex(out, r"(다\.|요\.|니다\.|[!?])$")

    def test_summary_for_display_humanizes_trailing_ellipsis(self):
        wp = mnakr.WPEngine(verify_auth=False, allow_no_auth=True)
        src = "건설업 면허 추가등록 전략 핵심 요건, 일정, 비용..."
        out = wp._summary_for_display(src)
        self.assertIn("내용을 본문에서 이어서 확인하세요.", out)
        self.assertNotIn("...", out)

    def test_with_particle_selects_correct_josa(self):
        self.assertEqual(mnakr._with_particle("건설업 양도양수 절차", "은/는"), "건설업 양도양수 절차는")
        self.assertEqual(mnakr._with_particle("건설업 등록기준", "은/는"), "건설업 등록기준은")

    def test_naturalize_korean_text_fixes_josa_and_repetition(self):
        src = "건설업 양도양수 절차은 핵심입니다. 확인하세요. 확인하세요."
        out = mnakr._naturalize_korean_text(src, keyword="건설업 양도양수 절차")
        self.assertIn("건설업 양도양수 절차는 핵심입니다.", out)
        self.assertNotIn("확인하세요. 확인하세요.", out)

    def test_naturalize_korean_text_adds_period_after_polite_ending(self):
        src = "핵심 요건을 정리했습니다 추가로 체크리스트를 확인하세요"
        out = mnakr._naturalize_korean_text(src, keyword="")
        self.assertIn("정리했습니다.", out)

    def test_featured_snippet_intro_uses_correct_keyword_particle(self):
        engine = mnakr.ColumnistEngine.__new__(mnakr.ColumnistEngine)
        content = {"intro": ""}
        engine._ensure_featured_snippet_intro("건설업 양도양수 절차", content)
        self.assertIn("건설업 양도양수 절차는", content["intro"])

    def test_build_seo_description_avoids_duplicate_consecutive_sentences(self):
        keyword = "건설업 양도양수 실사 체크리스트"
        src = f"{keyword} 핵심 요건을 정리했습니다"
        out = mnakr._build_seo_description(keyword, src, min_len=110, max_len=160)
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\\s+", out) if p.strip()]
        for i in range(1, len(parts)):
            self.assertNotEqual(parts[i], parts[i - 1])

    def test_render_post_html_uses_block_heading_for_summary(self):
        old_wp_url = mnakr.CONFIG.get("WP_URL")
        try:
            mnakr.CONFIG["WP_URL"] = "https://example.com/wp-json/wp/v2"
            wp = mnakr.WPEngine(verify_auth=False, allow_no_auth=True)
            content = {
                "headline": "건설업 면허 추가등록 전략",
                "summary": "요약 문장입니다.",
                "intro": "인트로 문장입니다.",
                "body1_title": "섹션1",
                "body1_text": "본문1",
                "body2_title": "섹션2",
                "body2_text": "본문2",
                "body3_title": "섹션3",
                "body3_text": "본문3",
                "conclusion": "결론입니다.",
            }
            html = wp._render_post_html("건설업 면허 추가등록 전략", content, include_related=False)
            self.assertIn('<div style="font-size:17px;font-weight:600;color:#003764;">핵심 요약</div>', html)
            self.assertNotIn('<span style="font-size:17px;font-weight:600;color:#003764;">핵심 요약</span>', html)
        finally:
            mnakr.CONFIG["WP_URL"] = old_wp_url

    def test_ai_schedule_optimizer_returns_slots(self):
        optimizer = mnakr.AIScheduleOptimizer()
        slots = optimizer.recommend_slots()
        self.assertTrue(slots)
        self.assertTrue(all(len(x) == 2 for x in slots))

    def test_lifecycle_register_creates_checkpoints(self):
        with tempfile.TemporaryDirectory() as td:
            original = mnakr.CONFIG.get("LIFECYCLE_FILE")
            original_enabled = mnakr.CONFIG.get("LIFECYCLE_ENABLED")
            mnakr.CONFIG["LIFECYCLE_FILE"] = os.path.join(td, "lifecycle.json")
            mnakr.CONFIG["LIFECYCLE_ENABLED"] = True
            opt = mnakr.LifecycleOptimizer()
            post = {"id": 123, "link": "https://example.com/p/123"}
            content = {"headline": "제목", "summary": "요약"}
            opt.register_post(post, "건설업 면허 반납 절차", content)
            data = opt._load()
            self.assertIn("123", data.get("posts", {}))
            cps = data["posts"]["123"].get("checkpoints", [])
            self.assertEqual(len(cps), 3)
            mnakr.CONFIG["LIFECYCLE_FILE"] = original
            mnakr.CONFIG["LIFECYCLE_ENABLED"] = original_enabled

    def test_lifecycle_bootstrap_from_wordpress(self):
        fake_rows = [
            {
                "id": 999,
                "link": "https://example.com/p/999",
                "title": {"rendered": "건설업 신규등록 절차 안내"},
                "excerpt": {"rendered": "<p>요약</p>"},
                "date": "2026-02-01T09:00:00",
            }
        ]

        class FakeResp:
            status_code = 200
            headers = {"X-WP-TotalPages": "1"}

            def json(self):
                return fake_rows

        with tempfile.TemporaryDirectory() as td:
            original_file = mnakr.CONFIG.get("LIFECYCLE_FILE")
            original_enabled = mnakr.CONFIG.get("LIFECYCLE_ENABLED")
            original_wp_url = mnakr.CONFIG.get("WP_URL")
            mnakr.CONFIG["LIFECYCLE_FILE"] = os.path.join(td, "lifecycle.json")
            mnakr.CONFIG["LIFECYCLE_ENABLED"] = True
            mnakr.CONFIG["WP_URL"] = "https://example.com/wp-json/wp/v2"
            opt = mnakr.LifecycleOptimizer()
            with patch("mnakr.requests.get", return_value=FakeResp()):
                added = opt.bootstrap_from_wordpress(max_posts=5)
            self.assertEqual(added, 1)
            data = opt._load()
            self.assertIn("999", data.get("posts", {}))
            mnakr.CONFIG["LIFECYCLE_FILE"] = original_file
            mnakr.CONFIG["LIFECYCLE_ENABLED"] = original_enabled
            mnakr.CONFIG["WP_URL"] = original_wp_url

    def test_portfolio_decision_rules(self):
        opt = mnakr.ContentPortfolioOptimizer()
        action, reason = opt._decide(
            score=45.0,
            metrics={"impressions": 20, "ctr": 0.003},
            age_days=60,
        )
        self.assertEqual(action, "delete_republish")
        self.assertIn("severe", reason)

        action2, _ = opt._decide(
            score=65.0,
            metrics={"impressions": 120, "ctr": 0.006},
            age_days=45,
        )
        self.assertEqual(action2, "rewrite")



    def test_query_rewrite_title_summary_rules(self):
        opt = mnakr.QueryCTRRewriteOptimizer()
        title, summary = opt._rewrite_title_summary(
            "건설업 양도양수 절차",
            "짧은 제목",
            "짧은 요약",
        )
        self.assertLessEqual(len(title), 58)
        self.assertLessEqual(len(summary), 160)
        self.assertGreaterEqual(len(summary), 100)
        self.assertIn("건설업 양도양수 절차", title)

    def test_query_rewrite_optimizer_applies_rewrite(self):
        class FakeResp:
            status_code = 200
            text = "{}"

            def raise_for_status(self):
                return None

            def json(self):
                return {}

        class FakeWPEngine:
            def __init__(self):
                self.wp_url = "https://example.com/wp-json/wp/v2"
                self.headers = {"Authorization": "x"}
                self.auth_headers = {"Authorization": "x"}
                self.meta_calls = []

            def _update_rankmath_meta(self, post_id, keyword, seo_title, seo_desc):
                self.meta_calls.append((post_id, keyword, seo_title, seo_desc))
                return True

        cfg_keys = [
            "QUERY_REWRITE_ENABLED",
            "QUERY_REWRITE_QUEUE_FILE",
            "QUERY_REWRITE_MIN_IMPRESSIONS",
            "QUERY_REWRITE_LOW_CTR",
            "QUERY_REWRITE_MAX_ACTIONS_PER_DAY",
            "QUERY_REWRITE_COOLDOWN_DAYS",
            "QUERY_REWRITE_MIN_SIMILARITY",
        ]

        with tempfile.TemporaryDirectory() as td:
            old_cfg = {k: mnakr.CONFIG.get(k) for k in cfg_keys}
            queue_path = os.path.join(td, "query_rewrite_queue.json")
            mnakr.CONFIG["QUERY_REWRITE_ENABLED"] = True
            mnakr.CONFIG["QUERY_REWRITE_QUEUE_FILE"] = queue_path
            mnakr.CONFIG["QUERY_REWRITE_MIN_IMPRESSIONS"] = 80
            mnakr.CONFIG["QUERY_REWRITE_LOW_CTR"] = 0.02
            mnakr.CONFIG["QUERY_REWRITE_MAX_ACTIONS_PER_DAY"] = 1
            mnakr.CONFIG["QUERY_REWRITE_COOLDOWN_DAYS"] = 14
            mnakr.CONFIG["QUERY_REWRITE_MIN_SIMILARITY"] = 0.3

            opt = mnakr.QueryCTRRewriteOptimizer()
            fake_wp = FakeWPEngine()
            posted = []

            posts = [
                {
                    "id": 101,
                    "title": {"rendered": "건설업 면허 반납 절차 실무 가이드"},
                    "slug": "construction-license-surrender-guide",
                    "link": "https://example.com/p/101",
                    "excerpt": {"rendered": "<p>기존 요약</p>"},
                }
            ]
            metrics = [
                {
                    "query": "건설업 면허 반납 절차",
                    "impressions": 500,
                    "ctr": 0.004,
                }
            ]

            def _fake_post(url, headers=None, json=None, timeout=None):
                posted.append((url, json))
                return FakeResp()

            try:
                with patch("mnakr.WPEngine", return_value=fake_wp), \
                     patch.object(mnakr.QueryCTRRewriteOptimizer, "_fetch_posts", return_value=posts), \
                     patch.object(opt.perf, "load_query_metrics", return_value=metrics), \
                     patch("mnakr.requests.post", side_effect=_fake_post):
                    result = opt.run_daily()

                self.assertEqual(result.get("queued"), 1)
                self.assertEqual(result.get("applied"), 1)
                self.assertTrue(any("/posts/101" in url for url, _payload in posted))
                self.assertEqual(len(fake_wp.meta_calls), 1)

                with open(queue_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.assertEqual(state.get("items", [])[0].get("status"), "applied")
            finally:
                for k, v in old_cfg.items():
                    if v is None and k in mnakr.CONFIG:
                        del mnakr.CONFIG[k]
                    else:
                        mnakr.CONFIG[k] = v

    def test_publication_qa_auditor_blocks_mojibake(self):
        keyword = "construction license surrender"
        content = {
            "headline": f"{keyword} 2026 guide",
            "english_slug": "construction-license-surrender-process",
            "summary": f"{keyword} summary overview.",
            "intro": f"{keyword}????? precheck required.[PARA]" + self._long_text(keyword, 420, 8),
            "body1_text": self._long_text(keyword, 850, 12),
            "body2_text": self._long_text(keyword, 850, 12),
            "body3_text": self._long_text(keyword, 850, 12),
            "conclusion": self._long_text(keyword, 340, 6)
            + "[PARA][FAQ]Q: duration?|A: timeline shared after precheck.[/FAQ]"
            + "[FAQ]Q: docs?|A: we review with a checklist.[/FAQ]",
        }
        html = (
            'background:#f8f9fb border-left:3px solid #003764 border:1px solid #e2e8f0 <ol href="#a" '
            "Author Updated <h2 id='a'></h2><h2 id='b'></h2><h2 id='c'></h2> "
            "background:#001a33 https://open.kakao.com/o/syWr1hIe "
            "margin-bottom:56px; margin-bottom:56px; margin-bottom:56px; <figure></figure> "
            '"FAQPage" "@type": "Article"'
        )
        report = mnakr.PublicationQAAuditor().audit(keyword, content, rendered_html=html)
        self.assertFalse(report["pass_gate"])
        self.assertFalse(report["content"]["checks"].get("encoding_clean", True))

    def test_publication_qa_auditor_blocks_placeholder_summary(self):
        keyword = "건설업 면허 반납 절차"
        content = {
            "headline": f"{keyword} 2026 최신 가이드",
            "english_slug": "construction-license-surrender-process",
            "summary": (
                f"{keyword} TBD 실무 안내입니다. 준비 서류와 체크리스트, 일정 및 비용 범위를 빠르게 확인하고 "
                "실행 리스크를 줄이는 순서를 정리했습니다."
            ),
            "intro": (
                f"{keyword}의 핵심은 등록기준 적합성과 서류 정합성, 일정 리스크 선제 점검입니다."
                f"[PARA]{self._long_text(keyword, 420, 8)}"
            ),
            "body1_title": f"{keyword} 핵심 요건",
            "body1_text": self._long_text(keyword, 850, 12),
            "body2_title": f"{keyword} 실무 체크리스트",
            "body2_text": self._long_text(keyword, 850, 12)
            + "[PARA][EXTLINK]건설산업기본법|https://www.law.go.kr/법령/건설산업기본법[/EXTLINK]",
            "body3_title": f"{keyword} 실행 로드맵",
            "body3_text": self._long_text(keyword, 850, 12)
            + "[PARA][LIST]1단계: 진단|2단계: 서류점검|3단계: 접수[/LIST]"
            + "[PARA][EXTLINK]건설공제조합|https://www.cgbo.co.kr[/EXTLINK]",
            "conclusion": self._long_text(keyword, 340, 6)
            + "[PARA][FAQ]Q: 진행 기간은?|A: 사전진단 후 일정표를 안내합니다.[/FAQ]"
            + "[FAQ]Q: 준비서류는?|A: 체크리스트 기준으로 사전검토합니다.[/FAQ]",
        }
        html = (
            "background:#f8f9fb border-left:3px solid #003764 border:1px solid #e2e8f0 <ol href=\"#a\" "
            "Author Updated "
            "<h2 id='a'></h2><h2 id='b'></h2><h2 id='c'></h2> "
            "background:#001a33 tel: https://open.kakao.com/o/syWr1hIe "
            "margin-bottom:56px; margin-bottom:56px; margin-bottom:56px; "
            "<figure></figure> \"FAQPage\" \"@type\": \"Article\""
        )
        report = mnakr.PublicationQAAuditor().audit(keyword, content, rendered_html=html)
        self.assertFalse(report["pass_gate"])
        self.assertFalse(report["content"]["checks"].get("no_placeholder_text", True))
        self.assertFalse(report["publish_readiness"]["checks"].get("summary_no_placeholder", True))

    def test_wp_publish_preflight_blocks_raw_tokens(self):
        keyword = "건설업 면허 반납 절차"
        content = {
            "headline": f"{keyword} 2026 최신 가이드",
            "english_slug": "construction-license-surrender-process",
            "summary": (
                f"{keyword} 준비서류, 체크리스트, 예상 일정·비용·리스크를 실무 기준으로 정리해 "
                "상담 전에 반드시 확인해야 할 실행 포인트를 제시합니다."
            ),
            "intro": f"{keyword} 실무 준비 가이드입니다.[PARA]{self._long_text(keyword, 420, 8)}",
            "body1_title": f"{keyword} 핵심 요건",
            "body1_text": self._long_text(keyword, 850, 12),
            "body2_title": f"{keyword} 실무 체크리스트",
            "body2_text": self._long_text(keyword, 850, 12),
            "body3_title": f"{keyword} 실행 로드맵",
            "body3_text": self._long_text(keyword, 850, 12),
            "conclusion": self._long_text(keyword, 340, 6)
            + "[PARA][FAQ]Q: 기간은?|A: 서류와 요건을 먼저 점검한 뒤 일정표를 확정합니다.[/FAQ]"
            + "[FAQ]Q: 핵심 리스크는?|A: 자본금, 기술인력, 서류 정합성 리스크를 사전진단합니다.[/FAQ]",
        }
        html_with_raw_tokens = (
            "background:#f8f9fb border-left:3px solid #003764 border:1px solid #e2e8f0 <ol href=\"#a\" "
            "Author Updated <h2 id='a'></h2><h2 id='b'></h2><h2 id='c'></h2> "
            "background:#001a33 tel: https://open.kakao.com/o/syWr1hIe "
            "margin-bottom:56px; margin-bottom:56px; margin-bottom:56px; "
            "<figure></figure> \"FAQPage\" \"@type\": \"Article\" [PARA]"
        )

        old_wp_url = mnakr.CONFIG.get("WP_URL")
        try:
            mnakr.CONFIG["WP_URL"] = "https://example.com/wp-json/wp/v2"
            wp = mnakr.WPEngine(verify_auth=False, allow_no_auth=True)
            with self.assertRaises(ValueError):
                wp._publish_preflight(
                    keyword=keyword,
                    content=content,
                    rendered_html=html_with_raw_tokens,
                    seo_title=f"{content['headline']} | seoulmna",
                    seo_desc=content["summary"][:150],
                    slug=content["english_slug"],
                    expect_images=True,
                )
        finally:
            mnakr.CONFIG["WP_URL"] = old_wp_url

    def test_content_checks_accept_english_steps_and_behavior_terms(self):
        keyword = "construction license transfer"
        long_en = ("checklist risk pre-check opportunity cost execution flow " * 120).strip()
        content = {
            "intro": (keyword + " " + long_en)[:500],
            "body1_text": long_en * 2,
            "body2_text": long_en * 2,
            "body3_text": long_en + " [PARA][LIST]Step 1: diagnose|Step 2: verify|Step 3: file[/LIST]",
            "conclusion": long_en[:400],
        }
        out = mnakr.PublicationQAAuditor()._content_checks(content)
        self.assertTrue(out["checks"]["behavioral_framework"])
        self.assertTrue(out["checks"]["action_steps"])

    def test_serp_snippet_garbled_detection(self):
        bad = mnakr._is_serp_snippet_garbled("??? ?? ??", "??? ???")
        self.assertTrue(bad.get("flagged"))

        good = mnakr._is_serp_snippet_garbled(
            "Construction license return guide",
            "Practical checklist for documents, timeline, and risk controls.",
        )
        self.assertFalse(good.get("flagged"))

    def test_startup_catchup_window(self):
        original_min = mnakr.CONFIG.get("STARTUP_CATCHUP_MIN_LOCAL_HOUR")
        original_max = mnakr.CONFIG.get("STARTUP_CATCHUP_MAX_LOCAL_HOUR")
        try:
            mnakr.CONFIG["STARTUP_CATCHUP_MIN_LOCAL_HOUR"] = 9
            mnakr.CONFIG["STARTUP_CATCHUP_MAX_LOCAL_HOUR"] = 22
            morning = datetime.now().astimezone().replace(hour=10, minute=0, second=0, microsecond=0)
            night = datetime.now().astimezone().replace(hour=1, minute=0, second=0, microsecond=0)
            self.assertTrue(mnakr._in_startup_catchup_window(morning))
            self.assertFalse(mnakr._in_startup_catchup_window(night))
        finally:
            mnakr.CONFIG["STARTUP_CATCHUP_MIN_LOCAL_HOUR"] = original_min
            mnakr.CONFIG["STARTUP_CATCHUP_MAX_LOCAL_HOUR"] = original_max

    def test_prev_day_publish_slot_conversion_weekday(self):
        old_enabled = mnakr.CONFIG.get("PUBLISH_PREV_DAY_ENABLED")
        old_time = mnakr.CONFIG.get("PUBLISH_PREV_DAY_TIME")
        try:
            mnakr.CONFIG["PUBLISH_PREV_DAY_ENABLED"] = True
            mnakr.CONFIG["PUBLISH_PREV_DAY_TIME"] = "21:00"
            out = mnakr._resolve_publish_slots([("tuesday", "08:30")])
            self.assertEqual(out, [("monday", "21:00")])
        finally:
            mnakr.CONFIG["PUBLISH_PREV_DAY_ENABLED"] = old_enabled
            mnakr.CONFIG["PUBLISH_PREV_DAY_TIME"] = old_time

    def test_prev_day_publish_slot_conversion_daily(self):
        old_enabled = mnakr.CONFIG.get("PUBLISH_PREV_DAY_ENABLED")
        old_time = mnakr.CONFIG.get("PUBLISH_PREV_DAY_TIME")
        try:
            mnakr.CONFIG["PUBLISH_PREV_DAY_ENABLED"] = True
            mnakr.CONFIG["PUBLISH_PREV_DAY_TIME"] = "21:00"
            out = mnakr._resolve_publish_slots([("daily", "09:00")])
            self.assertEqual(out, [("daily", "21:00")])
        finally:
            mnakr.CONFIG["PUBLISH_PREV_DAY_ENABLED"] = old_enabled
            mnakr.CONFIG["PUBLISH_PREV_DAY_TIME"] = old_time

    def test_scheduler_failed_job_not_marked_as_ran_today(self):
        with tempfile.TemporaryDirectory() as td:
            original_state = mnakr.CONFIG.get("SCHEDULER_STATE_FILE")
            mnakr.CONFIG["SCHEDULER_STATE_FILE"] = os.path.join(td, "scheduler_state.json")
            try:
                def _boom():
                    raise RuntimeError("boom")

                ok = mnakr._run_tracked_job("unit:test", _boom)
                self.assertFalse(ok)
                self.assertFalse(mnakr._job_ran_today("unit:test"))

                state = mnakr._load_scheduler_state()
                entry = state.get("last_runs", {}).get("unit:test", {})
                self.assertEqual(entry.get("status"), "failed")
            finally:
                mnakr.CONFIG["SCHEDULER_STATE_FILE"] = original_state

if __name__ == "__main__":
    unittest.main()






