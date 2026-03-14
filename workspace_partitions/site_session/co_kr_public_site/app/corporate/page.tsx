import type { Metadata } from "next";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { LegacyPageDirectory } from "@/components/legacy-page-directory";
import { ServiceDetailPage } from "@/components/service-detail-page";
import { getLegacyPagesByGroup } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";
import { corporateReferenceLinks, regulatoryReviewedAt } from "@/lib/regulatory-guidance";

export const metadata: Metadata = buildPageMetadata(
  "/corporate",
  "법인설립",
  "건설업 신규 진입을 위한 법인설립과 등록 준비 흐름을 안내하는 페이지입니다.",
);

export default function CorporatePage() {
  const importedPages = getLegacyPagesByGroup("corporate");

  return (
    <ServiceDetailPage
      eyebrow="Corporate Setup"
      title="법인설립"
      description="신규 진입 고객이 법인설립부터 건설업 등록 준비까지 어떤 순서로 움직여야 하는지 최신 기준으로 설명하는 페이지입니다."
      breadcrumbLabel="법인설립"
      breadcrumbPath="/corporate"
      heroLabel="신규 진입 준비"
      heroNote="설립과 등록을 함께 설계"
      reviewedAt={regulatoryReviewedAt}
      referenceText="법인설립 이후 건설업등록 연계 기준"
      summaryCards={[
        { label: "핵심 원칙", value: "설립과 등록은 별도 절차", note: "법인설립 자체가 건설업 등록을 대신하지 않으므로 설립 단계부터 등록요건을 동시에 검토해야 합니다." },
        { label: "설계 포인트", value: "정관 목적 · 자본 구조", note: "향후 건설업등록과 업종 확장에 맞게 목적 문구와 자본 흐름을 단순하게 잡는 것이 유리합니다." },
        { label: "설립 직후 준비", value: "사무실 · 통장 · 인력 계획", note: "설립 후 별도로 고민하기보다 설립 전에 바로 이어질 운영 인프라를 함께 설계해야 합니다." },
        { label: "비교 판단", value: "신규 등록 vs 양도양수", note: "시간과 실적 활용 목적에 따라 설립보다 양도양수가 더 맞는 경우도 있으므로 초기에 같이 비교해야 합니다." },
      ]}
      processTitle="법인설립은 건설업등록 준비와 분리하지 말고 한 흐름으로 설계해야 합니다"
      processSteps={[
        { title: "진입 방식 결정", body: "신규 등록으로 갈지, 양도양수로 갈지 먼저 나누고 법인설립의 필요성을 판단합니다." },
        { title: "법인 기본 구조 설계", body: "상호, 목적, 주주 구조, 자본금 규모를 향후 건설업등록과 세무 운영에 무리 없도록 설계합니다." },
        { title: "설립 직후 인프라 연결", body: "법인 통장, 사무실, 세무 기초 세팅, 기술인력 계획을 바로 이어서 등록 준비 단계로 넘깁니다." },
        { title: "등록 기준과 비교 검토", body: "설립이 끝난 뒤가 아니라 설립 전부터 등록기준과 양도양수 대안을 동시에 비교해야 중복 비용이 줄어듭니다." },
      ]}
      checklistTitle="설립 단계에서 먼저 정리해야 할 항목"
      checklistGroups={[
        { title: "정관 / 주주 구조", items: ["건설업 목적 문구 검토", "주주 및 대표 구성", "출자 흐름과 자본금 계획"] },
        { title: "운영 인프라", items: ["사무실 확보 계획", "법인 통장과 세무 기초 세팅", "인력 채용 또는 승계 계획"] },
        { title: "등록 연계", items: ["업종별 등록기준 확인", "보증가능금액 준비 가능성", "신규 등록과 양도양수 비교"] },
      ]}
      notesTitle="신규 진입 고객이 자주 놓치는 최신 포인트"
      notes={[
        { title: "정관 목적 문구는 나중에 비용이 될 수 있습니다", body: "초기 목적 설계를 부정확하게 하면 등록 단계에서 정관 변경이나 보완 서류가 추가될 수 있습니다." },
        { title: "설립 후 준비가 아니라 설립 전 준비가 중요합니다", body: "설립 완료 후 등록 요건을 맞추기 시작하면 사무실, 인력, 보증 구조를 다시 손보는 경우가 많습니다." },
        { title: "설립이 항상 정답은 아닙니다", body: "실적 활용, 일정, 업종 확장 목표를 보면 신규 설립보다 양도양수가 더 효율적인 경우도 많습니다." },
      ]}
      referenceLinks={corporateReferenceLinks}
      referenceNote="2026.03.11 기준 건설업등록 연계 법령을 기준으로 정리했습니다. 법인등기와 세무 실무는 개별 상황에 따라 추가 검토가 필요합니다."
      afterContent={(
        <>
          <LegacyPageDirectory
            title="이관된 법인설립 세부 안내"
            description="원본 사이트의 법인설립 세부 콘텐츠를 그대로 연결했습니다."
            pages={importedPages}
          />
          <AiToolBridge variant="full" />
        </>
      )}
    />
  );
}
