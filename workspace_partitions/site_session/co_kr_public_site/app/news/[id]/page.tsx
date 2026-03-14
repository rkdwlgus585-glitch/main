import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { LegacyContentPage } from "@/components/legacy-content-page";
import { boardConfig } from "@/lib/content-map";
import { getBoardPostById } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";

type PageProps = {
  params: Promise<{
    id: string;
  }>;
};

export const revalidate = 3600;
export const dynamicParams = true;

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const post = getBoardPostById("news", id);

  if (!post) {
    return {};
  }

  return buildPageMetadata(
    `${boardConfig.news.path}/${encodeURIComponent(post.id)}`,
    post.title,
    post.summary,
  );
}

export default async function NewsDetailPage({ params }: PageProps) {
  const { id } = await params;
  const post = getBoardPostById("news", id);

  if (!post) {
    notFound();
  }

  if (decodeURIComponent(id) !== post.id) {
    permanentRedirect(`${boardConfig.news.path}/${encodeURIComponent(post.id)}`);
  }

  return (
    <LegacyContentPage
      breadcrumbs={[
        { href: "/", label: "홈" },
        { href: boardConfig.news.path, label: boardConfig.news.title },
        { href: `${boardConfig.news.path}/${encodeURIComponent(post.id)}`, label: post.id },
      ]}
      eyebrow={boardConfig.news.eyebrow}
      title={post.title}
      description={post.summary}
      publishedAt={post.publishedAt}
      updatedAt={post.updatedAt}
      views={post.views}
      contentHtml={post.contentHtml}
    />
  );
}
