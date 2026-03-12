/** DiagnosisResult — 전체 상태 + 항목별 갭 분석 */
import type { PermitPrecheckResponse } from "@/lib/permit-types";
import { ResultBadge } from "@/components/shared/result-badge";
import { AlertTriangle, TrendingDown } from "lucide-react";

interface DiagnosisResultProps {
  result: PermitPrecheckResponse;
}

export function DiagnosisResult({ result }: DiagnosisResultProps) {
  const status = result.overall_status ?? "unknown";

  return (
    <div className="calc-result-card permit-diagnosis-main">
      <div className="permit-diagnosis-header">
        <div>
          <h3>{result.service_name ?? "검토 결과"}</h3>
          <ResultBadge status={status} />
        </div>
      </div>

      {/* Shortfall gap cards */}
      {result.shortfall_items && result.shortfall_items.length > 0 && (
        <div className="permit-gap-section">
          <div className="permit-gap-title">
            <TrendingDown size={16} aria-hidden="true" />
            <h4>미충족 항목</h4>
          </div>
          <div className="permit-gap-grid">
            {result.shortfall_items.map((item) => (
              <div key={item.field} className="permit-gap-card">
                <span className="permit-gap-label">{item.label}</span>
                <div className="permit-gap-row">
                  <span>필요</span>
                  <strong>{String(item.required)}</strong>
                </div>
                <div className="permit-gap-row">
                  <span>현재</span>
                  <strong className="permit-gap-current">{String(item.current)}</strong>
                </div>
                {item.gap != null && (
                  <div className="permit-gap-row permit-gap-deficit">
                    <span>부족</span>
                    <strong>{String(item.gap)}</strong>
                  </div>
                )}
                {item.estimated_cost_eok != null && (
                  <p className="permit-gap-cost">예상 보완 비용: {item.estimated_cost_eok.toFixed(2)} 억원</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Total shortfall cost */}
      {result.total_shortfall_cost_eok != null && result.total_shortfall_cost_eok > 0 && (
        <div className="permit-total-cost">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>총 예상 보완 비용: <strong>{result.total_shortfall_cost_eok.toFixed(2)} 억원</strong></span>
        </div>
      )}
    </div>
  );
}
