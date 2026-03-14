/**
 * Toss Payments Billing API — server-side helpers.
 *
 * All calls use Basic auth with TOSS_SECRET_KEY.
 * These functions must ONLY be called from API routes (server-side).
 */

const TOSS_API = "https://api.tosspayments.com/v1";
const TIMEOUT_MS = 60_000; // billing API can take up to 60s

function authHeader(): string {
  const secret = process.env.TOSS_SECRET_KEY;
  if (!secret) throw new Error("TOSS_SECRET_KEY not configured");
  return `Basic ${Buffer.from(`${secret}:`).toString("base64")}`;
}

/** Exchange authKey (from billing auth redirect) for a billingKey. */
export async function issueBillingKey(
  authKey: string,
  customerKey: string,
): Promise<{ billingKey: string; cardCompany: string; cardNumber: string }> {
  const res = await fetch(`${TOSS_API}/billing/authorizations/issue`, {
    method: "POST",
    headers: {
      Authorization: authHeader(),
      "Content-Type": "application/json",
      "Idempotency-Key": `issue-${customerKey}-${Date.now()}`,
    },
    body: JSON.stringify({ authKey, customerKey }),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: "unknown" }));
    throw new Error(`Billing key issue failed: ${err.code ?? res.status}`);
  }

  const data = await res.json();
  return {
    billingKey: data.billingKey,
    cardCompany: data.card?.issuerCode ?? "",
    cardNumber: data.card?.number ?? "",
  };
}

/** Charge a subscription using a stored billingKey. */
export async function chargeBilling(params: {
  billingKey: string;
  customerKey: string;
  orderId: string;
  amount: number;
  orderName: string;
  customerEmail?: string;
  customerName?: string;
}): Promise<{ paymentKey: string; status: string }> {
  const res = await fetch(
    `${TOSS_API}/billing/${encodeURIComponent(params.billingKey)}`,
    {
      method: "POST",
      headers: {
        Authorization: authHeader(),
        "Content-Type": "application/json",
        "Idempotency-Key": params.orderId,
      },
      body: JSON.stringify({
        customerKey: params.customerKey,
        amount: params.amount,
        orderId: params.orderId,
        orderName: params.orderName,
        customerEmail: params.customerEmail,
        customerName: params.customerName,
        taxFreeAmount: 0,
      }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    },
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: "unknown" }));
    throw new Error(`Billing charge failed: ${err.code ?? res.status}`);
  }

  const data = await res.json();
  return { paymentKey: data.paymentKey, status: data.status };
}

/** Cancel (full or partial refund) a payment. */
export async function cancelPayment(params: {
  paymentKey: string;
  cancelReason: string;
  cancelAmount?: number;
}): Promise<{ status: string }> {
  const res = await fetch(
    `${TOSS_API}/payments/${encodeURIComponent(params.paymentKey)}/cancel`,
    {
      method: "POST",
      headers: {
        Authorization: authHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        cancelReason: params.cancelReason,
        ...(params.cancelAmount != null && {
          cancelAmount: params.cancelAmount,
        }),
      }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    },
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: "unknown" }));
    throw new Error(`Payment cancel failed: ${err.code ?? res.status}`);
  }

  const data = await res.json();
  return { status: data.status };
}

/** Query payment status by paymentKey. */
export async function getPayment(paymentKey: string): Promise<{
  status: string;
  totalAmount: number;
  approvedAt: string;
}> {
  const res = await fetch(
    `${TOSS_API}/payments/${encodeURIComponent(paymentKey)}`,
    {
      method: "GET",
      headers: { Authorization: authHeader() },
      signal: AbortSignal.timeout(30_000),
    },
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: "unknown" }));
    throw new Error(`Payment query failed: ${err.code ?? res.status}`);
  }

  const data = await res.json();
  return {
    status: data.status,
    totalAmount: data.totalAmount,
    approvedAt: data.approvedAt,
  };
}
