/** ConfidenceMeter — percentage gauge for estimation confidence. */

interface ConfidenceMeterProps {
  percent: number;
  label?: string;
}

export function ConfidenceMeter({ percent, label }: ConfidenceMeterProps) {
  const safe = Number.isFinite(percent) ? percent : 0;
  const clamped = Math.max(0, Math.min(100, safe));
  const level = clamped >= 80 ? "high" : clamped >= 50 ? "mid" : "low";

  return (
    <div className="calc-confidence" aria-label={label ?? `신뢰도 ${clamped}%`}>
      <div className="calc-confidence-header">
        <span className="calc-confidence-label">신뢰도</span>
        <span className={`calc-confidence-value calc-confidence--${level}`}>
          {clamped}%
        </span>
      </div>
      <div className="calc-confidence-track" role="progressbar" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100}>
        <div
          className={`calc-confidence-fill calc-confidence--${level}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
