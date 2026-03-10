"""Comprehensive tests for maemul.py — 매물 수집기 extraction & display logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from maemul import (
    BASE_URL,
    LIST_URL,
    build_display_text,
    extract_detail_title,
    extract_listing_ids,
    extract_listing_summary,
    fetch_page,
    generate_html,
)


# ────────────────────────────────────────────────
# Helper: create BeautifulSoup from HTML
# ────────────────────────────────────────────────

def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# ────────────────────────────────────────────────
# extract_listing_ids
# ────────────────────────────────────────────────


class TestExtractListingIds:
    def test_basic_extraction(self) -> None:
        html = '<a href="/mna/1234">매물1</a><a href="/mna/5678">매물2</a>'
        assert extract_listing_ids(_soup(html)) == [1234, 5678]

    def test_deduplication(self) -> None:
        html = '<a href="/mna/100">A</a><a href="/mna/100">B</a><a href="/mna/200">C</a>'
        assert extract_listing_ids(_soup(html)) == [100, 200]

    def test_preserves_order(self) -> None:
        html = '<a href="/mna/3">C</a><a href="/mna/1">A</a><a href="/mna/2">B</a>'
        assert extract_listing_ids(_soup(html)) == [3, 1, 2]

    def test_no_mna_links(self) -> None:
        html = '<a href="/other/123">Other</a><a href="/">Home</a>'
        assert extract_listing_ids(_soup(html)) == []

    def test_empty_soup(self) -> None:
        assert extract_listing_ids(_soup("")) == []

    def test_mixed_links(self) -> None:
        html = '<a href="/mna/10">OK</a><a href="/about">skip</a><a href="/mna/20">OK2</a>'
        result = extract_listing_ids(_soup(html))
        assert result == [10, 20]

    def test_nested_links(self) -> None:
        html = '<div><ul><li><a href="/mna/42">Deep</a></li></ul></div>'
        assert extract_listing_ids(_soup(html)) == [42]

    def test_href_with_extra_path(self) -> None:
        html = '<a href="/mna/999/detail">With extra</a>'
        assert extract_listing_ids(_soup(html)) == [999]


# ────────────────────────────────────────────────
# extract_listing_summary
# ────────────────────────────────────────────────


class TestExtractListingSummary:
    def _table_html(self, rows: list[list[str]], with_mna_link: bool = True) -> str:
        """Build a table HTML from rows. First cell should be numeric ID."""
        row_strs = []
        for cells in rows:
            tds = []
            for i, cell in enumerate(cells):
                if i == 0 and with_mna_link and cell.isdigit():
                    tds.append(f'<td><a href="/mna/{cell}">{cell}</a></td>')
                else:
                    tds.append(f"<td>{cell}</td>")
            row_strs.append(f"<tr>{''.join(tds)}</tr>")
        return f"<table>{''.join(row_strs)}</table>"

    def test_basic_extraction(self) -> None:
        # ID, 상태, 8 filler cells, last 3: 출자금, 법인+양도가, 지역
        row = ["1234", "진행", "a", "b", "c", "d", "e", "f", "3좌", "법인회사 2억", "서울"]
        html = self._table_html([row])
        result = extract_listing_summary(_soup(html))
        assert 1234 in result
        assert result[1234]["상태"] == "진행"
        assert "출자금" in result[1234]
        assert "법인_양도가" in result[1234]
        assert result[1234]["지역"] == "서울"

    def test_no_table(self) -> None:
        assert extract_listing_summary(_soup("<p>No table</p>")) == {}

    def test_row_too_short(self) -> None:
        html = "<table><tr><td>1234</td><td>short</td></tr></table>"
        # Need at least 10 cells + mna link
        result = extract_listing_summary(_soup(html))
        assert result == {}

    def test_non_numeric_first_cell_skipped(self) -> None:
        row = ["번호", "상태", "a", "b", "c", "d", "e", "f", "g", "h", "i"]
        html = self._table_html([row], with_mna_link=False)
        result = extract_listing_summary(_soup(html))
        assert result == {}

    def test_multiple_rows(self) -> None:
        rows = [
            ["1001", "진행", "a", "b", "c", "d", "e", "f", "5좌", "3억", "서울"],
            ["1002", "완료", "a", "b", "c", "d", "e", "f", "2좌", "1억", "경기"],
        ]
        html = self._table_html(rows)
        result = extract_listing_summary(_soup(html))
        assert 1001 in result
        assert 1002 in result

    def test_region_detection(self) -> None:
        for region in ("서울", "지방", "경기", "인천", "세종", "수도권"):
            row = ["9999", "진행", "a", "b", "c", "d", "e", "f", "g", "h", region]
            html = self._table_html([row])
            result = extract_listing_summary(_soup(html))
            if 9999 in result:
                assert result[9999].get("지역") == region


# ────────────────────────────────────────────────
# build_display_text
# ────────────────────────────────────────────────


class TestBuildDisplayText:
    def test_with_title(self) -> None:
        result = build_display_text(100, "전기공사업 매물", {})
        assert result == "[전기공사업 매물]"

    def test_title_truncation(self) -> None:
        long_title = "A" * 80
        result = build_display_text(100, long_title, {})
        assert len(result) <= 72  # [67chars... + "]"
        assert result.endswith("...]")

    def test_no_title_basic(self) -> None:
        result = build_display_text(42, "", {})
        assert result == "[매물 42]"

    def test_no_title_with_summary(self) -> None:
        summary = {"법인_양도가": "법인회사 3억", "지역": "서울"}
        result = build_display_text(42, "", summary)
        assert "매물 42" in result
        assert "법인회사 3억" in result
        assert "서울" in result

    def test_no_title_only_region(self) -> None:
        summary = {"지역": "경기"}
        result = build_display_text(99, "", summary)
        assert "매물 99" in result
        assert "경기" in result

    def test_no_title_only_price(self) -> None:
        summary = {"법인_양도가": "5억"}
        result = build_display_text(77, "", summary)
        assert "5억" in result

    def test_title_exactly_70_chars(self) -> None:
        title = "X" * 70
        result = build_display_text(1, title, {})
        assert "..." not in result  # 70 is NOT > 70, no truncation

    def test_title_exactly_69_chars(self) -> None:
        title = "X" * 69
        result = build_display_text(1, title, {})
        assert "..." not in result  # 69 <= 70

    def test_empty_summary(self) -> None:
        result = build_display_text(1, "", {})
        assert result == "[매물 1]"


# ────────────────────────────────────────────────
# generate_html
# ────────────────────────────────────────────────


class TestGenerateHtml:
    def test_basic(self) -> None:
        items = [{"id": 100, "display": "[전기공사업]"}]
        result = generate_html(items)
        assert len(result) == 1
        assert "<li" in result[0]
        assert f"{LIST_URL}/100" in result[0]
        assert "[전기공사업]" in result[0]

    def test_multiple_items(self) -> None:
        items = [
            {"id": 1, "display": "[매물 1]"},
            {"id": 2, "display": "[매물 2]"},
            {"id": 3, "display": "[매물 3]"},
        ]
        result = generate_html(items)
        assert len(result) == 3

    def test_empty_items(self) -> None:
        assert generate_html([]) == []

    def test_target_blank(self) -> None:
        items = [{"id": 1, "display": "[Test]"}]
        result = generate_html(items)
        assert 'target="_blank"' in result[0]

    def test_url_format(self) -> None:
        items = [{"id": 12345, "display": "[Test]"}]
        result = generate_html(items)
        assert f"{LIST_URL}/12345" in result[0]

    def test_html_structure(self) -> None:
        items = [{"id": 1, "display": "[Test]"}]
        result = generate_html(items)
        assert result[0].startswith("<li")
        assert result[0].endswith("</li>")
        assert "<a href=" in result[0]


# ────────────────────────────────────────────────
# fetch_page (with mocking)
# ────────────────────────────────────────────────


class TestFetchPage:
    @patch("maemul.requests.get")
    def test_success(self, mock_get) -> None:
        mock_resp = MagicMock()
        mock_resp.text = "<html><body>OK</body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_page("https://example.com")
        assert result is not None
        assert result.find("body").get_text() == "OK"

    @patch("maemul.requests.get")
    def test_failure_returns_none(self, mock_get) -> None:
        import requests as req_lib
        mock_get.side_effect = req_lib.RequestException("Network error")
        result = fetch_page("https://bad.url")
        assert result is None

    @patch("maemul.requests.get")
    def test_retry_count(self, mock_get) -> None:
        import requests as req_lib
        mock_get.side_effect = req_lib.RequestException("Error")
        with patch("maemul.time.sleep"):
            fetch_page("https://retry.test")
        # RETRY_COUNT is 3
        assert mock_get.call_count == 3

    @patch("maemul.requests.get")
    def test_success_on_retry(self, mock_get) -> None:
        import requests as req_lib
        mock_resp = MagicMock()
        mock_resp.text = "<html>OK</html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.side_effect = [
            req_lib.RequestException("First fail"),
            mock_resp,
        ]
        with patch("maemul.time.sleep"):
            result = fetch_page("https://retry.test")
        assert result is not None


# ────────────────────────────────────────────────
# extract_detail_title (with mocking)
# ────────────────────────────────────────────────


class TestExtractDetailTitle:
    @patch("maemul.fetch_page")
    def test_fetch_failure(self, mock_fetch) -> None:
        mock_fetch.return_value = None
        assert extract_detail_title(999) == ""

    @patch("maemul.fetch_page")
    def test_inline_h1_found(self, mock_fetch) -> None:
        html = '<div><h1 style="font-size:24px">전기공사업 1종 양도 매물입니다</h1></div>'
        mock_fetch.return_value = _soup(html)
        result = extract_detail_title(100)
        assert "전기공사업" in result

    @patch("maemul.fetch_page")
    def test_skip_sub_title_class(self, mock_fetch) -> None:
        html = '''
        <div class="sub_title"><h1>건설업 양도양수 실시간 매물</h1></div>
        <h1 style="font-size:24px">진짜 제목 입니다 이것은 실제 매물 제목</h1>
        '''
        mock_fetch.return_value = _soup(html)
        result = extract_detail_title(100)
        assert "진짜 제목" in result

    @patch("maemul.fetch_page")
    def test_skip_common_header_text(self, mock_fetch) -> None:
        html = '<h1>건설업 양도양수 실시간 매물 목록</h1><h1>전기공사업 1종 양도 매물 실제 제목입니다</h1>'
        mock_fetch.return_value = _soup(html)
        result = extract_detail_title(100)
        assert "전기공사업" in result

    @patch("maemul.fetch_page")
    def test_short_h1_skipped(self, mock_fetch) -> None:
        html = '<h1>짧은</h1><h1>실제 매물 제목은 이것이며 충분히 길어야 합니다</h1>'
        mock_fetch.return_value = _soup(html)
        result = extract_detail_title(100)
        assert "실제 매물 제목" in result

    @patch("maemul.fetch_page")
    def test_fallback_to_page_title(self, mock_fetch) -> None:
        html = '<html><head><title>진행 > 매물 상세</title></head><body></body></html>'
        mock_fetch.return_value = _soup(html)
        result = extract_detail_title(555)
        assert "555" in result
        assert "진행" in result

    @patch("maemul.fetch_page")
    def test_no_h1_no_title(self, mock_fetch) -> None:
        mock_fetch.return_value = _soup("<div>No heading</div>")
        assert extract_detail_title(100) == ""


# ────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────


class TestConstants:
    def test_base_url(self) -> None:
        assert BASE_URL == "https://seoulmna.co.kr"

    def test_list_url(self) -> None:
        assert LIST_URL == f"{BASE_URL}/mna"
