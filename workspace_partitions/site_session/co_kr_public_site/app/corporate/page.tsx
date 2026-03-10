import type { Metadata } from "next";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { LegacyPageDirectory } from "@/components/legacy-page-directory";
import { ServiceDetailPage } from "@/components/service-detail-page";
import { getLegacyPagesByGroup } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";

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
      description="신규 진입 고객이 법인설립부터 면허 취득까지 어떤 순서로 움직여야 하는지 설명하는 페이지입니다."
      breadcrumbLabel="법인설립"
      breadcrumbPath="/corporate"
      heroLabel="신규 진입 준비"
      heroNote="설립과 등록을 함께 설계"
      reviewedAt="2026.03.10"
      referenceText="법인설립 절차 및 건설업등록 연계 검토"
      summaryCards={[
        { label: "출발점", value: "법인 구조 설계", note: "상호, 목적, 주주 구조를 단순하게 잡는 것이 이후 건설업등록과 운영에 유리합니다." },
        { label: "연결 포인트", value: "등록 준비 병행", note: "법인설립만 끝내고 등록 기준을 나중에 보면 중복 작업이 생기기 쉽습니다." },
        { label: "실무 축", value: "설립 후 즉시 준비", note: "계좌, 사무실, 인력 계획은 설립 직후보다 설립 전 검토가 효율적입니다." },
        { label: "상담 목적", value: "순서 오류 방지", note: "처음 순서를 잘못 잡으면 서류와 비용을 두 번 쓰는 경우가 많습니다." },
      ]}
      processTitle="법인설립은 건설업등록과 분리하지 말고 함께 설계해야 합니다"
      processSteps={[
        { title: "사업 방향 정리", body: "어떤 업종으로 진입할지, 양도양수와 신규 등록 중 무엇이 맞는지 먼저 나눠야 합니다." },
        { title: "법인 구조 결정", body: "상호, 목적, 자본금, 주주 구조를 향후 등록과 운영에 무리가 없도록 단순하게 설계합니다." },
        { title: "설립 후 필수 정비", body: "법인 계좌, 사무실, 세무 기초 세팅, 인력 계획까지 빠르게 이어져야 등록 단계로 넘어갈 수 있습니다." },
        { title: "등록 또는 확장 단계 연결", body: "설립 완료 직후 바로 건설업등록 또는 향후 업종 확장 계획으로 연결하는 흐름이 가장 효율적입니다." },
      ]}
      checklistTitle="설립 단계에서 먼저 정리해야 할 항목"
      checklistGroups={[
        { title: "법인 기본 구조", items: ["상호 및 목적 적정성", "주주 및 대표 구성", "자본금 설계와 출자 흐름"] },
        { title: "운영 인프라", items: ["사무실 확보 계획", "세무 기초 세팅", "법인 통장 및 기본 증빙 체계"] },
        { title: "향후 등록 준비", items: ["필요 기술인력 계획", "업종별 기준 검토", "양도양수와 신규 등록 비교"] },
      ]}
      notesTitle="신규 진입 고객이 자주 놓치는 포인트"
      notes={[
        { title: "법인 목적 문구는 나중에 비용이 될 수 있습니다", body: "초기 목적 설계를 부정확하게 하면 이후 정관 변경이나 보완 서류가 추가될 수 있습니다." },
        { title: "설립과 등록을 따로 보면 일정이 길어집니다", body: "설립 완료 후 등록 준비를 시작하면 사무실, 인력, 자본금 계획이 다시 흔들릴 수 있습니다." },
        { title: "양도양수가 더 맞는 경우도 있습니다", body: "신규 진입이라고 해서 항상 설립이 정답은 아니므로, 시간과 조건을 비교한 뒤 방향을 잡는 것이 좋습니다." },
      ]}
      afterContent={(
        <>
          <LegacyPageDirectory
            title="이관된 법인설립 세부 안내"
            description="원본 사이트의 법인설립 세부 콘텐츠를 그대로 연결했습니다."
            pages={importedPages}
          />
          <div className="page-shell page-shell--inner" style={{ paddingTop: 0 }}>
            <AiToolBridge variant="full" />
          </div>
        </>
      )}
    />
  );
}
