import type { MetadataRoute } from "next";
import { platformConfig } from "@/components/platform-config";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = platformConfig.platformFrontHost.replace(/\/$/, "");
  const now = new Date("2026-03-10T00:00:00+09:00");

  return [
    { url: base, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${base}/yangdo`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${base}/permit`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${base}/consult`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: `${base}/knowledge`, lastModified: now, changeFrequency: "weekly", priority: 0.6 },
    { url: `${base}/mna-market`, lastModified: now, changeFrequency: "daily", priority: 0.8 },
    { url: `${base}/terms`, lastModified: now, changeFrequency: "monthly", priority: 0.3 },
    { url: `${base}/privacy`, lastModified: now, changeFrequency: "monthly", priority: 0.3 },
  ];
}
