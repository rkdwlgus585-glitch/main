import { ImageResponse } from "next/og";
import { loadOgFont, ogFontFamily, ogFontOption } from "@/lib/og-font";

export const alt = "서울건설정보 — 건설업 AI 전문 플랫폼";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function TwitterImage() {
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
        {/* Decorative gradient orb */}
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

        {/* Brand mark — two-building icon */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "center",
            gap: "3px",
            width: "64px",
            height: "64px",
            borderRadius: "16px",
            background: "#003764",
            border: "2px solid rgba(255,255,255,0.15)",
            marginBottom: "24px",
            padding: "8px 10px",
          }}
        >
          <div style={{ width: "16px", height: "28px", background: "#E8222E", borderRadius: "3px", display: "flex" }} />
          <div style={{ width: "22px", height: "40px", background: "white", borderRadius: "3px", display: "flex" }} />
        </div>

        {/* Title */}
        <h1
          style={{
            fontSize: "48px",
            fontWeight: 700,
            color: "white",
            margin: 0,
            lineHeight: 1.2,
            textAlign: "center",
          }}
        >
          서울건설정보
        </h1>

        {/* Tagline */}
        <p
          style={{
            fontSize: "22px",
            fontWeight: 700,
            color: "rgba(255,255,255,0.65)",
            margin: "12px 0 0",
            textAlign: "center",
          }}
        >
          건설업 면허 양도가 산정 · 건설업등록 검토 · 전문 상담
        </p>
      </div>
    ),
    {
      ...size,
      ...ogFontOption(fontData),
    },
  );
}
