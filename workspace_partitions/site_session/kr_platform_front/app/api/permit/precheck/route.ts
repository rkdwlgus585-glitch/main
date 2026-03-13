import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/permit/precheck
 *
 * Proxies to the permit precheck API /v1/permit/precheck endpoint.
 * Transforms the backend response envelope into the frontend-expected shape.
 */

const BACKEND_URL =
  process.env.PERMIT_ENGINE_ORIGIN || "http://127.0.0.1:8100";

const MAX_BODY = 8_192; // 8 KB

/** Field label map for Korean display in shortfall cards. */
const FIELD_LABELS: Record<string, string> = {
  capital: "자본금",
  technicians: "기술인력",
  equipment: "장비",
  office: "사무실",
  facility: "시설",
  qualification: "자격증",
  insurance: "보험",
  deposit: "보증금",
};

/** Map criterion status from backend to frontend's pass/fail/unknown. */
function mapCriterionStatus(raw: string): "pass" | "fail" | "unknown" {
  if (raw === "ok" || raw === "pass") return "pass";
  if (raw === "fail" || raw === "shortfall") return "fail";
  return "unknown"; // missing_input, etc.
}

/**
 * Transform backend response → frontend PermitPrecheckResponse shape.
 *
 * Backend fields:
 *   criterion_results → criteria_results (renamed + mapped)
 *   required_summary  → shortfall_items (dict→array)
 *   next_actions      → next_actions (string[]→NextAction[])
 *   industry_name     → service_name
 */
function transformResponse(raw: Record<string, unknown>): Record<string, unknown> {
  const d = (typeof raw.data === "object" && raw.data !== null)
    ? raw.data as Record<string, unknown>
    : raw;

  // 1. Map criterion_results → criteria_results
  const rawCriteria = Array.isArray(d.criterion_results) ? d.criterion_results : [];
  const criteriaResults = rawCriteria.map((c: Record<string, unknown>) => ({
    field: c.criterion_id ?? c.input_key ?? "",
    label: c.label ?? "",
    status: mapCriterionStatus(String(c.status ?? "unknown")),
    required: c.required_value ?? undefined,
    current: c.current_value ?? undefined,
    note: c.blocking ? "등록 필수 (blocking)" : undefined,
  }));

  // 2. Convert required_summary dict → shortfall_items array
  const summary = (typeof d.required_summary === "object" && d.required_summary !== null)
    ? d.required_summary as Record<string, unknown>
    : {};
  const shortfallItems: Record<string, unknown>[] = [];
  for (const [key, val] of Object.entries(summary)) {
    if (typeof val !== "object" || val === null) continue;
    const item = val as Record<string, unknown>;
    if (item.ok === true) continue; // skip passing items
    shortfallItems.push({
      field: key,
      label: FIELD_LABELS[key] ?? key,
      required: item.required,
      current: item.current,
      gap: item.gap,
    });
  }

  // 3. Map next_actions (backend sends string[])
  const rawActions = Array.isArray(d.next_actions) ? d.next_actions : [];
  const nextActions = rawActions.map((act: unknown, i: number) => ({
    priority: i + 1,
    action: typeof act === "string" ? act : String(act),
  }));

  // 4. Compute total shortfall cost (from gap values in shortfall items)
  const totalCost = shortfallItems.reduce((sum, item) => {
    const gap = typeof item.gap === "number" ? Math.abs(item.gap) : 0;
    return sum + gap;
  }, 0);

  return {
    ok: d.ok ?? false,
    overall_status: d.typed_overall_status ?? d.overall_status ?? undefined,
    service_code: d.service_code ?? undefined,
    service_name: d.industry_name ?? d.service_name ?? undefined,
    criteria_results: criteriaResults,
    shortfall_items: shortfallItems,
    next_actions: nextActions,
    total_shortfall_cost_eok: totalCost > 0 ? totalCost : undefined,
  };
}

export async function POST(req: NextRequest) {
  /* ── Parse + size guard (body-based, not header-based) ── */
  let raw: string;
  try {
    raw = await req.text();
  } catch {
    return NextResponse.json(
      { ok: false, error: "invalid_body" },
      { status: 400 },
    );
  }
  if (raw.length > MAX_BODY) {
    return NextResponse.json(
      { ok: false, error: "payload_too_large" },
      { status: 413 },
    );
  }

  let body: Record<string, unknown>;
  try {
    body = JSON.parse(raw);
  } catch {
    return NextResponse.json(
      { ok: false, error: "invalid_json" },
      { status: 400 },
    );
  }

  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return NextResponse.json(
      { ok: false, error: "invalid_payload" },
      { status: 400 },
    );
  }

  /* ── Forward to backend ───────────────────────────── */
  try {
    const upstream = await fetch(`${BACKEND_URL}/v1/permit/precheck`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10_000),
    });

    if (!upstream.ok) {
      const errBody = await upstream.json().catch(() => ({}));
      const errMsg = typeof errBody === "object" && errBody !== null
        ? (errBody as Record<string, unknown>).error ?? "upstream_error"
        : "upstream_error";
      return NextResponse.json(
        { ok: false, error: errMsg },
        { status: upstream.status >= 500 ? 502 : upstream.status },
      );
    }
    const data = await upstream.json().catch(() => ({ ok: false }));
    const transformed = transformResponse(data as Record<string, unknown>);
    return NextResponse.json(transformed);
  } catch {
    return NextResponse.json(
      { ok: false, error: "upstream_unavailable" },
      { status: 502 },
    );
  }
}
