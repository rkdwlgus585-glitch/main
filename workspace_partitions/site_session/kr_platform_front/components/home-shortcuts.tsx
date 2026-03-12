import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  Building2,
  Calculator,
  MessagesSquare,
} from "lucide-react";

const shortcuts: Array<{
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
}> = [
  {
    title: "AI 양도가 산정",
    description: "AI가 적정 양도가격을 무료로 분석해 드립니다.",
    href: "/yangdo",
    icon: Calculator,
  },
  {
    title: "AI 인허가 검토",
    description: "191개 업종 등록기준과 비용을 바로 확인합니다.",
    href: "/permit",
    icon: Building2,
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
