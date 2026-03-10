import Link from "next/link";

export default function NotFoundPage() {
  return (
    <div className="page-shell page-shell--inner">
      <section className="not-found-shell">
        <p className="not-found-code">404</p>
        <h1>페이지를 찾을 수 없습니다</h1>
        <p>주소가 변경되었거나 아직 준비되지 않은 페이지입니다. 메인이나 고객센터로 이동해 주세요.</p>
        <div className="hero-actions">
          <Link className="cta-primary" href="/">
            메인으로 이동
          </Link>
          <Link className="cta-secondary not-found-secondary" href="/support">
            고객센터 이동
          </Link>
        </div>
      </section>
    </div>
  );
}
