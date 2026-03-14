import type { Metadata } from "next";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { LegacyPageDirectory } from "@/components/legacy-page-directory";
import { ServiceDetailPage } from "@/components/service-detail-page";
import { getLegacyPagesByGroup } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";
import { registrationReferenceLinks, regulatoryReviewedAt } from "@/lib/regulatory-guidance";

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
      description="신규 등록 또는 추가 등록을 준비하는 고객에게 현재 법령 기준의 등록요건과 접수 절차를 먼저 안내하는 페이지입니다."
      breadcrumbLabel="건설업등록"
      breadcrumbPath="/registration"
      heroLabel="신규 등록 / 추가 등록"
      heroNote="법령 기준 먼저 점검"
      reviewedAt={regulatoryReviewedAt}
      referenceText="건설산업기본법 제10조 · 시행령 제13조 · 시행규칙 제2조"
      summaryCards={[
        { label: "등록 기준", value: "자본금 · 보증 · 기술인력 · 사무실/장비", note: "업종별 핵심 기준은 시행령 제13조와 별표 2를 먼저 보는 편이 가장 빠릅니다." },
        { label: "접수 창구", value: "시·도지사 또는 수탁기관", note: "시행규칙 제2조는 전자문서 제출도 허용하고 있어 접수 준비 경로를 먼저 나눠야 합니다." },
        { label: "처리 기준", value: "등록신청서 서식 기준 20일", note: "실제 보완 요구가 발생하면 체감 일정은 더 길어질 수 있으므로 자료 완성도를 먼저 맞춰야 합니다." },
        { label: "최근 변경", value: "주력분야 추가 등록 서류 일부 생략", note: "2025년 6월 2일 시행규칙 개정으로 전문공사 주력분야 추가 등록 절차가 일부 완화됐습니다." },
      ]}
      processTitle="건설업등록은 접수보다 업종별 등록기준을 먼저 맞추는 구조가 중요합니다"
      processSteps={[
        { title: "업종과 등록 유형 결정", body: "신규 등록인지, 추가 등록인지, 전문공사 주력분야 추가인지에 따라 첨부서류와 검토 포인트가 달라집니다." },
        { title: "등록기준 충족 여부 확인", body: "자본금, 보증가능금액, 기술인력, 사무실, 업종별 장비 보유 여부를 현재 상태 기준으로 먼저 대조합니다." },
        { title: "신청서와 증빙 서류 정리", body: "건설업등록신청서와 재무, 인력, 사무실 증빙을 한 묶음으로 맞춰야 보완 요구가 줄어듭니다." },
        { title: "접수 후 보완 대응", body: "관할 시도 또는 수탁기관의 보완 요구까지 포함해 일정을 잡아야 실질 처리기간을 통제할 수 있습니다." },
      ]}
      checklistTitle="등록 신청 전에 반드시 정리해야 할 기준 묶음"
      checklistGroups={[
        { title: "재무 / 보증", items: ["업종별 자본금 기준 확인", "보증가능금액 확인 가능 여부 점검", "최근 재무자료와 예치 흐름 정리"] },
        { title: "기술인력", items: ["필수 기술자 수와 자격 구분", "겸직·중복·상시근무 여부 확인", "4대보험과 급여이체 흐름 점검"] },
        { title: "사무실 / 장비", items: ["독립 사무공간 요건 검토", "임대차 또는 사용승낙 증빙 정리", "장비 업종일 경우 보유·임차 증빙 확인"] },
      ]}
      notesTitle="실제 등록 준비에서 자주 놓치는 최신 포인트"
      notes={[
        { title: "법인설립만으로 등록이 끝나지 않습니다", body: "법인 설립과 건설업 등록은 별도 단계이므로 정관과 자본 구조를 등록기준과 함께 설계해야 중복 작업이 줄어듭니다." },
        { title: "추가 등록은 기존 법인 상태가 더 중요합니다", body: "이미 운영 중인 법인의 재무, 기술인력, 조합 상태가 신규 등록보다 큰 변수로 작용할 수 있습니다." },
        { title: "주력분야 추가 등록은 최근 규정 변화를 확인해야 합니다", body: "전문공사 주력분야 추가 등록은 2025년 개정 규정으로 일부 서류가 달라졌기 때문에 예전 체크리스트를 그대로 쓰면 안 됩니다." },
      ]}
      referenceLinks={registrationReferenceLinks}
      referenceNote="2026.03.11 기준 국가법령정보센터 기준을 반영했습니다. 업종과 관할 시도, 수탁기관에 따라 추가 보완서류가 요구될 수 있습니다."
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
