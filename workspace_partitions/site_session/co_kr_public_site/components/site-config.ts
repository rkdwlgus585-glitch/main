function getAllowIndexing(host: string) {
  try {
    const hostname = new URL(host).hostname.toLowerCase();

    return !(
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname === "example.com" ||
      hostname.endsWith(".example.com")
    );
  } catch {
    return false;
  }
}

const host = process.env.NEXT_PUBLIC_SITE_HOST || "https://seoulmna-public.example.com";

export const siteConfig = {
  brandName: "서울건설브리프",
  brandTagline: "건설업 양도양수 · 등록 실무 안내",
  host,
  companyName: process.env.NEXT_PUBLIC_COMPANY_NAME || "서울건설브리프",
  representativeName: process.env.NEXT_PUBLIC_REPRESENTATIVE_NAME || "강지현",
  businessNumber: process.env.NEXT_PUBLIC_BUSINESS_NUMBER || "781-01-02142",
  mailOrderNumber:
    process.env.NEXT_PUBLIC_MAIL_ORDER_NUMBER || "2026-서울영등포-가상0001",
  phone: process.env.NEXT_PUBLIC_CONTACT_PHONE || "1668-3548",
  mobile: process.env.NEXT_PUBLIC_CONTACT_MOBILE || "010-9926-8661",
  email: process.env.NEXT_PUBLIC_CONTACT_EMAIL || "contact@seoulmna-public.example.com",
  kakaoUrl: process.env.NEXT_PUBLIC_KAKAO_URL || "https://open.kakao.com/",
  platformHost: process.env.NEXT_PUBLIC_PLATFORM_HOST || "https://seoulmna.kr",
  address: process.env.NEXT_PUBLIC_COMPANY_ADDRESS || "서울특별시 영등포구 국제금융로 인근",
  officeHours:
    process.env.NEXT_PUBLIC_OFFICE_HOURS || "평일 09:00 - 18:00 · 토요일 예약 상담",
  analyticsId: process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID || "",
  allowIndexing: getAllowIndexing(host),
};

export const primaryMenu = [
  { href: "/mna", label: "양도양수" },
  { href: "/registration", label: "건설업등록" },
  { href: "/corporate", label: "법인설립" },
  { href: "/split-merger", label: "분할합병" },
  { href: "/practice", label: "건설실무" },
  { href: "/support", label: "고객센터" },
];
