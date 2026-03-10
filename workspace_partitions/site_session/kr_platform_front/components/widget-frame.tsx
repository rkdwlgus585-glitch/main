"use client";

import { useCallback, useEffect, useRef, useState } from "react";

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
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleLaunch = useCallback(() => {
    setIsExpanded(true);
    setLoadState("loading");
  }, []);

  const handleLoad = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setLoadState("loaded");
  }, []);

  const handleRetry = useCallback(() => {
    setLoadState("loading");
  }, []);

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
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        {openUrl ? (
          <a className="widget-open" href={openUrl} target="_blank" rel="noreferrer noopener">
            {"전체 화면으로 열기"}
          </a>
        ) : null}
      </header>
      {!isExpanded ? (
        <div className="widget-gate" data-traffic-gate="closed">
          <p>{gateNote}</p>
          <button
            type="button"
            className="widget-launch-button"
            data-traffic-gate-launch="true"
            onClick={handleLaunch}
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
            key={loadState === "error" ? "retry" : "initial"}
            src={widgetUrl}
            title={title}
            style={{
              width: "100%",
              minHeight: 1400,
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
