import type { MetadataRoute } from "next";
import { boardConfig } from "@/lib/content-map";
import {
  getAllLegacyPages,
  getAllListings,
  getBoardPosts,
  getFaqPage,
  getLegacyPagePath,
  getLatestContentUpdatedAt,
} from "@/lib/legacy-content";
import { primaryMenu, siteConfig } from "@/components/site-config";

export default function sitemap(): MetadataRoute.Sitemap {
  const staticRoutes = ["", "/privacy", "/terms"];
  const menuRoutes = primaryMenu.map((item) => item.href);
  const listings = getAllListings();
  const listingRoutes = listings.map((item) => ({
    path: `/mna/${encodeURIComponent(item.id)}`,
    updatedAt: item.updatedAt,
  }));
  const notices = getBoardPosts("notice").map((post) => ({
    path: `${boardConfig.notice.path}/${encodeURIComponent(post.id)}`,
    updatedAt: post.updatedAt,
  }));
  const premiums = getBoardPosts("premium").map((post) => ({
    path: `${boardConfig.premium.path}/${encodeURIComponent(post.id)}`,
    updatedAt: post.updatedAt,
  }));
  const news = getBoardPosts("news").map((post) => ({
    path: `${boardConfig.news.path}/${encodeURIComponent(post.id)}`,
    updatedAt: post.updatedAt,
  }));
  const pageRoutes = getAllLegacyPages().map((page) => ({
    path: getLegacyPagePath(page.slug),
    updatedAt: page.updatedAt,
  }));

  const routeEntries = [
    ...staticRoutes.map((path) => ({ path, updatedAt: getLatestContentUpdatedAt() })),
    ...menuRoutes.map((path) => ({ path, updatedAt: getLatestContentUpdatedAt() })),
    { path: boardConfig.notice.path, updatedAt: getBoardPosts("notice")[0]?.updatedAt ?? getLatestContentUpdatedAt() },
    { path: boardConfig.premium.path, updatedAt: getBoardPosts("premium")[0]?.updatedAt ?? getLatestContentUpdatedAt() },
    { path: boardConfig.news.path, updatedAt: getBoardPosts("news")[0]?.updatedAt ?? getLatestContentUpdatedAt() },
    { path: "/tl_faq", updatedAt: getFaqPage().updatedAt },
    ...listingRoutes,
    ...notices,
    ...premiums,
    ...news,
    ...pageRoutes,
  ];

  return routeEntries.map(({ path, updatedAt }) => {
    const isHome = path === "";
    const isDetail = path.includes("/mna/") || path.includes("/notice/") || path.includes("/premium/") || path.includes("/news/");

    return {
      url: `${siteConfig.host}${path}`,
      lastModified: new Date(updatedAt),
      changeFrequency: isHome || isDetail ? "weekly" : "monthly",
      priority: isHome ? 1 : isDetail ? 0.8 : 0.7,
    };
  });
}
