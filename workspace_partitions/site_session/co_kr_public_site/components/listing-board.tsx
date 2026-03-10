"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useId, useMemo, useState } from "react";
import { getAllListings } from "@/lib/listings";

const sectors = ["전체", "건축", "토목", "실내건축", "전기", "조경", "기계설비"] as const;
const regions = ["전체", "수도권", "충청", "영남", "호남"] as const;
const statusToneMap = {
  가능: "available",
  검토중: "review",
  협의중: "pending",
} as const;
const listingItems = getAllListings();

function getValidSector(value: string | null) {
  return sectors.find((item) => item === value) ?? "전체";
}

function getValidRegion(value: string | null) {
  return regions.find((item) => item === value) ?? "전체";
}

export function ListingBoard({
  compact = false,
  syncWithUrl = false,
  initialFilters,
}: {
  compact?: boolean;
  syncWithUrl?: boolean;
  initialFilters?: {
    sector?: string;
    region?: string;
    q?: string;
  };
}) {
  const searchId = useId();
  const [sector, setSector] = useState<(typeof sectors)[number]>(() => getValidSector(initialFilters?.sector ?? null));
  const [region, setRegion] = useState<(typeof regions)[number]>(() => getValidRegion(initialFilters?.region ?? null));
  const [searchTerm, setSearchTerm] = useState(() => initialFilters?.q ?? "");
  const deferredSearchTerm = useDeferredValue(searchTerm.trim().toLowerCase());
  const isFiltering = searchTerm.trim().toLowerCase() !== deferredSearchTerm;

  useEffect(() => {
    if (!syncWithUrl) {
      return;
    }

    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      setSector(getValidSector(params.get("sector")));
      setRegion(getValidRegion(params.get("region")));
      setSearchTerm(params.get("q") ?? "");
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [syncWithUrl]);

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

    const nextQuery = params.toString();
    const nextUrl = nextQuery ? `${window.location.pathname}?${nextQuery}` : window.location.pathname;
    const currentUrl = `${window.location.pathname}${window.location.search}`;

    if (nextUrl === currentUrl) {
      return;
    }

    window.history.replaceState(window.history.state, "", nextUrl);
  }, [region, searchTerm, sector, syncWithUrl]);

  const filtered = useMemo(() => {
    return listingItems.filter((item) => {
      const sectorMatch = sector === "전체" || item.sector === sector;
      const regionMatch = region === "전체" || item.region === region;
      const searchMatch =
        deferredSearchTerm.length === 0 ||
        [item.id, item.title, item.headline, item.memo]
          .join(" ")
          .toLowerCase()
          .includes(deferredSearchTerm);
      return sectorMatch && regionMatch && searchMatch;
    });
  }, [deferredSearchTerm, region, sector]);

  const visibleItems = compact ? filtered.slice(0, 4) : filtered;

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
                onChange={(event) => setSearchTerm(event.target.value)}
              />
              {searchTerm ? (
                <button type="button" className="listing-search-clear" onClick={() => setSearchTerm("")}>
                  초기화
                </button>
              ) : null}
            </div>
          </label>

          <div className="listing-filter-group">
            <p>업종</p>
            <div className="chip-wrap">
              {sectors.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`chip${sector === item ? " chip--active" : ""}`}
                  aria-pressed={sector === item}
                  onClick={() => setSector(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="listing-filter-group">
            <p>지역</p>
            <div className="chip-wrap">
              {regions.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`chip${region === item ? " chip--active" : ""}`}
                  aria-pressed={region === item}
                  onClick={() => setRegion(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="listing-summary-box">
            <strong>{filtered.length}건 확인 가능</strong>
            <span>메인 검증용 샘플 데이터입니다. 실제 운영 시 CMS나 DB로 대체하면 됩니다.</span>
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
                      {item.region} · {item.headline}
                    </small>
                  </div>
                  <div className="listing-cell">
                    <span className="listing-cell-label">상태</span>
                    <span className={`status-badge status-badge--${statusToneMap[item.status]}`}>{item.status}</span>
                  </div>
                  <div className="listing-cell">
                    <span className="listing-cell-label">업종</span>
                    <span>{item.sector}</span>
                  </div>
                  <div className="listing-cell">
                    <span className="listing-cell-label">면허년도</span>
                    <span>{item.licenseYear}</span>
                  </div>
                  <div className="listing-cell">
                    <span className="listing-cell-label">시공 / 실적</span>
                    <strong>{item.capacity}</strong>
                    <small>{item.performance}</small>
                  </div>
                  <div className="listing-cell">
                    <span className="listing-cell-label">메모</span>
                    <span>{item.memo}</span>
                  </div>
                  <div className="listing-cell listing-cell--price">
                    <span className="listing-cell-label">양도가</span>
                    <span className="price-cell">{item.price}</span>
                  </div>
                </article>
              ))
            ) : (
              <div className="listing-empty-state">
                <strong>현재 조건에 맞는 샘플 매물이 없습니다.</strong>
                <p>필터를 다시 선택하거나 고객센터에서 직접 상담을 요청해 주세요.</p>
                <Link href="/support" className="cta-primary listing-empty-action">
                  고객센터 이동
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
