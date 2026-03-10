import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "404 — 페이지를 찾을 수 없습니다 | 서울건설정보",
};

export default function NotFound() {
  return (
    <main className="page-shell not-found-shell">
      <p className="not-found-code">404</p>
      <h1>요청하신 페이지를 찾을 수 없습니다</h1>
      <p className="not-found-body">
        주소가 변경되었거나 잘못된 경로일 수 있습니다. 아래 링크로 이동하세요.
      </p>
      <div className="not-found-links">
        <Link href="/" className="cta-primary">홈으로 돌아가기</Link>
        <Link href="/yangdo" className="cta-secondary not-found-secondary">AI 양도가 산정</Link>
        <Link href="/permit" className="cta-secondary not-found-secondary">건설업등록</Link>
      </div>
    </main>
  );
}
