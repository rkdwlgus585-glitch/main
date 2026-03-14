import type { Metadata } from "next";
import Link from "next/link";
import { Check, ArrowRight, Shield, Zap, Building2 } from "lucide-react";
import { platformConfig } from "@/components/platform-config";
import { breadcrumbSchema, organizationRef, siteBase } from "@/lib/json-ld";
import { ScrollAnimate } from "@/components/scroll-animate";

const pageTitle = "요금제 | 서울건설정보";
const pageDescription =
  "AI 양도가 산정·AI 인허가 검토 시스템 구독 요금제. 1개월 무료 체험 후 자동 전환. 행정사사무소·건설 컨설팅 맞춤 플랜.";

export const metadata: Metadata = {
  title: pageTitle,
  description: pageDescription,
  alternates: { canonical: "/pricing" },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    url: "/pricing",
    type: "website",
    locale: "ko_KR",
  },
  twitter: {
    card: "summary",
    title: pageTitle,
    description: pageDescription,
  },
};

const plans = [
  {
    id: "starter",
    name: "스타터",
    price: "무료",
    period: "1개월 체험",
    description: "AI 시스템을 직접 경험해 보세요. 모든 기능을 1개월간 무료로 이용할 수 있습니다.",
    cta: "무료 체험 시작",
    ctaStyle: "cta-secondary" as const,
    highlight: false,
    features: [
      "AI 양도가 산정 무제한",
      "AI 인허가 검토 무제한",
      "191개 업종 전수 커버",
      "비교 매물 분석",
      "산정 근거 리포트",
      "이메일 지원",
    ],
    note: "체험 종료 후 프로 플랜으로 자동 전환됩니다. 전환 전 이메일로 안내드리며, 언제든 해지할 수 있습니다.",
  },
  {
    id: "pro",
    name: "프로",
    price: "99,000",
    period: "월",
    description: "행정사사무소·건설 컨설팅 실무에 최적화된 플랜입니다.",
    cta: "무료 체험 후 시작",
    ctaStyle: "cta-primary" as const,
    highlight: true,
    badge: "추천",
    features: [
      "AI 양도가 산정 무제한",
      "AI 인허가 검토 무제한",
      "191개 업종 전수 커버",
      "비교 매물 분석",
      "산정 근거 리포트",
      "복합면허 분해 분석",
      "정산 시나리오 (전기·통신·소방)",
      "우선 이메일·전화 지원",
      "위젯 임베딩 1개 도메인",
    ],
  },
  {
    id: "enterprise",
    name: "엔터프라이즈",
    price: "별도 협의",
    period: "",
    description: "대형 사무소·기관·다수 지점 운영에 맞춤 설계됩니다.",
    cta: "도입 상담 요청",
    ctaStyle: "cta-secondary" as const,
    highlight: false,
    features: [
      "프로 플랜 전체 기능",
      "멀티 도메인 위젯 임베딩",
      "API 직접 연동",
      "맞춤 브랜딩 적용",
      "전담 매니저 배정",
      "SLA 99.9% 가용성 보장",
      "온보딩 교육·기술 지원",
      "월간 시장 분석 리포트",
    ],
  },
];

const guarantees = [
  {
    icon: Shield,
    title: "안전한 결제",
    detail: "PCI DSS 준수 PG사를 통한 결제로 카드정보가 서버에 저장되지 않습니다.",
  },
  {
    icon: Zap,
    title: "언제든 해지",
    detail: "위약금 없이 다음 결제일 전까지 자유롭게 해지할 수 있습니다.",
  },
  {
    icon: Building2,
    title: "세금계산서 발행",
    detail: "사업자 회원에게 전자세금계산서를 자동 발행합니다.",
  },
];

const pricingFaqs = [
  {
    question: "무료 체험 후 자동으로 결제되나요?",
    answer:
      "네, 무료 체험 종료 7일 전에 이메일로 안내드리며, 체험 기간 내 해지하시면 결제되지 않습니다. 해지는 마이페이지에서 클릭 한 번으로 가능합니다.",
  },
  {
    question: "결제 수단은 무엇이 있나요?",
    answer:
      "신용카드(국내/해외), 계좌이체, 가상계좌를 지원합니다. 사업자 회원은 CMS 자동이체도 가능합니다.",
  },
  {
    question: "환불 정책은 어떻게 되나요?",
    answer:
      "결제일로부터 7일 이내 서비스 미이용 시 전액 환불됩니다. 이용 이력이 있는 경우 일할 계산하여 차액을 환불합니다.",
  },
  {
    question: "플랜을 변경할 수 있나요?",
    answer:
      "언제든 업그레이드 또는 다운그레이드가 가능합니다. 변경 시 일할 정산됩니다.",
  },
  {
    question: "세금계산서를 발행받을 수 있나요?",
    answer:
      "사업자등록번호를 등록한 회원에게 매월 자동으로 전자세금계산서를 발행합니다.",
  },
];

