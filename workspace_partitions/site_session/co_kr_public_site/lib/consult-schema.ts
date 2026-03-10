export const consultServiceOptions = ["양도양수", "건설업등록", "법인설립", "분할합병", "건설실무", "기타"] as const;
export type ConsultService = (typeof consultServiceOptions)[number];
