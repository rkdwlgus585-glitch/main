import Link from "next/link";
import { Breadcrumbs } from "@/components/breadcrumbs";
import type { LegacyPost } from "@/lib/legacy-types";

function buildPagination(currentPage: number, totalPages: number) {
  const start = Math.max(1, currentPage - 2);
  const end = Math.min(totalPages, start + 4);
  const adjustedStart = Math.max(1, end - 4);

  return Array.from({ length: end - adjustedStart + 1 }, (_, index) => adjustedStart + index);
}

function buildPageHref(boardPath: string, page: number) {
  return page <= 1 ? boardPath : `${boardPath}?page=${page}`;
}

export function BoardList({
  boardPath,
  eyebrow,
  title,
  description,
  treatmentLabel,
  treatmentSummary,
  posts,
  totalCount,
  currentPage,
  totalPages,
}: {
  boardPath: string;
  eyebrow: string;
  title: string;
  description: string;
  treatmentLabel?: string;
  treatmentSummary?: string;
  posts: LegacyPost[];
  totalCount: number;
  currentPage: number;
  totalPages: number;
}) {
  const pagination = buildPagination(currentPage, totalPages);

  return (
    <div className="page-shell page-shell--inner">
      <Breadcrumbs items={[{ href: "/", label: "홈" }, { href: boardPath, label: title }]} />

      <section className="inner-hero">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </section>

      {treatmentLabel || treatmentSummary ? (
        <section className="board-treatment-banner" aria-label={`${title} 운영 기준`}>
          {treatmentLabel ? <span className="board-treatment-badge">{treatmentLabel}</span> : null}
          {treatmentSummary ? <p>{treatmentSummary}</p> : null}
        </section>
      ) : null}

      <section className="board-list-shell">
        <header className="board-list-header">
          <div>
            <p className="eyebrow">Imported Board</p>
            <h2>{title} 전체 목록</h2>
          </div>
          <div className="board-list-meta">
            <strong>{totalCount}건</strong>
            <span>{currentPage} / {totalPages} 페이지</span>
          </div>
        </header>

        <div className="board-card-list">
          {posts.map((post) => (
            <article key={post.id} className="board-card">
              <div className="board-card-meta">
                <span>{post.publishedAt}</span>
                {post.views ? <span>조회 {post.views}</span> : null}
              </div>
              <h3>
                <Link href={`${boardPath}/${encodeURIComponent(post.id)}`}>{post.title}</Link>
              </h3>
              <p>{post.summary}</p>
              <Link className="board-card-link" href={`${boardPath}/${encodeURIComponent(post.id)}`}>
                본문 보기
              </Link>
            </article>
          ))}
        </div>

        {totalPages > 1 ? (
          <nav className="board-pagination" aria-label={`${title} 페이지 이동`}>
            {currentPage > 1 ? (
              <Link className="board-pagination-link" href={buildPageHref(boardPath, currentPage - 1)}>
                이전
              </Link>
            ) : null}

            {pagination.map((pageNumber) => (
              <Link
                key={pageNumber}
                className={`board-pagination-link${pageNumber === currentPage ? " board-pagination-link--active" : ""}`}
                href={buildPageHref(boardPath, pageNumber)}
                aria-current={pageNumber === currentPage ? "page" : undefined}
              >
                {pageNumber}
              </Link>
            ))}

            {currentPage < totalPages ? (
              <Link className="board-pagination-link" href={buildPageHref(boardPath, currentPage + 1)}>
                다음
              </Link>
            ) : null}
          </nav>
        ) : null}
      </section>
    </div>
  );
}
