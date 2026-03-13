import { NextResponse } from "next/server";

/**
 * GET /api/yangdo/meta
 *
 * Proxies to the yangdo blackbox API /v1/meta endpoint.
 * Returns aggregate stats + license UI profiles for the native calculator.
 */

const BACKEND_URL =
  process.env.YANGDO_ENGINE_ORIGIN || "http://127.0.0.1:8200";
const API_KEY = process.env.YANGDO_BLACKBOX_API_KEY || "";

export async function GET() {
  try {
    const headers: Record<string, string> = {};
    if (API_KEY) headers["X-API-Key"] = API_KEY;

    const upstream = await fetch(`${BACKEND_URL}/v1/meta`, {
      method: "GET",
      headers,
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
