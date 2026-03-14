import type { Metadata } from "next";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { LegacyPageDirectory } from "@/components/legacy-page-directory";
import { ServiceDetailPage } from "@/components/service-detail-page";
import { getLegacyPagesByGroup } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";
import { practiceReferenceLinks, regulatoryReviewedAt } from "@/lib/regulatory-guidance";

export const metadata: Metadata = buildPageMetadata(
  "/practice",
  "건설실무",
  "면허 유지, 실적, 기술자, 조합 관련 반복 문의를 정리한 건설실무 브리프 페이지입니다.",
);

export default function PracticePage() {
  const importedPages = getLegacyPagesByGroup("practice");

  return (
    <ServiceDetailPage
      eyebrow="Field Practice"
      title="건설실무"
      description="면허 유지, 실적 신고, 기술자, 조합 등 운영자가 자주 설명하는 내용을 2026 접수 일정 기준으로 묶어 둔 페이지입니다."
      breadcrumbLabel="건설실무"
      breadcrumbPath="/practice"
      heroLabel="운영 브리프"
      heroNote="2026 일정 반영"
      reviewedAt={regulatoryReviewedAt}
      referenceText="2026 협회 공지 기준 실적신고 · 시공능력 일정"
      summaryCards={[
        { label: "종합 일정", value: "실적 2/2~2/19 · 재무 4/1~4/15", note: "2026년도 시공능력평가 일정 공지 기준으로 종합건설 1차 실적과 재무 제출 일정을 먼저 잡아야 합니다." },
        { label: "전문 일정", value: "실적 2/2~2/19", note: "전문건설도 2026년 1차 실적신고 접수기간이 공지되어 있어 연초 준비가 핵심입니다." },
        { label: "운영 포인트", value: "실적 · 재무 · 기술자 동시 관리", note: "실적신고는 단독 작업이 아니라 재무제표, 고용·기술자 자료와 함께 움직여야 오류가 줄어듭니다." },
        { label: "리스크", value: "미신고 시 평가·증명 제한", note: "실적신고 누락은 시공능력평가 미산정과 실적·경영상태 증명 발급 제한으로 이어질 수 있습니다." },
      ]}
      processTitle="건설실무 페이지는 연초 일정과 반복 문의를 함께 줄이는 방향으로 설계해야 합니다"
      processSteps={[
        { title: "연초 일정 고정", body: "실적신고, 재무제표, 시공능력평가 일정을 먼저 달력으로 고정해 연초 업무를 앞당겨 준비합니다." },
        { title: "자료 묶음 정리", body: "공사실적, 재무제표, 기술자 및 고용 자료를 따로 보지 말고 신고 패키지로 묶어 관리합니다." },
        { title: "공지와 브리프 분리", body: "연도별 접수일정은 공지로, 오래 쓰는 판단 기준은 브리프로 분리해야 업데이트가 쉽습니다." },
        { title: "누락 위험 사전 차단", body: "미신고 불이익과 증명 발급 제한을 먼저 안내해 운영자가 연초에 고객 자료를 미리 받도록 유도합니다." },
      ]}
      checklistTitle="운영 페이지에서 우선 다뤄야 할 실무 묶음"
      checklistGroups={[
        { title: "실적 / 재무", items: ["전년도 공사실적 집계", "법인 재무제표 준비", "협회 공지 일정과 제출 창구 확인"] },
        { title: "면허 유지", items: ["기술자 유지 포인트", "사무실 유지 요건", "등록기준 미달 발생 시 대응 흐름"] },
        { title: "문의 응대", items: ["연초 자료 요청 템플릿", "공지와 FAQ 분리", "고객센터 연결 문구 유지"] },
      ]}
      notesTitle="실무 콘텐츠 운영에서 흔히 생기는 최신 문제"
      notes={[
        { title: "연도별 일정은 공지로 분리해야 합니다", body: "실적신고와 시공능력평가 일정은 해마다 공지 기준으로 갱신되므로 공지와 브리프를 섞으면 오래된 날짜가 남기 쉽습니다." },
        { title: "법령 기준과 협회 공지를 함께 봐야 합니다", body: "실무 일정은 법령상 제출의무와 협회 접수창구 공지가 함께 움직이므로 둘 중 하나만 보면 일정이 어긋날 수 있습니다." },
        { title: "상담 연결은 여전히 필요합니다", body: "브리프를 읽어도 업종, 법인 형태, 실적 구조가 다르므로 실제 제출 전에는 개별 확인이 필요합니다." },
      ]}
      referenceLinks={practiceReferenceLinks}
      referenceNote="2026.03.11 기준 종합·전문 협회 공지와 시공능력평가 공시 자료를 반영했습니다. 세부 접수창구와 보완 일정은 협회 지회 공지에 따라 달라질 수 있습니다."
      afterContent={(
        <>
          <LegacyPageDirectory
            title="이관된 건설실무 세부 안내"
            description="건설실무와 정부정책자금 관련 원본 콘텐츠를 모두 연결했습니다."
            pages={importedPages}
          />
          <AiToolBridge variant="full" />
        </>
      )}
    />
  );
}
