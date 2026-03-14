/**
 * Subscription domain types.
 * These are used across billing API routes and UI components.
 */

export type SubscriptionStatus =
  | "trial"       // Free 1-month trial, no card on file
  | "active"      // Paying subscriber
  | "past_due"    // Charge failed, retrying
  | "cancelled"   // User cancelled, access until period end
  | "expired";    // Trial or subscription ended

export interface Subscription {
  /** Internal user ID (UUID). */
  userId: string;
  /** Toss customerKey (UUID, never an email/phone). */
  customerKey: string;
  /** Toss billingKey — null during trial. */
  billingKey: string | null;
  /** Current subscription status. */
  status: SubscriptionStatus;
  /** Plan name. */
  plan: "starter" | "pro" | "enterprise";
  /** Monthly amount in KRW. */
  amount: number;
  /** Trial end date (ISO 8601). */
  trialEndsAt: string | null;
  /** Current billing period end (ISO 8601). */
  currentPeriodEnd: string | null;
  /** Last successful payment key. */
  lastPaymentKey: string | null;
  /** Card last 4 digits (masked). */
  cardLast4: string | null;
  /** Card company code. */
  cardCompany: string | null;
  /** Business registration number (for tax invoice). */
  businessRegNumber: string | null;
  /** Created timestamp (ISO 8601). */
  createdAt: string;
  /** Updated timestamp (ISO 8601). */
  updatedAt: string;
}

/** Pro plan monthly price in KRW (VAT included). */
export const PRO_PLAN_AMOUNT = 99_000;

/** Trial duration in days. */
export const TRIAL_DAYS = 30;

/** Full refund window in days from payment. */
export const REFUND_WINDOW_DAYS = 7;

/** Generate a unique order ID for billing. */
export function generateOrderId(customerKey: string): string {
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const suffix = customerKey.slice(0, 6);
  const rand = Math.random().toString(36).slice(2, 6);
  return `seoulmna-${date}-${suffix}-${rand}`;
}

/** Calculate prorated refund amount. */
export function calculateProratedRefund(
  amount: number,
  periodStart: Date,
  cancelDate: Date,
  periodDays: number = 30,
): number {
  const usedDays = Math.ceil(
    (cancelDate.getTime() - periodStart.getTime()) / (1000 * 60 * 60 * 24),
  );
  if (usedDays <= 0) return amount;
  if (usedDays >= periodDays) return 0;
  const remaining = periodDays - usedDays;
  return Math.round((amount * remaining) / periodDays);
}
