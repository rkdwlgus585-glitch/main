"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { XCircle } from "lucide-react";

/**
 * /billing/fail — Billing auth failure callback.
 *
 * Displays error info from Toss redirect query params.
 * Wrapped in Suspense because useSearchParams() requires it in Next.js.
 */
function FailContent() {
  const searchParams = useSearchParams();
  const errorCode = searchParams.get("code") ?? "UNKNOWN";
  const errorMessage = searchParams.get("message") ?? "결제 수단 등록에 실패했습니다.";

  return (
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
  );
}

export default function BillingFailPage() {
  return (
    <main id="main" className="page-shell billing-status-page">
      <Suspense
        fallback={
          <div className="billing-status-card">
            <div className="billing-spinner" aria-label="로딩 중" role="status" />
            <p>정보를 불러오는 중...</p>
          </div>
        }
      >
        <FailContent />
      </Suspense>
    </main>
  );
}
