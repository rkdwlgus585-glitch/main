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
    <main className="product-page">
      <Link className="back-link" href="/yangdo">
        {"\uc591\ub3c4\uac00 \uc548\ub0b4 \ud398\uc774\uc9c0\ub85c"}
      </Link>
      <WidgetFrame
        title={"\uac74\uc124\uc5c5 AI \uc591\ub3c4\uac00 \uc0b0\uc815"}
        description={"\uc591\ub3c4\uac00 \ubc94\uc704\ub97c \ucd94\uc815\ud558\ub294 \uc804\uc6a9 \uc2e4\ud589 \ud654\uba74\uc785\ub2c8\ub2e4."}
        widgetUrl={widgetUrl("yangdo")}
        eyebrow={"\uc804\uc6a9 \uc2e4\ud589 \ud654\uba74"}
        launchLabel={"\uc804\uc6a9 \ud654\uba74\uc5d0\uc11c \uc591\ub3c4\uac00 \uc2e4\ud589"}
        gateNote={"\uac80\uc0c9 \ubd07\uacfc \uc6d0\uce58 \uc54a\ub294 \ud638\ucd9c\uc744 \ub9c9\uae30 \uc704\ud574, \uc774 \ud398\uc774\uc9c0\ub3c4 \uc2e4\ud589 \ubc84\ud2bc\uc744 \ub204\ub978 \ud6c4\uc5d0\ub9cc iframe\uc744 \uc5fd\ub2c8\ub2e4."}
      />
    </main>
  );
}
