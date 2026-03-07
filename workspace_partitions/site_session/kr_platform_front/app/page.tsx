import { CapabilityStrip } from "@/components/capability-strip";
import { Hero } from "@/components/hero";
import { PlatformTopology } from "@/components/platform-topology";
import { PlatformStatus } from "@/components/platform-status";
import { ProductCard } from "@/components/product-card";
import { WorkflowGrid } from "@/components/workflow-grid";

export default function HomePage() {
  return (
    <main className="page-shell">
      <Hero />
      <PlatformStatus />
      <CapabilityStrip />
      <section className="product-grid">
        <ProductCard
          href="/yangdo"
          badge="System A"
          title={"\uac74\uc124\uc5c5 AI \uc591\ub3c4\uac00 \uc0b0\uc815"}
          description={"\uacf5\uc720 \ub9e4\ubb3c \ub124\ud2b8\uc6cc\ud06c\uc758 \uc911\ubcf5 \uc624\uc5fc\uc744 \ub204\ub974\uace0, \uadfc\uac70\ubc00\ub3c4\uc640 \uc2e0\ub8b0\ub3c4\ub97c \ud568\uaed8 \ubcf4\uc5ec\uc8fc\ub294 \uacf5\uac1c \uc0b0\uc815 \uc2dc\uc2a4\ud15c\uc785\ub2c8\ub2e4."}
          bullets={[
            "\ubcf5\ud569\uba74\ud5c8 \ub9e4\uce6d \uc624\ucc28 \uac10\uc810",
            "\uc911\ubcf5\ub9e4\ubb3c \uad70\uc9d1 \ubcf4\uc815 \ubc18\uc601",
            "\ud30c\ud2b8\ub108 \uc774\uc2dd\uc6a9 widget/API \ub3d9\uc2dc \uc81c\uacf5",
          ]}
        />
        <ProductCard
          href="/permit"
          badge="System B"
          title={"\ub4f1\ub85d\uae30\uc900 AI \uc778\ud5c8\uac00 \uc0ac\uc804\uac80\ud1a0"}
          description={"\uc790\ubcf8\uae08, \uae30\uc220\uc778\ub825, \uc0ac\ubb34\uc2e4, \uc7a5\ube44, \ucd94\uac00 \ub4f1\ub85d\uae30\uc900\uc744 \ud558\ub098\uc758 \uc0ac\uc804\uac80\ud1a0 \ud750\ub984\uc73c\ub85c \uc81c\uacf5\ud558\ub294 \uacf5\uac1c \uc785\uad6c\uc785\ub2c8\ub2e4."}
          bullets={[
            "\ub4f1\ub85d\uae30\uc900 \ud56d\ubaa9\ubcc4 gap \uc9c4\ub2e8",
            "\uc99d\ube59 \uccb4\ud06c\ub9ac\uc2a4\ud2b8\uc640 next action \uc81c\uc2dc",
            "\ud0c0\uc0ac \uc774\uc2dd\uc6a9 \uc911\uc559 \uc5d4\uc9c4 \uc7ac\uc0ac\uc6a9",
          ]}
        />
      </section>
      <WorkflowGrid />
      <PlatformTopology />
      <section className="narrative-band">
        <div>
          <p className="eyebrow">Platform Principle</p>
          <h2>{"\uacc4\uc0b0\uae30\ub97c \ubcf5\uc81c\ud558\uc9c0 \uc54a\uace0 \ud50c\ub7ab\ud3fc\uc73c\ub85c \uc6b4\uc601\ud569\ub2c8\ub2e4."}</h2>
          <p>
            {"\uc591\ub3c4\uac00 \uc0b0\uc815\uacfc \uc778\ud5c8\uac00 \uc0ac\uc804\uac80\ud1a0\ub294 \uac01\uac01 \ubcc4\ub3c4 \uc2dc\uc2a4\ud15c\uc73c\ub85c \uc6b4\uc601\ud558\uace0, \ud14c\ub10c\ud2b8\u00b7\ucc44\ub110\u00b7\uacfc\uae08\u00b7\uc704\uc82f \ubc30\ud3ec\ub9cc \uacf5\uc720 \ud50c\ub7ab\ud3fc\uc73c\ub85c \uad00\ub9ac\ud569\ub2c8\ub2e4. \uc774 \uad6c\uc870\uac00 \uc11c\uc6b8\uac74\uc124\uc815\ubcf4 \uc790\uccb4 \uc6b4\uc601\uacfc \ud0c0\uc0ac \uc774\uc2dd \ubaa8\ub450\uc5d0 \uc720\ub9ac\ud569\ub2c8\ub2e4."}
          </p>
        </div>
      </section>
    </main>
  );
}
