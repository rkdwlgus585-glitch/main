import type { MetadataRoute } from "next";
import { platformConfig } from "@/components/platform-config";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/yangdo", "/permit", "/terms", "/privacy"],
      disallow: ["/widget/", "/api/"],
    },
    sitemap: `${platformConfig.platformFrontHost.replace(/\/$/, "")}/sitemap.xml`,
  };
}
