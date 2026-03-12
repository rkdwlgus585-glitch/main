/** ScaleModeSelector — 시공능력 vs 실적 토글 */
"use client";

import { useId } from "react";

interface ScaleModeSelectorProps {
  mode: "specialty" | "sales";
  onChange: (mode: "specialty" | "sales") => void;
}

export function ScaleModeSelector({ mode, onChange }: ScaleModeSelectorProps) {
  const groupId = useId();

  return (
    <fieldset className="yangdo-scale-mode" aria-label="산정 기준 선택">
      <legend className="calc-field-label">산정 기준</legend>
      <div className="yangdo-scale-mode-btns" role="radiogroup">
        <button
          type="button"
          role="radio"
          aria-checked={mode === "specialty"}
          className={`yangdo-scale-btn${mode === "specialty" ? " yangdo-scale-btn--active" : ""}`}
          onClick={() => onChange("specialty")}
          id={`${groupId}-spec`}
        >
          시공능력 평가액
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={mode === "sales"}
          className={`yangdo-scale-btn${mode === "sales" ? " yangdo-scale-btn--active" : ""}`}
          onClick={() => onChange("sales")}
          id={`${groupId}-sales`}
        >
          연간 실적
        </button>
      </div>
    </fieldset>
  );
}
