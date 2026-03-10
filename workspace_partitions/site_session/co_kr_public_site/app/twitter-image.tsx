import { ImageResponse } from "next/og";
import { siteConfig } from "@/components/site-config";

export const alt = `${siteConfig.brandName} — ${siteConfig.brandTagline}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function TwitterImage() {
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
          padding: "60px 80px",
          background:
            "linear-gradient(140deg, rgb(3, 23, 44) 0%, rgb(8, 53, 95) 55%, rgb(13, 71, 123) 100%)",
          color: "white",
          fontFamily: "sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            width: "72px",
            height: "72px",
            borderRadius: "18px",
            background: "rgba(255,255,255,0.12)",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 28,
            fontWeight: 800,
            marginBottom: "24px",
          }}
        >
          CB
        </div>

        <div
          style={{
            display: "flex",
            fontSize: 48,
            fontWeight: 800,
            lineHeight: 1.2,
            textAlign: "center",
          }}
        >
          {siteConfig.brandName}
        </div>

        <div
          style={{
            display: "flex",
            marginTop: "14px",
            fontSize: 24,
            color: "rgba(255,255,255,0.7)",
            textAlign: "center",
          }}
        >
          {siteConfig.brandTagline}
        </div>
      </div>
    ),
    { ...size },
  );
}
