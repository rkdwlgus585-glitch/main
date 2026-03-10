import listingDetailsData from "@/data/imported/listing-details.json";
import listingSummariesData from "@/data/imported/listing-summaries.json";
import manifestData from "@/data/imported/manifest.json";
import newsPostsData from "@/data/imported/news-posts.json";
import noticePostsData from "@/data/imported/notice-posts.json";
import pagesData from "@/data/imported/pages.json";
import premiumPostsData from "@/data/imported/premium-posts.json";
import tlFaqPageData from "@/data/imported/tl-faq-page.json";
import type {
  FaqPreviewItem,
  LegacyBoardName,
  LegacyListingDetail,
  LegacyListingSummary,
  LegacyPage,
  LegacyPageGroup,
  LegacyPost,
} from "@/lib/legacy-types";

const listingSummaries = listingSummariesData as LegacyListingSummary[];
const listingDetails = listingDetailsData as LegacyListingDetail[];
const noticePosts = noticePostsData as LegacyPost[];
const premiumPosts = premiumPostsData as LegacyPost[];
const newsPosts = newsPostsData as LegacyPost[];
const tlFaqPage = tlFaqPageData as LegacyPost;
const legacyPages = pagesData as LegacyPage[];
const importManifest = manifestData as {
  generatedAt: string;
  counts: Record<string, number>;
};

const boardPosts = {
  notice: noticePosts,
  premium: premiumPosts,
  news: newsPosts,
} as const satisfies Record<Exclude<LegacyBoardName, "tl_faq">, LegacyPost[]>;

function normalizeId(value: string) {
  return decodeURIComponent(value).trim().toLowerCase();
}

function normalizePageSlug(value: string) {
  return decodeURIComponent(value).trim().replace(/\.php$/i, "");
}

export function getImportManifest() {
  return importManifest;
}

export function getAllListings() {
  return listingSummaries;
}

export function getListingIds() {
  return listingDetails.map((item) => item.id);
}

export function getListingById(id: string) {
  const normalizedId = normalizeId(id);

  return listingDetails.find((item) => normalizeId(item.id) === normalizedId) ?? null;
}

export function getAdjacentListings(id: string) {
  const listing = getListingById(id);

  if (!listing) {
    return { previous: null, next: null };
  }

  const index = listingDetails.findIndex((item) => item.id === listing.id);

  if (index === -1) {
    return { previous: null, next: null };
  }

  return {
    previous: index > 0 ? listingSummaries[index - 1] ?? null : null,
    next: index < listingDetails.length - 1 ? listingSummaries[index + 1] ?? null : null,
  };
}

export function getLatestListingUpdatedAt() {
  return listingSummaries.reduce((latest, item) => (
    new Date(item.updatedAt).getTime() > new Date(latest).getTime() ? item.updatedAt : latest
  ), listingSummaries[0]?.updatedAt ?? importManifest.generatedAt);
}

export function getBoardPosts(board: Exclude<LegacyBoardName, "tl_faq">) {
  return boardPosts[board];
}

export function getBoardPostIds(board: Exclude<LegacyBoardName, "tl_faq">) {
  return boardPosts[board].map((post) => post.id);
}

export function getBoardPostById(board: Exclude<LegacyBoardName, "tl_faq">, id: string) {
  const normalizedId = normalizeId(id);

  return boardPosts[board].find((post) => normalizeId(post.id) === normalizedId) ?? null;
}

export function getLatestPosts(board: Exclude<LegacyBoardName, "tl_faq">, limit = 3) {
  return boardPosts[board].slice(0, limit);
}

export function getFaqPage() {
  return tlFaqPage;
}

export function getFaqPreviewItems(limit = 3): FaqPreviewItem[] {
  const headingPattern = /<h2[^>]*>([\s\S]*?)<\/h2>/gi;
  const paragraphPattern = /<p[^>]*>([\s\S]*?)<\/p>/i;
  const cleanInlineHtml = (value: string) => value
    .replace(/<br\s*\/?>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  const items: FaqPreviewItem[] = [];
  let match: RegExpExecArray | null = headingPattern.exec(tlFaqPage.contentHtml);

  while (match && items.length < limit) {
    const question = cleanInlineHtml(match[1]);
    const sectionStart = match.index + match[0].length;
    const nextMatch = headingPattern.exec(tlFaqPage.contentHtml);
    const sectionEnd = nextMatch ? nextMatch.index : tlFaqPage.contentHtml.length;
    const sectionHtml = tlFaqPage.contentHtml.slice(sectionStart, sectionEnd);
    const paragraphMatch = sectionHtml.match(paragraphPattern);
    const answer = cleanInlineHtml(paragraphMatch?.[1] ?? "");

    if (question && answer) {
      items.push({ question, answer });
    }

    match = nextMatch;
  }

  return items;
}

export function getAllLegacyPages() {
  return legacyPages;
}

export function getLegacyPageBySlug(slug: string) {
  const normalizedSlug = normalizePageSlug(slug);

  return legacyPages.find((page) => page.slug === normalizedSlug) ?? null;
}

export function getLegacyPagePath(slug: string) {
  return `/pages/${encodeURIComponent(normalizePageSlug(slug))}.php`;
}

export function getLegacyPagesByGroup(group: LegacyPageGroup) {
  return legacyPages.filter((page) => page.group === group);
}

export function getLegacyPageGroups() {
  return {
    registration: getLegacyPagesByGroup("registration"),
    corporate: getLegacyPagesByGroup("corporate"),
    splitMerger: getLegacyPagesByGroup("split-merger"),
    practice: getLegacyPagesByGroup("practice"),
    support: getLegacyPagesByGroup("support"),
    mnaInfo: getLegacyPagesByGroup("mna-info"),
  };
}

export function getLatestContentUpdatedAt() {
  const timestamps = [
    getLatestListingUpdatedAt(),
    ...noticePosts.map((post) => post.updatedAt),
    ...premiumPosts.map((post) => post.updatedAt),
    ...newsPosts.map((post) => post.updatedAt),
    ...legacyPages.map((page) => page.updatedAt),
    tlFaqPage.updatedAt,
  ].map((value) => new Date(value).getTime());

  return new Date(Math.max(...timestamps)).toISOString();
}
