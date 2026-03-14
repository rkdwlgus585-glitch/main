"use client";

import Link from "next/link";

export default function BillingError() {
  return (
    <main id="main" className="page-shell billing-status-page">
      <div className="billing-status-card">
        <h1>오류가 발생했습니다</h1>
        <p>구독 관리 페이지를 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.</p>
        <div className="billing-status-actions">
          <Link className="cta-primary" href="/">
            홈으로 이동
          </Link>
        </div>
      </div>
    </main>
  );
}
