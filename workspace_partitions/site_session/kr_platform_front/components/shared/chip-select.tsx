/** ChipSelect — quick-pick chip button row for license selection. */

"use client";

interface ChipOption {
  value: string;
  label: string;
  count?: number;
}

interface ChipSelectProps {
  options: ChipOption[];
  selected?: string;
  onSelect: (value: string) => void;
  label?: string;
}

export function ChipSelect({ options, selected, onSelect, label }: ChipSelectProps) {
  if (!options.length) return null;

  return (
    <div className="calc-chips" role="group" aria-label={label ?? "빠른 선택"}>
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          className={`calc-chip${selected === opt.value ? " calc-chip--active" : ""}`}
          onClick={() => onSelect(opt.value)}
          aria-pressed={selected === opt.value}
        >
          {opt.label}
          {opt.count != null && <span className="calc-chip-count">{opt.count}</span>}
        </button>
      ))}
    </div>
  );
}
