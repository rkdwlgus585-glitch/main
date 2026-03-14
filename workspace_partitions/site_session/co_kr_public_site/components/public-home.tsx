import Link from "next/link";
import { ArrowRight, Building2, CircleHelp, ClipboardCheck, FileStack, Scale, Shield } from "lucide-react";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { ContentGovernanceSection } from "@/components/content-governance";
import { ContactLink } from "@/components/contact-link";
import { LegalUpdateSection } from "@/components/legal-update-section";
import { ListingPreview } from "@/components/listing-preview";
import { NoticePreview } from "@/components/notice-preview";
import { quickEntries } from "@/components/sample-data";
import { siteConfig } from "@/components/site-config";
import { getAllListings, getImportManifest, getListingDatasetStats } from "@/lib/legacy-content";
import { regulatoryReviewedAt } from "@/lib/regulatory-guidance";

const serviceCards = [
  {
    title: "양도·합병 신고 기준",
    body: "건설산업기본법 제17조부터 제19조까지의 신고, 공고, 진행 공사 정리 포인트를 먼저 안내합니다.",
    icon: Scale,
  },
  {
    title: "등록 신청 구조",
    body: "법 제10조, 시행령 제13조, 시행규칙 제2조를 기준으로 등록 전 체크 순서를 정리했습니다.",
    icon: Building2,
  },
  {
    title: "법인·분할 설계",
    body: "법인설립, 양도양수, 분할합병 중 무엇이 맞는지 초기 목적과 신고 구조를 함께 비교합니다.",
    icon: Shield,
  },
  {
    title: "실적·시공능력 일정",
    body: "2026 협회 공지 기준으로 실적신고, 재무제표 제출, 시공능력 공시 일정을 관리합니다.",
    icon: FileStack,
  },
];

const processSteps = [
  "양도양수인지 신규 등록인지부터 나누고, 신고 대상 여부를 먼저 확인합니다.",
  "업종별 등록기준과 필요 서류를 대조해 누락 항목을 초기 단계에서 정리합니다.",
  "2026 협회 접수 일정과 관할 수탁기관 흐름에 맞춰 자료 준비 순서를 잡습니다.",
  "실사 또는 상담 단계에서는 계약보다 신고, 공고, 진행 공사 정리 여부를 우선 확인합니다.",
];

export function PublicHome() {
  const latestListings = getAllListings().slice(0, 4);
  const manifest = getImportManifest();
  const listingStats = getListingDatasetStats();

  const websiteSchema = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: siteConfig.brandName,
    url: siteConfig.host,
    description: "건설업 양도양수, 등록, 분할합병, 실적신고 일정을 최신 법령과 절차 기준으로 안내하는 퍼블릭 사이트",
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
          <p className="hero-badge">{regulatoryReviewedAt} 기준 법령 · 절차 업데이트</p>
          <p className="hero-kicker">건설산업기본법 · 시행령 · 시행규칙 · 협회 공지 기준 반영</p>
          <h1>
            양도양수와 건설업 등록 절차를
            <br />
            최신 기준으로 먼저 정리합니다
          </h1>
          <p className="hero-body">
            건설업 양도·합병·상속은 신고 대상이고, 양도는 30일 이상 공고가 필요합니다. 등록 신청은 업종별 자본금,
            보증가능금액, 기술인력, 사무실·장비 기준을 먼저 맞춘 뒤 진행해야 하며, 2026년 실적·재무 제출 일정도 함께
            관리해야 합니다.
          </p>
          <div className="hero-ai-pills">
            <Link href="/mna" className="hero-ai-pill">
              <Scale size={16} aria-hidden="true" />
              <span>양도·합병 기준</span>
              <span className="hero-ai-pill-tag">법령</span>
            </Link>
            <Link href="/registration" className="hero-ai-pill">
              <ClipboardCheck size={16} aria-hidden="true" />
              <span>등록 신청 절차</span>
              <span className="hero-ai-pill-tag">접수</span>
            </Link>
            <Link href="/practice" className="hero-ai-pill">
              <FileStack size={16} aria-hidden="true" />
              <span>2026 실적 일정</span>
              <span className="hero-ai-pill-tag">실무</span>
            </Link>
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
              <strong>신고와 접수를 먼저 읽는 건설업 브리프</strong>
              <p>양도양수, 등록, 분할합병, 실적신고 일정을 법령과 협회 공지 기준으로 정리해 초기 판단 속도를 높입니다.</p>
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
        <article>
          <strong>기준 검토일</strong>
          <span>{regulatoryReviewedAt}</span>
        </article>
      </section>

      <LegalUpdateSection />

      <ContentGovernanceSection />

      <AiToolBridge variant="full" featured />

      <section className="quick-entry-section">
        <div className="section-header">
          <p className="eyebrow">Quick Entry</p>
          <h2>최신 기준 확인 후 바로 이어져야 하는 메뉴를 고정합니다</h2>
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
          <h2>구글시트 원본을 기준으로 운영하고 보존 게시판은 별도로 유지합니다</h2>
          <p>
            현재 독립 사이트에는 구글시트 기준 양도양수 {listingStats.sheetCount}건이 반영되어 있고,
            공지 {manifest.counts.notice}건과 프리미엄 {manifest.counts.premium}건은 공개 게시판 보존본으로 함께 유지됩니다.
          </p>
        </div>
        <ListingPreview listings={latestListings} />
      </section>

      <section className="section-block">
        <div className="section-header">
          <p className="eyebrow">Service Map</p>
          <h2>퍼블릭 사이트에서 직접 운영해야 할 최신 안내 범위</h2>
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
          <h2>최신 법령 확인에서 접수 준비까지 한 흐름으로 연결합니다</h2>
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
          <h2>홈에서 기준을 먼저 확인하고, 개별 사안은 상담 단계에서 마무리합니다</h2>
          <p>
            퍼블릭 사이트에서는 최신 법령과 절차를 먼저 정리하고, 실제 계약·신고 단계에서는 업종, 지역,
            진행 공사 여부에 맞춘 개별 검토로 이어갑니다.
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
