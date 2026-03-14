/** ConfidenceMeter — circular ring gauge for AI estimation confidence.
 *  Renders an SVG ring that fills based on the percentage value.
 *  Also shows a flat progress bar for linear context.
 */
"use client";

interface ConfidenceMeterProps {
  percent: number;
  label?: string;
}

const RING_SIZE = 80;
const STROKE = 6;
const RADIUS = (RING_SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function ConfidenceMeter({ percent, label }: ConfidenceMeterProps) {
  const safe = Number.isFinite(percent) ? percent : 0;
  const clamped = Math.max(0, Math.min(100, safe));
  const level = clamped >= 80 ? "high" : clamped >= 50 ? "mid" : "low";
  const offset = CIRCUMFERENCE - (clamped / 100) * CIRCUMFERENCE;
  const levelLabel = clamped >= 80 ? "높음" : clamped >= 50 ? "보통" : "낮음";

  return (
    <div className="calc-confidence">
      <div className="calc-confidence-ring-wrap">
        {/* SVG circular gauge */}
        <svg
          className="calc-confidence-ring"
          width={RING_SIZE}
          height={RING_SIZE}
          viewBox={`0 0 ${RING_SIZE} ${RING_SIZE}`}
          role="progressbar"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <circle
            className="calc-confidence-ring-bg"
            cx={RING_SIZE / 2}
            cy={RING_SIZE / 2}
            r={RADIUS}
            fill="none"
            strokeWidth={STROKE}
          />
          <circle
            className={`calc-confidence-ring-fill calc-confidence--${level}`}
            cx={RING_SIZE / 2}
            cy={RING_SIZE / 2}
            r={RADIUS}
            fill="none"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            transform={`rotate(-90 ${RING_SIZE / 2} ${RING_SIZE / 2})`}
          />
        </svg>
        <div className="calc-confidence-ring-text">
          <span className={`calc-confidence-ring-value calc-confidence--${level}`}>{clamped}</span>
          <span className="calc-confidence-ring-pct">%</span>
        </div>
      </div>
      <div className="calc-confidence-info">
        <span className="calc-confidence-label">AI 신뢰도</span>
        <span className={`calc-confidence-level calc-confidence--${level}`}>{levelLabel}</span>
      </div>
    </div>
  );
}
