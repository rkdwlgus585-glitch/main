// ── Permit Meta API ──────────────────────────────────
export interface PermitMetaResponse {
  ok: boolean;
  meta: PermitMeta;
  industries: PermitIndustry[];
  major_categories: MajorCategory[];
}

export interface PermitMeta {
  industry_total: number;
  with_registration_rule_total: number;
  coverage_pct: number;
  pending_rule_total: number;
  rule_catalog_version: string;
  rule_catalog_effective_date: string;
  public_claim_level: string;
  public_claim_message: string;
}

export interface PermitIndustry {
  service_code: string;
  service_name: string;
  major_code: string;
  major_name: string;
  has_rule: boolean;
}

export interface MajorCategory {
  major_code: string;
  major_name: string;
  industry_count: number;
}

// ── Permit Precheck API ──────────────────────────────
export interface PermitPrecheckRequest {
  service_code: string;
  service_name?: string;
  inputs: PermitInputs;
}

export interface PermitInputs {
  capital_eok?: number;
  technicians?: number;
  equipment?: number;
  office?: boolean;
  facility?: boolean;
  qualification?: boolean;
  insurance?: boolean;
  deposit_eok?: number;
  [key: string]: unknown;
}

export interface PermitPrecheckResponse {
  ok: boolean;
  error?: string;
  overall_status?: "pass" | "shortfall" | "manual_review";
  service_code?: string;
  service_name?: string;
  shortfall_items?: ShortfallItem[];
  criteria_results?: CriterionResult[];
  next_actions?: NextAction[];
  total_shortfall_cost_eok?: number;
}

export interface ShortfallItem {
  field: string;
  label: string;
  required: number | string;
  current: number | string;
  gap?: number | string;
  estimated_cost_eok?: number;
}

export interface CriterionResult {
  field: string;
  label: string;
  status: "pass" | "fail" | "unknown";
  required?: number | string | boolean;
  current?: number | string | boolean;
  note?: string;
}

export interface NextAction {
  priority: number;
  action: string;
  detail?: string;
  estimated_cost_eok?: number;
}
