/** AiThinkingOverlay — Premium AI analysis animation shown during API calls.
 *  Replaces plain spinner with multi-stage "AI thinking" visualization.
 *  Shows pulsing nodes, rotating ring, and progressive status messages.
 */
"use client";

import { useEffect, useState } from "react";
import { BrainCircuit } from "lucide-react";

const STAGES: readonly string[] = [
  "데이터 수집 중…",
  "AI 모델 분석 중…",
  "산업 패턴 비교 중…",
  "결과 도출 중…",
];

interface AiThinkingOverlayProps {
  /** Whether the overlay is active */
  active: boolean;
  /** Context label (e.g., "양도가 산정", "인허가 검토") */
  context?: string;
  /** Total expected duration in ms — drives stage timing */
  expectedMs?: number;
}

export function AiThinkingOverlay({
  active,
  context,
  expectedMs = 4000,
}: AiThinkingOverlayProps) {
  const [stageIdx, setStageIdx] = useState(0);

  useEffect(() => {
    if (!active) {
      setStageIdx(0);
      return;
    }
    const interval = expectedMs / STAGES.length;
    const timer = setInterval(() => {
      setStageIdx((prev) => Math.min(prev + 1, STAGES.length - 1));
    }, interval);
    return () => clearInterval(timer);
  }, [active, expectedMs]);

  if (!active) return null;

  return (
    <div className="ai-thinking" aria-label="AI 분석 진행 중">
      {/* Screen reader live announce — text changes on each stage */}
      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {STAGES[stageIdx]}
      </p>

      {/* Pulsing ring */}
      <div className="ai-thinking-ring" aria-hidden="true">
        <div className="ai-thinking-ring-outer" />
        <div className="ai-thinking-ring-inner" />
        <BrainCircuit size={28} className="ai-thinking-icon" />
      </div>

      {/* Context label */}
      {context && <p className="ai-thinking-context">{context}</p>}

      {/* Stage progress */}
      <div className="ai-thinking-stages">
        {STAGES.map((label, i) => (
          <div
            key={label}
            className={`ai-thinking-stage${
              i < stageIdx ? " ai-thinking-stage--done" : i === stageIdx ? " ai-thinking-stage--active" : ""
            }`}
          >
            <span className="ai-thinking-stage-dot" aria-hidden="true" />
            <span className="ai-thinking-stage-label">{label}</span>
          </div>
        ))}
      </div>

      {/* Progress bar */}
      <div className="ai-thinking-progress" aria-hidden="true">
        <div
          className="ai-thinking-progress-fill"
          style={{ width: `${Math.min(((stageIdx + 1) / STAGES.length) * 100, 95)}%` }}
        />
      </div>
    </div>
  );
}
