import type { MetadataRoute } from "next";
import { siteBase } from "@/lib/json-ld";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/about", "/yangdo", "/permit", "/consult", "/partners", "/pricing", "/terms", "/privacy"],
      disallow: ["/widget/", "/api/", "/billing/", "/knowledge", "/mna-market"],
    },
    sitemap: `${siteBase}/sitemap.xml`,
  };
}
