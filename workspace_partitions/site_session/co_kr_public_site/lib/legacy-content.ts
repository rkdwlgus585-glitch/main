import listingDetailsData from "@/data/imported/listing-details.json";
import listingSheetRowsData from "@/data/imported/listing-sheet-rows.json";
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

type ListingImportManifest = {
  generatedAt: string;
  counts: Record<string, number>;
};

type SheetListingRow = {
  id: string;
  sourceUid: string;
  rowIndex: number;
  sheetNo: string;
  updatedAt: string;
  status: string;
  sectors: string[];
  sectorLabel: string;
  licenseYears: string[];
  capacityValues: string[];
  performance3Values: string[];
  performance5Values: string[];
  performance2025Values: string[];
  region: string;
  companyType: string;
  companyYear: string;
  shares: string;
  associationMembership: string;
  capital: string;
  balance: string;
  price: string;
  claimPrice: string;
  memo: string;
  debtRatio: string;
  liquidityRatio: string;
  surplus: string;
  priceTraceSummary: string;
  priceSource: string;
  priceEvidence: string;
  priceConfidence: string;
  priceFallback: string;
  sourceUrl: string;
  sourceNowmnaUrl: string;
};

const legacyImportedSummaries = listingSummariesData as LegacyListingSummary[];
const legacyImportedDetails = listingDetailsData as LegacyListingDetail[];
const sheetListingRows = (listingSheetRowsData as SheetListingRow[]).filter((item) => Boolean(item?.id));
const noticePosts = noticePostsData as LegacyPost[];
const premiumPosts = premiumPostsData as LegacyPost[];
const newsPosts = newsPostsData as LegacyPost[];
const tlFaqPage = tlFaqPageData as LegacyPost;
const legacyPages = pagesData as LegacyPage[];
const importManifest = manifestData as ListingImportManifest;

const boardPosts = {
  notice: noticePosts,
  premium: premiumPosts,
  news: newsPosts,
} as const satisfies Record<Exclude<LegacyBoardName, "tl_faq">, LegacyPost[]>;

const legacyBoardRoutes = {
  mna: "/mna",
  notice: "/notice",
  premium: "/premium",
  news: "/news",
  tl_faq: "/tl_faq",
} as const;

function normalizeId(value: string) {
  return decodeURIComponent(value).trim().toLowerCase();
}

function normalizePageSlug(value: string) {
  return decodeURIComponent(value).trim().replace(/\.php$/i, "");
}

function normalizeSpace(value: string | null | undefined) {
  return (value ?? "").replace(/\s+/g, " ").trim();
}

