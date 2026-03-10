import { Calculator, ClipboardCheck, ExternalLink } from "lucide-react";
import { siteConfig } from "@/components/site-config";

type BridgeVariant = "full" | "yangdo" | "permit";

const tools = [
  {
    key: "yangdo" as const,
    title: "AI 양도가 산정",
    body: "건설업 면허 양도 예상 가격 범위를 AI가 데이터 기반으로 산정합니다. 업종과 조건을 입력하면 즉시 결과를 확인할 수 있습니다.",
    href: `${siteConfig.platformHost}/yangdo`,
    icon: Calculator,
    label: "양도가 산정 바로가기",
  },
  {
    key: "permit" as const,
    title: "AI 인허가 사전검토",
    body: "건설업 신규 등록에 필요한 기준 충족 여부를 AI가 사전 진단합니다. 자본금, 기술인력, 사무실 조건을 한번에 점검할 수 있습니다.",
    href: `${siteConfig.platformHost}/permit`,
    icon: ClipboardCheck,
    label: "인허가 검토 바로가기",
  },
];

export function AiToolBridge({ variant = "full" }: { variant?: BridgeVariant }) {
  const visibleTools =
    variant === "full"
      ? tools
      : tools.filter((t) => t.key === variant);

  return (
    <section className="ai-bridge-section" aria-labelledby="ai-bridge-heading">
      <div className="section-header">
        <p className="eyebrow">AI Tools</p>
        <h2 id="ai-bridge-heading">
          {variant === "full"
            ? "AI 도구로 먼저 확인하고, 상담은 그 다음에"
            : variant === "yangdo"
              ? "양도가를 AI로 먼저 확인해 보세요"
              : "등록 기준 충족 여부를 AI로 사전 점검해 보세요"}
        </h2>
      </div>
      <div className={`ai-bridge-grid${visibleTools.length === 1 ? " ai-bridge-grid--single" : ""}`}>
        {visibleTools.map(({ key, title, body, href, icon: Icon, label }) => (
          <a
            key={key}
            href={href}
            className="ai-bridge-card"
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`${label} (서울건설정보 새 창)`}
          >
            <span className="ai-bridge-icon" aria-hidden="true">
              <Icon size={22} />
            </span>
            <strong>{title}</strong>
            <p>{body}</p>
            <span className="ai-bridge-action">
              무료로 이용하기
              <ExternalLink size={14} aria-hidden="true" />
            </span>
          </a>
        ))}
      </div>
      <p className="ai-bridge-note">
        서울건설정보(seoulmna.kr)에서 제공하는 무료 AI 도구입니다. 결과 확인 후 이 사이트에서 전문 상담을 이어갈 수 있습니다.
      </p>
    </section>
  );
}
