/** NumberInput — numeric input with unit suffix (억원, 명, 대). */

"use client";

import { useId } from "react";

interface NumberInputProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  suffix?: string;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  "aria-describedby"?: string;
}

export function NumberInput({
  id,
  value,
  onChange,
  placeholder,
  suffix,
  min,
  max,
  step,
  disabled,
  ...rest
}: NumberInputProps) {
  const fallbackId = useId();
  const inputId = id ?? fallbackId;

  return (
    <div className="calc-number-input">
      <input
        id={inputId}
        type="number"
        inputMode="decimal"
        className="calc-number-input-field"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        min={min}
        max={max}
        step={step ?? "any"}
        disabled={disabled}
        aria-describedby={rest["aria-describedby"]}
      />
      {suffix && <span className="calc-number-input-suffix" aria-hidden="true">{suffix}</span>}
    </div>
  );
}
