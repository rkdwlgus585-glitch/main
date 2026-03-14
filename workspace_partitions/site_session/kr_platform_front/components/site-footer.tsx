import Link from "next/link";
import { platformConfig } from "@/components/platform-config";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <strong>{platformConfig.brandName}</strong>
          <p>AI 양도가 산정 &middot; AI 인허가 검토 &middot; 건설업 AI 분석 플랫폼</p>
        </div>
        <div className="footer-links">
          <div>
            <h4>AI 서비스</h4>
            <Link href="/yangdo">AI 양도가 산정</Link>
            <Link href="/permit">AI 인허가 검토</Link>
            <Link href="/pricing">요금제</Link>
            <Link href="/partners">시스템 도입</Link>
          </div>
          <div>
            <h4>상담</h4>
            <Link href="/consult">고객센터</Link>
            <a href={`tel:${platformConfig.contactPhone}`} aria-label={`전화: ${platformConfig.contactPhone}`}>{platformConfig.contactPhone}</a>
            <a href={`mailto:${platformConfig.contactEmail}`} aria-label={`이메일: ${platformConfig.contactEmail}`}>{platformConfig.contactEmail}</a>
          </div>
          <div>
            <h4>회사</h4>
            <Link href="/about">회사소개</Link>
            <Link href="/terms">이용약관</Link>
            <Link href="/privacy">개인정보처리방침</Link>
          </div>
        </div>

        {/* ── 사업자 정보 (전자상거래법 필수) ── */}
        <div className="footer-biz-info">
          <p>
            <span>상호: {platformConfig.companyName}</span>
            <span>대표: {platformConfig.ceoName}</span>
            <span>주소: {platformConfig.companyAddress}</span>
          </p>
          <p>
            {platformConfig.businessRegNo && (
              <span>사업자등록번호: {platformConfig.businessRegNo}</span>
            )}
            {platformConfig.ecommerceRegNo && (
              <span>통신판매업 신고번호: {platformConfig.ecommerceRegNo}</span>
            )}
            <span>호스팅 서비스: {platformConfig.hostingProvider}</span>
          </p>
          <p>
            <span>전화: {platformConfig.contactPhone}</span>
            <span>이메일: {platformConfig.contactEmail}</span>
            <span>개인정보보호 책임자: {platformConfig.ceoName}</span>
          </p>
          {platformConfig.businessRegNo && (
            <p>
              <a
                href={`https://www.ftc.go.kr/bizCommPop.do?wrkr_no=${platformConfig.businessRegNo.replace(/-/g, "")}`}
                target="_blank"
                rel="noreferrer noopener"
              >
                사업자정보확인 →
              </a>
            </p>
          )}
        </div>

        <div className="footer-bottom">
          <p>&copy; {new Date().getFullYear()} {platformConfig.brandName} ({platformConfig.companyName}). All rights reserved.</p>
          <p className="footer-disclaimer">
            AI 분석 결과는 참고용이며 공식 감정이 아닙니다. 양도가 확정·등록 비용·인허가 절차는 전문가 상담을 권장합니다.
          </p>
        </div>
      </div>
    </footer>
  );
}
