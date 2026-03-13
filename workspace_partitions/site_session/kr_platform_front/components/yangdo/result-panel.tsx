/** ResultPanel — 주요 산정 결과 표시 */
"use client";

import type { YangdoEstimateResponse } from "@/lib/yangdo-types";
import { AnimatedCounter } from "@/components/animated-counter";
import { RangeDisplay } from "@/components/shared/range-display";
import { ConfidenceMeter } from "@/components/shared/confidence-meter";
import { TrendingUp } from "lucide-react";

interface ResultPanelProps {
  result: YangdoEstimateResponse;
}

const PUB_MODE_LABELS: Record<string, string> = {
  full: "정상 산정",
  low_sample_diversity: "소수 표본",
  capped_confidence: "신뢰도 상한 적용",
  low_sample: "데이터 부족",
  manual_review: "수동 검토 필요",
  consult_only: "상담 전용",
};

export function ResultPanel({ result }: ResultPanelProps) {
  const center = result.public_center_eok ?? result.estimate_center_eok;
  const low = result.public_low_eok ?? result.estimate_low_eok;
  const high = result.public_high_eok ?? result.estimate_high_eok;
  const confidence = result.confidence_percent ?? 0;
  const hasEstimate = center != null && Number.isFinite(center) && center > 0;
  const isConsultOnly = result.publication_mode === "consult_only";

  return (
    <div className="calc-result-card yangdo-result-main">
      <div className="yangdo-result-header">
        <TrendingUp size={20} aria-hidden="true" />
        <h3>AI 추정 양도가</h3>
      </div>

      {hasEstimate ? (
        <>
          <div className="yangdo-result-center">
            <span className="yangdo-result-value">
              <AnimatedCounter end={Math.round((center ?? 0) * 100) / 100} suffix="" duration={1200} />
            </span>
            <span className="yangdo-result-unit">억원</span>
          </div>
          <RangeDisplay low={low ?? 0} center={center ?? 0} high={high ?? 0} />
        </>
      ) : (
        <div className="yangdo-result-center yangdo-result-consult-only">
          <p className="yangdo-result-consult-msg">
            {isConsultOnly
              ? "해당 업종은 데이터 기반 자동 산정이 어려워, 전문가 상담을 통해 정확한 양도가를 안내드립니다."
              : "산정 결과를 산출할 수 없습니다. 입력값을 확인해 주세요."}
          </p>
        </div>
      )}

      <div className="yangdo-result-meta">
        <ConfidenceMeter
          percent={confidence}
          label={`신뢰도 ${confidence}% — ${confidence >= 80 ? "높음" : confidence >= 50 ? "보통" : "낮음"}`}
        />
        {result.publication_mode && (
          <p className="yangdo-result-mode">
            산정 모드: <strong>{PUB_MODE_LABELS[result.publication_mode] ?? result.publication_mode}</strong>
          </p>
        )}
      </div>
    </div>
  );
}
