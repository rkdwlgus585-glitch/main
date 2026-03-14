import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { Phone, ArrowRight, BarChart3, Layers, Search, FileCheck } from "lucide-react";
import { platformConfig } from "@/components/platform-config";
import { breadcrumbSchema, organizationRef } from "@/lib/json-ld";
import { ScrollAnimate } from "@/components/scroll-animate";
import { YangdoCalculator } from "@/components/yangdo/yangdo-calculator";

const pageTitle = "AI 양도가 산정 | 서울건설정보";
const pageDescription =
  "건설업 면허 양도가격을 AI가 공시 데이터 기반으로 무료 산정합니다. 실시간 시세 분석, 업종별 정산 로직, 전문가 상담 연결까지 원스톱 제공.";

export const metadata: Metadata = {
  title: pageTitle,
  description: pageDescription,
  alternates: { canonical: "/yangdo" },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    url: "/yangdo",
    type: "website",
    locale: "ko_KR",
  },
  twitter: {
    card: "summary",
    title: pageTitle,
    description: pageDescription,
  },
};

const features = [
  {
    title: "공시 데이터 기반",
    detail: "공시 실적을 실시간 반영, 객관적 가격 범위 산정",
    icon: BarChart3,
  },
  {
    title: "복합면허 자동 분해",
    detail: "2개 이상 업종 결합 시 업종별 기여도 자동 분석",
    icon: Layers,
  },
  {
    title: "중복매물 보정",
    detail: "여러 사이트 중복 등록 자동 감지·가격 반영",
    icon: Search,
  },
  {
    title: "산정 근거 투명 공개",
    detail: "비교 대상·보정 과정·신뢰도 근거 전부 공개",
    icon: FileCheck,
  },
];

const howItWorks = [
  { step: "01", title: "업종 선택", detail: "텍스트 검색 또는 빠른 선택으로 업종 지정" },
  { step: "02", title: "기준 입력", detail: "시공능력·매출 등 기본 정보 입력" },
  { step: "03", title: "AI 분석", detail: "시장 패턴 실시간 분석·가격대 산출" },
  { step: "04", title: "결과 확인", detail: "가격·신뢰도·비교매물·정산 한 번에 확인" },
];

const stats = [
  { value: "특허 출원", label: "AI 알고리즘", detail: "양도가 산정 전용 AI 엔진" },
  { value: "실시간", label: "공시 데이터 연동", detail: "최신 건설업 실적 반영" },
  { value: "무료", label: "이용 비용", detail: "회원가입 없이 즉시 사용" },
];

const faqs = [
  {
    question: "양도가 산정 비용이 정말 무료인가요?",
    answer: "완전 무료, 회원가입 없이 바로 이용 가능합니다.",
  },
  {
    question: "산정 결과는 얼마나 정확한가요?",
    answer: "공시 데이터 기반 분석이며, 신뢰도 지표로 정확도를 직접 판단할 수 있습니다.",
  },
  {
    question: "복합면허도 산정이 가능한가요?",
    answer: "네, 복합면허도 업종별 기여도를 분해하여 정밀 산정합니다.",
  },
  {
    question: "전기·소방·정보통신 특수 업종도 되나요?",
    answer: "특수 업종은 업종별 정산 정책과 별도 신뢰도 기준이 적용됩니다.",
  },
  {
    question: "산정 후 상담도 연결되나요?",
    answer: "전문 행정사 맞춤 상담을 바로 연결하며, 양도가 협상 전략까지 지원합니다.",
  },
];

/* NOTE: JSON-LD uses dangerouslySetInnerHTML which is safe here because
   all data comes from compile-time string literals (not user input). */
function YangdoJsonLd() {
  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((f) => ({
      "@type": "Question",
      name: f.question,
      acceptedAnswer: { "@type": "Answer", text: f.answer },
    })),
  };
  const serviceSchema = {
    "@context": "https://schema.org",
    "@type": "Service",
    name: "AI 양도가 산정 시스템",
    description: "건설업 면허 양도가격을 공시 데이터 기반 AI가 무료로 산정합니다.",
    provider: organizationRef,
    serviceType: "AI 가격 산정",
    areaServed: { "@type": "Country", name: "KR" },
    datePublished: "2025-01-01",
    dateModified: "2026-03-14",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "KRW",
      description: "무료 AI 분석",
    },
  };
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema("AI 양도가 산정", "/yangdo")) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(serviceSchema) }}
      />
    </>
  );
}

