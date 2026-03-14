import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { Phone, ArrowRight, ClipboardCheck, Users, Banknote, AlertTriangle } from "lucide-react";
import { platformConfig } from "@/components/platform-config";
import { breadcrumbSchema, organizationRef } from "@/lib/json-ld";
import { ScrollAnimate } from "@/components/scroll-animate";
import { PermitCalculator } from "@/components/permit/permit-calculator";

const pageTitle = "AI 인허가 검토 | 서울건설정보";
const pageDescription =
  "191개 건설 업종 등록기준 충족 여부를 AI가 즉시 검토합니다. 자본금·기술인력·사무실 요건 진단과 신규 취득 비용 계산까지 무료 제공.";

export const metadata: Metadata = {
  title: pageTitle,
  description: pageDescription,
  alternates: { canonical: "/permit" },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    url: "/permit",
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
    title: "191개 업종 전수 검토",
    detail: "건설·전기·소방·정보통신 등 전 업종 등록기준 점검",
    icon: ClipboardCheck,
  },
  {
    title: "항목별 충족 진단",
    detail: "자본금·인력·사무실·장비 항목별 개별 진단",
    icon: Users,
  },
  {
    title: "신규 취득 비용 산정",
    detail: "등록기준 기반 신규 취득 예상 비용 자동 계산",
    icon: Banknote,
  },
  {
    title: "부족 항목 안내",
    detail: "미충족 항목과 보완 방법을 즉시 안내",
    icon: AlertTriangle,
  },
];

const howItWorks = [
  { step: "01", title: "업종 선택", detail: "검색 또는 카테고리에서 업종 선택" },
  { step: "02", title: "현황 입력", detail: "자본금·인력·사무실 등 현재 상태 입력" },
  { step: "03", title: "AI 진단", detail: "등록기준 전 항목 충족 여부 즉시 판정" },
  { step: "04", title: "결과 확인", detail: "진단·비용·조치를 한 화면에서 확인" },
];

const stats = [
  { value: "191개", label: "검토 업종 수", detail: "건설업 전 업종 등록기준 커버" },
  { value: "6,300+", label: "등록기준 항목", detail: "업종별 상세 요건 데이터" },
  { value: "무료", label: "이용 비용", detail: "회원가입 없이 즉시 사용" },
];

const faqs = [
  {
    question: "AI 인허가 검토 비용이 정말 무료인가요?",
    answer: "완전 무료, 회원가입 없이 바로 이용 가능합니다.",
  },
  {
    question: "어떤 업종을 검토할 수 있나요?",
    answer: "건설·전기·소방·정보통신 등 191개 업종 등록기준을 검토합니다.",
  },
  {
    question: "검토 항목에는 무엇이 포함되나요?",
    answer: "자본금·인력·사무실·시설·자격증 등 등록기준 전 항목을 점검합니다.",
  },
  {
    question: "신규 면허 취득 비용도 알 수 있나요?",
    answer: "등록기준 충족에 필요한 예상 비용(자본금·인력 등)을 안내합니다.",
  },
  {
    question: "검토 결과로 바로 인허가 신청이 가능한가요?",
    answer: "사전검토 결과 확인 후, 전문 행정사 상담을 통해 실제 신청을 진행할 수 있습니다.",
  },
];

/* NOTE: JSON-LD uses dangerouslySetInnerHTML which is safe here because
   all data comes from compile-time string literals (not user input). */
function PermitJsonLd() {
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
    name: "AI 인허가 사전검토 시스템",
    description:
      "건설업·유사 업종 191개의 등록기준 충족 여부를 AI가 무료로 진단합니다.",
    provider: organizationRef,
    serviceType: "AI 등록기준 진단",
    areaServed: { "@type": "Country", name: "KR" },
    datePublished: "2025-01-01",
    dateModified: "2026-03-14",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "KRW",
      description: "무료 AI 진단",
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
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema("AI 인허가 검토", "/permit")) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(serviceSchema) }}
      />
    </>
  );
}

export default function PermitPage() {
  return (
    <main id="main" className="product-page">
      <PermitJsonLd />
      <Link className="back-link" href="/">
        ← 플랫폼 홈으로
      </Link>

      {/* ── 히어로 ── */}
      <section className="showcase-hero" aria-label="서비스 소개">
        <p className="eyebrow">AI 인허가 검토</p>
        <h1>등록기준 충족 여부,<br />AI가 즉시 점검합니다</h1>
        <p className="showcase-hero-body">
          자본금, 기술인력, 사무실 요건을 항목별로 진단합니다.<br />
          부족 항목과 신규 취득 예상 비용까지 바로 확인하세요.
        </p>
        <div className="showcase-hero-actions">
          <a className="cta-primary cta-large" href="#calculator">
            지금 검토하기 <ArrowRight size={14} aria-hidden="true" />
          </a>
          <Link className="cta-secondary" href="/pricing">
            요금제 보기 <ArrowRight size={14} aria-hidden="true" />
          </Link>
        </div>
      </section>

      {/* ── 계산기 ── */}
      <ScrollAnimate>
        <section id="calculator" className="product-calculator-section" aria-label="AI 인허가 검토기">
          <div className="section-header">
            <p className="eyebrow">AI 인허가 검토</p>
            <h2>등록기준을 즉시 점검하세요</h2>
          </div>
          <Suspense fallback={<div className="calc-skeleton" aria-label="검토기 로딩 중" role="status" />}>
            <PermitCalculator />
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
            <h2>191개 업종, 항목별 즉시 진단</h2>
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
          <h2>지금 바로 등록기준을 점검해 보세요</h2>
          <a className="cta-primary cta-large" href="#calculator">
            등록기준 검토하기 <ArrowRight size={14} aria-hidden="true" />
          </a>
        </section>
      </ScrollAnimate>

      {/* ── FAQ ── */}
      <ScrollAnimate>
        <section className="service-faq" aria-label="자주 묻는 질문">
          <div className="section-header">
            <p className="eyebrow">자주 묻는 질문</p>
            <h2>AI 인허가 검토, 이것이 궁금합니다</h2>
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
          <p>귀사 시스템에 AI 인허가 검토를 도입하고 싶으신가요?</p>
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
