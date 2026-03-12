import { ImageResponse } from "next/og";
import { type NextRequest, NextResponse } from "next/server";

/**
 * GET /api/pwa-icon/:size
 *
 * Dynamically generates PNG icons for the PWA manifest.
 * Reproduces the brand logo design (navy+red two-building icon)
 * at any allowed pixel size. Cached aggressively on the CDN.
 */

const ALLOWED_SIZES = new Set([192, 512]);

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ size: string }> },
) {
  const { size: sizeParam } = await params;
  const size = parseInt(sizeParam, 10);

  if (!ALLOWED_SIZES.has(size)) {
    return NextResponse.json(
      { error: "size must be 192 or 512" },
      { status: 400 },
    );
  }

  const radius = Math.round(size * (6 / 32));
  const s = (v: number) => Math.round(size * (v / 32));

  return new ImageResponse(
    (
      <div
        style={{
          width: size,
          height: size,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#003764",
          borderRadius: radius,
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Left building (red) */}
        <div style={{ position: "absolute", left: s(3), top: s(12), width: s(10), height: s(17), background: "#E8222E", borderRadius: s(1), display: "flex" }} />
        {/* Right building (dark navy) */}
        <div style={{ position: "absolute", left: s(14), top: s(4), width: s(7), height: s(25), background: "#002244", borderRadius: s(1), display: "flex" }} />
        {/* Right building right half (red tint) */}
        <div style={{ position: "absolute", left: s(21), top: s(4), width: s(7), height: s(25), background: "#C41E24", borderRadius: s(0.5), display: "flex", opacity: 0.7 }} />
        {/* Windows - left building chevrons (simplified as bars) */}
        <div style={{ position: "absolute", left: s(4.5), top: s(15), width: s(7), height: s(1), background: "rgba(255,255,255,0.5)", display: "flex" }} />
        <div style={{ position: "absolute", left: s(4.5), top: s(18), width: s(7), height: s(1), background: "rgba(255,255,255,0.5)", display: "flex" }} />
        <div style={{ position: "absolute", left: s(4.5), top: s(21), width: s(7), height: s(1), background: "rgba(255,255,255,0.5)", display: "flex" }} />
        <div style={{ position: "absolute", left: s(4.5), top: s(24), width: s(7), height: s(1), background: "rgba(255,255,255,0.5)", display: "flex" }} />
        {/* Windows - right building */}
        <div style={{ position: "absolute", left: s(16), top: s(7), width: s(2.5), height: s(2.5), background: "rgba(255,255,255,0.45)", borderRadius: s(0.3), display: "flex" }} />
        <div style={{ position: "absolute", left: s(16), top: s(11), width: s(2.5), height: s(2.5), background: "rgba(255,255,255,0.45)", borderRadius: s(0.3), display: "flex" }} />
        <div style={{ position: "absolute", left: s(16), top: s(15), width: s(2.5), height: s(2.5), background: "rgba(255,255,255,0.45)", borderRadius: s(0.3), display: "flex" }} />
        <div style={{ position: "absolute", left: s(22), top: s(7), width: s(2.5), height: s(2.5), background: "rgba(255,255,255,0.3)", borderRadius: s(0.3), display: "flex" }} />
        <div style={{ position: "absolute", left: s(22), top: s(11), width: s(2.5), height: s(2.5), background: "rgba(255,255,255,0.3)", borderRadius: s(0.3), display: "flex" }} />
        <div style={{ position: "absolute", left: s(22), top: s(15), width: s(2.5), height: s(2.5), background: "rgba(255,255,255,0.3)", borderRadius: s(0.3), display: "flex" }} />
      </div>
    ),
    {
      width: size,
      height: size,
      headers: {
        "Cache-Control": "public, max-age=604800, s-maxage=2592000, immutable",
      },
    },
  );
}
