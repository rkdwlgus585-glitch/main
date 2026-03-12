import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  Brain,
  ClipboardCheck,
  ShieldCheck,
} from "lucide-react";

const engines: Array<{
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
}> = [
  {
    title: "AI 양도가 산정 엔진",
    description:
      "공시 재무·시장 거래·업종별 특성을 종합 분석해 적정 양도가격 범위와 신뢰도 지표를 함께 제공합니다.",
    href: "/yangdo",
    icon: Brain,
  },
  {
    title: "AI 인허가 검토 엔진",
    description:
      "191개 업종의 등록기준을 실시간 비교 분석합니다. 항목별 충족 여부를 진단하고 신규 취득 비용을 계산합니다.",
    href: "/permit",
    icon: ClipboardCheck,
  },
  {
    title: "특허 출원 기술",
    description:
      "AI 양도가 산정과 AI 인허가 사전검토 알고리즘은 한국특허청(KIPO)에 특허 출원된 독자 기술입니다.",
    href: "/about",
    icon: ShieldCheck,
  },
];

export function HomeShortcuts() {
  return (
    <section className="home-shortcuts" aria-label="AI 엔진 소개">
      <div className="section-header">
        <p className="eyebrow">핵심 기술</p>
        <h2>두 개의 AI 엔진, 하나의 플랫폼</h2>
      </div>
      <div className="home-shortcuts-grid">
        {engines.map(({ title, description, href, icon: Icon }) => (
          <Link key={title} href={href} className="home-shortcut-card">
            <span className="home-shortcut-icon" aria-hidden="true">
              <Icon size={20} />
            </span>
            <strong>{title}</strong>
            <p>{description}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
