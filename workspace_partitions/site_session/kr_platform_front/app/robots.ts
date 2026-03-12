import type { MetadataRoute } from "next";
import { siteBase } from "@/lib/json-ld";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/about", "/yangdo", "/permit", "/consult", "/knowledge", "/mna-market", "/terms", "/privacy"],
      disallow: ["/widget/", "/api/"],
    },
    sitemap: `${siteBase}/sitemap.xml`,
  };
}
