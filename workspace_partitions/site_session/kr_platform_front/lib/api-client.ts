/** Shared API client — typed fetch wrapper with error handling. */

const DEFAULT_TIMEOUT_MS = 15_000;

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message?: string,
  ) {
    super(message ?? `API error ${status}: ${code}`);
    this.name = "ApiError";
  }
}

interface FetchOptions {
  timeout?: number;
  signal?: AbortSignal;
}

async function apiFetch<T>(url: string, init?: RequestInit & FetchOptions): Promise<T> {
  const { timeout = DEFAULT_TIMEOUT_MS, signal: externalSignal, ...fetchInit } = init ?? {};

  const timeoutSignal = AbortSignal.timeout(timeout);
  const signal = externalSignal
    ? AbortSignal.any([timeoutSignal, externalSignal])
    : timeoutSignal;

  try {
    const res = await fetch(url, {
      ...fetchInit,
      signal,
    });

    if (!res.ok) {
      let code = "unknown_error";
      try {
        const body = await res.json();
        code = body?.error ?? code;
      } catch {
        // body not JSON
      }
      throw new ApiError(res.status, code);
    }

    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "timeout", "요청 시간이 초과되었습니다.");
    }
    throw new ApiError(0, "network_error", "네트워크 연결을 확인해 주세요.");
  }
}

// ── Yangdo API ───────────────────────────────────────

import type { YangdoMetaResponse, YangdoEstimateRequest, YangdoEstimateResponse } from "./yangdo-types";
import type { PermitMetaResponse, PermitPrecheckRequest, PermitPrecheckResponse } from "./permit-types";

export async function fetchYangdoMeta(options?: FetchOptions): Promise<YangdoMetaResponse> {
  return apiFetch<YangdoMetaResponse>("/api/yangdo/meta", { method: "GET", ...options });
}

export async function fetchYangdoEstimate(
  body: YangdoEstimateRequest,
  options?: FetchOptions,
): Promise<YangdoEstimateResponse> {
  return apiFetch<YangdoEstimateResponse>("/api/yangdo/estimate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    timeout: 20_000,
    ...options,
  });
}

// ── Permit API ───────────────────────────────────────

export async function fetchPermitMeta(options?: FetchOptions): Promise<PermitMetaResponse> {
  return apiFetch<PermitMetaResponse>("/api/permit/meta", { method: "GET", ...options });
}

export async function fetchPermitPrecheck(
  body: PermitPrecheckRequest,
  options?: FetchOptions,
): Promise<PermitPrecheckResponse> {
  return apiFetch<PermitPrecheckResponse>("/api/permit/precheck", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    ...options,
  });
}
