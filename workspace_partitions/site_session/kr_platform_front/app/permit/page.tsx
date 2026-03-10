import type { Metadata } from "next";
import Link from "next/link";
import { platformConfig, widgetUrl } from "@/components/platform-config";
import { WidgetFrame } from "@/components/widget-frame";

const pageTitle = "건설업등록 검토 | 서울건설정보";
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
  },
  {
    title: "항목별 충족 진단",
    detail: "자본금, 기술인력, 사무실, 장비 등 등록기준 항목별로 충족 여부를 개별 진단합니다.",
  },
  {
    title: "신규 취득 비용 산정",
    detail: "면허를 새로 취득할 때 필요한 예상 비용을 등록기준 기반으로 자동 계산합니다.",
  },
  {
    title: "부족 항목 안내",
    detail: "미충족 항목과 보완 방법을 구체적으로 안내하여 다음 조치를 바로 알 수 있습니다.",
  },
];

const faqs = [
  {
    question: "인허가 사전검토 비용이 정말 무료인가요?",
    answer:
      "네, AI 인허가 사전검토는 완전 무료입니다. 별도 회원가입이나 결제 없이 바로 이용할 수 있습니다.",
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
    name: "등록기준 AI 인허가 사전검토",
    description:
      "건설업·유사 업종 191개의 등록기준 충족 여부를 AI가 무료로 진단합니다.",
    provider: {
      "@type": "Organization",
      name: "서울건설정보",
      url: platformConfig.platformFrontHost,
    },
    serviceType: "AI 등록기준 진단",
    areaServed: { "@type": "Country", name: "KR" },
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
        플랫폼 홈으로
      </Link>

      {/* ── 서비스 소개 ── */}
      <section className="service-intro" aria-label="서비스 소개">
        <p className="eyebrow">건설업등록 검토</p>
        <h1>
          등록기준 충족 여부,
          <br />
          AI가 즉시 점검합니다
        </h1>
        <p className="service-intro-body">
          건설업 면허 취득에 필요한 자본금, 기술인력, 사무실 요건을 항목별로
          진단합니다. 부족 항목과 신규 취득 예상 비용까지 바로 확인하세요.
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
        title="등록기준 AI 인허가 사전검토"
        description="등록기준 충족 여부를 메인 플랫폼에서 바로 검토하고, 부족 항목과 다음 조치를 즉시 확인할 수 있는 진입면입니다."
        widgetUrl={widgetUrl("permit")}
        openUrl="/widget/permit"
        eyebrow="건설업등록 검토 화면"
        launchLabel="건설업등록 검토 실행"
        gateNote="페이지 진입만으로는 외부 엔진 호출이 시작되지 않습니다. 점검을 원할 때만 실행을 시작합니다."
      />

      {/* ── FAQ ── */}
      <section className="service-faq" aria-label="자주 묻는 질문">
        <div className="section-header">
          <p className="eyebrow">자주 묻는 질문</p>
          <h2>인허가 사전검토, 이것이 궁금합니다</h2>
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
        <p>등록기준 진단 후 전문 상담을 원하시나요?</p>
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
