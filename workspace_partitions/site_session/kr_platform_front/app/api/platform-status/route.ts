import { NextResponse } from "next/server";
import { platformConfig } from "@/components/platform-config";

export function GET() {
  return NextResponse.json({
    ok: true,
    frontHost: platformConfig.platformFrontHost,
    contentHost: platformConfig.contentHost,
    widgetConsumerHost: platformConfig.widgetConsumerHost,
    engineMode: "private",
    tenantId: platformConfig.tenantId,
    systems: ["yangdo", "permit"],
  });
}
