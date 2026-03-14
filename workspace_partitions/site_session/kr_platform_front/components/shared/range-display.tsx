/** RangeDisplay — low–center–high range bar visualization. */

interface RangeDisplayProps {
  low: number;
  center: number;
  high: number;
  unit?: string;
  label?: string;
}

/** Format number: up to 2 decimals, strip trailing zeros. */
function fmt(n: number): string {
  const s = n.toFixed(2);
  return s.replace(/\.?0+$/, "") || "0";
}

export function RangeDisplay({ low, center, high, unit = "억원", label }: RangeDisplayProps) {
  const safeLow = Number.isFinite(low) ? low : 0;
  const safeCenter = Number.isFinite(center) ? center : 0;
  const safeHigh = Number.isFinite(high) ? high : 0;
  const lo = Math.min(safeLow, safeHigh);
  const hi = Math.max(safeLow, safeHigh);
  const range = hi - lo;
  const centerPct = range > 0 ? ((safeCenter - lo) / range) * 100 : 50;

  /* Zero-range: all three values are identical — show single value instead */
  if (range === 0) {
    return (
      <div className="calc-range calc-range--single" aria-label={label ?? "추정 값"}>
        <p className="calc-range-single-value">
          <strong>{fmt(safeCenter)}</strong> {unit}
        </p>
      </div>
    );
  }

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
          {fmt(safeLow)} {unit}
        </span>
        <span className="calc-range-center">
          <strong>{fmt(safeCenter)}</strong> {unit}
        </span>
        <span className="calc-range-high">
          {fmt(safeHigh)} {unit}
        </span>
      </div>
    </div>
  );
}
