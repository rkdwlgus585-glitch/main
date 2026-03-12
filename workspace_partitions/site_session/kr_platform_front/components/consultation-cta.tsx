import Link from "next/link";
import { Phone, Mail, Bot, UserCheck, Clock } from "lucide-react";
import { platformConfig } from "@/components/platform-config";

export function ConsultationCTA() {
  return (
    <section className="cta-section" aria-label="전문 상담 안내">
      <div className="cta-content">
        <p className="eyebrow">전문 상담</p>
        <h2>건설업 면허 양도양수, 전문 상담이 필요하신가요?</h2>
        <p>
          AI 분석 결과를 바탕으로 건설업 전문 행정사가 직접 상담해 드립니다.
          양도가 협상, 신규 등록 절차, 면허 관리까지 원스톱으로 지원합니다.
        </p>

        {/* ── #11 Hybrid AI + Expert 2-step 시각화 ── */}
        <div className="cta-hybrid-flow" aria-label="서비스 흐름">
          <div className="cta-hybrid-step">
            <Bot size={20} aria-hidden="true" />
            <span>AI가 191개 업종 기준을 즉시 분석</span>
          </div>
          <span className="cta-hybrid-arrow" aria-hidden="true">→</span>
          <div className="cta-hybrid-step">
            <UserCheck size={20} aria-hidden="true" />
            <span>공인 행정사가 검증·맞춤 상담</span>
          </div>
        </div>

        {/* ── #7 Trust signals directly above CTA ── */}
        <div className="cta-trust-bar" aria-label="신뢰 지표">
          <span><Clock size={14} aria-hidden="true" /> 평균 응답 2시간 이내</span>
          <span>공인 행정사 직접 상담</span>
          <span>특허 출원 AI 엔진</span>
        </div>

        <div className="cta-actions">
          <a className="cta-primary cta-phone-pill" href={`tel:${platformConfig.contactPhone}`}>
            <Phone size={16} aria-hidden="true" />
            {platformConfig.contactPhone} 전화 상담
          </a>
          <a className="cta-secondary" href={`mailto:${platformConfig.contactEmail}`}>
            <Mail size={16} aria-hidden="true" />
            이메일 문의
          </a>
          <Link className="cta-secondary" href="/consult">
            고객센터 바로가기
          </Link>
        </div>
      </div>
    </section>
  );
}
