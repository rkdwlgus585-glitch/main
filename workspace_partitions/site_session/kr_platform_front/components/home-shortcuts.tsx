import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  BriefcaseBusiness,
  Building2,
  Calculator,
  Files,
  MessagesSquare,
} from "lucide-react";

const shortcuts: Array<{
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
}> = [
  {
    title: "실시간 매물",
    description: "지금 거래 가능한 건설업 면허 매물을 확인하세요.",
    href: "/mna-market",
    icon: BriefcaseBusiness,
  },
  {
    title: "건설업등록",
    description: "191개 업종 등록기준과 비용을 바로 확인합니다.",
    href: "/permit",
    icon: Building2,
  },
  {
    title: "양도가 산정",
    description: "AI가 적정 양도가격을 무료로 분석해 드립니다.",
    href: "/yangdo",
    icon: Calculator,
  },
  {
    title: "건설실무",
    description: "양도양수·등록기준·시장 동향 가이드를 모았습니다.",
    href: "/knowledge",
    icon: Files,
  },
  {
    title: "고객센터",
    description: "전문 행정사에게 전화 또는 온라인으로 상담하세요.",
    href: "/consult",
    icon: MessagesSquare,
  },
];

export function HomeShortcuts() {
  return (
    <section className="home-shortcuts" aria-label="빠른 진입 메뉴">
      <div className="home-shortcuts-grid">
        {shortcuts.map(({ title, description, href, icon: Icon }) => (
          <Link key={title} href={href} className="home-shortcut-card">
            <span className="home-shortcut-icon" aria-hidden="true">
              <Icon size={18} />
            </span>
            <strong>{title}</strong>
            <p>{description}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
