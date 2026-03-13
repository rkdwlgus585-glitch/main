/** RangeDisplay — low–center–high range bar visualization. */

interface RangeDisplayProps {
  low: number;
  center: number;
  high: number;
  unit?: string;
  label?: string;
}

export function RangeDisplay({ low, center, high, unit = "억원", label }: RangeDisplayProps) {
  const lo = Math.min(low, high);
  const hi = Math.max(low, high);
  const range = hi - lo;
  const centerPct = range > 0 ? ((center - lo) / range) * 100 : 50;

  return (
    <div className="calc-range" aria-label={label ?? "추정 범위"}>
      <div className="calc-range-bar">
        <div className="calc-range-fill" style={{ width: "100%" }}>
          <div
            className="calc-range-center-mark"
            style={{ left: `${Math.max(5, Math.min(95, centerPct))}%` }}
            aria-hidden="true"
          />
        </div>
      </div>
      <div className="calc-range-labels">
        <span className="calc-range-low">
          {low.toFixed(2)} {unit}
        </span>
        <span className="calc-range-center">
          <strong>{center.toFixed(2)}</strong> {unit}
        </span>
        <span className="calc-range-high">
          {high.toFixed(2)} {unit}
        </span>
      </div>
    </div>
  );
}
