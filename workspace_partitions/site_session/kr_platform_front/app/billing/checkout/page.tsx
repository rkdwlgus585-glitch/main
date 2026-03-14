"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";

/**
 * /billing/checkout — Toss Payments billing auth widget.
 *
 * Loads the Toss SDK and opens the billing authorization window.
 * On success, redirects to /billing/success with authKey + customerKey.
 * On failure, redirects to /billing/fail.
 */
export default function BillingCheckoutPage() {
  const [status, setStatus] = useState<"loading" | "error">("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const initiated = useRef(false);

  useEffect(() => {
    if (initiated.current) return;
    initiated.current = true;

    async function openBilling() {
      try {
        const clientKey = process.env.NEXT_PUBLIC_TOSS_CLIENT_KEY;
        if (!clientKey) {
          setErrorMsg("결제 시스템 설정이 완료되지 않았습니다.");
          setStatus("error");
          return;
        }

        const { loadTossPayments } = await import(
          "@tosspayments/tosspayments-sdk"
        );
        const toss = await loadTossPayments(clientKey);

        // Generate a unique customerKey per user session
        // In production, this should be the user's UUID from your auth system
        const customerKey = crypto.randomUUID();

        const payment = toss.payment({ customerKey });

        await payment.requestBillingAuth({
          method: "CARD",
          successUrl: `${window.location.origin}/billing/success`,
          failUrl: `${window.location.origin}/billing/fail`,
        });
      } catch (err) {
        console.error("[checkout] Billing auth error:", err);
        setErrorMsg("결제창을 열 수 없습니다. 잠시 후 다시 시도해 주세요.");
        setStatus("error");
      }
    }

    openBilling();
  }, []);

  if (status === "error") {
    return (
      <main id="main" className="page-shell billing-status-page">
        <div className="billing-status-card">
          <h1>결제 오류</h1>
          <p>{errorMsg}</p>
          <div className="billing-status-actions">
            <Link className="cta-primary" href="/billing">
              돌아가기
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main id="main" className="page-shell billing-status-page">
      <div className="billing-status-card">
        <div className="billing-spinner" aria-label="결제창 여는 중" role="status" />
        <h1>결제 수단 등록</h1>
        <p>토스페이먼츠 결제창을 여는 중입니다...</p>
      </div>
    </main>
  );
}
