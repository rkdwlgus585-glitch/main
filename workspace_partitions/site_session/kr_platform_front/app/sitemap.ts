import type { MetadataRoute } from "next";
import { platformConfig } from "@/components/platform-config";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = platformConfig.platformFrontHost.replace(/\/$/, "");
  return ["", "/yangdo", "/permit"].map((path) => ({
    url: `${base}${path}`,
    lastModified: new Date("2026-03-07T00:00:00+09:00"),
    changeFrequency: path ? "weekly" : "daily",
    priority: path ? 0.8 : 1,
  }));
}
