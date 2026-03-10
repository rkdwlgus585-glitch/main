import type { LucideIcon } from "lucide-react";
import { Building, FileText, Landmark, ShieldCheck } from "lucide-react";

const operations: Array<{
  title: string;
  body: string;
  icon: LucideIcon;
}> = [
  {
    title: "양도양수 자문",
    body: "매물 조건, 법인 상태, 협상 포인트를 먼저 정리하는 상담형 진입입니다.",
    icon: Landmark,
  },
  {
    title: "건설업등록 검토",
    body: "등록기준과 사전 준비 항목을 메인 흐름 안에서 자연스럽게 연결합니다.",
    icon: Building,
  },
  {
    title: "법인 · 구조 점검",
    body: "분할합병, 법인설립, 재무 정리 같은 보조 업무를 한 묶음으로 안내합니다.",
    icon: ShieldCheck,
  },
  {
    title: "실무 브리프",
    body: "건설실무, 고객센터, 자주 묻는 흐름을 따로 흩어지지 않게 모아 둡니다.",
    icon: FileText,
  },
];

const reasons = [
  "첫 화면에 매물 성격과 상담 진입점을 함께 둡니다.",
  "모바일에서도 표보다 읽기 쉬운 카드와 브리프 구조를 사용합니다.",
  "레거시 게시판 느낌은 남기되 색, 여백, 타이포를 정돈합니다.",
];

export function HomeOperations() {
  return (
    <section className="home-operations-section">
      <div className="home-operations-layout">
        <div className="home-operations-spotlight">
          <p className="eyebrow">Service Direction</p>
          <h2>비슷한 분위기는 유지하고, 운영 효율은 더 높이는 메인 구조</h2>
          <p>
            기존 메인의 핵심인 신뢰감과 정보 밀도를 유지하면서, 사용자가 실제로 먼저 보는
            블록만 재배열했습니다. 복제보다 운영 효율에 맞춘 리디자인에 가깝습니다.
          </p>
          <ul className="home-operations-reasons">
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>

        <div className="home-operations-grid">
          {operations.map(({ title, body, icon: Icon }) => (
            <article key={title} className="home-operation-card">
              <span className="home-operation-icon">
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
