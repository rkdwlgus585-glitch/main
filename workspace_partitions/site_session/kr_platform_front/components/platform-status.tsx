import { platformConfig } from "@/components/platform-config";

export function PlatformStatus() {
  return (
    <section className="status-grid">
      <div>
        <span>{"\ud50c\ub7ab\ud3fc \uc804\uba74"}</span>
        <strong>{platformConfig.platformFrontHost}</strong>
      </div>
      <div>
        <span>{"\ub9e4\ubb3c \uc0ac\uc774\ud2b8"}</span>
        <strong>{platformConfig.listingHost}</strong>
      </div>
      <div>
        <span>{"\uc0c1\ub2f4"}</span>
        <strong>{platformConfig.contactPhone}</strong>
      </div>
    </section>
  );
}
