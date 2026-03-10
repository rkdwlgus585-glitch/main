import Link from "next/link";
import { ArrowRight, Building2, Calculator, CircleHelp, ClipboardCheck, FileStack, Scale, Shield } from "lucide-react";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { ContactLink } from "@/components/contact-link";
import { ListingPreview } from "@/components/listing-preview";
import { NoticePreview } from "@/components/notice-preview";
import { quickEntries } from "@/components/sample-data";
import { siteConfig } from "@/components/site-config";
import { getAllListings, getImportManifest } from "@/lib/legacy-content";

const serviceCards = [
  {
    title: "양도양수 실무 안내",
    body: "상담 이전에 매물 성격과 인수 포인트를 빠르게 정리하는 메인 동선입니다.",
    icon: Scale,
  },
  {
    title: "등록기준 검토",
    body: "건설업 신규 등록을 준비하는 고객이 바로 들어와야 할 화면을 분리합니다.",
    icon: Building2,
  },
  {
    title: "법인 및 구조 정리",
    body: "법인설립과 분할합병 같은 보조 서비스도 같은 브랜드 안에서 연결합니다.",
    icon: Shield,
  },
  {
    title: "실무 자료실",
    body: "운영자가 반복 안내하는 내용을 건설실무 메뉴로 정리합니다.",
    icon: FileStack,
  },
];

const processSteps = [
  "메인에서 서비스 성격과 대표 매물을 먼저 보여줍니다.",
  "업종과 지역만으로 대표 유형을 빠르게 좁힙니다.",
  "양도양수, 등록, 법인, 실무 가이드로 자연스럽게 분기합니다.",
  "전화나 문의 채널로 연결해 운영자가 직접 후속 응대를 받습니다.",
];

