import { Award, Database, Scale, Shield } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { AnimatedCounter } from "@/components/animated-counter";

const trustItems: Array<{
  icon: LucideIcon;
  stat: React.ReactNode;
  label: string;
  detail: string;
}> = [
  {
    icon: Database,
    stat: <AnimatedCounter end={191} suffix="개" />,
    label: "분석 대상 업종",
    detail: "건설업 전 업종 등록기준 데이터를 AI가 실시간으로 분석합니다.",
  },
  {
    icon: Scale,
    stat: <><AnimatedCounter end={100} suffix="%" /></>,
    label: "데이터 기반 산정",
    detail: "실거래 데이터와 공시 정보를 교차 검증하여 양도가를 산정합니다.",
  },
  {
    icon: Shield,
    stat: "특허 출원",
    label: "AI 분석 알고리즘",
    detail: "양도가 산정 및 인허가 사전검토 엔진은 특허 출원 중입니다.",
  },
  {
    icon: Award,
    stat: "원스톱",
    label: "분석→상담→대행",
    detail: "AI 분석부터 전문 행정사 상담, 행정 대행까지 한 곳에서 완결합니다.",
  },
];

export function HomeTrust() {
  return (
    <section className="home-trust" aria-label="신뢰 지표">
      <div className="home-trust-inner">
        <div className="section-header" style={{ textAlign: "center" }}>
          <p className="eyebrow">신뢰할 수 있는 이유</p>
          <h2>데이터와 전문성으로 만든 건설업 AI 플랫폼</h2>
        </div>
        <div className="trust-grid">
          {trustItems.map(({ icon: Icon, stat, label, detail }) => (
            <article key={label} className="trust-card">
              <span className="trust-icon" aria-hidden="true">
                <Icon size={22} />
              </span>
              <strong className="trust-stat">{stat}</strong>
              <span className="trust-label">{label}</span>
              <p className="trust-detail">{detail}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