function uniqueStrings(values: Array<string | null | undefined>) {
  const output: string[] = [];
  const seen = new Set<string>();

  for (const value of values) {
    const normalized = normalizeSpace(value);
    if (!normalized || seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    output.push(normalized);
  }

  return output;
}

function preferText(primary: string | null | undefined, fallback: string | null | undefined) {
  return normalizeSpace(primary) || normalizeSpace(fallback);
}

function joinNonEmpty(values: Array<string | null | undefined>, separator = " / ") {
  return uniqueStrings(values).join(separator);
}

function formatShares(value: string) {
  const normalized = normalizeSpace(value);
  if (!normalized) {
    return "";
  }
  if (normalized.includes("좌")) {
    return normalized;
  }
  if (/^\d+(?:\.\d+)?$/.test(normalized)) {
    return `${normalized}좌`;
  }
  return normalized;
}

function mergeRecordMaps(
  preferred: Record<string, string>,
  fallback: Record<string, string>,
) {
  const output: Record<string, string> = {};

  for (const [key, value] of Object.entries(fallback)) {
    const normalized = normalizeSpace(value);
    if (normalized) {
      output[key] = normalized;
    }
  }

  for (const [key, value] of Object.entries(preferred)) {
    const normalized = normalizeSpace(value);
    if (normalized) {
      output[key] = normalized;
    }
  }

  return output;
}

function getRepeatedValue(values: string[], index: number) {
  return values[index] ?? (values.length === 1 ? values[0] ?? "" : "");
}

function buildPerformanceRowsFromSheet(
  record: SheetListingRow,
  fallback: string[][],
) {
  const headers = ["업종", "면허년도", "시공능력", "3년실적", "5년실적", "2025"];
  const rowCount = Math.max(
    record.sectors.length,
    record.licenseYears.length,
    record.capacityValues.length,
    record.performance3Values.length,
    record.performance5Values.length,
    record.performance2025Values.length,
  );

  if (rowCount === 0) {
    return fallback.length > 0 ? fallback : [headers];
  }

  return [
    headers,
    ...Array.from({ length: rowCount }, (_, index) => ([
      getRepeatedValue(record.sectors, index),
      getRepeatedValue(record.licenseYears, index),
      getRepeatedValue(record.capacityValues, index),
      getRepeatedValue(record.performance3Values, index),
      getRepeatedValue(record.performance5Values, index),
      getRepeatedValue(record.performance2025Values, index),
    ])),
  ];
}

function buildSummaryFromSheet(
  record: SheetListingRow,
  fallback: LegacyListingSummary | null,
): LegacyListingSummary {
  const sectors = uniqueStrings(record.sectors.length > 0 ? record.sectors : fallback?.sectors ?? []);
  const sectorLabel = joinNonEmpty(
    sectors.length > 0 ? sectors : [record.sectorLabel, fallback?.sectorLabel],
    " · ",
  ) || "건설업";
  const region = preferText(record.region, fallback?.region);
  const companyType = preferText(record.companyType, fallback?.companyType);
  const companyYear = preferText(record.companyYear, fallback?.companyYear);
  const price = preferText(record.price, fallback?.price) || "협의";
  const licenseYears = uniqueStrings(
    record.licenseYears.length > 0 ? record.licenseYears : fallback?.licenseYears ?? [],
  );
  const capacityLabel = joinNonEmpty(
    record.capacityValues.length > 0 ? record.capacityValues : [fallback?.capacityLabel],
  ) || "-";
  const performance3Year = joinNonEmpty(
    record.performance3Values.length > 0 ? record.performance3Values : [fallback?.performance3Year],
  ) || "-";
  const performance5Year = joinNonEmpty(
    record.performance5Values.length > 0 ? record.performance5Values : [fallback?.performance5Year],
  ) || "-";
  const performance2025 = joinNonEmpty(
    record.performance2025Values.length > 0 ? record.performance2025Values : [fallback?.performance2025],
  ) || "-";
  const note = preferText(record.memo, fallback?.note);
  const headline = joinNonEmpty([region, companyType, price], " · ");

  return {
    id: record.id,
    title: sectorLabel === "건설업" ? "건설업 양도양수 매물" : `${sectorLabel} 양도양수 매물`,
    headline,
    updatedAt: preferText(record.updatedAt, fallback?.updatedAt) || importManifest.generatedAt,
    status: preferText(record.status, fallback?.status) || "검토중",
    sectors,
    sectorLabel,
    region,
    companyType,
    companyYear,
    association: preferText(formatShares(record.shares), fallback?.association),
    capital: preferText(record.capital, fallback?.capital),
    balance: preferText(record.balance, fallback?.balance),
    price,
    licenseYears,
    capacityLabel,
    performance3Year,
    performance5Year,
    performance2025,
    note,
    sourceUrl: preferText(record.sourceUrl, fallback?.sourceUrl) || `/mna/${encodeURIComponent(record.id)}`,
    sourceKind: fallback ? "sheet-merged" : "sheet-only",
  };
}

function buildOverviewFromSheet(
  record: SheetListingRow,
  summary: LegacyListingSummary,
  fallback: Record<string, string>,
) {
  const preferred: Record<string, string> = {
    상태: summary.status,
    면허: summary.sectorLabel,
    면허년도: joinNonEmpty(summary.licenseYears),
    시평: summary.capacityLabel,
    소재지: summary.region,
    회사형태: summary.companyType,
    법인설립일: summary.companyYear,
    "공제조합 출자좌": formatShares(record.shares),
    협회: record.associationMembership,
    자본금: summary.capital,
    "대출후 남은잔액": summary.balance,
    양도가: summary.price,
  };

  if (normalizeSpace(record.claimPrice)) {
    preferred.청구양도가 = record.claimPrice;
  }

  return mergeRecordMaps(preferred, fallback);
}

function buildFinanceFromSheet(
  record: SheetListingRow,
  fallback: Record<string, string>,
) {
  const preferred: Record<string, string> = {
    부채비율: record.debtRatio,
    유동비율: record.liquidityRatio,
    잉여금: record.surplus,
    가격추적: record.priceTraceSummary,
    가격출처: record.priceSource,
    가격근거: record.priceEvidence,
    가격신뢰도: record.priceConfidence,
    대체기준: record.priceFallback,
  };

  return mergeRecordMaps(preferred, fallback);
}

function buildNotesFromSheet(
  record: SheetListingRow,
  fallback: string[],
) {
  return uniqueStrings([
    record.memo,
    normalizeSpace(record.claimPrice) ? `청구 양도가는 ${record.claimPrice}입니다.` : "",
    normalizeSpace(record.priceEvidence) ? `가격 근거: ${record.priceEvidence}` : "",
    normalizeSpace(record.priceTraceSummary) ? `가격 추적: ${record.priceTraceSummary}` : "",
    normalizeSpace(record.priceFallback) ? `대체 기준: ${record.priceFallback}` : "",
    ...fallback,
  ]);
}

function buildGuidanceFromSheet(
  record: SheetListingRow,
  fallback: string[],
) {
  return uniqueStrings([
    ...fallback,
    "이 매물은 서울MNA 운영 구글시트 원본 기준으로 최신 상태를 반영했습니다.",
    "계약 전에는 법인 서류, 진행 공사 승계 여부, 기술인력 유지, 공제조합 상태를 별도로 대조하세요.",
    "양도·합병 신고와 공고 요건은 업종 및 거래 구조에 따라 달라질 수 있으므로 계약서 작성 전에 별도 검토가 필요합니다.",
    normalizeSpace(record.sourceNowmnaUrl) ? `외부 출처 확인: ${record.sourceNowmnaUrl}` : "",
  ]);
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function buildPairsTable(entries: Record<string, string>) {
  const rows = Object.entries(entries)
    .map(([label, value]) => {
      const normalized = normalizeSpace(value);
      if (!normalized) {
        return "";
      }
      return `<tr><th>${escapeHtml(label)}</th><td>${escapeHtml(normalized)}</td></tr>`;
    })
    .filter(Boolean)
    .join("");

  if (!rows) {
    return "";
  }

  return `<div class="legacy-table-shell"><table class="legacy-table"><tbody>${rows}</tbody></table></div>`;
}

function buildPerformanceTable(rows: string[][]) {
  if (rows.length === 0) {
    return "";
  }

  const [headers, ...bodyRows] = rows;
  const headHtml = headers.map((cell) => `<th>${escapeHtml(cell)}</th>`).join("");
  const bodyHtml = bodyRows
    .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(normalizeSpace(cell) || "-")}</td>`).join("")}</tr>`)
    .join("");

  return [
    '<div class="legacy-table-shell"><table class="legacy-table"><thead><tr>',
    headHtml,
    "</tr></thead><tbody>",
    bodyHtml,
    "</tbody></table></div>",
  ].join("");
}

