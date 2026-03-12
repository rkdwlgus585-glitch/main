// ── Yangdo Meta API ──────────────────────────────────
export interface YangdoMetaResponse {
  ok: boolean;
  meta: YangdoMeta;
  license_profiles: LicenseProfileBundle;
}

export interface YangdoMeta {
  generated_at: string;
  all_record_count: number;
  train_count: number;
  priced_ratio: number;
  median_price_eok: number | null;
  p25_price_eok: number | null;
  p75_price_eok: number | null;
  avg_debt_ratio: number | null;
  avg_liq_ratio: number | null;
  avg_capital_eok: number | null;
  p90_capital_eok: number | null;
  avg_surplus_eok: number | null;
  p90_surplus_eok: number | null;
  avg_balance_eok: number | null;
  p90_balance_eok: number | null;
  median_specialty: number | null;
  p90_specialty: number | null;
  median_sales3_eok: number | null;
  p90_sales3_eok: number | null;
  top_license_tokens: TopLicenseToken[];
}

export interface TopLicenseToken {
  token: string;
  count: number;
}

export interface LicenseProfileBundle {
  profiles: Record<string, LicenseProfile>;
  quick_tokens: QuickToken[];
}

export interface LicenseProfile {
  token: string;
  display_name: string;
  sample_count: number;
  prefill_capital_eok: number;
  prefill_surplus_eok: number;
  default_balance_eok: number;
  median_balance_eok: number | null;
  typical_specialty_eok: number | null;
  typical_sales3_eok: number | null;
  typical_sales5_eok: number | null;
}

export interface QuickToken {
  token: string;
  display_name: string;
  sample_count: number;
}

// ── Yangdo Estimate API ──────────────────────────────
export interface YangdoEstimateRequest {
  license_text: string;
  scale_mode?: "specialty" | "sales";
  specialty?: number;
  sales3_eok?: number;
  sales5_eok?: number;
  balance_eok?: number;
  capital_eok?: number;
  surplus_eok?: number;
  debt_ratio?: number;
  liq_ratio?: number;
  reorg_mode?: string;
  credit_level?: string;
  admin_history?: string;
  balance_usage_mode?: string;
  seller_withdraws_guarantee_loan?: boolean;
  buyer_takes_balance_as_credit?: boolean;
}

export interface YangdoEstimateResponse {
  ok: boolean;
  error?: string;
  // Core estimate
  estimate_center_eok?: number;
  estimate_low_eok?: number;
  estimate_high_eok?: number;
  confidence_percent?: number;
  publication_mode?: string;
  // Public (display-safe) values
  public_center_eok?: number;
  public_low_eok?: number;
  public_high_eok?: number;
  // Settlement scenarios (전기/정보통신/소방)
  settlement_scenarios?: SettlementScenario[];
  requires_reorg_mode?: boolean;
  // Recommended listings
  recommended_listings?: RecommendedListing[];
  // Risk notes
  risk_notes?: string[];
  // Target echo
  target?: Record<string, unknown>;
}

export interface SettlementScenario {
  mode: string;
  label: string;
  balance_eok: number;
  cash_due_low_eok: number;
  cash_due_high_eok: number;
  center_eok?: number;
  summary?: string;
}

export interface RecommendedListing {
  license_text?: string;
  score?: number;
  label?: string;
  reason?: string;
  price_eok?: number;
  [key: string]: unknown;
}
