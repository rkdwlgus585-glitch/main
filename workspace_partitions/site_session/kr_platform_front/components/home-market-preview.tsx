import Link from "next/link";
import { ArrowRight, BarChart3, Building2, FileSearch, TrendingUp } from "lucide-react";

const highlights = [
  {
    icon: Building2,
    title: "전 업종 커버",
    body: "건축, 토목, 전기, 소방, 조경 등 건설업 전 업종 매물을 한 곳에서 확인합니다.",
  },
  {
    icon: TrendingUp,
    title: "실적·재무 검증",
    body: "3개년 실적 추이와 재무 상태를 사전 점검한 매물만 안내합니다.",
  },
  {
    icon: BarChart3,
    title: "AI 양도가 참고",
    body: "시장 데이터 기반 AI 분석으로 적정 가격대를 파악한 뒤 상담을 시작합니다.",
  },
  {
    icon: FileSearch,
    title: "조건 맞춤 탐색",
    body: "업종, 지역, 실적 규모 등 원하는 조건으로 빠르게 필터링할 수 있습니다.",
  },
];

export function HomeMarketPreview() {
  return (
    <section className="market-brief-section" id="market-brief" aria-label="실시간 매물 안내">
      <div className="market-brief-header">
        <div className="section-header">
          <p className="eyebrow">실시간 매물</p>
          <h2>검증된 건설업 면허 매물을 한 곳에서 확인하세요</h2>
        </div>
        <p className="market-brief-subtitle">
          업종별 양도양수 매물 현황을 실시간으로 업데이트합니다.
          AI 분석 데이터와 함께 조건에 맞는 매물을 빠르게 찾아보세요.
        </p>
      </div>

      <div className="market-highlights-grid">
        {highlights.map(({ icon: Icon, title, body }) => (
          <article key={title} className="market-highlight-card">
            <span className="market-highlight-icon">
              <Icon size={20} />
            </span>
            <h3>{title}</h3>
            <p>{body}</p>
          </article>
        ))}
      </div>

      <div className="market-brief-cta">
        <Link href="/mna-market" className="cta-primary">
          매물 현황 보기
          <ArrowRight size={18} strokeWidth={2.2} />
        </Link>
        <Link href="/yangdo" className="cta-secondary market-cta-secondary">
          AI 양도가 산정 먼저 해보기
        </Link>
      </div>
    </section>
  );
}
