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
};

export function ResultPanel({ result }: ResultPanelProps) {
  const center = result.public_center_eok ?? result.estimate_center_eok ?? 0;
  const low = result.public_low_eok ?? result.estimate_low_eok ?? 0;
  const high = result.public_high_eok ?? result.estimate_high_eok ?? 0;
  const confidence = result.confidence_percent ?? 0;

  return (
    <div className="calc-result-card yangdo-result-main">
      <div className="yangdo-result-header">
        <TrendingUp size={20} aria-hidden="true" />
        <h3>AI 추정 양도가</h3>
      </div>

      <div className="yangdo-result-center">
        <span className="yangdo-result-value">
          <AnimatedCounter end={Math.round(center * 100) / 100} suffix="" duration={1200} />
        </span>
        <span className="yangdo-result-unit">억원</span>
      </div>

      <RangeDisplay low={low} center={center} high={high} />

      <div className="yangdo-result-meta">
        <ConfidenceMeter percent={confidence} />
        {result.publication_mode && (
          <p className="yangdo-result-mode">
            산정 모드: <strong>{PUB_MODE_LABELS[result.publication_mode] ?? result.publication_mode}</strong>
          </p>
        )}
      </div>
    </div>
  );
}
