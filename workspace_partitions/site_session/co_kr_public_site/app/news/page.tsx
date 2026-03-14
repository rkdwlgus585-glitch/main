import type { Metadata } from "next";
import { BoardList } from "@/components/board-list";
import { boardConfig } from "@/lib/content-map";
import { getBoardPosts } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";

export const revalidate = 3600;

export const metadata: Metadata = buildPageMetadata(
  boardConfig.news.path,
  boardConfig.news.title,
  boardConfig.news.description,
);

export default function NewsPage() {
  const posts = getBoardPosts("news");

  return (
    <BoardList
      boardPath={boardConfig.news.path}
      eyebrow={boardConfig.news.eyebrow}
      title={boardConfig.news.title}
      description={boardConfig.news.description}
      treatmentLabel={boardConfig.news.treatmentLabel}
      treatmentSummary={boardConfig.news.treatmentSummary}
      posts={posts}
      totalCount={posts.length}
      currentPage={1}
      totalPages={1}
    />
  );
}
