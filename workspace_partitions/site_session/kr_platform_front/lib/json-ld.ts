/**
 * Shared JSON-LD schema builders for structured data.
 *
 * All helpers return plain objects — callers serialize them with
 * JSON.stringify and inject via standard Next.js JSON-LD pattern.
 *
 * SECURITY: Data is compile-time string literals only; no user input
 * is interpolated. This is the standard Next.js pattern for structured
 * data and is safe by construction.
 */

import { platformConfig } from "@/components/platform-config";

const base = platformConfig.platformFrontHost.replace(/\/$/, "");

/**
 * BreadcrumbList schema — used by every sub-page for Google rich results.
 *
 * @param name  Display name for the current page (e.g. "AI 양도가 산정")
 * @param path  URL path without leading origin (e.g. "/yangdo")
 */
export function breadcrumbSchema(name: string, path: string) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "홈", item: base },
      {
        "@type": "ListItem",
        position: 2,
        name,
        item: `${base}${path}`,
      },
    ],
  };
}
