import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { ContactLink } from "@/components/contact-link";
import { getAdjacentListings, getListingById, getListingIds } from "@/lib/listings";
import { siteConfig } from "@/components/site-config";
import { buildPageMetadata } from "@/lib/page-metadata";

type PageProps = {
  params: Promise<{
    id: string;
  }>;
};

export const revalidate = 3600;

export function generateStaticParams() {
  return getListingIds().map((id) => ({ id }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const listing = getListingById(id);

  if (!listing) {
    return {};
  }

  const metadata = buildPageMetadata(
    `/mna/${encodeURIComponent(listing.id)}`,
    `${listing.id} | ${listing.title}`,
    listing.overview,
  );

  return {
    ...metadata,
    openGraph: {
      ...metadata.openGraph,
      url: `${siteConfig.host}/mna/${encodeURIComponent(listing.id)}`,
      type: "website",
      images: [
        {
          url: `${siteConfig.host}/opengraph-image`,
          width: 1200,
          height: 630,
          alt: `${listing.id} ${listing.title}`,
        },
      ],
    },
    twitter: {
      ...metadata.twitter,
      images: [`${siteConfig.host}/opengraph-image`],
    },
  };
}

export default async function ListingDetailPage({ params }: PageProps) {
  const { id } = await params;
  const listing = getListingById(id);

  if (!listing) {
    notFound();
  }

  if (decodeURIComponent(id) !== listing.id) {
    permanentRedirect(`/mna/${encodeURIComponent(listing.id)}`);
  }

  const { previous, next } = getAdjacentListings(listing.id);
  const availabilityMap = {
    가능: "https://schema.org/InStock",
    검토중: "https://schema.org/LimitedAvailability",
    협의중: "https://schema.org/PreOrder",
  } as const;
  const listingSchema = {
    "@context": "https://schema.org",
    "@type": "ItemPage",
    name: `${listing.id} ${listing.title}`,
    description: listing.overview,
    url: `${siteConfig.host}/mna/${encodeURIComponent(listing.id)}`,
    dateModified: listing.updatedAt,
    mainEntity: {
      "@type": "Service",
      name: listing.title,
      description: listing.overview,
      serviceType: `건설업 ${listing.sector} 양도양수`,
      identifier: listing.id,
      areaServed: listing.region,
      provider: {
        "@type": "LocalBusiness",
        name: siteConfig.companyName,
        url: siteConfig.host,
        telephone: siteConfig.phone,
      },
      offers: {
        "@type": "Offer",
        availability: availabilityMap[listing.status],
        url: `${siteConfig.host}/mna/${encodeURIComponent(listing.id)}`,
        seller: {
          "@type": "LocalBusiness",
          name: siteConfig.companyName,
        },
      },
    },
  };

  return (
    <div className="page-shell page-shell--inner">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(listingSchema) }}
      />
      <Breadcrumbs
        items={[
          { href: "/", label: "홈" },
          { href: "/mna", label: "양도양수" },
          { href: `/mna/${encodeURIComponent(listing.id)}`, label: listing.id },
        ]}
      />

      <section className="listing-detail-hero">
        <div className="listing-detail-copy">
          <p className="eyebrow">Listing Detail</p>
          <h1>{listing.title}</h1>
          <p>{listing.overview}</p>

          <div className="detail-pill-row" aria-label="매물 핵심 정보">
            <span className="detail-pill">{listing.id}</span>
            <span className="detail-pill">{listing.status}</span>
            <span className="detail-pill">{listing.region}</span>
            <span className="detail-pill">{listing.sector}</span>
            <span className="detail-pill">업데이트 {listing.updatedAt.slice(0, 10)}</span>
          </div>
        </div>

        <aside className="detail-side-cta">
          <strong>{listing.price}</strong>
          <p>{listing.headline}</p>
          <div className="detail-summary-actions">
            <ContactLink
              href={`tel:${siteConfig.phone}`}
              className="cta-primary"
              eventName="click_phone"
              eventLabel={`listing_${listing.id}_phone`}
            >
              전화 상담 연결
            </ContactLink>
            <Link className="cta-secondary detail-secondary-action" href="/support">
              고객센터 이동
            </Link>
          </div>
        </aside>
      </section>

      <section className="detail-kpi-grid">
        <article className="detail-kpi">
          <span>면허년도</span>
          <strong>{listing.licenseYear}</strong>
        </article>
        <article className="detail-kpi">
          <span>시공능력</span>
          <strong>{listing.capacity}</strong>
        </article>
        <article className="detail-kpi">
          <span>최근 실적</span>
          <strong>{listing.performance}</strong>
        </article>
        <article className="detail-kpi">
          <span>진행 상태</span>
          <strong>{listing.status}</strong>
        </article>
      </section>

      <section className="detail-body-grid">
        <article className="detail-card">
          <h2>핵심 포인트</h2>
          <ul className="detail-list">
            {listing.highlights.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="detail-card">
          <h2>인수 범위</h2>
          <p>{listing.transferScope}</p>
        </article>

        <article className="detail-card">
          <h2>추천 대상</h2>
          <p>{listing.recommendedFor}</p>
        </article>

        <article className="detail-card">
          <h2>사전 확인 자료</h2>
          <ul className="detail-list">
            {listing.documents.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="detail-card detail-card--wide">
          <h2>검토 메모</h2>
          <p>{listing.memo}</p>
          <p>{listing.caution}</p>
        </article>
      </section>

      {(previous || next) ? (
        <section className="detail-pagination">
          {previous ? (
            <Link className="detail-pagination-link" href={`/mna/${encodeURIComponent(previous.id)}`}>
              <span>이전 매물</span>
              <strong>{previous.id}</strong>
            </Link>
          ) : (
            <div />
          )}

          {next ? (
            <Link className="detail-pagination-link detail-pagination-link--next" href={`/mna/${encodeURIComponent(next.id)}`}>
              <span>다음 매물</span>
              <strong>{next.id}</strong>
            </Link>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
