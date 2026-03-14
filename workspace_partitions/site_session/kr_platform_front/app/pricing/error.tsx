"use client";

import Link from "next/link";

export default function PricingError({ reset }: { error: Error; reset: () => void }) {
  return (
    <main id="main" className="page-shell">
      <section className="widget-shell">
        <header className="widget-header">
          <div>
            <p className="eyebrow">요금제</p>
            <h2>페이지 오류</h2>
            <p>요금제 페이지에서 일시적인 오류가 발생했습니다.</p>
          </div>
        </header>
        <div className="widget-gate" role="alert">
          <p>잠시 후 다시 시도해 주세요.</p>
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
    </main>
  );
}
