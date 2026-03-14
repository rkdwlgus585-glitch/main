import type { Metadata } from "next";
import Link from "next/link";
import { ArchiveCatalog } from "@/components/archive-catalog";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { ContentGovernanceSection } from "@/components/content-governance";
import { LegacyPageDirectory } from "@/components/legacy-page-directory";
import { boardConfig, pageGroupConfig } from "@/lib/content-map";
import { getImportManifest, getLegacyPageGroups, getLegacyPagePath, getListingDatasetStats } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";

export const revalidate = 3600;

export const metadata: Metadata = buildPageMetadata(
  "/archive",
  "전체 컨텐츠 아카이브",
  "seoulmna.co.kr에서 가져온 정적 안내 페이지와 게시판 경로를 한 곳에서 확인할 수 있는 콘텐츠 아카이브입니다.",
);

const boardCards = [
  { href: "/mna", label: "양도양수 매물", countKey: "mna" },
  { href: boardConfig.notice.path, label: boardConfig.notice.title, countKey: "notice" },
  { href: boardConfig.premium.path, label: boardConfig.premium.title, countKey: "premium" },
  { href: boardConfig.news.path, label: boardConfig.news.title, countKey: "news" },
  { href: "/tl_faq", label: "FAQ", countKey: "tl_faq" },
] as const;

const groupLabelMap = {
  registration: pageGroupConfig.registration.label,
  corporate: pageGroupConfig.corporate.label,
  splitMerger: pageGroupConfig["split-merger"].label,
  practice: pageGroupConfig.practice.label,
  support: pageGroupConfig.support.label,
  mnaInfo: pageGroupConfig["mna-info"].label,
} as const;

export default function ImportedPagesIndex() {
  const manifest = getImportManifest();
  const listingStats = getListingDatasetStats();
  const groups = getLegacyPageGroups();
  const catalogItems = [
    {
      href: "/mna",
      title: "양도양수 매물",
      summary: "구글시트 원본을 기준으로 동기화하는 운영형 매물 보드입니다.",
      kind: "board" as const,
      category: "mna",
      categoryLabel: "양도양수",
      mode: "구글시트 동기화",
    },
    {
      href: boardConfig.notice.path,
      title: boardConfig.notice.title,
      summary: boardConfig.notice.treatmentSummary,
      kind: "board" as const,
      category: "notice",
      categoryLabel: "공지사항",
      mode: boardConfig.notice.treatmentLabel,
    },
    {
      href: boardConfig.premium.path,
      title: boardConfig.premium.title,
      summary: boardConfig.premium.treatmentSummary,
      kind: "board" as const,
      category: "premium",
      categoryLabel: "프리미엄",
      mode: boardConfig.premium.treatmentLabel,
    },
    {
      href: boardConfig.news.path,
      title: boardConfig.news.title,
      summary: boardConfig.news.treatmentSummary,
      kind: "board" as const,
      category: "news",
      categoryLabel: "뉴스",
      mode: boardConfig.news.treatmentLabel,
    },
    {
      href: "/tl_faq",
      title: "FAQ",
      summary: "원문 FAQ 페이지를 그대로 보존하고 고객센터 동선에서 재활용합니다.",
      kind: "board" as const,
      category: "tl_faq",
      categoryLabel: "FAQ",
      mode: "원문 보존",
    },
    ...Object.entries(groups).flatMap(([groupKey, pages]) =>
      pages.map((page) => ({
        href: getLegacyPagePath(page.slug),
        title: page.title,
        summary: page.summary,
        kind: "page" as const,
        category: groupKey,
        categoryLabel: groupLabelMap[groupKey as keyof typeof groupLabelMap] ?? "정적 페이지",
        mode: "원문 보존",
      })),
    ),
  ];
  const totalContentCount =
    listingStats.sheetCount +
    manifest.counts.notice +
    manifest.counts.premium +
    manifest.counts.news +
    manifest.counts.tl_faq +
    manifest.counts.pages;

  return (
    <div className="page-shell page-shell--inner">
      <Breadcrumbs items={[{ href: "/", label: "홈" }, { href: "/archive", label: "전체 컨텐츠" }]} />

      <section className="inner-hero">
        <p className="eyebrow">Content Archive</p>
        <h1>전체 컨텐츠 아카이브</h1>
        <p>
          독립 퍼블릭 사이트에서 운영해야 하는 게시판과 안내 페이지를 한 화면에서 찾을 수 있도록
          정리했습니다. 현재 기준으로 매물, 공지, 프리미엄, 뉴스, FAQ, 정적 페이지를 포함해 총{" "}
          {totalContentCount.toLocaleString("ko-KR")}건이 반영되어 있습니다.
        </p>
      </section>

      <ContentGovernanceSection />

      <section className="section-block">
        <div className="section-header">
          <p className="eyebrow">Board Access</p>
          <h2>가져온 게시판 바로가기</h2>
          <p>실제 운영형으로 이어지는 주요 보드부터 먼저 접근할 수 있게 정리했습니다.</p>
        </div>

        <div className="board-overview-grid">
          {boardCards.map((board) => (
            <article key={board.href} className="board-overview-card">
              <strong>{board.label}</strong>
              <span>{board.countKey === "mna" ? listingStats.sheetCount : manifest.counts[board.countKey]}건</span>
              <Link href={board.href}>바로가기</Link>
            </article>
          ))}
        </div>
      </section>

      <ArchiveCatalog items={catalogItems} />

      <LegacyPageDirectory
        eyebrow="M&A Info"
        title="양도양수 안내 페이지"
        description="매물 게시판 외에 양도양수 절차와 개요를 설명하는 정적 페이지들입니다."
        pages={groups.mnaInfo}
      />

      <LegacyPageDirectory
        eyebrow="Registration"
        title="건설업 등록 안내"
        description="신규 등록과 추가 등록 안내에 해당하는 정적 페이지 모음입니다."
        pages={groups.registration}
      />

      <LegacyPageDirectory
        eyebrow="Corporate"
        title="법인 설립 안내"
        description="법인 설립과 관련된 설명 페이지를 한 곳에 모았습니다."
        pages={groups.corporate}
      />

      <LegacyPageDirectory
        eyebrow="Split & Merger"
        title="분할합병 안내"
        description="분할합병 절차와 구조 설명 페이지를 독립 사이트 기준으로 연결했습니다."
        pages={groups.splitMerger}
      />

      <LegacyPageDirectory
        eyebrow="Practice"
        title="건설 실무 자료"
        description="실무 설명, 업종 안내, 보완 자료 성격의 정적 콘텐츠입니다."
        pages={groups.practice}
      />

      <LegacyPageDirectory
        eyebrow="Support"
        title="고객센터 및 운영 안내"
        description="상담, 위치, 개인정보 처리 등 운영성 페이지를 모아두었습니다."
        pages={groups.support}
      />
    </div>
  );
}
