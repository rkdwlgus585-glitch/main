"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useId, useMemo, useState } from "react";
import type { LegacyListingSummary } from "@/lib/legacy-types";

const DEFAULT_PAGE_SIZE = 30;

function getStatusTone(status: string) {
  if (status === "가능" || status === "추천") {
    return "available";
  }

  if (status === "완료") {
    return "complete";
  }

  return "review";
}

function getValidOption(value: string | null, options: string[]) {
  return options.find((item) => item === value) ?? "전체";
}

function getValidPage(value: string | number | null | undefined) {
  const numeric = Number(value);

  return Number.isFinite(numeric) && numeric > 0 ? Math.floor(numeric) : 1;
}

function buildPagination(currentPage: number, totalPages: number) {
  const start = Math.max(1, currentPage - 2);
  const end = Math.min(totalPages, start + 4);
  const adjustedStart = Math.max(1, end - 4);

  return Array.from({ length: end - adjustedStart + 1 }, (_, index) => adjustedStart + index);
}

export function ListingBoard({
  listings,
  syncWithUrl = false,
  initialFilters,
}: {
  listings: LegacyListingSummary[];
  syncWithUrl?: boolean;
  initialFilters?: {
    sector?: string;
    region?: string;
    q?: string;
    page?: string;
  };
}) {
  const searchId = useId();
  const sectorOptions = useMemo(
    () => ["전체", ...Array.from(new Set(listings.flatMap((item) => item.sectors).filter(Boolean))).sort((a, b) => a.localeCompare(b, "ko-KR"))],
    [listings],
  );
  const regionOptions = useMemo(
    () => ["전체", ...Array.from(new Set(listings.map((item) => item.region).filter(Boolean))).sort((a, b) => a.localeCompare(b, "ko-KR"))],
    [listings],
  );

  const [sector, setSector] = useState(() => getValidOption(initialFilters?.sector ?? null, sectorOptions));
  const [region, setRegion] = useState(() => getValidOption(initialFilters?.region ?? null, regionOptions));
  const [searchTerm, setSearchTerm] = useState(() => initialFilters?.q ?? "");
  const [page, setPage] = useState(() => getValidPage(initialFilters?.page));
  const deferredSearchTerm = useDeferredValue(searchTerm.trim().toLowerCase());
  const isFiltering = searchTerm.trim().toLowerCase() !== deferredSearchTerm;

  useEffect(() => {
    if (!syncWithUrl) {
      return;
    }

    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      setSector(getValidOption(params.get("sector"), sectorOptions));
      setRegion(getValidOption(params.get("region"), regionOptions));
      setSearchTerm(params.get("q") ?? "");
      setPage(getValidPage(params.get("page")));
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [regionOptions, sectorOptions, syncWithUrl]);

  const filtered = useMemo(() => {
    return listings.filter((item) => {
      const sectorMatch = sector === "전체" || item.sectors.includes(sector) || item.sectorLabel === sector;
      const regionMatch = region === "전체" || item.region === region;
      const searchMatch =
        deferredSearchTerm.length === 0 ||
        [
          item.id,
          item.title,
          item.headline,
          item.note,
          item.sectorLabel,
          item.region,
          item.price,
        ]
          .join(" ")
          .toLowerCase()
          .includes(deferredSearchTerm);

      return sectorMatch && regionMatch && searchMatch;
    });
  }, [deferredSearchTerm, listings, region, sector]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / DEFAULT_PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const visibleItems = useMemo(() => {
    const start = (currentPage - 1) * DEFAULT_PAGE_SIZE;

    return filtered.slice(start, start + DEFAULT_PAGE_SIZE);
  }, [currentPage, filtered]);

  useEffect(() => {
    if (!syncWithUrl) {
      return;
    }

    const params = new URLSearchParams(window.location.search);

    if (sector === "전체") {
      params.delete("sector");
    } else {
      params.set("sector", sector);
    }

    if (region === "전체") {
      params.delete("region");
    } else {
      params.set("region", region);
    }

    if (searchTerm.trim().length === 0) {
      params.delete("q");
    } else {
      params.set("q", searchTerm.trim());
    }

    if (currentPage <= 1) {
      params.delete("page");
    } else {
      params.set("page", String(currentPage));
    }

    const nextQuery = params.toString();
    const nextUrl = nextQuery ? `${window.location.pathname}?${nextQuery}` : window.location.pathname;
    const currentUrl = `${window.location.pathname}${window.location.search}`;

    if (nextUrl === currentUrl) {
      return;
    }

    window.history.replaceState(window.history.state, "", nextUrl);
  }, [currentPage, region, searchTerm, sector, syncWithUrl]);

  const pagination = buildPagination(currentPage, totalPages);

  return (
    <section className="listing-board">
      <div className="listing-board-grid">
        <aside className="listing-filter">
          <label className="listing-search" htmlFor={searchId}>
            <span>매물 검색</span>
            <div className="listing-search-control">
              <input
                id={searchId}
                type="search"
                placeholder="등록번호 또는 키워드"
                value={searchTerm}
                onChange={(event) => {
                  setSearchTerm(event.target.value);
                  setPage(1);
                }}
              />
              {searchTerm ? (
                <button
                  type="button"
                  className="listing-search-clear"
                  onClick={() => {
                    setSearchTerm("");
                    setPage(1);
                  }}
                >
                  초기화
                </button>
              ) : null}
            </div>
          </label>

          <div className="listing-filter-group">
            <p>업종</p>
            <div className="chip-wrap">
              {sectorOptions.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`chip${sector === item ? " chip--active" : ""}`}
                  aria-pressed={sector === item}
                  onClick={() => {
                    setSector(item);
                    setPage(1);
                  }}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="listing-filter-group">
            <p>지역</p>
            <div className="chip-wrap">
              {regionOptions.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`chip${region === item ? " chip--active" : ""}`}
                  aria-pressed={region === item}
                  onClick={() => {
                    setRegion(item);
                    setPage(1);
                  }}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="listing-summary-box">
            <strong>{filtered.length}건 확인 가능</strong>
            <span>구글시트 원본과 공개 게시판 보존본을 병합한 최신 매물 기준입니다.</span>
          </div>
        </aside>

        <div className={`listing-table-shell${isFiltering ? " listing-table-shell--pending" : ""}`}>
          <div className="listing-results-status" aria-live="polite">
            {isFiltering ? "검색 반영 중..." : `${filtered.length}건 조건 반영 완료`}
          </div>
          <div className="listing-table-head">
            <span>등록번호</span>
            <span>상태</span>
            <span>업종</span>
            <span>면허년도</span>
            <span>시공 / 실적</span>
            <span>메모</span>
            <span>양도가</span>
          </div>

          <div className="listing-table-body">
            {visibleItems.length > 0 ? (
              visibleItems.map((item) => (
                <article key={item.id} className="listing-row">
                  <div className="listing-cell listing-cell--title">
                    <span className="listing-cell-label">등록번호</span>
                    <Link className="listing-title-link" href={`/mna/${encodeURIComponent(item.id)}`}>
                      <strong>{item.id}</strong>
                    </Link>
                    <small>
                      {item.region || "지역 협의"} · {item.headline || item.note || item.sectorLabel}
                    </small>
                  </div>
                  <div className="listing-cell">
                    <span className="listing-cell-label">상태</span>
                    <span className={`status-badge status-badge--${getStatusTone(item.status)}`}>{item.status || "검토중"}</span>
                  </div>
                  <div className="listing-cell">
                    <span className="listing-cell-label">업종</span>
                    <span>{item.sectorLabel}</span>
                  </div>
                  <div className="listing-cell">
                    <span className="listing-cell-label">면허년도</span>
                    <span>{item.licenseYears.join(" / ") || item.companyYear || "-"}</span>
                  </div>
                  <div className="listing-cell">
                    <span className="listing-cell-label">시공 / 실적</span>
                    <strong>{item.capacityLabel || "-"}</strong>
                    <small>{item.performance3Year || item.performance5Year || "-"}</small>
                  </div>
                  <div className="listing-cell">
                    <span className="listing-cell-label">메모</span>
                    <span>{item.note || item.companyType || "-"}</span>
                  </div>
                  <div className="listing-cell listing-cell--price">
                    <span className="listing-cell-label">양도가</span>
                    <span className="price-cell">{item.price || "협의"}</span>
                  </div>
                </article>
              ))
            ) : (
              <div className="listing-empty-state">
                <strong>현재 조건에 맞는 매물이 없습니다.</strong>
                <p>필터를 다시 선택하거나 고객센터에서 직접 상담을 요청해 주세요.</p>
                <Link href="/support" className="cta-primary listing-empty-action">
                  고객센터 이동
                </Link>
              </div>
            )}
          </div>

          {totalPages > 1 ? (
            <nav className="listing-pagination" aria-label="매물 페이지 이동">
              {currentPage > 1 ? (
                <button type="button" className="listing-pagination-link" onClick={() => setPage(currentPage - 1)}>
                  이전
                </button>
              ) : null}

              {pagination.map((pageNumber) => (
                <button
                  key={pageNumber}
                  type="button"
                  className={`listing-pagination-link${pageNumber === currentPage ? " listing-pagination-link--active" : ""}`}
                  onClick={() => setPage(pageNumber)}
                  aria-current={pageNumber === currentPage ? "page" : undefined}
                >
                  {pageNumber}
                </button>
              ))}

              {currentPage < totalPages ? (
                <button type="button" className="listing-pagination-link" onClick={() => setPage(currentPage + 1)}>
                  다음
                </button>
              ) : null}
            </nav>
          ) : null}
        </div>
      </div>
    </section>
  );
}
