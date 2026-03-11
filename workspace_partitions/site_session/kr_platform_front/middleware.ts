import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Edge Middleware — runs on every matched request at Vercel Edge.
 *
 * Responsibilities:
 * 1. X-Robots-Tag on /api/ and /widget/ paths (defense-in-depth with robots.txt)
 * 2. X-Request-Id on all responses for debugging/correlation
 * 3. Cache-Control: no-store on API responses (prevent CDN caching of dynamic data)
 */
export function middleware(request: NextRequest) {
  const response = NextResponse.next();
  const { pathname } = request.nextUrl;

  /* ── X-Request-Id for debugging ── */
  const requestId =
    request.headers.get("x-request-id") ?? crypto.randomUUID().replace(/-/g, "");
  response.headers.set("X-Request-Id", requestId);

  /* ── API / Widget paths: no indexing + no caching ── */
  if (pathname.startsWith("/api/") || pathname.startsWith("/widget/")) {
    response.headers.set("X-Robots-Tag", "noindex, nofollow");
  }

  if (pathname.startsWith("/api/") && !pathname.startsWith("/api/pwa-icon/")) {
    response.headers.set("Cache-Control", "no-store");
  }

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all paths EXCEPT:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - icon.svg, apple-icon.svg (favicons)
     * - media/ (static assets — cached by vercel.json)
     */
    "/((?!_next/static|_next/image|icon\\.svg|apple-icon\\.svg|media/).*)",
  ],
};
