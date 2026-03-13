/** DiagnosisResult — 전체 상태 + 항목별 갭 분석 */
"use client";

import type { PermitPrecheckResponse } from "@/lib/permit-types";
import { ResultBadge } from "@/components/shared/result-badge";
import { AnimatedCounter } from "@/components/animated-counter";
import { AlertTriangle, TrendingDown, CheckCircle } from "lucide-react";

/** Format shortfall field values for Korean display. */
function formatFieldValue(v: unknown): string {
  if (typeof v === "boolean") return v ? "보유" : "미보유";
  if (v == null) return "—";
  const n = Number(v);
  if (!Number.isNaN(n)) return n.toLocaleString("ko-KR");
  return String(v);
}

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

      {/* All pass message */}
      {status === "pass" && (!result.shortfall_items || result.shortfall_items.length === 0) && (
        <div className="permit-pass-message">
          <CheckCircle size={20} aria-hidden="true" />
          <span>모든 등록기준을 충족합니다.</span>
        </div>
      )}

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
                  <strong>{formatFieldValue(item.required)}</strong>
                </div>
                <div className="permit-gap-row">
                  <span>현재</span>
                  <strong className="permit-gap-current">{formatFieldValue(item.current)}</strong>
                </div>
                {item.gap != null && (
                  <div className="permit-gap-row permit-gap-deficit">
                    <span>부족</span>
                    <strong>{formatFieldValue(item.gap)}</strong>
                  </div>
                )}
                {item.estimated_cost_eok != null && (
                  <p className="permit-gap-cost">예상 보완 비용: <AnimatedCounter end={Math.round(item.estimated_cost_eok * 100) / 100} suffix="" duration={1000} /> 억원</p>
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
          <span>총 예상 보완 비용: <strong><AnimatedCounter end={Math.round(result.total_shortfall_cost_eok * 100) / 100} suffix="" duration={1200} /> 억원</strong></span>
        </div>
      )}
    </div>
  );
}
