import { platformConfig } from "@/components/platform-config";

export function ConsultationCTA() {
  return (
    <section className="cta-section">
      <div className="cta-content">
        <h2>건설업 면허 양도양수, 전문 상담이 필요하신가요?</h2>
        <p>
          AI 분석 결과를 바탕으로 건설업 전문 행정사가 직접 상담해 드립니다.
          양도가 협상, 신규 등록 절차, 면허 관리까지 원스톱으로 지원합니다.
        </p>
        <div className="cta-actions">
          <a className="cta-primary" href={`tel:${platformConfig.contactPhone}`}>
            {platformConfig.contactPhone} 전화 상담
          </a>
          <a className="cta-secondary" href={`mailto:${platformConfig.contactEmail}`}>
            이메일 문의
          </a>
        </div>
      </div>
    </section>
  );
}
