import { ConsultationCTA } from "@/components/consultation-cta";
import { HomeHero } from "@/components/home-hero";
import { HomeMarketPreview } from "@/components/home-market-preview";
import { HomeOperations } from "@/components/home-operations";
import { HomeProcess } from "@/components/home-process";
import { HomeShortcuts } from "@/components/home-shortcuts";
import { siteBase } from "@/lib/json-ld";
import { PlatformStatus } from "@/components/platform-status";

/*
 * NOTE: JSON-LD uses dangerouslySetInnerHTML which is safe here because
 * all data comes from compile-time string literals — no user input is
 * interpolated into the schema objects. This is the standard Next.js
 * pattern for structured data (see: next.js docs on JSON-LD).
 */
function HomeJsonLd() {
  const websiteSchema = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "서울건설정보",
    url: siteBase,
    description:
      "건설업 면허 양도가격 AI 산정, 191개 업종 등록기준 사전검토, 실시간 매물 — 건설업 전문 플랫폼",
    /* SearchAction은 실제 검색 기능 구현 후 추가 예정 */
  };
  const navItems = [
    { name: "실시간 매물", path: "/mna-market" },
    { name: "건설업등록", path: "/permit" },
    { name: "양도가 산정", path: "/yangdo" },
    { name: "건설실무", path: "/knowledge" },
    { name: "고객센터", path: "/consult" },
  ];
  const navSchema = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    itemListElement: navItems.map((item, i) => ({
      "@type": "SiteNavigationElement",
      position: i + 1,
      name: item.name,
      url: `${siteBase}${item.path}`,
    })),
  };
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(navSchema) }}
      />
    </>
  );
}

export default function HomePage() {
  return (
    <main id="main" className="page-shell page-shell--home">
      <HomeJsonLd />
      <PlatformStatus />
      <HomeHero />
      <HomeShortcuts />
      <HomeMarketPreview />
      <HomeOperations />
      <HomeProcess />
      <ConsultationCTA />
    </main>
  );
}
