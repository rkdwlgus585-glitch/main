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
    description: "대표 유형과 진입 동선을 먼저 확인합니다.",
    href: "/mna-market",
    icon: BriefcaseBusiness,
  },
  {
    title: "건설업등록",
    description: "등록기준과 준비 포인트를 바로 검토합니다.",
    href: "/permit",
    icon: Building2,
  },
  {
    title: "양도가 산정",
    description: "AI 기준 양도가 판단 흐름으로 이어집니다.",
    href: "/yangdo",
    icon: Calculator,
  },
  {
    title: "건설실무",
    description: "운영자가 자주 안내하는 실무 콘텐츠를 모읍니다.",
    href: "/knowledge",
    icon: Files,
  },
  {
    title: "고객센터",
    description: "전화 상담, 문의, 진행 흐름 안내로 연결됩니다.",
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
