import Link from "next/link";
import { ArrowRight, Building2, CircleHelp, FileStack, Scale, Shield } from "lucide-react";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { ContactLink } from "@/components/contact-link";
import { ListingBoard } from "@/components/listing-board";
import { NoticePreview } from "@/components/notice-preview";
import { quickEntries } from "@/components/sample-data";
import { siteConfig } from "@/components/site-config";

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
  return (
    <div className="page-shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="hero-badge">Independent Public Site</p>
          <p className="hero-kicker">seoulmna.kr과 분리된 운영 사이트</p>
          <h1>
            건설업 양도양수와 등록 실무를
            <br />
            한눈에 안내하는 독립 퍼블릭 사이트
          </h1>
          <p className="hero-body">
            이 프로젝트는 AI 시스템용 사이트와 별개로, 상담과 정보 제공 중심의
            퍼블릭 사이트를 새로 개설하기 위한 골격입니다. 기존 운영 사이트의 장점은 참고하되,
            구조와 문구는 새로 설계했습니다.
          </p>

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
              <strong>현장감 있는 메인 비주얼과 상담 유도 구조</strong>
              <p>기존 사이트의 첫인상은 참고하되, 자산과 카피는 독립적으로 구성합니다.</p>
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
          <h2>양도양수 게시판 성격을 유지하면서 읽기 쉬운 매물 브리프로 변환</h2>
        </div>
        <ListingBoard compact />
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

      <AiToolBridge variant="full" />

      <section className="section-block">
        <div className="section-header">
          <p className="eyebrow">Operating Flow</p>
          <h2>새 사이트는 AI보다 상담과 운영 흐름이 먼저 보이도록 설계합니다</h2>
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
          <h2>상담형 퍼블릭 사이트로 먼저 분리하고, AI 시스템은 별도 연결하는 구조가 맞습니다</h2>
          <p>
            지금 만든 골격은 `seoulmna.kr` 대체가 아니라, `seoulmna.co.kr` 역할을 독립적으로
            수행할 새 사이트의 시작점입니다.
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
