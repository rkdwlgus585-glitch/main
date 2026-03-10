import type { Metadata } from "next";
import { BoardList } from "@/components/board-list";
import { boardConfig } from "@/lib/content-map";
import { getBoardPosts } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";

const PAGE_SIZE = 12;

export const revalidate = 3600;

export const metadata: Metadata = buildPageMetadata(
  boardConfig.premium.path,
  boardConfig.premium.title,
  boardConfig.premium.description,
);

type PageProps = {
  searchParams: Promise<{
    page?: string;
  }>;
};

export default async function PremiumPage({ searchParams }: PageProps) {
  const { page } = await searchParams;
  const currentPage = Math.max(1, Number(page) || 1);
  const posts = getBoardPosts("premium");
  const totalPages = Math.max(1, Math.ceil(posts.length / PAGE_SIZE));
  const pageNumber = Math.min(currentPage, totalPages);
  const pagePosts = posts.slice((pageNumber - 1) * PAGE_SIZE, pageNumber * PAGE_SIZE);

  return (
    <BoardList
      boardPath={boardConfig.premium.path}
      eyebrow={boardConfig.premium.eyebrow}
      title={boardConfig.premium.title}
      description={boardConfig.premium.description}
      posts={pagePosts}
      totalCount={posts.length}
      currentPage={pageNumber}
      totalPages={totalPages}
    />
  );
}
