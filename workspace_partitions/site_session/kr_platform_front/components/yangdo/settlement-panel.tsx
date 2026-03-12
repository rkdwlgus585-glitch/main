/** SettlementPanel — 공제조합 정산 시나리오 (전기/통신/소방 전용) */
import type { SettlementScenario } from "@/lib/yangdo-types";
import { Landmark } from "lucide-react";

interface SettlementPanelProps {
  scenarios: SettlementScenario[];
}

export function SettlementPanel({ scenarios }: SettlementPanelProps) {
  return (
    <div className="yangdo-settlement">
      <div className="yangdo-settlement-header">
        <Landmark size={18} aria-hidden="true" />
        <h4>공제조합 출자금 정산 시나리오</h4>
      </div>
      <div className="yangdo-settlement-grid">
        {scenarios.map((s) => (
          <div key={s.mode} className="calc-result-card yangdo-settlement-card">
            <h5 className="yangdo-settlement-label">{s.label}</h5>
            <div className="yangdo-settlement-row">
              <span>출자금 잔액</span>
              <strong>{s.balance_eok.toFixed(2)} 억원</strong>
            </div>
            <div className="yangdo-settlement-row">
              <span>실지급 추정액</span>
              <strong>
                {s.cash_due_low_eok.toFixed(2)} ~ {s.cash_due_high_eok.toFixed(2)} 억원
              </strong>
            </div>
            {s.summary && <p className="yangdo-settlement-summary">{s.summary}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
