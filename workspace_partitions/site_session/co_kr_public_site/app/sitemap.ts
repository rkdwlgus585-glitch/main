import type { MetadataRoute } from "next";
import { notices } from "@/components/sample-data";
import { primaryMenu, siteConfig } from "@/components/site-config";
import { getAllListings } from "@/lib/listings";

export default function sitemap(): MetadataRoute.Sitemap {
  const staticRoutes = ["", "/privacy", "/terms"];
  const menuRoutes = primaryMenu.map((item) => item.href);
  const listings = getAllListings();
  const listingRoutes = listings.map((item) => `/mna/${encodeURIComponent(item.id)}`);
  const listingModifiedMap = new Map(
    listings.map((item) => [`/mna/${encodeURIComponent(item.id)}`, new Date(item.updatedAt)]),
  );
  const latestNoticeDate = notices.reduce((latest, notice) => (
    notice.date > latest ? notice.date : latest
  ), notices[0]?.date ?? "2026-03-10");
  const staticLastModified = new Date(`${latestNoticeDate}T00:00:00+09:00`);

  return [...staticRoutes, ...menuRoutes, ...listingRoutes].map((path) => {
    const isHome = path === "";
    const isListingDetail = path.startsWith("/mna/");

    return {
      url: `${siteConfig.host}${path}`,
      lastModified: listingModifiedMap.get(path) ?? staticLastModified,
      changeFrequency: isHome || isListingDetail ? "weekly" : "monthly",
      priority: isHome ? 1 : isListingDetail ? 0.8 : 0.7,
    };
  });
}
