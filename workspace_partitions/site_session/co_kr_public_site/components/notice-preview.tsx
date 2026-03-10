import Link from "next/link";
import { getImportManifest, getLatestPosts } from "@/lib/legacy-content";

const boardLinks = [
  { href: "/notice", key: "notice", label: "공지사항" },
  { href: "/premium", key: "premium", label: "프리미엄 매물" },
  { href: "/news", key: "news", label: "뉴스" },
  { href: "/tl_faq", key: "tl_faq", label: "FAQ" },
  { href: "/archive", key: "pages", label: "정적 페이지" },
] as const;

export function NoticePreview() {
  const notices = getLatestPosts("notice", 3);
  const manifest = getImportManifest();

  return (
    <section className="section-block">
      <div className="section-header">
        <p className="eyebrow">Imported Content</p>
        <h2>이관된 게시판과 콘텐츠를 바로 확인할 수 있습니다</h2>
      </div>

      <div className="board-overview-grid">
        {boardLinks.map((board) => (
          <article key={board.href} className="board-overview-card">
            <strong>{board.label}</strong>
            <span>{manifest.counts[board.key]}건</span>
            <Link href={board.href}>바로가기</Link>
          </article>
        ))}
      </div>

      <div className="notice-grid">
        {notices.map((notice) => (
          <article key={notice.id} className="notice-card">
            <span>{notice.publishedAt}</span>
            <h3>
              <Link href={`/notice/${encodeURIComponent(notice.id)}`}>{notice.title}</Link>
            </h3>
            <p>{notice.summary}</p>
          </article>
        ))}
      </div>
      <div className="notice-foot">
        <Link href="/notice">공지사항 전체 보기</Link>
      </div>
    </section>
  );
}
