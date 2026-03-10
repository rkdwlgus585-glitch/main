import type { Metadata } from "next";
import Link from "next/link";
import { widgetUrl } from "@/components/platform-config";
import { WidgetFrame } from "@/components/widget-frame";

export const metadata: Metadata = {
  title: "AI 인허가 사전검토 | 서울건설정보",
  description:
    "191개 건설 업종 등록기준 충족 여부를 AI가 즉시 검토합니다. 자본금·기술인력·사무실 요건 진단과 신규 취득 비용 계산까지 무료 제공.",
};

export default function PermitPage() {
  return (
    <main className="product-page">
      <Link className="back-link" href="/">
        플랫폼 홈으로
      </Link>
      <WidgetFrame
        title="등록기준 AI 인허가 사전검토"
        description="등록기준 충족 여부를 메인 플랫폼에서 바로 검토하고, 부족 항목과 다음 조치를 즉시 확인할 수 있는 진입면입니다."
        widgetUrl={widgetUrl("permit")}
        openUrl="/widget/permit"
        eyebrow="인허가 실행 화면"
        launchLabel="인허가 사전검토 실행"
        gateNote="페이지 진입만으로는 외부 엔진 호출이 시작되지 않습니다. 점검을 원할 때만 실행을 시작합니다."
      />
    </main>
  );
}
