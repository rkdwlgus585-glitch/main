const steps = [
  {
    system: "양도가",
    title: "메인 플랫폼 진입",
    detail:
      ".kr 메인 플랫폼에서 조건을 입력하고, 비공개 엔진이 비교군 정규화와 공개제어를 반영한 범위를 반환합니다.",
  },
  {
    system: "인허가",
    title: "등록기준 사전검토",
    detail:
      "업종별 등록기준 항목을 검사하고 부족항목, 증빙 체크리스트, 다음 조치를 바로 안내합니다.",
  },
  {
    system: "플랫폼",
    title: "매물 사이트와 서비스 분리",
    detail:
      ".co.kr은 매물 사이트에 집중하고, 계산기와 서비스 실행면은 .kr과 .kr/_calc/* 경로로 분리합니다.",
  },
];

export function WorkflowGrid() {
  return (
    <section className="workflow-grid">
      {steps.map((step, index) => (
        <article className="workflow-card" key={step.title}>
          <span className="workflow-index">0{index + 1}</span>
          <p className="product-badge">{step.system}</p>
          <h3>{step.title}</h3>
          <p>{step.detail}</p>
        </article>
      ))}
    </section>
  );
}