export function PublicHome() {
  const latestListings = getAllListings().slice(0, 4);
  const manifest = getImportManifest();

  const websiteSchema = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: siteConfig.brandName,
    url: siteConfig.host,
    description: "건설업 양도양수, 등록, 법인설립, 분할합병, 건설실무를 안내하는 독립 퍼블릭 사이트",
    publisher: {
      "@type": "Organization",
      name: siteConfig.companyName,
      url: siteConfig.host,
    },
  };

  return (
    <div className="page-shell">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
      />
      <section className="hero">
        <div className="hero-copy">
          <p className="hero-badge">AI System · Expert Consulting</p>
          <p className="hero-kicker">AI 양도가 산정 · AI 인허가 사전검토 시스템 운영</p>
          <h1>
            건설업 면허 양도와 등록,
            <br />
            AI로 먼저 확인하고 전문가와 상담하세요
          </h1>
          <p className="hero-body">
            AI 양도가 산정 시스템으로 면허 예상 가격을 즉시 확인하고, AI 인허가 사전검토로
            등록 요건 충족 여부를 무료로 점검할 수 있습니다. 결과를 바탕으로 전문가 상담까지 바로 연결됩니다.
          </p>
          <div className="hero-ai-pills">
            <a href={`${siteConfig.platformHost}/yangdo`} className="hero-ai-pill" target="_blank" rel="noopener noreferrer">
              <Calculator size={16} aria-hidden="true" />
              <span>AI 양도가 산정</span>
              <span className="hero-ai-pill-tag">무료</span>
            </a>
            <a href={`${siteConfig.platformHost}/permit`} className="hero-ai-pill" target="_blank" rel="noopener noreferrer">
              <ClipboardCheck size={16} aria-hidden="true" />
              <span>AI 인허가 사전검토</span>
              <span className="hero-ai-pill-tag">무료</span>
            </a>
          </div>

          <div className="hero-actions">
            <Link className="cta-primary" href="/mna">
              실시간 매물 보기
              <ArrowRight size={18} aria-hidden="true" />
            </Link>
            <Link className="cta-secondary" href="/support">
              고객센터 이동
            </Link>
            <ContactLink
              className="cta-tertiary"
              href={`tel:${siteConfig.phone}`}
              eventName="click_phone"
              eventLabel="hero_phone"
            >
              {siteConfig.phone}
            </ContactLink>
          </div>
        </div>

        <div className="hero-media">
          <div className="video-shell">
            <video autoPlay muted loop playsInline preload="metadata" poster="/media/hero-poster.svg" aria-label="건설 현장 메인 영상">
              <source src="/media/hero-construction.mp4" type="video/mp4" />
            </video>
            <div className="video-overlay" />
            <div className="video-caption">
              <strong>성공적인 건설 사업의 시작</strong>
              <p>면허 양도부터 신규 등록까지 — AI 시스템과 전문가 상담으로 더 정확하고 빠른 첫걸음을 내딛으세요.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="trust-strip" aria-label="사업자 정보">
        <article>
          <strong>대표자</strong>
          <span>{siteConfig.representativeName}</span>
        </article>
        <article>
          <strong>사업자등록번호</strong>
          <span>{siteConfig.businessNumber}</span>
        </article>
        <article>
          <strong>통신판매업신고번호</strong>
          <span>{siteConfig.mailOrderNumber}</span>
        </article>
        <article>
          <strong>상담 시간</strong>
          <span>{siteConfig.officeHours}</span>
        </article>
      </section>

      <AiToolBridge variant="full" featured />

      <section className="quick-entry-section">
        <div className="section-header">
          <p className="eyebrow">Quick Entry</p>
          <h2>첫 화면에서 바로 들어가야 하는 메뉴를 고정합니다</h2>
        </div>
        <div className="quick-entry-grid">
          {quickEntries.map((item) => (
            <Link key={item.href} href={item.href} className="quick-entry-card">
              <strong>{item.title}</strong>
              <p>{item.description}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className="section-block">
        <div className="section-header">
          <p className="eyebrow">Market Brief</p>
          <h2>원본 게시판에서 이관한 실제 매물을 읽기 쉬운 브리프로 변환</h2>
          <p>현재 독립 사이트에는 양도양수 {manifest.counts.mna}건, 공지 {manifest.counts.notice}건을 포함한 전체 콘텐츠가 반영되어 있습니다.</p>
        </div>
        <ListingPreview listings={latestListings} />
      </section>

      <section className="section-block">
        <div className="section-header">
          <p className="eyebrow">Service Map</p>
          <h2>퍼블릭 사이트에서 직접 운영해야 할 서비스 범위</h2>
        </div>
        <div className="service-card-grid">
          {serviceCards.map(({ title, body, icon: Icon }) => (
            <article key={title} className="service-card">
              <span className="service-icon" aria-hidden="true">
                <Icon size={20} />
              </span>
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section-block">
        <div className="section-header">
          <p className="eyebrow">Operating Flow</p>
          <h2>AI 확인 결과를 바탕으로 상담과 운영이 자연스럽게 연결됩니다</h2>
        </div>
        <div className="process-grid">
          {processSteps.map((step, index) => (
            <article key={step} className="process-card">
              <span>{String(index + 1).padStart(2, "0")}</span>
              <p>{step}</p>
            </article>
          ))}
        </div>
      </section>

      <NoticePreview />

      <section className="cta-section">
        <div className="cta-content">
          <CircleHelp size={20} aria-hidden="true" />
          <h2>AI 시스템으로 먼저 확인하고, 전문가 상담으로 완성하세요</h2>
          <p>
            면허 양도 예상 가격 산정부터 등록 기준 충족 여부 점검까지 — 무료 AI 도구로 먼저 확인하고,
            결과를 바탕으로 전문 상담을 이어갈 수 있습니다.
          </p>
          <div className="cta-actions">
            <Link className="cta-primary cta-primary--light" href="/support">
              상담 페이지 보기
            </Link>
            <ContactLink
              className="cta-secondary cta-secondary--light"
              href={`tel:${siteConfig.phone}`}
              eventName="click_phone"
              eventLabel="bottom_cta_phone"
            >
              {siteConfig.phone}
            </ContactLink>
          </div>
        </div>
      </section>
    </div>
  );
}
