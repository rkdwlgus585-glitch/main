"use client";

import Link from "next/link";
import { startTransition, useDeferredValue, useState } from "react";

type ArchiveCatalogItem = {
  href: string;
  title: string;
  summary: string;
  kind: "board" | "page";
  category: string;
  categoryLabel: string;
  mode: string;
};

const filterOptions = [
  { value: "all", label: "전체" },
  { value: "board", label: "게시판" },
  { value: "page", label: "정적 페이지" },
] as const;

export function ArchiveCatalog({ items }: { items: ArchiveCatalogItem[] }) {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<(typeof filterOptions)[number]["value"]>("all");
  const deferredQuery = useDeferredValue(query);
  const normalizedQuery = deferredQuery.trim().toLowerCase();

  const filteredItems = items.filter((item) => {
    if (kind !== "all" && item.kind !== kind) {
      return false;
    }

    if (!normalizedQuery) {
      return true;
    }

    const target = [item.title, item.summary, item.categoryLabel, item.mode].join(" ").toLowerCase();
    return target.includes(normalizedQuery);
  });

  return (
    <section className="section-block">
      <div className="section-header">
        <p className="eyebrow">Archive Finder</p>
        <h2>원문 보존 컨텐츠를 제목과 카테고리 기준으로 바로 찾습니다</h2>
        <p>
          notice, premium, 뉴스, FAQ, 정적 안내 페이지를 한 번에 검색할 수 있게 정리했습니다.
          서비스 랜딩에서 본 주제의 원문 글을 역추적할 때 쓰는 카탈로그입니다.
        </p>
      </div>

      <div className="archive-catalog-shell">
        <div className="archive-catalog-toolbar">
          <label className="archive-catalog-search">
            <span>검색</span>
            <input
              type="search"
              value={query}
              onChange={(event) => {
                const nextValue = event.target.value;
                startTransition(() => setQuery(nextValue));
              }}
              placeholder="예: 분할합병, 건설업등록, 프리미엄"
            />
          </label>

          <div className="archive-catalog-filters" aria-label="컨텐츠 유형 필터">
            {filterOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`chip${kind === option.value ? " chip--active" : ""}`}
                onClick={() => setKind(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="archive-catalog-meta">
          <strong>{filteredItems.length.toLocaleString("ko-KR")}건</strong>
          <span>검색 조건에 맞는 보존 컨텐츠 수</span>
        </div>

        <div className="archive-catalog-grid">
          {filteredItems.map((item) => (
            <article key={`${item.kind}-${item.href}`} className="archive-catalog-card">
              <div className="archive-catalog-card-top">
                <span className="archive-catalog-kind">{item.kind === "board" ? "게시판" : "정적 페이지"}</span>
                <span className="archive-catalog-mode">{item.mode}</span>
              </div>
              <strong>{item.title}</strong>
              <span className="archive-catalog-category">{item.categoryLabel}</span>
              <p>{item.summary}</p>
              <Link href={item.href}>바로가기</Link>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
