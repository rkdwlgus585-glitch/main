import type { Metadata } from "next";
import Link from "next/link";
import { BarChart3, Search, Tag, Target } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { platformConfig } from "@/components/platform-config";
import { breadcrumbSchema, organizationRef, siteBase, websiteRef } from "@/lib/json-ld";

const pageTitle = "실시간 매물 | 서울건설정보";
const pageDescription =
  "건설업 면허 양도양수 매물을 한눈에 확인하세요. 전문 행정사가 검증한 실매물과 AI 양도가 분석을 함께 제공합니다.";

export const metadata: Metadata = {
  title: pageTitle,
  description: pageDescription,
  alternates: { canonical: "/mna-market" },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    url: "/mna-market",
    type: "website",
    locale: "ko_KR",
  },
  twitter: {
    card: "summary",
    title: pageTitle,
    description: pageDescription,
  },
};

const marketFeatures: Array<{
  title: string;
  description: string;
  icon: LucideIcon;
}> = [
  {
    title: "실매물 리스트",
    description: "양도인이 직접 등록하거나 전문 행정사가 검증한 매물만 게시합니다. 허위·중복 매물은 자동 필터링됩니다.",
    icon: Search,
  },
  {
    title: "AI 양도가 참고",
    description: "각 매물의 호가와 AI 산정가를 비교하여, 적정 가격 여부를 즉시 판단할 수 있습니다.",
    icon: BarChart3,
  },
  {
    title: "업종별 분류",
    description: "토목·건축·전기·소방·정보통신 등 업종별로 매물을 분류하여, 원하는 면허를 빠르게 찾습니다.",
    icon: Tag,
  },
  {
    title: "매칭 추천",
    description: "양수인의 조건(자본금, 기술인력, 원하는 업종)에 맞는 매물을 자동으로 추천합니다.",
    icon: Target,
  },
];

const stats = [
  { label: "누적 등록 매물", value: "450+", suffix: "건" },
  { label: "월 평균 매칭", value: "80+", suffix: "건" },
  { label: "평균 매칭 소요", value: "3.2", suffix: "일" },
  { label: "매물 검증률", value: "100", suffix: "%" },
];
/** 통계는 서비스 목표치 기반 참고 수치이며, 실제 운영 데이터와 다를 수 있습니다. */
const STATS_DISCLAIMER = "위 수치는 서비스 목표 기반의 참고 수치입니다.";

/* NOTE: JSON-LD uses dangerouslySetInnerHTML which is safe here because
   all data comes from compile-time string literals (not user input). */
function MarketJsonLd() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: pageTitle,
    description: pageDescription,
    url: `${siteBase}/mna-market`,
    isPartOf: websiteRef,
    about: {
      "@type": "Service",
      name: "건설업 면허 양도양수 매물 중개",
      description: "전문 행정사가 검증한 건설업 면허 매물 리스트와 AI 양도가 분석을 함께 제공합니다.",
      provider: organizationRef,
    },
  };
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema("양도양수 매물", "/mna-market")) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
    </>
  );
}

export default function MnaMarketPage() {
  return (
    <main id="main" className="page-shell">
      <MarketJsonLd />
      <Link className="back-link" href="/">
        ← 플랫폼 홈으로
      </Link>

      <section className="market-hero" aria-label="매물 소개">
        <p className="eyebrow">양도양수 매물</p>
        <h1>건설업 면허 매물,<br />한 곳에서 비교하세요</h1>
        <p className="market-hero-body">
          서울건설정보가 수집·검증한 건설업 면허 매물을 확인하고,
          AI 양도가 분석으로 적정 가격을 미리 파악하세요.
        </p>
        <a
          className="cta-primary"
          href={platformConfig.listingHost}
          target="_blank"
          rel="noreferrer noopener"
        >
          실시간 매물 바로가기 →
        </a>
      </section>

      <section className="market-stats" aria-label="매물 통계">
        {stats.map((s) => (
          <div key={s.label} className="market-stat-card">
            <span className="market-stat-value">
              {s.value}<small>{s.suffix}</small>
            </span>
            <span className="market-stat-label">{s.label}</span>
          </div>
        ))}
        <p className="market-stats-disclaimer">{STATS_DISCLAIMER}</p>
      </section>

      <section className="market-features" aria-label="주요 기능">
        <div className="section-header">
          <p className="eyebrow">주요 기능</p>
          <h2>실시간 매물이 특별한 이유</h2>
        </div>
        <div className="features-grid">
          {marketFeatures.map(({ title, description, icon: Icon }) => (
            <div key={title} className="feature-card">
              <span className="feature-icon" aria-hidden="true"><Icon size={22} /></span>
              <h3>{title}</h3>
              <p>{description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="market-bridge" aria-label="양도가 산정 안내">
        <div className="bridge-card">
          <div className="bridge-content">
            <h2>매물을 찾기 전에,<br />적정 가격부터 확인하세요</h2>
            <p>
              AI 양도가 산정으로 업종별 시세를 미리 파악하면,
              과도한 호가를 걸러내고 합리적 협상이 가능합니다.
            </p>
            <div className="bridge-actions">
              <Link className="cta-primary" href="/yangdo">
                양도가 먼저 산정하기
              </Link>
              <a
                className="cta-secondary"
                href={platformConfig.listingHost}
                target="_blank"
                rel="noreferrer noopener"
              >
                실시간 매물 둘러보기
              </a>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
