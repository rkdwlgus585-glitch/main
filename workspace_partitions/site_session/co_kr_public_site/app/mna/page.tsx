import type { Metadata } from "next";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { LegacyPageDirectory } from "@/components/legacy-page-directory";
import { ListingBoard } from "@/components/listing-board";
import { siteConfig } from "@/components/site-config";
import { getAllListings } from "@/lib/listings";
import { getLegacyPagesByGroup, getListingDatasetStats } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";

export const revalidate = 3600;

export const metadata: Metadata = buildPageMetadata(
  "/mna",
  "양도양수 실시간 매물",
  "구글시트 원본과 공개 게시판 보존본을 합쳐 건설업 양도양수 매물을 업종과 지역 기준으로 빠르게 탐색할 수 있는 페이지입니다.",
);

type PageProps = {
  searchParams: Promise<{
    sector?: string;
    region?: string;
    q?: string;
    page?: string;
  }>;
};

export default async function MnaPage({ searchParams }: PageProps) {
  const filters = await searchParams;
  const listings = getAllListings();
  const listingStats = getListingDatasetStats();
  const importedPages = getLegacyPagesByGroup("mna-info");
  const itemListSchema = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "양도양수 실시간 매물",
    description: "건설업 양도양수 매물을 업종과 지역 기준으로 빠르게 탐색할 수 있는 목록 페이지입니다.",
    url: `${siteConfig.host}/mna`,
    mainEntity: {
      "@type": "ItemList",
      itemListElement: listings.slice(0, 100).map((item, index) => ({
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
        <p>
          구글시트 원본 {listingStats.sheetCount}건을 기준으로 최신 상태를 반영하고,
          공개 게시판 보존본은 별도로 유지했습니다. 업종, 지역, 키워드 기준으로 빠르게 좁히고 상세 페이지에서 회사개요와 실적표를 확인할 수 있습니다.
        </p>
      </section>
      <ListingBoard listings={listings} syncWithUrl initialFilters={filters} />
      <LegacyPageDirectory
        eyebrow="M&A Guide"
        title="양도양수 안내 페이지"
        description="매물 목록 외에 절차, 개요, 체크 포인트를 설명하는 가져온 안내 페이지도 함께 노출합니다."
        pages={importedPages}
      />
      <AiToolBridge variant="yangdo" />
    </div>
  );
}
