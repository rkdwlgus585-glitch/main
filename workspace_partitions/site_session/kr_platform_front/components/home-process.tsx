const steps = [
  {
    title: "서비스 선택",
    body: "양도가 산정 또는 인허가 검토 선택",
  },
  {
    title: "AI 즉시 분석",
    body: "공시 데이터 기반 가격·기준 즉시 분석",
  },
  {
    title: "전문가 상담",
    body: "전문 행정사가 협상·절차 안내",
  },
  {
    title: "거래 완료",
    body: "계약부터 관할 기관 접수까지 원스톱",
  },
];

export function HomeProcess() {
  return (
    <section className="home-process-section" aria-label="이용 절차">
      <div className="section-header">
        <p className="eyebrow">이용 절차</p>
        <h2>4단계로 완료되는 건설업 면허 취득</h2>
      </div>

      <div className="home-process-grid">
        {steps.map((step, index) => (
          <article key={step.title} className="home-process-card">
            <div className="home-process-header">
              <span className="home-process-index">{String(index + 1).padStart(2, "0")}</span>
              <h3>{step.title}</h3>
            </div>
            <p>{step.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