function buildSyntheticListingHtml(
  record: SheetListingRow,
  overview: Record<string, string>,
  finance: Record<string, string>,
  performanceRows: string[][],
  notes: string[],
  guidance: string[],
) {
  const sections: string[] = [];
  const originNote = normalizeSpace(record.sourceNowmnaUrl)
    ? `<p>구글시트 원본 기준 최신 상태를 반영했습니다. 외부 출처는 <a href="${escapeHtml(record.sourceNowmnaUrl)}">${escapeHtml(record.sourceNowmnaUrl)}</a> 입니다.</p>`
    : "<p>구글시트 원본 기준 최신 상태를 반영했습니다.</p>";

  sections.push(`<section><h2>매물 기준</h2>${originNote}</section>`);

  const overviewTable = buildPairsTable(overview);
  if (overviewTable) {
    sections.push(`<section><h2>회사개요</h2>${overviewTable}</section>`);
  }

  const performanceTable = buildPerformanceTable(performanceRows);
  if (performanceTable) {
    sections.push(`<section><h2>실적 요약</h2>${performanceTable}</section>`);
  }

  const financeTable = buildPairsTable(finance);
  if (financeTable) {
    sections.push(`<section><h2>재무제표</h2>${financeTable}</section>`);
  }

  if (notes.length > 0) {
    sections.push(
      `<section><h2>주요체크사항</h2><ul>${notes.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>`,
    );
  }

  if (guidance.length > 0) {
    sections.push(
      `<section><h2>안내</h2><ul>${guidance.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>`,
    );
  }

  return sections.join("");
}

