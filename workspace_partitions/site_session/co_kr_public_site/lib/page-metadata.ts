import type { Metadata } from "next";
import { siteConfig } from "@/components/site-config";

export function buildPageMetadata(
  path: string,
  title: string,
  description: string,
  options?: {
    indexable?: boolean;
  },
): Metadata {
  const canonicalUrl = `${siteConfig.host}${path}`;
  const allowIndex = siteConfig.allowIndexing && options?.indexable !== false;

  return {
    title: `${title} | ${siteConfig.brandName}`,
    description,
    alternates: {
      canonical: canonicalUrl,
    },
    robots: {
      index: allowIndex,
      follow: allowIndex,
      nocache: !allowIndex,
    },
    openGraph: {
      title: `${title} | ${siteConfig.brandName}`,
      description,
      url: canonicalUrl,
      siteName: siteConfig.brandName,
      locale: "ko_KR",
      type: "website",
      images: [
        {
          url: `${siteConfig.host}/opengraph-image`,
          width: 1200,
          height: 630,
          alt: `${siteConfig.brandName} 대표 이미지`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} | ${siteConfig.brandName}`,
      description,
      images: [`${siteConfig.host}/opengraph-image`],
    },
  };
}
