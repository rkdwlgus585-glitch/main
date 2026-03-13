import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/yangdo/estimate
 *
 * Proxies to the yangdo blackbox API /v1/yangdo/estimate endpoint.
 * Runs a full price estimation and returns the result.
 * Requires X-API-Key for the backend (server-side secret).
 */

const BACKEND_URL =
  process.env.YANGDO_ENGINE_ORIGIN || "http://127.0.0.1:8200";
const API_KEY = process.env.YANGDO_BLACKBOX_API_KEY || "";

const MAX_BODY = 16_384; // 16 KB

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
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (API_KEY) headers["X-API-Key"] = API_KEY;

    const upstream = await fetch(`${BACKEND_URL}/v1/yangdo/estimate`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(15_000),
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
    const raw_data = await upstream.json().catch(() => ({ ok: false }));
    const d = (typeof raw_data === "object" && raw_data !== null) ? raw_data : {};

    // Strip server-internal fields — only forward what the frontend needs.
    const {
      tenant_id: _t, neighbors: _n, target: _tgt,
      response_policy: _rp, response_meta: _rm,
      service: _s, api_version: _av, channel_id: _c, request_id: _r,
      data: _nested, // drop nested duplicate
      ...safeFields
    } = d as Record<string, unknown>;

    return NextResponse.json(safeFields);
  } catch {
    return NextResponse.json(
      { ok: false, error: "upstream_unavailable" },
      { status: 502 },
    );
  }
}
