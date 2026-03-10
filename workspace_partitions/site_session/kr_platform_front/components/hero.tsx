import Link from "next/link";

export function Hero() {
  return (
    <section className="hero-shell">
      <div className="hero-copy">
        <p className="eyebrow">건설업 AI 전문 플랫폼</p>
        <h1>
          건설업 면허 양도가격,
          <br />
          <span className="hero-accent">AI가 바로 산정합니다</span>
        </h1>
        <p className="hero-body">
          기존 면허 양도가 산정부터 신규 등록 비용 계산까지.
          행정사 방문 없이, 데이터 기반으로 즉시 확인하세요.
        </p>
        <div className="hero-actions">
          <Link className="cta-primary" href="/yangdo">
            무료 양도가 산정 시작
          </Link>
          <Link className="cta-secondary" href="/permit">
            건설업등록 시작
          </Link>
        </div>
      </div>
      <div className="hero-stats">
        <div className="stat-card">
          <strong className="stat-number">2,400+</strong>
          <span className="stat-label">분석 완료 건수</span>
        </div>
        <div className="stat-card">
          <strong className="stat-number">191개</strong>
          <span className="stat-label">진단 가능 업종</span>
        </div>
        <div className="stat-card">
          <strong className="stat-number">실시간</strong>
          <span className="stat-label">공시 데이터 반영</span>
        </div>
      </div>
    </section>
  );
}
