import Link from "next/link";
import type { Metadata } from "next";
import { widgetUrl } from "@/components/platform-config";
import { WidgetFrame } from "@/components/widget-frame";

export const metadata: Metadata = {
  robots: {
    index: false,
    follow: false,
  },
};

export default function PermitWidgetPage() {
  return (
    <main id="main" className="product-page">
      <Link className="back-link" href="/permit">
        ← 인허가 안내 페이지로
      </Link>
      <h1 className="sr-only">등록기준 AI 인허가 사전검토 실행</h1>
      <WidgetFrame
        title="등록기준 AI 인허가 사전검토"
        description="등록기준 충족 여부를 점검하는 전용 실행 화면입니다."
        widgetUrl={widgetUrl("permit")}
        eyebrow="전용 실행 화면"
        launchLabel="전용 화면에서 인허가 실행"
        gateNote="검색 봇과 원치 않는 호출을 막기 위해, 이 페이지도 실행 버튼을 누른 후에만 iframe을 엽니다."
      />
    </main>
  );
}
