import { platformConfig } from "@/components/platform-config";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div>
        <p className="eyebrow">Platform Topology</p>
        <strong>{platformConfig.platformFrontHost}</strong>
        <p>{"\uba54\uc778 \ud50c\ub7ab\ud3fc \uc9c4\uc785\uba74"}</p>
      </div>
      <div>
        <strong>{platformConfig.widgetConsumerHost}</strong>
        <p>{"\ub0b4\ubd80 \ubb34\uc81c\ud55c \uc704\uc82f \uc18c\ube44 \ucc44\ub110"}</p>
      </div>
      <div>
        <strong>{"Private Engine"}</strong>
        <p>{"\uacf5\uac1c \ube0c\ub79c\ub4dc\uc5d0\uc11c\ub294 \uc5d4\uc9c4 \ud638\uc2a4\ud2b8\ub97c \ub4dc\ub7ec\ub0b4\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4."}</p>
      </div>
      <div>
        <strong>{platformConfig.contactPhone}</strong>
        <p>{platformConfig.contactEmail}</p>
      </div>
    </footer>
  );
}
