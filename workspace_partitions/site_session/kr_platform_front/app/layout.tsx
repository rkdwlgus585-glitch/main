import type { Metadata } from "next";
import "./globals.css";
import { platformConfig } from "@/components/platform-config";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: "서울건설정보 | 건설업 AI 양도가 산정 · 인허가 사전검토 전문 플랫폼",
  description:
    "건설업 면허 양도가격을 AI가 무료로 산정합니다. 191개 업종 인허가 등록기준 사전검토까지 원스톱으로 제공하는 건설업 전문 플랫폼.",
  metadataBase: new URL(platformConfig.platformFrontHost),
  openGraph: {
    title: "서울건설정보 | 건설업 AI 전문 플랫폼",
    description:
      "건설업 면허 양도가 산정부터 인허가 등록기준 사전검토까지, 데이터 기반 AI 분석을 무료로 제공합니다.",
    url: platformConfig.platformFrontHost,
    siteName: "서울건설정보",
    type: "website",
  },
  keywords: [
    "건설업 면허",
    "양도가 산정",
    "건설업 양도양수",
    "인허가 사전검토",
    "건설업 등록기준",
    "건설업 AI",
    "면허 가격",
    "서울건설정보",
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <SiteHeader />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
