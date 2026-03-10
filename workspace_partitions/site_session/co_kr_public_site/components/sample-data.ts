export type ListingItem = {
  id: string;
  title: string;
  headline: string;
  updatedAt: string;
  sector: string;
  region: string;
  status: "가능" | "검토중" | "협의중";
  licenseYear: number;
  capacity: string;
  performance: string;
  memo: string;
  price: string;
  overview: string;
  transferScope: string;
  recommendedFor: string;
  caution: string;
  highlights: string[];
  documents: string[];
};

export const listingItems: ListingItem[] = [
  {
    id: "CB-7801",
    title: "실내건축 양도양수 매물",
    headline: "재무 정리와 인수 검토가 빠른 수도권 실내건축 법인",
    updatedAt: "2026-03-10T09:00:00+09:00",
    sector: "실내건축",
    region: "수도권",
    status: "가능",
    licenseYear: 2018,
    capacity: "9억",
    performance: "3년 18억",
    memo: "재무 정리 완료 · 인수 검토 빠름",
    price: "협의",
    overview:
      "실내건축 면허를 중심으로 인수 검토가 빠르게 가능한 구조입니다. 상담 초기 단계에서 재무, 실적, 기술자 현황을 함께 검토하기 좋습니다.",
    transferScope: "법인 인수와 면허 유지 검토를 함께 보는 유형으로, 초기 운영자금 부담이 비교적 낮은 편입니다.",
    recommendedFor: "실내건축 업종 진입을 빠르게 진행하려는 수도권 수요자에게 적합합니다.",
    caution: "기술자 승계 일정과 최근 실적 반영 범위는 실제 서류 기준으로 재확인해야 합니다.",
    highlights: ["수도권 실내건축", "재무 정리 완료", "인수 검토 빠름"],
    documents: ["법인등기부등본", "최근 재무자료", "실적증명", "기술자 보유 현황"],
  },
  {
    id: "CB-7798",
    title: "건축 양도양수 매물",
    headline: "영남권 중형 실적을 보유한 건축 법인",
    updatedAt: "2026-03-09T15:00:00+09:00",
    sector: "건축",
    region: "영남",
    status: "검토중",
    licenseYear: 2013,
    capacity: "110억",
    performance: "3년 74억",
    memo: "법인 이력 단순 · 상담 예약 다수",
    price: "6.8억",
    overview:
      "건축 업종 중심의 중형 매물로, 영남권 시공 이력과 법인 이력 단순성이 강점입니다. 실제 거래 가능 여부는 검토 진행 상황에 따라 달라질 수 있습니다.",
    transferScope: "법인 승계와 면허 유지, 최근 실적 활용 가능성을 함께 검토하는 구조입니다.",
    recommendedFor: "중형 건축 실적을 기반으로 빠르게 시장에 진입하려는 수요자에게 적합합니다.",
    caution: "현재 검토중 상태이므로 진행 시점과 협의 가능 범위를 먼저 확인해야 합니다.",
    highlights: ["영남권 건축", "3년 74억 실적", "법인 이력 단순"],
    documents: ["법인등기부등본", "실적증명", "재무제표", "조합 관련 자료"],
  },
  {
    id: "CB-7795",
    title: "토목 양도양수 매물",
    headline: "기술자 이관이 수월한 충청권 토목 법인",
    updatedAt: "2026-03-08T11:00:00+09:00",
    sector: "토목",
    region: "충청",
    status: "가능",
    licenseYear: 2016,
    capacity: "22억",
    performance: "3년 26억",
    memo: "잔액 안정 · 기술자 이관 수월",
    price: "협의",
    overview:
      "토목 업종 진입을 고려하는 경우 검토하기 좋은 유형입니다. 잔액 안정성과 기술자 이관 난이도가 낮은 편으로 분류되는 샘플입니다.",
    transferScope: "면허 유지, 기술자 이관, 조합 상태를 함께 검토하는 전형적인 양도양수 케이스입니다.",
    recommendedFor: "충청권 기반 토목 입찰 준비를 빠르게 시작하려는 수요자에게 적합합니다.",
    caution: "기술자 실제 승계 가능 여부와 최근 입찰 활용도는 상담 과정에서 확인이 필요합니다.",
    highlights: ["충청권 토목", "잔액 안정", "기술자 이관 수월"],
    documents: ["법인등기부등본", "통장 잔액 관련 자료", "기술자 보유 현황", "실적증명"],
  },
  {
    id: "CB-7789",
    title: "전기 양도양수 매물",
    headline: "신규 확장용으로 적합한 호남권 전기 법인",
    updatedAt: "2026-03-07T13:00:00+09:00",
    sector: "전기",
    region: "호남",
    status: "가능",
    licenseYear: 2020,
    capacity: "11억",
    performance: "3년 11억",
    memo: "신규 확장용으로 적합",
    price: "2.4억",
    overview:
      "신규 확장이나 사업 포트폴리오 보강에 맞는 전기 업종 샘플 매물입니다. 비교적 최근 면허 연도와 부담 가능한 규모가 특징입니다.",
    transferScope: "전기 업종 진입을 위한 법인 승계와 기본 서류 검토가 중심입니다.",
    recommendedFor: "호남권 전기 업종 신규 진입 또는 확장을 고려하는 수요자에게 적합합니다.",
    caution: "가격 협의 외에 실적 활용 범위와 면허 유지 조건을 사전에 점검해야 합니다.",
    highlights: ["호남권 전기", "최근 면허년도", "확장용 적합"],
    documents: ["법인등기부등본", "최근 재무자료", "면허 관련 서류", "기술자 현황"],
  },
  {
    id: "CB-7784",
    title: "조경 양도양수 매물",
    headline: "초기 운영 부담이 낮은 수도권 조경 법인",
    updatedAt: "2026-03-06T10:00:00+09:00",
    sector: "조경",
    region: "수도권",
    status: "가능",
    licenseYear: 2021,
    capacity: "7억",
    performance: "3년 8억",
    memo: "초기 운영 부담 낮음",
    price: "1.9억",
    overview:
      "조경 업종에서 상대적으로 가볍게 검토할 수 있는 샘플 매물입니다. 초기 비용 부담과 운영 복잡도를 낮추고 싶은 경우 참고하기 좋습니다.",
    transferScope: "수도권 조경 업종 진입을 위한 기본 법인 인수 검토와 운영 적합성 점검이 중심입니다.",
    recommendedFor: "초기 부담을 낮추며 수도권 조경 시장에 진입하려는 수요자에게 적합합니다.",
    caution: "최근 실적의 활용 가능 범위와 향후 기술자 충원 계획을 함께 검토해야 합니다.",
    highlights: ["수도권 조경", "초기 부담 낮음", "최근 면허년도"],
    documents: ["법인등기부등본", "재무자료", "실적증명", "기술자 현황"],
  },
  {
    id: "CB-7776",
    title: "기계설비 양도양수 매물",
    headline: "조합 상태가 안정적인 영남권 기계설비 법인",
    updatedAt: "2026-03-05T16:00:00+09:00",
    sector: "기계설비",
    region: "영남",
    status: "협의중",
    licenseYear: 2017,
    capacity: "16억",
    performance: "3년 22억",
    memo: "조합 상태 안정 · 구조 단순",
    price: "4.2억",
    overview:
      "기계설비 업종 중 조합 상태와 구조 단순성을 우선으로 보는 경우 적합한 샘플입니다. 협의 진행 중이므로 실제 조건은 달라질 수 있습니다.",
    transferScope: "기계설비 업종 진입을 위한 법인 구조 검토와 최근 실적 점검이 필요합니다.",
    recommendedFor: "영남권 기계설비 수주 기반을 확보하려는 수요자에게 적합합니다.",
    caution: "현재 협의중이므로 계약 가능 여부와 협상 범위를 먼저 확인해야 합니다.",
    highlights: ["영남권 기계설비", "조합 상태 안정", "구조 단순"],
    documents: ["법인등기부등본", "조합 관련 자료", "실적증명", "재무제표"],
  },
];

