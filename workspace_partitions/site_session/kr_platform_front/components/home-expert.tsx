import { Shield, Award, Briefcase, GraduationCap } from "lucide-react";
import { ScrollAnimate } from "@/components/scroll-animate";

const credentials = [
  {
    icon: GraduationCap,
    label: "행정사 자격",
    detail: "대한민국 공인 행정사",
  },
  {
    icon: Briefcase,
    label: "건설업 전문",
    detail: "건설업 양도양수·인허가 실무 전문",
  },
  {
    icon: Shield,
    label: "AI 시스템 설계",
    detail: "양도가·인허가 AI 알고리즘 설계",
  },
  {
    icon: Award,
    label: "특허 출원 중",
    detail: "AI 분석 엔진 특허 출원",
  },
];

export function HomeExpert() {
  return (
    <ScrollAnimate>
      <section className="home-expert-section" aria-label="개발 전문가 소개">
        <div className="section-header" style={{ textAlign: "center" }}>
          <p className="eyebrow">누가 만들었나</p>
          <h2>건설행정 전문가가 직접 설계한 AI</h2>
        </div>

        <div className="expert-card">
          <div className="expert-profile">
            <div className="expert-avatar" aria-hidden="true">
              <span>강</span>
            </div>
            <div className="expert-info">
              <strong className="expert-name">강지현 행정사</strong>
              <span className="expert-role">서울건설정보 대표 · AI 시스템 개발 총괄</span>
            </div>
          </div>

          <p className="expert-quote">
            현장 실무와 데이터를 AI에 녹여, 양도가·인허가를 누구나 쉽게 검토할 수 있도록 설계했습니다.
          </p>

          <div className="expert-credentials">
            {credentials.map(({ icon: Icon, label, detail }) => (
              <div key={label} className="expert-credential">
                <span className="expert-credential-icon" aria-hidden="true">
                  <Icon size={18} />
                </span>
                <div>
                  <strong>{label}</strong>
                  <span>{detail}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </ScrollAnimate>
  );
}
