/** ResultBadge — status badge (pass / shortfall / warning / manual_review). */

import { CheckCircle, AlertTriangle, XCircle, HelpCircle } from "lucide-react";

type BadgeStatus = "pass" | "shortfall" | "fail" | "warning" | "manual_review" | "unknown";

interface ResultBadgeProps {
  status: BadgeStatus;
  label?: string;
}

const CONFIG: Record<BadgeStatus, { icon: typeof CheckCircle; text: string }> = {
  pass: { icon: CheckCircle, text: "충족" },
  shortfall: { icon: XCircle, text: "미충족" },
  fail: { icon: XCircle, text: "미충족" },
  warning: { icon: AlertTriangle, text: "주의" },
  manual_review: { icon: HelpCircle, text: "수동 확인" },
  unknown: { icon: HelpCircle, text: "확인 필요" },
};

export function ResultBadge({ status, label }: ResultBadgeProps) {
  const cfg = CONFIG[status] ?? CONFIG.unknown;
  const Icon = cfg.icon;

  return (
    <span className={`calc-badge calc-badge--${status}`} aria-label={label ?? cfg.text}>
      <Icon size={14} aria-hidden="true" />
      {label ?? cfg.text}
    </span>
  );
}
