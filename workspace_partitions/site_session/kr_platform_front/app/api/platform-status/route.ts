import { NextResponse } from "next/server";
import { platformConfig } from "@/components/platform-config";

const BOOT_TIME = new Date().toISOString();

export function GET() {
  return NextResponse.json({
    ok: true,
    version: "0.37.0",
    bootedAt: BOOT_TIME,
    frontHost: platformConfig.platformFrontHost,
    contentHost: platformConfig.contentHost,
    listingHost: platformConfig.listingHost,
    engineOrigin: platformConfig.privateEngineOrigin,
    engineMode: "private",
    tenantId: platformConfig.tenantId,
    systems: [
      { id: "yangdo", label: "AI 양도가 산정", ready: true },
      { id: "permit", label: "AI 인허가 사전검토", ready: true },
    ],
    features: {
      postMessageHandshake: true,
      dynamicIframeResize: true,
      sandboxMode: true,
    },
  });
}
