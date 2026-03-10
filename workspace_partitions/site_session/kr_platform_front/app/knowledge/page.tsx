import type { Metadata } from "next";
import Link from "next/link";
import { platformConfig } from "@/components/platform-config";

const pageTitle = "건설실무 | 서울건설정보";
const pageDescription =
  "건설업 양도양수, 인허가, 등록기준, 시장 동향까지 — 건설업 전문 AI 플랫폼이 제공하는 실무 지식 콘텐츠.";

export const metadata: Metadata = {
  title: pageTitle,
  description: pageDescription,
  alternates: { canonical: "/knowledge" },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    url: "/knowledge",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: pageTitle,
    description: pageDescription,
  },
};

interface Article {
  title: string;
  slug: string;
}

const categories: {
  title: string;
  description: string;
  articles: Article[];
  icon: string;
  categorySlug: string;
}[] = [
  {
    title: "건설업 양도양수",
    description: "면허 양도가 산정 기준, 양수인 요건, 실거래 동향, 복합면허 전략까지 양도양수 실무의 핵심.",
    categorySlug: "양도양수",
    articles: [
      { title: "건설업 면허 양도가, 어떻게 정해지는가", slug: "양도가-산정-기준" },
      { title: "복합면허 양도 시 감점 반영 원리", slug: "복합면허-감점-반영" },
      { title: "전기공사업 양도양수 특수 정산 방식", slug: "전기공사업-특수-정산" },
      { title: "양도양수 절차 체크리스트 (2026년 기준)", slug: "양도양수-절차-체크리스트" },
    ],
    icon: "📊",
  },
  {
    title: "인허가 · 등록기준",
    description: "191개 업종별 등록기준 해설, 자본금·기술인력·시설 요건, 신규 취득 비용 산정 가이드.",
    categorySlug: "인허가-등록기준",
    articles: [
      { title: "건설업 등록기준 항목별 해설 (자본금·인력·시설)", slug: "등록기준-항목별-해설" },
      { title: "소방시설공사업 등록기준과 특수 요건", slug: "소방시설공사업-등록기준" },
      { title: "정보통신공사업 자격 요건 변경사항 정리", slug: "정보통신공사업-자격-변경" },
      { title: "신규 면허 취득 비용, AI로 미리 계산하기", slug: "신규-면허-취득-비용" },
    ],
    icon: "📋",
  },
  {
    title: "시장 동향 · 분석",
    description: "면허 시장 가격 추이, 업종별 수요 변화, 계절성 패턴, 정책 변경 영향 분석.",
    categorySlug: "시장-동향",
    articles: [
      { title: "2026년 건설업 면허 시장 전망", slug: "2026-면허-시장-전망" },
      { title: "업종별 양도가 추이 — 상승 vs 하락 업종", slug: "업종별-양도가-추이" },
      { title: "건설업 면허 가격에 영향을 주는 5가지 요인", slug: "면허-가격-영향-요인" },
      { title: "공시 실적 변동과 양도가의 상관관계", slug: "공시-실적-양도가-상관관계" },
    ],
    icon: "📈",
  },
  {
    title: "법률 · 규정",
    description: "건설산업기본법, 시행령/시행규칙 개정 사항, 행정 해석, 판례 요약.",
    categorySlug: "법률-규정",
    articles: [
      { title: "건설산업기본법 주요 조항 해설", slug: "건설산업기본법-조항-해설" },
      { title: "최근 시행령 개정이 양도양수에 미치는 영향", slug: "시행령-개정-영향" },
      { title: "건설업 면허 취소·정지 사유 정리", slug: "면허-취소-정지-사유" },
      { title: "인허가 반려 사례와 대응 방법", slug: "인허가-반려-사례-대응" },
    ],
    icon: "⚖️",
  },
];

/* NOTE: JSON-LD uses dangerouslySetInnerHTML which is safe here because
   all data comes from compile-time string literals (not user input). */
function KnowledgeJsonLd() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: pageTitle,
    description: pageDescription,
    url: `${platformConfig.platformFrontHost}/knowledge`,
    isPartOf: {
      "@type": "WebSite",
      name: "서울건설정보",
      url: platformConfig.platformFrontHost,
    },
    about: [
      { "@type": "Thing", name: "건설업 양도양수" },
      { "@type": "Thing", name: "건설업 인허가" },
      { "@type": "Thing", name: "건설업 등록기준" },
      { "@type": "Thing", name: "건설업 시장 동향" },
    ],
  };
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

export default function KnowledgePage() {
  return (
    <main id="main" className="page-shell">
      <KnowledgeJsonLd />
      <Link className="back-link" href="/">
        ← 플랫폼 홈으로
      </Link>

      <section className="knowledge-hero" aria-label="건설실무 소개">
        <p className="eyebrow">건설실무</p>
        <h1>건설업 전문가 수준의 지식,<br />누구나 쉽게 이해하도록</h1>
        <p className="knowledge-hero-body">
          서울건설정보가 보유한 공시 데이터와 실무 경험을 바탕으로
          건설업 양도양수, 인허가, 시장 동향을 정리했습니다.
        </p>
      </section>

      <div className="knowledge-grid" role="region" aria-label="지식 카테고리">
        {categories.map((cat) => (
          <div key={cat.title} className="knowledge-card">
            <div className="knowledge-card-header">
              <span className="knowledge-icon" aria-hidden="true">{cat.icon}</span>
              <h2>{cat.title}</h2>
            </div>
            <p className="knowledge-card-desc">{cat.description}</p>
            <ul className="knowledge-articles">
              {cat.articles.map((a) => (
                <li key={a.slug}>
                  <a
                    href={`${platformConfig.contentHost}/category/건설업-지식/${cat.categorySlug}/${a.slug}`}
                    rel="noreferrer noopener"
                  >
                    {a.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <section className="knowledge-cta" aria-label="블로그 안내">
        <p>
          더 많은 건설실무 콘텐츠는 블로그에서 확인하세요.
        </p>
        <a
          className="cta-primary"
          href={`${platformConfig.contentHost}/category/건설업-지식`}
          rel="noreferrer noopener"
        >
          블로그에서 더 보기 →
        </a>
      </section>
    </main>
  );
}
