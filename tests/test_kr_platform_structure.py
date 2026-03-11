"""Structural integrity tests for the seoulmna.kr Next.js platform.

Verifies that all expected route files, error boundaries, loading states,
and shared utilities exist.  Acts as a regression guard against accidental
file deletion during refactoring.
"""
from __future__ import annotations

import unittest
from pathlib import Path

_KR = Path(__file__).resolve().parent.parent / "workspace_partitions" / "site_session" / "kr_platform_front"


class RouteStructureTest(unittest.TestCase):
    """Every main route must have page.tsx."""

    _EXPECTED_PAGES = [
        "app/page.tsx",
        "app/yangdo/page.tsx",
        "app/permit/page.tsx",
        "app/consult/page.tsx",
        "app/knowledge/page.tsx",
        "app/mna-market/page.tsx",
        "app/privacy/page.tsx",
        "app/terms/page.tsx",
        "app/widget/yangdo/page.tsx",
        "app/widget/permit/page.tsx",
    ]

    def test_all_expected_pages_exist(self) -> None:
        for rel in self._EXPECTED_PAGES:
            with self.subTest(page=rel):
                self.assertTrue((_KR / rel).is_file(), f"Missing: {rel}")


class ErrorBoundaryTest(unittest.TestCase):
    """Error boundaries must exist for all data/widget routes."""

    _EXPECTED_ERROR_BOUNDARIES = [
        "app/error.tsx",              # root fallback
        "app/yangdo/error.tsx",       # yangdo landing
        "app/permit/error.tsx",       # permit landing
        "app/consult/error.tsx",      # consult page
        "app/knowledge/error.tsx",    # knowledge page
        "app/mna-market/error.tsx",   # mna-market page
        "app/widget/error.tsx",       # widget iframe (no site chrome)
    ]

    def test_all_error_boundaries_exist(self) -> None:
        for rel in self._EXPECTED_ERROR_BOUNDARIES:
            with self.subTest(boundary=rel):
                self.assertTrue((_KR / rel).is_file(), f"Missing: {rel}")

    def test_widget_error_has_no_link_import(self) -> None:
        """Widget error boundary must NOT import Link (runs inside iframe)."""
        content = (_KR / "app/widget/error.tsx").read_text(encoding="utf-8")
        self.assertNotIn("import Link", content)

    def test_page_error_boundaries_use_client(self) -> None:
        """All error boundaries must be client components ('use client')."""
        for rel in self._EXPECTED_ERROR_BOUNDARIES:
            with self.subTest(boundary=rel):
                content = (_KR / rel).read_text(encoding="utf-8")
                self.assertIn('"use client"', content)


class LoadingStateTest(unittest.TestCase):
    """Main data routes must have loading.tsx for Suspense boundaries."""

    _EXPECTED_LOADING = [
        "app/loading.tsx",            # root fallback
        "app/yangdo/loading.tsx",
        "app/permit/loading.tsx",
        "app/consult/loading.tsx",
        "app/knowledge/loading.tsx",
        "app/mna-market/loading.tsx",
    ]

    def test_all_loading_states_exist(self) -> None:
        for rel in self._EXPECTED_LOADING:
            with self.subTest(loading=rel):
                self.assertTrue((_KR / rel).is_file(), f"Missing: {rel}")

    def test_loading_states_have_role_status(self) -> None:
        """Loading components should use role='status' for screen readers."""
        for rel in self._EXPECTED_LOADING:
            with self.subTest(loading=rel):
                content = (_KR / rel).read_text(encoding="utf-8")
                self.assertIn('role="status"', content)


class SharedUtilitiesTest(unittest.TestCase):
    """Shared libraries and configs must exist."""

    _EXPECTED_FILES = [
        "lib/json-ld.ts",
        "lib/og-font.ts",
        "lib/widget-message-protocol.ts",
        "components/platform-config.ts",
        "components/widget-frame.tsx",
        "components/site-header.tsx",
        "components/site-footer.tsx",
        "components/home-hero.tsx",
        "middleware.ts",
        "app/layout.tsx",
        "app/not-found.tsx",
        "app/robots.ts",
        "app/sitemap.ts",
        "app/manifest.ts",
    ]

    def test_all_shared_utilities_exist(self) -> None:
        for rel in self._EXPECTED_FILES:
            with self.subTest(file=rel):
                self.assertTrue((_KR / rel).is_file(), f"Missing: {rel}")


class MetadataExportTest(unittest.TestCase):
    """All page routes (except widget) must export metadata for SEO."""

    _PAGES_WITH_METADATA = [
        "app/yangdo/page.tsx",
        "app/permit/page.tsx",
        "app/consult/page.tsx",
        "app/knowledge/page.tsx",
        "app/mna-market/page.tsx",
        "app/privacy/page.tsx",
        "app/terms/page.tsx",
    ]

    def test_pages_export_metadata(self) -> None:
        for rel in self._PAGES_WITH_METADATA:
            with self.subTest(page=rel):
                content = (_KR / rel).read_text(encoding="utf-8")
                self.assertIn("export const metadata", content)


if __name__ == "__main__":
    unittest.main()
