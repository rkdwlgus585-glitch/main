import type { Metadata } from "next";
import Link from "next/link";
import { Phone, ArrowRight, ClipboardCheck, Users, Banknote, AlertTriangle } from "lucide-react";
import { platformConfig } from "@/components/platform-config";
import { breadcrumbSchema, organizationRef } from "@/lib/json-ld";
import { ScrollAnimate } from "@/components/scroll-animate";

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
    detail: "건설업뿐 아니라 전기·소방·정보통신 등 유사 업종까지 등록기준을 전수 점검합니다.",
    icon: ClipboardCheck,
  },
  {
    title: "항목별 충족 진단",
    detail: "자본금, 기술인력, 사무실, 장비 등 등록기준 항목별로 충족 여부를 개별 진단합니다.",
    icon: Users,
  },
  {
    title: "신규 취득 비용 산정",
    detail: "면허를 새로 취득할 때 필요한 예상 비용을 등록기준 기반으로 자동 계산합니다.",
    icon: Banknote,
  },
  {
    title: "부족 항목 안내",
    detail: "미충족 항목과 보완 방법을 구체적으로 안내하여 다음 조치를 바로 알 수 있습니다.",
    icon: AlertTriangle,
  },
];

const howItWorks = [
  { step: "01", title: "업종 선택", detail: "191개 업종 중 검토할 업종을 검색하거나 카테고리에서 선택합니다." },
  { step: "02", title: "현황 입력", detail: "자본금, 기술인력, 사무실 보유 여부 등 현재 상태를 입력합니다." },
  { step: "03", title: "AI 진단", detail: "등록기준 전 항목을 대조하여 충족·미충족 여부를 즉시 판정합니다." },
  { step: "04", title: "결과 확인", detail: "종합 진단, 부족 항목, 보완 비용, 다음 조치를 한 화면에서 확인합니다." },
];

const stats = [
  { value: "191개", label: "검토 업종 수", detail: "건설업 전 업종 등록기준 커버" },
  { value: "6,300+", label: "등록기준 항목", detail: "업종별 상세 요건 데이터" },
  { value: "무료", label: "이용 비용", detail: "회원가입 없이 즉시 사용" },
];

const faqs = [
  {
    question: "AI 인허가 검토 비용이 정말 무료인가요?",
    answer:
      "네, AI 인허가 검토는 완전 무료입니다. 별도 회원가입 없이 바로 이용할 수 있습니다.",
  },
  {
    question: "어떤 업종을 검토할 수 있나요?",
    answer:
      "건설업 54개 업종을 포함하여 전기공사업, 소방시설공사업, 정보통신공사업 등 유사 업종까지 총 191개 업종의 등록기준을 검토할 수 있습니다.",
  },
  {
    question: "검토 항목에는 무엇이 포함되나요?",
    answer:
      "자본금(법인/개인), 기술인력 보유 현황, 사무실 요건, 시설·장비 기준, 자격증 요건 등 등록기준 전 항목을 점검합니다.",
  },
  {
    question: "신규 면허 취득 비용도 알 수 있나요?",
    answer:
      "네, 검토 결과에서 해당 업종의 등록기준을 충족하기 위해 필요한 예상 비용(자본금, 인력 채용 등)을 함께 안내합니다.",
  },
  {
    question: "검토 결과로 바로 인허가 신청이 가능한가요?",
    answer:
      "사전검토 결과는 등록기준 충족 여부를 미리 확인하는 것입니다. 실제 인허가 신청은 전문 행정사의 상담을 통해 진행할 수 있으며, 상담 연결을 지원합니다.",
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
          <Link className="cta-primary cta-large" href="/consult">
            무료 상담 신청 <ArrowRight size={14} aria-hidden="true" />
          </Link>
          <Link className="cta-secondary" href="/pricing">
            요금제 보기 <ArrowRight size={14} aria-hidden="true" />
          </Link>
        </div>
      </section>

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
          <p>전문 행정사가 AI 분석 결과를 기반으로 맞춤 상담을 제공합니다.</p>
          <Link className="cta-primary cta-large" href="/consult">
            무료 상담 신청 <ArrowRight size={14} aria-hidden="true" />
          </Link>
        </section>
      </ScrollAnimate>

      {/* ── FAQ ── */}
      <ScrollAnimate>
      <section className="service-faq" aria-label="자주 묻는 질문">
        <div className="section-header">
          <p className="eyebrow">자주 묻는 질문</p>
          <h2>AI 인허가 검토, 이것이 궁금합니다</h2>
        </div>
        <dl className="faq-list">
          {faqs.map((f) => (
            <div className="faq-item" key={f.question}>
              <dt>{f.question}</dt>
              <dd>{f.answer}</dd>
            </div>
          ))}
        </dl>
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
