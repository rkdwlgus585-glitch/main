import type { LegacyPageGroup } from "@/lib/legacy-types";

export const boardConfig = {
  notice: {
    path: "/notice",
    eyebrow: "Notice",
    title: "공지사항",
    description: "운영 공지, 시장 브리프, 실무 가이드를 정리한 게시판입니다.",
  },
  premium: {
    path: "/premium",
    eyebrow: "Premium Listing",
    title: "프리미엄 매물 정보",
    description: "정밀 분석형 프리미엄 매물 리포트를 정리한 게시판입니다.",
  },
  news: {
    path: "/news",
    eyebrow: "News",
    title: "뉴스",
    description: "실무 사례와 업계 이슈를 정리한 콘텐츠입니다.",
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
