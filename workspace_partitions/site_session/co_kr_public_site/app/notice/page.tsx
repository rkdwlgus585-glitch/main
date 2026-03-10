import type { Metadata } from "next";
import { BoardList } from "@/components/board-list";
import { boardConfig } from "@/lib/content-map";
import { getBoardPosts } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";

const PAGE_SIZE = 20;

export const revalidate = 3600;

export const metadata: Metadata = buildPageMetadata(
  boardConfig.notice.path,
  boardConfig.notice.title,
  boardConfig.notice.description,
);

type PageProps = {
  searchParams: Promise<{
    page?: string;
  }>;
};

export default async function NoticePage({ searchParams }: PageProps) {
  const { page } = await searchParams;
  const currentPage = Math.max(1, Number(page) || 1);
  const posts = getBoardPosts("notice");
  const totalPages = Math.max(1, Math.ceil(posts.length / PAGE_SIZE));
  const pageNumber = Math.min(currentPage, totalPages);
  const pagePosts = posts.slice((pageNumber - 1) * PAGE_SIZE, pageNumber * PAGE_SIZE);

  return (
    <BoardList
      boardPath={boardConfig.notice.path}
      eyebrow={boardConfig.notice.eyebrow}
      title={boardConfig.notice.title}
      description={boardConfig.notice.description}
      posts={pagePosts}
      totalCount={posts.length}
      currentPage={pageNumber}
      totalPages={totalPages}
    />
  );
}
