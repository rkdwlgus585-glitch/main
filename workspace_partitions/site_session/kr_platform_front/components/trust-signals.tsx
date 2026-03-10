import { Award, Database, Fingerprint, TrendingUp } from "lucide-react";

const signals = [
  {
    icon: Database,
    metric: "6.3MB",
    label: "등록기준 마스터 데이터",
    detail: "건설산업기본법 기반 191개 업종의 등록기준을 체계화",
  },
  {
    icon: TrendingUp,
    metric: "중복 보정",
    label: "매물 오염 제거 엔진",
    detail: "공유 매물 네트워크의 중복을 자동 감지하고 보정",
  },
  {
    icon: Fingerprint,
    metric: "투명 공개",
    label: "산정 근거 전량 공개",
    detail: "비교군 선정부터 신뢰도 계산까지 모든 과정을 공개",
  },
  {
    icon: Award,
    metric: "전문가 검증",
    label: "건설업 행정사 최종 확인",
    detail: "AI 분석 후 건설업 전문 행정사의 실무 검증 체계",
  },
];

export function TrustSignals() {
  return (
    <section className="trust-section">
      <div className="section-header">
        <p className="eyebrow">신뢰 기반</p>
        <h2>데이터와 전문성으로 신뢰를 만듭니다</h2>
      </div>
      <div className="trust-grid">
        {signals.map(({ icon: Icon, metric, label, detail }) => (
          <article className="trust-card" key={label}>
            <Icon size={20} strokeWidth={1.8} className="trust-icon" />
            <strong className="trust-metric">{metric}</strong>
            <p className="trust-label">{label}</p>
            <p className="trust-detail">{detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
