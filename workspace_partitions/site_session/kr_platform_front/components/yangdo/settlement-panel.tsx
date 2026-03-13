/** SettlementPanel — 공제조합 정산 시나리오 (전기/통신/소방 전용) */
"use client";

import type { SettlementScenario } from "@/lib/yangdo-types";
import { AnimatedCounter } from "@/components/animated-counter";
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
              <strong><AnimatedCounter end={Math.round(s.balance_eok * 100) / 100} suffix="" duration={1000} /> 억원</strong>
            </div>
            <div className="yangdo-settlement-row">
              <span>실지급 추정액</span>
              <strong>
                <AnimatedCounter end={Math.round(s.cash_due_low_eok * 100) / 100} suffix="" duration={1000} /> ~ <AnimatedCounter end={Math.round(s.cash_due_high_eok * 100) / 100} suffix="" duration={1000} /> 억원
              </strong>
            </div>
            {s.summary && <p className="yangdo-settlement-summary">{s.summary}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
