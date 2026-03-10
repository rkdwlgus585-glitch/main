import Link from "next/link";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { ContactLink } from "@/components/contact-link";
import { siteConfig } from "@/components/site-config";

type BreadcrumbItem = {
  href: string;
  label: string;
};

export function LegacyContentPage({
  breadcrumbs,
  eyebrow,
  title,
  description,
  publishedAt,
  updatedAt,
  views,
  contentHtml,
  contactLabel = "전화 상담 연결",
}: {
  breadcrumbs: BreadcrumbItem[];
  eyebrow: string;
  title: string;
  description: string;
  publishedAt?: string;
  updatedAt?: string;
  views?: number | null;
  contentHtml: string;
  contactLabel?: string;
}) {
  const pageUrl = breadcrumbs.length > 0 ? breadcrumbs[breadcrumbs.length - 1].href : "/";
  const articleSchema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: title,
    description,
    url: `${siteConfig.host}${pageUrl}`,
    ...(publishedAt ? { datePublished: publishedAt } : {}),
    ...(updatedAt ? { dateModified: updatedAt } : {}),
    author: {
      "@type": "Organization",
      name: siteConfig.companyName,
      url: siteConfig.host,
    },
    publisher: {
      "@type": "Organization",
      name: siteConfig.companyName,
      url: siteConfig.host,
    },
  };

  return (
    <div className="page-shell page-shell--inner">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleSchema) }}
      />
      <Breadcrumbs items={breadcrumbs} />

      <section className="legacy-content-hero">
        <div className="legacy-content-copy">
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p>{description}</p>
          <div className="detail-pill-row" aria-label="콘텐츠 메타 정보">
            {publishedAt ? <span className="detail-pill">등록 {publishedAt}</span> : null}
            {updatedAt ? <span className="detail-pill">업데이트 {updatedAt.slice(0, 10)}</span> : null}
            {views ? <span className="detail-pill">조회 {views}</span> : null}
          </div>
        </div>

        <aside className="legacy-content-side">
          <strong>상담 연결 가능</strong>
          <p>
            콘텐츠를 먼저 읽고 현재 상황을 정리한 뒤 상담으로 연결하면 검토 속도와 정확도가 더 좋아집니다.
          </p>
          <div className="detail-summary-actions">
            <ContactLink
              href={`tel:${siteConfig.phone}`}
              className="cta-primary"
              eventName="click_phone"
              eventLabel={`content_${title}_phone`}
            >
              {contactLabel}
            </ContactLink>
            <Link className="cta-secondary detail-secondary-action" href="/support">
              고객센터 이동
            </Link>
          </div>
        </aside>
      </section>

      <section className="legacy-content-shell">
        <div className="legacy-content-body" dangerouslySetInnerHTML={{ __html: contentHtml }} />
      </section>
    </div>
  );
}
