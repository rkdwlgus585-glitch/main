import { Check, X, Minus } from "lucide-react";
import { ScrollAnimate } from "@/components/scroll-animate";

const rows: Array<{
  feature: string;
  traditional: "none" | "partial" | "full";
  traditionalNote: string;
  platform: "none" | "partial" | "full";
  platformNote: string;
}> = [
  {
    feature: "AI 양도가 산정",
    traditional: "partial",
    traditionalNote: "경험 기반 추정",
    platform: "full",
    platformNote: "AI가 6,300+ 기준 교차 분석",
  },
  {
    feature: "AI 인허가 검토",
    traditional: "partial",
    traditionalNote: "수동 확인, 누락 위험",
    platform: "full",
    platformNote: "191개 업종 자동 사전검토",
  },
  {
    feature: "소요 시간",
    traditional: "none",
    traditionalNote: "수일~수주",
    platform: "full",
    platformNote: "즉시 분석 결과 확인",
  },
  {
    feature: "전문가 검증",
    traditional: "full",
    traditionalNote: "대면 상담",
    platform: "full",
    platformNote: "AI 분석 + 행정사 검증",
  },
  {
    feature: "비용 투명성",
    traditional: "none",
    traditionalNote: "견적 편차 큼",
    platform: "full",
    platformNote: "표준화된 분석 기준",
  },
];

function StatusIcon({ status }: { status: "none" | "partial" | "full" }) {
  if (status === "full")
    return <Check size={18} className="comp-icon comp-icon--full" aria-label="지원" />;
  if (status === "partial")
    return <Minus size={18} className="comp-icon comp-icon--partial" aria-label="부분 지원" />;
  return <X size={18} className="comp-icon comp-icon--none" aria-label="미지원" />;
}

export function HomeComparison() {
  return (
    <ScrollAnimate>
      <section className="home-comparison" aria-label="서비스 비교">
        <div className="section-header">
          <p className="eyebrow">왜 다를까</p>
          <h2>전통 중개 vs AI 플랫폼</h2>
        </div>
        <div className="comp-table-wrap">
          <table className="comp-table" role="table">
            <thead>
              <tr>
                <th scope="col">항목</th>
                <th scope="col">전통 중개</th>
                <th scope="col" className="comp-highlight">서울건설정보</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ feature, traditional, traditionalNote, platform, platformNote }) => (
                <tr key={feature}>
                  <td className="comp-feature">{feature}</td>
                  <td>
                    <StatusIcon status={traditional} />
                    <span className="comp-note">{traditionalNote}</span>
                  </td>
                  <td className="comp-highlight-cell">
                    <StatusIcon status={platform} />
                    <span className="comp-note">{platformNote}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </ScrollAnimate>
  );
}
