import { NextResponse } from "next/server";
import { saveConsultInquiry, validateConsultInquiry } from "@/lib/consult-inquiries";
import { checkConsultRateLimit } from "@/lib/consult-rate-limit";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const responseHeaders = {
  "Cache-Control": "no-store, max-age=0",
  "X-Robots-Tag": "noindex, nofollow",
};

function jsonResponse(payload: Record<string, unknown>, init?: { status?: number; headers?: Record<string, string> }) {
  return NextResponse.json(payload, {
    status: init?.status,
    headers: {
      ...responseHeaders,
      ...(init?.headers ?? {}),
    },
  });
}

export async function POST(request: Request) {
  try {
    const input = (await request.json()) as Record<string, unknown>;
    const honeypot = typeof input.website === "string" ? input.website.trim() : "";
    const forwardedFor = request.headers.get("x-forwarded-for");
    const ipAddress = forwardedFor?.split(",")[0]?.trim() || request.headers.get("x-real-ip") || "unknown";
    const rateLimit = checkConsultRateLimit(`consult:${ipAddress}`);

    if (!rateLimit.ok) {
      const retryAfter = Math.max(1, Math.ceil((rateLimit.resetAt - Date.now()) / 1000));

      return jsonResponse(
        { ok: false, message: "짧은 시간에 문의가 너무 많습니다. 잠시 후 다시 시도해 주세요." },
        {
          status: 429,
          headers: {
            "Retry-After": String(retryAfter),
          },
        },
      );
    }

    if (honeypot) {
      return jsonResponse({
        ok: true,
        id: "filtered",
        submittedAt: new Date().toISOString(),
      });
    }

    const validated = validateConsultInquiry(input);

    if (!validated.ok) {
      return jsonResponse({ ok: false, message: validated.message }, { status: 400 });
    }

    const record = await saveConsultInquiry(validated.value);

    return jsonResponse({
      ok: true,
      id: record.id,
      submittedAt: record.submittedAt,
    });
  } catch {
    return jsonResponse(
      { ok: false, message: "문의 접수 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요." },
      { status: 500 },
    );
  }
}
