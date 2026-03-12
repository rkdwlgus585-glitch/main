const steps = [
  {
    title: "AI 양도가 산정 · AI 인허가 검토",
    body: "AI가 면허 적정 가격을 산정하고, 등록기준 충족 여부를 즉시 점검합니다.",
  },
  {
    title: "AI 분석 실행",
    body: "AI 양도가 산정 시스템이 시장 데이터를 기반으로 적정 가격대를 분석하고, AI 인허가 검토로 등록기준 충족 여부를 점검합니다.",
  },
  {
    title: "전문가 상담 연결",
    body: "분석 결과를 바탕으로 건설업 전문 행정사가 양도양수 조건 협상과 절차를 안내합니다.",
  },
  {
    title: "거래 완료까지 지원",
    body: "계약, 서류 준비, 관할 기관 접수까지 원스톱으로 진행을 도와드립니다.",
  },
];

export function HomeProcess() {
  return (
    <section className="home-process-section" aria-label="이용 절차">
      <div className="section-header">
        <p className="eyebrow">이용 절차</p>
        <h2>4단계로 완료되는 건설업 양도양수</h2>
      </div>

      <div className="home-process-grid">
        {steps.map((step, index) => (
          <article key={step.title} className="home-process-card">
            <span className="home-process-index">{String(index + 1).padStart(2, "0")}</span>
            <h3>{step.title}</h3>
            <p>{step.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
