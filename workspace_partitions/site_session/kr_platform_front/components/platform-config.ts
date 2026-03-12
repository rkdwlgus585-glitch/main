/** 플랫폼 전역 설정 — 환경변수 또는 기본값 사용 */
interface PlatformConfig {
  readonly brandName: string;
  readonly brandTagline: string;
  readonly platformFrontHost: string;
  readonly listingHost: string;
  readonly contentHost: string;
  readonly calculatorMountBase: string;
  readonly privateEngineOrigin: string;
  readonly contactPhone: string;
  readonly contactEmail: string;
  readonly tenantId: string;
  readonly companyName: string;
  readonly companyAddress: string;
  /** 대표자 성명 (전자상거래법 필수) */
  readonly ceoName: string;
  /** 사업자등록번호 (전자상거래법 필수) */
  readonly businessRegNo: string;
  /** 통신판매업 신고번호 (전자상거래법 필수) */
  readonly ecommerceRegNo: string;
  /** 호스팅 서비스 제공자 (전자상거래법 권고) */
  readonly hostingProvider: string;
}

export const platformConfig: PlatformConfig = {
  brandName: "서울건설정보",
  brandTagline: "건설업 AI 분석 플랫폼",
  platformFrontHost: process.env.NEXT_PUBLIC_PLATFORM_FRONT_HOST || "https://seoulmna.kr",
  listingHost: process.env.NEXT_PUBLIC_LISTING_HOST || "https://seoulmna.co.kr",
  contentHost: process.env.NEXT_PUBLIC_CONTENT_HOST || "https://seoulmna.co.kr",
  calculatorMountBase:
    process.env.NEXT_PUBLIC_CALCULATOR_MOUNT_BASE || "https://seoulmna.kr/_calc",
  privateEngineOrigin:
    process.env.NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN || "https://calc.seoulmna.co.kr",
  contactPhone: process.env.NEXT_PUBLIC_CONTACT_PHONE || "1668-3548",
  contactEmail: process.env.NEXT_PUBLIC_CONTACT_EMAIL || "seoulmna@gmail.com",
  tenantId: process.env.NEXT_PUBLIC_TENANT_ID || "seoul_main",
  companyName: "서울건설정보",
  companyAddress: "서울특별시",
  ceoName: "강지현",
  businessRegNo: process.env.NEXT_PUBLIC_BIZ_REG_NO || "",
  ecommerceRegNo: process.env.NEXT_PUBLIC_ECOMMERCE_REG_NO || "",
  hostingProvider: "Vercel Inc.",
};

export function widgetUrl(widget: "yangdo" | "permit") {
  const url = new URL(`${platformConfig.calculatorMountBase}/${widget}`);
  url.searchParams.set("tenant_id", platformConfig.tenantId);
  url.searchParams.set("from", "kr-platform");
  url.searchParams.set("mode", widget === "yangdo" ? "customer" : "acquisition");
  return url.toString();
}
