import { NextResponse } from "next/server";

/**
 * GET /api/permit/meta
 *
 * Proxies to the permit precheck API /v1/permit/meta endpoint.
 * Returns industry catalog metadata + industry list for the calculator.
 */

const BACKEND_URL =
  process.env.PERMIT_ENGINE_ORIGIN || "http://127.0.0.1:8100";

export async function GET() {
  try {
    const upstream = await fetch(`${BACKEND_URL}/v1/permit/meta`, {
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
