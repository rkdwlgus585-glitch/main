import Link from "next/link";
import { boardConfig } from "@/lib/content-map";
import { getImportManifest, getListingDatasetStats } from "@/lib/legacy-content";

const toneClassMap = {
  sync: "content-policy-mode--sync",
  preserve: "content-policy-mode--preserve",
  upgrade: "content-policy-mode--upgrade",
} as const;

export function ContentGovernanceSection() {
  const manifest = getImportManifest();
  const listingStats = getListingDatasetStats();

  const cards = [
    {
      href: "/mna",
      title: "양도양수 매물",
      count: listingStats.sheetCount,
      mode: "구글시트 동기화",
      tone: "sync" as const,
      description: "매물은 공개 게시판이 아니라 26양도매물 구글시트 원본을 기준으로 동기화합니다. 공개 게시판 본문은 상세 설명 참고용으로만 병합합니다.",
    },
    {
      href: boardConfig.notice.path,
      title: boardConfig.notice.title,
      count: manifest.counts.notice,
      mode: boardConfig.notice.treatmentLabel,
      tone: "preserve" as const,
      description: "notice 게시판의 글은 원문 제목과 본문, 발행 순서를 그대로 보존해 운영 공지 아카이브로 제공합니다.",
    },
    {
      href: boardConfig.premium.path,
      title: boardConfig.premium.title,
      count: manifest.counts.premium,
      mode: boardConfig.premium.treatmentLabel,
      tone: "preserve" as const,
      description: "premium 게시판의 분석형 매물 글은 그대로 보존하고, 실제 탐색과 필터링은 운영형 매물 보드에서 별도로 제공합니다.",
    },
    {
      href: "/archive",
      title: "정적 안내 페이지",
      count: manifest.counts.pages,
      mode: "실무형 재구성",
      tone: "upgrade" as const,
      description: "기존 양도양수·등록·법인·분할합병 안내 글은 원문을 참고하되, 최신 법령, SEO, 고객경험 기준으로 서비스 랜딩 구조를 다시 설계했습니다.",
    },
    {
      href: boardConfig.news.path,
      title: "뉴스 · FAQ",
      count: manifest.counts.news + manifest.counts.tl_faq,
      mode: "원문 참고 + 보강",
      tone: "upgrade" as const,
      description: "뉴스와 FAQ는 원문 아카이브를 유지하면서, 실제 고객 동선에서는 고객센터와 서비스 상세 페이지에서 최신 기준으로 다시 설명합니다.",
    },
  ];

  return (
    <section className="section-block">
      <div className="section-header">
        <p className="eyebrow">Content Governance</p>
        <h2>무엇을 그대로 보존하고, 무엇을 운영형으로 업그레이드했는지 구분합니다</h2>
        <p>
          대체 사이트의 목적은 단순 복제가 아니라 운영 안정성과 검색 신뢰도를 함께 확보하는 것입니다.
          그래서 보존 대상과 재구성 대상을 분리해 관리합니다.
        </p>
      </div>

      <div className="content-policy-grid">
        {cards.map((card) => (
          <article key={card.title} className="content-policy-card">
            <div className="content-policy-top">
              <span className={`content-policy-mode ${toneClassMap[card.tone]}`}>{card.mode}</span>
              <strong>{card.count.toLocaleString("ko-KR")}건</strong>
            </div>
            <h3>{card.title}</h3>
            <p>{card.description}</p>
            <Link href={card.href}>해당 섹션 보기</Link>
          </article>
        ))}
      </div>

      <p className="content-policy-note">
        원문 보존 보드는 증거성과 이력 관리에 집중하고, 서비스 랜딩과 고객센터는 최신 법령, 법리 검토,
        고객 편의성 기준으로 별도 개선하는 구조입니다.
      </p>
    </section>
  );
}
