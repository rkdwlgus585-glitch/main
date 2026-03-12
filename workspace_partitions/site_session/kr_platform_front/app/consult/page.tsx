import type { Metadata } from "next";
import Link from "next/link";
import { platformConfig } from "@/components/platform-config";
import { ConsultForm } from "@/components/consult-form";
import { breadcrumbSchema, organizationRef, siteBase } from "@/lib/json-ld";

const pageTitle = "고객센터 | 서울건설정보";
const pageDescription =
  "건설업 양도양수, 인허가, 면허 관리까지 — AI 분석 결과를 바탕으로 건설업 전문 행정사가 직접 상담합니다.";

export const metadata: Metadata = {
  title: pageTitle,
  description: pageDescription,
  alternates: { canonical: "/consult" },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    url: "/consult",
    type: "website",
    locale: "ko_KR",
  },
  twitter: {
    card: "summary",
    title: pageTitle,
    description: pageDescription,
  },
};

const steps = [
  {
    step: "01",
    title: "AI 무료 분석",
    description: "양도가 산정 또는 인허가 사전검토를 먼저 실행하세요. 분석 결과가 상담의 출발점이 됩니다.",
  },
  {
    step: "02",
    title: "상담 접수",
    description: "전화 또는 이메일로 AI 분석 결과를 전달하시면, 전문 행정사가 검토 후 연락드립니다.",
  },
  {
    step: "03",
    title: "맞춤 컨설팅",
    description: "양도가 협상 전략, 등록기준 충족 로드맵, 서류 준비까지 원스톱으로 안내합니다.",
  },
  {
    step: "04",
    title: "실행 · 완료",
    description: "양도양수 계약 체결, 인허가 신청, 변경 등록까지 행정사가 직접 대행합니다.",
  },
];

const benefits = [
  {
    title: "데이터 기반 상담",
    description: "감이 아닌 AI 분석 데이터를 기초로 합리적 협상을 지원합니다.",
    icon: "🎯",
  },
  {
    title: "건설업 전문",
    description: "건설업 면허 양도양수·인허가만 전문으로 다루는 행정사가 직접 담당합니다.",
    icon: "🏗️",
  },
  {
    title: "원스톱 처리",
    description: "분석부터 계약, 행정 대행까지 한 곳에서 끝납니다. 별도 업체를 찾을 필요가 없습니다.",
    icon: "⚡",
  },
  {
    title: "비용 투명성",
    description: "AI 산정가와 시장 비교 데이터를 함께 제공하여 합리적 비용 판단을 돕습니다.",
    icon: "💎",
  },
];

/* NOTE: JSON-LD uses dangerouslySetInnerHTML which is safe here because
   all data comes from compile-time string literals (not user input). */
function ConsultJsonLd() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "ProfessionalService",
    name: "서울건설정보 고객센터",
    description: pageDescription,
    url: `${siteBase}/consult`,
    telephone: platformConfig.contactPhone,
    email: platformConfig.contactEmail,
    areaServed: { "@type": "Country", name: "KR" },
    serviceType: "건설업 양도양수·인허가 전문 상담",
    parentOrganization: organizationRef,
  };
  /* HowTo schema helps Google show the consultation flow as a step-by-step snippet */
  const howTo = {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: "건설업 전문 상담 진행 절차",
    description: "AI 분석 결과를 바탕으로 건설업 전문 행정사의 맞춤 상담을 받는 방법",
    step: steps.map((s, i) => ({
      "@type": "HowToStep",
      position: i + 1,
      name: s.title,
      text: s.description,
    })),
  };
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema("고객센터", "/consult")) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(howTo) }}
      />
    </>
  );
}

export default function ConsultPage() {
  return (
    <main id="main" className="page-shell">
      <ConsultJsonLd />
      <Link className="back-link" href="/">
        ← 플랫폼 홈으로
      </Link>

      <section className="consult-hero" aria-label="고객센터 소개">
        <p className="eyebrow">고객센터</p>
        <h1>AI 분석 다음 단계,<br />전문가가 이어갑니다</h1>
        <p className="consult-hero-body">
          AI가 산정한 양도가와 인허가 진단 결과를 바탕으로
          건설업 전문 행정사가 맞춤 상담을 제공합니다.
        </p>
        <div className="consult-hero-actions">
          <a className="cta-primary" href={`tel:${platformConfig.contactPhone}`}>
            <span aria-hidden="true">📞</span> {platformConfig.contactPhone}
          </a>
          <a className="cta-secondary" href={`mailto:${platformConfig.contactEmail}`}>
            이메일 문의
          </a>
        </div>
      </section>

      <section className="consult-benefits" aria-label="상담 장점">
        <div className="section-header">
          <p className="eyebrow">상담 장점</p>
          <h2>왜 서울건설정보인가요?</h2>
        </div>
        <div className="benefits-grid">
          {benefits.map((b) => (
            <div key={b.title} className="benefit-card">
              <span className="benefit-icon" aria-hidden="true">{b.icon}</span>
              <h3>{b.title}</h3>
              <p>{b.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="consult-steps" aria-label="진행 절차">
        <div className="section-header">
          <p className="eyebrow">진행 절차</p>
          <h2>상담은 이렇게 진행됩니다</h2>
        </div>
        <div className="steps-timeline">
          {steps.map((s) => (
            <div key={s.step} className="step-item">
              <span className="step-number">{s.step}</span>
              <div className="step-content">
                <h3>{s.title}</h3>
                <p>{s.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="consult-form-section" aria-label="온라인 상담 신청">
        <div className="section-header">
          <p className="eyebrow">온라인 접수</p>
          <h2>상담 신청서</h2>
        </div>
        <p className="consult-form-intro">
          아래 양식을 작성하시면 전문 행정사가 확인 후 연락드립니다.
          전화 상담을 원하시면{" "}
          <a href={`tel:${platformConfig.contactPhone}`}>{platformConfig.contactPhone}</a>으로
          바로 연락 주세요.
        </p>
        <ConsultForm />
      </section>

      <section className="consult-start" aria-label="상담 시작 안내">
        <h2>지금 바로 시작하세요</h2>
        <p>
          AI 분석을 아직 안 해보셨다면, 먼저 무료 분석부터 시작하세요.
          분석 결과가 없어도 전화 상담은 언제든 가능합니다.
        </p>
        <div className="consult-start-actions">
          <Link className="cta-primary" href="/yangdo">
            양도가 산정하기
          </Link>
          <Link className="cta-secondary" href="/permit">
            건설업등록 검토하기
          </Link>
          <a className="cta-secondary" href={`tel:${platformConfig.contactPhone}`}>
            <span aria-hidden="true">📞</span> 바로 전화하기
          </a>
        </div>
      </section>
    </main>
  );
}
