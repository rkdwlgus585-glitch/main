import type { MetadataRoute } from "next";
import { siteConfig } from "@/components/site-config";

export default function robots(): MetadataRoute.Robots {
  if (!siteConfig.allowIndexing) {
    return {
      rules: {
        userAgent: "*",
        disallow: "/",
      },
    };
  }

  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/"],
      },
    ],
    sitemap: `${siteConfig.host}/sitemap.xml`,
    host: siteConfig.host,
  };
}
