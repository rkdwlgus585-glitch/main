import type { Metadata } from "next";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { LegacyPageDirectory } from "@/components/legacy-page-directory";
import { ServiceDetailPage } from "@/components/service-detail-page";
import { getLegacyPagesByGroup } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";
import { regulatoryReviewedAt, splitMergerReferenceLinks } from "@/lib/regulatory-guidance";

export const metadata: Metadata = buildPageMetadata(
  "/split-merger",
  "분할합병",
  "면허와 법인 구조 재편을 검토하는 고객을 위한 분할합병 안내 페이지입니다.",
);

export default function SplitMergerPage() {
  const importedPages = getLegacyPagesByGroup("split-merger");

  return (
    <ServiceDetailPage
      eyebrow="Split & Merger"
      title="분할합병"
      description="면허, 법인, 사업 구조를 재편하려는 고객에게 현재 법령 기준의 양도·합병 검토 포인트를 정리하는 페이지입니다."
      breadcrumbLabel="분할합병"
      breadcrumbPath="/split-merger"
      heroLabel="구조 재편 검토"
      heroNote="신고 · 공고 · 진행 공사 확인"
      reviewedAt={regulatoryReviewedAt}
      referenceText="건설산업기본법 제17조 · 제18조 · 제19조"
      summaryCards={[
        { label: "법적 출발점", value: "양도 · 합병 · 상속 신고", note: "현재 기준상 건설업의 양도, 합병, 상속은 신고 구조를 먼저 확인해야 합니다." },
        { label: "공고 의무", value: "양도 전 30일 이상 공고", note: "양도 공고는 거래 막바지가 아니라 초기 일정에 포함해야 안전합니다." },
        { label: "승계 범위", value: "해당 업종의 권리·의무 정리", note: "면허만 떼어 보는 것이 아니라 권리·의무와 실적 활용 범위를 함께 읽어야 합니다." },
        { label: "진행 공사", value: "발주자 동의 또는 계약 정리", note: "진행 중인 공사가 있다면 계약 정리 방식이 전체 일정과 가격에 직접 영향을 줍니다." },
      ]}
      processTitle="분할합병은 신고와 계약 구조를 잘못 읽으면 전체 일정이 틀어집니다"
      processSteps={[
        { title: "재편 목적 확인", body: "사업 분리인지, 면허 유지인지, 책임 분리인지 먼저 정해야 양도양수와 분할합병 중 맞는 구조가 보입니다." },
        { title: "현재 구조 읽기", body: "법인, 실적, 조합, 기술자, 자산, 진행 공사가 어떤 구조로 묶여 있는지 먼저 파악해야 합니다." },
        { title: "신고와 공고 일정 설계", body: "양도 공고 30일, 신고 서류, 계약 정리를 함께 잡지 못하면 거래 후반에 일정이 밀립니다." },
        { title: "진행 공사와 권리·의무 정리", body: "진행 중인 공사 승계, 발주자 동의, 계약 해지 가능성까지 포함해 최종 구조를 확정합니다." },
      ]}
      checklistTitle="초기 검토에 필요한 핵심 묶음"
      checklistGroups={[
        { title: "법인 구조", items: ["기존 법인 수와 역할", "지분 및 의사결정 구조", "재편 목적 우선순위"] },
        { title: "면허 / 실적 / 공사", items: ["유지해야 할 면허", "실적 활용 또는 승계 범위", "진행 중 공사와 발주자 동의 여부"] },
        { title: "문서 / 일정", items: ["양도 공고 계획", "신고 및 계약 문서", "세무·등기 단계별 일정"] },
      ]}
      notesTitle="퍼블릭 사이트에서 먼저 강조해야 할 최신 포인트"
      notes={[
        { title: "모든 케이스가 상담형입니다", body: "분할합병은 표준 견적보다 사전 구조 검토와 서류 선확인이 우선되어야 합니다." },
        { title: "양도양수와 분리해 설명해야 합니다", body: "같은 면허 이전처럼 보여도 공고 의무와 진행 공사 처리 구조가 달라 혼동하면 안 됩니다." },
        { title: "진행 공사가 가격과 일정을 바꿉니다", body: "발주자 동의나 계약 정리가 필요한 현장이 있으면 전체 실행 순서와 거래 조건이 크게 달라질 수 있습니다." },
      ]}
      referenceLinks={splitMergerReferenceLinks}
      referenceNote="2026.03.11 기준 국가법령정보센터 조문을 기준으로 정리했습니다. 실제 합병, 분할, 영업양수도 구조는 세무·등기 검토가 추가로 필요합니다."
      afterContent={(
        <>
          <LegacyPageDirectory
            title="이관된 분할합병 세부 안내"
            description="원본 사이트의 분할합병 안내 페이지를 그대로 연결했습니다."
            pages={importedPages}
          />
          <AiToolBridge variant="yangdo" />
        </>
      )}
    />
  );
}
