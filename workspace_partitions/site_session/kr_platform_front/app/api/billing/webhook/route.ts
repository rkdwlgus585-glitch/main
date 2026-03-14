import crypto from "crypto";
import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/billing/webhook
 * Toss Payments webhook receiver.
 * Verifies HMAC-SHA256 signature and processes payment status changes.
 *
 * Must respond 200 within 10 seconds or Toss retries (up to 7 times over ~4 days).
 */
export async function POST(req: NextRequest) {
  const webhookSecret = process.env.TOSS_WEBHOOK_SECRET;
  if (!webhookSecret) {
    console.error("[webhook] TOSS_WEBHOOK_SECRET not configured");
    return NextResponse.json({ ok: false }, { status: 500 });
  }

  // 1. Read raw body before parsing
  const rawBody = await req.text();
  const transmissionTime =
    req.headers.get("tosspayments-webhook-transmission-time") ?? "";
  const signature = req.headers.get("tosspayments-signature") ?? "";

  // 2. HMAC-SHA256 verification
  const expected = crypto
    .createHmac("sha256", webhookSecret)
    .update(`${rawBody}:${transmissionTime}`)
    .digest("hex");

  if (expected !== signature) {
    console.warn("[webhook] Signature mismatch — rejecting");
    return NextResponse.json({ ok: false }, { status: 401 });
  }

  // 3. Parse and dispatch
  try {
    const event = JSON.parse(rawBody);

    if (event.eventType === "PAYMENT_STATUS_CHANGED") {
      const { paymentKey, status, orderId } = event.data ?? {};

      if (status === "DONE") {
        // Payment succeeded — mark subscription active
        // TODO: await db.subscriptions.update(...)
        // TODO: If business user, trigger tax invoice
        console.log(`[webhook] Payment DONE: ${paymentKey} / ${orderId}`);
      } else if (status === "CANCELED") {
        // Refund processed
        // TODO: await db.subscriptions.update({ status: "cancelled" })
        console.log(`[webhook] Payment CANCELED: ${paymentKey}`);
      } else if (status === "PARTIAL_CANCELED") {
        // Partial refund
        console.log(`[webhook] Partial cancel: ${paymentKey}`);
      }
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("[webhook] Parse error:", err);
    return NextResponse.json({ ok: false }, { status: 400 });
  }
}
