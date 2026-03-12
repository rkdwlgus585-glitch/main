/** NextActions — 조치 항목 목록 */
import type { NextAction } from "@/lib/permit-types";
import { ArrowRight } from "lucide-react";

interface NextActionsProps {
  actions: NextAction[];
}

export function NextActions({ actions }: NextActionsProps) {
  const sorted = [...actions].sort((a, b) => a.priority - b.priority);

  return (
    <div className="permit-actions">
      <h4 className="permit-actions-title">다음 조치 사항</h4>
      <ol className="permit-actions-list">
        {sorted.map((act, i) => (
          <li key={i} className="permit-action-item">
            <div className="permit-action-header">
              <ArrowRight size={14} aria-hidden="true" />
              <span className="permit-action-text">{act.action}</span>
            </div>
            {act.detail && <p className="permit-action-detail">{act.detail}</p>}
            {act.estimated_cost_eok != null && (
              <span className="permit-action-cost">예상 비용: {act.estimated_cost_eok.toFixed(2)} 억원</span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
