export default function Loading() {
  return (
    <div className="page-status-shell">
      <div className="loading-shell" aria-live="polite" aria-busy="true">
        <span className="loading-bar loading-bar--eyebrow" />
        <span className="loading-bar loading-bar--title" />
        <span className="loading-bar loading-bar--body" />
        <div className="loading-grid">
          <div className="loading-card" />
          <div className="loading-card" />
          <div className="loading-card" />
        </div>
      </div>
    </div>
  );
}
