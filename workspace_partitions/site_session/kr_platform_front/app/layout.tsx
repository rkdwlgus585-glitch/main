import type { Metadata, Viewport } from "next";
import "./globals.css";
import { platformConfig } from "@/components/platform-config";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

const siteTitle = "서울건설정보 | 건설업 AI 양도가 산정 · 건설업등록 전문 플랫폼";
const siteDescription =
  "건설업 면허 양도가격을 AI가 무료로 산정합니다. 191개 업종 등록기준 사전검토와 신규 취득 비용 계산까지 원스톱으로 제공하는 건설업 전문 플랫폼.";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export const metadata: Metadata = {
  title: siteTitle,
  description: siteDescription,
  metadataBase: new URL(platformConfig.platformFrontHost),
  alternates: { canonical: "/" },
  openGraph: {
    title: "서울건설정보 | 건설업 AI 전문 플랫폼",
    description:
      "건설업 면허 양도가 산정부터 신규 등록 비용 계산까지, 데이터 기반 AI 분석을 무료로 제공합니다.",
    url: platformConfig.platformFrontHost,
    siteName: "서울건설정보",
    type: "website",
    locale: "ko_KR",
  },
  twitter: {
    card: "summary_large_image",
    title: "서울건설정보 | 건설업 AI 전문 플랫폼",
    description: siteDescription,
  },
  keywords: [
    "건설업 면허",
    "양도가 산정",
    "건설업 양도양수",
    "인허가 사전검토",
    "신규 등록 비용",
    "건설업 등록기준",
    "건설업 AI",
    "면허 가격",
    "서울건설정보",
  ],
  /* google-site-verification: add token when Search Console is verified */
};

function JsonLd() {
  const schema = {
    "@context": "https://schema.org",
    "@type": ["Organization", "LocalBusiness"],
    name: "서울건설정보",
    url: platformConfig.platformFrontHost,
    telephone: platformConfig.contactPhone,
    email: platformConfig.contactEmail,
    address: {
      "@type": "PostalAddress",
      addressLocality: "서울특별시",
      addressRegion: "서울",
      addressCountry: "KR",
    },
    geo: { "@type": "GeoCoordinates", latitude: 37.5665, longitude: 126.978 },
    description: siteDescription,
    knowsAbout: ["건설업 양도양수", "건설업 면허", "인허가 사전검토", "건설업 등록기준"],
    priceRange: "무료",
  };
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        {/* Pretendard Variable — Korean optimized sans-serif (preconnect + preload) */}
        <link rel="dns-prefetch" href="https://cdn.jsdelivr.net" />
        <link rel="preconnect" href="https://cdn.jsdelivr.net" crossOrigin="anonymous" />
        <link
          rel="preload"
          as="style"
          crossOrigin="anonymous"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
        <link
          rel="stylesheet"
          crossOrigin="anonymous"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
        {/* Noto Sans KR — fallback */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap"
        />
      </head>
      <body>
        <JsonLd />
        <a className="skip-link" href="#main">
          본문 바로가기
        </a>
        <SiteHeader />
        <div id="main">{children}</div>
        <SiteFooter />
      </body>
    </html>
  );
}
