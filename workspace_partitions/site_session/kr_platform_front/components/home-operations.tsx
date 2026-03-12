import type { LucideIcon } from "lucide-react";
import { FileText, Handshake, Landmark, ShieldCheck } from "lucide-react";

const operations: Array<{
  title: string;
  body: string;
  icon: LucideIcon;
}> = [
  {
    title: "양도양수 상담",
    body: "AI 산정 결과를 바탕으로 양도양수 조건과 가격 협상을 전문 행정사가 1:1로 도와드립니다.",
    icon: Landmark,
  },
  {
    title: "면허 취득 컨설팅",
    body: "등록기준 충족 방안과 필요 비용을 안내하고, 신규 면허 취득까지 행정사가 지원합니다.",
    icon: Handshake,
  },
  {
    title: "법인·구조 점검",
    body: "법인 설립, 구조 변경, 재무 정리 등 양도양수에 필요한 부수 절차까지 안내합니다.",
    icon: ShieldCheck,
  },
  {
    title: "서류·절차 안내",
    body: "양도양수 계약서, 등록 서류, 관할 기관 접수까지 필요한 절차를 안내합니다.",
    icon: FileText,
  },
];

export function HomeOperations() {
  return (
    <section className="home-operations-section" aria-label="서비스 안내">
      <div className="home-operations-layout">
        <div className="home-operations-spotlight">
          <p className="eyebrow">전문 행정사 서비스</p>
          <h2>AI 분석 이후, 전문가가 실무를 처리합니다</h2>
          <p>
            AI가 분석한 결과를 바탕으로<br />
            건설업 전문 행정사가 상담·대행까지 완결합니다.
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
