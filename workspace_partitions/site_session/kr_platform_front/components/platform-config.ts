export const platformConfig = {
  brandName: "\uc11c\uc6b8\uac74\uc124\uc815\ubcf4",
  platformFrontHost: process.env.NEXT_PUBLIC_PLATFORM_FRONT_HOST || "https://seoulmna.kr",
  listingHost: process.env.NEXT_PUBLIC_LISTING_HOST || "https://seoulmna.co.kr",
  calculatorMountBase:
    process.env.NEXT_PUBLIC_CALCULATOR_MOUNT_BASE || "https://seoulmna.kr/_calc",
  privateEngineOrigin:
    process.env.NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN || "https://calc.seoulmna.co.kr",
  contactPhone: process.env.NEXT_PUBLIC_CONTACT_PHONE || "1668-3548",
  contactEmail: process.env.NEXT_PUBLIC_CONTACT_EMAIL || "seoulmna@gmail.com",
  tenantId: process.env.NEXT_PUBLIC_TENANT_ID || "seoul_main",
};

export function widgetUrl(widget: "yangdo" | "permit") {
  const url = new URL(`${platformConfig.calculatorMountBase}/${widget}`);
  url.searchParams.set("tenant_id", platformConfig.tenantId);
  url.searchParams.set("from", "kr-platform");
  url.searchParams.set("mode", widget === "yangdo" ? "customer" : "acquisition");
  return url.toString();
}
