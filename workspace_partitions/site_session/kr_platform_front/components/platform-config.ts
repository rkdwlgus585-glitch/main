export const platformConfig = {
  brandName: "서울건설정보",
  brandTagline: "건설업 AI 전문 플랫폼",
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
  businessNumber: "",
  kakaoChannelUrl: "",
};

export function widgetUrl(widget: "yangdo" | "permit") {
  const url = new URL(`${platformConfig.calculatorMountBase}/${widget}`);
  url.searchParams.set("tenant_id", platformConfig.tenantId);
  url.searchParams.set("from", "kr-platform");
  url.searchParams.set("mode", widget === "yangdo" ? "customer" : "acquisition");
  return url.toString();
}
