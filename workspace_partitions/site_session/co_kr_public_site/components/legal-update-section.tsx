import { ExternalLink } from "lucide-react";
import {
  homeRegulatoryHighlights,
  regulatoryReviewedAt,
} from "@/lib/regulatory-guidance";

export function LegalUpdateSection() {
  return (
    <section className="section-block legal-update-section">
      <div className="section-header">
        <p className="eyebrow">Latest Basis</p>
        <h2>{regulatoryReviewedAt} 기준으로 다시 확인한 법령·절차 핵심</h2>
        <p>
          국가법령정보센터 조문과 2026년 협회 공지 기준을 대조해, 퍼블릭 사이트 상단 안내 문구를 최신 실무 흐름에 맞게 정리했습니다.
        </p>
      </div>
      <div className="legal-highlight-grid">
        {homeRegulatoryHighlights.map((item) => (
          <article key={item.title} className="legal-highlight-card">
            <span className="legal-highlight-label">{item.title}</span>
            <h3>{item.headline}</h3>
            <ul className="detail-list">
              {item.bullets.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
            <div className="source-link-list" aria-label={`${item.title} 공식 근거`}>
              {item.sources.map((source) => (
                <a key={source.href} href={source.href} target="_blank" rel="noopener noreferrer">
                  <span>{source.label}</span>
                  <ExternalLink size={14} aria-hidden="true" />
                </a>
              ))}
            </div>
          </article>
        ))}
      </div>
      <p className="legal-update-note">
        실제 접수 창구와 보완 요청은 업종, 관할 시도, 수탁기관에 따라 달라질 수 있으므로 계약 또는 신고 직전에는 해당 공문과 접수 시스템을 한 번 더 확인해야 합니다.
      </p>
    </section>
  );
}
