import Link from "next/link";
import { platformConfig } from "@/components/platform-config";

export function SiteHeader() {
  return (
    <header className="site-header">
      <Link href="/" className="site-brand">
        <span className="site-brand-mark">SM</span>
        <span className="site-brand-copy">
          <strong>{platformConfig.brandName}</strong>
          <small>{platformConfig.brandTagline}</small>
        </span>
      </Link>
      <nav className="site-nav" aria-label="주요 메뉴">
        <Link href="/yangdo">양도가 산정</Link>
        <Link href="/permit">인허가 사전검토</Link>
        <a href={`${platformConfig.listingHost}/category/건설업-지식`} rel="noreferrer noopener">
          건설업 지식
        </a>
        <a href={`tel:${platformConfig.contactPhone}`} className="nav-phone">
          {platformConfig.contactPhone}
        </a>
      </nav>
    </header>
  );
}
