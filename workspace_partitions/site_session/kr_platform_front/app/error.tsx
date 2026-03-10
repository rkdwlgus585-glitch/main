"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[GlobalError]", error);
  }, [error]);

  return (
    <div className="page-shell not-found-shell">
      <p className="not-found-code" aria-hidden="true">
        Error
      </p>
      <h1>일시적인 오류가 발생했습니다</h1>
      <p className="not-found-body">
        잠시 후 다시 시도해 주세요. 문제가 지속되면 고객센터로 연락해 주세요.
      </p>
      <div className="not-found-links">
        <button type="button" className="cta-primary" onClick={reset}>
          다시 시도
        </button>
        <Link className="cta-primary not-found-secondary" href="/">
          홈으로 이동
        </Link>
      </div>
    </div>
  );
}
