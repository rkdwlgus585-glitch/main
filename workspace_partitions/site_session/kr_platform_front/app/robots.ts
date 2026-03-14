import type { MetadataRoute } from "next";
import { siteBase } from "@/lib/json-ld";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/about", "/yangdo", "/permit", "/consult", "/terms", "/privacy"],
      disallow: ["/widget/", "/api/", "/knowledge", "/mna-market", "/partners"],
    },
    sitemap: `${siteBase}/sitemap.xml`,
  };
}
