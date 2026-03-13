import type { MetadataRoute } from "next";
import { siteBase } from "@/lib/json-ld";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();

  return [
    { url: siteBase, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${siteBase}/about`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${siteBase}/yangdo`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${siteBase}/permit`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${siteBase}/consult`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: `${siteBase}/knowledge`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${siteBase}/mna-market`, lastModified: now, changeFrequency: "daily", priority: 0.8 },
    { url: `${siteBase}/partners`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: `${siteBase}/terms`, lastModified: now, changeFrequency: "monthly", priority: 0.3 },
    { url: `${siteBase}/privacy`, lastModified: now, changeFrequency: "monthly", priority: 0.3 },
  ];
}
