import Link from "next/link";
import { widgetUrl } from "@/components/platform-config";
import { WidgetFrame } from "@/components/widget-frame";

export default function YangdoPage() {
  return (
    <main className="product-page">
      <Link className="back-link" href="/">
        {"\ud50c\ub7ab\ud3fc \ud648\uc73c\ub85c"}
      </Link>
      <WidgetFrame
        title={"\uac74\uc124\uc5c5 AI \uc591\ub3c4\uac00 \uc0b0\uc815"}
        description={"\uc11c\uc6b8\uac74\uc124\uc815\ubcf4 \uba54\uc778 \ud50c\ub7ab\ud3fc\uc5d0\uc11c \uc2e4\uc81c \uc591\ub3c4\uac00 \uc0b0\uc815 \uc704\uc82f\uc744 \ubc14\ub85c \uc2e4\ud589\ud558\uace0 \uc0c1\ub2f4 \uc5f0\uacb0\uae4c\uc9c0 \uc774\uc5b4\uc9d1\ub2c8\ub2e4."}
        widgetUrl={widgetUrl("yangdo")}
        openUrl="/widget/yangdo"
        eyebrow={"\uc591\ub3c4\uac00 \uc2e4\ud589 \ud654\uba74"}
        launchLabel={"\uc591\ub3c4\uac00 \uc0b0\uc815 \uc2e4\ud589"}
        gateNote={"\ud398\uc774\uc9c0 \uc9c4\uc785\ub9cc\uc73c\ub85c\ub294 \uc678\ubd80 \uc5d4\uc9c4 \ud638\ucd9c\uc774 \uc2dc\uc791\ub418\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4. \uc2e4\uc81c \uc0b0\uc815\uc744 \uc6d0\ud560 \ub54c\ub9cc \uc2e4\ud589\uc744 \uc2dc\uc791\ud569\ub2c8\ub2e4."}
      />
    </main>
  );
}
