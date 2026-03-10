import { BarChart3, Clock, FileCheck, Shield } from "lucide-react";

const items = [
  {
    icon: BarChart3,
    title: "데이터 기반 산정",
    body: "공개 공시 데이터와 실거래 매물 네트워크를 교차 분석하여 신뢰도 높은 양도가 범위를 산정합니다.",
  },
  {
    icon: Clock,
    title: "즉시 결과 확인",
    body: "행정사 방문 없이 온라인에서 바로 결과를 확인하세요. 24시간 언제든 이용 가능합니다.",
  },
  {
    icon: FileCheck,
    title: "등록기준 전수 점검",
    body: "건설업·유사 업종 191개의 자본금, 기술인력, 사무실 등 등록기준을 점검하고 신규 취득 비용까지 산정합니다.",
  },
  {
    icon: Shield,
    title: "전문가 검증 체계",
    body: "AI 분석 결과를 건설업 전문 행정사가 최종 검증하여 실무 정확도를 보장합니다.",
  },
];

export function CapabilityStrip() {
  return (
    <section className="capability-strip">
      <div className="section-header">
        <p className="eyebrow">핵심 기능</p>
        <h2>왜 서울건설정보인가요?</h2>
      </div>
      <div className="capability-grid">
        {items.map(({ icon: Icon, title, body }) => (
          <article className="capability-card" key={title}>
            <div className="capability-icon">
              <Icon size={24} strokeWidth={1.8} />
            </div>
            <strong>{title}</strong>
            <p>{body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
