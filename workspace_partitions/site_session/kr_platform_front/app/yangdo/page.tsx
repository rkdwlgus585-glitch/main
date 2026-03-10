import type { Metadata } from "next";
import Link from "next/link";
import { widgetUrl } from "@/components/platform-config";
import { WidgetFrame } from "@/components/widget-frame";

export const metadata: Metadata = {
  title: "AI 양도가 산정 | 서울건설정보",
  description:
    "건설업 면허 양도가격을 AI가 공시 데이터 기반으로 무료 산정합니다. 실시간 시세 분석, 업종별 정산 로직, 전문가 상담 연결까지 원스톱 제공.",
};

export default function YangdoPage() {
  return (
    <main className="product-page">
      <Link className="back-link" href="/">
        플랫폼 홈으로
      </Link>
      <WidgetFrame
        title="건설업 AI 양도가 산정"
        description="서울건설정보 메인 플랫폼에서 실제 양도가 산정 위젯을 바로 실행하고 상담 연결까지 이어집니다."
        widgetUrl={widgetUrl("yangdo")}
        openUrl="/widget/yangdo"
        eyebrow="양도가 실행 화면"
        launchLabel="양도가 산정 실행"
        gateNote="페이지 진입만으로는 외부 엔진 호출이 시작되지 않습니다. 실제 산정을 원할 때만 실행을 시작합니다."
      />
    </main>
  );
}