function toSummary(detail: LegacyListingDetail): LegacyListingSummary {
  const {
    id,
    title,
    headline,
    updatedAt,
    status,
    sectors,
    sectorLabel,
    region,
    companyType,
    companyYear,
    association,
    capital,
    balance,
    price,
    licenseYears,
    capacityLabel,
    performance3Year,
    performance5Year,
    performance2025,
    note,
    sourceUrl,
    sourceKind,
  } = detail;

  return {
    id,
    title,
    headline,
    updatedAt,
    status,
    sectors,
    sectorLabel,
    region,
    companyType,
    companyYear,
    association,
    capital,
    balance,
    price,
    licenseYears,
    capacityLabel,
    performance3Year,
    performance5Year,
    performance2025,
    note,
    sourceUrl,
    sourceKind,
  };
}

function compareListingOrder(
  left: Pick<LegacyListingSummary, "id" | "updatedAt">,
  right: Pick<LegacyListingSummary, "id" | "updatedAt">,
) {
  const leftMatch = left.id.match(/^\d+/);
  const rightMatch = right.id.match(/^\d+/);
  const leftId = leftMatch ? Number(leftMatch[0]) : Number.NaN;
  const rightId = rightMatch ? Number(rightMatch[0]) : Number.NaN;

  if (Number.isFinite(leftId) && Number.isFinite(rightId) && leftId !== rightId) {
    return rightId - leftId;
  }

  const leftUpdated = new Date(left.updatedAt).getTime();
  const rightUpdated = new Date(right.updatedAt).getTime();
  if (leftUpdated !== rightUpdated) {
    return rightUpdated - leftUpdated;
  }

  return right.id.localeCompare(left.id, "ko-KR");
}

const legacySummaryById = new Map(
  legacyImportedSummaries.map((item) => [normalizeId(item.id), item] as const),
);
const legacyDetailById = new Map(
  legacyImportedDetails.map((item) => [normalizeId(item.id), item] as const),
);
const sheetRowIds = new Set(sheetListingRows.map((item) => normalizeId(item.id)));