/*
 * NOTE: JSON-LD uses dangerouslySetInnerHTML which is safe here because
 * all data comes from compile-time string literals — no user input is
 * interpolated. This is the standard Next.js pattern for structured data.
 */
function PricingJsonLd() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: "AI 건설업 분석 시스템 요금제",
    description: pageDescription,
    url: `${siteBase}/pricing`,
    provider: organizationRef,
  };
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema("요금제", "/pricing")) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
    </>
  );
}

export default function PricingPage() {
  return (
    <main id="main" className="page-shell">
      <PricingJsonLd />
      <Link className="back-link" href="/">
        ← 플랫폼 홈으로
      </Link>

      {/* ── 히어로 ── */}
      <section className="pricing-hero" aria-label="요금제 안내">
        <p className="eyebrow">요금제</p>
        <h1>1개월 무료 체험으로 시작하세요</h1>
        <p className="pricing-hero-body">
          모든 플랜은 동일한 AI 엔진을 사용합니다.<br />
          무료 체험 기간 동안 모든 기능을 제한 없이 이용할 수 있습니다.
        </p>
      </section>

      {/* ── 요금 카드 ── */}
      <ScrollAnimate>
        <section className="pricing-cards" aria-label="구독 플랜">
          <div className="pricing-grid">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className={`pricing-card${plan.highlight ? " pricing-card--highlight" : ""}`}
              >
                {plan.badge && <span className="pricing-badge">{plan.badge}</span>}
                <h2 className="pricing-plan-name">{plan.name}</h2>
                <div className="pricing-price">
                  {plan.price === "별도 협의" ? (
                    <span className="pricing-amount pricing-amount--custom">{plan.price}</span>
                  ) : (
                    <>
                      {plan.price !== "무료" && <span className="pricing-currency">&#8361;</span>}
                      <span className="pricing-amount">{plan.price}</span>
                      {plan.period && <span className="pricing-period">/{plan.period}</span>}
                    </>
                  )}
                </div>
                <p className="pricing-description">{plan.description}</p>
                {plan.id === "enterprise" ? (
                  <Link className={`${plan.ctaStyle} pricing-cta`} href="/partners">
                    {plan.cta} <ArrowRight size={14} aria-hidden="true" />
                  </Link>
                ) : (
                  <Link className={`${plan.ctaStyle} pricing-cta`} href="/consult">
                    {plan.cta}
                  </Link>
                )}
                <ul className="pricing-features">
                  {plan.features.map((f) => (
                    <li key={f}>
                      <Check size={16} aria-hidden="true" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                {plan.note && <p className="pricing-note">{plan.note}</p>}
              </div>
            ))}
          </div>
        </section>
      </ScrollAnimate>

      {/* ── 안심 보장 ── */}
      <ScrollAnimate delay={80}>
        <section className="pricing-guarantees" aria-label="안심 보장">
          <div className="section-header">
            <p className="eyebrow">안심 보장</p>
            <h2>투명하고 안전한 결제</h2>
          </div>
          <div className="pricing-guarantees-grid">
            {guarantees.map((g) => (
              <div key={g.title} className="pricing-guarantee-card">
                <span className="pricing-guarantee-icon" aria-hidden="true">
                  <g.icon size={24} />
                </span>
                <h3>{g.title}</h3>
                <p>{g.detail}</p>
              </div>
            ))}
          </div>
        </section>
      </ScrollAnimate>

      {/* ── FAQ ── */}
      <section className="service-faq" aria-label="자주 묻는 질문">
        <div className="section-header">
          <p className="eyebrow">자주 묻는 질문</p>
          <h2>요금제, 이것이 궁금합니다</h2>
        </div>
        <dl className="faq-list">
          {pricingFaqs.map((f) => (
            <div className="faq-item" key={f.question}>
              <dt>{f.question}</dt>
              <dd>{f.answer}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* ── 하단 CTA ── */}
      <section className="service-bottom-cta" aria-label="문의 안내">
        <p>대규모 도입이나 맞춤 견적이 필요하신가요?</p>
        <div className="service-bottom-actions">
          <Link className="cta-primary" href="/partners">
            도입 상담 요청
          </Link>
          <a className="cta-secondary" href={`tel:${platformConfig.contactPhone}`}>
            {platformConfig.contactPhone}
          </a>
        </div>
      </section>
    </main>
  );
}
