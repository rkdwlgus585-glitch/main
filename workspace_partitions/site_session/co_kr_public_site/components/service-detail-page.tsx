import type { ReactNode } from "react";
import Link from "next/link";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { ContactLink } from "@/components/contact-link";
import { siteConfig } from "@/components/site-config";

type SummaryCard = {
  label: string;
  value: string;
  note: string;
};

type ProcessStep = {
  title: string;
  body: string;
};

type ChecklistGroup = {
  title: string;
  items: string[];
};

type NoteCard = {
  title: string;
  body: string;
};

export function ServiceDetailPage({
  eyebrow,
  title,
  description,
  breadcrumbLabel,
  breadcrumbPath,
  heroLabel,
  heroNote,
  reviewedAt,
  referenceText,
  summaryCards,
  processTitle,
  processSteps,
  checklistTitle,
  checklistGroups,
  notesTitle,
  notes,
  afterContent,
}: {
  eyebrow: string;
  title: string;
  description: string;
  breadcrumbLabel: string;
  breadcrumbPath: string;
  heroLabel: string;
  heroNote: string;
  reviewedAt: string;
  referenceText: string;
  summaryCards: SummaryCard[];
  processTitle: string;
  processSteps: ProcessStep[];
  checklistTitle: string;
  checklistGroups: ChecklistGroup[];
  notesTitle: string;
  notes: NoteCard[];
  afterContent?: ReactNode;
}) {
  const serviceSchema = {
    "@context": "https://schema.org",
    "@type": "Service",
    name: `건설업 ${title}`,
    description,
    serviceType: `건설업 ${title} 컨설팅`,
    url: `${siteConfig.host}${breadcrumbPath}`,
    provider: {
      "@type": "LocalBusiness",
      name: siteConfig.companyName,
      url: siteConfig.host,
      telephone: siteConfig.phone,
    },
    areaServed: {
      "@type": "Country",
      name: "KR",
    },
  };

  return (
    <div className="page-shell page-shell--inner">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(serviceSchema) }}
      />
      <Breadcrumbs
        items={[
          { href: "/", label: "홈" },
          { href: breadcrumbPath, label: breadcrumbLabel },
        ]}
      />

      <section className="service-detail-hero">
        <div className="service-detail-copy">
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p>{description}</p>
          <div className="detail-pill-row" aria-label="서비스 핵심 정보">
            <span className="detail-pill">{heroLabel}</span>
            <span className="detail-pill">{heroNote}</span>
          </div>
        </div>

        <aside className="service-side-cta">
          <strong>상담 중심 진행</strong>
          <p>
            운영 사이트에서는 복잡한 설명보다 먼저 판단 기준과 준비 항목을 정리하고,
            세부 판단은 실제 상담으로 연결하는 방식이 효율적입니다.
          </p>
          <p className="service-side-meta">전문 실무팀 검토 후 전화 또는 자료 기준으로 후속 안내</p>
          <div className="detail-summary-actions">
            <ContactLink
              href={`tel:${siteConfig.phone}`}
              className="cta-primary"
              eventName="click_phone"
              eventLabel={`${breadcrumbPath}_phone`}
            >
              전화 상담 연결
            </ContactLink>
            <Link className="cta-secondary detail-secondary-action" href="/support">
              고객센터 이동
            </Link>
          </div>
        </aside>
      </section>

      <section className="service-meta-grid">
        <article className="service-meta-card">
          <span>최근 검토</span>
          <strong>{reviewedAt}</strong>
        </article>
        <article className="service-meta-card">
          <span>기준 참고</span>
          <strong>{referenceText}</strong>
        </article>
        <article className="service-meta-card">
          <span>상담 방식</span>
          <strong>자료 선검토 후 개별 안내</strong>
        </article>
      </section>

      <section className="service-summary-grid">
        {summaryCards.map((card) => (
          <article key={card.label} className="service-summary-card">
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <p>{card.note}</p>
          </article>
        ))}
      </section>

      <section className="section-block">
        <div className="section-header">
          <p className="eyebrow">Process Brief</p>
          <h2>{processTitle}</h2>
        </div>
        <div className="service-step-grid">
          {processSteps.map((step, index) => (
            <article key={step.title} className="service-step-card">
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{step.title}</strong>
              <p>{step.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section-block">
        <div className="section-header">
          <p className="eyebrow">Checklist</p>
          <h2>{checklistTitle}</h2>
        </div>
        <div className="service-checklist-grid">
          {checklistGroups.map((group) => (
            <article key={group.title} className="service-list-card">
              <h3>{group.title}</h3>
              <ul className="detail-list">
                {group.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="section-block">
        <div className="section-header">
          <p className="eyebrow">Note</p>
          <h2>{notesTitle}</h2>
        </div>
        <div className="service-note-grid">
          {notes.map((note) => (
            <article key={note.title} className="service-note-card">
              <h3>{note.title}</h3>
              <p>{note.body}</p>
            </article>
          ))}
        </div>
      </section>

      {afterContent}
    </div>
  );
}
