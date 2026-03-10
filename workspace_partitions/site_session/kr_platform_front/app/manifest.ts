import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "서울건설정보 | 건설업 AI 전문 플랫폼",
    short_name: "서울건설정보",
    description:
      "건설업 면허 양도가 산정부터 건설업등록 검토까지, 데이터 기반 AI 분석을 무료로 제공합니다.",
    start_url: "/",
    display: "standalone",
    background_color: "#F8FAFB",
    theme_color: "#003764",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
    ],
  };
}
