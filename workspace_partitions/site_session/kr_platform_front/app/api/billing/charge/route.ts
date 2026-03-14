import { NextRequest, NextResponse } from "next/server";
import { chargeBilling } from "@/lib/toss-billing";
import { PRO_PLAN_AMOUNT, generateOrderId } from "@/lib/subscription-types";

/**
 * POST /api/billing/charge
 * Charge a subscription using a stored billingKey.
 * Called by monthly cron job (Vercel Cron).
 *
 * Body: { billingKey, customerKey, customerEmail?, customerName? }
 */
export async function POST(req: NextRequest) {
  try {
    // Verify cron secret to prevent unauthorized charges
    const cronSecret = req.headers.get("x-cron-secret");
    if (cronSecret !== process.env.CRON_SECRET) {
      return NextResponse.json({ ok: false }, { status: 401 });
    }

    const body = await req.json();
    const { billingKey, customerKey, customerEmail, customerName } = body;

    if (!billingKey || !customerKey) {
      return NextResponse.json(
        { ok: false, error: "billingKey and customerKey are required" },
        { status: 400 },
      );
    }

    const orderId = generateOrderId(customerKey);

    const result = await chargeBilling({
      billingKey,
      customerKey,
      orderId,
      amount: PRO_PLAN_AMOUNT,
      orderName: "seoulmna.kr Pro 월간 구독",
      customerEmail,
      customerName,
    });

    // TODO: Update subscription in DB
    // await db.subscriptions.update({
    //   where: { customerKey },
    //   data: {
    //     lastPaymentKey: result.paymentKey,
    //     currentPeriodEnd: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    //     status: result.status === "DONE" ? "active" : "past_due",
    //   },
    // });

    // TODO: If business user, trigger tax invoice via Popbill/Barobill

    return NextResponse.json({ ok: true, paymentKey: result.paymentKey });
  } catch (err) {
    console.error("[billing/charge]", err);
    return NextResponse.json(
      { ok: false, error: "charge_failed" },
      { status: 500 },
    );
  }
}
