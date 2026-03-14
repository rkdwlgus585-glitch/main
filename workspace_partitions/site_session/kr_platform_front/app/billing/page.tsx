import type { Metadata } from "next";
import Link from "next/link";
import { Check, ArrowRight, CreditCard, Shield, Zap } from "lucide-react";
import { platformConfig } from "@/components/platform-config";
import { breadcrumbSchema, siteBase } from "@/lib/json-ld";
import { ScrollAnimate } from "@/components/scroll-animate";
import { PRO_PLAN_AMOUNT } from "@/lib/subscription-types";

const pageTitle = "구독 관리 | 서울건설정보";
const pageDescription = "AI 양도가 산정·인허가 검토 시스템 구독을 시작하세요. 1개월 무료 체험, 신용카드 간편 결제.";

export const metadata: Metadata = {
  title: pageTitle,
  description: pageDescription,
  alternates: { canonical: "/billing" },
  robots: { index: false, follow: false },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    url: "/billing",
    type: "website",
    locale: "ko_KR",
  },
};

const proFeatures = [
  "AI 양도가 산정 무제한",
  "AI 인허가 검토 무제한",
  "191개 업종 전수 커버",
  "복합면허 분해 분석",
  "정산 시나리오 (전기·통신·소방)",
  "우선 이메일·전화 지원",
  "위젯 임베딩 1개 도메인",
];

const guarantees = [
  { icon: CreditCard, text: "PCI DSS 준수 토스페이먼츠 결제" },
  { icon: Shield, text: "카드정보 서버 미저장" },
  { icon: Zap, text: "위약금 없이 언제든 해지" },
];

/*
 * NOTE: JSON-LD uses dangerouslySetInnerHTML which is safe here because
 * all data comes from compile-time string literals — no user input is
 * interpolated. This is the standard Next.js pattern for structured data.
 */
function BillingJsonLd() {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(breadcrumbSchema("구독 관리", "/billing")),
      }}
    />
  );
}

export default function BillingPage() {
  const formattedPrice = PRO_PLAN_AMOUNT.toLocaleString("ko-KR");

  return (
    <main id="main" className="page-shell">
      <BillingJsonLd />
      <Link className="back-link" href="/pricing">
        ← 요금제 보기
      </Link>

      <section className="billing-hero" aria-label="구독 시작">
        <p className="eyebrow">구독 관리</p>
        <h1>Pro 플랜 시작하기</h1>
        <p className="billing-hero-body">
          1개월 무료 체험 후 월 ₩{formattedPrice}
        </p>
      </section>

      <ScrollAnimate>
        <section className="billing-plan-card" aria-label="Pro 플랜 상세">
          <div className="billing-card">
            <div className="billing-card-header">
              <span className="pricing-badge">추천</span>
              <h2>프로</h2>
              <div className="billing-price">
                <span className="pricing-currency">₩</span>
                <span className="pricing-amount">{formattedPrice}</span>
                <span className="pricing-period">/월</span>
              </div>
              <p className="billing-trial-note">
                첫 1개월 무료 · 자동 전환 전 이메일 안내
              </p>
            </div>

            <ul className="billing-features">
              {proFeatures.map((f) => (
                <li key={f}>
                  <Check size={16} aria-hidden="true" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>

            <Link className="cta-primary cta-large billing-cta" href="/billing/checkout">
              무료 체험 시작 <ArrowRight size={14} aria-hidden="true" />
            </Link>
          </div>
        </section>
      </ScrollAnimate>

      <ScrollAnimate delay={80}>
        <section className="billing-guarantees" aria-label="결제 안심">
          <div className="billing-guarantees-row">
            {guarantees.map((g) => (
              <div key={g.text} className="billing-guarantee">
                <g.icon size={20} aria-hidden="true" />
                <span>{g.text}</span>
              </div>
            ))}
          </div>
        </section>
      </ScrollAnimate>

      <ScrollAnimate delay={80}>
        <section className="service-bottom-cta" aria-label="문의">
          <p>엔터프라이즈 도입이나 맞춤 견적이 필요하신가요?</p>
          <div className="service-bottom-actions">
            <Link className="cta-secondary" href="/partners">
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
