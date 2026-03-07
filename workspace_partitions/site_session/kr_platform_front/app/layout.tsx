import type { Metadata } from "next";
import "./globals.css";
import { platformConfig } from "@/components/platform-config";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: "\uc11c\uc6b8\uac74\uc124\uc815\ubcf4 \ud50c\ub7ab\ud3fc | \uc591\ub3c4\uac00 \uc0b0\uc815 \u00b7 \uc778\ud5c8\uac00 \uc0ac\uc804\uac80\ud1a0",
  description:
    "\uc591\ub3c4\uac00 \uc0b0\uc815\uacfc \uc778\ud5c8\uac00 \uc0ac\uc804\uac80\ud1a0\ub97c \ud558\ub098\uc758 \ud50c\ub7ab\ud3fc \uc785\uad6c\uc5d0\uc11c \uc5f0\uacb0\ud558\ub294 \uc11c\uc6b8\uac74\uc124\uc815\ubcf4 \uacf5\uac1c \ud504\ub860\ud2b8",
  metadataBase: new URL(platformConfig.platformFrontHost),
  openGraph: {
    title: "서울건설정보 플랫폼",
    description: "양도가 산정과 인허가 사전검토를 하나의 공개 진입면에서 연결하는 플랫폼 프런트",
    url: platformConfig.platformFrontHost,
    siteName: "서울건설정보 플랫폼",
    type: "website",
  },
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
