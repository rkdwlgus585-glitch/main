import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/yangdo/estimate
 *
 * Proxies to the yangdo blackbox API /v1/estimate endpoint.
 * Runs a full price estimation and returns the result.
 */

const BACKEND_URL =
  process.env.YANGDO_ENGINE_ORIGIN || "http://127.0.0.1:8200";

const MAX_BODY = 16_384; // 16 KB

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
    const upstream = await fetch(`${BACKEND_URL}/v1/estimate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(15_000),
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
