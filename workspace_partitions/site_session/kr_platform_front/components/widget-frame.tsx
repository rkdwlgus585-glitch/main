"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  generateNonce,
  parseWidgetMessage,
} from "@/lib/widget-message-protocol";

type WidgetFrameProps = {
  title: string;
  description: string;
  widgetUrl: string;
  openUrl?: string;
  eyebrow?: string;
  launchLabel?: string;
  gateNote?: string;
  defaultExpanded?: boolean;
};

type LoadState = "idle" | "loading" | "loaded" | "error";

const MIN_IFRAME_HEIGHT = 600;
const DEFAULT_IFRAME_HEIGHT = 1400;

export function WidgetFrame({
  title,
  description,
  widgetUrl,
  openUrl = "",
  eyebrow = "Widget launch",
  launchLabel = "Start widget",
  gateNote = "The external engine iframe is created only after the launch button is pressed.",
  defaultExpanded = false,
}: WidgetFrameProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [iframeHeight, setIframeHeight] = useState(DEFAULT_IFRAME_HEIGHT);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const nonceRef = useRef<string>("");
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  const handleLaunch = useCallback(() => {
    nonceRef.current = generateNonce();
    setIsExpanded(true);
    setLoadState("loading");
  }, []);

  /* Speculative preconnect: when user hovers the launch button, start
     DNS + TCP + TLS to the widget origin so the iframe loads faster. */
  const prefetchedRef = useRef(false);
  const handlePreconnect = useCallback(() => {
    if (prefetchedRef.current || !widgetUrl) return;
    try {
      const origin = new URL(widgetUrl).origin;
      if (origin && origin !== window.location.origin) {
        const link = document.createElement("link");
        link.rel = "preconnect";
        link.href = origin;
        link.crossOrigin = "anonymous";
        document.head.appendChild(link);
        prefetchedRef.current = true;
      }
    } catch {
      // Invalid URL — ignore
    }
  }, [widgetUrl]);

  const handleLoad = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setLoadState("loaded");
    // Send handshake init to iframe — widget can respond with widget-ready
    try {
      iframeRef.current?.contentWindow?.postMessage(
        { type: "platform-handshake", nonce: nonceRef.current },
        "*",
      );
    } catch {
      // Silently ignore if cross-origin blocks this
    }
  }, []);

  const handleRetry = useCallback(() => {
    nonceRef.current = generateNonce();
    setLoadState("loading");
  }, []);

  // PostMessage listener — handles widget-ready / widget-resize / widget-error
  useEffect(() => {
    if (loadState !== "loading" && loadState !== "loaded") return;

    function onMessage(event: MessageEvent) {
      const msg = parseWidgetMessage(event);
      if (!msg) return;

      switch (msg.type) {
        case "widget-ready":
          // Nonce validation: if widget echoes nonce, verify it matches.
          // Accept messages without nonce for backward compatibility.
          if (msg.nonce && msg.nonce !== nonceRef.current) break;
          // Confirm iframe JS initialised — clear timeout, mark loaded
          if (timeoutRef.current) clearTimeout(timeoutRef.current);
          setLoadState("loaded");
          break;

        case "widget-resize":
          setIframeHeight(Math.max(msg.height, MIN_IFRAME_HEIGHT));
          break;

        case "widget-error":
          // Non-fatal — log to console but don't break the UI
          // eslint-disable-next-line no-console
          console.warn("[widget-error]", msg.code, msg.detail ?? "");
          break;
      }
    }

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [loadState]);

  // Loading timeout
  useEffect(() => {
    if (loadState === "loading") {
      timeoutRef.current = setTimeout(() => {
        setLoadState("error");
      }, 20_000);
    }
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [loadState]);

  return (
    <section className="widget-shell">
      <header className="widget-header">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        {openUrl ? (
          <a className="widget-open" href={openUrl} target="_blank" rel="noreferrer noopener">
            {"전체 화면으로 열기"}
          </a>
        ) : null}
      </header>
      {!isExpanded ? (
        <div className="widget-gate" data-traffic-gate="closed" aria-hidden={loadState === "loading"}>
          <p>{gateNote}</p>
          <button
            type="button"
            className="widget-launch-button"
            data-traffic-gate-launch="true"
            onClick={handleLaunch}
            onPointerEnter={handlePreconnect}
          >
            {launchLabel}
          </button>
        </div>
      ) : (
        <div className="widget-viewport" data-traffic-gate="open" aria-busy={loadState === "loading"}>
          {loadState === "loading" && (
            <div className="widget-loading" role="status" aria-label="로딩 중">
              <div className="widget-spinner" />
              <p>AI 엔진을 불러오는 중입니다...</p>
            </div>
          )}
          {loadState === "error" && (
            <div className="widget-error" role="alert">
              <p>엔진 연결에 시간이 걸리고 있습니다.</p>
              <p className="widget-error-hint">
                네트워크 상태를 확인하시거나, 잠시 후 다시 시도해 주세요.
              </p>
              <button type="button" className="widget-retry-button" onClick={handleRetry}>
                다시 시도
              </button>
            </div>
          )}
          <iframe
            ref={iframeRef}
            key={loadState === "error" ? "retry" : "initial"}
            src={widgetUrl}
            title={title}
            style={{
              width: "100%",
              minHeight: iframeHeight,
              border: 0,
              display: loadState === "loaded" ? "block" : "none",
            }}
            sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
            allow="clipboard-write"
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
            onLoad={handleLoad}
          />
        </div>
      )}
    </section>
  );
}
