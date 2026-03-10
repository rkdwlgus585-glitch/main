import type { Metadata } from "next";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { LegacyPageDirectory } from "@/components/legacy-page-directory";
import { ServiceDetailPage } from "@/components/service-detail-page";
import { getLegacyPagesByGroup } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";

export const metadata: Metadata = buildPageMetadata(
  "/registration",
  "건설업등록",
  "신규 등록과 추가 등록을 준비하는 고객을 위한 건설업등록 기준과 절차 안내 페이지입니다.",
);

export default function RegistrationPage() {
  const importedPages = getLegacyPagesByGroup("registration");

  return (
    <ServiceDetailPage
      eyebrow="Registration"
      title="건설업등록"
      description="신규 등록 또는 추가 등록을 준비하는 고객에게 등록기준과 절차를 먼저 안내하는 페이지입니다."
      breadcrumbLabel="건설업등록"
      breadcrumbPath="/registration"
      heroLabel="신규 등록 / 추가 등록"
      heroNote="등록기준 먼저 점검"
      reviewedAt="2026.03.10"
      referenceText="건설업 등록기준 및 실무 서류 기준"
      summaryCards={[
        { label: "기본 축", value: "자본금 · 기술인력 · 사무실", note: "등록기준은 세 항목의 균형을 먼저 보는 것이 효율적입니다." },
        { label: "초기 판단", value: "업종별 기준 확인", note: "업종마다 필요한 인력과 장비 조건이 달라 처음부터 구분해야 합니다." },
        { label: "실무 흐름", value: "서류 준비 후 접수", note: "준비 없는 접수보다 누락 없는 사전 검토가 비용과 시간을 줄입니다." },
        { label: "상담 포인트", value: "기준 충족 가능성", note: "현재 상태로 가능한지, 보완 후 가능한지를 먼저 나눠 판단합니다." },
      ]}
      processTitle="건설업등록은 접수보다 사전 판단 구조가 더 중요합니다"
      processSteps={[
        { title: "업종과 목적 확인", body: "신규 설립 직후 등록인지, 기존 법인에 추가 등록인지부터 구분해야 이후 조건이 정리됩니다." },
        { title: "기준 충족 여부 점검", body: "자본금, 기술인력, 사무실, 필요 시 장비 항목을 현재 상태 기준으로 빠르게 분류합니다." },
        { title: "누락 항목 보완", body: "서류와 인력, 사무실 조건 중 미흡한 부분을 먼저 보완해야 접수 이후 리스크가 줄어듭니다." },
        { title: "접수와 후속 대응", body: "접수 이후 보완 요청 가능성을 고려해 운영자가 후속 대응 동선을 함께 잡아야 합니다." },
      ]}
      checklistTitle="등록 전 반드시 정리해야 할 기본 체크리스트"
      checklistGroups={[
        { title: "자본금", items: ["업종별 기준 금액 확인", "최근 재무 상태 정리", "증빙 가능한 형태인지 검토"] },
        { title: "기술인력", items: ["필수 기술자 수 확인", "자격 및 중복 여부 점검", "4대보험 및 상시근무 요건 확인"] },
        { title: "사무실 / 장비", items: ["독립 사무공간 요건 검토", "임대차 또는 사용 증빙 정리", "장비 업종일 경우 보유 조건 확인"] },
      ]}
      notesTitle="실제 운영 관점에서 놓치기 쉬운 부분"
      notes={[
        { title: "기준 충족과 유지 관리는 다릅니다", body: "접수 시점에만 맞추는 구조는 이후 유지 관리에서 바로 문제를 만들 수 있으므로 운영 계획까지 함께 봐야 합니다." },
        { title: "추가 등록은 기존 상태가 더 중요합니다", body: "이미 있는 법인의 재무, 실적, 인력 상태가 신규 등록보다 더 큰 변수로 작동할 수 있습니다." },
        { title: "서류 명칭보다 연결 관계가 중요합니다", body: "등기, 재무, 인력 자료가 각각 따로 있어도 상호 일치하지 않으면 보완 시간이 길어집니다." },
      ]}
      afterContent={(
        <>
          <LegacyPageDirectory
            title="이관된 건설업등록 세부 안내"
            description="원본 사이트에서 사용하던 등록 기준, 실무 설명 페이지를 그대로 연결했습니다."
            pages={importedPages}
          />
          <AiToolBridge variant="permit" />
        </>
      )}
    />
  );
}