export const quickEntries = [
  {
    title: "양도양수 실시간 매물",
    description: "업종, 지역, 양도가 감을 빠르게 훑고 상담으로 연결합니다.",
    href: "/mna",
  },
  {
    title: "건설업등록 검토",
    description: "등록기준과 준비 서류 흐름을 먼저 정리합니다.",
    href: "/registration",
  },
  {
    title: "법인설립 가이드",
    description: "신규 진입용 법인 구조와 준비 단계를 정리합니다.",
    href: "/corporate",
  },
  {
    title: "분할합병 검토",
    description: "구조조정이나 면허 이관 관점에서 핵심 포인트를 설명합니다.",
    href: "/split-merger",
  },
  {
    title: "건설실무 브리프",
    description: "면허 유지, 실적, 기술자, 조합 관련 실무 정보를 묶어 둡니다.",
    href: "/practice",
  },
  {
    title: "고객센터",
    description: "전화, 문의, 진행 절차를 한곳에서 안내합니다.",
    href: "/support",
  },
];

export const trustFacts = [
  {
    label: "대표자",
    value: "강지현",
  },
  {
    label: "사업자등록",
    value: "781-01-02142",
  },
  {
    label: "통신판매업",
    value: "2026-서울영등포-가상0001",
  },
  {
    label: "상담 시간",
    value: "평일 09:00 - 18:00",
  },
];

export const notices = [
  {
    title: "2026년 건설업 등록기준 상담 예약 운영 안내",
    summary: "전화 상담 집중 시간과 서류 사전 접수 방법을 안내합니다.",
    date: "2026-03-10",
  },
  {
    title: "양도양수 사전 검토 시 준비하면 좋은 자료",
    summary: "법인등기, 실적, 조합, 기술자 자료를 어떤 순서로 준비할지 정리했습니다.",
    date: "2026-03-07",
  },
  {
    title: "홈페이지 개설 준비 단계 안내",
    summary: "현재 사이트는 독립 운영 사이트로 구축 중이며, 데이터 연동은 다음 단계에서 진행됩니다.",
    date: "2026-03-05",
  },
];

export const faqs = [
  {
    question: "양도양수 상담 전에 어떤 자료를 준비해야 하나요?",
    answer:
      "법인등기부, 최근 재무자료, 실적 현황, 조합 관련 자료, 기술자 현황이 있으면 초기 판단이 빨라집니다.",
  },
  {
    question: "건설업등록은 신규 법인과 기존 법인 모두 가능한가요?",
    answer:
      "가능합니다. 다만 자본금, 기술인력, 사무실 조건 등 준비 항목이 달라질 수 있어 사전 검토가 필요합니다.",
  },
  {
    question: "홈페이지의 매물 표시는 실시간 운영 데이터인가요?",
    answer:
      "현재 이 프로젝트 단계에서는 샘플 데이터이며, 실제 운영 시 관리자 입력 또는 DB 연동으로 교체하면 됩니다.",
  },
];
