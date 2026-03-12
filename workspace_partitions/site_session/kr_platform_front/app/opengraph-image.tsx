import { ImageResponse } from "next/og";
import { loadOgFont, ogFontFamily, ogFontOption } from "@/lib/og-font";

export const alt = "서울건설정보 — 건설업 AI 전문 플랫폼";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OgImage() {
  const fontData = await loadOgFont();

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          background: "linear-gradient(145deg, #021225 0%, #05325f 55%, #0a4d8c 100%)",
          fontFamily: ogFontFamily(fontData),
          padding: "60px 80px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Decorative gradient orbs */}
        <div
          style={{
            position: "absolute",
            top: "-80px",
            right: "-80px",
            width: "400px",
            height: "400px",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(0,163,255,0.25) 0%, transparent 70%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: "-120px",
            left: "-60px",
            width: "360px",
            height: "360px",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(0,196,140,0.18) 0%, transparent 70%)",
          }}
        />

        {/* Brand mark — two-building icon */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "center",
            gap: "4px",
            width: "72px",
            height: "72px",
            borderRadius: "18px",
            background: "#003764",
            border: "2px solid rgba(255,255,255,0.15)",
            marginBottom: "28px",
            padding: "10px 12px",
          }}
        >
          <div style={{ width: "18px", height: "32px", background: "#E8222E", borderRadius: "3px", display: "flex" }} />
          <div style={{ width: "24px", height: "44px", background: "white", borderRadius: "3px", display: "flex" }} />
        </div>

        {/* Title */}
        <h1
          style={{
            fontSize: "56px",
            fontWeight: 700,
            color: "white",
            margin: 0,
            lineHeight: 1.2,
            textAlign: "center",
            letterSpacing: "-0.02em",
          }}
        >
          서울건설정보
        </h1>

        {/* Tagline */}
        <p
          style={{
            fontSize: "26px",
            fontWeight: 700,
            color: "rgba(255,255,255,0.7)",
            margin: "14px 0 0",
            textAlign: "center",
          }}
        >
          건설업 AI 전문 플랫폼
        </p>

        {/* Features row */}
        <div
          style={{
            display: "flex",
            gap: "32px",
            marginTop: "42px",
          }}
        >
          {["AI 양도가 산정", "AI 인허가 검토", "전문 행정사 상담"].map(
            (feature) => (
              <div
                key={feature}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "12px 22px",
                  borderRadius: "999px",
                  background: "rgba(255,255,255,0.08)",
                  border: "1px solid rgba(255,255,255,0.12)",
                }}
              >
                <div
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: "#00A3FF",
                  }}
                />
                <span style={{ color: "rgba(255,255,255,0.85)", fontSize: "18px", fontWeight: 700 }}>
                  {feature}
                </span>
              </div>
            ),
          )}
        </div>

        {/* Bottom URL hint */}
        <p
          style={{
            position: "absolute",
            bottom: "32px",
            right: "48px",
            fontSize: "16px",
            color: "rgba(255,255,255,0.35)",
            fontWeight: 700,
          }}
        >
          seoulmna.kr
        </p>
      </div>
    ),
    {
      ...size,
      ...ogFontOption(fontData),
    },
  );
}
