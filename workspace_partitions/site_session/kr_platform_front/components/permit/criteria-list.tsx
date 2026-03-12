/** CriteriaList — 개별 기준 pass/fail 체크리스트 */
import type { CriterionResult } from "@/lib/permit-types";
import { CheckCircle, XCircle, HelpCircle } from "lucide-react";

interface CriteriaListProps {
  criteria: CriterionResult[];
}

const STATUS_ICON = {
  pass: CheckCircle,
  fail: XCircle,
  unknown: HelpCircle,
} as const;

export function CriteriaList({ criteria }: CriteriaListProps) {
  return (
    <div className="permit-criteria">
      <h4 className="permit-criteria-title">등록기준 상세</h4>
      <ul className="permit-criteria-list">
        {criteria.map((c) => {
          const Icon = STATUS_ICON[c.status] ?? HelpCircle;
          return (
            <li key={c.field} className={`permit-criteria-item permit-criteria--${c.status}`}>
              <Icon size={16} aria-hidden="true" />
              <div className="permit-criteria-content">
                <span className="permit-criteria-label">{c.label}</span>
                {c.required != null && (
                  <span className="permit-criteria-detail">
                    필요: {String(c.required)} / 현재: {String(c.current ?? "—")}
                  </span>
                )}
                {c.note && <span className="permit-criteria-note">{c.note}</span>}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
