import type { Metadata } from "next";
import Link from "next/link";
import { platformConfig, widgetUrl } from "@/components/platform-config";
import { breadcrumbSchema, organizationRef } from "@/lib/json-ld";
import { WidgetFrame } from "@/components/widget-frame";

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
    detail: "건설업 공시 실적 데이터를 실시간 반영하여 객관적인 가격 범위를 산정합니다.",
  },
  {
    title: "복합면허 자동 분해",
    detail: "2개 이상 업종이 결합된 복합면허도 업종별 기여도를 자동 분석합니다.",
  },
  {
    title: "중복매물 보정",
    detail: "동일 면허가 여러 사이트에 중복 등록된 경우를 자동 감지하고 가격에 반영합니다.",
  },
  {
    title: "산정 근거 투명 공개",
    detail: "비교군 선정, 보정 계수, 신뢰도 계산 과정을 모두 공개하여 검증 가능합니다.",
  },
];

const faqs = [
  {
    question: "양도가 산정 비용이 정말 무료인가요?",
    answer:
      "네, AI 양도가 산정은 완전 무료입니다. 별도 회원가입이나 결제 없이 바로 이용할 수 있습니다.",
  },
  {
    question: "산정 결과는 얼마나 정확한가요?",
    answer:
      "건설업 공시 실적 데이터와 시장 거래 패턴을 분석하여 산정합니다. 산정 결과에는 신뢰도 지표가 함께 표시되어, 결과의 정확도를 직접 판단할 수 있습니다.",
  },
  {
    question: "복합면허도 산정이 가능한가요?",
    answer:
      "네, 2개 이상의 업종이 결합된 복합면허도 업종별 기여도를 분해하여 정밀 산정합니다. 매칭 오차 감점까지 자동 반영됩니다.",
  },
  {
    question: "전기·소방·정보통신 특수 업종도 되나요?",
    answer:
      "전기공사업, 소방시설공사업, 정보통신공사업 등 특수 업종은 업종별 정산 정책과 별도 신뢰도 기준이 적용됩니다.",
  },
  {
    question: "산정 후 상담도 연결되나요?",
    answer:
      "AI 산정 결과를 바탕으로 건설업 전문 행정사의 맞춤 상담을 바로 연결해 드립니다. 양도가 협상 전략까지 지원합니다.",
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
    name: "건설업 AI 양도가 산정",
    description: "건설업 면허 양도가격을 공시 데이터 기반 AI가 무료로 산정합니다.",
    provider: organizationRef,
    serviceType: "AI 가격 산정",
    areaServed: { "@type": "Country", name: "KR" },
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

      {/* ── 서비스 소개 ── */}
      <section className="service-intro" aria-label="서비스 소개">
        <p className="eyebrow">AI 양도가 산정</p>
        <h1>
          건설업 면허 양도가,
          <br />
          데이터로 바로 확인하세요
        </h1>
        <p className="service-intro-body">
          행정사 방문 없이 공시 실적 기반으로 양도가 범위를 즉시 산정합니다. 복합면허
          분해, 중복매물 보정, 신뢰도 지표까지 한 번에 확인하세요.
        </p>
      </section>

      {/* ── 특징 그리드 ── */}
      <section className="service-features" aria-label="서비스 특징">
        <div className="features-grid">
          {features.map((f) => (
            <div className="feature-item" key={f.title}>
              <h3>{f.title}</h3>
              <p>{f.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── 위젯 실행 ── */}
      <WidgetFrame
        title="건설업 AI 양도가 산정"
        description="서울건설정보 메인 플랫폼에서 실제 양도가 산정 위젯을 바로 실행하고 상담 연결까지 이어집니다."
        widgetUrl={widgetUrl("yangdo")}
        openUrl="/widget/yangdo"
        eyebrow="양도가 실행 화면"
        launchLabel="양도가 산정 실행"
        gateNote="페이지 진입만으로는 외부 엔진 호출이 시작되지 않습니다. 실제 산정을 원할 때만 실행을 시작합니다."
      />

      {/* ── FAQ ── */}
      <section className="service-faq" aria-label="자주 묻는 질문">
        <div className="section-header">
          <p className="eyebrow">자주 묻는 질문</p>
          <h2>양도가 산정, 이것이 궁금합니다</h2>
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

      {/* ── 하단 CTA ── */}
      <section className="service-bottom-cta" aria-label="상담 안내">
        <p>AI 산정 결과를 기반으로 전문 상담을 원하시나요?</p>
        <div className="service-bottom-actions">
          <a className="cta-primary" href={`tel:${platformConfig.contactPhone}`}>
            {platformConfig.contactPhone} 전화 상담
          </a>
          <Link className="cta-secondary" href="/consult">
            고객센터 보기
          </Link>
        </div>
      </section>
    </main>
  );
}
