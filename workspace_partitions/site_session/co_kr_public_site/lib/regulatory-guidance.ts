export type RegulatorySourceLink = {
  label: string;
  href: string;
  note?: string;
};

export type RegulatoryHighlight = {
  title: string;
  headline: string;
  bullets: string[];
  sources: RegulatorySourceLink[];
};

export const regulatoryReviewedAt = "2026.03.11";

export const regulatorySources = {
  transferReport: {
    label: "건설산업기본법 제17조(건설업의 양도 등)",
    href: "https://www.law.go.kr/lsLawLinkInfo.do?chrClsCd=010202&lsJoLnkSeq=900084343",
  },
  transferNotice: {
    label: "건설산업기본법 제18조(건설업 양도의 공고)",
    href: "https://law.go.kr/LSW/lsLawLinkInfo.do?chrClsCd=010202&lsJoLnkSeq=900084286",
  },
  transferScope: {
    label: "건설산업기본법 제19조(건설업 양도의 내용 등)",
    href: "https://www.law.go.kr/LSW/lsSideInfoP.do?chrClsCd=010201&docCls=&joBrNo=&joNo=&lsiSeq=113445&urlMode=lsRvsDocInfoR",
  },
  registrationLaw: {
    label: "건설산업기본법 제10조(건설업의 등록기준)",
    href: "https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0010&lsiSeq=273435&urlMode=lsScJoRltInfoR",
  },
  registrationEnforcement: {
    label: "건설산업기본법 시행령 제13조(건설업의 등록기준)",
    href: "https://www.law.go.kr/lsLawLinkInfo.do?chrClsCd=010202&lsJoLnkSeq=1000714359",
  },
  registrationAppendix: {
    label: "건설산업기본법 시행령 별표 2(건설업의 등록기준)",
    href: "https://law.go.kr/flDownload.do?bylClsCd=110201&flSeq=105856235&gubun=",
  },
  registrationRule: {
    label: "건설산업기본법 시행규칙 제2조(건설업등록신청서 및 첨부서류)",
    href: "https://www.law.go.kr/LSW/lsLawLinkInfo.do?chrClsCd=010202&lsJoLnkSeq=900085145",
  },
  registrationForm: {
    label: "건설업등록신청서 별지 제1호서식(처리기간 20일)",
    href: "https://law.go.kr/flDownload.do?bylClsCd=110202&flSeq=118778551&gubun=",
  },
  additionalMainFieldRule: {
    label: "2025.06.02 시행규칙 개정(주력분야 추가 등록 시 일부 서류 생략)",
    href: "https://www.law.go.kr/LSW/lsRvsDocListP.do?chrClsCd=010202&lsId=006184&lsRvsGubun=all",
  },
  cakSchedule2026: {
    label: "대한건설협회 2026년도 시공능력평가 일정 안내",
    href: "https://ulsan.cak.or.kr/lay1/bbs/S237T649C650/A/71/view.do?article_seq=154054&condition=&cpage=&keyword=&mode=view&rows=",
  },
  koscaSchedule2026: {
    label: "대한전문건설협회 2026 실적신고 접수 일정 안내",
    href: "https://daejeon.kosca.or.kr/bbs/view.do?bbsId=BBS000360&menuId=MENU001437&nttNo=3690",
  },
  cakDisclosure: {
    label: "대한건설협회 시공능력평가액 공시 사례(7월 31일 공시)",
    href: "https://www.cak.or.kr/lay1/bbs/S1T10C14/A/4/view.do?article_seq=2145&condition=&cpage=1&keyword=&rows=10",
  },
} satisfies Record<string, RegulatorySourceLink>;

export const homeRegulatoryHighlights: RegulatoryHighlight[] = [
  {
    title: "양도·합병 신고",
    headline: "양도·합병·상속은 신고 대상이고, 양도는 30일 이상 공고가 필요합니다.",
    bullets: [
      "양도양수 상담은 거래조건보다 먼저 신고 대상 여부와 승계 구조를 확인해야 합니다.",
      "양도하려는 업종의 권리·의무는 포괄 정리해야 하고, 진행 중인 공사는 발주자 동의 또는 계약 정리가 선행되어야 합니다.",
      "홈페이지 안내는 접수 자체보다 공고, 계약, 진행 공사 정리까지 포함한 일정으로 설명하는 편이 안전합니다.",
    ],
    sources: [
      regulatorySources.transferReport,
      regulatorySources.transferNotice,
      regulatorySources.transferScope,
    ],
  },
  {
    title: "건설업 등록 기준",
    headline: "등록 신청 전 업종별 자본금·보증가능금액·기술인력·사무실·장비 기준을 먼저 맞춰야 합니다.",
    bullets: [
      "등록기준의 뼈대는 법 제10조와 시행령 제13조, 별표 2에 정리되어 있습니다.",
      "신청은 시·도지사 또는 등록업무수탁기관에 전자문서로도 제출할 수 있습니다.",
      "2025년 6월 2일 시행규칙 개정으로 전문공사 주력분야 추가 등록은 일부 서류를 생략할 수 있습니다.",
    ],
    sources: [
      regulatorySources.registrationLaw,
      regulatorySources.registrationEnforcement,
      regulatorySources.registrationRule,
      regulatorySources.additionalMainFieldRule,
    ],
  },
  {
    title: "2026 실적·재무 일정",
    headline: "실적과 재무 제출은 법정 기준에 더해 협회 공지 일정을 함께 관리해야 합니다.",
    bullets: [
      "종합건설은 2026년 2월 2일부터 2월 19일까지 1차 공사실적, 4월 1일부터 4월 15일까지 재무제표를 접수합니다.",
      "전문건설은 2026년 2월 2일부터 2월 19일까지 1차 실적신고를 접수합니다.",
      "미신고 시 시공능력평가 미산정, 실적·경영상태 관련 증명 발급 제한 등 실무상 불이익이 발생할 수 있습니다.",
    ],
    sources: [
      regulatorySources.cakSchedule2026,
      regulatorySources.koscaSchedule2026,
      regulatorySources.cakDisclosure,
    ],
  },
];

export const registrationReferenceLinks: RegulatorySourceLink[] = [
  regulatorySources.registrationLaw,
  regulatorySources.registrationEnforcement,
  regulatorySources.registrationAppendix,
  regulatorySources.registrationRule,
  regulatorySources.registrationForm,
  regulatorySources.additionalMainFieldRule,
];

export const corporateReferenceLinks: RegulatorySourceLink[] = [
  regulatorySources.registrationLaw,
  regulatorySources.registrationEnforcement,
  regulatorySources.registrationRule,
  regulatorySources.registrationForm,
];

export const splitMergerReferenceLinks: RegulatorySourceLink[] = [
  regulatorySources.transferReport,
  regulatorySources.transferNotice,
  regulatorySources.transferScope,
];

export const practiceReferenceLinks: RegulatorySourceLink[] = [
  regulatorySources.cakSchedule2026,
  regulatorySources.koscaSchedule2026,
  regulatorySources.cakDisclosure,
];
