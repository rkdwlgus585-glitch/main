import { platformConfig } from "@/components/platform-config";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <strong>{platformConfig.companyName}</strong>
          <p>AI 양도가 산정 &middot; AI 인허가 사전검토 전문 플랫폼</p>
        </div>
        <div className="footer-links">
          <div>
            <h4>서비스</h4>
            <a href="/yangdo">AI 양도가 산정</a>
            <a href="/permit">AI 인허가 사전검토</a>
            <a href={platformConfig.listingHost}>매물 시장</a>
          </div>
          <div>
            <h4>고객 지원</h4>
            <a href={`tel:${platformConfig.contactPhone}`}>{platformConfig.contactPhone}</a>
            <a href={`mailto:${platformConfig.contactEmail}`}>{platformConfig.contactEmail}</a>
          </div>
          <div>
            <h4>법적 고지</h4>
            <a href="/terms">이용약관</a>
            <a href="/privacy">개인정보처리방침</a>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; {new Date().getFullYear()} {platformConfig.companyName}. All rights reserved.</p>
          <p className="footer-disclaimer">
            본 서비스의 AI 분석 결과는 참고용이며, 법적 효력이 있는 공식 감정 결과가 아닙니다.
            정확한 양도가 확정, 신규 등록 비용 및 인허가 절차는 반드시 전문가와 상담하시기 바랍니다.
          </p>
        </div>
      </div>
    </footer>
  );
}
