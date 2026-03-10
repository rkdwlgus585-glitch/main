import type { Metadata } from "next";
import { ServiceDetailPage } from "@/components/service-detail-page";
import { buildPageMetadata } from "@/lib/page-metadata";

export const metadata: Metadata = buildPageMetadata(
  "/practice",
  "건설실무",
  "면허 유지, 실적, 기술자, 조합 관련 반복 문의를 정리한 건설실무 브리프 페이지입니다.",
);

export default function PracticePage() {
  return (
    <ServiceDetailPage
      eyebrow="Field Practice"
      title="건설실무"
      description="면허 유지, 실적 신고, 기술자, 조합 등 운영자가 자주 설명하는 내용을 묶어 두는 페이지입니다."
      breadcrumbLabel="건설실무"
      breadcrumbPath="/practice"
      heroLabel="운영 브리프"
      heroNote="반복 문의를 구조화"
      reviewedAt="2026.03.10"
      referenceText="면허 유지 · 실적 · 기술자 운영 브리프"
      summaryCards={[
        { label: "주요 범위", value: "면허 유지 · 실적 · 기술자", note: "고객 문의가 반복되는 주제를 먼저 묶어 두면 상담 효율이 올라갑니다." },
        { label: "콘텐츠 목표", value: "짧고 실무적으로", note: "퍼블릭 사이트에서는 법령 원문보다 운영자가 바로 설명할 수 있는 언어가 중요합니다." },
        { label: "운영 방식", value: "공지 + 브리프 누적", note: "자주 바뀌는 내용은 공지로, 자주 묻는 구조는 브리프로 분리하는 것이 좋습니다." },
        { label: "연결 목적", value: "상담 전 이해도 확보", note: "모든 내용을 완결하기보다 상담 전 이해도를 올리는 것이 페이지의 역할입니다." },
      ]}
      processTitle="건설실무 페이지는 반복 문의를 줄이는 방향으로 설계해야 합니다"
      processSteps={[
        { title: "반복 질문 정리", body: "운영자가 자주 받는 질문을 먼저 추리고, 실제 상담 흐름에 맞게 재배열해야 합니다." },
        { title: "주제별로 묶기", body: "면허 유지, 실적 신고, 기술자, 조합처럼 고객이 이해하기 쉬운 축으로 나누는 것이 효과적입니다." },
        { title: "공지와 가이드를 분리", body: "일시적 변경사항은 공지로, 오래 쓰는 설명은 실무 브리프로 분리하면 유지보수가 쉬워집니다." },
        { title: "상담 연결 유지", body: "브리프를 읽은 뒤 바로 질문하거나 자료를 보낼 수 있게 고객센터 동선을 계속 노출해야 합니다." },
      ]}
      checklistTitle="운영 페이지에서 우선 다뤄야 할 실무 묶음"
      checklistGroups={[
        { title: "면허 유지", items: ["기술자 유지 포인트", "사무실 유지 요건", "기준 미달 발생 시 대응 흐름"] },
        { title: "실적 / 조합", items: ["최근 실적 확인 포인트", "조합 상태 점검", "입찰 준비 전 확인 항목"] },
        { title: "문의 응대", items: ["자료 요청 템플릿", "공지와 FAQ 분리", "고객센터 연결 문구 유지"] },
      ]}
      notesTitle="실무 콘텐츠 운영에서 흔히 생기는 문제"
      notes={[
        { title: "정보가 많다고 좋은 것은 아닙니다", body: "퍼블릭 사이트에서는 핵심 판단 기준을 먼저 보여주고 세부 내용은 단계적으로 확장하는 편이 읽기 쉽습니다." },
        { title: "실무 브리프는 자주 갱신되어야 합니다", body: "제도나 운영 기준이 바뀌는 항목은 공지와 함께 주기적으로 검토하지 않으면 오히려 혼선을 줍니다." },
        { title: "콘텐츠와 상담은 분리할 수 없습니다", body: "브리프를 충분히 읽어도 개별 상황은 다르므로, 페이지 끝에는 항상 상담 연결이 있어야 합니다." },
      ]}
    />
  );
}
