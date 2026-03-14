import type { Metadata } from "next";
import { buildPageMetadata } from "@/lib/page-metadata";
import { PublicHome } from "@/components/public-home";
import { siteConfig } from "@/components/site-config";

const homeDescription =
  "건설업 양도양수, 건설업등록, 분할합병, 실적신고 일정을 최신 법령과 절차 기준으로 안내하는 퍼블릭 사이트 메인 페이지입니다.";

const homeMetadata = buildPageMetadata("/", siteConfig.brandTagline, homeDescription);

export const metadata: Metadata = {
  ...homeMetadata,
  title: `${siteConfig.brandName} | ${siteConfig.brandTagline}`,
  openGraph: {
    ...homeMetadata.openGraph,
    title: `${siteConfig.brandName} | ${siteConfig.brandTagline}`,
  },
  twitter: {
    ...homeMetadata.twitter,
    title: `${siteConfig.brandName} | ${siteConfig.brandTagline}`,
  },
};

export default function HomePage() {
  return <PublicHome />;
}
