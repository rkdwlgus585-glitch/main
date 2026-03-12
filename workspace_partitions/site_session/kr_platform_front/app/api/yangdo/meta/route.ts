import { NextResponse } from "next/server";

/**
 * GET /api/yangdo/meta
 *
 * Proxies to the yangdo blackbox API /v1/meta endpoint.
 * Returns aggregate stats + license UI profiles for the native calculator.
 */

const BACKEND_URL =
  process.env.YANGDO_ENGINE_ORIGIN || "http://127.0.0.1:8200";

export async function GET() {
  try {
    const upstream = await fetch(`${BACKEND_URL}/v1/meta`, {
      method: "GET",
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
