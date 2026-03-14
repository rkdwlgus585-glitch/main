"use client";

import Link from "next/link";
import { XCircle } from "lucide-react";

/**
 * /billing/fail — Billing auth failure callback.
 *
 * Displays error info from Toss redirect query params.
 */
export default function BillingFailPage() {
  // Toss redirects with ?code=...&message=... on failure
  const params = typeof window !== "undefined"
    ? new URLSearchParams(window.location.search)
    : new URLSearchParams();
  const errorCode = params.get("code") ?? "UNKNOWN";
  const errorMessage = params.get("message") ?? "결제 수단 등록에 실패했습니다.";

  return (
    <main id="main" className="page-shell billing-status-page">
      <div className="billing-status-card" role="alert">
        <XCircle size={48} className="billing-fail-icon" aria-hidden="true" />
        <h1>등록 실패</h1>
        <p>{errorMessage}</p>
        <p className="billing-error-code">오류 코드: {errorCode}</p>
        <div className="billing-status-actions">
          <Link className="cta-primary" href="/billing">
            다시 시도
          </Link>
          <Link className="cta-secondary" href="/">
            홈으로 이동
          </Link>
        </div>
      </div>
    </main>
  );
}
