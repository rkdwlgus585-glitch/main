import Link from "next/link";
import { ContactLink } from "@/components/contact-link";
import { primaryMenu, siteConfig } from "@/components/site-config";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <strong>{siteConfig.brandName}</strong>
          <p>{siteConfig.brandTagline}</p>
        </div>

        <div className="footer-grid footer-grid--4col">
          <nav className="footer-link-group" aria-labelledby="footer-services-heading">
            <h4 id="footer-services-heading">서비스</h4>
            {primaryMenu.slice(0, 3).map((item) => (
              <Link key={item.href} href={item.href}>
                {item.label}
              </Link>
            ))}
          </nav>
          <nav className="footer-link-group" aria-labelledby="footer-guide-heading">
            <h4 id="footer-guide-heading">안내</h4>
            {primaryMenu.slice(3).map((item) => (
              <Link key={item.href} href={item.href}>
                {item.label}
              </Link>
            ))}
            <Link href="/notice">공지사항</Link>
            <Link href="/premium">프리미엄 매물</Link>
            <Link href="/news">뉴스</Link>
            <Link href="/tl_faq">자주하는 질문</Link>
            <Link href="/privacy">개인정보처리방침</Link>
            <Link href="/terms">이용약관</Link>
          </nav>
          <nav className="footer-link-group" aria-labelledby="footer-ai-heading">
            <h4 id="footer-ai-heading">AI 도구</h4>
            <a href={`${siteConfig.platformHost}/yangdo`} target="_blank" rel="noopener noreferrer">
              AI 양도가 산정
            </a>
            <a href={`${siteConfig.platformHost}/permit`} target="_blank" rel="noopener noreferrer">
              AI 인허가 사전검토
            </a>
            <a href={siteConfig.platformHost} target="_blank" rel="noopener noreferrer">
              서울건설정보
            </a>
          </nav>
          <nav className="footer-link-group" aria-labelledby="footer-contact-heading">
            <h4 id="footer-contact-heading">상담</h4>
            <ContactLink href={`tel:${siteConfig.phone}`} eventName="click_phone" eventLabel="footer_phone">
              {siteConfig.phone}
            </ContactLink>
            <ContactLink href={`tel:${siteConfig.mobile}`} eventName="click_mobile" eventLabel="footer_mobile">
              {siteConfig.mobile}
            </ContactLink>
            <ContactLink href={`mailto:${siteConfig.email}`} eventName="click_email" eventLabel="footer_email">
              {siteConfig.email}
            </ContactLink>
            <ContactLink href={siteConfig.kakaoUrl} eventName="click_kakao" eventLabel="footer_kakao" newTab>
              카카오 문의
            </ContactLink>
          </nav>
        </div>

        <address className="footer-meta">
          <p>
            대표자 {siteConfig.representativeName} · 사업자등록번호 {siteConfig.businessNumber}
          </p>
          <p>통신판매업신고번호 {siteConfig.mailOrderNumber}</p>
          <p>{siteConfig.address}</p>
          <p>{siteConfig.officeHours}</p>
          <p>
            © {new Date().getFullYear()} {siteConfig.brandName}. All rights reserved.
          </p>
          <p className="footer-disclaimer">
            이 사이트는 건설업 양도양수 및 등록 실무 안내용 퍼블릭 사이트입니다. 실제 거래 조건과
            계약 내용은 실사 및 상담 과정에서 별도로 확정됩니다.
          </p>
        </address>
      </div>
    </footer>
  );
}
