import { ImageResponse } from "next/og";
import { siteConfig } from "@/components/site-config";

export const alt = `${siteConfig.brandName} — ${siteConfig.brandTagline}`;
export const size = {
  width: 1200,
  height: 630,
};

export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "56px",
          background:
            "linear-gradient(140deg, rgb(3, 23, 44) 0%, rgb(8, 53, 95) 55%, rgb(13, 71, 123) 100%)",
          color: "white",
          fontFamily: "sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            width: "96px",
            height: "96px",
            borderRadius: "24px",
            background: "rgba(255,255,255,0.12)",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 34,
            fontWeight: 800,
          }}
        >
          CB
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
          <div style={{ display: "flex", fontSize: 28, color: "rgb(153, 220, 255)" }}>{siteConfig.brandName}</div>
          <div style={{ display: "flex", flexDirection: "column", fontSize: 68, lineHeight: 1.08, fontWeight: 800 }}>
            <span>{siteConfig.brandTagline}</span>
            <span>독립 퍼블릭 운영 사이트</span>
          </div>
          <div style={{ display: "flex", fontSize: 30, color: "rgba(255,255,255,0.78)" }}>
            {siteConfig.companyName} · 상담 중심 운영과 AI 시스템을 분리한 공개용 구조
          </div>
        </div>
      </div>
    ),
    {
      ...size,
    },
  );
}
