import { Calculator, ClipboardCheck, ExternalLink } from "lucide-react";
import { siteConfig } from "@/components/site-config";

type BridgeVariant = "full" | "yangdo" | "permit";

const tools = [
  {
    key: "yangdo" as const,
    title: "양도 기준 자가진단",
    body: "건설업 면허 양도 검토에 앞서 예상 가격 범위를 데이터 기반으로 먼저 가늠하는 도구입니다. 업종과 조건을 입력해 초기 판단에 활용할 수 있습니다.",
    href: `${siteConfig.platformHost}/yangdo`,
    icon: Calculator,
    label: "양도 기준 자가진단 바로가기",
  },
  {
    key: "permit" as const,
    title: "등록 기준 자가점검",
    body: "건설업 신규 등록 전에 자본금, 기술인력, 사무실 조건을 스스로 점검해 보는 도구입니다. 실제 접수 전 빠른 선별 단계로 활용할 수 있습니다.",
    href: `${siteConfig.platformHost}/permit`,
    icon: ClipboardCheck,
    label: "등록 기준 자가점검 바로가기",
  },
];

export function AiToolBridge({ variant = "full", featured = false }: { variant?: BridgeVariant; featured?: boolean }) {
  const visibleTools =
    variant === "full"
      ? tools
      : tools.filter((t) => t.key === variant);

  return (
    <section className={`ai-bridge-section${featured ? " ai-bridge-section--featured" : ""}`} aria-labelledby="ai-bridge-heading">
      <div className="section-header">
        <p className="eyebrow">AI Tools</p>
        <h2 id="ai-bridge-heading">
          {variant === "full"
            ? "자가점검 도구로 먼저 확인하고, 실제 판단은 상담에서 마무리"
            : variant === "yangdo"
              ? "양도 검토 기준을 먼저 가볍게 확인해 보세요"
              : "등록 기준 충족 여부를 먼저 점검해 보세요"}
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
              무료 도구 열기
              <ExternalLink size={14} aria-hidden="true" />
            </span>
          </a>
        ))}
      </div>
      <p className="ai-bridge-note">
        서울건설정보(seoulmna.kr)에서 제공하는 무료 자가점검 도구입니다. 결과는 참고용이며, 실제 신고·계약 판단은 이 사이트의 상담 절차에서 이어집니다.
      </p>
    </section>
  );
}
