import type { Metadata } from "next";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { LegacyPageDirectory } from "@/components/legacy-page-directory";
import { ServiceDetailPage } from "@/components/service-detail-page";
import { getLegacyPagesByGroup } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";

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
      description="면허, 법인, 사업 구조를 재편하려는 고객에게 주요 검토 포인트를 정리하는 페이지입니다."
      breadcrumbLabel="분할합병"
      breadcrumbPath="/split-merger"
      heroLabel="구조 재편 검토"
      heroNote="개별 사안별 판단 필수"
      reviewedAt="2026.03.10"
      referenceText="조직개편 실무 및 면허 유지 검토"
      summaryCards={[
        { label: "핵심 성격", value: "정형화 어려움", note: "분할합병은 표준 답보다 개별 구조와 목적을 먼저 해석해야 합니다." },
        { label: "검토 축", value: "법인 · 면허 · 실적", note: "세 항목이 서로 어떻게 이동하거나 유지되는지가 핵심입니다." },
        { label: "비교 포인트", value: "양도양수와 다른 목적", note: "단순 인수보다 구조조정, 사업 분리, 재편 목적이 강한 경우가 많습니다." },
        { label: "실무 방식", value: "문서 선검토 필수", note: "초기 문서 확인 없이 방향을 단정하면 비용과 시간 손실이 커집니다." },
      ]}
      processTitle="분할합병은 목적을 잘못 읽으면 전체 구조가 틀어집니다"
      processSteps={[
        { title: "재편 목적 확인", body: "사업 분리, 면허 유지, 재무 정리, 책임 분리 중 무엇이 핵심인지 먼저 정해야 합니다." },
        { title: "현재 구조 해석", body: "기존 법인, 실적, 조합, 기술자, 자산이 어떤 구조로 묶여 있는지 먼저 읽어야 합니다." },
        { title: "이동 가능 범위 검토", body: "무엇을 유지하고 무엇을 넘길 수 있는지 법적·실무적 범위를 따져야 합니다." },
        { title: "실행 순서 설계", body: "문서, 등기, 세무, 실무 운영 순서를 맞추지 못하면 이후 정정 비용이 커질 수 있습니다." },
      ]}
      checklistTitle="초기 검토에 필요한 핵심 묶음"
      checklistGroups={[
        { title: "법인 구조", items: ["기존 법인 수와 역할", "지분 및 의사결정 구조", "재편 목적의 우선순위"] },
        { title: "면허 / 실적", items: ["유지해야 할 면허", "실적 승계 또는 활용 범위", "기술자 및 조합 상태"] },
        { title: "문서 / 세무", items: ["등기 및 계약 문서", "세무 이슈 가능성", "실행 일정과 단계별 리스크"] },
      ]}
      notesTitle="퍼블릭 사이트에서 먼저 안내해야 할 현실적인 메시지"
      notes={[
        { title: "모든 케이스가 상담형입니다", body: "분할합병은 표준 견적형 페이지보다 사전 구조 검토와 개별 상담이 우선되어야 합니다." },
        { title: "양도양수와 섞어 설명하면 오해가 생깁니다", body: "거래 목적이 다르기 때문에 퍼블릭 사이트에서도 분리된 메뉴와 문구가 필요합니다." },
        { title: "세무와 등기 타이밍이 중요합니다", body: "실행 순서가 어긋나면 뒤에서 복구 비용이 커질 수 있으므로 초기에 일정 설계가 필요합니다." },
      ]}
      afterContent={(
        <>
          <LegacyPageDirectory
            title="이관된 분할합병 세부 안내"
            description="원본 사이트의 분할합병 안내 페이지를 그대로 연결했습니다."
            pages={importedPages}
          />
          <div className="page-shell page-shell--inner" style={{ paddingTop: 0 }}>
            <AiToolBridge variant="yangdo" />
          </div>
        </>
      )}
    />
  );
}
