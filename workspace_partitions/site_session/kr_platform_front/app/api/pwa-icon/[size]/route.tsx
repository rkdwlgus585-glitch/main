import { ImageResponse } from "next/og";
import { type NextRequest, NextResponse } from "next/server";

/**
 * GET /api/pwa-icon/:size
 *
 * Dynamically generates PNG icons for the PWA manifest.
 * Reproduces the icon.svg design (navy rounded-rect + "SM" text)
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

  /* Proportions matching icon.svg (32×32 base) */
  const radius = Math.round(size * (6 / 32));
  const fontSize = Math.round(size * (15 / 32));

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
          color: "white",
          fontSize,
          fontWeight: 900,
          fontFamily: "system-ui, -apple-system, sans-serif",
        }}
      >
        SM
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
