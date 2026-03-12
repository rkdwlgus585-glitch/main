import type { Metadata } from "next";
import Link from "next/link";
import { platformConfig } from "@/components/platform-config";
import { breadcrumbSchema, organizationRef, siteBase } from "@/lib/json-ld";

const pageTitle = "회사소개 | 서울건설정보";
const pageDescription =
  "건설업 양도양수·인허가 전문 AI 플랫폼 서울건설정보를 소개합니다. 데이터와 전문성을 결합한 건설업 원스톱 서비스.";

export const metadata: Metadata = {
  title: pageTitle,
  description: pageDescription,
  alternates: { canonical: "/about" },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    url: "/about",
    type: "website",
    locale: "ko_KR",
  },
  twitter: {
    card: "summary",
    title: pageTitle,
    description: pageDescription,
  },
};

const values = [
  {
    title: "데이터 중심",
    description:
      "감이나 경험에 의존하지 않습니다. 공시 데이터와 시장 실거래를 교차 분석해 객관적 근거를 만듭니다.",
  },
  {
    title: "전문성 결합",
    description:
      "AI 분석 결과를 건설업 전문 행정사가 검증하고, 실행 가능한 전략으로 전환합니다.",
  },
  {
    title: "원스톱 완결",
    description:
      "분석부터 상담, 행정 대행까지 한 곳에서 끝냅니다. 고객이 여러 곳을 전전할 필요가 없습니다.",
  },
  {
    title: "투명한 비용",
    description:
      "AI 양도가 산정과 인허가 사전검토는 무료입니다. 모든 비용 항목을 사전에 투명하게 안내합니다.",
  },
];

const milestones = [
  { year: "2024", event: "건설업 양도양수 시장 분석 데이터 구축 착수" },
  { year: "2025", event: "AI 양도가 산정 시스템 v1.0 개발 완료" },
  { year: "2025", event: "AI 인허가 사전검토 시스템 v1.0 개발 완료" },
  { year: "2025", event: "양도가 산정·인허가 사전검토 알고리즘 특허 출원" },
  { year: "2026", event: "seoulmna.kr 플랫폼 정식 오픈 · 191개 업종 분석 지원" },
];

/*
 * NOTE: JSON-LD uses dangerouslySetInnerHTML which is safe here because
 * all data comes from compile-time string literals — no user input is
 * interpolated. This is the standard Next.js pattern for structured data.
 */
function AboutJsonLd() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    name: pageTitle,
    description: pageDescription,
    url: `${siteBase}/about`,
    mainEntity: {
      ...organizationRef,
      "@type": ["Organization", "LocalBusiness"],
      description: pageDescription,
      foundingDate: "2024",
      telephone: platformConfig.contactPhone,
      email: platformConfig.contactEmail,
      address: {
        "@type": "PostalAddress",
        addressLocality: "서울특별시",
        addressCountry: "KR",
      },
      knowsAbout: [
        "건설업 양도양수",
        "건설업 면허",
        "인허가 사전검토",
        "건설업 등록기준",
      ],
    },
  };
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(breadcrumbSchema("회사소개", "/about")),
        }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
    </>
  );
}

export default function AboutPage() {
  return (
    <main id="main" className="page-shell">
      <AboutJsonLd />
      <Link className="back-link" href="/">
        ← 플랫폼 홈으로
      </Link>

      <section className="about-hero" aria-label="회사 소개">
        <p className="eyebrow">회사소개</p>
        <h1>
          건설업 면허 거래의
          <br />
          새로운 기준을 만듭니다
        </h1>
        <p className="about-hero-body">
          서울건설정보는 건설업 양도양수와 인허가를 데이터와 AI 기술로
          혁신하는 전문 플랫폼입니다. 복잡하고 불투명했던 건설업 면허
          시장에 객관적인 분석과 전문 상담을 결합해 합리적인 거래
          환경을 만들어갑니다.
        </p>
      </section>

      <section className="about-mission" aria-label="미션">
        <div className="section-header" style={{ textAlign: "center" }}>
          <p className="eyebrow">미션</p>
          <h2>
            &ldquo;건설업 면허 거래에서 정보 비대칭을 없앤다&rdquo;
          </h2>
        </div>
        <p className="about-mission-body">
          기존 건설업 면허 양도양수 시장은 가격 정보의 비대칭,
          수작업 중심의 검토 과정, 분산된 절차로 인해 비효율이
          큽니다. 서울건설정보는 AI 기술과 건설업 전문 행정사의
          노하우를 결합하여 이 문제를 해결합니다.
        </p>
      </section>

      <section className="about-values" aria-label="핵심 가치">
        <div className="section-header" style={{ textAlign: "center" }}>
          <p className="eyebrow">핵심 가치</p>
          <h2>우리가 중요하게 생각하는 것</h2>
        </div>
        <div className="about-values-grid">
          {values.map((v, i) => (
            <article key={v.title} className="about-value-card">
              <span className="about-value-index">{String(i + 1).padStart(2, "0")}</span>
              <h3>{v.title}</h3>
              <p>{v.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="about-tech" aria-label="기술 역량">
        <div className="section-header" style={{ textAlign: "center" }}>
          <p className="eyebrow">기술 역량</p>
          <h2>AI 기술 · 특허 출원 · 데이터 인프라</h2>
        </div>
        <div className="about-tech-grid">
          <div className="about-tech-card">
            <h3>AI 양도가 산정 엔진</h3>
            <p>
              공시 재무 데이터, 시장 거래 사례, 업종별 특성을
              종합 분석하여 적정 양도가격 범위를 산정합니다.
              신뢰도 지표와 근거 데이터를 함께 제공합니다.
            </p>
          </div>
          <div className="about-tech-card">
            <h3>AI 인허가 사전검토 엔진</h3>
            <p>
              191개 업종의 법정 등록기준을 실시간으로
              비교 분석합니다. 자본금, 기술인력, 시설 등
              항목별 충족 여부를 즉시 진단하고 신규 취득 비용을
              계산합니다.
            </p>
          </div>
          <div className="about-tech-card">
            <h3>특허 출원 기술</h3>
            <p>
              양도가 산정 알고리즘과 인허가 사전검토 방법론은
              한국특허청(KIPO)에 특허 출원되었으며,
              독자적인 지적재산으로 보호됩니다.
            </p>
          </div>
        </div>
      </section>

      <section className="about-timeline" aria-label="연혁">
        <div className="section-header" style={{ textAlign: "center" }}>
          <p className="eyebrow">연혁</p>
          <h2>주요 이정표</h2>
        </div>
        <div className="about-timeline-list">
          {milestones.map((m, i) => (
            <div key={i} className="about-milestone">
              <span className="about-milestone-year">{m.year}</span>
              <p className="about-milestone-event">{m.event}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="consult-start" aria-label="상담 안내">
        <h2>함께 시작하시겠습니까?</h2>
        <p>
          AI 분석부터 전문 상담까지, 건설업 면허에 관한 모든 것을
          서울건설정보와 함께하세요.
        </p>
        <div className="consult-start-actions">
          <Link className="cta-primary" href="/consult">
            상담 신청하기
          </Link>
          <Link className="cta-secondary" href="/yangdo">
            양도가 무료 산정
          </Link>
        </div>
      </section>
    </main>
  );
}
