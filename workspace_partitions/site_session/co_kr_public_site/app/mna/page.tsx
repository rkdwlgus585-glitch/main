import type { Metadata } from "next";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { ListingBoard } from "@/components/listing-board";
import { siteConfig } from "@/components/site-config";
import { getAllListings } from "@/lib/listings";
import { buildPageMetadata } from "@/lib/page-metadata";

export const revalidate = 3600;

export const metadata: Metadata = buildPageMetadata(
  "/mna",
  "양도양수 실시간 매물",
  "건설업 양도양수 매물을 업종과 지역 기준으로 빠르게 검토할 수 있는 목록 페이지입니다.",
);

type PageProps = {
  searchParams: Promise<{
    sector?: string;
    region?: string;
    q?: string;
  }>;
};

export default async function MnaPage({ searchParams }: PageProps) {
  const filters = await searchParams;
  const listings = getAllListings();
  const itemListSchema = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "양도양수 실시간 매물",
    description: "건설업 양도양수 매물을 업종과 지역 기준으로 빠르게 검토할 수 있는 목록 페이지입니다.",
    url: `${siteConfig.host}/mna`,
    mainEntity: {
      "@type": "ItemList",
      itemListElement: listings.map((item, index) => ({
        "@type": "ListItem",
        position: index + 1,
        url: `${siteConfig.host}/mna/${encodeURIComponent(item.id)}`,
        name: item.title,
      })),
    },
  };

  return (
    <div className="page-shell page-shell--inner">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(itemListSchema) }}
      />
      <Breadcrumbs items={[{ href: "/", label: "홈" }, { href: "/mna", label: "양도양수" }]} />
      <section className="inner-hero">
        <p className="eyebrow">Live Listings</p>
        <h1>양도양수 실시간 매물</h1>
        <p>seoulmna.co.kr 역할을 대체할 독립 사이트용 매물 목록 골격입니다. 실제 데이터는 이후 CMS 또는 DB로 연결하면 됩니다.</p>
      </section>
      <ListingBoard syncWithUrl initialFilters={filters} />
      <AiToolBridge variant="yangdo" />
    </div>
  );
}
