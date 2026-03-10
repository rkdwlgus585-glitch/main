import Link from "next/link";
import { notices } from "@/components/sample-data";

export function NoticePreview() {
  return (
    <section className="section-block">
      <div className="section-header">
        <p className="eyebrow">Notice</p>
        <h2>운영 사이트에서 바로 보이는 최근 공지</h2>
      </div>
      <div className="notice-grid">
        {notices.map((notice) => (
          <article key={notice.title} className="notice-card">
            <span>{notice.date}</span>
            <h3>{notice.title}</h3>
            <p>{notice.summary}</p>
          </article>
        ))}
      </div>
      <div className="notice-foot">
        <Link href="/support">고객센터에서 전체 안내 보기</Link>
      </div>
    </section>
  );
}
