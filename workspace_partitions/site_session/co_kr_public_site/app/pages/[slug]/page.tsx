import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { LegacyContentPage } from "@/components/legacy-content-page";
import { pageGroupConfig } from "@/lib/content-map";
import { getLegacyPageBySlug, getLegacyPagePath } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";

type PageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export const revalidate = 3600;
export const dynamicParams = true;

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const page = getLegacyPageBySlug(slug);

  if (!page) {
    return {};
  }

  return buildPageMetadata(
    getLegacyPagePath(page.slug),
    page.title,
    page.summary,
  );
}

export default async function LegacyStaticPage({ params }: PageProps) {
  const { slug } = await params;
  const page = getLegacyPageBySlug(slug);

  if (!page) {
    notFound();
  }

  const canonicalPath = getLegacyPagePath(page.slug);

  if (`/pages/${decodeURIComponent(slug)}` !== canonicalPath) {
    permanentRedirect(canonicalPath);
  }

  const group = page.group ? pageGroupConfig[page.group] : null;
  const breadcrumbs = [
    { href: "/", label: "홈" },
    ...(group ? [{ href: group.path, label: group.label }] : []),
    { href: canonicalPath, label: page.title },
  ];

  return (
    <LegacyContentPage
      breadcrumbs={breadcrumbs}
      eyebrow="Imported Page"
      title={page.title}
      description={page.summary}
      updatedAt={page.updatedAt}
      contentHtml={page.contentHtml}
    />
  );
}
