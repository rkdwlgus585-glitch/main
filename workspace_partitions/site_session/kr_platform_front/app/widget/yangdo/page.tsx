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

export default function YangdoWidgetPage() {
  return (
    <main id="main" className="product-page">
      <Link className="back-link" href="/yangdo">
        양도가 안내 페이지로
      </Link>
      <WidgetFrame
        title="건설업 AI 양도가 산정"
        description="양도가 범위를 추정하는 전용 실행 화면입니다."
        widgetUrl={widgetUrl("yangdo")}
        eyebrow="전용 실행 화면"
        launchLabel="전용 화면에서 양도가 실행"
        gateNote="검색 봇과 원치 않는 호출을 막기 위해, 이 페이지도 실행 버튼을 누른 후에만 iframe을 엽니다."
      />
    </main>
  );
}
