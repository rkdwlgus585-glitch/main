"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { Clock, Phone } from "lucide-react";
import { platformConfig } from "@/components/platform-config";

/**
 * /billing/checkout — Toss Payments billing auth widget.
 *
 * Loads the Toss SDK and opens the billing authorization window.
 * On success, redirects to /billing/success with authKey + customerKey.
 * On failure, redirects to /billing/fail.
 *
 * When NEXT_PUBLIC_TOSS_CLIENT_KEY is not configured, shows a friendly
 * "coming soon" page with contact info instead of a raw error.
 */
export default function BillingCheckoutPage() {
  const [status, setStatus] = useState<"loading" | "ready" | "coming_soon" | "error">("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const initiated = useRef(false);

  useEffect(() => {
    if (initiated.current) return;
    initiated.current = true;

    async function openBilling() {
      try {
        const clientKey = process.env.NEXT_PUBLIC_TOSS_CLIENT_KEY;
        if (!clientKey) {
          setStatus("coming_soon");
          return;
        }

        setStatus("ready");

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
      } catch {
        setErrorMsg("결제창을 열 수 없습니다. 잠시 후 다시 시도해 주세요.");
        setStatus("error");
      }
    }

    openBilling();
  }, []);

  /* ── Coming Soon: payment system not yet configured ── */
  if (status === "coming_soon") {
    return (
      <main id="main" className="page-shell billing-status-page">
        <div className="billing-status-card" role="status">
          <Clock size={48} className="billing-status-icon" aria-hidden="true" />
          <h1>온라인 결제 시스템 준비 중</h1>
          <p>
            온라인 결제 기능은 현재 준비 중입니다.
            <br />
            지금 바로 이용을 원하시면 전화로 문의해 주세요.
          </p>
          <div className="billing-status-actions">
            <a
              className="cta-primary"
              href={`tel:${platformConfig.contactPhone}`}
            >
              <Phone size={16} aria-hidden="true" />
              {platformConfig.contactPhone}
            </a>
            <Link className="cta-secondary" href="/billing">
              구독 관리로 돌아가기
            </Link>
          </div>
        </div>
      </main>
    );
  }

  /* ── Error state ── */
  if (status === "error") {
    return (
      <main id="main" className="page-shell billing-status-page">
        <div className="billing-status-card" role="alert">
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

  /* ── Loading state ── */
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
