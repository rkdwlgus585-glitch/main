"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function YangdoError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      console.error("[YangdoError]", error);
    }
  }, [error]);

  return (
    <section className="widget-shell">
      <header className="widget-header">
        <div>
          <p className="eyebrow">AI 양도가 산정</p>
          <h2>엔진 로딩 오류</h2>
          <p>양도가 산정 엔진에서 일시적인 오류가 발생했습니다.</p>
        </div>
      </header>
      <div className="widget-gate" role="alert">
        <p>잠시 후 다시 시도해 주세요. 문제가 지속되면 고객센터로 연락해 주세요.</p>
        <div className="not-found-links">
          <button type="button" className="cta-primary" onClick={reset}>
            다시 시도
          </button>
          <Link className="cta-secondary not-found-secondary" href="/">
            홈으로 이동
          </Link>
        </div>
      </div>
    </section>
  );
}
