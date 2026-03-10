/**
 * Widget ↔ Platform PostMessage protocol.
 *
 * Security model:
 *  - iframe sandbox does NOT include allow-same-origin → origin is "null"
 *  - Validation uses message type + structure checks instead of origin
 *  - Each session generates a random nonce for handshake authentication
 *  - Only messages matching the WidgetMessage schema are accepted
 *
 * Supported message types:
 *  - "widget-ready"   : iframe JS finished initialisation
 *  - "widget-resize"  : iframe requests height change
 *  - "widget-error"   : iframe reports a non-fatal error
 */

// ── Message schema ───────────────────────────────────────────────

export type WidgetReadyMessage = {
  type: "widget-ready";
  nonce?: string;
};

export type WidgetResizeMessage = {
  type: "widget-resize";
  height: number;
};

export type WidgetErrorMessage = {
  type: "widget-error";
  code: string;
  detail?: string;
};

export type WidgetMessage =
  | WidgetReadyMessage
  | WidgetResizeMessage
  | WidgetErrorMessage;

// ── Nonce utility ────────────────────────────────────────────────

export function generateNonce(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

// ── Allowed origins ──────────────────────────────────────────────
// Because the iframe sandbox omits allow-same-origin, the incoming
// origin will be "null" (the string, not null).  We accept both the
// literal "null" and the configured engine origin for forward
// compatibility (e.g. if allow-same-origin is later added).

const ALLOWED_ORIGINS: ReadonlySet<string> = new Set([
  "null",
  process.env.NEXT_PUBLIC_CALCULATOR_MOUNT_BASE
    ? new URL(process.env.NEXT_PUBLIC_CALCULATOR_MOUNT_BASE).origin
    : "",
  process.env.NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN ?? "",
  process.env.NEXT_PUBLIC_PLATFORM_FRONT_HOST ?? "",
].filter(Boolean));

export function isAllowedOrigin(origin: string): boolean {
  return ALLOWED_ORIGINS.has(origin);
}

// ── Message validation ───────────────────────────────────────────

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export function parseWidgetMessage(
  event: MessageEvent,
): WidgetMessage | null {
  // Origin gate
  if (!isAllowedOrigin(event.origin)) return null;

  const data: unknown = event.data;
  if (!isObject(data)) return null;
  if (typeof data.type !== "string") return null;

  switch (data.type) {
    case "widget-ready":
      return {
        type: "widget-ready",
        ...(typeof data.nonce === "string" ? { nonce: data.nonce } : {}),
      };

    case "widget-resize": {
      const h = Number(data.height);
      if (!Number.isFinite(h) || h < 200 || h > 8000) return null;
      return { type: "widget-resize", height: h };
    }

    case "widget-error":
      if (typeof data.code !== "string") return null;
      return {
        type: "widget-error",
        code: data.code.slice(0, 64),
        ...(typeof data.detail === "string"
          ? { detail: data.detail.slice(0, 256) }
          : {}),
      };

    default:
      return null;
  }
}
