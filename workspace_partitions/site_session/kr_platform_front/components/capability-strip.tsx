import { Blocks, Building2, ShieldCheck, Waypoints } from "lucide-react";

const items = [
  {
    icon: Blocks,
    title: "분리된 시스템",
    body: "양도가 산정과 인허가 사전검토는 별도 시스템으로 운영하고, 테넌트·채널·과금만 플랫폼 레이어에서 공유합니다.",
  },
  {
    icon: Waypoints,
    title: "비공개 엔진",
    body: "공개 브랜드는 .kr에 집중하고, 실제 산정과 판정은 비공개 엔진에서 처리합니다.",
  },
  {
    icon: ShieldCheck,
    title: "운영 게이트",
    body: "tenant, channel, usage, activation gate를 통해 무단 오픈과 과금 누락을 막습니다.",
  },
  {
    icon: Building2,
    title: "이식 전제",
    body: "iframe, embed, 서버-서버 API를 모두 고려한 구조로 타사 이식과 내부 확장을 동시에 염두에 둡니다.",
  },
];

export function CapabilityStrip() {
  return (
    <section className="capability-strip">
      {items.map(({ icon: Icon, title, body }) => (
        <article className="capability-card" key={title}>
          <Icon size={22} strokeWidth={2.1} />
          <strong>{title}</strong>
          <p>{body}</p>
        </article>
      ))}
    </section>
  );
}
