import Link from "next/link";
import { getLegacyPagePath } from "@/lib/legacy-content";
import type { LegacyPage } from "@/lib/legacy-types";

export function LegacyPageDirectory({
  eyebrow = "Legacy Content",
  title,
  description,
  pages,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  pages: LegacyPage[];
}) {
  if (pages.length === 0) {
    return null;
  }

  const duplicatedTitles = new Set(
    Object.entries(
      pages.reduce<Record<string, number>>((accumulator, page) => {
        accumulator[page.title] = (accumulator[page.title] ?? 0) + 1;
        return accumulator;
      }, {}),
    )
      .filter(([, count]) => count > 1)
      .map(([title]) => title),
  );

  return (
    <section className="section-block">
      <div className="section-header">
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>

      <div className="legacy-page-grid">
        {pages.map((page) => (
          <article key={page.slug} className="legacy-page-card">
            <span>{page.sourceUrl}</span>
            <h3>
              <Link href={getLegacyPagePath(page.slug)}>
                {duplicatedTitles.has(page.title) ? `${page.title} (${page.slug}.php)` : page.title}
              </Link>
            </h3>
            <p>{page.summary}</p>
            <Link className="board-card-link" href={getLegacyPagePath(page.slug)}>
              자세히 보기
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}
