const WINDOW_MS = 5 * 60 * 1000;
const MAX_REQUESTS = 5;

type RateLimitEntry = {
  count: number;
  resetAt: number;
};

const requestStore = new Map<string, RateLimitEntry>();

function cleanupExpiredEntries(now: number) {
  for (const [key, entry] of requestStore.entries()) {
    if (entry.resetAt <= now) {
      requestStore.delete(key);
    }
  }
}

// Best-effort limiter for a single server instance. Replace with a shared store for multi-instance deployments.
export function checkConsultRateLimit(key: string) {
  const now = Date.now();
  cleanupExpiredEntries(now);

  const entry = requestStore.get(key);

  if (!entry || entry.resetAt <= now) {
    const resetAt = now + WINDOW_MS;
    requestStore.set(key, { count: 1, resetAt });
    return { ok: true as const, remaining: MAX_REQUESTS - 1, resetAt };
  }

  if (entry.count >= MAX_REQUESTS) {
    return { ok: false as const, remaining: 0, resetAt: entry.resetAt };
  }

  entry.count += 1;
  requestStore.set(key, entry);

  return { ok: true as const, remaining: MAX_REQUESTS - entry.count, resetAt: entry.resetAt };
}
