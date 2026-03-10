import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { LegacyContentPage } from "@/components/legacy-content-page";
import { boardConfig } from "@/lib/content-map";
import { getBoardPostById, getBoardPostIds } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";

type PageProps = {
  params: Promise<{
    id: string;
  }>;
};

export const revalidate = 3600;

export function generateStaticParams() {
  return getBoardPostIds("premium").map((id) => ({ id }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const post = getBoardPostById("premium", id);

  if (!post) {
    return {};
  }

  return buildPageMetadata(
    `${boardConfig.premium.path}/${encodeURIComponent(post.id)}`,
    post.title,
    post.summary,
  );
}

export default async function PremiumDetailPage({ params }: PageProps) {
  const { id } = await params;
  const post = getBoardPostById("premium", id);

  if (!post) {
    notFound();
  }

  if (decodeURIComponent(id) !== post.id) {
    permanentRedirect(`${boardConfig.premium.path}/${encodeURIComponent(post.id)}`);
  }

  return (
    <LegacyContentPage
      breadcrumbs={[
        { href: "/", label: "홈" },
        { href: boardConfig.premium.path, label: boardConfig.premium.title },
        { href: `${boardConfig.premium.path}/${encodeURIComponent(post.id)}`, label: post.id },
      ]}
      eyebrow={boardConfig.premium.eyebrow}
      title={post.title}
      description={post.summary}
      publishedAt={post.publishedAt}
      updatedAt={post.updatedAt}
      views={post.views}
      contentHtml={post.contentHtml}
    />
  );
}
