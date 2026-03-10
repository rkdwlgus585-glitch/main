import { Check, X } from "lucide-react";

const channels = [
  {
    name: "기존 행정사",
    price: "50~200만원",
    priceNote: "면허 종류/난이도별 상이",
    features: {
      instant: false,
      transparent: false,
      datadriven: false,
      free: false,
      online: false,
    },
  },
  {
    name: "브로커",
    price: "수수료 별도",
    priceNote: "양도가에 수수료 포함",
    features: {
      instant: false,
      transparent: false,
      datadriven: false,
      free: false,
      online: false,
    },
  },
  {
    name: "서울건설정보",
    price: "무료",
    priceNote: "AI 산정 결과 즉시 제공",
    highlight: true,
    features: {
      instant: true,
      transparent: true,
      datadriven: true,
      free: true,
      online: true,
    },
  },
];

const featureLabels: Record<string, string> = {
  instant: "즉시 결과 확인",
  transparent: "산정 근거 투명 공개",
  datadriven: "공시 데이터 기반 분석",
  free: "무료 이용",
  online: "24시간 온라인 이용",
};

export function PricingComparison() {
  return (
    <section className="pricing-section">
      <div className="section-header">
        <p className="eyebrow">비교</p>
        <h2>기존 방식과 무엇이 다른가요?</h2>
      </div>
      <div className="pricing-grid">
        {channels.map((ch) => (
          <article
            className={`pricing-card ${ch.highlight ? "pricing-highlight" : ""}`}
            key={ch.name}
          >
            {ch.highlight && <span className="pricing-badge">추천</span>}
            <h3>{ch.name}</h3>
            <p className="pricing-amount">{ch.price}</p>
            <p className="pricing-note">{ch.priceNote}</p>
            <ul className="pricing-features">
              {Object.entries(ch.features).map(([key, ok]) => (
                <li key={key} className={ok ? "feature-yes" : "feature-no"}>
                  {ok ? <Check size={16} /> : <X size={16} />}
                  {featureLabels[key]}
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}
