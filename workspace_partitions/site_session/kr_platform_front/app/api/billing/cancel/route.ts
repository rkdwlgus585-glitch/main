import { NextRequest, NextResponse } from "next/server";
import { cancelPayment } from "@/lib/toss-billing";
import { REFUND_WINDOW_DAYS } from "@/lib/subscription-types";

/**
 * POST /api/billing/cancel
 * Cancel a subscription and process refund (full or prorated).
 *
 * Body: { paymentKey, cancelReason, periodStartIso? }
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { paymentKey, cancelReason, periodStartIso } = body;

    if (!paymentKey || !cancelReason) {
      return NextResponse.json(
        { ok: false, error: "paymentKey and cancelReason are required" },
        { status: 400 },
      );
    }

    // Determine refund amount
    let cancelAmount: number | undefined;

    if (periodStartIso) {
      const periodStart = new Date(periodStartIso);
      const now = new Date();
      const daysSincePayment = Math.ceil(
        (now.getTime() - periodStart.getTime()) / (1000 * 60 * 60 * 24),
      );

      if (daysSincePayment <= REFUND_WINDOW_DAYS) {
        // Full refund within 7 days if unused
        // TODO: Check usage records — if used, apply prorated
        cancelAmount = undefined; // Full refund
      } else {
        // No refund after 7 days
        // But user can still cancel — access continues until period end
        // TODO: Update DB to status="cancelled", don't charge next month
        return NextResponse.json({
          ok: true,
          action: "cancel_at_period_end",
          message: "구독이 현재 결제 기간 종료 후 해지됩니다.",
        });
      }
    }

    const result = await cancelPayment({
      paymentKey,
      cancelReason,
      cancelAmount,
    });

    // TODO: Update subscription in DB
    // await db.subscriptions.update({
    //   where: { lastPaymentKey: paymentKey },
    //   data: { status: "cancelled" },
    // });

    return NextResponse.json({ ok: true, status: result.status });
  } catch (err) {
    console.error("[billing/cancel]", err instanceof Error ? err.message : "unknown");
    return NextResponse.json(
      { ok: false, error: "cancel_failed" },
      { status: 500 },
    );
  }
}
