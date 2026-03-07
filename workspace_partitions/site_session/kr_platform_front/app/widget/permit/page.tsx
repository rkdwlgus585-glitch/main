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
    <main className="product-page">
      <Link className="back-link" href="/permit">
        {"\uc778\ud5c8\uac00 \uc548\ub0b4 \ud398\uc774\uc9c0\ub85c"}
      </Link>
      <WidgetFrame
        title={"\ub4f1\ub85d\uae30\uc900 AI \uc778\ud5c8\uac00 \uc0ac\uc804\uac80\ud1a0"}
        description={"\ub4f1\ub85d\uae30\uc900 \ucda9\uc871 \uc5ec\ubd80\ub97c \uc810\uac80\ud558\ub294 \uc804\uc6a9 \uc2e4\ud589 \ud654\uba74\uc785\ub2c8\ub2e4."}
        widgetUrl={widgetUrl("permit")}
        eyebrow={"\uc804\uc6a9 \uc2e4\ud589 \ud654\uba74"}
        launchLabel={"\uc804\uc6a9 \ud654\uba74\uc5d0\uc11c \uc778\ud5c8\uac00 \uc2e4\ud589"}
        gateNote={"\uac80\uc0c9 \ubd07\uacfc \uc6d0\uce58 \uc54a\ub294 \ud638\ucd9c\uc744 \ub9c9\uae30 \uc704\ud574, \uc774 \ud398\uc774\uc9c0\ub3c4 \uc2e4\ud589 \ubc84\ud2bc\uc744 \ub204\ub978 \ud6c4\uc5d0\ub9cc iframe\uc744 \uc5fd\ub2c8\ub2e4."}
      />
    </main>
  );
}
