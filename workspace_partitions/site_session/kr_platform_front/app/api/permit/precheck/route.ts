import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/permit/precheck
 *
 * Proxies to the permit precheck API /v1/permit/precheck endpoint.
 * Runs a registration-criteria diagnosis and returns the result.
 */

const BACKEND_URL =
  process.env.PERMIT_ENGINE_ORIGIN || "http://127.0.0.1:8100";

const MAX_BODY = 8_192; // 8 KB

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
      return NextResponse.json(
        { ok: false, error: "upstream_error" },
        { status: upstream.status >= 500 ? 502 : upstream.status },
      );
    }
    const data = await upstream.json().catch(() => ({ ok: false }));
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { ok: false, error: "upstream_unavailable" },
      { status: 502 },
    );
  }
}
