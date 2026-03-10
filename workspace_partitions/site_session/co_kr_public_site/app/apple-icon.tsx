import { ImageResponse } from "next/og";

export const size = {
  width: 180,
  height: 180,
};

export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "36px",
          background: "linear-gradient(145deg, #07355f 0%, #0b4f87 62%, #1794ff 100%)",
          color: "#ffffff",
          fontSize: 82,
          fontWeight: 800,
          fontFamily: "sans-serif",
          letterSpacing: "-0.06em",
        }}
      >
        CB
      </div>
    ),
    size,
  );
}
