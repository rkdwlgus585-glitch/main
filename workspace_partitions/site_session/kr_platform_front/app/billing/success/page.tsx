"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { CheckCircle } from "lucide-react";

/**
 * /billing/success — Billing auth success callback.
 *
 * Receives authKey + customerKey from Toss redirect query params.
 * Exchanges authKey for billingKey via /api/billing/issue.
 */
export default function BillingSuccessPage() {
  const [status, setStatus] = useState<"processing" | "done" | "error">("processing");
  const [cardInfo, setCardInfo] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    async function issueBilling() {
      try {
        const params = new URLSearchParams(window.location.search);
        const authKey = params.get("authKey");
        const customerKey = params.get("customerKey");

        if (!authKey || !customerKey) {
          setErrorMsg("필수 정보가 누락되었습니다.");
          setStatus("error");
          return;
        }

        const res = await fetch("/api/billing/issue", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ authKey, customerKey }),
        });

        const data = await res.json();

        if (!data.ok) {
          setErrorMsg("카드 등록에 실패했습니다. 다시 시도해 주세요.");
          setStatus("error");
          return;
        }

        setCardInfo(`${data.cardCompany} ****${data.cardLast4}`);
        setStatus("done");
      } catch {
        setErrorMsg("서버 연결에 실패했습니다.");
        setStatus("error");
      }
    }

    issueBilling();
  }, []);

  if (status === "processing") {
    return (
      <main id="main" className="page-shell billing-status-page">
        <div className="billing-status-card">
          <div className="billing-spinner" aria-label="처리 중" role="status" />
          <h1>카드 등록 중</h1>
          <p>결제 수단을 등록하고 있습니다...</p>
        </div>
      </main>
    );
  }

  if (status === "error") {
    return (
      <main id="main" className="page-shell billing-status-page">
        <div className="billing-status-card">
          <h1>등록 실패</h1>
          <p>{errorMsg}</p>
          <div className="billing-status-actions">
            <Link className="cta-primary" href="/billing">
              다시 시도
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main id="main" className="page-shell billing-status-page">
      <div className="billing-status-card billing-status-card--success">
        <CheckCircle size={48} className="billing-success-icon" aria-hidden="true" />
        <h1>구독이 시작되었습니다</h1>
        <p className="billing-card-detail">{cardInfo}</p>
        <p>1개월 무료 체험이 시작되었습니다. 체험 종료 7일 전 이메일로 안내드립니다.</p>
        <div className="billing-status-actions">
          <Link className="cta-primary" href="/yangdo">
            AI 양도가 산정 시작
          </Link>
          <Link className="cta-secondary" href="/permit">
            AI 인허가 검토 시작
          </Link>
        </div>
      </div>
    </main>
  );
}