const sheetBackedDetails = sheetListingRows.map((record) => {
  const fallbackSummary = legacySummaryById.get(normalizeId(record.id)) ?? null;
  const fallbackDetail = legacyDetailById.get(normalizeId(record.id)) ?? null;
  const summary = buildSummaryFromSheet(record, fallbackSummary);
  const overview = buildOverviewFromSheet(record, summary, fallbackDetail?.overview ?? {});
  const finance = buildFinanceFromSheet(record, fallbackDetail?.finance ?? {});
  const performanceRows = buildPerformanceRowsFromSheet(record, fallbackDetail?.performanceRows ?? []);
  const notes = buildNotesFromSheet(record, fallbackDetail?.notes ?? []);
  const guidance = buildGuidanceFromSheet(record, fallbackDetail?.guidance ?? []);

  return {
    ...summary,
    contentHtml: buildSyntheticListingHtml(record, overview, finance, performanceRows, notes, guidance),
    guidance,
    legacyTitle: fallbackDetail?.legacyTitle ?? summary.title,
    overview,
    performanceRows,
    finance,
    notes,
    sourceKind: fallbackDetail ? "sheet-merged" : "sheet-only",
  } satisfies LegacyListingDetail;
});

const legacyOnlyDetails = legacyImportedDetails
  .filter((item) => !sheetRowIds.has(normalizeId(item.id)))
  .map((item) => ({
    ...item,
    sourceKind: item.sourceKind ?? "legacy-import",
  } satisfies LegacyListingDetail));

const listingDetails = [...sheetBackedDetails].sort(compareListingOrder);
const listingSummaries = listingDetails.map(toSummary);
const listingDatasetStats = {
  legacyImportedCount: legacyImportedSummaries.length,
  sheetCount: sheetListingRows.length,
  mergedCount: listingSummaries.length,
  sheetMergedCount: listingSummaries.filter((item) => item.sourceKind === "sheet-merged").length,
  sheetOnlyCount: listingSummaries.filter((item) => item.sourceKind === "sheet-only").length,
  legacyOnlyCount: legacyOnlyDetails.length,
};

export function normalizeImportedHref(href: string) {
  const rawHref = href.trim();

  if (!rawHref) {
    return rawHref;
  }

  if (/^(mailto:|tel:|javascript:)/i.test(rawHref)) {
    return rawHref;
  }

  if (/^#tab\d+$/i.test(rawHref)) {
    return "#legacy-content-top";
  }

  let url: URL;

  try {
    url = rawHref.startsWith("/")
      ? new URL(rawHref, "https://seoulmna.co.kr")
      : new URL(rawHref);
  } catch {
    return rawHref;
  }

  const isLegacyHost = /(^|\.)seoulmna\.co\.kr$/i.test(url.hostname);
  const isRelativePath = rawHref.startsWith("/");

  if (!isLegacyHost && !isRelativePath) {
    return rawHref;
  }

  const sanitizedHash = /^#tab\d+$/i.test(url.hash) ? "" : url.hash;

  if (url.pathname === "/bbs/board.php") {
    const table = url.searchParams.get("bo_table")?.toLowerCase();
    const wrId = url.searchParams.get("wr_id");
    const boardPath = table ? legacyBoardRoutes[table as keyof typeof legacyBoardRoutes] : undefined;

    if (!boardPath) {
      return sanitizedHash || "#legacy-content-top";
    }

    if (table === "tl_faq") {
      return boardPath;
    }

    return wrId ? `${boardPath}/${encodeURIComponent(wrId)}` : boardPath;
  }

  if (url.pathname.toLowerCase().startsWith("/pages/")) {
    return `${url.pathname}${sanitizedHash}`;
  }

  if (Object.values(legacyBoardRoutes).some((path) => url.pathname === path || url.pathname.startsWith(`${path}/`))) {
    return `${url.pathname}${sanitizedHash}`;
  }

  if (rawHref.startsWith("#")) {
    return "#legacy-content-top";
  }

  return rawHref;
}

export function getImportManifest() {
  return importManifest;
}

export function getListingDatasetStats() {
  return listingDatasetStats;
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
  if (tlFaqPage.faqItems && tlFaqPage.faqItems.length > 0) {
    return tlFaqPage.faqItems.slice(0, limit);
  }

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