export default function YangdoPage() {
  return (
    <main id="main" className="product-page">
      <YangdoJsonLd />
      <Link className="back-link" href="/">
        ← 플랫폼 홈으로
      </Link>

      {/* ── 히어로 ── */}
      <section className="showcase-hero" aria-label="서비스 소개">
        <p className="eyebrow">AI 양도가 산정</p>
        <h1>건설업 면허 양도가,<br />데이터로 바로 확인하세요</h1>
        <p className="showcase-hero-body">
          공시 실적 기반 AI가 양도가 범위를 즉시 산정합니다.<br />
          복합면허 분해, 중복매물 보정, 신뢰도 지표까지 한 번에.
        </p>
        <div className="showcase-hero-actions">
          <a className="cta-primary cta-large" href="#calculator">
            지금 산정하기 <ArrowRight size={14} aria-hidden="true" />
          </a>
          <Link className="cta-secondary" href="/pricing">
            요금제 보기 <ArrowRight size={14} aria-hidden="true" />
          </Link>
        </div>
      </section>

      {/* ── 계산기 ── */}
      <ScrollAnimate>
        <section id="calculator" className="product-calculator-section" aria-label="AI 양도가 산정기">
          <div className="section-header">
            <p className="eyebrow">AI 양도가 산정</p>
            <h2>지금 바로 양도가를 확인하세요</h2>
          </div>
          <Suspense fallback={<div className="calc-skeleton" aria-label="계산기 로딩 중" role="status" />}>
            <YangdoCalculator />
          </Suspense>
        </section>
      </ScrollAnimate>

      {/* ── 핵심 수치 ── */}
      <ScrollAnimate>
        <section className="showcase-stats" aria-label="핵심 수치">
          <div className="showcase-stats-grid">
            {stats.map((s) => (
              <div key={s.label} className="showcase-stat-card">
                <span className="showcase-stat-value">{s.value}</span>
                <strong className="showcase-stat-label">{s.label}</strong>
                <p className="showcase-stat-detail">{s.detail}</p>
              </div>
            ))}
          </div>
        </section>
      </ScrollAnimate>

      {/* ── 특징 그리드 ── */}
      <ScrollAnimate delay={80}>
        <section className="service-features" aria-label="서비스 특징">
          <div className="section-header">
            <p className="eyebrow">주요 특징</p>
            <h2>정밀한 양도가, 투명한 근거</h2>
          </div>
          <div className="features-grid">
            {features.map((f) => (
              <div className="feature-item" key={f.title}>
                <span className="feature-icon" aria-hidden="true"><f.icon size={28} /></span>
                <h3>{f.title}</h3>
                <p>{f.detail}</p>
              </div>
            ))}
          </div>
        </section>
      </ScrollAnimate>

      {/* ── 이용 방법 ── */}
      <ScrollAnimate delay={80}>
        <section className="showcase-how" aria-label="이용 방법">
          <div className="section-header">
            <p className="eyebrow">이용 방법</p>
            <h2>4단계로 완료됩니다</h2>
          </div>
          <div className="showcase-how-grid">
            {howItWorks.map((s) => (
              <div key={s.step} className="showcase-how-item">
                <span className="showcase-how-number">{s.step}</span>
                <h3>{s.title}</h3>
                <p>{s.detail}</p>
              </div>
            ))}
          </div>
        </section>
      </ScrollAnimate>

      {/* ── 중간 CTA ── */}
      <ScrollAnimate delay={120}>
        <section className="showcase-mid-cta" aria-label="무료 체험">
          <h2>지금 바로 양도가를 확인해 보세요</h2>
          <a className="cta-primary cta-large" href="#calculator">
            양도가 산정하기 <ArrowRight size={14} aria-hidden="true" />
          </a>
        </section>
      </ScrollAnimate>

      {/* ── FAQ ── */}
      <ScrollAnimate>
        <section className="service-faq" aria-label="자주 묻는 질문">
          <div className="section-header">
            <p className="eyebrow">자주 묻는 질문</p>
            <h2>AI 양도가 산정, 이것이 궁금합니다</h2>
          </div>
          <div className="faq-list">
            {faqs.map((f) => (
              <details className="faq-details" key={f.question}>
                <summary>{f.question}</summary>
                <p className="faq-details-body">{f.answer}</p>
              </details>
            ))}
          </div>
        </section>
      </ScrollAnimate>

      {/* ── 하단 CTA ── */}
      <ScrollAnimate delay={80}>
        <section className="service-bottom-cta" aria-label="도입 안내">
          <p>귀사 시스템에 AI 양도가 산정을 도입하고 싶으신가요?</p>
          <div className="service-bottom-actions">
            <Link className="cta-primary" href="/partners">
              시스템 도입 문의
            </Link>
            <a className="cta-secondary" href={`tel:${platformConfig.contactPhone}`}>
              <Phone size={16} aria-hidden="true" /> {platformConfig.contactPhone}
            </a>
          </div>
        </section>
      </ScrollAnimate>
    </main>
  );
}
