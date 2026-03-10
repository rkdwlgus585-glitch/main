import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { ContactLink } from "@/components/contact-link";
import { siteConfig } from "@/components/site-config";
import { getAdjacentListings, getListingById, getListingIds } from "@/lib/listings";
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
    listing.headline || listing.note || listing.sectorLabel,
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
    추천: "https://schema.org/InStock",
    보류: "https://schema.org/LimitedAvailability",
    완료: "https://schema.org/SoldOut",
  } as const;
  const availability = availabilityMap[listing.status as keyof typeof availabilityMap] ?? "https://schema.org/LimitedAvailability";

  const listingSchema = {
    "@context": "https://schema.org",
    "@type": "ItemPage",
    name: `${listing.id} ${listing.title}`,
    description: listing.headline || listing.note || listing.sectorLabel,
    url: `${siteConfig.host}/mna/${encodeURIComponent(listing.id)}`,
    dateModified: listing.updatedAt,
    mainEntity: {
      "@type": "Service",
      name: listing.title,
      description: listing.headline || listing.note || listing.sectorLabel,
      serviceType: `건설업 ${listing.sectorLabel} 양도양수`,
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
        availability,
        priceCurrency: "KRW",
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
          <p>{listing.headline || listing.note || listing.sectorLabel}</p>

          <div className="detail-pill-row" aria-label="매물 핵심 정보">
            <span className="detail-pill">{listing.id}</span>
            <span className="detail-pill">{listing.status}</span>
            <span className="detail-pill">{listing.region}</span>
            <span className="detail-pill">{listing.sectorLabel}</span>
            <span className="detail-pill">업데이트 {listing.updatedAt.slice(0, 10)}</span>
          </div>
        </div>

        <aside className="detail-side-cta">
          <strong>{listing.price || "협의"}</strong>
          <p>{listing.companyType} · 법인설립일 {listing.companyYear || "-"}</p>
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
          <strong>{listing.licenseYears.join(" / ") || listing.companyYear || "-"}</strong>
        </article>
        <article className="detail-kpi">
          <span>시공능력</span>
          <strong>{listing.capacityLabel || "-"}</strong>
        </article>
        <article className="detail-kpi">
          <span>3년 실적</span>
          <strong>{listing.performance3Year || "-"}</strong>
        </article>
        <article className="detail-kpi">
          <span>5년 실적</span>
          <strong>{listing.performance5Year || "-"}</strong>
        </article>
      </section>

      <section className="detail-body-grid">
        <article className="detail-card">
          <h2>회사개요</h2>
          <dl className="detail-pairs">
            {Object.entries(listing.overview).map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value || "-"}</dd>
              </div>
            ))}
          </dl>
        </article>

        <article className="detail-card">
          <h2>재무제표</h2>
          <dl className="detail-pairs">
            {Object.entries(listing.finance).map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value || "-"}</dd>
              </div>
            ))}
          </dl>
        </article>

        <article className="detail-card detail-card--wide">
          <h2>최근년도 매출실적</h2>
          <div className="legacy-table-shell">
            <table className="legacy-table">
              <thead>
                <tr>
                  {listing.performanceRows[0]?.map((header) => (
                    <th key={header}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {listing.performanceRows.slice(1).map((row) => (
                  <tr key={row.join("-")}>
                    {row.map((cell, index) => (
                      <td key={`${row.join("-")}-${index}`}>{cell || "-"}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="detail-card detail-card--wide">
          <h2>주요체크사항</h2>
          <ul className="detail-list">
            {listing.notes.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        {listing.guidance.length > 0 ? (
          <article className="detail-card detail-card--wide">
            <h2>안내</h2>
            <ul className="detail-list">
              {listing.guidance.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        ) : null}
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
