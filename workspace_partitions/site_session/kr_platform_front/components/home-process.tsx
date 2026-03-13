const steps = [
  {
    title: "서비스 선택",
    body: "AI 양도가 산정 또는 AI 인허가 검토 중 필요한 서비스를 선택합니다.",
  },
  {
    title: "AI 즉시 분석",
    body: "공시 데이터 기반으로 적정 가격대를 산정하고, 등록기준 충족 여부를 점검합니다.",
  },
  {
    title: "전문가 상담 연결",
    body: "분석 결과를 바탕으로 건설업 전문 행정사가 면허 거래 조건 협상과 절차를 안내합니다.",
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
