export default function BillingLoading() {
  return (
    <main id="main" className="page-shell billing-status-page" role="status" aria-label="구독 관리 페이지 로딩 중">
      <div className="billing-status-card">
        <div className="billing-spinner" />
        <p>로딩 중...</p>
      </div>
    </main>
  );
}
