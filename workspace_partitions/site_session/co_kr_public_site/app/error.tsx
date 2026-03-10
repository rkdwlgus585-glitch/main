"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="page-status-shell">
      <section className="error-shell" aria-labelledby="error-title">
        <p className="eyebrow">Something Went Wrong</p>
        <h1 id="error-title">페이지를 불러오는 중 문제가 발생했습니다</h1>
        <p>
          일시적인 오류일 수 있습니다. 다시 시도해도 해결되지 않으면 고객센터로 이동해 상담 채널로
          접수해 주세요.
        </p>
        <div className="error-actions">
          <button type="button" className="cta-primary" onClick={reset}>
            다시 시도
          </button>
          <Link className="cta-secondary" href="/support">
            고객센터 이동
          </Link>
        </div>
      </section>
    </div>
  );
}
