import { platformConfig } from "@/components/platform-config";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <strong>{platformConfig.companyName}</strong>
          <p>건설업 양도양수 &middot; 건설업등록 &middot; 실무 브리프 플랫폼</p>
        </div>
        <div className="footer-links">
          <div>
            <h4>서비스</h4>
            <a href="/mna-market">실시간 매물</a>
            <a href="/permit">건설업등록</a>
            <a href="/yangdo">양도가 산정</a>
          </div>
          <div>
            <h4>정보 · 상담</h4>
            <a href="/knowledge">건설실무</a>
            <a href="/consult">고객센터</a>
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
