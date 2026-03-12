import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/consult-intake
 *
 * Proxies the contact-form submission to the backend yangdo_consult_api
 * /consult endpoint.  This keeps the backend origin private (not exposed
 * to the browser) and lets us apply rate-limiting or validation later.
 */

const BACKEND_URL =
  process.env.CONSULT_API_ORIGIN || "http://127.0.0.1:8788";

const MAX_BODY = 8_192; // 8 KB — generous for a contact form

export async function POST(req: NextRequest) {
  /* ── Size guard ───────────────────────────────────── */
  const contentLength = Number(req.headers.get("content-length") ?? 0);
  if (contentLength > MAX_BODY) {
    return NextResponse.json(
      { ok: false, error: "payload_too_large" },
      { status: 413 },
    );
  }

  /* ── Parse body ───────────────────────────────────── */
  let body: Record<string, unknown>;
  try {
    body = await req.json();
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
    const upstream = await fetch(`${BACKEND_URL}/consult`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10_000),
    });

    const data = await upstream.json().catch(() => ({ ok: false }));
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json(
      { ok: false, error: "upstream_unavailable" },
      { status: 502 },
    );
  }
}
