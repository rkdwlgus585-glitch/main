import type { LucideIcon } from "lucide-react";
import { Building, FileText, Landmark, ShieldCheck } from "lucide-react";

const operations: Array<{
  title: string;
  body: string;
  icon: LucideIcon;
}> = [
  {
    title: "양도양수 상담",
    body: "양도양수 조건과 가격 협상을 전문 행정사가 1:1로 도와드립니다.",
    icon: Landmark,
  },
  {
    title: "건설업등록 검토",
    body: "191개 업종의 등록기준 충족 여부를 AI가 사전검토하고, 신규 취득 비용을 계산합니다.",
    icon: Building,
  },
  {
    title: "법인·구조 점검",
    body: "법인 설립, 구조 변경, 재무 정리 등 양도양수에 필요한 부수 절차까지 안내합니다.",
    icon: ShieldCheck,
  },
  {
    title: "건설실무 가이드",
    body: "등록기준 해석, 서류 준비, 절차 안내 등 실무에 필요한 정보를 모아 제공합니다.",
    icon: FileText,
  },
];

export function HomeOperations() {
  return (
    <section className="home-operations-section" aria-label="서비스 안내">
      <div className="home-operations-layout">
        <div className="home-operations-spotlight">
          <p className="eyebrow">서비스 안내</p>
          <h2>건설업 면허 양도양수와 등록에 필요한 모든 것</h2>
          <p>
            양도가 산정, 등록기준 검토, 전문 상담까지 하나의 플랫폼에서 처리합니다.
            복잡한 건설업 인허가 절차를 데이터와 전문가의 도움으로 간소화합니다.
          </p>
        </div>

        <div className="home-operations-grid">
          {operations.map(({ title, body, icon: Icon }) => (
            <article key={title} className="home-operation-card">
              <span className="home-operation-icon" aria-hidden="true">
                <Icon size={20} />
              </span>
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
