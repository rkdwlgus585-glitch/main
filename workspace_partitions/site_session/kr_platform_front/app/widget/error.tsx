"use client";

import { useEffect } from "react";

/**
 * Widget-specific error boundary — renders INSIDE an iframe.
 * No site chrome (header/footer/back-links) because the parent page
 * already wraps the iframe with full layout.
 */
export default function WidgetError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      console.error("[WidgetError]", error);
    }
  }, [error]);

  return (
    <div className="widget-gate" role="alert" style={{ textAlign: "center", padding: "3rem 1.5rem" }}>
      <h2>실행 오류</h2>
      <p>위젯 로딩 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.</p>
      <button type="button" className="cta-primary" onClick={reset}>
        다시 시도
      </button>
    </div>
  );
}
