import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AnalyticsScripts } from "@/components/analytics-scripts";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { siteConfig } from "@/components/site-config";
import { StickyContactBar } from "@/components/sticky-contact-bar";

export const metadata: Metadata = {
  title: `${siteConfig.brandName} | ${siteConfig.brandTagline}`,
  description:
    "건설업 양도양수, 건설업등록, 법인설립, 분할합병, 건설실무, 고객센터를 운영하는 독립 퍼블릭 사이트 골격입니다.",
  metadataBase: new URL(siteConfig.host),
  robots: {
    index: siteConfig.allowIndexing,
    follow: siteConfig.allowIndexing,
    nocache: !siteConfig.allowIndexing,
  },
  openGraph: {
    title: `${siteConfig.brandName} | ${siteConfig.brandTagline}`,
    description:
      "AI 시스템과 분리된 건설업 상담형 퍼블릭 사이트. 매물 탐색과 실무 안내 중심 구조를 제공합니다.",
    url: siteConfig.host,
    siteName: siteConfig.brandName,
    type: "website",
    locale: "ko_KR",
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
    title: `${siteConfig.brandName} | ${siteConfig.brandTagline}`,
    description:
      "건설업 양도양수와 등록 실무를 안내하는 독립 퍼블릭 사이트입니다.",
    images: [`${siteConfig.host}/opengraph-image`],
  },
  keywords: [
    "건설업 양도양수",
    "건설업등록",
    "법인설립",
    "분할합병",
    "건설실무",
    "건설업 상담",
  ],
};

export const viewport: Viewport = {
  themeColor: "#07355f",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const orgSchema = {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    name: siteConfig.companyName,
    url: siteConfig.host,
    telephone: siteConfig.phone,
    email: siteConfig.email,
    address: {
      "@type": "PostalAddress",
      streetAddress: siteConfig.address,
      addressCountry: "KR",
    },
    identifier: siteConfig.businessNumber,
    founder: siteConfig.representativeName,
  };

  return (
    <html lang="ko">
      <body>
        <AnalyticsScripts />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(orgSchema) }}
        />
        <a className="skip-link" href="#main-content">
          본문 바로가기
        </a>
        <SiteHeader />
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
        <StickyContactBar />
        <SiteFooter />
      </body>
    </html>
  );
}
