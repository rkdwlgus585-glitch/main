import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { ContactLink } from "@/components/contact-link";
import { siteConfig } from "@/components/site-config";
import { getAdjacentListings, getListingById } from "@/lib/listings";
import { buildPageMetadata } from "@/lib/page-metadata";

type PageProps = {
  params: Promise<{
    id: string;
  }>;
};

export const revalidate = 3600;
export const dynamicParams = true;

function hasDisplayValue(value: string | null | undefined) {
  const text = String(value ?? "").trim();
  return Boolean(text && text !== "-" && text.toLowerCase() !== "empty");
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
  const detailPills = [
    listing.id,
    listing.status,
    listing.region,
    listing.sectorLabel,
    `업데이트 ${listing.updatedAt.slice(0, 10)}`,
  ].filter(hasDisplayValue);
  const companyMeta = [listing.companyType, hasDisplayValue(listing.companyYear) ? `법인설립일 ${listing.companyYear}` : ""]
    .filter(hasDisplayValue)
    .join(" · ");
  const detailKpis = [
    {
      label: "면허년도",
      value:
        listing.licenseYears.filter(hasDisplayValue).join(" / ") ||
        (hasDisplayValue(listing.companyYear) ? listing.companyYear : ""),
    },
    { label: "시공능력", value: listing.capacityLabel },
    { label: "3년 실적", value: listing.performance3Year },
    { label: "5년 실적", value: listing.performance5Year },
  ].filter((item) => hasDisplayValue(item.value));
  const overviewEntries = Object.entries(listing.overview).filter(([, value]) => hasDisplayValue(value));
  const financeEntries = Object.entries(listing.finance).filter(([, value]) => hasDisplayValue(value));
  const performanceRows = listing.performanceRows.filter(
    (row, index) => index === 0 || row.some((cell) => hasDisplayValue(cell)),
  );
  const notes = listing.notes.filter(hasDisplayValue);
  const guidance = listing.guidance.filter(hasDisplayValue);

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
            {detailPills.map((item) => (
              <span key={item} className="detail-pill">
                {item}
              </span>
            ))}
          </div>
        </div>

        <aside className="detail-side-cta">
          <strong>{listing.price || "협의"}</strong>
          {companyMeta ? <p>{companyMeta}</p> : null}
          <p>
            {listing.sourceKind === "sheet-only"
              ? "구글시트 원본 기준으로 생성된 매물입니다."
              : listing.sourceKind === "sheet-merged"
                ? "공개 게시판 보존본에 구글시트 최신 상태를 반영했습니다."
                : "공개 게시판 보존본 기준 매물입니다."}
          </p>
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

      {detailKpis.length > 0 ? (
        <section className="detail-kpi-grid">
          {detailKpis.map((item) => (
            <article key={item.label} className="detail-kpi">
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </article>
          ))}
        </section>
      ) : null}

      <section className="detail-body-grid">
        {overviewEntries.length > 0 ? (
          <article className="detail-card">
            <h2>회사개요</h2>
            <dl className="detail-pairs">
              {overviewEntries.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </article>
        ) : null}

        {financeEntries.length > 0 ? (
          <article className="detail-card">
            <h2>재무제표</h2>
            <dl className="detail-pairs">
              {financeEntries.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </article>
        ) : null}

        {performanceRows.length > 1 ? (
          <article className="detail-card detail-card--wide">
            <h2>최근년도 매출실적</h2>
            <div className="legacy-table-shell">
              <table className="legacy-table">
                <thead>
                  <tr>
                    {performanceRows[0]?.map((header) => (
                      <th key={header}>{header}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {performanceRows.slice(1).map((row) => (
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
        ) : null}

        {notes.length > 0 ? (
          <article className="detail-card detail-card--wide">
            <h2>주요체크사항</h2>
            <ul className="detail-list">
              {notes.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        ) : null}

        {guidance.length > 0 ? (
          <article className="detail-card detail-card--wide">
            <h2>안내</h2>
            <ul className="detail-list">
              {guidance.map((item) => (
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
