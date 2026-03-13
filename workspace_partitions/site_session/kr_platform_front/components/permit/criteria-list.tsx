/** CriteriaList — 개별 기준 pass/fail 체크리스트 */
import type { CriterionResult } from "@/lib/permit-types";
import { CheckCircle, XCircle, HelpCircle, ListChecks } from "lucide-react";

interface CriteriaListProps {
  criteria: CriterionResult[];
}

const STATUS_ICON = {
  pass: CheckCircle,
  fail: XCircle,
  unknown: HelpCircle,
} as const;

/** Format required/current display values. */
function fmtValue(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "boolean") return v ? "보유" : "미보유";
  const n = Number(v);
  if (!Number.isNaN(n)) return n.toLocaleString("ko-KR");
  return String(v);
}

export function CriteriaList({ criteria }: CriteriaListProps) {
  if (!criteria.length) {
    return (
      <div className="permit-criteria">
        <h4 className="permit-criteria-title">등록기준 상세</h4>
        <div className="calc-empty-state">
          <ListChecks size={24} className="calc-empty-state-icon" aria-hidden="true" />
          <p>등록기준 상세 정보가 없습니다.</p>
        </div>
      </div>
    );
  }

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
                    필요: {fmtValue(c.required)} / 현재: {fmtValue(c.current)}
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
