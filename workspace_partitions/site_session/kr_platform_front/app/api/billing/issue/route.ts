import { NextRequest, NextResponse } from "next/server";
import { issueBillingKey } from "@/lib/toss-billing";

/**
 * POST /api/billing/issue
 * Exchange Toss authKey for a billingKey after user completes card registration.
 * Called from /billing/success page.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { authKey, customerKey } = body;

    if (!authKey || !customerKey) {
      return NextResponse.json(
        { ok: false, error: "authKey and customerKey are required" },
        { status: 400 },
      );
    }

    const result = await issueBillingKey(authKey, customerKey);

    // TODO: Store billingKey in database
    // await db.subscriptions.update({
    //   where: { customerKey },
    //   data: {
    //     billingKey: result.billingKey,
    //     cardLast4: result.cardNumber.slice(-4),
    //     cardCompany: result.cardCompany,
    //     status: "active",
    //     currentPeriodEnd: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    //   },
    // });

    return NextResponse.json({
      ok: true,
      cardLast4: result.cardNumber.slice(-4),
      cardCompany: result.cardCompany,
    });
  } catch (err) {
    console.error("[billing/issue]", err);
    return NextResponse.json(
      { ok: false, error: "billing_issue_failed" },
      { status: 500 },
    );
  }
}
