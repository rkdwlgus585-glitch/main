/** ScaleModeSelector — 시공능력 vs 실적 토글 (WAI-ARIA radio group) */
"use client";

import { useId, useCallback } from "react";

interface ScaleModeSelectorProps {
  mode: "specialty" | "sales";
  onChange: (mode: "specialty" | "sales") => void;
}

const MODES: readonly ("specialty" | "sales")[] = ["specialty", "sales"];
const LABELS: Record<string, string> = { specialty: "시공능력 평가액", sales: "연간 실적" };
const HINTS: Record<string, string> = {
  specialty: "KISCON 공시 시공능력 평가액을 기준으로 산정합니다.",
  sales: "최근 3년 또는 5년 연평균 실적을 기준으로 산정합니다.",
};

export function ScaleModeSelector({ mode, onChange }: ScaleModeSelectorProps) {
  const groupId = useId();

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const idx = MODES.indexOf(mode);
      let next = idx;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        next = (idx + 1) % MODES.length;
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        next = (idx - 1 + MODES.length) % MODES.length;
      }
      if (next !== idx) onChange(MODES[next]);
    },
    [mode, onChange],
  );

  return (
    <fieldset className="yangdo-scale-mode">
      <legend className="calc-field-label">산정 기준</legend>
      <div className="yangdo-scale-mode-btns" role="radiogroup" aria-label="산정 기준 선택" onKeyDown={handleKeyDown}>
        {MODES.map((m) => (
          <button
            key={m}
            type="button"
            role="radio"
            aria-checked={mode === m}
            tabIndex={mode === m ? 0 : -1}
            className={`yangdo-scale-btn${mode === m ? " yangdo-scale-btn--active" : ""}`}
            onClick={() => onChange(m)}
            id={`${groupId}-${m}`}
          >
            {LABELS[m]}
          </button>
        ))}
      </div>
      <p className="calc-field-hint yangdo-scale-mode-hint">{HINTS[mode]}</p>
    </fieldset>
  );
}
