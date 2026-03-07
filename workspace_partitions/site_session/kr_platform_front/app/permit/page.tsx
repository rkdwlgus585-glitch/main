import Link from "next/link";
import { widgetUrl } from "@/components/platform-config";
import { WidgetFrame } from "@/components/widget-frame";

export default function PermitPage() {
  return (
    <main className="product-page">
      <Link className="back-link" href="/">
        {"\ud50c\ub7ab\ud3fc \ud648\uc73c\ub85c"}
      </Link>
      <WidgetFrame
        title={"\ub4f1\ub85d\uae30\uc900 AI \uc778\ud5c8\uac00 \uc0ac\uc804\uac80\ud1a0"}
        description={"\ub4f1\ub85d\uae30\uc900 \ucda9\uc871 \uc5ec\ubd80\ub97c \uba54\uc778 \ud50c\ub7ab\ud3fc\uc5d0\uc11c \ubc14\ub85c \uac80\ud1a0\ud558\uace0, \ubd80\uc871 \ud56d\ubaa9\uacfc \ub2e4\uc74c \uc870\uce58\ub97c \uc989\uc2dc \ud655\uc778\ud560 \uc218 \uc788\ub294 \uc9c4\uc785\uba74\uc785\ub2c8\ub2e4."}
        widgetUrl={widgetUrl("permit")}
        openUrl="/widget/permit"
        eyebrow={"\uc778\ud5c8\uac00 \uc2e4\ud589 \ud654\uba74"}
        launchLabel={"\uc778\ud5c8\uac00 \uc0ac\uc804\uac80\ud1a0 \uc2e4\ud589"}
        gateNote={"\ud398\uc774\uc9c0 \uc9c4\uc785\ub9cc\uc73c\ub85c\ub294 \uc678\ubd80 \uc5d4\uc9c4 \ud638\ucd9c\uc774 \uc2dc\uc791\ub418\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4. \uc810\uac80\uc744 \uc6d0\ud560 \ub54c\ub9cc \uc2e4\ud589\uc744 \uc2dc\uc791\ud569\ub2c8\ub2e4."}
      />
    </main>
  );
}
