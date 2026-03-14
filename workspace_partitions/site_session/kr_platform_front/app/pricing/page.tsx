import type { Metadata } from "next";
import Link from "next/link";
import { Check, X, ArrowRight, Shield, Zap, Building2 } from "lucide-react";
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
    description: "모든 기능 1개월 무료 체험",
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
    note: "자동 전환 전 이메일 안내, 언제든 해지 가능",
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
    detail: "PCI DSS 준수 PG사 결제, 카드정보 미저장",
  },
  {
    icon: Zap,
    title: "언제든 해지",
    detail: "위약금 없이 다음 결제일 전 자유 해지",
  },
  {
    icon: Building2,
    title: "세금계산서 발행",
    detail: "사업자 회원 전자세금계산서 자동 발행",
  },
];

const comparisonRows: { feature: string; starter: boolean | string; pro: boolean | string; enterprise: boolean | string }[] = [
  { feature: "AI 양도가 산정", starter: true, pro: true, enterprise: true },
  { feature: "AI 인허가 검토", starter: true, pro: true, enterprise: true },
  { feature: "191개 업종 커버", starter: true, pro: true, enterprise: true },
  { feature: "비교 매물 분석", starter: true, pro: true, enterprise: true },
  { feature: "산정 근거 리포트", starter: true, pro: true, enterprise: true },
  { feature: "복합면허 분해 분석", starter: false, pro: true, enterprise: true },
  { feature: "정산 시나리오 (전기·통신·소방)", starter: false, pro: true, enterprise: true },
  { feature: "위젯 임베딩", starter: false, pro: "1 도메인", enterprise: "무제한" },
  { feature: "API 직접 연동", starter: false, pro: false, enterprise: true },
  { feature: "맞춤 브랜딩", starter: false, pro: false, enterprise: true },
  { feature: "전담 매니저", starter: false, pro: false, enterprise: true },
  { feature: "SLA 가용성 보장", starter: false, pro: false, enterprise: "99.9%" },
  { feature: "지원 채널", starter: "이메일", pro: "이메일·전화", enterprise: "전담 매니저" },
];

const pricingFaqs = [
  {
    question: "무료 체험 후 자동으로 결제되나요?",
    answer: "종료 7일 전 이메일 안내, 체험 중 해지 시 결제 없음. 마이페이지에서 클릭 한 번으로 해지.",
  },
  {
    question: "결제 수단은 무엇이 있나요?",
    answer: "신용카드·계좌이체·가상계좌. 사업자는 CMS 자동이체도 가능.",
  },
  {
    question: "환불 정책은 어떻게 되나요?",
    answer: "7일 이내 미이용 시 전액 환불. 이용 시 일할 정산 후 차액 환불.",
  },
  {
    question: "플랜을 변경할 수 있나요?",
    answer: "언제든 업·다운그레이드 가능, 일할 정산.",
  },
  {
    question: "세금계산서를 발행받을 수 있나요?",
    answer: "사업자등록번호 등록 시 매월 자동 발행.",
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
  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: pricingFaqs.map((f) => ({
      "@type": "Question",
      name: f.question,
      acceptedAnswer: { "@type": "Answer", text: f.answer },
    })),
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
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
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
          모든 플랜 동일 AI 엔진, 무제한 무료 체험.
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
                  <Link className={`${plan.ctaStyle} pricing-cta`} href="/billing">
                    {plan.cta} <ArrowRight size={14} aria-hidden="true" />
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

      {/* ── 기능 비교표 ── */}
      <ScrollAnimate delay={120}>
        <section className="pricing-compare" aria-label="기능 비교">
          <div className="section-header">
            <p className="eyebrow">기능 비교</p>
            <h2>플랜별 상세 비교</h2>
          </div>
          <div className="pricing-compare-wrap">
            <table className="pricing-compare-table">
              <thead>
                <tr>
                  <th>기능</th>
                  <th>스타터</th>
                  <th className="pricing-compare-highlight">프로</th>
                  <th>엔터프라이즈</th>
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map((row) => (
                  <tr key={row.feature}>
                    <td>{row.feature}</td>
                    {(["starter", "pro", "enterprise"] as const).map((plan) => (
                      <td key={plan} className={plan === "pro" ? "pricing-compare-highlight" : ""}>
                        {row[plan] === true ? (
                          <Check size={18} className="pricing-check" aria-label="포함" />
                        ) : row[plan] === false ? (
                          <X size={16} className="pricing-x" aria-label="미포함" />
                        ) : (
                          <span className="pricing-compare-text">{row[plan]}</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </ScrollAnimate>

      {/* ── FAQ ── */}
      <ScrollAnimate>
        <section className="service-faq" aria-label="자주 묻는 질문">
          <div className="section-header">
            <p className="eyebrow">자주 묻는 질문</p>
            <h2>요금제, 이것이 궁금합니다</h2>
          </div>
          <div className="faq-list">
            {pricingFaqs.map((f) => (
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
      </ScrollAnimate>
    </main>
  );
}
