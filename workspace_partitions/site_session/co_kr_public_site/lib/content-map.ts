import type { LegacyPageGroup } from "@/lib/legacy-types";

export const boardConfig = {
  notice: {
    path: "/notice",
    eyebrow: "Notice",
    title: "공지사항",
    description: "운영 공지, 시장 브리프, 실무 가이드를 정리한 게시판입니다.",
    treatmentLabel: "원문 보존",
    treatmentSummary: "seoulmna.co.kr의 notice 게시판은 제목, 본문, 발행 순서를 그대로 유지하는 보존 아카이브로 운영합니다.",
  },
  premium: {
    path: "/premium",
    eyebrow: "Premium Listing",
    title: "프리미엄 매물 정보",
    description: "정밀 분석형 프리미엄 매물 리포트를 정리한 게시판입니다.",
    treatmentLabel: "원문 보존",
    treatmentSummary: "premium 게시판의 프리미엄 매물 리포트는 원문 본문을 그대로 보존하고, 운영형 매물 탐색은 /mna에서 별도로 제공합니다.",
  },
  news: {
    path: "/news",
    eyebrow: "News",
    title: "뉴스",
    description: "실무 사례와 업계 이슈를 정리한 콘텐츠입니다.",
    treatmentLabel: "원문 참고 + 실무 보강",
    treatmentSummary: "뉴스 원문은 아카이브로 남기되, 실제 운영형 안내는 서비스 랜딩 페이지에서 최신 법령, SEO, 고객경험 기준으로 다시 정리합니다.",
  },
} as const;

export const pageGroupConfig: Record<Exclude<LegacyPageGroup, null>, { path: string; label: string }> = {
  registration: { path: "/registration", label: "건설업등록" },
  corporate: { path: "/corporate", label: "법인설립" },
  "split-merger": { path: "/split-merger", label: "분할합병" },
  practice: { path: "/practice", label: "건설실무" },
  support: { path: "/support", label: "고객센터" },
  "mna-info": { path: "/mna", label: "양도양수" },
};
