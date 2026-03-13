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

    if (!upstream.ok) {
      return NextResponse.json(
        { ok: false, error: "upstream_error" },
        { status: upstream.status >= 500 ? 502 : upstream.status },
      );
    }
    const raw = await upstream.json().catch(() => ({ ok: false }));
    const d = (typeof raw === "object" && raw !== null) ? raw : {};
    // Strip server envelope — keep only what the frontend needs
    return NextResponse.json({
      ok: (d as Record<string, unknown>).ok ?? false,
      meta: (d as Record<string, unknown>).meta,
      industries: (d as Record<string, unknown>).industries ?? [],
      major_categories: (d as Record<string, unknown>).major_categories ?? [],
    });
  } catch {
    return NextResponse.json(
      { ok: false, error: "upstream_unavailable" },
      { status: 502 },
    );
  }
}
