/**
 * Platform status bar — now shows user-facing operational status
 * instead of internal topology.
 */
export function PlatformStatus() {
  return (
    <div className="status-bar" role="status" aria-label="서비스 상태">
      <span className="status-dot" aria-hidden="true" />
      <span>AI 분석 엔진 정상 운영 중</span>
    </div>
  );
}
