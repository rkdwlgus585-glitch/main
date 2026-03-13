/** RangeDisplay — low–center–high range bar visualization. */

interface RangeDisplayProps {
  low: number;
  center: number;
  high: number;
  unit?: string;
  label?: string;
}

export function RangeDisplay({ low, center, high, unit = "억원", label }: RangeDisplayProps) {
  const safeLow = Number.isFinite(low) ? low : 0;
  const safeCenter = Number.isFinite(center) ? center : 0;
  const safeHigh = Number.isFinite(high) ? high : 0;
  const lo = Math.min(safeLow, safeHigh);
  const hi = Math.max(safeLow, safeHigh);
  const range = hi - lo;
  const centerPct = range > 0 ? ((safeCenter - lo) / range) * 100 : 50;

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
          {safeLow.toFixed(2)} {unit}
        </span>
        <span className="calc-range-center">
          <strong>{safeCenter.toFixed(2)}</strong> {unit}
        </span>
        <span className="calc-range-high">
          {safeHigh.toFixed(2)} {unit}
        </span>
      </div>
    </div>
  );
}
