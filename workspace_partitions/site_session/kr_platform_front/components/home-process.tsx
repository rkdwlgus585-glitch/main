const steps = [
  {
    title: "첫 화면에서 분기",
    body: "매물 탐색, 건설업등록, 양도가 산정, 상담으로 자연스럽게 나뉘는 구조입니다.",
  },
  {
    title: "브리프로 판단",
    body: "표 전체를 읽기 전에 등록번호, 업종, 상태, 핵심 메모만 빠르게 확인합니다.",
  },
  {
    title: "상담으로 연결",
    body: "전화와 문의 동선을 한 화면 안에서 유지해 이탈을 줄입니다.",
  },
  {
    title: "세부 화면으로 이동",
    body: "상세 페이지나 별도 계산 화면은 메인에서 충분히 예열된 뒤 진입시킵니다.",
  },
];

export function HomeProcess() {
  return (
    <section className="home-process-section">
      <div className="section-header">
        <p className="eyebrow">Main Flow</p>
        <h2>사용자가 메인에서 바로 이해해야 하는 흐름만 남겼습니다</h2>
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
