const steps = [
  {
    step: "01",
    title: "업종 선택",
    detail: "건설업 면허 종류를 선택하면 해당 업종에 맞는 분석 조건이 자동으로 세팅됩니다.",
  },
  {
    step: "02",
    title: "조건 입력",
    detail: "보유 자본금, 기술인력 등 기본 조건을 입력하세요. 복잡한 전문 지식 없이도 쉽게 진행됩니다.",
  },
  {
    step: "03",
    title: "AI 분석 결과 확인",
    detail: "양도가 범위·신뢰도, 또는 등록기준 충족 여부·부족 항목·신규 취득 예상 비용을 즉시 확인합니다.",
  },
];

export function WorkflowGrid() {
  return (
    <section className="workflow-section">
      <div className="section-header">
        <p className="eyebrow">이용 방법</p>
        <h2>3단계로 간단하게</h2>
      </div>
      <div className="workflow-grid">
        {steps.map((step) => (
          <article className="workflow-card" key={step.step}>
            <span className="workflow-index">{step.step}</span>
            <h3>{step.title}</h3>
            <p>{step.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
