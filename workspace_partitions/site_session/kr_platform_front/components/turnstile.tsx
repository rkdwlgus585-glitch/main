"use client";

import { useEffect, useRef, useCallback } from "react";

/** Cloudflare Turnstile global API type declaration. */
interface TurnstileApi {
  render: (container: HTMLElement, options: Record<string, unknown>) => string;
  remove: (widgetId: string) => void;
}

declare global {
  interface Window {
    turnstile?: TurnstileApi;
  }
}

/**
 * Cloudflare Turnstile CAPTCHA 컴포넌트.
 *
 * 실제 활성화 시 필요 사항:
 * 1. Cloudflare Dashboard → Turnstile → 사이트 추가 → siteKey 발급
 * 2. .env.local에 NEXT_PUBLIC_TURNSTILE_SITE_KEY 설정
 * 3. 서버 측에서 siteverify API로 토큰 검증 (secret key 필요)
 *
 * @see https://developers.cloudflare.com/turnstile/
 */

const TURNSTILE_SCRIPT_URL =
  "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

interface TurnstileProps {
  /** 검증 성공 시 토큰을 전달하는 콜백 */
  onVerify: (token: string) => void;
  /** 검증 만료 시 콜백 */
  onExpire?: () => void;
  /** 검증 에러 시 콜백 */
  onError?: () => void;
  /** Turnstile 테마 */
  theme?: "light" | "dark" | "auto";
  /** 위젯 크기 */
  size?: "normal" | "compact";
}

/* 전역에 turnstile 스크립트 로드 상태 추적 */
let scriptLoaded = false;
let scriptLoading = false;
const loadCallbacks: (() => void)[] = [];

function loadTurnstileScript(): Promise<void> {
  if (scriptLoaded) return Promise.resolve();

  return new Promise((resolve) => {
    if (scriptLoading) {
      loadCallbacks.push(resolve);
      return;
    }
    scriptLoading = true;

    const script = document.createElement("script");
    script.src = TURNSTILE_SCRIPT_URL;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      scriptLoaded = true;
      scriptLoading = false;
      resolve();
      loadCallbacks.forEach((cb) => cb());
      loadCallbacks.length = 0;
    };
    script.onerror = () => {
      scriptLoading = false;
      /* 스크립트 로드 실패 시 조용히 실패 — 사용자 경험 방해 금지 */
      resolve();
    };
    document.head.appendChild(script);
  });
}

export function Turnstile({
  onVerify,
  onExpire,
  onError,
  theme = "auto",
  size = "normal",
}: TurnstileProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);

  const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;

  const renderWidget = useCallback(() => {
    if (
      !containerRef.current ||
      !siteKey ||
      typeof window === "undefined" ||
      !window.turnstile
    ) {
      return;
    }

    /* 이미 렌더된 위젯이 있으면 제거 */
    if (widgetIdRef.current !== null) {
      try {
        window.turnstile.remove(widgetIdRef.current);
      } catch {
        /* 무시 */
      }
    }

    widgetIdRef.current = window.turnstile.render(
      containerRef.current,
      {
        sitekey: siteKey,
        theme,
        size,
        callback: onVerify,
        "expired-callback": onExpire,
        "error-callback": onError,
      },
    );
  }, [siteKey, theme, size, onVerify, onExpire, onError]);

  useEffect(() => {
    if (!siteKey) return;

    loadTurnstileScript().then(renderWidget);

    return () => {
      if (
        widgetIdRef.current !== null &&
        window.turnstile
      ) {
        try {
          window.turnstile.remove(widgetIdRef.current);
        } catch {
          /* 언마운트 시 조용히 실패 */
        }
        widgetIdRef.current = null;
      }
    };
  }, [siteKey, renderWidget]);

  /* siteKey가 없으면 아무것도 렌더하지 않음 (개발 모드) */
  if (!siteKey) return null;

  return (
    <div
      ref={containerRef}
      className="turnstile-container"
      aria-label="보안 검증"
    />
  );
}
